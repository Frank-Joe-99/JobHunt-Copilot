# 🧠 core/ 目录：中枢控制与数据契约层

> 本模块为 JobHunt-Copilot 系统的**中枢控制层**。通过统一 Pydantic 强类型数据契约与流水线调度引擎，解耦各个独立业务技能，维护系统数据流动的一致性。

---

## 🏛️ 架构与数据流转

```text
                ┌────────────────────────────────────┐
                │           core/config.py           │
                │  (配置加载器：YAML 文本 ➔ 强类型)   │
                └─────────────────┬──────────────────┘
                                  │ 读取并校验本地 config/*.yaml
                                  ▼
                ┌────────────────────────────────────┐
                │           core/state.py            │
                │    (系统级 Pydantic V2 数据契约)   │
                └─────────────────┬──────────────────┘
                                  │ 提供跨模块统一数据实体
                                  ▼
                ┌────────────────────────────────────┐
                │          core/workflow.py          │
                │  (业务流水线编排总线与调度状态机)   │
                └─────────────────┬──────────────────┘
                                  │ 分发至各个独立业务技能
        ┌─────────────────────────┼─────────────────────────┐
        ▼                         ▼                         ▼
skills/resume_generator   skills/resume_polisher    skills/jd_matcher ...
```

---

## 🧩 核心组件职责

### 1. `config.py`（配置加载器）
- **功能定位**：定位项目根目录，安全读取 `config/*.yaml` 原始文本，并调用 Pydantic 校验模型完成数据反序列化。
- **提供的核心函数**：
  - `load_user_profile()` ➔ 返回 `UserProfile` 实体
  - `load_job_preference()` ➔ 返回 `JobPreferences` 实体
  - `load_app_settings()` ➔ 返回 `AppSettings` 实体

### 2. `state.py`（统一数据契约）
- **功能定位**：定义系统跨模块流转的全部强类型数据结构，确保所有数据在进出大模型或外部存储时格式受控。
- **配置实体与映射关系**：
  | 配置文件 | 对应 Pydantic 模型 | 业务流向 |
  | :--- | :--- | :--- |
  | `config/profile.yaml` | `UserProfile` | 主档案，流向简历生成、经历润色与模拟面试 |
  | `config/preferences.yaml` | `JobPreferences` | 求职意愿配置，流向岗位雷达与匹配器 |
  | `config/settings.yaml` | `AppSettings` | 运行时系统配置，流向统一 LLM 客户端与 GitHub 工具 |

- **关键业务流转模型**：
  - `JobDescription`：结构化岗位画像（公司名、岗位名、技术要求、加分项）。
  - `MatchResult`：人岗匹配分析结果（匹配分 0-100、命中技能、缺口清单、自荐信）。
  - `SkillGap`：技术短板实体（技能名、状态、补强建议）。
  - `TailoredApplicationPackage`：定向交付物料包（专属简历路径、综合战报路径）。
  - `InterviewSession`：模拟面试上下文状态实体（轮次、历史问答、当前阶段）。
  - `ApplicationRecord`：求职看板投递记录实体。

### 3. `workflow.py`（业务编排流水线）
- **功能定位**：组织跨技能复杂工作流，实现全自动物料交付。
- **核心流水线**：`tailor_application_flow`（端到端一键定向交付流）。
- **零污染准则**：经历定制和 STAR 重构仅在**内存深拷贝快照**中发生，绝对不向主档案 `config/profile.yaml` 执行写回操作。

---

## 🛠️ 核心操作与调用指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- 配置文件 `config/profile.yaml` 与 `config/settings.yaml` 存在且格式正确。
- 依赖环境已激活（运行于 `uv run` 环境中）。

---

### 2. 加载与校验用户档案操作

#### 步骤 1：导入加载函数
在 Python 模块中导入配置加载接口：
```python
from core.config import load_user_profile
```

#### 步骤 2：执行读取并访问字段
```python
# 读取主档案（自动进行 Pydantic 校验）
profile = load_user_profile()

# 访问强类型字段
print(f"姓名: {profile.basics.name}")
print(f"最高学历: {profile.education[0].degree}")
```
*预期结果*：如果 YAML 字段缺失或类型错误，将直接抛出 `pydantic.ValidationError` 并指出具体错误行；如果正常，返回完整的 `UserProfile` 对象。

---

### 3. 执行一键定向求职交付流水线操作

#### 步骤 1：调用业务流水线接口
```python
from core.workflow import tailor_application_flow

# 执行一键交付流
package = tailor_application_flow(
    jd_input="storage/raw_jds/01_bytedance_backend.txt",
    output_name="resume_bytedance_tailored",
    enable_github_search=True,
    auto_track=False,
)
```

#### 步骤 2：获取交付物料产物
```python
print(f"匹配得分: {package.match_result.score}/100")
print(f"PDF 简历路径: {package.resume_files['pdf']}")
print(f"Word 简历路径: {package.resume_files['docx']}")
print(f"综合战报路径: {package.package_report_path}")
```
*预期结果*：
1. 终端打印 5 个步骤的执行日志；
2. 在 `storage/resumes/` 目录下生成专属编译简历；
3. 在 `storage/exports/` 目录下生成综合交付战报 Markdown 文件。

---

## 📌 架构防腐与开发约束 (Rules)

1. **禁止技能间相互引用**：`skills/` 下的子模块（如 `skills/jd_matcher` 与 `skills/resume_polisher`）禁止互相 `import`。所有跨模块数据交互必须经由 `core/state.py` 中的标准契约对象流动。
2. **纯粹性原则**：`core/` 不包含任何业务 Prompt（Prompt 归属于 `skills/`），也不包含具体底层网络调用（网络请求归属于 `tools/`）。
