from collections.abc import Iterable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import services
from .models import User
from .security import decode_access_token


bearer_scheme = HTTPBearer(auto_error=False)


def get_db(request: Request):
    SessionLocal = request.app.state.SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None:
        raise services.ApiError(401, "请先登录")
    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise services.ApiError(401, "登录状态无效或已过期")
    user = services.get_user(db, int(payload["sub"]))
    if user is None:
        raise services.ApiError(401, "登录用户不存在")
    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User | None:
    if credentials is None:
        return None
    return get_current_user(db, credentials)


def require_roles(*roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise services.ApiError(403, "当前角色无权执行该操作")
        return current_user

    return dependency


def require_any_role(roles: Iterable[str]):
    return require_roles(*roles)
