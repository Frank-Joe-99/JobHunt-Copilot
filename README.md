# JobHunt-Copilot

本地优先的求职工具：简历生成、JD 匹配、经历润色、开源项目推荐、岗位雷达、模拟面试和投递看板。

[完整升级目录](future-upgrade/UPGRADE-INDEX.md) · [配置指南](config/README.md) · [MCP 接入](adapters/README.md)

## 开始使用

需要 Python ≥ 3.12 和 uv。在项目根目录执行：

```powershell
uv sync
```

按[配置指南](config/README.md)从 example 模板创建个人档案、偏好和模型设置，填写真实经历及可用的模型凭证。已有本地配置请保留。

```powershell
uv run python -X utf8 check_config.py
uv run jobhunt --help
```

## 常用命令

```powershell
# 从本地档案导出 PDF / Word
uv run jobhunt resume -o my_resume

# 按 JD 定制草稿；也可传入本地 JD 文本文件路径
uv run jobhunt tailor "示例岗位要求：React 与可访问性" --no-track

# 批量匹配本地 .txt 岗位文件
uv run jobhunt radar --dir storage/raw_jds

# 原流式面试 / 可选自适应训练
uv run jobhunt interview
uv run jobhunt interview --flow adaptive --mode practice --company 示例企业 --target-role 前端开发

# 看板 / 近期待办 / MCP 服务
uv run jobhunt tracker
uv run jobhunt tracker schedules --days 7
uv run jobhunt mcp
```

各命令的完整参数见 `uv run jobhunt <命令> --help`。

## 面试恢复与管理

回答在请求模型前保存；恢复沿用创建时的事实快照、岗位、流程和预算。

```powershell
uv run jobhunt interview --resume-session <session_id>
uv run jobhunt interview-sessions list
uv run jobhunt interview-sessions show <session_id>
uv run jobhunt interview-sessions compare <fixed_id> --with-session <adaptive_id>
uv run jobhunt interview-sessions delete <session_id>
```

回答后输入空行或 `/send` 提交；`/next` 跳过、`/pause` 暂停、`/retry` 重试、`/finish` 交卷。示例中的 `<session_id>` 等需替换为实际 ID。删除会话不删除已导出的 Markdown 报告。

默认 `--flow fixed` 保持流式流程；`adaptive` 在完整校验并保存后显示问题。`--mode practice` 允许提示和重答。预算、指标和比较方法见[面试说明](skills/mock_interviewer/README.md)。

## 生成结果与数据边界

- 定制输出简历草稿、修改对比和原始快照；改写按快照内 ID 校验，存疑项保留原文。使用前核对事实。
- 生成物料表示“已准备”；CLI 默认登记 `wishlist`，`--no-track` 可关闭，实际投递后再推进 `applied`。
- GitHub 推荐有预算、带日期缓存和失败降级；STAR 文本是完成任务后才可使用的模板。
- 基础简历排版、看板和会话查看/对比在本地运行；匹配、润色、推荐和面试生成会调用配置的外部服务。`--no-github` 只关闭 GitHub。
- 个人配置、图片、数据库与生成物保留本地，不提交。目录和删除范围见[存储说明](storage/README.md)。

## 文档与开发

| 内容 | 入口 |
| --- | --- |
| 配置与图片 | [config](config/README.md)、[assets](config/assets/README.md) |
| 业务模块与仓库 Skill | [skills](skills/README.md)、[.agents/skills](.agents/skills/) |
| 数据契约、编排与基础工具 | [core](core/README.md)、[tools](tools/README.md) |
| MCP 的 13 个工具 | [adapters](adapters/README.md) |
| M01～M09 改动、使用方法和后续规划 | [升级目录](future-upgrade/UPGRADE-INDEX.md) |

离线回归使用合成材料和模拟服务，当前为 157 项；真实模型的质量与延迟需另行评审。

```powershell
uv run pytest -q
```

开发约束见 [AGENTS.md](AGENTS.md)，许可证为 [MIT](LICENSE)。
