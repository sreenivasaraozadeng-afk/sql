# 后端逐行精讲 06：统计首页与操作日志

这一课讲最后一条后端主线：统计首页和操作日志。

前几课讲的是“业务流程怎么发生”，这一课讲的是“发生过的业务数据怎么汇总展示”。

你要记住一句话：

```text
统计首页不是前端写死数字，而是后端从 crews、certificates、job_demands、dispatches、voyage_records、ships 等表实时查询和汇总出来的。
```

这节课要能讲清楚 6 个接口：

```text
GET /api/dashboard/summary
GET /api/dashboard/crew-status
GET /api/dashboard/certificate-alerts
GET /api/dashboard/dispatch-trend
GET /api/dashboard/route-workload
GET /api/operation-logs
```

## 1. 为什么统计模块适合答辩

答辩时，老师很可能会问：

```text
你们的首页数据从哪里来？
这些表格是不是写死的？
能不能体现数据库查询？
```

你可以回答：

```text
首页统计全部来自后端接口，后端使用 SQLAlchemy 查询数据库。
比如总船员数来自 crews 表，待审核证书来自 certificates 表，进行中派遣来自 dispatches 表，航线工作量来自 voyage_records 表。
前端只是把接口返回的数据展示成卡片、表格和进度条。
```

这说明你的系统不只是页面好看，而是后端和数据库有真实查询逻辑。

## 2. 相关文件

| 作用 | 文件 | 重点 |
| --- | --- | --- |
| 统计接口入口 | `backend/app/routers/dashboard.py` | 5 个 `/api/dashboard/...` 接口 |
| 日志接口入口 | `backend/app/routers/logs.py` | `/api/operation-logs` |
| 统计业务逻辑 | `backend/app/services.py` | `dashboard_summary` 等函数 |
| 日志业务逻辑 | `backend/app/services.py` | `_add_operation_log`、`list_operation_logs` |
| 日志数据模型 | `backend/app/models.py` | `OperationLog` |

这一课读代码的顺序：

```text
routers/dashboard.py
-> services.dashboard_summary
-> services.dashboard_crew_status
-> services.dashboard_certificate_alerts
-> services.dashboard_dispatch_trend
-> services.dashboard_route_workload
-> routers/logs.py
-> services.list_operation_logs
-> models.OperationLog
```

## 3. dashboard.py：统计接口入口

`backend/app/routers/dashboard.py` 的前缀是：

```python
router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
```

所以这个文件里所有接口都以 `/api/dashboard` 开头。

接口列表：

| 接口 | 作用 | 允许角色 |
| --- | --- | --- |
| `GET /api/dashboard/summary` | 首页统计卡片 | manager、cert_admin、shipowner、admin |
| `GET /api/dashboard/crew-status` | 船员状态分布 | manager、cert_admin、shipowner、admin |
| `GET /api/dashboard/certificate-alerts` | 证书到期预警 | manager、cert_admin、shipowner、admin |
| `GET /api/dashboard/dispatch-trend` | 月度派遣趋势 | manager、shipowner、admin |
| `GET /api/dashboard/route-workload` | 航线工作量排行 | manager、shipowner、admin |

这里有一个细节：

```text
cert_admin 能看证书相关统计，但不能看派遣趋势和航线工作量；
manager、shipowner、admin 可以看派遣和航线统计。
```

这体现了角色权限控制。

## 4. summary：统计卡片接口

接口：

```text
GET /api/dashboard/summary
```

router 代码：

```python
@router.get("/summary")
def summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "shipowner", "admin")),
):
    return {"success": True, "data": services.dashboard_summary(db)}
```

逐行理解：

| 代码 | 意思 |
| --- | --- |
| `@router.get("/summary")` | 注册统计卡片接口 |
| `db: Session = Depends(get_db)` | 注入数据库连接 |
| `require_roles(...)` | 限制可访问角色 |
| `services.dashboard_summary(db)` | 调 service 层查询统计数据 |

真正的统计逻辑在 `dashboard_summary`。

## 5. dashboard_summary：每张统计卡片从哪里来

代码：

