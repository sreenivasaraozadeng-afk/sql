# 后端代码学习与答辩速查表

这份速查表的目标不是让你一次背完整个后端，而是让你能顺着真实代码讲清楚：请求从哪里进来、数据怎么校验、数据库表怎么关联、业务逻辑在哪里执行、最后怎么返回给前端。

## 一、后端整体主线

一句话版本：

```text
前端发请求 -> routers 接口层 -> schemas 参数校验 -> services 业务逻辑 -> models 数据库表 -> JSON 返回前端
```

对应代码：

| 层次 | 文件 | 作用 |
| --- | --- | --- |
| 启动入口 | `backend/run_sqlite.py` | 本地演示时启动 FastAPI，并使用 SQLite 演示数据库 |
| 应用入口 | `backend/app/main.py` | 创建 FastAPI 应用、配置跨域、注册所有路由 |
| 数据库连接 | `backend/app/database.py` | 创建数据库 engine 和 session |
| 依赖与权限 | `backend/app/dependencies.py` | 提供 `get_db`、当前用户识别、角色权限校验 |
| 表结构模型 | `backend/app/models.py` | SQLAlchemy ORM，类对应数据库表 |
| 请求校验 | `backend/app/schemas.py` | Pydantic 模型，检查前端传来的字段是否合法 |
| 业务逻辑 | `backend/app/services.py` | 真正执行登录、创建船员、证书审核、匹配、派遣、统计 |
| API 路由 | `backend/app/routers/*.py` | 定义接口地址、请求方法和权限 |

答辩可以这样说：

> 后端采用分层结构。路由层负责接收请求和权限控制，Schema 层负责参数校验，Service 层负责业务规则，Model 层负责数据库表映射。这样代码职责清晰，便于维护和答辩说明。

## 二、核心数据表怎么记

| 表/模型 | 作用 | 重点关系 |
| --- | --- | --- |
| `users` / `User` | 登录账号、角色、显示名称 | 一个用户可以关联一个船员档案 |
| `crews` / `Crew` | 船员基础档案 | 关联用户、岗位、证书、派遣、海历 |
| `certificates` / `Certificate` | 船员证书 | 关联船员和证书类型 |
| `certificate_review_records` | 证书审核记录 | 记录每次审核前后状态 |
| `job_demands` / `JobDemand` | 船东岗位需求 | 关联船舶、航线、岗位和所需证书 |
| `job_required_certificates` | 岗位要求证书 | 一个岗位需求可要求多类证书 |
| `dispatches` / `Dispatch` | 派遣主记录 | 关联岗位需求和船员 |
| `dispatch_status_logs` | 派遣状态日志 | 记录派遣状态流转 |
| `voyage_records` | 海历记录 | 上船后自动生成，下船后补全 |
| `operation_logs` | 操作日志 | 记录关键业务操作 |
| `ships`、`ports`、`routes` | 船舶、港口、航线 | 支持航线工作量统计 |
| `positions`、`certificate_types` | 岗位、证书类型字典表 | 避免大量重复字符串 |

答辩可以这样说：

> 我们把用户登录信息、船员档案、证书、岗位需求、派遣、海历拆成不同数据表，通过外键关联，减少数据冗余，也能清晰表达业务流程。

## 三、登录接口怎么讲

接口：

```text
POST /api/auth/login
```

入口：

```text
backend/app/routers/auth.py
```

主线：

```text
LoginRequest 校验账号密码
-> services.authenticate_user 查询 users 表
-> verify_password 校验密码哈希
-> create_access_token 生成 token
-> 返回用户信息和 token
```

你要会讲的点：

- `LoginRequest` 要求前端必须传 `username` 和 `password`。
- `authenticate_user` 用账号查 `users` 表。
- 数据库不保存明文密码，保存的是 `password_hash`。
- 登录成功后返回 token，后续请求靠 token 识别用户身份。

答辩句子：

> 登录接口先用 Pydantic 校验账号密码，再通过 SQLAlchemy 查询用户表，并用哈希校验密码。校验通过后生成 token，返回给前端用于后续身份认证。

## 四、创建船员怎么讲

接口：

```text
POST /api/crews
```

入口：

```text
backend/app/routers/crews.py
```

业务函数：

```text
services.create_crew
```

主线：

```text
CrewCreate 校验船员信息
-> 检查当前用户是否是 manager/admin
-> 创建 User 登录账号
-> 创建 Crew 船员档案
-> users 和 crews 通过 user_id 外键关联
-> 写入 operation_logs
```

你要会讲的点：

