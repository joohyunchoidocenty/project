"""
테스트용 계정 엔티티
"""
from sqlalchemy import Column, String
from src.database import Base


class AccountTest(Base):
    """테스트용 계정 테이블"""
    __tablename__ = "accounttest"

    id = Column(String(36), primary_key=True, comment="ID")
    username = Column(String(50), nullable=False, comment="사용자명")
