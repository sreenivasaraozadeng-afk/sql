# 后端逐行精讲 05：派遣状态流转与海历生成

这一课讲派遣模块。它是后端里非常重要的一条业务主线，因为它不是简单的增删改查，而是一个“状态流转”。

你要记住这条主线：

```text
经理发起派遣
-> 船东确认
-> 经理确认上船
-> 系统生成海历
-> 经理确认下船
-> 系统结束海历并恢复船员状态
```

对应的状态变化是：

```text
pending_owner -> confirmed -> onboard -> offboard
```

如果中途取消，则进入：

```text
cancelled
```

这节课要能讲清楚 5 个接口：

```text
POST /api/dispatches
PUT  /api/dispatches/{dispatch_id}/confirm
PUT  /api/dispatches/{dispatch_id}/onboard
PUT  /api/dispatches/{dispatch_id}/offboard
PUT  /api/dispatches/{dispatch_id}/cancel
```

## 1. 这个模块为什么重要

答辩时可以这样说：

```text
派遣模块是岗位匹配之后的实际业务执行环节。
它会把岗位需求、船员、证书校验、船东确认、上船下船和海历记录串起来。
每一次状态变化都会写 dispatch_status_logs，关键操作还会写 operation_logs。
所以这个模块能体现数据库表之间的关系、状态约束和业务流程完整性。
```

老师喜欢听到的关键词：

```text
状态流转
多表联动
日志追踪
外键关联
业务约束
海历自动生成
```

## 2. 相关文件

| 作用 | 文件 | 重点 |
| --- | --- | --- |
| 派遣接口入口 | `backend/app/routers/dispatches.py` | 5 个派遣状态接口 |
| 请求参数 | `backend/app/schemas.py` | `DispatchCreate` |
| 业务逻辑 | `backend/app/services.py` | `create_dispatch`、`confirm_dispatch`、`onboard_dispatch`、`offboard_dispatch`、`cancel_dispatch` |
| 数据表模型 | `backend/app/models.py` | `Dispatch`、`DispatchStatusLog`、`VoyageRecord` |
| 旧版海历兼容接口 | `backend/app/routers/legacy.py` | `/api/voyages`、`/api/my-voyages/{crew_id}` |

这一课读代码的顺序：

```text
routers/dispatches.py
-> schemas.DispatchCreate
-> services.create_dispatch
-> services.confirm_dispatch
-> services.onboard_dispatch
-> services.offboard_dispatch
-> services.cancel_dispatch
-> models.Dispatch / DispatchStatusLog / VoyageRecord
```

## 3. 先看路由：dispatches.py

`backend/app/routers/dispatches.py` 的 router 前缀是：

```python
router = APIRouter(prefix="/api/dispatches", tags=["dispatches"])
```

所以这个文件里的所有接口都以 `/api/dispatches` 开头。

接口列表：

| 接口 | 作用 | 允许角色 |
| --- | --- | --- |
| `GET /api/dispatches` | 查看派遣列表 | manager、shipowner、admin |
| `GET /api/dispatches/{id}` | 查看派遣详情和状态日志 | manager、shipowner、admin |
| `POST /api/dispatches` | 经理发起派遣 | manager、admin |
| `PUT /api/dispatches/{id}/confirm` | 船东确认派遣 | shipowner、admin |
| `PUT /api/dispatches/{id}/onboard` | 确认上船 | manager、admin |
| `PUT /api/dispatches/{id}/offboard` | 确认下船 | manager、admin |
| `PUT /api/dispatches/{id}/cancel` | 取消派遣 | manager、admin |

权限设计可以这样讲：

```text
经理负责调度，所以由 manager 发起派遣和确认上下船；
船东拥有岗位需求，所以派遣要经过 shipowner 确认；
admin 作为系统管理员拥有全部权限。
```

## 4. DispatchCreate：发起派遣要传什么

`DispatchCreate` 在 `backend/app/schemas.py`：

```python
class DispatchCreate(BaseModel):
    job_id: int
    crew_id: int
```

只有两个字段：

| 字段 | 含义 |
| --- | --- |
| `job_id` | 要派到哪个岗位需求 |
| `crew_id` | 要派哪个船员 |

