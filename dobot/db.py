from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

DB_PATH = Path(__file__).resolve().parent.parent / "dobot.sqlite3"
SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_conn() -> Iterable[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_conn() as conn:
        conn.executescript(schema)


def upsert_user(telegram_id: int, name: str, tz: str = "Europe/Zurich") -> sqlite3.Row:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO users (telegram_id, name, tz)
            VALUES (:tg_id, :name, :tz)
            ON CONFLICT(telegram_id) DO UPDATE SET name = excluded.name
            """,
            {"tg_id": telegram_id, "name": name, "tz": tz},
        )
        cur = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return cur.fetchone()


def get_user(telegram_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return cur.fetchone()


def update_user(user_id: int, **fields: Any) -> None:
    if not fields:
        return
    columns = ", ".join(f"{k} = :{k}" for k in fields)
    fields["user_id"] = user_id
    with get_conn() as conn:
        conn.execute(f"UPDATE users SET {columns} WHERE id = :user_id", fields)


def list_users() -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM users")
        return cur.fetchall()


def list_domains() -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM domains ORDER BY name")
        return cur.fetchall()


def create_task(user_id: int, data: Dict[str, Any]) -> int:
    keys = ", ".join(data.keys())
    placeholders = ", ".join(f":{k}" for k in data)
    sql = f"INSERT INTO tasks (user_id, {keys}) VALUES (:user_id, {placeholders})"
    data = data.copy()
    data["user_id"] = user_id
    with get_conn() as conn:
        cur = conn.execute(sql, data)
        return cur.lastrowid


def update_task(task_id: int, **fields: Any) -> None:
    if not fields:
        return
    parts = ", ".join(f"{k} = :{k}" for k in fields)
    fields["task_id"] = task_id
    with get_conn() as conn:
        conn.execute(f"UPDATE tasks SET {parts} WHERE id = :task_id", fields)


def get_task(task_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT t.*, d.name AS domain_name, d.weight_bias FROM tasks t "
            "LEFT JOIN domains d ON d.id = t.domain_id WHERE t.id = ?",
            (task_id,),
        )
        return cur.fetchone()


def list_tasks(
    user_id: int,
    status: str = "active",
    limit: int = 5,
    offset: int = 0,
) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT t.*, d.name AS domain_name, d.weight_bias FROM tasks t "
            "LEFT JOIN domains d ON d.id = t.domain_id "
            "WHERE t.user_id = ? AND t.status = ? ORDER BY t.priority = 'must' DESC, CASE WHEN t.due_at IS NULL THEN 1 ELSE 0 END, t.due_at, t.id DESC "
            "LIMIT ? OFFSET ?",
            (user_id, status, limit, offset),
        )
        return cur.fetchall()


def count_tasks(user_id: int, status: str = "active") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT COUNT(*) FROM tasks WHERE user_id = ? AND status = ?",
            (user_id, status),
        )
        (count,) = cur.fetchone()
        return int(count)


def get_subtasks(task_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM subtasks WHERE task_id = ? ORDER BY order_idx, id",
            (task_id,),
        )
        return cur.fetchall()


def add_subtask(task_id: int, title: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO subtasks (task_id, title) VALUES (?, ?)",
            (task_id, title),
        )
        return cur.lastrowid


def toggle_subtask(subtask_id: int) -> None:
    with get_conn() as conn:
        cur = conn.execute("SELECT done FROM subtasks WHERE id = ?", (subtask_id,))
        row = cur.fetchone()
        if not row:
            return
        done = 0 if row["done"] else 1
        done_at = datetime.utcnow().isoformat() if done else None
        conn.execute(
            "UPDATE subtasks SET done = ?, done_at = ? WHERE id = ?",
            (done, done_at, subtask_id),
        )


def last_completion(task_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM completions WHERE task_id = ? ORDER BY completed_at DESC LIMIT 1",
            (task_id,),
        )
        return cur.fetchone()


def completion_count(task_id: int) -> int:
    with get_conn() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM completions WHERE task_id = ?", (task_id,))
        (count,) = cur.fetchone()
        return int(count)


def log_completion(task_id: int, xp: float, completed_at: str, streak_after: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO completions (task_id, completed_at, xp_earned, streak_after) VALUES (?,?,?,?)",
            (task_id, completed_at, xp, streak_after),
        )


def get_streak(task_id: int) -> Optional[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM streaks WHERE task_id = ?", (task_id,))
        return cur.fetchone()


def save_streak(task_id: int, current: int, longest: int, last_completed_at: str) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO streaks (task_id, current_streak, longest_streak, last_completed_at)
            VALUES (?,?,?,?)
            ON CONFLICT(task_id) DO UPDATE SET
              current_streak = excluded.current_streak,
              longest_streak = excluded.longest_streak,
              last_completed_at = excluded.last_completed_at
            """,
            (task_id, current, longest, last_completed_at),
        )


