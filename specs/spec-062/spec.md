# Spec — Persistência relacional SQLite do Post Engine

## 1. Propósito

Esta especificação define a substituição incremental da persistência de domínio
baseada em `.data/sessions/current-session.json` por um banco relacional
SQLite em `.data/post-engine.sqlite3`.

Ela deriva do estado documentado em `research.md`. O objetivo não é armazenar o
mesmo documento em outra mídia, e sim criar uma fonte de verdade relacional
para usuários, posts, sessões editoriais, versões de conteúdo e suas trilhas de
auditoria.

## 2. Escopo

### 2.1 Incluído

- banco SQLite de domínio;
- migrations versionadas;
- múltiplos usuários selecionáveis;
- múltiplos posts por usuário;
- múltiplas sessões editoriais por post;
- múltiplas versões imutáveis por post;
- entrevista e gateway autoral históricos;
- storyboard, abordagens, drafts e seleções históricos;
- composição, segmentação, ajustes e avaliações;
- catálogo de exports;
- rastreabilidade de execuções LLM;
- eventos de sessão;
- APIs orientadas por IDs;
- frontend com seleção explícita de usuário, post e sessão;
- optimistic locking;
- isolamento e concorrência entre sessões;
- importação do JSON e dos artefatos legados;
- transição `legacy → dual_write → sqlite_shadow_read → sqlite`;
- corte definitivo da escrita no JSON;
- testes, observabilidade, backup e rollback.

### 2.2 Excluído

- autenticação;
- autorização;
- senha;
- token;
- login;
- papéis e permissões;
- publicação automática em redes externas;
- sincronização em nuvem;
- arquitetura multi-tenant remota;
- isolamento de segurança entre clientes hostis;
- substituição do Prompt Registry;
- união obrigatória dos bancos de domínio e Prompt Registry;
- introdução obrigatória de framework web;
- migração para PostgreSQL, MySQL ou outro banco;
- edição colaborativa em tempo real do mesmo conteúdo;
- sincronização distribuída entre máquinas.

O `User` desta especificação é uma entidade editorial selecionável, não uma
identidade autenticada.

## 3. Princípios obrigatórios

1. SQLite é a fonte de verdade final do domínio.
2. Nenhuma tabela principal de sessão pode ser equivalente a
   `id + payload_json`.
3. Campos usados em relação, ordenação, filtro, status, decisão, concorrência,
   versão ou auditoria são explícitos.
4. JSON é permitido somente para bruto externo, documento realmente flexível,
   metadata sem regra de negócio, compatibilidade temporária e diagnóstico.
5. IDs novos são UUIDs textuais canônicos.
6. Timestamps são UTC em formato RFC 3339 com sufixo `Z`.
7. Histórico não é sobrescrito.
8. Versões de conteúdo são imutáveis.
9. Arquivamento substitui exclusão destrutiva nas APIs.
10. Toda ação editorial identifica a sessão.
11. O frontend nunca é a fonte de verdade do estado de domínio.
12. Uma transação SQLite nunca permanece aberta durante chamada externa de LLM.
13. O Prompt Registry continua separado e não recebe migrations do domínio.

## 4. Convenções do schema

### 4.1 Tipos

| Conceito | Tipo SQLite | Regra |
| --- | --- | --- |
| UUID | `TEXT` | lowercase, formato UUID canônico, validado na aplicação |
| Timestamp | `TEXT` | UTC RFC 3339, por exemplo `2026-07-16T12:00:00Z` |
| Booleano | `INTEGER` | `0` ou `1`, com `CHECK` |
| Enum | `TEXT` | `CHECK` com valores definidos nesta spec |
| Inteiro | `INTEGER` | `CHECK` para limites quando aplicável |
| Decimal | `REAL` | limites por `CHECK` quando aplicável |
| Texto longo | `TEXT` | sem truncamento silencioso |
| JSON permitido | `TEXT` | JSON canônico validado na aplicação; `json_valid` se disponível |
| Hash | `TEXT` | SHA-256 lowercase quando não indicado o contrário |

### 4.2 Auditoria

Toda entidade possui `created_at`. Entidades cujo status ou metadados podem
mudar possuem `updated_at`. Entidades arquiváveis possuem `archived_at`.

Não será criado `created_by` autenticado. Eventos podem registrar
`actor_kind = ui | system | import | migration` e um `actor_ref` textual
opcional.

### 4.3 Exclusão

- APIs não expõem hard delete.
- `users`, `posts`, `sessions`, `post_versions` e históricos são arquivados.
- FKs de raízes usam `ON DELETE RESTRICT`.
- Tabelas de itens podem usar `ON DELETE CASCADE` apenas para limpeza de testes,
  rollback de importação ainda não publicada ou falha de criação dentro da
  mesma unidade transacional.
- Dados consolidados, publicados ou importados com sucesso não são apagados por
  cascata em operação normal.

### 4.4 IDs legados

Quando útil, a entidade pode conter `legacy_id TEXT NULL`. Esse campo:

- não substitui o UUID;
- é único apenas dentro de uma importação ou pai quando especificado;
- não participa de novas relações;
- serve para relatório, deduplicação e rastreabilidade.

### 4.5 Índices

Toda foreign key usada em navegação deve possuir índice. Índices compostos
devem refletir os catálogos e ordenações descritos nesta especificação.

## 5. Modelo relacional

### 5.1 `schema_migrations`

**Responsabilidade:** registrar migrations do banco de domínio.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `version` | INTEGER | PK, maior que zero |
| `name` | TEXT | obrigatório, único |
| `checksum` | TEXT | obrigatório, SHA-256 do arquivo |
| `applied_at` | TEXT | obrigatório |
| `duration_ms` | INTEGER | obrigatório, maior ou igual a zero |

Unicidade: `version`, `name`.

Exclusão/arquivamento: nunca excluir por fluxo normal.

Auditoria: `applied_at`.

### 5.2 `users`

**Responsabilidade:** pessoa editorial selecionável na interface.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `display_name` | TEXT | obrigatório, não vazio |
| `slug` | TEXT | obrigatório |
| `status` | TEXT | `active | archived` |
| `created_at` | TEXT | obrigatório |
| `updated_at` | TEXT | obrigatório |
| `archived_at` | TEXT | nulo salvo status `archived` |

Unicidade: `slug` case-insensitive entre registros não arquivados.

Índices:

- `(status, display_name)`;
- índice único parcial de `slug` onde `status = active`.

Exclusão: `RESTRICT` se houver posts.

Arquivamento: mantém posts e histórico; bloqueia criação de novo post.

### 5.3 `posts`

**Responsabilidade:** raiz editorial de um conteúdo pertencente a um usuário.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `user_id` | TEXT | FK obrigatória para `users.id` |
| `title` | TEXT | obrigatório, nome de catálogo |
| `theme` | TEXT | obrigatório |
| `platform` | TEXT | obrigatório |
| `objective` | TEXT | obrigatório |
| `content_type` | TEXT | `post | article | short_carousel | long_slide` |
| `default_personality` | TEXT | obrigatório, pode ser vazio |
| `status` | TEXT | `draft | active | completed | archived` |
| `created_at` | TEXT | obrigatório |
| `updated_at` | TEXT | obrigatório |
| `completed_at` | TEXT | nulo salvo conclusão |
| `archived_at` | TEXT | nulo salvo arquivamento |

PK: `id`.

FK: `user_id ON DELETE RESTRICT`.

Unicidade: não é necessário título único; dois posts podem tratar o mesmo tema.

Índices:

- `(user_id, status, updated_at DESC)`;
- `(user_id, created_at DESC)`;
- `(status, updated_at DESC)`.

Exclusão: `RESTRICT` se houver sessões ou versões.

Arquivamento: bloqueia nova sessão e nova versão, preservando tudo.

### 5.4 `sessions`

**Responsabilidade:** uma execução/tentativa do workflow de um post.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `post_id` | TEXT | FK obrigatória para `posts.id` |
| `attempt_number` | INTEGER | obrigatório, maior que zero |
| `status` | TEXT | `active | completed | failed | cancelled | archived` |
| `workflow_phase` | TEXT | fase válida definida em 8.2 |
| `authorial_progress_state` | TEXT | estado válido definido em 8.3 |
| `max_questions` | INTEGER | obrigatório, maior que zero |
| `closure_reason` | TEXT | nulo |
| `personality_snapshot` | TEXT | obrigatório, pode ser vazio |
| `lock_version` | INTEGER | obrigatório, começa em zero |
| `legacy_session_id` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |
| `started_at` | TEXT | obrigatório |
| `updated_at` | TEXT | obrigatório |
| `completed_at` | TEXT | nulo |
| `failed_at` | TEXT | nulo |
| `cancelled_at` | TEXT | nulo |
| `archived_at` | TEXT | nulo |

PK: `id`.

FK: `post_id ON DELETE RESTRICT`.

Unicidade:

- `(post_id, attempt_number)`;
- `(post_id, legacy_session_id)` quando `legacy_session_id` não for nulo.

Índices:

- `(post_id, status, updated_at DESC)`;
- `(post_id, attempt_number DESC)`;
- `(status, updated_at DESC)`.

