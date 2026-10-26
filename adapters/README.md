# MCP 适配层

通过 stdio 提供 13 个工具和 `profile://summary` 资源，复用项目的业务模块与 core 服务。

## 启动与接入

```powershell
uv run jobhunt mcp

# 仅生成包含本机项目路径的连接配置，不安装
uv run python -X utf8 adapters/generate_client_configs.py
```

将生成的服务定义加入宿主的 MCP 配置。服务 stdout 只承载 JSON-RPC，日志写 stderr；配置生成脚本单独运行。

## 工具

| 工具 | 用途 / 主要参数 |
| --- | --- |
| `tool_generate_resume` | 本地生成 PDF / Word；`template`、`output_name` |
| `tool_analyze_jd` | 岗位匹配和自荐信草稿；`jd_text` |
| `tool_recommend_projects` | 公开项目推荐；`skills`、`language` |
| `tool_one_click_tailor` | 定向物料；`jd_text`、`enable_github`、`auto_track` |
| `tool_diagnose_ats` | 表达与关键词诊断；可选 `target_jd_text` |
| `tool_polish_experiences` | 带定位与核实标记的改写建议；可选 `jd_text` |
| `tool_scan_jds` | 扫描项目内 JD 目录；`directory` |
| `tool_track_application` | 新增或更新投递记录；`record_id`、岗位和状态等 |
| `tool_get_upcoming_schedules` | 日程查询；`days_ahead` |
| `tool_get_funnel_analytics` | 本地漏斗统计 |
| `tool_interview_start` | 新建 / 恢复面试；岗位、`mode`、`flow`、`resume_session_id` |
| `tool_interview_answer` | 作答或控制指令；`session_id`、`user_answer`、可选 `request_id` |
| `tool_interview_finish` | 结束并生成 / 读取报告；`session_id`、`request_id="finish"` |

模型工具可通过 `provider` 选择已配置供应商。完整字段与类型以服务的 tools/list 为准。

## 定制与面试约定

- `tool_one_click_tailor` 默认 `auto_track=false`；显式开启仅登记 wishlist。返回草稿、差异及快照路径，不代表已投递。
- 面试与 CLI 共用 `storage/interviews.db`。恢复沿用原快照、岗位、流程和策略，不依赖进程内缓存。
- `flow="fixed"` 为默认流式流程，`adaptive` 为完整校验后返回的自适应试验；`mode="practice"` 允许提示和重答。
- 可选策略：`max_turns`、`max_duration_seconds`、`max_followups`、`max_requests_per_turn`、`max_requests_total`、`request_timeout_seconds`。
- 同一次作答重试复用原 `request_id` 和完全相同的输入；或输入 `/retry`。`/pause` 后使用 start 的 `resume_session_id` 恢复。
- 已完成请求直接重放；重放旧结果后先读取当前会话再继续。默认 finish 请求可跨重启读取同一报告。
- 开场 / 追问失败返回 `recoverable_error`、会话 ID 和待重试 ID。新增指标区分已知请求与崩溃未知上界；部分问题不进入正式问答。

更多用法见[面试说明](../skills/mock_interviewer/README.md)和[M09 比较方法](../future-upgrade/M09-EVALUATION.md)。

## 数据与验证

`profile://summary` 过滤部分联系字段，但仍含个人资料，不能视为匿名资源。模型分析使用独立的业务字段白名单；生成流程可能把业务材料发送到外部模型。

```powershell
uv run pytest -q tests/test_mcp_protocol.py tests/test_mcp_tools.py tests/test_interview_entrypoints.py tests/test_adaptive_interview.py
```

测试使用临时数据与离线替身。实现见 [mcp_server.py](mcp_server.py)。
