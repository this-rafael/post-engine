from __future__ import annotations

import json
from typing import Any

from content_engine.editorial_generation import EditorialComposer, collect_selected_drafts
from content_engine.schemas import AgentResult, TuiSessionState
from tests.llm_fakes import AgentFakeRunMixin


class RecordingAgent(AgentFakeRunMixin):
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self.payloads = list(payloads)
        self.prompts: list[str] = []
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
        del model, reasoning_effort, sandbox, json_output, extra_context
        del ephemeral, ignore_user_config, runner
        self.prompts.append(prompt)
        payload = self.payloads[min(self.index, len(self.payloads) - 1)]
        self.index += 1
        return AgentResult(
            tool="codex",
            command=["codex", "exec"],
            returncode=0,
            stdout=json.dumps(payload, ensure_ascii=False),
            stderr="",
            events=None,
            error=None,
        )


def _flow_for_selected(contents: list[str]) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    by_block: dict[str, Any] = {}
    for index, content in enumerate(contents, start=1):
        block_id = f"blk-{index}"
        option_id = f"opt-{index}"
        blocks.append(
            {
                "id": block_id,
                "order": index,
                "role": f"papel {index}",
                "focus": f"foco {index}",
            }
        )
        by_block[block_id] = {
            "selected_option_id": option_id,
            "options": [
                {
                    "id": option_id,
                    "content": content,
                    "persona_id": "persona",
                    "approach": {"title": "direta"},
                }
            ],
        }
    return {"storyboard": {"version": 1, "blocks": blocks}, "drafts": {"by_block": by_block}}


def _compose(
    contents: list[str],
    payloads: list[dict[str, Any]],
    *,
    tipo_de_post: str = "post",
) -> tuple[Any, Any, RecordingAgent]:
    flow = _flow_for_selected(contents)
    state = TuiSessionState(
        tema="Fronteiras de servico",
        plataforma="linkedin",
        objetivo_do_post="Ensinar decisao arquitetural com evidencia.",
        personalidade="cética e concreta",
        tipo_de_post=tipo_de_post,  # type: ignore[arg-type]
        briefing_autoral={
            "theme": "Fronteiras de servico",
            "objective": "Ensinar com exemplos",
        },
        interview_state={
            "schema_version": "4.0",
            "context": {"tema": "Fronteiras de servico", "objetivo": "Ensinar com exemplos"},
        },
        evidence_ledger=[
            {
                "id": "evidence-1",
                "text": "O checkout parecia independente apenas no diagrama.",
                "source_answer_id": "answer-1",
            },
            {
                "id": "evidence-2",
                "text": "O diagrama parece moderno. O acoplamento continua.",
                "source_answer_id": "answer-1",
            },
        ],
    )
    selected = collect_selected_drafts(flow)
    agent = RecordingAgent(payloads)
    conteudo, run = EditorialComposer(agent).compose(state, flow, selected_drafts=selected)
    return conteudo, run, agent


def _payload(conteudo: str) -> dict[str, Any]:
    return {"conteudo": conteudo, "metadados": {}, "alertas": []}


def test_rejects_concrete_example_reduced_to_abstract_category() -> None:
    source = "Consistência eventual aparece quando o cliente pagou, mas o pedido ainda não aparece."
    conteudo, run, agent = _compose([source], [_payload("Consistência eventual exige reconciliação.")])

    assert conteudo is None
    assert run.ok is False
    assert "situacao_concreta" in (run.error or "")
    assert len(agent.prompts) == 2


def test_rejects_causal_chain_reduced_to_label() -> None:
    source = (
        "Mudanças atravessavam checkout e financeiro → contratos evoluíam juntos "
        "→ deploy exigia coordenação."
    )
    conteudo, run, _ = _compose([source], [_payload("Os serviços continuaram acoplados.")])

    assert conteudo is None
    assert run.ok is False
    assert "cadeia_causal" in (run.error or "")


def test_rejects_authorial_graph_method_reduced_to_metrics() -> None:
    source = "Transforme módulos, tabelas, chamadas e commits em um grafo simples. Veja quais nós concentram dependência."
    conteudo, run, _ = _compose([source], [_payload("Avalie fan-in, fan-out e dependências circulares.")])

    assert conteudo is None
    assert run.ok is False
    assert "metodo_autoral" in (run.error or "")


