"""Testes do fluxo editorial V3 (backend)."""
from __future__ import annotations

import json
from typing import Any

import pytest

from content_engine.editorial_flow import assign_storyboard_blocks, compute_briefing_fingerprint, derive_editorial_status
from content_engine.editorial_generation import parse_approaches, parse_storyboard_blocks
from content_engine.schemas import AgentResult
from gui.server import GuiController
from tests.llm_fakes import AgentFakeRunMixin


class FakeAgent(AgentFakeRunMixin):
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.index = 0

    def run_codex(
        self,
        prompt: str,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        sandbox: str = "read-only",
        json_output: bool = False,
        extra_context: str | None = None,
        ephemeral: bool = True,
        ignore_user_config: bool = False,
        runner: Any = None,
    ) -> AgentResult:
        del prompt, model, reasoning_effort, sandbox, extra_context, ephemeral
        del ignore_user_config, runner
        stdout = self.responses[min(self.index, len(self.responses) - 1)]
        self.index += 1
        return AgentResult(
            tool="codex",
            command=["codex"],
            returncode=0,
            stdout=stdout,
            stderr="",
            events=None,
            error=None,
        )


@pytest.fixture()
def controller(tmp_path, monkeypatch):
    monkeypatch.setattr("content_engine.llm_config.CONFIG_FILE", tmp_path / "agent-config.yml")
    monkeypatch.setattr("content_engine.llm_config.DATA_DIR", tmp_path)
    ctrl = GuiController(session_path=tmp_path / "session.json")
    return ctrl


def test_parse_storyboard_blocks_rejects_invalid() -> None:
    with pytest.raises(Exception):
        parse_storyboard_blocks({"blocks": [{"role": "", "focus": "x"}]})


def test_parse_approaches_requires_three() -> None:
    with pytest.raises(Exception):
        parse_approaches({"approaches": [{"title": "A", "description": "B"}]})


def test_assign_storyboard_increments_order() -> None:
    blocks = assign_storyboard_blocks(
        [{"role": "Gancho", "focus": "Abrir tensao"}],
        version=2,
    )
    assert blocks[0]["order"] == 1
    assert blocks[0]["revision"] == 2


def test_generate_storyboard_action(controller, monkeypatch) -> None:
    payload = {
        "blocks": [
            {"role": "Gancho", "focus": "Capturar atencao"},
            {"role": "Desenvolvimento", "focus": "Explicar ideia central"},
        ]
    }
    agent = FakeAgent([json.dumps(payload)])

    def factory():
        return agent

    monkeypatch.setattr(controller.app, "_agent_factory", factory)
    controller.app.state.briefing_autoral = {"tese": "Teste"}
    controller.app.state.tema = "Tema"
    controller.action("generate_storyboard", {})
    snap = controller.snapshot()
    blocks = snap["state"]["editorial_flow"]["storyboard"]["blocks"]
    assert len(blocks) == 2
    assert snap["derived"]["editorial"]["storyboard_available"] is True
    assert snap["derived"]["active_stage"] == "storyboard"
    assert snap["derived"]["active_status_text"] == "Fase ativa: Storyboard."


def test_update_storyboard_invalidates_drafts(controller) -> None:
    fp = compute_briefing_fingerprint(controller.app.state)
    controller.app.state.editorial_flow = {
        "schema_version": "1.0",
        "briefing_fingerprint": fp,
        "storyboard": {
            "version": 1,
            "status": "available",
            "blocks": [{"id": "b1", "order": 1, "role": "A", "focus": "f", "revision": 1}],
        },
        "drafts": {
            "storyboard_version": 1,
            "by_block": {"b1": {"status": "available", "options": [], "selected_option_id": None}},
        },
        "composition": {"status": "available", "selection_fingerprint": "fp", "conteudo": "x", "conteudo_json": {}},
    }
    controller.action(
        "update_storyboard",
        {"blocks": [{"id": "b1", "role": "A", "focus": "novo foco"}]},
    )
    snap = controller.snapshot()
    assert snap["state"]["editorial_flow"]["storyboard"]["version"] == 2
    assert snap["state"]["editorial_flow"]["drafts"]["by_block"] == {}


