# 出海船员管理系统

这是一个面向数据库课程设计的出海船员管理系统。当前版本从原来的基础船员管理扩展为“船员资源调度与证书风控系统”，重点展示数据库表设计、外键关系、状态约束、审核日志、派遣流程和统计可视化。

## 技术栈

- 后端：FastAPI、SQLAlchemy、PyMySQL
- 数据库：MySQL 8
- 前端：静态 HTML/CSS/JavaScript
- 部署：Docker Compose
- 测试：unittest、FastAPI TestClient

## 核心功能

- 用户登录和角色权限：管理员、业务经理、证书管理员、船东、船员。
- 船员档案：新增、编辑、停用、岗位和状态管理。
- 证书风控：证书录入、审核、拒绝、30 天到期预警。
- 船舶航线：航运公司、船舶、港口、航线等实体化管理。
- 岗位需求：船东发布岗位，岗位可配置船舶、航线、人数和所需证书。
- 智能匹配：根据岗位、证书审核状态、证书有效期、历史海历计算匹配分。
- 派遣流程：待船东确认、已确认、上船、下船、取消，并记录状态日志。
- 统计可视化：船员状态分布、证书预警、派遣趋势、航线工作量。
- 审计日志：关键操作写入 `operation_logs`。

## 数据库设计亮点

当前 `init.sql` 包含 16 张业务表和 4 个统计视图：

- 核心业务表：`users`、`crews`、`certificates`、`job_demands`、`dispatches`、`voyage_records`
- 字典/实体表：`positions`、`certificate_types`、`ship_companies`、`ships`、`ports`、`routes`
- 关系/日志表：`job_required_certificates`、`certificate_review_records`、`dispatch_status_logs`、`operation_logs`
- 统计视图：`v_crew_certificate_status`、`v_dispatch_flow_stats`、`v_route_workload`、`v_job_match_overview`

详细 ER 图和数据字典见 [docs/database_design.md](docs/database_design.md)。

## 启动方式

在项目根目录执行：

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

如果修改了 `init.sql` 并希望重新导入演示数据，需要清空数据库卷：

```powershell
docker compose down -v
docker compose up --build
```

## 演示账号

| 账号 | 密码 | 角色 | 用途 |
| --- | --- | --- | --- |
| `admin` | `admin123` | admin | 管理员，演示全部功能 |
| `manager` | `manager123` | manager | 业务经理，演示匹配和派遣 |
| `cert_admin` | `cert123` | cert_admin | 证书管理员，演示证书审核 |
| `owner` | `owner123` | shipowner | 船东甲，演示岗位确认 |
| `other_owner` | `owner123` | shipowner | 船东乙 |
| `crew01` | `123456` | seafarer | 船员个人中心 |

## 主要接口

```text
POST /api/auth/login
POST /api/login

GET/POST /api/crews
GET/POST /api/certificates
PUT /api/certificates/{id}/review

GET/POST /api/ships
GET/POST /api/ports
GET/POST /api/routes
GET/POST /api/positions
GET/POST /api/certificate-types

GET/POST /api/jobs
GET /api/jobs/{id}/matches
GET/POST /api/dispatches
PUT /api/dispatches/{id}/confirm
PUT /api/dispatches/{id}/onboard
PUT /api/dispatches/{id}/offboard
PUT /api/dispatches/{id}/cancel

GET /api/dashboard/summary
GET /api/dashboard/crew-status
GET /api/dashboard/certificate-alerts
GET /api/dashboard/dispatch-trend
GET /api/dashboard/route-workload
GET /api/operation-logs
```

## 四人分工建议

- 组长：数据库总设计、ER 图、数据字典、`init.sql`、最终整合与答辩主讲。
- 组员 A：后端模型、接口、匹配评分、派遣日志、统计接口。
- 组员 B：前端页面、表格筛选、统计可视化、演示截图。
- 组员 C：需求分析、流程图、测试用例、PPT 和部署说明。

## 测试

如果本机 Python 环境可用，在 `backend` 目录执行：

```powershell
python -m unittest tests.test_api_contract tests.test_docker_configuration -v
```

也可以使用 Docker 启动后通过 `http://localhost:3000/docs` 手动验证接口。
