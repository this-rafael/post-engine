# Tasks: SPEC-061 — Post Engine V4 (Entrevista)

**Input**: [spec_061.md](spec_061.md), [plan.md](plan.md), [research.md](research.md)

**Prerequisites**: `plan.md` (required), `spec_061.md` (required), `research.md` (Fase 0 parcialmente completa)

**Breaking change policy**: **sem suporte a V2/V3**. Remover código legado; rejeitar sessões com `schema_version < 4.0`. Não há migrador nem modo legado.

**Tests**: Stubs P1 conforme `plan.md`. FR-019/FR-020 usam corpus histórico (métricas), não runtime V3.

**Organization**: Fases alinhadas aos Épicos 0–10. Tarefas `[P]` paralelizáveis na fase.

## Project Mode

`Brownfield` — substituição total do subsistema de entrevista, não coexistência.

## Epic / Capability Map

- **Épico 0** → Pesquisa e corpus
- **Épico 1** → Domínio e persistência (schema 4.0)
- **Épico 2** → Exploração
- **Épico 3** → Extração
- **Épico 4** → Heurística
- **Épico 5** → Avaliação LLM
- **Épico 6** → Gateway híbrido
- **Épico 7** → Lacunas e aprofundamento
- **Épico 8** → GUI
- **Épico 9** → Métricas de qualidade (corpus)
- **Épico 10** → **Remoção de código legado**

## Brownfield Notes

- **Substituir**: `session_app.py` (branches entrevista), `schemas.py` (campos legados), `persistence.py`
- **Deletar**: `adaptive_interview.py`, `memory_pack.py`, `interview.py`, `scoring.py`, `evaluator_client.py`, prompts `initial-*`/`recursive-*`/`questions-*`
- **Portar antes de deletar**: casos úteis de `tests/test_adaptive_quality.py` → `tests/test_interview_*.py`

---

## Phase 1: Épico 0 — Pesquisa

- [x] T001 {TR-001} Diagrama de sequência V4 em `specs/spec-061/research.md` [VERIFY: grep "sequenceDiagram" specs/spec-061/research.md]
- [x] T002 {TR-002} Máquina de estados V4 documentada em `research.md`
- [x] T003 {TR-003} [P] Corpus em `tests/fixtures/interview_corpus/` (8+ categorias)
- [x] T004 {TR-004} [P] Relatório histórico V2↔V3 em `research.md` (referência, não runtime)
- [x] T005 {TR-005} Plano de métricas §3.6 em `research.md`
- [x] T006 {TR-006} [P] Entrada SPEC-061 em `specs/checklist.md`

---

## Phase 2: Épico 1 — Domínio (Fundacional)

- [x] T007 {FR-005} Stub `tests/test_interview_extraction.py::test_FR_005_original_answer_immutable`
- [x] T008 {FR-006} Stub `tests/test_interview_extraction.py::test_FR_006_every_signal_has_evidence`
- [x] T009 [P] Criar `src/content_engine/interview/` com `SESSION_SCHEMA_VERSION = "4.0"`
- [x] T010 [P] Dataclasses em `interview/schemas.py` → exports: UserAnswer, Evidence, AuthorialSignal, InterviewState
- [x] T011 {FR-005, FR-006} **Reescrever** `TuiSessionState` em `schemas.py` — remover `interview_mode`, `memory_pack`, `interview_plan`, `scores`, `estado_entrevista`, `batch_interview_state`, `interview_pack` legado; adicionar campos V4
- [x] T012 {FR-005} `criar_estado_inicial()` em `interview/schemas.py` [VERIFY: pytest tests/test_interview_extraction.py::test_FR_005_original_answer_immutable -x]
- [x] T013 {TR-007} `persistence.py`: rejeitar `schema_version < 4.0` com `ValueError`; sem migração
- [x] T014 [P] Atualizar `__init__.py` exports

---

