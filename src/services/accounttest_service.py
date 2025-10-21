"""
AccountTest Service
"""
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.entity.accounttest_entity import AccountTest
from src.domain.accounttest_dto import AccountTestCreate


class AccountTestService:
    """AccountTest 비즈니스 로직"""

    async def create_account(self, db: AsyncSession, data: AccountTestCreate) -> AccountTest:
        """계정 생성"""
        account = AccountTest(
            id=str(uuid.uuid4()),
            username=data.username
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return account

    async def get_all_accounts(self, db: AsyncSession) -> list[AccountTest]:
        """전체 계정 조회"""
        result = await db.execute(select(AccountTest))
        return result.scalars().all()
