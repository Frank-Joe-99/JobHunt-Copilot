# 🛠️ skills/ 目录：业务专家技能层 (Expert Skill Packs)

> 本目录为 JobHunt-Copilot 的**核心业务逻辑层**。每一个子文件夹封装一个独立的求职业务场景，包含该领域的领域知识、Prompt 模板与业务调度逻辑。

> [!NOTE]
> 本目录下的 `skills.*` 为 Python 业务实现模块。面向 Codex 智能体的仓库级 Skill 声明位于 [`.agents/skills/`](../.agents/skills/)，通过 `$jobhunt-*` 触发调用并复用此处的 Python 业务逻辑。

---

## 🗂️ 业务技能模块清单

| 模块目录 | 模块定位 | 核心输入 | 核心交付物 |
| :--- | :--- | :--- | :--- |
| [`resume_generator/`](./resume_generator/README.md) | **模块 0：双格式简历排版引擎** | `UserProfile` | 镜像对齐的 Word (.docx) 与 PDF (.pdf) 双格式简历 |
| [`resume_polisher/`](./resume_polisher/README.md) | **模块 1：STAR 润色与 ATS 诊断** | 经历列表 / 目标 JD | 经历重塑报告（不捏造数据）、ATS 关键词体检报告 |
| [`job_radar/`](./job_radar/README.md) | **模块 2：批量岗位机会雷达** | 文件夹多份 JD 文本 | 契合度榜单、梯队分类（主投/冲刺/暂缓）与共性短板简报 |
| [`jd_matcher/`](./jd_matcher/README.md) | **模块 3：岗位 JD 深度穿透** | 单份 JD 文本 | 技能树重合度打分、技术缺口清单与定制自荐信草稿 |
| [`project_recommender/`](./project_recommender/README.md) | **模块 4：开源实战与短板攻坚** | 技能缺口列表 | 匹配的 GitHub 高星项目、速成路线与 STAR 转化模板 |
| [`mock_interviewer/`](./mock_interviewer/README.md) | **模块 5：场景化模拟面试官** | 目标岗位与面试官人设 | 5 阶段状态机推演问答、六维成绩单与复盘 Markdown 报告 |
| [`application_tracker/`](./application_tracker/README.md) | **模块 6：求职投递看板** | 投递记录信息 | 本地 SQLite 看板、转化漏斗分析与 7 天日程提醒 |

---

## 📐 技能包内部标准化结构

每个独立的子模块均遵循标准的三层内部组织规范：
```text
skills/<skill_name>/
├── __init__.py      # 导出公开 Handler 函数
├── prompt.py        # 领域业务提示词、系统指令、STAR 评估标准与 Few-Shot 示例
├── handler.py       # 业务执行调度器：基于 core.state 强类型入参/出参，调用 tools
└── templates/       # (可选) Typst / Word 模板文件
```

---

## 🛠️ 新增业务技能操作指南 (How to Add a Skill)

### 1. 前置条件 (Prerequisites)
- 熟悉 `core/state.py` 中的数据契约定义。
- 确认新技能不跨模块直接 `import` 现存的其他 `skills`。

---

### 2. 标准添加步骤 (Procedure)

#### 步骤 1：创建技能目录结构
在 `skills/` 下新建目录（以 `skills/salary_negotiator/` 薪资谈判辅导为例）：
```bash
mkdir skills/salary_negotiator
```

#### 步骤 2：编写业务提示词 (`prompt.py`)
在 `skills/salary_negotiator/prompt.py` 中定义业务系统提示词：
```python
NEGOTIATION_SYSTEM_PROMPT = """你是一名资深猎头与薪资谈判顾问。请根据候选人背景与当前 Offer 结构出具议价策略。"""
```

#### 步骤 3：编写业务执行入口 (`handler.py`)
在 `skills/salary_negotiator/handler.py` 中实现业务调度函数，入参与出参严格使用 Pydantic 类型：
```python
from tools.llm_client import LLMClient
from skills.salary_negotiator.prompt import NEGOTIATION_SYSTEM_PROMPT

def evaluate_offer(offer_details: dict, provider: str | None = None) -> dict:
    client = LLMClient(provider=provider)
    messages = [
        {"role": "system", "content": NEGOTIATION_SYSTEM_PROMPT},
        {"role": "user", "content": str(offer_details)},
    ]
    return client.chat_json(messages)
```

#### 步骤 4：在全局入口或 MCP 中注册
- 将新函数挂载至 `main.py` CLI 入口：`@app.command()`；
- 或在 `adapters/mcp_server.py` 中注册为 `@mcp_app.tool()`。

#### 步骤 5：运行测试验证
编写单元测试执行单模块断言：
```bash
uv run pytest tests/ -k salary_negotiator
```
