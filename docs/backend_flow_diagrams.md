# 后端流程图学习笔记

这份文档用图帮你建立后端代码的空间感。你看代码时不要只盯一行一行，要先知道这段代码属于哪条链路。

## 1. 整体请求链路

```mermaid
flowchart LR
    A["前端页面"] --> B["API 请求"]
    B --> C["routers 路由层"]
    C --> D["schemas 参数校验"]
    C --> E["dependencies 权限/数据库依赖"]
    D --> F["services 业务逻辑"]
    E --> F
    F --> G["models ORM 模型"]
    G --> H["数据库表"]
    H --> F
    F --> I["统一 JSON 响应"]
    I --> A
```

对应代码：

- `backend/app/routers/*.py`：接口入口。
- `backend/app/schemas.py`：检查请求参数。
- `backend/app/dependencies.py`：提供数据库连接和角色权限。
- `backend/app/services.py`：业务逻辑。
- `backend/app/models.py`：数据库表映射。

你要记住：

```text
routers 不做复杂业务，复杂业务交给 services。
schemas 不写数据库，只负责参数是否合格。
models 不处理流程，只描述表结构和关系。
```

## 2. 登录流程

接口：

```text
POST /api/auth/login
```

```mermaid
sequenceDiagram
    participant F as 前端
    participant R as routers/auth.py
    participant S as schemas.py
    participant SV as services.py
    participant P as passwords.py
    participant SEC as security.py
    participant DB as users 表

    F->>R: 提交 username/password
    R->>S: LoginRequest 校验
    R->>SV: authenticate_user(db, payload)
    SV->>DB: 按 username 查询用户
    DB-->>SV: 返回 User
    SV->>P: verify_password
    P-->>SV: 密码是否正确
    SV-->>R: 返回 User
    R->>SEC: create_access_token(user.id, user.role)
    SEC-->>R: 返回 token
    R-->>F: success + token + user
```

答辩关键词：

```text
参数校验、用户表查询、密码哈希校验、token、角色权限
```

## 3. 创建船员流程

接口：

```text
POST /api/crews
```

```mermaid
sequenceDiagram
    participant F as 前端
    participant R as routers/crews.py
    participant S as schemas.py
    participant D as dependencies.py
    participant SV as services.py
    participant U as users 表
    participant C as crews 表
    participant L as operation_logs 表

    F->>R: 提交船员账号和档案
    R->>S: CrewCreate 校验
    R->>D: 检查 manager/admin 权限
    R->>SV: create_crew(db, payload, current_user)
    SV->>U: 创建 User 登录账号
    SV->>C: 创建 Crew 船员档案
    C-->>U: crews.user_id 外键关联 users.id
    SV->>L: 写 create crew 操作日志
    SV-->>R: 返回船员数据
    R-->>F: 船员创建成功
```

表关系：

```mermaid
erDiagram
    users ||--o| crews : "user_id"
    positions ||--o{ crews : "position_id"
    crews ||--o{ certificates : "crew_id"
    crews ||--o{ dispatches : "crew_id"
    crews ||--o{ voyage_records : "crew_id"
```

答辩关键词：

```text
users 负责登录，crews 负责业务档案，一对一外键关联
```

## 4. 证书审核流程

接口：

```text
POST /api/certificates
PUT /api/certificates/{certificate_id}/review
```

```mermaid
stateDiagram-v2
    [*] --> pending: 证书录入
    pending --> approved: 审核通过
    pending --> rejected: 审核拒绝
    rejected --> approved: 重新审核通过
    approved --> rejected: 复核不通过
```

审核写库流程：

```mermaid
flowchart TD
    A["证书管理员提交审核"] --> B["CertificateReview 校验 review_status"]
    B --> C["services.review_certificate"]
    C --> D["修改 certificates 当前状态"]
    C --> E["记录 reviewed_by_user_id / reviewed_at / review_remark"]
    C --> F["新增 certificate_review_records 审核历史"]
    C --> G["新增 operation_logs 操作日志"]
    D --> H["返回证书数据"]
```

证书能参与匹配的条件：

```mermaid
flowchart LR
    A["证书"] --> B{"review_status == approved?"}
    B -- 否 --> X["不能参与匹配"]
    B -- 是 --> C{"expires_at >= today?"}
    C -- 否 --> X
    C -- 是 --> Y["可以参与匹配"]
```

答辩关键词：

```text
当前状态在 certificates，历史审核在 certificate_review_records。
只有 approved 且未过期证书参与智能匹配。
```

## 5. 岗位需求和智能匹配流程

接口：

```text
POST /api/jobs
GET /api/jobs/{job_id}/matches
```

岗位需求关系：

```mermaid
erDiagram
    job_demands ||--o{ job_required_certificates : "job_id"
    ships ||--o{ job_demands : "ship_id"
    routes ||--o{ job_demands : "route_id"
    positions ||--o{ job_demands : "position_id"
```

匹配流程：