```python
def dashboard_summary(db: Session) -> dict:
    total_crews = db.scalar(select(func.count()).select_from(Crew).where(Crew.status != "inactive")) or 0
    at_sea = db.scalar(select(func.count()).select_from(Crew).where(Crew.status == "at_sea")) or 0
    available = db.scalar(select(func.count()).select_from(Crew).where(Crew.status == "available")) or 0
    pending_reviews = (
        db.scalar(select(func.count()).select_from(Certificate).where(Certificate.review_status == "pending")) or 0
    )
    certificate_alert_count = len(list_certificate_alerts(db))
    open_jobs = db.scalar(select(func.count()).select_from(JobDemand).where(JobDemand.status == "open")) or 0
    active_dispatches = (
        db.scalar(
            select(func.count())
            .select_from(Dispatch)
            .where(Dispatch.status.in_(["pending_owner", "confirmed", "onboard"]))
        )
        or 0
    )
    total_ships = db.scalar(select(func.count()).select_from(Ship).where(Ship.status != "inactive")) or 0
    return {
        "total_crews": total_crews,
        "available_crews": available,
        "at_sea_crews": at_sea,
        "pending_certificate_reviews": pending_reviews,
        "certificate_alerts": certificate_alert_count,
        "open_jobs": open_jobs,
        "active_dispatches": active_dispatches,
        "total_ships": total_ships,
    }
```

这个函数就是“首页统计卡片”的来源。

逐项拆开：

| 返回字段 | 查询来源 | 含义 |
| --- | --- | --- |
| `total_crews` | `crews.status != inactive` | 总有效船员数 |
| `available_crews` | `crews.status == available` | 在岸可派遣船员 |
| `at_sea_crews` | `crews.status == at_sea` | 出海中船员 |
| `pending_certificate_reviews` | `certificates.review_status == pending` | 待审核证书数量 |
| `certificate_alerts` | `list_certificate_alerts(db)` | 30 天内到期证书数量 |
| `open_jobs` | `job_demands.status == open` | 开放中的岗位需求 |
| `active_dispatches` | `dispatches.status in (...)` | 进行中的派遣 |
| `total_ships` | `ships.status != inactive` | 有效船舶数量 |

这段代码里反复出现：

```python
select(func.count()).select_from(...)
```

它的意思是：

```text
从某张表里统计符合条件的记录数量。
```

比如：

```python
select(func.count()).select_from(Crew).where(Crew.status == "available")
```

可以翻译成：

```text
统计 crews 表中 status 等于 available 的记录数。
```

这就是 SQL 聚合查询。

## 6. crew-status：船员状态分布

接口：

```text
GET /api/dashboard/crew-status
```

router：

```python
@router.get("/crew-status")
def crew_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "shipowner", "admin")),
):
    return {"success": True, "data": services.dashboard_crew_status(db)}
```

service：

```python
def dashboard_crew_status(db: Session) -> list[dict]:
    label_map = {
        "available": "在岸可派遣",
        "pending": "待上船",
        "at_sea": "出海中",
        "inactive": "已停用",
    }
    crews = db.scalars(select(Crew)).all()
    counter = Counter(crew.status for crew in crews)
    return [
        {"status": status, "label": label_map[status], "count": counter.get(status, 0)}
        for status in ["available", "pending", "at_sea", "inactive"]
    ]
```

这个接口返回的是一个列表：

```json
[
  {"status": "available", "label": "在岸可派遣", "count": 6},
  {"status": "pending", "label": "待上船", "count": 1},
  {"status": "at_sea", "label": "出海中", "count": 1},
  {"status": "inactive", "label": "已停用", "count": 0}
]
```

逐行理解：

| 代码 | 意思 |
| --- | --- |
| `label_map` | 把英文状态转成中文展示 |
| `select(Crew)` | 查询所有船员 |
| `Counter(crew.status for crew in crews)` | 按船员状态计数 |
| `counter.get(status, 0)` | 如果某状态没有记录，就返回 0 |

为什么要返回 0？

```text
因为前端表格或进度条需要固定显示所有状态。
即使当前没有出海中船员，也应该显示 “出海中 0”。
```

这就是后端为前端展示做的数据整理。

## 7. certificate-alerts：证书到期预警

接口：

```text
GET /api/dashboard/certificate-alerts
```

router：

```python
@router.get("/certificate-alerts")
def certificate_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "cert_admin", "shipowner", "admin")),
):
    return {"success": True, "data": services.dashboard_certificate_alerts(db)}
```

