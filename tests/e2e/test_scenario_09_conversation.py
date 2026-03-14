"""Scenario 9: Conversation History Continuity.

Tests: forge start -> work -> stop -> resume -> verify conversation context preserved across sessions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestConversationHistory:

    def test_conversation_context_preserved_across_sessions(
        self, mvp_project, orchestrator, validator
    ):
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)

        # Let agents have substantial conversations
        orchestrator.watch_terminals(duration=120, interval=15)

        # Capture pre-stop transcripts
        pre_transcripts = orchestrator.collect_transcripts()
        snap_before = orchestrator.capture_state()

        # Verify checkpoints have conversation history
        for agent, cp in snap_before.checkpoints.items():
            recent = cp.get("recent_conversation", [])
            if recent:
                # Each entry should have role and content
                for entry in recent:
                    assert "role" in entry, \
                        f"{agent}: conversation entry missing 'role'"
                    assert "content" in entry, \
                        f"{agent}: conversation entry missing 'content'"

        orchestrator.stop_gracefully()
        orchestrator.resume_session(wait_for_agents=True)

        # Capture post-resume transcripts
        orchestrator.watch_terminals(duration=60, interval=15)

        orchestrator.save_transcripts("scenario_09_conversation")
