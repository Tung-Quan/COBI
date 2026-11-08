from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .calculations import calculate_application

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get("COBI_DB_PATH", ROOT / "data" / "checkout_credit.sqlite"))
SEED_PATH = ROOT / "data" / "seed_applications.json"


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS applications (
                application_id TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id TEXT NOT NULL REFERENCES applications(application_id),
                action TEXT NOT NULL,
                route TEXT,
                reason TEXT NOT NULL,
                actor TEXT NOT NULL DEFAULT 'Simulated credit officer',
                created_at TEXT NOT NULL,
                details_json TEXT NOT NULL DEFAULT '{}'
            );
            CREATE TABLE IF NOT EXISTS calculation_results (
                application_id TEXT PRIMARY KEY REFERENCES applications(application_id),
                assessment_json TEXT NOT NULL,
                routing_json TEXT NOT NULL,
                computed_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS audit_application_action ON audit_events(application_id, action);
            CREATE TRIGGER IF NOT EXISTS audit_events_no_update
            BEFORE UPDATE ON audit_events BEGIN
                SELECT RAISE(ABORT, 'audit events are append-only');
            END;
            CREATE TRIGGER IF NOT EXISTS audit_events_no_delete
            BEFORE DELETE ON audit_events BEGIN
                SELECT RAISE(ABORT, 'audit events are append-only');
            END;
            """
        )
        connection.execute("BEGIN IMMEDIATE")
        existing = connection.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        if existing == 0:
            seeds = json.loads(SEED_PATH.read_text(encoding="utf-8"))
            v2 = json.loads((ROOT / "data" / "demo_001_v2.json").read_text(encoding="utf-8"))
            seeds = [item | (v2 if item["application_id"] == v2["application_id"] else {"fixture_version": "seed-v2.0"})
                     for item in seeds]
            for item in seeds:
                if item["application_id"] == v2["application_id"]:
                    item.pop("risk_anchor", None)
                    item["evidence"]["reconciliation_notes"][1] = "Synthetic purchase equals loan principal plus stated own funds."
            now = datetime.now(timezone.utc).isoformat()
            connection.executemany(
                "INSERT INTO applications(application_id, data_json, created_at) VALUES (?, ?, ?)",
                [(item["application_id"], json.dumps(item, separators=(",", ":")), now) for item in seeds],
            )


def list_applications() -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute("SELECT data_json FROM applications ORDER BY created_at DESC, application_id").fetchall()
    return [json.loads(row["data_json"]) for row in rows]


def get_application(application_id: str, connection: sqlite3.Connection | None = None) -> dict[str, Any] | None:
    if connection is None:
        with connect() as own_connection:
            return get_application(application_id, own_connection)
    row = connection.execute("SELECT data_json FROM applications WHERE application_id = ?", (application_id,)).fetchone()
    return json.loads(row["data_json"]) if row else None


def create_application(data: dict[str, Any], audit_details: dict[str, Any]) -> None:
    with connect() as connection:
        connection.execute(
            "INSERT INTO applications(application_id, data_json, created_at) VALUES (?, ?, ?)",
            (data["application_id"], json.dumps(data, separators=(",", ":")), datetime.now(timezone.utc).isoformat()),
        )
        append_audit_event(data["application_id"], "application_received", None,
                           "Application received in the synthetic workbench.", audit_details, connection=connection)


def audit_history(application_id: str) -> list[dict[str, Any]]:
    with connect() as connection:
        rows = connection.execute(
            "SELECT event_id, action, route, reason, actor, created_at, details_json FROM audit_events "
            "WHERE application_id = ? ORDER BY event_id DESC",
            (application_id,),
        ).fetchall()
    return [{**dict(row), "details": json.loads(row["details_json"])} for row in rows]


def append_audit_event(application_id: str, action: str, route: str | None, reason: str,
                       details: dict[str, Any] | None = None, *,
                       connection: sqlite3.Connection | None = None) -> dict[str, Any]:
    if connection is None:
        with connect() as own_connection:
            return append_audit_event(application_id, action, route, reason, details, connection=own_connection)
    timestamp = datetime.now(timezone.utc).isoformat()
    cursor = connection.execute(
        "INSERT INTO audit_events(application_id, action, route, reason, created_at, details_json) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (application_id, action, route, reason, timestamp, json.dumps(details or {}, separators=(",", ":"))),
    )
    return {
        "event_id": cursor.lastrowid,
        "application_id": application_id,
        "action": action,
        "route": route,
        "reason": reason,
        "actor": "Simulated credit officer",
        "created_at": timestamp,
        "details": details or {},
    }


def revoke_consent(application: dict[str, Any], reason: str, details: dict[str, Any], connection: sqlite3.Connection) -> dict:
    application_id = application["application_id"]
    event = append_audit_event(application_id, "consent_revoked", None, reason, details, connection=connection)
    revoked = application | {"consent": False, "consent_revoked_at": event["created_at"]}
    connection.execute("UPDATE applications SET data_json = ? WHERE application_id = ?",
                       (json.dumps(revoked, separators=(",", ":")), application_id))
    connection.execute("DELETE FROM calculation_results WHERE application_id = ?", (application_id,))
    return event


def persist_calculation(application: dict[str, Any], assessment: dict[str, Any], routing: dict[str, Any]) -> None:
    """Persist the latest reproducible result; simulator calls do not use this."""
    with connect() as connection:
        connection.execute(
            "INSERT INTO calculation_results(application_id, assessment_json, routing_json, computed_at) "
            "SELECT application_id, ?, ?, ? FROM applications WHERE application_id = ? AND data_json = ? "
            "ON CONFLICT(application_id) DO UPDATE SET "
            "assessment_json = excluded.assessment_json, routing_json = excluded.routing_json, computed_at = excluded.computed_at",
            (json.dumps(assessment, separators=(",", ":")), json.dumps(routing, separators=(",", ":")),
             datetime.now(timezone.utc).isoformat(), application["application_id"], json.dumps(application, separators=(",", ":"))),
        )


def get_calculation_result(application_id: str) -> dict[str, Any] | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT assessment_json, routing_json, computed_at FROM calculation_results WHERE application_id = ?",
            (application_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "assessment": json.loads(row["assessment_json"]),
        "routing": json.loads(row["routing_json"]),
        "computed_at": row["computed_at"],
    }


def export_bundle() -> dict[str, Any]:
    applications: list[dict[str, Any]] = []
    for application in list_applications():
        result = calculate_application(application)
        persist_calculation(application, result.assessment, result.routing)
        applications.append({
            "application": application,
            "assessment": result.assessment,
            "routing": result.routing,
            "audit_history": audit_history(application["application_id"]),
        })
    return {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "data_classification": "Synthetic demonstration data only",
        "applications": applications,
    }
