# AGENTS.md

JobHunt-Copilot：本地优先的应届生求职工具（简历生成、JD 匹配、STAR 润色、开源项目推荐、岗位雷达、模拟面试、投递看板）。

## 运行环境
- Python ≥ 3.12，使用 `uv` 管理依赖：`uv sync`，命令一律通过 `uv run` 执行。
- 统一 CLI 入口：`uv run jobhunt --help`（`tailor` / `resume` / `interview` / `radar` / `tracker` / `mcp`）。
- Windows 下直接 `python` 输出中文/emoji 可能乱码，必要时加 `-X utf8`。

## 目录约定
- `core/`：数据契约（`state.py`）、配置加载、工作流编排。
- `skills/<name>/`：业务模块（`handler.py` + `prompt.py`）。**模块之间不得互相 import**，跨模块数据只经 `core/state.py` 的对象流转。
- `tools/`：纯技术封装（LLM 客户端、GitHub 客户端），不含业务提示词。
- `adapters/`：外部协议适配（MCP 服务端）。
- `.agents/skills/`：Codex Skill（`SKILL.md` + `agents/openai.yaml`），通过 `$jobhunt-*` 显式调用。

## 隐私红线
- `config/profile.yaml`、`config/preferences.yaml`、`config/settings.yaml`、`config/assets/*` 含个人信息与密钥，已在 `.gitignore` 中。**禁止**在对话、日志、提交里输出其内容；修改配置只改 `*.example.*` 模板。
- `storage/` 下的简历、面试记录、雷达报告、`tracker.db` 均为私有产物，**不得提交**。
- 调用 LLM/GitHub 的流程会把档案或 JD 内容发往外部服务；用户要求离线时不要运行。

## 内容真实性
- 生成或润色简历内容时，不得编造雇主、项目、技术栈、指标、规模或影响力；缺失数据用占位符并提示用户核实。
- 开源项目推荐里的 STAR 文本只是**待完成后才能使用的模板**，不能写成已完成的成果。

## 开发约束
- 凡是会被 `adapters/mcp_server.py` 调用到的代码路径，**禁止向 stdout 写内容**（`print`、rich `Console()` 默认输出）：stdio 传输用 stdout 承载 JSON-RPC，杂项输出会破坏协议。需要日志时使用 `logging` 或写 stderr。
- 不要提交 `tmp/`、`storage/`、`config/*.yaml`（非 example）。
- 修改 `main.py` 的 CLI 参数时，同步更新 `.agents/skills/*/SKILL.md` 中引用的命令。