- 新建船员时会同时创建登录账号。
- `users` 表保存账号、密码哈希、角色。
- `crews` 表保存姓名、身份证、电话、岗位、状态。
- `crews.user_id` 指向 `users.id`，并且唯一，表示一对一关系。
- 新船员默认角色是 `seafarer`，默认状态是 `available`。

答辩句子：

> 创建船员时系统同时写入用户账号和船员档案。账号信息放在 `users` 表，业务档案放在 `crews` 表，两者通过外键一对一关联，既支持登录权限，也保持船员资料结构清晰。

## 五、证书审核怎么讲

接口：

```text
POST /api/certificates
PUT /api/certificates/{certificate_id}/review
```

入口：

```text
backend/app/routers/certificates.py
```

业务函数：

```text
services.create_certificate
services.review_certificate
```

主线：

```text
录入证书 -> review_status = pending
审核证书 -> review_status 改为 approved/rejected
写入 certificate_review_records
写入 operation_logs
智能匹配只认可 approved 且未过期证书
```

你要会讲的点：

- 证书刚录入时不是直接有效，而是 `pending`。
- 只有 `cert_admin` 和 `admin` 可以审核证书。
- 当前审核状态保存在 `certificates.review_status`。
- 每次审核历史保存在 `certificate_review_records`。
- 匹配时只使用审核通过且未过期的证书。

答辩句子：

> 证书模块设计了审核流程。证书录入后默认为待审核，审核通过后才参与岗位匹配。系统同时保存当前审核状态和历史审核记录，便于追溯证书审核过程。

## 六、岗位需求和智能匹配怎么讲

接口：

```text
POST /api/jobs
GET /api/jobs/{job_id}/matches
```

入口：

```text
backend/app/routers/jobs.py
backend/app/routers/matching.py
```

业务函数：

```text
services.create_job
services.list_matching_crews
services._score_match
```

岗位需求包含：

- 船舶
- 航线
- 所需岗位
- 招聘人数
- 上船时间
- 所需证书

匹配评分：

| 评分项 | 分值 | 说明 |
| --- | ---: | --- |
| 岗位匹配 | 40 | 船员岗位和需求岗位完全一致 |
| 证书满足度 | 40 | 按所需证书满足比例给分 |
| 证书有效期风险 | 10 | 有效期越充足分越高 |
| 历史海历经验 | 10 | 做过相同岗位或相同航线加分 |

筛选规则：

```text
只查 available 船员
只认可 approved 且未过期证书
只返回 60 分以上船员
按 match_score 倒序排列
```

答辩句子：

> 智能匹配不是简单查询，而是一个可解释评分模型。系统从岗位匹配、证书满足度、证书有效期风险和历史海历经验四个维度打分，并返回匹配原因，帮助经理选择合适船员。

## 七、派遣流程怎么讲

接口：

```text
POST /api/dispatches
PUT /api/dispatches/{id}/confirm
PUT /api/dispatches/{id}/onboard
PUT /api/dispatches/{id}/offboard
PUT /api/dispatches/{id}/cancel
```

入口：

```text
backend/app/routers/dispatches.py
```

业务函数：

```text
services.create_dispatch
services.confirm_dispatch
services.onboard_dispatch
services.offboard_dispatch
services.cancel_dispatch
```

正常状态流转：

```text
pending_owner -> confirmed -> onboard -> offboard
```

每一步发生什么：

| 步骤 | 派遣状态 | 船员状态 | 其他变化 |
| --- | --- | --- | --- |
| 经理创建派遣 | `pending_owner` | `available` | 写派遣状态日志 |
| 船东确认 | `confirmed` | `pending` | 记录确认人，岗位可能变 `matched` |
| 确认上船 | `onboard` | `at_sea` | 自动新增 `voyage_records` |
| 确认下船 | `offboard` | `available` | 岗位关闭，海历补下船时间 |
| 取消派遣 | `cancelled` | 恢复可派遣 | 释放岗位名额 |

创建派遣前的后端校验：

- 船员必须可派遣。
- 船员岗位必须满足需求。
- 船员不能已有进行中派遣。
- 船员证书必须审核通过、未过期、满足岗位需求。
- 岗位人数不能超过 `headcount`。

答辩句子：

> 派遣模块采用状态机设计。每次状态变化都会写入派遣状态日志，上船时自动生成海历记录，下船时补充下船时间并恢复船员可派遣状态，形成从需求、匹配、派遣到海历的完整业务闭环。

## 八、统计首页怎么讲

接口：

```text
GET /api/dashboard/summary
GET /api/dashboard/crew-status
GET /api/dashboard/certificate-alerts
GET /api/dashboard/dispatch-trend
GET /api/dashboard/route-workload
```

