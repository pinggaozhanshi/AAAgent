/**
 * 工具分类与表示接口定义
 * 支持拟物化分类（休闲模式）与原始分类（专业模式）
 */

/** 工具分类（拟物化） */
export enum ToolCategory {
  SENSES = 'senses',       // 感官：浏览、识别、感知
  LIMBS = 'limbs',         // 肢体：操作、执行
  MEMORY = 'memory',       // 记忆：存储、检索
  EXPRESSION = 'expression', // 表达：输出、展示
  COGNITION = 'cognition', // 思维：计算、推理
  SOCIAL = 'social',       // 社交：通讯、交互
}

/** 工具等级 */
export enum ToolLevel {
  BASIC = 1,    // 基础：只读、安全操作
  ADVANCED = 2, // 进阶：可修改、需确认
  POWER = 3,    // 高级：执行代码、系统级操作
}

/** 工具表示层配置（休闲模式用） */
export interface ToolPresentation {
  /** 所属分类 */
  category: ToolCategory;
  /** 显示名称 */
  displayName: string;
  /** 副标题 */
  subtitle: string;
  /** Emoji 图标 */
  icon: string;
  /** 描述 */
  description: string;
  /** 等级 */
  level: ToolLevel;
  /** 主题色 */
  color: string;
}

/** 工具注册表接口 */
export interface IToolRegistry {
  /** 注册 MCP Server */
  registerServer(config: MCPServerConfig): Promise<void>;
  /** 注销 MCP Server */
  unregisterServer(name: string): void;
  /** 按分类获取工具（休闲模式） */
  getToolsByCategory(category: ToolCategory): RegisteredTool[];
  /** 获取所有可用工具 */
  getAllTools(): RegisteredTool[];
  /** 执行工具调用 */
  executeTool(toolName: string, args: Record<string, any>): Promise<ToolResult>;
}

/** MCP Server 配置 */
export interface MCPServerConfig {
  name: string;
  command: string;
  args?: string[];
  env?: Record<string, string>;
  tools?: Tool[];
}

/** 注册后的工具 */
export interface RegisteredTool {
  name: string;
  description: string;
  /** 原始 MCP Server */
  server: string;
  /** 表示层配置（如有） */
  presentation?: ToolPresentation;
}

/** 工具执行结果 */
export interface ToolResult {
  success: boolean;
  content: string;
  error?: string;
}

// 复用 LLM 接口中的 Tool 定义
import type { Tool } from '../llm/interfaces';
export type { Tool };
