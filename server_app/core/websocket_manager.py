import json
import asyncio
from typing import Dict, List, Optional
from fastapi import WebSocket
from models.user_chat_model import UserChat
from sqlalchemy.orm import Session
from database.session import LocalSession


class WebSocketManager:
    """Менеджер WebSocket соединений для real-time чата."""
    
    def __init__(self):
        # user_id -> WebSocket
        self.active_connections: Dict[int, WebSocket] = {}
        # chat_id -> List[user_id]
        self.chat_subscribers: Dict[int, List[int]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int) -> bool:
        """
        Подключение пользователя к WebSocket.
        Возвращает True если подключение успешно.
        """
        # Проверяем существование пользователя
        db = LocalSession()
        try:
            from models.user_model import User
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                await websocket.close(code=4001, reason="User not found")
                return False
            
            await websocket.accept()
            self.active_connections[user_id] = websocket
            
            # Загружаем чаты пользователя
            user_chats = db.query(UserChat).filter(UserChat.user_id == user_id).all()
            for user_chat in user_chats:
                chat_id = user_chat.chat_id
                if chat_id not in self.chat_subscribers:
                    self.chat_subscribers[chat_id] = []
                if user_id not in self.chat_subscribers[chat_id]:
                    self.chat_subscribers[chat_id].append(user_id)
            
            # Уведомляем о подключении
            await self.broadcast_user_status(user_id, "online", db)
            return True
            
        finally:
            db.close()
    
    async def disconnect(self, user_id: int):
        """Отключение пользователя."""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        
        # Удаляем из всех чатов
        for chat_id, subscribers in self.chat_subscribers.items():
            if user_id in subscribers:
                subscribers.remove(user_id)
        
        # Уведомляем об отключении
        db = LocalSession()
        try:
            await self.broadcast_user_status(user_id, "offline", db)
        finally:
            db.close()
    
    async def send_personal_message(self, message: dict, user_id: int):
        """Отправка личного сообщения пользователю."""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)
    
    async def broadcast_to_chat(self, message: dict, chat_id: int, exclude_user_id: Optional[int] = None):
        """Рассылка сообщения всем участникам чата."""
        if chat_id not in self.chat_subscribers:
            return
        
        subscribers = self.chat_subscribers[chat_id].copy()
        for user_id in subscribers:
            if user_id != exclude_user_id and user_id in self.active_connections:
                try:
                    await self.active_connections[user_id].send_json(message)
                except Exception:
                    # Если отправка не удалась, отключаем пользователя
                    await self.disconnect(user_id)
    
    async def broadcast_user_status(self, user_id: int, status: str, db: Session):
        """Уведомление о статусе пользователя (online/offline)."""
        from models.user_model import User
        
        user = db.query(User).filter(User.user_id == user_id).first()
        if not user:
            return
        
        # Получаем чаты пользователя
        user_chats = db.query(UserChat).filter(UserChat.user_id == user_id).all()
        
        message = {
            "type": "user_status",
            "user_id": user_id,
            "username": user.username or user.first_name,
            "status": status,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        # Рассылаем в чаты где состоит пользователь
        for user_chat in user_chats:
            await self.broadcast_to_chat(message, user_chat.chat_id, exclude_user_id=user_id)
    
    async def notify_new_message(self, chat_id: int, message_data: dict, exclude_user_id: Optional[int] = None):
        """Уведомление о новом сообщении в чате."""
        notification = {
            "type": "new_message",
            "chat_id": chat_id,
            "message": message_data
        }
        await self.broadcast_to_chat(notification, chat_id, exclude_user_id)
    
    async def notify_message_updated(self, chat_id: int, message_data: dict):
        """Уведомление об обновлении сообщения."""
        notification = {
            "type": "message_updated",
            "chat_id": chat_id,
            "message": message_data
        }
        await self.broadcast_to_chat(notification, chat_id)
    
    async def notify_message_deleted(self, chat_id: int, message_id: int):
        """Уведомление об удалении сообщения."""
        notification = {
            "type": "message_deleted",
            "chat_id": chat_id,
            "message_id": message_id
        }
        await self.broadcast_to_chat(notification, chat_id)
    
    def add_user_to_chat(self, user_id: int, chat_id: int):
        """Добавление пользователя в чат (при создании чата или добавлении участника)."""
        if chat_id not in self.chat_subscribers:
            self.chat_subscribers[chat_id] = []
        if user_id not in self.chat_subscribers[chat_id]:
            self.chat_subscribers[chat_id].append(user_id)
    
    def remove_user_from_chat(self, user_id: int, chat_id: int):
        """Удаление пользователя из чата."""
        if chat_id in self.chat_subscribers and user_id in self.chat_subscribers[chat_id]:
            self.chat_subscribers[chat_id].remove(user_id)
    
    def get_user_chat_ids(self, user_id: int) -> List[int]:
        """Получение списка чатов пользователя."""
        chat_ids = []
        for chat_id, subscribers in self.chat_subscribers.items():
            if user_id in subscribers:
                chat_ids.append(chat_id)
        return chat_ids


# Singleton instance
websocket_manager = WebSocketManager()
