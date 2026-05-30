# 后端逐行精讲 02：创建船员接口

这一课讲第二条后端主线：

```text
POST /api/crews
```

目标是让你能讲清楚：为什么创建一个船员时，后端会同时写入 `users` 表和 `crews` 表。

## 1. 先看完整流程

```text
前端提交船员信息
-> routers/crews.py 的 create_crew 接收请求
-> CrewCreate 校验账号、密码、姓名、性别、身份证、岗位
-> get_db 提供数据库 session
-> get_optional_current_user 识别当前用户
-> 检查 manager/admin 权限
-> services.create_crew 执行业务逻辑
-> 处理岗位字典 positions
-> 创建 User 登录账号
-> 创建 Crew 船员档案
-> users 和 crews 通过 user_id 外键关联
-> 写 operation_logs
-> 返回船员数据
```

对应文件：

| 文件 | 在创建船员里做什么 |
| --- | --- |
| `routers/crews.py` | 定义船员接口和权限 |
| `schemas.py` | 校验新增船员请求 |
| `dependencies.py` | 提供数据库连接和当前用户 |
| `services.py` | 创建账号、创建档案、写日志 |
| `models.py` | 定义 `users`、`crews`、`positions` 表结构 |
| `passwords.py` | 把密码转成哈希 |

## 2. 路由层：`routers/crews.py`

先看导入：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import services
from ..dependencies import get_db, get_optional_current_user
from ..models import User
from ..schemas import CrewCreate, CrewUpdate
```

解释：

- `APIRouter`：定义接口组。
- `Depends`：自动注入数据库连接和当前用户。
- `Session`：数据库会话类型。
- `services`：业务逻辑所在文件。
- `get_db`：提供数据库连接。
- `get_optional_current_user`：如果请求带 token，就识别当前用户；没带也返回 `None`。
- `CrewCreate`：新增船员请求格式。
- `CrewUpdate`：更新船员请求格式。

路由前缀：

```python
router = APIRouter(prefix="/api/crews", tags=["crews"])
```

这表示本文件里的接口都以：

```text
/api/crews
```

开头。

## 3. 权限辅助函数

代码：

```python
def _enforce_role_when_authenticated(
    current_user: User | None,
    allowed_roles: set[str],
) -> None:
    if current_user is not None and current_user.role not in allowed_roles:
        raise services.ApiError(403, "当前角色无权执行该操作")
