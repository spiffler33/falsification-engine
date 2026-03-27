# config.py — Application settings and path constants.
# Depends on: .env file for API keys
# Depended on by: all backend modules that need paths or settings
from pathlib import Path
from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent.parent
THEORIES_DIR = BASE_DIR / "theories"
DATA_DIR = BASE_DIR / "data"
MOCK_DATA_DIR = BASE_DIR / "mock_data"
DB_PATH = DATA_DIR / "falsification.db"


class Settings(BaseSettings):
    fred_api_key: str = ""
    anthropic_api_key: str = ""
    database_url: str = f"sqlite:///{DB_PATH}"

    model_config = {"env_file": str(BASE_DIR / ".env"), "env_file_encoding": "utf-8"}


settings = Settings()
