# 后端运行与调试手册

这份手册教你真正动手熟悉后端：启动服务、打开接口文档、发送请求、看返回结果、定位报错、用 PyCharm/VSCode 打断点。

你学习后端时，最重要的不是把代码背下来，而是能做到：

```text
我知道怎么启动它
我知道怎么调用接口
我知道接口进了哪个函数
我知道它查了哪些表
我知道报错时该看哪里
```

## 1. 推荐学习运行方式

你现在练后端，优先用 SQLite 演示入口：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork\backend
python run_sqlite.py
```

启动成功会看到：

```text
Uvicorn running on http://127.0.0.1:3000
```

然后打开：

```text
http://127.0.0.1:3000/docs
```

这是 FastAPI 自动生成的接口文档页面。你可以在这里直接测试接口。

为什么推荐 `run_sqlite.py`：

- 不需要先配置 MySQL。
- 会使用 `backend/seafarer.db`。
- 每次启动会重建表并写入演示数据。
- 适合你反复练接口、看代码、打断点。

注意：

`run_sqlite.py` 每次启动都会重建演示数据库，所以你手动新增的数据重启后会被清空。这对学习是好事，因为环境每次都干净。

## 2. PyCharm 怎么打开和运行

打开项目：

1. 打开 PyCharm。
2. 选择 `Open`。
3. 打开目录：

```text
C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork
```

配置解释器：

1. 进入 `Settings`。
2. 找到 `Project: SeafarerManagementSystem_DBwork`。
3. 选择 `Python Interpreter`。
4. 可以选项目里的：

```text
backend\.venv\Scripts\python.exe
```

运行后端：

1. 在左侧打开 `backend/run_sqlite.py`。
2. 右键文件。
3. 选择 `Run 'run_sqlite'`。

调试后端：

1. 在 `backend/app/routers/auth.py` 的 `login` 函数里点一个断点。
2. 右键 `backend/run_sqlite.py`。
3. 选择 `Debug 'run_sqlite'`。
4. 浏览器打开 `http://127.0.0.1:3000/docs`。
5. 调用登录接口。
6. 程序会停在断点处，你就能一行一行看变量。

你最适合打断点的位置：

| 你要看什么 | 断点位置 |
| --- | --- |
| 登录 | `routers/auth.py` 的 `login` |
| 创建船员 | `routers/crews.py` 的 `create_crew` |
| 证书审核 | `routers/certificates.py` 的 `review_certificate` |
| 智能匹配 | `services.py` 的 `_score_match` |
| 创建派遣 | `services.py` 的 `create_dispatch` |
| 上船下船 | `services.py` 的 `onboard_dispatch`、`offboard_dispatch` |

## 3. VSCode 怎么打开和运行

打开项目：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork
code .
```

如果 `code` 命令不可用，就手动打开 VSCode，再选择 `File -> Open Folder`，打开项目根目录。

选择 Python 解释器：

1. 按 `Ctrl + Shift + P`。
2. 输入 `Python: Select Interpreter`。
3. 选择：

```text
backend\.venv\Scripts\python.exe
```

运行后端：

1. 打开 VSCode 终端。
2. 执行：

```powershell
cd backend
python run_sqlite.py
```

调试后端：

1. 打开 `backend/run_sqlite.py`。
2. 在你想看的代码行打断点。
3. 点击左侧 `Run and Debug`。
4. 选择 `Python File`。
5. 启动后去 `http://127.0.0.1:3000/docs` 调接口。

## 4. 用接口文档测试登录

打开：

```text
http://127.0.0.1:3000/docs
```

找到：

```text
POST /api/auth/login
```

点击 `Try it out`，输入：

```json
{
  "username": "admin",
  "password": "admin123"
}
```

如果你的种子数据账号不同，就打开 `backend/app/services.py`，搜索 `seed_demo_data`，看里面创建了哪些用户。

成功返回里会有：

```json
{
  "success": true,
  "message": "登录成功",
  "data": {
    "access_token": "...",
    "token_type": "bearer",
    "user": {
      "id": 1,
      "username": "admin",
      "role": "admin"
    }
  }
}
```

你要理解：

```text
access_token 就是登录凭证。
后面访问需要权限的接口，要带这个 token。
```

## 5. 用 PowerShell 测接口

如果你不想点网页，也可以用 PowerShell。

登录：

```powershell
$login = Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:3000/api/auth/login" `
  -ContentType "application/json" `
  -Body '{"username":"admin","password":"admin123"}'

$token = $login.data.access_token
$token
```

带 token 查船员：

```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://127.0.0.1:3000/api/crews" `
  -Headers @{ Authorization = "Bearer $token" }
```

查统计首页：

```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://127.0.0.1:3000/api/dashboard/summary" `
  -Headers @{ Authorization = "Bearer $token" }
```

查操作日志：

```text
GET /api/operation-logs
```

```powershell
Invoke-RestMethod -Method Get `
  -Uri "http://127.0.0.1:3000/api/operation-logs" `
  -Headers @{ Authorization = "Bearer $token" }
