import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from src.io import write_json


def save_trace(state, folder="runs"):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    write_json(folder / (run_id + ".json"), state)
    with sqlite3.connect(folder / "traces.sqlite3") as db:
        db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created TEXT, status TEXT, reason TEXT, seconds REAL, tokens INTEGER, state TEXT)")
        db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?)", (run_id, datetime.now(timezone.utc).isoformat(), state["status"],
                   state.get("reason", ""), state.get("seconds", 0), state.get("tokens", 0), json.dumps(state)))
    return run_id
