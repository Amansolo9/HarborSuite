from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from backend.models import ContentStatus, ContentType, OrderState, PaymentMethod, Role


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str | None = None
    token_type: str | None = None
    expires_in_seconds: int
    user_id: str
    full_name: str
    role: Role
    organization_id: str
    organization_name: str


class CurrentUserResponse(BaseModel):
    user_id: str
    username: str
    full_name: str
    role: Role
    organization_id: str
    organization_name: str
    session_idle_minutes: int


class OverviewResponse(BaseModel):
    property_name: str
    role: Role
    open_folios: int
    active_orders: int
    pending_content: int
    open_complaints: int
    unread_releases: int
    pending_exports: int


class OrderItemRequest(BaseModel):
    sku: str | None = Field(default=None, max_length=80)
    name: str
    quantity: int = Field(ge=1, le=50)
    unit_price: Decimal = Field(ge=0)
    size: str | None = Field(default=None, max_length=40)
    specs: dict[str, str] = Field(default_factory=dict)
    delivery_slot_label: str | None = Field(default=None, max_length=80)


class CreateOrderRequest(BaseModel):
    folio_id: str
    items: list[OrderItemRequest] = Field(min_length=1)
    payment_method: PaymentMethod
    packaging_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    service_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    order_note: str | None = Field(default=None, max_length=250)
    delivery_window_start: datetime
    delivery_window_end: datetime
    price_confirmed_at: datetime
    reconfirm_token: str


class ConfirmQuoteRequest(BaseModel):
    folio_id: str
    items: list[OrderItemRequest] = Field(min_length=1)
    payment_method: PaymentMethod
    packaging_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    service_fee: Decimal = Field(default=Decimal("0.00"), ge=0)
    tax_rate: Decimal = Field(default=Decimal("0.10"), ge=0, le=1)
    delivery_window_start: datetime
    delivery_window_end: datetime


class ConfirmQuoteResponse(BaseModel):
    reconfirm_token: str
    expires_at: datetime
    quote_hash: str


class OrderResponse(BaseModel):
    id: str
    folio_id: str
    organization_id: str
    state: OrderState
    subtotal_amount: Decimal
    packaging_fee: Decimal
    service_fee: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    payment_method: PaymentMethod
    order_items: list[OrderItemRequest]
    delivery_window_start: datetime
    delivery_window_end: datetime
    tax_reconfirm_by: datetime
    order_note: str | None = None
    reversal_reason: str | None = None
    created_by_user_id: str
    service_end_at: datetime | None = None


class OrderTransitionRequest(BaseModel):
    next_state: OrderState
    reversal_reason: str | None = None


class OrderAllocationRow(BaseModel):
    supplier: str = Field(min_length=2, max_length=120)
    warehouse: str = Field(min_length=2, max_length=120)
    sla_tier: str = Field(min_length=2, max_length=80)
    quantity: int = Field(ge=1)


class OrderSplitRequest(BaseModel):
    allocations: list[OrderAllocationRow] = Field(min_length=1)


class OrderMergeRequest(BaseModel):
    supplier: str = Field(min_length=2, max_length=120)
    warehouse: str = Field(min_length=2, max_length=120)
    sla_tier: str = Field(min_length=2, max_length=80)


class OrderAllocationResponse(BaseModel):
    supplier: str
    warehouse: str
    sla_tier: str
    quantity: int


class FolioPaymentRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    payment_method: PaymentMethod
    note: str | None = Field(default=None, max_length=255)


class FolioAdjustmentRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=5, max_length=255)


class FolioReversalRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=5, max_length=255)


class FolioChargeRequest(BaseModel):
    amount: Decimal = Field(gt=0)
    reason: str = Field(min_length=5, max_length=255)
    payment_method: PaymentMethod | None = None


class FolioSplitRequest(BaseModel):
    allocations: list[Decimal] = Field(min_length=2)


class FolioSplitAllocationResponse(BaseModel):
    source_folio_id: str
    child_folio_id: str
    amount: Decimal


