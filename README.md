# AAAgent — AI Agent for All

> 一款面向 AI 新手的友好型多模态智能体桌面应用。

## 项目简介

AAAgent 基于微软 [markitdown](https://github.com/microsoft/markitdown) 项目构建，致力于降低 AI Agent 的使用门槛。用户可以通过多种输入方式（文本、文件、图片、网页等）与大模型交互，并通过**拟物化的"机器人能力"概念**直观配置 AI 工具。

## 核心特性

- 🎯 **对新手友好**：休闲模式用生活化术语替代技术黑话
- 🤖 **拟物化配置**：将 MCP 工具映射为机器人的"眼睛"、"记忆"、"双手"等能力
- 📎 **多模态输入**：支持文本、文件、图片、音频、网页链接等
- 🧠 **双模式切换**：休闲模式（图形化）与专业模式（完整参数）
- 🔌 **可扩展架构**：插件化设计，支持自定义输入处理器、LLM 适配器、工具等

## 项目状态

| 版本 | 状态 | 说明 |
|------|------|------|
| V1.0 | 🚧 设计中 | 完成架构设计文档，核心模块待开发 |

## 快速开始

```bash
# 克隆项目
git clone <repo-url> AAAgent
cd AAAgent

# 安装依赖 (待补充)
# npm install

# 启动开发 (待补充)
# npm run dev
```

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 软件设计文档 | [docs/SDD-v1.md](./docs/SDD-v1.md) | V1.0 架构设计、模块划分、扩展性设计 |
| API 文档 | docs/API.md | 📝 待编写 |
| 用户手册 | docs/USER_GUIDE.md | 📝 待编写 |

## 目录结构

```
AAAgent/
├── docs/              # 项目文档
├── src/               # 源代码
│   ├── main/          # 主进程 (Tauri/Electron)
│   ├── renderer/      # 渲染进程 (React UI)
│   ├── core/          # 核心逻辑 (输入/LLM/工具/记忆/会话)
│   └── config/        # 配置系统
├── assets/            # 静态资源
├── tests/             # 测试用例
└── plugins/           # 插件目录
```

## 技术栈

- **桌面框架**: Tauri (Rust + WebView)
- **前端**: React + TypeScript
- **状态管理**: Zustand
- **MCP 客户端**: @modelcontextprotocol/sdk
- **配置**: YAML + Zod Schema 校验

## 参与贡献

本项目处于早期设计阶段，欢迎提出 Idea 与建议！

## 许可证

MIT (待确认)

---

> 注意：本项目为早期原型，许多功能仍在规划中。详见 [docs/SDD-v1.md](./docs/SDD-v1.md) 的"后续规划"章节。
