# AAAgent 软件设计文档 (SDD) — V1.0

> **文档版本**: V1.0 — 基础架构版  
> **日期**: 2025-06-28  
> **状态**: 初步设计 / 持续迭代  
> **备注**: 本文档为第一版，许多扩展 Idea 尚未纳入，后续版本将持续补充。

---

## 1. 项目概述

### 1.1 项目名称
**AAAgent** — "AI Agent for All"，一款面向 AI 新手的友好型智能体应用。

### 1.2 项目愿景
打造一款**对 AI 新手极度友好**的多模态智能体前端应用。用户可以通过多种输入方式与 AI 交互，系统调用大模型 API 解决问题。核心创新在于将复杂的 AI Agent 配置（如 MCP 工具、模型参数）通过**拟物化的"机器人能力"概念**进行图形化呈现，让用户像在配置一个机器人的"五官"与"四肢"一样直观地配置 AI 能力。

### 1.3 核心特性
| 特性 | 描述 |
|------|------|
| 多模态输入 | 支持文本、文件、图片、音频、网页链接等多种输入类型 |
| 双模式切换 | **休闲模式**（面向新手，术语通俗化，图形化配置）与 **专业模式**（面向进阶用户，保留完整参数） |
| 拟物化工具配置 | 将 MCP 工具按功能归类为"感官"、"肢体"、"记忆"等模块，图形化拖拽配置 |
| 大模型 API 桥接 | 抽象层设计，支持多种 LLM Provider（OpenAI、Anthropic、Kimi、本地模型等） |
| 可扩展架构 | 插件化设计，便于后续添加新的输入处理器、工具、UI 主题等 |

---

## 2. 系统架构

### 2.1 架构总览

AAAgent 采用**分层模块化架构**，自上而下分为四层：

```
┌─────────────────────────────────────────────┐
│           Presentation Layer (UI)            │  ← 休闲/专业双模式界面
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ 休闲模式  │ │ 专业模式  │ │ 机器人配置面板 │  │
│  │(新手友好) │ │(完整参数) │ │(拟物化工具箱) │  │
│  └──────────┘ └──────────┘ └──────────────┘  │
├─────────────────────────────────────────────┤
│           Application Layer                  │  ← 核心业务流程编排
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ 模式管理器 │ │ 会话引擎  │ │ 输入路由器    │  │
│  └──────────┘ └──────────┘ └──────────────┘  │
├─────────────────────────────────────────────┤
│           Core Layer (引擎)                   │  ← 业务逻辑核心
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ LLM 桥接  │ │ 工具调度  │ │ 记忆管理     │  │
│  └──────────┘ └──────────┘ └──────────────┘  │
├─────────────────────────────────────────────┤
│           Infrastructure Layer               │  ← 基础设施与扩展
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐  │
│  │ 输入处理器 │ │ MCP 工具  │ │ 配置持久化   │  │
│  │ 集合      │ │ 集合     │ │ 插件系统     │  │
│  └──────────┘ └──────────┘ └──────────────┘  │
└─────────────────────────────────────────────┘
```

### 2.2 架构原则

1. **单一职责 (SRP)**: 每个模块只负责一类功能，边界清晰。
2. **开闭原则 (OCP)**: 对扩展开放，对修改关闭。新增输入类型、工具、模型无需修改核心代码。
3. **依赖倒置 (DIP)**: 高层模块依赖抽象接口，而非具体实现。
4. **配置即代码**: 所有能力配置通过声明式配置对象定义，UI 层自动渲染。

---

## 3. 模块详细设计

### 3.1 输入处理模块 (Input Processing Module)

#### 3.1.1 设计目标
- 支持**可扩展**的多类型输入
- 基于 markitdown 实现文件到文本的转换
- 统一输出为内部标准消息格式（Standard Message Format）

#### 3.1.2 架构图
```
┌────────────────────────────────────────────┐
│              Input Router                    │
│         (根据 MIME 类型 / 扩展名分发)          │
└──────────┬────────────┬──────────┬───────────┘
           │            │          │
    ┌──────▼──────┐ ┌───▼────┐ ┌──▼────┐ ┌──────▼──────┐
    │ 文本处理器   │ │ 文件   │ │ 图片  │ │  网页处理器   │
    │ (直接透传)   │ │ 处理器  │ │ 处理器 │ │ (URL→文本)  │
    └─────────────┘ └───┬────┘ └──┬────┘ └─────────────┘
                        │       │
              ┌─────────▼───────▼────────┐
              │    markitdown 转换层      │
              │  (PDF/DOCX/PPTX → Markdown)│
              └────────────┬─────────────┘
                           │
              ┌────────────▼────────────┐
              │  Standard Message Format │
              │  {type, content, meta}   │
              └─────────────────────────┘
```