## Phase 3: Épico 3 — Extração

- [x] T015 {FR-005} `append_answer()` em `interview/extraction.py`
- [x] T016 {FR-006} `extract_signals()` — todo sinal com `evidence_ids` [VERIFY: pytest tests/test_interview_extraction.py -x]
- [x] T017 [P] Portar lógica útil de inferência local (sem `InterviewNeed`)
- [x] T018 {FR-006} Integrar em `interview/controller.py::process_answer()`

---

## Phase 4: Épico 4 — Heurística

- [x] T019 {FR-007} Stub `tests/test_interview_heuristic.py::test_FR_007_deterministic_score_is_explainable`
- [x] T020 {FR-012} Stub `tests/test_interview_gateway.py::test_FR_012_absolute_vetoes_block_approval`
- [x] T021 [P] `DIMENSION_CATALOG`, `GATEWAY_PROFILES` em `interview/heuristic.py`
- [x] T022 {FR-007} `assess_dimensions()` com `rules_triggered` [VERIFY: pytest tests/test_interview_heuristic.py::test_FR_007 -x]
- [x] T023 {FR-012} `detect_absolute_vetos()`
- [x] T024 Integrar heurística no controller

---

## Phase 5: Épico 5 — Avaliação LLM

- [x] T025 {FR-008} Prompt `prompts/interview/evaluate-authorship.md`
- [x] T026 {FR-008} `evaluate_authorship_llm()` em `interview/llm_evaluation.py`
- [x] T027 Registrar `interview_evaluate` em `llm_config.py`
- [x] T028 Fake LLM em `tests/llm_fakes.py`
- [x] T029 Integrar no controller

---

## Phase 6: Épico 6 — Gateway híbrido

- [x] T030 Stubs FR-008–FR-013 em `tests/test_interview_gateway.py`
- [x] T031 {FR-008, FR-009} `evaluate_gateway()` — LLM + heurística, nenhum sozinho [VERIFY: pytest tests/test_interview_gateway.py::test_FR_008 tests/test_interview_gateway.py::test_FR_009 -x]
- [x] T032 {FR-010} `_balanced_gateway()`
- [x] T033 {FR-011, FR-013} `_strong_imbalanced_gateway()`
- [x] T034 {FR-012} Vetos absolutos no gateway [VERIFY: pytest tests/test_interview_gateway.py -x]

---

## Phase 7: Épico 2 — Exploração

- [x] T035 Stubs FR-001–FR-004 em `tests/test_interview_exploration.py`
- [x] T036 {FR-001} Prompt `prompts/interview/explore.md` (sem estrutura editorial)
- [x] T037 {FR-002, FR-003} `interview/validation.py` — portar validadores; sem `adaptive_llm_forced`
- [x] T038 {FR-001, FR-002} `generate_candidates()` em `interview/exploration.py`
- [x] T039 {FR-004} `select_question()` — fail-closed [VERIFY: pytest tests/test_interview_exploration.py::test_FR_004 -x]
- [x] T040 Registrar `interview_questions` em `llm_config.py` + fake
- [x] T041 Wire `generate_next_question()` no controller

---

## Phase 8: Épico 7 — Lacunas

- [x] T042–T043 Stubs FR-014, FR-015
- [x] T044 `identify_gaps()` em `interview/gaps.py`
- [x] T045 `decide_deepening()`
- [x] T046 `explain_decision()`
- [x] T047 Prompt `prompts/interview/deepen.md`
- [x] T048 Integrar no controller [VERIFY: pytest tests/test_interview_gaps.py tests/test_interview_session.py -x]

---

## Phase 9: Integração session_app

- [x] T049 `interview/controller.py::run_round()` — loop completo
- [x] T050 **Substituir** handlers de entrevista em `session_app.py` — remover `_gerar_pergunta_adaptativa`, batch, legacy
- [x] T051 `interview/briefing.py::build_briefing()` — só ledger V4
- [x] T052 Conectar encerramento → estágio `briefing` → `prompt_builder.py`
- [x] T053 Testes integração `tests/test_interview_session.py`

