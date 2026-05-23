from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db
from ..schemas import LoginRequest, LoginOut, UserOut
from ..security import create_access_token


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = services.authenticate_user(db, payload)
    data = LoginOut(
        access_token=create_access_token(user.id, user.role),
        user=UserOut.model_validate(user),
    )
    return {"success": True, "message": "登录成功", "data": data.model_dump()}
