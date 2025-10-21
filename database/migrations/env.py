"""
Alembic 환경 설정
Dcty-BotStudio-serv의 마이그레이션 패턴 참고
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

# 설정 및 모델 import
from src.configs.webconfig import get_settings
from src.database import Base
from src.entity.resume_entities import Resume, ResumeSearchHistory  # 모든 모델 import

# Alembic Config 객체
config = context.config

# 로깅 설정
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData 객체 (마이그레이션 대상)
target_metadata = Base.metadata


def get_url():
    """환경 변수에서 DB URL 가져오기"""
    settings = get_settings()
    return settings.sync_database_url  # 동기 URL 사용 (psycopg2)


def run_migrations_offline() -> None:
    """
    오프라인 모드 마이그레이션 (SQL 파일 생성)

    Usage:
        alembic upgrade head --sql > migration.sql
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    온라인 모드 마이그레이션 (DB에 직접 적용)

    Usage:
        alembic upgrade head
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


# 모드 선택
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
