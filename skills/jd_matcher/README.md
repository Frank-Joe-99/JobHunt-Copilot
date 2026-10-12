# 🎯 skills/jd_matcher/：模块 3 目标岗位 JD 深度穿透与定制建议

> 本模块为 JobHunt-Copilot 的**人岗匹配分析引擎**。通过对目标招聘岗位 JD 执行语义穿透，提炼硬性技术门槛与隐性加分项，并与候选人主档案进行多维对比，输出契合度评分、短板缺口及针对性的自荐信草稿。

---

## 🎯 业务定位与分析维度

解决候选人“一份简历海投走天下”命中率低的问题。模块深入解析岗位深层技术诉求，输出四维诊断结果：

| 分析维度 | 输出内容 | 业务价值 |
| :--- | :--- | :--- |
| **契合度综合评分 (0-100)** | 基于必备项与加分项覆盖率的量化打分 | 辅助决策是否应当投递本岗位 |
| **已吻合优势技能清单** | 命中的技术点与档案中佐证经历段落的映射 | 确定面试中需重点突出的优势武器 |
| **短板缺口技能清单 (Skill Gaps)** | 目标岗位强要求但档案中缺失的技术栈 | 输入至 `project_recommender` 触发开源项目补强 |
| **简历定向微调建议** | 针对该 JD 建议置顶的项目与关键技术词 | 指导简历排版针对性调优 |
| **专属定制自荐信草稿** | 结合候选人经历量身定制的沟通开场白 | 可直接复制至招聘平台或邮件附言 |

---

## 🏗️ 内部组件与核心 API

```text
skills/jd_matcher/
├── __init__.py            # 导出 parse_jd, match_profile_with_jd, analyze_jd
├── prompt.py              # JD 实体抽取与人岗契合度分析系统提示词
├── handler.py             # 核心业务调度实现
└── README.md              # 本说明文档
```

### 核心接口契约：
1. **`parse_jd(jd_text: str, provider: str | None = None) -> JobDescription`**  
   解析 JD 文本，提取企业名称、岗位名称、硬性门槛与加分项。
2. **`match_profile_with_jd(profile: UserProfile, jd: JobDescription, provider: str | None = None) -> MatchResult`**  
   对比内存档案与已解析的岗位画像，执行技术契合度打分。
3. **`analyze_jd(jd_text: str, profile: UserProfile | None = None, provider: str | None = None) -> MatchResult`**  
   端到端门面接口：自动解析并完成画像深度比对。

---

## 🛠️ 操作与调用指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- `config/settings.yaml` 中已配置有效的大模型 API 凭证。
- 本地档案 `config/profile.yaml` 存在且格式正确（若调用时不显式传入 `profile`，系统将自动读取）。

---

### 2. 执行岗位 JD 穿透分析操作

#### 步骤 1：导入接口
在 Python 脚本中引入 `analyze_jd` 门面函数：
```python
from skills.jd_matcher import analyze_jd
```

#### 步骤 2：准备目标岗位 JD 文本
定义或读取目标岗位的招聘 JD 纯文本：
```python
jd_content = """
【字节跳动】后端开发工程师（基础架构）
职责：负责分布式存储与自研 KV 系统的研发，保障高可用与高吞吐。
要求：精通 Go/C++ 或 Python，深入理解 Raft/Paxos 协议，熟悉 Redis 核心机制与性能调优。
"""
```

#### 步骤 3：调用分析函数
执行穿透匹配并接收 `MatchResult` 强类型实体：
```python
result = analyze_jd(jd_content)
```

#### 步骤 4：验证并处理输出结果
打印契合度得分、技术短板及自荐信：
```python
print(f"契合度得分: {result.score} / 100")
print("已吻合技能:", [s.skill for s in result.matched_skills])
print("技术短板:", [g.skill for g in result.missing_skills])
print("\n简历微调建议:")
for advice in result.resume_tuning_advice:
    print(" -", advice)
print("\n定制自荐信草稿:\n", result.cover_letter_draft)
```
*预期结果*：
- 契合度得分返回 0 到 100 的整数；
- 成功提取出缺失技术项（例如 Raft 协议）；
- 自荐信草稿生成完毕，无格式异常。
