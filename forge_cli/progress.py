"""Rich-based progress display for forge generation and refinement."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text


@dataclass
class StepInfo:
    """Metadata for a single generation/refinement step."""

    name: str
    description: str
    status: str = "pending"  # pending | running | done | skipped | error
    detail: str = ""
    files_total: int = 0
    files_done: int = 0


class ForgeProgress:
    """Orchestrates Rich progress display for forge operations.

    Provides context managers for steps and file-level progress tracking
    with a live-updating display showing current status.
    """

    def __init__(self, console: Console | None = None, enabled: bool = True) -> None:
        self._console = console or Console()
        self._enabled = enabled
        self._steps: list[StepInfo] = []
        self._current_step: StepInfo | None = None
        self._live: Live | None = None

    def _build_display(self) -> Table:
        """Build the current progress table."""
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("icon", width=3)
        table.add_column("step", min_width=40)
        table.add_column("detail", min_width=30)

        for step in self._steps:
            if step.status == "done":
                icon = Text("✓", style="green bold")
                name = Text(step.description, style="green")
                detail = Text(step.detail, style="dim")
            elif step.status == "running":
                icon = Text("⟳", style="cyan bold")
                name = Text(step.description, style="cyan bold")
                if step.files_total > 0:
                    bar = f"[{step.files_done}/{step.files_total}]"
                    detail = Text(f"{bar} {step.detail}", style="cyan")
                else:
                    detail = Text(step.detail, style="cyan")
            elif step.status == "error":
                icon = Text("✗", style="red bold")
                name = Text(step.description, style="red")
                detail = Text(step.detail, style="red")
            elif step.status == "skipped":
                icon = Text("–", style="dim")
                name = Text(step.description, style="dim")
                detail = Text("skipped", style="dim")
            else:
                icon = Text(" ", style="dim")
                name = Text(step.description, style="dim")
                detail = Text("")

            table.add_row(icon, name, detail)

        return table

    @contextmanager
    def live(self) -> Generator[ForgeProgress, None, None]:
        """Context manager for the live display session."""
        if not self._enabled:
            yield self
            return

        self._live = Live(
            self._build_display(),
            console=self._console,
            refresh_per_second=4,
            transient=True,
        )
        with self._live:
            yield self
        self._live = None
        # Print final state (transient=True clears the live display,
        # so we print the completed table as permanent output)
        self._console.print(self._build_display())

    @contextmanager
    def step(
        self,
        name: str,
        description: str,
        total_files: int = 0,
    ) -> Generator[StepInfo, None, None]:
        """Context manager for a single generation step.

        Args:
            name: Internal step identifier.
            description: Human-readable step description.
            total_files: Total number of files to process (0 if not file-based).
        """
        info = StepInfo(
            name=name,
            description=description,
            status="running",
            files_total=total_files,
        )
        self._steps.append(info)
        self._current_step = info
        self._refresh()

        try:
            yield info
            info.status = "done"
        except Exception:
            info.status = "error"
            raise
        finally:
            self._current_step = None
            self._refresh()

    def update(self, detail: str = "", files_done: int | None = None) -> None:
        """Update the current step's progress."""
        if self._current_step is None:
            return
        if detail:
            self._current_step.detail = detail
        if files_done is not None:
            self._current_step.files_done = files_done
        self._refresh()

    def skip(self, name: str, description: str) -> None:
        """Mark a step as skipped."""
        info = StepInfo(name=name, description=description, status="skipped")
        self._steps.append(info)
        self._refresh()

    def _refresh(self) -> None:
        """Refresh the live display."""
        if self._live is not None:
            self._live.update(self._build_display())


@dataclass
class RefinementFileState:
    """Track refinement progress for an individual file."""

    file_name: str
    current_score: int = 0
    initial_score: int = 0
    target_score: int = 90
    iteration: int = 0
    max_iterations: int = 5
    status: str = "waiting"  # waiting | scoring | refining | done | failed
    last_change: str = ""  # Most recent improvement summary


