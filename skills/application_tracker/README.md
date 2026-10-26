# 投递看板与日程

使用本地 `storage/tracker.db` 保存求职记录、日程和备注，提供列表、漏斗及到期查询，不调用模型或自动推送提醒。

## 使用

```powershell
uv run jobhunt tracker

# 先登记准备中的岗位
uv run jobhunt tracker add --company 示例企业 --role 前端开发 --status wishlist

# 实际投递后，按真实记录 ID 更新
uv run jobhunt tracker update 1 --status applied
uv run jobhunt tracker update 1 --status interview_1 --schedule "2026-11-02 14:00" --notes "线上面试"

uv run jobhunt tracker schedules --days 7
uv run jobhunt tracker update 1 --clear-schedule
```

支持状态：`wishlist`、`applied`、`assessment`、`interview_1`、`interview_2`、`hr_stage`、`offer`、`rejected`、`closed`。

`tracker add` 默认 applied，只有已实际提交时才使用该语义；准备记录显式选 wishlist。定制流程的自动记录只记 wishlist，`--no-track` 可关闭；MCP 定制默认不登记。

## API

从 `skills.application_tracker` 导入：

- `add_application` / `get_application` / `list_applications`
- `update_status` / `delete_application`
- `get_upcoming_schedules` / `get_funnel_analytics`

可通过 `db_path` 注入临时库。数据库连接与建表在 `database.py`，业务逻辑在 `handler.py`；面试记录使用独立的 interviews.db。

[CLI 全部参数](../../README.md) · [存储说明](../../storage/README.md) · [MCP 工具](../../adapters/README.md)
