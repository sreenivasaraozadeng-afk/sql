from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db
from ..schemas import LoginOut, LoginRequest, UserOut
from ..security import create_access_token


router = APIRouter(prefix="/api/auth", tags=["auth"])

#前端访问
@router.post("/login")  # 定义一个 POST 请求接口，接口地址是 /login，用来处理用户登录
def login(
    payload: LoginRequest,  # 接收前端传来的登录数据，并用 LoginRequest 这个 Pydantic 模型自动校验格式
    db: Session = Depends(get_db)  # 通过 Depends 自动获取数据库连接，会得到一个 SQLAlchemy 的 Session 对象
):
    user = services.authenticate_user(db, payload)  # 调用登录验证函数：根据账号查用户，并检查密码是否正确

    data = LoginOut(  # 创建登录成功后要返回给前端的数据对象
        access_token=create_access_token(user.id, user.role),  # 根据用户 id 和角色生成登录令牌 token
        user=UserOut.model_validate(user),  # 把数据库查出来的 user 对象转换成接口返回用的 UserOut 对象
    )

    return {  # 返回给前端的 JSON 数据
        "success": True,  # 表示登录成功
        "message": "登录成功",  # 返回提示信息
        "data": data.model_dump()  # 把 LoginOut 对象转换成普通字典，方便 FastAPI 返回 JSON
    }