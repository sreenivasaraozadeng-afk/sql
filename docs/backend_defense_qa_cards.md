# 后端答辩追问问答卡

这份文档用来模拟老师追问。你不需要逐字背，但要能用自己的话说出同样意思。

回答问题时固定用这个结构：

```text
先说业务含义 -> 再说代码位置 -> 再说涉及的数据表 -> 最后说为什么这样设计
```

## 一、后端整体结构

### Q1：你们后端为什么要分 `routers`、`schemas`、`services`、`models`？

答：

> 这是分层设计。`routers` 负责接口地址、请求方法和权限控制；`schemas` 负责校验前端传来的参数；`services` 负责真正的业务逻辑；`models` 负责数据库表映射。这样每一层职责清楚，后期修改接口或数据库时不会互相混乱。

补充代码：

```text
routers: backend/app/routers/*.py
schemas: backend/app/schemas.py
services: backend/app/services.py
models: backend/app/models.py
```

### Q2：一个前端请求进入后端后，大概经过哪些步骤？

答：

> 以前端请求为例，首先进入对应的 router 函数，然后 Pydantic schema 校验请求参数，再通过 dependency 获取数据库 session 和当前用户，接着调用 service 函数执行业务逻辑，service 通过 SQLAlchemy model 查询或修改数据库，最后返回统一 JSON 给前端。

简化链路：

```text
前端 -> router -> schema -> dependency -> service -> model -> database -> JSON
```

### Q3：为什么后端接口返回都带 `success`、`message`、`data`？

答：

> 这是统一响应格式。前端拿到结果后可以先看 `success` 判断是否成功，`message` 用来显示提示，`data` 保存真正的数据。这样前后端约定清晰，页面处理起来更简单。

## 二、登录和权限

### Q4：登录接口怎么实现？

答：

> 登录接口是 `POST /api/auth/login`，路由在 `routers/auth.py`。它接收 `LoginRequest`，调用 `services.authenticate_user` 查询 `users` 表并校验密码哈希。校验成功后调用 `create_access_token` 生成 token，返回给前端。

关键代码：

```text
routers/auth.py -> login
services.py -> authenticate_user
passwords.py -> verify_password
security.py -> create_access_token
```

### Q5：为什么不把密码明文存在数据库？

答：

> 明文密码有安全风险。系统使用 `hash_password` 把密码加盐并哈希后保存到 `users.password_hash`。登录时用 `verify_password` 对用户输入再次哈希，然后和数据库中的哈希值比较。

### Q6：token 里保存了什么？

答：

> token 中主要保存用户 id、角色、签发时间和过期时间。后续接口可以根据 token 判断当前用户是谁，以及他有没有权限执行某个操作。

### Q7：权限控制在哪里做？

答：

> 权限控制主要在 `dependencies.py` 的 `require_roles`。路由函数通过 `Depends(require_roles(...))` 指定允许访问的角色。如果当前用户角色不在允许列表中，后端会返回 403。

例子：

```text
证书审核: cert_admin/admin
创建派遣: manager/admin
船东确认: shipowner/admin
```

## 三、船员管理

### Q8：为什么创建船员时要同时创建 `users` 和 `crews`？

答：

> 因为 `users` 表负责登录账号和角色，`crews` 表负责船员业务档案。一个船员既需要能登录系统，又需要保存姓名、身份证、电话、岗位、状态等业务信息，所以创建船员时会同时写两张表，并通过 `crews.user_id` 外键关联。

### Q9：`users` 和 `crews` 是什么关系？

答：

> 一对一关系。`crews.user_id` 外键指向 `users.id`，并且设置了唯一约束，保证一个登录账号最多对应一个船员档案。

### Q10：为什么删除船员不是直接删除数据？

答：

> 系统采用软删除，把 `crews.status` 改为 `inactive`。这样可以保留历史证书、派遣和海历记录，避免删除后历史数据断裂。

### Q11：船员有哪些状态？

答：

```text
available: 在岸可派遣
pending: 待上船
at_sea: 出海中
inactive: 已停用
```

## 四、证书审核

### Q12：证书刚录入时为什么是 `pending`？

答：

> 因为证书需要经过证书管理员审核。刚录入的证书可能还没有确认真实性，所以默认是 `pending`，不能直接参与岗位匹配。

