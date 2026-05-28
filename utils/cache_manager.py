"""
cache_manager.py — Self-improving LLM step cache.

Tracks per-test-case generation outcomes and decides when to
regenerate steps via the LLM. Enables a feedback loop where
repeatedly-failing tests are flagged 'suspect' and regenerated
with failure context embedded in the LLM prompt.

Architecture:
- SQLite DB at locators/cache.db (single file, easy to inspect)
- Schema is forward-compatible: schema_version table tracks migrations
- All operations are best-effort: if the DB is corrupted, the framework
  falls back to "regenerate everything" (safe default)

CLI:
  python -m utils.cache_manager stats          — show cache statistics
  python -m utils.cache_manager invalidate NAME — force regeneration of one test
  python -m utils.cache_manager reset           — wipe the entire cache

Place this file at: utils/cache_manager.py
"""

import hashlib
import os
import re
import sqlite3
import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Optional

CACHE_DB_PATH = "locators/cache.db"
SCHEMA_VERSION = 1

# Auto-invalidation thresholds — tunable, not hardcoded magic
CONSECUTIVE_FAILURES_THRESHOLD = 3
LOW_CONFIDENCE_THRESHOLD = 0.50
LOW_CONFIDENCE_WINDOW = 5


# ──────────────────────────────────────────────────────────────────────
#  Schema
# ──────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS test_cases (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_name       TEXT NOT NULL UNIQUE,
    semantic_hash   TEXT NOT NULL,
    generated_at    TEXT NOT NULL,
    generated_by    TEXT,
    status          TEXT NOT NULL DEFAULT 'fresh',
    last_failure_context TEXT
);

