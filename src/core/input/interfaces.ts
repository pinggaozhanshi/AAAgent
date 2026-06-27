/**
 * 输入处理器接口定义
 * 所有输入处理器需实现此接口
 */

export interface IInputProcessor {
  /** 支持的 MIME 类型列表 */
  readonly supportedMimeTypes: string[];
  /** 支持的文件扩展名列表 */
  readonly supportedExtensions: string[];
  /**
   * 处理原始输入，转换为标准消息格式
   * @param input 原始输入数据
   */
  process(input: RawInput): Promise<StandardMessage>;
}

/** 原始输入数据 */
export interface RawInput {
  /** 输入类型 */
  type: 'text' | 'file' | 'url' | 'audio' | 'image' | 'folder';
  /** 原始内容/路径 */
  content: string | File | Blob;
  /** 额外元数据 */
  meta?: Record<string, any>;
}

/** 标准消息格式（所有输入转换后的统一格式） */
export interface StandardMessage {
  /** 消息类型 */
  type: 'text' | 'image' | 'audio' | 'mixed';
  /** 文本内容（markitdown 转换后的 Markdown 文本） */
  textContent: string;
  /** 附件列表（图片、音频等二进制内容） */
  attachments?: Attachment[];
  /** 元信息：来源、大小、处理时间等 */
  meta: {
    sourceType: string;
    originalName?: string;
    processedAt: string;
    size?: number;
  };
}

export interface Attachment {
  mimeType: string;
  data: ArrayBuffer | string; // base64 或原始 buffer
  name: string;
}
