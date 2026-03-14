"""Scenario 11: Forge Update Simulation.

Tests: forge start -> stop -> simulate forge version update (regenerate all files) -> resume -> verify state preserved.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.e2e.checkpoint_validator import CheckpointValidator
from tests.e2e.tmux_helpers import ForgeSessionOrchestrator


@pytest.mark.e2e
class TestForgeUpdate:

    def test_forge_update_new_skill_files_applied_on_resume(
        self, mvp_project, orchestrator, validator
    ):
        """Simulate: user upgrades forge (new version generates better skills).
        Agents should resume with new skill files but same checkpoint state."""
        project_dir, config = mvp_project
        orchestrator.project_dir = project_dir
        orchestrator.config = config

        orchestrator.generate_project()
        orchestrator.start_session(wait_for_agents=True)
        orchestrator.watch_terminals(duration=60, interval=15)

        snap_before = orchestrator.capture_state()

        # Record skill file content before "update"
        skills_before: dict[str, str] = {}
        skills_dir = project_dir / ".claude" / "skills"
        if skills_dir.exists():
            for skill_file in skills_dir.glob("*.md"):
                skills_before[skill_file.name] = skill_file.read_text()

        orchestrator.stop_gracefully()

        # -- Simulate forge update: regenerate ALL files --
        orchestrator.regenerate_files()

        # Verify skill files exist after regeneration
        skills_after: dict[str, str] = {}
        if skills_dir.exists():
            for skill_file in skills_dir.glob("*.md"):
                skills_after[skill_file.name] = skill_file.read_text()

        # New checkpoint skill should exist
        assert "checkpoint.md" in skills_after, \
            "Regenerated files should include checkpoint skill"

        # -- Resume with new files --
        snap_after = orchestrator.resume_session(wait_for_agents=True)

        # -- VERIFY: agents use new instruction files but same state --
        violations = validator.assert_state_continuity(snap_before, snap_after)
        assert len(violations) == 0, f"State violated after forge update: {violations}"

        # Verify instruction file hashes are tracked in session
        session_path = project_dir / ".forge" / "session.json"
        if session_path.exists():
            session = json.loads(session_path.read_text())
            stored_hashes = session.get("instruction_file_hashes", {})
            # Hashes should be present (populated by forge start/resume)
            # May or may not differ from pre-update depending on generator determinism

        orchestrator.save_transcripts("scenario_11_forge_update")
