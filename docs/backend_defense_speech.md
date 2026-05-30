# 后端答辩口述总稿

这份文档不是逐行讲代码，而是帮你把后端讲成一段完整、清楚、有层次的答辩发言。

你作为组长，可以按这个稿子练。不要死背每个字，要背住顺序和关键词。

目标时间：

```text
标准版：5 到 8 分钟
压缩版：2 到 3 分钟
加长版：老师追问时展开
```

## 1. 先用 30 秒讲后端整体结构

可以这样说：

```text
老师好，我们这个系统后端使用 FastAPI 加 SQLAlchemy 实现，数据库课程设计的重点放在表结构、外键关系、状态流转和统计查询上。

后端代码采用分层结构：routers 负责接口入口和权限控制，schemas 负责请求参数校验，services 负责业务逻辑，models 负责数据库表映射。

一个前端请求进入后端后，大概会经过 router、schema、dependency、service、model，最后查询或修改数据库，再返回统一 JSON 给前端。
```

这段要点：

```text
FastAPI
SQLAlchemy
routers / schemas / services / models
请求链路
数据库设计是重点
```

老师如果问“你从哪里看出分层”，你指这些文件：

```text
backend/app/routers/*.py
backend/app/schemas.py
backend/app/services.py
backend/app/models.py
```

## 2. 用 40 秒讲数据库主表关系

可以这样说：

```text
数据库方面，我们没有把所有信息放在一张大表里，而是按业务对象拆分。

users 表负责登录账号和角色，crews 表负责船员业务档案，两者通过 crews.user_id 一对一关联。

certificates 表保存船员证书，certificate_review_records 表保存证书审核记录。

job_demands 表保存船东岗位需求，job_required_certificates 表保存岗位要求的多种证书。

dispatches 表保存派遣主记录，dispatch_status_logs 表记录派遣状态变化，voyage_records 表记录船员海历。

另外还有 ships、ports、routes、positions、certificate_types 这些实体表和字典表，用来规范船舶、港口、航线、岗位和证书类型。
```

这段要点：

```text
users + crews：账号和档案
certificates + review_records：证书和审核
job_demands + job_required_certificates：岗位和证书要求
dispatches + dispatch_status_logs + voyage_records：派遣、状态日志、海历
字典表：positions、certificate_types
实体表：ships、ports、routes
```

老师如果问“为什么要拆表”，你答：

```text
拆表可以减少冗余，体现一对一、一对多关系，也方便外键约束、统计查询和业务扩展。
```

## 3. 第一条主线：登录和权限

可以这样讲：

```text
登录接口是 POST /api/auth/login，入口在 routers/auth.py。

前端传 username 和 password 后，LoginRequest 会先校验参数。然后 service 层的 authenticate_user 根据 username 查询 users 表，并用 verify_password 校验密码哈希。

密码不是明文保存的，数据库里保存的是 password_hash。登录成功后，后端调用 create_access_token 生成 token，返回给前端。

后续接口会通过 dependencies.py 里的 get_current_user 识别当前用户，再用 require_roles 判断角色权限。比如证书审核只允许 cert_admin 和 admin，创建派遣只允许 manager 和 admin，船东确认只允许 shipowner 和 admin。
```

你要能指到代码：

```text
routers/auth.py
schemas.LoginRequest
services.authenticate_user
passwords.verify_password
security.create_access_token
dependencies.require_roles
models.User
```

这一段老师常问：

```text
为什么密码不明文保存？
权限在哪里控制？
token 有什么用？
```

标准回答：

```text
密码哈希保存更安全；
权限在 dependencies.py 的 require_roles 控制；
token 用来让后续接口识别当前用户身份和角色。
```

## 4. 第二条主线：船员管理

可以这样讲：

```text
船员管理的核心接口是 POST /api/crews，入口在 routers/crews.py。

创建船员时，前端传来的数据先经过 CrewCreate 校验，比如姓名、身份证、岗位、账号密码等。

service 层的 create_crew 会同时创建 User 和 Crew。User 保存登录账号、密码哈希和角色；Crew 保存船员姓名、身份证、电话、岗位和状态。

users 和 crews 是一对一关系，crews.user_id 外键指向 users.id，并且设置唯一约束。这样一个船员既能登录系统，又有自己的业务档案。

新船员默认角色是 seafarer，默认状态是 available，表示在岸可派遣。
```

你要能指到代码：

```text
routers/crews.py
schemas.CrewCreate
services.create_crew
models.User
models.Crew
```

要记住的状态：

```text
available：在岸可派遣
pending：待上船
at_sea：出海中
inactive：已停用
```

老师如果问“为什么删除不是直接删”，你答：

