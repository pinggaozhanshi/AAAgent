/**
 * 会话引擎接口定义
 */

export interface ISessionEngine {
  /** 创建新会话 */
  createSession(config: SessionConfig): ChatSession;
  /** 获取会话 */
  getSession(id: string): ChatSession | undefined;
  /** 获取所有会话 */
  getAllSessions(): ChatSession[];
  /** 删除会话 */
  deleteSession(id: string): void;
}

export interface ChatSession {
  id: string;
  /** 会话名称（可自动生成） */
  name: string;
  /** 创建时间 */
  createdAt: Date;
  /** 消息历史 */
  messages: Message[];
  /** 当前启用的工具列表 */
  activeTools: string[];
  /** 会话配置 */
  config: SessionConfig;
}

export interface SessionConfig {
  /** 使用的模型 */
  model: string;
  /** 模型预设 */
  preset?: string;
  /** 系统提示词（角色设定） */
  systemPrompt?: string;
  /** 启用的工具 */
  tools: string[];
  /** 是否启用记忆 */
  enableMemory: boolean;
  /** 模式：休闲/专业 */
  mode: 'casual' | 'pro';
}

// 复用 LLM 接口中的 Message
import type { Message } from '../llm/interfaces';
export type { Message };
