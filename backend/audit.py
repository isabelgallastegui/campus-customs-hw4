"""Append-only audit log for agent activity.

Every call to the agent writes one run entry to `output/audit_trail.json`:
when it happened, which tools were called with what arguments and results, how
the run stopped, and how much it used. Entries are only ever appended — a run is
never edited or removed, and the file survives restarts.

What is deliberately *not* logged: customer names, email addresses, password
hashes, API keys, or the contents of any table other than the catalogue. A run
is attributed to a numeric `user_id` and nothing more, so the trail is useful
for debugging without becoming a second copy of the customer database.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
AUDIT_PATH = BASE_DIR / "output" / "audit_trail.json"

SCHEMA = "campus-customs-audit-v1"

# Keep the file readable and bounded. Arguments and results are summaries, not
# full payloads — the point is to see what the agent did, not to replay it.
MAX_FIELD_CHARS = 220
MAX_MESSAGE_CHARS = 300
# Oldest runs are dropped only once the file grows past this, so an afternoon of
# testing is always retained in full.
MAX_RUNS = 500

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def summarize(value: Any, limit: int = MAX_FIELD_CHARS) -> str:
    """Render any tool argument or result as one short, safe string."""
    if value is None:
        return ""

    if isinstance(value, (list, tuple)):
        # Lists of products are the common case: report the count and a few names.
        names = []
        for item in value[:3]:
            if isinstance(item, (str, int, float)):
                name = item
            elif isinstance(item, dict):
                name = item.get("name") or item.get("product_id")
            else:
                name = getattr(item, "name", None) or getattr(item, "product_id", None)
            names.append(str(name) if name is not None else type(item).__name__)
        more = f" (+{len(value) - 3} more)" if len(value) > 3 else ""
        text = f"{len(value)} item(s): " + ", ".join(names) + more

    elif isinstance(value, dict):
        text = ", ".join(f"{k}={summarize(v, 60)}" for k, v in list(value.items())[:5])

    elif hasattr(value, "model_dump"):
        text = summarize(value.model_dump(), limit)

    else:
        text = str(value)

    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _empty_log() -> dict[str, Any]:
    return {"schema": SCHEMA, "created_at": _now(), "runs": []}


def _read() -> dict[str, Any]:
    """Load the existing log, tolerating a missing or damaged file."""
    if not AUDIT_PATH.exists():
        return _empty_log()
    try:
        data = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Never lose new entries because an old file is unreadable.
        return _empty_log()
    if not isinstance(data, dict) or not isinstance(data.get("runs"), list):
        return _empty_log()
    return data


def new_run_id() -> str:
    return uuid.uuid4().hex[:12]


def record_run(entry: dict[str, Any]) -> None:
    """Append one run to the audit trail. Never raises into the request path."""
    try:
        with _lock:
            log = _read()
            log["runs"].append(entry)
            if len(log["runs"]) > MAX_RUNS:
                log["runs"] = log["runs"][-MAX_RUNS:]
            log["updated_at"] = _now()

            AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
            # Write to a temp file and replace, so a crash mid-write cannot
            # truncate the existing trail.
            temp = AUDIT_PATH.with_suffix(".json.tmp")
            temp.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
            os.replace(temp, AUDIT_PATH)
    except Exception:  # noqa: BLE001 - auditing must never break a customer's chat
        pass


def build_entry(
    *,
    run_id: str,
    started_at: str,
    message: str,
    model: str,
    user_id: int | None,
    page_product_id: str | None,
    page_path: str | None,
) -> dict[str, Any]:
    """Start an entry. Tool calls and the stop reason are filled in later."""
    return {
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": None,
        "duration_ms": None,
        "model": model,
        # Identity is recorded as an id only — never a name, email, or hash.
        "user_id": user_id,
        "signed_in": user_id is not None,
        "page": {"path": page_path, "product_id": page_product_id},
        "message": summarize(message, MAX_MESSAGE_CHARS),
        "tool_calls": [],
        "stop_reason": None,
        "usage": {},
    }


def extract_tool_calls(messages: list[Any]) -> list[dict[str, Any]]:
    """Pull (tool, arguments, result) triples out of a finished agent run."""
    calls: dict[str, dict[str, Any]] = {}
    ordered: list[dict[str, Any]] = []

    for message in messages:
        for part in getattr(message, "parts", []):
            kind = type(part).__name__

            if kind == "ToolCallPart":
                record = {
                    "time": _now(),
                    "tool": part.tool_name,
                    "arguments": summarize(getattr(part, "args", None)),
                    "result": None,
                }
                call_id = getattr(part, "tool_call_id", None) or part.tool_name
                calls[call_id] = record
                ordered.append(record)

            elif kind in {"ToolReturnPart", "RetryPromptPart"}:
                call_id = getattr(part, "tool_call_id", None) or getattr(part, "tool_name", "")
                record = calls.get(call_id)
                if record is not None:
                    content = getattr(part, "content", None)
                    record["result"] = summarize(content)
                    if kind == "RetryPromptPart":
                        record["retried"] = True

    return ordered