```

这几条命令练熟后，你就能自己验证后端有没有正常工作。

## 6. 一条接口怎么跟代码

以 `GET /api/crews` 为例：

1. 先看接口地址：

```text
GET /api/crews
```

2. 根据 `/api/crews` 找路由文件：

```text
backend/app/routers/crews.py
```

3. 找到：

```python
@router.get("")
def list_crews(...)
```

4. 看到它调用：

```python
services.list_crews(db)
```

5. 跳到：

```text
backend/app/services.py
```

6. 找到 `list_crews`，看它查询了哪个模型：

```python
select(Crew)
```

7. 再去 `models.py` 找 `class Crew(Base)`，就能对应到 `crews` 表。

这就是追代码的标准路线：

```text
接口地址 -> router 函数 -> schema 参数 -> service 逻辑 -> model 表结构 -> 数据库
```

## 7. 常见报错怎么判断

### 端口占用

报错：

```text
WinError 10048
```

意思：

```text
3000 端口已经有一个后端在运行。
```

查看占用：

```powershell
netstat -ano | findstr :3000
```

找到 `LISTENING` 那一行的 PID，然后结束进程：

```powershell
taskkill /PID 进程号 /F
```

### 404

意思：

```text
接口地址写错，或者请求方法写错。
```

比如：

```text
GET /api/login
```

可能不存在，因为登录是：

```text
POST /api/auth/login
```

遇到 404，先去：

```text
http://127.0.0.1:3000/docs
```

确认接口地址和请求方法。

### 401

意思：

```text
没有登录，或者 token 无效。
```

解决：

先调用登录接口拿 token，再带：

```text
Authorization: Bearer 你的token
```

### 403

意思：

```text
角色没有权限。
```

例如普通船员不能审核证书，船东不能随便确认别人的派遣。

代码位置：

```text
backend/app/dependencies.py
```

重点看：

```python
require_roles(...)
```

### 422 或 400

意思：

```text
请求参数格式不对，或者业务规则不允许。
```

常见例子：

- 身份证号格式不对。
- 性别不是 `男` 或 `女`。
- 证书到期时间早于签发时间。
- 船员证书不满足岗位要求。

先看：

```text
backend/app/schemas.py
```

再看：

```text
backend/app/services.py
```

### 500

意思：

```text
后端代码执行时异常。
```

你之前遇到过：

```text
sqlite3.OperationalError: no such column: crews.position_id
```

这类问题通常是：

```text
models.py 里的模型字段和数据库旧表结构不一致。
```

现在 `run_sqlite.py` 会重建演示数据库，所以本地演示时一般不会再出现旧表结构问题。

## 8. 调试时重点看哪些变量

登录接口：

| 变量 | 看什么 |
| --- | --- |
| `payload.username` | 前端传来的账号 |
| `payload.password` | 前端传来的密码 |
| `user` | 数据库查到的用户 |
| `access_token` | 生成的 token |

创建船员：

| 变量 | 看什么 |
| --- | --- |
| `payload` | 前端传来的船员信息 |
| `position_id`、`position_name` | 岗位字典匹配结果 |
| `user` | 新建的登录账号 |
| `crew` | 新建的船员档案 |

证书审核：

| 变量 | 看什么 |
| --- | --- |
| `certificate` | 当前证书对象 |
| `old_status` | 审核前状态 |
| `payload.review_status` | 审核后状态 |
| `reviewer` | 审核人 |

智能匹配：

| 变量 | 看什么 |
| --- | --- |
| `required_certificates` | 岗位要求证书 |
| `valid_types` | 船员有效证书 |
| `missing` | 缺少哪些证书 |
| `score` | 当前匹配分数 |
| `reasons` | 匹配原因 |

派遣流程：

| 变量 | 看什么 |
| --- | --- |
| `dispatch.status` | 派遣状态 |
| `crew.status` | 船员状态 |
| `job.status` | 岗位状态 |
| `voyage` | 海历记录 |

## 9. 最小实操路线

你第一次动手，不要贪多，按这个顺序：

1. 启动 `python run_sqlite.py`。
2. 打开 `http://127.0.0.1:3000/docs`。
3. 调 `POST /api/auth/login` 登录。
4. 调 `GET /api/crews` 看船员。
5. 调 `GET /api/dashboard/summary` 看统计。
6. 在 `services.py` 的 `list_matching_crews` 打断点。
7. 调 `GET /api/jobs/{job_id}/matches` 看匹配过程。
8. 在 `services.py` 的 `create_dispatch` 打断点。
9. 调 `POST /api/dispatches` 看派遣创建过程。

做完这 9 步，你对后端就不是“看过”，而是“跑过、调过、验证过”。

## 10. 一键接口练习脚本

项目里还有一个练习脚本：

```text
tools/backend_api_practice.py
```

先启动后端：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork\backend
python run_sqlite.py
```

再开一个新的 PowerShell，在项目根目录运行：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork
python tools\backend_api_practice.py
```

它会自动调用：

```text
GET /health
POST /api/auth/login
GET /api/dashboard/summary
GET /api/crews
GET /api/certificates
GET /api/jobs
GET /api/jobs/{job_id}/matches
GET /api/dispatches
GET /api/operation-logs
```

这个脚本的作用不是代替前端，而是帮你练习“一个接口请求进入后端以后，数据是怎么返回的”。

## 11. 后端代码自测脚本

如果你想检查自己有没有真的理解后端，可以运行：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork
python tools\backend_quiz.py
```

它会随机问 10 道后端代码题，内容包括：

```text
后端分层
登录和权限
船员管理
证书审核
智能匹配
派遣流程
统计和日志
常见报错
```

想一次练全部题：

```powershell
python tools\backend_quiz.py --all
```

想固定题目顺序，方便反复练：

```powershell
python tools\backend_quiz.py --count 10 --seed 1
```

这个脚本不需要后端服务启动，它是专门帮你自测理论和代码链路的。

## 12. 答辩时可以怎么说

> 我不仅看了后端代码，也实际启动过服务，通过 FastAPI 的 `/docs` 页面测试了登录、船员、证书、匹配、派遣和统计接口。调试时可以从路由函数进入，再跟到 service 业务逻辑，最后对应到 SQLAlchemy 的 model 和数据库表。因此我能说明每个接口的参数、权限、涉及的数据表和状态变化。
