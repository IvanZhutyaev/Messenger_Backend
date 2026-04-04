import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from core.websocket_manager import websocket_manager
from api.deps import get_db
from services.message_services import MessageService
from services.chat_services import ChatService
from schemas.message_schemas import MessageCreate, MessageResponse
from models.user_chat_model import UserChat

router = APIRouter(tags=["websocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: Optional[int] = Query(None, description="User ID for authentication")
):
    """
    WebSocket endpoint для real-time обмена сообщениями.
    
    Протокол:
    - Подключение: /ws?user_id=123
    - Отправка сообщения: {"action": "send_message", "chat_id": 1, "text": "Hello"}
    - Редактирование: {"action": "edit_message", "message_id": 1, "text": "New text"}
    - Удаление: {"action": "delete_message", "message_id": 1}
    - Получение истории: {"action": "get_history", "chat_id": 1, "limit": 50}
    
    События от сервера:
    - {"type": "new_message", "chat_id": 1, "message": {...}}
    - {"type": "message_updated", "chat_id": 1, "message": {...}}
    - {"type": "message_deleted", "chat_id": 1, "message_id": 1}
    - {"type": "user_status", "user_id": 123, "username": "...", "status": "online/offline"}
    - {"type": "error", "message": "..."}
    """
    
    if not user_id:
        await websocket.close(code=4001, reason="user_id is required")
        return
    
    # Подключаем пользователя
    connected = await websocket_manager.connect(websocket, user_id)
    if not connected:
        return
    
    db = next(get_db())
    
    try:
        # Отправляем подтверждение подключения
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "message": "Successfully connected to WebSocket"
        })
        
        # Основной цикл обработки сообщений
        while True:
            try:
                # Получаем сообщение от клиента
                data = await websocket.receive_text()
                
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
                    continue
                
                action = payload.get("action")
                
                # === SEND MESSAGE ===
                if action == "send_message":
                    chat_id = payload.get("chat_id")
                    text = payload.get("text", "").strip()
                    
                    if not chat_id or not text:
                        await websocket.send_json({
                            "type": "error",
                            "message": "chat_id and text are required"
                        })
                        continue
                    
                    # Проверяем, что пользователь состоит в чате
                    user_chat = db.query(UserChat).filter(
                        UserChat.user_id == user_id,
                        UserChat.chat_id == chat_id
                    ).first()
                    
                    if not user_chat:
                        await websocket.send_json({
                            "type": "error",
                            "message": "You are not a member of this chat"
                        })
                        continue
                    
                    # Создаем сообщение через сервис
                    message_data = MessageCreate(
                        chat_id=chat_id,
                        sender_id=user_id,
                        message_text=text
                    )
                    
                    try:
                        new_message = MessageService.create_message(db, message_data)
                        
                        # Формируем ответ
                        message_response = {
                            "message_id": new_message.message_id,
                            "chat_id": new_message.chat_id,
                            "sender_id": new_message.sender_id,
                            "message_text": new_message.message_text,
                            "sent_at": new_message.sent_at.isoformat() if new_message.sent_at else None
                        }
                        
                        # Уведомляем отправителя об успехе
                        await websocket.send_json({
                            "type": "message_sent",
                            "message": message_response
                        })
                        
                        # Уведомляем всех в чате (включая отправителя для синхронизации)
                        await websocket_manager.notify_new_message(
                            chat_id, message_response, exclude_user_id=None
                        )
                        
                    except ValueError as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })
                
                # === EDIT MESSAGE ===
                elif action == "edit_message":
                    message_id = payload.get("message_id")
                    new_text = payload.get("text", "").strip()
                    
                    if not message_id or not new_text:
                        await websocket.send_json({
                            "type": "error",
                            "message": "message_id and text are required"
                        })
                        continue
                    
                    # Проверяем, что сообщение принадлежит пользователю
                    from models.message_model import Message
                    message = db.query(Message).filter(Message.message_id == message_id).first()
                    
                    if not message:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Message not found"
                        })
                        continue
                    
                    if message.sender_id != user_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "You can only edit your own messages"
                        })
                        continue
                    
                    # Обновляем сообщение
                    from schemas.message_schemas import MessageUpdate
                    update_data = MessageUpdate(message_text=new_text)
                    
                    try:
                        updated_message = MessageService.update_message(db, message_id, update_data)
                        
                        if updated_message:
                            message_response = {
                                "message_id": updated_message.message_id,
                                "chat_id": updated_message.chat_id,
                                "sender_id": updated_message.sender_id,
                                "message_text": updated_message.message_text,
                                "sent_at": updated_message.sent_at.isoformat() if updated_message.sent_at else None
                            }
                            
                            # Уведомляем всех в чате
                            await websocket_manager.notify_message_updated(
                                updated_message.chat_id, message_response
                            )
                            
                            await websocket.send_json({
                                "type": "message_edited",
                                "message": message_response
                            })
                        
                    except ValueError as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })
                
                # === DELETE MESSAGE ===
                elif action == "delete_message":
                    message_id = payload.get("message_id")
                    
                    if not message_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "message_id is required"
                        })
                        continue
                    
                    # Проверяем сообщение
                    from models.message_model import Message
                    message = db.query(Message).filter(Message.message_id == message_id).first()
                    
                    if not message:
                        await websocket.send_json({
                            "type": "error",
                            "message": "Message not found"
                        })
                        continue
                    
                    if message.sender_id != user_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "You can only delete your own messages"
                        })
                        continue
                    
                    chat_id = message.chat_id
                    
                    try:
                        deleted = MessageService.delete_message(db, message_id)
                        
                        if deleted:
                            # Уведомляем всех в чате
                            await websocket_manager.notify_message_deleted(chat_id, message_id)
                            
                            await websocket.send_json({
                                "type": "message_deleted",
                                "message_id": message_id,
                                "chat_id": chat_id
                            })
                        
                    except ValueError as e:
                        await websocket.send_json({
                            "type": "error",
                            "message": str(e)
                        })
                
                # === GET CHAT HISTORY ===
                elif action == "get_history":
                    chat_id = payload.get("chat_id")
                    limit = payload.get("limit", 50)
                    skip = payload.get("skip", 0)
                    
                    if not chat_id:
                        await websocket.send_json({
                            "type": "error",
                            "message": "chat_id is required"
                        })
                        continue
                    
                    # Проверяем доступ к чату
                    user_chat = db.query(UserChat).filter(
                        UserChat.user_id == user_id,
                        UserChat.chat_id == chat_id
                    ).first()
                    
                    if not user_chat:
                        await websocket.send_json({
                            "type": "error",
                            "message": "You are not a member of this chat"
                        })
                        continue
                    
                    # Получаем сообщения
                    messages = MessageService.get_messages_by_chat(db, chat_id, skip=skip, limit=limit)
                    
                    messages_data = []
                    for msg in messages:
                        messages_data.append({
                            "message_id": msg.message_id,
                            "chat_id": msg.chat_id,
                            "sender_id": msg.sender_id,
                            "message_text": msg.message_text,
                            "sent_at": msg.sent_at.isoformat() if msg.sent_at else None
                        })
                    
                    await websocket.send_json({
                        "type": "chat_history",
                        "chat_id": chat_id,
                        "messages": messages_data,
                        "count": len(messages_data)
                    })
                
                # === PING ===
                elif action == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": payload.get("timestamp")
                    })
                
                # === UNKNOWN ACTION ===
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                # Логируем ошибку но продолжаем работу
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Internal error: {str(e)}"
                    })
                except:
                    break
    
    finally:
        # Отключаем пользователя при разрыве соединения
        await websocket_manager.disconnect(user_id)
        db.close()


@router.get("/ws/info")
def websocket_info():
    """Информация о WebSocket API."""
    return {
        "endpoint": "/ws",
        "authentication": "Query parameter ?user_id=123",
        "protocol": {
            "actions": {
                "send_message": {
                    "description": "Send a message to chat",
                    "payload": {"action": "send_message", "chat_id": 1, "text": "Hello"}
                },
                "edit_message": {
                    "description": "Edit your message",
                    "payload": {"action": "edit_message", "message_id": 1, "text": "New text"}
                },
                "delete_message": {
                    "description": "Delete your message",
                    "payload": {"action": "delete_message", "message_id": 1}
                },
                "get_history": {
                    "description": "Get chat history",
                    "payload": {"action": "get_history", "chat_id": 1, "limit": 50}
                },
                "ping": {
                    "description": "Keep connection alive",
                    "payload": {"action": "ping", "timestamp": 1234567890}
                }
            },
            "events": [
                "connected",
                "message_sent",
                "new_message",
                "message_edited",
                "message_deleted",
                "chat_history",
                "user_status",
                "error",
                "pong"
            ]
        }
    }
