# Plano de Depreciação e Remoção Completa da TUI

A partir desta data, a interface TUI (Textual) é considerada **deprecated**.
O suporte oficial será mantido exclusivamente via GUI (React + HTTP server).
Este documento cobre desde a depreciação até a **remoção completa** de todo código, dependências, entry points e referências à TUI.

---

## 1. Motivação

- A GUI oferece experiência mais rica, acessível e alinhada com a evolução V3.
- Manter duas interfaces ativas duplica esforço de manutenção, testes e documentação.
- O `V3_EVO.md` já define que a TUI não é frente de produto e recebe apenas ajustes mínimos de compatibilidade.
- A dependência `textual>=0.50` e todo o módulo `src/tui/` representam superfície técnica que não será mais sustentada.

## 2. Inventário de Acoplamentos

### 2.1 Código-fonte TUI

| Arquivo | Descrição |
|---------|-----------|
| `src/tui/__init__.py` | Re-exporta `PostEngineApp` |
| `src/tui/__main__.py` | Entry point CLI (`python -m tui`); também serve `--gui` |
| `src/tui/app.py` | App Textual completo (~2300 linhas), constantes `PHASE_*`, `SCORE_AVALIACAO_ASPECTOS`, `_pergunta_fallback_experiencia` |

### 2.2 Módulos auxiliares acoplados

| Arquivo | Acoplamento |
|---------|-------------|
| `src/content_engine/tui_validation.py` | Lógica de validação nomeada para TUI |

### 2.3 GUI — imports de `tui.app`

`src/gui/server.py` importa 10 símbolos de `tui.app`:

- `PHASE_ENTRADA`, `PHASE_ENTREVISTA`, `PHASE_BRIEFING`, `PHASE_PROMPT`
- `PHASE_EXECUCAO`, `PHASE_SEGMENTACAO`, `PHASE_AVALIACAO`, `PHASE_EXPORTACAO`
- `PostEngineApp` (usada como orquestrador de sessão)
- `SCORE_AVALIACAO_ASPECTOS`

### 2.4 Testes com imports de `tui`

| Teste | Import |
|-------|--------|
| `tests/test_spec_041_048.py` | `from tui import PostEngineApp` + `textual.widgets` |
| `tests/test_spec_058.py` | `from tui import PostEngineApp` + `textual.widgets` |
| `tests/test_spec_061.py` | `from tui import PostEngineApp` |
| `tests/test_spec_062.py` | `from tui import PostEngineApp` + `textual.widgets` |
| `tests/test_session_log.py` | `from tui import PostEngineApp` |
| `tests/test_objetivo_nao_contexto_pergunta.py` | `from tui.app import _pergunta_fallback_experiencia`, `from tui import app as app_mod` |
| `tests/test_gui_avaliacao.py` | `from tui.app import SCORE_AVALIACAO_ASPECTOS` |
| `tests/test_tui_cli.py` | `from tui import __main__ as tui_main` |
| `tests/test_tui_phase8_layout.py` | `from tui import PostEngineApp` + `textual.widgets` |

### 2.5 Scripts e configuração

| Arquivo | Referência |
|---------|------------|
| `scripts/run.fish` | `python -m src.tui` (entry point TUI) |
| `scripts/gui.fish` | `python -m src.tui --gui` (entry point GUI via TUI) |
| `scripts/validate_phase2_tui.py` | Script de validação TUI via pexpect |
| `pyproject.toml` | Dependência `textual>=0.50` |
| `uv.lock` | Lock de `textual` e sub-dependências |

### 2.6 Documentação com referências TUI

| Arquivo | Natureza |
|---------|----------|
| `PRD.md` | TUI como interface operacional (seções 39, 46, 47, 50) |
| `V3_EVO.md` | Diretrizes de compatibilidade mínima TUI |
| `PLAN_UPDATE_POST_ENGINE_OUTPUT.MD` | Referências a propagação TUI |
| `new_screens.md` | Plano de telas TUI |
| `QUESTIONARIO.md` | Contexto histórico de falhas TUI |
| `RESUMO_IMPLEMENTACAO_PERGUNTAS_LLM.md` | Menções a sanitize TUI |

## 3. Fases

### Fase 1 — Extração de Lógica Compartilhada

**Objetivo:** desacoplar `src/gui/server.py` de `src/tui/app.py`.

1. Criar `src/core/phases.py` com as constantes `PHASE_*`.
2. Criar `src/core/avaliacao.py` com `SCORE_AVALIACAO_ASPECTOS`.
3. Extrair `PostEngineApp` (lógica de orquestração de sessão, não widgets Textual) para `src/core/session.py` ou equivalente — renomear para `SessionOrchestrator` ou manter o nome se a classe já é agnóstica de UI.
4. Extrair `_pergunta_fallback_experiencia` para `src/content_engine/perguntas.py` (ou módulo existente de perguntas).
5. Atualizar imports em `src/gui/server.py` para apontar para os novos módulos.
6. Atualizar `src/content_engine/tui_validation.py` → renomear para `src/content_engine/validacao.py` (remover prefixo `tui_`).

### Fase 2 — Migração do Entry Point

**Objetivo:** criar entry point independente da TUI.

