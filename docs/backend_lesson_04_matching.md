# 后端逐行精讲 04：岗位需求与智能匹配

这一课讲系统里最容易拿高分、也最适合答辩展示的模块：岗位需求与智能匹配。

你不要把它理解成“算法很高级”。它真正的价值是：系统不是随便从船员表里挑人，而是根据岗位、证书审核状态、证书有效期、历史海历这些数据库信息，给出一个可解释的匹配分数。

这一课要能讲清楚两条接口：

```text
POST /api/jobs
GET  /api/jobs/{job_id}/matches
```

第一条是船东发布岗位需求，第二条是经理查看系统推荐的匹配船员。

## 1. 先讲业务场景

答辩时可以这样开头：

```text
这个模块模拟的是船东发布用人需求、经理根据系统推荐挑选船员的流程。
船东发布岗位时，需要说明船舶、航线、岗位、所需证书、计划上船时间和人数。
系统保存岗位需求后，经理可以点击智能匹配。
智能匹配会读取可派遣船员，检查岗位是否一致、证书是否已审核并且未过期、证书有效期是否有风险、船员是否有相近海历，然后计算匹配分数并返回原因。
```

这段话的重点是“读取多张表并形成业务判断”，这正是数据库课程设计要强调的地方。

## 2. 这两条接口在哪些文件里

| 作用 | 文件 | 你要重点看什么 |
| --- | --- | --- |
| 岗位接口入口 | `backend/app/routers/jobs.py` | `/api/jobs` 的增查关 |
| 匹配接口入口 | `backend/app/routers/matching.py` | `/api/jobs/{job_id}/matches` |
| 请求参数校验 | `backend/app/schemas.py` | `JobCreate` |
| 业务逻辑 | `backend/app/services.py` | `create_job`、`list_matching_crews`、`_score_match` |
| 数据表模型 | `backend/app/models.py` | `JobDemand`、`JobRequiredCertificate`、`Crew`、`Certificate`、`VoyageRecord` |

你以后看到一个接口，不要慌，固定按这个顺序找：

```text
router 接口入口
-> schema 参数校验
-> service 业务处理
-> model 数据表
-> 返回给前端的数据
```

## 3. 第一条接口：发布岗位需求

接口地址：

```text
POST /api/jobs
```

它在 `backend/app/routers/jobs.py` 里：

```python
@router.post("")
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("shipowner", "admin")),
):
    return {
        "success": True,
        "message": "岗位发布成功",
        "data": services.create_job(db, payload, current_user),
    }
```

逐行理解：

| 代码 | 意思 |
| --- | --- |
| `@router.post("")` | 注册 POST 接口，因为 router 前缀是 `/api/jobs`，所以完整地址是 `/api/jobs` |
| `payload: JobCreate` | 前端传来的岗位数据要先经过 `JobCreate` 校验 |
| `db: Session = Depends(get_db)` | FastAPI 自动给这个接口传入数据库连接 |
| `current_user = Depends(require_roles(...))` | 只有 `shipowner` 和 `admin` 能发布岗位 |
| `services.create_job(...)` | 真正创建岗位的逻辑交给 service 层 |

你可以这样回答老师：

```text
router 层不直接写复杂 SQL，它只负责接收请求、做权限入口、调用 service。
这样分层后，接口入口很清楚，业务规则集中在 services.py 里。
```

## 4. JobCreate：发布岗位时前端要传什么

`JobCreate` 在 `backend/app/schemas.py`：

```python
class JobCreate(BaseModel):
    title: str
    ship_name: str | None = None
    ship_id: int | None = None
    route: str | None = None
    route_id: int | None = None
    required_position: str | None = None
    position_id: int | None = None
    required_certificates: list[str] = Field(default_factory=list)
    required_certificate_type_ids: list[int] = Field(default_factory=list)
    headcount: int = 1
    onboard_at: datetime
```

这里有一个很重要的设计：系统同时支持“传中文名称”和“传字典表 ID”。

比如岗位可以传：

```json
{
  "required_position": "二副"
}
```

也可以传：

```json
{
  "position_id": 2
}
```

为什么要这样设计？

