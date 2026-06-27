/**
 * LLM 编排器
 * 负责模型选择、负载均衡与回退
 */

import { ILLMAdapter, Message, ChatOptions, ChatChunk, Tool, ToolCallResult } from './interfaces';

export class LLMOrchestrator {
  private adapters: Map<string, ILLMAdapter> = new Map();
  private defaultProvider: string = '';

  register(adapter: ILLMAdapter): void {
    this.adapters.set(adapter.provider, adapter);
  }

  setDefault(provider: string): void {
    this.defaultProvider = provider;
  }

  async *chat(messages: Message[], options: ChatOptions): AsyncIterable<ChatChunk> {
    const provider = options.provider || this.defaultProvider;
    const adapter = this.adapters.get(provider);
    if (!adapter) {
      throw new Error(`Provider not found: ${provider}`);
    }
    yield* adapter.chat(messages, options);
  }

  async callTool(messages: Message[], tools: Tool[], options: ChatOptions): Promise<ToolCallResult> {
    const provider = options.provider || this.defaultProvider;
    const adapter = this.adapters.get(provider);
    if (!adapter) {
      throw new Error(`Provider not found: ${provider}`);
    }
    return adapter.callTool(messages, tools, options);
  }

  getAvailableProviders(): string[] {
    return Array.from(this.adapters.keys());
  }
}
