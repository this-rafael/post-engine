# Fase 2 Evo - Change Log

Resumo exato de todas as mudancas implementadas para transformar a fase 2
em motor de entrevista por lotes com contrato estruturado (`InterviewPack`).

---

## Arquivos novos

### `src/content_engine/taxonomy.py` (502 linhas)

Modulo central que define a fonte unica de verdade para todos os eixos.

**Simbolos criados:**
- `AxisDefinition` — dataclass frozen com: `id`, `label`, `kind`, `group`, `description`, `required_by_formats`, `weight_by_format`
- `ALL_AXIS_DEFINITIONS` — tuple com 27 `AxisDefinition` (17 humanos + 10 organizacionais)
- `AXIS_BY_ID` — dict[str, AxisDefinition] indexado por `id`
- `AXIS_IDS` — tuple de todos os IDs
- `BATCH_ORDER` — ordem oficial dos 7 lotes
- `AXES_PER_BATCH` — dict mapeando lote -> tuple de eixos
- `LEGACY_ASPECT_TO_NEW_AXIS` — mapeamento dos 5 aspectos antigos para novos eixos
- `FORMAT_REQUIRED_ORG_BATCHES` — lotes obrigatorios por formato
- `HUMAN_BATCHES_ALWAYS_REQUIRED` — lotes humanos sempre obrigatorios
- Funcoes: `required_batches_for_format()`, `axes_required_for_format()`, `axis_definitions_for_ids()`, `get_batch_kind()`, `get_group_from_batch()`, `next_batch()`, `batch_index()`

**Taxonomia implementada:**

Humanos:
- `interno`: sentimento, desejo, medo, vulnerabilidade, personalidade
- `cognitivo`: opiniao, crenças, aprendizado, valores
- `biografico`: experiencia, identidade, repertorio
- `relacional`: intencao, relacao_com_publico, conflito, transformacao, limite

Organizacionais:
- `argumento`: tese, contexto, evidencia, tensao
- `arquitetura`: estrutura, didatica, aplicabilidade
- `formato`: transicoes, escaneabilidade, chamada

---

### `src/content_engine/batch_validation.py` (236 linhas)

Validacao estrita de lotes gerados pela LLM. Sem fallback silencioso.

**Simbolos criados:**
- `BatchValidationError` — excecao com lista de erros e batch_id
- `validate_question_batch(batch, content_type)` — valida QuestionBatch com 10 regras
- `parse_and_validate_batch(raw_payload, batch_id, expected_axes, content_type)` — parse + validacao de payload bruto da LLM
- `compute_coverage(answers_by_axis, all_required_axes)` — calcula cobertura

**Regras de validacao implementadas:**
1. `kind` deve ser "humano" ou "organizacional"
2. `group` deve bater com `kind`
3. Todos os `expected_axes` devem existir na taxonomia
4. Todos os eixos retornados devem existir na taxonomia
5. Todos os `expected_axes` devem estar presentes (nenhum faltando)
6. Nenhum eixo extra pode existir
7. Cada eixo precisa de pelo menos uma pergunta valida
8. Nenhuma pergunta pode ser vazia
9. Nenhuma duplicidade por eixo
10. Eixos devem pertencer ao lote correto

---

### `tests/test_fase2evo.py` (640 linhas, 62 testes)

**Classes de teste:**
- `TestTaxonomy` — 16 testes (IDs unicos, campos obrigatorios, ordem, mapeamento legado, congelamento)
- `TestQuestionItem` — 3 testes (criacao, serializacao, frozen)
- `TestQuestionBatch` — 3 testes (criacao, roundtrip, status invalido)
- `TestInterviewAnswer` — 2 testes (criacao, frozen)
- `TestInterviewCoverage` — 3 testes (percent, zero total, roundtrip)
- `TestInterviewPack` — 4 testes (criacao, get_answer, all_answers, roundtrip)
- `TestQuestionGenerationError` — 2 testes (criacao, to_dict)
- `TestBatchValidation` — 12 testes (valido, eixo faltante, eixo extra, pergunta vazia, duplicidade, eixo errado, kind errado, parse valido, parse invalido, eixos faltantes, coverage)
- `TestBatchInterviewState` — 7 testes (criacao, avanço, ultimo lote, resposta, eixos, roundtrip, all_answers_for_pack)
- `TestCriarBatchState` — 3 testes (post reduzido, article completo, tema vazio)
- `TestBatchStateToPack` — 2 testes (estado vazio, estado com respostas)
- `TestPersistenceBatchState` — 5 testes (save/load batch state, pack, schema version, legacy defaults, invalid mode)
- `TestInterviewBatchMode` — 1 teste (BatchGenerationFailed)