为什么这么少？

```text
因为岗位需求本身已经包含船舶、航线、岗位、计划上船时间；
船员表也已经包含姓名、岗位、状态；
所以派遣只需要把 job 和 crew 关联起来。
```

这就是关系型数据库的设计思想：不要重复保存已经能通过外键查到的数据。

## 5. create_dispatch：经理发起派遣

接口：

```text
POST /api/dispatches
```

router 代码：

```python
@router.post("")
def create_dispatch(
    payload: DispatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {
        "success": True,
        "message": "派遣已提交船东确认",
        "data": services.create_dispatch(db, payload, current_user),
    }
```

这说明只有 `manager` 和 `admin` 可以发起派遣。

真正逻辑在 `services.create_dispatch`：

```python
def create_dispatch(db: Session, payload: DispatchCreate, creator: User) -> dict:
    job = _get_job_or_404(db, payload.job_id)
    crew = _get_crew_or_404(db, payload.crew_id)
    if job.status not in {"open", "matched"}:
        raise ApiError(400, "岗位当前不可派遣")
    if _active_dispatch_count(db, job.id) >= job.headcount:
        raise ApiError(400, "该岗位招聘人数已满")
    _ensure_crew_matches_job(db, crew, job)
    dispatch = Dispatch(
        job=job,
        crew=crew,
        status="pending_owner",
        created_by_user_id=creator.id,
    )
    db.add(dispatch)
    db.flush()
    _append_dispatch_status_log(db, dispatch, None, "pending_owner", creator, "业务经理发起派遣")
    _add_operation_log(db, creator, "create", "dispatch", dispatch.id, f"{crew.name}->{job.title}")
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)
```

这个函数可以拆成 6 步。

### 5.1 查岗位和船员

```python
job = _get_job_or_404(db, payload.job_id)
crew = _get_crew_or_404(db, payload.crew_id)
```

如果岗位或船员不存在，后端直接返回 404。

这里涉及两张表：

```text
job_demands
crews
```

### 5.2 判断岗位是否还能派遣

```python
if job.status not in {"open", "matched"}:
    raise ApiError(400, "岗位当前不可派遣")
```

岗位状态来自 `job_demands.status`。

本系统里的岗位状态有：

| 状态 | 含义 |
| --- | --- |
| `open` | 正在招聘 |
| `matched` | 已匹配到足够派遣人数 |
| `closed` | 已结束 |

如果岗位已经 `closed`，就不能再派遣。

### 5.3 判断招聘人数是否已满

```python
if _active_dispatch_count(db, job.id) >= job.headcount:
    raise ApiError(400, "该岗位招聘人数已满")
```

`_active_dispatch_count` 会统计这个岗位下正在进行的派遣数量：

```python
Dispatch.status.in_(["pending_owner", "confirmed", "onboard"])
```

也就是说，下面这些状态都算“占用了名额”：

```text
待船东确认
已确认待上船
已上船
```

这样可以防止一个岗位要求 1 人，却派出 2 个船员。

### 5.4 再次校验船员是否符合岗位

```python
_ensure_crew_matches_job(db, crew, job)
```

这个函数很关键：

```python
def _ensure_crew_matches_job(db: Session, crew: Crew, job: JobDemand) -> None:
    if crew.status != "available":
        raise ApiError(400, "该船员当前不可派遣")
    if crew.position != job.required_position:
        raise ApiError(400, "船员岗位不满足岗位需求")
    active_dispatch = db.scalar(
        select(Dispatch).where(
            Dispatch.crew_id == crew.id,
            Dispatch.status.in_(["pending_owner", "confirmed", "onboard"]),
        )
    )
    if active_dispatch is not None:
        raise ApiError(400, "该船员已有进行中的派遣")
    required_certificates = [
        item.certificate_type for item in job.required_certificates
    ]
    if not _crew_has_valid_certificates(crew, required_certificates, datetime.now(UTC).date()):
        raise ApiError(400, "船员证书未审核、已过期或不满足岗位需求")
```

这一步检查 4 件事：

