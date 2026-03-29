from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserBase(BaseModel):
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    phone_number: Optional[str] = None
    is_bot: Optional[bool] = None


class UserResponse(UserBase):
    user_id: int
    model_config = ConfigDict(from_attributes=True)
