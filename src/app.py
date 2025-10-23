"""
FastAPI 메인 애플리케이션
Dcty-BotStudio-serv 구조 참고
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.configs.webconfig import get_settings
from src.database import db_manager
import logging


# 로거 설정
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    애플리케이션 생명주기 관리
    Dcty-BotStudio-serv의 lifespan 패턴
    """
    settings = get_settings()

    # ========== Startup ==========
    logger.info("🚀 애플리케이션 시작 중...")

    # 1. 데이터베이스 초기화
    try:
        await db_manager.init()
        logger.info("✅ 데이터베이스 연결 성공")

        # 개발 환경에서만 테이블 자동 생성 (프로덕션은 Alembic 사용)
        if settings.app_env == "local" and settings.debug:
            await db_manager.create_tables()
            logger.info("✅ 데이터베이스 테이블 생성 완료")

    except Exception as e:
        logger.error(f"❌ 데이터베이스 초기화 실패: {e}")
        raise

    # 2. 업로드 디렉토리 확인
    settings.ensure_upload_dir()
    logger.info(f"✅ 업로드 디렉토리: {settings.upload_dir}")

    logger.info(f"✅ {settings.app_name} 준비 완료!")
    logger.info(f"   Environment: {settings.app_env}")
    logger.info(f"   Debug: {settings.debug}")
    logger.info(f"   Database: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")

    yield

    # ========== Shutdown ==========
    logger.info("⛔ 애플리케이션 종료 중...")
    await db_manager.close()
    logger.info("✅ 데이터베이스 연결 종료")


# FastAPI 앱 생성
settings = get_settings()
app = FastAPI(
    title="AI Resume Management API",
    description="이력서 업로드, 파싱, AI 분석 백엔드",
    version="1.0.0",
    lifespan=lifespan,
    debug=settings.debug,
)

# ========== 미들웨어 설정 ==========

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 예외 핸들러 ==========

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """전역 예외 처리"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "data": None,
            "meta": {
                "code": 500,
                "errors": [{
                    "code": 500,
                    "msg": "Internal server error",
                    "desc": str(exc) if settings.debug else None
                }]
            }
        }
    )


# ========== 라우터 등록 ==========

from src.controllers.accounttest_router import router as accounttest_router
from src.controllers.pdf_parser_router import router as pdf_parser_router

app.include_router(accounttest_router, prefix="/api/accounttest", tags=["AccountTest"])
app.include_router(pdf_parser_router, prefix="/api/pdf", tags=["PDF Parser - Upstage API"])


# ========== 기본 엔드포인트 ==========

@app.get("/")
def root():
    """루트 엔드포인트"""
    return {
        "status": "ok",
        "message": f"{settings.app_name} is running",
        "version": "1.0.0",
        "environment": settings.app_env
    }


@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "database": "connected" if db_manager.engine else "not connected"
    }


@app.get("/db-test")
async def test_database():
    """데이터베이스 연결 테스트"""
    try:
        from sqlalchemy import text
        async with db_manager.async_session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            result.scalar()
        return {
            "status": "ok",
            "message": "Database connection successful"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
