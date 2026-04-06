import enum
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import mapped_column, relationship

from .base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    GUEST = "guest"
    FRONT_DESK = "front_desk"
    SERVICE_STAFF = "service_staff"
    FINANCE = "finance"
    CONTENT_EDITOR = "content_editor"
    GENERAL_MANAGER = "general_manager"


class PaymentMethod(str, enum.Enum):
    CASH = "cash"
    CARD_PRESENT_MANUAL = "card_present_manual"
    GIFT_CERTIFICATE = "gift_certificate"
    DIRECT_BILL = "direct_bill"


class FolioStatus(str, enum.Enum):
    OPEN = "open"
    IN_AUDIT = "in_audit"
    CLOSED = "closed"


class FolioEntryType(str, enum.Enum):
    CHARGE = "charge"
    PAYMENT = "payment"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"


class OrderState(str, enum.Enum):
    CREATED = "created"
    CONFIRMED = "confirmed"
    IN_PREP = "in_prep"
    DELIVERED = "delivered"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class ContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    ROLLED_BACK = "rolled_back"


class ContentType(str, enum.Enum):
    ANNOUNCEMENT = "announcement"
    NEWS = "news"
    CAROUSEL_PROMO = "carousel_promo"


class DayCloseStatus(str, enum.Enum):
    COMPLETED = "completed"
    FAILED = "failed"


ALLOWED_ORDER_TRANSITIONS = {
    OrderState.CREATED: {OrderState.CONFIRMED, OrderState.IN_PREP, OrderState.CANCELED},
    OrderState.CONFIRMED: {OrderState.IN_PREP, OrderState.CANCELED, OrderState.REFUNDED},
    OrderState.IN_PREP: {OrderState.DELIVERED, OrderState.CANCELED},
    OrderState.DELIVERED: {OrderState.REFUNDED},
    OrderState.CANCELED: set(),
    OrderState.REFUNDED: set(),
}


