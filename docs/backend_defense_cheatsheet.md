# 后端代码答辩速查表

这份表给答辩现场用。它不是长篇教程，而是让你被老师问到某个模块或接口时，能马上按固定套路回答。

固定回答结构：

```text
这个接口做什么
-> 入口在哪个 router
-> 参数由哪个 schema 校验
-> 调哪个 service
-> 查/改哪些表
-> 为什么这样设计
```

## 1. 全局一句话

```text
后端使用 FastAPI + SQLAlchemy，按 routers、schemas、services、models 分层；核心业务围绕船员、证书、岗位需求、智能匹配、派遣海历、统计日志展开，重点体现数据库表关系、状态流转和统计查询。
```

## 2. 模块一句话速记

| 模块 | 一句话讲法 | 关键文件 |
| --- | --- | --- |
| 启动与路由 | `run_sqlite.py` 启动 FastAPI，`main.py` 注册所有路由和跨域配置 | `backend/run_sqlite.py`、`backend/app/main.py` |
| 登录权限 | 登录查 `users`，校验密码哈希，生成 token，后续接口用角色控制权限 | `routers/auth.py`、`dependencies.py`、`security.py` |
| 船员管理 | `users` 管账号，`crews` 管船员档案，一对一关联 | `routers/crews.py`、`services.create_crew` |
| 证书审核 | 证书先 `pending`，审核后变 `approved/rejected`，审核过程单独留痕 | `routers/certificates.py`、`CertificateReviewRecord` |
| 船舶航线字典 | 船舶、港口、航线、岗位、证书类型独立成表，避免到处写重复字符串 | `routers/ships.py`、`routers/lookups.py` |
| 岗位需求 | `job_demands` 保存岗位主信息，`job_required_certificates` 保存岗位要求证书 | `routers/jobs.py` |
| 智能匹配 | 后端按岗位、证书、证书有效期、海历经验计算 100 分匹配分 | `routers/matching.py`、`services._score_match` |
| 派遣海历 | 派遣按状态流转，上船自动生成海历，下船补全海历 | `routers/dispatches.py` |
| 统计首页 | 后端从多张表汇总船员状态、证书预警、派遣趋势、航线工作量 | `routers/dashboard.py` |
| 操作日志 | `operation_logs` 记录谁做了什么，`dispatch_status_logs` 记录派遣状态怎么变 | `routers/logs.py`、`models.OperationLog` |
| 旧接口兼容 | `/api/login`、`/api/voyages` 等旧接口保留，避免旧前端直接失效 | `routers/legacy.py` |

## 3. 接口怎么讲

### 3.1 登录与权限

| 接口 | 一句话讲法 | 答辩展开 |
| --- | --- | --- |
| `POST /api/auth/login` | 用户登录，返回 token 和用户信息 | 入口在 `routers/auth.py`，参数用 `LoginRequest`，service 是 `authenticate_user`，查 `users` 表，用 `verify_password` 校验 `password_hash`，成功后 `create_access_token` 生成 token。 |
| `POST /api/login` | 旧版登录兼容接口 | 在 `routers/legacy.py`，为了兼容旧页面。答辩时主讲新接口 `/api/auth/login`，补充说旧接口保留是为了平滑升级。 |

老师追问：

| 问题 | 回答 |
| --- | --- |
| 为什么不存明文密码？ | 明文密码不安全，数据库保存 `password_hash`，登录时用哈希校验。 |
| 权限在哪里控制？ | 路由函数里通过 `Depends(require_roles(...))` 控制，核心在 `dependencies.py`。 |
| token 有什么用？ | 后续请求带 token，后端识别当前用户和角色，再决定是否允许访问接口。 |

### 3.2 船员管理

