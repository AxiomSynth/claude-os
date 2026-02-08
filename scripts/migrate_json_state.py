#!/usr/bin/env python3
"""
Migrate existing claude-os-state.json files to SQLite database.

Usage:
    python scripts/migrate_json_state.py /path/to/project
    python scripts/migrate_json_state.py /path/to/project/claude-os-state.json
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.sqlite_manager import get_sqlite_manager


def migrate_state(json_path: str):
    """Migrate a claude-os-state.json file to SQLite."""

    json_path = Path(json_path).expanduser().resolve()

    # Handle both file path and directory path
    if json_path.is_dir():
        json_path = json_path / "claude-os-state.json"

    if not json_path.exists():
        print(f"❌ File not found: {json_path}")
        sys.exit(1)

    project_path = json_path.parent

    print(f"📂 Project: {project_path}")
    print(f"📄 JSON file: {json_path}")
    print()

    # Read JSON
    with open(json_path) as f:
        data = json.load(f)

    print("📊 JSON contents:")
    print(f"   Version: {data.get('version', 'unknown')}")

    db = get_sqlite_manager()
    conn = db.get_connection()
    cursor = conn.cursor()

    try:
        # 1. Create or get project
        project_name = project_path.name
        cursor.execute("SELECT id FROM projects WHERE path = ?", (str(project_path),))
        row = cursor.fetchone()

        if row:
            project_id = row['id']
            print(f"   ✓ Project exists (ID: {project_id})")
        else:
            cursor.execute(
                "INSERT INTO projects (name, path, description) VALUES (?, ?, ?)",
                (project_name, str(project_path), f"Migrated from JSON on {datetime.now().isoformat()}")
            )
            project_id = cursor.lastrowid
            print(f"   ✓ Project created (ID: {project_id})")

        # 2. Migrate statistics
        stats = data.get("statistics", {})
        if stats:
            print(f"\n📈 Statistics:")
            print(f"   Total sessions: {stats.get('total_sessions', 0)}")
            print(f"   Total memories saved: {stats.get('total_memories_saved', 0)}")
            print(f"   Total patterns: {stats.get('total_patterns_discovered', 0)}")
            print(f"   Avg duration: {stats.get('average_session_duration', 0):.1f} min")

            # Check if stats exist
            cursor.execute("SELECT id FROM session_statistics WHERE project_id = ?", (project_id,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE session_statistics SET
                        total_sessions = ?,
                        total_memories_saved = ?,
                        total_patterns_discovered = ?,
                        total_insights_extracted = ?,
                        average_session_duration = ?,
                        most_referenced_memories = ?,
                        updated_at = ?
                    WHERE project_id = ?
                """, (
                    stats.get('total_sessions', 0),
                    stats.get('total_memories_saved', 0),
                    stats.get('total_patterns_discovered', 0),
                    stats.get('total_insights_extracted', 0),
                    stats.get('average_session_duration', 0),
                    json.dumps(stats.get('most_referenced_memories', [])),
                    datetime.now().isoformat(),
                    project_id
                ))
                print("   ✓ Statistics updated")
            else:
                cursor.execute("""
                    INSERT INTO session_statistics
                    (project_id, total_sessions, total_memories_saved, total_patterns_discovered,
                     total_insights_extracted, average_session_duration, most_referenced_memories)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id,
                    stats.get('total_sessions', 0),
                    stats.get('total_memories_saved', 0),
                    stats.get('total_patterns_discovered', 0),
                    stats.get('total_insights_extracted', 0),
                    stats.get('average_session_duration', 0),
                    json.dumps(stats.get('most_referenced_memories', []))
                ))
                print("   ✓ Statistics created")

        # 3. Migrate preferences
        prefs = data.get("preferences", {})
        if prefs:
            print(f"\n⚙️  Preferences:")
            print(f"   Auto search on start: {prefs.get('auto_search_on_start', True)}")
            print(f"   Max memories to load: {prefs.get('max_memories_to_load', 5)}")

            extraction = prefs.get('session_extraction', {})

            cursor.execute("SELECT id FROM session_preferences WHERE project_id = ?", (project_id,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE session_preferences SET
                        auto_search_on_start = ?,
                        max_memories_to_load = ?,
                        search_days_back = ?,
                        include_pattern_search = ?,
                        proactive_suggestions = ?,
                        extraction_enabled = ?,
                        extraction_auto_prompt = ?,
                        extraction_min_confidence = ?,
                        extraction_auto_save_high = ?,
                        extraction_insight_types = ?,
                        updated_at = ?
                    WHERE project_id = ?
                """, (
                    1 if prefs.get('auto_search_on_start', True) else 0,
                    prefs.get('max_memories_to_load', 5),
                    prefs.get('search_days_back', 14),
                    1 if prefs.get('include_pattern_search', True) else 0,
                    1 if prefs.get('proactive_suggestions', True) else 0,
                    1 if extraction.get('enabled', True) else 0,
                    1 if extraction.get('auto_prompt_on_end', True) else 0,
                    extraction.get('min_confidence_threshold', 0.7),
                    1 if extraction.get('auto_save_high_confidence', False) else 0,
                    json.dumps(extraction.get('insight_types', ['decisions', 'patterns', 'solutions', 'blockers'])),
                    datetime.now().isoformat(),
                    project_id
                ))
                print("   ✓ Preferences updated")
            else:
                cursor.execute("""
                    INSERT INTO session_preferences
                    (project_id, auto_search_on_start, max_memories_to_load, search_days_back,
                     include_pattern_search, proactive_suggestions, extraction_enabled,
                     extraction_auto_prompt, extraction_min_confidence, extraction_auto_save_high,
                     extraction_insight_types)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id,
                    1 if prefs.get('auto_search_on_start', True) else 0,
                    prefs.get('max_memories_to_load', 5),
                    prefs.get('search_days_back', 14),
                    1 if prefs.get('include_pattern_search', True) else 0,
                    1 if prefs.get('proactive_suggestions', True) else 0,
                    1 if extraction.get('enabled', True) else 0,
                    1 if extraction.get('auto_prompt_on_end', True) else 0,
                    extraction.get('min_confidence_threshold', 0.7),
                    1 if extraction.get('auto_save_high_confidence', False) else 0,
                    json.dumps(extraction.get('insight_types', ['decisions', 'patterns', 'solutions', 'blockers']))
                ))
                print("   ✓ Preferences created")

        # 4. Migrate last session if exists
        last_session = data.get("last_session")
        if last_session:
            print(f"\n📝 Last session:")
            print(f"   Task: {last_session.get('task', 'unknown')}")
            print(f"   Duration: {last_session.get('duration_minutes', 0)} min")
            print(f"   Ended: {last_session.get('ended_at', 'unknown')}")

            # Create a historical session record
            cursor.execute("""
                INSERT INTO sessions
                (project_id, task, started_at, ended_at, duration_minutes, is_active,
                 work_completed, memories_saved, metadata)
                VALUES (?, ?, ?, ?, ?, 0, ?, ?, ?)
            """, (
                project_id,
                last_session.get('task', 'Migrated session'),
                last_session.get('ended_at', datetime.now().isoformat()),  # Approximate
                last_session.get('ended_at', datetime.now().isoformat()),
                last_session.get('duration_minutes', 0),
                json.dumps(last_session.get('work_completed', [])),
                last_session.get('memories_saved', 0),
                json.dumps({"migrated_from": "json", "migrated_at": datetime.now().isoformat()})
            ))
            print("   ✓ Last session imported as historical record")

        # 5. Check for current session (shouldn't migrate active sessions)
        current = data.get("current_session", {})
        if current.get("active"):
            print(f"\n⚠️  Active session found - NOT migrating (would lose context)")
            print(f"   Task: {current.get('task')}")
            print(f"   End this session first, then re-run migration")

        conn.commit()

        print(f"\n✅ Migration complete!")
        print(f"   Project ID: {project_id}")
        print(f"   Run '/claude-os-session status' in {project_name} to verify")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Migration failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate_json_state.py /path/to/project")
        print("   or: python scripts/migrate_json_state.py /path/to/claude-os-state.json")
        sys.exit(1)

    migrate_state(sys.argv[1])
