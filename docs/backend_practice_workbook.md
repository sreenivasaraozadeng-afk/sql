# 后端代码练习册

这份练习册给组长用。目标不是背代码，而是训练你看到一个接口时，能自己顺着代码说出：

```text
这个接口在哪里 -> 接收什么参数 -> 查哪几张表 -> 改哪些字段 -> 返回什么结果 -> 为什么这样设计
```

建议每天练 30 到 60 分钟。每次只追一条业务线，别一上来通读 `services.py`，那个文件太长，硬读会头疼。

## 0. 通用追代码模板

以后看到任何接口，都按这张表填：

| 问题 | 你的答案 |
| --- | --- |
| 接口地址是什么？ | 例如 `POST /api/crews` |
| 路由文件在哪里？ | 例如 `backend/app/routers/crews.py` |
| 请求参数模型是什么？ | 例如 `CrewCreate` |
| 参数在哪里校验？ | 例如 `backend/app/schemas.py` |
| 调用了哪个 service 函数？ | 例如 `services.create_crew` |
| 查了哪些表？ | 例如 `users`、`crews`、`positions` |
| 改了哪些字段？ | 例如 `crews.status` |
| 有没有权限控制？ | 例如 `manager/admin` |
| 有没有写日志？ | 例如 `operation_logs` |
| 返回给前端什么？ | 例如 `success/message/data` |

你能独立填完这张表，就说明这条接口基本懂了。

## 第 1 天：启动入口和后端主线

目标：

看懂服务怎么启动，知道请求为什么能进到后端。

阅读文件：

- `backend/run_sqlite.py`
- `backend/app/main.py`
- `backend/app/database.py`
- `backend/app/dependencies.py`

练习任务：

1. 找到 `uvicorn.run(app, host="127.0.0.1", port=3000)`，说出它的作用。
2. 找到 `create_app(...)`，说出它为什么要接收 `database_url`、`create_tables`、`seed_demo`。
3. 找到 `app.include_router(...)`，列出至少 5 个被注册的路由模块。
4. 找到 `get_db`，说出它为什么最后要 `db.close()`。
5. 找到 `require_roles`，说出它怎么判断当前用户有没有权限。

自测答案要点：

- `run_sqlite.py` 是本地演示入口。
- `main.py` 是 FastAPI 应用入口。
- `database.py` 负责创建数据库连接。
- `dependencies.py` 负责数据库会话和权限依赖。

答辩练习句：

> 本地运行时通过 `run_sqlite.py` 启动服务，FastAPI 应用在 `main.py` 中创建，所有功能模块通过 `include_router` 注册为接口，数据库会话通过依赖注入传入每个接口。

## 第 2 天：登录接口

目标：

看懂认证流程：账号密码怎么变成 token。

阅读文件：

- `backend/app/routers/auth.py`
- `backend/app/schemas.py` 的 `LoginRequest`、`LoginOut`
- `backend/app/services.py` 的 `authenticate_user`
- `backend/app/passwords.py`
- `backend/app/security.py`

接口：

```text
POST /api/auth/login
```

练习任务：

1. 在 `auth.py` 找到 `login` 函数，写出它调用了哪两个核心函数。
2. 在 `schemas.py` 找到 `LoginRequest`，说出前端必须传哪两个字段。
3. 在 `services.py` 找到 `authenticate_user`，说出账号错误和密码错误会返回什么。
4. 在 `passwords.py` 找到 `verify_password`，说出为什么数据库不保存明文密码。
5. 在 `security.py` 找到 `create_access_token`，说出 token 里保存了哪些信息。

自测答案要点：

- 登录先查 `users` 表。
- 密码通过哈希比对，不直接比较明文。
- token 里包含用户 id、角色、签发时间、过期时间。

你要能讲：

```text
前端传 username/password -> 后端校验参数 -> 查询 users 表 -> 校验密码哈希 -> 生成 token -> 返回用户信息
```

## 第 3 天：船员管理

目标：

看懂为什么创建船员时会同时写 `users` 和 `crews` 两张表。

阅读文件：

- `backend/app/routers/crews.py`
- `backend/app/schemas.py` 的 `CrewCreate`、`CrewUpdate`
- `backend/app/models.py` 的 `User`、`Crew`
- `backend/app/services.py` 的 `create_crew`、`update_crew`、`soft_delete_crew`

接口：