```text
系统采用软删除，把 crew.status 改成 inactive。这样可以保留历史证书、派遣和海历记录，不会破坏历史数据。
```

## 5. 第三条主线：证书录入与审核

可以这样讲：

```text
证书模块有两个重点接口：POST /api/certificates 录入证书，PUT /api/certificates/{id}/review 审核证书。

证书录入后，默认 review_status 是 pending，表示待审核。证书管理员或管理员可以审核，把状态改成 approved 或 rejected。

审核时，系统不仅会更新 certificates 表里的 review_status 和 review_remark，还会往 certificate_review_records 表插入一条审核记录，保存旧状态、新状态、审核人和备注。

这个设计的重点是证书审核会影响后续智能匹配。只有 approved 且未过期的证书，才会参与岗位匹配和派遣校验。
```

你要能指到代码：

```text
routers/certificates.py
schemas.CertificateCreate
schemas.CertificateReview
services.create_certificate
services.review_certificate
models.Certificate
models.CertificateReviewRecord
```

证书状态：

```text
pending：待审核
approved：审核通过
rejected：审核拒绝
```

老师如果问“为什么需要审核记录表”，你答：

```text
因为证书审核是关键业务操作，不能只覆盖当前状态，还要保留每次审核的历史，便于追溯。
```

## 6. 第四条主线：岗位需求与智能匹配

可以这样讲：

```text
岗位需求由船东或管理员发布，接口是 POST /api/jobs，入口在 routers/jobs.py。

JobCreate 会校验岗位标题、船舶、航线、岗位、所需证书、招聘人数和上船时间。

service 层 create_job 会写入 job_demands 主表，同时把岗位所需证书写入 job_required_certificates 明细表。这样一个岗位可以要求多个证书，符合一对多关系。

智能匹配接口是 GET /api/jobs/{job_id}/matches，入口在 routers/matching.py。

后端会查询当前 available 的船员，并读取他们的证书和海历，然后用 _score_match 计算匹配分数。

评分模型总分 100 分：岗位匹配 40 分，证书满足度 40 分，证书有效期风险 10 分，历史海历经验 10 分。系统只返回 60 分以上的船员，并返回 match_reasons、missing_certificates、certificate_risk 等解释信息。
```

你要能指到代码：

```text
routers/jobs.py
routers/matching.py
schemas.JobCreate
services.create_job
services.list_matching_crews
services._score_match
models.JobDemand
models.JobRequiredCertificate
```

老师如果问“是不是前端写死推荐”，你答：

```text
不是，前端只展示结果。真正匹配逻辑在后端 services.py，后端从岗位、船员、证书、海历多张表查询数据后计算 match_score。
```

老师如果问“未审核证书能不能参与匹配”，你答：

```text
不能。_valid_certificate_types 只统计 review_status 为 approved 且 expires_at 没过期的证书。
```

## 7. 第五条主线：派遣状态流转与海历

可以这样讲：

```text
智能匹配之后，经理可以发起派遣，接口是 POST /api/dispatches。

创建派遣时，DispatchCreate 只需要 job_id 和 crew_id，因为船舶、航线、岗位来自 job_demands，船员信息来自 crews。

service 层 create_dispatch 会先校验岗位是否开放、招聘人数是否已满、船员是否 available、岗位是否匹配、证书是否审核通过且未过期，并检查船员是否已有进行中的派遣。

校验通过后，系统写入 dispatches 表，初始状态是 pending_owner，表示等待船东确认，同时写 dispatch_status_logs 和 operation_logs。

船东确认后，状态从 pending_owner 变成 confirmed，船员状态从 available 变成 pending。

经理确认上船后，状态从 confirmed 变成 onboard，船员状态变成 at_sea，同时系统自动新增 voyage_records 海历记录。

经理确认下船后，状态从 onboard 变成 offboard，船员恢复 available，岗位变为 closed，海历补充 offboard_at 并变成 offboard。
```

状态流转一定要背：

```text
pending_owner -> confirmed -> onboard -> offboard
```

取消状态：

```text
cancelled
```

你要能指到代码：

```text
routers/dispatches.py
schemas.DispatchCreate
services.create_dispatch
services.confirm_dispatch
services.onboard_dispatch
services.offboard_dispatch
services.cancel_dispatch
models.Dispatch
models.DispatchStatusLog
models.VoyageRecord
```

老师如果问“上船后数据库发生什么”，你答：

```text
dispatches.status 变为 onboard；
crews.status 变为 at_sea；
voyage_records 新增一条海历；
dispatch_status_logs 记录状态变化；
operation_logs 记录操作审计。
```

## 8. 第六条主线：统计首页与操作日志

可以这样讲：

