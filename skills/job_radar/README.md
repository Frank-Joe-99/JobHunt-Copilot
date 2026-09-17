# 📡 skills/job_radar/：模块 2 目标岗位机会雷达与投递战略简报

## 🎯 业务定位与解决痛点
- **解决痛点**：
  - 应届生投递季同时看中多家大厂或团队的 3~10 个岗位 JD，不知道该优先投哪个、如何排兵布阵；
  - 缺乏全局视角，难以发现不同岗位之间的“共性高频技能缺口”；
  - 传统手动比对费时费力，缺乏清晰的量化评估与一岗一策分层指导。
- **本模块职责**：
  - 支持**批量输入 JD 纯文本**或**一键扫描本地 JD 文件夹**（如 `storage/raw_jds/*.txt`）；
  - 智能复用 `skills/jd_matcher` 进行像素级深度穿透打分；
  - 按契合度降序排列，自动划分梯队（【🟢 优先主投】/【🟡 微调冲刺】/【🔴 暂缓考虑】）；
  - 自动提炼跨岗位的共性高频技能短板，指出最值得突击的知识点；
  - 在 `storage/radar_reports/` 一键输出排版精美的 Markdown 机会雷达战略决策简报。

---

## 📂 模块结构与实现现状
```text
skills/job_radar/
├── __init__.py            # 包标记文件
├── handler.py             # 核心调度逻辑：批量比对 -> 降序排名 -> 共性短板分析 -> 导出 Markdown 简报
└── README.md
```

## 📥 输入与输出契约
1. **纯文本批量扫描 (`scan_opportunities`)**：
   - **输入**：`jd_texts: list[str]`（岗位纯文本列表）+ 可选 `UserProfile`。
   - **输出**：`list[RankedOpportunity]`（按得分降序排列的岗位排名列表）。
2. **文件夹一键扫描 (`scan_from_directory`)**：
   - **输入**：`dir_path: Path | str`（默认 `storage/raw_jds`）。
   - **输出**：`list[RankedOpportunity]`。
3. **全自动导出 Markdown 战略报告 (`run_radar_pipeline` / `export_radar_report`)**：
   - **输出**：`JobRadarReport` 对象，并在 `storage/radar_reports/` 生成 `radar_report_YYYYMMDD_HHMMSS.md`。

---

## 🚀 独立调用与验证命令

### 方式一：一键扫描 `storage/raw_jds` 目录并导出报告（推荐）
```powershell
uv run python -c "
from skills.job_radar.handler import run_radar_pipeline
report = run_radar_pipeline('storage/raw_jds')
print(f'已扫描 {report.total_scanned} 个岗位，生成报告：{report.report_file_path}')
for opp in report.opportunities:
    print(f'#{opp.rank} [{opp.score}分 - {opp.tier}] {opp.company} - {opp.role}')
"
```

### 方式二：直接传入 JD 纯文本列表进行即时评估
```powershell
uv run python -c "
from skills.job_radar.handler import scan_opportunities
jds = [
    '公司：字节跳动\n职位：后端开发\n要求：Python/Go，Redis/MySQL 高并发，分布式系统',
    '公司：腾讯\n职位：Web前端开发\n要求：Vue3/React，CSS3，Webpack/Vite，图形动效',
]
ranked = scan_opportunities(jds)
for r in ranked:
    print(f'#{r.rank} [{r.score}分 - {r.tier}] {r.company} - {r.role}')
"
```