Exclusão: `RESTRICT` quando houver histórico.

Arquivamento: não elimina dados; sessão arquivada é somente leitura.

Concorrência: `lock_version` é atualizado por compare-and-swap.

### 5.5 `session_constraints`

**Responsabilidade:** restrições ordenadas usadas em uma tentativa.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `position` | INTEGER | obrigatório, maior que zero |
| `text` | TEXT | obrigatório, não vazio |
| `created_at` | TEXT | obrigatório |

Unicidade: `(session_id, position)`.

Índice: `(session_id, position)`.

Exclusão: `CASCADE` somente com remoção transacional de sessão não publicada.

Arquivamento: herdado da sessão.

### 5.6 `session_events`

**Responsabilidade:** trilha append-only de eventos de domínio e operação.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `sequence_number` | INTEGER | obrigatório, maior que zero |
| `event_type` | TEXT | obrigatório |
| `operation` | TEXT | nulo |
| `actor_kind` | TEXT | `ui | system | import | migration` |
| `actor_ref` | TEXT | nulo |
| `entity_type` | TEXT | nulo |
| `entity_id` | TEXT | nulo |
| `message` | TEXT | nulo |
| `payload_json` | TEXT | nulo, apenas diagnóstico flexível |
| `occurred_at` | TEXT | obrigatório |
| `created_at` | TEXT | obrigatório |

Unicidade: `(session_id, sequence_number)`.

Índices:

- `(session_id, sequence_number)`;
- `(session_id, event_type, occurred_at)`;
- `(entity_type, entity_id)` quando preenchidos.

Exclusão/arquivamento: append-only; acompanha retenção da sessão.

### 5.7 `interview_rounds`

**Responsabilidade:** agrupar uma rodada padrão ou lote de extensão.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `sequence_number` | INTEGER | obrigatório, maior que zero |
| `kind` | TEXT | `standard | extension` |
| `status` | TEXT | `pending | active | completed | cancelled | failed` |
| `title` | TEXT | nulo |
| `gap_diagnosis` | TEXT | nulo |
| `started_at` | TEXT | nulo |
| `completed_at` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |
| `updated_at` | TEXT | obrigatório |

Unicidade: `(session_id, sequence_number)`.

Índice: `(session_id, sequence_number)`.

Exclusão: `RESTRICT` quando houver perguntas.

Arquivamento: herdado da sessão.

### 5.8 `interview_questions`

**Responsabilidade:** preservar todas as candidatas e perguntas selecionadas.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `round_id` | TEXT | FK obrigatória |
| `legacy_id` | TEXT | nulo |
| `sequence_number` | INTEGER | obrigatório dentro da rodada |
| `candidate_key` | TEXT | nulo, ID legado da candidata |
| `text` | TEXT | obrigatório |
| `direction` | TEXT | nulo |
| `why_now` | TEXT | nulo |
| `source` | TEXT | obrigatório |
| `status` | TEXT | `candidate | rejected | selected | pending_answer | answered | cancelled` |
| `accepted` | INTEGER | booleano |
| `relation_score` | REAL | 0 a 1 ou escala documentada pelo serviço |
| `discovery_score` | REAL | idem |
| `answerability_score` | REAL | idem |
| `risk_induction` | REAL | nulo |
| `risk_repetition` | REAL | nulo |
| `risk_compound` | REAL | nulo |
| `llm_execution_id` | TEXT | FK nula para execução que gerou |
| `selected_at` | TEXT | nulo |
| `answered_at` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |
| `updated_at` | TEXT | obrigatório |

PK: `id`.

FKs:

- `round_id ON DELETE RESTRICT`;
- `llm_execution_id ON DELETE SET NULL`.

Unicidade:

- `(round_id, sequence_number, id)`;
- `legacy_id` somente no escopo da importação, não global.

Índices:

- `(round_id, sequence_number)`;
- `(round_id, status)`;
- `(llm_execution_id)`.

Exclusão: histórico não é apagado.

Arquivamento: herdado da sessão.

### 5.9 `interview_question_issues`

**Responsabilidade:** normalizar problemas de validação das candidatas.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `question_id` | TEXT | FK obrigatória |
| `position` | INTEGER | obrigatório |
| `code` | TEXT | nulo |
| `description` | TEXT | obrigatório |
| `created_at` | TEXT | obrigatório |

Unicidade: `(question_id, position)`.

Índice: `(question_id, position)`.

Exclusão: item acompanha pergunta apenas em rollback transacional.

### 5.10 `interview_answers`

**Responsabilidade:** resposta original imutável e normalização separada.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `question_id` | TEXT | FK obrigatória |
| `legacy_id` | TEXT | nulo |
| `sequence_number` | INTEGER | obrigatório |
| `original_text` | TEXT | obrigatório |
| `normalized_text` | TEXT | obrigatório |
| `submitted_at` | TEXT | obrigatório |
| `created_at` | TEXT | obrigatório |

Unicidade:

- uma resposta por pergunta: `question_id`;
- sequência única por sessão, reforçada por validação e consulta ao round.

Índices:

- `(question_id)`;
- `(sequence_number)`.

Exclusão: `RESTRICT`; resposta aceita não é editada. Correção cria nova rodada
ou mecanismo futuro explícito, não `UPDATE` de texto.

### 5.11 `interview_answer_assessments`

**Responsabilidade:** preservar cada avaliação cumulativa após uma resposta ou
marco da entrevista.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `answer_id` | TEXT | FK nula para avaliação sem resposta específica |
| `revision_number` | INTEGER | obrigatório |
| `status` | TEXT | `pending | completed | failed` |
| `deterministic_global_score` | INTEGER | 0 a 100, nulo |
| `deterministic_approved` | INTEGER | booleano nulo |
| `evidence_count` | INTEGER | maior ou igual a zero |
| `answer_count` | INTEGER | maior ou igual a zero |
| `llm_approved` | INTEGER | booleano nulo |
| `llm_confidence` | REAL | 0 a 1, nulo |
| `epistemic_integrity` | TEXT | nulo |
| `justification` | TEXT | nulo |
| `parse_error` | TEXT | nulo |
| `source` | TEXT | `deterministic | llm | combined | import` |
| `llm_execution_id` | TEXT | FK nula |
| `created_at` | TEXT | obrigatório |
| `completed_at` | TEXT | nulo |

Unicidade: `(session_id, revision_number)`.

Índices:

- `(session_id, revision_number DESC)`;
- `(answer_id)`;
- `(llm_execution_id)`.

Exclusão: histórico append-only.

### 5.12 `interview_answer_assessment_items`

**Responsabilidade:** strengths, weaknesses, risks, vetos e regras de uma
avaliação.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `assessment_id` | TEXT | FK obrigatória |
| `kind` | TEXT | `strength | weakness | risk | veto | rule` |
| `position` | INTEGER | obrigatório |
| `code` | TEXT | nulo |
| `text` | TEXT | obrigatório |
| `created_at` | TEXT | obrigatório |

Unicidade: `(assessment_id, kind, position)`.

Índice: `(assessment_id, kind, position)`.

Exclusão: acompanha somente rollback da avaliação.

### 5.13 `authorial_evidence`

**Responsabilidade:** trechos de evidência com proveniência.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `answer_id` | TEXT | FK nula somente em importação justificada |
| `legacy_id` | TEXT | nulo |
| `sequence_number` | INTEGER | obrigatório |
| `text` | TEXT | obrigatório |
| `origin` | TEXT | obrigatório |
| `created_at` | TEXT | obrigatório |

Unicidade:

- `(session_id, sequence_number)`;
- `(session_id, legacy_id)` quando preenchido.

Índices:

- `(session_id, sequence_number)`;
- `(answer_id)`.

Exclusão: `RESTRICT`.

### 5.14 `authorial_evidence_types`

**Responsabilidade:** tipos de sinal associados à evidência.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `evidence_id` | TEXT | parte da PK, FK |
| `signal_type` | TEXT | parte da PK |
| `created_at` | TEXT | obrigatório |

PK: `(evidence_id, signal_type)`.

Índice: `(signal_type, evidence_id)`.

Exclusão: acompanha rollback da evidência.

### 5.15 `authorial_signals`

**Responsabilidade:** sinais autorais históricos produzidos pela validação.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `answer_id` | TEXT | FK nula |
| `legacy_id` | TEXT | nulo |
| `signal_type` | TEXT | obrigatório |
| `summary` | TEXT | obrigatório |
| `confidence` | REAL | 0 a 1 |
| `origin` | TEXT | obrigatório |
| `status` | TEXT | `CONFIRMADO | INFERIDO | INCERTO | CONFLITANTE` |
| `created_at` | TEXT | obrigatório |

Índices:

- `(session_id, signal_type, status)`;
- `(answer_id)`.

Exclusão: histórico append-only.

### 5.16 `authorial_signal_evidence`

**Responsabilidade:** relação N:N entre sinais e evidências.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `signal_id` | TEXT | parte da PK, FK |
| `evidence_id` | TEXT | parte da PK, FK |
| `created_at` | TEXT | obrigatório |

PK: `(signal_id, evidence_id)`.

