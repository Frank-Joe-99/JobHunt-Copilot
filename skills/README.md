# 🛠️ skills/ 目录：业务技能层 (Expert Skill Packs)

`skills/` 是本系统的**“专家业务顾问群”**。每一个子文件夹对应一个具体的求职业务场景，内部高度内聚了该领域的**行业方法论、专业 Prompt 模板与业务执行逻辑**。

---

## 📐 单个 Skill 内部规范 (即插即用设计)

每个独立的 Skill 文件夹均遵循统一的标准化内部结构：

```text
skills/example_skill/
├── __init__.py
├── prompt.py       # 该业务领域的专业提示词库、STAR 标准、Few-Shot 范例
├── handler.py      # 业务执行入口函数：入参/出参基于 core.state 强类型，调用 tools 与 LLM
└── templates/      # (可选) 若涉及前端/排版渲染，存放 jinja2 / typst 模板文件
```

---

## 🗂️ 核心模块清单

| 模块目录 | 对应功能 | 核心交付物 |
| :--- | :--- | :--- |
| [`resume_generator/`](./resume_generator/README.md) | **模块 0：本地简历排版引擎** | 基于 Typst 与 python-docx，一键同时导出 A4 严密排版的 **Word (.docx) + PDF (.pdf)** 双版本 |
| [`resume_polisher/`](./resume_polisher/README.md) | **模块 1：STAR 法则润色与诊断** | 经历深度重塑、ATS 关键词分析、量化指标提取 |
| [`job_radar/`](./job_radar/README.md) | **模块 2：全网校招岗位雷达** | 每日/每周校招新发岗位语义聚合与推荐简报 |
| [`jd_matcher/`](./jd_matcher/README.md) | **模块 3：目标岗位 JD 深度穿透** | 技能树重合度雷达分析、量身定制自荐信与定制简历建议 |
| [`project_recommender/`](./project_recommender/README.md) | **模块 4：开源实战与技能补短板** | GitHub 练手开源项目推荐、经历转 STAR 写作模板 |
| [`mock_interviewer/`](./mock_interviewer/README.md) | **模块 5：AI 场景化模拟面试官** | 多轮追问交互状态机、面试复盘体检报告 |
| [`application_tracker/`](./application_tracker/README.md) | **模块 6：求职投递看板** | 本地投递生命周期追踪、笔面试时间备忘 |

---

## 🔌 如何添加一个新技能？（3 步极简扩展）

当你想新增一个场景（如：`skills/assessment_prep/` 校招性格测试辅导）：
1. 在 `skills/` 下新建目录 `assessment_prep/`；
2. 编写 `prompt.py`（封装测评维度规则）与 `handler.py`（执行测评题诊断）；
3. 在 `core/workflow.py` 或 `adapters/mcp_server.py` 中直接导入并注册。
👉 **整个过程对已有代码零侵入、零污染！**
