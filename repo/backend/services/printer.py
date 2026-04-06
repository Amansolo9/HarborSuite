from __future__ import annotations

import json
import re
import shlex
import subprocess
from pathlib import Path

from backend.core.config import settings
from sqlalchemy.orm import Session

from backend.models import PrintJob, UserAccount
from backend.services.audit import audit_event


def _dispatch_to_local_printer(queue_file: Path) -> bool:
    template = settings.print_command_template.strip()
    if not template:
        return False
    file_path = str(queue_file)
    if not re.match(r'^[\w\-./\\: ]+$', file_path):
        return False
    try:
        parts = shlex.split(template)
        args = [file_path if part == "{file}" else part for part in parts]
        if "{file}" not in parts:
            args.append(file_path)
        result = subprocess.run(args, shell=False, check=False, capture_output=True, text=True)
        return result.returncode == 0
    except Exception:
        return False


def queue_document_print(
    db: Session,
    user: UserAccount,
    folio_id: str,
    document_type: str,
    payload: dict[str, object],
) -> PrintJob:
    job = PrintJob(
        organization_id=user.organization_id,
        created_by_user_id=user.id,
        folio_id=folio_id,
        document_type=document_type,
        payload_json=json.dumps(payload, default=str),
        status="queued",
    )
    db.add(job)
    db.flush()

    queue_dir = Path("data/print_queue") / user.organization_id
    queue_dir.mkdir(parents=True, exist_ok=True)
    queue_file = queue_dir / f"print-job-{job.id}.json"
    queue_file.write_text(job.payload_json, encoding="utf-8")

    if _dispatch_to_local_printer(queue_file):
        job.status = "dispatched"
        audit_event(db, user, "print_dispatched", "print_job", job.id, {"folio_id": folio_id, "queue_path": str(queue_file)})
    else:
        job.status = "queued"

    audit_event(db, user, f"{document_type}_print_queued", "print_job", job.id, {"folio_id": folio_id, "queue_path": str(queue_file)})
    db.commit()
    db.refresh(job)
    return job


def queue_receipt_print(db: Session, user: UserAccount, folio_id: str, receipt: dict[str, object]) -> PrintJob:
    return queue_document_print(db, user, folio_id, "folio_receipt", receipt)


def queue_invoice_print(db: Session, user: UserAccount, folio_id: str, invoice: dict[str, object]) -> PrintJob:
    return queue_document_print(db, user, folio_id, "folio_invoice", invoice)
