# 🎭 skills/mock_interviewer/：模块 5 AI 场景化模拟面试官

> 本模块为 JobHunt-Copilot 的**沉浸式模拟面试与复盘评估系统**。结合目标企业岗位画像与候选人真实档案，基于多轮递进状态机模拟真实面试现场，提供由浅入深的穿透式追问，并在面试结束时出具六维能力复盘评估报告。

---

## 🎯 业务定位与面试官人设

解决应届生临场缺乏经验、答非所问、缺乏高质量专业导师模拟演练的痛点。

### 内置三大面试官风格：
| 考官风格代码 | 人设特点 | 提问侧重点 |
| :--- | :--- | :--- |
| `strict_architect` | **硬核严苛架构师** | 底层原理深挖、高并发与极限吞吐场景、分布式一致性、选型边界 |
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
├── handler.py             # 核心调度器：上下文装配、流式对话生成与 Markdown 报告持久化
└── README.md              # 本说明文档
```

### 核心接口契约：
1. **`start_interview(profile=None, target_role="...", target_company="...", role=..., provider=None)`**  
   初始化会话，返回 `(InterviewSession, Generator[str, None, None])`（会话实体与首句开场白生成器）。
2. **`step_interview_stream(session, user_answer, profile=None, provider=None) -> Generator[str, None, None]`**  
   提交作答内容，驱动状态机推演，流式输出面试官追问。
3. **`finish_interview(session, provider=None) -> tuple[InterviewEvaluationReport, Path]`**  
   结束会话，大模型结构化生成复盘报告实体，并保存至 `storage/interview_logs/`。

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
```

#### 步骤 2：参数说明表
| 参数名 | 必填 | 默认值 | 说明 |
| :--- | :---: | :--- | :--- |
| `--role` | 否 | 交互选择 | 面试官人设：`strict_architect` / `practical_lead` / `hrbp` |
| `--company` | 否 | "目标大厂" | 面试企业名称 |
| `--target-role` | 否 | 主档案目标岗位 | 目标岗位名称 |

#### 步骤 3：交互与快捷指令
- 输入回答内容，连续按**两次回车**提交长文本；
- 输入 `next`：跳过当前题目并推进到下一阶段；
- 输入 `finish`：提前交卷并立即生成复盘报告。

#### 步骤 4：查看复盘产物
面试结束时，终端输出能力诊断仪表盘，并在 `storage/interview_logs/` 下生成完整的 Markdown 复盘体检报告（含原问题、满分示范与失分点）。

---

### 3. 通过 Python API 进行多轮交互

```python
from core.state import InterviewRole
from skills.mock_interviewer import start_interview, step_interview_stream, finish_interview

# 1. 开启面试会话
session, stream = start_interview(
    target_role="后端开发工程师",
    target_company="腾讯",
    role=InterviewRole.STRICT_ARCHITECT,
)
print("面试官:", "".join(list(stream)))

# 2. 提交回答并推进
answer = "面试官好，我是一名计算机应届生，主修分布式存储与后端高并发架构。"
reply_stream = step_interview_stream(session, user_answer=answer)
print("\n面试官追问:", "".join(list(reply_stream)))

# 3. 终结面试并导出报告
report, report_path = finish_interview(session)
print(f"\n综合评分: {report.overall_score} 分")
print(f"报告落盘路径: {report_path}")
```
