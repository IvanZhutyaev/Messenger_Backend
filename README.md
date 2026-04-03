# Messenger_Backend

Backend for android-messenger. FastAPI + PostgreSQL.

## Requirements

- Python 3.11+
- Docker Desktop

## Запуск

```sh
docker compose up -d --build
```

API будет доступен на http://localhost:8000/docs

## API

- `POST /api/v1/users/register` - Регистрация
- `POST /api/v1/users/login` - Вход
- `GET /api/v1/users/{id}` - Профиль пользователя
- `POST /api/v1/chats` - Создать чат
- `GET /api/v1/chats/{id}/messages` - Сообщения чата
- `POST /api/v1/chats/{id}/messages` - Отправить сообщение
