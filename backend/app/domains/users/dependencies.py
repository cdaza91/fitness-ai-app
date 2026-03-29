import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.core.db import get_db
from app.core.config import settings
from app.domains.users.models import User

# Configure logger
logger = logging.getLogger(__name__)

# Correct the tokenUrl to the actual login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency function to validate JWT and return the current user.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token expirado o inválido. Inicia sesión de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("Token payload missing 'sub' field")
            raise credentials_exception
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        logger.warning(f"User with email '{email}' not found in database")
        raise credentials_exception

    return user
