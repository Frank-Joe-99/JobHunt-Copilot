# 第一批开发记录：M01～M05

日期：2026-10-25  
对应路线：[最终开发路线 v1.0](FINAL-ROADMAP.md)

本批实现 M01～M05，保留现有 CLI 参数、MCP 的 13 个工具入口和主要返回字段。新增能力通过可选参数与新增字段提供。真实个人配置未修改；测试使用合成材料、临时存储和模拟 HTTP。

## 修改内容

| 工作包 | 已实现内容 | 主要代码 |
| --- | --- | --- |
| M01 | 面试风格与领域解耦；取消虚构身份、默认个人贡献与无证据的报告评分；推荐不再强制编造文件路径 | [面试处理](../skills/mock_interviewer/handler.py)、[面试任务契约](../skills/mock_interviewer/prompt.py) |
| M02 | JD 原文、结构化要求和匹配建议贯穿润色；匹配与面试保留全部必要业务材料；输入超预算明确报错而不静默截取 | [业务字段白名单](../core/context.py)、[润色处理](../skills/resume_polisher/handler.py)、[JD 匹配](../skills/jd_matcher/handler.py) |
| M03 | 快照内 ID、原文摘要和版本校验；未知、重复、过期提案在修改前拒绝；批量应用、完整差异报告与私有原始快照 | [修改校验与应用](../core/resume_edits.py)、[定制工作流](../core/workflow.py) |
| M04 | 显式配置采样与预算参数；移除统一 8192 截断；保存结束状态和使用量；区分拒绝、截断、限流、传输失败与无效响应 | [模型客户端](../tools/llm_client.py)、[配置示例](../config/settings.example.yaml) |
| M05 | 雷达跨模块协调移入 core；保留旧入口；物料准备只记心愿单，不自动记为已投递；修复缺失的 jobhunt 安装入口 | [雷达编排](../core/radar_workflow.py)、[CLI](../main.py)、[构建配置](../pyproject.toml) |

现有 YAML 的 highlights 仍为字符串列表，无需迁移用户档案。定位 ID 只对对应冻结快照有效，不宣称跨重排或跨会话永久稳定。

改写中的新增数字/英文术语、职责扩大、学习或未完成边界丢失等会触发保守检查。被标记的建议仅进入对比报告，导出草稿保留对应原文。这些规则只能发现部分疑点，不能证明改写语义真实，也可能产生需要人工排除的误报。

“尚无证据”的技能不直接当作已确认缺口触发 GitHub 搜索。推荐不可用的提示也不再解释为候选人已经覆盖所有岗位要求。

## 使用与兼容性

旧的 tailor、resume、interview、radar、tracker、mcp 命令与原有选项继续可用。

面试新增可选参数：

```powershell
uv run jobhunt interview --role strict_architect --company 示例企业 --target-role 前端开发 --jd "岗位要求：React 与可访问性" --mode practice
```

- --jd 支持纯文本或本地文本路径。
- --mode 默认 simulation；practice 在提示词层允许讲解、提示与重答。
- 缺失或损坏的档案会报告配置错误，不再使用内置虚构学历继续。
- 固定阶段与轮数机制仍保留；受控自适应属于后续 M09。

CLI tailor 默认保留本地登记行为，但状态为 wishlist，表示物料已准备。--no-track 继续关闭该登记；用户明确确认实际提交后再推进 applied。

MCP 的 tool_one_click_tailor 继续默认 auto_track=false；显式 true 时同样只登记心愿单。返回新增：

- resume_diff_path
- resume_snapshot_path
- review_required
- preparation_status（当前为 draft）

tool_polish_experiences 新增可选 jd_text；tool_interview_start 新增可选 jd_text 和 mode。未增加新的必填参数，也未增加工具数量。相关仓库 Skill 和使用说明已同步。

MCP 的 profile://summary 资源保持原有读取/脱敏行为。本批业务字段白名单用于模型分析调用，不代表这个资源已变为完全匿名的数据契约。该资源的额外调整曾被自动审批以“可能向宿主扩大私有数据暴露”为由拒绝，最终保留原实现，没有绕过审核。

## 模型配置

仅更新 settings.example.yaml。原有配置仍按兼容默认加载；需要不同参数的端点应在本机显式配置能力：

- temperature 可设 null，或以 supports_temperature=false 省略。
- token_limit_parameter 选择 max_tokens / max_completion_tokens。
- max_tokens 保留原有“输出预算”的含义；output_token_limit 可声明端点上限。
- context_char_limit 是应用输入字符预算，不是模型 token 窗口。
- supports_json_mode 可显式控制 JSON mode。

没有通过模型名称猜测能力，也没有自动切换模型、供应商或数据外发目的地。客户端仍使用现有兼容文本端点，原生 schema 和分层格式降级留待 M08。

## 验证结果

完整测试命令：

```powershell
uv run --no-sync pytest -q
```

本次结果：**71 passed**，包括原有 8 项 MCP 测试与新增回归检查。

覆盖范围：

- 真实 stdio 子进程握手、13 个工具发现、参数 schema、错误传播和原有资源脱敏。
- 使用合成档案生成本地 Word/PDF，检查产物存在及协议未被 stdout 杂项破坏。
- 全量业务材料和 JD 传递、联系方式字段排除、重复原文准确定位。
- 非法定位、过期快照、职责或指标疑点、主档案不被定制修改污染。
- HTTP 参数兼容、限流与临时错误重试、截断/拒绝/无效结构、JSON 修复状态。
- 流式中断不重播，未完整问题不记为完整题目。
- 雷达排序和失败隔离、业务模块 import 边界。
- 原 CLI 子命令帮助、旧面试参数和新可选参数。

同一合成档案面对 React 与 FastAPI 两个 JD 的输入/输出已成对审阅，验证的是传参、选定目标和应用链路；模型回复由测试替身提供，不能据此宣称真实大模型质量已经改善。

测试默认禁止真实 HTTP，MCP 子进程使用独立配置、数据库和输出目录，没有使用真实求职档案或投递看板。

另已执行：

- Python 语法编译检查。
- uv sync --offline：从本地缓存构建并安装当前项目。
- uv run jobhunt --help：实际命令入口验证通过。
- Git 差异空白检查。

构建修复添加 setuptools 后端和 Typst 模板包数据；uv.lock 的项目来源由 virtual 变为 editable，运行时依赖清单未新增。

## 本批边界

本批没有实现会话持久化、自适应阶段推进、GitHub 缓存/配额管理、原生 schema 降级或新界面。它们继续按 M06～M12 排序实施。

PDF 仍由原确定性排版器生成；本批没有增加成品解析评分，也没有把任何模型分数解释成真实招聘平台通过率。

真实提供商的在线兼容性、延迟与生成质量尚未实测。结构与语义核实需要分开看待；不完整响应会失败，不会作为已经完成的业务结果继续应用。
