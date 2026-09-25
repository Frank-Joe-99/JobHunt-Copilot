# 🔌 adapters/ 目录：多环境与外部生态协议适配层

`adapters/` 赋予了 JobHunt-Copilot **“跨生态互操作（Interoperability）”** 的核心能力。它将内部封装好的 `skills/` 和 `core/` 转换成业界通用的协议与标准，使得本工具可以被各种外部主流智能体环境（Cursor、Claude Desktop、VS Code、Zed、OpenAI Harness 等）即插即用。

---

## 🌐 核心适配架构

```text
┌─────────────────────────────────────────────────────────────┐
│          External AI Agent Hosts & Desktop Clients          │
│       (Claude Desktop, Cursor IDE, VS Code, Zed, etc.)      │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Model Context Protocol - stdio)
                               ▼
            ┌────────────────────────────────────┐
            │       adapters/mcp_server.py       │
            │     (Anthropic MCP 标准协议服务端)    │
            └──────────────────┬─────────────────┘
                               │ Dispatch Tools
                               ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                     Core Expert Skills                      │
 │ ├── skills/resume_generator     (极速排版双格式简历)          │
 │ ├── skills/jd_matcher           (JD穿透比对与自荐信)          │
 │ ├── skills/project_recommender  (GitHub 开源项目补短板)       │
 │ ├── core/workflow               (一键全套定制交付流)          │
 │ └── skills/application_tracker  (投递看板与日程漏斗)          │
 └─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 暴露的 7 大 MCP 核心工具 (Tools)

| Tool 名称 | 功能简介 | 核心参数 |
| :--- | :--- | :--- |
| `tool_generate_resume` | 依据本地主档案编译输出高保真 PDF 与 Word 双格式简历 | `template` ("modern"), `output_name` |
| `tool_analyze_jd` | 深度穿透分析岗位招聘 JD，比对技能契合度并生成自荐信草稿 | `jd_text`, `provider` |
| `tool_recommend_projects` | 针对技能短板检索高价值 GitHub 开源项目并给出 STAR 范文 | `skills` (列表), `language`, `provider` |
| `tool_one_click_tailor` | **【一键全套定向交付】**比对+开源推荐+STAR强化+生成简历+入库 | `jd_text`, `auto_track` (默认 True) |
| `tool_track_application` | 投递看板管理：登记新投递或推进已有求职流程阶段/面试预约 | `company`, `role`, `status`, `record_id`, `next_schedule_time` |
| `tool_get_upcoming_schedules` | 查询未来若干天（默认 7 天）以及近期的面试/笔试日程与倒计时 | `days_ahead` (默认 7) |
| `tool_get_funnel_analytics` | 获取当前求职转化漏斗全景统计（网申数、进面数、Offer数及比率） | 无需必填参数 |

---

## 💻 外部集成配置指南

### 1. Claude Desktop 配置
在 Claude Desktop 配置文件（Windows: `%APPDATA%\Claude\claude_desktop_config.json`，macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`）中添加：

```json
{
  "mcpServers": {
    "jobhunt-copilot": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\11482\\Desktop\\JobHunt-Copilot",
        "run",
        "python",
        "-m",
        "adapters.mcp_server"
      ]
    }
  }
}
```

### 2. Cursor IDE 配置
打开 Cursor **Settings** ➔ **Features** ➔ **MCP** ➔ 点击 **Add new MCP server**：
- **Name**: `jobhunt-copilot`
- **Type**: `command`
- **Command**: `uv --directory C:\Users\11482\Desktop\JobHunt-Copilot run python -m adapters.mcp_server`

---

## 🧪 验证与自测

可在终端直接自测 Tools 注册与连通性（Windows 终端建议携带 -X utf8 避免 Emoji 编码异常）：
```bash
uv run python -X utf8 -c "from adapters.mcp_server import mcp_app; import asyncio; print(asyncio.run(mcp_app.list_tools()))"
```
