from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for PROJECT ANCHOR."""

    model_config = SettingsConfigDict(
        env_prefix="ANCHOR_",
        env_file=".env",
        extra="ignore",
    )

    APP_NAME: str = "PROJECT ANCHOR"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Base Paths
    BASE_DIR: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    @property
    def DATA_DIR(self) -> Path:
        return self.BASE_DIR / "data"

    @property
    def PDFS_DIR(self) -> Path:
        return self.DATA_DIR / "pdfs"

    @property
    def SCHEMAS_DIR(self) -> Path:
        return self.DATA_DIR / "schemas"

    @property
    def LANCEDB_DIR(self) -> Path:
        return self.DATA_DIR / "lancedb"

    @property
    def TANTIVY_DIR(self) -> Path:
        return self.DATA_DIR / "tantivy"

    @property
    def SQLITE_PATH(self) -> Path:
        return self.DATA_DIR / "sqlite" / "anchor.db"

    @property
    def MODELS_DIR(self) -> Path:
        return self.BASE_DIR / "models"

    @property
    def BGE_M3_PATH(self) -> Path:
        return self.MODELS_DIR / "bge-m3"

    @property
    def BGE_RERANKER_PATH(self) -> Path:
        return self.MODELS_DIR / "bge-reranker-large"

    @property
    def DEBERTA_NLI_PATH(self) -> Path:
        return self.MODELS_DIR / "deberta-v3-nli"

    # Hardware & Runtime
    OPENVINO_DEVICE: str = "AUTO"
    MAX_RAM_GB: float = 12.5

    # Retrieval Hyperparameters
    RRF_K: int = 60
    TOP_K_RETRIEVAL: int = 10
    TOP_K_RERANK: int = 3
    TEMPORAL_MULTIPLIER_2024_PLUS: float = 1.5

    # Verification & Quality Thresholds
    NLI_ENTAILMENT_THRESHOLD: float = 0.85
    NLI_CONTRADICTION_THRESHOLD: float = 0.08
    CORRECTIVE_GATE_SIMILARITY_MIN: float = 0.65

    # Ollama Endpoints
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b-instruct-q4_K_M"

    # Security & API Policies (ENH-016, ENH-018, ENH-020)
    RATE_LIMIT_RPM: int = 120  # Max requests per minute per IP
    AUTH_PIN: Optional[str] = None  # Session PIN if authentication enabled
    LOG_JSON_LINES: bool = True  # Output structured JSON lines to logs


    def ensure_directories(self) -> None:
        """Ensure all runtime directories exist."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.PDFS_DIR.mkdir(parents=True, exist_ok=True)
        self.SCHEMAS_DIR.mkdir(parents=True, exist_ok=True)
        self.LANCEDB_DIR.mkdir(parents=True, exist_ok=True)
        self.TANTIVY_DIR.mkdir(parents=True, exist_ok=True)
        self.SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.MODELS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