class Organization(Base):
    __tablename__ = "organizations"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = mapped_column(String(200), nullable=False)
    code = mapped_column(String(50), nullable=False, unique=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class UserAccount(Base):
    __tablename__ = "users"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    username = mapped_column(String(120), nullable=False, unique=True)
    full_name = mapped_column(String(140), nullable=False)
    role = mapped_column(Enum(Role, native_enum=False), nullable=False)
    audience_tags = mapped_column(String(255), default="all", nullable=False)
    password_hash = mapped_column(String(255), nullable=False)
    failed_login_attempts = mapped_column(Integer, default=0, nullable=False)
    locked_until = mapped_column(DateTime(timezone=True), nullable=True)
    last_activity_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class SessionToken(Base):
    __tablename__ = "session_tokens"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash = mapped_column(String(64), nullable=False, unique=True, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    last_seen_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)


class Folio(Base):
    __tablename__ = "folios"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    guest_user_id = mapped_column(ForeignKey("users.id"), nullable=True)
    guest_name = mapped_column(String(140), nullable=False)
    room_number = mapped_column(String(20), nullable=False)
    status = mapped_column(Enum(FolioStatus, native_enum=False), default=FolioStatus.OPEN, nullable=False)
    opened_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    closed_at = mapped_column(DateTime(timezone=True), nullable=True)

    entries = relationship("FolioEntry", back_populates="folio", cascade="all, delete-orphan")


class FolioEntry(Base):
    __tablename__ = "folio_entries"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    folio_id = mapped_column(ForeignKey("folios.id"), nullable=False, index=True)
    entry_type = mapped_column(Enum(FolioEntryType, native_enum=False), nullable=False)
    amount = mapped_column(Numeric(12, 2), nullable=False)
    payment_method = mapped_column(Enum(PaymentMethod, native_enum=False), nullable=True)
    note = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    folio = relationship("Folio", back_populates="entries")


class Order(Base):
    __tablename__ = "orders"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    folio_id = mapped_column(ForeignKey("folios.id"), nullable=False, index=True)
    created_by_user_id = mapped_column(ForeignKey("users.id"), nullable=False)
    service_staff_user_id = mapped_column(ForeignKey("users.id"), nullable=True)
    state = mapped_column(Enum(OrderState, native_enum=False), default=OrderState.CREATED, nullable=False)
    subtotal_amount = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    packaging_fee = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    service_fee = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_amount = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_amount = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    payment_method = mapped_column(Enum(PaymentMethod, native_enum=False), nullable=False)
    order_items_json = mapped_column(Text, nullable=False)
    order_note = mapped_column(String(250), nullable=True)
    delivery_window_start = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_window_end = mapped_column(DateTime(timezone=True), nullable=False)
    price_confirmed_at = mapped_column(DateTime(timezone=True), nullable=False)
    tax_reconfirm_by = mapped_column(DateTime(timezone=True), nullable=False)
    reversal_reason = mapped_column(String(255), nullable=True)
    service_start_at = mapped_column(DateTime(timezone=True), nullable=True)
    service_end_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    def transition_to(self, next_state: OrderState) -> None:
        allowed = ALLOWED_ORDER_TRANSITIONS[self.state]
        if next_state not in allowed:
            raise ValueError(f"Invalid order transition: {self.state.value} -> {next_state.value}")
        self.state = next_state


class ContentRelease(Base):
    __tablename__ = "content_releases"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    title = mapped_column(String(140), nullable=False)
    body = mapped_column(Text, nullable=False)
    content_type = mapped_column(Enum(ContentType, native_enum=False), default=ContentType.ANNOUNCEMENT, nullable=False)
    version = mapped_column(Integer, default=1, nullable=False)
    status = mapped_column(Enum(ContentStatus, native_enum=False), default=ContentStatus.PENDING_APPROVAL, nullable=False)
    target_roles = mapped_column(String(255), nullable=False)
    target_tags = mapped_column(String(255), nullable=False)
    target_organizations = mapped_column(String(255), default="all", nullable=False)
    readership_count = mapped_column(Integer, default=0, nullable=False)
    rollback_of_id = mapped_column(String(36), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ContentReadEvent(Base):
    __tablename__ = "content_read_events"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    release_id = mapped_column(ForeignKey("content_releases.id"), nullable=False, index=True)
    user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ComplaintCase(Base):
    __tablename__ = "complaint_cases"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    folio_id = mapped_column(ForeignKey("folios.id"), nullable=False)
    reported_by_user_id = mapped_column(ForeignKey("users.id"), nullable=False)
    subject = mapped_column(String(140), nullable=False)
    detail = mapped_column(Text, nullable=False)
    service_rating = mapped_column(Integer, nullable=False)
    violation_flag = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ExportBundle(Base):
    __tablename__ = "export_bundles"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    export_type = mapped_column(String(80), nullable=False)
    scope = mapped_column(String(80), nullable=False)
    checksum = mapped_column(String(64), nullable=False)
    storage_path = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class AnalyticsSnapshot(Base):
    __tablename__ = "analytics_snapshots"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    snapshot_type = mapped_column(String(60), nullable=False, index=True)
    payload_json = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor = mapped_column(String(120), nullable=False)
    action = mapped_column(String(120), nullable=False)
    resource_type = mapped_column(String(60), nullable=False)
    resource_id = mapped_column(String(36), nullable=False)
    organization_id = mapped_column(String(36), nullable=False, index=True)
    metadata_json = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Rating(Base):
    __tablename__ = "ratings"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    order_id = mapped_column(ForeignKey("orders.id"), nullable=True, index=True)
    from_user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    to_user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    score = mapped_column(Integer, nullable=False)
    comment = mapped_column(String(255), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class OrderAllocation(Base):
    __tablename__ = "order_allocations"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    order_id = mapped_column(ForeignKey("orders.id"), nullable=False, index=True)
    supplier = mapped_column(String(120), nullable=False)
    warehouse = mapped_column(String(120), nullable=False)
    sla_tier = mapped_column(String(80), nullable=False)
    quantity = mapped_column(Integer, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class DayCloseRun(Base):
    __tablename__ = "day_close_runs"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    business_date = mapped_column(String(10), nullable=False, index=True)
    cutoff_time = mapped_column(String(5), nullable=False)
    status = mapped_column(Enum(DayCloseStatus, native_enum=False), nullable=False)
    failed_count = mapped_column(Integer, default=0, nullable=False)
    auto_posted_entries = mapped_column(Integer, default=0, nullable=False)
    details_json = mapped_column(Text, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class MetricDefinition(Base):
    __tablename__ = "metric_definitions"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    metric_name = mapped_column(String(120), nullable=False, index=True)
    description = mapped_column(String(255), nullable=False)
    source_query_ref = mapped_column(String(255), nullable=False)
    version = mapped_column(Integer, default=1, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    dataset_name = mapped_column(String(120), nullable=False, index=True)
    version = mapped_column(String(40), nullable=False)
    schema_json = mapped_column(Text, nullable=False)
    checksum = mapped_column(String(64), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class DataLineage(Base):
    __tablename__ = "data_lineage"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    metric_name = mapped_column(String(120), nullable=False)
    dataset_version_id = mapped_column(ForeignKey("dataset_versions.id"), nullable=False, index=True)
    source_tables = mapped_column(String(255), nullable=False)
    source_query_ref = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class DataDictionaryField(Base):
    __tablename__ = "data_dictionary_fields"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    dataset_name = mapped_column(String(120), nullable=False)
    field_name = mapped_column(String(120), nullable=False)
    data_type = mapped_column(String(80), nullable=False)
    sensitivity = mapped_column(String(40), nullable=False)
    description = mapped_column(String(255), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    created_by_user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    folio_id = mapped_column(ForeignKey("folios.id"), nullable=False, index=True)
    document_type = mapped_column(String(60), nullable=False)
    payload_json = mapped_column(Text, nullable=False)
    status = mapped_column(String(20), default="queued", nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class FolioSplitAllocation(Base):
    __tablename__ = "folio_split_allocations"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    source_folio_id = mapped_column(ForeignKey("folios.id"), nullable=False, index=True)
    child_folio_id = mapped_column(ForeignKey("folios.id"), nullable=False, index=True)
    amount = mapped_column(Numeric(12, 2), nullable=False)
    created_by_user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class CreditProfile(Base):
    __tablename__ = "credit_profiles"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    score = mapped_column(Integer, default=700, nullable=False)
    violation_count = mapped_column(Integer, default=0, nullable=False)
    last_rating = mapped_column(Integer, default=3, nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class CreditEvent(Base):
    __tablename__ = "credit_events"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    rating = mapped_column(Integer, nullable=False)
    penalty = mapped_column(Numeric(12, 2), nullable=False)
    violation = mapped_column(Boolean, default=False, nullable=False)
    note = mapped_column(String(255), nullable=True)
    created_by_user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class OrderQuote(Base):
    __tablename__ = "order_quotes"

    id = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id = mapped_column(ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    folio_id = mapped_column(ForeignKey("folios.id"), nullable=False, index=True)
    quote_hash = mapped_column(String(64), nullable=False)
    reconfirm_token = mapped_column(String(72), nullable=False, unique=True, index=True)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