```text
数据库里使用 position_id、ship_id、route_id 这种外键关系，结构更规范。
但前端页面和答辩演示时仍然返回中文名称，方便同学和老师理解。
```

`JobCreate` 里还有几个校验点：

| 校验 | 作用 |
| --- | --- |
| `validate_title` | 岗位标题不能为空，长度不能超过 100 |
| `normalize_ship_name` | 去掉船舶名称前后空格，空字符串转成 None |
| `normalize_route` | 去掉航线前后空格 |
| `normalize_required_position` | 去掉岗位名称前后空格 |
| `validate_required_certificates` | 没传证书时使用空列表，避免后面遍历时报错 |
| `validate_headcount` | 招聘人数不能小于 1 |

这部分是后端的第一层保护：前端传错数据时，后端不会直接写入数据库。

## 5. create_job：岗位需求怎么写入数据库

`create_job` 在 `backend/app/services.py`。它做五件事：

```text
1. 确认船舶
2. 确认航线
3. 确认岗位
4. 保存岗位主表 job_demands
5. 保存岗位所需证书子表 job_required_certificates
```

### 5.1 确认船舶

```python
ship_id = payload.ship_id
ship_name = payload.ship_name
if ship_id is not None:
    ship = db.get(Ship, ship_id)
    if ship is None:
        raise ApiError(404, "船舶不存在")
    ship_name = ship.name
if not ship_name:
    raise ApiError(400, "船舶不能为空")
```

逐行理解：

| 代码 | 意思 |
| --- | --- |
| `ship_id = payload.ship_id` | 先取出前端传来的船舶 ID |
| `ship_name = payload.ship_name` | 同时也允许前端直接传船舶名称 |
| `if ship_id is not None` | 如果传了 ID，就优先按 ID 查船舶表 |
| `db.get(Ship, ship_id)` | 根据主键去 `ships` 表找这艘船 |
| `ship is None` | 没找到就抛 404 |
| `ship_name = ship.name` | 查到后使用数据库里的标准船名 |
| `if not ship_name` | 如果既没传 ID，也没传名称，就说明岗位信息不完整 |

这体现了数据库实体表的作用：船舶不是普通字符串，而是 `ships` 表里的正式记录。

### 5.2 确认航线

```python
route_id = payload.route_id
route_name = payload.route
if route_id is not None:
    route = db.get(Route, route_id)
    if route is None:
        raise ApiError(404, "航线不存在")
    route_name = _route_label(route)
if not route_name:
    raise ApiError(400, "航线不能为空")
```

这里和船舶类似：

```text
如果传 route_id，就去 routes 表查正式航线；
如果只传中文 route，也可以保存；
最后要求 route_name 必须存在。
```

`_route_label(route)` 的作用是把航线对象转成前端好懂的中文显示，比如：

```text
上海港 -> 新加坡港
```

### 5.3 确认岗位

```python
position_id, position_name = _get_position_name(
    db,
    payload.position_id,
    payload.required_position,
)
```

这一行做了“岗位字典表转换”。

如果前端传 `position_id`，后端去 `positions` 表查岗位名称；如果传 `required_position`，后端用中文名称。最后统一得到：

```text
position_id
position_name
```

数据库里保存两份信息是为了兼顾：

| 字段 | 作用 |
| --- | --- |
| `position_id` | 规范外键，方便数据库关联 |
| `required_position` | 中文快照，方便展示和历史记录 |

### 5.4 写入岗位主表 job_demands

```python
job = JobDemand(
    owner_user_id=owner.id,
    ship_id=ship_id,
    route_id=route_id,
    position_id=position_id,
    title=payload.title,
    ship_name=ship_name,
    route=route_name,
    required_position=position_name,
    headcount=payload.headcount,
    onboard_at=payload.onboard_at,
    status="open",
)
```

这对应数据库表 `job_demands`。

它保存的是一个岗位需求的主信息：

| 字段 | 含义 |
| --- | --- |
| `owner_user_id` | 哪个船东发布的需求 |
| `ship_id` / `ship_name` | 对应船舶 |
| `route_id` / `route` | 对应航线 |
| `position_id` / `required_position` | 需要什么岗位 |
| `headcount` | 招几个人 |
| `onboard_at` | 计划上船时间 |
| `status` | 需求状态，默认 `open` |

