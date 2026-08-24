from enum import Enum

from pydantic import BaseModel, Field

from models import RFQ, ApprovalPolicy, Quote, VendorProfile
from datetime import date, timedelta


class Outcome(str, Enum):
    """What decision agent should do with the quote"""
    REJECT = "reject"
    AUTO_APPROVE = "auto_approve"
    ESCALATE = "escalate"

def reject_reasons(quote: Quote, vendor: VendorProfile) -> list[str]:
    """checked before a quote ever reaches comparision. An unapproved vendor or a below MOQ quote is rejected regardless of price"""
    reasons: list[str] = []
    if vendor.onboarding_status != "approved":
        reasons.append(f"vendor onboarding_status is {vendor.onboarding_status}, not approved")

    if quote.moq is not None and quote.quantity < quote.moq:
        reasons.append(f"quoted quantity {quote.quantity} is below vendor's stated MOQ, which is {quote.moq}")
    return reasons

def misses_deadline(quote: Quote, rfq: RFQ, order_date=None) -> bool:
    """Wheather this quote lead time would miss the RFQs needed by date"""
    order_date = order_date or date.today()
    return order_date + timedelta(days=quote.lead_time_days) > rfq.needed_by_date

def exceeds_budget(quote: Quote, rfq: RFQ) -> bool:
    """Wheather this quote total exceeds the RFQs stated budget ceiling"""
    if rfq.budget_ceiling is None:
        return False
    return quote.unit_price * quote.quantity > rfq.budget_ceiling

class Decision(BaseModel):
    """Result of evaluating a single quote against policy"""
    outcome: Outcome = Field(description="What VendorOps should do with this quote.")
    reasons: list[str] = Field(default_factory=list, description="Human-readable reasons behind the outcome, most decisive first.")

def evaluate_quote(rfq: RFQ, quote: Quote, vendor: VendorProfile, policy: ApprovalPolicy) -> Decision:
    """Evaluate one quote end to end against all the scenarios. `cheapest_price` is the lowest unit_price among this RFQs selected quotes, needed for the local preference check, omit if this is the only surviving quote."""
    reasons_to_reject = reject_reasons(quote, vendor)
    if reasons_to_reject:
        return Decision(outcome=Outcome.REJECT, reasons=reasons_to_reject)
    total_price = quote.unit_price * quote.quantity
    escalate_reasons: list[str] = []
    if total_price > policy.auto_approve_limit:
        escalate_reasons.append(f"total {total_price} exceeds auto_approve_limit of {policy.auto_approve_limit}")
    if policy.require_trusted_vendor_for_auto_approve and not vendor.trusted:
        escalate_reasons.append("vendor is not yet trusted (no record)")
    if policy.require_warranty_terms and not quote.warranty_terms:
        escalate_reasons.append("quote is missing warranty_terms")
    if misses_deadline(quote, rfq):
        escalate_reasons.append(f"lead_time_days {quote.lead_time_days} would miss needed_by_date {rfq.needed_by_date}")
    if exceeds_budget(quote, rfq):
        escalate_reasons.append(f"total {total_price} exceeds RFQ budget_ceiling {rfq.budget_ceiling}")
    if escalate_reasons:
        return Decision(outcome=Outcome.ESCALATE, reasons=escalate_reasons)
    return Decision(outcome=Outcome.AUTO_APPROVE, reasons=["within policy on all checks"])