| 接口 | 一句话讲法 | 答辩展开 |
| --- | --- | --- |
| `GET /api/crews` | 查询船员列表 | 入口在 `routers/crews.py`，调用 `services.list_crews`，查 `crews` 并关联 `users`，返回船员基础档案。 |
| `POST /api/crews` | 创建船员账号和档案 | 参数是 `CrewCreate`，调用 `create_crew`，同时写 `users` 和 `crews`，默认角色 `seafarer`，默认状态 `available`，并写 `operation_logs`。 |
| `GET /api/crews/{crew_id}` | 查询单个船员详情 | 根据 `crew_id` 查 `crews`，不存在返回 404。 |
| `PUT /api/crews/{crew_id}` | 修改船员信息 | 参数是 `CrewUpdate`，可以更新电话、岗位、状态等；如果岗位变化，会同步处理 `position_id` 和中文岗位名。 |
| `DELETE /api/crews/{crew_id}` | 停用船员 | 不物理删除，而是软删除，把 `crews.status` 改为 `inactive`，保留历史证书、派遣和海历。 |

老师追问：

| 问题 | 回答 |
| --- | --- |
| 为什么创建船员要写两张表？ | `users` 负责登录和权限，`crews` 负责业务档案，两者通过 `crews.user_id` 一对一关联。 |
| 为什么删除是停用？ | 船员可能有关联证书、派遣、海历，直接删除会破坏历史数据，所以用 `inactive` 软删除。 |
| 船员状态有哪些？ | `available` 在岸可派遣，`pending` 待上船，`at_sea` 出海中，`inactive` 已停用。 |

### 3.3 证书管理与审核

| 接口 | 一句话讲法 | 答辩展开 |
| --- | --- | --- |
| `GET /api/certificates` | 查询证书列表 | 调 `list_certificates`，查 `certificates` 并关联船员，给前端展示证书状态。 |
| `POST /api/certificates` | 录入船员证书 | 参数是 `CertificateCreate`，写 `certificates`，默认 `review_status = pending`，说明证书录入后还不能直接用于匹配。 |
| `GET /api/certificates/alerts` | 查询证书到期预警 | 调 `list_certificate_alerts`，查 30 天内到期且状态为 `pending/approved` 的证书，并按到期时间排序。 |
| `PUT /api/certificates/{certificate_id}` | 更新证书基础信息 | 参数是 `CertificateUpdate`，可更新证书编号、有效期、附件等，更新后继续受审核状态约束。 |
| `PUT /api/certificates/{certificate_id}/review` | 审核证书 | 参数是 `CertificateReview`，把证书状态改为 `approved/rejected`，并写 `certificate_review_records` 和 `operation_logs`。 |

老师追问：

| 问题 | 回答 |
| --- | --- |
| 为什么证书默认是 `pending`？ | 录入不代表真实有效，必须由证书管理员审核后才能参与匹配。 |
| 审核记录为什么单独建表？ | `certificates` 保存当前状态，`certificate_review_records` 保存每次审核历史，方便追溯。 |
| 什么证书能参与智能匹配？ | 只有 `review_status = approved` 且 `expires_at` 未过期的证书。 |

### 3.4 船舶、港口、航线、岗位、证书类型

| 接口 | 一句话讲法 | 答辩展开 |
| --- | --- | --- |
| `GET /api/ships` | 查询船舶列表 | 调 `list_ships`，查 `ships`，船东只能看自己的船舶，经理和管理员可看管理视角数据。 |
| `POST /api/ships` | 创建船舶 | 参数是 `ShipCreate`，写 `ships`，关联船东或船公司信息。 |
| `GET /api/positions` | 查询岗位字典 | 查 `positions`，用于船员岗位和岗位需求选择。 |
| `POST /api/positions` | 新增岗位类型 | 参数是 `PositionCreate`，写 `positions`，避免岗位名称随意填写。 |
| `GET /api/certificate-types` | 查询证书类型 | 查 `certificate_types`，用于证书录入和岗位证书要求。 |
| `POST /api/certificate-types` | 新增证书类型 | 参数是 `CertificateTypeCreate`，由证书管理员或管理员维护。 |
| `GET /api/ports` | 查询港口 | 查 `ports`，航线由起点港口和终点港口组成。 |
| `POST /api/ports` | 新增港口 | 参数是 `PortCreate`，写 `ports`。 |
| `GET /api/routes` | 查询航线 | 查 `routes`，并通过港口关系显示起点和终点。 |
| `POST /api/routes` | 新增航线 | 参数是 `RouteCreate`，写 `routes`，关联出发港和目的港。 |

