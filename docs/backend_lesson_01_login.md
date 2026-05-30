# 后端逐行精讲 01：登录接口

这一课只讲一条链路：

```text
POST /api/auth/login
```

目标是让你能从前端提交账号密码，一直讲到后端返回 token。

## 1. 先看完整流程

```text
前端提交 username/password
-> routers/auth.py 的 login 函数接收请求
-> LoginRequest 校验账号密码不能为空
-> get_db 提供数据库 session
-> services.authenticate_user 查询 users 表并校验密码
-> create_access_token 生成 token
-> LoginOut 组织返回数据
-> 返回 success/message/data 给前端
```

你先不要怕文件多。它们分工很清楚：

| 文件 | 在登录里做什么 |
| --- | --- |
| `routers/auth.py` | 定义登录接口地址 |
| `schemas.py` | 校验登录请求和组织返回结构 |
| `dependencies.py` | 提供数据库连接 |
| `services.py` | 查询用户并判断账号密码 |
| `passwords.py` | 校验密码哈希 |
| `security.py` | 生成和解析 token |
| `models.py` | 定义 `users` 表结构 |

## 2. 路由层：`routers/auth.py`

代码：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db
from ..schemas import LoginOut, LoginRequest, UserOut
from ..security import create_access_token
```

解释：

- `APIRouter`：用来创建一组接口。
- `Depends`：FastAPI 的依赖注入，用来自动拿数据库连接、当前用户等。
- `Session`：SQLAlchemy 的数据库会话类型。
- `services`：业务逻辑都在这里。
- `get_db`：每个请求进来时，帮你准备一个数据库连接。
- `LoginRequest`：登录请求格式。
- `LoginOut`、`UserOut`：登录返回格式。
- `create_access_token`：生成 token。

答辩可以说：

> 登录接口的路由文件只负责接收请求和组织返回，真正的认证逻辑放在 service 层。

继续看：

```python
router = APIRouter(prefix="/api/auth", tags=["auth"])
```

解释：

这表示这个文件里的接口统一以 `/api/auth` 开头。

所以后面写：

```python
@router.post("/login")
```

完整接口地址就是：

```text
POST /api/auth/login
```

这点很重要，老师问接口地址时，你要能从 `prefix + path` 拼出来。

核心函数：

```python
@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = services.authenticate_user(db, payload)
    data = LoginOut(
        access_token=create_access_token(user.id, user.role),
        user=UserOut.model_validate(user),
    )
    return {"success": True, "message": "登录成功", "data": data.model_dump()}
```

逐行解释：

```python
@router.post("/login")
```

定义一个 POST 接口，路径是 `/api/auth/login`。

```python
def login(payload: LoginRequest, db: Session = Depends(get_db)):
```

这个函数有两个参数：

- `payload`：前端传来的账号密码，会自动用 `LoginRequest` 校验。
- `db`：数据库会话，由 `get_db` 自动提供。

```python
user = services.authenticate_user(db, payload)
```

调用 service 层认证用户。它会查 `users` 表，并校验密码。

```python
data = LoginOut(...)
```

把 token 和用户信息包装成统一返回格式。

```python
access_token=create_access_token(user.id, user.role)
```

用用户 id 和角色生成 token。后面访问需要权限的接口时，就靠 token 识别用户。

```python
user=UserOut.model_validate(user)
```

把 SQLAlchemy 的 `User` 对象转换成 Pydantic 的返回对象，只返回前端需要的字段。

```python
return {"success": True, "message": "登录成功", "data": data.model_dump()}
```

返回统一 JSON。

这段你要能背出来的人话版：

> 前端提交账号密码后，后端先用 `LoginRequest` 校验参数，再通过 `get_db` 获得数据库连接，调用 `authenticate_user` 查询用户并校验密码。成功后生成 token，并返回用户信息。

## 3. 参数校验层：`schemas.py`

登录请求模型：

```python
class LoginRequest(BaseModel):
    username: str
    password: str
```

解释：

前端必须传两个字段：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

如果缺少字段，或者字段类型不对，FastAPI/Pydantic 会拦截。

继续看：

```python
@field_validator("username", mode="before")
@classmethod
def validate_username(cls, value: str):
    return _require_text(value, "账号", 50)
