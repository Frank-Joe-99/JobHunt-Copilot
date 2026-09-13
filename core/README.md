# 🧠 core/ 目录：中枢控制与数据契约层

`core/` 是整个 JobHunt-Copilot 系统的**“中枢神经”**与**“数据标准制定者”**。它统领全局数据流向，消除各个业务模块之间的直接耦合。

---

## 🏛️ 核心架构职责

```
                ┌────────────────────────────────────┐
                │           core/state.py            │
                │  (Global Pydantic Data Contracts)  │
                └─────────────────┬──────────────────┘
                                  │ Defines standard data flow
                                  ▼
                ┌────────────────────────────────────┐
                │          core/workflow.py          │
                │ (Workflow & State Machine Engine)  │
                └─────────────────┬──────────────────┘
                                  │ Dispatches expert skills
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
skills/resume_polisher    skills/jd_matcher      skills/mock_interviewer
```

### 1. `state.py`（全系统数据契约）
- 基于 **Pydantic V2** 构建强类型数据模型。
- **数据结构定义**：
  - `UserProfile`：个人完整主档案对象（教育、技能、经历、荣誉等）。
  - `JobDescription`：解析后的结构化岗位 JD（企业、岗位、硬性要求、加分项）。
  - `MatchResult`：JD 匹配结果模型（匹配度得分、技能契合点、技能缺口清单）。
  - `SkillGap`：技能差距实体（缺失技术栈、学习建议、关联开源项目推荐）。
  - `InterviewState`：模拟面试上下文状态机（当前轮次、问题历史、打分项）。
  - `ApplicationRecord`：求职投递看板记录实体。
- **价值**：大模型输出的数据经过严格校验与反序列化，绝不出现格式错乱导致崩溃；任何外部 Harness 均可通过这些 Schema 了解输入输出要求。

### 2. `workflow.py`（工作流编排总线）
- 负责定义复杂的跨技能业务流程。
- **典型场景调度流水线**：
  - `one_click_tailor_flow`（一键定制流）：读取 Profile ➡️ 传入目标 JD ➡️ 执行 `jd_matcher` 提取差距 ➡️ 触发 `resume_polisher` 生成针对性简历 ➡️ 调用 `resume_generator` 导出 PDF。
  - `interview_prep_flow`（面试备战流）：读取针对性简历与 JD ➡️ 触发 `mock_interviewer` 生成该企业专属模拟题库 ➡️ 启动交互状态机。

---

## 📌 设计规范（防腐准则）
1. **技能间零交叉引用**：`skills/` 内部的任何模块严禁跨模块互相 `import`。所有跨模块数据交互必须通过 `core/state.py` 中的标准契约对象由 `workflow.py` 调度流转。
2. **纯粹性**：`core/` 不包含具体的 LLM 提示词（Prompt 属于 `skills/`），也不包含具体的 PDF 编译二进制调用（底层操作属于 `tools/`）。