---

## Arquivos modificados

### `src/content_engine/schemas.py`

**Adicoes:**
- `StatusBatch` — Literal["pendente", "valido", "invalido", "erro_llm"]
- `QuestionItem` — dataclass frozen: `axis`, `question`, `rationale` + `to_dict()`
- `QuestionBatch` — dataclass frozen: `kind`, `group`, `expected_axes`, `questions`, `status` + `to_dict()`, `from_dict()`
- `InterviewAnswer` — dataclass frozen: `batch_id`, `axis`, `question`, `answer` + `to_dict()`
- `InterviewCoverage` — dataclass frozen: `by_axis`, `by_group`, `total_axes`, `covered_axes` + propriedade `percent`, `to_dict()`, `from_dict()`
- `InterviewPack` — dataclass frozen: `theme`, `platform`, `objective`, `content_type`, `answers`, `coverage`, `personality`, `schema_version` + `to_dict()`, `from_dict()`, `get_answer()`, `answers_for_group()`, `all_answers()`
- `QuestionGenerationError` — dataclass frozen: `content_type`, `batch_id`, `expected_axes`, `received_axes`, `parse_error`, `validation_error`, `raw_payload` + `to_dict()`, `__str__()`
- `SESSION_SCHEMA_VERSION = "2.0"`

**Modificacoes em `TuiSessionState`:**
- Adicionado campo `interview_mode: str = "legacy"` — "legacy" | "batch"
- Adicionado campo `batch_interview_state: dict[str, Any] | None = None`
- Adicionado campo `interview_pack: dict[str, Any] | None = None`

---

### `src/content_engine/interview_state.py`

**Substituido por:** modulo completo com suporte a modo por lotes.

**Simbolos mantidos (compatibilidade):**
- `criar_estado_inicial()` — funcao original preservada

**Simbolos novos:**
- `BatchInterviewState` — dataclass com: `current_batch_id`, `completed_batches`, `pending_batches`, `batches_data`, `answers_by_axis`, `batch_errors`, `schema_version`
  - Metodos: `to_dict()`, `from_dict()`, `is_batch_completed()`, `current_axes()`, `advance_to_next_batch()`, `register_answer()`, `register_batch_error()`, `all_answers_for_pack()`
- `criar_batch_state(input_data)` — cria estado inicial para modo por lotes, derivando lotes obrigatorios do formato
- `batch_state_to_pack(batch_state, input_data)` — converte estado de lotes para InterviewPack com coverage calculado

---

### `src/content_engine/questions.py`

**Adicoes:**
- Import de `QuestionBatch`, `QuestionGenerationError`, `QuestionItem` dos schemas
- Import de `AXES_PER_BATCH`, `AXIS_BY_ID`, `get_batch_kind`, `get_group_from_batch` da taxonomia
- Metodo `QuestionGenerator.gerar_lote()` — gera perguntas para um lote especifico via LLM, com validacao estrita, sem fallback silencioso
- Funcao `_formato_requisitos(tipo_de_post)` — retorna requisitos do formato para o prompt
- Funcao `_build_batch_from_llm_response()` — constrói QuestionBatch a partir de resposta da LLM com validacao
- `_BATCH_PROMPT_TEMPLATE` — template de prompt inline para geracao de perguntas por lote

---

### `src/content_engine/interview.py`