```

解释：

这表示在正式处理 `username` 前，先检查它：

- 去掉前后空格。
- 不能为空。
- 不能超过 50 个字符。

密码校验：

```python
@field_validator("password", mode="before")
@classmethod
def validate_password(cls, value: str):
    return _require_text(value, "密码")
```

解释：

密码不能为空。

返回用户模型：

```python
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    display_name: str
```

解释：

`UserOut` 控制登录后返回哪些用户字段。注意它没有返回 `password_hash`，这是安全设计。

登录返回模型：

```python
class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
```

解释：

登录成功后返回三部分：

- `access_token`：登录凭证。
- `token_type`：固定是 `bearer`。
- `user`：用户基本信息。

答辩可以说：

> Schema 层负责请求和响应的数据结构，能保证前端传来的账号密码不为空，也能避免把密码哈希等敏感字段返回给前端。

## 4. 数据库连接：`dependencies.py`

登录函数里有：

```python
db: Session = Depends(get_db)
```

它对应：

```python
def get_db(request: Request):
    SessionLocal = request.app.state.SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

逐行解释：

```python
SessionLocal = request.app.state.SessionLocal
```

从 FastAPI 应用对象里拿数据库会话工厂。

```python
db = SessionLocal()
```

创建一次数据库会话。

```python
yield db
```

把这个数据库会话交给接口函数使用。

```python
finally:
    db.close()
```

请求结束后关闭数据库会话，避免连接泄漏。

答辩可以说：

> 后端通过 FastAPI 的依赖注入给接口提供数据库 session，请求结束后自动关闭，避免每个接口重复写连接和关闭逻辑。

## 5. 业务逻辑层：`services.authenticate_user`

代码：

```python
def authenticate_user(db: Session, payload: LoginRequest) -> User:
    user = db.scalar(select(User).where(User.username == payload.username))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ApiError(401, "账号或密码错误")
    return user
```

逐行解释：

```python
user = db.scalar(select(User).where(User.username == payload.username))
```

这行是在查数据库：

```sql
SELECT * FROM users WHERE username = 前端传来的账号
```

`User` 是 SQLAlchemy 模型，对应数据库的 `users` 表。

```python
if user is None
```

如果查不到用户，说明账号不存在。

```python
not verify_password(payload.password, user.password_hash)
```

如果用户存在，就校验密码。这里不是拿明文密码直接比，而是用哈希算法比。

```python
raise ApiError(401, "账号或密码错误")
```

账号不存在或密码错误，都统一返回“账号或密码错误”。

为什么不告诉用户“账号不存在”还是“密码错误”？

因为这样更安全，避免别人枚举系统里有哪些账号。

```python
return user
```

认证成功，返回用户对象给路由层。

答辩可以说：

> 登录认证逻辑在 service 层。系统先按用户名查询用户表，再用密码哈希校验密码。账号不存在或密码错误都返回 401，避免泄露账号是否存在。

## 6. 密码哈希：`passwords.py`

创建密码哈希：

```python
def hash_password(password: str, salt: str | None = None) -> str:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt.encode("utf-8"),
        ITERATIONS,
    ).hex()
    return f"{ALGORITHM}${ITERATIONS}${password_salt}${digest}"
```

你不需要完全背算法，但要懂含义：

- 给密码加盐。
- 用 PBKDF2 + SHA256 算哈希。
- 迭代 120000 次，增加破解成本。
- 数据库存储的是哈希结果，不是明文密码。

校验密码：

```python
def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt, expected_digest = password_hash.split("$", 3)
        if algorithm != ALGORITHM:
            return False
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected_digest)
```

人话版：

> 登录时，系统把用户输入的密码用同样的盐和算法再算一次哈希，然后和数据库保存的哈希比较。如果一致，说明密码正确。

这里的关键点：

```python
hmac.compare_digest(digest, expected_digest)
```

它比普通 `==` 更适合比较敏感字符串，避免一些时间侧信道风险。答辩不一定会问，但你知道会显得很稳。

## 7. Token 生成：`security.py`

代码：

```python
def create_access_token(user_id: int, role: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRE_MINUTES)).timestamp()),
    }
```

解释：

token 里保存：

