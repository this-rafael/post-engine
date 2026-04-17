"""Parser de JSON de saida LLM: Codex (legacy) e OpenCode."""
from __future__ import annotations

import json

from content_engine.llm_json_parser import extract_json_object_from_llm_output


def _opencode_ndjson_with_fenced_payload(payload: dict) -> str:
    """Simula stdout JSONL do OpenCode com ``part.text`` em fence markdown."""
    text = "```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```"
    events = [
        {
            "type": "step_start",
            "timestamp": 1,
            "sessionID": "ses_test",
            "part": {"id": "prt_1", "type": "step-start"},
        },
        {
            "type": "text",
            "timestamp": 2,
            "sessionID": "ses_test",
            "part": {
                "id": "prt_2",
                "type": "text",
                "text": text,
            },
        },
        {
            "type": "step_finish",
            "timestamp": 3,
            "sessionID": "ses_test",
            "part": {"id": "prt_3", "type": "step-finish", "reason": "stop"},
        },
    ]
    return "\n".join(json.dumps(event, ensure_ascii=False) for event in events)


def test_parser_opencode_part_text_markdown_fence_candidatas() -> None:
    payload = {
        "candidatas": [
            {
                "pergunta": "Quando o review virou hierarquia?",
                "direcao": "memoria",
                "por_que_agora": "abre o tema sem pressupor culpa",
            }
        ]
    }
    stdout = _opencode_ndjson_with_fenced_payload(payload)
    parsed = extract_json_object_from_llm_output(
        stdout,
        prefer_evaluation_shape=False,
        prefer_keys=("candidatas", "candidates", "perguntas"),
    )

    assert parsed.ok is True
    assert parsed.data is not None
    assert "candidatas" in parsed.data
    assert parsed.data["candidatas"][0]["pergunta"].startswith("Quando o review")


def test_parser_codex_legacy_item_text_still_works() -> None:
    payload = {"candidatas": [{"pergunta": "Pergunta legacy?", "direcao": "opiniao"}]}
    stdout = json.dumps(
        {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": json.dumps(payload)},
        }
    )
    parsed = extract_json_object_from_llm_output(
        stdout,
        prefer_evaluation_shape=False,
        prefer_keys=("candidatas", "candidates", "perguntas"),
    )

    assert parsed.ok is True
    assert parsed.data == payload


def test_parser_opencode_prefers_payload_over_envelope() -> None:
    payload = {"accepted": True, "issues": [], "relation_score": 0.8}
    stdout = _opencode_ndjson_with_fenced_payload(payload)
    parsed = extract_json_object_from_llm_output(
        stdout,
        prefer_evaluation_shape=False,
        prefer_keys=("accepted", "issues", "risk_scores", "relation_score"),
    )

    assert parsed.ok is True
    assert parsed.data == payload


def test_parser_real_session_opencode_stdout_excerpt() -> None:
    """Regressao: envelope OpenCode nao deve mascarar candidatas."""
    candidatas = {
        "candidatas": [
            {
                "pergunta": "Voce ja recusou aprovar um PR por preferencia?",
                "direcao": "erro",
                "por_que_agora": "evita tom de acusacao",
            }
        ]
    }
    stdout = (
        json.dumps(
            {
                "type": "text",
                "timestamp": 1,
                "sessionID": "ses_x",
                "part": {
                    "id": "prt_x",
                    "type": "text",
                    "text": "```json\n" + json.dumps(candidatas) + "\n```",
                },
            }
        )
        + "\n"
        + json.dumps(
            {
                "type": "step_start",
                "timestamp": 0,
                "sessionID": "ses_x",
                "part": {"id": "prt_0", "type": "step-start"},
            }
        )
    )
    parsed = extract_json_object_from_llm_output(
        stdout,
        prefer_evaluation_shape=False,
        prefer_keys=("candidatas", "candidates", "perguntas"),
    )
    assert parsed.ok is True
    assert parsed.data is not None
    assert len(parsed.data["candidatas"]) == 1
