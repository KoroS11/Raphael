from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from db.connection import get_db
from db.models import User
from api.auth import verify_password, hash_password, create_token, require_role
import uuid

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class CreateUserRequest(BaseModel):
    username:     str
    password:     str
    display_name: str
    role:         str
    organization: str = ""

@router.post("/auth/login")
async def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(str(user.id))
    return {
        "status": "success",
        "data": {
            "token":        token,
            "user_id":      str(user.id),
            "display_name": user.display_name,
            "role":         user.role
        },
        "meta": {},
        "errors": []
    }

@router.get("/")
async def list_users(
    db: Session = Depends(get_db),
    _user = Depends(require_role("admin"))
):
    users = db.query(User).all()
    data = [
        {"id": str(u.id), "username": u.username,
         "role": u.role, "display_name": u.display_name}
        for u in users
    ]
    return {
        "status": "success",
