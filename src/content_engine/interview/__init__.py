"""Public V4 interview API."""
from .briefing import build_briefing
from .controller import InterviewController
from .exploration import (
    QuestionGenerationError,
    generate_candidates,
    generate_next_question,
    select_question,
)
from .gateway import evaluate_gateway, gateway_desequilibrado_forte, gateway_equilibrado
from .gaps import decide_deepening, explain_decision, identify_gaps
from .heuristic import DIMENSION_CATALOG, assess_dimensions, detect_absolute_vetos
from .schemas import (
    SESSION_SCHEMA_VERSION,
    AuthorialDimension,
    AuthorialSignal,
    DeepeningDecision,
    DeterministicAssessment,
    DimensionScore,
    Evidence,
    Gap,
    GatewayResult,
    InterviewState,
    InterviewV4Session,
    LlmAssessment,
    QuestionCandidate,
    SelectedQuestion,
    ThemeContext,
    UserAnswer,
    create_initial_state,
    criar_estado_inicial,
)
from .ui import build_interview_ui

__all__ = [
    "DIMENSION_CATALOG",
    "AuthorialDimension",
    "AuthorialSignal",
    "DeepeningDecision",
    "DeterministicAssessment",
    "DimensionScore",
    "Evidence",
    "Gap",
    "GatewayResult",
    "InterviewController",
    "InterviewState",
    "InterviewV4Session",
    "LlmAssessment",
    "QuestionCandidate",
    "QuestionGenerationError",
    "SESSION_SCHEMA_VERSION",
    "SelectedQuestion",
    "ThemeContext",
    "UserAnswer",
    "assess_dimensions",
    "build_briefing",
    "build_interview_ui",
    "create_initial_state",
    "criar_estado_inicial",
    "decide_deepening",
    "detect_absolute_vetos",
    "evaluate_gateway",
    "explain_decision",
    "gateway_desequilibrado_forte",
    "gateway_equilibrado",
    "generate_candidates",
    "generate_next_question",
    "identify_gaps",
    "select_question",
]