Índice adicional: `(evidence_id, signal_id)`.

Exclusão: acompanha rollback do sinal.

### 5.17 `authorial_dimensions`

**Responsabilidade:** score de cada dimensão em cada revisão de avaliação.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `assessment_id` | TEXT | FK obrigatória |
| `dimension_code` | TEXT | obrigatório |
| `score` | INTEGER | 0 a 100 |
| `state` | TEXT | estado válido definido em 8.4 |
| `rationale` | TEXT | nulo |
| `essential` | INTEGER | booleano |
| `critical` | INTEGER | booleano |
| `created_at` | TEXT | obrigatório |

Unicidade: `(assessment_id, dimension_code)`.

Índices:

- `(assessment_id, dimension_code)`;
- `(dimension_code, state, score)`.

Exclusão: acompanha rollback da avaliação; histórico concluído é imutável.

### 5.18 `authorial_dimension_evidence`

**Responsabilidade:** evidências que suportam uma dimensão.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `dimension_id` | TEXT | parte da PK, FK |
| `evidence_id` | TEXT | parte da PK, FK |
| `position` | INTEGER | obrigatório |
| `created_at` | TEXT | obrigatório |

PK: `(dimension_id, evidence_id)`.

Unicidade: `(dimension_id, position)`.

Exclusão: acompanha rollback da dimensão.

### 5.19 `authorial_dimension_rules`

**Responsabilidade:** regras determinísticas acionadas por dimensão.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `dimension_id` | TEXT | parte da PK, FK |
| `rule_code` | TEXT | parte da PK |
| `position` | INTEGER | obrigatório |
| `created_at` | TEXT | obrigatório |

PK: `(dimension_id, rule_code)`.

Unicidade: `(dimension_id, position)`.

### 5.20 `authorial_gaps`

**Responsabilidade:** lacunas identificadas em uma revisão de avaliação.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `assessment_id` | TEXT | FK obrigatória |
| `sequence_number` | INTEGER | obrigatório |
| `gap_type` | TEXT | obrigatório |
| `dimension_code` | TEXT | nulo |
| `relevance` | TEXT | `low | medium | high` |
| `expected_gain` | TEXT | `low | medium | high` |
| `critical` | INTEGER | booleano |
| `reason` | TEXT | obrigatório |
| `suggested_question` | TEXT | nulo |
| `status` | TEXT | `open | selected | addressed | dismissed` |
| `created_at` | TEXT | obrigatório |
| `updated_at` | TEXT | obrigatório |

Unicidade: `(assessment_id, sequence_number)`.

Índices:

- `(assessment_id, status, sequence_number)`;
- `(dimension_code, status)`.

Exclusão: histórico não é apagado.

### 5.21 `authorial_gateways`

**Responsabilidade:** decisão autoral por revisão, sem sobrescrever gateways
anteriores.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `round_id` | TEXT | FK nula |
| `assessment_id` | TEXT | FK obrigatória |
| `revision_number` | INTEGER | obrigatório |
| `approved` | INTEGER | booleano |
| `gateway_type` | TEXT | `EQUILIBRADO | DESEQUILIBRADO_FORTE | REPROVADO` |
| `llm_approved` | INTEGER | booleano |
| `heuristic_approved` | INTEGER | booleano |
| `balanced` | INTEGER | booleano |
| `strong_imbalanced` | INTEGER | booleano |
| `global_score` | INTEGER | 0 a 100 |
| `llm_confidence` | REAL | 0 a 1 |
| `justification` | TEXT | obrigatório |
| `deepening_should_ask` | INTEGER | booleano |
| `deepening_reason` | TEXT | nulo |
| `deepening_why_now` | TEXT | nulo |
| `marginal_gain` | TEXT | `low | medium | high`, nulo |
| `closure_reason` | TEXT | nulo |
| `selected_gap_id` | TEXT | FK nula |
| `created_at` | TEXT | obrigatório |

Unicidade: `(session_id, revision_number)`.

Índices:

- `(session_id, revision_number DESC)`;
- `(assessment_id)`;
- `(approved, gateway_type)`.

Exclusão: append-only.

### 5.22 `authorial_gateway_items`

**Responsabilidade:** dimensões excepcionais/fracas e vetos do gateway.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `gateway_id` | TEXT | FK obrigatória |
| `kind` | TEXT | `exceptional_dimension | weak_dimension | veto` |
| `position` | INTEGER | obrigatório |
| `value` | TEXT | obrigatório |
| `created_at` | TEXT | obrigatório |

Unicidade: `(gateway_id, kind, position)`.

Índice: `(gateway_id, kind, position)`.

### 5.23 `briefings`

**Responsabilidade:** revisão consolidada da matéria-prima autoral usada pelo
fluxo editorial.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `gateway_id` | TEXT | FK obrigatória |
| `revision_number` | INTEGER | obrigatório |
| `status` | TEXT | `draft | consolidated | superseded` |
| `theme` | TEXT | obrigatório |
| `objective` | TEXT | obrigatório |
| `format` | TEXT | obrigatório |
| `personality` | TEXT | obrigatório |
| `progress_state` | TEXT | obrigatório |
| `closure_reason` | TEXT | nulo |
| `fingerprint` | TEXT | obrigatório |
| `created_at` | TEXT | obrigatório |
| `consolidated_at` | TEXT | nulo |
| `superseded_at` | TEXT | nulo |

Unicidade:

- `(session_id, revision_number)`;
- um briefing `consolidated` ativo por sessão, via índice parcial.

Índices:

- `(session_id, revision_number DESC)`;
- `(gateway_id)`;
- `(fingerprint)`.

Exclusão: histórico não é apagado.

### 5.24 Relações congeladas do briefing

As tabelas abaixo preservam quais dados compunham cada briefing:

- `briefing_answers(briefing_id, answer_id, position, created_at)`;
- `briefing_evidence(briefing_id, evidence_id, position, created_at)`;
- `briefing_signals(briefing_id, signal_id, position, created_at)`;
- `briefing_dimensions(briefing_id, dimension_id, position, created_at)`;
- `briefing_gaps(briefing_id, gap_id, position, created_at)`.

Cada tabela possui PK composta pelo par de IDs, unicidade de posição dentro do
briefing, FKs `RESTRICT` e índice inverso pela entidade referenciada.

### 5.25 `storyboards`

**Responsabilidade:** cabeçalho de cada revisão de storyboard.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `briefing_id` | TEXT | FK obrigatória |
| `revision_number` | INTEGER | obrigatório |
| `status` | TEXT | `generating | available | failed | superseded | archived` |
| `briefing_fingerprint` | TEXT | obrigatório |
| `llm_execution_id` | TEXT | FK nula |
| `error_message` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |
| `updated_at` | TEXT | obrigatório |
| `completed_at` | TEXT | nulo |
| `superseded_at` | TEXT | nulo |
| `archived_at` | TEXT | nulo |

Unicidade: `(session_id, revision_number)`.

Índices:

- `(session_id, revision_number DESC)`;
- um storyboard `available` não superseded por sessão;
- `(briefing_id)`.

Exclusão: `RESTRICT`.

### 5.26 `storyboard_blocks`

**Responsabilidade:** blocos ordenados de uma revisão de storyboard.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `storyboard_id` | TEXT | FK obrigatória |
| `legacy_id` | TEXT | nulo |
| `position` | INTEGER | obrigatório, maior que zero |
| `role` | TEXT | obrigatório |
| `focus` | TEXT | obrigatório |
| `source_revision` | INTEGER | obrigatório |
| `created_at` | TEXT | obrigatório |

Unicidade:

- `(storyboard_id, position)`;
- `(storyboard_id, legacy_id)` quando preenchido.

Índice: `(storyboard_id, position)`.

Exclusão: apenas rollback de storyboard não concluído.

### 5.27 `block_approaches`

**Responsabilidade:** abordagem gerada para um bloco.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `block_id` | TEXT | FK obrigatória |
| `position` | INTEGER | obrigatório |
| `title` | TEXT | obrigatório |
| `description` | TEXT | obrigatório |
| `llm_execution_id` | TEXT | FK nula |
| `created_at` | TEXT | obrigatório |

Unicidade: `(block_id, position)`.

Índices: `(block_id, position)`, `(llm_execution_id)`.

Exclusão: histórico não é apagado após drafts.

### 5.28 `block_drafts`

**Responsabilidade:** rascunho gerado para uma abordagem/persona.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `block_id` | TEXT | FK obrigatória |
| `approach_id` | TEXT | FK obrigatória |
| `legacy_id` | TEXT | nulo |
| `revision_number` | INTEGER | obrigatório |
| `persona_id` | TEXT | obrigatório |
| `persona_name` | TEXT | obrigatório |
| `content_text` | TEXT | obrigatório, pode ser vazio enquanto pendente |
| `status` | TEXT | `pending | generating | available | failed | superseded` |
| `error_message` | TEXT | nulo |
| `llm_execution_id` | TEXT | FK nula |
| `created_at` | TEXT | obrigatório |
| `updated_at` | TEXT | obrigatório |
| `completed_at` | TEXT | nulo |
| `superseded_at` | TEXT | nulo |

