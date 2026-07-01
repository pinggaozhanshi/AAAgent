# AAAgent 架构设计 V2.0 — 从简单开始

> **版本**: V2.0 — 前端架构与渐进式路线图  
> **日期**: 2025-06-28  
> **设计哲学**: 简单优于复杂，渐进优于一步到位，可控优于完美

---

## 0. 设计哲学（The Zen of AAAgent）

```
简单优于复杂。      (Simple is better than complex.)
逐步优于一步到位。  (Incremental is better than all-in.)
可控优于完美。      (Controllable is better than perfect.)
显式优于隐式。      (Explicit is better than implicit.)
可读性很重要。      (Readability counts.)
```

本版设计的核心策略：
- **从零开始**：先构建一个仅有系统指令 + LLM 的裸核 Agent
- **逐步生长**：每完成一个里程碑，再添加下一个模块
- **始终可评测**：每个阶段都有明确的 "Guardrails"（护栏）和验证指标

---

## 1. 前端目录结构（React + TypeScript）

采用**扁平优先**（flat is better than nested）的目录风格：

```
src/
│
├── main.tsx                      # 应用入口（挂载根组件）
├── App.tsx                       # 根组件（路由/模式分发）
├── index.css                     # 全局样式（Tailwind 或原生）
│
├── stores/                       # 全局状态（Zustand，小型模块化）
│   ├── chat.store.ts             # 聊天状态：消息、加载态、错误
│   ├── agent.store.ts            # Agent 状态：模式、系统指令、工具开关
│   ├── config.store.ts           # 配置状态：模型、API Key、主题
│   └── index.ts                  # 统一导出
│
├── components/                   # 纯展示组件（Props 驱动，无状态）
│   ├── ChatBubble.tsx            # 单条消息气泡（用户/助手）
│   ├── ChatInput.tsx             # 输入框（支持多模态入口）
│   ├── RobotPanel.tsx            # 机器人配置面板（休闲模式核心）
│   ├── ToolCard.tsx              # 单个工具卡片（拟物化）
│   ├── ToolSlot.tsx              # 机器人"部位"插槽（眼睛/记忆/手等）
│   ├── ModeSwitcher.tsx          # 休闲/专业模式切换按钮
│   ├── MarkdownRenderer.tsx      # Markdown 渲染（含代码高亮）
│   ├── ModelSelector.tsx         # 模型选择下拉框
│   └── LoadingIndicator.tsx      # 流式输出加载动画
│
├── hooks/                        # 自定义业务 Hook（逻辑复用）
│   ├── useChat.ts                # 聊天主逻辑：发送、接收、流式解析
│   ├── useAgent.ts               # Agent 能力编排：组装提示词、工具声明
│   ├── useLLM.ts                 # LLM API 调用（封装 fetch/流式）
│   ├── useTools.ts               # 工具调用与结果回调
│   └── useMemory.ts              # 短期/长期记忆读写（V2 阶段）
│
├── services/                     # 与外部交互的纯函数（副作用隔离）
│   ├── llm.service.ts            # LLM Provider 请求（OpenAI/Kimi/本地）
│   ├── tool.service.ts           # MCP 工具调用封装
│   ├── input.service.ts          # 文件/URL 输入预处理（markitdown）
│   └── storage.service.ts        # 本地持久化（localStorage/IndexedDB）
│
├── types/                        # 全局类型定义（单文件，清晰）
│   └── index.ts                  # 所有接口、联合类型、枚举
│
├── utils/                        # 纯工具函数（无副作用，可测试）
│   ├── markdown.ts               # Markdown 辅助（截断、清理）
│   ├── validators.ts             # 配置校验（Zod Schema）
│   ├── terminolopy.ts            # 术语映射（休闲/专业）
│   ├── constants.ts              # 常量（分类图标、预设参数等）
│   └── helpers.ts                # 通用工具（防抖、深拷贝等）
│
├── guards/                       # 护栏模块（Guardrails）
│   ├── safety.guard.ts           # 安全过滤：敏感内容、危险工具拦截
│   ├── rate.guard.ts             # 频率控制：请求限流、Token 上限
│   └── eval.guard.ts             # 评估指标：响应质量、延迟、错误率
│
└── assets/                       # 静态资源
    ├── icons/                    # 分类图标（眼睛/手/记忆等）
    └── themes/                   # 主题配置（CSS 变量）
```

> **目录原则**：深度不超过 3 层。如果某个模块膨胀，先拆分文件而非创建新文件夹。

---

