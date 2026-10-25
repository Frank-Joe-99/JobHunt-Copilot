"""结构化传输格式工具；只保存能力摘要，不保存请求、结果或认证信息。"""

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import time

from core.config import PROJECT_ROOT

DEFAULT_CACHE_PATH = PROJECT_ROOT / "storage" / "llm_capabilities.db"


class UnsupportedStrictSchema(ValueError):
    """合法业务 schema 含任意键映射等严格传输不能表示的结构。"""


def strict_schema(schema: dict) -> dict:
    result = deepcopy(schema)
    def visit(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                if node.get("additionalProperties") not in (None, False) or "properties" not in node:
                    raise UnsupportedStrictSchema("该业务 schema 含动态映射，请使用 JSON mode 或提示词 JSON。")
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            node.pop("default", None)
            for key in ("properties", "$defs", "definitions"):
                for child in node.get(key, {}).values():
                    visit(child)
            for key in ("items", "anyOf", "oneOf", "allOf"):
                if key in node:
                    visit(node[key])
        elif isinstance(node, list):
            for value in node:
                visit(value)
    if not isinstance(result, dict) or result.get("type") != "object" or "properties" not in result:
        raise ValueError("结构化 schema 根必须为具有 properties 的对象。")
    visit(result)
    return result


def format_unsupported(response, format_name: str) -> bool:
    """只识别明确的格式能力错误；不把任意 400、无效 schema 或权限错误当作降级许可。"""
    if response.status_code not in (400, 422) or format_name == "prompt_json":
        return False
    try:
        error = response.json().get("error", {})
        code, param, message = error.get("code"), error.get("param"), error.get("message", "")
        if not isinstance(message, str):
            return False
        if code not in ("unsupported_parameter", "unsupported_value", "unsupported_response_format"):
            return False
        if param not in ("response_format", "response_format.type", "response_format.json_schema"):
            return False
        message = message.lower()
        return ("not support" in message or "unsupported" in message) and (
            format_name in message or (code == "unsupported_parameter" and "response_format" in message)
        )
    except (ValueError, AttributeError, TypeError):
        return False


class FormatCache:
    def __init__(self, identity: dict, ttl: int, path: Path | None = None):
        self.key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        self.ttl = ttl
        self.path = path or DEFAULT_CACHE_PATH

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=1)
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if (version == 0 and tables) or version not in (0, 1) or tables - {"unsupported_formats"}:
                raise sqlite3.DatabaseError("unsupported capability cache")
            conn.execute("CREATE TABLE IF NOT EXISTS unsupported_formats (identity TEXT, format TEXT, saved_at REAL, PRIMARY KEY(identity,format))")
            conn.execute("PRAGMA user_version=1")
            conn.commit()
            return conn
        except BaseException:
            conn.close()
            raise

    def unsupported(self, name: str) -> bool:
        if self.ttl == 0:
            return False
        conn = None
        try:
            conn = self._connect()
            row = conn.execute("SELECT saved_at FROM unsupported_formats WHERE identity=? AND format=?", (self.key, name)).fetchone()
            return bool(row and 0 <= time.time() - row[0] < self.ttl)
        except (sqlite3.Error, OSError):
            return False
        finally:
            if conn is not None:
                conn.close()

    def remember(self, name: str):
        if self.ttl == 0:
            return
        conn = None
        try:
            conn = self._connect()
            conn.execute("INSERT OR REPLACE INTO unsupported_formats VALUES (?,?,?)", (self.key, name, time.time()))
            conn.commit()
        except (sqlite3.Error, OSError):
            pass  # 能力缓存故障不阻断合法请求，不输出路径或认证信息。
        finally:
            if conn is not None:
                conn.close()
