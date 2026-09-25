"""
求职投递看板与日程管理业务调度器 (Application Tracker Handler)
提供求职生命周期全流程跟踪、面试/笔试日程提醒及投递转化漏斗统计分析。
"""

import json
from datetime import datetime, date
from pathlib import Path
from typing import Any

from core.state import (
    ApplicationStatus,
    ApplicationRecord,
    UpcomingScheduleEvent,
    ApplicationFunnelStats,
)
from skills.application_tracker.database import get_db_connection


def _row_to_record(row: Any) -> ApplicationRecord:
    """将 SQLite 行数据映射为 ApplicationRecord 实体"""
    notes_list: list[str] = []
    if row["notes_json"]:
        try:
            notes_list = json.loads(row["notes_json"])
        except Exception:
            notes_list = [row["notes_json"]]

    status_val = row["status"]
    # 容错处理枚举值
    try:
        app_status = ApplicationStatus(status_val)
    except ValueError:
        app_status = ApplicationStatus.APPLIED

    return ApplicationRecord(
        id=row["id"],
        company=row["company"],
        role=row["role"],
        status=app_status,
        salary_range=row["salary_range"],
        location=row["location"],
        apply_date=row["apply_date"],
        next_schedule_time=row["next_schedule_time"],
        next_schedule_notes=row["next_schedule_notes"],
        resume_path=row["resume_path"],
        notes=notes_list,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def add_application(
    company: str,
    role: str,
    status: ApplicationStatus | str = ApplicationStatus.APPLIED,
    salary_range: str | None = None,
    location: str | None = None,
    apply_date: str | None = None,
    next_schedule_time: str | None = None,
    next_schedule_notes: str | None = None,
    resume_path: str | None = None,
    note: str | None = None,
    db_path: Path | str | None = None,
) -> ApplicationRecord:
    """
    登记一条新的求职投递记录。
    """
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    today_str = now.strftime("%Y-%m-%d")
    final_apply_date = apply_date or today_str

    status_str = status.value if isinstance(status, ApplicationStatus) else str(status)

    notes_list: list[str] = []
    if note:
        notes_list.append(f"[{now_str}] 投递登记: {note.strip()}")
    else:
        notes_list.append(f"[{now_str}] 投递登记")

    notes_json = json.dumps(notes_list, ensure_ascii=False)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO applications (
                company, role, status, salary_range, location,
                apply_date, next_schedule_time, next_schedule_notes,
                resume_path, notes_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                company.strip(),
                role.strip(),
                status_str,
                salary_range.strip() if salary_range else None,
                location.strip() if location else None,
                final_apply_date.strip(),
                next_schedule_time.strip() if next_schedule_time else None,
                next_schedule_notes.strip() if next_schedule_notes else None,
                str(resume_path).strip() if resume_path else None,
                notes_json,
                now_str,
                now_str,
            ),
        )
        record_id = cursor.lastrowid
        conn.commit()

        cursor.execute("SELECT * FROM applications WHERE id = ?;", (record_id,))
        row = cursor.fetchone()
        return _row_to_record(row)


def get_application(record_id: int, db_path: Path | str | None = None) -> ApplicationRecord | None:
    """根据 ID 获取投递详情"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM applications WHERE id = ?;", (record_id,))
        row = cursor.fetchone()
        return _row_to_record(row) if row else None


def update_status(
    record_id: int,
    status: ApplicationStatus | str | None = None,
    next_schedule_time: str | None = None,
    next_schedule_notes: str | None = None,
    salary_range: str | None = None,
    location: str | None = None,
    note: str | None = None,
    clear_schedule: bool = False,
    db_path: Path | str | None = None,
) -> ApplicationRecord | None:
    """
    推进求职阶段、更新面试日程或追加流转备注。
    """
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    existing = get_application(record_id, db_path=db_path)
    if not existing:
        return None

    updated_notes = list(existing.notes)
    status_changed = False
    new_status_str = existing.status.value

    if status is not None:
        target_status_str = status.value if isinstance(status, ApplicationStatus) else str(status)
        if target_status_str != existing.status.value:
            status_changed = True
            new_status_str = target_status_str
            old_label = existing.status.label
            try:
                new_label = ApplicationStatus(target_status_str).label
            except ValueError:
                new_label = target_status_str
            updated_notes.append(f"[{now_str}] 阶段变更: {old_label} ➔ {new_label}")

    if note:
        updated_notes.append(f"[{now_str}] 备注: {note.strip()}")

    # 日程更新
    final_schedule_time = existing.next_schedule_time
    final_schedule_notes = existing.next_schedule_notes
    if clear_schedule:
        final_schedule_time = None
        final_schedule_notes = None
    else:
        if next_schedule_time is not None:
            final_schedule_time = next_schedule_time.strip() if next_schedule_time else None
        if next_schedule_notes is not None:
            final_schedule_notes = next_schedule_notes.strip() if next_schedule_notes else None

    final_salary = salary_range.strip() if salary_range is not None else existing.salary_range
    final_location = location.strip() if location is not None else existing.location

    notes_json = json.dumps(updated_notes, ensure_ascii=False)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE applications
            SET status = ?, salary_range = ?, location = ?,
                next_schedule_time = ?, next_schedule_notes = ?,
                notes_json = ?, updated_at = ?
            WHERE id = ?;
            """,
            (
                new_status_str,
                final_salary,
                final_location,
                final_schedule_time,
                final_schedule_notes,
                notes_json,
                now_str,
                record_id,
            ),
        )
        conn.commit()
        cursor.execute("SELECT * FROM applications WHERE id = ?;", (record_id,))
        row = cursor.fetchone()
        return _row_to_record(row) if row else None


