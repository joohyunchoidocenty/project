"""
데이터베이스 연결 및 세션 관리
Dcty-BotStudio-serv 패턴 참고
"""
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase
from src.configs.webconfig import get_settings
from typing import AsyncGenerator


class Base(DeclarativeBase):
    """모든 모델의 베이스 클래스"""
    pass


# ========== Entity 임포트 (테이블 등록을 위해 필수) ==========
# 새로운 Entity를 만들면 여기에 임포트 추가
from src.entity.accounttest_entity import AccountTest  # noqa: F401
from src.entity.resume_entities import Resume, ResumeSearchHistory  # noqa: F401


class DatabaseManager:
    """
    데이터베이스 연결 관리자
    Dcty-BotStudio-serv의 DBResourceManager 패턴
    """

    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.async_session_maker: async_sessionmaker[AsyncSession] | None = None

    async def init(self):
        """데이터베이스 엔진 및 세션 팩토리 초기화"""
        settings = get_settings()

        # 비동기 엔진 생성
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,  # SQL 로깅
            pool_pre_ping=True,  # 연결 헬스 체크
            pool_size=10,  # 연결 풀 크기
            max_overflow=20,  # 최대 추가 연결
        )

        # 세션 팩토리 생성
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        print(f"✅ Database engine created: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")

    async def create_tables(self):
        """테이블 생성 (개발 환경에서만 사용, 프로덕션은 Alembic 사용)"""
        if self.engine is None:
            raise RuntimeError("Database engine not initialized. Call init() first.")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created")

    async def close(self):
        """데이터베이스 연결 종료"""
        if self.engine:
            await self.engine.dispose()
            print("✅ Database engine disposed")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        비동기 세션 제너레이터 (FastAPI Depends에서 사용)

        Usage:
            @router.get("/items")
            async def get_items(db: AsyncSession = Depends(get_db)):
                ...
        """
        if self.async_session_maker is None:
            raise RuntimeError("Session maker not initialized. Call init() first.")

        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# 전역 데이터베이스 매니저 인스턴스
db_manager = DatabaseManager()


# FastAPI Depends를 위한 헬퍼 함수
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 의존성 주입용 DB 세션 제공

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Item))
            return result.scalars().all()
    """
    async for session in db_manager.get_session():
        yield session
