# JD 解析与匹配

保留 JD 原文，将岗位要求与候选人的必要业务材料比较，输出优势、缺口、改写建议和自荐信草稿。

## API

```python
from skills.jd_matcher import analyze_jd

result = analyze_jd("示例岗位要求：React、TypeScript 与可访问性")
```

| 入口 | 返回 |
| --- | --- |
| `parse_jd(jd_text, provider=None)` | `JobDescription`，含原文和结构化要求 |
| `match_profile_with_jd(profile, jd, provider=None)` | `MatchResult` |
| `analyze_jd(jd_text, profile=None, provider=None)` | 解析与匹配的组合结果 |

`MatchResult` 包含 `score`、`overview`、`matched_skills`、`missing_skills`、`resume_tuning_advice` 和 `cover_letter_draft`。

## 行为边界

分析保留全部必要经历，按业务白名单排除无关联系方式；输入超预算会报错，不静默截断。缺少证据不直接等同“不会”，模型分析也不能反向当作候选人事实。

本模块调用配置的模型，不直接调度其他业务模块。跨模块定制由 [core/workflow.py](../../core/workflow.py)完成；MCP 对应 `tool_analyze_jd`。

[配置指南](../../config/README.md) · [匹配与定制测试](../../tests/test_resume_tailoring.py)
