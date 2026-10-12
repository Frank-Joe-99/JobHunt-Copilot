# 📡 skills/job_radar/：模块 2 岗位机会雷达与投递战略简报

> 本模块为 JobHunt-Copilot 的**批量岗位机会雷达与战略决策引擎**。支持对目录内的批量 JD 文本进行自动化语义穿透，按人岗契合度智能降序排列、划分机会梯队，并自动统计跨岗位共性短板，导出排版清晰的 Markdown 决策报告。

---

## 🎯 业务定位与评估梯队

解决候选人同时面对多家公司 3~10 个岗位时缺乏全局优先级判断、无法识别核心共性缺口的痛点。

### 机会分层标准：
| 梯队标识 | 匹配得分范围 | 核心投递策略 |
| :--- | :--- | :--- |
| **🟢 优先主投** | 80 ~ 100 分 | 核心技术与项目经历高度重合，建议优先重点投递 |
| **🟡 微调冲刺** | 65 ~ 79 分 | 具备良好基本盘，存在局部技能短板，建议针对性优化经历后投递 |
| **🔴 暂缓考虑** | 0 ~ 64 分 | 核心技术栈与业务场景差距较大，短期投递性价比低，建议暂缓 |

---

## 🏗️ 内部组件与核心 API

```text
skills/job_radar/
├── __init__.py            # 导出扫描与报告生成函数
├── handler.py             # 核心业务逻辑：批量扫描 -> 降序排名 -> 统计共性短板 -> 渲染 Markdown 简报
└── README.md              # 本说明文档
```

### 核心接口契约：
1. **`scan_opportunities(jd_texts: list[str], profile=None, provider=None) -> list[RankedOpportunity]`**  
   直接传入纯文本列表，执行打分并按匹配度降序排列。
2. **`scan_from_directory(dir_path="storage/raw_jds", profile=None, provider=None) -> list[RankedOpportunity]`**  
   扫描指定文件夹下的所有 `.txt` 岗位文件进行批量评估。
3. **`run_radar_pipeline(dir_path="storage/raw_jds", profile=None, provider=None) -> JobRadarReport`**  
   一键快捷门面：自动扫描文件夹 ➔ 批量比对 ➔ 自动在 `storage/radar_reports/` 落盘 Markdown 战略简报。

---

## 🛠️ 操作与扫描指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- 待评估的岗位 JD 文件以 `.txt` 格式存放于 `storage/raw_jds/`（或自定义指定目录）。
- 确认大模型 API 已在 `config/settings.yaml` 中配置。

---

### 2. 通过 CLI 命令行批量扫描

#### 步骤 1：执行雷达扫描命令
在终端运行 `jobhunt radar` 命令指定扫描目录：
```bash
uv run jobhunt radar --dir storage/raw_jds
```

#### 步骤 2：参数说明表
| 参数名 | 简写 | 必填 | 默认值 | 说明 |
| :--- | :--- | :---: | :--- | :--- |
| `--dir` | `-d` | 否 | `storage/raw_jds` | 存放待扫描 `.txt` 岗位文件的目录路径 |

#### 步骤 3：验证扫描结果
1. 终端打印梯队排名榜单与共性技术短板统计；
2. 检查生成的 Markdown 战略简报：`storage/radar_reports/radar_report_<timestamp>.md`。

---

### 3. 通过 Python API 调用扫描

#### 步骤 1：调用自动化流水线
```python
from skills.job_radar.handler import run_radar_pipeline

# 扫描并导出报告
report = run_radar_pipeline(dir_path="storage/raw_jds")
```

#### 步骤 2：读取分析指标
```python
print(f"总计评估岗位: {report.total_scanned} 个")
print(f"战略简报路径: {report.report_file_path}")

# 遍历高频共性技能短板
print("\n跨岗位共性攻坚短板:")
for gap in report.common_skill_gaps:
    print(f" - [{gap['importance']}] {gap['skill']} (关联 {gap['count']} 个岗位)")

# 遍历排名榜单
print("\n岗位契合度排行榜:")
for opp in report.opportunities:
    print(f" #{opp.rank} [{opp.score}分 · {opp.tier}] {opp.company} - {opp.role}")
```
*预期结果*：返回包含岗位排名、共性短板、战略建议与报告路径的 `JobRadarReport` 实体。
