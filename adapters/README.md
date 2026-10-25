# 🔌 adapters/ 目录：跨生态协议适配层

> 本模块为 JobHunt-Copilot 提供**外部协议标准化适配能力**。通过标准 Model Context Protocol (MCP) 与 stdio 传输通道，使外部智能体（Claude Desktop、Cursor IDE、VS Code、Codex）能够直接调用求职核心能力。

---

## 🌐 架构与设计原则

```text
┌─────────────────────────────────────────────────────────────┐
│          外部 AI 宿主客户端 (Host Environments)            │
│       (Claude Desktop, Cursor IDE, VS Code, Codex)          │
└──────────────────────────────┬──────────────────────────────┘
                               │ JSON-RPC 2.0 (stdio 通道)
                               ▼
             ┌────────────────────────────────────┐
             │       adapters/mcp_server.py       │
             │   (Anthropic MCP 2.x 标准服务端)    │
             └──────────────────┬─────────────────┘
                                │ 调度业务技能与资源
                                ▼
 ┌─────────────────────────────────────────────────────────────┐
 │                业务专家技能层 (Skills & Core)                │
 │ ├── skills/resume_generator     (简历排版编译)             │
 │ ├── skills/jd_matcher           (JD穿透比对与自荐信)       │
 │ ├── skills/project_recommender  (开源项目补短板)           │
 │ ├── skills/resume_polisher      (ATS诊断与STAR润色)        │
 │ ├── skills/job_radar            (岗位机会雷达扫描)         │
 │ ├── skills/mock_interviewer     (AI模拟面试状态机)         │
 │ ├── skills/application_tracker  (投递看板与日程管理)       │
 │ └── core/workflow               (一键全套定制交付长任务)   │
 └─────────────────────────────────────────────────────────────┘
```

### 核心设计规范
1. **stdio 协议防护**：禁止业务模块向 `stdout` 输出非 JSON-RPC 字符串。所有业务日志必须写入 `stderr`，并在工具执行层配备 `@_mcp_tool_safe` 强制重定向防护。
2. **长任务非阻塞**：耗时流水线（如 `tool_one_click_tailor`）采用异步线程池与进度回调（`ctx.report_progress`），避免挂起宿主通信事件循环。
3. **数据隐私隔离**：暴露的 `profile://summary` Resource 自动抹除手机号、邮箱与身份证号等个人敏感字段。

---

## 🛠️ MCP 工具清单 (Tools Reference)

服务端已注册 13 个强类型工具，支持 `readOnlyHint`、`openWorldHint`、`destructiveHint` 等标准协议注解：

### 1. 简历排版与岗位穿透
| 工具名称 | 注解属性 | 功能说明 | 关键输入参数 |
| :--- | :--- | :--- | :--- |
| `tool_generate_resume` | 本地写入 | 编译输出 Word (.docx) 与 PDF (.pdf) 双格式简历 | `template` ("modern"/"minimal"), `output_name` |
| `tool_analyze_jd` | 只读·外部API | 深度解析岗位 JD，计算技术契合度并生成求职自荐信 | `jd_text`, `provider` |
| `tool_recommend_projects` | 只读·外部API | 检索 GitHub 开源实战项目并生成简历 STAR 范文 | `skills` (列表), `language`, `provider` |
| `tool_one_click_tailor` | 写入·长任务 | 串联比对、开源补强、STAR优化与简历编译，提供 5 阶段进度 | `jd_text`, `auto_track` (默认 `False`), `enable_github` (默认 `True`) |

### 2. 简历诊断与重塑
| 工具名称 | 注解属性 | 功能说明 | 关键输入参数 |
| :--- | :--- | :--- | :--- |
| `tool_diagnose_ats` | 只读·外部API | 评估简历 ATS 关键词覆盖率、量化指标完整性并打分 | `target_jd_text` (可选), `provider` |
| `tool_polish_experiences` | 只读·外部API | 生成带快照定位与待核实标记的改写建议 | `provider`, `jd_text`（可选） |

### 3. 机会雷达与投递看板
| 工具名称 | 注解属性 | 功能说明 | 关键输入参数 |
| :--- | :--- | :--- | :--- |
| `tool_scan_jds` | 写入·外部API | 批量评估目录内岗位 JD，生成梯队榜单（含路径防穿越拦截） | `directory` (默认 "storage/raw_jds"), `provider` |
| `tool_track_application` | 本地写入 | 登记求职申请或推进状态阶段（严格枚举校验） | `company`, `role`, `status` (枚举), `record_id`, `next_schedule_time` |
| `tool_get_upcoming_schedules` | 只读 | 查询未来 7 天内以及近期待办笔试/面试日程 | `days_ahead` (默认 7) |
| `tool_get_funnel_analytics` | 只读 | 查询投递总览、进面率、Offer转化率及各阶段分布 | 无需输入参数 |

