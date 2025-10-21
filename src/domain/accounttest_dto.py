"""
AccountTest DTO
"""
from pydantic import BaseModel


class AccountTestCreate(BaseModel):
    username: str


class AccountTestResponse(BaseModel):
    id: str
    username: str

    class Config:
        from_attributes = True
