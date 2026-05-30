# 后端接口到代码与数据表定位地图

这份文档解决一个很实际的问题：老师随口问一个接口时，你能不能立刻知道该打开哪个文件、哪个函数、哪几张表。

固定定位顺序：

```text
接口地址
-> router 文件
-> schema 参数模型
-> service 业务函数
-> model / 数据表
-> 答辩关键词
```

## 1. 总入口

| 位置 | 作用 | 答辩说法 |
| --- | --- | --- |
| `backend/run_sqlite.py` | 本地演示启动入口，创建 SQLite 演示库并启动 Uvicorn | 本地答辩演示用它启动后端 |
| `backend/app/main.py` | 创建 FastAPI 应用，配置 CORS，注册 routers | 所有接口最终都在这里挂载到 FastAPI |
| `backend/app/database.py` | 创建数据库 engine 和 session | router 通过 `Depends(get_db)` 拿数据库连接 |
| `backend/app/dependencies.py` | 当前用户识别和角色权限 | `require_roles` 决定哪些角色能访问接口 |
| `backend/app/schemas.py` | Pydantic 请求/响应模型 | 前端参数先在这里校验 |
| `backend/app/services.py` | 业务逻辑集中地 | 绝大多数查表、改表和状态流转都在这里 |
| `backend/app/models.py` | SQLAlchemy 数据表模型 | 类名对应数据库表 |

## 2. 登录与权限

| 接口 | router | schema | service | 表/模型 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| `POST /api/auth/login` | `routers/auth.py` | `LoginRequest` | `authenticate_user` | `User` / `users` | 查账号、校验密码哈希、返回 token |
| `POST /api/login` | `routers/legacy.py` | `LegacyLoginRequest` | `authenticate_user` | `User` / `users` | 旧登录接口兼容 |

答辩定位句：

```text
登录先看 routers/auth.py，再看 schemas.LoginRequest，然后看 services.authenticate_user，最后看 models.User。
```

常见追问：

```text
密码不明文保存，登录时用 verify_password 校验 password_hash。
后续接口通过 token 找到当前用户，再由 require_roles 判断权限。
```

## 3. 船员管理

| 接口 | router | schema | service | 表/模型 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/crews` | `routers/crews.py` | 无请求体 | `list_crews` | `Crew`、`User` | 船员列表，关联用户 |
| `POST /api/crews` | `routers/crews.py` | `CrewCreate` | `create_crew` | `User`、`Crew`、`Position`、`OperationLog` | 同时创建账号和船员档案 |
| `GET /api/crews/{crew_id}` | `routers/crews.py` | 路径参数 | `get_crew` | `Crew` | 单个船员 |
| `PUT /api/crews/{crew_id}` | `routers/crews.py` | `CrewUpdate` | `update_crew` | `Crew`、`Position`、`OperationLog` | 修改档案和岗位 |
| `DELETE /api/crews/{crew_id}` | `routers/crews.py` | 路径参数 | `soft_delete_crew` | `Crew`、`OperationLog` | 软删除，状态改 `inactive` |
| `PUT /api/crews/{crew_id}/status` | `routers/legacy.py` | `LegacyCrewStatusUpdate` | `set_crew_sea_status` | `Crew` | 旧页面船员出海状态兼容 |

答辩定位句：

```text
船员模块重点看 routers/crews.py 和 services.create_crew。创建船员会同时写 users 和 crews，通过 crews.user_id 一对一关联。
```

## 4. 证书管理与审核

| 接口 | router | schema | service | 表/模型 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/certificates` | `routers/certificates.py` | 无请求体 | `list_certificates` | `Certificate`、`Crew` | 证书列表 |
| `POST /api/certificates` | `routers/certificates.py` | `CertificateCreate` | `create_certificate` | `Certificate`、`CertificateType`、`OperationLog` | 录入后默认 `pending` |
| `GET /api/certificates/alerts` | `routers/certificates.py` | 无请求体 | `list_certificate_alerts` | `Certificate`、`Crew` | 30 天内到期预警 |
| `PUT /api/certificates/{certificate_id}` | `routers/certificates.py` | `CertificateUpdate` | `update_certificate` | `Certificate`、`CertificateType`、`OperationLog` | 更新证书信息 |
| `PUT /api/certificates/{certificate_id}/review` | `routers/certificates.py` | `CertificateReview` | `review_certificate` | `Certificate`、`CertificateReviewRecord`、`OperationLog` | 审核状态和审核历史 |