注意：岗位需求是主表，但“所需证书”没有直接放在一个字符串字段里。

原因是一个岗位可能需要多个证书，比如：

```text
船长证书
GMDSS 证书
高级消防证书
```

如果把它们塞进一个字符串字段，后面查询、统计、约束都会很麻烦。所以系统设计了一张子表：`job_required_certificates`。

### 5.5 写入岗位所需证书子表

```python
required_names = list(dict.fromkeys(payload.required_certificates))
for cert_type_id in dict.fromkeys(payload.required_certificate_type_ids):
    type_id, type_name = _get_certificate_type_name(db, cert_type_id, None)
    required_names.append(type_name)
for certificate_type in dict.fromkeys(required_names):
    type_id, type_name = _get_certificate_type_name(db, None, certificate_type)
    job.required_certificates.append(
        JobRequiredCertificate(
            certificate_type_id=type_id,
            certificate_type=type_name,
        )
    )
```

逐行理解：

| 代码 | 意思 |
| --- | --- |
| `dict.fromkeys(...)` | 去重，避免同一种证书重复保存 |
| `required_certificate_type_ids` | 如果前端传证书类型 ID，就去 `certificate_types` 表查 |
| `_get_certificate_type_name` | 把 ID 或名称统一转成证书类型名称 |
| `job.required_certificates.append(...)` | 给这个岗位添加一条“所需证书”记录 |

这里体现的是一对多关系：

```text
一个岗位需求 JobDemand
可以对应多条 JobRequiredCertificate
```

用数据库语言讲就是：

```text
job_demands.id = job_required_certificates.job_id
```

这就是数据库设计里非常重要的“主表 + 明细表”。

### 5.6 提交事务和写操作日志

```python
db.add(job)
db.flush()
_add_operation_log(db, owner, "create", "job", job.id, job.title)
db.commit()
db.refresh(job)
return job_to_dict(job)
```

逐行理解：

| 代码 | 意思 |
| --- | --- |
| `db.add(job)` | 把岗位对象加入数据库会话 |
| `db.flush()` | 先让数据库生成 `job.id`，但还没最终提交 |
| `_add_operation_log(...)` | 写入操作日志，记录谁创建了岗位 |
| `db.commit()` | 提交事务，岗位和证书要求正式入库 |
| `db.refresh(job)` | 从数据库重新读取最新对象 |
| `job_to_dict(job)` | 转成前端能直接用的字典 |

这里可以向老师强调：

```text
我们不只保存业务数据，也记录关键操作日志，便于审计和答辩展示。
```

## 6. job_to_dict：为什么前端不用理解复杂 ID

`job_to_dict` 在 `backend/app/services.py`：

```python
def job_to_dict(job: JobDemand) -> dict:
    return {
        "id": job.id,
        "owner_user_id": job.owner_user_id,
        "ship_id": job.ship_id,
        "route_id": job.route_id,
        "position_id": job.position_id,
        "title": job.title,
        "ship_name": job.ship_name,
        "route": job.route,
        "required_position": job.required_position,
        "required_certificates": [
            item.certificate_type for item in job.required_certificates
        ],
        "headcount": job.headcount,
        "onboard_at": job.onboard_at,
        "status": job.status,
    }
```

注意返回值里既有 ID，也有中文名称：

```text
ship_id、route_id、position_id：方便后续编辑或关联
ship_name、route、required_position：方便前端直接显示
required_certificates：把子表里的多条证书记录整理成列表
```

这就是“数据库设计复杂，前端展示简单”的思想。

## 7. 第二条接口：智能匹配

接口地址：

```text
GET /api/jobs/{job_id}/matches
```

它在 `backend/app/routers/matching.py`：

```python
@router.get("/{job_id}/matches")
def match_crews(
    job_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("manager", "admin")),
):
    return {"success": True, "data": services.list_matching_crews(db, job_id)}
```

逐行理解：

