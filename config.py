from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List

class Settings(BaseSettings):
    GOOGLE_API_KEY: str = Field(..., descrription="google api key")
    PLANNER_MODEL: str = Field(default="gemini-2.5-pro", descrription="planner model")
    VERIFIER_MODEL: str = Field(default="gemini-3-flash-preview", descrription="verifier model")
    RESPONDER_MODEL: str = Field(default="gemini-3-flash-preview", descrription="responder model")
    EMBEDDING_MODEL: str = Field(default="gemini-embedding-001", descrription="embedding model")
    MAX_RETRIES: int = Field(default=3, descrription="max retries")
    DATA_DIR: str = Field(default="./data", descrription="data directory")
    DOCS_DIR: str = Field(default="./docs", descrription="docs directory")

    DATA_WINDOW_START: str = Field(default="2024-08-01", description="earliest date in the dataset")
    DATA_WINDOW_END: str = Field(default="2025-12-31", description="latest date in the dataset")

    ALLOWED_QUARTERS: List[str] = Field(
        default=["2024Q4", "2025Q1", "2025Q2", "2025Q3", "2025Q4"],
        description="valid quarters for fact_ln_metrics",
    )

    HOST: str = Field(default="0.0.0.0", description="host for the api")
    PORT: int = Field(default=8000, description="port for the api")

    model_config = SettingsConfigDict(env_file=('.env.prod', '.env'), env_file_encoding='utf-8',  extra='ignore')

settings = Settings()