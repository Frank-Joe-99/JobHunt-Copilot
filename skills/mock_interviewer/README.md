# 模拟面试

根据岗位 / JD 和真实档案进行问答与复盘。风格可选 `strict_architect`、`practical_lead`、`hrbp`，技术领域独立由岗位决定。

## 开始与恢复

```powershell
uv run jobhunt interview
uv run jobhunt interview --flow adaptive --mode practice --company 示例企业 --target-role 前端开发
uv run jobhunt interview --resume-session <session_id>
```

| 参数 | 行为 |
| --- | --- |
| `--flow fixed` | 默认，固定阶段流式问答 |
| `--flow adaptive` | 可选试验，每轮一个小决策，完整校验并保存后显示正文 |
| `--mode simulation` | 默认模拟，保持考官视角 |
| `--mode practice` | 允许提示、讲解和重答 |
| `--jd` / `--provider` | JD 文本或文件 / 已配置供应商 |

阶段路标为自我介绍、项目深挖、岗位基础、行为场景和反问。自适应可澄清、追问或进入下一阶段；充分回答可立即换题，最后反问先回应再结束。

回答后用空行或 `/send` 提交；`/next` 跳过、`/pause` 暂停、`/retry` 重试、`/finish` 交卷。EOF / Ctrl+C 也会暂停。恢复沿用原快照、流程和预算，不附加新岗位或预算参数；改变背景或策略需新建会话。模型 / 端点变化时显式指定 `--provider`。

## 自适应预算

| 参数 | 默认 |
| --- | ---: |
| `--max-turns` | 16，含开场、提示与重答 |
| `--max-duration` | 1800 秒有效时长，暂停不计 |
| `--max-followups` | 连续追问最多 2 次，不要求问满 |
| `--request-budget` | 每轮最多 1 次模型 HTTP 请求 |
| `--max-requests` | 整场问答最多 32 次请求 |
| `--request-timeout` | 单轮生成 30 秒 |

复盘请求另计。fixed 默认保留旧行为，显式指定预算时执行共有轮数、时长与请求限制；追问上限用于 adaptive。结构化输出还受模型配置预算约束。

## 查看、比较与删除

```powershell
uv run jobhunt interview-sessions list
uv run jobhunt interview-sessions show <session_id>
uv run jobhunt interview-sessions compare <fixed_id> --with-session <adaptive_id>
uv run jobhunt interview-sessions delete <session_id>
```

这些管理操作离线运行。show 提供问答与指标；compare 核对输入和共有策略，展示服务侧文本就绪延迟、失败 / 重试和已知请求数。崩溃遗留请求保留未知上界，不当作实测费用。真实质量与延迟比较见 [M09 试验方法](../../future-upgrade/M09-EVALUATION.md)。

## 存储与 API

回答先保存；失败片段不进入正式问答。跨进程会话锁和版本检查阻止并发覆盖，网络期间不持有数据库写事务。同请求 ID 必须对应相同输入，完整结果可重放；回放旧结果后先恢复读取当前会话再继续。

私有快照、问答与请求保存在 `storage/interviews.db`，报告位于 `storage/interview_logs/`。删除会话会级联删除请求，已导出报告保留。数据库 v2 从精确校验的 v1 表新增指标列，旧事实与历史不重写。

持久化 API 从 `core.interview_service` 导入 `start_interview`、`step_interview_stream`、`resume_interview`、`finish_interview`；流式生成器需消费完成。`skills.mock_interviewer` 的包级 API 保留为底层兼容入口，不自动持久化。

复盘只使用正式问答，区分训练帮助与候选人事实；证据不足标未观察到。当前默认 fixed，尚未以真实模型评审证明 adaptive 更好。

[持久化测试](../../tests/test_interview_persistence.py) · [自适应测试](../../tests/test_adaptive_interview.py) · [MCP 接入](../../adapters/README.md)