class ForgeRefinementProgress:
    """Parallel multi-file progress display for the refinement phase.

    Uses a compact live display that only shows active files (scoring/refining).
    Completed files are printed as permanent output above the live display so
    the live area stays small and Rich ``Live`` can overwrite it in-place
    regardless of how many total files exist.

    Example live display (at most ``concurrency`` rows + 1 summary):
     ⟳  backend-developer.md  refining   [2/5]  78 → 85/90  Added domain patterns
     ⟳  architect.md          scoring    [1/5]        …/90   evaluating quality
        3/31 complete · 26 queued

    Completed rows scroll above as permanent output:
     ✓  team-leader.md        done       [1/5]  92 → 94/90  passed
    """

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()
        self._files: dict[str, RefinementFileState] = {}
        self._file_order: list[str] = []
        self._live: Live | None = None
        self._total_files: int = 0
        self._completed_files: int = 0
        self._passed_files: int = 0
        self._failed_files: int = 0
        self._below_files: int = 0

    # ------------------------------------------------------------------
    # Display builders
    # ------------------------------------------------------------------

    def _build_live_display(self) -> Table:
        """Build compact live table — only active (scoring/refining) files."""
        table = Table(show_header=False, box=None, padding=(0, 1), expand=False)
        table.add_column("", width=3)           # icon
        table.add_column("File", min_width=28)
        table.add_column("Status", width=10)
        table.add_column("Iter", width=6, justify="center")
        table.add_column("Score", width=16, justify="center")
        table.add_column("Detail", min_width=30)

        for name in self._file_order:
            fp = self._files[name]
            if fp.status not in ("scoring", "refining"):
                continue

            short_name = name.rsplit("/", 1)[-1]
            if fp.status == "scoring":
                icon = Text("⟳", style="cyan bold")
                status = Text("scoring", style="cyan")
                if fp.initial_score > 0:
                    score_str = f"{fp.initial_score} → …/{fp.target_score}"
                else:
                    score_str = f"…/{fp.target_score}"
                score_style = "cyan"
                detail = Text(fp.last_change or "evaluating quality", style="dim")
            else:  # refining
                icon = Text("⟳", style="cyan bold")
                status = Text("refining", style="cyan")
                score_str = f"{fp.initial_score} → {fp.current_score}/{fp.target_score}"
                score_style = "cyan"
                detail = Text(fp.last_change or "improving content", style="cyan")

            iter_str = f"[{fp.iteration}/{fp.max_iterations}]"
            table.add_row(
                icon,
                Text(short_name, style="bold"),
                status,
                Text(iter_str, style="dim"),
                Text(score_str, style=score_style),
                detail,
            )

        # Summary footer
        waiting = sum(1 for f in self._files.values() if f.status == "waiting")
        parts: list[str] = []
        if self._completed_files:
            parts.append(f"{self._completed_files}/{self._total_files} complete")
        if waiting:
            parts.append(f"{waiting} queued")
        if parts:
            table.add_row(
                Text(""),
                Text(" · ".join(parts), style="bold dim"),
                Text(""), Text(""), Text(""), Text(""),
            )

        return table

    def _build_final_display(self) -> Table:
        """Build full summary table printed after Live exits."""
        table = Table(show_header=True, box=None, padding=(0, 1), expand=False)
        table.add_column("", width=3)
        table.add_column("File", min_width=28, style="bold")
        table.add_column("Status", width=10)
        table.add_column("Iter", width=6, justify="center")
        table.add_column("Score", width=16, justify="center")
        table.add_column("Detail", min_width=30)

        for name in self._file_order:
            fp = self._files[name]
            short_name = name.rsplit("/", 1)[-1]
            icon, status, score_str, score_style, detail, iter_str = \
                self._render_file_row(fp, short_name)
            table.add_row(icon, Text(short_name), status,
                          Text(iter_str, style="dim"),
                          Text(score_str, style=score_style), detail)

        # Summary footer
        table.add_row(
            Text(""),
            Text(f"{self._completed_files}/{self._total_files} files complete",
                 style="bold"),
            Text(""), Text(""), Text(""), Text(""),
        )
        return table

    @staticmethod
    def _render_file_row(
        fp: RefinementFileState, short_name: str,
    ) -> tuple[Text, Text, str, str, Text, str]:
        """Return (icon, status, score_str, score_style, detail, iter_str)."""
        if fp.status == "done":
            passed = fp.current_score >= fp.target_score
            icon = Text("✓" if passed else "▲",
                        style="green bold" if passed else "yellow bold")
            status = Text("done", style="green" if passed else "yellow")
            score_str = f"{fp.initial_score} → {fp.current_score}/{fp.target_score}"
            score_style = "green bold" if passed else "yellow"
            detail = Text("passed" if passed else f"best: {fp.current_score}",
                          style="dim")
        elif fp.status == "failed":
            icon = Text("✗", style="red bold")
            status = Text("failed", style="red")
            score_str = f"{fp.current_score}/{fp.target_score}"
            score_style = "red"
            detail = Text(fp.last_change or "error", style="red")
        elif fp.status == "scoring":
            icon = Text("⟳", style="cyan bold")
            status = Text("scoring", style="cyan")
            score_str = (f"{fp.initial_score} → …/{fp.target_score}"
                         if fp.initial_score > 0 else f"…/{fp.target_score}")
            score_style = "cyan"
            detail = Text(fp.last_change or "evaluating quality", style="dim")
        elif fp.status == "refining":
            icon = Text("⟳", style="cyan bold")
            status = Text("refining", style="cyan")
            score_str = f"{fp.initial_score} → {fp.current_score}/{fp.target_score}"
            score_style = "cyan"
            detail = Text(fp.last_change or "improving content", style="cyan")
        else:  # waiting
            icon = Text(" ", style="dim")
            status = Text("waiting", style="dim")
            score_str = f"/{fp.target_score}"
            score_style = "dim"
            detail = Text("")

        iter_str = (f"[{fp.iteration}/{fp.max_iterations}]"
                    if fp.status != "waiting" else "")
        return icon, status, score_str, score_style, detail, iter_str

    def _print_completed_row(self, fp: RefinementFileState) -> None:
        """Print a finished file as permanent output above the live display."""
        short_name = fp.file_name.rsplit("/", 1)[-1]
        if fp.status == "done":
            passed = fp.current_score >= fp.target_score
            icon = "✓" if passed else "▲"
            color = "green" if passed else "yellow"
            score = f"{fp.initial_score} → {fp.current_score}/{fp.target_score}"
            detail = "passed" if passed else f"best: {fp.current_score}"
        elif fp.status == "failed":
            icon = "✗"
            color = "red"
            score = f"{fp.current_score}/{fp.target_score}"
            detail = fp.last_change or "error"
            if len(detail) > 50:
                detail = detail[:47] + "..."
        else:
            return

        iter_str = f"[{fp.iteration}/{fp.max_iterations}]"
        self._console.print(
            f" [{color} bold]{icon}[/]  {short_name:<30}"
            f"[{color}]{'done' if fp.status == 'done' else 'failed':<10}[/]"
            f"[dim]{iter_str:^8}[/]"
            f"[{color} bold]{score:^18}[/]"
            f"[dim]{detail}[/]"
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @contextmanager
    def track(self, total_files: int) -> Generator[ForgeRefinementProgress, None, None]:
        """Context manager for the live refinement display."""
        self._total_files = total_files
        self._live = Live(
            self._build_live_display(),
            console=self._console,
            refresh_per_second=4,
            transient=True,
        )
        with self._live:
            yield self
        self._live = None
        # Print a compact final summary (individual rows already printed)
        self._console.print()
        summary_parts: list[str] = []
        if self._passed_files:
            summary_parts.append(f"[green]{self._passed_files} passed[/]")
        if self._below_files:
            summary_parts.append(f"[yellow]{self._below_files} below threshold[/]")
        if self._failed_files:
            summary_parts.append(f"[red]{self._failed_files} failed[/]")
        if summary_parts:
            self._console.print(
                f"  [bold]{self._completed_files}/{self._total_files} files:[/] "
                + " · ".join(summary_parts)
            )

    def register_file(self, file_name: str, target_score: int = 90) -> None:
        """Register a file in 'waiting' state (queued but not yet started)."""
        fp = RefinementFileState(
            file_name=file_name,
            target_score=target_score,
            status="waiting",
        )
        self._files[file_name] = fp
        if file_name not in self._file_order:
            self._file_order.append(file_name)
        self._refresh()

    def start_file(self, file_name: str, target_score: int = 90) -> None:
        """Mark a file as actively being processed (scoring)."""
        fp = self._files.get(file_name)
        if fp is not None:
            fp.status = "scoring"
            self._refresh()
            return
        # Fallback: register + start in one call (backward compat)
        fp = RefinementFileState(
            file_name=file_name,
            target_score=target_score,
            status="scoring",
        )
        self._files[file_name] = fp
        if file_name not in self._file_order:
            self._file_order.append(file_name)
        self._refresh()

    def update_score(
        self,
        file_name: str,
        score: int,
        iteration: int,
        status: str = "refining",
        detail: str = "",
    ) -> None:
        """Update a file's score and iteration."""
        fp = self._files.get(file_name)
        if fp is None:
            return
        if fp.initial_score == 0:
            fp.initial_score = score
        fp.current_score = score
        fp.iteration = iteration
        fp.status = status
        if detail:
            fp.last_change = detail
        self._refresh()

    def complete_file(self, file_name: str, final_score: int) -> None:
        """Mark a file as complete and print its row as permanent output."""
        fp = self._files.get(file_name)
        if fp is None:
            return
        fp.current_score = final_score
        fp.status = "done"
        self._completed_files += 1
        if fp.current_score >= fp.target_score:
            self._passed_files += 1
        else:
            self._below_files += 1
        self._print_completed_row(fp)
        self._refresh()

    def fail_file(self, file_name: str, reason: str = "") -> None:
        """Mark a file as failed and print its row as permanent output."""
        fp = self._files.get(file_name)
        if fp is None:
            return
        fp.status = "failed"
        fp.last_change = reason
        self._completed_files += 1
        self._failed_files += 1
        self._print_completed_row(fp)
        self._refresh()

    def _refresh(self) -> None:
        """Refresh the live display."""
        if self._live is not None:
            self._live.update(self._build_live_display())