service：

```python
def dashboard_certificate_alerts(db: Session) -> list[dict]:
    return list_certificate_alerts(db)
```

它复用了 `list_certificate_alerts`：

```python
def list_certificate_alerts(db: Session) -> list[dict]:
    today = datetime.now(UTC).date()
    deadline = today + timedelta(days=30)
    certificates = db.scalars(
        select(Certificate)
        .options(joinedload(Certificate.crew))
        .where(
            Certificate.review_status.in_(["pending", "approved"]),
            Certificate.expires_at >= today,
            Certificate.expires_at <= deadline,
        )
        .order_by(Certificate.expires_at)
    ).all()
    return [certificate_to_dict(certificate) for certificate in certificates]
```

这段查询的条件是：

```text
证书状态是 pending 或 approved；
证书还没有过期；
证书会在 30 天内到期。
```

为什么不包含 `rejected`？

```text
rejected 已经是审核拒绝证书，不需要作为可用证书预警。
```

为什么要 `joinedload(Certificate.crew)`？

```text
前端显示证书预警时，不只要证书编号，还要显示哪个船员的证书快到期。
```

这说明统计接口不是单表孤立查询，也会关联船员信息。

## 8. dispatch-trend：月度派遣趋势

接口：

```text
GET /api/dashboard/dispatch-trend
```

service：

```python
def dashboard_dispatch_trend(db: Session) -> list[dict]:
    dispatches = db.scalars(select(Dispatch).order_by(Dispatch.created_at)).all()
    counter: dict[str, int] = defaultdict(int)
    for dispatch in dispatches:
        counter[dispatch.created_at.strftime("%Y-%m")] += 1
    return [{"month": month, "count": counter[month]} for month in sorted(counter)]
```

这个接口统计：

```text
每个月创建了多少条派遣记录。
```

核心字段是：

```text
dispatches.created_at
```

代码里的：

```python
dispatch.created_at.strftime("%Y-%m")
```

会把具体时间变成月份，比如：

```text
2026-05-30 12:00:00 -> 2026-05
```

然后用 `defaultdict(int)` 计数。

返回结果像这样：

```json
[
  {"month": "2026-04", "count": 2},
  {"month": "2026-05", "count": 5}
]
```

前端可以用这个数据做月度趋势表或简单柱状条。

## 9. route-workload：航线工作量排行

接口：

```text
GET /api/dashboard/route-workload
```

service：

```python
def dashboard_route_workload(db: Session) -> list[dict]:
    voyages = db.scalars(select(VoyageRecord)).all()
    counter: dict[str, int] = defaultdict(int)
    onboard_counter: dict[str, int] = defaultdict(int)
    for voyage in voyages:
        counter[voyage.route] += 1
        if voyage.status == "onboard":
            onboard_counter[voyage.route] += 1
    if not counter:
        jobs = db.scalars(select(JobDemand)).all()
        for job in jobs:
            counter[job.route] += 0
    return [
        {
            "route": route,
            "voyage_count": counter[route],
            "onboard_count": onboard_counter.get(route, 0),
        }
        for route in sorted(counter, key=lambda item: counter[item], reverse=True)
    ]
```

这个接口主要查：

```text
voyage_records
```

它统计每条航线：

| 字段 | 含义 |
| --- | --- |
| `route` | 航线 |
| `voyage_count` | 这条航线累计海历数 |
| `onboard_count` | 当前仍在船上的数量 |

为什么用 `voyage_records` 而不是直接用 `routes`？

```text
因为航线工作量关注的是实际发生过多少次出海经历。
海历表代表真实执行记录，所以用 voyage_records 更合适。
```

这里还有一个小设计：

```python
if not counter:
    jobs = db.scalars(select(JobDemand)).all()
    for job in jobs:
        counter[job.route] += 0
```

意思是：

```text
如果还没有任何海历，也从岗位需求里拿航线，让前端表格不要完全空白。
```

这对演示很友好。

## 10. logs.py：操作日志接口入口

日志接口在 `backend/app/routers/logs.py`：

```python
router = APIRouter(prefix="/api/operation-logs", tags=["operation-logs"])
```

完整接口：

```text
GET /api/operation-logs
```

router：

