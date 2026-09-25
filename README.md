# 🎯 JobHunt-Copilot

> **面向技术开发者的工业级智能求职辅助外挂与定向交付引擎**。维护一份本地私密 YAML 个人档案，实现双格式高保真简历排版、STAR 经历重塑、岗位 JD 穿透比对、开源练手项目赋能、全真 AI 模拟面试、求职投递看板与 MCP 跨生态协议服务。

---

## 🌟 核心特色与架构能力

- 📄 **高保真双格式简历生成**：基于 Typst 与 python-docx，一键秒级排版编译 Word (.docx) 和 PDF (.pdf)，视觉考究紧凑，原生支持极具科技质感的现代风排版。
- 🎯 **一键岗位定向全套交付流**：输入目标企业 JD，端到端自动化完成“JD穿透比对 ➔ 开源练手补强 ➔ 经历定向 STAR 强化 ➔ 编译专属定制简历 ➔ 交付综合战报 ➔ 自动入库跟踪”（**严格遵循零污染原则，绝不篡改主档案**）。
- 🤖 **全真 AI 场景化模拟面试官**：内置三大真实面试官人设（严苛架构师/务实Lead/亲和HRBP），5 大递进面试阶段流转、穿透式追问与全景复盘体检报告（含五维雷达诊断与满分示范）。
- 📋 **本地私密求职投递看板**：基于原生 SQLite（WAL并发模式），离线跟踪网申、笔试、一面、二面、HR、Offer各阶段流转，提供未来 7 天面试日程提醒与全流程转化漏斗分析（进面率、Offer率）。
- 📡 **全网/批量机会雷达**：批量扫描岗位 JD，按人岗契合度智能降序排名、梯队分类（主投/冲刺/暂缓），自动统计跨岗位共性短板并导出战略决策简报。
- 🔌 **Model Context Protocol (MCP) 协议服务**：基于官方 MCP 协议标准搭建，7 大核心 Tools 即插即用，无缝连接 Claude Desktop、Cursor IDE、VS Code 等主流宿主。

> 🔒 **隐私至上原则**：除调用大模型 API 分析与 GitHub 检索外，所有数据（个人真实档案、简历文件、本地投递数据库 `storage/tracker.db`、面试记录）全部离线私密落盘，已通过 `.gitignore` 严格本地隔离，绝无云端泄露风险。

---

## ⚡ 快速开始

### 1. 环境准备

