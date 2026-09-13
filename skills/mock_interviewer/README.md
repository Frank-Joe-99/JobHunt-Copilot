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
```text
skills/mock_interviewer/
├── __init__.py
├── prompt.py              # 面试官性格人设 Prompt、不同轮次出题策略、打分评测体系
├── state_machine.py       # 多轮状态跳转逻辑与上下文维护
├── handler.py             # 核心逻辑：推进对话、处理用户语音/文本输入、汇总复盘报告
└── README.md
```

## 📥 输入与输出契约
- **输入**：`UserProfile` + `JobDescription` + 面试角色设定（如：严苛架构师、亲和 HR）。
- **输出**：多轮流式对话 + 最终输出的 `InterviewEvaluationReport`（存储至 `storage/interview_logs/`）。
