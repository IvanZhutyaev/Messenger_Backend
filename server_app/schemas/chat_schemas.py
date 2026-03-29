from pydantic import BaseModel, ConfigDict
from typing import Optional


class ChatBase(BaseModel):
    chat_name: Optional[str] = None
    is_group_chat: bool = False


class ChatCreate(ChatBase):
    pass


class ChatUpdate(BaseModel):
    chat_name: Optional[str] = None
    is_group_chat: Optional[bool] = None


class ChatResponse(ChatBase):
    chat_id: int
    model_config = ConfigDict(from_attributes=True)
