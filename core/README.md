# 🧠 core/ 目录：中枢控制与数据契约层

`core/` 是整个 JobHunt-Copilot 系统的**“中枢神经”**与**“数据标准制定者”**。它统领全局数据流向，消除各个业务模块之间的直接耦合。

---

## 🏛️ 核心架构职责

```
                ┌────────────────────────────────────┐
                │           core/config.py           │
                │ (Config Loader: YAML -> Pydantic)  │
                └─────────────────┬──────────────────┘
                                  │ Parses config/*.yaml safely
                                  ▼
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
skills/resume_generator   skills/resume_polisher    skills/jd_matcher ...
```

### 1. `config.py`（统一配置加载与路径解析器）
- 职责：作为“搬运工”，定位项目根目录，读取 `config/*.yaml` 原始文本，并送入 `core/state.py` 完成 Pydantic V2 校验。
- **核心提供函数**：
  ```python
  from core.config import load_user_profile, load_job_preference, load_app_settings

  # 1. 读取并校验用户主档案 (返回 UserProfile 对象)
  profile = load_user_profile()

  # 2. 读取并校验求职偏好与雷达配置 (返回 JobPreferences 对象)
  preferences = load_job_preference()

  # 3. 读取并校验全系统运行时配置 (返回 AppSettings 对象)
  settings = load_app_settings()
  ```

### 2. `state.py`（全系统数据契约与配置桥接）
- 基于 **Pydantic V2** 构建强类型数据模型。
- **与 `config/*.yaml` 的本地配置映射**：
  | 本地配置文件 | 对应 Pydantic 模型 | 业务用途与流向 |
  | :--- | :--- | :--- |
  | `config/profile.yaml` | `UserProfile` | 个人完整档案，流向 `resume_generator`、`resume_polisher`、`mock_interviewer` |
  | `config/preferences.yaml` | `JobPreferences` | 求职意愿与雷达配置，流向 `job_radar`、`jd_matcher` |
  | `config/settings.yaml` | `AppSettings` | 运行时基础设施配置，流向 `tools/llm_client.py` 等基础设施层 |

- **其他动态业务流转模型**：
  - `JobDescription`：解析后的结构化岗位 JD（企业、岗位、硬性要求、加分项）。
  - `MatchResult`：JD 匹配结果模型（匹配度得分、技能契合点、技能缺口清单）。
  - `SkillGap`：技能差距实体（缺失技术栈、学习建议、关联开源项目推荐）。
  - `InterviewSession`：模拟面试上下文状态实体（当前轮次、问题历史、考核阶段）。
  - `ApplicationRecord`：求职投递看板记录实体。
- **价值**：大模型输出与外部配置均经过严格校验与反序列化，绝不出现格式错乱导致崩溃；任何外部 Harness（Claude Desktop / Cursor）均可通过这些 Schema 了解输入输出要求。

### 3. `workflow.py`（工作流编排总线）
- 负责定义复杂的跨技能业务流程。
- **典型场景调度流水线**：
  - `tailor_application_flow`（一键定向全套交付流）：读取 Profile ➡️ 传入目标 JD ➡️ 执行 `jd_matcher` 提取差距 ➡️ 触发 `project_recommender` 检索开源练手补强 ➡️ 触发 `resume_polisher` STAR 定向润色 ➡️ 调用 `resume_generator` 编译定制 PDF/Word ➡️ 封装交付战报 ➡️ 自动登记投递看板。
  - 交互式模拟面试由 `skills/mock_interviewer` 和 `run_interview.py` (CLI: `jobhunt interview`) 进行调度。

---

## 📌 设计规范（防腐准则）
1. **技能间零交叉引用**：`skills/` 内部的任何模块严禁跨模块互相 `import`。所有跨模块数据交互必须通过 `core/state.py` 中的标准契约对象由 `workflow.py` 调度流转。
2. **纯粹性**：`core/` 不包含具体的 LLM 提示词（Prompt 属于 `skills/`），也不包含具体的二进制/网络底层调用（底层操作属于 `tools/`）。
