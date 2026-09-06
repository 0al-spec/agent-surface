"""Bounded ADP-02 safety-state SPIKE (offline, synthetic, not a runtime)."""
from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path


SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS grants (
  grant_id TEXT PRIMARY KEY, grant_hash TEXT NOT NULL, valid INTEGER NOT NULL,
  revision INTEGER NOT NULL, revoked INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY, lineage_id TEXT NOT NULL, grant_id TEXT NOT NULL,
  grant_hash TEXT NOT NULL, generation INTEGER NOT NULL, state TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS lineage_guards (
  lineage_id TEXT PRIMARY KEY, hard_limit INTEGER NOT NULL,
  count INTEGER NOT NULL DEFAULT 0, fenced INTEGER NOT NULL DEFAULT 0,
  fence_id TEXT
);
"""


@dataclass(frozen=True)
class Admission:
    outcome: str
    session_id: str
    generation: int
    fence_id: str | None = None


class SafetyStore:
    """One local SQLite authority. Inputs are fixed synthetic harness values."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self.db: sqlite3.Connection | None = None
        try:
            db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            db.execute("PRAGMA foreign_keys=ON")
            db.executescript(SCHEMA)
            self.db = db
        except (sqlite3.Error, OSError):
            try:
                db.close()
            except (NameError, sqlite3.Error):
                pass
            self.db = None

    def close(self) -> None:
        if self.db is not None:
            self.db.close()
            self.db = None

    def _run(self, fn):
        if self.db is None:
            return None
        try:
            return fn(self.db)
        except sqlite3.Error:
            try:
                self.db.rollback()
            except sqlite3.Error:
                pass
            return None

    def seed(self, *, grant_id: str, grant_hash: str, lineage_id: str,
             session_id: str, hard_limit: int = 2) -> bool:
        def op(db):
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO grants VALUES (?, ?, 1, 1, 0)",
                       (grant_id, grant_hash))
            db.execute("INSERT INTO lineage_guards(lineage_id, hard_limit) VALUES (?, ?)",
                       (lineage_id, hard_limit))
            db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, 1, 'active')",
                       (session_id, lineage_id, grant_id, grant_hash))
            db.commit()
            return True
        result = self._run(op)
        return result is True

    def revoke(self, grant_id: str) -> bool:
        def op(db):
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute("UPDATE grants SET revoked=1, revision=revision+1 "
                             "WHERE grant_id=?", (grant_id,))
            db.commit()
            return cur.rowcount == 1
        return self._run(op) is True

    def resume(self, session_id: str, expected_generation: int) -> str:
        """Increment only from exact current generation, retaining lineage."""
        def op(db):
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT generation, state, grant_id, grant_hash, lineage_id "
                             "FROM sessions WHERE session_id=?",
                             (session_id,)).fetchone()
            if row is None:
                db.rollback(); return "session_missing"
            current, state, grant_id, grant_hash, lineage_id = row
            grant = db.execute("SELECT valid, revoked, grant_hash FROM grants WHERE grant_id=?",
                               (grant_id,)).fetchone()
            guard = db.execute("SELECT fenced FROM lineage_guards WHERE lineage_id=?",
                               (lineage_id,)).fetchone()
            if grant is None or guard is None:
                db.rollback(); return "storage_unavailable"
            if not grant[0] or grant[1] or grant[2] != grant_hash:
                db.rollback(); return "denied_grant_revoked"
            if guard[0]:
                db.rollback(); return "denied_fenced"
            if expected_generation != current:
                db.rollback(); return "generation_invalid"
            if state != "interrupted":
                db.rollback(); return "session_state_invalid"
            db.execute("UPDATE sessions SET generation=?, state='active' WHERE session_id=?",
                       (current + 1, session_id))
            db.commit(); return "resumed"
        return self._run(op) or "storage_unavailable"

    def interrupt(self, session_id: str) -> bool:
        def op(db):
            db.execute("BEGIN IMMEDIATE")
            cur = db.execute("UPDATE sessions SET state='interrupted' "
                             "WHERE session_id=? AND state='active'", (session_id,))
            db.commit(); return cur.rowcount == 1
        return self._run(op) is True

    def admit(self, *, session_id: str, expected_generation: int,
              grant_id: str, grant_hash: str) -> Admission:
        """Atomically verify Grant/session/generation, fence, count, and admit."""
        def op(db):
            db.execute("BEGIN IMMEDIATE")
            session = db.execute("SELECT lineage_id, grant_id, grant_hash, generation, state "
                                 "FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            grant = db.execute("SELECT grant_hash, valid, revoked FROM grants WHERE grant_id=?",
                               (grant_id,)).fetchone()
            if session is None or grant is None:
                db.rollback(); return Admission("denied_authority", session_id, expected_generation)
            lineage, sgid, shash, generation, state = session
            if (sgid, shash) != (grant_id, grant_hash) or grant[0] != grant_hash:
                db.rollback(); return Admission("denied_authority", session_id, generation)
            if not grant[1] or grant[2]:
                db.rollback(); return Admission("denied_grant_revoked", session_id, generation)
            if expected_generation != generation:
                db.rollback(); return Admission("denied_generation_invalid", session_id, generation)
            if state != "active":
                db.rollback(); return Admission("denied_session_state", session_id, generation)
            fence, count, limit, fence_id = db.execute(
                "SELECT fenced, count, hard_limit, fence_id FROM lineage_guards WHERE lineage_id=?",
                (lineage,)).fetchone() or (None, None, None, None)
            if fence is None:
                db.rollback(); return Admission("storage_unavailable", session_id, generation)
            if fence:
                db.rollback(); return Admission("denied_fenced", session_id, generation, fence_id)
            if count >= limit:
                fence_id = "fence-" + uuid.uuid4().hex
                db.execute("UPDATE lineage_guards SET fenced=1, fence_id=? WHERE lineage_id=?",
                           (fence_id, lineage))
                db.commit()
                return Admission("guard_triggered", session_id, generation, fence_id)
            db.execute("UPDATE lineage_guards SET count=count+1 WHERE lineage_id=?", (lineage,))
            db.commit()
            return Admission("admitted", session_id, generation)
        result = self._run(op)
        return result or Admission("storage_unavailable", session_id, expected_generation)

    def new_session(self, *, session_id: str, lineage_id: str, grant_id: str,
                    grant_hash: str) -> str:
        """Create a generation-1 session only if its durable lineage is unfenced."""
        def op(db):
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT fenced FROM lineage_guards WHERE lineage_id=?",
                             (lineage_id,)).fetchone()
            grant = db.execute("SELECT valid, revoked, grant_hash FROM grants WHERE grant_id=?",
                               (grant_id,)).fetchone()
            if not row or not grant:
                db.rollback(); return "storage_unavailable"
            if row[0]:
                db.rollback(); return "denied_fenced"
            if not grant[0] or grant[1] or grant[2] != grant_hash:
                db.rollback(); return "denied_grant_revoked"
            db.execute("INSERT INTO sessions VALUES (?, ?, ?, ?, 1, 'active')",
                       (session_id, lineage_id, grant_id, grant_hash))
            db.commit(); return "session_created"
        return self._run(op) or "storage_unavailable"
