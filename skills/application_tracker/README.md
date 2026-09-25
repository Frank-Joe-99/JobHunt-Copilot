# 📋 skills/application_tracker/：求职投递看板与时间线日程管理

## 🎯 业务定位与解决痛点

- **解决痛点**：
  - 秋招/春招旺季，应届生往往投递了 50~100+ 家公司，用普通记事本容易记混各家网申状态；
  - 经常搞错笔试时间、面试预约冲突、不知道某家公司目前处于初试还是复试阶段；
  - 缺乏对个人求职投递漏斗（网申量、进面率、Offer 转化率）的客观数据复盘。
- **本模块职责**：
  - 基于本地轻量数据库（SQLite，私密无云端泄露），管理求职全流程的投递生命周期；
  - 记录企业名称、投递岗位、投递日期、当前状态、笔试/面试日程、薪资待遇预期与跟进备注；
  - 提供近期 3~7 天面试/笔试日程提醒及倒计时；
  - 提供全流程投递漏斗转化率统计（网申量、进面率、Offer 率、在途流程数）；
  - 深度联动 `core/workflow.py`，每次一键定向定制生成简历时自动登记归档入库。

---

## 📊 投递阶段流转状态机

```text
[⭐ 意向备选 (wishlist)]
        │
        ▼
  [📨 已网申 (applied)] ────────────────┐
        │                               │
        ▼                               │
[📝 笔试测评 (assessment)]              ▼
        │                        [❌ 已淘汰 (rejected)]
        ▼                               ▲
 [🎯 技术一面 (interview_1)]            │
        │                               │
        ▼                               │
 [🔥 技术复试 (interview_2)]            │
        │                               │
        ▼                               │
  [🤝 HR谈薪 (hr_stage)] ───────────────┘
        │
        ▼
  [🎉 录用Offer (offer)]
        │
        ▼
  [⏹ 已放弃/结束 (closed)]
```

---

## 📂 模块内部结构

```text
skills/application_tracker/
├── __init__.py           # 模块门面函数导出
├── database.py           # 原生 SQLite 连接管理 (WAL 模式)、自动建表与索引
├── handler.py            # 业务调度器：增删改查、状态变迁、日程筛选、漏斗分析
└── README.md             # 本技术文档
```

---

## 🔑 核心数据契约 (`core/state.py`)

- `ApplicationStatus`：状态枚举 (`wishlist`, `applied`, `assessment`, `interview_1`, `interview_2`, `hr_stage`, `offer`, `rejected`, `closed`)
- `ApplicationRecord`：投递主记录模型（含 ID、企业、岗位、状态、日程、备注流水）
- `UpcomingScheduleEvent`：近期待办日程事件（含倒计时天数计算）
- `ApplicationFunnelStats`：全流程转化漏斗统计分析（总数、正式投递、进面数、Offer数、进面率、Offer率）

---

## 🚀 核心 Python API

```python
from skills.application_tracker import (
    add_application,
    update_status,
    get_application,
    list_applications,
    delete_application,
    get_upcoming_schedules,
    get_funnel_analytics,
)
from core.state import ApplicationStatus

# 1. 登记新投递
rec = add_application(
    company="字节跳动",
    role="基础架构平台开发工程师",
    status=ApplicationStatus.APPLIED,
    salary_range="25k~35k*16",
    location="北京",
    note="官网校招投递，绑定定制简历",
)

# 2. 状态推进与日程预约
update_status(
    record_id=rec.id,
    status=ApplicationStatus.INTERVIEW_1,
    next_schedule_time="2026-09-28 14:00",
    next_schedule_notes="飞书会议 123-456-789",
    note="收到 HR 面试邀约",
)

# 3. 查询未来 7 天待办面试日程
events = get_upcoming_schedules(days_ahead=7)
for e in events:
    print(f"[{e.schedule_time}] {e.company} {e.role} (倒计时 {e.days_left} 天): {e.notes}")

# 4. 获取投递转化漏斗统计
funnel = get_funnel_analytics()
print(f"投递: {funnel.applied_count}, 进面: {funnel.interview_count} (进面率: {funnel.interview_rate}%), Offer: {funnel.offer_count}")
```
