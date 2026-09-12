# 📡 skills/job_radar/：模块 1.5 全网校招岗位雷达与定期推荐

## 🎯 业务定位与解决痛点
- **解决痛点**：
  - 应届生面临巨大的“校招信息差”：各家大厂提前批、秋招、春招开启与截止时间零碎分散；
  - 缺乏精力每天去几十个招聘官网、论坛搜寻，容易错过心仪岗位的最佳网申窗口期。
- **本模块职责**：
  - 读取 `config/preferences.yaml` 中配置的求职意向（目标方向、城市、薪资期待、行业）；
  - 定时调度数据抓取器或聚合公开 RSS/API 源；
  - 基于 Embedding 语义相似度或关键词矩阵对新岗位进行过滤打分；
  - 周期性（如每天早晨 9:00 或每周一）在 `storage/radar_reports/` 输出高匹配度岗位精选推荐简报。

---

## 🔄 数据流转架构
```text
[公开校招/招聘数据源] ──(tools/crawler.py)──> 原始岗位列表
                                                    │
                                                    ▼
[用户偏好 (preferences.yaml)] ──> 语义相关性比对 & 过滤打分
                                                    │
                                                    ▼
                                    Top-N 高契合度校招新发岗位
                                                    │
                                                    ▼
                             生成 storage/radar_reports/日报/周报 (Markdown)
```

---

## 📂 预期内部结构
```text
skills/job_radar/
├── __init__.py
├── prompt.py              # 岗位需求结构化提取 Prompt、匹配度打分 Prompt
├── handler.py             # 核心逻辑：触发爬取、执行匹配打分、输出推荐列表
├── reporter.py            # 格式化生成漂亮的 Markdown 岗位日报
└── README.md
```

## 📥 输入与输出契约
- **输入**：`JobPreferences`（来自 `core.state`） + 抓取配置。
- **输出**：`List[RecommendedJob]`（包含：公司名、岗位名、地点、薪资范围、网申链接、核心要求、与用户的匹配度得分及推荐理由）。
