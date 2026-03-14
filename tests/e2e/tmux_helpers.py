"""Tmux session management and forge orchestration for E2E tests.

Provides TmuxTestSession for low-level tmux control and
ForgeSessionOrchestrator for high-level forge lifecycle testing.
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SessionSnapshot:
    """Immutable snapshot of forge session state at a point in time."""

    timestamp: str
    session_json: dict | None = None
    checkpoints: dict[str, dict] = field(default_factory=dict)
    activity_logs: dict[str, list] = field(default_factory=dict)
    pane_contents: dict[str, str] = field(default_factory=dict)
    pane_count: int = 0
    git_branches: list[str] = field(default_factory=list)
    git_status: str = ""
    git_log: list[str] = field(default_factory=list)
    checkpoint_files: list[str] = field(default_factory=list)
    instruction_file_hashes: dict[str, str] = field(default_factory=dict)


class TmuxTestSession:
    """Low-level tmux session management for E2E tests."""

    def __init__(self, session_name: str, project_dir: Path):
        self.session_name = session_name
        self.project_dir = project_dir
        self._snapshots: list[dict] = []

    def create(self) -> None:
        """Create a new tmux session."""
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", self.session_name,
             "-c", str(self.project_dir), "-x", "200", "-y", "50"],
            check=True, capture_output=True,
        )

    def kill(self) -> None:
        """Kill the tmux session gracefully."""
        subprocess.run(
            ["tmux", "kill-session", "-t", self.session_name],
            capture_output=True,
        )

    def kill_abruptly(self) -> None:
        """SIGKILL all processes in the session."""
        pids = self.get_pane_pids()
        for pid in pids:
            subprocess.run(["kill", "-9", str(pid)], capture_output=True)
        self.kill()

    def is_alive(self) -> bool:
        """Check if the tmux session still exists."""
        result = subprocess.run(
            ["tmux", "has-session", "-t", self.session_name],
            capture_output=True,
        )
        return result.returncode == 0

    def send_keys(self, pane: str, keys: str, enter: bool = True) -> None:
        """Send keys to a tmux pane."""
        cmd = ["tmux", "send-keys", "-t", f"{self.session_name}:{pane}", keys]
        if enter:
            cmd.append("Enter")
        subprocess.run(cmd, capture_output=True)

    def send_text_to_claude(self, pane: str, text: str) -> None:
        """Send user input to a Claude session in a pane."""
        self.send_keys(pane, text, enter=True)

    def capture_pane(self, pane: str = "0", lines: int = 500) -> str:
        """Capture content from a tmux pane."""
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", f"{self.session_name}:{pane}",
             "-p", "-S", f"-{lines}"],
            capture_output=True, text=True,
        )
        return result.stdout

    def capture_all_panes(self) -> dict[str, str]:
        """Capture content from all panes."""
        panes = self.list_panes()
        result = {}
        for pane in panes:
            pane_id = pane.get("id", "0")
            result[pane_id] = self.capture_pane(pane_id)
        return result

    def wait_for_text(self, text: str, pane: str = "0",
                      timeout: float = 120, interval: float = 2) -> bool:
        """Wait until text appears in a pane."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            content = self.capture_pane(pane)
            if text in content:
                return True
            time.sleep(interval)
        return False

    def wait_for_file(self, path: Path, timeout: float = 60) -> bool:
        """Wait until a file exists."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return True
            time.sleep(1)
        return False

    def wait_for_file_content(self, path: Path, json_path: str, expected: str,
                              timeout: float = 60) -> bool:
        """Wait until a JSON file contains expected value at json_path."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                try:
                    data = json.loads(path.read_text())
                    # Simple dot-path navigation
                    for key in json_path.split("."):
                        data = data[key]
                    if str(data) == expected:
                        return True
                except (json.JSONDecodeError, KeyError, TypeError):
                    pass
            time.sleep(1)
        return False

    def wait_for_pane_count(self, count: int, timeout: float = 120) -> bool:
        """Wait until tmux session has N panes."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.pane_count() >= count:
                return True
            time.sleep(2)
        return False

    def list_panes(self) -> list[dict]:
        """Returns pane info for each pane in the session."""
        result = subprocess.run(
            ["tmux", "list-panes", "-t", self.session_name,
             "-F", "#{pane_id}:#{pane_pid}:#{pane_current_command}:#{pane_active}"],
            capture_output=True, text=True,
        )
        panes = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split(":", 3)
            if len(parts) >= 4:
                panes.append({
                    "id": parts[0], "pid": int(parts[1]),
                    "command": parts[2], "active": parts[3] == "1",
                })
        return panes

    def pane_count(self) -> int:
        """Return number of panes in the session."""
        return len(self.list_panes())

    def get_pane_pids(self) -> list[int]:
        """Return PIDs of all pane processes."""
        return [p["pid"] for p in self.list_panes()]

    def take_snapshot(self) -> dict:
        """Capture full session state."""
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "panes": self.capture_all_panes(),
            "pane_count": self.pane_count(),
            "alive": self.is_alive(),
        }

    def get_snapshots(self) -> list[dict]:
        return self._snapshots


class ForgeSessionOrchestrator:
    """High-level orchestrator for forge start/stop/resume E2E testing."""

    def __init__(self, project_dir: Path, config: Any,
                 llm_provider: Any, transcript_dir: Path):
        self.project_dir = project_dir
        self.config = config
        self.llm = llm_provider
        self.tmux: TmuxTestSession | None = None
        self.transcript_dir = transcript_dir
        self.session_history: list[SessionSnapshot] = []

    def generate_project(self) -> None:
        """Run forge generate to create all instruction files."""
        from forge_cli.generators.orchestrator import generate_all
        if self.config:
            self.config.project.directory = str(self.project_dir)
            generate_all(self.config)

    def start_session(self, wait_for_agents: bool = True,
                      agent_activity_timeout: float = 180) -> SessionSnapshot:
        """Start a forge session in a detached tmux session.

        Mirrors forge start --tmux logic but without os.execvp (which
        replaces the process and breaks subprocess.run in tests).
        Directly creates the tmux session, session.json, and launches claude.
        """
        import shutil
        from datetime import datetime, timezone
        from uuid import uuid4

        from forge_cli.checkpoint import (
            SessionState, compute_instruction_hashes, write_session,
        )
        from forge_cli.generators.hooks import generate_hook_scripts

        project_path = self.project_dir.resolve()
        forge_dir = project_path / ".forge"
        forge_dir.mkdir(parents=True, exist_ok=True)

        # Generate hook scripts
        generate_hook_scripts(self.config, forge_dir)

        # Create session.json
        session_name = f"forge-{project_path.name}"
        session = SessionState(
            forge_session_id=str(uuid4()),
            project_dir=str(project_path),
            project_name=project_path.name,
            config_hash="",
            started_at=datetime.now(timezone.utc).isoformat(),
            updated_at=datetime.now(timezone.utc).isoformat(),
            status="running",
            instruction_file_hashes=compute_instruction_hashes(project_path),
            tmux_session_name=session_name,
        )
        write_session(session, forge_dir)

        claude_bin = shutil.which("claude")
        tmux_bin = shutil.which("tmux")
        init_prompt = (
            "Read team-init-plan.md and initialize the team. "
            "Follow the startup sequence and begin Iteration 1."
        )

        # Kill existing session if present
        subprocess.run(
            [tmux_bin, "kill-session", "-t", session_name],
            capture_output=True,
        )

        # Create detached tmux session with claude
        subprocess.run(
            [
                tmux_bin, "new-session",
                "-d", "-s", session_name,
                "-c", str(project_path),
                "-x", "200", "-y", "50",
                claude_bin, init_prompt,
            ],
            check=True,
        )

        subprocess.run(
            [tmux_bin, "set-environment", "-t", session_name,
             "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "1"],
            capture_output=True,
        )

        self.tmux = TmuxTestSession(session_name, project_path)

        if wait_for_agents:
            self.tmux.wait_for_text("team", timeout=agent_activity_timeout)

        snap = self.capture_state()
        self.session_history.append(snap)
        return snap

    def stop_gracefully(self, timeout: float = 90) -> SessionSnapshot:
        """forge stop."""
        subprocess.run(
            ["forge", "stop", "--project-dir", str(self.project_dir),
             "--timeout", str(int(timeout))],
            capture_output=True, text=True, timeout=timeout + 30,
            cwd=str(self.project_dir),
        )
        snap = self.capture_state()
        self.session_history.append(snap)
        return snap

    def stop_via_user_message(self, message: str = "Stop working for the day") -> SessionSnapshot:
        """Send stop message directly to TL pane."""
        if self.tmux:
            self.tmux.send_text_to_claude("0", message)
            time.sleep(30)  # Wait for agents to process
        snap = self.capture_state()
        self.session_history.append(snap)
        return snap

    def kill_terminal(self) -> SessionSnapshot:
        """tmux kill-session. Simulates terminal close."""
        snap = self.capture_state()
        if self.tmux:
            self.tmux.kill()
        self.session_history.append(snap)
        return snap

    def kill_processes(self) -> SessionSnapshot:
        """kill -9 all Claude processes. Simulates laptop death."""
        snap = self.capture_state()
        if self.tmux:
            self.tmux.kill_abruptly()
        self.session_history.append(snap)
        return snap

    def resume_session(self, wait_for_agents: bool = True,
                       agent_activity_timeout: float = 180) -> SessionSnapshot:
        """Resume a forge session in a detached tmux session.

        Mirrors forge resume --tmux logic but without os.execvp.
        """
        import shutil
        from datetime import datetime, timezone

        from forge_cli.checkpoint import (
            build_resume_prompt, compute_instruction_hashes,
            detect_instruction_changes, read_all_checkpoints,
            read_session, write_session,
        )

        project_path = self.project_dir.resolve()
        forge_dir = project_path / ".forge"
        checkpoints_dir = forge_dir / "checkpoints"

        session = read_session(forge_dir)
        if session is None:
            raise RuntimeError("No session.json found for resume")

        checkpoints = read_all_checkpoints(checkpoints_dir)
        current_hashes = compute_instruction_hashes(project_path)
        changes = detect_instruction_changes(
            session.instruction_file_hashes, current_hashes,
        )
        resume_prompt = build_resume_prompt(session, checkpoints, changes)

        session_name = f"forge-{project_path.name}"
        session.status = "running"
        session.updated_at = datetime.now(timezone.utc).isoformat()
        session.instruction_file_hashes = current_hashes
        session.tmux_session_name = session_name
        write_session(session, forge_dir)

        claude_bin = shutil.which("claude")
        tmux_bin = shutil.which("tmux")

        # Kill existing session if present
        subprocess.run(
            [tmux_bin, "kill-session", "-t", session_name],
            capture_output=True,
        )

        # Create detached tmux session with resume prompt
        subprocess.run(
            [
                tmux_bin, "new-session",
                "-d", "-s", session_name,
                "-c", str(project_path),
                "-x", "200", "-y", "50",
                claude_bin, resume_prompt,
            ],
            check=True,
        )

        subprocess.run(
            [tmux_bin, "set-environment", "-t", session_name,
             "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", "1"],
            capture_output=True,
        )

        self.tmux = TmuxTestSession(session_name, project_path)

        if wait_for_agents:
            self.tmux.wait_for_text("resum", timeout=agent_activity_timeout)

        snap = self.capture_state()
        self.session_history.append(snap)
        return snap

    def modify_config(self, **overrides: Any) -> None:
        """Update forge config with new values."""
        if self.config:
            for key, value in overrides.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

    def regenerate_files(self) -> None:
        """Run forge generate with current config."""
        self.generate_project()

    def capture_state(self) -> SessionSnapshot:
        """Full state capture."""
        forge_dir = self.project_dir / ".forge"
        checkpoints_dir = forge_dir / "checkpoints"

        # Read session.json
        session_json = None
        session_path = forge_dir / "session.json"
        if session_path.exists():
            try:
                session_json = json.loads(session_path.read_text())
            except json.JSONDecodeError:
                pass

        # Read checkpoints
        checkpoints: dict[str, dict] = {}
        if checkpoints_dir.exists():
            for cp_file in checkpoints_dir.glob("*.json"):
                if cp_file.name.endswith(".tmp"):
                    continue
                try:
                    checkpoints[cp_file.stem] = json.loads(cp_file.read_text())
                except json.JSONDecodeError:
                    pass

        # Read activity logs
        activity_logs: dict[str, list] = {}
        if checkpoints_dir.exists():
            for log_file in checkpoints_dir.glob("*.activity.jsonl"):
                lines = []
                for line in log_file.read_text().strip().split("\n"):
                    if line:
                        try:
                            lines.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
                activity_logs[log_file.stem.replace(".activity", "")] = lines

        # Pane contents
        pane_contents: dict[str, str] = {}
        pane_count = 0
        if self.tmux and self.tmux.is_alive():
            pane_contents = self.tmux.capture_all_panes()
            pane_count = self.tmux.pane_count()

        # Git state
        git_branches: list[str] = []
        git_status = ""
        git_log: list[str] = []
        try:
            result = subprocess.run(
                ["git", "branch", "--list"], capture_output=True,
                text=True, cwd=str(self.project_dir),
            )
            git_branches = [b.strip().lstrip("* ") for b in result.stdout.strip().split("\n") if b.strip()]
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["git", "status", "--short"], capture_output=True,
                text=True, cwd=str(self.project_dir),
            )
            git_status = result.stdout
        except Exception:
            pass
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-10"], capture_output=True,
                text=True, cwd=str(self.project_dir),
            )
            git_log = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]
        except Exception:
            pass

        # Instruction file hashes
        from forge_cli.checkpoint import compute_instruction_hashes
        instruction_hashes = compute_instruction_hashes(self.project_dir)

        # Checkpoint file list
        checkpoint_files = [
            str(f.relative_to(self.project_dir))
            for f in checkpoints_dir.glob("*.json")
            if checkpoints_dir.exists() and not f.name.endswith(".tmp")
        ]

        return SessionSnapshot(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            session_json=session_json,
            checkpoints=checkpoints,
            activity_logs=activity_logs,
            pane_contents=pane_contents,
            pane_count=pane_count,
            git_branches=git_branches,
            git_status=git_status,
            git_log=git_log,
            checkpoint_files=checkpoint_files,
            instruction_file_hashes=instruction_hashes,
        )

    def watch_terminals(self, duration: float = 30, interval: float = 5) -> list[dict]:
        """Periodically capture all pane content over duration."""
        timeline: list[dict] = []
        start = time.monotonic()
        while time.monotonic() - start < duration:
            if self.tmux and self.tmux.is_alive():
                timeline.append(self.tmux.take_snapshot())
            time.sleep(interval)
        return timeline

    def collect_transcripts(self) -> dict[str, str]:
        """Read Claude session transcripts for analysis."""
        # Claude stores transcripts in ~/.claude/projects/
        transcripts: dict[str, str] = {}
        claude_dir = Path.home() / ".claude" / "projects"
        if claude_dir.exists():
            for jsonl_file in claude_dir.rglob("*.jsonl"):
                try:
                    transcripts[jsonl_file.stem] = jsonl_file.read_text()
                except OSError:
                    pass
        return transcripts

    def save_transcripts(self, test_name: str) -> Path:
        """Save all transcripts to transcript_dir/{test_name}/."""
        output_dir = self.transcript_dir / test_name
        output_dir.mkdir(parents=True, exist_ok=True)
        transcripts = self.collect_transcripts()
        for name, content in transcripts.items():
            (output_dir / f"{name}.jsonl").write_text(content)
        return output_dir

    def wait_for_agent_activity(self, agent_type: str, timeout: float = 120) -> bool:
        """Wait until specific agent shows activity."""
        activity_file = self.project_dir / ".forge" / "checkpoints" / f"{agent_type}.activity.jsonl"
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if activity_file.exists() and activity_file.stat().st_size > 0:
                return True
            time.sleep(2)
        return False
