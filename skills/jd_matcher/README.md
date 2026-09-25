# 🎯 skills/jd_matcher/：模块 3 目标岗位 JD 深度穿透与定制建议

## 🎯 业务定位与解决痛点
- **解决痛点**：
  - “一份简历海投走天下”导致命中率极低。不同公司虽然岗位名称类似，但底层技术栈侧重截然不同（例如同为后端：A 公司侧重高并发分布式，B 公司侧重微服务业务流）；
  - 缺乏对企业 JD（Job Description）潜台词的精准理解，无法提炼关键技术词汇。
- **本模块职责**：
  - 解析用户提供的目标岗位 JD 文本；
  - 深度提取该岗位的硬性门槛要求、核心技术栈、加分项与软实力偏好；
  - 与用户主档案 (`profile.yaml`) 进行多维比对，输出匹配度评分与技能差距清单；
  - 给出针对该特定岗位的简历定制修改建议与专属求职自荐信（Cover Letter）。

---

## 📊 输出分析维度
1. **技能树匹配度得分 (0-100)**：基础技能符合率、加分项覆盖率。
2. **缺失关键技能清单 (Skill Gaps)**：目标岗位强烈要求但用户档案中未体现的内容。
3. **简历定制调优策略**：
   - 应该把哪一个项目置顶突出？
   - 应该强化哪些关键词（如补充说明项目中对 Redis、Kafka 的运用）？
4. **一键生成高匹配自荐信**：针对该团队业务痛点量身打造的自荐文案。

---

## 📂 模块结构与实现现状
```text
skills/jd_matcher/
├── __init__.py            # 导出 parse_jd, match_profile_with_jd, analyze_jd
├── prompt.py              # JD 关键实体提取 Prompt、契合度比对 Prompt、自荐信模板
├── handler.py             # 核心逻辑：解析 JD、穿透比对画像、生成匹配结果与自荐信
└── README.md
```

---

## 📥 核心 API 规范

### 1. `parse_jd(...)`
```python
def parse_jd(
    jd_text: str,
    provider: str | None = None,
) -> JobDescription:
    """提取 JD 中的企业名称、岗位名称、硬性门槛、加分项与技术关键词"""
```

### 2. `match_profile_with_jd(...)`
```python
def match_profile_with_jd(
    profile: UserProfile,
    jd: JobDescription,
    provider: str | None = None,
) -> MatchResult:
    """对比个人画像与目标岗位，计算契合度得分、已匹配技能、缺失短板与微调建议"""
```

### 3. `analyze_jd(...)` (统一门面便捷接口)
```python
def analyze_jd(
    jd_text: str,
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> MatchResult:
    """端到端门面函数：解析 JD 并直接与当前 profile 深度穿透比对"""
```

### 核心数据契约：
- **`MatchResult`**：
  - `score: int`（契合度综合评分 0~100）
  - `matched_skills: list[MatchedSkill]`（已吻合技能及对应佐证经历）
  - `missing_skills: list[SkillGap]`（缺失技能短板及补强建议）
  - `resume_tuning_advice: list[str]`（针对该 JD 的简历置顶与微调建议）
  - `overview: str`（综合评语分析）
  - `cover_letter: str`（针对目标岗位的定制求职自荐信草稿）

---

## 🚀 极简调用示例

```python
from skills.jd_matcher import analyze_jd

jd_content = """
【字节跳动】后端开发工程师（基础架构）
职责：负责分布式存储与自研 KV 系统的研发，保障高可用与高吞吐。
要求：精通 Go/C++ 或 Python，深入理解 Raft/Paxos 协议，熟悉 Redis 核心机制与性能调优。
"""

result = analyze_jd(jd_content)
print(f"匹配得分: {result.score} / 100")
print("契合技能:", [s.skill for s in result.matched_skills])
print("短板技能:", [s.skill for s in result.missing_skills])
print("\n简历微调建议:")
for advice in result.resume_tuning_advice:
    print(" -", advice)
```