需要 Python 3.12+ 和 [uv](https://github.com/astral-sh/uv)。在项目根目录运行：

```bash
git clone https://github.com/Frank-Joe-99/JobHunt-Copilot.git
cd JobHunt-Copilot
uv sync
uv pip install -e .
```

### 2. 准备配置

首次使用时复制示例文件；已有配置时跳过对应文件：

```bash
cp config/profile.example.yaml config/profile.yaml
cp config/preferences.example.yaml config/preferences.yaml
cp config/settings.example.yaml config/settings.yaml
```

| 配置文件 | 用途说明 |
| --- | --- |
| `config/profile.yaml` | 教育背景、技能、实习、项目等个人核心经历（主档案） |
| `config/preferences.yaml` | 目标岗位、期望城市、薪资等求职偏好与雷达阈值配置 |
| `config/settings.yaml` | 大模型供应商（DeepSeek / OpenAI / 阿里百炼等）、API Key 与参数 |

*可选个人证件照和校徽可放置于 `config/assets/` 并在档案中指定路径。详见 [配置与字段文档](config/README.md)。*

### 3. 一键校验配置

```bash
uv run check_config.py
```
*验证三份 YAML 配置文件能否正确解析并通过 Pydantic 强类型校验（不产生模型 API 费用）。*

---

## 🚀 统一终端命令体验 (`jobhunt` / `uv run main.py`)

系统提供一站式命令行网关，无需记忆零碎脚本：

### ① 一键岗位定向全套交付 (`jobhunt tailor`)
针对特定企业岗位进行定向定制，生成专属双格式简历并自动建档：
```bash
# 指定本地真实 JD 文件或直接粘贴 JD 文本
uv run jobhunt tailor storage/raw_jds/01_bytedance_backend.txt

# 自定义输出文件名
uv run jobhunt tailor storage/raw_jds/01_bytedance_backend.txt -o resume_bytedance
```
*生成物料包括：专属定制版 PDF 简历、Word 简历、定向自荐信草稿、综合交付战报，并自动登记到求职看板。*

### ② 全真 AI 场景化模拟面试 (`jobhunt interview`)
沉浸式多轮技术演练，支持双回车换行长答案提交与打字机流式输出：
```bash
# 交互式菜单引导（自主选择考官人设与目标企业岗位）
uv run jobhunt interview

# 或直达严苛架构师人设
uv run jobhunt interview --role strict_architect --company 字节跳动 --target-role 分布式存储研发工程师
```
*交卷后自动在终端输出五维成绩单仪表盘，并导出全景体检 Markdown 报告至 `storage/interview_logs/`。*

### ③ 求职投递看板与日程管理 (`jobhunt tracker`)
离线私密管理求职全流程与面试日程：
```bash
# 查看求职全景转化漏斗、近期待办面试与投递跟踪清单
uv run jobhunt tracker

# 手动登记新的投递记录
uv run jobhunt tracker add --company "腾讯" --role "微信后台研发" --status applied --location "深圳" --note "官网校招投递"

# 推进阶段并预约面试日程
uv run jobhunt tracker update 1 --status interview_1 --schedule "2026-09-28 14:00" --notes "腾讯会议 123-456-789" --note "收到技术一面邀约"

# 查看未来 7 天内待办笔试/面试日程及倒计时
uv run jobhunt tracker schedules --days 7
```

### ④ 机会雷达批量扫描 (`jobhunt radar`)
批量评估某个目录下的所有岗位 JD，智能输出匹配度排行榜与战略报告：
```bash
uv run jobhunt radar --dir storage/raw_jds
```

### ⑤ 基础简历极速编译 (`jobhunt resume`)
基于主档案秒级编译最新的基础简历：
```bash
uv run jobhunt resume --template modern
```

### ⑥ 启动 MCP 协议服务端 (`jobhunt mcp`)
以标准 stdio 运行 Model Context Protocol 服务端，与外部 AI 助手无缝互联：
```bash
uv run jobhunt mcp
```

---

## 🔌 接入 Claude Desktop / Cursor (MCP 协议)

可在任何主流 AI 工具中以自然语言直接调度本系统的所有工具能力：

### 1. Claude Desktop 配置
在 `claude_desktop_config.json` 中配置：
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
在 Cursor **Settings ➔ Features ➔ MCP** 中点击 **Add new MCP server**：
- **Name**: `jobhunt-copilot`
- **Type**: `command`
- **Command**: `uv --directory C:\Users\11482\Desktop\JobHunt-Copilot run python -m adapters.mcp_server`

---

## 📂 模块文档索引

各模块的业务细节与技术实现详见对应文档：

- ⚙️ [配置与字段规范 (Config)](config/README.md)
- 🧠 [核心数据状态模型与业务流 (Core)](core/README.md)
- 🧰 [业务技能包总览 (Skills)](skills/README.md)
  - 📄 [简历排版编译引擎](skills/resume_generator/README.md)
  - 💎 [经历 STAR 润色与 ATS 诊断](skills/resume_polisher/README.md)
  - 🎯 [目标岗位 JD 穿透比对](skills/jd_matcher/README.md)
  - 🚀 [开源项目推荐与 STAR 转化](skills/project_recommender/README.md)
  - 📡 [岗位机会雷达与战略简报](skills/job_radar/README.md)
  - 🤖 [全真 AI 场景化模拟面试官](skills/mock_interviewer/README.md)
  - 📋 [求职投递看板与时间线日程](skills/application_tracker/README.md)
- 🔧 [底层驱动与工具层 (Tools)](tools/README.md)
- 💾 [产物存储与隐私隔离 (Storage)](storage/README.md)
- 🔌 [跨生态协议适配层 (Adapters)](adapters/README.md)

---

## 许可证

[MIT](LICENSE)