| 代码 | 意思 |
| --- | --- |
| `@router.get("/{job_id}/matches")` | 注册匹配接口，完整地址是 `/api/jobs/岗位ID/matches` |
| `job_id: int` | 从 URL 里拿岗位 ID |
| `require_roles("manager", "admin")` | 只有经理和管理员能看匹配结果 |
| `services.list_matching_crews(db, job_id)` | 调用 service 层计算匹配船员 |

这里的权限设计也能答辩：

```text
船东负责发布需求，经理负责调度匹配，所以匹配接口只开放给 manager 和 admin。
```

## 8. list_matching_crews：匹配接口主流程

`list_matching_crews` 在 `backend/app/services.py`：

```python
def list_matching_crews(db: Session, job_id: int) -> list[dict]:
    job = _get_job_or_404(db, job_id)
    today = datetime.now(UTC).date()
    crews = db.scalars(
        select(Crew)
        .options(
            joinedload(Crew.user),
            joinedload(Crew.certificates),
            selectinload(Crew.voyages),
        )
        .where(Crew.status == "available")
        .order_by(Crew.id)
    ).unique().all()
    scored = [_score_match(crew, job, today) for crew in crews]
    return sorted(
        [item for item in scored if item["match_score"] >= 60],
        key=lambda item: item["match_score"],
        reverse=True,
    )
```

这个函数可以分成 5 步：

### 8.1 查岗位

```python
job = _get_job_or_404(db, job_id)
```

根据 URL 里的 `job_id` 找岗位。如果岗位不存在，就返回 404。

### 8.2 取得今天日期

```python
today = datetime.now(UTC).date()
```

为什么要今天日期？

因为证书有效期要和当前日期比较：

```text
证书过期了，不能参与匹配。
证书快过期了，可以匹配，但要降低风险分。
```

### 8.3 查询可派遣船员

```python
select(Crew)
.options(
    joinedload(Crew.user),
    joinedload(Crew.certificates),
    selectinload(Crew.voyages),
)
.where(Crew.status == "available")
```

这里非常适合讲数据库查询优化：

| 代码 | 含义 |
| --- | --- |
| `select(Crew)` | 查询船员表 |
| `joinedload(Crew.user)` | 顺带加载对应用户信息 |
| `joinedload(Crew.certificates)` | 顺带加载船员证书 |
| `selectinload(Crew.voyages)` | 顺带加载船员海历 |
| `Crew.status == "available"` | 只匹配当前可派遣的船员 |

为什么要加载证书和海历？

```text
因为匹配分数不是只看船员姓名，而是要看证书是否满足、证书是否过期、有没有相似岗位或航线海历。
```

### 8.4 给每个船员打分

```python
scored = [_score_match(crew, job, today) for crew in crews]
```

每个可派遣船员都会进入 `_score_match`。

### 8.5 过滤和排序

```python
return sorted(
    [item for item in scored if item["match_score"] >= 60],
    key=lambda item: item["match_score"],
    reverse=True,
)
```

规则是：

```text
低于 60 分的不推荐；
60 分及以上才返回给前端；
分数越高排在越前面。
```

这让前端页面很容易做“推荐列表”。

## 9. _score_match：100 分匹配模型

`_score_match` 是这个模块最核心的函数。

总分 100 分，由四部分组成：

| 维度 | 分值 | 说明 |
| --- | ---: | --- |
| 岗位匹配 | 40 分 | 船员岗位和需求岗位一致 |
| 证书满足度 | 40 分 | 所需证书满足得越多，分越高 |
| 证书有效期风险 | 10 分 | 证书有效期越充足，风险分越高 |
| 历史海历经验 | 10 分 | 有相近岗位或航线海历加分 |

答辩时不要说“AI 算法”，可以说：

```text
这是一个可解释的规则评分模型。
它不追求复杂机器学习，而是让老师能看清楚每一分来自哪张表、哪个字段和哪条业务规则。
```

### 9.1 先取出岗位要求的证书

```python
required_certificates = [item.certificate_type for item in job.required_certificates]
score = 0
reasons: list[str] = []
```

`job.required_certificates` 来自子表 `job_required_certificates`。

这里把多条证书要求整理成一个列表，比如：

```text
["船长适任证书", "GMDSS 证书", "高级消防证书"]
```