| 检查 | 数据来源 | 目的 |
| --- | --- | --- |
| 船员必须 `available` | `crews.status` | 防止派遣不可用船员 |
| 岗位必须一致 | `crews.position` 和 `job_demands.required_position` | 防止岗位不匹配 |
| 船员不能已有进行中派遣 | `dispatches` | 防止同一船员被重复派 |
| 证书必须有效 | `certificates` | 防止未审核或过期证书通过 |

这一步和上一课智能匹配对应：

```text
智能匹配是推荐；
create_dispatch 是强校验；
推荐结果不能替代后端校验。
```

这个点答辩时很加分。

### 5.5 创建派遣主记录

```python
dispatch = Dispatch(
    job=job,
    crew=crew,
    status="pending_owner",
    created_by_user_id=creator.id,
)
```

写入的是 `dispatches` 表。

新派遣的初始状态是：

```text
pending_owner
```

意思是：

```text
业务经理已经发起派遣，但还在等待船东确认。
```

### 5.6 写状态日志和操作日志

```python
_append_dispatch_status_log(db, dispatch, None, "pending_owner", creator, "业务经理发起派遣")
_add_operation_log(db, creator, "create", "dispatch", dispatch.id, f"{crew.name}->{job.title}")
```

这里写了两张日志表：

| 日志表 | 作用 |
| --- | --- |
| `dispatch_status_logs` | 记录某一条派遣的状态变化 |
| `operation_logs` | 记录系统关键操作，比如创建、确认、上船、下船 |

区别可以这样讲：

```text
dispatch_status_logs 只关心派遣状态从什么变成什么；
operation_logs 更像系统审计日志，记录用户做了什么操作。
```

## 6. confirm_dispatch：船东确认派遣

接口：

```text
PUT /api/dispatches/{dispatch_id}/confirm
```

router 层要求：

```python
current_user: User = Depends(require_roles("shipowner", "admin"))
```

也就是船东或管理员才能确认。

service 逻辑：

```python
def confirm_dispatch(db: Session, dispatch_id: int, user: User) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "pending_owner":
        raise ApiError(400, "只有待船东确认的派遣可以确认")
    if user.role == "shipowner" and dispatch.job.owner_user_id != user.id:
        raise ApiError(403, "船东只能确认自己岗位的派遣")
    old_status = dispatch.status
    dispatch.status = "confirmed"
    dispatch.confirmed_by_user_id = user.id
    dispatch.crew.status = "pending"
    if _active_dispatch_count(db, dispatch.job_id) >= dispatch.job.headcount:
        dispatch.job.status = "matched"
    _append_dispatch_status_log(db, dispatch, old_status, "confirmed", user, "船东确认派遣")
    _add_operation_log(db, user, "confirm", "dispatch", dispatch.id, dispatch.crew.name)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)
```

逐步理解：

| 代码 | 意思 |
| --- | --- |
| `_get_dispatch_or_404` | 查派遣记录 |
| `dispatch.status != "pending_owner"` | 只有待船东确认的派遣能确认 |
| `dispatch.job.owner_user_id != user.id` | 船东只能确认自己的岗位 |
| `old_status = dispatch.status` | 记录旧状态，方便写日志 |
| `dispatch.status = "confirmed"` | 派遣状态变为已确认 |
| `dispatch.confirmed_by_user_id = user.id` | 记录是谁确认的 |
| `dispatch.crew.status = "pending"` | 船员状态变为待上船 |
| `dispatch.job.status = "matched"` | 如果人数已满，岗位变为已匹配 |

这一阶段涉及状态变化：

```text
dispatches.status: pending_owner -> confirmed
crews.status: available -> pending
job_demands.status: open -> matched
```

注意：`job_demands.status` 只有在派遣人数达到 `headcount` 时才改成 `matched`。

## 7. onboard_dispatch：确认上船并生成海历

接口：

```text
PUT /api/dispatches/{dispatch_id}/onboard
```

只有 `manager` 和 `admin` 可以操作。

service 逻辑：

