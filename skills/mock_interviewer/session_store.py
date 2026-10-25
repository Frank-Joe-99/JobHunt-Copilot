"""面试私有存储。独立 schema、短事务和请求结果缓存，不依赖投递模块。"""

from contextlib import contextmanager
import hashlib
import hmac
import json
from pathlib import Path
import re
import sqlite3
import time

from pydantic import ValidationError

from core.config import PROJECT_ROOT
from core.state import (
    InterviewEvaluationReport, InterviewRequest, InterviewSession, InterviewStage, StoredInterview, UserProfile,
)
from tools.file_lock import exclusive_file_lock

DEFAULT_DB_PATH = PROJECT_ROOT / "storage" / "interviews.db"
SCHEMA_VERSION = 1


class SessionStoreError(RuntimeError):
    pass


class SessionConflict(SessionStoreError):
    pass


def profile_digest(profile: UserProfile) -> str:
    return hashlib.sha256(json.dumps(
        profile.model_dump(mode="json"), ensure_ascii=False, sort_keys=True,
    ).encode("utf-8")).hexdigest()


def _input_digest(operation: str, text: str) -> str:
    return hashlib.sha256(json.dumps([operation, text], ensure_ascii=False).encode()).hexdigest()


class InterviewStore:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH

    @staticmethod
    def _check_id(value: str):
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
            raise ValueError("会话或请求 ID 只能包含字母、数字、下划线和短横线，最长 128 字符。")

    def locked(self, session_id: str):
        self._check_id(session_id)
        name = hashlib.sha256(session_id.encode()).hexdigest() + ".lock"
        return exclusive_file_lock(self.db_path.parent / (self.db_path.name + ".locks") / name)

    @contextmanager
    def _connect(self):
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=5, isolation_level=None)
        conn.row_factory = sqlite3.Row
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row[0] for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            }
            allowed = {"interview_sessions", "interview_requests"}
            if version not in (0, SCHEMA_VERSION) or tables - allowed or (version == 0 and tables):
                raise SessionStoreError("存储不是受支持的面试数据库，未进行迁移或覆盖。")
            if version == 0:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.executescript("""
                    BEGIN IMMEDIATE;
                    CREATE TABLE IF NOT EXISTS interview_sessions (
                        session_id TEXT PRIMARY KEY, revision INTEGER NOT NULL,
                        schema_version INTEGER NOT NULL, session_json TEXT NOT NULL,
                        profile_json TEXT NOT NULL, profile_hash TEXT NOT NULL,
                        created_at REAL NOT NULL, updated_at REAL NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS interview_requests (
                        session_id TEXT NOT NULL, request_id TEXT NOT NULL,
                        operation TEXT NOT NULL, input_hash TEXT NOT NULL, input_text TEXT NOT NULL,
                        status TEXT NOT NULL, output_text TEXT NOT NULL DEFAULT '',
                        result_session_json TEXT, report_json TEXT, report_path TEXT,
                        error_code TEXT, attempts INTEGER NOT NULL DEFAULT 1,
                        updated_at REAL NOT NULL,
                        PRIMARY KEY(session_id, request_id),
                        FOREIGN KEY(session_id) REFERENCES interview_sessions(session_id) ON DELETE CASCADE
                    );
                    PRAGMA user_version=1;
                    COMMIT;
                """)
            elif not allowed.issubset(tables):
                raise SessionStoreError("面试数据库 schema 不完整，未覆盖原数据。")
            conn.execute("PRAGMA foreign_keys=ON")
            yield conn
        except sqlite3.Error:
            if conn.in_transaction:
                conn.rollback()
            raise SessionStoreError("面试存储操作失败，未输出私有记录。") from None
        finally:
            conn.close()

    @staticmethod
    def _load_row(row) -> StoredInterview:
        if row is None:
            raise SessionStoreError("未找到该面试会话。")
        if row["schema_version"] != SCHEMA_VERSION:
            raise SessionStoreError("会话数据版本不受支持。")
        try:
            profile = UserProfile.model_validate_json(row["profile_json"])
            if not hmac.compare_digest(profile_digest(profile), row["profile_hash"]):
                raise SessionStoreError("会话事实快照校验失败，未继续调用模型。")
            session = InterviewSession.model_validate_json(row["session_json"])
            if session.session_id != row["session_id"]:
                raise SessionStoreError("会话 ID 与存储不一致。")
            session.revision = row["revision"]
            return StoredInterview(
                session=session, profile=profile, profile_hash=row["profile_hash"], updated_at=row["updated_at"],
            )
        except (ValidationError, ValueError):
            raise SessionStoreError("会话记录无法校验，未输出私有数据。") from None

    @staticmethod
    def _request_row(row) -> InterviewRequest | None:
        if row is None:
            return None
        try:
            return InterviewRequest(
                request_id=row["request_id"], operation=row["operation"], input_text=row["input_text"],
                status=row["status"], output_text=row["output_text"],
                result_session=InterviewSession.model_validate_json(row["result_session_json"])
                if row["result_session_json"] else None,
                report=InterviewEvaluationReport.model_validate_json(row["report_json"])
                if row["report_json"] else None,
                report_path=row["report_path"], error_code=row["error_code"], attempts=row["attempts"],
            )
        except (ValidationError, ValueError):
            raise SessionStoreError("请求记录无法校验。") from None

    def create(self, session: InterviewSession, profile: UserProfile, *, prepare_opening: bool = False):
        self._check_id(session.session_id)
        now = time.time()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "INSERT INTO interview_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (session.session_id, 0, SCHEMA_VERSION, session.model_dump_json(),
                 profile.model_dump_json(), profile_digest(profile), now, now),
            )
            if prepare_opening:
                conn.execute(
                    "INSERT INTO interview_requests "
                    "(session_id,request_id,operation,input_hash,input_text,status,attempts,updated_at) "
                    "VALUES (?,'opening','opening',?,'','pending',0,?)",
                    (session.session_id, _input_digest("opening", ""), now),
                )
            conn.commit()

    def load(self, session_id: str) -> StoredInterview:
        self._check_id(session_id)
        with self._connect() as conn:
            return self._load_row(conn.execute(
                "SELECT * FROM interview_sessions WHERE session_id=?", (session_id,),
            ).fetchone())

    def get_request(self, session_id: str, request_id: str) -> InterviewRequest | None:
        self._check_id(session_id)
        self._check_id(request_id)
        with self._connect() as conn:
            return self._request_row(conn.execute(
                "SELECT * FROM interview_requests WHERE session_id=? AND request_id=?",
                (session_id, request_id),
            ).fetchone())

    def unfinished(self, session_id: str) -> InterviewRequest | None:
        self._check_id(session_id)
        with self._connect() as conn:
            return self._request_row(conn.execute(
                "SELECT * FROM interview_requests WHERE session_id=? AND status IN ('pending','failed') "
                "ORDER BY updated_at DESC LIMIT 1", (session_id,),
            ).fetchone())

    def begin_request(
        self, session_id: str, request_id: str, operation: str, input_text: str,
        *, expected_revision: int | None = None,
    ) -> tuple[StoredInterview, InterviewRequest]:
        self._check_id(session_id)
        self._check_id(request_id)
        if operation not in ("opening", "answer", "finish"):
            raise ValueError("未知面试请求类型。")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current = self._load_row(conn.execute(
                "SELECT * FROM interview_sessions WHERE session_id=?", (session_id,),
            ).fetchone())
            existing = conn.execute(
                "SELECT * FROM interview_requests WHERE session_id=? AND request_id=?", (session_id, request_id),
            ).fetchone()
            digest = _input_digest(operation, input_text)
            if existing:
                if existing["input_hash"] != digest or existing["status"] == "cancelled":
                    raise SessionConflict("该 request_id 已用于不同或已取消的请求。")
                if existing["status"] == "completed":
                    conn.commit()
                    return current, self._request_row(existing)
            if expected_revision is not None and current.session.revision != expected_revision:
                raise SessionConflict("会话版本已变化，请重新读取或恢复后作答。")
            finish = operation == "finish" or input_text.strip().lower() in (
                "finish", "/finish", "退出", "quit", "/quit", "交卷",
            )
            control = finish or input_text.strip().lower() in ("next", "/next", "跳过")
            other = conn.execute(
                "SELECT request_id FROM interview_requests WHERE session_id=? "
                "AND status IN ('pending','failed') AND request_id<>?",
                (session_id, request_id),
            ).fetchone()
            if other and not control:
                raise SessionConflict("会话有未完成请求，请使用 /retry 重试，或暂停/结束。")
            if control:
                conn.execute(
                    "UPDATE interview_requests SET status='cancelled' WHERE session_id=? "
                    "AND status IN ('pending','failed') AND request_id<>?", (session_id, request_id),
                )
            session = current.session
            if session.is_paused and operation != "finish":
                raise SessionConflict("会话已暂停，请先恢复。")
            if operation == "finish":
                session.is_paused = False
                # 结束问答是用户指令，复盘失败不应让会话重新接受回答。
                session.is_finished = True
                session.current_stage = InterviewStage.COMPLETED
            if operation == "answer":
                if session.is_finished:
                    raise SessionConflict("面试问答已结束，请生成或读取复盘报告。")
                if not session.history and not finish:
                    raise SessionConflict("开场问题尚未完成，请先 /retry。")
                if not control and not existing:
                    if session.history[-1].answer:
                        raise SessionConflict("上一回答已保存，不能重复追加到同一道问题。")
                    session.history[-1].answer = input_text.strip() or "（候选人未作答）"
            session.revision += 1
            conn.execute(
                "UPDATE interview_sessions SET revision=?,session_json=?,updated_at=? WHERE session_id=?",
                (session.revision, session.model_dump_json(), time.time(), session_id),
            )
            if existing:
                conn.execute(
                    "UPDATE interview_requests SET status='pending',output_text='',error_code=NULL,"
                    "attempts=attempts+1,updated_at=? WHERE session_id=? AND request_id=?",
                    (time.time(), session_id, request_id),
                )
            else:
                conn.execute(
                    "INSERT INTO interview_requests "
                    "(session_id,request_id,operation,input_hash,input_text,status,updated_at) VALUES (?,?,?,?,?,'pending',?)",
                    (session_id, request_id, operation, digest, input_text, time.time()),
                )
            conn.commit()
            request = self._request_row(conn.execute(
                "SELECT * FROM interview_requests WHERE session_id=? AND request_id=?", (session_id, request_id),
            ).fetchone())
            return current, request

    def complete(
        self, session: InterviewSession, request_id: str, expected_revision: int, output: str,
        report: InterviewEvaluationReport | None = None, report_path: str | None = None,
    ):
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            session.revision = expected_revision + 1
            row = conn.execute(
                "UPDATE interview_sessions SET revision=?,session_json=?,updated_at=? "
                "WHERE session_id=? AND revision=?",
                (session.revision, session.model_dump_json(), time.time(), session.session_id, expected_revision),
            )
            if row.rowcount != 1:
                raise SessionConflict("会话版本已改变，旧请求未覆盖新状态。")
            row = conn.execute(
                "UPDATE interview_requests SET status='completed',output_text=?,result_session_json=?,"
                "report_json=?,report_path=?,error_code=NULL,updated_at=? "
                "WHERE session_id=? AND request_id=? AND status='pending'",
                (output, session.model_dump_json(), report.model_dump_json() if report else None,
                 report_path, time.time(), session.session_id, request_id),
            )
            if row.rowcount != 1:
                raise SessionConflict("请求状态已改变，未提交重复结果。")
            conn.commit()

    def fail(self, session_id: str, request_id: str, partial: str, error: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE interview_requests SET status='failed',output_text=?,error_code=?,updated_at=? "
                "WHERE session_id=? AND request_id=? AND status='pending'",
                (partial, error, time.time(), session_id, request_id),
            )

    def set_paused(self, session_id: str, paused: bool) -> InterviewSession:
        with self.locked(session_id):
            current = self.load(session_id).session
            if current.is_finished and paused:
                raise SessionConflict("已结束会话无需暂停。")
            if current.is_paused == paused:
                return current
            current.is_paused = paused
            self._update(current, current.revision)
            return current

    def _update(self, session: InterviewSession, expected_revision: int):
        with self._connect() as conn:
            session.revision = expected_revision + 1
            result = conn.execute(
                "UPDATE interview_sessions SET revision=?,session_json=?,updated_at=? "
                "WHERE session_id=? AND revision=?",
                (session.revision, session.model_dump_json(), time.time(), session.session_id, expected_revision),
            )
            if result.rowcount != 1:
                raise SessionConflict("会话版本冲突。")

    def list_sessions(self, limit: int = 20) -> list[dict]:
        if not 1 <= limit <= 200:
            raise ValueError("limit 必须在 1～200。")
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM interview_sessions ORDER BY updated_at DESC LIMIT ?", (limit,),
            ).fetchall()
            return [{
                "session_id": item.session.session_id, "target_company": item.session.target_company,
                "target_role": item.session.target_role, "stage": item.session.current_stage.value,
                "is_paused": item.session.is_paused, "is_finished": item.session.is_finished,
                "revision": item.session.revision, "updated_at": item.updated_at,
            } for item in (self._load_row(row) for row in rows)]

    def delete(self, session_id: str) -> bool:
        with self.locked(session_id), self._connect() as conn:
            return conn.execute(
                "DELETE FROM interview_sessions WHERE session_id=?", (session_id,),
            ).rowcount == 1