#### 3.1.3 支持的输入类型 (V1.0)
| 类型 | 处理方式 | 依赖 |
|------|----------|------|
| 纯文本 | 直接透传 | 无 |
| Markdown 文件 | 直接读取 | 无 |
| PDF/DOCX/PPTX | markitdown 转换 | markitdown |
| 图片 | 视觉模型描述 + 原始文件上传 | 多模态 LLM |
| 音频 | 语音转文本 (Whisper) | 语音 API |
| 网页 URL | 抓取 + 清洗 → Markdown | 网页抓取工具 |
| 文件夹 | 批量递归处理 | 文件遍历器 |

#### 3.1.4 扩展接口
```typescript
interface IInputProcessor {
  readonly supportedMimeTypes: string[];
  readonly supportedExtensions: string[];
  process(input: RawInput): Promise<StandardMessage>;
}

// 注册新处理器 → InputRouter 自动识别
InputRouter.register(new MyCustomProcessor());
```

---

### 3.2 LLM 桥接模块 (LLM Bridge Module)

#### 3.2.1 设计目标
- 抽象不同 LLM Provider 的差异，提供统一调用接口
- 支持多模型切换、流式输出、工具调用 (Function Calling)

#### 3.2.2 架构图
```
┌─────────────────────────────────────────┐
│           LLM Orchestrator              │
│      (模型选择 / 负载均衡 / 回退)          │
└────────────┬────────────┬─────────────┘
             │            │
    ┌────────▼────┐  ┌────▼──────┐
    │  OpenAI     │  │  Claude   │
    │  Adapter    │  │  Adapter  │
    └─────────────┘  └───────────┘
    ┌─────────────┐  ┌───────────┐
    │  Kimi       │  │  Ollama   │
    │  Adapter    │  │  Adapter  │
    │  (Moonshot) │  │  (本地)   │
    └─────────────┘  └───────────┘
```

#### 3.2.3 统一接口定义
```typescript
interface ILLMAdapter {
  readonly provider: string;
  chat(messages: Message[], options: ChatOptions): AsyncIterable<ChatChunk>;
  callTool(messages: Message[], tools: Tool[], options: ChatOptions): Promise<ToolCallResult>;
  // 统一能力查询接口
  getCapabilities(): ModelCapabilities;
}
```

#### 3.2.4 模型能力声明
每个 Adapter 需声明自身能力，供系统决策：
```typescript
interface ModelCapabilities {
  streaming: boolean;        // 是否支持流式输出
  toolCalling: boolean;      // 是否支持工具调用
  vision: boolean;           // 是否支持图片输入
  maxTokens: number;         // 最大上下文长度
  supportsSystemPrompt: boolean;
}
```

---

### 3.3 工具调度模块 (Tool Orchestration Module)

#### 3.3.1 设计目标
- 实现 MCP (Model Context Protocol) 客户端能力
- 支持工具的动态发现、注册、调用与生命周期管理
- 为休闲模式提供**拟物化分类层**

#### 3.3.2 核心概念：拟物化分类 (Anthropomorphic Classification)

为了让新手用户直观理解 AI 工具的作用，我们将工具按功能映射到"机器人能力"的隐喻：

| 分类名称 | 隐喻 | 功能描述 | 示例工具 |
|----------|------|----------|----------|
| **感官 (Senses)** | 机器人的眼睛、耳朵 | 感知外部信息的能力 | 网页浏览、图片识别、语音识别 |
| **肢体 (Limbs)** | 机器人的手 | 操作外部系统的能力 | 文件操作、代码执行、发送邮件 |
| **记忆 (Memory)** | 机器人的大脑存储 | 存储与检索信息的能力 | 向量数据库、笔记记录、搜索历史 |
| **表达 (Expression)** | 机器人的嘴巴 | 输出与展示信息的能力 | 生成图表、语音合成、生成 PPT |
| **思维 (Cognition)** | 机器人的核心处理器 | 逻辑推理与计算能力 | 计算器、代码解释器、逻辑验证 |
| **社交 (Social)** | 机器人的通讯模块 | 与外部系统/人交互的能力 | 发送消息、API 调用、Webhook |

