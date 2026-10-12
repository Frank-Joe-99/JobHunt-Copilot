# 🔌 adapters/ 目录：多环境与外部生态协议适配层

`adapters/` 赋予了 JobHunt-Copilot **“跨生态互操作（Interoperability）”** 的核心能力。它将内部封装好的 `skills/` 和 `core/` 转换成业界通用的协议与标准，使得本工具可以被各种外部主流智能体环境（Claude Desktop、Cursor、VS Code、Codex 等）即插即用。

---

## 🌐 核心适配架构

```text
┌─────────────────────────────────────────────────────────────┐
│          External AI Agent Hosts & Desktop Clients          │
│       (Claude Desktop, Cursor IDE, VS Code, Codex, etc.)    │
└──────────────────────────────┬──────────────────────────────┘
                               │ (Model Context Protocol - stdio JSON-RPC)
                               ▼
             ┌────────────────────────────────────┐
             │       adapters/mcp_server.py       │
             │   (Anthropic MCP 2.x 标准服务端)    │
             └──────────────────┬─────────────────┘
                                │ Dispatch Tools & Resources
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                Core Skills & Infrastructure                 │
 │ ├── skills/resume_generator     (极速排版双格式简历)          │
 │ ├── skills/jd_matcher           (JD穿透比对与自荐信)          │
 │ ├── skills/project_recommender  (GitHub 开源项目补短板)       │
 │ ├── skills/resume_polisher      (ATS体检与经历STAR润色)       │
 │ ├── skills/job_radar            (全网/批量岗位雷达简报)        │
 │ ├── skills/mock_interviewer     (AI场景化模拟面试状态机)      │
 │ ├── skills/application_tracker  (投递看板与日程漏斗)          │
 │ └── core/workflow               (一键全套定制交付长任务流)    │
 └─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 暴露的 13 大 MCP 核心工具 (Tools)

系统支持带注解（`readOnlyHint`、`openWorldHint`、`destructiveHint`）的丰富工具集，全面覆盖 8 项核心求职能力：

### 1. 简历与岗位深度匹配
| Tool 名称 | 注解 | 功能简介 | 关键入参 |
| :--- | :--- | :--- | :--- |
| `tool_generate_resume` | 本地写入 | 依据本地主档案编译输出高保真 PDF 与 Word 双格式简历 | `template` ("modern"/"minimal"), `output_name` |
| `tool_analyze_jd` | 只读·外联 | 深度穿透分析岗位招聘 JD，比对技能契合度并生成自荐信草稿 | `jd_text`, `provider` |
| `tool_recommend_projects` | 只读·外联 | 针对技能短板检索高价值 GitHub 开源项目并给出 STAR 范文 | `skills` (列表), `language`, `provider` |
| `tool_one_click_tailor` | 写入·长任务 | **【一键全套定向交付】**比对+开源推荐+STAR强化+生成简历+入库（支持 5 步进度实时通知） | `jd_text`, `auto_track` (默认 **False**), `enable_github` (默认 True) |

### 2. 简历体检与 STAR 润色
| Tool 名称 | 注解 | 功能简介 | 关键入参 |
| :--- | :--- | :--- | :--- |
| `tool_diagnose_ats` | 只读·外联 | 对本地简历档案进行 ATS 关键词覆盖率、规范性与量化指标深度体检打分 | `target_jd_text` (可选), `provider` |
| `tool_polish_experiences` | 只读·外联 | 按 STAR 原则重构经历亮点（严守事实底线，严禁捏造虚假指标） | `provider` |

### 3. 机会雷达与投递看板
| Tool 名称 | 注解 | 功能简介 | 关键入参 |
| :--- | :--- | :--- | :--- |
| `tool_scan_jds` | 写入·外联 | 批量扫描目录内 JD，生成机会梯队排名与共性短板雷达战略报告（内置越权路径拦截） | `directory` (默认 "storage/raw_jds"), `provider` |
| `tool_track_application` | 本地写入 | 投递看板管理：登记新投递或推进已有流程状态（枚举校验）/录入面试日程 | `company`, `role`, `status` (枚举), `record_id`, `next_schedule_time` |
| `tool_get_upcoming_schedules` | 只读 | 查询未来若干天（默认 7 天）以及近期的面试/笔试日程与倒计时 | `days_ahead` (默认 7) |
| `tool_get_funnel_analytics` | 只读 | 获取当前求职转化漏斗全景统计（网申数、进面数、Offer数及比率） | 无需必填参数 |

### 4. 模拟面试状态机交互
| Tool 名称 | 注解 | 功能简介 | 关键入参 |
| :--- | :--- | :--- | :--- |
| `tool_interview_start` | 状态写入 | 初始化模拟面试会话，生成面试官第一句破冰词，返回 `session_id` | `target_company`, `target_role`, `interviewer_role` |
| `tool_interview_answer` | 状态写入 | 向正在进行的面试提交应答，驱动状态机推演并获得面试官追问/反馈 | `session_id`, `user_answer` (支持 'next'/'finish') |
| `tool_interview_finish` | 写入·完结 | 终结指定面试，调用大模型生成全维度复盘体检报告并持久化落盘 Markdown | `session_id` |

---

## 📦 暴露的 MCP 资源 (Resources)

| URI | 资源名称 | 描述 | MIME 类型 |
| :--- | :--- | :--- | :--- |
| `profile://summary` | `candidate_profile_summary` | 本地求职者脱敏个人画像（已移除手机号、邮箱等个人隐私数据） | `application/json` |

---

## 💻 外部宿主环境接入指南

> **提示**：为确保跨平台（尤其是 Windows）下 JSON-RPC 协议不被字符集干扰，启动参数均建议指定 `-X utf8`。

### 1. Codex 接入
通过 Codex CLI 添加 MCP 服务端：
```bash
codex mcp add jobhunt-copilot -- uv --directory <仓库绝对路径> run python -X utf8 -m adapters.mcp_server
```
或直接写入 `~/.codex/config.toml`：
```toml
[mcp_servers.jobhunt-copilot]
command = "uv"
args = ["--directory", "C:/Users/11482/Desktop/JobHunt-Copilot", "run", "python", "-X", "utf8", "-m", "adapters.mcp_server"]
tool_timeout_sec = 180  # 建议为长任务设置更宽松的超时时间
```

### 2. Claude Desktop 配置
在配置文件中添加（Windows: `%APPDATA%\Claude\claude_desktop_config.json`，macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`）：

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
        "-X",
        "utf8",
        "-m",
        "adapters.mcp_server"
      ]
    }
  }
}
```

### 3. Cursor IDE 配置
打开 Cursor **Settings** ➔ **Features** ➔ **MCP** ➔ 点击 **Add new MCP server**：
- **Name**: `jobhunt-copilot`
- **Type**: `command`
- **Command**: `uv --directory C:\Users\11482\Desktop\JobHunt-Copilot run python -X utf8 -m adapters.mcp_server`

---

## 🧪 自动化测试与验证

仓库内置了针对 MCP 协议与业务工具的自动化冒烟与端到端测试脚本：
```bash
# 验证 P0/P1 基础协议安全、枚举与日志重定向
uv run python -X utf8 tmp/verify_p0_p1.py

# 验证 P2/P3 13大工具、脱敏资源与模拟面试生命周期闭环
uv run python -X utf8 tmp/verify_p2_p3.py
```