`reasons` 是匹配原因列表，前端可以直接显示：

```text
岗位完全匹配
所需证书齐全且已审核
证书有效期充足
有相近岗位或航线海历
```

这就是“可解释匹配”。

### 9.2 岗位匹配：40 分

```python
if crew.position == job.required_position:
    score += 40
    reasons.append("岗位完全匹配")
else:
    reasons.append("岗位不匹配")
```

这一步比较：

```text
crews.position
job_demands.required_position
```

如果船员岗位等于岗位需求，直接加 40 分。

注意：岗位不匹配并不是立刻淘汰，而是不给这 40 分。这样做的好处是老师能看到系统是评分推荐，不是简单 yes/no。

不过后面真正创建派遣时，后端还会二次校验岗位必须满足。也就是说，推荐阶段可以评分展示，派遣阶段必须严格保证。

### 9.3 只统计“已审核且未过期”的证书

```python
def _valid_certificate_types(crew: Crew, today: date) -> set[str]:
    return {
        certificate.certificate_type
        for certificate in crew.certificates
        if certificate.review_status == "approved" and certificate.expires_at >= today
    }
```

这段很重要：

```text
pending 未审核证书不能算；
rejected 审核拒绝证书不能算；
过期证书不能算；
只有 approved 且 expires_at >= today 的证书才参与匹配。
```

这能把“证书审核模块”和“智能匹配模块”连接起来。

答辩时可以说：

```text
证书审核不是孤立功能，它会影响后续岗位匹配。
这体现了系统不同业务模块之间的数据联动。
```

### 9.4 证书满足度：40 分

```python
valid_types = _valid_certificate_types(crew, today)
missing = [item for item in required_certificates if item not in valid_types]
if required_certificates:
    cert_score = int(40 * (len(required_certificates) - len(missing)) / len(required_certificates))
else:
    cert_score = 40
score += cert_score
```

这段的计算公式是：

```text
证书分 = 40 * 已满足证书数量 / 岗位要求证书总数
```

举例：

```text
岗位要求 4 个证书，船员满足 3 个：
证书分 = 40 * 3 / 4 = 30 分
```

如果岗位没有强制证书要求，则直接给 40 分。

然后记录原因：

```python
if not missing:
    reasons.append("所需证书齐全且已审核")
else:
    reasons.append("缺少证书：" + "、".join(missing))
```

如果缺证书，前端不会只显示“分数低”，而会显示缺什么证书。

这对老师来说很有说服力，因为它不是黑盒推荐。

### 9.5 证书有效期风险：10 分

```python
valid_required = [
    certificate
    for certificate in crew.certificates
    if certificate.certificate_type in required_certificates
    and certificate.review_status == "approved"
    and certificate.expires_at >= today
]
days_to_expire = [
    (certificate.expires_at - today).days for certificate in valid_required
]
```

这一步只看岗位要求的证书，并计算这些证书离过期还有多少天。

后面按风险加分：

```python
if not required_certificates:
    score += 10
    certificate_risk = "无强制证书要求"
elif days_to_expire and min(days_to_expire) >= 180:
    score += 10
    certificate_risk = "证书有效期充足"
elif days_to_expire and min(days_to_expire) >= 30:
    score += 6
    certificate_risk = "证书半年内需关注"
elif days_to_expire:
    score += 2
    certificate_risk = "证书临近到期"
else:
    certificate_risk = "证书不可用"
```

你可以这样讲：

```text
系统不只是判断证书有没有，还会判断证书剩余有效期。
如果证书还有 180 天以上，说明风险低，给满 10 分；
如果 30 到 180 天，说明需要关注，给 6 分；
如果 30 天内到期，风险高，只给 2 分；
如果没有可用证书，不给风险分。
```

这部分对应数据库字段：

```text
certificates.review_status
certificates.expires_at
```

### 9.6 历史海历经验：10 分

```python
has_similar_voyage = any(
    voyage.position == job.required_position or voyage.route == job.route
    for voyage in crew.voyages
)
if has_similar_voyage:
    score += 10
    reasons.append("有相近岗位或航线海历")
else:
    reasons.append("暂无相近海历")
```

