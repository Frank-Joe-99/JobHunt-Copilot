# JobHunt-Copilot

面向应届生与开发者的求职辅助工具。维护一份 YAML 个人档案，用于排版生成双格式简历、STAR 法则重塑经历、深度分析岗位要求、推荐开源练手项目及批量评估求职机会。

## 当前功能

- **简历生成**：基于 Typst 与 python-docx 从个人档案一键生成 Word (.docx) 和 PDF (.pdf)，支持本地纯离线运行，排版严密紧凑。
- **经历润色**：严格遵循工业界 STAR 法则重构项目与实习经历，提取量化指标，并诊断简历技术关键词与 ATS 得分。
- **岗位分析**：深度解构目标岗位招聘描述（JD），穿透比对个人技能树与硬性要求，输出一岗一策修改建议与专属自荐信草稿。
- **项目推荐**：根据岗位分析诊断出的技能短板，自动从 GitHub 检索高星开源项目，提供精确到核心文件的极简速成路径与简历 STAR 范文。
- **机会雷达**：支持多岗位 JD 批量扫描（支持文本列表或本地文件夹），自动对标打分、梯队排序（主投/冲刺/暂缓），统计跨岗位高频共性短板，并导出 Markdown 战略简报。

> **隐私说明**：除本地简历生成外，经历润色、岗位分析、项目推荐与机会雷达调用大模型 API。个人真实档案、照片、真实岗位 JD 与导出报告已全部通过 `.gitignore` 严格本地隔离，绝不会意外提交至代码仓库。

## 快速开始

### 1. 环境准备

需要 Python 3.12+ 和 [uv](https://github.com/astral-sh/uv)。在项目根目录运行：

```bash
git clone https://github.com/Frank-Joe-99/JobHunt-Copilot.git
cd JobHunt-Copilot
uv sync
```

### 2. 准备配置

首次使用时复制示例文件；已有配置时跳过对应文件，避免覆盖：

```bash
cp config/profile.example.yaml config/profile.yaml
cp config/preferences.example.yaml config/preferences.yaml
cp config/settings.example.yaml config/settings.yaml
```

| 配置文件 | 用途说明 |
| --- | --- |
| `config/profile.yaml` | 教育背景、技能、实习、项目等个人经历；生成简历与对标分析必需 |
| `config/preferences.yaml` | 目标岗位、城市、薪资等求职偏好与雷达阈值配置 |
| `config/settings.yaml` | 模型供应商（DeepSeek / OpenAI 等）、API Key 与运行参数 |

可选个人照片和校徽可放置于 `config/assets/` 并在档案中指定路径。详见 [配置与字段文档](config/README.md)。

### 3. 一键检查配置

```bash
uv run check_config.py
```

验证三份 YAML 配置文件能否正确解析并通过 Pydantic 强类型校验（不产生模型 API 费用）。

## 常用功能使用

### ① 一键导出 Word + PDF 双格式简历

```bash
uv run generate_resume.py
```

产物将输出至：
- `storage/resumes/resume_default.docx`
- `storage/resumes/resume_default.pdf`

### ② 经历 STAR 润色与 ATS 诊断

```bash
# 经历 STAR 深度重塑
uv run python -c "from skills.resume_polisher.handler import polish_experiences; report = polish_experiences(); print(report.summary)"

# 简历 ATS 关键词与技术深度体检
uv run python -c "from skills.resume_polisher.handler import diagnose_ats; ats = diagnose_ats(); print(f'ATS 得分: {ats.score} 分 | 命中关键词: {len(ats.matched_keywords)} 个')"
```

### ③ 目标岗位 JD 穿透与定制分析

```bash
uv run python -c "from skills.jd_matcher.handler import analyze_jd; res = analyze_jd('公司：字节跳动\n职位：后端开发\n要求：熟悉 Python/Go，深入理解 Redis/MySQL 高并发'); print(f'契合度: {res.score} 分\n自荐信草稿:\n{res.cover_letter_draft}')"
```

### ④ 开源项目练手推荐（补齐短板）

```bash
uv run python -c "from core.state import SkillGap; from skills.project_recommender.handler import recommend_projects; recs = recommend_projects([SkillGap(skill='分布式缓存 Redis', status='missing', suggestion='了解多级缓存')]); [print(f'[{r.repo_name}] {r.stars}★: {r.why_recommended[:50]}...') for r in recs]"
```

### ⑤ 机会雷达批量扫描与战略简报

将意向岗位的 JD 文本以 `.txt` 格式放入 `storage/raw_jds/`，执行：

```bash
uv run python -c "from skills.job_radar.handler import run_radar_pipeline; report = run_radar_pipeline(); print(f'扫描完成，共评估 {report.total_scanned} 个岗位，战略报告已生成：{report.report_file_path}')"
```

报告将以排版精美的 Markdown 格式保存于 `storage/radar_reports/`，包含岗位综合排行榜、跨岗位共性缺口及逐岗微调指南。

## 后续计划

- **AI 模拟面试**：基于多轮追问交互状态机的模拟面试官与面试复盘体检报告 (`skills/mock_interviewer`)。
- **求职投递看板**：本地求职投递生命周期与备忘管理工具 (`skills/application_tracker`)。
- **MCP 协议服务**：本地 Model Context Protocol 服务实现，支持通过 stdio 对接 Claude Desktop 与 Cursor (`adapters/mcp_server.py`)。
- **ChatGPT Work 适配**：插件封装与文件交付闭环 (`adapters/chatgpt_work`)。

## 模块文档索引

各模块的业务细节与技术实现详见对应文档：

- [配置与字段规范](config/README.md)
- [核心数据模型与配置加载器](core/README.md)
- [业务技能包总览 (Skills)](skills/README.md)
  - [简历生成引擎](skills/resume_generator/README.md)
  - [经历润色与 ATS 诊断](skills/resume_polisher/README.md)
  - [目标岗位 JD 穿透比对](skills/jd_matcher/README.md)
  - [开源项目推荐与 STAR 转化](skills/project_recommender/README.md)
  - [岗位机会雷达与战略简报](skills/job_radar/README.md)
- [底层驱动与工具层 (Tools)](tools/README.md)
- [产物存储与隐私规则 (Storage)](storage/README.md)
- [外部协议接入规划 (Adapters)](adapters/README.md)

## 许可证

[MIT](LICENSE)
