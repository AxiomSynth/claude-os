"""
Session State Manager for Claude OS.

Simple JSON-file-based session tracking. Learnings (patterns, decisions,
blockers) are saved directly to project KBs via upload_document, not stored
in session state.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

STATE_FILENAME = "claude-os-state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _state_path(project_path: str) -> Path:
    return Path(project_path).expanduser().resolve() / STATE_FILENAME


def _read_state(project_path: str) -> Dict[str, Any]:
    path = _state_path(project_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to read state file {path}: {e}")
        return {}


def _write_state(project_path: str, state: Dict[str, Any]) -> None:
    path = _state_path(project_path)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def start_session(
    project_path: str,
    task: str,
    branch: Optional[str] = None,
    project_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Start a new session. Returns session info."""
    state = _read_state(project_path)

    if state.get("active"):
        return {
            "success": False,
            "error": "Session already active",
            "current_task": state.get("last_task"),
        }

    now = _now_iso()
    new_state = {
        "project_name": project_name or state.get("project_name") or Path(project_path).name,
        "last_task": task,
        "last_branch": branch,
        "started_at": now,
        "stopped_at": None,
        "one_liner": None,
        "active": True,
    }
    _write_state(project_path, new_state)

    return {
        "success": True,
        "task": task,
        "branch": branch,
        "project_name": new_state["project_name"],
        "started_at": now,
    }


def end_session(
    project_path: str,
    one_liner: Optional[str] = None,
) -> Dict[str, Any]:
    """End the current session. Returns summary."""
    state = _read_state(project_path)

    if not state.get("active"):
        return {"success": False, "error": "No active session"}

    now = _now_iso()
    started = state.get("started_at", now)

    state["active"] = False
    state["stopped_at"] = now
    state["one_liner"] = one_liner
    _write_state(project_path, state)

    return {
        "success": True,
        "task": state.get("last_task"),
        "project_name": state.get("project_name"),
        "started_at": started,
        "stopped_at": now,
        "one_liner": one_liner,
    }


def get_session_status(project_path: str) -> Dict[str, Any]:
    """Get current session status."""
    state = _read_state(project_path)

    if not state:
        return {
            "active": False,
            "project_name": None,
            "last_task": None,
            "last_branch": None,
            "started_at": None,
            "stopped_at": None,
            "one_liner": None,
        }

    return {
        "active": state.get("active", False),
        "project_name": state.get("project_name"),
        "last_task": state.get("last_task"),
        "last_branch": state.get("last_branch"),
        "started_at": state.get("started_at"),
        "stopped_at": state.get("stopped_at"),
        "one_liner": state.get("one_liner"),
    }