```

逐行解释：

```python
current_user: User | None
```

当前登录用户。可能有用户，也可能是 `None`。

```python
allowed_roles: set[str]
```

允许操作的角色集合，比如：

```python
{"manager", "admin"}
```

```python
if current_user is not None and current_user.role not in allowed_roles:
```

如果用户已经登录，但角色不在允许列表里，就禁止。

```python
raise services.ApiError(403, "当前角色无权执行该操作")
```

返回 403，表示有登录身份但权限不够。

注意：

这里用的是 `get_optional_current_user`，所以没带 token 的情况下可能不会拦截。这是为了兼容旧页面和演示场景。答辩时如果老师问权限设计，你可以说：新接口中关键操作通常会使用角色依赖控制；船员模块这里保留了可选用户兼容逻辑，但如果识别到用户，会检查角色。

## 4. 创建船员接口

代码：

```python
@router.post("")
def create_crew(
    payload: CrewCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    _enforce_role_when_authenticated(current_user, {"manager", "admin"})
    return {
        "success": True,
        "message": "船员创建成功",
        "data": services.create_crew(db, payload, current_user),
    }
```

逐行解释：

```python
@router.post("")
```

因为路由前缀是 `/api/crews`，这里的空字符串表示完整接口就是：

```text
POST /api/crews
```

```python
payload: CrewCreate
```

前端传来的船员信息会被 `CrewCreate` 校验。

```python
db: Session = Depends(get_db)
```

FastAPI 自动创建数据库会话传进来。

```python
current_user: User | None = Depends(get_optional_current_user)
```

尝试读取当前登录用户。

```python
_enforce_role_when_authenticated(current_user, {"manager", "admin"})
```

如果当前用户存在，必须是 `manager` 或 `admin` 才能创建船员。

```python
"data": services.create_crew(db, payload, current_user)
```

真正创建逻辑交给 service 层。

答辩可以说：

> 路由层只负责接收请求、注入数据库、检查权限和返回统一 JSON，真正的新增船员逻辑在 `services.create_crew`。

## 5. 请求参数：`CrewCreate`

代码：

```python
class CrewCreate(BaseModel):
    username: str
    password: str
    name: str
    gender: str = "男"
    id_card: str
    phone: str | None = None
    position: str = "水手"
    position_id: int | None = None
```

前端大概传：

```json
{
  "username": "crew009",
  "password": "123456",
  "name": "张三",
  "gender": "男",
  "id_card": "110101200001011234",
  "phone": "13800138000",
  "position": "水手"
}
```

字段解释：

| 字段 | 作用 |
| --- | --- |
| `username` | 船员登录账号 |
| `password` | 初始密码 |
| `name` | 船员姓名 |
| `gender` | 性别，默认男 |
| `id_card` | 身份证号 |
| `phone` | 联系电话，可为空 |
| `position` | 岗位名称，默认水手 |
| `position_id` | 岗位字典 id，可为空 |

账号校验：

```python
@field_validator("username", mode="before")
@classmethod
def validate_username(cls, value: str):
    return _require_text(value, "账号", 50)
```

含义：

账号不能为空，长度不能超过 50。

密码校验：

```python
@field_validator("password", mode="before")
@classmethod
def validate_password(cls, value: str):
    value = _require_text(value, "密码")
    if len(value) < 3:
        raise ValueError("密码长度不能少于 3 位")
    return value
```

含义：

密码不能为空，至少 3 位。

姓名校验：

```python
return _require_text(value, "姓名", 50)
```

含义：

姓名不能为空，长度不能超过 50。

性别校验：

```python
if value not in {"男", "女"}:
    raise ValueError("性别只能是男或女")
```

含义：

性别只能是 `男` 或 `女`。

身份证校验：

```python
if not ID_CARD_PATTERN.fullmatch(value):
    raise ValueError("身份证号格式不正确")
```

含义：

身份证必须符合 15 位或 18 位格式。

电话校验：

```python
return _validate_optional_phone(value)
```

含义：

电话可以不填；如果填写，必须是 6 到 20 位数字，可带 `+`。

岗位校验：

```python
return _require_text(value, "岗位", 50)
```

含义：

岗位不能为空。

答辩可以说：

> 新增船员使用 `CrewCreate` 校验请求参数，能在进入业务逻辑前拦截账号为空、密码太短、身份证格式错误、性别非法等问题。

## 6. 业务逻辑：`services.create_crew`

完整代码：

```python
def create_crew(db: Session, payload: CrewCreate, actor: User | None = None) -> dict:
    position_id, position_name = _get_position_name(db, payload.position_id, payload.position)
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        role="seafarer",
        display_name=payload.name,
    )
    crew = Crew(
        user=user,
        position_id=position_id,
        name=payload.name,
        gender=payload.gender,
        id_card=payload.id_card,
        phone=payload.phone,
        position=position_name,
        status="available",
    )
    db.add(crew)
    _flush_or_duplicate(db, "账号、身份证号或证书编号已存在")
    _add_operation_log(db, actor, "create", "crew", crew.id, crew.name)
    _commit_or_duplicate(db, "账号、身份证号或证书编号已存在")
    db.refresh(crew)
    return crew_to_dict(crew)
```

逐行解释：

```python
position_id, position_name = _get_position_name(db, payload.position_id, payload.position)
```

先处理岗位。前端可能传 `position_id`，也可能只传岗位名称 `position`。

如果传的是 id，就去 `positions` 表查。

如果只传名称，就按名称查；如果不存在，就自动创建一个岗位字典记录。

这体现了岗位字典表设计。

```python
user = User(...)
```

创建登录账号，对应 `users` 表。

```python
username=payload.username
```

账号来自前端。

```python
password_hash=hash_password(payload.password)
```

密码不能明文保存，要先哈希。

```python
role="seafarer"
```

新建船员默认角色是普通船员。

```python
display_name=payload.name
```

用户显示名称使用船员姓名。

接着：

```python
crew = Crew(...)
```

创建船员档案，对应 `crews` 表。

```python
user=user
```

这是最关键的一行。它把新建的 `Crew` 和新建的 `User` 关联起来。

SQLAlchemy 会根据模型关系，把 `users` 和 `crews` 两张表一起处理。

```python
position_id=position_id
position=position_name
```

同时保存岗位 id 和岗位名称。

为什么两个都存？

因为 `position_id` 方便关联字典表，`position` 方便前端和旧接口直接显示中文岗位名。

```python
status="available"
```

新船员默认是可派遣状态。

```python
db.add(crew)
```

把船员对象加入数据库会话。因为 `crew.user = user`，所以关联的用户也会一起保存。

```python
_flush_or_duplicate(db, "账号、身份证号或证书编号已存在")
```

先 flush 一次，让数据库检查唯一约束。

可能触发重复的字段：

- `users.username`
- `crews.id_card`

```python
_add_operation_log(db, actor, "create", "crew", crew.id, crew.name)
```

写操作日志，记录谁创建了哪个船员。

```python
_commit_or_duplicate(db, "账号、身份证号或证书编号已存在")
```

提交事务，真正写入数据库。

```python
db.refresh(crew)
```

刷新对象，拿到数据库生成的 id、时间等最新值。

```python
return crew_to_dict(crew)
```

转换成字典返回给前端。

答辩可以说：

> `create_crew` 会先处理岗位字典，再创建 `User` 登录账号和 `Crew` 船员档案。两者通过 ORM 关系关联，提交后写入 `users` 和 `crews` 两张表。系统还会检查账号和身份证唯一性，并记录操作日志。

## 7. 岗位字典：`_get_position_name`

代码：

```python
def _get_position_name(db: Session, position_id: int | None, fallback: str | None) -> tuple[int | None, str]:
    if position_id is not None:
        position = db.get(Position, position_id)
        if position is None:
            raise ApiError(404, "岗位不存在")
        return position.id, position.name
    if fallback:
        position = db.scalar(select(Position).where(Position.name == fallback))
        if position is None:
            position = Position(name=fallback)
            db.add(position)
            db.flush()
        return position.id, position.name
    raise ApiError(400, "岗位不能为空")
