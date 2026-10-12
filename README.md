# 🎯 JobHunt-Copilot

> 本地优先的开发者智能求职辅助工具与定向交付引擎。通过本地私密 YAML 档案，提供简历双格式排版、STAR 经历提炼、岗位契合度分析、开源练手项目推荐、模拟面试、投递看板与 MCP 跨生态协议服务。

---

## 📖 核心特性与架构定位

JobHunt-Copilot 面向应届生与技术开发者，解决简历缺乏重点、对岗位要求理解不透、面试缺乏实战演练等求职痛点。所有操作遵循**本地优先**与**数据零污染**原则：

| 模块名称 | 核心能力 | 输入与产物 |
| :--- | :--- | :--- |
| **简历排版引擎** | 基于 Typst 与 python-docx，秒级编译双格式简历 | 输入 Profile ➔ 输出 PDF 与 Word (.docx) |
| **一键定向交付流** | 串联 JD 解析、开源赋能、经历 STAR 强化与简历生成 | 输入目标 JD ➔ 输出专属简历与综合战报（内存深拷贝，不污染主档案） |
| **模拟面试状态机** | 三类面试官风格（硬核架构师/务实Leader/HRBP），多阶段追问 | 交互式终端对练 ➔ 输出六维评估报告与 Markdown 复盘日志 |
| **投递看板与日程** | 基于本地 SQLite WAL 模式，管理投递进度与面试日程 | 记录网申/一面/二面/HR面/Offer ➔ 输出转化漏斗与到期提醒 |
| **批量机会雷达** | 批量扫描文件夹内 JD，按契合度排序并识别共性短板 | 输入多份 JD 文本 ➔ 输出机会梯队榜单与攻坚策略 |
| **MCP 跨生态服务** | 遵循标准 Model Context Protocol 规范，暴露 13 个类型化工具与 1 项脱敏资源 | 连接 Claude Desktop / Cursor / VS Code / Codex |

> [!IMPORTANT]
> **隐私至上原则**：除调用配置的大模型 API 与 GitHub 公共接口外，个人主档案、简历文件、本地数据库（`storage/tracker.db`）与面试日志均保存在本地，通过 `.gitignore` 隔离，严禁向外部同步。

---

## ⚡ 快速开始 (Getting Started)

