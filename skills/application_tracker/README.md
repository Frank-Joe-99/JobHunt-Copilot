# 📋 skills/application_tracker/：模块 6 求职投递看板与时间线日程管理

> 本模块为 JobHunt-Copilot 的**投递全生命周期跟踪与日程管理系统**。基于本地原生 SQLite 数据库（WAL 模式），离线记录求职进度、笔面试日程，并提供全流程漏斗转化分析。

---

## 🎯 业务定位与解决痛点

解决多线求职过程中投递记录混乱、笔面试日程容易撞车遗忘、缺乏数据复盘依据的痛点。

### 核心功能指标：
- **本地安全**：数据存储于本地 SQLite（`storage/tracker.db`），杜绝简历流向与日程信息的云端泄露。
- **阶段流转跟踪**：记录投递企业、岗位、薪资预期、面试时间备忘及复盘笔记。
- **转化漏斗分析**：自动统计投递总数、有效投递量、进面率（%）与 Offer 转化率（%）。
- **待办日程提醒**：检索未来 7 天内待办笔试与面试，提供时间倒计时。
- **自动联动归档**：执行 `jobhunt tailor` 定制简历时，可自动建档沉淀入库。

---

## 📊 投递阶段流转状态机

```text
[⭐ 意向备选 (wishlist)]
        │
        ▼
   [📨 已网申 (applied)] ────────────────┐
        │                                │
        ▼                                │
 [📝 笔试测评 (assessment)]              ▼
        │                         [❌ 已淘汰 (rejected)]
        ▼                                ▲
  [🎯 技术一面 (interview_1)]            │
        │                                │
        ▼                                │
  [🔥 技术复试 (interview_2)]            │
        │                                │
        ▼                                │
   [🤝 HR谈薪 (hr_stage)] ───────────────┘
        │
        ▼
   [🎉 录用Offer (offer)]
        │
        ▼
   [⏹ 流程关闭 (closed)]
```

---

## 🏗️ 内部组件与核心 API

```text
skills/application_tracker/
├── __init__.py           # 导出看板 CRUD、日程与漏斗分析函数
├── database.py           # 原生 SQLite 连接管理 (WAL 模式)、自动建表与索引
├── handler.py            # 业务调度逻辑：增删改查、阶段迁移、日程筛选与漏斗统计
└── README.md             # 本说明文档
```

---

## 🛠️ 操作与管理指南 (Procedures)

### 1. 前置条件 (Prerequisites)
- 位于项目根目录下（数据库 `storage/tracker.db` 会在初次操作时自动建表并激活 WAL 模式）。

---

### 2. 通过 CLI 命令行管理看板

#### 步骤 1：查看投递全景与漏斗看板
在终端中执行下列命令查看当前投递汇总：
```bash
uv run jobhunt tracker
```
*预期结果*：终端打印当前转化漏斗（投递量、进面率、Offer率）与所有进行中的投递列表。

#### 步骤 2：登记新投递记录
使用 `tracker add` 子命令录入投递信息：
```bash
uv run jobhunt tracker add \
  --company "字节跳动" \
  --role "后端开发工程师" \
  --status applied \
  --location "北京" \
  --salary "25-35K*16" \
  --note "官网秋招投递，关联定制简历"
```

#### 步骤 3：推进阶段状态并预约面试
使用 `tracker update` 子命令更新已有记录（通过 Record ID）：
```bash
uv run jobhunt tracker update 1 \
  --status interview_1 \
  --schedule "2026-10-25 14:00" \
  --notes "飞书会议号 123-456-789" \
  --note "收到技术一面邀约"
```

#### 步骤 4：查询待办面试日程
查询未来 7 天内的面试/笔试提醒：
```bash
uv run jobhunt tracker schedules --days 7
```
*预期结果*：终端按时间升序列出未来待办事件，并标明倒计时天数。

---

### 3. 通过 Python API 调用操作

```python
from core.state import ApplicationStatus
from skills.application_tracker import (
    add_application,
    update_status,
    get_funnel_analytics,
    get_upcoming_schedules,
)

# 1. 登记新申请
record = add_application(
    company="腾讯",
    role="后台研发",
    status=ApplicationStatus.APPLIED,
    salary_range="20-25K",
    location="深圳",
    note="官网网申",
)

# 2. 状态推进并预约二面
update_status(
    record_id=record.id,
    status=ApplicationStatus.INTERVIEW_2,
    next_schedule_time="2026-10-28 15:30",
    next_schedule_notes="腾讯会议 987-654-321",
    note="一面通过，预约总监复试",
)

# 3. 获取漏斗转化率
funnel = get_funnel_analytics()
print(f"投递数: {funnel.applied_count}, 进面数: {funnel.interview_count}")
print(f"进面率: {funnel.interview_rate}%, Offer数: {funnel.offer_count}")

# 4. 获取待办日程
schedules = get_upcoming_schedules(days_ahead=7)
for event in schedules:
    print(f"[{event.schedule_time}] {event.company} - {event.role} (还剩 {event.days_left} 天)")
```
