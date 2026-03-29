from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Chat(Base):
    __tablename__ = "chats"

    chat_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_group_chat: Mapped[bool] = mapped_column(Boolean, default=False)

    users = relationship("UserChat", back_populates="chat")
    messages = relationship("Message", back_populates="chat")
