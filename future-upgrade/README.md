# 升级文档

M01～M09 已实现，现有 CLI 和 13 个 MCP 工具保持兼容；M09 为可选自适应试验，默认仍是 fixed。M10～M12 为后续规划。

**先读[完整升级目录](UPGRADE-INDEX.md)**，了解阅读顺序、功能变化、使用入口、代码、测试与提交。

| 文档 | 内容 |
| --- | --- |
| [最终路线](FINAL-ROADMAP.md) | 取舍、依赖、验收与后续规划 |
| [第一批 M01～M05](BATCH-1-IMPLEMENTATION.md) | 事实边界、JD、快照改写、模型参数与编排 |
| [第二批 M06～M07](BATCH-2-IMPLEMENTATION.md) | 公开资料缓存、降级与会话恢复 |
| [第三批 M08～M09](BATCH-3-IMPLEMENTATION.md) | 分层输出、受控自适应、指标与迁移 |
| [M08 说明](M08-STRUCTURED-OUTPUT.md) | 格式、能力缓存、错误分类和预算 |
| [M09 试验方法](M09-EVALUATION.md) | 使用、自适应限制和成对质量 / 延迟比较 |

当前 157 项离线回归验证确定性边界，不证明真实模型效果提升；在线质量与延迟仍需另行评审。

历史讨论保存在[初版分析](INITIAL-ANALYSIS.md)和[审核意见](Adverse.md)。日常使用见[项目 README](../README.md)。