def test_generate_block_drafts_keeps_generated_options(controller, monkeypatch) -> None:
    responses = [
        json.dumps(
            {
                "approaches": [
                    {"title": "A", "description": "Primeira abordagem"},
                    {"title": "B", "description": "Segunda abordagem"},
                    {"title": "C", "description": "Terceira abordagem"},
                ]
            }
        ),
        json.dumps({"draft": {"content": "Rascunho A"}}),
        json.dumps({"draft": {"content": "Rascunho B"}}),
        json.dumps({"draft": {"content": "Rascunho C"}}),
    ]
    agent = FakeAgent(responses)

    def factory():
        return agent

    monkeypatch.setattr(controller.app, "_agent_factory", factory)
    controller.app.state.briefing_autoral = {"tese": "Teste"}
    controller.app.state.tema = "Tema"
    controller.app.state.editorial_flow = {
        "schema_version": "1.0",
        "storyboard": {
            "version": 1,
            "status": "available",
            "blocks": [{"id": "b1", "order": 1, "role": "Gancho", "focus": "Abrir tese", "revision": 1}],
        },
        "drafts": {"storyboard_version": 1, "by_block": {}},
        "composition": {"status": "available", "selection_fingerprint": "fp", "conteudo": "x", "conteudo_json": {}},
    }

    controller.action("generate_block_drafts", {"block_id": "b1"})
    snap = controller.snapshot()
    entry = snap["state"]["editorial_flow"]["drafts"]["by_block"]["b1"]

    assert entry["status"] == "available"
    assert [option["content"] for option in entry["options"]] == ["Rascunho A", "Rascunho B", "Rascunho C"]
    assert snap["state"]["editorial_flow"]["composition"]["status"] == "empty"
    assert snap["derived"]["editorial"]["drafts_available"] is True
    assert snap["derived"]["active_stage"] == "drafts"
    assert snap["derived"]["active_status_text"] == "Fase ativa: Rascunhos."


def test_snapshot_preserves_editorial_stage_across_restore(controller) -> None:
    controller.app.state.current_phase = "briefing_autoral"
    controller.app.state.current_stage = "drafts"
    controller.app.state.status_operacional = "Fase ativa: Rascunhos."
    controller.app._persistir()

    restored = GuiController(session_path=controller.app.session_path)
    snap = restored.snapshot()

    assert snap["state"]["current_phase"] == "briefing_autoral"
    assert snap["state"]["current_stage"] == "drafts"
    assert snap["derived"]["active_stage"] == "drafts"
    assert snap["derived"]["active_status_text"] == "Fase ativa: Rascunhos."


def test_navigate_by_editorial_stage(controller) -> None:
    controller.app.state.current_phase = "briefing_autoral"
    controller.app.state.current_stage = "briefing"
    controller.action("navigate", {"stage": "drafts"})
    snap = controller.snapshot()

    assert snap["state"]["current_stage"] == "drafts"
    assert snap["state"]["current_phase"] == "briefing_autoral"
    assert snap["derived"]["active_stage"] == "drafts"
    assert snap["derived"]["active_status_text"] == "Fase ativa: Rascunhos."


def _two_block_storyboard() -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "storyboard": {
            "version": 1,
            "status": "available",
            "blocks": [
                {"id": "b1", "order": 1, "role": "Gancho", "focus": "Abrir tese", "revision": 1},
                {"id": "b2", "order": 2, "role": "Diagnostico", "focus": "Problema", "revision": 1},
            ],
        },
        "drafts": {"storyboard_version": 1, "by_block": {}},
        "composition": {"status": "empty", "selection_fingerprint": "", "conteudo": "", "conteudo_json": {}},
    }


def test_generate_block_drafts_requires_prior_selection(controller) -> None:
    controller.app.state.editorial_flow = _two_block_storyboard()
    controller.action("generate_block_drafts", {"block_id": "b2"})
    assert controller.app.state.error is not None
    assert "Selecione o bloco anterior" in controller.app.state.error


def test_generate_all_block_drafts_rejected(controller) -> None:
    controller.app.state.editorial_flow = _two_block_storyboard()
    controller.action("generate_all_block_drafts", {})
    assert controller.app.state.error is not None
    assert "lote" in controller.app.state.error.lower()


def test_select_block_invalidates_downstream(controller) -> None:
    flow = _two_block_storyboard()
    flow["drafts"]["by_block"] = {
        "b1": {
            "status": "available",
            "selected_option_id": "o1",
            "options": [
                {
                    "id": "o1",
                    "approach": {"title": "T", "description": "D"},
                    "persona_id": "observador",
                    "persona_name": "O Observador",
                    "content": "Gancho escolhido",
                    "status": "available",
                    "obsolete": False,
                }
            ],
        },
        "b2": {
            "status": "available",
            "selected_option_id": "o2",
            "options": [
                {
                    "id": "o2",
                    "approach": {"title": "T2", "description": "D2"},
                    "persona_id": "observador",
                    "persona_name": "O Observador",
                    "content": "Diagnostico escolhido",
                    "status": "available",
                    "obsolete": False,
                }
            ],
        },
    }
    controller.app.state.editorial_flow = flow
    controller.action("select_block_draft", {"block_id": "b1", "option_id": "o1"})
    snap = controller.snapshot()
    assert "b2" not in snap["state"]["editorial_flow"]["drafts"]["by_block"]