## 2. 状态管理设计（Zustand — 模块化 Store）

### 2.1 核心理念

```
一个状态一个 Store。  (One concern per store.)
Store 之间不直接引用。  (Stores are independent.)
通过 Hook 组合业务逻辑。 (Compose logic in hooks, not stores.)
```

### 2.2 Store 定义

```typescript
// stores/chat.store.ts — 聊天状态
// 职责：管理消息列表、流式输出状态、加载指示
// 不直接操作 LLM，只接收 useChat Hook 的 dispatch

interface ChatStore {
  messages: Message[];
  isLoading: boolean;
  error: string | null;

  // Actions
  addMessage: (msg: Message) => void;
  appendChunk: (chunk: string) => void;     // 流式追加
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearMessages: () => void;
}

// stores/agent.store.ts — Agent 配置状态
// 职责：管理用户配置的系统指令、启用工具、模式

interface AgentStore {
  mode: 'casual' | 'pro';
  systemPrompt: string;
  activeTools: string[];         // 工具名列表
  toolPermissions: ToolPermission[]; // 每个工具的安全等级

  // Actions
  setMode: (mode: 'casual' | 'pro') => void;
  setSystemPrompt: (prompt: string) => void;
  toggleTool: (toolName: string) => void;
  setToolPermission: (toolName: string, level: ToolLevel) => void;
}

// stores/config.store.ts — 应用配置
// 职责：模型选择、API Key、主题、持久化

interface ConfigStore {
  provider: string;              // 'openai' | 'kimi' | 'ollama'
  model: string;
  apiKey: string;
  temperature: number;           // 专业模式：精确控制
  preset: 'economy' | 'balanced' | 'quality'; // 休闲模式：预设档位
  theme: 'light' | 'dark';

  // Actions
  setProvider: (p: string) => void;
  setApiKey: (key: string) => void;
  setPreset: (p: 'economy' | 'balanced' | 'quality') => void;
  persist: () => void;           // 保存到 localStorage
  load: () => void;             // 从 localStorage 恢复
}
```

### 2.3 Store 组合（在 Hook 中，而非 Store 中）

```typescript
// hooks/useChat.ts — 业务逻辑组合层
// 将多个 Store 的 action 组合成完整的 "发送消息" 流程

export function useChat() {
  const { messages, addMessage, appendChunk, setLoading, setError } = useChatStore();
  const { systemPrompt, activeTools } = useAgentStore();
  const { provider, model, apiKey } = useConfigStore();
  const { checkSafety } = useSafetyGuard();      // 护栏

  async function sendMessage(userInput: string) {
    // 1. 添加用户消息
    addMessage({ role: 'user', content: userInput });
    setLoading(true);
    setError(null);

    // 2. 组装上下文（系统指令 + 历史消息）
    const context = buildContext(systemPrompt, messages);

    // 3. 安全护栏检查
    if (!checkSafety(userInput)) {
      setError('输入内容不符合安全策略');
      setLoading(false);
      return;
    }

    // 4. 调用 LLM（流式）
    try {
      for await (const chunk of llmService.chat(context, { provider, model, apiKey })) {
        appendChunk(chunk);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '未知错误');
    } finally {
      setLoading(false);
    }
  }

  return { messages, isLoading, error, sendMessage };
}
```

---

## 3. 组件设计（极简原则）

### 3.1 组件层次

```
App.tsx（根）
├── ModeSwitcher（顶部栏：模式切换）
├── Sidebar（左侧边栏：会话列表 + 机器人配置入口）
│   ├── SessionList
│   └── RobotPanel（机器人配置面板）
│       ├── RobotAvatar（机器人形象预览）
│       ├── ToolSlotGroup（插槽组：眼睛/记忆/手等）
│       │   └── ToolSlot（可拖拽放置工具）
│       └── ToolBox（工具箱：所有可用工具卡片）
│           └── ToolCard（单个工具：图标+名称+描述）
└── MainChat（主聊天区域）
    ├── ChatHeader（模型显示、当前工具数）
    ├── ChatMessageList（消息流）
    │   └── ChatBubble（每条消息）
    │       ├── MarkdownRenderer（文本渲染）
    │       └── ToolCallBadge（如果含工具调用，显示调用标记）
    ├── ChatInput（输入栏）
    │   ├── InputTextarea（多行输入）
    │   ├── InputAttachments（附件预览）
    │   └── SendButton
    └── LoadingIndicator（流式加载）
```

### 3.2 组件签名示例（休闲模式核心）

