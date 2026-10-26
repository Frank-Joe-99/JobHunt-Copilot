# 业务模块

`skills/` 是 Python 业务实现；宿主调用说明位于 [.agents/skills](../.agents/skills/)，通过对应的 `$jobhunt-*` Skill 使用。

| 模块 | 用途 | 常用入口 |
| --- | --- | --- |
| [resume_generator](resume_generator/README.md) | 本地 PDF / Word 排版 | `generate_resume` |
| [resume_polisher](resume_polisher/README.md) | 定向改写建议与关键词诊断 | `polish_experiences`、`diagnose_ats` |
| [jd_matcher](jd_matcher/README.md) | 解析 JD、匹配和自荐信草稿 | `analyze_jd` |
| [project_recommender](project_recommender/README.md) | 有来源、预算和缓存的公开项目推荐 | `recommend_projects_report` |
| [job_radar](job_radar/README.md) | 本地 JD 批量排名与报告 | `run_radar_pipeline` |
| [mock_interviewer](mock_interviewer/README.md) | 固定 / 自适应面试与复盘 | 持久化入口使用 `core.interview_service` |
| [application_tracker](application_tracker/README.md) | 本地投递记录、日程与漏斗 | `add_application`、`update_status` |

## 开发约定

- `handler.py` 负责业务，`prompt.py` 保存所需任务契约；模板、存储和纯状态规则按需拆分。
- 业务模块之间不互相 import；跨模块编排放在 [core](../core/README.md)，流转对象定义在 `core/state.py`。
- 只使用已知事实；报告、参考答案和推荐模板不能当作已完成经历。
- 使用模型的功能会发送必要业务材料；测试注入合成配置、临时数据库和模拟服务。
- MCP 可达代码的日志写 stderr / logging，禁止写 stdout。

用户命令见[项目 README](../README.md)，升级范围见[完整目录](../future-upgrade/UPGRADE-INDEX.md)。