答辩定位句：

```text
证书审核看 review_certificate。当前状态存在 certificates，审核历史存在 certificate_review_records。
```

必须记住：

```text
只有 approved 且未过期证书能参与智能匹配和派遣校验。
```

## 5. 船舶、港口、航线、岗位、证书类型

| 接口 | router | schema | service | 表/模型 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/ships` | `routers/ships.py` | 无请求体 | `list_ships` | `Ship`、`ShipCompany` | 船舶列表，船东按自己过滤 |
| `POST /api/ships` | `routers/ships.py` | `ShipCreate` | `create_ship` | `Ship`、`ShipCompany`、`OperationLog` | 创建船舶 |
| `GET /api/positions` | `routers/lookups.py` | 无请求体 | `list_positions` | `Position` | 岗位字典 |
| `POST /api/positions` | `routers/lookups.py` | `PositionCreate` | `create_position` | `Position`、`OperationLog` | 新增岗位 |
| `GET /api/certificate-types` | `routers/lookups.py` | 无请求体 | `list_certificate_types` | `CertificateType` | 证书类型字典 |
| `POST /api/certificate-types` | `routers/lookups.py` | `CertificateTypeCreate` | `create_certificate_type` | `CertificateType`、`OperationLog` | 新增证书类型 |
| `GET /api/ports` | `routers/lookups.py` | 无请求体 | `list_ports` | `Port` | 港口字典 |
| `POST /api/ports` | `routers/lookups.py` | `PortCreate` | `create_port` | `Port`、`OperationLog` | 新增港口 |
| `GET /api/routes` | `routers/lookups.py` | 无请求体 | `list_routes` | `Route`、`Port` | 航线列表 |
| `POST /api/routes` | `routers/lookups.py` | `RouteCreate` | `create_route` | `Route`、`Port`、`OperationLog` | 航线关联起点港和终点港 |

答辩定位句：

```text
这些是实体表和字典表，用来把船舶、航线、岗位、证书类型规范化，避免大量重复字符串。
```

## 6. 岗位需求与智能匹配

| 接口 | router | schema | service | 表/模型 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/jobs` | `routers/jobs.py` | 无请求体 | `list_jobs` | `JobDemand`、`JobRequiredCertificate` | 岗位列表，船东看自己的 |
| `POST /api/jobs` | `routers/jobs.py` | `JobCreate` | `create_job` | `JobDemand`、`JobRequiredCertificate`、`Ship`、`Route`、`Position`、`CertificateType`、`OperationLog` | 发布岗位并写所需证书 |
| `GET /api/jobs/{job_id}` | `routers/jobs.py` | 路径参数 | `get_job` | `JobDemand` | 岗位详情 |
| `PUT /api/jobs/{job_id}/close` | `routers/jobs.py` | 路径参数 | `close_job` | `JobDemand`、`OperationLog` | 关闭岗位 |
| `GET /api/jobs/{job_id}/matches` | `routers/matching.py` | 路径参数 | `list_matching_crews`、`_score_match` | `Crew`、`Certificate`、`VoyageRecord`、`JobDemand`、`JobRequiredCertificate` | 100 分匹配模型 |

匹配分数定位：

```text
_score_match
岗位 40 分
证书满足度 40 分
证书有效期风险 10 分
历史海历 10 分
```

答辩定位句：

```text
匹配接口不是前端写死，真正逻辑在 services._score_match，会查可派遣船员、证书、海历和岗位要求。
```

## 7. 派遣与海历