### 4. 场景化模拟面试
| 工具名称 | 注解属性 | 功能说明 | 关键输入参数 |
| :--- | :--- | :--- | :--- |
| `tool_interview_start` | 状态写入 | 创建面试会话并返回 `session_id`，支持可选 JD 和模拟/训练模式 | `target_company`, `target_role`, `interviewer_role`, `jd_text`（可选）, `mode`（默认 `simulation`） |
| `tool_interview_answer` | 状态写入 | 提交应答，驱动状态机推演并获取面试官追问（支持 `next`/`finish`） | `session_id`, `user_answer` |
| `tool_interview_finish` | 写入·完结 | 结束面试，生成六维能力复盘报告并持久化为 Markdown 文件 | `session_id` |

---

## 📦 MCP 资源清单 (Resources Reference)

| 资源 URI | 资源名称 | 描述 | MIME 类型 |
| :--- | :--- | :--- | :--- |
| `profile://summary` | `candidate_profile_summary` | 本地候选人脱敏个人档案（过滤手机号、邮箱等个人敏感隐私） | `application/json` |

`tool_one_click_tailor` 的原有参数保持可用，返回结果新增 `resume_diff_path`、`resume_snapshot_path`、`review_required` 和 `preparation_status`。`auto_track=true` 仅把物料准备登记为 `wishlist`，不代表已提交申请；默认仍为 `false`。原档案摘要资源保持现有行为，模型分析调用使用独立的业务字段白名单。

---

## ⚙️ 宿主客户端接入指南 (Host Setup Procedures)

### 1. 前置条件 (Prerequisites)
- 项目依赖已安装完整（`uv sync` 已成功执行）。
- 基础配置已准备就绪（`config/profile.yaml` 与 `config/settings.yaml` 已通过校验）。

---

### 2. Codex 客户端接入操作

#### 步骤 1：自动写入配置（推荐）
在终端中执行下列自动化命令：
```bash
uv run python -X utf8 adapters/generate_client_configs.py --install-codex
```
*预期结果*：终端输出 `[+] 成功将 jobhunt-copilot 写入 ~/.codex/config.toml！` 并自动生成备份。

#### 步骤 2：手动写入配置（备选）
若选择手动配置，向 `~/.codex/config.toml` 中追加下列内容：
```toml
[mcp_servers.jobhunt-copilot]
command = "uv"
args = [
    "--directory",
    "C:/Users/11482/Desktop/JobHunt-Copilot",
    "run",
    "python",
    "-X",
    "utf8",
    "-m",
    "adapters.mcp_server",
]
startup_timeout_sec = 60
tool_timeout_sec = 180
```

#### 步骤 3：验证连通状态
1. 重新启动 Codex 客户端或新起一个会话窗口。
2. 在输入框中执行 `/mcp` 命令。
3. 检查列表中 `jobhunt-copilot` 是否呈现绿色连接状态。

---

### 3. Claude Desktop 接入操作

#### 步骤 1：打开配置文件
打开对应系统的配置文件：
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

#### 步骤 2：添加服务定义
在 `mcpServers` 节点下添加 `jobhunt-copilot`：
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

#### 步骤 3：重启并验证
1. 完全退出并重新启动 Claude Desktop 应用程序。
2. 在对话界面右下角点击小锤子图标（Tools）。
3. 验证是否显示 `tool_generate_resume` 等 13 个可用工具。

---

### 4. Cursor IDE 接入操作

#### 步骤 1：打开 MCP 设置界面
1. 启动 Cursor IDE。
2. 打开 **Settings**（设置）➔ **Features** ➔ **MCP**。

#### 步骤 2：添加新服务
点击 **Add new MCP server** 按钮，填写下列信息：
- **Name**: `jobhunt-copilot`
- **Type**: `command`
- **Command**: `uv --directory "C:\Users\11482\Desktop\JobHunt-Copilot" run python -X utf8 -m adapters.mcp_server`

#### 步骤 3：刷新并验证
点击保存后，等待状态圆点变为绿色，确认服务连接正常。

---

## 🧪 自动化测试验证 (Verification)

在终端执行自动化测试套件验证服务连通性与安全性：
```bash
# 执行全量 MCP 协议与业务工具测试
uv run pytest tests/test_mcp_protocol.py tests/test_mcp_tools.py -v
```
*预期结果*：8 个测试项全部通过 (`8 passed`)，无超时或管道异常。