### 1. 前置条件 (Prerequisites)
- 安装 Python 3.12 或更高版本。
- 安装包管理工具 [uv](https://github.com/astral-sh/uv)。

### 2. 操作步骤 (Step-by-Step Procedure)

#### 步骤 1：克隆项目并安装依赖
在终端中执行下列命令克隆代码库并完成虚拟环境同步：
```bash
git clone https://github.com/Frank-Joe-99/JobHunt-Copilot.git
cd JobHunt-Copilot
uv sync
```
*预期结果*：终端输出 `Resolved ... packages` 并成功生成 `.venv` 虚拟环境。

#### 步骤 2：创建本地配置文件
复制模板文件生成工作配置文件（模板位于 `config/*.example.yaml`）：
```bash
cp config/profile.example.yaml config/profile.yaml
cp config/preferences.example.yaml config/preferences.yaml
cp config/settings.example.yaml config/settings.yaml
```
根据个人实际情况编辑上述文件：
- `config/profile.yaml`：填写真实教育背景、技能清单、实习经历与项目经历。
- `config/preferences.yaml`：设定求职意向岗位、城市与期望薪资。
- `config/settings.yaml`：配置大模型提供商（DeepSeek、OpenAI、阿里百炼等）与 API Key。

#### 步骤 3：校验配置完整性
运行配置校验脚本，确保 YAML 语法与数据类型符合系统契约：
```bash
uv run python -X utf8 check_config.py
```
*预期结果*：终端打印 `[✓] All configurations validated successfully!`，不产生任何外部大模型请求费用。

---

## 🚀 终端命令操作指南 (CLI Guide)

系统通过统一入口 `jobhunt`（或 `uv run main.py`）提供全套命令行功能。

### 1. 一键岗位定向全套交付 (`jobhunt tailor`)
根据目标岗位的招聘需求，自动化生成专属简历并完成投递归档。

- **执行命令**：
  ```bash
  # 语法：uv run jobhunt tailor <JD文本路径或文本内容> [选项]
  uv run jobhunt tailor storage/raw_jds/01_bytedance_backend.txt -o resume_bytedance
  ```
- **参数说明**：
  | 参数名 | 简写 | 必填 | 默认值 | 说明 |
  | :--- | :--- | :---: | :--- | :--- |
  | `jd_input` | 无 | 是 | - | 目标岗位 JD 文本文件路径，或直接传入 JD 纯文本 |
  | `--output-name` | `-o` | 否 | 自动根据企业和岗位生成 | 导出简历文件的基本名称（不含扩展名） |
  | `--template` | `-t` | 否 | `modern` | 简历排版模板，可选 `modern`（现代专业）或 `minimal`（极简学术） |
  | `--no-github` | 无 | 否 | `False` | 禁用 GitHub 开源练手项目检索 |
  | `--no-track` | 无 | 否 | `False` | 禁止自动将本次交付登记到求职看板 |
- **预期产物**：
  - 定制简历：`storage/resumes/<output_name>.pdf` 与 `.docx`
  - 交付战报：`storage/exports/package_<company>_<role>_<timestamp>.md`

---

### 2. 全真 AI 场景化模拟面试 (`jobhunt interview`)
进入交互式终端模拟面试，支持长文本作答与实时复盘评估。

- **执行命令**：
  ```bash
  # 方式 A：启动交互式向导选择岗位与面试官人设
  uv run jobhunt interview

  # 方式 B：直接指定参数启动
  uv run jobhunt interview --role strict_architect --company 字节跳动 --target-role 后端开发工程师
  ```
- **参数说明**：
  | 参数名 | 必填 | 默认值 | 说明 |
  | :--- | :---: | :--- | :--- |
  | `--role` | 否 | 交互选择 | 面试官风格：`strict_architect`（严苛架构师）、`practical_lead`（务实组长）、`hrbp`（HR） |
  | `--company` | 否 | "目标大厂" | 目标企业名称 |
  | `--target-role` | 否 | 档案设定值 | 目标求职岗位 |
- **交互指令**：
  - 输入作答内容后按两次回车提交。
  - 输入 `next`：跳过当前面试环节。
  - 输入 `finish`：提前结束面试并生成复盘报告。
- **预期产物**：终端打印五维能力雷达评分，并在 `storage/interview_logs/` 下生成完整复盘 Markdown 报告。

---

### 3. 求职投递看板与日程管理 (`jobhunt tracker`)
本地管理求职生命周期，统计漏斗转化率与面试待办日程。

- **执行步骤与命令**：
  1. 查看投递总览与当前漏斗：
     ```bash
     uv run jobhunt tracker
     ```
  2. 登记新投递记录：
     ```bash
     uv run jobhunt tracker add --company "腾讯" --role "后台开发" --status applied --location "深圳" --note "官网投递"
     ```
  3. 推进流程状态并设置面试提醒：
     ```bash
     uv run jobhunt tracker update 1 --status interview_1 --schedule "2026-10-25 14:00" --notes "腾讯会议 123-456-789"
     ```
  4. 查询未来待办日程：
     ```bash
     uv run jobhunt tracker schedules --days 7
     ```
- **状态枚举（`status`）**：
  `wishlist`（心愿单）➔ `applied`（已投递）➔ `assessment`（笔试/测评）➔ `interview_1`（一面）➔ `interview_2`（二面）➔ `hr_stage`（HR面）➔ `offer`（录用）➔ `rejected`（未通过）➔ `closed`（流程关闭）。

---

### 4. 批量岗位雷达扫描 (`jobhunt radar`)
批量评估指定目录内的所有 `.txt` 岗位文件，输出契合度榜单与攻坚策略。

- **执行命令**：
  ```bash
  uv run jobhunt radar --dir storage/raw_jds
  ```
- **预期产物**：在终端输出排序榜单，并在 `storage/radar_reports/` 生成详细战略评估简报。

---

### 5. 编译基础本地简历 (`jobhunt resume`)
基于主档案直接生成双格式简历，不进行特定岗位定制。

- **执行命令**：
  ```bash
  uv run jobhunt resume --template modern -o my_resume
  ```
- **预期产物**：生成 `storage/resumes/my_resume.pdf` 与 `storage/resumes/my_resume.docx`。

---

### 6. 运行 MCP 协议服务 (`jobhunt mcp`)
启动 Model Context Protocol 服务端，支持外部 AI 宿主通过标准 stdio 调度求职工具。

- **执行命令**：
  ```bash
  uv run jobhunt mcp
  ```
- **验证方法**：服务正常启动后等待 stdio JSON-RPC 消息输入。详细集成配置见 [MCP 适配层文档](adapters/README.md)。

---

## 🔌 外部 AI 宿主接入 (MCP Integration)

### 1. Codex 接入
向 `~/.codex/config.toml` 追加配置（或运行 `uv run python adapters/generate_client_configs.py --install-codex` 自动写入）：
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

### 2. Claude Desktop 接入
打开 `%APPDATA%\Claude\claude_desktop_config.json` 并添加：
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

### 3. Cursor 接入
进入 **Settings ➔ Features ➔ MCP ➔ Add new MCP server**：
- **Name**: `jobhunt-copilot`
- **Type**: `command`
- **Command**: `uv --directory "C:\Users\11482\Desktop\JobHunt-Copilot" run python -X utf8 -m adapters.mcp_server`

---

## 🧩 Codex Skills 调用说明

仓库级 Skill 定义位于 [`.agents/skills/`](.agents/skills/)。以本仓库作为工作目录打开 Codex 时即可生效：

- **调用语法**：在对话框键入 `$` 并选择对应技能，例如：
  ```text
  $jobhunt-jd-analysis 帮我分析以下 JD 与我的背景匹配度：...
  ```
- **内置 8 大技能列表**：
  1. `$jobhunt-jd-analysis`：岗位契合度深度拆解
  2. `$jobhunt-resume-review`：经历 STAR 重构与 ATS 体检
  3. `$jobhunt-resume-build`：本地简历排版导出
  4. `$jobhunt-project-recommendation`：开源项目攻坚推荐
  5. `$jobhunt-job-radar`：多岗位机会雷达扫描
  6. `$jobhunt-mock-interview`：全真模拟面试演练
  7. `$jobhunt-application-tracker`：求职流程与日程跟踪
  8. `$jobhunt-application-package`：一键全套定制求职物料

---

## 📂 模块文档导航

各子模块的详细设计与业务规范见对应文档：

- ⚙️ [配置与字段规范 (config/)](config/README.md)
- 🧠 [中枢状态机与数据契约 (core/)](core/README.md)
- 🧰 [业务专家技能总览 (skills/)](skills/README.md)
  - 📄 [简历排版编译引擎 (resume_generator)](skills/resume_generator/README.md)
  - 💎 [STAR 经历润色与 ATS 体检 (resume_polisher)](skills/resume_polisher/README.md)
  - 🎯 [岗位 JD 穿透比对 (jd_matcher)](skills/jd_matcher/README.md)
  - 🚀 [开源项目推荐补短板 (project_recommender)](skills/project_recommender/README.md)
  - 📡 [批量机会雷达与简报 (job_radar)](skills/job_radar/README.md)
  - 🤖 [场景化模拟面试官 (mock_interviewer)](skills/mock_interviewer/README.md)
  - 📋 [投递看板与日程管理 (application_tracker)](skills/application_tracker/README.md)
- 🔧 [底层网络与 LLM 驱动 (tools/)](tools/README.md)
- 🔌 [跨生态 MCP 服务端 (adapters/)](adapters/README.md)

---

## 📄 许可证

本项目基于 [MIT 许可证](LICENSE) 开源。
