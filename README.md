# 🎓 JobHunt-Copilot (应届生求职助手)

> **专为应届毕业生量身打造的全生命周期 AI 求职智能体系统**  
> 本地存储优先 · STAR 经历重塑 · 智能排版引擎 · 岗位雷达 · 开源实战补短板 · AI 模拟面试 · MCP 多端接入规划

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2.7%2B-e92063.svg)](https://docs.pydantic.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Protocol: MCP](https://img.shields.io/badge/Protocol-MCP-orange.svg)](https://modelcontextprotocol.io/)
[![Architecture: Decoupled](https://img.shields.io/badge/Architecture-Skills%20%26%20Tools-purple.svg)]()

---

## 📖 项目简介

应届毕业生在求职过程中常常面临多重困境：
- **经历苍白流水账**：参与过课程大作业或简单实习，但描述空泛，缺乏工业界认可的量化成果。
- **排版繁琐与隐私泄露**：在线简历制作网站收费高、模版僵硬，且容易造成手机号、身份证、住址等隐私泄露。
- **校招信息差**：难以全面掌握各大企业校招时间线与最新发布的匹配岗位。
- **缺少实战经验**：没有真正经历过技术追问或行为面试（BQ），面试现场容易紧张、答非所问。

**JobHunt-Copilot** 基于现代大语言模型（LLM）与智能体架构设计，从**“个人资产沉淀 ➡️ 机会雷达 ➡️ 简历定制 ➡️ 背景提升 ➡️ 模拟面试 ➡️ 投递管理”**构建起全流程求职闭环。个人核心档案默认存储在本地（Local-First）；启用云端 LLM、Claude Desktop 或 ChatGPT Work 集成后，提交给模型的内容及工具返回的数据会进入对应服务，接入设计需遵循最小必要数据原则。

---

## 🏛️ 系统架构与设计哲学

本项目遵循 **“低耦合、高内聚、数据与逻辑彻底解耦”** 的现代工程架构：

```
             ┌───────────────────────────────────────────────────┐
             │                Multiple Interfaces                │
             │       Terminal CLI / Streamlit WebUI              │
             │       Claude Desktop / ChatGPT Work Plugin        │
             └─────────────────────────┬─────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 Core Orchestration & Unified Contract Layer                 │
│         • state.py (Unified Pydantic Data Contracts & Schemas)              │
│         • workflow.py (State Machine & Pipeline Orchestration Engine)       │
├──────────────────────────────────────┬──────────────────────────────────────┤
│    Skills (Domain Expert Modules)    │   Tools (Infrastructure & Drivers)   │
│  • Mod 0: Resume Builder (Typst/HTML)│  • Unified LLM Client (llm_client.py)│
│  • Mod 1: STAR Resume Polisher       │  • PDF Engine/Parser (pdf_engine.py) │
│  • Mod 2: Campus Job Radar & Push    │  • GitHub Client (github_client.py)  │
│  • Mod 3: Target JD Deep Matcher     │  • Job Web Crawler (crawler.py)      │
│  • Mod 4: Project Portfolio Booster  │                                      │
│  • Mod 5: AI Scenario Interviewer    │                                      │
│  • Mod 6: Application Kanban Tracker │                                      │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

- **数据与逻辑彻底解耦**：用户只需在本地维护一份结构化档案（`profile.yaml`），即可跨平台生成简历、执行比对、驱动面试。
- **Schema 驱动规范**：使用 Pydantic 定义严格的数据对象，杜绝大模型随机输出造成的程序异常。
- **即插即用（Pluggable）**：新增一个技能（如：性格测评指导、Offer 排雷）无需改动核心代码。
- **Write Once, Run Everywhere（架构目标）**：复用同一套业务技能，通过 **MCP（Model Context Protocol）** 适配 Claude Desktop、Cursor/Zed 及 **ChatGPT Work 插件**，并保留独立终端与网页入口。各入口的实现状态见下文接入规划与路线图。

---

## 📂 目录结构总览

以下为目标目录结构，包含尚未实现的规划文件；当前可用基础包括配置契约、配置加载和双格式简历生成器。

```text
JobHunt-Copilot/
├── config/                      # 【用户档案与配置中心】个人资产沉淀，严禁上传公共代码库
│   ├── profile.example.yaml     # 个人主档案标准范例模板（涵盖本科/硕博学术科研、直博等）
│   ├── preferences.example.yaml # 求职意愿与岗位雷达抓取过滤范例模板
│   ├── settings.example.yaml    # 系统与大模型 API Key 运行参数范例模板
│   └── assets/                  # 个人静态资源目录（证件照、校徽矢量图等）
│
├── core/                        # 【核心控制与契约层】系统总线与数据标准
│   ├── config.py                # 统一配置加载器（加载并校验 profile/preferences/settings.yaml）
│   ├── state.py                 # 全局 Pydantic V2 强类型数据契约（UserProfile, JobPreferences, AppSettings）
│   └── workflow.py              # 业务工作流与状态机编排引擎
│
├── skills/                      # 【专家业务技能包】封装专业求职方法论与 Prompt
│   ├── resume_generator/        # 模块 0：本地排版引擎（支持 Word .docx 与 Typst .pdf 双版本镜像输出）
│   ├── resume_polisher/         # 模块 1：STAR 法则经历润色与 ATS 诊断评分
│   ├── job_radar/               # 模块 2：全网校招岗位雷达与定期语义推荐
│   ├── jd_matcher/              # 模块 3：目标岗位 JD 深度穿透与“一岗一策”定制建议
│   ├── project_recommender/     # 模块 4：技能缺口分析与 GitHub 优质开源实战推荐
│   ├── mock_interviewer/        # 模块 5：支持多轮追问的 AI 场景化模拟面试官
│   └── application_tracker/     # 模块 6：求职投递看板与时间线日程管理
│
├── tools/                       # 【底层基础设施驱动】纯技术能力，不含业务逻辑
│   ├── llm_client.py            # 统一大模型 API 调用封装（DeepSeek/OpenAI/Claude/Gemini）
│   ├── pdf_engine.py            # PDF 编译、渲染与解析工具
│   ├── github_client.py         # GitHub API 封装（仓库检索、Stars、难度过滤）
│   └── crawler.py               # 招聘网站公开接口与校招信息解析器
│
├── storage/                     # 【产物持久化仓库】自动生成物（已加入 .gitignore）
│   ├── resumes/                 # 编译生成的各版本高质量 PDF 简历
│   ├── radar_reports/           # 每日/每周推送的岗位推荐 Markdown 报告
│   ├── interview_logs/          # 模拟面试多轮对话记录与复盘诊断体检表
│   └── tracker.db               # 投递看板本地 SQLite 数据库
│
├── adapters/                    # 【外部生态协议适配层】
│   ├── mcp_server.py            # [规划] 共用 MCP 入口：stdio / Streamable HTTP
│   ├── tool_registry.py         # [规划] 共用工具注册、参数校验与结果转换
│   ├── artifact_service.py      # [规划] 简历产物标识、受控读取与远程交付
│   ├── chatgpt_work/            # [规划] ChatGPT Work 插件清单、连接映射与 SKILL.md
│   └── function_schemas.py      # [规划] OpenAI / DeepSeek API Function Calling 描述导出
│
├── pyproject.toml               # 现代化项目依赖与构建规范 (PEP 621)
├── uv.lock                      # 全局依赖版本与哈希确定性锁定文件
├── .gitignore                   # 隐私保护与工程忽略规则
├── LICENSE                      # 开源许可协议 (MIT)
└── README.md                    # 本说明文档
```

---

## 🧩 核心功能矩阵（全生命周期流）

### 阶段一：资产沉淀与背景提升
* **模块 0：本地双格式排版引擎 (Profile & Generator)**
  - 用户只需维护易读易改的 `config/profile.yaml`。
  - 一键同时生成 **Word (.docx)** 与 **PDF (.pdf)** 双版本：
    - **Word 版本**：基于 `python-docx` 渲染，方便针对不同企业岗位快速手工微调细节。
    - **PDF 版本**：基于现代排版新星 **Typst** 毫秒级编译，杜绝跨系统排版错位，符合工业级/学术级视觉规范。
  - 排版本身可本地离线运行；通过云端对话查看或下载简历时，按接入模式处理数据传输。
* **模块 4：技能缺口分析与 GitHub 开源实战推荐 (Portfolio Booster)**
  - 针对目标岗位计算技能差距（如：“高并发、Redis缓存、Docker容器化”）。
  - 调用 GitHub API 检索 star 数适中、文档完备、适合应届生练手的开源项目。
  - 提供如何将开源实践转化为简历 STAR 描述的参考模板。

### 阶段二：机会雷达与精准匹配
* **模块 1：简历诊断与 STAR 法则重塑 (Resume Polisher)**
  - 按照 **STAR 原则**（情境 Situation、任务 Task、行动 Action、结果 Result）重构语句。
  - 强化量化指标（百分比、吞吐量、优化耗时、用户量），剔除空泛无力的副词与中庸表达。
* **模块 2：全网校招岗位雷达 (Job Radar，暂时不开发)**
  - 接入合法公开招聘数据源，根据用户配置的意向行业与城市，自动计算 Embedding 语义相似度。
  - 周期性（每日/每周）输出匹配度前 10 的新岗位简报与网申链接。
* **模块 3：目标岗位 JD 深度穿透 (JD Matcher)**
  - 输入目标企业招聘 JD，输出技能树重合度雷达分析与缺失关键词提示。
  - 自动生成高度定制的求职自荐信与一岗一策修改版简历。

### 阶段三：应试备战与实战冲刺
* **模块 5：AI 真实场景模拟面试官 (Mock Interviewer)**
  - 支持多轮状态流转（破冰自我介绍 ➡️ 核心项目深度追问 ➡️ 计算机/专业八股 ➡️ 场景行为面 ➡️ 答疑反问）。
  - 面试结束后输出《复盘体检报告》，涵盖表达逻辑、技术深度、加分点与回答改进示例。
* *[规划中] 扩展：校招性格测评与笔试避坑指南 (Assessment Shield)*
  - 解读北森/SHL测评机制，提示一致性校验与极端选项陷阱。

### 阶段四：全程管理与终局决策
* **模块 6：求职投递看板 (Application Tracker)**
  - 本地 SQLite 轻量记录投递企业、岗位、投递日期、笔试时间与当前面试进展。
* *[规划中] 扩展：Offer 综合价值评估与三方协议排雷 (Offer Evaluator)*
  - 折算税后真实到手年包与时薪，排查劳动合同与三方协议违约风险。

---

## 🚀 快速上手 (Quick Start)

### 1. 环境准备与依赖安装
本项目使用现代 Python 包管理器 **[uv](https://github.com/astral-sh/uv)** 进行极速环境初始化与依赖锁定（秒级完成）：

```bash
# 1. 克隆本项目
git clone https://github.com/Frank-Joe-99/JobHunt-Copilot.git
cd JobHunt-Copilot

# 2. 一键创建虚拟环境并安装全部依赖 (基于 pyproject.toml 与 uv.lock)
uv sync
```

> 💡 *若本地尚未安装 uv，可通过 `pip install uv` 安装；亦可通过传统 `python -m venv .venv` 创建虚拟环境。*

---

### 2. 配置个人主档案与密钥
在 `config/` 目录下根据范例复制并创建您的主档案：
```bash
# Windows PowerShell 或 Linux/macOS
cp config/profile.example.yaml config/profile.yaml
cp config/preferences.example.yaml config/preferences.yaml
cp config/settings.example.yaml config/settings.yaml
```
- 编辑 `config/profile.yaml`：填入真实的教育背景、技能清单与经历信息（支持本科、硕博学术科研论文与直博经历）。
- 编辑 `config/preferences.yaml`：设定目标岗位、期望城市与薪资、岗位雷达扫描过滤条件。
- 编辑 `config/settings.yaml`：配置您的大模型 API 密钥（支持 DeepSeek、OpenAI、Claude、Gemini 等）。
- 放置照片资源至 `config/assets/`（如 `avatar.png`、`school_logo.png`）。

**配置一键自检**：在终端执行单行命令，验证配置文件是否符合 Pydantic 强类型契约：
```bash
uv run python -c "from core.state import UserProfile, JobPreferences, AppSettings; import yaml; UserProfile.model_validate(yaml.safe_load(open('config/profile.yaml', encoding='utf-8'))); print('✅ 配置文件校验通过！')"
```

### 3. 使用场景示例 (规划路线)

**场景 A：一键生成本地 Word + PDF 双格式简历**
```bash
uv run python -c "from skills.resume_generator.handler import generate_resume; res = generate_resume(); print('Word:', res['docx']); print('PDF:', res['pdf'])"
# 产物将保存至: storage/resumes/resume_default.docx 及 resume_default.pdf
```

**场景 B：诊断现有经历并按 STAR 法则重塑**
```bash
python main.py resume polish
```

**场景 C：输入目标岗位 JD 进行精准穿透与技能差距分析**
```bash
python main.py jd match --file ./target_jd.txt
```

**场景 D：开启多轮 AI 模拟面试**
```bash
python main.py interview start --role "后端开发工程师"
```

---

## 🔌 多端接入规划：Claude Desktop 与 ChatGPT Work

> **当前状态**：MCP 适配器和 ChatGPT Work 插件均待开发。目前 `adapters/` 只有说明文档与包初始化文件，下面的启动参数、工具接口和插件文件是后续开发约定，完成实现前不能直接运行。
>
> **资料核对日期：2026-09-15。** 本文的 ChatGPT Work 指 ChatGPT 的 Work 模式。官方支持通过插件组合技能与 MCP 工具；不同客户端、账号和工作区的可用入口可能不同，实施时需再次核对。[官方插件说明](https://learn.chatgpt.com/docs/plugins)

### 1. 接入方式与职责划分

| 使用入口 | 本项目的接入方式（规划） | 运行与数据位置 |
| :--- | :--- | :--- |
| Claude Desktop / 支持本地 MCP 的 IDE | 本地 MCP 子进程，使用 `stdio`（标准输入/输出）通信 | Python 服务读取本机配置并生成文件 |
| ChatGPT Work：个人开发与联调 | 注册 MCP 连接，再封装为插件；优先评估 Secure MCP Tunnel 连接本地服务 | 档案与排版可保留在本机，工具请求与结果经隧道传输 |
| ChatGPT Work：公开插件发布 | 稳定的 HTTPS MCP 服务，使用 Streamable HTTP | 服务读取其获授权的数据，生成可交付的产物 |
| 自建 OpenAI / DeepSeek API 应用 | `function_schemas.py` 导出工具描述，由自建程序执行工具调用 | 根据应用部署位置决定 |

ChatGPT 开发者模式可连接 HTTPS MCP 端点或 Secure MCP Tunnel；隧道可转发到本地 stdio/HTTP 服务，公开插件提交则需要稳定的公共 HTTPS 端点。[官方连接与测试流程](https://developers.openai.com/plugins/deploy/connect-chatgpt)

**本项目的开发决策**：采用“共用 MCP 服务 + ChatGPT Work 插件封装”。`skills/` 保持业务实现，`core/` 负责契约与编排，`adapters/` 负责协议和客户端交付。将 `llm.providers.openai` 配置为模型供应商只影响后端模型调用；让 Work 发现并调用本项目，还需要完成 MCP 连接和插件安装。

### 2. Claude Desktop 配置约定（待实现）

先实现下面约定的启动入口，并在项目目录执行 `uv sync`。随后在 `claude_desktop_config.json` 中加入配置，将示例路径替换为实际项目绝对路径：

```json
{
  "mcpServers": {
    "jobhunt-copilot": {
      "command": "uv",
      "args": [
        "--directory", "C:/path/to/JobHunt-Copilot",
        "run", "python", "-m", "adapters.mcp_server",
        "--transport", "stdio"
      ]
    }
  }
}
```

若桌面程序找不到 `uv`，将 `command` 换成 `uv` 可执行文件的绝对路径。`--directory` 用于固定项目环境，`--transport` 需由未来的 `mcp_server.py` 实现。stdio 模式下，日志必须写到 stderr；现有简历生成器的进度 `print()` 需要调整或重定向，避免污染 MCP 协议输出。

### 3. ChatGPT Work 接入与插件封装（待实现）

#### 3.1 先打通 MCP 连接

1. **准备服务**：先暴露 `generate_resume_tool`，通过 MCP Inspector 验证初始化、工具发现和调用；联调用 `profile.example.yaml` 构造测试档案。
2. **选择连接路径**：
   - **个人联调优先评估 Secure MCP Tunnel**：在 Platform 创建隧道，取得 `tunnel_id`，将隧道关联到目标 ChatGPT 工作区；本机运行 `tunnel-client`，转发到本项目的 stdio 或 HTTP 服务。需要隧道运行时 API Key，以及相应的 Tunnels Read / Manage / Use 权限。隧道使用外连 HTTPS，适合保留本地档案与排版环境；本机服务和隧道客户端需持续运行。
   - **公开发布采用 HTTPS**：部署 Streamable HTTP 服务，约定端点为 `https://<你的域名>/mcp`。远程服务访问的是部署环境的数据；需要另外实现档案导入、用户隔离和文件交付。
3. **注册连接**：在支持的账号中进入 ChatGPT `Settings → Security and login → Developer mode`，然后在 `Plugins` 中点加号创建连接，填写 HTTPS URL，或选择 `Tunnel` 并指定隧道；检查发现的工具列表。
4. **验证调用**：新建 Work 对话，选择该连接并测试“生成 modern 模板的 Word 和 PDF 简历”。修改工具描述或 Schema 后，重启服务、刷新连接元数据，再新建对话复测。

隧道权限与 Work 开发者模式权限分别管理；具体申请、工作区关联与客户端配置以 [Secure MCP Tunnel 官方文档](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) 为准。界面入口与刷新步骤参见 [官方连接与测试流程](https://developers.openai.com/plugins/deploy/connect-chatgpt)。

#### 3.2 再封装可安装的 Work 插件

首版建议使用官方 `@plugin-creator` 支持的兼容布局，将注册完成的 MCP 连接与求职工作流一起封装。以下文件均为规划：

```text
adapters/chatgpt_work/
├── .codex-plugin/
│   └── plugin.json             # 插件名称、版本、skills 路径及 apps: "./.app.json"
├── .app.json                   # 注册后的 MCP 连接映射，使用真实技术 ID
└── skills/
    └── jobhunt-assistant/
        └── SKILL.md            # 求职任务触发条件、工具调用步骤、结果呈现约定
```

实现要求：

- MCP 连接注册成功后取得 `plugin_asdk_app...` 技术 ID，再交给 `@plugin-creator` 生成映射和本地 marketplace 条目；该 ID 来自实际连接，不能用示例值代替。
- 检查清单中的 `apps` 指向 `./.app.json`，`skills` 指向 `./skills/`，并安装生成的插件，在新 Work 对话中完成端到端验证。[官方插件构建入门](https://learn.chatgpt.com/docs/build-plugins)
- 使用桌面端本地 marketplace 开发时，插件从安装缓存加载；修改源码后需更新安装副本并重新验证。后续若采用根目录 `plugin.json` / `mcp.json` 的可移植格式，按该格式的 Schema 整体迁移。[官方插件打包规范](https://developers.openai.com/plugins/build/plugins)
- 仓库根目录的 `skills/` 是 **Python 业务模块**；插件内的 `SKILL.md` 是 **给 Work 的工作流说明**。后者描述如何调用 MCP 工具，业务逻辑继续复用原模块。
- 首版以文字与结构化结果完成流程；简历预览卡片、匹配雷达图和投递看板 UI 可在工具调用稳定后扩展。

### 4. 共用工具接口与结果契约（开发约定）

先封装已有简历生成能力，再随业务模块完成情况增加工具。未实现的工具不应注册到客户端。

| 工具名称（拟定） | 主要输入 | 输出与副作用 | 优先级 |
| :--- | :--- | :--- | :--- |
| `generate_resume_tool` | `template_name="modern"`；个人版使用服务端配置的档案 | 返回 Word/PDF 产物描述，创建新文件 | P0：复用已有生成器 |
| `get_artifact_tool` | `artifact_id` | 返回授权范围内的产物信息与可用交付方式 | P0：补齐文件交付 |
| `polish_experience_tool` | `raw_text`、可选目标岗位 | 返回 STAR 草稿及待补充事实，不自动改写主档案 | P1：依赖润色模块 |
| `match_jd_tool` | `jd_text` | 返回匹配分数、依据和技能差距 | P1：依赖 JD 模块 |
| `recommend_projects_tool` | `skill_gaps` | 返回仓库链接与推荐依据，访问 GitHub | P2：依赖项目推荐模块 |

**适配约定**：

- 在 `core/state.py` 增加工具请求/响应模型，通过 Pydantic 生成 JSON Schema；共用工具名称、说明和校验逻辑，保持不同客户端行为一致。
- `generate_resume_tool` 将 `template_name` 映射到现有 `generate_resume(profile=..., output_name=..., template=...)`。首版模板使用已有的 `modern`；由服务端生成唯一 `output_name`，把返回的 `Path` 转成可序列化的产物描述，避免重复覆盖 `resume_default`。
- 每个工具声明输入 Schema、适当的输出 Schema 和准确的 `readOnlyHint`、`destructiveHint`、`openWorldHint`；生成文件属于写操作。结果同时提供简洁的 `content` 和供后续调用使用的 `structuredContent`。[官方 MCP 工具与返回规范](https://developers.openai.com/plugins/build/mcp-server)
- 业务失败返回 `isError: true` 及可处理的错误信息，例如档案缺失、模板不存在、编译失败；协议错误与业务错误分别处理，不把异常堆栈或密钥返回给对话。
- 润色与 JD 匹配需明确推理执行位置：首版先实现无需模型 API 的排版工具；后续若由服务端调用 `tools/llm_client.py`，使用服务端配置的供应商凭据，并在工具说明中写明数据流向。
- 岗位 JD、简历正文和外部网页均视为待分析数据；其中夹带的命令不能改变工具权限、输出路径或工作流授权。缺少量化成果时返回待补充项，不能编造经历。

生成成功的 `structuredContent` 示例（项目拟定格式，非已有实现）：

```json
{
  "status": "completed",
  "artifacts": [
    {
      "artifact_id": "resume_example_pdf",
      "filename": "resume_example.pdf",
      "mime_type": "application/pdf",
      "delivery": "local",
      "relative_path": "storage/resumes/resume_example.pdf"
    },
    {
      "artifact_id": "resume_example_docx",
      "filename": "resume_example.docx",
      "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "delivery": "local",
      "relative_path": "storage/resumes/resume_example.docx"
    }
  ]
}
```

### 5. 档案访问、文件交付与部署要求

以下为本项目接入设计要求：

- **本地路径与可下载文件分别处理**：上例的 `relative_path` 只用于定位本地产物。通过隧道调用成功不代表 Work 已获得文件，也不会自动使 `C:/...` 或 `file://...` 成为远程下载地址。个人版需明确提示“已在本机生成”；若要在对话中交付文件，应实现并验证目标客户端支持的文件传输方式，或由 `get_artifact_tool` 提供短期有效的受控下载地址。
- **产物生命周期**：`artifact_service.py` 维护 `artifact_id`、归属、文件类型和过期时间；远程交付响应使用 `delivery="download"`、`download_url`、`expires_at`。下载地址应有过期与撤销机制，下载处理器检查授权。stdio 与 MCP 隧道仅承担协议通信，远程下载端点需要单独设计。
- **私有档案访问**：个人联调限制在本人授权的连接与测试档案；面向多用户时，先从已验证的身份确定档案和产物归属，再执行业务逻辑。不能让所有远程用户共用默认 `config/profile.yaml`。
- **认证与授权**：远程私有数据接口按 MCP 授权规范接入 OAuth 2.1，验证 token 的签名、签发方、目标服务、有效期与权限范围；工具注解只协助客户端判断调用方式，权限校验仍由服务端实施。[官方认证规范](https://developers.openai.com/plugins/build/auth)
- **路径与写入边界**：模板使用白名单，文件写入限制在配置的产物目录；拒绝任意绝对路径、`../`、符号链接越界及任意文件读取。档案覆盖、投递状态修改等后续工具必须体现具体写入范围和授权，简历生成默认创建新版本。
- **数据与密钥**：分析任务仅传递所需经历、技能和 JD，默认去掉无关的联系方式；日志记录工具名、耗时和错误码，不记录完整档案、token 或简历正文。密钥、真实档案、照片与生成文件不得打包到插件或提交公共仓库。
- **运行环境**：保留 Python 3.12+ 与 `uv`；选择并锁定支持所需传输和结果结构的 MCP SDK 版本，更新 `pyproject.toml` 与 `uv.lock`。远程部署还要验证 Typst、中文字体、模板、可写存储、并发输出隔离和请求超时，业务配置随实现扩展 `AppSettings` 与示例配置。

### 6. 首版验收清单

- [ ] MCP Inspector 能完成初始化、列出工具、成功调用简历生成；非法参数、缺失档案及编译错误都有明确反馈。
- [ ] Claude Desktop 使用 stdio 生成 Word/PDF；进度日志不影响协议通信。
- [ ] 在实际目标账号的 ChatGPT Work 中完成 MCP 连接注册、插件安装及新对话调用，记录客户端版本、连接方式和权限前提。
- [ ] 两个客户端使用同一测试档案与 `modern` 模板，均得到能打开的 Word/PDF；重复或并发调用不覆盖其他任务的文件。
- [ ] 个人版明确返回本机保存位置；若宣称支持 Work 内下载，已在 Work 中打开并核对两个格式的文件，而非仅返回路径字符串。
- [ ] 开启远程私有数据访问时，未授权请求、跨用户产物读取及过期下载均被拒绝；路径越界请求不产生文件。
- [ ] 插件可被相关求职请求触发，无关请求不会误调用；工具和技能更新后，刷新连接/更新安装副本并通过复测。
- [ ] 补全实际安装说明、故障排查及脱敏配置示例，再将对应路线图项标为完成。

**后续完整场景示例（依赖 P1 技能实现）**：

> “使用 JobHunt-Copilot 分析这份后端开发 JD，说明我已有经历与岗位的差距。先给出修改建议，确认采用后生成一份新的 Word 和 PDF 简历。”

---

## 🗺️ 开发路线图 (Roadmap)

- [x] **Phase 1: 核心规范与本地排版引擎**
  - [x] 完成架构分层设计与标准化工程脚手架搭建
  - [x] 迁移至现代化 Python 包管理与依赖锁定（`pyproject.toml` + `uv.lock`）
  - [x] 制定 `config/` 详细字段规范与模板（覆盖本科、硕博科研论文、直博经历与雷达偏好）
  - [x] 完整实现 `core/state.py` Pydantic V2 全系统强类型数据契约（`UserProfile`, `JobPreferences`, `AppSettings`）
  - [x] 实现 `core/config.py` 自动化配置加载与强类型校验系统
  - [x] 实现 `skills/resume_generator` 模块（基于 python-docx 与 Typst 双轨一键输出 Word + PDF）
- [ ] **Phase 2: LLM 技能接入 (STAR 润色与 JD 匹配)**
  - [ ] 封装 `tools/llm_client.py` 多模型适配层
  - [ ] 编写 `skills/resume_polisher` 诊断评分与重写引擎
  - [ ] 实现 `skills/jd_matcher` 技能树穿透与差异对比
- [ ] **Phase 3: 机会雷达与开源项目赋能**
  - [ ] 封装 `tools/github_client.py` 实现 `skills/project_recommender`
  - [ ] 实现 `skills/job_radar` 公开岗位检索与定期推送
- [ ] **Phase 4: 模拟面试、看板与生态适配**
  - [ ] 基于状态机实现 `skills/mock_interviewer` 多轮追问系统
  - [ ] 实现 `adapters/mcp_server.py` 与共用工具注册，首先封装已有简历生成器并支持 stdio
  - [ ] 完成 Claude Desktop / Cursor 联调，验证模块启动方式、日志与结果序列化
  - [ ] 打造 Streamlit 可视化交互前端
- [ ] **Phase 5: ChatGPT Work 接入与插件交付**
  - [ ] **P0**：通过 Secure MCP Tunnel 或 HTTPS 注册开发者模式 MCP 连接，完成简历生成闭环
  - [ ] **P0**：建立 `adapters/chatgpt_work/` 插件清单、连接映射与工作流技能，完成本地 marketplace 安装
  - [ ] **P0**：实现产物标识与本地交付说明；需要 Work 内下载时，补齐受控文件交付并实际验收
  - [ ] **P1**：接入 STAR 润色与 JD 匹配，复用业务契约并明确后端模型调用边界
  - [ ] **P1**：需要多用户或公开发布时，实现 HTTPS、OAuth、用户数据隔离与产物生命周期
  - [ ] **P2**：按需求扩展项目推荐、面试与投递管理；评估可选 UI 和公开插件发布
  - [ ] 完成上文跨客户端验收清单，更新支持矩阵及实际配置文档

> Phase 5 的 P0 只依赖配置、简历生成器和基础 MCP 适配器，可先于模拟面试、机会雷达和 WebUI 开发。

---

## 🤝 贡献与反馈

欢迎提 Issue 或 Pull Request！我们期待与广大应届生和开发者共同完善这个开源求职助手。

## 📄 开源许可证

本项目采用 [MIT License](LICENSE) 开源许可。
