# 后端学习从这里开始

这份文件是你的后端学习导航。你不用一次看完所有资料，按这里的顺序走就行。

目标很明确：

```text
不是背代码，而是能顺着一个接口讲清楚：
请求进哪里 -> 参数怎么校验 -> 调哪个 service -> 查/改哪张表 -> 返回什么 -> 为什么这样设计
```

## 1. 你现在拥有哪些资料

| 文件 | 用途 | 什么时候看 |
| --- | --- | --- |
| `docs/backend_flow_diagrams.md` | 流程图，帮你建立整体框架 | 第一次学某个模块前先看 |
| `docs/backend_api_code_map.md` | 接口到 router/schema/service/model/数据表定位地图 | 被问接口时快速定位代码 |
| `docs/backend_code_quick_reference.md` | 速查表，教你答辩怎么讲 | 答辩前复习 |
| `docs/backend_defense_cheatsheet.md` | 后端代码答辩速查表，按模块和接口快速回答 | 答辩前最后翻 |
| `docs/backend_practice_workbook.md` | 7 天练习册，带你按接口追代码 | 每天练 30 到 60 分钟 |
| `docs/backend_run_debug_playbook.md` | 运行调试手册，教你启动、打断点、测接口 | 真正上手跑后端时看 |
| `docs/backend_defense_speech.md` | 后端答辩 5 到 8 分钟口述总稿 | 能看懂六条主线后练口述 |
| `docs/backend_defense_qa_cards.md` | 老师追问问答卡 | 答辩前模拟问答 |
| `docs/backend_lesson_01_login.md` | 登录接口逐行精讲 | 第一次深入读代码时看 |
| `docs/backend_lesson_02_create_crew.md` | 创建船员接口逐行精讲 | 学完登录后看 |
| `docs/backend_lesson_03_certificate_review.md` | 证书录入与审核逐行精讲 | 学完船员后看 |
| `docs/backend_lesson_04_matching.md` | 岗位需求与智能匹配逐行精讲 | 学完证书后看 |
| `docs/backend_lesson_05_dispatch_voyage.md` | 派遣状态流转与海历生成逐行精讲 | 学完智能匹配后看 |
| `docs/backend_lesson_06_dashboard_logs.md` | 统计首页与操作日志逐行精讲 | 学完派遣海历后看 |
| `tools/backend_api_practice.py` | 一键调用核心接口 | 后端启动后运行 |
| `tools/backend_quiz.py` | 后端自测题 | 随时刷题检查理解 |
| `tools/backend_oral_trainer.py` | 后端口述训练器 | 答辩前练“开口讲” |

## 2. 推荐学习顺序

第一轮只建立感觉，不要求全懂：

```text
backend_flow_diagrams.md
-> backend_api_code_map.md
-> backend_code_quick_reference.md
-> backend_run_debug_playbook.md
```

第二轮开始动手：

```text
启动 python run_sqlite.py
-> 打开 http://127.0.0.1:3000/docs
-> 运行 tools/backend_api_practice.py
-> 对照 backend_practice_workbook.md 追代码
```

第三轮准备答辩：

```text
backend_defense_speech.md
-> backend_defense_cheatsheet.md
-> backend_defense_qa_cards.md
-> tools/backend_quiz.py
-> tools/backend_oral_trainer.py
-> 对着代码讲 6 条业务线
```

如果你想从第一条接口开始精读代码：

```text
backend_lesson_01_login.md
-> routers/auth.py
-> services.authenticate_user
-> security.py
```

第二条精读链路：

```text
backend_lesson_02_create_crew.md
-> routers/crews.py
-> schemas.CrewCreate
-> services.create_crew
-> models.User / Crew / Position
```

第三条精读链路：

```text
backend_lesson_03_certificate_review.md
-> routers/certificates.py
-> schemas.CertificateCreate / CertificateReview
-> services.create_certificate / review_certificate
-> models.Certificate / CertificateReviewRecord
```

第四条精读链路：

```text
backend_lesson_04_matching.md
-> routers/jobs.py / routers/matching.py
-> schemas.JobCreate
-> services.create_job / list_matching_crews / _score_match
-> models.JobDemand / JobRequiredCertificate
```

第五条精读链路：

```text
backend_lesson_05_dispatch_voyage.md
-> routers/dispatches.py
-> schemas.DispatchCreate
-> services.create_dispatch / confirm_dispatch / onboard_dispatch / offboard_dispatch / cancel_dispatch
-> models.Dispatch / DispatchStatusLog / VoyageRecord
```

第六条精读链路：

```text
backend_lesson_06_dashboard_logs.md
-> routers/dashboard.py / routers/logs.py
-> services.dashboard_summary / dashboard_crew_status / dashboard_dispatch_trend / dashboard_route_workload
-> services.list_operation_logs
-> models.OperationLog
```

## 3. 每天怎么练

### 第 1 天：后端整体入口

看：

- `docs/backend_flow_diagrams.md` 的整体请求链路
- `backend/run_sqlite.py`
- `backend/app/main.py`
- `backend/app/dependencies.py`

你要能讲：

```text
后端怎么启动？
路由怎么注册？
数据库 session 怎么传给接口？
权限怎么判断？
```

### 第 2 天：登录

看：

- `backend/app/routers/auth.py`
- `backend/app/services.py` 的 `authenticate_user`
- `backend/app/passwords.py`
- `backend/app/security.py`

你要能讲：

