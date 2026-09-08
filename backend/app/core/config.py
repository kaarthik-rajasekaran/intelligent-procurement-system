import os
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_BASE = BASE_DIR / "storage"

class Settings(BaseSettings):
    PROJECT_NAME: str = "Intelligent Procurement System"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "procurement-system-super-secure-jwt-secret-key-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database: SQLite fallback for instant zero-dependency local run, or PostgreSQL
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'procurement.db'}")

    # Storage paths
    STORAGE_DIR: Path = STORAGE_BASE
    PO_STORAGE_DIR: Path = STORAGE_BASE / "purchase_orders"
    QUOTATION_STORAGE_DIR: Path = STORAGE_BASE / "quotations"
    KNOWLEDGE_STORAGE_DIR: Path = STORAGE_BASE / "knowledge_documents"

    # Business rule thresholds
    DUPLICATE_QUANTITY_THRESHOLD_PERCENT: float = 20.0

    # Vendor recommendation weights (sum to 1.0)
    WEIGHT_QUALITY: float = 0.25
    WEIGHT_DELIVERY_RELIABILITY: float = 0.25
    WEIGHT_ITEM_SPECIFIC: float = 0.20
    WEIGHT_PRICE_COMPETITIVENESS: float = 0.15
    WEIGHT_HISTORICAL_FULFILLMENT: float = 0.10
    WEIGHT_RESPONSIVENESS: float = 0.05

    # Quotation evaluation weights V1 (legacy — sum to 1.0, used by evaluate_quotations)
    QUOTE_WEIGHT_PRICE: float = 0.40
    QUOTE_WEIGHT_DELIVERY: float = 0.20
    QUOTE_WEIGHT_RELIABILITY: float = 0.20
    QUOTE_WEIGHT_QUALITY: float = 0.20

    # Quotation evaluation weights V2 (multi-vendor RFQ — sum to 1.0)
    # Incorporates expected_delivery_date as a distinct factor from lead_time_days
    QUOTE_V2_WEIGHT_PRICE: float = 0.35
    QUOTE_V2_WEIGHT_DELIVERY_DATE: float = 0.20   # How soon the vendor commits to deliver
    QUOTE_V2_WEIGHT_LEAD_TIME: float = 0.15       # Lead time from order to delivery in days
    QUOTE_V2_WEIGHT_RELIABILITY: float = 0.15     # Vendor's historical delivery reliability
    QUOTE_V2_WEIGHT_QUALITY: float = 0.15         # Vendor's historical quality score

    # AI & RAG Configuration
    AI_ENABLED: bool = True
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")  # "mock_local", "gemini", "openai", "anthropic"
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "AIzaSyDj56w6Heffi8RTGaYE9JJF0vnj01xYCus")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")

    # Vendor recommendation cache (in-memory TTL per item+quantity bracket)
    VENDOR_REC_CACHE_TTL_MINUTES: int = 15

    # Email provider: logger for local zero-dependency execution
    EMAIL_PROVIDER: str = "logger"

    class Config:
        env_file = ".env"
        extra = "allow"

settings = Settings()

# Ensure storage directories exist
settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.PO_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.QUOTATION_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
settings.KNOWLEDGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
