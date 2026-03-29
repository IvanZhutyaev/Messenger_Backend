from sqlalchemy import ForeignKey, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from database import Base


class Message(Base):
    __tablename__ = "messages"

    message_id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True)

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))

    message_text: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow)

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages")
