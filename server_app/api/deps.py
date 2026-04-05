from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError
from database.session import LocalSession
from services.auth_services import decode_token
from models.user_model import User


def get_db():
    db = LocalSession()
    try:
        yield db
    finally:
        db.close()


# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/users/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """Get current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception
    
    user = db.query(User).filter(User.user_id == user_id_int).first()
    if user is None:
        raise credentials_exception
    
    return user


def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
    """Get current user if token is valid, otherwise return None."""
    if not token:
        return None
    
    payload = decode_token(token)
    if payload is None:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        return None
    
    user = db.query(User).filter(User.user_id == user_id_int).first()
    return user
