from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from api.deps import get_db
from core.websocket_manager import websocket_manager

router = APIRouter(prefix="/api/v1/chats", tags=["chat_members"])

# ============ CHAT MEMBERS ENDPOINTS ============

@router.post("/{chat_id}/members/{user_id}", status_code=status.HTTP_201_CREATED)
def add_member_to_chat(chat_id: int, user_id: int, db: Session = Depends(get_db)):
    """Добавить пользователя в чат."""
    from models.user_chat_model import UserChat
    from models.user_model import User
    from models.chat_model import Chat
    
    # Проверяем существование чата
    chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    
    # Проверяем существование пользователя
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    # Проверяем, не состоит ли уже пользователь в чате
    existing = db.query(UserChat).filter(
        UserChat.chat_id == chat_id,
        UserChat.user_id == user_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User is already a member of this chat")
    
    # Добавляем пользователя в чат
    user_chat = UserChat(chat_id=chat_id, user_id=user_id)
    db.add(user_chat)
    
    try:
        db.commit()
        
        # Уведомляем WebSocket о новом участнике
        try:
            websocket_manager.add_user_to_chat(user_id, chat_id)
        except Exception:
            pass
        
        return {
            "message": "User added to chat successfully",
            "chat_id": chat_id,
            "user_id": user_id
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{chat_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member_from_chat(chat_id: int, user_id: int, db: Session = Depends(get_db)):
    """Удалить пользователя из чата."""
    from models.user_chat_model import UserChat
    from models.chat_model import Chat
    
    # Проверяем существование чата
    chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    
    # Находим связь пользователя с чатом
    user_chat = db.query(UserChat).filter(
        UserChat.chat_id == chat_id,
        UserChat.user_id == user_id
    ).first()
    
    if not user_chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User is not a member of this chat")
    
    db.delete(user_chat)
    
    try:
        db.commit()
        
        # Уведомляем WebSocket об удалении участника
        try:
            websocket_manager.remove_user_from_chat(user_id, chat_id)
        except Exception:
            pass
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{chat_id}/members")
def get_chat_members(chat_id: int, db: Session = Depends(get_db)):
    """Получить список участников чата."""
    from models.user_chat_model import UserChat
    from models.user_model import User
    from models.chat_model import Chat
    
    # Проверяем существование чата
    chat = db.query(Chat).filter(Chat.chat_id == chat_id).first()
    if not chat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chat not found")
    
    # Получаем участников
    members = db.query(User).join(UserChat).filter(UserChat.chat_id == chat_id).all()
    
    return [
        {
            "user_id": member.user_id,
            "login": member.login,
            "first_name": member.first_name,
            "last_name": member.last_name,
            "username": member.username,
            "avatar_url": member.avatar_url
        }
        for member in members
    ]
