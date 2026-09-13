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

### 1. `state.py`（全系统数据契约与配置桥接）
- 基于 **Pydantic V2** 构建强类型数据模型。
- **与 `config/*.yaml` 的本地配置桥接**：
  `core/state.py` 是连接底层本地 YAML 配置文件与上层业务技能的桥梁：
  | 本地配置文件 | 对应 Pydantic 模型 | 业务用途与流向 |
  | :--- | :--- | :--- |
  | `config/profile.yaml` | `UserProfile` | 个人完整档案，流向 `resume_polisher`、`resume_generator`、`mock_interviewer` |
  | `config/preferences.yaml` | `JobPreferences` | 求职意愿与雷达配置，流向 `job_radar`、`jd_matcher` |
  | `config/settings.yaml` | `AppSettings` | 运行时基础设施配置，流向 `tools/llm_client.py`、`tools/pdf_engine.py` |

- **配置加载与反序列化范式**：
  ```python
  import yaml
  from core.state import UserProfile, JobPreferences, AppSettings

  # 1. 加载用户主档案
  with open("config/profile.yaml", "r", encoding="utf-8") as f:
      profile = UserProfile.model_validate(yaml.safe_load(f))

  # 2. 加载求职偏好
  with open("config/preferences.yaml", "r", encoding="utf-8") as f:
      preferences = JobPreferences.model_validate(yaml.safe_load(f))

  # 3. 加载系统大模型与环境设置
  with open("config/settings.yaml", "r", encoding="utf-8") as f:
      settings = AppSettings.model_validate(yaml.safe_load(f))
  ```

- **其他动态业务流转模型**：
  - `JobDescription`：解析后的结构化岗位 JD（企业、岗位、硬性要求、加分项）。
  - `MatchResult`：JD 匹配结果模型（匹配度得分、技能契合点、技能缺口清单）。
  - `SkillGap`：技能差距实体（缺失技术栈、学习建议、关联开源项目推荐）。
  - `InterviewState`：模拟面试上下文状态机（当前轮次、问题历史、打分项）。
  - `ApplicationRecord`：求职投递看板记录实体。
- **价值**：大模型输出与外部配置均经过严格校验与反序列化，绝不出现格式错乱导致崩溃；任何外部 Harness（Claude Desktop / Cursor）均可通过这些 Schema 了解输入输出要求。

### 2. `workflow.py`（工作流编排总线）
- 负责定义复杂的跨技能业务流程。
- **典型场景调度流水线**：
  - `one_click_tailor_flow`（一键定制流）：读取 Profile ➡️ 传入目标 JD ➡️ 执行 `jd_matcher` 提取差距 ➡️ 触发 `resume_polisher` 生成针对性简历 ➡️ 调用 `resume_generator` 导出 PDF。
  - `interview_prep_flow`（面试备战流）：读取针对性简历与 JD ➡️ 触发 `mock_interviewer` 生成该企业专属模拟题库 ➡️ 启动交互状态机。

---

## 📌 设计规范（防腐准则）
1. **技能间零交叉引用**：`skills/` 内部的任何模块严禁跨模块互相 `import`。所有跨模块数据交互必须通过 `core/state.py` 中的标准契约对象由 `workflow.py` 调度流转。
2. **纯粹性**：`core/` 不包含具体的 LLM 提示词（Prompt 属于 `skills/`），也不包含具体的 PDF 编译二进制调用（底层操作属于 `tools/`）。
