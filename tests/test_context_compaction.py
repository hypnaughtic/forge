"""Unit tests for context compaction system.

Covers lifecycle skill content verification, cooperative compaction hooks,
PreCompact hook, anchor reminder logic, compaction-marker detection,
compaction_needed event application, token counter tracking, decision tree
in agent files, and compaction config integration.
"""

from __future__ import annotations

import pytest

from forge_cli.config_schema import CompactionConfig, ForgeConfig
from forge_cli.generators.agent_files import _checkpoint_protocol_section
from forge_cli.generators.hooks import (
    _bash_checkpoint_reminder_script,
    _post_tool_checkpoint_script,
    _pre_compact_checkpoint_script,
    _resolve_identity_script,
)
from forge_cli.generators.skills import (
    _agent_init_skill,
    _checkpoint_skill,
    _context_reload_skill,
    _handoff_skill,
    _respawn_skill,
    _spawn_agent_skill,
)
from forge_cli.models import AgentCheckpoint, AgentMeta, SessionState
from forge_cli.session import _apply_event


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def default_config() -> ForgeConfig:
    """Return a ForgeConfig with defaults."""
    return ForgeConfig()


@pytest.fixture()
def custom_compaction_config() -> ForgeConfig:
    """Return a ForgeConfig with non-default compaction settings."""
    return ForgeConfig(
        compaction=CompactionConfig(
            compaction_threshold_tokens=50_000,
            anchor_interval_minutes=10,
            enable_context_anchors=True,
        ),
    )


# ---------------------------------------------------------------------------
# 1. Lifecycle Skill Content Verification
# ---------------------------------------------------------------------------


class TestAgentInitSkillContent:
    """Verify /agent-init skill contains expected keywords and sections."""

    def test_has_three_modes(self, default_config: ForgeConfig) -> None:
        content = _agent_init_skill(default_config)
        assert "fresh" in content.lower()
        assert "resume" in content.lower()
        assert "detect" in content.lower()

    def test_references_claude_md(self, default_config: ForgeConfig) -> None:
        content = _agent_init_skill(default_config)
        assert "CLAUDE.md" in content

    def test_references_instruction_file(self, default_config: ForgeConfig) -> None:
        content = _agent_init_skill(default_config)
        assert ".claude/agents/" in content

    def test_references_checkpoint_save(self, default_config: ForgeConfig) -> None:
        content = _agent_init_skill(default_config)
        assert "/checkpoint" in content

    def test_has_context_anchor_format(self, default_config: ForgeConfig) -> None:
        content = _agent_init_skill(default_config)
        assert "context-anchor.md" in content

    def test_has_essential_files_reference(self, default_config: ForgeConfig) -> None:
        content = _agent_init_skill(default_config)
        assert "essential_files" in content

    def test_anchor_interval_injected(self, custom_compaction_config: ForgeConfig) -> None:
        content = _agent_init_skill(custom_compaction_config)
        assert "10 minutes" in content


class TestSpawnAgentSkillContent:
    """Verify /spawn-agent skill contains naming protocol, event registration, checkpoint path."""

    def test_has_naming_protocol(self, default_config: ForgeConfig) -> None:
        content = _spawn_agent_skill(default_config)
        # The spawn skill mentions naming or "choose a name" or "agent-init detect"
        assert "naming" in content.lower() or "agent-init" in content.lower()

    def test_has_event_registration(self, default_config: ForgeConfig) -> None:
        content = _spawn_agent_skill(default_config)
        assert "event" in content.lower()
        assert "agent_started" in content or "agent_type" in content

    def test_has_checkpoint_path_computation(self, default_config: ForgeConfig) -> None:
        content = _spawn_agent_skill(default_config)
        # References checkpoint tracking or sub_agents list
        assert "checkpoint" in content.lower()

    def test_has_agent_list(self, default_config: ForgeConfig) -> None:
        content = _spawn_agent_skill(default_config)
        assert "backend-developer" in content
        assert "qa-engineer" in content


