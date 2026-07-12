# AAAgent 软件设计文档（SDD）— v0.1.1

## 1. 项目概述

### 1.1 项目定位

AAAgent 是一款本地优先的 AI Agent 桌面应用，目标是让没有工程背景的用户也能理解并使用 Agent。它通过“眼睛、双手、记忆”等拟物化能力表示输入、工具和上下文，让复杂的模型能力变成可配置的工作台。

AAAgent 的核心使用场景包括：

- 使用用户自己的 API 与模型进行对话
- 将文件、图片和网页内容交给 Agent 处理
- 通过 MCP 工具扩展 Agent 的能力
- 在本地保存会话、配置和长期记忆
- 为求职者提供一个可运行、可展示、可解释的 AI 桌面项目

### 1.2 设计目标

1. **本地优先**：模型请求可以由用户自行配置，数据默认保存在本机。
2. **渐进式复杂度**：新用户先使用休闲模式，熟悉后再进入专业模式。
3. **桌面应用体验**：正式版本使用 Electron 独立窗口，不依赖用户手动打开浏览器。
4. **协议优先**：模型统一适配 OpenAI 兼容接口，工具统一适配 MCP。
5. **边界清晰**：Electron 主进程、React 渲染进程、本地服务和可选 Python 服务各司其职。
6. **可测试和可打包**：关键逻辑采用纯函数和服务接口，支持自动化测试及 Windows 安装包构建。

## 2. 总体架构

```text
┌────────────────────────────────────────────────────────┐
│ Electron Desktop Shell                                 │
│  ┌──────────────────────┐  ┌────────────────────────┐  │
│  │ Main Process          │  │ Renderer Process       │  │
│  │ Window / IPC / Secure │◄─┤ React + TypeScript     │  │
│  │ Storage / Lifecycle   │  │ Vite + Zustand         │  │
│  └──────────┬───────────┘  └────────────────────────┘  │
│             │ localhost / IPC                           │
│  ┌──────────▼────────────────────────────────────────┐  │
│  │ Node.js Local Service                             │  │
│  │ Session · LLM Adapter · Tool Orchestrator         │  │
│  └──────┬───────────────┬───────────────┬───────────┘  │
│         │               │               │              │
│  ┌──────▼─────┐  ┌──────▼─────┐  ┌──────▼─────────┐   │
│  │ SQLite      │  │ MCP Tools   │  │ OpenAI API     │   │
│  │ Sessions    │  │ Files/Web   │  │ Kimi/Ollama    │   │
│  └────────────┘  └─────────────┘  └────────────────┘   │
│                                                        │
│  Optional: FastAPI service for OCR, parsing, vectors  │
└────────────────────────────────────────────────────────┘
```

### 2.1 进程职责

#### Electron 主进程

- 创建和销毁 `BrowserWindow`
- 启动和停止 Node.js 本地服务
- 管理应用生命周期和单实例锁
- 通过 `contextBridge` 暴露最小化 IPC API
- 使用 safeStorage 或系统凭据安全保存 API Key

#### React 渲染进程

- 展示聊天、配置、会话和能力槽
- 管理输入状态和临时 UI 状态
- 通过 IPC 或本地服务 API 调用后端能力
- 不直接访问文件系统、进程和密钥存储

#### Node.js 本地服务

- 接收聊天请求和流式响应
- 统一处理 OpenAI 兼容模型接口
- 管理会话、工具调用和配置
- 访问 SQLite
- 对文件和外部工具操作进行权限检查

#### FastAPI 能力层

FastAPI 不是第一阶段的必需组件。只有在需要 OCR、复杂文档解析、音频处理或 Python AI 库时才启动它。Node 服务负责统一入口，避免前端感知多种后端。

## 3. 核心模块设计

### 3.1 输入处理模块

输入处理器将文本、文件、图片和网页统一转换为 Agent 可理解的消息内容。

```ts
export type InputKind = 'text' | 'file' | 'image' | 'url' | 'audio';

export interface InputItem {
  kind: InputKind;
  name?: string;
  mimeType?: string;
  content: string;
  metadata?: Record<string, unknown>;
}

export interface InputProcessor {
  supports(item: InputItem): boolean;
  normalize(item: InputItem): Promise<NormalizedContent>;
}
```

Phase 0 只实现文本。文件和图片处理器放到 Phase 3，避免一开始引入过多依赖。

### 3.2 LLM 适配模块

所有模型供应商都转换为 OpenAI 兼容的统一接口。适配器只负责请求格式、鉴权、错误转换和流式读取，不在适配器中放置 UI 逻辑。

```ts
export interface ChatRequest {
  provider: string;
  baseUrl: string;
  apiKey?: string;
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  maxTokens?: number;
  stream?: boolean;
}

export interface LLMAdapter {
  chat(request: ChatRequest): AsyncIterable<ChatChunk>;
  validate(config: ProviderConfig): Promise<ValidationResult>;
}
```

支持的初始供应商：OpenAI、Kimi、DeepSeek、Ollama 和自定义 OpenAI 兼容服务。

### 3.3 工具调度模块

工具层通过 MCP 统一描述工具名称、参数、权限和结果。Agent 不直接执行工具，而是经过以下步骤：

1. 模型提出工具调用。
2. 服务层校验工具是否已启用。
3. 对需要确认的操作展示确认界面。
4. 执行工具并记录输入、输出和错误。
5. 将结果追加到当前会话。

拟物化能力映射：

| 机器人能力 | 技术含义 | 初始工具 |
|---|---|---|
| 眼睛 | 接收和读取信息 | 文本、文件、图片 |
| 双手 | 执行外部操作 | MCP 工具、文件操作 |
| 记忆 | 保存和检索上下文 | SQLite 会话、FTS5 |
| 耳朵 | 语音输入 | 后续音频处理器 |