Unicidade: `(block_id, revision_number, approach_id)`.

Índices:

- `(block_id, status, revision_number)`;
- `(approach_id)`;
- `(llm_execution_id)`.

Exclusão: histórico não é apagado.

### 5.29 `block_draft_selections`

**Responsabilidade:** histórico de seleção de rascunho por bloco.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `block_id` | TEXT | FK obrigatória |
| `draft_id` | TEXT | FK obrigatória |
| `selection_revision` | INTEGER | obrigatório |
| `active` | INTEGER | booleano |
| `selected_at` | TEXT | obrigatório |
| `superseded_at` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |

Unicidade:

- `(block_id, selection_revision)`;
- índice parcial único `(block_id)` onde `active = 1`.

Índices: `(block_id, selection_revision DESC)`, `(draft_id)`.

Exclusão: seleção antiga é desativada, nunca sobrescrita.

### 5.30 `post_versions`

**Responsabilidade:** conteúdo imutável de um post em um ponto do histórico.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `post_id` | TEXT | FK obrigatória |
| `produced_by_session_id` | TEXT | FK nula |
| `source_version_id` | TEXT | FK nula para versão anterior |
| `version_number` | INTEGER | obrigatório, maior que zero |
| `origin` | TEXT | `generated | composed | adjusted | imported | manual` |
| `status` | TEXT | `draft | consolidated | published | archived` |
| `content_text` | TEXT | obrigatório |
| `content_type` | TEXT | enum de formato |
| `platform` | TEXT | obrigatório |
| `personality_snapshot` | TEXT | obrigatório |
| `document_json` | TEXT | nulo; SlideMark ou documento flexível justificado |
| `metadata_json` | TEXT | nulo; não pode conter regra relacional |
| `content_sha256` | TEXT | obrigatório |
| `llm_execution_id` | TEXT | FK nula |
| `created_at` | TEXT | obrigatório |
| `consolidated_at` | TEXT | nulo |
| `published_at` | TEXT | nulo |
| `archived_at` | TEXT | nulo |

Unicidade:

- `(post_id, version_number)`;
- `content_sha256` não precisa ser único.

Índices:

- `(post_id, version_number DESC)`;
- `(post_id, status, version_number DESC)`;
- `(produced_by_session_id, created_at)`;
- `(source_version_id)`.

Exclusão: `RESTRICT`.

Imutabilidade: conteúdo, formato, plataforma, personalidade, origem, fonte e
documento não recebem `UPDATE`. Apenas transições de status e seus timestamps
são mutáveis.

### 5.31 `segments`

**Responsabilidade:** segmentos imutáveis e ordenados de uma versão.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `post_version_id` | TEXT | FK obrigatória |
| `legacy_id` | TEXT | nulo |
| `position` | INTEGER | obrigatório |
| `role` | TEXT | obrigatório |
| `text` | TEXT | obrigatório |
| `slide_number` | INTEGER | nulo |
| `title` | TEXT | nulo |
| `visual_notes` | TEXT | nulo |
| `image_mode` | TEXT | nulo |
| `image_description` | TEXT | nulo |
| `image_url` | TEXT | nulo |
| `image_source` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |

Unicidade: `(post_version_id, position)`.

Índices: `(post_version_id, position)`, `(role)`.

Bullets de slides, quando múltiplos, ficam em
`segment_bullets(segment_id, position, text, created_at)`.

Exclusão: `RESTRICT`; versão e segmentos são imutáveis.

### 5.32 `segment_adjustments`

**Responsabilidade:** pedido e resultado histórico de ajuste.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `source_version_id` | TEXT | FK obrigatória |
| `source_segment_id` | TEXT | FK obrigatória |
| `batch_id` | TEXT | UUID obrigatório |
| `request_text` | TEXT | obrigatório |
| `problem` | TEXT | nulo |
| `direction` | TEXT | nulo |
| `status` | TEXT | `proposed | accepted | rejected | failed` |
| `proposed_text` | TEXT | nulo |
| `result_version_id` | TEXT | FK nula |
| `result_segment_id` | TEXT | FK nula |
| `llm_execution_id` | TEXT | FK nula |
| `error_message` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |
| `decided_at` | TEXT | nulo |

Índices:

- `(source_version_id, source_segment_id, created_at)`;
- `(session_id, status, created_at)`;
- `(batch_id)`;
- `(result_version_id)`.

Exclusão: append-only.

Aceitar ajustes cria uma nova `post_version` e novos `segments`; nunca altera a
versão de origem.

### 5.33 `evaluations`

**Responsabilidade:** avaliação histórica de sessão, versão ou export.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK nula |
| `post_version_id` | TEXT | FK nula |
| `export_id` | TEXT | FK nula |
| `scope` | TEXT | `authorial | content | slidemark | export` |
| `status` | TEXT | `pending | running | completed | failed | cancelled | archived` |
| `total_score` | REAL | nulo |
| `verdict` | TEXT | nulo |
| `llm_execution_id` | TEXT | FK nula |
| `error_message` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |
| `started_at` | TEXT | nulo |
| `completed_at` | TEXT | nulo |
| `archived_at` | TEXT | nulo |

Regra de alvo:

- `authorial` exige `session_id`;
- `content` ou `slidemark` exige `post_version_id`;
- `export` exige `export_id`;
- campos de alvo não aplicáveis ficam nulos.

Índices:

- `(session_id, scope, created_at DESC)`;
- `(post_version_id, scope, created_at DESC)`;
- `(status, created_at)`.

Exclusão: histórico não é apagado.

### 5.34 `evaluation_items`

**Responsabilidade:** scores dimensionais, forças, fraquezas, redundâncias,
falhas, trechos fracos e sugestões.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `evaluation_id` | TEXT | FK obrigatória |
| `kind` | TEXT | `score | strength | weakness | weak_segment | redundancy | technical_failure | suggestion` |
| `position` | INTEGER | obrigatório |
| `dimension_code` | TEXT | nulo |
| `score` | REAL | nulo |
| `text` | TEXT | nulo |
| `segment_id` | TEXT | FK nula |
| `severity` | TEXT | `low | medium | high`, nulo |
| `problem` | TEXT | nulo |
| `reason` | TEXT | nulo |
| `direction` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |

Unicidade: `(evaluation_id, kind, position)`.

Índices:

- `(evaluation_id, kind, position)`;
- `(dimension_code, score)`;
- `(segment_id)`.

Exclusão: acompanha somente rollback da avaliação.

### 5.35 `exports`

**Responsabilidade:** tentativa e resultado de export de uma versão.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `post_version_id` | TEXT | FK obrigatória |
| `session_id` | TEXT | FK nula |
| `format` | TEXT | `markdown | json | slidemark_json` |
| `status` | TEXT | `pending | running | completed | failed | cancelled | archived` |
| `requested_path` | TEXT | nulo |
| `actual_path` | TEXT | nulo até concluir |
| `mime_type` | TEXT | nulo |
| `file_sha256` | TEXT | nulo |
| `file_size_bytes` | INTEGER | nulo, maior ou igual a zero |
| `error_message` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |
| `started_at` | TEXT | nulo |
| `completed_at` | TEXT | nulo |
| `archived_at` | TEXT | nulo |

Índices:

- `(post_version_id, created_at DESC)`;
- `(session_id, created_at DESC)`;
- `(status, created_at)`;
- `(file_sha256)`.

Exclusão: arquivar registro não apaga arquivo automaticamente. Remoção física
de arquivo é operação futura fora do escopo.

### 5.36 `llm_executions`

**Responsabilidade:** uma chamada concreta de LLM/agente e sua auditoria.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `session_id` | TEXT | FK obrigatória |
| `operation` | TEXT | obrigatório |
| `attempt_number` | INTEGER | obrigatório, maior que zero |
| `status` | TEXT | `queued | running | succeeded | failed | timed_out | cancelled | interrupted` |
| `provider` | TEXT | obrigatório |
| `model` | TEXT | nulo |
| `agent_tool` | TEXT | obrigatório |
| `reasoning` | TEXT | nulo |
| `sandbox` | TEXT | obrigatório |
| `timeout_seconds` | INTEGER | nulo |
| `prompt_text` | TEXT | nulo |
| `request_json` | TEXT | nulo, bruto/flexível |
| `response_text` | TEXT | nulo |
| `raw_response_json` | TEXT | nulo, bruto externo |
| `stdout_text` | TEXT | nulo |
| `stderr_text` | TEXT | nulo |
| `command_json` | TEXT | nulo, lista bruta de argumentos |
| `return_code` | INTEGER | nulo |
| `error_type` | TEXT | nulo |
| `error_message` | TEXT | nulo |
| `prompt_registry_execution_id` | TEXT | nulo |
| `prompt_operation` | TEXT | nulo |
| `prompt_composition_id` | TEXT | nulo |
| `prompt_composition_version` | INTEGER | nulo |
| `prompt_template_sha256` | TEXT | nulo |
| `prompt_resolved_sha256` | TEXT | nulo |
| `prompt_artifact_versions_json` | TEXT | nulo, snapshot de referências |
| `prompt_resolution_source` | TEXT | nulo |
| `prompt_used_fallback` | INTEGER | booleano nulo |
| `created_at` | TEXT | obrigatório |
| `queued_at` | TEXT | obrigatório |
| `started_at` | TEXT | nulo |
| `completed_at` | TEXT | nulo |
| `heartbeat_at` | TEXT | nulo |

