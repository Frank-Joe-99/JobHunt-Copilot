# ✨ skills/resume_polisher/：模块 1 简历诊断与 STAR 法则重塑

## 🎯 业务定位与解决痛点
- **解决痛点**：
  - 应届生写项目或实习经历常常是“流水账”，只会写“负责某某模块的开发与测试”，缺乏技术深度与商业认知；
  - 缺乏量化数据支撑，无法体现实际业务价值；
  - 未针对大厂 HR 的 ATS（Applicant Tracking System）筛选机制进行关键词埋点。
- **本模块职责**：
  - 对用户的原始经历文本进行全面健康体检与评分；
  - 严格依据 **STAR 黄金法则**（Situation 背景、Task 目标、Action 核心行动、Result 成果数据）重构每一条履历；
  - 剔除无意义副词，增强动词表现力，补充合理的量化指标框架。

---

## 📐 STAR 重构范式
```text
【改造前 (普通学生写法)】：
参与学校教务系统重构，负责选课模块开发，使用了 Redis 缓存，系统运行稳定。

【改造后 (工业界 STAR 重塑)】：
- 【背景与挑战】针对选课高峰期高并发并发写入导致的数据库连接池耗尽与锁超时问题（Situation/Task）；
- 【技术方案】设计基于 Redis Lua 脚本的令牌桶分布式限流策略与热点数据多级缓存方案，重写选课扣减逻辑（Action）；
- 【量化成效】支撑全校 3 万名学生并发选课，核心接口响应时间由 850ms 降至 65ms (提升 92%)，零超卖事故发生（Result）。
```

---

## 📂 模块结构与实现现状
```text
skills/resume_polisher/
├── __init__.py            # 导出 polish_experiences 与 diagnose_ats
├── prompt.py              # STAR 润色 Prompt、ATS 打分规范、Few-Shot 优质示例
├── handler.py             # 核心逻辑：诊断经历、调用 LLM 润色、生成对比修改报告
└── README.md
```

---

## 📥 核心 API 规范

### 1. `polish_experiences(...)`
```python
def polish_experiences(
    profile: UserProfile | None = None,
    provider: str | None = None,
) -> ResumePolishReport:
    """提取 profile 中的所有亮点经历，调用大模型按 STAR 法则重构提炼并输出对比报告"""
```

### 2. `diagnose_ats(...)`
```python
def diagnose_ats(
    profile: UserProfile | None = None,
    target_jd_text: str | None = None,
    provider: str | None = None,
) -> ATSScoreReport:
    """针对候选人画像（及可选的目标岗位 JD）进行 ATS 关键词命中与通过率诊断"""
```

### 核心数据契约：
- **`ResumePolishReport`**：
  - `items: list[PolishedItem]`（包含 `original`, `polished`, `reasoning`, `metrics_hint`）
  - `overall_advice: str`（综合改进建议）
- **`ATSScoreReport`**：
  - `score: int`（ATS 预估通过分 0~100）
  - `matched_keywords: list[str]`（已命中关键词）
  - `missing_keywords: list[str]`（缺失高频关键词）
  - `risk_factors: list[str]`（潜在风险点）
  - `suggestions: list[str]`（针对性改进行动项）

---

## 🚀 极简调用示例

```python
from skills.resume_polisher import polish_experiences, diagnose_ats

# 1. 执行 STAR 经历润色
report = polish_experiences()
print(f"共润色 {len(report.items)} 条核心经历：")
for item in report.items[:2]:
    print("【原句】:", item.original)
    print("【STAR精修】:", item.polished)
    print("【修改理由】:", item.reasoning)

# 2. 执行 ATS 诊断
ats = diagnose_ats()
print(f"ATS 预估评分: {ats.score} / 100")
```
