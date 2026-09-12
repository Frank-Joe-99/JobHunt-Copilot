# 🎓 JobHunt-Copilot (应届生求职助手)

> **专为应届毕业生量身打造的全生命周期 AI 求职智能体系统**  
> 本地隐私优先 · STAR 经历重塑 · 智能排版引擎 · 岗位雷达 · 开源实战补短板 · AI 模拟面试 · 原生支持 MCP 协议

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
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

**JobHunt-Copilot** 基于现代大语言模型（LLM）与智能体架构设计，从**“个人资产沉淀 ➡️ 机会雷达 ➡️ 简历定制 ➡️ 背景提升 ➡️ 模拟面试 ➡️ 投递管理”**构建起全流程求职闭环。所有个人核心档案均存储在本地（Local-First），确保个人隐私绝对安全。

---

## 🏛️ 系统架构与设计哲学

本项目遵循 **“低耦合、高内聚、数据与逻辑彻底解耦”** 的现代工程架构：

```
             ┌───────────────────────────────────────────────────┐
             │                Multiple Interfaces                │
             │   (Terminal CLI / Streamlit WebUI / Claude MCP)   │
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
- **Write Once, Run Everywhere**：既支持独立终端与网页运行，也支持通过 **MCP（Model Context Protocol）** 协议作为 Claude Desktop 或 Cursor/Zed 等编辑器的外挂求职工具。

---

## 📂 目录结构总览

```text
JobHunt-Copilot/
├── config/                      # 【用户档案与配置中心】个人资产沉淀，严禁上传公共代码库
│   ├── profile.example.yaml     # 个人主档案标准范例模板
│   ├── preferences.example.yaml # 求职意愿与偏好范例模板
│   ├── settings.example.yaml    # 系统与模型 API 配置范例模板
│   └── assets/                  # 个人静态资源目录（证件照、校徽矢量图等）
│
├── core/                        # 【核心控制与契约层】系统总线与数据标准
│   ├── state.py                 # 全局数据模型定义（Resume, JobDescription, SkillGap等）
│   └── workflow.py              # 业务工作流与状态机编排引擎
│
├── skills/                      # 【专家业务技能包】封装专业求职方法论与 Prompt
│   ├── resume_generator/        # 模块 0：本地排版引擎（支持 Typst / 现代化 HTML 转 PDF）
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
│   ├── mcp_server.py            # Model Context Protocol 服务实现（供 Claude/IDE 调用）
│   └── function_schemas.py      # OpenAI / DeepSeek Function Calling 描述导出
│
├── .gitignore                   # 隐私保护与工程忽略规则
├── LICENSE                      # 开源许可协议 (MIT)
└── README.md                    # 本说明文档
```

---

## 🧩 核心功能矩阵（全生命周期流）

### 阶段一：资产沉淀与背景提升
* **模块 0：本地排版引擎 (Profile & Generator)**
  - 用户只需维护易读易改的 `config/profile.yaml` 或 Markdown。
  - 基于现代排版新星 **Typst** 或 HTML+CSS 模板，一键渲染出对齐严谨、字体优美、控制在 A4 一页纸内的工业级 PDF 简历。
  - 本地离线运行，零云端隐私泄露风险。
* **模块 4：技能缺口分析与 GitHub 开源实战推荐 (Portfolio Booster)**
  - 针对目标岗位计算技能差距（如：“高并发、Redis缓存、Docker容器化”）。
  - 调用 GitHub API 检索 star 数适中、文档完备、适合应届生练手的开源项目。
  - 提供如何将开源实践转化为简历 STAR 描述的参考模板。

### 阶段二：机会雷达与精准匹配
* **模块 1：简历诊断与 STAR 法则重塑 (Resume Polisher)**
  - 按照 **STAR 原则**（情境 Situation、任务 Task、行动 Action、结果 Result）重构语句。
  - 强化量化指标（百分比、吞吐量、优化耗时、用户量），剔除空泛无力的副词与中庸表达。
* **模块 2：全网校招岗位雷达 (Job Radar)**
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

### 1. 环境准备
确保已安装 Python 3.10 以上版本，并克隆本项目：
```bash
git clone https://github.com/Frank-Joe-99/JobHunt-Copilot.git
cd JobHunt-Copilot

# 创建并激活虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置个人主档案
在 `config/` 目录下根据范例复制并创建您的主档案：
```bash
cp config/profile.example.yaml config/profile.yaml
cp config/preferences.example.yaml config/preferences.yaml
cp config/settings.example.yaml config/settings.yaml
```
- 编辑 `config/profile.yaml`：填入真实的教育背景、技能清单与经历信息。
- 编辑 `config/settings.yaml`：配置您的大模型 API 密钥（如 DeepSeek、OpenAI、Gemini 等）。
- 放置照片资源至 `config/assets/`（如 `avatar.png`、`school_logo.png`）。

### 3. 使用场景示例 (规划路线)

**场景 A：一键生成本地 PDF 简历**
```bash
python main.py resume generate --template modern
# 产物将保存至: storage/resumes/resume_default.pdf
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

## 🔌 接入 Claude Desktop (MCP 协议支持)

本项目提供了原生的 **Model Context Protocol (MCP)** 适配器。你可以将其接入 Claude Desktop，在与 Claude 对话时直接调用本地的求职能力。

在 Claude Desktop 配置文件 `claude_desktop_config.json` 中增加：
```json
{
  "mcpServers": {
    "jobhunt-copilot": {
      "command": "python",
      "args": [
        "C:/path/to/JobHunt-Copilot/adapters/mcp_server.py"
      ]
    }
  }
}
```
配置完成后，在 Claude 中即可直接输入：
> *“帮我分析这个字节跳动后端的招聘 JD，调用我的 JobHunt-Copilot 算出技能差距，并针对性生成一份优化简历。”*

---

## 🗺️ 开发路线图 (Roadmap)

- [ ] **Phase 1: 核心规范与本地排版引擎**
  - [x] 完成架构分层设计与标准化工程脚手架搭建
  - [ ] 制定 `config/profile.yaml` 详细字段规范与示例
  - [ ] 实现 `core/state.py` Pydantic 数据契约
  - [ ] 实现 `skills/resume_generator` 模块（集成 Typst/HTML 模板渲染）
- [ ] **Phase 2: LLM 技能接入 (STAR 润色与 JD 匹配)**
  - [ ] 封装 `tools/llm_client.py` 多模型适配层
  - [ ] 编写 `skills/resume_polisher` 诊断评分与重写引擎
  - [ ] 实现 `skills/jd_matcher` 技能树穿透与差异对比
- [ ] **Phase 3: 机会雷达与开源项目赋能**
  - [ ] 封装 `tools/github_client.py` 实现 `skills/project_recommender`
  - [ ] 实现 `skills/job_radar` 公开岗位检索与定期推送
- [ ] **Phase 4: 模拟面试、看板与生态适配**
  - [ ] 基于状态机实现 `skills/mock_interviewer` 多轮追问系统
  - [ ] 完善 `adapters/mcp_server.py`，支持 Claude Desktop / Cursor 联动
  - [ ] 打造 Streamlit 可视化交互前端

---

## 🤝 贡献与反馈

欢迎提 Issue 或 Pull Request！我们期待与广大应届生和开发者共同完善这个开源求职助手。

## 📄 开源许可证

本项目采用 [MIT License](LICENSE) 开源许可。
