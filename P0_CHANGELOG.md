# P0 改动说明文档

> 改动日期：2026-05-23
> 改动范围：frontend/ 目录下所有 HTML 文件 + 新增 2 个共享文件

---

## 一、新增文件

### 1. `frontend/common.css` — 共享样式表

提取了所有页面的重复 CSS，统一管理：

- 通用布局：body、header-bar
- 表格：table、th、td、tr:hover
- 按钮：button、action-btn（编辑/删除/状态）
- 标签：tag-sea（出海中）、tag-land（在岸）
- 模态弹窗：modal、modal-content、form-group、modal-actions
- 统计卡片：stats-row、stat-card
- 搜索栏：search-bar（新增）
- 分页：pagination（新增）
- Toast 提示：toast、toast-error、toast-success（新增）

### 2. `frontend/common.js` — 共享 JS 工具库

| 函数 | 作用 |
|------|------|
| `API_BASE` | 统一的后端地址常量 `http://localhost:3000`，修改一处全局生效 |
| `apiGet(path)` | GET 请求封装，自动检查 response.ok |
| `apiPost(path, body)` | POST 请求封装，自动 JSON 序列化 |
| `apiPut(path, body)` | PUT 请求封装 |
| `apiDelete(path)` | DELETE 请求封装 |
| `showToast(msg, type)` | 右上角提示框，3秒自动消失，支持 success/error |
| `formatTime(isoString)` | 时间格式化 |

---

## 二、`crew_list.html` 改动（重点）

### 修复的 Bug

| 问题 | 位置（旧文件） | 修复 |
|------|--------------|------|
| `changeStatus` 函数定义了两次 | 第187行和第226行 | 删除重复定义，保留一处 |
| 表单 submit 事件绑定了两次 | 第212行和第280行 | 删除重复绑定 |
| 密码明文显示在表格中 | 第153行 `crew.password` | **整列移除**，后端已返回 `******` |
| 大量注释解释代码"做了什么" | 全文 | 删除冗余注释 |

### 新增功能

#### 1. 搜索与筛选

```
┌─────────────────────────────────────────────────────┐
│ [🔍 搜索姓名...]  [全部状态 ▼]  [全部岗位 ▼]  共7条 │
└─────────────────────────────────────────────────────┘
```

- **姓名搜索**：输入框实时过滤，前端模糊匹配
- **状态筛选**：下拉框 — 全部 / 在岸可派遣 / 待上船 / 出海中 / 已停用
- **岗位筛选**：下拉框 — 自动从数据中提取所有岗位，去重排序
- 三个条件可组合使用

#### 2. 分页

- 每页 10 条
- 上一页 / 下一页按钮，首尾页自动禁用
- 显示 "共 X 条记录，第 Y/Z 页"

#### 3. 编辑弹窗

- 每行新增 **编辑** 按钮（蓝色）
- 点击弹出预填数据的表单：姓名、性别、电话、岗位
- 调用 `PUT /api/crews/{id}` 接口更新
- 保存后自动刷新列表

#### 4. 状态系统更新

- 旧版用 `is_at_sea`（0/1）判断状态
- 新版用 `status` 字段：`available` / `pending` / `at_sea` / `inactive`
- 操作按钮文字和样式根据状态自动切换

### 其他改进

- 添加 `<meta name="viewport">`
- 表格新增**岗位**列（旧版缺少）
- 错误处理改用 `showToast()` 替代 `alert()`
- 加载数据时 loadStats 和 loadCrews 并行请求

---

## 三、其他页面改动

### `voyage_list.html`

- 内联 CSS → 引用 `common.css`
- 硬编码 URL → 使用 `apiGet/apiPost` 
- `alert()` → `showToast()`
- 删除冗余注释
- 添加 `<meta name="viewport">`

### `user.html`

- 内联 CSS → 引用 `common.css`（保留页面特有卡片样式）
- 硬编码 URL → 使用 `apiGet` / `formatTime`
- 空数据时显示友好提示
- 添加 `<meta name="viewport">`

### `index.html`

- 内联样式 → 引用 `common.css`（保留登录框特有样式）
- 硬编码 URL → 使用 `apiPost`
- `alert()` → `showToast()`
- 添加 `<meta name="viewport">`

---

## 四、对应后端接口

前端功能对应的后端 API 均已就绪，无需改动：

| 前端操作 | 接口 | 方法 |
|---------|------|------|
| 加载列表 | `/api/crews` | GET |
| 搜索/筛选/分页 | 客户端处理 | — |
| 新增船员 | `/api/crews` | POST |
| 编辑船员 | `/api/crews/{id}` | PUT |
| 切换状态 | `/api/crews/{id}` | PUT |
| 删除船员 | `/api/crews/{id}` | DELETE |
| 统计数据 | `/api/stats` | GET |

---

## 五、文件清单

```
frontend/
├── common.css          🆕 共享样式
├── common.js           🆕 共享 JS 工具
├── index.html          🔧 重构
├── admin.html          ─  未改动
├── crew_list.html      🔧 重写（P0 核心）
├── voyage_list.html    🔧 重构
├── user.html           🔧 重构
├── nginx.conf          ─  未改动
└── Dockerfile          ─  未改动
```