```text
username/password 怎么变成 token？
密码为什么不明文保存？
后续接口怎么识别当前用户？
```

### 第 3 天：船员

看：

- `backend/app/routers/crews.py`
- `backend/app/schemas.py` 的 `CrewCreate`
- `backend/app/services.py` 的 `create_crew`
- `backend/app/models.py` 的 `User`、`Crew`

你要能讲：

```text
为什么创建船员时同时写 users 和 crews？
users 和 crews 是什么关系？
软删除为什么用 inactive？
```

### 第 4 天：证书

看：

- `backend/app/routers/certificates.py`
- `backend/app/services.py` 的 `create_certificate`、`review_certificate`
- `backend/app/models.py` 的 `Certificate`、`CertificateReviewRecord`

你要能讲：

```text
证书为什么先 pending？
审核后改哪些字段？
审核记录表保存什么？
为什么只有 approved 且未过期证书能匹配？
```

### 第 5 天：智能匹配

看：

- `backend/app/routers/jobs.py`
- `backend/app/routers/matching.py`
- `backend/app/services.py` 的 `create_job`、`list_matching_crews`、`_score_match`
- `backend/app/models.py` 的 `JobDemand`、`JobRequiredCertificate`

你要能讲：

```text
岗位需求包含什么？
为什么岗位所需证书单独建表？
100 分匹配模型怎么计算？
为什么匹配结果要返回原因？
```

### 第 6 天：派遣和海历

看：

- `docs/backend_lesson_05_dispatch_voyage.md`
- `backend/app/routers/dispatches.py`
- `backend/app/services.py` 的 `create_dispatch`、`confirm_dispatch`、`onboard_dispatch`、`offboard_dispatch`
- `backend/app/models.py` 的 `Dispatch`、`DispatchStatusLog`、`VoyageRecord`

你要能讲：

```text
pending_owner -> confirmed -> onboard -> offboard 每一步发生什么？
什么时候生成海历？
为什么要有 dispatch_status_logs？
```

### 第 7 天：统计和日志

看：

- `docs/backend_lesson_06_dashboard_logs.md`
- `backend/app/routers/dashboard.py`
- `backend/app/routers/logs.py`
- `backend/app/services.py` 的 dashboard 函数和 `list_operation_logs`
- `backend/app/models.py` 的 `OperationLog`

你要能讲：

```text
首页统计数据从哪些表来？
月度派遣趋势按什么字段统计？
operation_logs 和 dispatch_status_logs 有什么区别？
```

## 4. 三个脚本怎么用

如果 PowerShell 提示 `python` 不是可识别的命令，就在 PyCharm 里直接运行脚本，或者把下面命令里的 `python` 换成你解释器的完整路径，例如：

```powershell
C:\Users\zxj\AppData\Local\Python\pythoncore-3.14-64\python.exe tools\backend_oral_trainer.py
```

### 接口练习脚本

先启动后端：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork\backend
python run_sqlite.py
```

再开一个新的 PowerShell：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork
python tools\backend_api_practice.py
```

它会自动调用登录、统计、船员、证书、岗位、匹配、派遣、日志接口。

### 自测脚本

不需要启动后端，直接运行：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork
python tools\backend_quiz.py
```

练全部题：

```powershell
python tools\backend_quiz.py --all
```

固定题目顺序：

```powershell
python tools\backend_quiz.py --count 10 --seed 1
```

### 口述训练脚本

不需要启动后端，直接运行：

```powershell
cd C:\Users\zxj\Desktop\SeafarerManagementSystem_DBwork
python tools\backend_oral_trainer.py
```

它会像老师一样抽问你。你先自己开口讲，按回车后再看参考要点，然后给自己打分。

练全部口述题：

```powershell
python tools\backend_oral_trainer.py --all
```

只练某一类主题：

```powershell
python tools\backend_oral_trainer.py --topic 智能匹配 --show-files
```

## 5. 判断自己是否学会

你不用做到能默写代码。达到下面这些就够答辩了：

| 能力 | 达标标准 |
| --- | --- |
| 启动后端 | 能用 `python run_sqlite.py` 启动并打开 `/docs` |
| 找接口 | 知道接口地址对应哪个 `routers/*.py` |
| 找参数 | 知道请求体对应 `schemas.py` 哪个类 |
| 找业务 | 知道接口调用 `services.py` 哪个函数 |
| 找表 | 知道业务涉及 `models.py` 哪些模型 |
| 讲流程 | 能讲登录、船员、证书、匹配、派遣、统计 6 条线 |
| 查错误 | 知道 404、401、403、500 大概怎么定位 |
| 过自测 | `tools/backend_quiz.py --all` 正确率达到 80% 以上 |

## 6. 最终 10 分钟答辩自检

不看资料，试着讲这 6 个问题：

1. 登录接口从前端请求到返回 token，中间发生了什么？
2. 创建船员为什么同时写 `users` 和 `crews`？
3. 证书审核为什么会影响智能匹配？
4. 智能匹配 100 分由哪几部分组成？
5. 派遣从创建到下船，哪些表会变化？
6. 首页统计数据从哪些表查出来？

如果能讲清楚，你就已经熟悉后端主线了。

## 7. 你答辩时的底气句

> 我不是只看页面。我能从接口地址顺着 router 找到 schema、service 和 model，也能说明每个接口涉及的数据表、权限控制和状态变化。这个系统后端的重点是用数据库表关系和状态流转支撑完整业务流程。