### Q13：证书审核状态有哪些？

答：

```text
pending: 待审核
approved: 审核通过
rejected: 审核拒绝
```

### Q14：`certificates` 和 `certificate_review_records` 有什么区别？

答：

> `certificates` 保存证书当前状态，比如当前是通过还是拒绝；`certificate_review_records` 保存每一次审核历史，比如从什么状态变成什么状态、谁审核、备注是什么。一个看当前结果，一个看历史过程。

### Q15：智能匹配为什么只认可审核通过的证书？

答：

> 因为派遣是高风险业务，只有证书管理员确认真实有效的证书才能作为岗位匹配依据。代码中 `_valid_certificate_types` 明确要求 `review_status == "approved"` 且 `expires_at >= today`。

### Q16：如果证书审核通过但已经过期，还能匹配吗？

答：

> 不能。系统要求同时满足两个条件：审核通过、未过期。过期证书即使曾经通过审核，也不能证明当前有效。

## 五、岗位需求和智能匹配

### Q17：岗位需求表为什么还要有 `job_required_certificates`？

答：

> 因为一个岗位需求可能要求多个证书，这是一个一对多关系。把证书要求单独放到 `job_required_certificates` 表，避免在岗位表中用字符串拼接多个证书，更符合数据库规范化设计。

### Q18：智能匹配的分数怎么来的？

答：

> 满分 100 分，岗位匹配 40 分，证书满足度 40 分，证书有效期风险 10 分，历史海历经验 10 分。系统会给每个可派遣船员打分，并返回匹配原因。

### Q19：为什么只匹配 `available` 船员？

答：

> 因为只有在岸可派遣的船员才能被安排新岗位。待上船、出海中、已停用的船员都不应该进入推荐列表。

### Q20：为什么只返回 60 分以上？

答：

> 60 分是推荐门槛。低于 60 分说明岗位、证书或经验存在明显不足，系统不推荐给经理，减少无效选择。

### Q21：匹配结果为什么要返回原因？

答：

> 这是可解释匹配。经理不仅要知道谁分数高，还要知道为什么高，比如岗位完全匹配、证书齐全、有效期充足、有相近海历。这样比黑箱推荐更适合课程设计展示。

### Q22：为什么匹配之后创建派遣还要再次校验？

答：

> 因为前端推荐结果可能不是最新状态，也可能被绕过直接调用接口。后端必须在创建派遣前再次检查船员状态、岗位、证书和岗位人数，保证业务规则最终由后端控制。

## 六、派遣流程

### Q23：派遣状态有哪些？

答：

```text
pending_owner: 待船东确认
confirmed: 已确认
onboard: 已上船
offboard: 已下船
cancelled: 已取消
```

正常流程：

```text
pending_owner -> confirmed -> onboard -> offboard
```

### Q24：创建派遣时会检查哪些条件？

答：

> 会检查岗位是否可派遣、岗位人数是否已满、船员是否 `available`、岗位是否匹配、船员是否已有进行中派遣、证书是否审核通过且未过期并满足岗位要求。

### Q25：船东确认后哪些数据会变化？

答：

> `dispatches.status` 从 `pending_owner` 变成 `confirmed`；`confirmed_by_user_id` 记录确认人；`crews.status` 从 `available` 变成 `pending`；如果岗位人数已满，`job_demands.status` 可能变成 `matched`。

### Q26：什么时候生成海历？

答：

> 确认上船时生成海历。因为海历代表真实出海经历，只有派遣进入 `onboard` 后才说明船员实际上船。

### Q27：下船后会改哪些数据？

答：

> 派遣状态变为 `offboard`，船员状态恢复 `available`，岗位状态变成 `closed`，海历记录补充 `offboard_at` 下船时间，并把海历状态改为 `offboard`。

### Q28：`dispatches` 和 `dispatch_status_logs` 有什么区别？

答：

> `dispatches` 保存派遣当前状态；`dispatch_status_logs` 保存状态变化历史。比如当前状态是 `onboard`，但日志能看到它曾经从 `pending_owner` 到 `confirmed` 再到 `onboard`。

## 七、统计和日志

### Q29：首页统计数据从哪里来？

答：

> 来自后端 dashboard 接口。后端通过 SQLAlchemy 查询 `crews`、`certificates`、`job_demands`、`dispatches`、`ships`、`voyage_records` 等表，按状态、月份、航线汇总数据，前端只负责展示。