#### 3.3.3 配置架构
```
┌─────────────────────────────────────────────┐
│          工具配置 (Tool Configuration)         │
├─────────────────────────────────────────────┤
│  原始层 (Raw)          │  表示层 (Presentation) │
│  MCP Server Config     │  机器人能力卡片        │
│  {                     │  {                    │
│    name: "browser",    │    category: "senses", │
│    command: "npx -y...",│    icon: "👁️",        │
│    env: {...},         │    displayName: "眼睛",│
│    tools: [...]        │    description: "...", │
│  }                     │    level: 1            │
│                        │  }                    │
│  ← 专业模式直接编辑      │  ← 休闲模式图形化配置   │
└─────────────────────────────────────────────┘
```

#### 3.3.4 工具注册表
```typescript
interface IToolRegistry {
  // 注册 MCP Server
  registerServer(config: MCPServerConfig): void;
  // 按分类获取工具（休闲模式用）
  getToolsByCategory(category: ToolCategory): Tool[];
  // 获取所有可用工具
  getAllTools(): Tool[];
  // 执行工具调用
  executeTool(toolName: string, args: Record<string, any>): Promise<ToolResult>;
}
```

---

### 3.4 双模式系统 (Dual Mode System)

#### 3.4.1 模式定义

| 维度 | 休闲模式 (Casual Mode) | 专业模式 (Pro Mode) |
|------|------------------------|----------------------|
| **目标用户** | AI 新手、普通用户 | AI 进阶用户、开发者 |
| **术语体系** | 拟人化/生活化（"眼睛"、"记忆"） | 技术术语（MCP、Tool、Prompt） |
| **工具配置** | 图形化卡片，拖拽式配置 | JSON/YAML 直接编辑，完整参数 |
| **模型参数** | 预设档位（经济/平衡/质量） | 完整参数暴露（temperature、top_p 等） |
| **输出展示** | 卡片式、富文本、自动格式化 | 原始 Markdown、元信息展示 |
| **会话管理** | 自动命名、按主题归档 | 手动管理、标签系统 |
| **V1.0 状态** | ✅ 核心功能 | 📝 待定 (TBD) |

#### 3.4.2 模式切换机制
```
┌─────────────────────────────────────────┐
│            Mode Manager                 │
│  ┌─────────────────────────────────┐    │
│  │  配置抽象层 (Mode Abstraction)   │    │
│  │  - 术语映射表 (Terminology Map)   │    │
│  │  - UI 组件映射 (Component Map)    │    │
│  │  - 配置校验器 (Config Validator)  │    │
│  └─────────────────────────────────┘    │
│           ↓ 统一数据模型                 │
│  ┌─────────────────────────────────┐    │
│  │  核心引擎 (Core Engine)          │    │
│  │  (与模式无关，只处理标准化数据)     │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

#### 3.4.3 术语映射示例
```typescript
const terminologyMap = {
  casual: {
    "MCP Server": "能力模块",
    "Tool": "技能",
    "Prompt": "指令",
    "System Prompt": "角色设定",
    "Function Calling": "调用技能",
    "Temperature": "创意程度",
    "Embedding": "记忆编码",
    "Vector DB": "记忆库",
    "RAG": "查阅资料",
  },
  pro: {
    // 直接使用原始技术术语
  }
};
```

---

### 3.5 会话与记忆模块 (Session & Memory Module)

#### 3.5.1 设计目标
- 支持多会话并行管理
- 提供短期（对话上下文）与长期（持久化记忆）两种记忆
- 为 RAG 提供向量存储能力

#### 3.5.2 架构图
```
┌─────────────────────────────────────────┐
│           Session Manager               │
│  ┌────────────┐  ┌──────────────────┐  │
│  │ 会话列表    │  │ 当前会话上下文    │  │
│  │ (Metadata) │  │ (Message History) │  │
│  └────────────┘  └──────────────────┘  │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
   ┌────▼────┐           ┌────▼────┐
   │ 短期记忆 │           │ 长期记忆 │
   │ (内存)  │           │ (持久化) │
   └─────────┘           └────┬────┘
                               │
                    ┌──────────▼──────────┐
                    │  Vector Store / DB   │
                    │  (Chroma/LanceDB)    │
                    └─────────────────────┘
