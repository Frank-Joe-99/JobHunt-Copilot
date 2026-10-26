# 数据契约与编排

集中维护跨业务数据和工作流，协调 CLI / MCP 共用能力。

| 文件 | 职责 |
| --- | --- |
| [state.py](state.py) | 档案、配置、JD、改写、会话、策略及结果契约 |
| [config.py](config.py) | YAML 加载、环境变量展开、缓存与脱敏校验错误 |
| [context.py](context.py) | 保留完整业务经历，排除姓名、联系方式等无关字段 |
| [resume_edits.py](resume_edits.py) | 冻结快照、目标 ID / 摘要校验、保守审查和差异 |
| [workflow.py](workflow.py) | 定向物料编排，输出草稿、对比和原始快照 |
| [radar_workflow.py](radar_workflow.py) | JD 解析 / 匹配的跨模块协调 |
| [interview_service.py](interview_service.py) | 持久会话、幂等、预算与离线比较 |

## 常用入口

| 入口 | 返回 |
| --- | --- |
| `load_user_profile()` / `load_job_preference()` / `load_app_settings()` | 经校验的数据对象，位于 config.py |
| `tailor_application_flow(jd_input, ...)` | `TailoredApplicationPackage` |
| `run_radar_pipeline(dir_path, ...)` | `JobRadarReport` |
| `start_interview(...)` | 会话和文本生成器，位于 interview_service.py |
| `resume_interview(session_id)` | 原事实快照对应的会话 |
| `compare_interviews(first_id, second_id)` | 输入条件与指标对比，不自动评质量 |

定制只修改草稿，不写回主档案；定位 ID 仅在对应冻结快照内有效。物料准备登记为 wishlist，不自动标为已投递。面试恢复、重试与事务规则见[面试模块](../skills/mock_interviewer/README.md)。

## 开发边界

业务 prompt 放在 `skills/<模块>/prompt.py`，网络封装放在 `tools/`。业务模块之间不得互相 import，跨模块协调由 core 使用数据契约完成。MCP 可达路径不得向 stdout 输出日志。

测试使用合成配置和临时存储，禁止依赖真实个人档案或密钥。完整约束见 [AGENTS.md](../AGENTS.md)。
