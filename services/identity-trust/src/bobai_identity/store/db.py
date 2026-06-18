"""SQLite-backed store.

Privacy-first choices:
  * IP and device fingerprints are stored only as HMAC-SHA256 tokens (never raw PII).
  * The audit log is append-only and hash-chained, so any tampering is detectable.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import sqlite3
import threading
from dataclasses import dataclass, field


@dataclass
class UserProfile:
    """Rolling risk baseline for a user. Created lazily on first event."""

    user_id: str
    last_ts: float | None = None
    last_lat: float | None = None
    last_lon: float | None = None
    known_devices: list[str] = field(default_factory=list)  # HMAC tokens
    behavioral_baseline: dict[str, float] = field(default_factory=dict)  # feature -> EWMA mean
    event_count: int = 0


_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    last_ts REAL,
    last_lat REAL,
    last_lon REAL,
    known_devices TEXT NOT NULL DEFAULT '[]',
    behavioral_baseline TEXT NOT NULL DEFAULT '{}',
    event_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS decisions (
    decision_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ts REAL NOT NULL,
    risk_score REAL NOT NULL,
    band TEXT NOT NULL,
    action TEXT NOT NULL,
    required_aal TEXT NOT NULL,
    reason_codes TEXT NOT NULL,
    signals TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_decisions_user ON decisions(user_id, ts);
CREATE TABLE IF NOT EXISTS audit_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,
    ref TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS webauthn_credentials (
    user_id TEXT NOT NULL,
    credential_id TEXT NOT NULL,
    public_key TEXT NOT NULL,
    sign_count INTEGER NOT NULL DEFAULT 0,
    transports TEXT NOT NULL DEFAULT '[]',
    PRIMARY KEY (user_id, credential_id)
);
CREATE TABLE IF NOT EXISTS webauthn_challenges (
    user_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    challenge TEXT NOT NULL,
    created REAL NOT NULL,
    PRIMARY KEY (user_id, kind)
);
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    action TEXT NOT NULL,
    band TEXT NOT NULL,
    risk_score REAL NOT NULL,
    lat REAL,
    lon REAL,
    country TEXT,
    city TEXT,
    top_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_access_ts ON access_log(ts);
"""