class TestRespawnSkillContent:
    """Verify /respawn skill has token counter reset, context anchor, checkpoint verification."""

    def test_has_context_anchor_loading(self, default_config: ForgeConfig) -> None:
        content = _respawn_skill(default_config)
        assert "context-anchor.md" in content

    def test_has_checkpoint_verification(self, default_config: ForgeConfig) -> None:
        content = _respawn_skill(default_config)
        assert "checkpoint" in content.lower()
        # Verifies checkpoint existence
        assert ".forge/checkpoints/" in content

    def test_has_compaction_count_reference(self, default_config: ForgeConfig) -> None:
        content = _respawn_skill(default_config)
        assert "compaction_count" in content

    def test_has_agent_init_resume_instruction(self, default_config: ForgeConfig) -> None:
        content = _respawn_skill(default_config)
        assert "/agent-init resume" in content

    def test_has_respawn_after_compaction_note(self, default_config: ForgeConfig) -> None:
        content = _respawn_skill(default_config)
        assert "compaction" in content.lower()


class TestHandoffSkillContent:
    """Verify /handoff skill has complete/compaction/blocked modes and structured report."""

    def test_has_complete_mode(self, default_config: ForgeConfig) -> None:
        content = _handoff_skill(default_config)
        assert "`complete`" in content

    def test_has_compaction_mode(self, default_config: ForgeConfig) -> None:
        content = _handoff_skill(default_config)
        assert "`compaction`" in content

    def test_has_blocked_mode(self, default_config: ForgeConfig) -> None:
        content = _handoff_skill(default_config)
        assert "`blocked`" in content

    def test_has_structured_handoff_report(self, default_config: ForgeConfig) -> None:
        content = _handoff_skill(default_config)
        assert "Handoff Report" in content

    def test_compaction_mode_references_essential_files(
        self, default_config: ForgeConfig
    ) -> None:
        content = _handoff_skill(default_config)
        assert "essential_files" in content

    def test_compaction_mode_references_context_summary(
        self, default_config: ForgeConfig
    ) -> None:
        content = _handoff_skill(default_config)
        assert "context_summary" in content

    def test_has_handoff_notes_reference(self, default_config: ForgeConfig) -> None:
        content = _handoff_skill(default_config)
        assert "handoff_notes" in content


class TestContextReloadSkillContent:
    """Verify /context-reload skill has reload/anchor/status sub-commands and essential_files."""

    def test_has_reload_subcommand(self, default_config: ForgeConfig) -> None:
        content = _context_reload_skill(default_config)
        assert "`reload`" in content

    def test_has_anchor_subcommand(self, default_config: ForgeConfig) -> None:
        content = _context_reload_skill(default_config)
        assert "`anchor`" in content

    def test_has_status_subcommand(self, default_config: ForgeConfig) -> None:
        content = _context_reload_skill(default_config)
        assert "`status`" in content

    def test_has_essential_files_reference(self, default_config: ForgeConfig) -> None:
        content = _context_reload_skill(default_config)
        assert "essential_files" in content

    def test_has_compaction_marker_cleanup(self, default_config: ForgeConfig) -> None:
        content = _context_reload_skill(default_config)
        assert "compaction-marker" in content

    def test_config_values_injected(self, custom_compaction_config: ForgeConfig) -> None:
        content = _context_reload_skill(custom_compaction_config)
        assert "10 minutes" in content or "10" in content
        assert "50,000" in content