```

---

### 3.6 UI 模块 (Presentation Layer)

#### 3.6.1 技术选型
- **框架**: 基于 Electron / Tauri（桌面端）或 Next.js（Web 端）
- **组件库**: 自定义组件 + 拟物化设计系统
- **状态管理**: 分层状态管理（UI 状态 vs 应用状态）

#### 3.6.2 核心界面

1. **主聊天界面**
   - 输入栏（支持多模态输入入口）
   - 消息流（支持代码高亮、图片渲染、文件卡片）
   - 侧边栏（会话列表、工具配置入口）

2. **机器人配置面板**（休闲模式核心）
   - 机器人形象预览（根据配置的工具显示不同的"五官"）
   - 能力拖拽区（从工具箱拖拽到机器人对应部位）
   - 能力等级（Level 1-3，表示工具使用权限/复杂度）

3. **专业模式面板**（V1.0 占位）
   - JSON/YAML 编辑器
   - 模型参数面板
   - 日志与调试信息

#### 3.6.3 机器人配置面板 UI 概念图
```
┌──────────────────────────────────────────────┐
│  🤖 我的机器人 — 配置面板                      │
├────────────────────┬─────────────────────────┤
│                    │                         │
│    ┌──────┐       │  【工具箱】              │
│    │  👁️  │ ←──── │  ┌─────────┐            │
│    │眼睛  │       │  │ 👁️ 浏览 │ 感官      │
│    └──────┘       │  │ 🖐️ 操作 │ 肢体      │
│    ┌──────┐       │  │ 🧠 记忆 │ 记忆      │
│    │  🧠  │ ←──── │  │ 🗣️ 表达 │ 表达      │
│    │记忆  │       │  │ 🔢 计算 │ 思维      │
│    └──────┘       │  └─────────┘            │
│    ┌──────┐       │                         │
│    │  🖐️  │ ←──── │  拖拽到对应部位即可配置   │
│    │双手  │       │                         │
│    └──────┘       │                         │
│                   │                         │
│  【能力等级】Lv.2  │  【当前配置】            │
│  经济 / 平衡 / 质量 │  • 眼睛: 网页浏览 ✓      │
│                   │  • 记忆: 本地知识库 ✓     │
│                   │                         │
├────────────────────┴─────────────────────────┤
│  [ 保存配置 ]  [ 测试运行 ]  [ 切换专业模式 ]  │
└──────────────────────────────────────────────┘
```

---

## 4. 数据流设计

### 4.1 标准请求处理流程

```
用户输入
   │
   ▼
[输入路由器] ── 识别类型 ──→ [对应处理器]
   │                         │
   │                    [markitdown/转换]
   │                         │
   └────────←─────────── StandardMessage
            │
            ▼
   [模式管理器] ── 选择术语/UI 渲染策略
            │
            ▼
   [会话引擎] ── 组装上下文 + 工具声明
            │
            ▼
   [LLM 桥接] ── 调用大模型 API
            │
            ▼
   [流式输出] ── 解析工具调用 / 纯文本
            │
            ▼
   [工具调度] ←── 如需工具调用 ──→ [MCP 工具执行]
            │                              │
            └──────────←───────────────── 结果
                         │
                         ▼
                [输出渲染] ── 根据模式渲染
                         │
                         ▼
                      用户界面
```

### 4.2 工具调用流程

```
LLM 返回 tool_calls
        │
        ▼
[Tool Parser] ── 解析调用参数
        │
        ▼
[Permission Gate] ── 休闲模式：检查能力等级/用户确认
        │            专业模式：按配置直接执行/确认
        │
        ▼
[Tool Executor] ── 调用 MCP Server / 本地工具
        │
        ▼
[Result Formatter] ── 格式化为 LLM 可理解的文本
        │
        ▼
  返回给 LLM（继续对话）或展示给用户