Unicidade:

- `(session_id, operation, attempt_number)` quando a semântica da operação
  permitir; retries concorrentes são proibidos;
- índice parcial único `(session_id)` onde status é `queued` ou `running`.

Índices:

- `(session_id, created_at DESC)`;
- `(session_id, operation, created_at DESC)`;
- `(status, created_at)`;
- `(prompt_registry_execution_id)`;
- `(prompt_resolved_sha256)`.

Exclusão: histórico não é apagado. Retenção de campos volumosos poderá mover ou
compactar conteúdo no futuro, mas nunca remover metadados, hashes e status sem
política versionada.

### 5.37 `llm_execution_events`

**Responsabilidade:** eventos ordenados, stdout estruturado e progresso de uma
execução.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `llm_execution_id` | TEXT | FK obrigatória |
| `sequence_number` | INTEGER | obrigatório |
| `event_type` | TEXT | obrigatório |
| `stream` | TEXT | `system | stdout | stderr | external`, nulo |
| `level` | TEXT | `debug | info | warning | error`, nulo |
| `message` | TEXT | nulo |
| `payload_json` | TEXT | nulo, evento externo flexível |
| `occurred_at` | TEXT | obrigatório |
| `created_at` | TEXT | obrigatório |

Unicidade: `(llm_execution_id, sequence_number)`.

Índices:

- `(llm_execution_id, sequence_number)`;
- `(event_type, occurred_at)`.

Exclusão: acompanha a retenção da execução, nunca por API comum.

### 5.38 `legacy_imports`

**Responsabilidade:** idempotência, auditoria, divergências e rollback da
importação.

| Coluna | Tipo | Regra |
| --- | --- | --- |
| `id` | TEXT | PK UUID |
| `source_kind` | TEXT | `session_json | jsonl | export_scan` |
| `source_path` | TEXT | obrigatório |
| `source_schema_version` | TEXT | nulo |
| `source_sha256` | TEXT | obrigatório |
| `source_size_bytes` | INTEGER | obrigatório |
| `source_mtime_utc` | TEXT | nulo |
| `mode` | TEXT | `dry_run | apply` |
| `status` | TEXT | estado definido em 8.8 |
| `target_user_id` | TEXT | FK nula |
| `target_post_id` | TEXT | FK nula |
| `target_session_id` | TEXT | FK nula |
| `rows_planned` | INTEGER | maior ou igual a zero |
| `rows_written` | INTEGER | maior ou igual a zero |
| `warning_count` | INTEGER | maior ou igual a zero |
| `divergence_count` | INTEGER | maior ou igual a zero |
| `report_json` | TEXT | obrigatório, relatório flexível |
| `error_message` | TEXT | nulo |
| `backup_path` | TEXT | nulo |
| `created_at` | TEXT | obrigatório |
| `started_at` | TEXT | nulo |
| `completed_at` | TEXT | nulo |
| `rolled_back_at` | TEXT | nulo |

Unicidade:

- `(source_kind, source_sha256, mode, target_user_id)` para evitar repetição
  acidental;
- uma importação `apply` concluída por fonte/usuário, salvo override explícito.

Índices:

- `(status, created_at DESC)`;
- `(source_sha256)`;
- `(target_session_id)`.

Exclusão: registro nunca é apagado; rollback muda status e registra evento.

## 6. Regras de domínio

### 6.1 Usuários, posts e sessões

```text
pode_criar_post =
    usuario.status = active
```

```text
pode_criar_sessao =
    usuario.status = active
    E (
        post.status EM {draft, active}
        OU (post.status = completed E reabertura_explicita = verdadeiro)
      )
    E post.status != archived
```

- Usuário arquivado não recebe novo post.
- Post arquivado não recebe nova sessão nem nova versão.
- Uma nova tentativa sempre cria nova `session`.
- Sessão concluída, falha ou cancelada não volta a `active` silenciosamente.
- Retomar significa abrir a mesma sessão ainda ativa ou consultar uma sessão
  histórica; não significa sobrescrever outra.
- Para continuar após sessão terminal, criar nova tentativa.
- `attempt_number` é sequencial dentro do post e alocado em transação.
- Seleção atual de usuário/post/sessão não é salva nas tabelas de domínio.

### 6.2 Fase e ações

```text
acao_valida =
    sessao.status = active
    E acao PERTENCE_A acoes_permitidas(sessao.workflow_phase)
    E nenhum_pre_requisito_esta_ausente
```

- Ação inválida para fase atual retorna erro de domínio sem mudança.
- Falha de LLM não avança a fase.
- Transição e criação das entidades resultantes ocorrem na mesma transação
  curta posterior à execução.
- Eventos são acrescentados somente quando a mutação correspondente confirma.
- Mensagem de interface não define fase.

### 6.3 Entrevista

- Resposta original é imutável.
- Todas as candidatas são preservadas.
- Cada pergunta pertence a uma rodada.
- Uma rodada possui no máximo uma pergunta pendente por vez no fluxo padrão,
  salvo lote de extensão explicitamente modelado.
- Avaliações, dimensões, gaps e gateways são revisionados.
- Briefing consolidado referencia exatamente as evidências usadas.
- Novo gateway não apaga o anterior.
- `question_count` é derivado; `max_questions` é regra persistida da sessão.

### 6.4 Storyboard, drafts e seleção

- Alterar storyboard cria nova revisão.
- Blocos da revisão anterior permanecem históricos.
- Draft pertence a um bloco específico de uma revisão.
- Retry cria nova revisão de draft ou nova tentativa, não sobrescreve conteúdo
  disponível anterior.
- No máximo uma seleção ativa por bloco.
- Toda mudança de seleção desativa a seleção anterior e cria outra linha.
- Composição exige seleção ativa válida para todos os blocos da revisão.
- Seleção de draft superseded é inválida.

```text
pode_compor =
    storyboard.status = available
    E PARA_TODO bloco_ativo:
        existe_selecao_ativa
        E selecao.draft.status = available
```

### 6.5 Versões, segmentos e ajustes

- Toda versão é imutável desde a inserção.
- `version_number` é sequencial por post.
- A primeira versão tem número 1.
- Nova versão é criada dentro de transação que reserva o próximo número.
- Versão consolidada ou publicada nunca volta a draft.
- Publicar/consolidar muda apenas status e timestamp.
- Ajuste aceito cria nova versão e copia segmentos não alterados.
- Ajuste rejeitado mantém histórico e não cria versão.
- Avaliação sempre aponta para a versão efetivamente avaliada.
- Export sempre aponta para uma versão.

```text
aceitar_ajuste =
    ajuste.status = proposed
    E versao_origem.nao_arquivada
    E texto_proposto_valido
    ENTÃO criar_nova_versao
         E criar_novos_segmentos
         E marcar_ajuste = accepted
```

### 6.6 Optimistic locking

Toda mutação de sessão recebe `expected_lock_version`.

```text
atualizacao_valida =
    expected_lock_version = sessions.lock_version
```

A atualização SQL deve:

1. filtrar por `session_id` e `lock_version`;
2. incrementar `lock_version`;
3. verificar exatamente uma linha alterada.

Se zero linhas forem alteradas:

- rollback;
- resposta de conflito;
- nenhuma entidade parcial permanece.

Leituras não incrementam versão. Uma ação que não muda o domínio também não
incrementa.

### 6.7 Execuções LLM

- No máximo uma execução com status `queued` ou `running` por sessão.
- Sessões diferentes podem ter execuções ativas simultaneamente.
- A execução recebe UUID antes da resolução do prompt.
- O mesmo UUID é passado ao Prompt Registry como
  `prompt_registry_execution_id`.
- Configuração efetiva é copiada para `llm_executions`.
- A reserva da execução ocorre em transação curta.
- A chamada externa ocorre após commit.
- Resultado é persistido em nova transação curta.
- Falha de persistência do resultado não é convertida em sucesso.
- Na inicialização, execuções `running` sem processo recuperável tornam-se
  `interrupted` por reconciliação explícita.
- O sistema não mantém uma transação aberta enquanto aguarda LLM.

```text
pode_iniciar_llm =
    sessao.status = active
    E nao_existe_execucao_ativa(sessao.id)
    E lock_version_confere
```

### 6.8 Arquivamento

- Arquivar não apaga histórico.
- Arquivar usuário não arquiva automaticamente posts.
- Arquivar post não muda status das sessões/versões existentes, mas torna-as
  somente leitura.
- Arquivar sessão não arquiva post.
- Arquivar versão não apaga exports nem avaliações.
- Entidade arquivada não pode ser alvo de nova mutação de conteúdo.

## 7. Estados e transições

### 7.1 Post

Estados:

- `draft`;
- `active`;
- `completed`;
- `archived`.

Transições:

```text
draft -> active
draft -> archived
active -> completed
active -> archived
completed -> active      somente comando explícito de reabertura
completed -> archived
archived -> nenhuma
```