老师追问：

| 问题 | 回答 |
| --- | --- |
| 为什么要建字典表？ | 岗位、证书类型、港口、航线如果都写字符串，会重复且难维护；字典表能规范数据并支持外键关联。 |
| 前端为什么还能显示中文？ | 后端保存 ID 关联，同时返回中文名称，数据库规范和页面可读性都兼顾。 |
| 航线为什么要关联港口？ | 航线本质上由出发港和目的港组成，拆成港口表和航线表更符合实体关系。 |

### 3.5 岗位需求与智能匹配

| 接口 | 一句话讲法 | 答辩展开 |
| --- | --- | --- |
| `GET /api/jobs` | 查询岗位需求列表 | 调 `list_jobs`，查 `job_demands`，船东只能看自己的岗位需求。 |
| `POST /api/jobs` | 发布岗位需求 | 参数是 `JobCreate`，写 `job_demands` 主表，同时把所需证书写入 `job_required_certificates`。 |
| `GET /api/jobs/{job_id}` | 查看岗位需求详情 | 根据岗位 ID 查 `job_demands`，返回船舶、航线、岗位、人数、所需证书等。 |
| `PUT /api/jobs/{job_id}/close` | 关闭岗位需求 | 把 `job_demands.status` 改为 `closed`，并写操作日志。 |
| `GET /api/jobs/{job_id}/matches` | 智能匹配船员 | 调 `list_matching_crews`，查询 `available` 船员，再用 `_score_match` 按 100 分模型计算推荐结果。 |

匹配评分怎么讲：

| 评分项 | 分值 | 数据来源 |
| --- | ---: | --- |
| 岗位匹配 | 40 | `crews.position` 对比 `job_demands.required_position` |
| 证书满足度 | 40 | `certificates` 对比 `job_required_certificates` |
| 证书有效期风险 | 10 | `certificates.expires_at` |
| 历史海历经验 | 10 | `voyage_records.position` 或 `voyage_records.route` |

老师追问：

| 问题 | 回答 |
| --- | --- |
| 智能匹配是不是前端写死？ | 不是。前端只展示，分数由后端 `services._score_match` 根据数据库数据计算。 |
| 为什么岗位所需证书单独建表？ | 一个岗位可以要求多个证书，是一对多关系，单独建表比逗号拼接更规范。 |
| 为什么只返回 60 分以上？ | 过滤明显不合适船员，让推荐结果更有业务意义。 |

### 3.6 派遣与海历

| 接口 | 一句话讲法 | 答辩展开 |
| --- | --- | --- |
| `GET /api/dispatches` | 查询派遣列表 | 调 `list_dispatches`，查 `dispatches` 并关联 `crews`、`job_demands`；船东只能看自己岗位的派遣。 |
| `GET /api/dispatches/{dispatch_id}` | 查询派遣详情 | 调 `get_dispatch`，额外加载 `dispatch_status_logs`，展示状态流转历史。 |
| `POST /api/dispatches` | 经理发起派遣 | 参数是 `DispatchCreate`，传 `job_id` 和 `crew_id`；后端校验岗位、人数、船员状态、岗位匹配和证书有效性。 |
| `PUT /api/dispatches/{dispatch_id}/confirm` | 船东确认派遣 | 状态 `pending_owner -> confirmed`，船员 `available -> pending`，记录确认人和日志。 |
| `PUT /api/dispatches/{dispatch_id}/onboard` | 确认上船 | 状态 `confirmed -> onboard`，船员变 `at_sea`，自动新增 `voyage_records`。 |
| `PUT /api/dispatches/{dispatch_id}/offboard` | 确认下船 | 状态 `onboard -> offboard`，船员恢复 `available`，岗位关闭，海历写 `offboard_at`。 |
| `PUT /api/dispatches/{dispatch_id}/cancel` | 取消派遣 | 状态变 `cancelled`，释放船员和岗位，必要时同步取消海历。 |

