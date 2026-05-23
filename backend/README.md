# FastAPI 后端说明

本目录是出海船员管理系统的 FastAPI 后端。当前版本已经从原 `backend/server.js` 的 Node.js + Express 后端迁移为 Python 后端，并扩展为船员、证书、岗位、匹配、派遣流程的 MVP。

## 模块结构

```text
app/
├─ main.py              # FastAPI 应用入口
├─ database.py          # 数据库连接
├─ dependencies.py      # 当前用户、角色权限依赖
├─ models.py            # SQLAlchemy 表模型
├─ schemas.py           # Pydantic 入参/出参校验
├─ services.py          # 业务规则与事务处理
├─ security.py          # Token 生成与校验
├─ passwords.py         # 密码哈希与校验
└─ routers/
   ├─ auth.py
   ├─ crews.py
   ├─ certificates.py
   ├─ jobs.py
   ├─ matching.py
   ├─ dispatches.py
   └─ legacy.py           # 旧 HTML 前端兼容接口
```

## 主要接口

```text
POST /api/auth/login
POST /api/login

GET    /api/crews
POST   /api/crews
GET    /api/crews/{id}
PUT    /api/crews/{id}
DELETE /api/crews/{id}
PUT    /api/crews/{id}/status
GET    /api/stats

GET  /api/certificates
POST /api/certificates
PUT  /api/certificates/{id}
GET  /api/certificates/alerts

GET  /api/jobs
POST /api/jobs
GET  /api/jobs/{id}
PUT  /api/jobs/{id}/close
GET  /api/jobs/{id}/matches

POST /api/dispatches
PUT  /api/dispatches/{id}/confirm
PUT  /api/dispatches/{id}/onboard
PUT  /api/dispatches/{id}/offboard
PUT  /api/dispatches/{id}/cancel

GET  /api/voyages
POST /api/voyages
GET  /api/my-profile/{id}
GET  /api/my-voyages/{id}
```

## 本地启动

在项目根目录安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
```

在 `backend` 目录启动：

```powershell
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 3000
```

接口文档：

```text
http://localhost:3000/docs
```

## 数据库

默认连接：

```text
mysql+pymysql://root:123456@127.0.0.1:3306/SeafarerDB?charset=utf8mb4
```

如需修改：

```powershell
$env:SEAFARER_DATABASE_URL='mysql+pymysql://root:你的密码@127.0.0.1:3306/SeafarerDB?charset=utf8mb4'
```

数据库初始化脚本在项目根目录的 `init.sql`。当前还没有接入 Alembic，修改表结构后，Docker 开发环境需要重建数据库卷：

```powershell
docker compose down -v
docker compose up --build
```

## 测试

在 `backend` 目录执行：

```powershell
..\.venv\Scripts\python.exe -m unittest tests.test_api_contract tests.test_docker_configuration -v
```

测试覆盖登录权限、船员 CRUD、证书预警、岗位匹配、派遣流转和 Docker/SQL 配置。
