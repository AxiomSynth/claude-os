"""Tests for the simplified session state manager."""

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.session_state_manager import (
    STATE_FILENAME,
    end_session,
    get_session_status,
    start_session,
)


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project directory."""
    return str(tmp_path)


class TestStartSession:
    def test_creates_state_file(self, tmp_project):
        result = start_session(tmp_project, "Build feature X")
        assert result["success"] is True
        assert result["task"] == "Build feature X"

        state_file = os.path.join(tmp_project, STATE_FILENAME)
        assert os.path.exists(state_file)

        with open(state_file) as f:
            state = json.load(f)
        assert state["active"] is True
        assert state["last_task"] == "Build feature X"

    def test_includes_branch(self, tmp_project):
        result = start_session(tmp_project, "Fix bug", branch="fix/bug-123")
        assert result["branch"] == "fix/bug-123"

        with open(os.path.join(tmp_project, STATE_FILENAME)) as f:
            state = json.load(f)
        assert state["last_branch"] == "fix/bug-123"

    def test_stores_project_name(self, tmp_project):
        result = start_session(tmp_project, "Task", project_name="Sieve")
        assert result["project_name"] == "Sieve"

        with open(os.path.join(tmp_project, STATE_FILENAME)) as f:
            state = json.load(f)
        assert state["project_name"] == "Sieve"

    def test_falls_back_to_directory_name(self, tmp_project):
        result = start_session(tmp_project, "Task")
        assert result["project_name"] == os.path.basename(tmp_project)

    def test_reuses_project_name_from_previous_state(self, tmp_project):
        # First session sets project name
        start_session(tmp_project, "Task 1", project_name="Sieve")
        end_session(tmp_project)

        # Second session should reuse it without explicit project_name
        result = start_session(tmp_project, "Task 2")
        assert result["project_name"] == "Sieve"

    def test_rejects_when_already_active(self, tmp_project):
        start_session(tmp_project, "First task")
        result = start_session(tmp_project, "Second task")
        assert result["success"] is False
        assert "already active" in result["error"].lower()
        assert result["current_task"] == "First task"


class TestEndSession:
    def test_updates_state_file(self, tmp_project):
        start_session(tmp_project, "Build feature")
        result = end_session(tmp_project, one_liner="Feature done")

        assert result["success"] is True
        assert result["task"] == "Build feature"
        assert result["one_liner"] == "Feature done"
        assert result["stopped_at"] is not None

        with open(os.path.join(tmp_project, STATE_FILENAME)) as f:
            state = json.load(f)
        assert state["active"] is False
        assert state["one_liner"] == "Feature done"

    def test_rejects_when_no_active_session(self, tmp_project):
        result = end_session(tmp_project)
        assert result["success"] is False
        assert "no active session" in result["error"].lower()

    def test_preserves_project_name(self, tmp_project):
        start_session(tmp_project, "Task", project_name="Sieve")
        result = end_session(tmp_project)
        assert result["project_name"] == "Sieve"


class TestGetSessionStatus:
    def test_no_file_returns_inactive(self, tmp_project):
        status = get_session_status(tmp_project)
        assert status["active"] is False
        assert status["project_name"] is None
        assert status["last_task"] is None

    def test_active_session(self, tmp_project):
        start_session(tmp_project, "Build feature", branch="main", project_name="Sieve")
        status = get_session_status(tmp_project)

        assert status["active"] is True
        assert status["project_name"] == "Sieve"
        assert status["last_task"] == "Build feature"
        assert status["last_branch"] == "main"
        assert status["started_at"] is not None

    def test_ended_session(self, tmp_project):
        start_session(tmp_project, "Build feature")
        end_session(tmp_project, one_liner="Done")
        status = get_session_status(tmp_project)

        assert status["active"] is False
        assert status["last_task"] == "Build feature"
        assert status["one_liner"] == "Done"
        assert status["stopped_at"] is not None


class TestEdgeCases:
    def test_corrupted_state_file(self, tmp_project):
        """Corrupted state file should not crash."""
        state_file = os.path.join(tmp_project, STATE_FILENAME)
        with open(state_file, "w") as f:
            f.write("not valid json {{{")

        # Should return inactive, not crash
        status = get_session_status(tmp_project)
        assert status["active"] is False

        # Should be able to start fresh
        result = start_session(tmp_project, "Fresh start")
        assert result["success"] is True