派遣状态必须背：

```text
pending_owner -> confirmed -> onboard -> offboard
cancelled 是异常结束状态
```

老师追问：

| 问题 | 回答 |
| --- | --- |
| 为什么创建派遣前还要校验？ | 智能匹配只是推荐，创建派遣是写数据库，必须再次校验状态、岗位、证书和人数。 |
| 上船时数据库发生什么？ | `dispatches.status` 变 `onboard`，`crews.status` 变 `at_sea`，新增 `voyage_records`，写状态日志和操作日志。 |
| 下船时数据库发生什么？ | `dispatches.status` 变 `offboard`，船员恢复 `available`，岗位 `closed`，海历写入 `offboard_at`。 |
| 为什么要 `dispatch_status_logs`？ | 当前状态只保存在 `dispatches`，历史变化需要单独日志表追溯。 |

### 3.7 统计首页

| 接口 | 一句话讲法 | 答辩展开 |
| --- | --- | --- |
| `GET /api/dashboard/summary` | 首页统计卡片 | 调 `dashboard_summary`，从 `crews`、`certificates`、`job_demands`、`dispatches`、`ships` 汇总核心数量。 |
| `GET /api/dashboard/crew-status` | 船员状态分布 | 调 `dashboard_crew_status`，按 `crews.status` 统计 `available/pending/at_sea/inactive`。 |
| `GET /api/dashboard/certificate-alerts` | 证书到期预警 | 调 `dashboard_certificate_alerts`，查询 30 天内到期的 `pending/approved` 证书。 |
| `GET /api/dashboard/dispatch-trend` | 月度派遣趋势 | 调 `dashboard_dispatch_trend`，按 `dispatches.created_at` 的年月统计数量。 |
| `GET /api/dashboard/route-workload` | 航线工作量 | 调 `dashboard_route_workload`，按 `voyage_records.route` 统计海历数量和在船数量。 |

老师追问：

| 问题 | 回答 |
| --- | --- |
| 首页数据是不是写死的？ | 不是，前端调用 dashboard 接口，后端实时查询数据库并返回统计结果。 |
| 月度趋势按什么字段统计？ | 按 `dispatches.created_at` 格式化成 `YYYY-MM` 统计。 |
| 航线工作量为什么用海历表？ | 海历代表真实出海记录，工作量应按实际发生的航次统计。 |

### 3.8 操作日志

| 接口 | 一句话讲法 | 答辩展开 |
| --- | --- | --- |
| `GET /api/operation-logs` | 查看最近操作日志 | 入口在 `routers/logs.py`，调用 `list_operation_logs`，默认查最近 100 条 `operation_logs`。 |

老师追问：

| 问题 | 回答 |
| --- | --- |
| `operation_logs` 记录什么？ | 记录谁在什么时候对什么对象做了什么操作，比如创建船员、审核证书、发起派遣。 |
| 和 `dispatch_status_logs` 有什么区别？ | `operation_logs` 是系统级审计日志；`dispatch_status_logs` 是派遣状态流转专用日志。 |
| 为什么日志表要有索引？ | 按用户、操作类型、对象、时间查询日志时更快。 |

### 3.9 旧版兼容接口

| 接口 | 一句话讲法 |
| --- | --- |
| `GET /api/stats` | 旧统计接口，兼容旧页面 |
| `GET /api/voyages` | 旧海历列表接口 |
| `POST /api/voyages` | 旧海历创建接口，内部仍复用新派遣和海历逻辑 |
| `GET /api/my-profile/{crew_id}` | 船员查看个人档案 |
| `GET /api/my-voyages/{crew_id}` | 船员查看个人海历 |
| `PUT /api/crews/{crew_id}/status` | 旧页面修改船员状态 |