```text
GET /api/crews
POST /api/crews
GET /api/crews/{crew_id}
PUT /api/crews/{crew_id}
DELETE /api/crews/{crew_id}
```

练习任务：

1. 找到 `CrewCreate`，列出新增船员需要哪些字段。
2. 找到 `create_crew`，圈出创建 `User` 的代码。
3. 找到 `create_crew`，圈出创建 `Crew` 的代码。
4. 找到 `Crew.user_id`，说出它外键指向哪张表。
5. 找到 `soft_delete_crew`，说出删除船员为什么不是物理删除。

自测答案要点：

- `users` 表负责登录账号。
- `crews` 表负责船员业务档案。
- 两表通过 `crews.user_id -> users.id` 一对一关联。
- 停用船员用 `status="inactive"`，保留历史数据。

你要能讲：

```text
创建船员 = 创建登录账号 + 创建船员档案 + 建立 user_id 外键关系 + 写操作日志
```

## 第 4 天：证书录入和审核

目标：

看懂证书状态怎么控制匹配结果。

阅读文件：

- `backend/app/routers/certificates.py`
- `backend/app/schemas.py` 的 `CertificateCreate`、`CertificateReview`
- `backend/app/models.py` 的 `Certificate`、`CertificateReviewRecord`
- `backend/app/services.py` 的 `create_certificate`、`review_certificate`

接口：

```text
POST /api/certificates
PUT /api/certificates/{certificate_id}/review
GET /api/certificates/alerts
```

练习任务：

1. 找到 `CertificateCreate`，说出为什么要校验到期日期不能早于签发日期。
2. 找到 `create_certificate`，说出新证书默认状态是什么。
3. 找到 `review_certificate`，列出审核时会修改 `certificates` 表哪些字段。
4. 找到 `CertificateReviewRecord`，说出它和 `Certificate` 的区别。
5. 找到 `_valid_certificate_types`，说出匹配时什么证书才算有效。

自测答案要点：

- 证书录入后默认 `pending`。
- 审核状态只能是 `pending`、`approved`、`rejected`。
- 审核会记录审核人、审核时间、审核备注。
- 匹配只认可 `approved` 且未过期证书。

你要能讲：

```text
录入证书 -> pending -> 审核通过 approved -> 写审核记录 -> 匹配时才可使用
```

## 第 5 天：岗位需求和智能匹配

目标：

看懂系统最复杂的业务规则：匹配评分。

阅读文件：

- `backend/app/routers/jobs.py`
- `backend/app/routers/matching.py`
- `backend/app/schemas.py` 的 `JobCreate`
- `backend/app/models.py` 的 `JobDemand`、`JobRequiredCertificate`
- `backend/app/services.py` 的 `create_job`、`list_matching_crews`、`_score_match`

接口：

```text
POST /api/jobs
GET /api/jobs/{job_id}/matches
```

练习任务：

1. 找到 `JobCreate`，说出岗位需求包含哪些业务字段。
2. 找到 `JobRequiredCertificate`，解释为什么岗位证书要求要单独建表。
3. 找到 `list_matching_crews`，说出为什么只查询 `Crew.status == "available"`。
4. 找到 `_score_match`，写出四个评分项和对应分值。
5. 找到 `_valid_certificate_types`，说明证书审核和匹配之间的关系。

自测答案要点：

- 岗位匹配 40 分。
- 证书满足度 40 分。
- 证书有效期风险 10 分。
- 历史海历经验 10 分。
- 只返回 60 分以上，并按分数倒序排列。

你要能讲：

```text
智能匹配 = 可派遣船员过滤 + 岗位/证书/有效期/海历评分 + 返回可解释原因
```

## 第 6 天：派遣状态流转

目标：

看懂系统业务闭环：匹配船员如何变成派遣和海历。

阅读文件：

- `backend/app/routers/dispatches.py`
- `backend/app/schemas.py` 的 `DispatchCreate`
- `backend/app/models.py` 的 `Dispatch`、`DispatchStatusLog`、`VoyageRecord`
- `backend/app/services.py` 的派遣相关函数

接口：

```text
POST /api/dispatches
PUT /api/dispatches/{id}/confirm
PUT /api/dispatches/{id}/onboard
PUT /api/dispatches/{id}/offboard
PUT /api/dispatches/{id}/cancel
```

练习任务：

