"""Shared contracts for the Post Engine runtime.

Interview-specific contracts live in :mod:`content_engine.interview.schemas`.
The session stores only the V4 interview projection and never carries an
alternative interview representation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


TipoDePost = Literal["post", "article", "short_carousel", "long_slide"]
ToolName = Literal["codex", "opencode", "cursor"]
SandboxPolicy = Literal["read-only", "workspace-write", "danger-full-access"]
SeveridadeSlide = Literal["baixa", "media", "alta"]

SESSION_SCHEMA_VERSION = "4.0"
INTERVIEW_SCHEMA_VERSION = SESSION_SCHEMA_VERSION

TIPOS_DE_POST_VALIDOS: tuple[TipoDePost, ...] = (
    "post",
    "article",
    "short_carousel",
    "long_slide",
)
FERRAMENTAS_VALIDAS: tuple[ToolName, ...] = ("codex", "opencode", "cursor")
SANDBOXES_VALIDOS: tuple[SandboxPolicy, ...] = (
    "read-only",
    "workspace-write",
    "danger-full-access",
)


def migrate_tipo_de_post(value: object) -> TipoDePost:
    """Return a valid content format without carrying session migrations."""

    if isinstance(value, str) and value in TIPOS_DE_POST_VALIDOS:
        return value  # type: ignore[return-value]
    return "post"


def is_tipo_de_post(value: object) -> bool:
    return isinstance(value, str) and value in TIPOS_DE_POST_VALIDOS


def is_tool(value: object) -> bool:
    return value in FERRAMENTAS_VALIDAS


def is_sandbox(value: object) -> bool:
    return value in SANDBOXES_VALIDOS


_SCORE_DO_POST_WEIGHTS: dict[str, int] = {
    "tese": 1,
    "progressao": 2,
    "concretude": 2,
    "precisao_tecnica": 2,
    "retencao": 1,
    "autoridade": 1,
    "autoria": 1,
    "slidemark": 1,
    "revisao_textual": 1,
}
_SCORE_DO_POST_WEIGHT_SUM = sum(_SCORE_DO_POST_WEIGHTS.values())


@dataclass(frozen=True)
class ScoreDoPost:
    tese: int
    progressao: int
    concretude: int
    precisao_tecnica: int
    retencao: int
    autoridade: int
    autoria: int
    slidemark: int
    revisao_textual: int

    @property
    def total(self) -> float:
        weighted = (
            self.tese * _SCORE_DO_POST_WEIGHTS["tese"]
            + self.progressao * _SCORE_DO_POST_WEIGHTS["progressao"]
            + self.concretude * _SCORE_DO_POST_WEIGHTS["concretude"]
            + self.precisao_tecnica * _SCORE_DO_POST_WEIGHTS["precisao_tecnica"]
            + self.retencao * _SCORE_DO_POST_WEIGHTS["retencao"]
            + self.autoridade * _SCORE_DO_POST_WEIGHTS["autoridade"]
            + self.autoria * _SCORE_DO_POST_WEIGHTS["autoria"]
            + self.slidemark * _SCORE_DO_POST_WEIGHTS["slidemark"]
            + self.revisao_textual * _SCORE_DO_POST_WEIGHTS["revisao_textual"]
        ) / _SCORE_DO_POST_WEIGHT_SUM
        result = round(weighted, 1)
        if self.tese >= 8 and self.progressao < 5:
            result = min(result, 7.0)
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "tese": self.tese,
            "progressao": self.progressao,
            "concretude": self.concretude,
            "precisao_tecnica": self.precisao_tecnica,
            "retencao": self.retencao,
            "autoridade": self.autoridade,
            "autoria": self.autoria,
            "slidemark": self.slidemark,
            "revisao_textual": self.revisao_textual,
            "total": self.total,
        }


@dataclass(frozen=True)
class TrechoFraco:
    trecho: int
    problema: str
    severidade: SeveridadeSlide
    motivo: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "trecho": self.trecho,
            "problema": self.problema,
            "severidade": self.severidade,
            "motivo": self.motivo,
        }


@dataclass(frozen=True)
class AvaliacaoSlideMark:
    score: ScoreDoPost
    veredito: str
    pontos_fortes: list[str]
    pontos_fracos: list[str]
    trechos_fracos: list[TrechoFraco]
    redundancias: list[str]
    falhas_tecnicas: list[str]
    sugestoes_melhoria: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score.to_dict(),
            "veredito": self.veredito,
            "pontos_fortes": list(self.pontos_fortes),
            "pontos_fracos": list(self.pontos_fracos),
            "trechos_fracos": [item.to_dict() for item in self.trechos_fracos],
            "redundancias": list(self.redundancias),
            "falhas_tecnicas": list(self.falhas_tecnicas),
            "sugestoes_melhoria": list(self.sugestoes_melhoria),
        }


@dataclass(frozen=True)
class SegmentoPost:
    id: str
    ordem: int
    texto: str
    papel_interno: str


@dataclass(frozen=True)
class SugestaoImagem:
    modo: str
    descricao: str
    url: str | None = None
    fonte: str | None = None


@dataclass(frozen=True)
class SlideContent:
    numero: int
    titulo: str
    bullets: list[str]
    notas_visuais: str | None = None
    sugestao_imagem: SugestaoImagem | None = None


@dataclass(frozen=True)
class GenerationPromptInput:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    briefing_autoral: dict[str, Any]
    interview_context: dict[str, Any] | None = None
    gateway_result: dict[str, Any] | None = None
    restricoes_de_geracao: list[str] | None = None
    personalidade: str | None = None


@dataclass
class AgentResult:
    tool: ToolName
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    events: list[dict[str, Any]] | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.error is None


@dataclass
class TuiSessionState:
    session_id: str = ""
    session_log_path: str = ""
    current_phase: str = "entrada_inicial"
    current_stage: str = "entry"

    tema: str = ""
    plataforma: str = ""
    objetivo_do_post: str = ""
    personalidade: str = ""
    tipo_de_post: TipoDePost = "post"
    slides_gerados: list[dict[str, Any]] = field(default_factory=list)
    tool: ToolName = "codex"
    model: str | None = None
    sandbox: SandboxPolicy = "read-only"

    briefing_autoral: dict[str, Any] = field(default_factory=dict)
    restricoes_de_geracao: list[str] = field(default_factory=list)
    interview_state: dict[str, Any] | None = None
    evidence_ledger: list[dict[str, Any]] = field(default_factory=list)
    gateway_result: dict[str, Any] = field(default_factory=dict)

    fase_atual: str = "entrada"
    status_operacional: str = "Aguardando entrada inicial."
    prompt_renderizado: str = ""
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    events: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None
    conteudo_gerado: str = ""
    conteudo_json: dict[str, Any] = field(default_factory=dict)
    segmentos: list[dict[str, Any]] = field(default_factory=list)
    avaliacao_post: dict[str, Any] = field(default_factory=dict)
    is_running: bool = False
    _segmento_index: int | None = None
    editorial_flow: dict[str, Any] = field(default_factory=dict)


__all__ = [
    "AgentResult",
    "AvaliacaoSlideMark",
    "FERRAMENTAS_VALIDAS",
    "GenerationPromptInput",
    "INTERVIEW_SCHEMA_VERSION",
    "SANDBOXES_VALIDOS",
    "SESSION_SCHEMA_VERSION",
    "SandboxPolicy",
    "ScoreDoPost",
    "SegmentoPost",
    "SeveridadeSlide",
    "SlideContent",
    "SugestaoImagem",
    "TIPOS_DE_POST_VALIDOS",
    "TipoDePost",
    "ToolName",
    "TrechoFraco",
    "TuiSessionState",
    "is_sandbox",
    "is_tipo_de_post",
    "is_tool",
    "migrate_tipo_de_post",
]