### 7.2 Fase da sessão

Valores canônicos:

- `entry`;
- `interview`;
- `authorial_gateway`;
- `briefing`;
- `storyboard`;
- `drafting`;
- `composition`;
- `segmentation`;
- `evaluation`;
- `adjustment`;
- `export_ready`;
- `completed`.

Aliases legados são convertidos no boundary/importador, não armazenados como
novos valores.

Transições normais:

```text
entry -> interview
interview -> authorial_gateway
authorial_gateway -> interview       quando aprofundamento é solicitado
authorial_gateway -> briefing        quando aprovado
briefing -> storyboard
storyboard -> drafting
drafting -> composition
composition -> segmentation
segmentation -> evaluation
evaluation -> adjustment
evaluation -> export_ready
adjustment -> evaluation
adjustment -> export_ready
export_ready -> completed
```

Limpeza/retry pode permanecer na mesma fase. Retrocesso que invalida downstream
cria novas revisões e marca resultados anteriores como superseded; não os
apaga.

### 7.3 Progresso autoral

- `EXPLORANDO`;
- `MATERIAL_HUMANO_IDENTIFICADO`;
- `APROFUNDANDO`;
- `MATERIAL_SUFICIENTE`;
- `CONCLUIDA`.

As transições seguem o controller autoral. `CONCLUIDA` não retorna a estado
anterior dentro da mesma tentativa sem comando explícito de extensão.

### 7.4 Dimensão autoral

- `NAO_OBSERVADA`;
- `FRACA`;
- `PARCIAL`;
- `SUFICIENTE`;
- `FORTE`;
- `EXCEPCIONAL`;
- `CONFLITANTE`;
- `NAO_APLICAVEL`.

São resultados de uma revisão, não um state machine mutável da mesma linha.

### 7.5 Sessão

```text
active -> completed
active -> failed
active -> cancelled
active -> archived
completed -> archived
failed -> archived
cancelled -> archived
archived -> nenhuma
```

Retry após terminal cria nova sessão.

### 7.6 Execução LLM

```text
queued -> running
queued -> cancelled
queued -> failed
running -> succeeded
running -> failed
running -> timed_out
running -> cancelled
running -> interrupted
estado_terminal -> nenhuma
```

Estados terminais: `succeeded`, `failed`, `timed_out`, `cancelled`,
`interrupted`.

### 7.7 Versão

```text
draft -> consolidated
draft -> published
draft -> archived
consolidated -> published
consolidated -> archived
published -> archived
archived -> nenhuma
```

O conteúdo é imutável em todos os estados.

### 7.8 Avaliação

```text
pending -> running
pending -> cancelled
running -> completed
running -> failed
running -> cancelled
completed -> archived
failed -> archived
cancelled -> archived
archived -> nenhuma
```

### 7.9 Export

Mesmas transições de avaliação, substituindo `pending` por criação do registro
antes da escrita do arquivo. `completed` exige caminho, hash e tamanho.

### 7.10 Importação legada

Estados:

- `pending`;
- `dry_run_ready`;
- `running`;
- `completed`;
- `completed_with_warnings`;
- `diverged`;
- `failed`;
- `rolled_back`.

Transições:

```text
pending -> dry_run_ready
pending -> failed
dry_run_ready -> running
dry_run_ready -> failed
running -> completed
running -> completed_with_warnings
running -> diverged
running -> failed
completed -> rolled_back
completed_with_warnings -> rolled_back
diverged -> rolled_back
failed -> nenhuma
rolled_back -> nenhuma
```

Um novo attempt de importação cria novo `legacy_imports.id`; não reabre a linha.

## 8. Persistência e infraestrutura

### 8.1 Abertura de conexão

Cada request/unidade de trabalho obtém sua própria conexão. Não compartilhar
uma conexão mutável global entre threads.

Na abertura:

```text
foreign_keys = ON
journal_mode = WAL
busy_timeout = valor_configurado
```

O valor inicial recomendado para `busy_timeout` é 5000 ms, alinhado ao Prompt
Registry, mas deve ser configurável e medido.

`synchronous` permanece decisão de implementação entre `NORMAL` e `FULL`. A
escolha deve ser documentada por ambiente.

### 8.2 Transações

- controle explícito de `BEGIN`, `COMMIT`, `ROLLBACK`;
- escrita concorrente sensível pode usar `BEGIN IMMEDIATE`;
- nenhuma transação atravessa I/O externo;
- rollback em qualquer exceção;
- criação de evento e mutação correspondente na mesma transação;
- alocação de `attempt_number`, `version_number`, sequências e `lock_version`
  dentro da transação;
- erros de `busy` são traduzidos para erro operacional recuperável, não sucesso.

### 8.3 Repositories

Repositories são a única camada autorizada a executar SQL de domínio fora do
runner de migrations.

Agregados mínimos:

- `UserRepository`;
- `PostRepository`;
- `SessionRepository`;
- `InterviewRepository`;
- `EditorialRepository`;
- `PostVersionRepository`;
- `EvaluationRepository`;
- `ExportRepository`;
- `LlmExecutionRepository`;
- `LegacyImportRepository`.

Cada repository:

- recebe uma conexão/UoW;
- não abre commit por conta própria;
- mapeia rows para modelos de domínio;
- possui testes próprios;
- oferece consultas por pai e ordenação;
- aplica invariantes que o banco não consegue expressar sozinho.

### 8.4 Unidade de trabalho

A unidade de trabalho:

- abre conexão;
- inicia transação quando solicitado;
- fornece repositories ligados à mesma conexão;
- confirma somente no boundary de serviço;
- faz rollback automático em erro;
- fecha conexão;
- não é mantida no controller como estado global.

### 8.5 Migration runner

- migrations numeradas e imutáveis;
- checksum validado antes de iniciar a aplicação;
- execução em ordem;
- uma transação por migration;
- falha impede startup mutável;
- execução repetida em schema atualizado é no-op;
- migration alterada após aplicação gera erro explícito;
- backup obrigatório antes de migration destrutiva ou corte de dados;
- banco novo deve chegar ao schema atual do zero;
- upgrade de cada versão suportada deve ser testado.

Migrations do domínio não leem nem alteram
`.data/prompt-registry.sqlite3`.

### 8.6 Banco de testes

- um arquivo temporário por teste de integração/repository;
- não usar o banco real;
- migrations reais aplicadas;
- foreign keys e pragmas iguais aos de produção;
- fixtures mínimas;
- limpeza pelo descarte do arquivo;
- testes concorrentes usam conexões diferentes.

### 8.7 Snapshot da sessão

Um `SessionSnapshotAssembler` reconstrói a projeção necessária à UI a partir do
banco. O snapshot:

- contém IDs e `lock_version`;
- contém o estado selecionado da sessão;
- inclui catálogos somente quando o endpoint pedir;
- deriva fases liberadas e indicadores;
- não duplica fontes de verdade em storage;
- pode oferecer campos temporários de compatibilidade durante a migração;
- nunca é aceito de volta como comando de substituição.

### 8.8 Lock por sessão

O processo mantém um registro de locks em memória indexado por `session_id`
apenas para reduzir disputa local. A garantia durável é:

- optimistic locking;
- índice parcial de execução ativa;
- transações SQLite.

O lock em memória:

- não é global;
- não substitui o banco;
- é liberado em `finally`;
- não impede execução de outra sessão;
- precisa de limpeza de entradas inativas.

## 9. APIs

Os caminhos abaixo são contratos recomendados. O servidor HTTP atual pode
implementá-los sem framework novo. Contratos equivalentes são aceitáveis desde
que mantenham IDs, versionamento e semântica.

### 9.1 Regras gerais

- JSON de request contém apenas parâmetros do comando.
- Toda ação editorial recebe `session_id` no path ou em campo obrigatório.
- Toda mutação de sessão recebe `expected_lock_version`.
- Nenhum endpoint aceita o estado completo como fonte de verdade.
- Respostas de mutação retornam novo `lock_version`.
- Entidade inexistente ou fora do pai retorna 404.
- Regra de domínio inválida retorna 422.
- Lock otimista ou execução ativa conflitante retorna 409.
- Banco ocupado após política de retry retorna 503.
- Erro interno retorna 500 com ID de correlação, sem vazar prompt/segredo.

### 9.2 Usuários

| Método e caminho | Contrato |
| --- | --- |
| `GET /api/users` | lista ativos; filtro opcional de arquivados |
| `POST /api/users` | cria com `display_name` |
| `GET /api/users/{user_id}` | detalhe |
| `PATCH /api/users/{user_id}` | altera nome enquanto ativo |
| `POST /api/users/{user_id}/archive` | arquiva |

### 9.3 Posts

| Método e caminho | Contrato |
| --- | --- |
| `GET /api/users/{user_id}/posts` | catálogo por status |
| `POST /api/users/{user_id}/posts` | cria post |
| `GET /api/posts/{post_id}` | detalhe |
| `PATCH /api/posts/{post_id}` | altera metadata mutável do post |
| `POST /api/posts/{post_id}/complete` | conclui |
| `POST /api/posts/{post_id}/reopen` | reabre explicitamente |
| `POST /api/posts/{post_id}/archive` | arquiva |