```

---

## 5. 配置系统

### 5.1 配置分层

```
global.config.yaml          # 全局配置：主题、语言、默认模型
├── providers/              # LLM Provider 配置
│   ├── openai.yaml
│   ├── kimi.yaml
│   └── ollama.yaml
├── tools/                  # 工具配置（MCP Servers）
│   ├── browser.yaml         # 网页浏览 → 映射到 "眼睛"
│   ├── filesystem.yaml      # 文件操作 → 映射到 "双手"
│   └── memory.yaml        # 向量存储 → 映射到 "记忆"
├── modes/                  # 模式配置
│   ├── casual.yaml        # 休闲模式：术语映射、UI 配置
│   └── pro.yaml           # 专业模式：完整参数暴露
└── robots/                # 用户保存的机器人配置
    ├── default.yaml
    └── custom-1.yaml
```

### 5.2 工具配置示例

```yaml
# tools/browser.yaml — 原始技术配置
mcp_server:
  name: "browser"
  command: "npx -y @modelcontextprotocol/server-puppeteer"
  env: {}

# modes/casual.yaml — 休闲模式表示层映射
tool_presentations:
  browser:
    category: "senses"
    display_name: "眼睛"
    subtitle: "浏览网页的能力"
    icon: "👁️"
    description: "让机器人能够查看网页内容，获取最新信息"
    level: 1  # 1=基础, 2=进阶, 3=高级
    color: "#4A90D9"