```python
@router.get("")
def list_operation_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {"success": True, "data": services.list_operation_logs(db)}
```

只有：

```text
manager
admin
```

可以查看操作日志。

原因是操作日志属于管理和审计信息，不应该让普通船员或船东随便查看。

## 11. _add_operation_log：日志是怎么写进去的

在 `backend/app/services.py` 里：

```python
def _add_operation_log(
    db: Session,
    user: User | None,
    action: str,
    target_type: str,
    target_id: int | None,
    detail: str | None = None,
) -> None:
    db.add(
        OperationLog(
            user_id=user.id if user is not None else None,
            username=user.username if user is not None else None,
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )
```

这个函数不是接口，它是内部工具函数。

很多业务函数会调用它，比如：

```text
创建船员
创建证书
审核证书
创建岗位
创建派遣
确认派遣
上船
下船
取消派遣
```

它会保存：

| 字段 | 含义 |
| --- | --- |
| `user_id` | 操作人 ID |
| `username` | 操作人账号 |
| `action` | 操作类型，比如 create、review、confirm |
| `target_type` | 操作对象类型，比如 crew、certificate、dispatch |
| `target_id` | 操作对象 ID |
| `detail` | 详情说明 |

答辩时可以说：

```text
我们把关键业务操作统一写入 operation_logs，方便管理员查看最近系统行为，也方便追踪是谁做了什么操作。
```

## 12. list_operation_logs：最近操作日志怎么查

service：

```python
def list_operation_logs(db: Session, limit: int = 100) -> list[dict]:
    logs = db.scalars(
        select(OperationLog).order_by(OperationLog.id.desc()).limit(limit)
    ).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "detail": log.detail,
            "created_at": log.created_at,
        }
        for log in logs
    ]
```

逐行理解：

| 代码 | 意思 |
| --- | --- |
| `select(OperationLog)` | 查询操作日志表 |
| `order_by(OperationLog.id.desc())` | 最新日志排在前面 |
| `limit(limit)` | 默认只取最近 100 条，避免一次返回太多 |
| `return [...]` | 转成前端能直接展示的字典列表 |

为什么按 `id.desc()` 排？

```text
日志 ID 越大通常越新，按倒序可以让管理员先看到最近发生的操作。
```

## 13. OperationLog 表结构

`OperationLog` 在 `backend/app/models.py`：

```python
class OperationLog(Base):
    __tablename__ = "operation_logs"
    __table_args__ = (
        Index("idx_operation_logs_user_id", "user_id"),
        Index("idx_operation_logs_action", "action"),
        Index("idx_operation_logs_target", "target_type", "target_id"),
        Index("idx_operation_logs_created_at", "created_at"),
    )
```

这里建了多个索引：

| 索引 | 作用 |
| --- | --- |
| `idx_operation_logs_user_id` | 按操作人查询更快 |
| `idx_operation_logs_action` | 按操作类型查询更快 |
| `idx_operation_logs_target` | 按操作对象查询更快 |
| `idx_operation_logs_created_at` | 按时间查询或排序更快 |

字段：

```python
id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
username: Mapped[str | None] = mapped_column(String(50))
action: Mapped[str] = mapped_column(String(50), nullable=False)
target_type: Mapped[str] = mapped_column(String(50), nullable=False)
target_id: Mapped[int | None] = mapped_column(Integer)
detail: Mapped[str | None] = mapped_column(Text)
created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
```

注意：

```text
user_id 是外键，关联 users.id；
username 也冗余保存一份，方便日志展示；
created_at 使用数据库默认时间。
```

为什么日志里既有 `user_id` 又有 `username`？

```text
user_id 适合关联查询；
username 适合直接展示。
即使以后用户显示名变化，日志里也保留当时操作账号的信息。
```

## 14. operation_logs 和 dispatch_status_logs 的区别

这是老师很可能追问的问题。

| 表 | 记录什么 | 例子 |
| --- | --- | --- |
| `operation_logs` | 用户做了什么操作 | manager 创建派遣、cert_admin 审核证书 |
| `dispatch_status_logs` | 某条派遣状态怎么变化 | pending_owner -> confirmed |

可以这样答：

```text
operation_logs 是系统级操作审计，覆盖船员、证书、岗位、派遣等多种对象；
dispatch_status_logs 是派遣业务专用日志，只记录派遣状态流转。
```

