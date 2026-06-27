/**
 * 长期记忆（持久化向量存储）
 * 基于向量数据库实现语义检索
 */

export interface LongTermMemoryEntry {
  id: string;
  content: string;
  embedding: number[];
  metadata: Record<string, any>;
  timestamp: Date;
}

export class LongTermMemory {
  // V1.0 占位实现
  // 实际需集成 LanceDB / Chroma / SQLite-vec 等

  private entries: LongTermMemoryEntry[] = [];

  async add(content: string, metadata?: Record<string, any>): Promise<void> {
    // TODO: 调用 Embedding 服务生成向量
    const entry: LongTermMemoryEntry = {
      id: crypto.randomUUID(),
      content,
      embedding: [], // 待生成
      metadata: metadata || {},
      timestamp: new Date(),
    };
    this.entries.push(entry);
  }

  async query(query: string, topK: number = 5): Promise<LongTermMemoryEntry[]> {
    // TODO: 生成 query 的 embedding，进行向量相似度检索
    return this.entries.slice(0, topK);
  }

  async delete(id: string): Promise<void> {
    this.entries = this.entries.filter(e => e.id !== id);
  }

  async clear(): Promise<void> {
    this.entries = [];
  }
}
