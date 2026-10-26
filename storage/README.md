# 本地存储

保存输入材料、缓存、数据库及生成物；此处是私有工作目录。

| 路径 | 内容 |
| --- | --- |
| `raw_jds/` | 待分析的本地 JD 文本 |
| `resumes/` | PDF / Word 简历 |
| `exports/` | 定制报告、修改对比与原始快照 |
| `radar_reports/` | 岗位排名和共性缺口报告 |
| `interview_logs/` | 面试复盘 Markdown |
| `tracker.db` | 投递看板与日程 |
| `interviews.db` | 事实快照、问答、请求状态与指标 |
| `interviews.db.locks/` | 跨进程会话锁文件 |
| `github_cache.db` | 带日期的公开仓库资料与冷却状态 |
| `llm_capabilities.db` | 输出格式能力摘要与时间，不含正文或密钥 |

## 管理规则

- 数据库及其 WAL / 日志、生成物由 .gitignore 排除。README、占位文件和公开样例是例外；个人内容不要写入这些例外文件。
- `raw_jds/` 存在公开样例命名例外，保存私人 JD 后核对 Git 状态，不强制暂存私有文件。
- 会话库 v2 可从已校验的 v1 结构原子增加指标列，不重写原事实与问答。
- `uv run jobhunt interview-sessions delete <session_id>` 删除会话及关联请求；独立导出的 Markdown 报告仍保留。
- 备份或分享前区分个人材料与公开缓存；本地文件不是匿名数据。

恢复、查看和比较见[面试说明](../skills/mock_interviewer/README.md)，准备与已投递的区别见[看板说明](../skills/application_tracker/README.md)。