def test_rejects_ambiguous_logical_to_physical_extraction() -> None:
    source = "Isolar módulo → estabilizar borda → testar progressivamente → extração física."
    conteudo, run, _ = _compose([source], [_payload("Migre tráfego aos poucos e só depois extraia o serviço.")])

    assert conteudo is None
    assert run.ok is False
    assert "sequencia_operacional" in (run.error or "")


def test_allows_removing_literal_repetition_when_concrete_anchor_survives() -> None:
    source = (
        "O cliente pagou, mas o pedido ainda não aparece. "
        "Consistência eventual é consistência eventual. Consistência eventual é consistência eventual."
    )
    output = "O cliente pagou, mas o pedido ainda não aparece: esse é o custo observável da consistência eventual."
    conteudo, run, agent = _compose([source], [_payload(output)])

    assert run.ok is True
    assert conteudo is not None
    assert conteudo.conteudo == output
    assert conteudo.conteudo.lower().count("consistência eventual") == 1
    assert len(agent.prompts) == 1


def test_allows_cohesive_bridge_without_replacing_selected_material() -> None:
    sources = [
        "O cliente pagou, mas o pedido ainda não aparece: distribuir cobra uma conta operacional.",
        "Isolar módulo → estabilizar borda → testar progressivamente → extração física.",
        "A sprint pede um atalho, mas atalho sem etiqueta vira dívida permanente.",
    ]
    output = (
        "Quando o cliente pagou, mas o pedido ainda não aparece, o custo da distribuição deixou de ser abstrato. "
        "Por isso, antes de extrair: isole o módulo, estabilize a borda, teste progressivamente e faça a extração física. "
        "Se a sprint pedir um atalho, nomeie a dívida: atalho sem etiqueta vira dívida permanente."
    )
    conteudo, run, _ = _compose(sources, [_payload(output)])

    assert run.ok is True
    assert conteudo is not None
    assert "Por isso" in conteudo.conteudo
    assert "→" not in conteudo.conteudo


def test_compose_prompt_contains_full_source_contract_and_authorial_context() -> None:
    source = "O cliente pagou, mas o pedido ainda não aparece."
    output = "O cliente pagou, mas o pedido ainda não aparece; consistência eventual tem custo observável."
    conteudo, run, agent = _compose([source], [_payload(output)], tipo_de_post="long_slide")

    assert run.ok is True
    assert conteudo is not None
    prompt = agent.prompts[0]
    assert source in prompt
    assert "Anchors editoriais prioritários" in prompt
    assert "O checkout parecia independente apenas no diagrama." in prompt
    assert "Ensinar com exemplos" in prompt
    assert "9 a 20 slides" in prompt
    assert "{{" not in prompt
    assert "{[" not in prompt


def test_compose_prompt_contains_anti_ia_policies() -> None:
    source = "O cliente pagou, mas o pedido ainda não aparece."
    output = "O cliente pagou, mas o pedido ainda não aparece; consistência eventual tem custo observável."
    conteudo, run, agent = _compose([source], [_payload(output)])

    assert run.ok is True
    prompt = agent.prompts[0]
    assert "Políticas anti-IA obrigatórias" in prompt
    assert "VOICE_01" in prompt
    assert "VOICE_02" in prompt
    assert "STYLE_01" in prompt
    assert "STYLE_02" in prompt
    assert "travessão" in prompt.lower() or "travessao" in prompt.lower()
    assert "hard" in prompt
    assert "{{politicasAntiIa}}" not in prompt


def test_long_slide_anchor_can_survive_in_slidemark_without_plain_content() -> None:
    source = "O cliente pagou, mas o pedido ainda não aparece."
    payload = {
        "slidemark": {
            "version": "1.0.0",
            "slides": [
                {
                    "id": "consistencia-01",
                    "type": "content.text",
                    "title": "O estado que o cliente enxerga",
                    "body": ["O cliente pagou, mas o pedido ainda não aparece."],
                }
            ],
        },
        "metadados": {},
        "alertas": [],
    }
    conteudo, run, _ = _compose([source], [payload], tipo_de_post="long_slide")

    assert run.ok is True
    assert conteudo is not None
    assert "cliente pagou" in conteudo.conteudo