入口：

```text
backend/app/routers/dashboard.py
```

业务函数：

```text
services.dashboard_summary
services.dashboard_crew_status
services.dashboard_certificate_alerts
services.dashboard_dispatch_trend
services.dashboard_route_workload
```

统计项来源：

| 页面数据 | 后端来源 |
| --- | --- |
| 船员总数 | `crews` 表 |
| 在岸/出海/待上船 | `crews.status` |
| 待审核证书 | `certificates.review_status = pending` |
| 证书预警 | `certificates.expires_at` |
| 开放岗位 | `job_demands.status = open` |
| 进行中派遣 | `dispatches.status` |
| 月度派遣趋势 | `dispatches.created_at` |
| 航线工作量 | `voyage_records.route` |

答辩句子：

> 首页可视化数据由后端统计接口实时查询数据库得到，不是前端写死。后端按状态、月份、航线等维度统计船员、证书、派遣和海历数据，前端只负责展示表格和进度条。

## 九、日志怎么讲

日志分两类：

| 日志 | 表 | 作用 |
| --- | --- | --- |
| 操作日志 | `operation_logs` | 记录谁对什么对象做了什么操作 |
| 派遣状态日志 | `dispatch_status_logs` | 只记录派遣状态从什么变成什么 |

操作日志接口：

```text
GET /api/operation-logs
```

写日志函数：

```text
services._add_operation_log
services._append_dispatch_status_log
```

答辩句子：

> 系统设计了操作日志和派遣状态日志。操作日志用于审计用户行为，派遣状态日志用于追踪派遣流程，两类日志分别服务于系统审计和业务流程追踪。

## 十、老师常问问题速答

### 1. 为什么要把 `users` 和 `crews` 分开？

因为 `users` 负责登录和权限，`crews` 负责船员业务档案。分开后结构更清晰，也避免把登录字段和业务字段混在一张表里。

### 2. 为什么岗位要求证书要单独建表？

因为一个岗位需求可以要求多个证书，这是典型的一对多关系。单独建 `job_required_certificates` 可以避免在岗位表里用逗号拼接证书，符合数据库规范化设计。

### 3. 为什么证书要审核？

因为只有真实有效的证书才能参与派遣。系统通过 `pending`、`approved`、`rejected` 三种状态控制证书生命周期，并保留审核历史。

### 4. 为什么匹配后创建派遣还要再校验？

因为前端推荐结果可能过期或被绕过，后端必须再次校验岗位、船员状态、证书有效性和岗位人数，保证业务规则可靠。

### 5. 为什么上船时才生成海历？

因为海历表示实际出海经历。只有派遣确认上船后才算真实海历，下船时再补充下船时间，数据更符合业务事实。

### 6. 为什么要有 `operation_logs`？

为了记录关键操作，方便追踪是谁创建了船员、审核了证书、发起了派遣或确认了上下船。

### 7. 你的系统哪里体现数据库设计？

体现在多表关联、外键约束、唯一约束、检查约束、状态字段、字典表、日志表和统计查询。不是只做页面，而是用数据库表达业务关系和流程。

## 十一、读代码顺序

第一次读，不要从第一行读到最后一行。按业务读：

1. 先看 `run_sqlite.py`，知道项目怎么启动。
2. 看 `main.py`，知道路由怎么注册。
3. 看 `routers/auth.py`，理解登录。
4. 看 `routers/crews.py` 和 `services.create_crew`，理解新增船员。
5. 看 `routers/certificates.py` 和 `services.review_certificate`，理解证书审核。
6. 看 `routers/matching.py` 和 `services._score_match`，理解智能匹配。
7. 看 `routers/dispatches.py` 和派遣相关 service，理解状态流转。
8. 看 `dashboard.py` 和统计 service，理解可视化数据来源。
9. 最后回头看 `models.py`，把代码和数据库表对应起来。

## 十二、你答辩时的总介绍模板

> 我们后端使用 FastAPI 和 SQLAlchemy 实现。FastAPI 负责提供接口，Pydantic 负责参数校验，SQLAlchemy 负责数据库 ORM 映射。系统围绕船员、证书、岗位需求、智能匹配、派遣和海历展开。船东发布岗位需求，经理根据岗位、证书和海历进行智能匹配，证书管理员审核证书，派遣过程通过状态机控制，并自动生成海历记录。统计首页通过后端查询数据库实时汇总船员状态、证书预警、派遣趋势和航线工作量。整体设计重点体现了多表关联、约束、状态流转、日志追踪和统计查询。