### Q30：月度派遣趋势按什么统计？

答：

> 按 `dispatches.created_at` 的年月统计每个月创建了多少派遣记录。

### Q31：航线工作量为什么查 `voyage_records`？

答：

> 因为工作量应该根据实际或已发生的海历统计，而不是只看岗位需求。`voyage_records` 记录真实上船航线，更能反映航线工作量。

### Q32：`operation_logs` 记录什么？

答：

> 记录谁在什么时间对什么对象做了什么操作，包括操作人、动作、目标类型、目标 id、详情和时间。

### Q33：`operation_logs` 和 `dispatch_status_logs` 有什么区别？

答：

> `operation_logs` 是通用操作审计，记录创建、修改、审核、确认等用户行为；`dispatch_status_logs` 专门记录派遣状态流转，用于追踪派遣流程。

## 八、数据库设计追问

### Q34：你的系统哪里体现外键？

答：

> 比如 `crews.user_id` 指向 `users.id`，`certificates.crew_id` 指向 `crews.id`，`dispatches.job_id` 指向 `job_demands.id`，`dispatches.crew_id` 指向 `crews.id`，`voyage_records.dispatch_id` 指向 `dispatches.id`。这些外键保证业务数据之间有关联，不是孤立存储。

### Q35：你的系统哪里体现唯一约束？

答：

> 比如 `users.username` 唯一，保证账号不能重复；`crews.id_card` 唯一，保证身份证不能重复；`certificates.certificate_no` 唯一，保证证书编号不能重复；`crews.user_id` 唯一，保证一个账号只对应一个船员档案。

### Q36：你的系统哪里体现检查约束？

答：

> 状态字段和枚举字段用了检查约束，比如用户角色、船员状态、证书审核状态、派遣状态等只能取系统规定的值，避免数据库中出现非法状态。

### Q37：为什么要有字典表？

答：

> 岗位、证书类型、船舶、航线这些信息如果都用普通字符串，会造成重复和不一致。使用 `positions`、`certificate_types`、`ships`、`routes` 等字典表或实体表，可以统一管理基础数据。

### Q38：为什么说这个系统符合规范化设计？

答：

> 因为系统把不同主题拆成不同表，例如用户、船员、证书、岗位需求、派遣、海历、日志分别建表，避免大量重复字段；多对一和一对多关系通过外键表达；多值字段如岗位所需证书单独建子表，而不是用逗号拼接。

## 九、运行调试追问

### Q39：如果后端返回 404，你怎么查？

答：

> 先确认接口地址和请求方法是否正确，然后打开 `http://127.0.0.1:3000/docs` 看 FastAPI 自动生成的接口文档。如果接口文档里没有这个地址，说明请求路径写错或路由没有注册。

### Q40：如果后端返回 401 或 403，有什么区别？

答：

> 401 通常表示没有登录或 token 无效；403 表示已经登录，但角色权限不够。比如普通船员没有证书审核权限，就会是 403。

### Q41：如果出现端口占用怎么办？

答：

> Windows 上可以用 `netstat -ano | findstr :3000` 查看占用 3000 端口的进程号，然后用 `taskkill /PID 进程号 /F` 结束旧进程，或者换一个端口启动。

### Q42：如果出现数据库字段不存在，比如 `no such column`，说明什么？

答：

> 通常说明 ORM 模型和数据库实际表结构不一致。比如模型新增了字段，但旧数据库没有这个列。本地 SQLite 演示用 `run_sqlite.py` 会重建表，可以解决旧结构问题；正式 MySQL 环境则需要重新导入或迁移数据库结构。

## 十、现场回答兜底句

如果老师问得很细，一时想不起代码行，可以这样回答：

> 这个逻辑在后端 service 层实现，路由层只负责接收请求和权限控制。具体数据表由 SQLAlchemy model 映射，业务修改会通过数据库 session 提交。这个问题我可以从接口地址顺着 router、schema、service、model 四层定位。

如果老师问为什么这样设计：

> 我们这样设计主要是为了让业务关系清楚、数据约束明确、流程可追踪。数据库课程设计重点不只是页面展示，而是让表结构、外键、约束、状态流转和统计查询能够支撑完整业务。

