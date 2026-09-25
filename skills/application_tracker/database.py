"""
本地 SQLite 投递数据库存储引擎 (Application Tracker Database Layer)
基于 Python 原生 sqlite3 实现零第三方重量级依赖，支持 WAL 并发模式与自动迁移。
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

from core.config import PROJECT_ROOT

# 默认数据库存储路径: storage/tracker.db
DEFAULT_DB_PATH = PROJECT_ROOT / "storage" / "tracker.db"

# 记录已完成初始化的数据库路径，避免高频请求重复执行 DDL
_INITIALIZED_DBS: set[str] = set()


def _init_db_schema(conn: sqlite3.Connection) -> None:
    """初始化投递跟踪相关的数据表结构与索引"""
    cursor = conn.cursor()
    
    # 启用 WAL 模式，避免多进程/多线程写入锁表
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("PRAGMA synchronous=NORMAL;")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company TEXT NOT NULL,
        role TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'applied',
        salary_range TEXT,
        location TEXT,
        apply_date TEXT NOT NULL,
        next_schedule_time TEXT,
        next_schedule_notes TEXT,
        resume_path TEXT,
        notes_json TEXT NOT NULL DEFAULT '[]',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """)

    # 建立高频检索索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_company ON applications(company);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_apps_schedule ON applications(next_schedule_time);")

    conn.commit()


@contextmanager
def get_db_connection(db_path: Path | str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """
    获取 SQLite 数据库连接的上下文管理器。
    自动建表建索引，并配置 row_factory 为 sqlite3.Row，支持按列名访问字段。
    """
    path = Path(db_path) if db_path else DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    abs_path_str = str(path.resolve())

    conn = sqlite3.connect(str(path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    try:
        if abs_path_str not in _INITIALIZED_DBS:
            _init_db_schema(conn)
            _INITIALIZED_DBS.add(abs_path_str)
        yield conn
    finally:
        conn.close()