这一步读取的是 `voyage_records` 表。

如果船员过去做过相同岗位，或者跑过相同航线，就加 10 分。

这体现了海历表不是摆设，而是会影响调度决策。

答辩时可以说：

```text
voyage_records 不只是记录历史，它还被智能匹配复用，用来判断船员经验是否贴近当前岗位需求。
```

### 9.7 返回匹配结果

```python
data = crew_to_dict(crew)
data.update(
    {
        "match_score": min(score, 100),
        "match_reasons": reasons,
        "missing_certificates": missing,
        "certificate_risk": certificate_risk,
    }
)
return data
```

返回给前端的数据包括：

| 字段 | 含义 |
| --- | --- |
| `match_score` | 匹配分数，最高 100 |
| `match_reasons` | 为什么推荐或为什么扣分 |
| `missing_certificates` | 缺少哪些证书 |
| `certificate_risk` | 证书有效期风险提示 |

前端可以把这些字段展示成表格、进度条、标签。

## 10. 派遣时为什么还要二次校验

匹配接口只是“推荐”，真正创建派遣时还要调用 `_ensure_crew_matches_job`：

```python
def _ensure_crew_matches_job(db: Session, crew: Crew, job: JobDemand) -> None:
    if crew.status != "available":
        raise ApiError(400, "该船员当前不可派遣")
    if crew.position != job.required_position:
        raise ApiError(400, "船员岗位不满足岗位需求")
    ...
    if not _crew_has_valid_certificates(...):
        raise ApiError(400, "船员证书未审核、已过期或不满足岗位需求")
```

为什么要这样？

```text
因为前端展示结果不能代替后端校验。
就算有人绕过前端，直接请求创建派遣，后端也会再次检查船员状态、岗位和证书。
```

这是一个很好的加分点：

```text
推荐阶段用于排序和解释；
派遣阶段用于强约束和保证数据正确。
```

## 11. 这个模块涉及哪些数据库表

| 表 | 作用 | 在匹配里怎么用 |
| --- | --- | --- |
| `job_demands` | 岗位需求主表 | 保存船舶、航线、岗位、人数、上船时间 |
| `job_required_certificates` | 岗位所需证书明细表 | 一个岗位可以要求多个证书 |
| `crews` | 船员表 | 查询可派遣船员、岗位、状态 |
| `certificates` | 船员证书表 | 判断证书是否 approved、是否过期 |
| `certificate_types` | 证书类型字典表 | 规范证书名称 |
| `positions` | 岗位字典表 | 规范岗位名称 |
| `ships` | 船舶表 | 岗位需求关联具体船舶 |
| `routes` | 航线表 | 岗位需求关联具体航线 |
| `voyage_records` | 海历表 | 判断是否有相近岗位或航线经验 |
| `operation_logs` | 操作日志表 | 记录创建岗位等关键操作 |

这张表你一定要记住，因为答辩老师很可能问：

```text
你这个智能匹配到底用了哪些表？
```

你可以回答：

```text
核心是 job_demands 和 job_required_certificates 表描述岗位需求；
crews 表提供可派遣船员；
certificates 和 certificate_types 判断证书满足度；
voyage_records 判断历史经验；
ships、routes、positions 是实体表或字典表，用来规范船舶、航线和岗位；
operation_logs 记录发布岗位等关键操作。
```

## 12. 为什么所需证书要单独建表

这是数据库设计高频问题。

错误做法：

```text
在 job_demands 表里放一个字段 required_certificates = "船长证书,GMDSS证书,高级消防证书"
```

这样会有问题：

| 问题 | 说明 |
| --- | --- |
| 不符合规范化 | 一个字段里塞了多个值 |
| 查询困难 | 想查“哪些岗位需要 GMDSS”很麻烦 |
| 约束困难 | 数据库无法对每个证书单独加外键 |
| 统计困难 | 统计热门证书需求时要拆字符串 |

正确做法：

```text
job_demands 保存岗位主信息；
job_required_certificates 每一行保存一个岗位需要的一种证书。
```

关系是：

```text
job_demands 1 ---- N job_required_certificates
```