class TestCheckpointSkillContent:
    """Verify /checkpoint skill has hierarchical paths with {type}/{name}.json."""

    def test_has_hierarchical_paths(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_skill(default_config)
        assert "{your-agent-type}" in content
        assert "{your-agent-name}" in content

    def test_has_save_command(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_skill(default_config)
        assert "`save`" in content

    def test_has_load_command(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_skill(default_config)
        assert "`load`" in content

    def test_has_check_stop_command(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_skill(default_config)
        assert "check-stop" in content

    def test_has_atomic_write_reference(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_skill(default_config)
        assert ".tmp" in content

    def test_checkpoint_path_format(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_skill(default_config)
        assert ".forge/checkpoints/{your-agent-type}/{your-agent-name}.json" in content


# ---------------------------------------------------------------------------
# 2. Cooperative Compaction Hook Output
# ---------------------------------------------------------------------------


class TestPostToolCheckpointScript:
    """Verify _post_tool_checkpoint_script contains token tracking, threshold, events."""

    def test_has_token_tracking_heuristic(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        # bytes/4 estimate
        assert "/ 4" in script or "/4" in script

    def test_has_estimated_tokens_accumulation(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "ESTIMATED_TOKENS" in script

    def test_has_compaction_threshold_check(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "COMPACTION_THRESHOLD" in script
        assert "100000" in script

    def test_has_handoff_compaction_reference(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "/handoff compaction" in script

    def test_has_event_file_writing_for_compaction_needed(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "compaction_needed" in script or "compaction-needed" in script

    def test_has_event_atomic_write(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "events" in script.lower()
        # Atomic write pattern: write to tmp, then mv
        assert ".tmp" in script
        assert "mv" in script

    def test_compaction_warning_message(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "COMPACTION WARNING" in script

    def test_custom_threshold_injected(self) -> None:
        script = _post_tool_checkpoint_script(50_000, 10)
        assert "50000" in script


# ---------------------------------------------------------------------------
# 3. PreCompact Hook Output
# ---------------------------------------------------------------------------


class TestPreCompactCheckpointScript:
    """Verify _pre_compact_checkpoint_script output contains expected references."""

    def test_has_compaction_marker_touch(self) -> None:
        script = _pre_compact_checkpoint_script()
        assert "compaction-marker" in script

    def test_has_context_reload_reference(self) -> None:
        script = _pre_compact_checkpoint_script()
        assert "/context-reload reload" in script or "context-reload" in script.lower()

    def test_has_resolve_identity_call(self) -> None:
        script = _pre_compact_checkpoint_script()
        assert "resolve_identity.py" in script

    def test_has_urgent_warning(self) -> None:
        script = _pre_compact_checkpoint_script()
        assert "URGENT" in script

    def test_has_checkpoint_save_instruction(self) -> None:
        script = _pre_compact_checkpoint_script()
        assert "/checkpoint save" in script


# ---------------------------------------------------------------------------
# 4. Anchor Reminder Logic
# ---------------------------------------------------------------------------


class TestAnchorReminderLogic:
    """Verify _post_tool_checkpoint_script references anchor freshness check."""

    def test_has_anchor_freshness_check(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "ANCHOR_INTERVAL" in script
        assert "ANCHOR_AGE" in script

    def test_anchor_interval_configurable(self) -> None:
        script_15 = _post_tool_checkpoint_script(100_000, 15)
        script_30 = _post_tool_checkpoint_script(100_000, 30)
        assert "ANCHOR_INTERVAL=15" in script_15
        assert "ANCHOR_INTERVAL=30" in script_30

    def test_has_anchor_file_reference(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "context-anchor.md" in script

    def test_has_anchor_reminder_message(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "ANCHOR REMINDER" in script

    def test_has_context_reload_anchor_instruction(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "/context-reload anchor" in script


# ---------------------------------------------------------------------------
# 5. Compaction-Marker Detection
# ---------------------------------------------------------------------------


class TestCompactionMarkerDetection:
    """Verify _bash_checkpoint_reminder_script checks for .compaction-marker."""

    def test_has_compaction_marker_check(self) -> None:
        script = _bash_checkpoint_reminder_script()
        assert "compaction-marker" in script

    def test_has_context_reload_instruction(self) -> None:
        script = _bash_checkpoint_reminder_script()
        # Should reference context-reload or handoff compaction for recovery
        assert "/context-reload" in script or "/handoff compaction" in script

    def test_has_compaction_marker_message(self) -> None:
        script = _bash_checkpoint_reminder_script()
        assert "COMPACTION MARKER" in script

    def test_has_stop_signal_check(self) -> None:
        script = _bash_checkpoint_reminder_script()
        assert "STOP_REQUESTED" in script


# ---------------------------------------------------------------------------
# 6. compaction_needed Event Application
# ---------------------------------------------------------------------------


class TestCompactionNeededEventApplication:
    """Verify _apply_event correctly sets agent status to compaction_pending."""

    def _make_session_with_agent(self, agent_name: str = "Nova") -> SessionState:
        """Build a minimal session with one registered+active agent."""
        session = SessionState(
            forge_session_id="test-session",
            project_dir="/tmp/test",
            project_name="test",
            config_hash="abc",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T10:00:00Z",
        )
        session.agent_tree[agent_name] = AgentMeta(
            agent_type="backend-developer",
            agent_name=agent_name,
            status="active",
        )
        return session

    def test_compaction_needed_sets_status(self) -> None:
        session = self._make_session_with_agent("Nova")
        event = {
            "event": "compaction_needed",
            "agent_name": "Nova",
        }
        _apply_event(session, event)
        assert session.agent_tree["Nova"].status == "compaction_pending"

    def test_compaction_needed_unknown_agent_is_noop(self) -> None:
        session = self._make_session_with_agent("Nova")
        event = {
            "event": "compaction_needed",
            "agent_name": "Unknown",
        }
        _apply_event(session, event)
        # Original agent not affected
        assert session.agent_tree["Nova"].status == "active"
        # Unknown agent not added
        assert "Unknown" not in session.agent_tree

    def test_compaction_needed_empty_name_is_noop(self) -> None:
        session = self._make_session_with_agent("Nova")
        event = {
            "event": "compaction_needed",
            "agent_name": "",
        }
        _apply_event(session, event)
        assert session.agent_tree["Nova"].status == "active"

    def test_compaction_needed_idempotent(self) -> None:
        session = self._make_session_with_agent("Nova")
        event = {
            "event": "compaction_needed",
            "agent_name": "Nova",
        }
        _apply_event(session, event)
        _apply_event(session, event)
        assert session.agent_tree["Nova"].status == "compaction_pending"

    def test_full_lifecycle_transitions(self) -> None:
        """Verify the compaction_pending status fits the lifecycle chain."""
        session = self._make_session_with_agent("Nova")
        # registered -> active (via agent_started)
        session.agent_tree["Nova"].status = "registered"
        _apply_event(session, {
            "event": "agent_started",
            "agent_name": "Nova",
            "session_id": "sess-123",
        })
        assert session.agent_tree["Nova"].status == "active"

        # active -> compaction_pending
        _apply_event(session, {
            "event": "compaction_needed",
            "agent_name": "Nova",
        })
        assert session.agent_tree["Nova"].status == "compaction_pending"


# ---------------------------------------------------------------------------
# 7. Token Counter Tracking + Reset
# ---------------------------------------------------------------------------


class TestTokenCounterTracking:
    """Verify token counter file path references in hook scripts."""

    def test_post_tool_uses_activity_log_for_tracking(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        # Token tracking uses the activity log file size as proxy
        assert "LOG_BYTES" in script or "LOG_FILE" in script

    def test_post_tool_has_bytes_to_tokens_conversion(self) -> None:
        script = _post_tool_checkpoint_script(100_000, 15)
        assert "ESTIMATED_TOKENS" in script
        # bytes/4 heuristic
        assert "/ 4" in script or "/4" in script

    def test_token_threshold_in_post_tool_script(self) -> None:
        script = _post_tool_checkpoint_script(75_000, 15)
        assert "75000" in script

    def test_resolve_identity_script_returns_json(self) -> None:
        script = _resolve_identity_script()
        assert "json.dumps" in script
        assert "agent_type" in script
        assert "agent_name" in script


# ---------------------------------------------------------------------------
# 8. Decision Tree in Agent Files
# ---------------------------------------------------------------------------


class TestCheckpointProtocolSection:
    """Verify _checkpoint_protocol_section output contains the Skill Decision Tree."""

    def test_has_skill_decision_tree_header(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_protocol_section(default_config)
        assert "Skill Decision Tree" in content

    def test_has_all_lifecycle_triggers(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_protocol_section(default_config)
        assert "JUST SPAWNED" in content
        assert "/agent-init detect" in content
        assert "NEED SUB-AGENT" in content
        assert "/spawn-agent" in content
        assert "COMPACTION THRESHOLD HIT" in content
        assert "/handoff compaction" in content
        assert "CHILD RETURNED" in content
        assert "/respawn" in content
        assert "ALL TASKS FINISHED" in content
        assert "/handoff complete" in content
        assert "BLOCKED" in content
        assert "/handoff blocked" in content
        assert "AFTER COMPACTION" in content
        assert "/context-reload reload" in content
        assert "/context-reload anchor" in content
        assert "/context-reload status" in content
        assert "/checkpoint save" in content

    def test_has_compaction_awareness_section(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_protocol_section(default_config)
        assert "Compaction Awareness" in content

    def test_has_compaction_threshold(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_protocol_section(default_config)
        assert "100,000" in content

    def test_has_anchor_interval(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_protocol_section(default_config)
        assert "15 minutes" in content

    def test_team_leader_extra_section(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_protocol_section(default_config, agent_type="team-leader")
        assert "Team Leader Lifecycle Rules" in content
        assert "/respawn" in content
        assert "compaction_needed" in content
        assert "session.json" in content

    def test_non_team_leader_no_extra_section(self, default_config: ForgeConfig) -> None:
        content = _checkpoint_protocol_section(default_config, agent_type="backend-developer")
        assert "Team Leader Lifecycle Rules" not in content

    def test_custom_config_values_in_decision_tree(
        self, custom_compaction_config: ForgeConfig
    ) -> None:
        content = _checkpoint_protocol_section(custom_compaction_config)
        assert "50,000" in content
        assert "10 minutes" in content


# ---------------------------------------------------------------------------
# 9. Compaction Config Integration
# ---------------------------------------------------------------------------


class TestCompactionConfigIntegration:
    """Verify config values are injected into generated content."""

    def test_default_compaction_config(self) -> None:
        config = ForgeConfig()
        assert config.compaction.compaction_threshold_tokens == 100_000
        assert config.compaction.anchor_interval_minutes == 15
        assert config.compaction.enable_context_anchors is True

    def test_custom_compaction_config(self) -> None:
        config = ForgeConfig(
            compaction=CompactionConfig(
                compaction_threshold_tokens=200_000,
                anchor_interval_minutes=30,
                enable_context_anchors=False,
            ),
        )
        assert config.compaction.compaction_threshold_tokens == 200_000
        assert config.compaction.anchor_interval_minutes == 30
        assert config.compaction.enable_context_anchors is False

    def test_threshold_injected_into_hook(self) -> None:
        script = _post_tool_checkpoint_script(200_000, 30)
        assert "200000" in script
        assert "ANCHOR_INTERVAL=30" in script

    def test_threshold_injected_into_context_reload_skill(self) -> None:
        config = ForgeConfig(
            compaction=CompactionConfig(
                compaction_threshold_tokens=75_000,
                anchor_interval_minutes=20,
            ),
        )
        content = _context_reload_skill(config)
        assert "75,000" in content
        assert "20 minutes" in content or "20 min" in content

    def test_anchor_interval_injected_into_agent_init_skill(self) -> None:
        config = ForgeConfig(
            compaction=CompactionConfig(anchor_interval_minutes=25),
        )
        content = _agent_init_skill(config)
        assert "25 minutes" in content

    def test_config_round_trips_through_model(self) -> None:
        config = ForgeConfig(
            compaction=CompactionConfig(
                compaction_threshold_tokens=42_000,
                anchor_interval_minutes=7,
            ),
        )
        data = config.model_dump()
        restored = ForgeConfig.model_validate(data)
        assert restored.compaction.compaction_threshold_tokens == 42_000
        assert restored.compaction.anchor_interval_minutes == 7


# ---------------------------------------------------------------------------
# 10. AgentCheckpoint model fields for context rot reduction
# ---------------------------------------------------------------------------


class TestAgentCheckpointCompactionFields:
    """Verify essential_files, compaction_count, and context_anchor_updated_at fields."""

    def test_essential_files_default_empty(self) -> None:
        cp = AgentCheckpoint(agent_type="dev", agent_name="test")
        assert cp.essential_files == []

    def test_essential_files_stores_list(self) -> None:
        cp = AgentCheckpoint(
            agent_type="dev",
            agent_name="test",
            essential_files=["src/main.py", "src/config.py"],
        )
        assert len(cp.essential_files) == 2

    def test_essential_files_truncated_to_10(self) -> None:
        files = [f"src/file_{i}.py" for i in range(15)]
        cp = AgentCheckpoint(
            agent_type="dev",
            agent_name="test",
            essential_files=files,
        )
        assert len(cp.essential_files) == 10

    def test_compaction_count_default_zero(self) -> None:
        cp = AgentCheckpoint(agent_type="dev", agent_name="test")
        assert cp.compaction_count == 0

    def test_compaction_count_increments(self) -> None:
        cp = AgentCheckpoint(
            agent_type="dev",
            agent_name="test",
            compaction_count=3,
        )
        assert cp.compaction_count == 3

    def test_context_anchor_updated_at_default_empty(self) -> None:
        cp = AgentCheckpoint(agent_type="dev", agent_name="test")
        assert cp.context_anchor_updated_at == ""


# ---------------------------------------------------------------------------
# 11. Multi-level hierarchy: compaction references correct parent
# ---------------------------------------------------------------------------


class TestMultiLevelHierarchyCompaction:
    """Verify compaction instructions reference correct parent at each level."""

    def test_compaction_event_applies_to_correct_agent_in_hierarchy(self) -> None:
        """Build a 3-level tree and verify compaction_needed targets the right agent."""
        session = SessionState(
            forge_session_id="test",
            project_dir="/tmp/test",
            project_name="test",
            config_hash="abc",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T10:00:00Z",
        )
        # Level 0: TL
        session.agent_tree["TL"] = AgentMeta(
            agent_type="team-leader", agent_name="TL", status="active",
        )
        # Level 1: sub-TL
        session.agent_tree["SubTL"] = AgentMeta(
            agent_type="architect", agent_name="SubTL",
            parent_agent="TL", status="active",
        )
        # Level 2: worker
        session.agent_tree["Worker"] = AgentMeta(
            agent_type="backend-developer", agent_name="Worker",
            parent_agent="SubTL", status="active",
        )

        # Worker hits compaction threshold
        _apply_event(session, {
            "event": "compaction_needed",
            "agent_name": "Worker",
        })

        # Only Worker changes status
        assert session.agent_tree["Worker"].status == "compaction_pending"
        assert session.agent_tree["SubTL"].status == "active"
        assert session.agent_tree["TL"].status == "active"

    def test_multiple_agents_compaction_independent(self) -> None:
        """Two agents at different levels can both be in compaction_pending."""
        session = SessionState(
            forge_session_id="test",
            project_dir="/tmp/test",
            project_name="test",
            config_hash="abc",
            started_at="2026-03-14T10:00:00Z",
            updated_at="2026-03-14T10:00:00Z",
        )
        session.agent_tree["A"] = AgentMeta(
            agent_type="dev", agent_name="A", parent_agent="TL", status="active",
        )
        session.agent_tree["B"] = AgentMeta(
            agent_type="qa", agent_name="B", parent_agent="TL", status="active",
        )

        _apply_event(session, {"event": "compaction_needed", "agent_name": "A"})
        _apply_event(session, {"event": "compaction_needed", "agent_name": "B"})

        assert session.agent_tree["A"].status == "compaction_pending"
        assert session.agent_tree["B"].status == "compaction_pending"

    def test_respawn_skill_references_hierarchical_checkpoint_path(
        self, default_config: ForgeConfig
    ) -> None:
        """Verify /respawn skill uses {agent-type}/{agent-name} path format."""
        content = _respawn_skill(default_config)
        assert ".forge/checkpoints/{agent-type}/{agent-name}" in content

    def test_handoff_skill_references_hierarchical_checkpoint_path(
        self, default_config: ForgeConfig
    ) -> None:
        """Verify /handoff skill uses {your-agent-type}/{your-name} path format."""
        content = _handoff_skill(default_config)
        assert ".forge/checkpoints/{your-agent-type}/{your-name}" in content
