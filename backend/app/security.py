import bcrypt
from datetime import datetime, timedelta
from jose import jwt

# En producción, esto debe ir en tu archivo .env
SECRET_KEY = "tu_super_secreto_para_jwt_cambialo_despues"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # El token durará 7 días

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt requiere que los strings se conviertan a bytes (encode)
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt