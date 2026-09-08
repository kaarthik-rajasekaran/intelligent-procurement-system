import uuid
from typing import Optional, Dict, Any
import json
from sqlalchemy.orm import Session
from app.models.entities import Notification, AuditLog, User
from app.services.email_service import email_service

def create_notification(
    db: Session,
    user_id: uuid.UUID,
    notif_type: str,
    title: str,
    message: str,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[uuid.UUID] = None,
    send_email: bool = True
) -> Notification:
    """
    Creates an in-app notification and optionally triggers an email notification.
    """
    notif = Notification(
        user_id=user_id,
        type=notif_type,
        title=title,
        message=message,
        is_read=False,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    if send_email:
        user = db.query(User).filter(User.id == user_id).first()
        if user and user.email:
            email_service.send_email(
                to_email=user.email,
                subject=f"[Procurement Alert] {title}",
                body=f"Hello {user.name},\n\n{message}\n\nPlease check your procurement dashboard for details."
            )

    return notif

def record_audit(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[uuid.UUID] = None,
    actor_id: Optional[uuid.UUID] = None,
    previous_state: Optional[Dict[str, Any]] = None,
    new_state: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> AuditLog:
    """
    Records an immutable audit log entry.
    """
    audit = AuditLog(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        previous_state=json.dumps(previous_state) if previous_state else None,
        new_state=json.dumps(new_state) if new_state else None,
        metadata_json=json.dumps(metadata) if metadata else None
    )
    db.add(audit)
    db.commit()
    return audit
