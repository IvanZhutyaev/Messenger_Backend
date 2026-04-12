from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.user_model import User
from schemas.user_schemas import UserRegister, UserLogin
from typing import Optional


class UserService:
    @staticmethod
    def register_user(db: Session, user_data: UserRegister) -> User:
        existing_user = db.query(User).filter(
            User.login == user_data.login).first()
        if existing_user:
            raise ValueError(
                f"User with login '{user_data.login}' already exists")

        user = User(
            login=user_data.login,
            password=user_data.password,
            first_name=user_data.first_name,
            last_name=user_data.last_name
        )

        db.add(user)
        try:
            db.commit()
            db.refresh(user)
            return user
        except IntegrityError:
            db.rollback()
            raise ValueError("Error creating user")

    @staticmethod
    def login_user(db: Session, login_data: UserLogin) -> User:
        user = db.query(User).filter(User.login == login_data.login).first()
        if not user:
            raise ValueError("Invalid login or password")
        return user

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.user_id == user_id).first()

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 100) -> list[User]:
        return db.query(User).offset(skip).limit(limit).all()
