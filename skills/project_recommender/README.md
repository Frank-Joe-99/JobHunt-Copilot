# 🚀 skills/project_recommender/：模块 4 技能缺口分析与 GitHub 开源实战推荐

## 🎯 业务定位与解决痛点
- **解决痛点**：
  - 应届生如果投递心仪大厂，发现自己的技术栈和项目经历与 JD 存在一定差距（例如缺少 Docker、MQ、分布式经验），但距离秋招/面试还有 1~3 个月准备时间；
  - 想做项目提升，却不知道去哪找优质、适合应届生练手、且能在面试中讲出亮点的开源项目；
  - 即使做完了项目，不知道如何将开源实战以专业规范的语言转化为简历上的亮点。
- **本模块职责**：
  - 承接 `skills/jd_matcher` 计算出的“缺失关键技能清单 (Skill Gaps)”；
  - 调用 GitHub API 过滤并检索高契合度的开源练手项目（按 Stars、最近更新、语言、Issue 活跃度综合排序）；
  - 针对筛选出的项目，生成针对性的“实战学习路径”；
  - 提供**“如何将该开源项目转化为简历 STAR 经历”**的标准示例文本。
  - 调用 `tools/github_client.py` 过滤并检索高契合度的开源练手项目（按 Stars、最近更新、语言、技术栈综合排序）；
  - 借助大模型智能评估，挑选最具实战价值的项目，生成精确到文件的“极简速成路径”；
  - 提供**“如何将该开源项目转化为简历 STAR 经历”**的标准工业级示例文本，可直接复制进简历。

---

## 🔍 项目推荐与筛选标准
1. **适中体量**：非 Linux 内核等天文级项目，代码结构清晰，应届生可在 1~2 周内跑通并掌握核心模块。
2. **工业级技术栈**：深度包含当前互联网/软件工业界高频考点（如：基于 Go 的轻量级 KV 存储、基于 Python 的 RAG 智能问答系统）。
2. **工业级技术栈**：深度包含当前互联网工业界高频考点（如：基于 Redis 的轻量队列、基于 Python 的语义缓存与 RAG 问答）。
3. **输出转换模板**：直接教会学生如何在面试官面前讲清楚“你为什么做这个项目、解决了什么问题、学到了什么底层原理”。

---

## 📂 预期内部结构
## 📂 模块结构与实现现状
```text
skills/project_recommender/
├── __init__.py
├── prompt.py              # 开源项目价值提取 Prompt、简历 STAR 转化 Prompt
├── handler.py             # 核心逻辑：获取缺口 -> 调用 GitHub Client 搜索 -> 筛选与产出转化文案
├── __init__.py            # 包标记文件
├── prompt.py              # PROJECT_EVAL_SYSTEM 评估与 STAR 转化提示词
├── handler.py             # 核心调度逻辑：核心词提炼 -> GitHub 搜索去重 -> LLM 筛选与 STAR 转化
└── README.md
```

## 📥 输入与输出契约
- **输入**：`List[SkillGap]`（缺失技能清单） + 求职专业方向。
- **输出**：`List[ProjectRecommendation]`（包含：Repo 名称、链接、技术栈、核心亮点、推荐练手模块、简历描述示范）。
- **主入口函数**：`recommend_projects(skills_gaps: list[SkillGap], language: str | None = "python", provider: str | None = None) -> list[ProjectRecommendation]`
- **完整报告函数**：`recommend_projects_report(...) -> ProjectRecommendationReport`
- **输出实体**：`ProjectRecommendation`（包含 `repo_name`, `repo_url`, `stars`, `language`, `why_recommended`, `learning_path`, `interview_tips`, `star_resume_sample`）。

---

## 🚀 独立调用与验证命令

```powershell
uv run python -c "
from core.state import SkillGap
from skills.project_recommender.handler import recommend_projects
gaps = [
    SkillGap(skill='分布式缓存 Redis', status='missing', suggestion='建议了解多级缓存设计'),
    SkillGap(skill='消息队列 Kafka', status='partial', suggestion='建议深化生产者消费者模型'),
]
recs = recommend_projects(gaps, language='python')
for r in recs:
    print(f'[{r.repo_name}] ({r.stars} stars)')
    print('  推荐理由:', r.why_recommended[:60], '...')
    print('  简历范文:', r.star_resume_sample[:60], '...')
"
```