### 3.4 双模式系统

#### 休闲模式

面向新用户，使用“模型连接”“响应风格”“能力槽”等低门槛概念。隐藏原始参数，只展示必要设置。

#### 专业模式

展示完整的 Provider、Base URL、模型名称、温度、最大 Token、超时、工具权限和调试信息。

两种模式共享同一份配置数据，只改变表示层和可编辑字段，不复制业务逻辑。

### 3.5 会话与记忆模块

SQLite 是本地数据的唯一事实来源。建议的核心表：

```text
sessions       id, title, created_at, updated_at
messages       id, session_id, role, content, metadata, created_at
provider_configs id, name, provider, base_url, model, encrypted_key
memories       id, content, source_session_id, importance, created_at
settings       key, value, updated_at
```

Phase 1 先完成 sessions 和 messages。Phase 4 增加 memories 与 FTS5 检索。

### 3.6 桌面 UI 模块

- **桌面框架**：Electron
- **前端**：React + TypeScript + Vite
- **状态管理**：Zustand
- **校验**：Zod
- **图标**：Lucide React
- **设计方向**：克制、清晰、高信息密度，参考 OpenAI 和 Google 产品的留白、层级与控件反馈

主要界面：

1. 主聊天界面
2. 模型连接设置
3. 会话侧栏
4. 机器人能力槽
5. 工具确认弹窗
6. 专业模式设置页

## 4. 数据流设计

### 4.1 普通对话

```text
用户输入
  → React Chat Store
  → IPC / Node Local Service
  → LLM Adapter
  → OpenAI 兼容 API
  → 流式 ChatChunk
  → Node 服务转换
  → React 逐块更新消息
  → SQLite 保存完整消息
```

### 4.2 工具调用

```text
模型返回 tool_call
  → Tool Registry 查找
  → 权限与参数校验
  → 用户确认（如需要）
  → MCP Client 执行
  → 结果写入会话
  → 再次请求模型生成最终回答
```

### 4.3 桌面启动

```text
AAAgent.exe
  → Electron main.ts
  → 启动 Node local service
  → 等待服务健康检查
  → 创建 BrowserWindow
  → 加载 renderer
  → 应用退出时关闭本地服务
```

## 5. 配置和安全

配置分为三层：

1. **应用配置**：主题、窗口、语言和日志级别。
2. **模型配置**：Provider、Base URL、模型、参数和 API Key。
3. **能力配置**：工具是否启用、权限级别和确认策略。

安全要求：

- API Key 不进入 React bundle、日志和 Git。
- 开发环境可使用本地配置文件，正式版本使用 `safeStorage`。
- 服务只监听 `127.0.0.1`。
- 文件路径必须经过工作区和权限校验。
- MCP 工具默认关闭，启用高风险工具前必须确认。

## 6. 扩展性设计

### 6.1 Provider 插件

通过统一 `LLMAdapter` 接口接入新的 OpenAI 兼容服务。增加供应商不应修改聊天组件。

### 6.2 输入处理器

每种输入类型实现一个 `InputProcessor`，由注册表根据 MIME 类型和输入来源选择处理器。

### 6.3 工具插件

MCP Server 负责提供工具，AAAgent 只负责发现、配置、授权和调用。插件生命周期由 Node 服务统一管理。

### 6.4 FastAPI 扩展

当 Node 生态不足以支持某项能力时，通过本地 FastAPI 子进程扩展。Node 服务提供统一代理和健康检查，React 不直接调用 Python 服务。

## 7. 技术栈清单

| 层级 | 技术 | 选择理由 |
|---|---|---|
| 桌面 | Electron | 复用 Web 技术，快速形成 Windows 软件 |
| UI | React + TypeScript | 组件化、类型安全、适合复杂交互 |
| 构建 | Vite | 启动快、配置清晰 |
| 状态 | Zustand | 轻量，适合按功能拆分 Store |
| 本地服务 | Node.js | 与 Electron 和前端共享 TypeScript 类型 |
| Python 能力 | FastAPI | OCR、文档解析和 AI 工具生态丰富 |
| 数据库 | SQLite | 本地优先、免部署、便于打包 |
| 模型协议 | OpenAI 兼容 API | 供应商切换成本低 |
| 工具协议 | MCP | 工具生态和扩展边界清晰 |
| 打包 | electron-builder | Windows 安装包和自动更新支持成熟 |

## 8. 目录结构

```text
src/
├── main/                 # Electron 主进程
├── renderer/             # React 渲染进程
├── services/             # LLM、会话、工具和记忆服务
├── shared/               # 跨进程类型和协议
└── config/               # 配置 schema
backend/                  # 可选 FastAPI 服务
assets/                   # UI 和应用资源
tests/                    # 单元、组件、E2E 测试
docs/                     # 设计和使用文档
```

## 9. 版本规划

- **V0.1**：API 配置、单轮对话、流式显示、本地服务。
- **V0.2**：Electron 窗口、多轮会话、SQLite 和会话列表。
- **V0.3**：MCP 工具、权限确认和工具调用记录。
- **V0.4**：文件、图片和网页输入。
- **V1.0**：长期记忆、FTS5 检索、稳定打包和 Windows 发布。
- **V1.1+**：专业模式、插件管理、评估、日志和跨平台支持。

## 10. 术语

- **Agent**：能够理解任务并调用模型、工具和记忆完成工作的应用。
- **Provider**：模型服务供应商或本地模型服务。
- **MCP**：用于连接外部工具和数据源的模型上下文协议。
- **IPC**：Electron 主进程与渲染进程之间的进程通信。
- **本地优先**：核心数据和运行服务默认在用户设备上完成。