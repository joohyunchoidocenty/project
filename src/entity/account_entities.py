"""
계정 데이터베이스 모델 (간단한 테스트용)
"""
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from src.database import Base
from datetime import datetime


class Account(Base):
    """
    계정 테이블 (테스트용)
    """
    __tablename__ = "accounts"

    # Primary Key
    id = Column(String(36), primary_key=True, index=True, comment="UUID")

    # 계정 정보
    username = Column(String(50), nullable=False, unique=True, index=True, comment="사용자명")
    email = Column(String(255), nullable=False, unique=True, index=True, comment="이메일")
    full_name = Column(String(100), comment="전체 이름")

    # 타임스탬프
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="생성 시간"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="수정 시간"
    )

    def to_dict(self) -> dict:
        """Entity를 딕셔너리로 변환"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, username={self.username}, email={self.email})>"
