# 🎭 skills/mock_interviewer/：模块 5 AI 场景化模拟面试官

> 本模块为 JobHunt-Copilot 的**沉浸式模拟面试与复盘评估系统**。结合目标企业岗位画像与候选人真实档案，基于多轮递进状态机模拟真实面试现场，提供由浅入深的穿透式追问，并在面试结束时出具六维能力复盘评估报告。

---

## 🎯 业务定位与面试官人设

解决应届生临场缺乏经验、答非所问、缺乏高质量专业导师模拟演练的痛点。

### 内置三大面试官风格：
| 考官风格代码 | 人设特点 | 提问侧重点 |
| :--- | :--- | :--- |
| `strict_architect` | **严苛技术面试官** | 根据目标岗位追问原理、因果链条、选型边界，不预设特定技术领域 |
| `practical_lead` | **务实带教业务组长** | 业务落地交付、踩坑排障思路、代码质量、工程协同与敏捷开发 |
| `hrbp` | **敏锐资深 HRBP** | 职业规划、行为面试 (BQ)、团队沟通、冲突化解与抗压稳定性 |

---

## 🔄 面试流程状态机 (State Machine)

```text
[阶段 0: 开场破冰 (INTRO)] ──────────> 自我介绍与应聘动机
                                        │
                                        ▼
[阶段 1: 简历深挖 (DEEP_DIVE)] ──────> 针对项目与实习亮点深挖底层贡献与指标
                                        │
                                        ▼
[阶段 2: 核心八股与场景 (CODING)] ───> 计算机基础、框架机制与业务设计题
                                        │
                                        ▼
[阶段 3: 行为面试 (BQ)] ─────────────> 团队协作、压力应对与软实力考察
                                        │
                                        ▼
[阶段 4: 候选人反问 (REVERSE_QA)] ───> 候选人提问，评估思考深度与职业成熟度
                                        │
                                        ▼
[阶段 5: 复盘完结 (COMPLETED)] ──────> 输出综合能力打分、诊断评语与满分范例
```

---

## 🏗️ 内部组件与核心 API

```text
skills/mock_interviewer/
├── __init__.py            # 导出 start_interview, step_interview_stream, finish_interview
├── prompt.py              # 三大人设提示词、各阶段出题规则、追问指令与复盘评分标准
├── state_machine.py       # 状态机：轮次计数、阶段流转判定与快捷指令拦截
├── handler.py             # 上下文装配、流式生成与 Markdown 报告导出
├── session_store.py       # 独立 SQLite、快照校验、请求状态与短事务
└── README.md              # 本说明文档
```

CLI / MCP 共用的持久化入口为 `core/interview_service.py`，核心接口如下。原 `skills.mock_interviewer` 导出继续作为不自动持久化的底层兼容 API；需要恢复和幂等时使用 core 服务。

### 核心接口契约：
1. **`start_interview(profile=None, target_role="...", target_company="...", role=..., provider=None)`**  
   初始化会话，返回 `(InterviewSession, Generator[str, None, None])`（会话实体与首句开场白生成器）。
2. **`step_interview_stream(session, user_answer, profile=None, provider=None) -> Generator[str, None, None]`**  
   提交作答内容，驱动状态机推演，流式输出面试官追问。
3. **`finish_interview(session, provider=None) -> tuple[InterviewEvaluationReport, Path]`**  
   结束会话，大模型结构化生成复盘报告实体，并保存至 `storage/interview_logs/`。
4. **`resume_interview(session_id)`**  
   从独立会话库恢复，不重新读取当前主档案、不请求模型。

`start_interview` 支持可选 `job_description`、`mode`；`step_interview_stream` 支持可选 `request_id`；`finish_interview` 默认 `request_id="finish"`。测试可注入 `store=InterviewStore(temporary_path)`。

### 状态与一致性