这就是数据库规范化设计。

## 13. 老师可能怎么追问

### 问：你这个智能匹配是不是只是前端写死的？

答：

```text
不是。前端只负责展示，真正的匹配逻辑在后端 services.py 的 list_matching_crews 和 _score_match。
后端会从数据库查询岗位需求、船员、证书和海历，再计算 match_score。
```

### 问：证书没有审核能不能参与匹配？

答：

```text
不能。_valid_certificate_types 只会统计 review_status 等于 approved 且 expires_at 没过期的证书。
pending、rejected、已过期证书都不会算作有效证书。
```

### 问：为什么低于 60 分不返回？

答：

```text
这是为了让推荐结果更有业务意义。系统会给每个可派遣船员打分，但只把 60 分以上的船员返回给经理，避免推荐明显不合适的人。
```

### 问：岗位不匹配的人会不会被派遣？

答：

```text
不会。匹配接口是推荐阶段，可能给出较低分；真正创建派遣时，后端还会调用 _ensure_crew_matches_job 二次校验。
如果岗位不满足、证书未审核、证书过期或船员不可派遣，后端会拒绝创建派遣。
```

### 问：海历表在这里有什么用？

答：

```text
voyage_records 会记录船员历史上船岗位和航线。智能匹配时，如果船员做过相同岗位或跑过相同航线，就说明经验更贴近当前需求，系统会加 10 分。
```

### 问：为什么要有 ID 又要有中文名称？

答：

```text
ID 用于数据库外键关联，保证数据规范；中文名称用于页面展示和历史快照。
这样既能体现数据库设计，又能让前端和答辩展示更容易理解。
```

## 14. 你要亲手跑一遍

先启动后端：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork\backend
python run_sqlite.py
```

打开接口文档：

```text
http://127.0.0.1:3000/docs
```

建议按这个顺序试：

```text
1. 登录 admin 或 shipowner
2. 调用 GET /api/jobs 看已有岗位
3. 调用 POST /api/jobs 新增一个岗位
4. 登录 manager 或 admin
5. 调用 GET /api/jobs/{job_id}/matches 查看匹配结果
6. 观察 match_score、match_reasons、missing_certificates、certificate_risk
```

如果你不会构造请求体，就先看已有演示数据和接口文档里的 schema。

## 15. 这一课你必须会背的主线

不是背代码，是背这条逻辑：

```text
船东发布岗位需求
-> router/jobs.py 接收 POST /api/jobs
-> JobCreate 校验船舶、航线、岗位、证书、人数和上船时间
-> services.create_job 写 job_demands 主表
-> 同时写 job_required_certificates 明细表
-> 经理调用 GET /api/jobs/{job_id}/matches
-> services.list_matching_crews 查询 available 船员
-> _score_match 按岗位 40 分、证书 40 分、有效期风险 10 分、海历 10 分打分
-> 只返回 60 分以上结果，并返回匹配原因
-> 创建派遣时后端再次校验，防止不合格船员被派遣
```

能把这条讲顺，你就已经能回答这个模块 80% 的问题了。

## 16. 小练习

自己试着回答下面 6 个问题：

1. `POST /api/jobs` 对应哪个 router 文件？
2. `JobCreate` 里为什么既有 `ship_id` 又有 `ship_name`？
3. `job_demands` 和 `job_required_certificates` 是什么关系？
4. 只有什么状态的证书能参与智能匹配？
5. `match_score` 的 100 分由哪四部分组成？
6. 为什么匹配接口返回推荐后，创建派遣时还要二次校验？

标准答案：

```text
1. backend/app/routers/jobs.py
2. ship_id 用于数据库关联，ship_name 用于兼容前端输入和中文展示。
3. 一对多，一个岗位需求可以要求多个证书。
4. review_status = approved 且 expires_at >= today 的证书。
5. 岗位 40 分、证书满足度 40 分、证书有效期风险 10 分、历史海历 10 分。
6. 前端推荐不能替代后端规则，后端必须保证最终写入派遣表的数据合法。
```

这一课学完后，你应该能做到：老师点开智能匹配页面，你能从页面结果一路讲到后端代码，再讲到数据库表关系。