```typescript
// components/RobotPanel.tsx
// 机器人配置面板：拟物化工具配置的核心界面

interface RobotPanelProps {
  mode: 'casual' | 'pro';
}

export function RobotPanel({ mode }: RobotPanelProps) {
  // 从 agent store 读取当前配置的工具
  const { activeTools, toggleTool } = useAgentStore();
  const allTools = useToolRegistry(); // 从 service 获取所有可用工具

  if (mode === 'pro') {
    return <ProConfigEditor />; // 专业模式：JSON 编辑器
  }

  return (
    <div className="robot-panel">
      <RobotAvatar equippedTools={activeTools} />
      <div className="slots">
        {SLOT_DEFINITIONS.map(slot => (
          <ToolSlot
            key={slot.id}
            category={slot.category}
            icon={slot.icon}
            equippedTool={findToolInSlot(activeTools, slot.category)}
            onDrop={(toolName) => toggleTool(toolName)}
            onRemove={(toolName) => toggleTool(toolName)}
          />
        ))}
      </div>
      <ToolBox tools={allTools} onDragStart={handleDragStart} />
    </div>
  );
}

// constants.ts — 插槽定义（拟物化映射）
export const SLOT_DEFINITIONS = [
  { id: 'eyes',   category: 'senses',      icon: '👁️', label: '眼睛' },
  { id: 'memory', category: 'memory',      icon: '🧠', label: '记忆' },
  { id: 'hands',  category: 'limbs',       icon: '🖐️', label: '双手' },
  { id: 'voice',  category: 'expression',  icon: '🗣️', label: '表达' },
  { id: 'brain',  category: 'cognition',   icon: '🔢', label: '思维' },
  { id: 'comm',   category: 'social',      icon: '📡', label: '社交' },
] as const;
```

---

## 4. 渐进式开发路线图（Roadmap）

### Phase 0 — 裸核验证（V0.1）

> **目标**：验证 "系统指令 + LLM" 能正常工作。这是整个项目的基石。

```
组件：
  - ChatInput（文本输入）
  - ChatBubble（显示消息）
  - ModelSelector（选择模型）
  - ApiKeyInput（输入密钥）

状态：
  - chat.store（消息列表 + 加载态）
  - config.store（模型 + API Key）

服务：
  - llm.service（简单 fetch，非流式）

护栏：
  - eval.guard（基础指标：响应时间、错误率）

评估指标：
  ✅ 能成功发送消息并收到回复
  ✅ 平均响应时间 < 5 秒
  ✅ 错误率 < 5%
```

### Phase 1 — 多轮对话（V0.2）

> **目标**：添加短期记忆，实现上下文连贯的多轮对话。

```
新增：
  - useMemory Hook（管理对话历史上下文）
  - 系统指令编辑器（System Prompt 输入框）
  - 会话管理（新建/切换/清空会话）

修改：
  - llm.service → 支持流式输出（SSE/ReadableStream）
  - chat.store → 支持 appendChunk（流式追加）

护栏：
  - rate.guard（Token 上限限制，防止超出上下文窗口）
  - safety.guard（基础敏感内容过滤）

评估指标：
  ✅ 多轮对话上下文连贯（用户测试）
  ✅ 流式输出延迟 < 500ms（首字时间）
  ✅ 单会话最大上下文不溢出（自动截断）
```

### Phase 2 — 工具调用（V0.3）

> **目标**：让 Agent 能调用外部工具（MCP），这是 Agent 从"聊天"到"行动"的质变。

```
新增：
  - RobotPanel（机器人配置面板，休闲模式）
  - ToolCard + ToolSlot（拟物化拖拽配置）
  - useTools Hook（工具注册、调用、结果回传）
  - tool.service（MCP Client 封装）
  - 工具调用结果展示（ToolCallBadge）

修改：
  - useChat → 集成工具调用流程（发送 → LLM 返回 tool_call → 执行工具 → 回传结果 → 最终回复）

护栏：
  - safety.guard（工具权限分级：基础/进阶/高级，高等级工具需确认）
  - rate.guard（工具调用频率限制）

评估指标：
  ✅ 工具调用成功率 > 90%
  ✅ 工具调用延迟 < 10 秒（含执行时间）
  ✅ 用户能独立完成工具配置（新手测试）
```

### Phase 3 — 多模态输入（V0.4）

> **目标**：支持文件、图片、网页等输入，利用 markitdown。

```
新增：
  - 输入文件拖拽区域（DropZone）
  - 图片预览（ImagePreview）
  - 附件列表（AttachmentList）
  - input.service（markitdown 集成）

评估指标：
  ✅ PDF/DOCX 转换成功率 > 95%
  ✅ 图片输入能被多模态模型正确理解
```