```python
def onboard_dispatch(db: Session, dispatch_id: int, user: User | None = None) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "confirmed":
        raise ApiError(400, "只有已确认的派遣可以上船")
    now = utc_now()
    old_status = dispatch.status
    dispatch.status = "onboard"
    dispatch.crew.status = "at_sea"
    voyage = VoyageRecord(
        dispatch=dispatch,
        crew=dispatch.crew,
        job_id=dispatch.job_id,
        ship_name=dispatch.job.ship_name,
        route=dispatch.job.route,
        position=dispatch.job.required_position,
        onboard_at=now,
        status="onboard",
    )
    db.add(voyage)
    _append_dispatch_status_log(db, dispatch, old_status, "onboard", user, "确认上船")
    _add_operation_log(db, user, "onboard", "dispatch", dispatch.id, dispatch.crew.name)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)
```

这一步是整个模块最关键的地方，因为它会自动生成海历。

状态变化：

```text
dispatches.status: confirmed -> onboard
crews.status: pending -> at_sea
voyage_records: 新增一条海历记录
```

### 7.1 为什么只有 confirmed 才能上船

```python
if dispatch.status != "confirmed":
    raise ApiError(400, "只有已确认的派遣可以上船")
```

这就是状态机约束。

不能从 `pending_owner` 直接上船，因为还没经过船东确认。

也不能从 `cancelled` 上船，因为已经取消。

### 7.2 生成 VoyageRecord

```python
voyage = VoyageRecord(
    dispatch=dispatch,
    crew=dispatch.crew,
    job_id=dispatch.job_id,
    ship_name=dispatch.job.ship_name,
    route=dispatch.job.route,
    position=dispatch.job.required_position,
    onboard_at=now,
    status="onboard",
)
```

这对应 `voyage_records` 表。

海历里保存：

| 字段 | 来源 |
| --- | --- |
| `dispatch_id` | 当前派遣 |
| `crew_id` | 当前船员 |
| `job_id` | 当前岗位需求 |
| `ship_name` | 岗位对应船舶 |
| `route` | 岗位对应航线 |
| `position` | 岗位要求 |
| `onboard_at` | 确认上船时间 |
| `status` | `onboard` |

为什么海历保存 `ship_name`、`route`、`position` 这种中文快照？

```text
因为海历是历史记录。
即使以后岗位、船舶或航线信息有变化，过去这次出海经历也应该保留当时的船舶、航线和岗位信息。
```

这就是历史快照设计。

## 8. offboard_dispatch：确认下船并结束海历

接口：

```text
PUT /api/dispatches/{dispatch_id}/offboard
```

service 逻辑：

```python
def offboard_dispatch(db: Session, dispatch_id: int, user: User | None = None) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status != "onboard":
        raise ApiError(400, "只有已上船的派遣可以下船")
    now = utc_now()
    old_status = dispatch.status
    dispatch.status = "offboard"
    dispatch.crew.status = "available"
    dispatch.job.status = "closed"
    if dispatch.voyage is not None:
        dispatch.voyage.offboard_at = now
        dispatch.voyage.status = "offboard"
    _append_dispatch_status_log(db, dispatch, old_status, "offboard", user, "确认下船")
    _add_operation_log(db, user, "offboard", "dispatch", dispatch.id, dispatch.crew.name)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)
```

状态变化：

```text
dispatches.status: onboard -> offboard
crews.status: at_sea -> available
job_demands.status: matched/open -> closed
voyage_records.status: onboard -> offboard
voyage_records.offboard_at: 写入下船时间
```

这里可以这样解释：

```text
船员下船后，说明这次派遣已经结束，所以派遣状态变为 offboard；
船员重新变成 available，可以参与下一次匹配；
岗位需求完成后变成 closed；
海历记录补上下船时间，形成完整的上船到下船经历。
```

这就是派遣模块和海历模块的联动。

## 9. cancel_dispatch：取消派遣

接口：

```text
PUT /api/dispatches/{dispatch_id}/cancel
```

service 逻辑：

```python
def cancel_dispatch(db: Session, dispatch_id: int, user: User | None = None) -> dict:
    dispatch = _get_dispatch_or_404(db, dispatch_id)
    if dispatch.status == "offboard":
        raise ApiError(400, "已下船的派遣不能取消")
    old_status = dispatch.status
    dispatch.status = "cancelled"
    if dispatch.crew.status in {"pending", "at_sea"}:
        dispatch.crew.status = "available"
    if dispatch.job.status == "matched":
        dispatch.job.status = "open"
    if dispatch.voyage is not None:
        dispatch.voyage.status = "cancelled"
        dispatch.voyage.offboard_at = dispatch.voyage.offboard_at or utc_now()
    _append_dispatch_status_log(db, dispatch, old_status, "cancelled", user, "取消派遣")
    _add_operation_log(db, user, "cancel", "dispatch", dispatch.id, dispatch.crew.name)
    db.commit()
    db.refresh(dispatch)
    return dispatch_to_dict(dispatch)
```

