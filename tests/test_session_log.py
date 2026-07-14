from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from content_engine.agent_wrapper import AgentWrapper
from content_engine.codex_llm_client import CodexLlmClient
from content_engine.persistence import carregar_sessao, salvar_sessao
from content_engine.schemas import AgentResult, TuiSessionState
from content_engine.session_log import SessionLogger, ensure_session_logger
from content_engine.session_controller import PostEngineApp
from tests.llm_fakes import fake_v4_llm_run


def _records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _ok(stdout: str = "ok", stderr: str = "", returncode: int = 0) -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class V4Agent:
    def run(self, tool: str, prompt: str, **kwargs: object) -> AgentResult:
        return fake_v4_llm_run(tool, prompt, **kwargs)


def test_session_logger_cria_arquivo_jsonl_e_persiste_id(tmp_path: Path) -> None:
    state = TuiSessionState()
    logger = ensure_session_logger(state, tmp_path / "session.json")
    logger.write("screen_operation", "teste", {"valor": "ação"})

    assert state.session_id
    assert state.session_log_path.endswith(f"{state.session_id}.jsonl")
    registros = _records(Path(state.session_log_path))
    assert registros[0]["session_id"] == state.session_id
    assert registros[0]["payload"] == {"valor": "ação"}

    session_path = tmp_path / "session.json"
    salvar_sessao(state, session_path)
    loaded = carregar_sessao(session_path)
    assert loaded.session_id == state.session_id
    assert loaded.session_log_path == state.session_log_path


def test_agent_wrapper_loga_prompt_e_resposta_llm(tmp_path: Path) -> None:
    logger = SessionLogger("sess-agent", tmp_path / "agent.jsonl")
    wrapper = AgentWrapper(workspace=tmp_path, session_logger=logger)

    result = wrapper.run_codex(
        "prompt do usuario",
        json_output=False,
        runner=lambda *a, **k: _ok(stdout="resposta llm"),
    )

    assert result.ok is True
    registros = _records(logger.path)
    assert registros[0]["event_type"] == "llm_request"
    assert registros[0]["payload"]["prompt"] == "prompt do usuario"
    assert registros[1]["event_type"] == "llm_response"
    assert registros[1]["payload"]["stdout"] == "resposta llm"


def test_codex_llm_client_loga_stdin_e_resposta(tmp_path: Path) -> None:
    logger = SessionLogger("sess-codex", tmp_path / "codex.jsonl")
    client = CodexLlmClient(
        workspace=tmp_path,
        runner=lambda *a, **k: _ok(stdout='{"ok": true}'),
        session_logger=logger,
    )

    result = client.run("codex", "prompt perguntas", model="gpt-x")

    assert result.ok is True
    registros = _records(logger.path)
    assert registros[0]["event_type"] == "llm_request"
    assert registros[0]["payload"]["prompt"] == "prompt perguntas"
    assert registros[1]["event_type"] == "llm_response"
    assert registros[1]["payload"]["stdout"] == '{"ok": true}'


def test_session_app_logs_v4_interview_start(tmp_path: Path) -> None:
    session_path = tmp_path / "session.json"
    app = PostEngineApp(
        agent_factory=lambda: V4Agent(),
        question_agent_factory=lambda: V4Agent(),
        session_path=session_path,
        run_sync_inline=True,
    )
    app.state.tema = "Tema"
    app.state.plataforma = "linkedin"
    app.state.objetivo_do_post = "Gerar autoridade"
    app.state.tipo_de_post = "post"
    app.action_start_interview_v4()

    records = _records(Path(app.state.session_log_path))
    operations = [record["operation"] for record in records]
    assert "app_initialized" in operations
    assert "interview.start" in operations
    assert json.loads(session_path.read_text(encoding="utf-8"))["session_id"]