def domain_xp_snapshot(user_id: int, days: int = 30) -> Dict[int, float]:
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT COALESCE(t.domain_id, 0) AS domain_id, SUM(c.xp_earned) AS xp
            FROM completions c
            JOIN tasks t ON t.id = c.task_id
            WHERE t.user_id = ? AND c.completed_at >= ?
            GROUP BY COALESCE(t.domain_id, 0)
            """,
            (user_id, since),
        )
        return {int(row["domain_id"]): float(row["xp"] or 0.0) for row in cur.fetchall()}


def domain_average(snapshot: Dict[int, float], domain_count: int) -> float:
    if not snapshot:
        return 0.0
    total = sum(snapshot.values())
    return total / max(domain_count, 1)


def due_today_tasks(user_id: int, now_iso: str) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT t.*, d.name AS domain_name FROM tasks t
            LEFT JOIN domains d ON d.id = t.domain_id
            WHERE t.user_id = ? AND t.status = 'active' AND t.due_at IS NOT NULL AND date(t.due_at) = date(?)
            ORDER BY t.due_at ASC
            """,
            (user_id, now_iso),
        )
        return cur.fetchall()


def overdue_tasks(user_id: int, now_iso: str) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT t.*, d.name AS domain_name FROM tasks t
            LEFT JOIN domains d ON d.id = t.domain_id
            WHERE t.user_id = ? AND t.status = 'active' AND t.due_at IS NOT NULL AND datetime(t.due_at) < datetime(?)
            ORDER BY datetime(t.due_at) ASC
            """,
            (user_id, now_iso),
        )
        return cur.fetchall()


def neglected_candidates(user_id: int, domain_id: Optional[int], limit: int = 5) -> List[sqlite3.Row]:
    params: Sequence[Any]
    where = "t.user_id = ? AND t.status = 'active'"
    params = [user_id]
    if domain_id is not None:
        where += " AND t.domain_id = ?"
        params.append(domain_id)
    with get_conn() as conn:
        cur = conn.execute(
            f"SELECT t.*, d.name AS domain_name FROM tasks t "
            f"LEFT JOIN domains d ON d.id = t.domain_id WHERE {where} "
            "ORDER BY t.energy = 'medium' DESC, t.energy = 'high' DESC, t.id DESC LIMIT ?",
            (*params, limit),
        )
        return cur.fetchall()


def streak_overview(user_id: int) -> Tuple[List[sqlite3.Row], List[sqlite3.Row], List[sqlite3.Row]]:
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT s.*, t.title, t.recurrence, t.due_at, t.priority
            FROM streaks s JOIN tasks t ON t.id = s.task_id
            WHERE t.user_id = ? AND t.status = 'active'
            """,
            (user_id,),
        )
        rows = cur.fetchall()
    best = sorted(rows, key=lambda r: r["current_streak"], reverse=True)[:3]
    weakest = sorted(rows, key=lambda r: r["current_streak"])[:3]
    at_risk: List[sqlite3.Row] = []
    now = datetime.utcnow()
    for row in rows:
        last = row["last_completed_at"]
        if not last:
            continue
        last_dt = datetime.fromisoformat(last)
        if (now - last_dt) > timedelta(days=2):
            at_risk.append(row)
    return best, weakest, at_risk[:3]


def stats_snapshot(user_id: int, days: int) -> Dict[str, Any]:
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_conn() as conn:
        domain_rows = conn.execute(
            """
            SELECT COALESCE(d.name, 'unsorted') AS domain, SUM(c.xp_earned) AS xp
            FROM completions c
            JOIN tasks t ON t.id = c.task_id
            LEFT JOIN domains d ON d.id = t.domain_id
            WHERE t.user_id = ? AND c.completed_at >= ?
            GROUP BY domain
            ORDER BY xp DESC
            """,
            (user_id, since),
        ).fetchall()
        horizon_rows = conn.execute(
            """
            SELECT t.time_horizon, COUNT(*) AS cnt
            FROM completions c JOIN tasks t ON t.id = c.task_id
            WHERE t.user_id = ? AND c.completed_at >= ?
            GROUP BY t.time_horizon
            """,
            (user_id, since),
        ).fetchall()
        overdue_cnt = conn.execute(
            """
            SELECT COUNT(*) FROM tasks
            WHERE user_id = ? AND status = 'active' AND due_at IS NOT NULL AND datetime(due_at) < datetime('now')
            """,
            (user_id,),
        ).fetchone()[0]
        completions_cnt = conn.execute(
            """
            SELECT COUNT(*) FROM completions c JOIN tasks t ON t.id = c.task_id
            WHERE t.user_id = ? AND c.completed_at >= ?
            """,
            (user_id, since),
        ).fetchone()[0]
    return {
        "domains": domain_rows,
        "horizons": horizon_rows,
        "overdue": int(overdue_cnt),
        "completions": int(completions_cnt),
    }


def list_rewards(user_id: int) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM rewards WHERE user_id = ? ORDER BY level_req, xp_cost",
            (user_id,),
        )
        return cur.fetchall()


def create_reward(user_id: int, title: str, xp_cost: float, level_req: int) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO rewards (user_id, title, xp_cost, level_req) VALUES (?,?,?,?)",
            (user_id, title, xp_cost, level_req),
        )
        return cur.lastrowid


def mark_reward_claimed(reward_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE rewards SET claimed_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), reward_id),
        )
