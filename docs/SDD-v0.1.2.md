# AAAgent 架构设计 v0.1.2 — Electron 桌面化与渐进式实现

## 0. 设计哲学

AAAgent 的 V2 不追求一次性实现完整 Agent，而是先交付一个可靠的桌面聊天产品，再逐步增加工具、多模态和记忆能力。

核心原则：

- **先能运行，再扩展能力**：每个阶段都应该能独立启动和演示。
- **用户看到的是 Agent，开发者维护的是清晰边界**：拟物化只存在于 UI 表示层。
- **共享契约，不共享混乱**：主进程、渲染进程和服务层通过 TypeScript 类型通信。
- **本地默认安全**：密钥、会话和文件不因为使用桌面 UI 就自动上传。
- **控制信息密度**：休闲模式保持简单，专业模式再显示完整参数。

## 1. 目标工程结构

```text
src/
├── main/
│   ├── main.ts              # Electron 生命周期和窗口
│   ├── preload.ts           # contextBridge 安全 API
│   ├── local-server.ts      # 启动 Node 服务
│   └── ipc/                 # IPC handler
├── renderer/
│   ├── app/
│   │   ├── App.tsx
│   │   ├── routes.tsx
│   │   └── layout/
│   ├── components/
│   │   ├── ui/
│   │   ├── chat/
│   │   ├── settings/
│   │   └── abilities/
│   ├── features/
│   │   ├── chat/
│   │   ├── sessions/
│   │   ├── providers/
│   │   └── tools/
│   ├── stores/              # Zustand stores
│   └── styles/              # 主题、变量和全局样式
├── services/
│   ├── llm/
│   ├── sessions/
│   ├── tools/
│   └── memory/
└── shared/
    ├── contracts.ts
    └── schemas.ts
```

当前 `src/ui` 中的 HTML/CSS/JavaScript 原型作为 Phase 0 的验证版本保留。迁移到 React 后，功能行为不变，逐步替换视图层。

## 2. Electron 运行模型

### 2.1 开发模式

```text
npm run desktop:dev
  → Vite 启动 renderer
  → Node 服务启动本地 API
  → Electron 加载 Vite 地址
```

### 2.2 打包模式

```text
AAAgent.exe
  → Electron 启动
  → 加载打包后的 renderer 文件
  → 启动内置 Node 服务
  → BrowserWindow 显示应用
```

Electron 主进程不得把 API Key 注入页面 URL 或渲染进程全局变量。敏感配置通过 IPC 请求主进程，由主进程读取 safeStorage 后交给本地服务使用。

## 3. React 组件设计

组件按业务功能拆分，避免把整个应用写成一个页面组件。

```tsx
export function ChatPage() {
  const messages = useChatStore((state) => state.messages);
  const sendMessage = useChatStore((state) => state.sendMessage);

  return (
    <ChatLayout>
      <ConversationList messages={messages} />
      <ChatComposer onSubmit={sendMessage} />
    </ChatLayout>
  );
}
```

组件职责：

- `ChatLayout`：控制桌面窗口内的整体布局。
- `ConversationList`：渲染消息、流式状态和错误状态。
- `ChatComposer`：文本、文件和发送控制。
- `ProviderSettings`：模型供应商、Base URL、模型和 API Key。
- `AbilityPanel`：机器人能力启用状态。
- `ToolApprovalDialog`：高风险工具的确认。

页面负责组合组件，服务负责业务逻辑，Store 负责状态，不在 UI 组件里直接拼接模型请求。

## 4. Zustand 状态设计

Store 按功能拆分：

```ts
interface ChatState {
  activeSessionId: string | null;
  messages: ChatMessage[];
  isGenerating: boolean;
  error: string | null;
  sendMessage(input: string): Promise<void>;
  stopGeneration(): void;
}

interface SettingsState {
  provider: ProviderConfig;
  mode: 'casual' | 'professional';
  theme: 'light' | 'dark' | 'system';
  updateProvider(config: Partial<ProviderConfig>): void;
}

interface AbilityState {
  enabled: Record<AbilityName, boolean>;
  toggle(name: AbilityName): void;
}
```

Store 不直接保存未加密的 API Key。开发环境可以暂存表单值，正式环境提交后由主进程处理敏感字段。

## 5. 服务层与接口契约

### 5.1 聊天接口

```ts
export interface ChatRequest {
  sessionId?: string;
  provider: string;
  model: string;
  messages: ChatMessage[];
  temperature?: number;
  maxTokens?: number;
  enabledAbilities?: AbilityName[];
}

export interface ChatChunk {
  type: 'text' | 'tool_call' | 'error' | 'done';
  content?: string;
  toolCall?: ToolCall;
  error?: string;
}
```

### 5.2 Provider 配置

```ts
export const providerConfigSchema = z.object({
  provider: z.string().min(1),
  baseUrl: z.string().url(),
  model: z.string().min(1),
  apiKey: z.string().optional(),
});
```

