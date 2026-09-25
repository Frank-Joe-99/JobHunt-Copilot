"""
JobHunt-Copilot 求职投递看板与日程管理模块 (Application Tracker)
基于本地私密 SQLite 数据库，全生命周期跟踪各企业投递阶段、面试日程提醒与全流程转化漏斗。
"""

from skills.application_tracker.database import get_db_connection, DEFAULT_DB_PATH
from skills.application_tracker.handler import (
    add_application,
    get_application,
    update_status,
    delete_application,
    list_applications,
    get_upcoming_schedules,
    get_funnel_analytics,
)

__all__ = [
    "get_db_connection",
    "DEFAULT_DB_PATH",
    "add_application",
    "get_application",
    "update_status",
    "delete_application",
    "list_applications",
    "get_upcoming_schedules",
    "get_funnel_analytics",
]
