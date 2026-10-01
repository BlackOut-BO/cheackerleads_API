"""Хранилище веб-версии чекера лидов: свои таблицы в SQLite веба (с ботом ничего общего)."""
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DB_PATH = Path(os.environ.get("BUYING_DB", Path(__file__).resolve().parents[2] / "data" / "buying.db"))
RUNNING = ("queued", "running")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init() -> None:
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS leads_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source TEXT NOT NULL,              -- text | file | single
            file_name TEXT, file_type TEXT,
            input TEXT,                        -- исходный текст (для повтора); для файла — NULL
            leads TEXT NOT NULL DEFAULT '[]',  -- распознанные лиды
            status TEXT NOT NULL,              -- queued | running | done | error | cancelled
            total INTEGER NOT NULL DEFAULT 0, done INTEGER NOT NULL DEFAULT 0,
            results TEXT,                      -- результаты LeadChecker как есть
            output_kind TEXT,                  -- csv | txt | summary — что бот прислал бы в чат
            output_name TEXT, output BLOB,
            message TEXT, error TEXT,
            created_at TEXT NOT NULL, finished_at TEXT, deleted INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS leads_files (
            check_id INTEGER PRIMARY KEY, content BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS leads_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL, action TEXT NOT NULL, details TEXT NOT NULL DEFAULT '{}', at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS leads_audit_user ON leads_audit(user_id, id);
        """)
        c.execute("UPDATE leads_checks SET status='error', error=?, finished_at=? WHERE status IN ('queued','running')",
                  ("Сервис перезапускался во время проверки — запусти проверку ещё раз", now()))


def _row(r: sqlite3.Row | None, full: bool = True) -> dict | None:
    if r is None:
        return None
    d = dict(r)
    d["leads"] = json.loads(d.get("leads") or "[]")
    d["results"] = json.loads(d["results"]) if full and d.get("results") else ([] if full else None)
    d.pop("output", None)
    return d


def create_check(user_id: int, source: str, leads: list[dict], file_name: str | None = None, file_type: str | None = None,
                 text: str | None = None, file_bytes: bytes | None = None) -> int:
    with conn() as c:
        cur = c.execute(
            "INSERT INTO leads_checks (user_id, source, file_name, file_type, input, leads, status, total, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (user_id, source, file_name, file_type, text, json.dumps(leads, ensure_ascii=False), "queued", len(leads), now()),
        )
        cid = int(cur.lastrowid)
        if file_bytes is not None:
            c.execute("INSERT INTO leads_files (check_id, content) VALUES (?,?)", (cid, file_bytes))
        return cid


def update_check(cid: int, **fields: Any) -> None:
    if "results" in fields and not isinstance(fields["results"], str):
        fields["results"] = json.dumps(fields["results"], ensure_ascii=False, default=str)
    sets = ", ".join(f"{k}=?" for k in fields)
    with conn() as c:
        c.execute(f"UPDATE leads_checks SET {sets} WHERE id=?", (*fields.values(), cid))


def get_check(cid: int, user_id: int | None = None) -> dict | None:
    with conn() as c:
        r = c.execute("SELECT * FROM leads_checks WHERE id=? AND deleted=0", (cid,)).fetchone()
    d = _row(r)
    if d and user_id is not None and d["user_id"] != user_id:
        return None
    return d


def get_output(cid: int) -> tuple[str | None, str | None, bytes | None]:
    with conn() as c:
        r = c.execute("SELECT output_kind, output_name, output FROM leads_checks WHERE id=?", (cid,)).fetchone()
    return (r["output_kind"], r["output_name"], r["output"]) if r else (None, None, None)


def get_file(cid: int) -> bytes | None:
    with conn() as c:
        r = c.execute("SELECT content FROM leads_files WHERE check_id=?", (cid,)).fetchone()
    return r["content"] if r else None


def list_checks(user_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    with conn() as c:
        rows = c.execute(
            "SELECT id, user_id, source, file_name, file_type, status, total, done, output_kind, output_name, message, error, created_at, finished_at, results "
            "FROM leads_checks WHERE user_id=? AND deleted=0 ORDER BY id DESC LIMIT ? OFFSET ?", (user_id, limit, offset)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        res = json.loads(d.pop("results") or "[]")
        d["stats"] = verdict_stats(res)
        out.append(d)
    return out


def delete_check(cid: int) -> None:
    with conn() as c:
        c.execute("UPDATE leads_checks SET deleted=1 WHERE id=?", (cid,))


def verdict_stats(results: list[dict]) -> dict:
    s = {"clean": 0, "risky": 0, "spam": 0, "unknown": 0}
    for r in results:
        v = (r or {}).get("verdict") or "unknown"
        s[v if v in s else "unknown"] += 1
    return s


# ── журнал действий ──────────────────────────────────────────────
def audit(user_id: int, action: str, details: dict | None = None) -> None:
    with conn() as c:
        c.execute("INSERT INTO leads_audit (user_id, action, details, at) VALUES (?,?,?,?)",
                  (user_id, action, json.dumps(details or {}, ensure_ascii=False, default=str), now()))


def list_audit(user_id: int | None, limit: int = 100, offset: int = 0) -> list[dict]:
    q, args = "SELECT * FROM leads_audit", []
    if user_id is not None:
        q += " WHERE user_id=?"
        args.append(user_id)
    q += " ORDER BY id DESC LIMIT ? OFFSET ?"
    with conn() as c:
        rows = c.execute(q, (*args, limit, offset)).fetchall()
    return [{**dict(r), "details": json.loads(r["details"])} for r in rows]
