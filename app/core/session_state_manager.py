"""
Session State Manager for Claude OS.
Provides session management with SQLite storage and JSON export for git-trackability.

Hybrid approach:
- SQLite: Primary storage (queryable history, cross-project analytics)
- JSON: Export on session end (git-trackable snapshot per project)
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.sqlite_manager import get_sqlite_manager

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PYDANTIC MODELS (for API responses and validation)
# ═══════════════════════════════════════════════════════════════════════════

class SessionExtractionPrefs(BaseModel):
    """Preferences for session history extraction."""
    enabled: bool = True
    auto_prompt_on_end: bool = True
    min_confidence_threshold: float = 0.7
    auto_save_high_confidence: bool = False
    insight_types: List[str] = Field(
        default=["decisions", "patterns", "solutions", "blockers"]
    )


class SessionPreferences(BaseModel):
    """User preferences for session behavior."""
    auto_search_on_start: bool = True
    max_memories_to_load: int = 5
    search_days_back: int = 14
    include_pattern_search: bool = True
    proactive_suggestions: bool = True
    session_extraction: SessionExtractionPrefs = Field(default_factory=SessionExtractionPrefs)


class CurrentSession(BaseModel):
    """Current active session state."""
    id: Optional[int] = None
    active: bool = False
    started_at: Optional[str] = None
    task: Optional[str] = None
    project: Optional[str] = None
    branch: Optional[str] = None
    context: List[str] = Field(default_factory=list)
    decisions_made: List[str] = Field(default_factory=list)
    blockers: List[str] = Field(default_factory=list)
    patterns_discovered: List[str] = Field(default_factory=list)
    builtin_session_id: Optional[str] = None


class LastSession(BaseModel):
    """Summary of the last completed session."""
    id: int
    ended_at: str
    duration_minutes: int
    task: Optional[str] = None
    work_completed: List[str] = Field(default_factory=list)
    memories_saved: int = 0


class SessionStatistics(BaseModel):
    """Cumulative statistics across all sessions."""
    total_sessions: int = 0
    total_memories_saved: int = 0
    total_patterns_discovered: int = 0
    total_insights_extracted: int = 0
    total_duration_minutes: int = 0
    average_session_duration: float = 0.0
    most_referenced_memories: List[str] = Field(default_factory=list)


class SessionFlags(BaseModel):
    """Flags for pending actions."""
    needs_memory_consolidation: bool = False
    has_unresolved_blockers: bool = False
    patterns_ready_to_document: bool = False


class SessionState(BaseModel):
    """Complete session state schema (for API responses)."""
    version: str = "2.0.0"
    current_session: CurrentSession = Field(default_factory=CurrentSession)
    last_session: Optional[LastSession] = None
    statistics: SessionStatistics = Field(default_factory=SessionStatistics)
    flags: SessionFlags = Field(default_factory=SessionFlags)
    preferences: SessionPreferences = Field(default_factory=SessionPreferences)
    recent_sessions: List[Dict[str, Any]] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# STATE MANAGER (SQLite-backed)
# ═══════════════════════════════════════════════════════════════════════════

class SessionStateManager:
    """
    Manages session state with SQLite storage.

    Features:
    - Full session history (queryable)
    - Cross-project analytics
    - JSON export for git-trackability
    """

    JSON_EXPORT_FILENAME = "claude-os-state.json"

    def __init__(self, project_path: str):
        """
        Initialize manager for a specific project.

        Args:
            project_path: Absolute path to project directory
        """
        self.project_path = Path(project_path).expanduser().resolve()
        self.project_name = self.project_path.name
        self.db = get_sqlite_manager()
        self._project_id: Optional[int] = None

    def _now_iso(self) -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat()

    def _get_project_id(self) -> int:
        """Get or create project in database."""
        if self._project_id is not None:
            return self._project_id

        conn = self.db.get_connection()
        try:
            cursor = conn.cursor()

            # Try to find existing project
            cursor.execute(
                "SELECT id FROM projects WHERE path = ?",
                (str(self.project_path),)
            )
            row = cursor.fetchone()

            if row:
                self._project_id = row['id']
            else:
                # Create new project
                cursor.execute(
                    """
                    INSERT INTO projects (name, path, description)
                    VALUES (?, ?, ?)
                    """,
                    (self.project_name, str(self.project_path), f"Auto-created for {self.project_name}")
                )
                conn.commit()
                self._project_id = cursor.lastrowid

                # Initialize statistics and preferences
                cursor.execute(
                    "INSERT INTO session_statistics (project_id) VALUES (?)",
                    (self._project_id,)
                )
                cursor.execute(
                    "INSERT INTO session_preferences (project_id) VALUES (?)",
                    (self._project_id,)
                )
                conn.commit()

            return self._project_id
        finally:
            conn.close()

    def _get_active_session(self, conn) -> Optional[Dict[str, Any]]:
        """Get the currently active session if any."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, task, branch, started_at, builtin_session_id, metadata
            FROM sessions
            WHERE project_id = ? AND is_active = 1
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (self._get_project_id(),)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def _get_session_items(self, conn, session_id: int, item_type: Optional[str] = None) -> List[str]:
        """Get items (blockers, patterns, etc.) for a session."""
        cursor = conn.cursor()
        if item_type:
            cursor.execute(
                """
                SELECT description FROM session_items
                WHERE session_id = ? AND item_type = ?
                ORDER BY created_at
                """,
                (session_id, item_type)
            )
        else:
            cursor.execute(
                "SELECT description FROM session_items WHERE session_id = ? ORDER BY created_at",
                (session_id,)
            )
        return [row['description'] for row in cursor.fetchall()]

    def _get_statistics(self, conn) -> Dict[str, Any]:
        """Get session statistics for project."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT total_sessions, total_memories_saved, total_patterns_discovered,
                   total_insights_extracted, total_duration_minutes, average_session_duration,
                   most_referenced_memories
            FROM session_statistics
            WHERE project_id = ?
            """,
            (self._get_project_id(),)
        )
        row = cursor.fetchone()
        if row:
            return {
                "total_sessions": row['total_sessions'],
                "total_memories_saved": row['total_memories_saved'],
                "total_patterns_discovered": row['total_patterns_discovered'],
                "total_insights_extracted": row['total_insights_extracted'],
                "total_duration_minutes": row['total_duration_minutes'],
                "average_session_duration": row['average_session_duration'],
                "most_referenced_memories": json.loads(row['most_referenced_memories'] or '[]')
            }
        return SessionStatistics().model_dump()

    def _get_preferences(self, conn) -> Dict[str, Any]:
        """Get session preferences for project."""
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT auto_search_on_start, max_memories_to_load, search_days_back,
                   include_pattern_search, proactive_suggestions, extraction_enabled,
                   extraction_auto_prompt, extraction_min_confidence, extraction_auto_save_high,
                   extraction_insight_types
            FROM session_preferences
            WHERE project_id = ?
            """,
            (self._get_project_id(),)
        )
        row = cursor.fetchone()
        if row:
            return {
                "auto_search_on_start": bool(row['auto_search_on_start']),
                "max_memories_to_load": row['max_memories_to_load'],
                "search_days_back": row['search_days_back'],
                "include_pattern_search": bool(row['include_pattern_search']),
                "proactive_suggestions": bool(row['proactive_suggestions']),
                "session_extraction": {
                    "enabled": bool(row['extraction_enabled']),
                    "auto_prompt_on_end": bool(row['extraction_auto_prompt']),
                    "min_confidence_threshold": row['extraction_min_confidence'],
                    "auto_save_high_confidence": bool(row['extraction_auto_save_high']),
                    "insight_types": json.loads(row['extraction_insight_types'] or '[]')
                }
            }
        return SessionPreferences().model_dump()

    def get_state(self) -> SessionState:
        """
        Get complete session state for project.

        Returns:
            SessionState object with current session, stats, preferences
        """
        conn = self.db.get_connection()
        try:
            project_id = self._get_project_id()

            # Get active session
            active_session = self._get_active_session(conn)
            current = CurrentSession()

            if active_session:
                current = CurrentSession(
                    id=active_session['id'],
                    active=True,
                    started_at=active_session['started_at'],
                    task=active_session['task'],
                    project=str(self.project_path),
                    branch=active_session['branch'],
                    builtin_session_id=active_session['builtin_session_id'],
                    context=self._get_session_items(conn, active_session['id'], 'context'),
                    blockers=self._get_session_items(conn, active_session['id'], 'blocker'),
                    patterns_discovered=self._get_session_items(conn, active_session['id'], 'pattern'),
                    decisions_made=self._get_session_items(conn, active_session['id'], 'decision')
                )

            # Get last completed session
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, task, ended_at, duration_minutes, work_completed, memories_saved
                FROM sessions
                WHERE project_id = ? AND is_active = 0
                ORDER BY ended_at DESC
                LIMIT 1
                """,
                (project_id,)
            )
            last_row = cursor.fetchone()
            last_session = None
            if last_row:
                last_session = LastSession(
                    id=last_row['id'],
                    ended_at=last_row['ended_at'],
                    duration_minutes=last_row['duration_minutes'] or 0,
                    task=last_row['task'],
                    work_completed=json.loads(last_row['work_completed'] or '[]'),
                    memories_saved=last_row['memories_saved'] or 0
                )

            # Get recent sessions (last 10)
            cursor.execute(
                """
                SELECT id, task, branch, started_at, ended_at, duration_minutes, memories_saved
                FROM sessions
                WHERE project_id = ?
                ORDER BY started_at DESC
                LIMIT 10
                """,
                (project_id,)
            )
            recent_sessions = [dict(row) for row in cursor.fetchall()]

            # Check for unresolved blockers
            cursor.execute(
                """
                SELECT COUNT(*) as count FROM session_items si
                JOIN sessions s ON si.session_id = s.id
                WHERE s.project_id = ? AND si.item_type = 'blocker' AND si.resolved = 0
                """,
                (project_id,)
            )
            unresolved_count = cursor.fetchone()['count']

            flags = SessionFlags(
                has_unresolved_blockers=unresolved_count > 0,
                patterns_ready_to_document=len(current.patterns_discovered) > 0 if current.active else False
            )

            return SessionState(
                current_session=current,
                last_session=last_session,
                statistics=SessionStatistics(**self._get_statistics(conn)),
                flags=flags,
                preferences=SessionPreferences(**self._get_preferences(conn)),
                recent_sessions=recent_sessions
            )
        finally:
            conn.close()

    def start_session(self, task: str, branch: Optional[str] = None) -> Dict[str, Any]:
        """
        Start a new session.

        Args:
            task: Description of the task/goal
            branch: Optional git branch name

        Returns:
            Dict with session info and loaded context
        """
        conn = self.db.get_connection()
        try:
            project_id = self._get_project_id()

            # Check for existing active session
            active = self._get_active_session(conn)
            if active:
                return {
                    "success": False,
                    "error": "Session already active",
                    "current_task": active['task'],
                    "session_id": active['id']
                }

            # Create new session
            cursor = conn.cursor()
            started_at = self._now_iso()
            cursor.execute(
                """
                INSERT INTO sessions (project_id, task, branch, started_at, is_active)
                VALUES (?, ?, ?, ?, 1)
                """,
                (project_id, task, branch, started_at)
            )
            conn.commit()
            session_id = cursor.lastrowid

            return {
                "success": True,
                "session_id": session_id,
                "task": task,
                "branch": branch,
                "started_at": started_at,
                "preferences": self._get_preferences(conn)
            }
        finally:
            conn.close()

    def end_session(self, work_completed: Optional[List[str]] = None,
                    memories_saved: int = 0) -> Dict[str, Any]:
        """
        End the current session and record summary.

        Args:
            work_completed: List of completed work items
            memories_saved: Number of memories saved during session

        Returns:
            Dict with session summary
        """
        conn = self.db.get_connection()
        try:
            active = self._get_active_session(conn)
            if not active:
                return {
                    "success": False,
                    "error": "No active session"
                }

            session_id = active['id']
            ended_at = self._now_iso()

            # Calculate duration
            started = datetime.fromisoformat(active['started_at'].replace('Z', '+00:00'))
            ended = datetime.now(timezone.utc)
            duration_minutes = int((ended - started).total_seconds() / 60)

            # Get patterns count for stats update
            patterns_count = len(self._get_session_items(conn, session_id, 'pattern'))

            # Update session
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE sessions
                SET is_active = 0, ended_at = ?, duration_minutes = ?,
                    work_completed = ?, memories_saved = ?
                WHERE id = ?
                """,
                (ended_at, duration_minutes, json.dumps(work_completed or []),
                 memories_saved, session_id)
            )

            # Update statistics
            cursor.execute(
                """
                UPDATE session_statistics
                SET total_sessions = total_sessions + 1,
                    total_memories_saved = total_memories_saved + ?,
                    total_patterns_discovered = total_patterns_discovered + ?,
                    total_duration_minutes = total_duration_minutes + ?,
                    average_session_duration = (total_duration_minutes + ?) * 1.0 / (total_sessions + 1),
                    updated_at = ?
                WHERE project_id = ?
                """,
                (memories_saved, patterns_count, duration_minutes, duration_minutes,
                 self._now_iso(), self._get_project_id())
            )
            conn.commit()

            # Export to JSON for git-trackability
            self._export_json()

            return {
                "success": True,
                "session_id": session_id,
                "task": active['task'],
                "duration_minutes": duration_minutes,
                "work_completed": work_completed or [],
                "memories_saved": memories_saved,
                "patterns_discovered": patterns_count,
                "ended_at": ended_at
            }
        finally:
            conn.close()

    def add_blocker(self, description: str) -> Dict[str, Any]:
        """Add a blocker to the current session."""
        return self._add_item('blocker', description)

    def add_pattern(self, description: str) -> Dict[str, Any]:
        """Add a discovered pattern to the current session."""
        return self._add_item('pattern', description)

    def add_decision(self, description: str) -> Dict[str, Any]:
        """Add a decision made during the current session."""
        return self._add_item('decision', description)

    def add_context(self, memory_id: str) -> Dict[str, Any]:
        """Add a loaded memory to session context."""
        return self._add_item('context', memory_id)

    def _add_item(self, item_type: str, description: str) -> Dict[str, Any]:
        """Add an item to the current session."""
        conn = self.db.get_connection()
        try:
            active = self._get_active_session(conn)
            if not active:
                return {"success": False, "error": "No active session"}

            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO session_items (session_id, item_type, description)
                VALUES (?, ?, ?)
                """,
                (active['id'], item_type, description)
            )
            conn.commit()

            items = self._get_session_items(conn, active['id'], item_type)
            return {
                "success": True,
                "item_type": item_type,
                "items": items
            }
        finally:
            conn.close()

    def resolve_blocker(self, index: int) -> Dict[str, Any]:
        """Mark a blocker as resolved by index."""
        conn = self.db.get_connection()
        try:
            active = self._get_active_session(conn)
            if not active:
                return {"success": False, "error": "No active session"}

            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, description FROM session_items
                WHERE session_id = ? AND item_type = 'blocker' AND resolved = 0
                ORDER BY created_at
                """,
                (active['id'],)
            )
            blockers = cursor.fetchall()

            if 0 <= index < len(blockers):
                blocker_id = blockers[index]['id']
                cursor.execute(
                    "UPDATE session_items SET resolved = 1 WHERE id = ?",
                    (blocker_id,)
                )
                conn.commit()
                return {
                    "success": True,
                    "resolved": blockers[index]['description']
                }

            return {"success": False, "error": "Invalid blocker index"}
        finally:
            conn.close()

    def get_status(self) -> Dict[str, Any]:
        """Get current session status summary."""
        conn = self.db.get_connection()
        try:
            project_id = self._get_project_id()
            active = self._get_active_session(conn)

            status = {
                "project_path": str(self.project_path),
                "project_name": self.project_name,
                "session_active": active is not None,
                "statistics": self._get_statistics(conn)
            }

            if active:
                started = datetime.fromisoformat(active['started_at'].replace('Z', '+00:00'))
                duration = datetime.now(timezone.utc) - started

                status["current_session"] = {
                    "id": active['id'],
                    "task": active['task'],
                    "branch": active['branch'],
                    "started_at": active['started_at'],
                    "duration_minutes": int(duration.total_seconds() / 60),
                    "context_count": len(self._get_session_items(conn, active['id'], 'context')),
                    "blocker_count": len(self._get_session_items(conn, active['id'], 'blocker')),
                    "pattern_count": len(self._get_session_items(conn, active['id'], 'pattern')),
                    "decision_count": len(self._get_session_items(conn, active['id'], 'decision'))
                }

            # Get last session
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT task, ended_at, duration_minutes
                FROM sessions
                WHERE project_id = ? AND is_active = 0
                ORDER BY ended_at DESC
                LIMIT 1
                """,
                (project_id,)
            )
            last = cursor.fetchone()
            if last:
                status["last_session"] = dict(last)

            return status
        finally:
            conn.close()

    def _export_json(self) -> None:
        """Export current state to JSON file for git-trackability."""
        try:
            state = self.get_state()
            export_path = self.project_path / self.JSON_EXPORT_FILENAME

            export_data = {
                "version": state.version,
                "exported_at": self._now_iso(),
                "project": str(self.project_path),
                "last_session": state.last_session.model_dump() if state.last_session else None,
                "statistics": state.statistics.model_dump(),
                "preferences": state.preferences.model_dump(),
                "flags": state.flags.model_dump()
            }

            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)

            logger.info(f"Exported session state to {export_path}")
        except Exception as e:
            logger.error(f"Failed to export JSON: {e}")

    # ═══════════════════════════════════════════════════════════════════════
    # CROSS-PROJECT QUERIES (class methods)
    # ═══════════════════════════════════════════════════════════════════════

    @classmethod
    def list_all_sessions(cls, limit: int = 50) -> List[Dict[str, Any]]:
        """List sessions across all projects."""
        db = get_sqlite_manager()
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT s.id, s.task, s.branch, s.started_at, s.ended_at,
                       s.duration_minutes, s.is_active, p.name as project_name, p.path as project_path
                FROM sessions s
                JOIN projects p ON s.project_id = p.id
                ORDER BY s.started_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @classmethod
    def list_all_blockers(cls, unresolved_only: bool = True) -> List[Dict[str, Any]]:
        """List blockers across all projects."""
        db = get_sqlite_manager()
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT si.id, si.description, si.resolved, si.created_at,
                       s.task, p.name as project_name, p.path as project_path
                FROM session_items si
                JOIN sessions s ON si.session_id = s.id
                JOIN projects p ON s.project_id = p.id
                WHERE si.item_type = 'blocker'
            """
            if unresolved_only:
                query += " AND si.resolved = 0"
            query += " ORDER BY si.created_at DESC"

            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @classmethod
    def list_all_patterns(cls, limit: int = 100) -> List[Dict[str, Any]]:
        """List patterns discovered across all projects."""
        db = get_sqlite_manager()
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT si.id, si.description, si.created_at,
                       s.task, p.name as project_name, p.path as project_path
                FROM session_items si
                JOIN sessions s ON si.session_id = s.id
                JOIN projects p ON s.project_id = p.id
                WHERE si.item_type = 'pattern'
                ORDER BY si.created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @classmethod
    def get_global_statistics(cls) -> Dict[str, Any]:
        """Get aggregated statistics across all projects."""
        db = get_sqlite_manager()
        conn = db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT
                    COUNT(DISTINCT project_id) as total_projects,
                    SUM(total_sessions) as total_sessions,
                    SUM(total_memories_saved) as total_memories_saved,
                    SUM(total_patterns_discovered) as total_patterns_discovered,
                    SUM(total_duration_minutes) as total_duration_minutes,
                    AVG(average_session_duration) as avg_session_duration
                FROM session_statistics
                """
            )
            row = cursor.fetchone()
            return {
                "total_projects": row['total_projects'] or 0,
                "total_sessions": row['total_sessions'] or 0,
                "total_memories_saved": row['total_memories_saved'] or 0,
                "total_patterns_discovered": row['total_patterns_discovered'] or 0,
                "total_duration_minutes": row['total_duration_minutes'] or 0,
                "average_session_duration": row['avg_session_duration'] or 0.0
            }
        finally:
            conn.close()
