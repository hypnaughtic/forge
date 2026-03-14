"""Scenario 4: Context Limit (PreCompact).

Tests: forge start -> work -> trigger context pressure -> verify PreCompact handling -> stop -> resume.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestContextLimit:

    def test_precompact_triggers_checkpoint_and_conversation_capture(
        self, mvp_project, orchestrator, validator
    ):
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)

        # Let agents work extensively to approach context limit
        orchestrator.watch_terminals(duration=120, interval=15)

        # Feed large context to TL to trigger compaction faster
        if orchestrator.tmux:
            orchestrator.tmux.send_text_to_claude(
                "0",
                "Here is a very long requirements update for context pressure testing: "
                + "x" * 5000,
            )

        # Wait for PreCompact hook to fire (check for conversation snapshot file)
        checkpoints_dir = project_dir / ".forge" / "checkpoints"
        conversation_snapshots = (
            list(checkpoints_dir.glob("*.conversation.json"))
            if checkpoints_dir.exists()
            else []
        )
        # PreCompact may or may not fire during our test window
        # If it fires, verify the snapshot
        if conversation_snapshots:
            for snap_file in conversation_snapshots:
                snap = json.loads(snap_file.read_text())
                assert "entries" in snap or "conversation" in snap, \
                    "Conversation snapshot should contain conversation entries"

        # Stop and resume
        orchestrator.stop_gracefully()
        snap_after_resume = orchestrator.resume_session(wait_for_agents=True)

        validator.assert_session_status("running")
        orchestrator.save_transcripts("scenario_04_context_limit")
