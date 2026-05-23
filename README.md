# 出海船员管理系统

本项目基于原仓库 [DEmons-art/SeafarerManagementSystem_DBwork](https://github.com/DEmons-art/SeafarerManagementSystem_DBwork) 继续开发。原项目主要围绕船员基础档案、出海状态和航次记录展开；当前分支将后端从 Node.js + Express 迁移为 Python FastAPI，并进一步扩展为“船员、证书、岗位、派遣、海历”的后端 MVP。

当前分支重点面向四人小组分工协作：前端同学负责页面和交互，后端同学负责 API 与业务规则，数据库同学负责表结构/ER 图/初始化数据，论文同学负责系统分析、模块设计和测试说明。

## 当前分支改动概览

- 后端由 `backend/server.js` 迁移为 `backend/app/main.py` FastAPI 应用。
- 后端拆分为模块化路由：`auth`、`crews`、`certificates`、`jobs`、`matching`、`dispatches`。
- 新增 JWT 登录认证和角色权限控制。
- 数据库从原来的船员/航次简化结构扩展为 MVP 核心表：
  `users`、`crews`、`certificates`、`job_demands`、`job_required_certificates`、`dispatches`、`voyage_records`。
- 新增证书到期预警、岗位规则匹配、派遣确认、上船、下船等业务流转。
- 使用 Docker Compose 统一启动 MySQL、FastAPI 后端和 Nginx 前端。
- 新增后端接口契约测试和 Docker 配置测试，便于提交前验证。

## 技术栈

```text
后端框架：FastAPI
ASGI 服务：Uvicorn
数据库：MySQL 8
ORM：SQLAlchemy
数据库驱动：PyMySQL
认证方式：JWT-like HMAC token
密码存储：PBKDF2-SHA256 哈希
测试：unittest + FastAPI TestClient
部署/启动：Docker Compose
```

## 目录结构

```text
SeafarerManagementSystem_DBwork/
├─ backend/
│  ├─ app/
│  │  ├─ main.py              # FastAPI 应用入口
│  │  ├─ database.py          # 数据库连接
│  │  ├─ dependencies.py      # 登录用户与角色权限依赖
│  │  ├─ models.py            # SQLAlchemy 数据模型
│  │  ├─ schemas.py           # Pydantic 请求/响应模型
│  │  ├─ services.py          # 核心业务规则
│  │  ├─ security.py          # Token 生成与校验
│  │  ├─ passwords.py         # 密码哈希与校验
│  │  └─ routers/             # 分模块 API 路由
│  ├─ tests/                  # 后端接口和配置测试
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ README.md
├─ frontend/                  # 原 HTML 前端页面与 Nginx 配置
├─ init.sql                   # MySQL 初始化脚本
├─ docker-compose.yml         # MySQL + 后端 + 前端编排
└─ README.md
```

## 一键启动

开发环境推荐使用 Docker Desktop。在项目根目录执行：

```powershell
docker compose up --build
```

访问地址：

```text
前端页面：http://localhost:8080
后端接口：http://localhost:3000
接口文档：http://localhost:3000/docs
健康检查：http://localhost:3000/health
```

如果已经启动过旧版本数据库，MySQL 数据卷中仍是旧表结构。开发阶段需要重建数据库卷：

```powershell
docker compose down -v
docker compose up --build
```

注意：`docker compose down -v` 会清空 Docker 中的 MySQL 数据，仅适合开发阶段重置。

## 演示账号

`init.sql` 和测试种子数据内置了以下账号：

| 账号 | 密码 | 角色 | 用途 |
| --- | --- | --- | --- |
| `admin` | `admin123` | `admin` | 系统管理员 |
| `manager` | `manager123` | `manager` | 业务经理 |
| `cert_admin` | `cert123` | `cert_admin` | 证书管理员 |
| `owner` | `owner123` | `shipowner` | 船东甲 |
| `other_owner` | `owner123` | `shipowner` | 船东乙 |
| `crew01` | `123456` | `seafarer` | 示例船员 |

## 后端已完成功能

### 登录与权限

- `POST /api/auth/login` 登录并返回 token。
- 使用 `Authorization: Bearer <token>` 调用受保护接口。
- 当前角色固定为：
  `seafarer`、`manager`、`cert_admin`、`shipowner`、`admin`。
- 已实现基础角色限制，例如船东不能新增船员，证书/岗位/派遣等核心接口需要登录授权；为兼容旧 HTML 页面，船员列表等少量旧接口允许无 token 访问。

### 船员档案

- `GET /api/crews` 查询船员列表。
- `POST /api/crews` 新增船员，同时创建登录用户。
- `GET /api/crews/{id}` 查询船员详情。
- `PUT /api/crews/{id}` 修改船员资料。
- `DELETE /api/crews/{id}` 软删除船员，将状态改为 `inactive`，保留历史派遣与海历。

船员状态：

```text
available  在岸可派遣
pending    已确认派遣，等待上船
at_sea     出海中
inactive   停用/软删除
```

### 证书管理

- `GET /api/certificates` 查询证书列表。
- `POST /api/certificates` 录入证书。
- `PUT /api/certificates/{id}` 修改证书。
- `GET /api/certificates/alerts` 查询 30 天内即将到期的证书。
- 证书是否过期不单独存字段，由后端根据 `expires_at` 动态计算。

### 岗位需求

- `GET /api/jobs` 查询岗位列表。
- `POST /api/jobs` 船东发布岗位。
- `GET /api/jobs/{id}` 查询岗位详情。
- `PUT /api/jobs/{id}/close` 关闭岗位。
- 岗位可配置所需岗位、上船时间、招聘人数和所需证书。

岗位状态：

```text
open     招聘中
matched  已有派遣匹配
closed   已关闭
```

### 智能匹配

- `GET /api/jobs/{id}/matches` 根据岗位要求推荐船员。
- 当前匹配规则为：
  船员状态为 `available`；
  船员岗位等于岗位要求；
  船员拥有岗位所需证书；
  对应证书未过期。

### 派遣流程

- `POST /api/dispatches` 业务经理发起派遣。
- `PUT /api/dispatches/{id}/confirm` 船东确认派遣。
- `PUT /api/dispatches/{id}/onboard` 业务经理确认上船。
- `PUT /api/dispatches/{id}/offboard` 业务经理确认下船。
- `PUT /api/dispatches/{id}/cancel` 取消派遣。

派遣状态：

```text
pending_owner  待船东确认
confirmed      已确认，等待上船
onboard        已上船
offboard       已下船
cancelled      已取消
```

核心业务规则：

- 已出海、停用或已有进行中派遣的船员不能再次派遣。
- 证书过期或缺少岗位所需证书的船员不能被匹配和派遣。
- 船东只能确认自己发布岗位对应的派遣。
- 确认派遣后船员状态变为 `pending`。
- 确认上船后船员状态变为 `at_sea`，并生成海历记录。
- 确认下船后船员状态变为 `available`，并补全海历下船时间。

## 与前端同学的交接

当前后端同时提供新版 MVP 接口和旧 HTML 前端兼容接口。旧页面暂时不用大改，可以继续调用：

- `POST /api/login`
- `GET /api/crews`、`POST /api/crews`、`DELETE /api/crews/{id}`
- `PUT /api/crews/{id}/status`
- `GET /api/stats`
- `GET /api/voyages`、`POST /api/voyages`
- `GET /api/my-profile/{id}`、`GET /api/my-voyages/{id}`

后续如果前端有时间重构，仍建议逐步迁移到新版 token 接口，例如 `/api/auth/login`、`/api/jobs`、`/api/dispatches` 等。新版通用响应格式：

```json
{
  "success": true,
  "message": "操作成功",
  "data": {}
}
```

登录示例：

```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "manager",
  "password": "manager123"
}
```

登录后前端保存 `data.access_token`，后续请求带上：

```http
Authorization: Bearer <access_token>
```

建议前端优先实现的页面：

- 登录页：调用 `/api/auth/login`。
- 船员管理页：对接 `/api/crews`。
- 证书管理页：对接 `/api/certificates` 和 `/api/certificates/alerts`。
- 岗位需求页：对接 `/api/jobs`。
- 派遣匹配页：对接 `/api/jobs/{id}/matches` 和 `/api/dispatches`。

## 与数据库设计同学的交接

当前最小数据库结构已经在 `init.sql` 中落地，数据库同学可以在此基础上完善 ER 图、字段说明和索引说明。

核心表说明：

| 表名 | 作用 |
| --- | --- |
| `users` | 登录账号、密码哈希、角色 |
| `crews` | 船员档案，与 `users` 一对一 |
| `certificates` | 船员证书，与 `crews` 多对一 |
| `job_demands` | 船东发布的岗位需求 |
| `job_required_certificates` | 岗位所需证书 |
| `dispatches` | 派遣流程记录 |
| `voyage_records` | 上船/下船形成的海历记录 |

后续数据库可优化方向：

- 为论文补充 ER 图和数据字典。
- 确认是否要加入证书审核状态、附件地址、软删除时间等字段。
- 评估是否需要更多组合索引，例如岗位状态 + 上船时间、船员状态 + 岗位。
- 正式开发建议引入 Alembic，不再只依赖 `init.sql` 重建数据库。

## 与论文同学的交接

论文可围绕以下模块展开：

- 用户登录与角色权限模块。
- 船员档案管理模块。
- 证书管理与到期预警模块。
- 船东岗位需求模块。
- 船员岗位匹配模块。
- 派遣审批与海历生成模块。

可以绘制的流程图：

- 登录认证流程。
- 船东发布岗位到业务经理匹配船员流程。
- 派遣状态流转流程。
- 上船/下船生成海历流程。
- 证书到期预警流程。

可以写入论文的后端亮点：

- 使用 FastAPI 自动生成接口文档。
- 使用 SQLAlchemy 将数据库表映射为后端模型。
- 使用角色权限控制不同用户操作范围。
- 使用规则匹配实现岗位推荐。
- 使用状态机思想控制派遣流程。
- 使用自动化测试保障接口契约和核心业务规则。

## 运行测试

在 `backend` 目录执行：

```powershell
..\.venv\Scripts\python.exe -m unittest tests.test_api_contract tests.test_docker_configuration -v
```

当前测试覆盖：

- 登录成功、密码错误、无 token、角色无权限。
- 船员新增、修改、查询、软删除。
- 证书录入、过期判断、30 天到期预警。
- 岗位发布、岗位关闭、岗位所需证书保存。
- 匹配接口只返回在岸且证书满足要求的船员。
- 派遣完整流程：发起派遣、船东确认、上船、下船。
- 异常流程：重复派遣、过期证书派遣、非岗位船东确认派遣。
- Docker Compose 和初始化 SQL 基础配置。

## 当前还未落实的内容

- 面向新版前端的派遣列表、派遣详情、海历列表等查询接口。
- 分页、搜索、筛选。
- 证书图片/PDF 附件上传。
- 证书审核流程。
- 系统通知。
- 操作日志审计。
- Alembic 数据库迁移。
- 完整 Docker 容器联调验证。

## 后续可开发方向

建议按优先级继续开发：

1. 补充面向新版前端的派遣列表、派遣详情、海历列表接口，方便前端展示流程结果。
2. 逐步把旧 HTML 页面从兼容接口迁移到新版 token 接口。
3. 给船员、证书、岗位、派遣列表增加分页、搜索和状态筛选。
4. 引入 Alembic 管理数据库结构变更。
5. 增加证书附件上传与审核流程。
6. 增加通知系统：证书到期、派遣确认、上船/下船提醒。
7. 增加操作日志审计，方便管理员和论文展示。
8. 扩展船东评价船员、船员个人中心、统计报表等模块。

## 提交前检查

建议提交或推送前执行：

```powershell
cd backend
..\.venv\Scripts\python.exe -m unittest tests.test_api_contract tests.test_docker_configuration -v
cd ..
docker compose config
git status
```

如果修改了 `init.sql` 并希望 Docker 重新导入初始数据，开发阶段需要清理数据库卷：

```powershell
docker compose down -v
docker compose up --build
```