class Store:
    def __init__(self, db_path: str, secret: str) -> None:
        self._secret = secret.encode("utf-8")
        self._lock = threading.Lock()
        if db_path != ":memory:":
            parent = os.path.dirname(os.path.abspath(db_path))
            os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    # ---- privacy: deterministic PII tokenization ----
    def tokenize(self, value: str | None) -> str | None:
        """HMAC-SHA256 token; deterministic so repeats match, but irreversible."""
        if value is None:
            return None
        return hmac.new(self._secret, value.encode("utf-8"), hashlib.sha256).hexdigest()

    # ---- user profiles ----
    def get_profile(self, user_id: str) -> UserProfile:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM user_profiles WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return UserProfile(user_id=user_id)
        return UserProfile(
            user_id=row["user_id"],
            last_ts=row["last_ts"],
            last_lat=row["last_lat"],
            last_lon=row["last_lon"],
            known_devices=json.loads(row["known_devices"]),
            behavioral_baseline=json.loads(row["behavioral_baseline"]),
            event_count=row["event_count"],
        )

    def save_profile(self, p: UserProfile) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO user_profiles
                       (user_id, last_ts, last_lat, last_lon, known_devices,
                        behavioral_baseline, event_count)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET
                       last_ts=excluded.last_ts, last_lat=excluded.last_lat,
                       last_lon=excluded.last_lon, known_devices=excluded.known_devices,
                       behavioral_baseline=excluded.behavioral_baseline,
                       event_count=excluded.event_count""",
                (
                    p.user_id, p.last_ts, p.last_lat, p.last_lon,
                    json.dumps(p.known_devices), json.dumps(p.behavioral_baseline),
                    p.event_count,
                ),
            )
            self._conn.commit()

    # ---- decisions ----
    def save_decision(self, decision: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO decisions
                       (decision_id, user_id, event_type, ts, risk_score, band,
                        action, required_aal, reason_codes, signals)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    decision["decision_id"], decision["user_id"], decision["event_type"],
                    decision["timestamp"], decision["risk_score"], decision["band"],
                    decision["action"], decision["required_aal"],
                    json.dumps(decision["reason_codes"]), json.dumps(decision["signals"]),
                ),
            )
            self._conn.commit()

    def recent_decisions(self, user_id: str | None = None, limit: int = 100) -> list[dict]:
        with self._lock:
            if user_id:
                rows = self._conn.execute(
                    "SELECT * FROM decisions WHERE user_id = ? ORDER BY ts DESC LIMIT ?",
                    (user_id, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM decisions ORDER BY ts DESC LIMIT ?", (limit,)
                ).fetchall()
        out = []
        for r in rows:
            d = dict(r)
            d["reason_codes"] = json.loads(d["reason_codes"])
            d["signals"] = json.loads(d["signals"])
            out.append(d)
        return out

    # ---- tamper-evident audit log (hash chain) ----
    def _genesis_hash(self) -> str:
        return hashlib.sha256(b"BOBAI-AUDIT-GENESIS" + self._secret).hexdigest()

    def append_audit(self, kind: str, ref: str, payload: dict, ts: float) -> str:
        """Append an append-only, hash-chained audit entry. Returns the entry hash."""
        payload_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        with self._lock:
            prev = self._conn.execute(
                "SELECT entry_hash FROM audit_log ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            prev_hash = prev["entry_hash"] if prev else self._genesis_hash()
            entry_hash = hashlib.sha256(
                f"{prev_hash}|{ts}|{kind}|{ref}|{payload_hash}".encode("utf-8")
            ).hexdigest()
            self._conn.execute(
                """INSERT INTO audit_log (ts, kind, ref, payload_hash, prev_hash, entry_hash)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (ts, kind, ref, payload_hash, prev_hash, entry_hash),
            )
            self._conn.commit()
        return entry_hash

    def verify_audit_chain(self) -> dict:
        """Recompute the chain; report whether it is intact and where it breaks."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM audit_log ORDER BY seq ASC"
            ).fetchall()
        prev_hash = self._genesis_hash()
        for r in rows:
            expected = hashlib.sha256(
                f"{prev_hash}|{r['ts']}|{r['kind']}|{r['ref']}|{r['payload_hash']}".encode("utf-8")
            ).hexdigest()
            if r["prev_hash"] != prev_hash or r["entry_hash"] != expected:
                return {"intact": False, "broken_at_seq": r["seq"], "entries": len(rows)}
            prev_hash = r["entry_hash"]
        return {"intact": True, "broken_at_seq": None, "entries": len(rows)}

    # ---- WebAuthn credential / challenge storage ----
    def save_challenge(self, user_id: str, kind: str, challenge_b64: str, ts: float) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO webauthn_challenges (user_id, kind, challenge, created)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id, kind) DO UPDATE SET
                       challenge=excluded.challenge, created=excluded.created""",
                (user_id, kind, challenge_b64, ts),
            )
            self._conn.commit()

    def pop_challenge(self, user_id: str, kind: str) -> str | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT challenge FROM webauthn_challenges WHERE user_id = ? AND kind = ?",
                (user_id, kind),
            ).fetchone()
            if row:
                self._conn.execute(
                    "DELETE FROM webauthn_challenges WHERE user_id = ? AND kind = ?",
                    (user_id, kind),
                )
                self._conn.commit()
        return row["challenge"] if row else None

    def save_credential(
        self, user_id: str, credential_id: str, public_key: str, sign_count: int, transports: list[str]
    ) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO webauthn_credentials
                       (user_id, credential_id, public_key, sign_count, transports)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT(user_id, credential_id) DO UPDATE SET
                       public_key=excluded.public_key, sign_count=excluded.sign_count,
                       transports=excluded.transports""",
                (user_id, credential_id, public_key, sign_count, json.dumps(transports)),
            )
            self._conn.commit()

    def get_credentials(self, user_id: str) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM webauthn_credentials WHERE user_id = ?", (user_id,)
            ).fetchall()
        return [
            {
                "credential_id": r["credential_id"],
                "public_key": r["public_key"],
                "sign_count": r["sign_count"],
                "transports": json.loads(r["transports"]),
            }
            for r in rows
        ]

    def update_sign_count(self, user_id: str, credential_id: str, sign_count: int) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE webauthn_credentials SET sign_count = ? WHERE user_id = ? AND credential_id = ?",
                (sign_count, user_id, credential_id),
            )
            self._conn.commit()

    # ---- access log + analytics ----
    def record_access(
        self, ts: float, user_id: str, event_type: str, action: str, band: str,
        risk_score: float, lat: float | None, lon: float | None,
        country: str | None, city: str | None, top_reason: str | None,
    ) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO access_log
                       (ts, user_id, event_type, action, band, risk_score,
                        lat, lon, country, city, top_reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (ts, user_id, event_type, action, band, risk_score,
                 lat, lon, country, city, top_reason),
            )
            self._conn.commit()

    def access_recent(self, limit: int = 200) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM access_log ORDER BY ts DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(r) for r in rows]

    def analytics_summary(self) -> dict:
        with self._lock:
            total = self._conn.execute("SELECT COUNT(*) c FROM access_log").fetchone()["c"]
            by_action = {
                r["action"]: r["c"]
                for r in self._conn.execute(
                    "SELECT action, COUNT(*) c FROM access_log GROUP BY action"
                ).fetchall()
            }
            by_band = {
                r["band"]: r["c"]
                for r in self._conn.execute(
                    "SELECT band, COUNT(*) c FROM access_log GROUP BY band"
                ).fetchall()
            }
            by_country = {
                (r["country"] or "Unknown"): r["c"]
                for r in self._conn.execute(
                    "SELECT country, COUNT(*) c FROM access_log GROUP BY country "
                    "ORDER BY c DESC LIMIT 10"
                ).fetchall()
            }
            top_reasons = [
                {"reason": r["top_reason"], "count": r["c"]}
                for r in self._conn.execute(
                    "SELECT top_reason, COUNT(*) c FROM access_log "
                    "WHERE top_reason IS NOT NULL GROUP BY top_reason ORDER BY c DESC LIMIT 6"
                ).fetchall()
            ]
            distinct_users = self._conn.execute(
                "SELECT COUNT(DISTINCT user_id) c FROM access_log"
            ).fetchone()["c"]
        step_up = by_action.get("step_up", 0)
        deny = by_action.get("deny", 0)
        return {
            "total_events": total,
            "distinct_users": distinct_users,
            "by_action": by_action,
            "by_band": by_band,
            "by_country": by_country,
            "top_reasons": top_reasons,
            "step_up_count": step_up,
            "deny_count": deny,
            "step_up_rate": round((step_up + deny) / total, 3) if total else 0.0,
        }

    def close(self) -> None:
        with self._lock:
            self._conn.close()