| 接口 | router | schema | service | 表/模型 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/dispatches` | `routers/dispatches.py` | 无请求体 | `list_dispatches` | `Dispatch`、`Crew`、`JobDemand` | 派遣列表 |
| `GET /api/dispatches/{dispatch_id}` | `routers/dispatches.py` | 路径参数 | `get_dispatch` | `Dispatch`、`DispatchStatusLog`、`Crew`、`JobDemand` | 派遣详情和状态日志 |
| `POST /api/dispatches` | `routers/dispatches.py` | `DispatchCreate` | `create_dispatch`、`_ensure_crew_matches_job` | `Dispatch`、`Crew`、`JobDemand`、`Certificate`、`DispatchStatusLog`、`OperationLog` | 发起派遣，等待船东确认 |
| `PUT /api/dispatches/{dispatch_id}/confirm` | `routers/dispatches.py` | 路径参数 | `confirm_dispatch` | `Dispatch`、`Crew`、`JobDemand`、`DispatchStatusLog`、`OperationLog` | 船东确认 |
| `PUT /api/dispatches/{dispatch_id}/onboard` | `routers/dispatches.py` | 路径参数 | `onboard_dispatch` | `Dispatch`、`Crew`、`VoyageRecord`、`DispatchStatusLog`、`OperationLog` | 上船并生成海历 |
| `PUT /api/dispatches/{dispatch_id}/offboard` | `routers/dispatches.py` | 路径参数 | `offboard_dispatch` | `Dispatch`、`Crew`、`JobDemand`、`VoyageRecord`、`DispatchStatusLog`、`OperationLog` | 下船并补全海历 |
| `PUT /api/dispatches/{dispatch_id}/cancel` | `routers/dispatches.py` | 路径参数 | `cancel_dispatch` | `Dispatch`、`Crew`、`JobDemand`、`VoyageRecord`、`DispatchStatusLog`、`OperationLog` | 取消派遣，恢复状态 |

状态流转定位：

```text
pending_owner -> confirmed -> onboard -> offboard
cancelled 是取消状态
```

答辩定位句：

```text
派遣是状态机。每一步不只是改 dispatches，还会联动 crews、job_demands、voyage_records，并写日志。
```

## 8. 统计首页与日志

| 接口 | router | schema | service | 表/模型 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/dashboard/summary` | `routers/dashboard.py` | 无请求体 | `dashboard_summary` | `Crew`、`Certificate`、`JobDemand`、`Dispatch`、`Ship` | 首页统计卡片 |
| `GET /api/dashboard/crew-status` | `routers/dashboard.py` | 无请求体 | `dashboard_crew_status` | `Crew` | 船员状态分布 |
| `GET /api/dashboard/certificate-alerts` | `routers/dashboard.py` | 无请求体 | `dashboard_certificate_alerts`、`list_certificate_alerts` | `Certificate`、`Crew` | 证书到期预警 |
| `GET /api/dashboard/dispatch-trend` | `routers/dashboard.py` | 无请求体 | `dashboard_dispatch_trend` | `Dispatch` | 按 `created_at` 月份统计 |
| `GET /api/dashboard/route-workload` | `routers/dashboard.py` | 无请求体 | `dashboard_route_workload` | `VoyageRecord`、`JobDemand` | 航线工作量 |
| `GET /api/operation-logs` | `routers/logs.py` | 无请求体 | `list_operation_logs` | `OperationLog` | 最近 100 条操作日志 |
| `GET /api/stats` | `routers/legacy.py` | 无请求体 | `crew_stats` | `Crew` | 旧统计接口兼容 |

答辩定位句：

```text
统计接口集中在 dashboard.py，service 层从多张业务表汇总数据，前端只负责展示。
```

日志区别：

```text
operation_logs：系统级操作审计。
dispatch_status_logs：派遣状态流转历史。
```

## 9. 旧版海历兼容接口

