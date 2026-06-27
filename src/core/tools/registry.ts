/**
 * 工具注册表
 * 管理所有可用工具，支持按拟物化分类查询
 */

import { 
  IToolRegistry, MCPServerConfig, RegisteredTool, ToolResult, 
  ToolCategory, ToolPresentation 
} from './interfaces';
import { MCPClient } from './mcp-client';

export class ToolRegistry implements IToolRegistry {
  private mcpClient = new MCPClient();
  private tools: Map<string, RegisteredTool> = new Map();
  private presentations: Map<string, ToolPresentation> = new Map();

  async registerServer(config: MCPServerConfig): Promise<void> {
    await this.mcpClient.connect(config);
    const tools = await this.mcpClient.listTools(config.name);
    for (const tool of tools) {
      this.tools.set(tool.name, {
        name: tool.name,
        description: tool.description,
        server: config.name,
        presentation: this.presentations.get(tool.name),
      });
    }
  }

  unregisterServer(name: string): void {
    this.mcpClient.disconnect(name);
    // 清理该 server 下的所有工具
    for (const [toolName, tool] of this.tools) {
      if (tool.server === name) {
        this.tools.delete(toolName);
      }
    }
  }

  getToolsByCategory(category: ToolCategory): RegisteredTool[] {
    return Array.from(this.tools.values()).filter(
      t => t.presentation?.category === category
    );
  }

  getAllTools(): RegisteredTool[] {
    return Array.from(this.tools.values());
  }

  async executeTool(toolName: string, args: Record<string, any>): Promise<ToolResult> {
    const tool = this.tools.get(toolName);
    if (!tool) {
      return { success: false, content: '', error: `Tool not found: ${toolName}` };
    }
    return this.mcpClient.callTool(tool.server, toolName, args);
  }

  /** 注册工具的表示层配置（休闲模式用） */
  registerPresentation(toolName: string, presentation: ToolPresentation): void {
    this.presentations.set(toolName, presentation);
    // 如果工具已注册，更新其 presentation
    const tool = this.tools.get(toolName);
    if (tool) {
      tool.presentation = presentation;
    }
  }
}
