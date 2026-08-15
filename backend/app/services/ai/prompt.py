"""Prompt construction and versioning for the role analysis engine.

The prompt template is versioned by its content hash. Any change to the
template automatically produces a new ``PROMPT_VERSION``, ensuring
traceability between prompt revisions and analysis results.
"""

from __future__ import annotations

import hashlib
import json

from app.services.ai.base import AIAnalysisRequest

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_OUTPUT_SCHEMA = json.dumps(
    {
        "ai_exposure_score": "<float 0.0-1.0>",
        "ai_exposure_summary": "<1-3 sentence overview of AI exposure>",
        "automation_score": "<float 0.0-1.0>",
        "augmentation_score": "<float 0.0-1.0>",
        "reskilling_priority": "<low|medium|high|critical>",
        "activity_impacts": [
            {
                "activity_ref": "act_N",
                "automation_score": "<float 0.0-1.0>",
                "augmentation_score": "<float 0.0-1.0>",
                "human_responsibility": "<what remains the human's responsibility for this activity>",
                "description": "<brief impact description>",
            }
        ],
        "future_responsibilities": [
            {
                "title": "<responsibility title>",
                "description": "<what this involves>",
                "rationale": "<why this becomes important>",
            }
        ],
        "future_skills": [
            {
                "name": "<skill name>",
                "category": "<skill category>",
                "relevance": "<float 0.0-1.0>",
                "priority": "<low|medium|high|critical>",
            }
        ],
        "recommendations": [
            {
                "title": "<recommendation title>",
                "description": "<actionable detail>",
                "rationale": "<why this matters>",
                "priority": "<low|medium|high|critical>",
            }
        ],
        "reasoning": "<2-4 sentence explanation of overall assessment>",
    },
    indent=2,
)

PROMPT_TEMPLATE = """\
You are an AI-powered workforce intelligence engine. Analyze the role below \
and produce a structured JSON assessment of AI exposure, automation potential, \
and future skill requirements.

## Role
- Name: {role_name}
- Description: {role_description}
- Industry: {industry}

## Processes
{processes_section}

## Activities
{activities_section}
Each activity is labeled with a temporary reference (act_0, act_1, ...) for \
your response.

## Current Skills
{skills_section}

## Output
Return exactly one JSON object matching this schema:

{output_schema}

## Guidelines
- Scores: 0.0 (none) to 1.0 (full exposure/automation/augmentation).
- reskilling_priority levels: low (well-positioned), medium (some reskilling \
needed), high (significant reskilling needed), critical (role at risk).
- Be specific to the provided context; avoid generic statements.
- activity_impacts MUST include entries for ALL activities listed above, \
using their exact temporary references (act_0, act_1, ...). For each one \
describe human_responsibility: the judgement/oversight/interaction that \
remains with the human even as AI automates or augments the work.
- future_skills should focus on emerging skills NOT already in the current \
skill set.
- Recommendations should be actionable and prioritised by impact.
- reasoning should explain your overall assessment in 2-4 sentences.
"""


# ---------------------------------------------------------------------------
# Versioning
# ---------------------------------------------------------------------------

PROMPT_VERSION: str = hashlib.sha256(PROMPT_TEMPLATE.encode()).hexdigest()[:16]

ANALYSIS_VERSION: str = "3.0.0"


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def _build_processes_section(request: AIAnalysisRequest) -> str:
    if not request.processes:
        return "- No processes defined for this role."
    lines = []
    for i, p in enumerate(request.processes, 1):
        desc = f" -- {p.description}" if p.description else ""
        lines.append(f"{i}. {p.name}{desc}")
    return "\n".join(lines)


def _build_activities_section(request: AIAnalysisRequest) -> str:
    if not request.activities:
        return "- No activities defined for this role."
    lines = []
    for a in request.activities:
        involvement = a.current_human_involvement or "unknown"
        desc = f" -- {a.description}" if a.description else ""
        lines.append(
            f"- [{a.temp_ref}] {a.name} (human involvement: {involvement}){desc}"
        )
    return "\n".join(lines)


def _build_skills_section(request: AIAnalysisRequest) -> str:
    if not request.current_skills:
        return "- No skills defined for this role."
    lines = []
    for s in request.current_skills:
        cat = f" [{s.category}]" if s.category else ""
        desc = f" -- {s.description}" if s.description else ""
        lines.append(f"- {s.name}{cat}{desc}")
    return "\n".join(lines)


def build_analysis_prompt(request: AIAnalysisRequest) -> str:
    """Build the complete analysis prompt from a structured request."""
    return PROMPT_TEMPLATE.format(
        role_name=request.role_name,
        role_description=request.role_description or "Not provided",
        industry=request.industry or "Not specified",
        processes_section=_build_processes_section(request),
        activities_section=_build_activities_section(request),
        skills_section=_build_skills_section(request),
        output_schema=_OUTPUT_SCHEMA,
    )
