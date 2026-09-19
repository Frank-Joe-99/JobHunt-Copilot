# 🎭 skills/mock_interviewer/：模块 5 AI 场景化模拟面试官

## 🎯 业务定位与解决痛点
- **解决痛点**：
  - 应届生初入职场，由于缺乏实战面试经验，容易临场慌乱、语无伦次；
  - 面试官一旦深挖项目细节（如“为什么选这个架构？出现并发冲突怎么排查？”），往往答非所问；
  - 找不到资深学长或行业导师进行高质量的全真模拟演练。
- **本模块职责**：
  - 结合目标企业、具体岗位 JD 与求职者的真实简历，构建专属的 AI 模拟面试官；
  - 基于**多轮状态机（State Machine）**推进真实面试流程，支持由浅入深的穿透式追问与压力面测试；
  - 面试结束后即时生成**《面试复盘体检报告》**，提供回答亮点、致命软肋与高分改进参考。

---

## 🔄 面试流程状态机设计
```text
[Stage 0: Icebreaking] ─────────> Self-introduction & job motivation
                                     │
                                     ▼
[Stage 1: Resume Deep Dive] ────> Technical deep dive into core projects & experiences
                                     │
                                     ▼
[Stage 2: Core Fundamentals] ───> Essential domain knowledge (Data structures, Networks, etc.)
                                     │
                                     ▼
[Stage 3: Behavioral & BQ] ─────> Behavioral questions (Teamwork, Conflict resolution, Stress)
                                     │
                                     ▼
[Stage 4: Reverse Q&A] ─────────> Candidate reverse Q&A, evaluating depth & maturity
                                     │
                                     ▼
[Stage 5: Debrief & Summary] ───> Multi-dimensional evaluation radar & feedback report
```

---

## 📂 预期内部结构
## 📂 模块内部架构
```text
skills/mock_interviewer/
├── __init__.py
├── prompt.py              # 面试官性格人设 Prompt、不同轮次出题策略、打分评测体系
├── state_machine.py       # 多轮状态跳转逻辑与上下文维护
├── handler.py             # 核心逻辑：推进对话、处理用户语音/文本输入、汇总复盘报告
├── __init__.py            # 导出 start_interview, step_interview_stream, finish_interview 等
├── prompt.py              # 三大人设 Prompt、5 大阶段出题规范、穿透追问机制、复盘评估 Prompt
├── state_machine.py       # 状态机控制器：阶段跳转规则、轮次计数、快捷指令拦截 (/next, /finish)
├── handler.py             # 业务处理器：组装候选人画像与历史上下文、流式问答推进、复盘报告生成
└── README.md
```

## 📥 输入与输出契约
- **输入**：`UserProfile` + `JobDescription` + 面试角色设定（如：严苛架构师、亲和 HR）。
- **输出**：多轮流式对话 + 最终输出的 `InterviewEvaluationReport`（存储至 `storage/interview_logs/`）。
## 📥 核心 API 规范

### 1. `start_interview(...)`
```python
def start_interview(
    profile: UserProfile | None = None,
    target_role: str = "AI infra 研究员",
    target_company: str = "目标大厂",
    role: InterviewRole = InterviewRole.STRICT_ARCHITECT,
    provider: str | None = None,
) -> tuple[InterviewSession, Generator[str, None, None]]:
    """初始化面试会话，返回 (session 实体, 首句开场白流式生成器)"""
```

### 2. `step_interview_stream(...)`
```python
def step_interview_stream(
    session: InterviewSession,
    user_answer: str,
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> Generator[str, None, None]:
    """接收候选人回答，驱动状态机推演，流式输出面试官的下一句追问或转入新阶段"""
```

### 3. `finish_interview(...)`
```python
def finish_interview(
    session: InterviewSession,
    provider: str | None = None,
) -> tuple[InterviewEvaluationReport, Path]:
    """终结面试，调用大模型生成全维度复盘体检报告，并持久化保存为 Markdown 文件"""
```

---

## 🚀 极简调用示例

```python
from core.state import InterviewRole
from skills.mock_interviewer import start_interview, step_interview_stream, finish_interview

# 1. 开启面试
session, stream = start_interview(
    target_role="分布式存储研发工程师",
    target_company="字节跳动",
    role=InterviewRole.STRICT_ARCHITECT,
)
for chunk in stream:
    print(chunk, end="", flush=True)

# 2. 多轮推进
while not session.is_finished:
    user_input = input("\n\n候选人回答 (/next 跳过, /finish 交卷) > ")
    stream = step_interview_stream(session, user_input)
    for chunk in stream:
        print(chunk, end="", flush=True)

# 3. 出具全景复盘报告
report, file_path = finish_interview(session)
print(f"\n报告已生成: {file_path}, 综合得分: {report.overall_score}")
```