```

---

## 6. 扩展性设计

### 6.1 插件系统架构

AAAgent 设计为**插件友好**的架构，扩展点包括：

| 扩展点 | 接口 | 示例 |
|--------|------|------|
| 输入处理器 | `IInputProcessor` | 新增视频输入、邮件输入 |
| LLM 适配器 | `ILLMAdapter` | 接入 Gemini、Llama.cpp |
| MCP 工具 | MCP Protocol | 任何符合 MCP 规范的工具 |
| UI 主题 | `IThemeProvider` | 自定义皮肤、布局 |
| 拟物分类 | `IToolCategorizer` | 自定义工具分类体系 |
| 记忆后端 | `IMemoryBackend` | 替换为 Weaviate、Milvus |

### 6.2 热插拔设计

```typescript
// 插件加载器
class PluginLoader {
  async loadPlugin(pluginPath: string): Promise<IPlugin> {
    const plugin = await import(pluginPath);
    // 自动注册到各模块
    if (plugin.inputProcessor) InputRouter.register(plugin.inputProcessor);
    if (plugin.llmAdapter) LLMRegistry.register(plugin.llmAdapter);
    if (plugin.toolCategorizer) ToolRegistry.registerCategorizer(plugin.toolCategorizer);
    return plugin;
  }
}
```

---

## 7. 技术栈建议

| 层级 | 技术选型 | 备选 |
|------|----------|------|
| 桌面框架 | **Tauri** (Rust + WebView) | Electron |
| 前端框架 | React + TypeScript | Vue + TS |
| 状态管理 | Zustand | Redux Toolkit |
| UI 组件 | 自定义 + Radix UI | Ant Design |
| 后端运行时 | Node.js / Rust (Tauri 命令) | Python (如果需要) |
| 配置解析 | YAML + Zod Schema 校验 | JSON Schema |
| MCP 客户端 | @modelcontextprotocol/sdk | 自研实现 |
| 向量存储 | LanceDB (轻量) | Chroma, Weaviate |
| 持久化 | SQLite / JSON 文件 | PostgreSQL |
| 打包分发 | Tauri 原生打包 | electron-builder |

---

## 8. 目录结构

```
AAAgent/
├── docs/                          # 文档
│   ├── SDD-v1.md                 # 本设计文档
│   ├── API.md                    # 接口文档 (待)
│   └── USER_GUIDE.md             # 用户手册 (待)
├── src/
│   ├── main/                     # 主进程 (Tauri/Electron)
│   │   ├── index.ts
│   │   └── preload.ts
│   ├── renderer/                 # 渲染进程 (React UI)
│   │   ├── components/           # 通用组件
│   │   ├── modes/                # 模式相关 UI
│   │   │   ├── casual/           # 休闲模式组件
│   │   │   │   ├── RobotConfigPanel/
│   │   │   │   ├── ToolCard/
│   │   │   │   └── ChatBubble/
│   │   │   └── pro/              # 专业模式组件
│   │   │       ├── JsonEditor/
│   │   │       └── LogPanel/
│   │   ├── hooks/                # 自定义 Hooks
│   │   ├── stores/               # 状态管理
│   │   └── App.tsx
│   ├── core/                     # 核心逻辑 (与 UI 无关)
│   │   ├── input/                # 输入处理
│   │   │   ├── router.ts
│   │   │   ├── processors/
│   │   │   └── interfaces.ts
│   │   ├── llm/                  # LLM 桥接
│   │   │   ├── adapters/
│   │   │   ├── orchestrator.ts
│   │   │   └── interfaces.ts
│   │   ├── tools/                # 工具调度
│   │   │   ├── registry.ts
│   │   │   ├── mcp-client.ts
│   │   │   └── categorizers/     # 拟物化分类器
│   │   ├── memory/               # 记忆管理
│   │   │   ├── short-term.ts
│   │   │   └── long-term.ts
│   │   └── session/              # 会话引擎
│   │       ├── manager.ts
│   │       └── engine.ts
│   ├── config/                   # 配置系统
│   │   ├── loader.ts
│   │   ├── schemas/
│   │   └── defaults/
│   └── utils/                    # 工具函数
│       ├── markdown.ts
│       └── validators.ts
├── assets/                       # 静态资源
│   ├── icons/
│   └── themes/
├── tests/                        # 测试
│   ├── unit/
│   └── integration/
├── plugins/                      # 插件目录 (用户可安装)
├── aaagent.config.yaml           # 全局配置文件
└── package.json / Cargo.toml
```

---

## 9. 后续规划 (V2+ 待添加功能)

> 以下功能为本项目的后续 Idea，不在 V1.0 范围内，但架构已预留扩展点。

### 9.1 专业模式完整功能
- [ ] 完整 MCP Server 配置编辑器（YAML/JSON 带校验）
- [ ] 模型参数精细化调节（temperature, top_p, frequency_penalty 等）
- [ ] 多 Agent 协作编排（LangGraph / AutoGen 集成）
- [ ] Prompt 版本管理与 A/B 测试
- [ ] 调用链路追踪与调试日志

### 9.2 输入扩展
- [ ] 实时语音对话（WebRTC 语音流）
- [ ] 视频输入分析
- [ ] 邮件/IMAP 输入
- [ ] 日历/日程输入
- [ ] 数据库连接输入

### 9.3 输出扩展
- [ ] 多模态输出（语音合成、图片生成）
- [ ] 自动生成可视化图表
- [ ] 导出为 PPT / Word / PDF
- [ ] 生成可分享链接

### 9.4 协作与同步
- [ ] 云端配置同步
- [ ] 团队共享机器人配置
- [ ] 机器人市场（分享/下载配置模板）

### 9.5 智能增强
- [ ] 自动工具推荐（根据用户问题推荐启用工具）
- [ ] 机器人自主进化（根据使用习惯优化配置）
- [ ] 多轮对话意图识别与优化

### 9.6 平台扩展
- [ ] 移动端 App (React Native / Flutter)
- [ ] 浏览器插件版本
- [ ] 服务端部署模式（Web 版）

---

## 10. 附录

### 10.1 术语表

| 术语 | 定义 |
|------|------|
| MCP | Model Context Protocol，模型上下文协议，用于标准化 AI 工具调用 |
| markitdown | 微软开源项目，将多种文件格式转换为 Markdown 文本 |
| LLM | Large Language Model，大语言模型 |
| RAG | Retrieval-Augmented Generation，检索增强生成 |
| Tool Calling | 大模型调用外部工具的机制 |
| 拟物化 | 将抽象技术概念映射为生活中可理解的实体隐喻 |

### 10.2 参考项目
- [microsoft/markitdown](https://github.com/microsoft/markitdown) — 文件转换基础
- [Model Context Protocol](https://modelcontextprotocol.io/) — 工具协议标准
- [Claude Desktop](https://claude.ai/download) — MCP 客户端参考实现
- [Cherry Studio](https://github.com/CherryHQ/cherry-studio) — 国内优秀的 LLM 客户端参考

### 10.3 变更日志

| 版本 | 日期 | 变更内容 | 作者 |
|------|------|----------|------|
| V1.0 | 2025-06-28 | 初始架构设计，核心模块定义 | - |
| V1.1 | 待定 | 待补充：详细接口定义、数据模型 | - |

---

> **文档结束**  
> 本文档为 AAAgent 项目的第一版软件设计文档，确立了项目的整体架构、模块划分和扩展方向。随着项目迭代，各模块的详细设计将在后续版本中补充完善。