| 接口 | router | schema | service / 逻辑 | 表/模型 | 关键词 |
| --- | --- | --- | --- | --- | --- |
| `GET /api/voyages` | `routers/legacy.py` | 无请求体 | `_list_legacy_voyages` | `VoyageRecord`、`Crew`、`Dispatch`、`JobDemand` | 旧海历列表 |
| `POST /api/voyages` | `routers/legacy.py` | `LegacyVoyageCreate` | 复用 `create_dispatch`、`confirm_dispatch`、`onboard_dispatch` | `Dispatch`、`VoyageRecord` | 旧页面创建海历兼容 |
| `GET /api/my-profile/{crew_id}` | `routers/legacy.py` | 路径参数 | 直接查 `Crew` | `Crew`、`User` | 船员个人档案 |
| `GET /api/my-voyages/{crew_id}` | `routers/legacy.py` | 路径参数 | `_list_legacy_voyages` | `VoyageRecord` | 船员个人海历 |

答辩定位句：

```text
legacy.py 主要是兼容旧静态前端。核心新业务仍然主讲 auth、crews、certificates、jobs、matching、dispatches、dashboard。
```

## 10. 你被问到接口时怎么快速找

### 10.1 看前缀找 router

| URL 前缀 | 文件 |
| --- | --- |
| `/api/auth` | `routers/auth.py` |
| `/api/crews` | `routers/crews.py` |
| `/api/certificates` | `routers/certificates.py` |
| `/api/ships` | `routers/ships.py` |
| `/api/positions`、`/api/certificate-types`、`/api/ports`、`/api/routes` | `routers/lookups.py` |
| `/api/jobs` | `routers/jobs.py` 或 `routers/matching.py` |
| `/api/dispatches` | `routers/dispatches.py` |
| `/api/dashboard` | `routers/dashboard.py` |
| `/api/operation-logs` | `routers/logs.py` |
| 旧 `/api/login`、`/api/voyages` | `routers/legacy.py` |

### 10.2 看请求体找 schema

| 请求体 | schema |
| --- | --- |
| 登录 | `LoginRequest` |
| 创建船员 | `CrewCreate` |
| 修改船员 | `CrewUpdate` |
| 录入证书 | `CertificateCreate` |
| 更新证书 | `CertificateUpdate` |
| 审核证书 | `CertificateReview` |
| 创建船舶 | `ShipCreate` |
| 创建岗位/证书类型/港口/航线 | `PositionCreate`、`CertificateTypeCreate`、`PortCreate`、`RouteCreate` |
| 发布岗位需求 | `JobCreate` |
| 发起派遣 | `DispatchCreate` |

### 10.3 看业务找 service

| 业务 | service |
| --- | --- |
| 登录 | `authenticate_user` |
| 船员 | `list_crews`、`create_crew`、`update_crew`、`soft_delete_crew` |
| 证书 | `create_certificate`、`review_certificate`、`list_certificate_alerts` |
| 字典表 | `create_position`、`create_certificate_type`、`create_port`、`create_route` |
| 船舶 | `list_ships`、`create_ship` |
| 岗位 | `create_job`、`close_job` |
| 匹配 | `list_matching_crews`、`_score_match` |
| 派遣 | `create_dispatch`、`confirm_dispatch`、`onboard_dispatch`、`offboard_dispatch`、`cancel_dispatch` |
| 统计 | `dashboard_summary`、`dashboard_crew_status`、`dashboard_dispatch_trend`、`dashboard_route_workload` |
| 日志 | `_add_operation_log`、`_append_dispatch_status_log`、`list_operation_logs` |

## 11. 最短答辩模板

老师问某接口时，你可以直接套：

```text
这个接口入口在 routers/xxx.py，参数由 schemas.py 里的 xxx 模型校验，业务逻辑在 services.py 的 xxx 函数。
它主要查/改 xxx 表，返回前端需要的 JSON。
这样设计的原因是把接口、校验、业务和数据库模型分层，便于维护，也能清楚体现数据库表关系。
```

例如问智能匹配：

```text
智能匹配接口是 GET /api/jobs/{job_id}/matches，入口在 routers/matching.py，调用 services.list_matching_crews 和 _score_match。
它会查询可派遣船员、证书、海历和岗位要求，按岗位 40 分、证书 40 分、证书风险 10 分、海历 10 分计算匹配分，最后返回 60 分以上结果和匹配原因。
```