所有供应商均通过 `/chat/completions` 兼容协议接入。供应商差异只存在于配置和错误适配层。

### 5.3 IPC 契约

```ts
window.aaagent.chat.send(request)
window.aaagent.chat.stop(sessionId)
window.aaagent.settings.get()
window.aaagent.settings.save(settings)
window.aaagent.tools.list()
window.aaagent.tools.approve(toolCallId)
```

`window.aaagent` 由 preload 通过 `contextBridge` 暴露，渲染进程不能使用 `nodeIntegration`。

## 6. 视觉和交互设计

AAAgent 的设计参考 OpenAI 和 Google 的产品感：

- 大面积留白和稳定的内容宽度
- 中性背景、清晰边框和低强度阴影
- 颜色用于状态和重点，而不是装饰堆叠
- 控件有明确的 hover、focus、loading 和 error 状态
- 桌面端采用固定导航和可滚动配置侧栏
- 移动或窄窗口时，配置栏变成抽屉式面板
- 对话内容占据主区域，输入框保持在底部
- 不使用无法解释功能的装饰性卡片和复杂动效

休闲模式把技术参数翻译成用户语言；专业模式提供完整字段、日志和诊断信息。

## 7. 渐进式路线图

### Phase 0 — 裸核验证（V0.1）

目标：证明“输入 API 后可以对话”。

- Provider、Base URL、API Key、Model 配置
- 单轮和基础多轮对话
- OpenAI 兼容接口
- 流式输出和停止生成
- 本地 Node 服务
- 当前原生 HTML 原型

验收：配置有效 API 后，可以完成一次真实对话；错误会以可读文本展示。

### Phase 0.5 — 桌面化（V0.1.5）

目标：从本地网页原型变成独立软件窗口。

- Electron 主进程
- preload 和安全 IPC
- 启动、健康检查和关闭 Node 服务
- Vite 开发窗口
- electron-builder Windows 打包

验收：双击桌面程序即可打开 AAAgent，不启动外部浏览器。

### Phase 1 — 多轮对话（V0.2）

- SQLite 数据库
- 会话列表、新建、重命名和删除
- 消息持久化
- 上下文长度控制
- 网络错误重试和中断恢复

### Phase 2 — 工具调用（V0.3）

- MCP Client 和工具注册表
- 能力槽开关
- 参数校验
- 高风险操作确认
- 工具调用记录

### Phase 3 — 多模态输入（V0.4）

- Electron 文件选择器
- 文件内容抽取
- 图片输入
- URL 解析
- 需要时启动 FastAPI 文档处理服务

### Phase 4 — 长期记忆（V1.0）

- 记忆提取策略
- SQLite FTS5 检索
- 记忆编辑和删除
- 会话引用来源
- 隐私和数据清理入口

### Phase 5 — 专业模式（V1.1+）

- 完整模型参数
- Prompt 模板
- 工具权限策略
- 调试日志和请求追踪
- Provider 管理
- 插件和自动化工作流

## 8. 护栏设计

### 8.1 安全护栏

- API Key 使用 safeStorage 或系统凭据保存。
- 文件访问限制在用户明确选择的路径。
- 工具调用根据权限级别分类：只读、可修改、危险。
- 危险操作必须二次确认。

### 8.2 频率护栏

- 单次请求限制最大 Token 和超时时间。
- 流式请求可被用户停止。
- 本地服务限制并发请求数。
- 对同一 Provider 的连续失败进行退避。

### 8.3 质量护栏

- 记录请求状态、耗时和错误类型，不记录 API Key。
- 关键服务使用单元测试。
- UI 使用组件测试覆盖发送、停止、错误和空状态。
- 使用 Playwright 验证桌面前端的主要流程。

## 9. 测试策略

```text
单元测试       → services、schemas、纯函数
组件测试       → ChatComposer、ProviderSettings、AbilityPanel
集成测试       → Node 服务与 SQLite
端到端测试     → 启动 Electron 后完成配置和对话流程
```

每个 Phase 都要包含：可启动入口、最小演示流程、错误路径和文档更新。

## 10. 交付标准

一个可交付的 AAAgent 版本必须满足：

- 可通过一个明确入口启动
- 不要求用户修改源码才能配置模型
- 关键数据不会因为应用关闭而丢失
- 网络和模型错误有清晰反馈
- 文档中的命令与实际脚本一致
- Windows 用户可以获得安装包或可执行目录

## 11. 变更记录

- **V2 技术路线更新**：从备选桌面框架统一为 Electron。
- **V2 前端更新**：从原生 HTML 原型逐步迁移到 React + TypeScript + Vite。
- **数据层更新**：从仅使用 localStorage 规划为 SQLite 本地持久化。
- **服务层更新**：Node.js 作为默认本地服务，FastAPI 仅作为可选 Python 能力层。