### Phase 4 — 长期记忆（V1.0）

> **目标**：持久化记忆、向量检索、RAG 能力。

```
新增：
  - LongTermMemory（向量存储后端）
  - 知识库导入（本地文件向量化）
  - 记忆检索结果展示

评估指标：
  ✅ 向量检索准确率 > 80%（Top-3 命中）
  ✅ 记忆不影响对话延迟（< 100ms 额外开销）
```

### Phase 5 — 专业模式（V1.1+）

> **目标**：完整的专业配置界面，面向开发者。

```
新增：
  - JSON/YAML 配置编辑器（Monaco Editor）
  - MCP Server 自定义配置
  - 完整模型参数调节（temperature, top_p, etc.）
  - 调试日志面板（LogPanel）
  - 多 Agent 协作编排

评估指标：
  ✅ 专业用户能配置任意 MCP Server
  ✅ 配置导入导出无错误
```

---

## 5. 接口定义（类型契约）

```typescript
// types/index.ts — 全局类型契约
// 单文件，所有模块共享。修改时所有引用点同步感知。

// ==================== 核心类型 ====================

export type MessageRole = 'system' | 'user' | 'assistant' | 'tool';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  toolCalls?: ToolCall[];           //  assistant 发起的工具调用
  toolResults?: ToolResult[];       // 工具执行结果
  createdAt: Date;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResult {
  toolCallId: string;
  name: string;
  content: string;
  success: boolean;
}

// ==================== 工具配置 ====================

export type ToolCategory = 'senses' | 'limbs' | 'memory' | 'expression' | 'cognition' | 'social';
export type ToolLevel = 1 | 2 | 3; // 基础 / 进阶 / 高级

export interface ToolDefinition {
  name: string;
  description: string;
  parameters: object;              // JSON Schema
  category: ToolCategory;
  level: ToolLevel;
  // 表示层（休闲模式）
  presentation?: {
    displayName: string;
    icon: string;
    color: string;
  };
}

export interface ToolPermission {
  toolName: string;
  level: ToolLevel;
  requiresConfirmation: boolean;   // 执行前是否需用户确认
}

// ==================== LLM 配置 ====================

export interface LLMConfig {
  provider: string;                // 'openai' | 'kimi' | 'ollama' | ...
  model: string;
  apiKey: string;
  baseUrl?: string;
  // 专业参数
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  // 休闲参数（预设档位）
  preset?: 'economy' | 'balanced' | 'quality';
}

export interface LLMResponse {
  content: string;
  toolCalls?: ToolCall[];
  usage: {
    promptTokens: number;
    completionTokens: number;
  };
}

// ==================== 会话 ====================

export interface ChatSession {
  id: string;
  name: string;
  createdAt: Date;
  messages: Message[];
  config: SessionConfig;
}

export interface SessionConfig {
  model: string;
  systemPrompt: string;
  activeTools: string[];
  enableMemory: boolean;
}

// ==================== 模式 ====================

export interface ModeConfig {
  id: 'casual' | 'pro';
  displayName: string;
  // 术语映射：技术术语 → 生活化术语
  terminologyMap: Record<string, string>;
  // 可见组件
  visibleComponents: string[];
}

// ==================== 护栏 ====================

export interface GuardrailResult {
  allowed: boolean;
  reason?: string;
  severity: 'info' | 'warning' | 'block';
}

export interface EvalMetrics {
  responseTimeMs: number;
  tokenCount: number;
  errorOccurred: boolean;
  toolCallsUsed: number;
  userSatisfaction?: number;       // 可选：用户反馈评分
}
```

---

## 6. 护栏（Guardrails）设计

### 6.1 安全护栏（Safety Guard）

```typescript
// guards/safety.guard.ts
// 职责：拦截危险输入、限制危险工具、防止提示词注入

export class SafetyGuard {
  checkInput(input: string): GuardrailResult {
    // 检查敏感关键词
    if (this.containsSensitiveKeywords(input)) {
      return { allowed: false, reason: '包含敏感内容', severity: 'block' };
    }
    // 检查提示词注入（Prompt Injection）
    if (this.detectPromptInjection(input)) {
      return { allowed: false, reason: '检测到提示词注入尝试', severity: 'block' };
    }
    return { allowed: true, severity: 'info' };
  }

  checkToolExecution(toolName: string, level: ToolLevel): GuardrailResult {
    if (level === 3) {
      return { allowed: true, reason: '高级工具，需用户确认', severity: 'warning' };
    }
    return { allowed: true, severity: 'info' };
  }

  private containsSensitiveKeywords(input: string): boolean { /* ... */ return false; }
  private detectPromptInjection(input: string): boolean { /* ... */ return false; }
}
```

