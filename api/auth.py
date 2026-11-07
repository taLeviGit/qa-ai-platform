import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Demo users (in a real system these would live in a DB with hashed passwords)

USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "agent": {"password": "agent123", "role": "user"},
}

# token -> user info (in memory: tokens are lost when the server restarts)

TOKENS: dict[str,dict] = {}

bearer = HTTPBearer(auto_error=False)

def login(username: str, password: str) -> str | None:
    user = USERS.get(username)
    if user is None or user["password"] != password:
        return None
    
    token  = secrets.token_hex(16)
    TOKENS[token] = {"username": username, "role": user["role"]}
    return token

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer)
    ) -> dict:
    """ 401 - we don't know who you are. """
    if credentials is None or credentials.credentials not in TOKENS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid token")
    return TOKENS[credentials.credentials]


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """403 - we know who you are, but you are not allowed."""
    if user["role"] != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user