class FolioMergeRequest(BaseModel):
    primary_folio_id: str
    secondary_folio_id: str


class FolioReceiptResponse(BaseModel):
    folio_id: str
    guest_name: str
    room_number: str
    balance_due: Decimal
    printable_lines: list[str]


class FolioInvoiceResponse(BaseModel):
    folio_id: str
    invoice_id: str
    guest_name: str
    room_number: str
    balance_due: Decimal
    invoice_lines: list[str]


class PrintJobResponse(BaseModel):
    print_job_id: str
    status: str
    queue_path: str


class FolioSummaryResponse(BaseModel):
    id: str
    guest_name: str
    room_number: str
    status: str
    balance_due: Decimal


class ContentReleaseRequest(BaseModel):
    title: str = Field(min_length=4, max_length=140)
    body: str = Field(min_length=10, max_length=4000)
    content_type: ContentType = ContentType.ANNOUNCEMENT
    target_roles: list[Role] = Field(min_length=1)
    target_tags: list[str] = Field(default_factory=lambda: ["all"])
    target_organizations: list[str] = Field(default_factory=lambda: ["all"])


class ContentReleaseResponse(BaseModel):
    id: str
    title: str
    content_type: ContentType
    version: int
    status: ContentStatus
    target_roles: list[Role]
    target_tags: list[str]
    target_organizations: list[str]
    readership_count: int
    rollback_of_id: str | None = None


class ComplaintRequest(BaseModel):
    folio_id: str
    subject: str = Field(min_length=4, max_length=140)
    detail: str = Field(min_length=10, max_length=2000)
    service_rating: int = Field(ge=1, le=5)
    violation_flag: bool = False


class ComplaintResponse(BaseModel):
    id: str
    subject: str
    service_rating: int
    violation_flag: bool
    folio_id: str


class ComplaintPacketResponse(BaseModel):
    complaint_id: str
    checksum: str
    sections: list[str]
    packet_filename: str
    packet_path: str
    packet_media_type: str
    manifest_path: str
    download_url: str


class RatingRequest(BaseModel):
    to_username: str
    score: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=255)
    order_id: str


class RatingResponse(BaseModel):
    id: str
    from_user_id: str
    to_user_id: str
    score: int
    comment: str | None
    order_id: str | None
    created_at: datetime


class MetricDefinitionRequest(BaseModel):
    metric_name: str = Field(min_length=3, max_length=120)
    description: str = Field(min_length=5, max_length=255)
    source_query_ref: str = Field(min_length=3, max_length=255)
    version: int = Field(default=1, ge=1)


class MetricDefinitionResponse(BaseModel):
    id: str
    metric_name: str
    description: str
    source_query_ref: str
    version: int


class DatasetVersionRequest(BaseModel):
    dataset_name: str = Field(min_length=3, max_length=120)
    version: str = Field(min_length=1, max_length=40)
    dataset_schema: dict[str, str]


class DatasetVersionResponse(BaseModel):
    id: str
    dataset_name: str
    version: str
    checksum: str


class LineageRequest(BaseModel):
    metric_name: str = Field(min_length=3, max_length=120)
    dataset_version_id: str
    source_tables: list[str] = Field(min_length=1)
    source_query_ref: str = Field(min_length=3, max_length=255)


class LineageResponse(BaseModel):
    id: str
    metric_name: str
    dataset_version_id: str
    source_tables: list[str]
    source_query_ref: str


class DataDictionaryExportResponse(BaseModel):
    organization_id: str
    fields: list[dict[str, str]]


class ExportRequest(BaseModel):
    export_type: str = Field(min_length=3, max_length=80)
    scope: str = Field(min_length=3, max_length=80)


class ExportResponse(BaseModel):
    export_id: str
    export_type: str
    storage_path: str
    checksum: str


class AuditEventResponse(BaseModel):
    id: str
    actor: str
    action: str
    resource_type: str
    resource_id: str
    organization_id: str
    created_at: datetime
    metadata: dict[str, str]