取消规则：

| 情况 | 处理 |
| --- | --- |
| 已下船 `offboard` | 不能取消，因为流程已经完成 |
| 船员状态是 `pending` 或 `at_sea` | 恢复为 `available` |
| 岗位状态是 `matched` | 恢复为 `open` |
| 已经生成海历 | 海历状态改为 `cancelled` |

这里体现了数据修正：

```text
取消派遣不能只改 dispatches.status。
它还要把船员状态、岗位状态、海历状态一起调整，否则数据库会出现不一致。
```

## 10. 状态流转总表

| 操作 | 派遣状态 | 船员状态 | 岗位状态 | 海历变化 |
| --- | --- | --- | --- | --- |
| 发起派遣 | `pending_owner` | `available` | `open` 或 `matched` | 无 |
| 船东确认 | `confirmed` | `pending` | 人数满则 `matched` | 无 |
| 确认上船 | `onboard` | `at_sea` | `matched` | 新增 `voyage_records` |
| 确认下船 | `offboard` | `available` | `closed` | 写 `offboard_at`，状态 `offboard` |
| 取消派遣 | `cancelled` | 恢复 `available` | 可能恢复 `open` | 可能改为 `cancelled` |

这张表非常适合答辩时背下来。

老师问“派遣流程中哪些表会变”，你就按这张表讲。

## 11. 三张核心表怎么设计

### 11.1 dispatches：派遣主表

`Dispatch` 模型：

```python
class Dispatch(Base):
    __tablename__ = "dispatches"
```

核心字段：

| 字段 | 含义 |
| --- | --- |
| `id` | 派遣 ID |
| `job_id` | 关联岗位需求 |
| `crew_id` | 关联船员 |
| `status` | 派遣状态 |
| `created_by_user_id` | 谁发起派遣 |
| `confirmed_by_user_id` | 谁确认派遣 |
| `created_at` | 创建时间 |
| `updated_at` | 更新时间 |

外键关系：

```text
dispatches.job_id -> job_demands.id
dispatches.crew_id -> crews.id
```

模型里还有：

```python
job: Mapped[JobDemand] = relationship(back_populates="dispatches")
crew: Mapped[Crew] = relationship(back_populates="dispatches")
voyage: Mapped["VoyageRecord | None"] = relationship(back_populates="dispatch")
status_logs: Mapped[list["DispatchStatusLog"]] = relationship(...)
```

意思是：

```text
一条派遣属于一个岗位；
一条派遣属于一个船员；
一条派遣最多对应一条海历；
一条派遣可以有多条状态日志。
```

### 11.2 dispatch_status_logs：派遣状态日志表

`DispatchStatusLog` 保存的是每次状态变化。

核心字段：

| 字段 | 含义 |
| --- | --- |
| `dispatch_id` | 哪一条派遣发生变化 |
| `old_status` | 原状态 |
| `new_status` | 新状态 |
| `operator_user_id` | 谁操作的 |
| `remark` | 操作说明 |
| `created_at` | 操作时间 |

每次调用下面函数都会新增一条状态日志：

```python
_append_dispatch_status_log(db, dispatch, old_status, new_status, user, remark)
```

老师问“你们怎么追踪派遣流程”时，可以答：

```text
每次派遣状态变化，系统都会往 dispatch_status_logs 插入一条记录，保存旧状态、新状态、操作人和时间。
因此我们可以完整追溯一条派遣从发起、确认、上船到下船的全过程。
```

### 11.3 voyage_records：海历表

`VoyageRecord` 是船员实际出海经历。

核心字段：

