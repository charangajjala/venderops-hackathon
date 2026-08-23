"""Domain models for VendorOps - RFQ, Quote, PurchaseOrder, VendorProfile, etc.

Field descriptions here are not decoration: `structured_output()` hands the model
the JSON schema generated from these `Field(description=...)` values, so each
description is the domain explanation the LLM sees at extraction/decision time.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Incoterm(str, Enum):
    """ICC Incoterms 2020 - who bears shipping cost/risk at each point in transit."""

    EXW = "EXW"  # Ex Works
    FCA = "FCA"  # Free Carrier
    FAS = "FAS"  # Free Alongside Ship
    FOB = "FOB"  # Free On Board
    CFR = "CFR"  # Cost and Freight
    CIF = "CIF"  # Cost, Insurance and Freight
    CPT = "CPT"  # Carriage Paid To
    CIP = "CIP"  # Carriage and Insurance Paid To
    DAP = "DAP"  # Delivered At Place
    DPU = "DPU"  # Delivered at Place Unloaded
    DDP = "DDP"  # Delivered Duty Paid


class PaymentMethod(str, Enum):
    """The underlying payment mechanism - distinct from payment_terms because the
    risk profile differs even at identical terms (escrow vs. net-30-with-a-trusted-
    vendor are not the same risk)."""

    WIRE_TRANSFER = "wire_transfer"
    LETTER_OF_CREDIT = "letter_of_credit"
    ESCROW = "escrow"
    MILESTONE_BASED = "milestone_based"
    ACH = "ach"
    CHECK = "check"
    CREDIT_CARD = "credit_card"
    OTHER = "other"


class POType(str, Enum):
    """Four PO variants. Standard = one-time purchase (VendorOps' MVP case)."""

    STANDARD = "standard"  # one-time purchase
    BLANKET = "blanket"  # recurring spend cap with one vendor
    PLANNED = "planned"  # committed quantity/price, staged deliveries
    CONTRACT = "contract"  # framework agreement signed before specific items defined


class OnboardingStatus(str, Enum):
    """A vendor's qualification state. A hard gate: an unapproved vendor is never
    auto-act eligible, no matter how good their price looks."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"


class RFQStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    QUOTES_RECEIVED = "quotes_received"
    AWARDED = "awarded"
    CANCELLED = "cancelled"


class QuoteStatus(str, Enum):
    RECEIVED = "received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"  # e.g. below vendor's own MOQ, or vendor not approved
    EXPIRED = "expired"


class POStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PARTIALLY_FULFILLED = "partially_fulfilled"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"


class ShipmentStatus(str, Enum):
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    LOST = "lost"


class ReturnReason(str, Enum):
    """Why an RMA was opened - feeds vendor reliability scoring."""

    DEFECTIVE = "defective"
    WRONG_ITEM = "wrong_item"
    DAMAGED_IN_TRANSIT = "damaged_in_transit"
    QUALITY_REJECT = "quality_reject"


class ReturnStatus(str, Enum):
    OPEN = "open"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"


# ---------------------------------------------------------------------------
# Vendor
# ---------------------------------------------------------------------------


class VendorProfile(BaseModel):
    """A vendor VendorOps can request quotes from or purchase from."""

    id: UUID = Field(default_factory=uuid4, description="Unique vendor identifier.")
    name: str = Field(description="Vendor's legal or trading name.")
    contact_email: str | None = Field(
        default=None, description="Primary contact email for sending RFQs and POs."
    )
    location: str | None = Field(
        default=None,
        description="Vendor's city/region, used to evaluate local_preference_pct in ApprovalPolicy.",
    )
    onboarding_status: OnboardingStatus = Field(
        default=OnboardingStatus.PENDING,
        description=(
            "Vendor's qualification state. Hard gate: only APPROVED vendors are "
            "ever eligible for auto-acting, regardless of price."
        ),
    )
    trusted: bool = Field(
        default=False,
        description=(
            "Whether the Autonomy Policy Engine treats this vendor as trusted. "
            "Distinct from onboarding_status - a vendor can be approved-to-transact "
            "but not yet trusted until a track record of deliveries exists. Defaults "
            "False for any vendor with no history."
        ),
    )
    reliability_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description=(
            "0-1 score derived from on-time-delivery rate and RMA rate, updated over "
            "time via memory. Learned, not hand-set."
        ),
    )
    on_time_delivery_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of past shipments delivered on or before the promised lead time.",
    )
    rma_rate: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of past POs that resulted in a Return Merchandise Authorization.",
    )
    historical_avg_price: dict[str, Decimal] = Field(
        default_factory=dict,
        description=(
            "Average historical unit price paid to this vendor, keyed by item/SKU "
            "description. Used to detect price anomalies via "
            "ApprovalPolicy.price_variance_tolerance_pct."
        ),
    )
    tags: list[str] = Field(
        default_factory=list, description="Free-form categorization tags (e.g. item categories supplied)."
    )
    notes: str | None = Field(
        default=None, description="Freeform notes about this vendor not captured in structured fields."
    )
    extra_terms: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Any vendor-specific term that comes up but isn't in the schema - "
            "captured here rather than silently dropped or blocking on a schema change."
        ),
    )


# ---------------------------------------------------------------------------
# RFQ / Quote
# ---------------------------------------------------------------------------


class RFQ(BaseModel):
    """Request For Quotation - the buyer's formal ask: what's needed, how much,
    by when, and under what terms. Sent to multiple vendors at once."""

    id: UUID = Field(default_factory=uuid4, description="Unique RFQ identifier.")
    item_description: str = Field(description="What the buyer needs, in plain terms.")
    quantity: int = Field(gt=0, description="Quantity the buyer wants to purchase.")
    needed_by_date: date = Field(
        description="Date the buyer needs the goods delivered by. Compared against each quote's lead_time."
    )
    budget_ceiling: Decimal | None = Field(
        default=None,
        gt=0,
        description="Maximum total the buyer is willing to pay, if stated up front.",
    )
    requested_incoterm: Incoterm | None = Field(
        default=None, description="Incoterm the buyer is requesting quotes under, if any."
    )
    vendor_ids: list[UUID] = Field(
        default_factory=list, description="Vendors this RFQ was sent to (can be sent to multiple at once)."
    )
    status: RFQStatus = Field(default=RFQStatus.DRAFT, description="Current lifecycle state of this RFQ.")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="When this RFQ was created.")
    extra_terms: dict[str, str] = Field(
        default_factory=dict,
        description="Any buyer-stated term not captured elsewhere in the schema.",
    )


class Quote(BaseModel):
    """A vendor's response to an RFQ. Raw quotes are messy text/PDF; VendorOps
    normalizes them into this structured form."""

    id: UUID = Field(default_factory=uuid4, description="Unique quote identifier.")
    rfq_id: UUID = Field(description="The RFQ this quote responds to.")
    vendor_id: UUID = Field(description="The vendor who submitted this quote.")
    unit_price: Decimal = Field(gt=0, description="Price per unit quoted by the vendor.")
    currency: str = Field(default="USD", description="ISO 4217 currency code for unit_price.")
    quantity: int = Field(gt=0, description="Quantity this quote is priced for.")
    moq: int | None = Field(
        default=None,
        gt=0,
        description=(
            "Minimum Order Quantity the vendor will accept. A quote for less than "
            "the vendor's MOQ isn't actually fulfillable as quoted and should be "
            "rejected/flagged, not silently accepted."
        ),
    )
    lead_time_days: int = Field(
        ge=0, description="Days from order confirmation to delivery. Compared against the RFQ's needed_by_date."
    )
    incoterm: Incoterm | None = Field(
        default=None, description="Incoterm this quote is priced under."
    )
    payment_terms: str = Field(
        description='Human-readable payment schedule, e.g. "Net 30" or "30% deposit, 70% on delivery".'
    )
    payment_method: PaymentMethod | None = Field(
        default=None,
        description=(
            "Underlying payment mechanism (wire, LC, escrow, milestone, etc.). "
            "Distinct from payment_terms - the risk profile differs even at identical terms."
        ),
    )
    warranty_terms: str | None = Field(
        default=None,
        description="Vendor's stated warranty terms. Absence of this is itself a signal worth flagging, not just missing data.",
    )
    valid_until: date | None = Field(
        default=None, description="Date after which this quote is no longer honored by the vendor."
    )
    status: QuoteStatus = Field(default=QuoteStatus.RECEIVED, description="Current state of this quote.")
    received_at: datetime = Field(
        default_factory=datetime.utcnow, description="When this quote was received/normalized."
    )
    extra_terms: dict[str, str] = Field(
        default_factory=dict,
        description="Any quoted term that comes up but isn't in the schema - captured here, never silently dropped.",
    )

    @field_validator("quantity")
    @classmethod
    def quantity_meets_moq(cls, v: int, info) -> int:
        moq = info.data.get("moq")
        if moq is not None and v < moq:
            raise ValueError(f"quoted quantity {v} is below vendor's stated MOQ {moq}")
        return v


# ---------------------------------------------------------------------------
# Purchase Order / amendments / shipments / returns
# ---------------------------------------------------------------------------


class PurchaseOrder(BaseModel):
    """The buyer's formal commitment to purchase - legally the order itself, not
    just a request. Generated once a vendor is selected."""

    id: UUID = Field(default_factory=uuid4, description="Unique purchase order identifier.")
    po_type: POType = Field(
        default=POType.STANDARD,
        description=(
            "Standard = one-time purchase. Blanket = recurring spend cap with one "
            "vendor. Planned = committed quantity/price, staged deliveries. "
            "Contract = framework agreement signed before specific items are defined."
        ),
    )
    rfq_id: UUID | None = Field(default=None, description="The RFQ this PO originated from, if any.")
    quote_id: UUID = Field(description="The winning quote this PO was generated from.")
    vendor_id: UUID = Field(description="The vendor this order was placed with.")
    item_description: str = Field(description="What is being purchased.")
    quantity: int = Field(gt=0, description="Quantity ordered.")
    unit_price: Decimal = Field(gt=0, description="Agreed price per unit.")
    total_price: Decimal = Field(gt=0, description="Total committed spend for this PO (unit_price * quantity plus any adjustments).")
    currency: str = Field(default="USD", description="ISO 4217 currency code for unit_price/total_price.")
    incoterm: Incoterm | None = Field(default=None, description="Agreed Incoterm for this order.")
    payment_terms: str = Field(description="Agreed human-readable payment schedule.")
    payment_method: PaymentMethod | None = Field(default=None, description="Agreed underlying payment mechanism.")
    needed_by_date: date | None = Field(default=None, description="Date the buyer needs delivery by.")
    lead_time_days: int | None = Field(default=None, ge=0, description="Agreed days from order confirmation to delivery.")
    status: POStatus = Field(default=POStatus.DRAFT, description="Current lifecycle state of this PO.")
    auto_approved: bool = Field(
        default=False,
        description="Whether this PO was issued autonomously without human approval, per ApprovalPolicy.",
    )
    approver: str | None = Field(
        default=None, description="Identity of the human who approved this PO, if a human was involved."
    )
    issued_at: datetime | None = Field(default=None, description="When this PO was issued to the vendor.")
    extra_terms: dict[str, str] = Field(
        default_factory=dict,
        description="Any agreed term that comes up but isn't in the schema - never silently dropped.",
    )


class POAmendment(BaseModel):
    """A modification to an existing PO (price, quantity, cancellation). Modeled
    as its own record rather than an in-place edit, to preserve an audit trail.
    The PO itself is never silently mutated."""

    id: UUID = Field(default_factory=uuid4, description="Unique amendment identifier.")
    po_id: UUID = Field(description="The PO being amended.")
    field_changed: str = Field(description='Name of the PO field being changed, e.g. "quantity" or "unit_price".')
    old_value: str = Field(description="Previous value of the field, as a string.")
    new_value: str = Field(description="New value of the field, as a string.")
    reason: str = Field(description="Why this amendment was made.")
    approver: str | None = Field(default=None, description="Who approved this amendment, if a human was involved.")
    amended_at: datetime = Field(default_factory=datetime.utcnow, description="When this amendment was recorded.")


class ShipmentRecord(BaseModel):
    """One delivery against a PO. A PO isn't assumed to be one PO = one delivery -
    partial shipments/backorders are tracked as multiple ShipmentRecords."""

    id: UUID = Field(default_factory=uuid4, description="Unique shipment record identifier.")
    po_id: UUID = Field(description="The PO this shipment fulfills, in part or in full.")
    quantity_shipped: int = Field(gt=0, description="Quantity included in this shipment.")
    carrier: str | None = Field(default=None, description="Shipping carrier used.")
    tracking_number: str | None = Field(default=None, description="Carrier tracking number, if available.")
    status: ShipmentStatus = Field(default=ShipmentStatus.IN_TRANSIT, description="Current shipment status.")
    shipped_at: datetime | None = Field(default=None, description="When this shipment left the vendor.")
    delivered_at: datetime | None = Field(default=None, description="When this shipment was received by the buyer.")


class ReturnAuthorization(BaseModel):
    """RMA - the formal process for returning goods: defective, wrong item,
    damaged in transit, or quality reject. Resolution outcome eventually degrades
    or preserves the vendor's reliability_score."""

    id: UUID = Field(default_factory=uuid4, description="Unique RMA identifier.")
    po_id: UUID = Field(description="The PO this return relates to.")
    shipment_record_id: UUID | None = Field(
        default=None, description="The specific shipment this return relates to, if known."
    )
    reason: ReturnReason = Field(description="Why the return was opened.")
    quantity: int = Field(gt=0, description="Quantity being returned.")
    status: ReturnStatus = Field(default=ReturnStatus.OPEN, description="Current state of this RMA.")
    opened_at: datetime = Field(default_factory=datetime.utcnow, description="When this RMA was opened.")
    resolved_at: datetime | None = Field(default=None, description="When this RMA reached a final resolution.")
    resolution: str | None = Field(
        default=None, description="How this RMA was resolved, e.g. replacement shipped, refund issued."
    )


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------


class ApprovalPolicy(BaseModel):
    """Explicit, human-set policy config the Decision Agent reads directly -
    deliberately not folded into a prompt as prose and not left for the model to
    learn/infer on its own. See docs/README.md section 4d."""

    auto_approve_limit: Decimal = Field(
        gt=0,
        description="Maximum total PO value that may be auto-approved without human involvement. Always escalates above this, regardless of how clean the decision otherwise looks.",
    )
    price_variance_tolerance_pct: float = Field(
        default=15.0,
        ge=0,
        description="Max allowed percentage deviation of a quote's unit_price from the vendor's historical_avg_price before it's treated as a price anomaly requiring escalation.",
    )
    local_preference_pct: float = Field(
        default=5.0,
        ge=0,
        description="If a local vendor's price is within this percentage of the cheapest quote, it is preferred automatically without escalation.",
    )
    require_trusted_vendor_for_auto_approve: bool = Field(
        default=True,
        description="If True, only vendors with trusted=True are eligible for auto-approval, even if within auto_approve_limit.",
    )
    require_warranty_terms: bool = Field(
        default=True,
        description="If True, a quote missing warranty_terms is flagged for human review rather than auto-approved.",
    )
