/**
 * 短期记忆（会话级上下文）
 * 保留当前对话的最近 N 条消息
 */

import { Message } from '../llm/interfaces';

export class ShortTermMemory {
  private messages: Message[] = [];
  private maxMessages: number;

  constructor(maxMessages: number = 50) {
    this.maxMessages = maxMessages;
  }

  add(message: Message): void {
    this.messages.push(message);
    if (this.messages.length > this.maxMessages) {
      // 保留 system 消息，移除最早的非 system 消息
      const systemMessages = this.messages.filter(m => m.role === 'system');
      const otherMessages = this.messages.filter(m => m.role !== 'system');
      while (otherMessages.length > this.maxMessages - systemMessages.length) {
        otherMessages.shift();
      }
      this.messages = [...systemMessages, ...otherMessages];
    }
  }

  getMessages(): Message[] {
    return [...this.messages];
  }

  clear(): void {
    this.messages = [];
  }

  setMaxMessages(max: number): void {
    this.maxMessages = max;
  }
}
