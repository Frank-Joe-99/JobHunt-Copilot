# 开源项目推荐

根据已确认的 missing / partial 技能缺口检索公开仓库，结合有限 README 证据生成学习建议。未知技能先澄清，不直接触发补强推荐。

## API

```python
from core.state import SkillGap
from skills.project_recommender import recommend_projects_report

report = recommend_projects_report(
    skills_gaps=[SkillGap(skill="TypeScript", status="missing")],
    language="typescript",
)
```

`recommend_projects()` 返回项目列表；`recommend_projects_report()` 还返回状态、降级说明、请求数和缓存命中数。MCP 对应 `tool_recommend_projects`，定制流程也可自动使用。

## 预算与证据

- 默认最多 6 次请求、3 次搜索、2 份 README；大小、耗时、缓存期限见 [settings 示例](../../config/settings.example.yaml)。
- 公开资料缓存到 `storage/github_cache.db`；陈旧结果保留原日期，不冒充实时星数。
- 区分 `completed`、`disabled`、`unavailable`、`no_match`、`no_gaps`，服务失败可降级而不阻断简历主流程。
- 仓库身份和元数据来自实际读取；精确文件引用需有来源依据，不默认遍历整个仓库。
- STAR 文本是实际完成学习 / 实现后才可使用的模板，不能写成已完成成果。
- GitHub 离线设置只关闭 GitHub；读取缓存后生成建议仍可能调用模型。

[底层工具](../../tools/README.md) · [离线测试](../../tests/test_github_recommendations.py)