| 字段 | 含义 |
| --- | --- |
| `sub` | 用户 id |
| `role` | 用户角色 |
| `iat` | 签发时间 |
| `exp` | 过期时间 |

继续看：

```python
header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
signing_input = f"{_b64encode(_json_bytes(header))}.{_b64encode(_json_bytes(payload))}"
signature = hmac.new(
    JWT_SECRET.encode("utf-8"),
    signing_input.encode("ascii"),
    hashlib.sha256,
).digest()
return f"{signing_input}.{_b64encode(signature)}"
```

解释：

这段是在生成一个类似 JWT 的 token：

```text
header.payload.signature
```

- `header`：说明签名算法。
- `payload`：保存用户 id、角色和过期时间。
- `signature`：用密钥签名，防止 token 被篡改。

答辩可以说：

> 登录成功后，系统生成包含用户 id、角色和过期时间的 token，并使用密钥签名。后续请求携带 token，后端就能识别当前用户身份和权限。

## 8. Token 怎么被后续接口使用

虽然登录接口只负责生成 token，但你还要知道后续接口怎么用它。

`dependencies.py`：

```python
def get_current_user(
    db: Session = Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
```

解释：

这个函数会从请求头里读取：

```text
Authorization: Bearer 你的token
```

然后：

```python
payload = decode_access_token(credentials.credentials)
```

解析 token。

```python
user = services.get_user(db, int(payload["sub"]))
```

根据 token 里的用户 id 查询 `users` 表。

如果 token 缺失、无效、过期，返回 401。

权限判断：

```python
def require_roles(*roles: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise services.ApiError(403, "当前角色无权执行该操作")
        return current_user
```

解释：

如果接口写了：

```python
Depends(require_roles("manager", "admin"))
```

那只有 `manager` 和 `admin` 可以访问。

答辩可以说：

> 登录接口生成 token，后续接口通过 `get_current_user` 解析 token 得到当前用户，再通过 `require_roles` 判断用户角色是否有权限。

## 9. 你应该如何调试登录接口

启动后端：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork\backend
python run_sqlite.py
```

打开：

```text
http://127.0.0.1:3000/docs
```

找到：

```text
POST /api/auth/login
```

输入：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

建议打断点的位置：

1. `routers/auth.py` 的 `login` 函数。
2. `services.py` 的 `authenticate_user`。
3. `passwords.py` 的 `verify_password`。
4. `security.py` 的 `create_access_token`。

你要观察这些变量：

| 变量 | 看什么 |
| --- | --- |
| `payload.username` | 前端传来的账号 |
| `payload.password` | 前端传来的密码 |
| `user` | 数据库查出来的用户 |
| `user.password_hash` | 数据库存储的哈希密码 |
| `access_token` | 登录成功后生成的 token |

## 10. 登录接口答辩模板

短版：

> 登录接口是 `POST /api/auth/login`。前端提交账号密码后，后端使用 `LoginRequest` 校验参数，通过 SQLAlchemy 查询 `users` 表，再用密码哈希函数校验密码。校验通过后生成包含用户 id 和角色的 token，并返回给前端。

详细版：

> 登录接口位于 `routers/auth.py`，路由前缀是 `/api/auth`，所以完整地址是 `/api/auth/login`。接口接收 `LoginRequest`，确保账号密码不为空，同时通过 `Depends(get_db)` 获取数据库会话。认证逻辑放在 `services.authenticate_user`，它按用户名查询 `users` 表，并调用 `verify_password` 比对密码哈希。登录成功后，`create_access_token` 会生成包含用户 id、角色、签发时间和过期时间的 token。后续接口通过 `Authorization: Bearer token` 识别用户，并用 `require_roles` 做角色权限控制。

## 11. 自测题

1. `/api/auth/login` 的完整路径是怎么拼出来的？
2. `LoginRequest` 校验了哪两个字段？
3. 为什么 `UserOut` 不返回 `password_hash`？
4. `authenticate_user` 查的是哪张表？
5. 账号不存在和密码错误为什么都返回同一句提示？
6. token 里保存了哪些关键信息？
7. 后续接口如何通过 token 找到当前用户？
8. 401 和 403 有什么区别？

能把这 8 个问题讲清楚，登录链路就算过关。

