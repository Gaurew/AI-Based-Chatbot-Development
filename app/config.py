import os
from pydantic import BaseModel


class Settings(BaseModel):
    gemini_api_key: str | None = os.getenv("GEMINI_API_KEY")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
    chroma_dir: str = os.getenv("CHROMA_PERSIST_DIR", ".chroma")
    user_agent: str = (
        os.getenv(
            "SCRAPER_USER_AGENT",
            "JobYaariScraper/0.1 (local; +https://jobyaari.com)"
        )
    )
    max_concurrency: int = int(os.getenv("SCRAPER_MAX_CONCURRENCY", "4"))
    min_delay_ms: int = int(os.getenv("SCRAPER_MIN_DELAY_MS", "500"))
    max_delay_ms: int = int(os.getenv("SCRAPER_MAX_DELAY_MS", "1500"))


def get_settings() -> Settings:
    return Settings()


