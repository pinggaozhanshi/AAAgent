/**
 * 会话引擎
 * 编排单次对话的完整流程：输入 → 上下文组装 → LLM 调用 → 工具执行 → 输出
 */

import { Message } from '../llm/interfaces';
import { ChatSession } from './interfaces';

export class SessionEngine {
  // V1.0 占位实现
  // 实际需整合 InputRouter, LLMOrchestrator, ToolRegistry, Memory

  async processInput(session: ChatSession, userInput: Message): Promise<AsyncIterable<string>> {
    // 1. 添加用户消息到会话
    session.messages.push(userInput);

    // 2. 组装上下文（System Prompt + 历史消息）
    const context = this.buildContext(session);

    // 3. 调用 LLM（流式）
    // TODO: 调用 LLMOrchestrator

    // 4. 处理工具调用（如有）
    // TODO: 调用 ToolRegistry

    // 5. 返回流式输出
    async function* generator() {
      yield "[V1.0 占位] 这是模拟的流式输出...";
      yield "实际实现需整合 LLM Orchestrator 与 Tool Registry";
    }
    return generator();
  }

  private buildContext(session: ChatSession): Message[] {
    const context: Message[] = [];
    
    // 系统提示词
    if (session.config.systemPrompt) {
      context.push({
        role: 'system',
        content: session.config.systemPrompt,
      });
    }

    // 历史消息
    context.push(...session.messages);
    return context;
  }
}
