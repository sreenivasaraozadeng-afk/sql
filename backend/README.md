# FastAPI 后端说明

后端负责登录鉴权、船员档案、证书审核、船舶航线、岗位需求、智能匹配、派遣流程、统计接口和日志审计。

## 模块结构

```text
app/
├── main.py
├── database.py
├── dependencies.py
├── models.py
├── schemas.py
├── services.py
├── security.py
├── passwords.py
└── routers/
    ├── auth.py
    ├── crews.py
    ├── certificates.py
    ├── lookups.py
    ├── ships.py
    ├── jobs.py
    ├── matching.py
    ├── dispatches.py
    ├── dashboard.py
    ├── logs.py
    └── legacy.py
```

## 运行

推荐通过项目根目录的 Docker Compose 运行：

```powershell
docker compose up --build
```

本地 Python 环境可用时，也可以在 `backend` 目录运行：

```powershell
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 3000
```

接口文档：

```text
http://localhost:3000/docs
```

## 测试

```powershell
python -m unittest tests.test_api_contract tests.test_docker_configuration -v
```

测试覆盖登录权限、字典接口、船舶接口、证书审核、匹配评分、派遣状态日志、操作日志、Docker 配置和初始化 SQL。
