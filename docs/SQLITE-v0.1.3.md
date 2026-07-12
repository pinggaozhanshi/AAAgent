# AAAgent SQLite 使用指南 — v0.1.3

> 给有 MySQL 使用经验的开发者：AAAgent 为什么选择 SQLite、怎样初始化、怎样安全写入专业模式数据。

## 1. SQLite 与 MySQL 的关键差异

| MySQL | SQLite | 对 AAAgent 的影响 |
|---|---|---|
| 独立数据库服务 | 一个本地 `.db` 文件 | 不需要安装或启动数据库服务 |
| 多客户端高并发写入 | 同一时刻只允许一个写入事务 | 写事务必须短小，不要在事务中请求模型 API |
| 用户、权限、网络连接 | 文件权限和应用进程控制 | Electron 与本地服务负责访问边界 |
| `DECIMAL` 常用于金额 | 常用整数最可靠 | 费用存 `cost_microunits`，避免浮点误差 |
| JSON 类型 | JSON 通常以 TEXT 保存 | Python/Zod 负责结构校验 |

SQLite 非常适合 AAAgent：数据只属于单个本地用户、会话与运行记录需要离线保存、部署时不应要求用户安装 MySQL。

## 2. 本项目的数据库文件

默认位置：

```text
backend/data/aaagent.db
```

该文件以及它的 WAL 辅助文件都不应提交 Git。`.gitignore` 已忽略 `*.db`；请同时忽略 `*.db-wal` 和 `*.db-shm`。

## 3. 初始化数据库

在项目根目录执行：

```powershell
python backend/database.py
```

首次执行会创建 `backend/data/aaagent.db` 和 v0.1.3 的所有表。重复执行是安全的：schema 使用 `CREATE TABLE IF NOT EXISTS`。

查看数据库推荐使用 VS Code 的 SQLite Viewer、DB Browser for SQLite，或 SQLite CLI：

```powershell
sqlite3 backend/data/aaagent.db
.tables
.schema tasks
.quit
```

## 4. 表设计与用途

```text
api_profiles       保存模型方案元数据和密钥引用，不保存 API Key
sessions/messages  保存会话和消息
runs               一次用户请求对应一次运行，保存规划/执行方案快照
task_graphs        保存原始 JSON 任务图和可读 Markdown
tasks              每个可执行任务的状态与结果
task_dependencies  任务之间的 DAG 依赖关系
task_artifacts     文本、文件和工具结果等产物
usage_records      Token、费用、耗时；真实值或估算值均有来源标识
run_events         驱动前端任务图和调试时间线
```

核心原则：`task_graphs.graph_json` 用于回放原始计划，`tasks` 与 `task_dependencies` 用于可靠调度。不要在运行时反复解析 Markdown 来决定执行顺序。

## 5. 必须记住的 SQLite 规则

### 每个连接都要开启外键

SQLite 默认不强制外键。每次新建连接后都必须执行：

```sql
PRAGMA foreign_keys = ON;
```

`backend/database.py` 已经处理此项。没有它，`ON DELETE CASCADE` 不会生效。

### 使用 WAL，但不要长事务

schema 已启用 WAL：读操作和一个短写操作可以更好地共存。它不意味着可以同时进行多个长写事务。

错误做法：

```text
BEGIN
调用规划模型，等待 20 秒
写入任务图
COMMIT
```

正确做法：先调用模型，再开启很短的事务写入 TaskGraph、Tasks 和 Dependencies。

### 时间、布尔值与金额

- 时间使用 UTC ISO 8601 字符串，例如 `2026-07-13T10:00:00Z`。
- 布尔值使用 `0` / `1`。
- 金额使用最小整数单位。`cost_microunits = 12500` 表示 `0.012500 USD`。
- UUID 使用 TEXT，前端与后端都可以生成。

## 6. 第一批数据如何写入

以下示例用 Python 标准库演示一次“创建会话”的最小写入。生产代码应放在 Repository 层，不要在 FastAPI 路由里散落 SQL。

```python
from uuid import uuid4
from backend.database import connect_database

session_id = str(uuid4())
with connect_database() as db:
    db.execute(
        "INSERT INTO sessions(id, title, mode) VALUES (?, ?, ?)",
        (session_id, "职业规划讨论", "professional"),
    )
```

使用 `?` 参数绑定，绝不使用字符串拼接 SQL：

```python
# 错误：存在 SQL 注入和转义问题
f"INSERT INTO sessions(title) VALUES ('{title}')"
```

## 7. 如何查询可执行任务

调度器需要找出“自身状态是 planned，且所有前置任务都已 completed”的任务：

```sql
SELECT t.*
FROM tasks AS t
WHERE t.run_id = ?
  AND t.status = 'planned'
  AND NOT EXISTS (
    SELECT 1
    FROM task_dependencies AS d
    JOIN tasks AS prerequisite ON prerequisite.id = d.prerequisite_task_id
    WHERE d.task_id = t.id
      AND prerequisite.status <> 'completed'
  );
```

查询结果才可以由 Scheduler 转换为 `ready`。循环依赖检查必须在插入前的 TaskGraph 校验器中完成，不能依赖这条 SQL 侥幸发现。

## 8. API Key 的正确保存方式

以下设计不可使用：

```text
api_profiles.api_key = "sk-..."
```

正确流程：

1. 设置页面把 Key 通过安全 IPC 交给 Electron 主进程。
2. 主进程用 `safeStorage` 或系统凭据仓库存储 Key。
3. 主进程返回 `credential_ref`。
4. SQLite 的 `api_profiles` 只保存 `credential_ref` 与非敏感配置。
5. 请求模型时，主进程或本地服务根据引用读取密钥；日志永远只记录掩码。

当前 SSE 原型仍从请求中接收 `apiKey`，这是 Phase 0 的临时行为。接入专业模式前必须改为上述流程。

## 9. 迁移而不是手改生产数据库

`schema.sql` 是新安装的基准 schema。未来修改表结构时：

1. 新建独立迁移文件，例如 `backend/migrations/002_add_memory.sql`。
2. 在事务内执行迁移并向 `schema_migrations` 写入版本记录。
3. 在数据库副本上验证迁移。
4. 不修改已经发布的旧迁移文件。

SQLite 的 `ALTER TABLE` 能力比 MySQL 少。复杂变更通常采用“新建表 → 复制数据 → 替换表名”的迁移方式。

## 10. 下一步接入后端

推荐顺序：

1. 在 FastAPI lifespan 中调用 `initialize_database()`。
2. 新建 `repositories/`，先实现 `SessionRepository` 与 `ProfileRepository`。
3. 聊天结束时写入 `messages` 与 `usage_records`。
4. 再接入 Planner、TaskGraph 校验和 `tasks/task_dependencies`。
5. 最后实现 Scheduler、取消、重试和前端事件流。

不要先实现自动并发任务执行。先让一条运行记录、一个单节点任务和一条 Token 用量记录完整落库，再扩大调度复杂度。