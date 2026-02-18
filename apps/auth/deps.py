from fastapi import Depends, HTTPException, status, Request
from sqlmodel import Session
from database import get_session
from apps.auth.models import User

def get_current_user(request: Request, session: Session = Depends(get_session)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    
    user = session.get(User, user_id)
    return user

def require_user(user: User | None = Depends(get_current_user)) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/auth/login"}
        )
    return user