class PromptCapturingAgent(AgentFakeRunMixin):
    def __init__(self, responses: list[str]) -> None:
        self.responses = list(responses)
        self.index = 0
        self.prompts: list[str] = []

    def run_codex(
        self,
        prompt: str,
        *,
        model: str | None = None,
        reasoning_effort: str | None = None,
        sandbox: str = "read-only",
        json_output: bool = False,
        extra_context: str | None = None,
        ephemeral: bool = True,
        ignore_user_config: bool = False,
        runner: Any = None,
    ) -> AgentResult:
        self.prompts.append(prompt)
        del model, reasoning_effort, sandbox, extra_context, ephemeral
        del ignore_user_config, runner
        stdout = self.responses[min(self.index, len(self.responses) - 1)]
        self.index += 1
        return AgentResult(
            tool="codex",
            command=["codex"],
            returncode=0,
            stdout=stdout,
            stderr="",
            events=None,
            error=None,
        )


def test_previous_selected_drafts_in_prompt(controller, monkeypatch) -> None:
    responses = [
        json.dumps(
            {
                "approaches": [
                    {"title": "A", "description": "Primeira abordagem"},
                    {"title": "B", "description": "Segunda abordagem"},
                    {"title": "C", "description": "Terceira abordagem"},
                ]
            }
        ),
        json.dumps({"draft": {"content": "Rascunho A"}}),
        json.dumps({"draft": {"content": "Rascunho B"}}),
        json.dumps({"draft": {"content": "Rascunho C"}}),
    ]
    agent = PromptCapturingAgent(responses)

    def factory():
        return agent

    monkeypatch.setattr(controller.app, "_agent_factory", factory)
    controller.app.state.briefing_autoral = {"tese": "Teste"}
    controller.app.state.tema = "Tema"
    flow = _two_block_storyboard()
    flow["drafts"]["by_block"] = {
        "b1": {
            "status": "available",
            "selected_option_id": "o1",
            "options": [
                {
                    "id": "o1",
                    "approach": {"title": "T", "description": "D"},
                    "persona_id": "observador",
                    "persona_name": "O Observador",
                    "content": "Texto do gancho selecionado",
                    "status": "available",
                    "obsolete": False,
                }
            ],
        },
    }
    controller.app.state.editorial_flow = flow

    controller.action("generate_block_drafts", {"block_id": "b2"})
    assert agent.prompts
    assert "Texto do gancho selecionado" in agent.prompts[0]
    assert "previousSelectedDraftsJson" not in agent.prompts[0]
    draft_prompts = [p for p in agent.prompts if "Texto do gancho selecionado" in p]
    assert len(draft_prompts) >= 1


def test_block_draft_prompt_contains_anti_ia_policies(controller, monkeypatch) -> None:
    responses = [
        json.dumps(
            {
                "approaches": [
                    {"title": "A", "description": "Primeira abordagem"},
                    {"title": "B", "description": "Segunda abordagem"},
                    {"title": "C", "description": "Terceira abordagem"},
                ]
            }
        ),
        json.dumps({"draft": {"content": "Rascunho A"}}),
        json.dumps({"draft": {"content": "Rascunho B"}}),
        json.dumps({"draft": {"content": "Rascunho C"}}),
    ]
    agent = PromptCapturingAgent(responses)

    def factory():
        return agent

    monkeypatch.setattr(controller.app, "_agent_factory", factory)
    controller.app.state.briefing_autoral = {"tese": "Teste"}
    controller.app.state.tema = "Tema"
    flow = _two_block_storyboard()
    flow["drafts"]["by_block"] = {}
    controller.app.state.editorial_flow = flow

    controller.action("generate_block_drafts", {"block_id": "b1"})
    draft_prompts = [p for p in agent.prompts if "Políticas anti-IA obrigatórias" in p]
    assert draft_prompts, "Draft prompt deve conter a secao de politicas anti-IA"
    assert "VOICE_01" in draft_prompts[0]
    assert "STYLE_01" in draft_prompts[0]
    assert "hard" in draft_prompts[0]
    assert "{{politicasAntiIa}}" not in draft_prompts[0]


def test_selection_blocks_compose(controller) -> None:
    controller.app.state.editorial_flow = {
        "schema_version": "1.0",
        "storyboard": {
            "version": 1,
            "status": "available",
            "blocks": [{"id": "b1", "order": 1, "role": "A", "focus": "f", "revision": 1}],
        },
        "drafts": {
            "storyboard_version": 1,
            "by_block": {
                "b1": {
                    "status": "available",
                    "selected_option_id": None,
                    "options": [
                        {
                            "id": "o1",
                            "approach": {"title": "T", "description": "D"},
                            "persona_id": "observador",
                            "persona_name": "O Observador",
                            "content": "Texto",
                            "status": "available",
                            "obsolete": False,
                        }
                    ],
                }
            },
        },
        "composition": {"status": "empty", "selection_fingerprint": "", "conteudo": "", "conteudo_json": {}},
    }
    controller.action("compose_editorial", {})
    assert controller.app.state.error is not None
    status = derive_editorial_status(controller.app.state.editorial_flow)
    assert status["can_compose"] is False