| 字段 | 含义 |
| --- | --- |
| `dispatch_id` | 对应哪次派遣 |
| `crew_id` | 哪个船员 |
| `job_id` | 对应哪个岗位需求 |
| `ship_name` | 船名快照 |
| `route` | 航线快照 |
| `position` | 岗位快照 |
| `onboard_at` | 上船时间 |
| `offboard_at` | 下船时间 |
| `status` | 海历状态 |

注意这一行：

```python
dispatch_id: Mapped[int] = mapped_column(ForeignKey("dispatches.id"), unique=True)
```

`unique=True` 表示：

```text
一条派遣最多生成一条海历。
```

这能防止重复上船导致重复海历。

## 12. dispatch_to_dict：返回给前端什么

`dispatch_to_dict` 在 `backend/app/services.py`：

```python
def dispatch_to_dict(dispatch: Dispatch, include_logs: bool = False) -> dict:
    data = {
        "id": dispatch.id,
        "job_id": dispatch.job_id,
        "job_title": dispatch.job.title,
        "crew_id": dispatch.crew_id,
        "crew_name": dispatch.crew.name,
        "ship_name": dispatch.job.ship_name,
        "route": dispatch.job.route,
        "position": dispatch.job.required_position,
        "status": dispatch.status,
        "created_at": dispatch.created_at,
        "updated_at": dispatch.updated_at,
    }
```

前端拿到这个对象后，可以显示：

```text
岗位名称
船员姓名
船舶
航线
岗位
当前派遣状态
创建时间
更新时间
```

如果是详情接口，还会带上状态日志：

```python
if include_logs:
    data["status_logs"] = [
        {
            "id": item.id,
            "old_status": item.old_status,
            "new_status": item.new_status,
            "operator_user_id": item.operator_user_id,
            "remark": item.remark,
            "created_at": item.created_at,
        }
        for item in sorted(dispatch.status_logs, key=lambda log: log.id)
    ]
```

也就是说：

```text
列表页看当前状态；
详情页看完整流转历史。
```

## 13. list_dispatches 和 get_dispatch

### 13.1 派遣列表

```python
def list_dispatches(db: Session, user: User | None = None) -> list[dict]:
    query = (
        select(Dispatch)
        .options(joinedload(Dispatch.crew), joinedload(Dispatch.job))
        .order_by(Dispatch.id.desc())
    )
    if user is not None and user.role == "shipowner":
        query = query.join(JobDemand).where(JobDemand.owner_user_id == user.id)
    dispatches = db.scalars(query).unique().all()
    return [dispatch_to_dict(dispatch) for dispatch in dispatches]
```

重点：

```text
经理和管理员可以看全部派遣；
船东只能看自己发布岗位对应的派遣。
```

这体现了数据权限控制。

### 13.2 派遣详情

```python
def get_dispatch(db: Session, dispatch_id: int, user: User | None = None) -> dict:
    dispatch = db.scalar(
        select(Dispatch)
        .options(
            joinedload(Dispatch.crew),
            joinedload(Dispatch.job),
            selectinload(Dispatch.status_logs),
        )
        .where(Dispatch.id == dispatch_id)
    )
```

详情接口会加载：

```text
派遣主表 dispatches
船员 crews
岗位 job_demands
状态日志 dispatch_status_logs
```

最后：

```python
return dispatch_to_dict(dispatch, include_logs=True)
```

所以详情页能展示完整状态日志。

## 14. 为什么要同时有两种日志

很多同学会混淆：

```text
dispatch_status_logs
operation_logs
```

区别：

| 表 | 粒度 | 例子 |
| --- | --- | --- |
| `dispatch_status_logs` | 派遣状态变化 | pending_owner -> confirmed |
| `operation_logs` | 系统操作审计 | manager 创建派遣、shipowner 确认派遣 |

可以这样理解：

```text
dispatch_status_logs 是业务流程轨迹；
operation_logs 是系统操作审计。
```

这两个表一起让系统更完整。

## 15. 老师可能怎么追问

### 问：派遣为什么不创建后直接上船？

答：

```text
因为业务上需要船东确认。经理只能发起派遣，船东确认后才能进入 confirmed，再由经理确认上船。
这样状态流转更符合实际业务，也体现了不同角色的权限控制。
```

### 问：上船时为什么要生成海历？

答：

