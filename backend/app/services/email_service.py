import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("email_service")
logging.basicConfig(level=logging.INFO)

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str, attachment_path: Optional[str] = None) -> bool:
        """
        Sends email via configured provider.
        For local hackathon execution, logs email delivery cleanly without network dependency.
        Guaranteed not to raise an exception or fail core transactions.
        """
        try:
            if settings.EMAIL_PROVIDER == "logger":
                logger.info("=" * 60)
                logger.info(f"[MOCK EMAIL DISPATCH]")
                logger.info(f"TO: {to_email}")
                logger.info(f"SUBJECT: {subject}")
                logger.info(f"BODY:\n{body}")
                if attachment_path:
                    logger.info(f"ATTACHMENT: {attachment_path}")
                logger.info("=" * 60)
                return True
            else:
                logger.warning(f"Unsupported email provider {settings.EMAIL_PROVIDER}, falling back to logger.")
                logger.info(f"[EMAIL TO {to_email}]: {subject}")
                return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

email_service = EmailService()