1. 找到 `create_dispatch`，说出创建派遣前会检查哪些条件。
2. 找到 `confirm_dispatch`，说出船东确认后船员状态怎么变。
3. 找到 `onboard_dispatch`，说出什么时候新增 `voyage_records`。
4. 找到 `offboard_dispatch`，说出下船后船员、岗位、海历分别怎么变。
5. 找到 `_append_dispatch_status_log`，说出它为什么重要。

自测答案要点：

正常状态流转：

```text
pending_owner -> confirmed -> onboard -> offboard
```

关键变化：

- 创建派遣：写 `dispatches` 和 `dispatch_status_logs`。
- 船东确认：船员变 `pending`。
- 确认上船：船员变 `at_sea`，新增海历。
- 确认下船：船员恢复 `available`，岗位关闭，海历补下船时间。

你要能讲：

```text
派遣模块用状态机控制流程，并用日志表记录每一次状态变化
```

## 第 7 天：统计首页和日志

目标：

看懂前端可视化数据从哪里来。

阅读文件：

- `backend/app/routers/dashboard.py`
- `backend/app/routers/logs.py`
- `backend/app/models.py` 的 `OperationLog`
- `backend/app/services.py` 的 dashboard 和 log 函数

接口：

```text
GET /api/dashboard/summary
GET /api/dashboard/crew-status
GET /api/dashboard/certificate-alerts
GET /api/dashboard/dispatch-trend
GET /api/dashboard/route-workload
GET /api/operation-logs
```

练习任务：

1. 找到 `dashboard_summary`，列出它统计了哪些数量。
2. 找到 `dashboard_crew_status`，说出船员有哪些状态。
3. 找到 `dashboard_dispatch_trend`，说出月度趋势按哪个字段统计。
4. 找到 `dashboard_route_workload`，说出航线工作量来自哪张表。
5. 找到 `_add_operation_log`，列出操作日志记录了哪些字段。

自测答案要点：

- 首页数据由后端查询数据库汇总。
- 前端只负责展示，不负责伪造统计结果。
- `operation_logs` 记录用户行为。
- `dispatch_status_logs` 记录派遣状态变化。

你要能讲：

```text
前端展示图表，后端统计数据，数据库保存真实业务记录
```

## 最终通关测试

给自己 10 分钟，不看资料，说清楚下面 6 条业务线：

1. 登录：账号密码怎么变成 token？
2. 创建船员：为什么同时写 `users` 和 `crews`？
3. 证书审核：为什么证书不是录入后立刻有效？
4. 智能匹配：100 分由哪几部分组成？
5. 派遣流程：从创建派遣到下船，哪些表发生变化？
6. 统计首页：前端的表格数据来自哪些后端查询？

如果某条讲不顺，就回到对应日期重新练。

## 老师追问时的回答方法

老师问代码细节时，不要慌。按这个顺序回答：

```text
先说接口地址
再说路由文件
再说调用的 service 函数
再说涉及的数据表
最后说为什么这样设计
```

例子：

> 老师如果问“证书审核怎么实现”，我会先说接口是 `PUT /api/certificates/{certificate_id}/review`，路由在 `routers/certificates.py`，真正逻辑在 `services.review_certificate`。它会修改 `certificates` 表的审核状态、审核人、审核时间和备注，同时插入 `certificate_review_records` 保存历史记录。这样既能看到证书当前状态，也能追溯审核过程。

## 你现在最应该练的 3 个高频答辩问题

### 问题 1：你的后端为什么要分 routers、schemas、services、models？

答：

> 这样职责清晰。`routers` 负责接口地址和权限，`schemas` 负责参数校验，`services` 负责业务逻辑，`models` 负责数据库表映射。分层后代码更容易维护，也更容易说明业务流程。

### 问题 2：你的系统哪里体现数据库课程设计？

答：

> 体现在多表关联、外键约束、唯一约束、检查约束、状态字段、字典表、日志表和统计查询。比如船员和用户是一对一，岗位和所需证书是一对多，派遣和海历有关联，证书审核和派遣状态都有日志表追踪。

### 问题 3：你的智能匹配为什么比简单查询更复杂？

答：

> 因为它不是只判断能不能派遣，而是从岗位匹配、证书满足度、证书有效期风险、历史海历经验四个维度计算分数，并返回匹配原因。这样经理不仅能看到推荐结果，还能知道为什么推荐。