- 私有事实快照、JD、问答、schema 版本、模型身份摘要和请求状态保存在 `storage/interviews.db`，不使用 `tracker.db`。
- 在请求模型前保存回答和请求 ID；生成期间使用工作副本，完整成功后才提交新问题及其阶段。失败片段只留在请求记录，不进入正式问答和复盘。
- 跨线程、跨进程的会话文件锁阻止并发写入；SQLite 只使用短事务，等待网络时不持有数据库写锁。版本冲突会明确拒绝旧更新。
- 同一请求 ID 必须对应相同输入；完成结果可跨重启重放。旧请求重放不会回退数据库，但返回的是当时的结果快照，继续新作答前应恢复读取最新会话。
- 结束是用户的明确指令，立即关闭问答；报告失败可继续重试，不重新开放问答。相同报告请求不重复调用模型；文件丢失时从已保存结果重新导出。
- schema v1 只初始化空数据库；未知版本、未版本化的旧表或投递数据库会拒绝打开，不自动猜测迁移。

---

## 🛠️ 操作与演练指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- `config/profile.yaml` 个人档案已完善。
- `config/settings.yaml` 中大模型 API 凭证有效。

---

### 2. 通过 CLI 命令行进行模拟面试

#### 步骤 1：启动面试程序
在终端执行下列命令启动交互式演练：
```bash
# 方式 A：交互向导选择参数
uv run jobhunt interview

# 方式 B：指定参数直接启动
uv run jobhunt interview --role strict_architect --company 字节跳动 --target-role 后端开发

# 恢复保存的会话，不需要重新选择岗位或读取主档案
uv run jobhunt interview --resume-session <session_id>

# 离线管理（show 输出问答和未完成请求，不输出原始档案）
uv run jobhunt interview-sessions list
uv run jobhunt interview-sessions show <session_id>
uv run jobhunt interview-sessions delete <session_id>
```

#### 步骤 2：参数说明表
| 参数名 | 必填 | 默认值 | 说明 |
| :--- | :---: | :--- | :--- |
| `--role` | 否 | 交互选择 | 面试官人设：`strict_architect` / `practical_lead` / `hrbp` |
| `--company` | 否 | "目标大厂" | 面试企业名称 |
| `--target-role` | 否 | 主档案目标岗位 | 目标岗位名称 |
| `--jd` | 否 | 无 | JD 文本或本地文本路径 |
| `--mode` | 否 | `simulation` | `practice` 允许提示、讲解 |
| `--provider` | 否 | 配置默认 | 恢复时默认沿用原供应商；配置模型或端点变化须显式指定 |
| `--resume-session` | 否 | 无 | 使用原会话快照、岗位与模式，不与新岗位/JD/风格参数混用 |

#### 步骤 3：交互与快捷指令
- 输入回答内容，连续按**两次回车**提交长文本；
- 输入 `next`：跳过当前题目并推进到下一阶段；
- 输入 `finish`：提前交卷并立即生成复盘报告。
- 输入 `/pause`：暂停并保存；EOF 或 Ctrl+C 也会暂停，已提交回答保留。
- 输入 `/retry`：使用原请求 ID 和原回答重试未完成问题。已有回答不能用不同 ID 静默替换；可明确跳过或结束。

#### 步骤 4：查看复盘产物
面试结束时，终端输出能力诊断仪表盘，并在 `storage/interview_logs/` 下生成完整的 Markdown 复盘体检报告（含原问题、满分示范与失分点）。

删除会话会删除快照和关联请求记录；已单独导出的 Markdown 文件保留，需另行删除。会话库、锁文件、缓存和报告均在 Git 忽略的 `storage/` 中。存储为本地明文文件，遵循与现有投递库相同的私有目录约定。

---

### 3. 通过 Python API 进行多轮交互

```python
from core.state import InterviewRole
from core.interview_service import start_interview, step_interview_stream, finish_interview, resume_interview

# 1. 开启面试会话
session, stream = start_interview(
    target_role="后端开发工程师",
    target_company="腾讯",
    role=InterviewRole.STRICT_ARCHITECT,
)
print("面试官:", "".join(list(stream)))

# 2. 提交回答并推进
answer = "面试官好，我是一名计算机应届生，主修分布式存储与后端高并发架构。"
reply_stream = step_interview_stream(session, user_answer=answer, request_id="example_answer_1")
print("\n面试官追问:", "".join(list(reply_stream)))

# 3. 终结面试并导出报告
report, report_path = finish_interview(session)
print(f"\n综合评分: {report.overall_score} 分")
print(f"报告落盘路径: {report_path}")
```

相同作答重试需复用 `request_id` 和原文。背景变化时新建会话；恢复后沿用创建时的事实快照。使用的是配置的大模型服务，离线要求下只运行会话查看/删除，不运行生成流程。