```text
统计首页不是前端写死数字，而是后端从数据库实时查询。

统计接口集中在 routers/dashboard.py，包括 summary、crew-status、certificate-alerts、dispatch-trend、route-workload。

summary 统计总船员数、可派遣船员、出海中船员、待审核证书、证书预警、开放岗位、进行中派遣和船舶数量。

crew-status 从 crews 表按状态统计。

certificate-alerts 从 certificates 表查询 30 天内到期且状态为 pending 或 approved 的证书，并关联船员信息。

dispatch-trend 根据 dispatches.created_at 按年月统计派遣数量。

route-workload 根据 voyage_records.route 统计每条航线的海历数量和当前在船数量。

操作日志接口是 GET /api/operation-logs，后端从 operation_logs 表查询最近 100 条关键操作。
```

你要能指到代码：

```text
routers/dashboard.py
routers/logs.py
services.dashboard_summary
services.dashboard_crew_status
services.dashboard_certificate_alerts
services.dashboard_dispatch_trend
services.dashboard_route_workload
services.list_operation_logs
models.OperationLog
```

老师如果问“operation_logs 和 dispatch_status_logs 有什么区别”，你答：

```text
operation_logs 是系统级操作审计，记录用户对船员、证书、岗位、派遣等对象做了什么；
dispatch_status_logs 是派遣业务专用日志，只记录某条派遣状态从什么变成什么。
```

## 9. 最后用 30 秒总结亮点

可以这样收尾：

```text
总结一下，我们后端的重点不是简单增删改查，而是围绕船员出海派遣这条主线设计数据库。

从登录权限、船员档案、证书审核、岗位匹配，到派遣状态流转、海历生成、统计首页和操作日志，每个模块都对应明确的数据表和业务约束。

其中证书审核会影响智能匹配，智能匹配会影响派遣，派遣上船会生成海历，海历又会参与航线工作量统计。这样各模块之间不是孤立的，而是通过数据库关系和状态变化串成完整流程。
```

这段要点：

```text
不是简单 CRUD
数据库表关系清晰
业务流程完整
证书影响匹配
派遣生成海历
海历支持统计
日志支持追溯
```

## 10. 2 到 3 分钟压缩版

如果老师只给很短时间，你就讲这个版本：

```text
我们后端采用 FastAPI 和 SQLAlchemy，代码分为 routers、schemas、services、models 四层。

router 层负责接口入口和权限控制，schema 层负责参数校验，service 层负责业务逻辑，model 层对应数据库表。

数据库设计围绕船员出海派遣展开。users 表保存账号和角色，crews 表保存船员档案；certificates 表保存证书，certificate_review_records 保存审核历史；job_demands 保存岗位需求，job_required_certificates 保存岗位要求的证书；dispatches 保存派遣记录，dispatch_status_logs 保存派遣状态变化，voyage_records 保存海历；operation_logs 保存操作审计。

业务流程是：用户登录后按角色访问接口；经理维护船员，证书管理员审核证书；船东发布岗位需求；经理调用智能匹配，系统按岗位 40 分、证书 40 分、证书风险 10 分、海历经验 10 分计算匹配分；经理发起派遣后，船东确认，经理确认上船，系统自动生成海历，下船后补全海历并恢复船员状态。

首页统计也不是写死的，而是从 crews、certificates、job_demands、dispatches、voyage_records、ships 等表查询汇总。操作日志和派遣状态日志可以追踪谁做了什么，以及派遣状态怎么变化。

所以这个系统的后端重点是用数据库表关系、状态流转和查询统计支撑完整业务流程。
```

## 11. 你答辩时不要这样说

不要说：

```text
这个接口就是增删改查。
这个地方我不清楚，应该是系统自动做的。
这个推荐是前端显示的。
数据库表我没怎么看。
```

要换成：

```text
这个接口入口在 routers，业务规则在 services，对应的数据表在 models。
这个动作会修改哪些状态，我可以顺着代码讲。
推荐结果由后端根据岗位、证书和海历计算，前端只负责展示。
数据库表之间通过外键和状态字段支撑完整业务流程。
```

## 12. 练习方法

按这个顺序练：

```text
第一遍：照着稿子读，熟悉顺序。
第二遍：只看小标题，自己讲每一段。
第三遍：打开代码文件，一边指文件一边讲。
第四遍：让同学随机问你一个模块，你用“业务含义 -> 代码位置 -> 数据表 -> 设计原因”的结构回答。
```

最终标准：

```text
你不需要能默写代码；
但要能说清楚每条业务线入口在哪里、调哪个 service、改哪些表、为什么这样设计。
```

这就是后端答辩真正需要的熟悉程度。