---

## Phase 10: Épico 8 — GUI

- [x] T054 Stubs FR-016–FR-018
- [x] T055 Tipos V4 em `pe-types.ts`
- [x] T056 **Reescrever** `mapInterview()` em `interview.ts` (sem paths legados)
- [x] T057 `AuthorialMap.tsx` — dimensões only no radar
- [x] T058 `AxisDetailPanel.tsx` — sinais, evidências, regras
- [x] T059 Contador unificado em `InterviewStage.tsx`
- [x] T060 Justificativas na UI
- [x] T061 `derived.interview` no snapshot `server.py`

---

## Phase 11: Épico 9 — Métricas de qualidade

- [x] T062 Stubs FR-019/FR-020 (skip até corpus) em `tests/test_interview_quality.py`
- [x] T063 `measure_induced_answer_rate()` no corpus
- [x] T064 `measure_original_language_preservation()`
- [x] T065 Script `scripts/run_interview_quality_eval.py`
- [x] T066 Remover `skip` quando corpus pronto

---

## Phase 12: Épico 10 — Remoção de legado (breaking)

- [x] T067 **Deletar** `src/content_engine/adaptive_interview.py`
- [x] T068 **Deletar** `src/content_engine/memory_pack.py`, `interview.py`, `scoring.py`, `evaluator_client.py`
- [x] T069 **Deletar** prompts legados: `prompts/interview/initial-*`, `recursive-*`, `questions-*`, `evaluate-answer.md`, `update-memory-pack.md`
- [x] T070 **Deletar** `tests/test_adaptive_quality.py`, `tests/test_adaptive_controller.py` após portar casos
- [x] T071 Remover `gateway.avaliar_gateway` (5 aspectos) e `avaliar_gateway_interview_pack` (cobertura pura)
- [x] T072 [P] Grep zero: `interview_mode`, `memory_pack`, `InterviewPlan`, `required_axes`, `adaptive_llm_forced` [VERIFY: rg "interview_mode|memory_pack|InterviewPlan|required_axes|adaptive_llm_forced" src/ tests/ --glob '!*.md']
- [x] T073 Atualizar `briefing.py`, `prompt_builder.py`, `generator.py` para contrato único V4
- [x] T074 Revisar/remover specs 001–060 e testes mortos de contratos legados de entrevista (documentação histórica preservada; contratos de teste removidos)

---

## Phase 13: Polish

- [x] T075 Atualizar `specs/checklist.md`
- [x] T076 Resolver `tests/test_spec_061.py` (spec antiga de parser) — renomear ou integrar
- [x] T077 [COMPLETES SPEC-061] Suite final [VERIFY: uv run pytest -q]

---

## Dependencies

```text
Phase 1 ──► Phase 2 (Domínio + schema 4.0) ──► Phases 3–8 (motor)
                                                    │
                                                    ▼
                                              Phase 9 (session_app)
                                                    │
                                                    ▼
                                              Phase 10 (GUI)
                                                    │
                    Phase 1 corpus ──────────────────┼──► Phase 11 (métricas)
                                                    │
                                                    ▼
                                              Phase 12 (remoção legado) ──► Phase 13
```

**Ordem crítica**: Phase 12 só após Phase 9 (session_app já usa pipeline novo). T013 (reject schema) pode ir cedo.

---

## Definition of Done

- [x] FR-001–FR-020 GREEN (FR-019/020 após corpus)
- [x] Um único pipeline de entrevista — sem `interview_mode`
- [x] `schema_version == "4.0"` obrigatório
- [x] Zero referências a código legado de entrevista (T072)
- [x] GUI: contador = lista = gráfico (mesma coleção de dimensões)
- [x] Sessões V3 **não** abrem — breaking change documentado
