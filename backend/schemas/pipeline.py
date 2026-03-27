# pipeline.py — Pydantic models for pipeline state and run tracking.
# Depends on: nothing
# Depended on by: api/pipeline.py
from pydantic import BaseModel


class PipelineStatus(BaseModel):
    """Current state of the pipeline workflow."""
    current_step: int = 0  # 0=not started, 1-5 for each pass
    run_id: str = ""
    activation_complete: bool = False
    generation_complete: bool = False
    elimination_complete: bool = False
    conviction_complete: bool = False
    status: str = "idle"  # idle | running | complete | error
    error_message: str = ""


class RunSummary(BaseModel):
    """Summary of a completed pipeline run."""
    id: str
    timestamp: str
    status: str
    hypotheses_generated: int = 0
    hypotheses_survived: int = 0
    hypotheses_wounded: int = 0
    hypotheses_killed: int = 0
    theories_active: list[str] = []
