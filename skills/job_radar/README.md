# 岗位雷达

批量分析本地 .txt JD，按契合度排序，汇总共性缺口并导出 Markdown 报告；不自动采集网站或提交申请。

## 使用

```powershell
uv run jobhunt radar --dir storage/raw_jds
```

将待分析 JD 放到指定目录。匹配会调用配置的模型；失败条目跳过，继续评估其他岗位。报告保存在 `storage/radar_reports/`。

| 评分 | 当前梯队 |
| --- | --- |
| ≥ 80 | 优先主投 |
| 65～79 | 微调冲刺 |
| < 65 | 暂缓考虑 |

分数是模型分析参考，不是录用概率。

## API 与职责

`scan_opportunities(jd_texts, ...)`、`scan_from_directory(dir_path, ...)` 返回 `RankedOpportunity` 列表；`run_radar_pipeline(dir_path, ...)` 返回含报告路径的 `JobRadarReport`。

旧的 `skills.job_radar` 入口保留。JD 解析 / 匹配协调位于 [core/radar_workflow.py](../../core/radar_workflow.py)；本模块负责读取、排名、共性缺口和导出。MCP 的 `tool_scan_jds` 只允许扫描项目内目录。

[配置指南](../../config/README.md) · [回归测试](../../tests/test_radar_and_cli.py)
