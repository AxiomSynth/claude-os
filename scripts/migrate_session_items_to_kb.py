#!/usr/bin/env python3
"""
Migrate session_items from SQLite to project knowledge bases.

Reads all patterns, decisions, and blockers from the session_items table
and uploads them as documents to the appropriate project KB via the API.

This is a one-time migration script for the session management simplification.
"""

import sqlite3
import sys
import time
from pathlib import Path

import httpx

API_BASE = "http://localhost:8051"
DB_PATH = Path(__file__).parent.parent / "data" / "claude-os.db"

# All session items are Sieve-related (including worktree-named projects)
TARGET_KB = "Sieve-project_memories"


def get_session_items(db_path: Path) -> list[dict]:
    """Read all session_items joined with sessions and projects."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT
            si.id,
            si.item_type,
            si.description,
            si.resolved,
            si.created_at,
            s.task AS session_task,
            s.branch AS session_branch,
            p.name AS project_name
        FROM session_items si
        JOIN sessions s ON si.session_id = s.id
        JOIN projects p ON s.project_id = p.id
        ORDER BY si.item_type, si.created_at
    """)
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items


def format_document(item: dict) -> str:
    """Format a session item as a markdown document."""
    item_type = item["item_type"].capitalize()
    lines = [
        f"# {item_type}: {item['description']}",
        "",
        f"**Session**: {item['session_task']}",
        f"**Date**: {item['created_at']}",
        f"**Project**: {item['project_name']}",
    ]
    if item["session_branch"]:
        lines.append(f"**Branch**: {item['session_branch']}")
    if item["item_type"] == "blocker" and item["resolved"]:
        lines.append("**Status**: Resolved")
    return "\n".join(lines)


def upload_document(kb_name: str, filename: str, content: str) -> dict:
    """Upload a document to a knowledge base via the API."""
    with httpx.Client(timeout=60.0) as client:
        response = client.post(
            f"{API_BASE}/api/kb/{kb_name}/upload",
            files={"file": (filename, content.encode("utf-8"), "text/markdown")},
        )
        response.raise_for_status()
        return response.json()


def main():
    if not DB_PATH.exists():
        print(f"Database not found: {DB_PATH}")
        sys.exit(1)

    # Verify API is running
    try:
        resp = httpx.get(f"{API_BASE}/api/kb", timeout=5.0)
        resp.raise_for_status()
    except Exception as e:
        print(f"API not reachable at {API_BASE}: {e}")
        sys.exit(1)

    # Verify target KB exists
    kbs = resp.json().get("knowledge_bases", [])
    kb_names = [kb["name"] for kb in kbs]
    if TARGET_KB not in kb_names:
        print(f"Target KB '{TARGET_KB}' not found. Available: {kb_names}")
        sys.exit(1)

    items = get_session_items(DB_PATH)
    print(f"Found {len(items)} session items to migrate")

    by_type = {}
    for item in items:
        by_type.setdefault(item["item_type"], []).append(item)
    for t, group in by_type.items():
        print(f"  {t}: {len(group)}")

    if not items:
        print("Nothing to migrate.")
        return

    print(f"\nUploading to KB: {TARGET_KB}")
    print("-" * 60)

    succeeded = 0
    failed = 0

    for item in items:
        ts = item["created_at"].replace(" ", "T").replace(":", "")[:15]
        filename = f"migrated-{item['item_type']}-{ts}.md"
        content = format_document(item)

        try:
            result = upload_document(TARGET_KB, filename, content)
            succeeded += 1
            print(f"  OK: {filename}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {filename} - {e}")

        # Small delay to avoid overwhelming the API
        time.sleep(0.1)

    print("-" * 60)
    print(f"Done: {succeeded} succeeded, {failed} failed out of {len(items)} total")

    if failed == 0:
        print("\nAll items migrated successfully.")
        print("Verify with: curl -s 'http://localhost:8051/api/kb/Sieve-project_memories/search?query=pattern&top_k=5' | python3 -m json.tool")


if __name__ == "__main__":
    main()
