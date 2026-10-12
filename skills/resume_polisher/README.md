# ✨ skills/resume_polisher/：模块 1 简历诊断与 STAR 法则重塑

> 本模块为 JobHunt-Copilot 的**经历润色与 ATS 体检组件**。严格遵循真实性底线，基于 STAR 黄金法则重构经历亮点，并针对大厂 ATS（简历自动筛选系统）进行关键词覆盖率体检与打分。

---

## 🎯 业务定位与事实准则

解决候选人经历描述口水化、缺乏技术深度与量化产出的痛点。本模块遵循以下设计原则：

1. **STAR 结构化重塑**：
   - **S (Situation)**：项目背景与面临的技术瓶颈。
   - **T (Task)**：候选人实际承担的核心职责。
   - **A (Action)**：采取的关键技术方案、架构重构与调优动作（强化动词表现力）。
   - **R (Result)**：经实验或上线验证的量化成果。
2. **严禁虚构事实（红线）**：
   - 绝不编造未发生的指标、性能提升百分比或系统规模。
   - 缺失量化数据的部分，仅以 `[待确认：具体指标及测试基线]` 占位符提示候选人自主补充真实数据。

---

## 🏗️ 内部组件与核心 API

```text
skills/resume_polisher/
├── __init__.py            # 导出 polish_experiences 与 diagnose_ats
├── prompt.py              # STAR 润色规范、ATS 打分提示词与真实改写范例
├── handler.py             # 经历提取、大模型调度与报告生成逻辑
└── README.md              # 本说明文档
```

### 核心接口契约：
1. **`polish_experiences(profile: UserProfile | None = None, provider: str | None = None) -> ResumePolishReport`**  
   提取档案中的所有经历亮点，执行 STAR 法则深度重塑并输出对比报告。
2. **`diagnose_ats(profile: UserProfile | None = None, target_jd_text: str | None = None, provider: str | None = None) -> ATSScoreReport`**  
   评估简历针对标准大厂（或特定对标岗位 JD）的 ATS 关键词覆盖率与规范性。

---

## 🛠️ 操作与调用指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- `config/settings.yaml` 中大模型提供商已配置完备。
- 本地档案 `config/profile.yaml` 中包含至少一条实习、项目或科研经历。

---

### 2. 执行 STAR 经历润色操作

#### 步骤 1：导入接口并调用
在 Python 脚本中调用 `polish_experiences`：
```python
from skills.resume_polisher import polish_experiences

# 执行 STAR 重构分析
report = polish_experiences()
```

#### 步骤 2：遍历检查润色前后对比
```python
print(f"已完成 {len(report.items)} 条经历的 STAR 重构：\n")
for idx, item in enumerate(report.items, start=1):
    print(f"【经历 {idx} · {item.source}】")
    print(f"  原始描述: {item.original}")
    print(f"  STAR精修: {item.polished}")
    print(f"  提分原因: {item.improvement_reason}\n")
```
*预期结果*：输出润色后段落，语言符合工业界规范，缺失指标处包含占位符。

---

### 3. 执行 ATS 简历健康度体检操作

#### 步骤 1：调用体检接口
调用 `diagnose_ats`（可按需传入对标的特定 JD）：
```python
from skills.resume_polisher import diagnose_ats

# 进行通用大厂 ATS 体检
ats_report = diagnose_ats()
```

#### 步骤 2：输出体检得分与关键词缺口
```python
print(f"ATS 预估通过得分: {ats_report.ats_score} / 100")
print("已命中高频关键词:", ats_report.matched_keywords)
print("缺失关键技能词:", ats_report.missing_keywords)
print("潜在风险项:", ats_report.risk_factors)
print("针对性改进建议:")
for tip in ats_report.suggestions:
    print(" -", tip)
```
*预期结果*：返回 0 到 100 的 ATS 评分，并明确给出缺失的技术术语列表。