```mermaid
flowchart TD
    A["经理选择岗位需求 job_id"] --> B["GET /api/jobs/{job_id}/matches"]
    B --> C["查询 JobDemand 和 required_certificates"]
    C --> D["查询 status=available 的船员"]
    D --> E["加载船员证书和海历"]
    E --> F["_score_match 逐个算分"]
    F --> G{"match_score >= 60?"}
    G -- 否 --> H["不返回"]
    G -- 是 --> I["加入推荐列表"]
    I --> J["按分数倒序返回"]
```

评分模型：

```mermaid
pie title 智能匹配评分构成
    "岗位匹配" : 40
    "证书满足度" : 40
    "证书有效期风险" : 10
    "历史海历经验" : 10
```

答辩关键词：

```text
不是简单查询，是可解释评分模型。
返回 match_score、match_reasons、missing_certificates、certificate_risk。
```

## 6. 派遣状态流转

接口：

```text
POST /api/dispatches
PUT /api/dispatches/{id}/confirm
PUT /api/dispatches/{id}/onboard
PUT /api/dispatches/{id}/offboard
PUT /api/dispatches/{id}/cancel
```

状态机：

```mermaid
stateDiagram-v2
    [*] --> pending_owner: 经理创建派遣
    pending_owner --> confirmed: 船东确认
    confirmed --> onboard: 经理确认上船
    onboard --> offboard: 经理确认下船
    pending_owner --> cancelled: 取消
    confirmed --> cancelled: 取消
    onboard --> cancelled: 异常取消
    offboard --> [*]
    cancelled --> [*]
```

表联动：

```mermaid
flowchart TD
    A["创建派遣"] --> B["dispatches.status = pending_owner"]
    B --> C["写 dispatch_status_logs"]
    C --> D["船东确认"]
    D --> E["dispatches.status = confirmed"]
    E --> F["crews.status = pending"]
    F --> G["确认上船"]
    G --> H["dispatches.status = onboard"]
    H --> I["crews.status = at_sea"]
    I --> J["新增 voyage_records"]
    J --> K["确认下船"]
    K --> L["dispatches.status = offboard"]
    L --> M["crews.status = available"]
    M --> N["job_demands.status = closed"]
    N --> O["voyage_records 补 offboard_at"]
```

创建派遣前的后端校验：

```mermaid
flowchart TD
    A["create_dispatch"] --> B{"岗位是否 open/matched?"}
    B -- 否 --> X["拒绝"]
    B -- 是 --> C{"岗位人数是否已满?"}
    C -- 是 --> X
    C -- 否 --> D{"船员是否 available?"}
    D -- 否 --> X
    D -- 是 --> E{"岗位是否匹配?"}
    E -- 否 --> X
    E -- 是 --> F{"是否已有进行中派遣?"}
    F -- 是 --> X
    F -- 否 --> G{"证书是否有效且满足要求?"}
    G -- 否 --> X
    G -- 是 --> H["创建派遣"]
```

答辩关键词：

```text
派遣是状态机；状态变化写 dispatch_status_logs；上船自动生成海历。
```

## 7. 统计首页和日志

接口：

```text
GET /api/dashboard/summary
GET /api/dashboard/crew-status
GET /api/dashboard/certificate-alerts
GET /api/dashboard/dispatch-trend
GET /api/dashboard/route-workload
GET /api/operation-logs
```

统计数据来源：

```mermaid
flowchart LR
    A["dashboard 页面"] --> B["dashboard.py 路由"]
    B --> C["dashboard_summary"]
    B --> D["dashboard_crew_status"]
    B --> E["dashboard_certificate_alerts"]
    B --> F["dashboard_dispatch_trend"]
    B --> G["dashboard_route_workload"]
    C --> H["crews / certificates / jobs / dispatches / ships"]
    D --> I["crews.status"]
    E --> J["certificates.expires_at"]
    F --> K["dispatches.created_at"]
    G --> L["voyage_records.route"]
```

日志区别：

```mermaid
flowchart TD
    A["日志"] --> B["operation_logs"]
    A --> C["dispatch_status_logs"]
    B --> D["记录谁做了什么操作"]
    C --> E["记录派遣状态从什么变成什么"]
```

答辩关键词：

```text
前端负责展示，后端负责统计，数据库负责保存真实业务数据。
```

## 8. 复习时怎么用这份图

每看一张图，就打开对应代码：

| 图 | 对应代码 |
| --- | --- |
| 整体请求链路 | `main.py`、`dependencies.py` |
| 登录流程 | `routers/auth.py`、`services.authenticate_user` |
| 创建船员 | `routers/crews.py`、`services.create_crew` |
| 证书审核 | `routers/certificates.py`、`services.review_certificate` |
| 智能匹配 | `routers/matching.py`、`services._score_match` |
| 派遣状态流转 | `routers/dispatches.py`、派遣相关 service |
| 统计首页 | `routers/dashboard.py`、dashboard service |

你最终要做到：

```text
看到图能说代码，看到代码能画图。
```