1. Criar `src/gui/__main__.py` com a lógica de argparse atualmente em `src/tui/__main__.py` (apenas os args `--gui`, `--gui-host`, `--gui-port`; remover `--restore-session` TUI).
2. Atualizar `scripts/gui.fish` para `uv run -- python -m src.gui $argv`.
3. Remover `scripts/run.fish` (entry point TUI puro).

### Fase 3 — Migração de Testes

**Objetivo:** eliminar todos os imports de `tui` nos testes.

1. Testes que instanciam `PostEngineApp` para testar lógica de sessão → migrar para importar de `src/core/session.py`.
2. Testes que usam `textual.widgets` (test_spec_041_048, test_spec_058, test_spec_062, test_tui_phase8_layout) → reescrever para testar via GUI HTTP ou remover se a lógica já estiver coberta por testes de `core`.
3. `test_gui_avaliacao.py` → importar `SCORE_AVALIACAO_ASPECTOS` de `src/core/avaliacao.py`.
4. `test_objetivo_nao_contexto_pergunta.py` → importar `_pergunta_fallback_experiencia` do novo módulo.
5. `test_tui_cli.py` → remover integralmente (testa CLI TUI).
6. `test_tui_phase8_layout.py` → remover integralmente (testa layout Textual).

### Fase 4 — Remoção do Código TUI

1. Remover diretório `src/tui/` integralmente (`__init__.py`, `__main__.py`, `app.py`, `__pycache__/`).
2. Remover `tests/test_tui_cli.py`.
3. Remover `tests/test_tui_phase8_layout.py`.
4. Remover `scripts/run.fish`.
5. Remover `scripts/validate_phase2_tui.py`.
6. Remover `new_screens.md`.

### Fase 5 — Remoção da Dependência `textual`

1. Remover `"textual>=0.50"` de `pyproject.toml` (`dependencies`).
2. Rodar `uv lock` para regenerar `uv.lock` sem `textual` e suas sub-dependências.
3. Verificar que nenhum outro módulo importa `textual` (grep por `from textual` / `import textual`).

### Fase 6 — Limpeza de Documentação

1. `PRD.md` — remover seções 39.1, 46, 47, 50 e todas as menções à TUI como interface operacional.
2. `V3_EVO.md` — remover menções de compatibilidade TUI (linhas 9, 19, 21, 27, 77, 149, 424, 451, 506, 546, 655, 672).
3. `PLAN_UPDATE_POST_ENGINE_OUTPUT.MD` — remover referências a propagação TUI.
4. `QUESTIONARIO.md` — remover menções a fluxo TUI.
5. `RESUMO_IMPLEMENTACAO_PERGUNTAS_LLM.md` — remover menções a sanitize TUI.

### Fase 7 — Validação Final

1. `grep -r "from tui" src/ tests/` → deve retornar vazio.
2. `grep -r "import textual" src/ tests/` → deve retornar vazio.
3. `grep -r "textual" pyproject.toml uv.lock` → deve retornar vazio.
4. Rodar suíte completa: `pytest`.
5. Rodar lint: `ruff check src/ tests/`.
6. Rodar typecheck (se configurado).
7. Validar que `python -m src.gui` inicia a GUI sem erros.

## 4. Cronograma Sugerido

| Fase | Estimativa |
|------|-----------|
| Fase 1 — Extração de lógica | 1-2 dias |
| Fase 2 — Migração do entry point | 0.5 dia |
| Fase 3 — Migração de testes | 1 dia |
| Fase 4 — Remoção do código TUI | 0.5 dia |
| Fase 5 — Remoção da dependência | 0.5 dia |
| Fase 6 — Limpeza de documentação | 0.5 dia |
| Fase 7 — Validação final | 0.5 dia |
| **Total** | **4-5 dias** |

## 5. Critérios de Conclusão

- [ ] Diretório `src/tui/` não existe.
- [ ] Nenhum `from tui` ou `import tui` em `src/` ou `tests/`.
- [ ] Dependência `textual` removida de `pyproject.toml` e `uv.lock`.
- [ ] Entry point GUI funcional via `python -m src.gui`.
- [ ] `scripts/gui.fish` atualizado e funcional.
- [ ] `scripts/run.fish` removido.
- [ ] Todos os testes passam sem módulos TUI.
- [ ] Lint e typecheck limpos.
- [ ] Documentação sem referências à TUI como interface suportada.
- [ ] `src/content_engine/tui_validation.py` renomeado para `validacao.py`.

## 6. Riscos e Mitigações

| Risco | Mitigação |
|-------|-----------|
| `PostEngineApp` contém lógica de sessão tightly coupled com widgets Textual | Analisar a classe na Fase 1; separar orquestração (state machine, persistência) de rendering Textual |
| Testes de spec (041-048, 058, 061, 062) validam comportamento via TUI | Reescrever como testes de integração via GUI HTTP ou testes unitários da lógica extraída |
| `scripts/gui.fish` é usado em dev workflow | Comunicar a mudança do entry point; atualizar script antes de remover o antigo |
| Remoção de `textual` pode quebrar imports indiretos | Grep exaustivo por `textual` antes e após remoção; CI deve validar |
