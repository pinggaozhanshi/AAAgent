/**
 * 会话管理器
 * 负责会话的 CRUD 与持久化
 */

import { ChatSession, SessionConfig } from './interfaces';

export class SessionManager {
  private sessions: Map<string, ChatSession> = new Map();

  createSession(config: SessionConfig): ChatSession {
    const session: ChatSession = {
      id: crypto.randomUUID(),
      name: '新会话',
      createdAt: new Date(),
      messages: [],
      activeTools: config.tools,
      config,
    };
    this.sessions.set(session.id, session);
    return session;
  }

  getSession(id: string): ChatSession | undefined {
    return this.sessions.get(id);
  }

  getAllSessions(): ChatSession[] {
    return Array.from(this.sessions.values())
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime());
  }

  deleteSession(id: string): void {
    this.sessions.delete(id);
  }

  updateSession(id: string, updates: Partial<ChatSession>): void {
    const session = this.sessions.get(id);
    if (session) {
      Object.assign(session, updates);
    }
  }

  // TODO: 持久化到本地存储（SQLite / JSON）
  async saveToDisk(): Promise<void> {}
  async loadFromDisk(): Promise<void> {}
}
