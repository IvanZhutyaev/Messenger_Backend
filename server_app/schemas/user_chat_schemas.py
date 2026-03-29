from pydantic import BaseModel, ConfigDict


class UserChatBase(BaseModel):
    user_id: int
    chat_id: int


class UserChatCreate(UserChatBase):
    pass


class UserChatResponse(UserChatBase):
    model_config = ConfigDict(from_attributes=True)