两者不是重复，而是粒度不同。

## 15. 五个统计接口和表的对应关系

| 接口 | 主要表 | 统计内容 |
| --- | --- | --- |
| `/api/dashboard/summary` | `crews`、`certificates`、`job_demands`、`dispatches`、`ships` | 首页卡片 |
| `/api/dashboard/crew-status` | `crews` | 船员状态分布 |
| `/api/dashboard/certificate-alerts` | `certificates`、`crews` | 证书到期预警 |
| `/api/dashboard/dispatch-trend` | `dispatches` | 按月统计派遣数量 |
| `/api/dashboard/route-workload` | `voyage_records`、`job_demands` | 航线工作量 |
| `/api/operation-logs` | `operation_logs` | 最近系统操作 |

这张表很适合背。

老师问“首页统计数据从哪些表查出来”，你就按这张表讲。

## 16. 统计接口为什么不直接查视图

项目里有数据库视图用于报告和展示，但后端统计接口这里主要用 SQLAlchemy 查询。

可以这样解释：

```text
数据库视图适合课程报告展示复杂查询结果；
后端接口用 SQLAlchemy 查询，方便根据业务权限、参数和页面需要动态组织返回数据。
两者并不冲突。
```

如果老师问“为什么有的统计在后端算”，可以回答：

```text
因为前端只负责展示，统计规则应该放在后端，避免前端重复写业务逻辑，也能统一权限控制。
```

## 17. 亲手跑一遍

启动后端：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork\backend
python run_sqlite.py
```

打开接口文档：

```text
http://127.0.0.1:3000/docs
```

建议按顺序试：

```text
1. 登录 admin 或 manager
2. 调用 GET /api/dashboard/summary
3. 调用 GET /api/dashboard/crew-status
4. 调用 GET /api/dashboard/certificate-alerts
5. 调用 GET /api/dashboard/dispatch-trend
6. 调用 GET /api/dashboard/route-workload
7. 调用 GET /api/operation-logs
```

观察返回字段：

```text
summary 里面有哪些统计卡片字段？
crew-status 是否固定返回四种状态？
certificate-alerts 是否包含 crew_name？
dispatch-trend 是否按 month 返回？
route-workload 是否包含 voyage_count 和 onboard_count？
operation-logs 是否按最新操作排在前面？
```

## 18. 这一课必须背下来的主线

```text
前端首页打开后，会调用 /api/dashboard 下的多个统计接口。
router 层负责权限控制和调用 service。
service 层从 crews、certificates、job_demands、dispatches、voyage_records、ships 等表查询数据。
summary 用 count 查询统计卡片；
crew-status 按船员状态计数；
certificate-alerts 查询 30 天内到期的 pending/approved 证书；
dispatch-trend 按 dispatches.created_at 的年月分组；
route-workload 按 voyage_records.route 统计航线工作量；
operation-logs 查询最近 100 条操作日志。
前端只负责展示，统计规则和数据权限都放在后端。
```

能把这条讲顺，你就能回答统计模块的大部分问题。

## 19. 小练习

试着回答：

1. `/api/dashboard/summary` 返回哪些统计字段？
2. 船员状态分布来自哪张表？
3. 证书到期预警为什么要关联船员？
4. 月度派遣趋势按哪个字段统计？
5. 航线工作量为什么主要用 `voyage_records`？
6. `operation_logs` 默认返回最近多少条？
7. `operation_logs` 和 `dispatch_status_logs` 有什么区别？

标准答案：

```text
1. total_crews、available_crews、at_sea_crews、pending_certificate_reviews、certificate_alerts、open_jobs、active_dispatches、total_ships。
2. crews 表，按 crews.status 计数。
3. 因为前端要显示哪个船员的证书快到期，所以用 joinedload 加载 Certificate.crew。
4. dispatches.created_at，格式化成 YYYY-MM 后计数。
5. voyage_records 代表真实出海记录，航线工作量应按实际海历统计。
6. 默认 100 条。
7. operation_logs 是系统级操作审计，dispatch_status_logs 是派遣状态流转日志。
```

学完这一课，你就能把后端 6 条主线串完整：登录、船员、证书、匹配、派遣、统计日志。
