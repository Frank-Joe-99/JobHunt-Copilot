# 🔌 adapters/ 目录：多环境与外部生态协议适配层

`adapters/` 赋予了 JobHunt-Copilot **“跨生态互操作（Interoperability）”** 的核心能力。它将内部封装好的 `skills/` 和 `core/` 转换成业界通用的协议与标准，使得本工具可以被各种外部智能体环境（Claude、Cursor、OpenAI、DeepSeek Harness 等）即插即用。

---

## 🌐 核心适配能力

```
            ┌───────────────────────────────────────────────┐
            │    External Calling Environments (Harnesses)  │
            └───────────────┬───────────────────┬───────────┘
                            │ (MCP Protocol)    │ (Function Calling)
                            ▼                   ▼
            ┌───────────────────────┬───────────────────────┐
            │ adapters/mcp_server.py│ adapters/             │
            │ (Claude Desktop /     │  function_schemas.py  │
            │  Zed / Cursor)        │ (DeepSeek/OpenAI/RAG) │
            └───────────────┬───────┴───────────┬───────────┘
                            └─────────┬─────────┘
                                      ▼
                        Dispatch to Core Expert Skills
```

### 1. `mcp_server.py`（Anthropic Model Context Protocol 适配器）
- 采用官方推荐的 **FastMCP** 框架构建极轻量化的 MCP Server。
- **暴露的核心工具接口**：
  - `generate_resume_tool(template_name: str)`：根据本地档案一键编译最新 PDF 简历。
  - `match_jd_tool(jd_text: str)`：分析目标企业招聘 JD 与当前求职者经历的匹配度及差距。
  - `recommend_projects_tool(skill_gaps: list[str])`：根据技能差距检索 GitHub 开源实战项目。
  - `polish_experience_tool(raw_text: str)`：输入一段经历，按照 STAR 法则重写并提供量化指标。
- **使用体验**：配置到 Claude Desktop 后，与 Claude 对话即可直接调用本项目的全部功能。

### 2. `function_schemas.py`（OpenAI / DeepSeek 工具描述导出器）
- 自动将 `core/state.py` 中的 Pydantic 请求与响应模型一键导出为标准的 OpenAPI / JSON Schema。
- 供基于原生 API 或开源 Agent 框架（如 LangChain、CrewAI、AutoGen）直接注册为工具（Tool Calling）。