**Adicoes:**
- Import de `BatchValidationError`, `validate_question_batch`, `BatchInterviewState`, `batch_state_to_pack`, `criar_batch_state`
- Import de `InterviewPack`, `QuestionBatch`, `QuestionGenerationError`
- Import de `AXES_PER_BATCH`, `BATCH_ORDER`, `required_batches_for_format` da taxonomia
- `BatchQuestionGenerator` — Protocolo para gerador de perguntas por lote
- `ColetorRespostasLote` — tipo Callable para coletar respostas de um lote
- `executar_entrevista_por_lotes()` — loop async que processa lotes sequencialmente, com retry e falha explicita
- `BatchGenerationFailed` — excecao para falha na geracao de perguntas
- Funcoes auxiliares: `_kind_key()`, `_group_key()`, `_find_axis_for_question()`

**Mantidos (compatibilidade):**
- `executar_entrevista()` — funcao original do modo legado preservada
- `EvaluationLike`, `QuestionLike`, `ColetorDeRespostas` — protocols originais preservados

---

### `src/content_engine/persistence.py`

**Modificacoes:**
- Import de `SESSION_SCHEMA_VERSION` dos schemas
- Docstring atualizada com mencao a versao de schema e modo por lotes
- `_state_to_dict()` — adicionados campos: `schema_version`, `interview_mode`, `batch_interview_state`, `interview_pack`
- `_dict_to_state()` — leitura dos novos campos com migracao:
  - `interview_mode` default "legacy" se ausente ou invalido
  - `batch_interview_state` e `interview_pack` deserialize de dict ou None

---

### `src/content_engine/__init__.py`

**Adicoes nas imports:**
- `batch_validation`: `BatchValidationError`, `compute_coverage`, `parse_and_validate_batch`, `validate_question_batch`
- `interview`: `BatchGenerationFailed`, `ColetorRespostasLote`
- `interview_state`: `BatchInterviewState`, `batch_state_to_pack`, `criar_batch_state`
- `schemas`: `InterviewAnswer`, `InterviewCoverage`, `InterviewPack`, `QuestionBatch`, `QuestionGenerationError`, `QuestionItem`, `SESSION_SCHEMA_VERSION`
- `taxonomy`: todos os simbolos publicos (`ALL_AXIS_DEFINITIONS`, `AXES_PER_BATCH`, `AXIS_BY_ID`, `AXIS_IDS`, `BATCH_ORDER`, `AxisDefinition`, `axes_required_for_format`, etc.)

**Atualizacao do `__all__`:** 86 simbolos exportados (antes ~70)

---

## Safeguards implementados

| Premissa | Implementacao |
|---|---|
| Nenhum passo segue com schema invalido | `validate_question_batch()` raises `BatchValidationError` |
| Nenhuma resposta da LLM e aceita sem validacao | 10 regras de validacao em `batch_validation.py` |
| Nenhum eixo fora da taxonomia entra | Checagem contra `AXIS_BY_ID` em todos os parsers |
| Nenhuma pergunta fica sem eixo | Regra "eixos sem pergunta valida" na validacao |
| Nenhum fallback local mascara falha | `QuestionGenerationError` explicito, nunca converte para fallback |
| Toda fase subsequente consome o mesmo contrato | `InterviewPack` definido como contrato central |
| Toda sessao persistida e versionada | `SESSION_SCHEMA_VERSION = "2.0"` em todo JSON |
| Migracao de sessoes antigas | Defaults para `interview_mode="legacy"` |

---

## Nao implementado (pendente)

- Integracao visual na TUI (progresso por lote, erros explicitos, cobertura)
- Atualizacao de `briefing.py` para consumir `InterviewPack`
- Atualizacao de `prompt_builder.py` para consumir `InterviewPack`
- Atualizacao de `gateway.py` e `scoring.py` para novos eixos
- Atualizacao de `adjust_segment.py` para operar por eixo
- Atualizacao de `segmentation.py` para usar eixos organizacionais
- Atualizacao de `post_evaluation.py` com pesos por formato