```text
海历代表船员真实出海经历。只有派遣确认并上船后，才说明这次经历实际开始，所以系统在 onboard_dispatch 中自动新增 voyage_records。
```

### 问：下船时哪些表会改？

答：

```text
dispatches.status 改为 offboard；
crews.status 改为 available；
job_demands.status 改为 closed；
voyage_records.offboard_at 写入下船时间，voyage_records.status 改为 offboard；
同时写 dispatch_status_logs 和 operation_logs。
```

### 问：怎么防止同一个船员被重复派遣？

答：

```text
create_dispatch 会调用 _ensure_crew_matches_job。
它会检查该船员是否已有 pending_owner、confirmed、onboard 状态的派遣。
如果有，后端会拒绝创建新派遣。
```

### 问：取消派遣为什么要恢复船员和岗位状态？

答：

```text
因为派遣取消后，船员不应该继续保持 pending 或 at_sea，岗位也可能需要重新开放。
如果只改 dispatches.status，会造成表之间状态不一致。
```

### 问：海历和派遣是什么关系？

答：

```text
派遣是调度流程，海历是实际出海记录。
一条派遣在确认上船后生成一条海历，voyage_records.dispatch_id 唯一关联 dispatches.id，所以一条派遣最多对应一条海历。
```

## 16. 你亲手跑一遍

启动后端：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork\backend
python run_sqlite.py
```

打开接口文档：

```text
http://127.0.0.1:3000/docs
```

建议按这个顺序操作：

```text
1. 登录 manager
2. 调用 GET /api/jobs，找一个 open 岗位
3. 调用 GET /api/jobs/{job_id}/matches，找一个匹配船员
4. 调用 POST /api/dispatches，传 job_id 和 crew_id
5. 登录 shipowner 或 admin
6. 调用 PUT /api/dispatches/{dispatch_id}/confirm
7. 登录 manager 或 admin
8. 调用 PUT /api/dispatches/{dispatch_id}/onboard
9. 调用 GET /api/dispatches/{dispatch_id}，查看状态日志
10. 调用 PUT /api/dispatches/{dispatch_id}/offboard
```

观察这些变化：

```text
dispatches.status 怎么变
crews.status 怎么变
job_demands.status 怎么变
voyage_records 是什么时候新增的
dispatch_status_logs 有几条记录
```

## 17. 这一课必须背下来的主线

```text
经理调用 POST /api/dispatches 发起派遣
-> 后端检查岗位是否开放、人数是否已满、船员是否可派、岗位和证书是否满足
-> dispatches 新增记录，状态 pending_owner
-> 写 dispatch_status_logs 和 operation_logs
-> 船东调用 confirm，派遣状态变 confirmed，船员状态变 pending
-> 经理调用 onboard，派遣状态变 onboard，船员状态变 at_sea，并新增 voyage_records
-> 经理调用 offboard，派遣状态变 offboard，船员恢复 available，岗位 closed，海历写入 offboard_at
-> 每次状态变化都写日志，保证流程可追踪
```

能把这条讲顺，你就掌握了后端状态流转的核心。

## 18. 小练习

试着回答：

1. `POST /api/dispatches` 为什么只需要 `job_id` 和 `crew_id`？
2. 新建派遣的初始状态是什么？
3. 船东确认后，船员状态会变成什么？
4. 哪一步会新增 `voyage_records`？
5. 下船时会改哪些表？
6. `dispatch_status_logs` 和 `operation_logs` 有什么区别？
7. 为什么一条派遣最多只能生成一条海历？

标准答案：

```text
1. 因为船舶、航线、岗位来自 job_demands，船员信息来自 crews，派遣只需要关联两者。
2. pending_owner。
3. pending，表示待上船。
4. onboard_dispatch，也就是确认上船时。
5. dispatches、crews、job_demands、voyage_records，并写两种日志。
6. dispatch_status_logs 记录派遣状态变化，operation_logs 记录系统操作审计。
7. voyage_records.dispatch_id 设置了 unique=True，一条派遣只能对应一条海历。
```

学完这一课，你要能做到：老师问“点击确认上船后数据库发生什么”，你可以顺着代码讲出状态变化、涉及表、日志写入和海历生成。