```

这段做三种情况：

第一种：前端传了 `position_id`。

```python
position = db.get(Position, position_id)
```

按主键查 `positions` 表。

如果查不到：

```python
raise ApiError(404, "岗位不存在")
```

第二种：前端没传 id，但传了岗位名称。

```python
position = db.scalar(select(Position).where(Position.name == fallback))
```

按名称查。

如果岗位名称也不存在：

```python
position = Position(name=fallback)
db.add(position)
db.flush()
```

自动新增岗位字典记录。

第三种：id 和名称都没有。

```python
raise ApiError(400, "岗位不能为空")
```

答辩可以说：

> 岗位既支持通过字典表 id 关联，也兼容直接传中文岗位名。后端会统一解析成岗位 id 和岗位名称，保证数据能关联，也方便前端显示。

## 8. 表结构：`User`、`Crew`、`Position`

`User` 模型：

```python
class User(Base):
    __tablename__ = "users"

    id = 主键
    username = 唯一账号
    password_hash = 密码哈希
    role = 用户角色
    display_name = 显示名称
```

你要记住：

`users` 表负责登录和权限。

`Crew` 模型：

```python
class Crew(Base):
    __tablename__ = "crews"

    user_id = ForeignKey("users.id"), unique=True
    position_id = ForeignKey("positions.id")
    name = 船员姓名
    gender = 性别
    id_card = 身份证号，唯一
    phone = 电话
    position = 岗位名称
    status = 船员状态
```

你要记住：

`crews` 表负责船员业务档案。

关键关系：

```python
user: Mapped[User] = relationship(back_populates="crew")
position_ref: Mapped[Position | None] = relationship(back_populates="crews")
certificates: Mapped[list["Certificate"]] = relationship(back_populates="crew")
dispatches: Mapped[list["Dispatch"]] = relationship(back_populates="crew")
voyages: Mapped[list["VoyageRecord"]] = relationship(back_populates="crew")
```

这些关系说明：

- 一个船员关联一个用户。
- 一个船员属于一个岗位。
- 一个船员可以有多本证书。
- 一个船员可以有多条派遣记录。
- 一个船员可以有多条海历记录。

`Position` 模型：

```python
class Position(Base):
    __tablename__ = "positions"
    name = 唯一岗位名称
```

岗位名称唯一，避免岗位字典重复。

答辩可以说：

> 船员模块体现了多表关系。`users` 和 `crews` 是一对一，`positions` 和 `crews` 是一对多，`crews` 又和证书、派遣、海历形成一对多关系。

## 9. 返回数据：`crew_to_dict`

代码：

```python
def crew_to_dict(crew: Crew) -> dict:
    return {
        "id": crew.id,
        "username": crew.user.username,
        "password": "******",
        "name": crew.name,
        "gender": crew.gender,
        "id_card": crew.id_card,
        "phone": crew.phone,
        "position_id": crew.position_id,
        "position": crew.position,
        "status": crew.status,
        "is_at_sea": 1 if crew.status == "at_sea" else 0,
        "role": "admin" if crew.user.role == "admin" else "user",
    }
