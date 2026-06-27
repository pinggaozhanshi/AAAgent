/**
 * 输入路由器
 * 负责根据输入类型分发到对应的处理器
 */

import { IInputProcessor, RawInput, StandardMessage } from './interfaces';

export class InputRouter {
  private processors: IInputProcessor[] = [];

  register(processor: IInputProcessor): void {
    this.processors.push(processor);
  }

  unregister(processor: IInputProcessor): void {
    this.processors = this.processors.filter(p => p !== processor);
  }

  async route(input: RawInput): Promise<StandardMessage> {
    // 根据输入类型和 MIME 类型找到合适的处理器
    const processor = this.findProcessor(input);
    if (!processor) {
      throw new Error(`No processor found for input type: ${input.type}`);
    }
    return processor.process(input);
  }

  private findProcessor(input: RawInput): IInputProcessor | undefined {
    // 简单实现：按 MIME 类型和扩展名匹配
    // V1.0 占位，实际需完善匹配逻辑
    const mimeType = input.meta?.mimeType as string;
    const ext = input.meta?.extension as string;
    
    return this.processors.find(p => 
      p.supportedMimeTypes.includes(mimeType) || 
      p.supportedExtensions.includes(ext)
    );
  }
}
