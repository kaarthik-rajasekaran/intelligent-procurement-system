import uuid
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.entities import (
    PurchaseRequest, PurchaseRequestReview, User, UserRole, PRStatus, Department
)

# Valid state transitions map
VALID_TRANSITIONS = {
    PRStatus.DRAFT.value: [PRStatus.SUBMITTED.value],
    PRStatus.SUBMITTED.value: [PRStatus.UNDER_REVIEW.value, PRStatus.APPROVED_FOR_RFQ.value, PRStatus.REVISION_REQUIRED.value, PRStatus.REJECTED.value],
    PRStatus.UNDER_REVIEW.value: [PRStatus.REVISION_REQUIRED.value, PRStatus.APPROVED_FOR_RFQ.value, PRStatus.REJECTED.value],
    PRStatus.REVISION_REQUIRED.value: [PRStatus.SUBMITTED.value],
    PRStatus.APPROVED_FOR_RFQ.value: [PRStatus.RFQ_ISSUED.value],
    PRStatus.RFQ_ISSUED.value: [PRStatus.QUOTATION_RECEIVED.value],
    PRStatus.QUOTATION_RECEIVED.value: [PRStatus.VENDOR_SELECTION_PENDING.value],
    PRStatus.VENDOR_SELECTION_PENDING.value: [PRStatus.FINAL_APPROVAL_PENDING.value],
    PRStatus.FINAL_APPROVAL_PENDING.value: [PRStatus.APPROVED.value, PRStatus.REJECTED.value],
    PRStatus.APPROVED.value: [PRStatus.PO_GENERATED.value],
    PRStatus.PO_GENERATED.value: [PRStatus.COMPLETED.value],
    PRStatus.COMPLETED.value: [],
    PRStatus.REJECTED.value: []
}

def validate_supervisor_authority(db: Session, supervisor: User, pr: PurchaseRequest):
    """
    Validates that the supervisor is authorized for the PR's department.
    """
    if supervisor.role == UserRole.ADMIN.value:
        return True

    if supervisor.role != UserRole.SUPERVISOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not have supervisor authority."
        )

    # Check if supervisor belongs to or supervises PR department
    dept = db.query(Department).filter(Department.id == pr.department_id).first()
    is_supervisor = False
    if supervisor.department_id == pr.department_id:
        is_supervisor = True
    elif dept and any(s.id == supervisor.id for s in dept.supervisors):
        is_supervisor = True

    if not is_supervisor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Supervisor {supervisor.name} is not assigned to review department {dept.name if dept else pr.department_id}."
        )
    return True

def transition_pr_status(
    db: Session,
    pr: PurchaseRequest,
    target_status: PRStatus,
    actor: Optional[User] = None,
    decision_type: Optional[str] = None,
    reason: Optional[str] = None
) -> PurchaseRequest:
    """
    Validates and executes a PR workflow state transition.
    """
    current_status = pr.status
    allowed_next = VALID_TRANSITIONS.get(current_status, [])

    if target_status.value not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid workflow transition from '{current_status}' to '{target_status.value}'. Allowed: {allowed_next}"
        )

    # Business rule: Revision required and Rejection must have a mandatory reason
    if target_status in [PRStatus.REVISION_REQUIRED, PRStatus.REJECTED] and (not reason or len(reason.strip()) < 3):
        action_word = "Rejecting" if target_status == PRStatus.REJECTED else "Returning"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{action_word} a PR requires a mandatory, substantive reason."
        )

    pr.status = target_status.value

    # Record review if decision is made by supervisor
    if actor and decision_type:
        review = PurchaseRequestReview(
            purchase_request_id=pr.id,
            supervisor_id=actor.id,
            decision=decision_type,
            reason=reason
        )
        db.add(review)

    db.commit()
    db.refresh(pr)
    return pr
