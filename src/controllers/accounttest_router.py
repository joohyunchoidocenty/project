"""
AccountTest Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.services.accounttest_service import AccountTestService
from src.domain.accounttest_dto import AccountTestCreate, AccountTestResponse

router = APIRouter()
service = AccountTestService()


@router.post("/", response_model=AccountTestResponse)
async def create_account(
    data: AccountTestCreate,
    db: AsyncSession = Depends(get_db)
):
    """계정 생성"""
    account = await service.create_account(db, data)
    return account


@router.get("/", response_model=list[AccountTestResponse])
async def get_accounts(db: AsyncSession = Depends(get_db)):
    """전체 계정 조회"""
    accounts = await service.get_all_accounts(db)
    return accounts