### 6.2 频率护栏（Rate Guard）

```typescript
// guards/rate.guard.ts
// 职责：限制请求频率、Token 消耗、工具调用次数

export class RateGuard {
  private requestTimestamps: number[] = [];
  private maxRequestsPerMinute = 30;
  private maxTokensPerSession = 100000;

  checkRequestRate(): GuardrailResult {
    const now = Date.now();
    this.requestTimestamps = this.requestTimestamps.filter(t => now - t < 60000);
    if (this.requestTimestamps.length >= this.maxRequestsPerMinute) {
      return { allowed: false, reason: '请求过于频繁，请稍后再试', severity: 'warning' };
    }
    this.requestTimestamps.push(now);
    return { allowed: true, severity: 'info' };
  }

  checkTokenBudget(usedTokens: number): GuardrailResult {
    if (usedTokens > this.maxTokensPerSession) {
      return { allowed: false, reason: '当前会话 Token 已用完，请新建会话', severity: 'warning' };
    }
    if (usedTokens > this.maxTokensPerSession * 0.8) {
      return { allowed: true, reason: 'Token 即将用完（80%）', severity: 'warning' };
    }
    return { allowed: true, severity: 'info' };
  }
}
```

### 6.3 评估护栏（Eval Guard）

```typescript
// guards/eval.guard.ts
// 职责：收集运行指标，生成评估报告

export class EvalGuard {
  private metrics: EvalMetrics[] = [];

  record(metrics: EvalMetrics): void {
    this.metrics.push(metrics);
    // 超过阈值时触发告警
    if (metrics.responseTimeMs > 10000) {
      console.warn('[EvalGuard] 响应时间超过 10 秒');
    }
    if (metrics.errorOccurred) {
      console.error('[EvalGuard] 请求发生错误');
    }
  }

  getAverageResponseTime(): number {
    if (this.metrics.length === 0) return 0;
    return this.metrics.reduce((s, m) => s + m.responseTimeMs, 0) / this.metrics.length;
  }

  getErrorRate(): number {
    if (this.metrics.length === 0) return 0;
    const errors = this.metrics.filter(m => m.errorOccurred).length;
    return errors / this.metrics.length;
  }

  // 导出 CSV 报告（用于手动分析）
  exportReport(): string {
    const headers = 'timestamp,responseTimeMs,tokenCount,errorOccurred,toolCallsUsed\n';
    const rows = this.metrics.map(m => `${m.responseTimeMs},${m.tokenCount},${m.errorOccurred},${m.toolCallsUsed}`).join('\n');
    return headers + rows;
  }
}
```

---

## 7. 服务层设计（纯函数，可测试）

```typescript
// services/llm.service.ts
// 职责：与 LLM Provider 通信。返回 AsyncIterable，支持流式。

export async function* chatStream(
  messages: Message[],
  config: LLMConfig,
): AsyncIterable<string> {
  const response = await fetch(`${config.baseUrl}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      messages,
      stream: true,
      temperature: config.temperature ?? 0.7,
      max_tokens: config.maxTokens ?? 2048,
    }),
  });

  if (!response.ok) {
    throw new Error(`LLM API error: ${response.status} ${response.statusText}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error('Response body is null');

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    // 解析 SSE 数据块...
    // 提取 delta 文本，yield 出去
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') continue;
        try {
          const chunk = JSON.parse(data);
          const content = chunk.choices?.[0]?.delta?.content;
          if (content) yield content;
        } catch { /* 忽略解析失败的行 */ }
      }
    }
  }
}
```

---

## 8. 附录：变更日志

| 版本 | 日期 | 变更 | 说明 |
|------|------|------|------|
| V1.0 | 2025-06-28 | 初始架构 | 后端核心模块定义、拟物化概念 |
| V2.0 | 2025-06-28 | 前端架构 + 渐进式 | 新增 React 组件树、Zustand 状态、路线图、护栏设计 |

---

> **结语**：本设计文档不是终点，而是起点。从 Phase 0 的裸核开始，每完成一个阶段，都将其运行起来、验证指标、收集反馈，再进入下一个阶段。这种"小步快跑、持续验证"的方式，是控制复杂性的最佳策略。
