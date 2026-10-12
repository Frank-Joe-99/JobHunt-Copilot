# 🚀 skills/project_recommender/：模块 4 开源实战推荐与技能补短板

> 本模块为 JobHunt-Copilot 的**技能短板攻坚与开源实战推荐引擎**。针对岗位比对发现的技能缺口，检索 GitHub 高价值开源项目，制定 1-2 周速成路线，并提供项目实际完成后如何梳理亮点的 STAR 简历撰写模板。

---

## 🎯 业务定位与推荐准则

解决候选人发现技术栈与岗位存在差距后，不知道学什么项目、如何高效上手、如何体现到简历中的痛点。

### 项目筛选原则：
1. **适中体量**：筛选代码架构清晰、非天文级规模的项目，确保应届生可在 1~2 周内跑通核心代码并掌握关键机制。
2. **工业级技术栈**：紧扣大厂高频考点（如：分布式锁、消息队列轻量实现、高性能 KV、语义缓存等）。
3. **真实性提示**：模块生成的简历 STAR 范文为**待完成后的写作参考模板**，严禁将未实际运行或未学习的项目直接作为已完成成果写入简历。

---

## 🏗️ 内部组件与核心 API

```text
skills/project_recommender/
├── __init__.py            # 导出 recommend_projects 与 recommend_projects_report
├── prompt.py              # 项目智能筛选与学习路线制定提示词
├── handler.py             # 核心逻辑：提取关键词 -> GitHub 检索去重 -> LLM 筛选与建议
└── README.md              # 本说明文档
```

### 核心接口契约：
1. **`recommend_projects(skills_gaps: list[SkillGap], language: str | None = "python", provider: str | None = None) -> list[ProjectRecommendation]`**  
   直接返回精选的开源项目推荐列表。
2. **`recommend_projects_report(skills_gaps: list[SkillGap], language: str | None = "python", provider: str | None = None) -> ProjectRecommendationReport`**  
   返回包含整体概述与项目详情的完整报告实体。

---

## 🛠️ 操作与调用指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- `config/settings.yaml` 中大模型提供商已配置完备。
- 可选配置 `github.token` 以提升 GitHub API 请求配额。

---

### 2. 执行开源项目推荐操作

#### 步骤 1：构造技能缺口列表
定义需要补强的短板技能清单（通常由 `jd_matcher` 自动生成）：
```python
from core.state import SkillGap
from skills.project_recommender import recommend_projects_report

# 构造短板列表
gaps = [
    SkillGap(skill="Redis 分布式缓存", status="missing", suggestion="需补充高并发缓存实战"),
    SkillGap(skill="Kafka 消息队列", status="missing", suggestion="需掌握削峰填谷模型"),
]
```

#### 步骤 2：调用推荐接口
执行推荐流程，可指定主力语言偏好：
```python
report = recommend_projects_report(skills_gaps=gaps, language="python")
```

#### 步骤 3：查看并输出推荐成果
遍历并输出推荐项目详情：
```python
print("推荐综述:", report.overview)
for idx, item in enumerate(report.recommendations, start=1):
    print(f"\n【推荐项目 {idx}】{item.repo_name} (⭐ {item.stars})")
    print(f"  项目链接: {item.repo_url}")
    print(f"  推荐理由: {item.why_recommended}")
    print(f"  攻坚路径: {item.learning_path}")
    print(f"  面试高频考点: {item.interview_tips}")
    print(f"  待完成后的简历范文:\n  {item.star_resume_sample}")
```
*预期结果*：
- 返回 2~4 个 GitHub 开源项目；
- 每个项目提供明确的上手步骤与面试考察要点。