CREATE TABLE IF NOT EXISTS run_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_case_id    INTEGER NOT NULL,
    run_at          TEXT NOT NULL,
    outcome         TEXT NOT NULL,
    confidence      REAL,
    failed_step     INTEGER,
    failure_reason  TEXT,
    FOREIGN KEY (test_case_id) REFERENCES test_cases(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_run_history_test_case
    ON run_history(test_case_id, run_at DESC);
"""


# ──────────────────────────────────────────────────────────────────────
#  Connection management
# ──────────────────────────────────────────────────────────────────────

def _ensure_db_dir():
    db_dir = os.path.dirname(CACHE_DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)


@contextmanager
def _connect():
    """
    Context manager for a SQLite connection.
    Initialises schema on first use.
    Returns (conn, cursor).
    """
    _ensure_db_dir()
    conn = sqlite3.connect(CACHE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.executescript(SCHEMA_SQL)
        # Bootstrap version row if absent
        cur.execute("SELECT version FROM schema_version LIMIT 1")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
        conn.commit()
        yield conn, cur
    finally:
        conn.close()


# ──────────────────────────────────────────────────────────────────────
#  Semantic hashing
# ──────────────────────────────────────────────────────────────────────

def compute_semantic_hash(test_case_text: str) -> str:
    """
    Hash the *semantic content* of a test case, ignoring formatting noise.
    Whitespace, blank lines, and case are normalised away so trivial
    edits don't invalidate the cache.

    Args:
        test_case_text: raw text of the test case (title + step lines)
    Returns:
        16-char hex hash
    """
    if not test_case_text:
        return ""

    # Normalise: lowercase, collapse whitespace, strip blank lines
    normalised_lines = []
    for line in test_case_text.splitlines():
        stripped = line.strip().lower()
        if not stripped:
            continue
        # Collapse internal whitespace
        stripped = re.sub(r"\s+", " ", stripped)
        normalised_lines.append(stripped)

    normalised = "\n".join(normalised_lines)
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:16]


# ──────────────────────────────────────────────────────────────────────
#  Cache lookup / decision
# ──────────────────────────────────────────────────────────────────────

def should_regenerate(test_name: str, current_hash: str) -> tuple[bool, str]:
    """
    Decide whether a test case needs LLM regeneration.

    Returns (should_regenerate, reason).
    Reason is a short human-readable string for logging.
    """
    try:
        with _connect() as (conn, cur):
            cur.execute(
                "SELECT id, semantic_hash, status FROM test_cases "
                "WHERE test_name = ?",
                (test_name,),
            )
            row = cur.fetchone()

            if not row:
                return True, "MISS (first run)"

            if row["semantic_hash"] != current_hash:
                return True, "MISS (semantic hash changed — test edited)"

            if row["status"] == "invalidated":
                return True, "MISS (manually invalidated)"

            if row["status"] == "suspect":
                return True, "MISS (auto-flagged suspect after repeated failures)"

            # Check failure streak from run history.
            # Order by id (monotonic) rather than run_at — multiple
            # outcomes recorded in the same second would otherwise
            # have non-deterministic ordering.
            cur.execute(
                "SELECT outcome FROM run_history "
                "WHERE test_case_id = ? "
                "ORDER BY id DESC LIMIT ?",
                (row["id"], CONSECUTIVE_FAILURES_THRESHOLD),
            )
            recent = cur.fetchall()
            if len(recent) >= CONSECUTIVE_FAILURES_THRESHOLD and all(
                r["outcome"] == "FAIL" for r in recent
            ):
                # Auto-mark as suspect so next pre-run decision is fast
                cur.execute(
                    "UPDATE test_cases SET status = 'suspect' WHERE id = ?",
                    (row["id"],),
                )
                conn.commit()
                return True, (
                    f"MISS (auto-flagged after "
                    f"{CONSECUTIVE_FAILURES_THRESHOLD} consecutive failures)"
                )

            return False, "HIT"

    except sqlite3.Error as e:
        # Best-effort: if the DB is corrupted, regenerate everything
        print(f"[CACHE] ⚠️ SQLite error (will regenerate): {e}")
        return True, "MISS (cache error — safe fallback)"


def get_failure_context(test_name: str, limit: int = 3) -> str:
    """
    Build a feedback string from recent failures, suitable for
    embedding into the LLM regeneration prompt.

    Returns empty string if no failure history exists.
    """
    try:
        with _connect() as (conn, cur):
            cur.execute(
                "SELECT id, last_failure_context FROM test_cases "
                "WHERE test_name = ?",
                (test_name,),
            )
            tc = cur.fetchone()
            if not tc:
                return ""

            cur.execute(
                "SELECT run_at, outcome, failed_step, failure_reason "
                "FROM run_history "
                "WHERE test_case_id = ? AND outcome = 'FAIL' "
                "ORDER BY id DESC LIMIT ?",
                (tc["id"], limit),
            )
            failures = cur.fetchall()
            if not failures:
                return ""

            lines = ["Previous attempts at this test case failed:"]
            for f in failures:
                step_info = f"step {f['failed_step']}" if f["failed_step"] else "unknown step"
                reason = (f["failure_reason"] or "no reason recorded")[:120]
                lines.append(
                    f"- {f['run_at'][:10]}: failed at {step_info} — {reason}"
                )

            lines.append(
                "\nWhen generating steps, avoid patterns that previously "
                "caused these failures. Be conservative; prefer steps with "
                "explicit waits where the previous run timed out."
            )
            return "\n".join(lines)

    except sqlite3.Error:
        return ""


# ──────────────────────────────────────────────────────────────────────
#  Recording
# ──────────────────────────────────────────────────────────────────────

def record_generation(
    test_name: str,
    semantic_hash: str,
    generated_by: str = "gpt-4o-mini",
) -> None:
    """Mark a test case as freshly generated (resets status to 'fresh')."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        with _connect() as (conn, cur):
            cur.execute(
                "INSERT INTO test_cases "
                "(test_name, semantic_hash, generated_at, generated_by, status) "
                "VALUES (?, ?, ?, ?, 'fresh') "
                "ON CONFLICT(test_name) DO UPDATE SET "
                "  semantic_hash = excluded.semantic_hash, "
                "  generated_at = excluded.generated_at, "
                "  generated_by = excluded.generated_by, "
                "  status = 'fresh'",
                (test_name, semantic_hash, now, generated_by),
            )
            conn.commit()
    except sqlite3.Error as e:
        print(f"[CACHE] ⚠️ Failed to record generation: {e}")


def record_outcome(
    test_name: str,
    outcome: str,
    confidence: float,
    failed_step: Optional[int] = None,
    failure_reason: Optional[str] = None,
) -> None:
    """
    Record one run outcome for a test case.

    Args:
        outcome: 'PASS' | 'PASS_WITH_HEALING' | 'FAIL'
        confidence: average step confidence (0.0–1.0)
        failed_step: index (1-based) of the first failing step, or None
        failure_reason: short error summary, or None
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        with _connect() as (conn, cur):
            cur.execute(
                "SELECT id FROM test_cases WHERE test_name = ?",
                (test_name,),
            )
            row = cur.fetchone()
            if not row:
                # Test case not in cache — likely because generation
                # was skipped (e.g. running stale steps).  Insert a
                # minimal record so history is still tracked.
                cur.execute(
                    "INSERT INTO test_cases "
                    "(test_name, semantic_hash, generated_at, status) "
                    "VALUES (?, ?, ?, 'fresh')",
                    (test_name, "unknown", now),
                )
                test_case_id = cur.lastrowid
            else:
                test_case_id = row["id"]

            cur.execute(
                "INSERT INTO run_history "
                "(test_case_id, run_at, outcome, confidence, "
                " failed_step, failure_reason) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    test_case_id, now, outcome, confidence,
                    failed_step, failure_reason,
                ),
            )

            # If this run succeeded, clear suspect flag
            if outcome in ("PASS", "PASS_WITH_HEALING"):
                cur.execute(
                    "UPDATE test_cases SET status = 'fresh' "
                    "WHERE id = ? AND status = 'suspect'",
                    (test_case_id,),
                )

            conn.commit()
    except sqlite3.Error as e:
        print(f"[CACHE] ⚠️ Failed to record outcome: {e}")


# ──────────────────────────────────────────────────────────────────────
#  Stats & maintenance
# ──────────────────────────────────────────────────────────────────────

def get_stats() -> dict:
    """Return a snapshot of cache stats for reporting."""
    try:
        with _connect() as (conn, cur):
            cur.execute("SELECT COUNT(*) AS n FROM test_cases")
            total = cur.fetchone()["n"]

            cur.execute(
                "SELECT COUNT(*) AS n FROM test_cases WHERE status = 'fresh'"
            )
            fresh = cur.fetchone()["n"]

            cur.execute(
                "SELECT COUNT(*) AS n FROM test_cases WHERE status = 'suspect'"
            )
            suspect = cur.fetchone()["n"]

            cur.execute(
                "SELECT COUNT(*) AS n FROM test_cases "
                "WHERE status = 'invalidated'"
            )
            invalidated = cur.fetchone()["n"]

            cur.execute("SELECT COUNT(*) AS n FROM run_history")
            total_runs = cur.fetchone()["n"]

            cur.execute(
                "SELECT outcome, COUNT(*) AS n FROM run_history "
                "GROUP BY outcome"
            )
            by_outcome = {r["outcome"]: r["n"] for r in cur.fetchall()}

            return {
                "total_test_cases": total,
                "fresh":            fresh,
                "suspect":          suspect,
                "invalidated":      invalidated,
                "total_runs":       total_runs,
                "outcomes":         by_outcome,
            }
    except sqlite3.Error as e:
        return {"error": str(e)}


def invalidate(test_name: str) -> bool:
    """Mark one test case for regeneration on the next run."""
    try:
        with _connect() as (conn, cur):
            cur.execute(
                "UPDATE test_cases SET status = 'invalidated' "
                "WHERE test_name = ?",
                (test_name,),
            )
            updated = cur.rowcount
            conn.commit()
            return updated > 0
    except sqlite3.Error as e:
        print(f"[CACHE] ⚠️ Invalidate failed: {e}")
        return False


def reset() -> None:
    """Wipe the entire cache database."""
    if os.path.exists(CACHE_DB_PATH):
        os.remove(CACHE_DB_PATH)
        print(f"[CACHE] Reset — removed {CACHE_DB_PATH}")
    else:
        print(f"[CACHE] Nothing to reset (no DB at {CACHE_DB_PATH})")


# ──────────────────────────────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────────────────────────────

def _cli():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return

    cmd = args[0]

    if cmd == "stats":
        stats = get_stats()
        if "error" in stats:
            print(f"❌ {stats['error']}")
            return
        print("─" * 50)
        print("Cache statistics")
        print("─" * 50)
        print(f"Total test cases cached: {stats['total_test_cases']}")
        print(f"  Fresh:        {stats['fresh']}")
        print(f"  Suspect:      {stats['suspect']}")
        print(f"  Invalidated:  {stats['invalidated']}")
        print()
        print(f"Total runs recorded: {stats['total_runs']}")
        for outcome, count in stats["outcomes"].items():
            print(f"  {outcome:20s} {count}")
        print("─" * 50)

    elif cmd == "invalidate":
        if len(args) < 2:
            print("Usage: invalidate \"Test Case Name\"")
            return
        name = " ".join(args[1:])
        if invalidate(name):
            print(f"✅ Invalidated: {name}")
        else:
            print(f"❌ No test case named: {name}")

    elif cmd == "reset":
        confirm = input("Wipe entire cache? (yes/no): ").strip().lower()
        if confirm == "yes":
            reset()
        else:
            print("Aborted.")

    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    _cli()