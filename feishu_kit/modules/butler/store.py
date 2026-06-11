"""Butler SQLite persistence — conversations, goals, plans, reminders, approvals, audit log."""

import json
import logging
import sqlite3
import time
from pathlib import Path

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     TEXT    NOT NULL,
    open_id     TEXT    NOT NULL,
    role        TEXT    NOT NULL,  -- user / assistant / system
    content     TEXT    NOT NULL,
    intent      TEXT    DEFAULT '',
    created_at  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_conv_chat_id ON conversations(chat_id);

CREATE TABLE IF NOT EXISTS goals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     TEXT    NOT NULL,
    open_id     TEXT    NOT NULL,
    intent      TEXT    NOT NULL,
    fields_json TEXT    NOT NULL DEFAULT '{}',
    status      TEXT    NOT NULL DEFAULT 'active',  -- active/completed/cancelled/clarifying
    created_at  REAL    NOT NULL,
    updated_at  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_goals_chat ON goals(chat_id, status);

CREATE TABLE IF NOT EXISTS plans (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id     INTEGER NOT NULL REFERENCES goals(id),
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending/executing/completed/failed/cancelled
    created_at  REAL    NOT NULL,
    updated_at  REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS plan_steps (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id     INTEGER NOT NULL REFERENCES plans(id),
    seq         INTEGER NOT NULL,
    action      TEXT    NOT NULL,
    params_json TEXT    NOT NULL DEFAULT '{}',
    safety      TEXT    NOT NULL DEFAULT 'AUTO_EXECUTE',  -- AUTO_EXECUTE/CONFIRM_REQUIRED/ADMIN_ONLY/DENY
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending/running/done/failed/skipped
    result_json TEXT    DEFAULT NULL,
    error       TEXT    DEFAULT NULL,
    created_at  REAL    NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     TEXT    NOT NULL,
    open_id     TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    fire_at     REAL    NOT NULL,
    recurring   TEXT    DEFAULT NULL,  -- cron expression or NULL for one-shot
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending/fired/cancelled
    goal_id     INTEGER DEFAULT NULL REFERENCES goals(id),
    created_at  REAL    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reminders_fire ON reminders(fire_at, status);

CREATE TABLE IF NOT EXISTS approvals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    goal_id     INTEGER NOT NULL REFERENCES goals(id),
    plan_step_id INTEGER NOT NULL REFERENCES plan_steps(id),
    chat_id     TEXT    NOT NULL,
    open_id     TEXT    NOT NULL,
    action      TEXT    NOT NULL,
    params_json TEXT    NOT NULL DEFAULT '{}',
    status      TEXT    NOT NULL DEFAULT 'pending',  -- pending/approved/denied/expired
    created_at  REAL    NOT NULL,
    resolved_at REAL    DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status);

CREATE TABLE IF NOT EXISTS audit_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     TEXT    DEFAULT '',
    open_id     TEXT    DEFAULT '',
    action      TEXT    NOT NULL,
    target      TEXT    DEFAULT '',
    result      TEXT    DEFAULT '',
    safety      TEXT    DEFAULT '',
    created_at  REAL    NOT NULL
);
"""


class Store:
    """SQLite-backed persistence for the Butler."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    def open(self) -> None:
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._conn.commit()
        logger.info("Butler store opened: %s", self._db_path)

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("Store not opened")
        return self._conn

    # ── Conversations ──────────────────────────────────────────────

    def append_conversation(
        self, chat_id: str, open_id: str, role: str, content: str, intent: str = ""
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO conversations (chat_id, open_id, role, content, intent, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, open_id, role, content, intent, time.time()),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_conversation_history(self, chat_id: str, limit: int = 50) -> list[dict]:
        rows = self.conn.execute(
            "SELECT role, content, intent, created_at FROM conversations "
            "WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
            (chat_id, limit),
        ).fetchall()
        return [
            {"role": r[0], "content": r[1], "intent": r[2], "created_at": r[3]}
            for r in reversed(rows)
        ]

    # ── Goals ──────────────────────────────────────────────────────

    def create_goal(
        self, chat_id: str, open_id: str, intent: str, fields: dict
    ) -> int:
        now = time.time()
        cur = self.conn.execute(
            "INSERT INTO goals (chat_id, open_id, intent, fields_json, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'active', ?, ?)",
            (chat_id, open_id, intent, json.dumps(fields), now, now),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_active_goal(self, chat_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT id, chat_id, open_id, intent, fields_json, status, created_at, updated_at "
            "FROM goals WHERE chat_id = ? AND status IN ('active', 'clarifying') "
            "ORDER BY updated_at DESC LIMIT 1",
            (chat_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "chat_id": row[1], "open_id": row[2], "intent": row[3],
            "fields": json.loads(row[4]), "status": row[5],
            "created_at": row[6], "updated_at": row[7],
        }

    def update_goal(self, goal_id: int, *, fields: dict | None = None, status: str | None = None) -> None:
        parts: list[str] = []
        params: list = []
        if fields is not None:
            parts.append("fields_json = ?")
            params.append(json.dumps(fields))
        if status is not None:
            parts.append("status = ?")
            params.append(status)
        if not parts:
            return
        parts.append("updated_at = ?")
        params.append(time.time())
        params.append(goal_id)
        self.conn.execute(
            f"UPDATE goals SET {', '.join(parts)} WHERE id = ?", params
        )
        self.conn.commit()

    # ── Plans ──────────────────────────────────────────────────────

    def create_plan(self, goal_id: int) -> int:
        now = time.time()
        cur = self.conn.execute(
            "INSERT INTO plans (goal_id, status, created_at, updated_at) "
            "VALUES (?, 'pending', ?, ?)",
            (goal_id, now, now),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def add_plan_step(
        self, plan_id: int, seq: int, action: str, params: dict, safety: str
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO plan_steps (plan_id, seq, action, params_json, safety, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?)",
            (plan_id, seq, action, json.dumps(params), safety, time.time()),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_plan(self, plan_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT id, goal_id, status, created_at, updated_at FROM plans WHERE id = ?",
            (plan_id,),
        ).fetchone()
        if not row:
            return None
        steps = self.conn.execute(
            "SELECT id, seq, action, params_json, safety, status, result_json, error "
            "FROM plan_steps WHERE plan_id = ? ORDER BY seq",
            (plan_id,),
        ).fetchall()
        return {
            "id": row[0], "goal_id": row[1], "status": row[2],
            "created_at": row[3], "updated_at": row[4],
            "steps": [
                {
                    "id": s[0], "seq": s[1], "action": s[2],
                    "params": json.loads(s[3]), "safety": s[4],
                    "status": s[5], "result": json.loads(s[6]) if s[6] else None,
                    "error": s[7],
                }
                for s in steps
            ],
        }

    def get_plan_for_goal(self, goal_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT id FROM plans WHERE goal_id = ? ORDER BY id DESC LIMIT 1",
            (goal_id,),
        ).fetchone()
        if not row:
            return None
        return self.get_plan(row[0])

    def update_plan_status(self, plan_id: int, status: str) -> None:
        self.conn.execute(
            "UPDATE plans SET status = ?, updated_at = ? WHERE id = ?",
            (status, time.time(), plan_id),
        )
        self.conn.commit()

    def update_step(self, step_id: int, *, status: str, result: dict | None = None, error: str | None = None) -> None:
        self.conn.execute(
            "UPDATE plan_steps SET status = ?, result_json = ?, error = ? WHERE id = ?",
            (status, json.dumps(result) if result else None, error, step_id),
        )
        self.conn.commit()

    def get_pending_approval_step(self, plan_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT id, seq, action, params_json, safety, status FROM plan_steps "
            "WHERE plan_id = ? AND status = 'pending' AND safety = 'CONFIRM_REQUIRED' "
            "ORDER BY seq LIMIT 1",
            (plan_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "seq": row[1], "action": row[2],
            "params": json.loads(row[3]), "safety": row[4], "status": row[5],
        }

    def get_next_executable_step(self, plan_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT id, seq, action, params_json, safety, status FROM plan_steps "
            "WHERE plan_id = ? AND status = 'pending' ORDER BY seq LIMIT 1",
            (plan_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "seq": row[1], "action": row[2],
            "params": json.loads(row[3]), "safety": row[4], "status": row[5],
        }

    # ── Reminders ─────────────────────────────────────────────────

    def create_reminder(
        self, chat_id: str, open_id: str, message: str,
        fire_at: float, recurring: str | None = None, goal_id: int | None = None,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO reminders (chat_id, open_id, message, fire_at, recurring, status, goal_id, created_at) "
            "VALUES (?, ?, ?, ?, ?, 'pending', ?, ?)",
            (chat_id, open_id, message, fire_at, recurring, goal_id, time.time()),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_pending_reminders(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, chat_id, open_id, message, fire_at, recurring, status, goal_id "
            "FROM reminders WHERE status = 'pending' AND fire_at <= ?",
            (time.time(),),
        ).fetchall()
        return [
            {
                "id": r[0], "chat_id": r[1], "open_id": r[2], "message": r[3],
                "fire_at": r[4], "recurring": r[5], "status": r[6], "goal_id": r[7],
            }
            for r in rows
        ]

    def get_upcoming_reminders(self, within_seconds: float = 3600) -> list[dict]:
        """Get reminders scheduled within the next N seconds."""
        now = time.time()
        rows = self.conn.execute(
            "SELECT id, chat_id, open_id, message, fire_at, recurring, status, goal_id "
            "FROM reminders WHERE status = 'pending' AND fire_at <= ? AND fire_at > ?",
            (now + within_seconds, now),
        ).fetchall()
        return [
            {
                "id": r[0], "chat_id": r[1], "open_id": r[2], "message": r[3],
                "fire_at": r[4], "recurring": r[5], "status": r[6], "goal_id": r[7],
            }
            for r in rows
        ]

    def mark_reminder_fired(self, reminder_id: int) -> None:
        self.conn.execute(
            "UPDATE reminders SET status = 'fired' WHERE id = ?", (reminder_id,)
        )
        self.conn.commit()

    def cancel_reminder(self, reminder_id: int) -> None:
        self.conn.execute(
            "UPDATE reminders SET status = 'cancelled' WHERE id = ?", (reminder_id,)
        )
        self.conn.commit()

    # ── Approvals ─────────────────────────────────────────────────

    def create_approval(
        self, goal_id: int, step_id: int, chat_id: str, open_id: str,
        action: str, params: dict,
    ) -> int:
        cur = self.conn.execute(
            "INSERT INTO approvals (goal_id, plan_step_id, chat_id, open_id, action, params_json, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)",
            (goal_id, step_id, chat_id, open_id, action, json.dumps(params), time.time()),
        )
        self.conn.commit()
        return cur.lastrowid  # type: ignore[return-value]

    def get_pending_approval(self, chat_id: str) -> dict | None:
        row = self.conn.execute(
            "SELECT id, goal_id, plan_step_id, chat_id, open_id, action, params_json, status "
            "FROM approvals WHERE chat_id = ? AND status = 'pending' "
            "ORDER BY created_at DESC LIMIT 1",
            (chat_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "goal_id": row[1], "step_id": row[2],
            "chat_id": row[3], "open_id": row[4], "action": row[5],
            "params": json.loads(row[6]), "status": row[7],
        }

    def resolve_approval(self, approval_id: int, approved: bool) -> None:
        status = "approved" if approved else "denied"
        self.conn.execute(
            "UPDATE approvals SET status = ?, resolved_at = ? WHERE id = ?",
            (status, time.time(), approval_id),
        )
        self.conn.commit()

    # ── Audit Log ─────────────────────────────────────────────────

    def audit(
        self, action: str, target: str = "", result: str = "",
        safety: str = "", chat_id: str = "", open_id: str = "",
    ) -> None:
        self.conn.execute(
            "INSERT INTO audit_log (chat_id, open_id, action, target, result, safety, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, open_id, action, target, result, safety, time.time()),
        )
        self.conn.commit()

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        rows = self.conn.execute(
            "SELECT id, chat_id, open_id, action, target, result, safety, created_at "
            "FROM audit_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "id": r[0], "chat_id": r[1], "open_id": r[2], "action": r[3],
                "target": r[4], "result": r[5], "safety": r[6], "created_at": r[7],
            }
            for r in reversed(rows)
        ]