def delete_application(record_id: int, db_path: Path | str | None = None) -> bool:
    """删除指定的投递记录"""
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM applications WHERE id = ?;", (record_id,))
        conn.commit()
        return cursor.rowcount > 0


def list_applications(
    status: ApplicationStatus | str | None = None,
    keyword: str | None = None,
    limit: int = 100,
    db_path: Path | str | None = None,
) -> list[ApplicationRecord]:
    """
    按状态、关键词查询投递记录列表，按更新时间倒序排列。
    """
    query = "SELECT * FROM applications WHERE 1=1"
    params: list[Any] = []

    if status:
        status_str = status.value if isinstance(status, ApplicationStatus) else str(status)
        query += " AND status = ?"
        params.append(status_str)

    if keyword:
        kw_pattern = f"%{keyword.strip()}%"
        query += " AND (company LIKE ? OR role LIKE ? OR location LIKE ?)"
        params.extend([kw_pattern, kw_pattern, kw_pattern])

    query += " ORDER BY updated_at DESC LIMIT ?;"
    params.append(limit)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [_row_to_record(r) for r in rows]


def get_upcoming_schedules(
    days_ahead: int = 7,
    db_path: Path | str | None = None,
) -> list[UpcomingScheduleEvent]:
    """
    获取未来若干天内（默认 7 天）以及近 3 天未关闭的笔试/面试日程提醒。
    按时间先后升序排列。
    """
    today = date.today()

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, company, role, status, next_schedule_time, next_schedule_notes
            FROM applications
            WHERE next_schedule_time IS NOT NULL AND next_schedule_time != ''
            AND status NOT IN ('offer', 'rejected', 'closed');
        """)
        rows = cursor.fetchall()

    events: list[UpcomingScheduleEvent] = []

    for r in rows:
        schedule_str = r["next_schedule_time"].strip()
        # 尝试解析日期部分 (支持 YYYY-MM-DD 或 YYYY-MM-DD HH:MM)
        date_part_str = schedule_str.split()[0]
        try:
            event_date = datetime.strptime(date_part_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        days_left = (event_date - today).days

        # 包含近 3 天前（未处理日程）以及未来指定天数之内的日程
        if -3 <= days_left <= days_ahead:
            try:
                st = ApplicationStatus(r["status"])
            except ValueError:
                st = ApplicationStatus.APPLIED

            events.append(
                UpcomingScheduleEvent(
                    record_id=r["id"],
                    company=r["company"],
                    role=r["role"],
                    status=st,
                    schedule_time=schedule_str,
                    notes=r["next_schedule_notes"] or "",
                    days_left=days_left,
                )
            )

    # 按日程时间升序排序
    events.sort(key=lambda e: e.schedule_time)
    return events


def get_funnel_analytics(db_path: Path | str | None = None) -> ApplicationFunnelStats:
    """
    计算全景投递转化漏斗数据与阶段分布。
    """
    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status, notes_json FROM applications;")
        rows = cursor.fetchall()

    total_count = len(rows)
    distribution: dict[str, int] = {s.value: 0 for s in ApplicationStatus}

    assessment_stage_count = 0
    interview_stage_count = 0
    offer_stage_count = 0
    rejected_count = 0
    active_in_progress = 0

    interview_status_set = {
        ApplicationStatus.INTERVIEW_1.value,
        ApplicationStatus.INTERVIEW_2.value,
        ApplicationStatus.HR_STAGE.value,
        ApplicationStatus.OFFER.value,
    }
    assessment_status_set = interview_status_set | {ApplicationStatus.ASSESSMENT.value}

    applied_count = 0

    for r in rows:
        st = r["status"]
        if st in distribution:
            distribution[st] += 1

        notes_text = r["notes_json"] or ""

        # 是否属于正式投递 (除 wishlist 意向备选外均算)
        if st != ApplicationStatus.WISHLIST.value:
            applied_count += 1

        # 是否进入面试阶段 (当前处于面试/HR/Offer，或历史轨迹中曾到达面试)
        reached_interview = (st in interview_status_set) or ("技术一面" in notes_text or "初试" in notes_text or "interview_1" in notes_text)
        # 是否进入笔试阶段
        reached_assessment = reached_interview or (st in assessment_status_set) or ("笔试" in notes_text or "测评" in notes_text)

        if reached_assessment:
            assessment_stage_count += 1
        if reached_interview:
            interview_stage_count += 1

        if st == ApplicationStatus.OFFER.value:
            offer_stage_count += 1
        elif st == ApplicationStatus.REJECTED.value:
            rejected_count += 1

        if st not in (ApplicationStatus.OFFER.value, ApplicationStatus.REJECTED.value, ApplicationStatus.CLOSED.value):
            active_in_progress += 1

    interview_rate = round((interview_stage_count / applied_count * 100.0), 1) if applied_count > 0 else 0.0
    offer_rate = round((offer_stage_count / applied_count * 100.0), 1) if applied_count > 0 else 0.0

    return ApplicationFunnelStats(
        total_count=total_count,
        applied_count=applied_count,
        assessment_count=assessment_stage_count,
        interview_count=interview_stage_count,
        offer_count=offer_stage_count,
        rejected_count=rejected_count,
        active_in_progress=active_in_progress,
        interview_rate=interview_rate,
        offer_rate=offer_rate,
        status_distribution=distribution,
    )
