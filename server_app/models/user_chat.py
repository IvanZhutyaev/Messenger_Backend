from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class UserChat(Base):
    __tablename__ = "user_chats"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.chat_id"), primary_key=True)

    user = relationship("User", back_populates="chats")
    chat = relationship("Chat", back_populates="users")
