/**
 * LLM 适配器接口定义
 * 所有 LLM Provider 适配器需实现此接口
 */

export interface ILLMAdapter {
  /** Provider 标识 */
  readonly provider: string;
  /** Provider 显示名称 */
  readonly displayName: string;

  /**
   * 发起对话（流式输出）
   * @param messages 消息历史
   * @param options 对话选项
   */
  chat(messages: Message[], options: ChatOptions): AsyncIterable<ChatChunk>;

  /**
   * 调用工具（Function Calling / Tool Use）
   * @param messages 消息历史
   * @param tools 可用工具声明
   * @param options 对话选项
   */
  callTool(messages: Message[], tools: Tool[], options: ChatOptions): Promise<ToolCallResult>;

  /**
   * 获取模型能力声明
   */
  getCapabilities(): ModelCapabilities;
}

/** 对话消息 */
export interface Message {
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  /** 多模态内容（图片等） */
  attachments?: Array<{
    type: 'image_url' | 'image_base64';
    source: string;
  }>;
  /** 工具调用结果 */
  toolCallId?: string;
}

/** 对话选项 */
export interface ChatOptions {
  model: string;
  temperature?: number;
  maxTokens?: number;
  topP?: number;
  systemPrompt?: string;
  /** 是否启用流式输出 */
  streaming?: boolean;
}

/** 流式输出片段 */
export interface ChatChunk {
  /** 文本增量 */
  delta: string;
  /** 是否为最后一块 */
  isDone: boolean;
  /** 工具调用声明（如有） */
  toolCalls?: ToolCall[];
  /** 使用量统计（最后一块时提供） */
  usage?: {
    promptTokens: number;
    completionTokens: number;
  };
}

/** 工具声明 */
export interface Tool {
  name: string;
  description: string;
  parameters: object; // JSON Schema
}

/** 工具调用 */
export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
}

/** 工具调用结果 */
export interface ToolCallResult {
  /**  assistant 的文本回复 */
  content: string;
  /** 实际调用的工具列表 */
  executedTools: {
    toolCallId: string;
    name: string;
    result: string;
  }[];
  usage: {
    promptTokens: number;
    completionTokens: number;
  };
}

/** 模型能力声明 */
export interface ModelCapabilities {
  /** 是否支持流式输出 */
  streaming: boolean;
  /** 是否支持工具调用 */
  toolCalling: boolean;
  /** 是否支持视觉输入 */
  vision: boolean;
  /** 最大上下文 Token 数 */
  maxTokens: number;
  /** 是否支持系统提示词 */
  supportsSystemPrompt: boolean;
}