答辩时讲法：

```text
核心业务主讲新接口，legacy.py 里的旧接口主要用于兼容原有静态前端，避免系统升级后旧页面失效。
```

## 4. 老师追问万能回答模板

### 4.1 问某个接口怎么实现

```text
这个接口入口在 routers/xxx.py。
请求参数由 schemas.py 中的 xxx 模型校验。
然后调用 services.py 的 xxx 函数。
service 里通过 SQLAlchemy 查询或修改 xxx 表。
最后把 ORM 对象转换成字典，按 success/data/message 的格式返回前端。
```

### 4.2 问为什么要拆表

```text
因为不同表表达不同实体或不同关系。
比如 users 是账号，crews 是船员档案；job_demands 是岗位主表，job_required_certificates 是岗位要求证书明细。
拆表后能减少冗余，便于外键约束和统计查询，也更符合数据库规范化设计。
```

### 4.3 问为什么要有状态字段

```text
状态字段用来表达业务流程。
比如船员有 available、pending、at_sea、inactive；派遣有 pending_owner、confirmed、onboard、offboard、cancelled。
后端通过状态限制下一步能做什么，避免流程乱跳。
```

### 4.4 问为什么要有日志

```text
日志用于追溯。
operation_logs 追踪用户操作，dispatch_status_logs 追踪派遣状态变化。
如果出现问题，可以知道谁在什么时候做了什么、状态从什么变成了什么。
```

### 4.5 问哪里体现数据库课程设计

```text
主要体现在表结构拆分、主外键关系、唯一约束、检查约束、字典表、状态流转、审核记录、操作日志和统计查询。
系统不是只做页面，而是用数据库关系支撑完整业务流程。
```

## 5. 答辩现场最容易被问的 12 个问题

| 问题 | 一句话答案 |
| --- | --- |
| 后端分几层？ | `routers` 接口、`schemas` 校验、`services` 业务、`models` 表映射。 |
| 登录怎么做？ | 查 `users`，校验 `password_hash`，生成 token，后续用 token 判断身份。 |
| 权限怎么控制？ | 路由里用 `require_roles`，不同角色访问不同接口。 |
| 为什么 `users` 和 `crews` 分开？ | 账号权限和船员档案职责不同，通过 `crews.user_id` 一对一关联。 |
| 证书审核有什么用？ | 只有审核通过且未过期证书能参与匹配和派遣。 |
| 为什么岗位证书要求单独建表？ | 一个岗位可要求多个证书，是一对多关系。 |
| 智能匹配怎么算？ | 岗位 40、证书 40、有效期风险 10、海历 10。 |
| 为什么匹配后派遣还要校验？ | 推荐不等于最终写库，后端必须保证数据合法。 |
| 派遣状态怎么流转？ | `pending_owner -> confirmed -> onboard -> offboard`。 |
| 海历什么时候生成？ | 确认上船时生成，下船时补充 `offboard_at`。 |
| 首页统计从哪里来？ | 后端从船员、证书、岗位、派遣、海历、船舶等表查询汇总。 |
| 两种日志区别？ | `operation_logs` 记用户操作，`dispatch_status_logs` 记派遣状态变化。 |

## 6. 30 秒兜底总结

如果你突然紧张，就背这一段：

```text
我们后端用 FastAPI 和 SQLAlchemy，按 routers、schemas、services、models 分层。数据库围绕船员出海派遣设计，users 管账号，crews 管船员档案，certificates 管证书，job_demands 管岗位需求，dispatches 管派遣，voyage_records 管海历，operation_logs 和 dispatch_status_logs 管追溯。业务上从登录权限、证书审核、岗位匹配、派遣状态流转到统计首页都能对应到具体数据表，不是简单页面展示，而是用数据库关系和状态变化支撑完整流程。
```