### 9.4 Sessões

| Método e caminho | Contrato |
| --- | --- |
| `GET /api/posts/{post_id}/sessions` | lista tentativas em ordem decrescente |
| `POST /api/posts/{post_id}/sessions` | cria nova tentativa |
| `GET /api/sessions/{session_id}` | metadata da sessão |
| `GET /api/sessions/{session_id}/snapshot` | snapshot para Workstation |
| `POST /api/sessions/{session_id}/complete` | conclui com versão esperada |
| `POST /api/sessions/{session_id}/cancel` | cancela |
| `POST /api/sessions/{session_id}/archive` | arquiva |
| `GET /api/sessions/{session_id}/events` | eventos paginados |

Criar sessão nunca reutiliza a última sessão terminal.

### 9.5 Ações do workflow

Contrato:

```text
POST /api/sessions/{session_id}/actions/{action_name}

body:
    expected_lock_version
    parameters

response:
    session_id
    lock_version
    action_result
    snapshot
```

Ações mínimas:

- iniciar entrevista;
- enviar resposta;
- diagnosticar lacunas;
- iniciar extensão;
- enviar lote de extensão;
- encerrar entrevista;
- atualizar/continuar gateway;
- consolidar briefing;
- gerar storyboard;
- revisar storyboard;
- gerar drafts de bloco;
- retry de draft;
- selecionar draft;
- compor versão;
- segmentar versão;
- avaliar versão;
- propor ajuste;
- aceitar/rejeitar ajuste;
- solicitar export.

Parâmetros contêm somente IDs e entradas específicas. Por exemplo, selecionar
draft recebe `block_id` e `draft_id`, não `editorial_flow`.

### 9.6 Versões

| Método e caminho | Contrato |
| --- | --- |
| `GET /api/posts/{post_id}/versions` | lista versões |
| `GET /api/versions/{version_id}` | conteúdo, segmentos e metadata |
| `POST /api/versions/{version_id}/consolidate` | muda status |
| `POST /api/versions/{version_id}/publish` | muda status local |
| `POST /api/versions/{version_id}/archive` | arquiva |
| `GET /api/versions/{version_id}/evaluations` | histórico |
| `GET /api/versions/{version_id}/exports` | histórico |

Não existe endpoint de atualização de conteúdo de versão.

### 9.7 Importação legada

| Método e caminho | Contrato |
| --- | --- |
| `POST /api/legacy-imports/dry-run` | analisa fonte e usuário alvo |
| `POST /api/legacy-imports` | aplica dry run aprovado |
| `GET /api/legacy-imports/{import_id}` | status e relatório |
| `GET /api/legacy-imports/{import_id}/comparison` | divergências detalhadas |
| `POST /api/legacy-imports/{import_id}/rollback` | rollback permitido |

Importação não substitui uma sessão existente. Ela cria entidades novas ou
retorna idempotentemente o resultado já aplicado.

### 9.8 Compatibilidade temporária

Durante `legacy` e `dual_write`, os endpoints atuais podem permanecer atrás de
feature flag. Eles devem:

- ser marcados deprecated;
- registrar uso;
- nunca ser usados pelo novo frontend depois da fase de compatibilidade;
- ser removidos antes do corte definitivo.

`POST /api/restore` não existe no contrato final. Sua substituição é o importador
auditável.

## 10. Frontend

### 10.1 Estado de seleção

O provider da aplicação mantém:

- `selectedUserId`;
- `selectedPostId`;
- `selectedSessionId`;
- catálogo de usuários;
- catálogo de posts do usuário selecionado;
- catálogo de sessões do post selecionado;
- snapshot da sessão selecionada;
- versão de lock do snapshot;
- estado transitório da interface.

Os IDs selecionados podem ser lembrados em URL ou localStorage, mas isso não
cria “sessão atual” no domínio.

### 10.2 Catálogos e biblioteca

A interface deve permitir:

- criar e selecionar usuário;
- listar posts ativos e arquivados;
- criar e selecionar post;
- listar sessões por tentativa/status/data;
- criar nova tentativa;
- retomar sessão ativa;
- consultar sessão terminal;
- listar versões do post;
- abrir versões e seus exports/avaliações.

### 10.3 Workstation

- renderiza somente com `selectedSessionId`;
- carrega `/snapshot`;
- ações enviam IDs/parâmetros e `expected_lock_version`;
- troca de sessão limpa transient state específico;
- ação longa em uma sessão não bloqueia navegação para catálogo;
- snapshots de sessões diferentes não se misturam;
- uma sessão histórica terminal é somente leitura;
- o componente não mantém cópia do estado interno completo para reenviar.

### 10.4 ContextBar

A ContextBar passa a:

- exibir seletores ou breadcrumb de usuário/post/sessão;
- mostrar status e tentativa;
- mostrar versão de conteúdo em foco;
- separar metadata do post de estado transitório;
- remover “salvar sessão inteira”;
- oferecer refresh da seleção;
- oferecer criação de nova tentativa;
- encaminhar arquivamento por ação explícita.

### 10.5 Reset

O reset global atual deixa de existir.

Comportamentos:

- “nova tentativa” cria nova sessão;
- “limpar formulário não salvo” afeta somente estado local;
- “recomeçar fase” cria revisão/entidade histórica conforme a regra;
- arquivar sessão não apaga;
- não há botão que substitua silenciosamente o histórico do post.

### 10.6 Conflitos

Ao receber 409 por `lock_version`:

1. preservar a entrada local ainda não enviada;
2. buscar snapshot atual;
3. informar que a sessão mudou;
4. permitir reaplicar apenas o comando, quando seguro;
5. nunca reenviar o snapshot antigo inteiro.

Ao receber 409 por execução LLM ativa:

- exibir operação ativa;
- acompanhar status;
- impedir novo disparo na mesma sessão;
- não bloquear sessões diferentes.

### 10.7 Dev Drawer

- remove “estado enviado em `/api/action`” como fonte editável;
- mostra IDs, `lock_version`, comando e parâmetros;
- pode mostrar snapshot somente leitura;
- substitui restore JSON por acesso ao importador legado;
- permite copiar IDs de correlação e execução;
- nunca expõe prompts ou stdout sensível sem ação explícita de desenvolvimento.

## 11. Migração

### 11.1 Estado `legacy`

- JSON é a fonte operacional.
- SQLite de domínio pode ainda não existir.
- Instrumentar inventário e métricas de uso.
- Criar backup do JSON e dos logs antes do primeiro import.
- Nenhuma mudança de comportamento para usuário final.

### 11.2 Estado `dual_write`

- JSON permanece fonte operacional temporária.
- Toda mutação confirmada é decomposta e gravada no SQLite.
- Cada tentativa registra sucesso/falha de ambos os lados.
- Como não há transação entre arquivo e SQLite, divergência é explícita.
- Falha no SQLite não pode ser ocultada.
- O rollout deve poder voltar a `legacy` por feature flag.
- Novas entidades recebem IDs estáveis compartilhados entre os writers quando
  possível.

Partes que podem coexistir:

- writer JSON e writer SQLite;
- endpoints legados e novos;
- snapshot legado e snapshot reconstruído;
- JSONL e eventos no banco;
- frontend antigo e frontend novo atrás de flags.

Partes que não podem coexistir como autoridade:

- dois alocadores independentes de número de versão;
- duas regras divergentes de fase;
- duas sessões “atuais” implícitas;
- restauração arbitrária de estado completo enquanto SQLite é autoridade;
- atualização de versão por JSON depois de consolidada.

### 11.3 Estado `sqlite_shadow_read`

- Escrita continua nos dois destinos.
- Resposta funcional ainda usa a fonte designada pelo rollout.
- A aplicação reconstrói snapshot do SQLite em background ou no fim da ação.
- Um comparador canônico confronta:
  - fase;
  - entrevista;
  - briefing;
  - storyboard;
  - drafts e seleção;
  - composição;
  - segmentos;
  - avaliação;
  - última execução quando correlacionável.
- Diferenças derivadas conhecidas são normalizadas.
- Divergências reais entram em `legacy_imports.report_json` ou registro de
  observabilidade equivalente.
- Corte é bloqueado enquanto divergências críticas excederem o limiar aprovado.

### 11.4 Estado `sqlite`

- SQLite é a única fonte de verdade.
- Escrita de `current-session.json` é desligada.
- Endpoints de estado completo e restore são removidos.
- JSON legado permanece somente leitura por período de retenção.
- JSONL deixa de ser mecanismo primário; novas execuções escrevem no banco.
- Export continua em arquivo, catalogado no banco.
- Prompt Registry permanece separado.

### 11.5 Importador idempotente

O importador:

1. calcula hash, tamanho e mtime;
2. valida schema e estrutura;
3. exige ou resolve usuário alvo segundo política aprovada;
4. executa dry run sem escrever entidades de domínio;
5. lista entidades planejadas;
6. detecta duplicações internas;
7. registra lacunas irrecuperáveis;
8. aplica tudo em transação;
9. monta snapshot relacional;
10. compara com snapshot legado;
11. registra relatório e divergências;
12. confirma ou faz rollback.

