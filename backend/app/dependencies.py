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

def get_optional_current_user(  # 定义一个函数：尝试获取当前登录用户，但允许用户不登录
    db: Session = Depends(get_db),  # 通过 Depends 自动获取数据库连接，用来查询用户信息
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),  # 尝试从请求头里获取 token；如果没有 token，就是 None
) -> User | None:  # 返回值可能是 User 用户对象，也可能是 None
    if credentials is None:  # 判断前端请求里有没有携带登录 token
        return None  # 如果没有 token，说明用户未登录，直接返回 None，不报错

    return get_current_user(db, credentials)  # 如果有 token，就调用 get_current_user 校验 token，并返回当前用户


def require_roles(*roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise services.ApiError(403, "当前角色无权执行该操作")
        return current_user

    return dependency


def require_any_role(roles: Iterable[str]):
    return require_roles(*roles)
