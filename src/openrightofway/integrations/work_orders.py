from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from openrightofway.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class WorkOrder:
    id: int
    title: str
    description: str
    priority: str
    latitude: float | None
    longitude: float | None
    evidence_path: str | None
    status: str


class WorkOrderManager:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS work_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    priority TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    evidence_path TEXT,
                    status TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create(self, title: str, description: str, priority: str = "high", latitude: float | None = None,
               longitude: float | None = None, evidence_path: str | None = None) -> WorkOrder:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "INSERT INTO work_orders (title, description, priority, latitude, longitude, evidence_path, status) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (title, description, priority, latitude, longitude, evidence_path, "open"),
            )
            conn.commit()
            wo_id = int(cur.lastrowid) if cur.lastrowid is not None else 0
        logger.info("Created work order %d", wo_id)
        return WorkOrder(
            id=wo_id,
            title=title,
            description=description,
            priority=priority,
            latitude=latitude,
            longitude=longitude,
            evidence_path=evidence_path,
            status="open",
        )

    def get(self, wo_id: int) -> WorkOrder | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT id, title, description, priority, latitude, longitude, evidence_path, status FROM work_orders WHERE id=?",
                (wo_id,),
            ).fetchone()
        if not row:
            return None
        return WorkOrder(*row)

    def update_status(self, wo_id: int, status: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute("UPDATE work_orders SET status=? WHERE id=?", (status, wo_id))
            conn.commit()
            return cur.rowcount > 0