Reexecutar a mesma fonte para o mesmo usuário:

- retorna importação anterior quando já concluída;
- não duplica entidades;
- exige override explícito para novo attempt de importação.

### 11.6 Regras de decomposição

- gerar UUIDs novos;
- preservar IDs legados;
- não inventar usuário;
- não inventar rodadas históricas perdidas;
- deduplicar cópias exatas de evidência/gateway/briefing;
- registrar divergência entre cópias;
- converter `is_running = true` em execução `interrupted`, nunca ativa;
- criar execução sintética `imported` apenas quando houver dados concretos;
- não correlacionar JSONL por tempo quando houver ambiguidade;
- composição e conteúdo de topo divergentes viram divergência, não overwrite;
- total de avaliação é recalculado e comparado;
- paths de export só são associados quando a origem for demonstrável.

### 11.7 Dry run e relatório

O relatório contém:

- fonte e hash;
- schema detectado;
- usuário/post/sessão alvo;
- contagens por tabela;
- campos descartados por serem transitórios;
- duplicações colapsadas;
- dados não recuperáveis;
- linhas JSONL válidas/inválidas;
- correlações fortes/fracas/ausentes;
- divergências;
- warnings;
- status final;
- backup criado;
- instruções de rollback.

### 11.8 Backup

Antes de importação aplicada, migration destrutiva e corte:

- copiar JSON legado;
- catalogar JSONL relevantes;
- criar backup consistente do banco de domínio;
- executar checkpoint WAL antes da cópia offline ou usar API de backup SQLite;
- registrar hash e caminho no relatório;
- não alterar backups do Prompt Registry.

### 11.9 Rollback

Antes do corte:

- desabilitar dual write;
- voltar feature flag para `legacy`;
- manter SQLite para análise;
- rollback de importação remove somente entidades marcadas pela importação e que
  não receberam dependências posteriores.

Após o corte:

- não voltar a um JSON estagnado;
- rollback requer export de compatibilidade a partir do SQLite ou restauração
  do backup consistente do momento do corte;
- novas entidades criadas após o backup precisam ser preservadas/exportadas;
- decisão de rollback deve ser explícita e auditada.

### 11.10 Corte definitivo

Pré-condições:

- migrations aprovadas;
- importação idempotente validada;
- shadow read sem divergência crítica no período definido;
- frontend sem endpoints legados;
- testes de concorrência aprovados;
- restart e recovery aprovados;
- backup testado;
- rollback ensaiado;
- auditoria de dependências legadas limpa.

## 12. Observabilidade

Métricas/logs mínimos:

- tempo e falha de migration;
- `busy`/timeout SQLite;
- duração de transações;
- conflitos de `lock_version`;
- rejeições por execução LLM ativa;
- execuções por status/operação/sessão;
- execuções interrompidas recuperadas;
- divergências dual write/shadow read;
- importações por status;
- tamanho do banco e WAL;
- crescimento de texto bruto/eventos;
- uso de endpoints legados;
- falhas de export após criação do registro.

Logs não devem expor automaticamente prompts completos, respostas do usuário ou
stdout. O ID de correlação permite consulta autorizada localmente.

## 13. Segurança e privacidade local

Embora não exista autenticação:

- o servidor não deve assumir isolamento contra clientes hostis;
- dados de usuários diferentes são separados por relações, não por permissão;
- paths de export/import são validados contra diretórios permitidos;
- SQL usa parâmetros;
- payloads JSON têm limite de tamanho;
- logs evitam conteúdo sensível por default;
- o banco e backups permanecem fora de commits;
- não há tokens ou senhas nas novas tabelas.

## 14. Critérios de aceite

### 14.1 Estrutura e migrations

- Dado banco inexistente, iniciar aplica todas as migrations e cria schema
  completo.
- Dado banco atualizado, reiniciar não reaplica nem altera migrations.
- Dada migration aplicada com checksum divergente, startup falha explicitamente.
- Toda conexão de domínio retorna foreign keys habilitadas, WAL ativo e
  `busy_timeout` configurado.
- `.data/prompt-registry.sqlite3` não é alterado por migrations do domínio.

### 14.2 Múltiplos usuários e posts

- Criar usuários A e B.
- Criar pelo menos dois posts para A e um para B.
- Listar posts de A não retorna posts de B.
- Arquivar A impede novo post para A e preserva os existentes.
- Selecionar usuário no frontend não altera estado global de domínio.

### 14.3 Múltiplas sessões

- Criar duas sessões para o mesmo post produz IDs distintos e attempts
  sequenciais.
- Criar sessão para outro post não altera a primeira.
- Concluir sessão 1 e iniciar nova tentativa cria sessão 2.
- Retomar sessão ativa após reinício retorna o mesmo snapshot relacional.
- Abrir sessão histórica não muda a seleção de outro cliente.

### 14.4 Isolamento

```text
estado_da_sessao_A_antes = estado_da_sessao_A_depois
SE somente_sessao_B_foi_alterada
```

- Resposta, draft, seleção, versão, avaliação e export de B não aparecem em A.
- Reset local da UI não altera A nem B no backend.
- Não existe controller singleton contendo `TuiSessionState` global.

### 14.5 Versionamento

- Compor cria versão 1.
- Ajuste aceito cria versão 2 e preserva versão 1 byte a byte.
- Dois ajustes sequenciais criam números sem repetição.
- Versão consolidada/publicada rejeita alteração de conteúdo.
- Segmentos de cada versão permanecem ligados somente àquela versão.

### 14.6 Concorrência

- Duas ações com o mesmo `expected_lock_version` na mesma sessão: exatamente uma
  confirma e a outra recebe 409.
- O rollback da ação conflitante não deixa linhas parciais.
- Duas sessões diferentes executam LLM simultaneamente sem lock global.
- Duas execuções LLM para a mesma sessão não ficam ativas ao mesmo tempo.
- O banco não mantém transação aberta durante a chamada externa.
- `busy` além do timeout produz erro recuperável e não perda silenciosa.

### 14.7 Falhas e transações

- Falha ao inserir item de um agregado reverte cabeçalho, itens, evento e
  incremento de lock.
- Falha de LLM registra execução terminal e não avança fase.
- Reinício converte execução órfã `running` em `interrupted`.
- Falha de export registra `failed` e não cria registro `completed`.

### 14.8 Prompt Registry

- Uma execução nova usa o mesmo UUID no domínio e na referência do registry.
- O domínio continua consultável se o arquivo do registry estiver indisponível.
- Não existe foreign key cross-database.
- Configuração efetiva e hashes permanecem na execução.

### 14.9 Importação legada

- Dry run não altera tabelas de domínio.
- Aplicar a mesma fonte duas vezes não duplica dados.
- JSON schema `4.0` válido gera usuário alvo, post, sessão e histórico
  recuperável.
- Duplicações exatas são colapsadas.
- Divergências são reportadas, não ocultadas.
- `is_running` legado não cria execução ativa.
- JSON inválido falha sem escrita parcial.
- Rollback permitido remove somente dados daquela importação.
- Snapshot reconstruído é comparado com o legado.

### 14.10 API

- Toda ação editorial contém `session_id`.
- Toda mutação de sessão verifica `expected_lock_version`.
- Nenhuma API aceita o snapshot completo como fonte de verdade.
- Endpoints retornam 404, 409, 422, 503 e 500 conforme os contratos.
- Cada endpoint novo possui teste de integração HTTP.

### 14.11 Frontend

- Existem `selectedUserId`, `selectedPostId` e `selectedSessionId`.
- Catálogos podem trocar seleção sem mutar o domínio.
- Workstation envia comando específico, IDs e lock, sem JSON completo.
- Conflito recarrega snapshot e preserva entrada local.
- ContextBar identifica usuário, post e tentativa.
- Reset não destrói sessão histórica.
- Dev Drawer não restaura estado completo.

### 14.12 Corte

- Com feature mode `sqlite`, nenhuma escrita ocorre em
  `current-session.json`.
- Reinício funciona com o JSON removido do caminho padrão.
- Nenhum endpoint legado é usado pelo frontend.
- Novos eventos de LLM ficam no banco, não dependem de JSONL.
- SQLite é a única fonte de verdade de domínio.
- Auditoria final não encontra dependências ativas de:
  - `current-session.json`;
  - JSONL como persistência de domínio;
  - sessão global;
  - envio do estado completo;
  - métodos legados de persistência.

## 15. Decisões abertas controladas

As seguintes decisões não bloqueiam a especificação conceitual, mas precisam
ser fechadas antes da fase correspondente:

1. usuário default de importação versus seleção obrigatória;
2. política de retenção/compressão de prompt, stdout, stderr e raw JSON;
3. importação integral ou parcial dos JSONL antigos;
4. scan de exports legados;
5. `synchronous=NORMAL` ou `FULL`;
6. duração do shadow read e limiar de divergência;
7. suporte oficial a múltiplos processos;
8. mecanismo de cancelamento do processo externo;
9. prazo de retenção dos arquivos legados após corte.

Qualquer escolha deve preservar os princípios e critérios de aceite acima.
