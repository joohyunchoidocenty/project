"""
애플리케이션 설정 관리
Dcty-BotStudio-serv 패턴 참고
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path


class Settings(BaseSettings):
    """애플리케이션 설정 (Pydantic Settings)"""

    # Application
    app_name: str = "AI Resume Backend"
    app_env: str = "local"
    debug: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # PostgreSQL
    postgres_user: str = "hansol"
    postgres_password: str = "hansol1234"
    postgres_db: str = "resume_db"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Database URL (자동 생성)
    database_url: str = ""

    # OpenAI
    openai_api_key: str | None = None
    
    # Upstage API
    upstage_api_key: str | None = None

    # File Upload
    upload_dir: str = "./uploads"
    max_upload_size: int = 10485760  # 10MB

    # Security
    api_key: str = "dev-api-key"
    secret_key: str = "your-secret-key"

    model_config = SettingsConfigDict(
        env_file=".env.local",
        case_sensitive=False,
        extra="ignore"
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # DATABASE_URL이 설정되지 않았으면 자동 생성
        if not self.database_url:
            self.database_url = (
                f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )

    @property
    def sync_database_url(self) -> str:
        """동기 DB URL (Alembic용)"""
        return self.database_url.replace("+asyncpg", "")

    def ensure_upload_dir(self):
        """업로드 디렉토리 생성"""
        Path(self.upload_dir).mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """
    싱글톤 패턴으로 설정 인스턴스 반환
    Dcty-BotStudio-serv의 app_settings() 패턴
    """
    settings = Settings()
    settings.ensure_upload_dir()
    return settings
