# 经历润色与关键词诊断

结合真实经历和可选 JD 生成改写建议；ATS 诊断用于检查表达与证据覆盖，不代表招聘平台的实际筛选结果。

## API

```python
from skills.resume_polisher import polish_experiences, diagnose_ats

report = polish_experiences(jd_text="示例岗位要求：React 与可访问性")
ats = diagnose_ats(target_jd_text="示例岗位要求：React 与可访问性")
```

可显式传入 `profile` 和 `provider`。润色还支持 `job_description`、`match_result`、`snapshot`，旧的调用方式保留。

| 结果 | 主要字段 |
| --- | --- |
| `ResumePolishReport` | `summary`、`snapshot_id`、`items`、`needs_confirmation` |
| 改写条目 | `target_ref`、原文摘要、`original`、`polished`、理由和核实标记 |
| `ATSScoreReport` | `score`、`dimension_scores`、`matched_keywords`、`missing_keywords`、`suggestions` |

## 应用规则

改写定位只在对应冻结快照内有效；未知、重复和过期目标会拒绝。新增数字、技术名、职责扩大等疑点被保守标记，定制草稿保留相应原文；规则不能证明语义真实。

本模块返回建议，不写回主档案。[core/resume_edits.py](../../core/resume_edits.py)负责审查、应用和差异，完整交付使用 `uv run jobhunt tailor "JD文本"`。

MCP 对应 `tool_polish_experiences` 和 `tool_diagnose_ats`。生成会调用配置的模型；测试见 [test_resume_tailoring.py](../../tests/test_resume_tailoring.py)。
