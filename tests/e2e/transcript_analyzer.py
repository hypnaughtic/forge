"""LLM-powered transcript analysis for E2E tests.

Uses real LLM (local_claude via llm-gateway) to evaluate whether
agents behaved correctly during checkpoint/resume cycles.
NO MOCKING — uses actual LLM for quality judgments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisResult:
    """Result of analyzing a transcript or behavior."""

    score: int  # 0-100
    findings: list[str] = field(default_factory=list)
    missed_checkpoints: list[str] = field(default_factory=list)
    extra_checkpoints: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)


class TranscriptAnalyzer:
    """Uses real LLM to analyze E2E test transcripts."""

    def __init__(self, llm_provider: Any):
        self.llm = llm_provider

    async def analyze_checkpoint_compliance(self, transcript: str) -> AnalysisResult:
        """Did the agent save checkpoints at appropriate moments?"""
        prompt = f"""\
Analyze this Claude Code agent transcript. Score (0-100) how well the agent
complied with checkpoint save requirements.

Check for:
- Did the agent run /checkpoint save after task completions?
- Did the agent checkpoint after phase transitions?
- Did the agent checkpoint after major decisions?
- Were there long gaps between checkpoints (>15 min)?

Transcript:
{transcript[:5000]}

Return JSON: {{"score": int, "findings": [str], "missed_checkpoints": [str]}}
"""
        try:
            response = await self.llm.generate(prompt=prompt, model="claude-sonnet-4-20250514")
            import json
            data = json.loads(response.text)
            return AnalysisResult(
                score=data.get("score", 0),
                findings=data.get("findings", []),
                missed_checkpoints=data.get("missed_checkpoints", []),
            )
        except Exception as e:
            return AnalysisResult(score=0, findings=[f"Analysis failed: {e}"])

    async def analyze_resume_fidelity(self, pre_stop_transcript: str,
                                      post_resume_transcript: str,
                                      checkpoint: dict) -> AnalysisResult:
        """Did the resumed agent correctly restore context?"""
        prompt = f"""\
Analyze whether this agent correctly resumed from its checkpoint.

Checkpoint data:
- Agent name: {checkpoint.get('agent_name', 'unknown')}
- Iteration: {checkpoint.get('iteration', 'unknown')}
- Phase: {checkpoint.get('phase', 'unknown')}
- Context: {checkpoint.get('context_summary', '')[:500]}
- Handoff notes: {checkpoint.get('handoff_notes', '')[:500]}

Post-resume transcript (first 3000 chars):
{post_resume_transcript[:3000]}

Check:
- Did the agent acknowledge its previous state?
- Did it use the correct name from checkpoint?
- Did it continue from the right step (not restart)?
- Did it reference previous decisions?
- Did it NOT re-do completed work?

Return JSON: {{"score": int, "findings": [str]}}
"""
        try:
            response = await self.llm.generate(prompt=prompt, model="claude-sonnet-4-20250514")
            import json
            data = json.loads(response.text)
            return AnalysisResult(
                score=data.get("score", 0),
                findings=data.get("findings", []),
            )
        except Exception as e:
            return AnalysisResult(score=0, findings=[f"Analysis failed: {e}"])

    async def analyze_stop_cascade(self, tl_transcript: str,
                                   agent_transcripts: dict[str, str]) -> AnalysisResult:
        """Did the stop cascade execute correctly?"""
        agent_summary = "\n".join(
            f"- {name}: {transcript[:500]}"
            for name, transcript in list(agent_transcripts.items())[:5]
        )
        prompt = f"""\
Analyze whether the Team Leader correctly cascaded a stop signal to all agents.

Team Leader transcript (last 2000 chars):
{tl_transcript[-2000:]}

Agent transcripts (summaries):
{agent_summary}

Check:
- Did TL send stop messages to agents?
- Did agents acknowledge and checkpoint?
- Was the cascade timely (not delayed)?

Return JSON: {{"score": int, "findings": [str]}}
"""
        try:
            response = await self.llm.generate(prompt=prompt, model="claude-sonnet-4-20250514")
            import json
            data = json.loads(response.text)
            return AnalysisResult(
                score=data.get("score", 0),
                findings=data.get("findings", []),
            )
        except Exception as e:
            return AnalysisResult(score=0, findings=[f"Analysis failed: {e}"])

    async def analyze_conversation_continuity(self, pre_transcript: str,
                                              post_transcript: str) -> AnalysisResult:
        """Did the agent maintain conversational context across sessions?"""
        prompt = f"""\
Analyze whether this agent maintained conversational context across a stop/resume cycle.

Pre-stop transcript (last 2000 chars):
{pre_transcript[-2000:]}

Post-resume transcript (first 2000 chars):
{post_transcript[:2000]}

Check:
- Does the agent reference previous exchanges?
- Does it build on previous decisions?
- Does it avoid re-asking answered questions?
- Does it acknowledge the time gap?

Return JSON: {{"score": int, "findings": [str]}}
"""
        try:
            response = await self.llm.generate(prompt=prompt, model="claude-sonnet-4-20250514")
            import json
            data = json.loads(response.text)
            return AnalysisResult(
                score=data.get("score", 0),
                findings=data.get("findings", []),
            )
        except Exception as e:
            return AnalysisResult(score=0, findings=[f"Analysis failed: {e}"])

    async def analyze_instruction_adaptation(self, old_instructions: str,
                                             new_instructions: str,
                                             post_resume_transcript: str) -> AnalysisResult:
        """Did the agent correctly adapt to updated instruction files?"""
        prompt = f"""\
Analyze whether this agent adapted to updated instruction files after resume.

Key differences between old and new instructions:
Old (first 1000 chars): {old_instructions[:1000]}
New (first 1000 chars): {new_instructions[:1000]}

Post-resume transcript (first 2000 chars):
{post_resume_transcript[:2000]}

Check:
- Does the agent follow new guidance?
- Does it preserve task state from checkpoint?
- Does it acknowledge instruction changes?

Return JSON: {{"score": int, "findings": [str]}}
"""
        try:
            response = await self.llm.generate(prompt=prompt, model="claude-sonnet-4-20250514")
            import json
            data = json.loads(response.text)
            return AnalysisResult(
                score=data.get("score", 0),
                findings=data.get("findings", []),
            )
        except Exception as e:
            return AnalysisResult(score=0, findings=[f"Analysis failed: {e}"])

    async def generate_improvement_suggestions(self, analysis_results: list[AnalysisResult],
                                               skill_content: str) -> list[str]:
        """Based on analysis failures, suggest improvements to the checkpoint skill."""
        findings = []
        for result in analysis_results:
            findings.extend(result.findings)

        if not findings:
            return []

        prompt = f"""\
Based on these E2E test findings, suggest specific improvements to the
checkpoint skill file.

Findings:
{chr(10).join(f'- {f}' for f in findings[:20])}

Current skill content (first 2000 chars):
{skill_content[:2000]}

Return JSON: {{"suggestions": [str]}}
"""
        try:
            response = await self.llm.generate(prompt=prompt, model="claude-sonnet-4-20250514")
            import json
            data = json.loads(response.text)
            return data.get("suggestions", [])
        except Exception:
            return []