```

重点：

```python
"password": "******"
```

返回给前端时不返回真实密码，也不返回密码哈希。

```python
"username": crew.user.username
```

通过 `crew.user` 读取关联用户账号。

```python
"is_at_sea": 1 if crew.status == "at_sea" else 0
```

兼容旧前端可能使用的字段。

答辩可以说：

> 返回数据时，后端会把 ORM 对象转换成前端需要的字典，同时隐藏密码信息，只返回业务展示需要的字段。

## 10. 删除船员为什么是软删除

代码：

```python
def soft_delete_crew(db: Session, crew_id: int, actor: User | None = None) -> dict:
    crew = _get_crew_or_404(db, crew_id)
    crew.status = "inactive"
    _add_operation_log(db, actor, "delete", "crew", crew.id, crew.name)
    db.commit()
    db.refresh(crew)
    return crew_to_dict(crew)
```

解释：

它没有真正删除数据库记录，而是：

```python
crew.status = "inactive"
```

为什么？

因为船员可能已经有证书、派遣、海历。如果直接删除，会影响历史数据完整性。软删除保留数据，只是在列表里过滤掉。

`list_crews` 中就有：

```python
.where(Crew.status != "inactive")
```

所以停用船员不会出现在普通船员列表里。

答辩可以说：

> 删除船员采用软删除，把状态改为 `inactive`。这样既能让前端不再显示该船员，又能保留证书、派遣和海历等历史数据，保证数据库完整性。

## 11. 这条接口涉及哪些数据库约束

你要会讲这些：

| 约束 | 位置 | 作用 |
| --- | --- | --- |
| `users.username unique` | `User.username` | 账号不能重复 |
| `crews.user_id unique` | `Crew.user_id` | 一个账号只对应一个船员档案 |
| `crews.id_card unique` | `Crew.id_card` | 身份证不能重复 |
| `positions.name unique` | `Position.name` | 岗位字典名称不能重复 |
| `ck_crews_gender` | `Crew` | 性别只能是男/女 |
| `ck_crews_status` | `Crew` | 状态只能是系统允许值 |

答辩可以说：

> 创建船员不仅有前端表单校验，还有数据库唯一约束和检查约束。这样即使前端绕过校验，数据库层也能保证账号、身份证和状态值合法。

## 12. 调试这条接口

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
POST /api/crews
```

示例请求：

```json
{
  "username": "crew_test",
  "password": "123456",
  "name": "测试船员",
  "gender": "男",
  "id_card": "110101200001019999",
  "phone": "13800138000",
  "position": "水手"
}
```

建议打断点：

1. `routers/crews.py` 的 `create_crew`。
2. `schemas.py` 的 `CrewCreate` 校验方法。
3. `services.py` 的 `_get_position_name`。
4. `services.py` 的 `create_crew`。
5. `services.py` 的 `crew_to_dict`。

观察变量：

| 变量 | 看什么 |
| --- | --- |
| `payload` | 前端传来的船员信息 |
| `current_user` | 当前登录用户 |
| `position_id`、`position_name` | 岗位解析结果 |
| `user` | 新建登录账号 |
| `crew` | 新建船员档案 |
| `crew.id` | 数据库生成的船员 id |

## 13. 答辩模板

短版：

> 创建船员接口是 `POST /api/crews`。前端提交船员账号和档案信息后，后端用 `CrewCreate` 校验参数，再调用 `services.create_crew`。该函数会创建 `users` 登录账号和 `crews` 船员档案，两者通过 `crews.user_id` 外键一对一关联，同时写入操作日志。

详细版：

> 创建船员接口位于 `routers/crews.py`，路由前缀是 `/api/crews`。接口接收 `CrewCreate`，校验账号、密码、姓名、性别、身份证和岗位等字段。业务逻辑在 `services.create_crew`，它先根据 `position_id` 或岗位名称处理岗位字典，然后创建 `User` 对象保存登录账号、密码哈希和角色，再创建 `Crew` 对象保存船员姓名、身份证、电话、岗位和状态。`Crew.user_id` 外键指向 `users.id`，并设置唯一约束，保证一个账号只对应一个船员档案。提交时还会检查账号和身份证唯一性，并写入操作日志。

## 14. 自测题

1. `POST /api/crews` 的完整路径是怎么来的？
2. `CrewCreate` 校验了哪些字段？
3. 创建船员时为什么要创建 `User`？
4. `User` 和 `Crew` 是什么关系？
5. `hash_password(payload.password)` 的作用是什么？
6. 新建船员默认角色是什么？
7. 新建船员默认状态是什么？
8. 为什么 `db.add(crew)` 后 `user` 也会一起保存？
9. 为什么删除船员用 `inactive` 而不是直接删除？
10. 这条接口体现了哪些数据库约束？

能讲清这 10 个问题，船员创建链路就过关了。

