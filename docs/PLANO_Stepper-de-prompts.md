## 1. Descobertas do repositório

### Fato confirmado: os prompts já estão armazenados em banco SQLite

O sistema **não** lê prompts diretamente dos arquivos `.md` em runtime. O fluxo real é:

1. **Bootstrap idempotente**: `src/content_engine/prompt_registry/importer.py:204` — `import_legacy_prompts()` popula o SQLite a partir dos 33 arquivos `.md` em `prompts/` (editorial, generator, interview, registry-seeds) na primeira execução.
2. **Banco de dados**: `.data/prompt-registry.sqlite3` (512 KB, 6 tabelas, 2 migrations aplicadas).
3. **Resolução em runtime**: `src/content_engine/prompt_registry/resolver.py:53` — `PromptResolver.resolve()` consulta exclusivamente o SQLite; os arquivos `.md` são ignorados após a migração inicial.
4. **Consumidores LLM**: todos os 13 pontos de chamada usam `resolve_prompt()` (ou indiretamente via `_resolve_editorial_prompt()`) — nunca leem arquivos.

### Tabelas existentes no SQLite

| Tabela | Linhas | Função |
|--------|--------|--------|
| `prompt_artifacts` | 38 | Artefatos (bases, personas, regras, políticas, contratos, etc.) |
| `prompt_artifact_versions` | 37 | Versões imutáveis de cada artefato (SHA-256, placeholders, status) |
| `prompt_operations` | 13 | Operações LLM (consumer_symbol, phase, rollout_mode) |
| `prompt_compositions` | 13 | Composições ativas (conjunto de itens condicionais por operação) |
| `prompt_composition_items` | 39 | Itens de composição com posição, condição (field/operator/value) e slot |
| `prompt_execution_references` | variável | Audit trail imutável de cada resolução de prompt |
| `schema_migrations` | 2 | Versionamento do schema SQLite |

### Nenhum LLM SDK — CLI tools via subprocess

O sistema é isolado por CLI:

| Provider | Binário | Método | Como o prompt chega |
|----------|---------|--------|---------------------|
| Codex | `codex exec` | `AgentWrapper.run_codex()` (agent_wrapper.py:96) | stdin (`-`) |
| OpenCode | `opencode run` | `AgentWrapper.run_opencode()` (agent_wrapper.py:140) | argumento CLI |
| Cursor | `agent --print` | `AgentWrapper.run_cursor()` (agent_wrapper.py:177) | argumento CLI |

**Não existe array de mensagens com roles `system`/`user`/`assistant`.** O único local com distinção é o cliente legado `CodexLlmClient._build_prompt()` (codex_llm_client.py:136), que concatena `system_prompt` e `user_prompt` com `"\n\n"`. Este cliente legado não é mais usado no fluxo principal.

### Template e placeholder engine

`src/content_engine/prompt_registry/renderer.py`:
- Placeholders: `{{var_name}}` ou `{var_name}`
- Validação estrita: placeholders não declarados causam erro
- Variáveis obrigatórias ausentes causam erro
- Placeholders sem valor causam erro
- Extração automática de placeholders com `extract_placeholders()`

### API existente do registry

`src/content_engine/prompt_registry/api.py`:
- `PromptRegistryApi.catalog()` — lista operações + artefatos + diagnósticos
- `PromptRegistryApi.operation(key)` — detalhes de uma operação (composição, itens, execuções)
- `PromptRegistryApi.preview(operation, context)` — resolve um prompt sem registrar execução
- `create_wsgi_app()` — adaptador WSGI com 3 rotas: `GET /api/prompt-registry`, `GET /api/prompt-registry/operations/<id>`, `POST /api/prompt-registry/preview`

**Estas rotas não estão expostas no servidor GUI atual.** O `server.py` do GUI não importa nem monta o `create_wsgi_app`.

### Frontend existente

- **Stack**: React 19 + TypeScript 5.8 + Vite 8 + Tailwind CSS 4 + `motion` (Framer Motion)
- **Design system**: tokens CSS custom (`--flux`, `--void`, `--bg`, `--surface`, `--hairline`, `--ink`, `--ember`, `--danger`, `--ok`), sistema de cores dinâmico (`--flux-hue` animado por fase), tipografia (`Space Grotesk`, `Inter Tight`, `IBM Plex Mono`)
- **Componentes reutilizáveis**: `PeButton` (variants: flux, ghost, outline, danger), `panel`, `inset-panel`, `mono-tag`, `eyebrow`, `sheen`, `Field`, `ErrorAccordion`, `ModalShell`, `FormattedText`, `AnimatedNumber`, `Reveal`, `ActivityGlyph`
- **Navegação**: `PipelineRail` (sidebar esquerda, 10 estágios), sem router URL — state-driven
- **Estado**: Zustand-style via React Context (`pe-store.tsx`) com `usePE()` hook
- **Já existe `PromptStage.tsx`**: renderiza o prompt de geração compilado — mas é minimal e específico da fase de geração

### Stack do backend

- **Servidor HTTP**: `http.server.ThreadingHTTPServer` (stdlib, sem framework) em `src/gui/server.py`
- **API REST**: endpoints `GET/PATCH /api/session`, `POST /api/action`, `GET/PUT /api/llm-config`, `POST /api/restore`
- **Persistência**: SQLite via `prompt_registry` + JSON via `persistence.py`
- **Python**: >=3.11, setuptools, sem dependências web (exceto PyYAML)

---

## 2. Mapa das chamadas de LLM

| # | Operação | Função/Local | Provider padrão | Modelo padrão | Condição | Conteúdo enviado | Origem do conteúdo | Editabilidade atual |
|---|----------|-------------|-----------------|---------------|----------|-----------------|--------------------|---------------------|
| 1 | `interview_questions` | `exploration.py:111 generate_candidates()` | opencode | opencode-go/qwen3.7-plus | sempre (entrevista) | prompt resolvido de `interview.questions` via registry | SQLite (seed: `registry-seeds/interview-questions.md`) | `EDITABLE_CONTENT` |
| 2 | `interview_validate` | `validation.py:120 validate_question()` | opencode | opencode-go/glm-5.2 | sempre (valida cada candidata) | prompt resolvido de `interview.validate` via registry | SQLite (seed: `registry-seeds/interview-validate.md`) | `EDITABLE_CONTENT` |
| 3 | `interview_evaluate` | `llm_evaluation.py:82 evaluate_authorship_llm()` | cursor | auto | gateway de autoria | prompt resolvido de `interview.evaluate` via registry | SQLite (seed: `registry-seeds/interview-evaluate.md`) | `EDITABLE_CONTENT` |
| 4 | `post_generate` | `generator.py:442 generate()` + `prompt_builder.py:51 build_generation_prompt()` | codex | gpt-5.5 | sempre (geração) | composição complexa de 9-13 artefatos condicionais | SQLite (base + persona + regras + política + contrato) | `EDITABLE_CONTENT` (fragmentos) |
| 5 | `storyboard_generate` | `editorial_generation.py:241 StoryboardGenerator.gerar()` | codex | gpt-5.6-terra | sempre (editorial) | `editorial.storyboard` via registry | SQLite (seed: `editorial/storyboard.md`) | `EDITABLE_CONTENT` |
| 6 | `block_approaches_generate` | `editorial_generation.py:266 BlockDraftGenerator.gerar_abordagens()` | codex | gpt-5.6-luna | por bloco (editorial) | `editorial.block_approaches` via registry | SQLite (seed: `editorial/block_approaches.md`) | `EDITABLE_CONTENT` |
| 7 | `block_draft_generate` | `editorial_generation.py:294 BlockDraftGenerator.gerar_rascunho()` | codex | gpt-5.6-terra | por bloco x abordagem (editorial) | composição: `editorial.block_draft` + `policy.anti_ia` | SQLite | `EDITABLE_CONTENT` (fragmentos) |
| 8 | `editorial_compose` | `editorial_generation.py:341 EditorialComposer.compose()` | codex | gpt-5.6-sol | sempre + retry condicional | composição complexa: `editorial.compose` + rules + policy + retry_appendix | SQLite | `EDITABLE_CONTENT` (fragmentos) |
| 9 | `segment` | `segmentation.py:238 Segmenter.segmentar()` | opencode | opencode-go/qwen3.6-plus | sempre (pós-geração) | `generator.segment` ou `generator.segment_slides` condicional | SQLite | `EDITABLE_CONTENT` |
| 10 | `adjust_segment` | `adjust_segment.py:30 SegmentAdjuster.ajustar()` | opencode | opencode-go/qwen3.6-plus | ajuste individual | `generator.adjust_segment` via registry | SQLite | `EDITABLE_CONTENT` |
| 11 | `adjust_segments_bulk` | `adjust_segments_bulk.py:57 SegmentBulkAdjuster.ajustar()` | cursor | auto | ajuste em lote | `generator.adjust_segments_bulk` via registry | SQLite | `EDITABLE_CONTENT` |
| 12 | `post_evaluate` | `post_evaluation.py:145 PostEvaluator.avaliar()` | codex | gpt-5.6-terra | sempre + condicional por tipo | composição condicional: evaluate_post_{type} | SQLite | `EDITABLE_CONTENT` |
| 13 | `slidemark_export` | `slidemark_converter.py:150 SlideMarkConverter.converter()` | opencode | opencode-go/qwen3.6-plus | condicional (visual track) | composição: export_slidemark + rules + contract | SQLite | `EDITABLE_CONTENT` (fragmentos) |

### Observações sobre retry/fallback

- **Única operação com retry explícito**: `editorial_compose` (editorial_generation.py:368-403). Se a validação de preservação falha, re-executa com `retry_attempt=1`, que ativa o artefato condicional `editorial.retry_preservation`.
- **Não há fallbacks automáticos** no registry. Se uma operação falha, o erro é propagado.
- **Provider switching em runtime**: configurável via `agent-config.yml` e pela UI Agents, mas não há fallback automático entre providers.

---

## 3. Mapa dos prompts e fragmentos

### Artefatos operacionais (38 total, 33 ativos)

| Key | Tipo | Status | Origem | Path seed | Operações | Variáveis | Composição |
|-----|------|--------|--------|-----------|-----------|-----------|------------|
| `interview.questions` | `PROMPT_TEMPLATE` | ACTIVE | markdown | `registry-seeds/interview-questions.md` | interview_questions | `candidate_count`, `context_json` | Não |
| `interview.validate` | `PROMPT_TEMPLATE` | ACTIVE | markdown | `registry-seeds/interview-validate.md` | interview_validate | `known_issues`, `context_json` | Não |
| `interview.evaluate` | `EVALUATION` | ACTIVE | markdown | `registry-seeds/interview-evaluate.md` | interview_evaluate | `material_json` | Não |
| `interview.explore` | `REFERENCE` | ACTIVE | markdown | `interview/explore.md` | Nenhuma | — | — |
| `interview.evaluate_authorship` | `REFERENCE` | ACTIVE | markdown | `interview/evaluate-authorship.md` | Nenhuma | — | — |
| `interview.deepen` | `REFERENCE` | ACTIVE | markdown | `interview/deepen.md` | Nenhuma | — | — |
| `generator.base` | `BASE` | ACTIVE | markdown | `generator/base.md` | post_generate (cond: post/article) | múltiplas (briefing, tema, etc.) | Sim |
| `generator.base_short_carousel` | `BASE` | ACTIVE | markdown | `generator/base-short-carousel.md` | post_generate (cond: short_carousel) | múltiplas | Sim |
| `generator.base_long_slide` | `BASE` | ACTIVE | markdown | `generator/base-long-slide.md` | post_generate (cond: long_slide) | múltiplas | Sim |
| `generator.rules_post` | `FORMAT_RULES` | ACTIVE | markdown | `generator/rules-post.md` | post_generate, editorial_compose | — | Sim |
| `generator.rules_article` | `FORMAT_RULES` | ACTIVE | markdown | `generator/rules-article.md` | post_generate, editorial_compose | — | Sim |
| `generator.rules_short_carousel` | `FORMAT_RULES` | ACTIVE | markdown | `generator/rules-short-carousel.md` | post_generate, editorial_compose, slidemark_export | — | Sim |
| `generator.rules_long_slide` | `FORMAT_RULES` | ACTIVE | markdown | `generator/rules-long-slide.md` | post_generate, editorial_compose, slidemark_export | — | Sim |
| `generator.persona_post` | `PERSONA` | ACTIVE | markdown | `generator/personas/dev-interlocutor-post.md` | post_generate (slot: personaSelecionada) | — | Sim (slot) |
| `generator.persona_article` | `PERSONA` | ACTIVE | markdown | `generator/personas/dev-interlocutor-article.md` | post_generate (slot: personaSelecionada) | — | Sim (slot) |
| `generator.persona_short_carousel` | `PERSONA` | ACTIVE | markdown | `generator/personas/dev-interlocutor-short-carousel.md` | post_generate (slot: personaSelecionada) | — | Sim (slot) |
| `generator.persona_long_slide` | `PERSONA` | ACTIVE | markdown | `generator/personas/dev-interlocutor-long-slide.md` | post_generate (slot: personaSelecionada) | — | Sim (slot) |
| `policy.anti_ia` | `POLICY` | ACTIVE | json | `registry-seeds/anti-ia-policy.json` | post_generate, block_draft, editorial_compose | — | Sim (slot) |
| `contract.slidemark` | `OUTPUT_CONTRACT` | ACTIVE | markdown | `registry-seeds/slidemark-contract.md` | post_generate, slidemark_export | — | Sim (slot) |
| `generator.segment` | `SEGMENTATION` | ACTIVE | markdown | `generator/segment.md` | segment (cond: not visual) | múltiplas | Não |
| `generator.segment_slides` | `SEGMENTATION` | ACTIVE | markdown | `generator/segment-slides.md` | segment (cond: visual) | múltiplas | Não |
| `generator.adjust_segment` | `SEGMENTATION` | ACTIVE | markdown | `generator/adjust-segment.md` | adjust_segment | múltiplas | Não |
| `generator.adjust_segments_bulk` | `SEGMENTATION` | ACTIVE | markdown | `generator/adjust-segments-bulk.md` | adjust_segments_bulk | múltiplas | Não |
| `generator.export_slidemark` | `PROMPT_TEMPLATE` | ACTIVE | markdown | `generator/export-slidemark.md` | slidemark_export | múltiplas | Sim (composição) |
| `generator.evaluate_post_post` | `EVALUATION` | ACTIVE | markdown | `generator/evaluate-post-post.md` | post_evaluate (cond: post) | múltiplas | Não |
| `generator.evaluate_post_article` | `EVALUATION` | ACTIVE | markdown | `generator/evaluate-post-article.md` | post_evaluate (cond: article) | múltiplas | Não |
| `generator.evaluate_post_short_carousel` | `EVALUATION` | ACTIVE | markdown | `generator/evaluate-post-short-carousel.md` | post_evaluate (cond: short_carousel) | múltiplas | Não |
| `generator.evaluate_post_long_slide` | `EVALUATION` | ACTIVE | markdown | `generator/evaluate-post-long-slide.md` | post_evaluate (cond: long_slide) | múltiplas | Não |
| `editorial.storyboard` | `EDITORIAL` | ACTIVE | markdown | `editorial/storyboard.md` | storyboard_generate | múltiplas | Não |
| `editorial.block_approaches` | `EDITORIAL` | ACTIVE | markdown | `editorial/block_approaches.md` | block_approaches_generate | múltiplas | Não |
| `editorial.block_draft` | `EDITORIAL` | ACTIVE | markdown | `editorial/block_draft.md` | block_draft_generate | múltiplas | Sim (com anti_ia) |
| `editorial.compose` | `EDITORIAL` | ACTIVE | markdown | `editorial/compose.md` | editorial_compose | múltiplas | Sim (com rules + policy + retry) |
| `editorial.retry_preservation` | `RETRY_APPENDIX` | ACTIVE | markdown | `registry-seeds/editorial-retry-preservation.md` | editorial_compose (cond: retry_attempt=1) | `preservation_issues` | Sim (slot) |

### Artefatos legados/orphans

| Key | Status | Motivo |
|-----|--------|--------|
| `generator.rules_feed` | LEGACY | Regras de feed legadas, não participam de runtime |
| `generator.rules_slide` | LEGACY | Regras de slide legadas, não participam de runtime |
| `generator.persona_feed` | LEGACY | Persona de feed legada |
| `generator.persona_slide` | LEGACY | Persona de slide legada |
| `router.suggest_content_type` | ORPHAN | Sem fonte (path=None), nunca usado |

---

## 4. Arquitetura recomendada

### Estado atual

```
┌──────────────────────────────────────────────────────────────┐
│                      CONSUMIDORES LLM                         │
│  exploration.py  validation.py  llm_evaluation.py             │
│  generator.py    editorial_generation.py                      │
│  segmentation.py adjust_segment.py  adjust_segments_bulk.py   │
│  post_evaluation.py  slidemark_converter.py                   │
│  prompt_builder.py (build_generation_prompt)                  │
└──────────────────────────┬───────────────────────────────────┘
                           │ resolve_prompt("operation", ctx)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    PROMPT RESOLVER                             │
│  resolver.py: PromptResolver.resolve()                        │
│  - lookup operation → composition → items                     │
│  - evaluate conditions against context                        │
│  - resolve runtime slots                                      │
│  - concatenate artifact contents                              │
│  - render template with context variables                     │
│  - record execution reference (audit)                         │
└──────────────────────────┬───────────────────────────────────┘
                           │ SQL queries
                           ▼
┌──────────────────────────────────────────────────────────────┐
│                    PROMPT REGISTRY (SQLite)                    │
│  prompt_artifacts + prompt_artifact_versions                  │
│  prompt_operations + prompt_compositions + composition_items  │
│  prompt_execution_references                                  │
└──────────────────────────────────────────────────────────────┘
```

### Arquitetura recomendada

O sistema já possui infraestrutura suficiente. O plano é **estender** o que existe, não reescrever.

```
                        ┌─────────────────┐
                        │   API SERVER     │
                        │  gui/server.py   │
                        │  (adicionar      │
                        │  rotas registry) │
                        └────────┬────────┘
                                 │ GET/PUT /api/prompt-registry/...
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                    NOVA TELA: PROMPT OBSERVATORY                    │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  CABEÇALHO: título, resumo, busca global, filtros           │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  STEPPER HORIZONTAL (fases reais do pipeline)               │    │
│  │  ┌────┬────┬────┬────┬────┬────┬────┬────┬────┬────┬────┐  │    │
│  │  │Int │Int │Int │Gen │Edit│Edit│Edit│Seg │Adj │Eval│Exp │  │    │
│  │  │Expl│Val │Eval│    │Stor│Draf│Comp│    │    │    │    │  │    │
│  │  └────┴────┴────┴────┴────┴────┴────┴────┴────┴────┴────┘  │    │
│  │                                                              │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  PAINEL DA FASE SELECIONADA                                 │    │
│  │  ┌──────────────────────┐ ┌──────────────────────────────┐  │    │
│  │  │ operações LLM (lista)│ │ prompts e fragmentos (lista) │  │    │
│  │  │                      │ │                              │  │    │
│  │  │                      │ │                              │  │    │
│  │  └──────────────────────┘ └──────────────────────────────┘  │    │
│  │                                                              │    │
│  ├─────────────────────────────────────────────────────────────┤    │
│  │  VISUALIZADOR DE COMPOSIÇÃO (para operações com composição) │    │
│  │  [base] → [persona] → [regras] → [política] → [contrato]   │    │
│  │                                                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  EDITOR (painel lateral deslizante ou tela dividida)               │
└────────────────────────────────────────────────────────────────────┘
```

### Fonte única de verdade

**Recomendação**: o SQLite Prompt Registry **já é** a fonte única de verdade. O plano é mantê-lo assim.

| Camada | Responsabilidade |
|--------|-----------------|
| **SQLite** (`prompt_artifact_versions.content`) | Conteúdo canônico editável |
| **Importer** (`importer.py`) | Migração inicial (idempotente, nunca sobrescreve edições manuais) |
| **Resolver** (`resolver.py`) | Único ponto de consumo em runtime |
| **API** (`api.py` + novas rotas em `server.py`) | Leitura e escrita para o frontend |
| **Frontend** (nova tela) | Visualização e edição |
| **Instrumentação** (opcional futuro) | `agent_wrapper.py` já loga `llm_request`/`llm_response`; o resolver já registra `prompt_execution_references` |

**Não é necessário extrair conteúdo embedded em Python** — porque não há. Todo conteúdo de prompt já está no SQLite.

### Migração de conteúdo embedded

**Não aplicável no estado atual.** O código Python contém apenas:
1. Constantes de mapeamento (`PERSONAS_POR_TIPO`, `BASE_FILES_POR_TIPO`) — não são prompts, são metadados de roteamento.
2. Builders de contexto (`build_generation_prompt()`, `_storyboard_context()`, etc.) — constroem o dict de variáveis, não strings de prompt.
3. Constantes de scoring (`_SCORE_KEYS`, `_papeis_esperados_por_formato`) — lógica de negócio.
4. Dicionários de configuração (`DEFAULT_OPERATION_CONFIGS`) — metadados de provider/modelo.

Nenhum destes deve ser extraído — são código estrutural, não conteúdo editorial.

---

## 5. Proposta de UX/UI

### Layout geral

A tela é uma **nova área de navegação**, acessível via:
- **Atalho**: `Cmd+Shift+P` (ou botão no `ContextBar`)
- **Ou**: Um step adicional "Observability" no `PipelineRail` (após o step 09 "Exportação")
- **Ou**: Um ícone dedicado na barra superior (recomendado: ícone de "olho" ou "pipeline" ao lado do toggle de tema)

**Justificativa**: Não deve substituir a tela de PromptStage existente (que é parte do fluxo de geração). Deve ser uma área de observabilidade independente, acessível a qualquer momento.

```
┌──────────────────────────────────────────────────────────────────────────┐
│  [◀ Post Engine]   Prompt Pipeline Observatory            [Cmd+Shift+P]  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  🔍 Buscar prompts, operações, artefatos...    [filtros] [status]  │  │
│  │  13 operações  ·  38 artefatos  ·  39 fragmentos  ·  0 problemas   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                          │
│  ═══════════════════════════════════════════════════════════════════════ │
│  STEPPER HORIZONTAL                                                      │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ [◀ scroll ▶]                                                        │  │
│  │                                                                      │  │
│  │  ●─────────●─────────●─────────●──────┬──────●──────●──────●──────● │  │
│  │  │         │         │         │      │      │      │      │      │  │  │
│  │  │ 01      │ 02      │ 03      │ 04   │ 05   │ 06   │ 07   │ 08   │  │  │
│  │  │ Interview│Interview│Interview│Gene- │Edito-│Edito-│Edito-│Seg-  │  │  │
│  │  │ Explore │Validate │Evaluate │ration│rial  │rial  │rial  │ment. │  │  │
│  │  │         │         │         │      │SB    │Drafts│Compose│     │  │  │
│  │  │  1 op   │  1 op   │  1 op   │ 1 op │1 op  │2 ops │1 op  │1 op  │  │  │
│  │  │  1 frag │  1 frag │  1 frag │13 fr │1 fr  │2 fr  │6 fr  │2 fr  │  │  │
│  │  │  ACTIVE │  ACTIVE │  ACTIVE │ACTIVE│ACTIVE│ACTIVE│COND. │COND. │  │  │
│  │  └─────────┴─────────┴─────────┴──────┴──────┴──────┴──────┴──────┘  │  │
│  │                                    ...mais steps visíveis ao scroll   │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│  ═══════════════════════════════════════════════════════════════════════ │
│                                                                          │
│  ┌─────────────────────────────────┬──────────────────────────────────┐  │
│  │  PAINEL ESQUERDO (60%)          │  PAINEL DIREITO (40%)             │  │
│  │  ┌───────────────────────────┐  │  ┌────────────────────────────┐  │  │
│  │  │ OPERAÇÕES LLM             │  │  │ PROMPTS & FRAGMENTOS       │  │  │
│  │  │                           │  │  │                            │  │  │
│  │  │ ▼ post_generate           │  │  │ ▶ generator.base           │  │  │
│  │  │   codex · gpt-5.5         │  │  │   BASE · 12 variáveis      │  │  │
│  │  │   9-13 fragmentos         │  │  │   EDITABLE_CONTENT         │  │  │
│  │  │   cond: content_type      │  │  │                            │  │  │
│  │  │   └─ composição ativa     │  │  │ ▶ generator.persona_post   │  │  │
│  │  │                           │  │  │   PERSONA · slot           │  │  │
│  │  │                           │  │  │   EDITABLE_CONTENT         │  │  │
│  │  │                           │  │  │                            │  │  │
│  │  │                           │  │  │ ▶ generator.rules_post     │  │  │
│  │  │                           │  │  │   FORMAT_RULES · slot      │  │  │
│  │  │                           │  │  │   EDITABLE_CONTENT         │  │  │
│  │  │                           │  │  │                            │  │  │
│  │  │                           │  │  │ ▶ policy.anti_ia           │  │  │
│  │  │                           │  │  │   POLICY · slot            │  │  │
│  │  │                           │  │  │   EDITABLE_WITH_VALIDATION │  │  │
│  │  │                           │  │  │                            │  │  │
│  │  │                           │  │  │ ▶ contract.slidemark       │  │  │
│  │  │                           │  │  │   OUTPUT_CONTRACT · slot   │  │  │
│  │  │                           │  │  │   EDITABLE_WITH_VALIDATION │  │  │
│  │  └───────────────────────────┘  │  └────────────────────────────┘  │  │
│  └─────────────────────────────────┴──────────────────────────────────┘  │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  VISUALIZADOR DE COMPOSIÇÃO (expansível, para operações compostas)  │  │
│  │                                                                      │  │
│  │  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐       │  │
│  │  │          │    │ persona  │    │ format   │    │ anti_ia  │       │  │
│  │  │  base    │───▶│ _post    │───▶│ rules    │───▶│ policy   │───▶   │  │
│  │  │          │    │ (slot)   │    │ (slot)   │    │ (slot)   │       │  │
│  │  └──────────┘    └──────────┘    └──────────┘    └──────────┘       │  │
│  │                                              ┌──────────┐            │  │
│  │                                              │ slidemark│            │  │
│  │                                         ────▶│ contract │            │  │
│  │                                              │ (cond.)  │            │  │
│  │                                              └──────────┘            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Stepper horizontal

**Design**: trilhos de conexão com dots/retângulos, scroll horizontal com `scroll-snap-type: x mandatory`.

**Estados visuais do step**:
- **Ativo/selecionado**: glow flux, borda destacada, conectores iluminados
- **Inativo**: reduzido (cor ink-faint)
- **Condicional**: indicador visual (ex: pequeno losango, badge "COND")
- **Com erro**: borda danger, ícone de alerta
- **Não executável na sessão atual**: opacidade reduzida, tooltip explicativo

**Hierarquia**:
- **Nível 1 (stepper)**: fases agrupadas por macro-categoria (Interview, Generation, Editorial, Segmentation, Evaluation, Export)
- **Nível 2 (painel)**: operações LLM dentro da fase
- **Nível 3 (lista)**: artefatos/fragmentos dentro da operação

### Painel da fase

Ao selecionar uma fase no stepper:
- **Esquerda**: lista de operações LLM daquela fase (nome, provider, modelo, condição, status, número de fragmentos)
- **Direita**: lista de artefatos/fragmentos usados pelas operações da fase (título, tipo, status, editabilidade, variáveis)
- **Abaixo**: visualizador de composição para a operação selecionada (se composta)

### Visualizador de composição

Para operações compostas (ex: `post_generate` com 13 itens), mostra os artefatos em sua ordem real de concatenação:

```
[base.post (pos 10)] ───▶ [persona_post (pos 40, slot)] ───▶ [rules_post (pos 80, slot)] ───▶ [anti_ia (pos 120, slot)] ───▶ [slidemark (pos 130, cond)]
```

Cada bloco é clicável e revela:
- Nome e key do artefato
- Tipo (BASE, PERSONA, FORMAT_RULES, etc.)
- Posição na composição
- Condição de inclusão
- Se é slot ou concatenação inline
- Prévia do conteúdo (primeiras 5 linhas)
- Status da versão ativa
- Editabilidade

### Editor

**Decisão**: painel lateral deslizante (`slide-over` da direita, 480px ou 50% da tela).

**Justificativa**:
- Mantém o contexto da fase visível (não perde o mapa do pipeline)
- Funciona bem em resoluções ≥1024px (o pipeline rail já ocupa 248px)
- O pattern `DevDrawer` já existe no frontend e pode ser adaptado
- Alternativa (tela dedicada) quebraria a fluidez da navegação entre fases

**Estados do editor**:
1. **Leitura**: conteúdo completo renderizado com syntax highlighting de placeholders
2. **Edição**: textarea monospace com destaque de sintaxe de placeholders
3. **Alterado**: indicador visual de dirty state, botão "Desfazer alterações"
4. **Salvando**: indicador de progresso
5. **Erro de validação**: lista de problemas (placeholder removido, contrato quebrado, etc.)
6. **Salvo**: confirmação temporária com animação

**Avisos contextuais no editor**:
- Em artefatos compostos: "Este fragmento participa de {n} operações. Alterações afetarão: post_generate, editorial_compose"
- Em artefatos LEGACY: "Este artefato não participa do runtime atual"
- Em artefatos com slot: "Este artefato é injetado como variável {slotName} no template pai"

### Responsividade

- **≥1280px**: layout completo com 3 colunas (stepper + 2 painéis + editor opcional)
- **1024-1279px**: stepper + 1 painel principal (toggle entre operações e fragmentos), editor como slide-over
- **<1024px**: stepper vertical colapsável, lista única alternável, editor full-screen

### Animações e microinterações

- **Stepper**: transição suave entre steps com `transition: all 0.3s ease` nos conectores
- **Seleção de fase**: highlight com `box-shadow` glow animado (reutilizar `flux-glow`)
- **Abertura de painel**: slide do editor com spring physics (reutilizar `motion` library existente)
- **Seleção de artefato**: expansão suave com `layout` animation do motion
- **Visualizador de composição**: animação de "fluxo" entre blocos (linhas tracejadas animadas com `stroke-dashoffset`)
- **Scroll do stepper**: `scroll-behavior: smooth` + snap points

### Acessibilidade

- Navegação completa por teclado (Tab, Shift+Tab, Enter, Escape, setas no stepper)
- ARIA labels em todos os elementos interativos
- Focus rings visíveis (usando `--flux` para consistência)
- Alto contraste mantido (cores do design system já têm bom contraste)
- Animações respeitam `prefers-reduced-motion`

### Estratégia "deslumbrante sem prejudicar"

O design system já provê atmosfera premium (flux colors, glass morphism, tipografia Space Grotesk + IBM Plex Mono). O diferencial visual virá de:

1. **Fluxo de dados animado no visualizador de composição**: linhas que "fluem" entre blocos, como dados percorrendo um circuito
2. **Indicadores de status pulsantes** (já existe `ActivityGlyph`)
3. **Stepper com profundidade**: sombras sutis e camadas sobrepostas nos conectores
4. **Tipografia com hierarquia excepcional**: números mono para ordens, display para títulos, body tight para descrições
5. **Background sutil com grid** (já existe `AmbientField`) — mas em versão reduzida para a tela de observabilidade
6. **Micro-interações de revelação**: conteúdo que aparece com stagger animation ao selecionar uma fase

---

## 6. Contratos (Modelos e API)

### Modelo de dados (já existente + extensões)

Os modelos abaixo **já existem** em `src/content_engine/prompt_registry/models.py`:

- `PromptArtifact` — id, key, title, description, artifact_type, status, source_origin, legacy_source_path
- `PromptArtifactVersion` — id, artifact_id, version, content, content_hash, expected_variables, required_variables, status
- `PromptOperation` — id, key, label, description, phase, consumer_symbol, is_conditional, retry_policy, fallback_policy, rollout_mode
- `PromptComposition` — id, operation_id, version, status
- `PromptCompositionItem` — id, composition_id, artifact_id, position, required, separator, condition_type, condition_field, condition_operator, condition_value, runtime_slot
- `PromptExecutionReference` — execution_id, operation_key, composition_id, composition_version, artifact_versions, template_hash, resolved_hash, provider, model, resolved_at, resolution_source, error, rollout_mode, used_fallback, placeholders

**Extensões propostas** (novos campos e tabelas):

```python
# Campos adicionais em prompt_artifacts (via migration v3)
ALTER TABLE prompt_artifacts ADD COLUMN purpose TEXT NOT NULL DEFAULT '';
ALTER TABLE prompt_artifacts ADD COLUMN execution_moment TEXT NOT NULL DEFAULT '';
ALTER TABLE prompt_artifacts ADD COLUMN trigger_condition TEXT NOT NULL DEFAULT '';
ALTER TABLE prompt_artifacts ADD COLUMN existence_reason TEXT NOT NULL DEFAULT '';
ALTER TABLE prompt_artifacts ADD COLUMN editability TEXT NOT NULL DEFAULT 'UNKNOWN';
ALTER TABLE prompt_artifacts ADD COLUMN editability_reason TEXT NOT NULL DEFAULT '';

# Nova tabela para cache de payloads resolvidos (sanitizados)
CREATE TABLE prompt_resolved_snapshots (
    id INTEGER PRIMARY KEY,
    execution_id TEXT NOT NULL UNIQUE,
    operation_key TEXT NOT NULL,
    sanitized_payload TEXT NOT NULL,  -- JSON: array de {role, content_truncated}
    variables_snapshot TEXT NOT NULL,  -- JSON: {var_name: "redacted:var_name"}
    created_at TEXT NOT NULL,
    FOREIGN KEY (execution_id) REFERENCES prompt_execution_references(execution_id)
);
```

### Classificação de editabilidade (enum)

```python
class Editability(StrEnum):
    EDITABLE_CONTENT = "EDITABLE_CONTENT"              # seguro editar
    EDITABLE_WITH_VALIDATION = "EDITABLE_WITH_VALIDATION"  # validar placeholders/contrato
    READ_ONLY_CODE = "READ_ONLY_CODE"                  # embedded em Python
    MIGRATION_REQUIRED = "MIGRATION_REQUIRED"          # precisa ser extraído antes
    GENERATED_RUNTIME = "GENERATED_RUNTIME"            # só visualização
    REFERENCE_ONLY = "REFERENCE_ONLY"                  # não participa do runtime
    LEGACY = "LEGACY"                                  # fora de uso
    UNKNOWN = "UNKNOWN"                                # não classificado
```

### Endpoints de API (novos, a serem adicionados em `gui/server.py`)

Base path: `/api/prompt-registry`

| Método | Rota | Descrição | Autenticação |
|--------|------|-----------|-------------|
| `GET` | `/api/prompt-registry/catalog` | Catálogo completo (operações, artefatos, diagnósticos) | Local apenas |
| `GET` | `/api/prompt-registry/operations` | Lista de operações com detalhes de composição | Local |
| `GET` | `/api/prompt-registry/operations/<key>` | Detalhe de operação + composição + execuções | Local |
| `GET` | `/api/prompt-registry/artifacts` | Lista de artefatos com status, tipo, editabilidade | Local |
| `GET` | `/api/prompt-registry/artifacts/<key>` | Detalhe do artefato + versões + conteúdo ativo | Local |
| `GET` | `/api/prompt-registry/artifacts/<key>/versions` | Histórico de versões | Local |
| `GET` | `/api/prompt-registry/artifacts/<key>/versions/<v>` | Conteúdo de versão específica | Local |
| `PUT` | `/api/prompt-registry/artifacts/<key>` | Atualizar conteúdo (cria nova versão, valida) | Local |
| `POST` | `/api/prompt-registry/artifacts/<key>/activate` | Ativar uma versão específica | Local |
| `POST` | `/api/prompt-registry/artifacts/<key>/rollback` | Rollback para versão anterior | Local |
| `POST` | `/api/prompt-registry/preview` | Preview de resolução (sem registrar execução) | Local |
| `GET` | `/api/prompt-registry/diagnostics` | Diagnósticos de integridade | Local |
| `GET` | `/api/prompt-registry/executions` | Lista de execuções recentes | Local |
| `GET` | `/api/prompt-registry/phases` | Lista de fases com metadados (ordem, operações, status) | Local |

### Contrato do frontend (TypeScript, no mesmo estilo de `pe-types.ts`)

```typescript
// Prompt Observatory types

export interface PhaseInfo {
  id: string;
  label: string;
  shortLabel: string;
  category: "interview" | "generation" | "editorial" | "segmentation" | "evaluation" | "export";
  order: number;
  operations: OperationSummary[];
  artifactCount: number;
  fragmentCount: number;
  isConditional: boolean;
  isAlternative: boolean;
  status: "active" | "inactive" | "conditional" | "error";
}

export interface OperationSummary {
  key: string;
  label: string;
  phase: string;
  consumerSymbol: string;
  provider: ProviderId;
  model: string;
  isConditional: boolean;
  rolloutMode: string;
  compositionVersion: number | null;
  artifactCount: number;
  executionCount: number;
  lastExecutedAt: string | null;
  error: string | null;
}

export interface ArtifactSummary {
  key: string;
  title: string;
  type: ArtifactType;
  status: ArtifactStatus;
  sourceOrigin: string;
  legacySourcePath: string | null;
  activeVersion: number | null;
  contentHash: string | null;
  variableCount: number;
  operationCount: number;
  editability: Editability;
  editabilityReason: string;
  purpose: string;
  executionMoment: string;
}

export interface ArtifactDetail extends ArtifactSummary {
  description: string;
  content: string;
  expectedVariables: string[];
  requiredVariables: string[];
  versions: VersionSummary[];
  usedInOperations: string[];
  usedInCompositions: CompositionReference[];
}

export interface CompositionVisualization {
  operationKey: string;
  items: CompositionItemVisual[];
  templateContent: string | null;
  resolvedExample: string | null;
}

export interface CompositionItemVisual {
  position: number;
  artifactKey: string;
  artifactTitle: string;
  artifactType: string;
  condition: ConditionInfo | null;
  runtimeSlot: string | null;
  separator: string;
  required: boolean;
}

export interface DiagnosticInfo {
  code: string;
  severity: "error" | "warning" | "info";
  message: string;
  operation: string | null;
  artifact: string | null;
}

export type ArtifactType =
  | "PROMPT_TEMPLATE" | "BASE" | "PERSONA" | "FORMAT_RULES"
  | "POLICY" | "OUTPUT_CONTRACT" | "EDITORIAL" | "SEGMENTATION"
  | "EVALUATION" | "RETRY_APPENDIX" | "REFERENCE" | "LEGACY";

export type ArtifactStatus = "DRAFT" | "ACTIVE" | "ARCHIVED" | "REFERENCE_ONLY" | "LEGACY" | "ORPHAN";

export type Editability =
  | "EDITABLE_CONTENT" | "EDITABLE_WITH_VALIDATION" | "READ_ONLY_CODE"
  | "MIGRATION_REQUIRED" | "GENERATED_RUNTIME" | "REFERENCE_ONLY"
  | "LEGACY" | "UNKNOWN";
```

### Instrumentação de runtime (opcional, fase futura)

O `AgentWrapper._run_subprocess()` já loga `llm_request` e `llm_response` via `SessionLogger`. O `PromptResolver.resolve()` já registra `prompt_execution_references` com template_hash, resolved_hash, artifact_versions, placeholders.

**Extensão futura**: adicionar um hook opcional em `AgentWrapper.run()` que capture o payload final (prompt resolvido) e o registre na tabela `prompt_resolved_snapshots` com sanitização automática (substituir valores de variáveis por `redacted:var_name`).

---

## 7. Arquivos afetados

### Arquivos existentes a modificar

| Arquivo | Modificação |
|---------|-------------|
| `src/gui/server.py` | Adicionar 12 rotas `/api/prompt-registry/*` delegando para `PromptRegistryApi` + novo endpoint `PUT /api/prompt-registry/artifacts/<key>` |
| `src/content_engine/prompt_registry/api.py` | Adicionar métodos: `update_artifact()`, `activate_version()`, `rollback_version()`, `list_phases()`, `get_artifact_detail()` |
| `src/content_engine/prompt_registry/repository.py` | Adicionar `update_artifact_description()`, `get_artifact_usage()` (quais operações usam este artefato) |
| `src/content_engine/prompt_registry/models.py` | Adicionar `Editability` enum |
| `frontend/src/lib/pe-types.ts` | Adicionar tipos `PhaseInfo`, `OperationSummary`, `ArtifactSummary`, `ArtifactDetail`, `CompositionVisualization`, `DiagnosticInfo`, `Editability` |
| `frontend/src/lib/pe-api.ts` | Adicionar funções `fetchPromptCatalog()`, `fetchArtifact()`, `updateArtifact()`, `fetchComposition()`, `fetchDiagnostics()` |
| `frontend/src/components/workstation/Workstation.tsx` | Adicionar atalho `Cmd+Shift+P` + rota condicional para `PromptObservatory` |
| `frontend/src/components/workstation/ContextBar.tsx` | Adicionar botão/ícone de acesso ao Observatory |

### Novos arquivos a criar

| Arquivo | Responsabilidade |
|---------|-----------------|
| `frontend/src/components/workstation/prompt-observatory/PromptObservatory.tsx` | Container principal da tela |
| `frontend/src/components/workstation/prompt-observatory/ObservatoryHeader.tsx` | Cabeçalho com busca, filtros, resumo |
| `frontend/src/components/workstation/prompt-observatory/PhaseStepper.tsx` | Stepper horizontal com scroll snap |
| `frontend/src/components/workstation/prompt-observatory/PhaseStep.tsx` | Step individual do stepper |
| `frontend/src/components/workstation/prompt-observatory/OperationList.tsx` | Lista de operações da fase selecionada |
| `frontend/src/components/workstation/prompt-observatory/ArtifactList.tsx` | Lista de artefatos/fragmentos |
| `frontend/src/components/workstation/prompt-observatory/ArtifactCard.tsx` | Card de artefato na lista |
| `frontend/src/components/workstation/prompt-observatory/CompositionViewer.tsx` | Visualizador de composição (blocos conectados) |
| `frontend/src/components/workstation/prompt-observatory/CompositionBlock.tsx` | Bloco individual na visualização de composição |
| `frontend/src/components/workstation/prompt-observatory/ArtifactEditor.tsx` | Painel lateral de edição (slide-over) |
| `frontend/src/components/workstation/prompt-observatory/EditorToolbar.tsx` | Toolbar do editor (salvar, desfazer, diff, validar) |
| `frontend/src/components/workstation/prompt-observatory/PlaceholderHighlighter.tsx` | Highlight de placeholders no conteúdo |
| `frontend/src/components/workstation/prompt-observatory/DiagnosticsPanel.tsx` | Painel de diagnósticos (problemas, warnings) |
| `frontend/src/components/workstation/prompt-observatory/ExecutionTimeline.tsx` | Timeline de execuções recentes |
| `frontend/src/components/workstation/prompt-observatory/types.ts` | Tipos TypeScript locais |
| `frontend/src/components/workstation/prompt-observatory/hooks.ts` | Hooks de dados (usePhaseData, useArtifactData, etc.) |
| `frontend/src/components/workstation/prompt-observatory/utils.ts` | Utilitários (format, sort, filter, highlight placeholders) |

### Responsabilidades por arquivo

**`PromptObservatory.tsx`**:
- Gerencia estado: fase selecionada, operação selecionada, artefato selecionado
- Controla abertura/fechamento do editor
- Orquestra chamadas de API
- Layout grid responsivo

**`PhaseStepper.tsx`**:
- Renderiza steps com conectores visuais
- Scroll horizontal com snap
- Indicação de fase ativa com destaque glow
- Badges condicionais e de erro

**`CompositionViewer.tsx`**:
- Recebe `CompositionVisualization`
- Renderiza blocos em ordem com linhas de conexão animadas
- Tooltips com detalhes de cada item
- Diferenciação visual: slots vs inline, condicional vs obrigatório

**`ArtifactEditor.tsx`**:
- Painel lateral com animação de entrada
- Modo leitura e modo edição
- Syntax highlighting de placeholders (`{{var}}` em cor flux)
- Validação client-side: detectar placeholders removidos
- Confirmação antes de salvar
- Indicador de dirty state

### Itens não confirmados (dependem de confirmação)

- Se a rota `Cmd+Shift+P` conflita com algum atalho existente
- Se o `DevDrawer` (aberto via `Cmd+K`) deve coexistir com o Observatory ou ser substituído
- Se a instrumentação de runtime com snapshots sanitizados deve entrar no MVP ou em fase posterior
- Se o campo `editability` deve ser populado automaticamente (via heurística) ou manualmente (via migration de dados)

---

## 8. Plano incremental

### Etapa 1: Endpoints de leitura no backend
- **Objetivo**: Expor os dados do registry via API REST
- **Dependências**: Nenhuma (o código já existe em `api.py`)
- **Arquivos**: `src/gui/server.py` (adicionar rotas), `src/content_engine/prompt_registry/api.py` (estender)
- **Riscos**: Baixo. API já tem base implementada.
- **Critério**: `curl localhost:8765/api/prompt-registry/catalog` retorna JSON com operações e artefatos

### Etapa 2: Tipos e API client no frontend
- **Objetivo**: Tipar o contrato e implementar fetch functions
- **Dependências**: Etapa 1
- **Arquivos**: `frontend/src/lib/pe-types.ts`, `frontend/src/lib/pe-api.ts`
- **Riscos**: Baixo. Seguir padrão existente.
- **Critério**: Tipos compilam sem erro, funções fetch retornam dados tipados

### Etapa 3: Tela base e stepper (read-only)
- **Objetivo**: Layout principal com stepper funcional e dados carregados
- **Dependências**: Etapa 2
- **Arquivos**: `PromptObservatory.tsx`, `ObservatoryHeader.tsx`, `PhaseStepper.tsx`, `PhaseStep.tsx`
- **Riscos**: Performance com 11+ steps no stepper (mitigação: virtualização ou `content-visibility: auto`)
- **Critério**: Stepper mostra 11 fases, ao clicar carrega operações da fase

### Etapa 4: Painéis de operação e artefatos
- **Objetivo**: Listar operações e artefatos com detalhes ao selecionar
- **Dependências**: Etapa 3
- **Arquivos**: `OperationList.tsx`, `ArtifactList.tsx`, `ArtifactCard.tsx`
- **Riscos**: Muitos artefatos em algumas fases (post_generate tem 13). Mitigação: scroll virtualizado, busca local, agrupamento por tipo.
- **Critério**: Ao selecionar fase, mostra operações à esquerda e artefatos à direita

### Etapa 5: Visualizador de composição
- **Objetivo**: Mostrar graficamente como artefatos se combinam em composições
- **Dependências**: Etapa 4
- **Arquivos**: `CompositionViewer.tsx`, `CompositionBlock.tsx`
- **Riscos**: Complexidade visual para composições com muitas condições (ex: post_generate tem 13 itens com 4 variantes condicionais). Mitigação: mostrar apenas a versão "default" (content_type=post), com toggle para outros content_types.
- **Critério**: Selecionar post_generate mostra fluxo base → persona → rules → policy → contract com animação

### Etapa 6: Editor de artefatos
- **Objetivo**: Permitir edição de conteúdo com validação e versionamento
- **Dependências**: Etapa 5 + endpoint PUT no backend
- **Arquivos**: `ArtifactEditor.tsx`, `EditorToolbar.tsx`, `PlaceholderHighlighter.tsx`
- **Riscos**: 
  - Alterar artefatos compostos pode quebrar múltiplas operações (mitigação: aviso contextual)
  - Remover placeholders obrigatórios (mitigação: validação client-side + server-side)
  - Concorrência entre múltiplos editores (mitigação: optimistic locking via version number)
- **Critério**: Editar conteúdo de um artefato → salvar → nova versão criada → versão ativada

### Etapa 7: Preview de resolução
- **Objetivo**: Mostrar como um prompt ficaria resolvido com contexto de exemplo
- **Dependências**: Etapa 6
- **Arquivos**: endpoint `POST /api/prompt-registry/preview` (já existe em `api.py`), componente de preview no frontend
- **Riscos**: Dados sensíveis no preview (mitigação: sanitização automática já implementada em `api.py:_sanitize()`)
- **Critério**: Botão "Preview" mostra prompt resolvido com placeholders substituídos por valores de exemplo

### Etapa 8: Diagnósticos
- **Objetivo**: Exibir problemas de integridade detectados
- **Dependências**: Etapa 1 (diagnósticos já existem em `diagnostics.py`)
- **Arquivos**: `DiagnosticsPanel.tsx`
- **Riscos**: Baixo. Diagnósticos já implementados.
- **Critério**: Painel mostra problemas com severidade e ações sugeridas

### Etapa 9: Versionamento e rollback
- **Objetivo**: Histórico de versões com diff visual e rollback
- **Dependências**: Etapa 6
- **Arquivos**: endpoints GET/POST no backend, componente de histórico no editor
- **Riscos**: Rollback para versão quebrada (mitigação: preview antes de confirmar)
- **Critério**: Selecionar versão anterior → preview → confirmar rollback → versão reativada

### Etapa 10: Acabamento visual e responsividade
- **Objetivo**: Refinar animações, microinterações, responsividade e acessibilidade
- **Dependências**: Etapas 3-9
- **Arquivos**: Todos os componentes do observatory
- **Riscos**: Performance de animações em dispositivos lentos (mitigação: `prefers-reduced-motion`)
- **Critério**: Lighthouse audit ≥90, navegação por teclado completa, responsivo ≥1024px

### Etapa 11: Testes
- **Objetivo**: Cobertura de testes unitários, integração e E2E
- **Dependências**: Etapa 10
- **Arquivos**: Novos arquivos em `tests/` e `frontend/e2e/`
- **Riscos**: Baixo
- **Critério**: Testes passam, cobertura ≥80% nos novos módulos

### Etapa 12: Instrumentação runtime (opcional, pós-MVP)
- **Objetivo**: Capturar snapshots sanitizados de payloads reais
- **Dependências**: Etapa 7
- **Arquivos**: `agent_wrapper.py` (hook), nova tabela `prompt_resolved_snapshots`
- **Riscos**: Exposição de dados sensíveis (mitigação: sanitização automática)
- **Critério**: Payloads reais aparecem na timeline de execuções com dados sanitizados

---

## 9. Estratégia de testes

### Testes unitários (backend)

| Módulo | O que testar |
|--------|-------------|
| `prompt_registry/api.py` | Novos métodos: `update_artifact()`, `activate_version()`, `rollback_version()`, `list_phases()`, `get_artifact_detail()` |
| `prompt_registry/repository.py` | `update_artifact_description()`, `get_artifact_usage()` |
| `gui/server.py` | Novas rotas `/api/prompt-registry/*` — teste com `http.client` ou `pytest` + `ThreadingHTTPServer` |

### Testes unitários (frontend)

| Componente | O que testar |
|-----------|-------------|
| `PhaseStepper` | Renderiza N steps, seleção por clique, scroll horizontal |
| `ArtifactCard` | Renderiza título, tipo, status, editabilidade; clique seleciona |
| `CompositionViewer` | Renderiza blocos em ordem, mostra condições, slots |
| `ArtifactEditor` | Modo leitura/edição, dirty state, validação de placeholders |
| `PlaceholderHighlighter` | Destaca `{{var}}` com a classe correta |
| `DiagnosticsPanel` | Agrupa por severidade, mostra mensagens |

### Testes de integração

- Fluxo completo: carregar catalog → selecionar fase → listar operações → selecionar artefato → abrir editor → editar → salvar → verificar nova versão
- Preview de resolução: enviar contexto → receber prompt resolvido → verificar sanitização
- Rollback: criar versão → ativar → rollback → verificar versão ativa restaurada

### Testes E2E (Playwright)

| Cenário | Descrição |
|---------|-----------|
| Navegação completa | Abrir Observatory → percorrer todas as fases → verificar dados carregados |
| Edição segura | Editar artefato → salvar → verificar sucesso → editar com placeholder inválido → verificar erro |
| Composição visual | Selecionar post_generate → verificar visualização com 13 blocos conectados |
| Rollback | Criar versão → ativar → rollback → verificar conteúdo restaurado |
| Diagnósticos | Verificar painel de diagnósticos → confirmar que problemas são exibidos |
| Responsividade | Redimensionar viewport → verificar layout adaptativo |
| Acessibilidade | Navegar por teclado → verificar focus rings → verificar ARIA labels |

### Dados de teste

Os `_SEEDS` em `importer.py` já fornecem dados completos. Usar `import_legacy_prompts()` para popular o banco de teste. Para testes de update, criar artefatos adicionais em `setUp`.

---

## 10. Riscos e decisões

### Decisões técnicas

| Decisão | Alternativas consideradas | Justificativa |
|---------|--------------------------|---------------|
| Estender `PromptRegistryApi` existente em vez de criar nova API | Criar API separada, usar FastAPI/Flask | A API existente já cobre ~70% das necessidades; estender é mais seguro e rápido |
| Editor como slide-over | Modal, tela dedicada, split view | Slide-over mantém contexto visível e é padrão já usado no `DevDrawer` |
| SQLite como fonte única (manter) | Migrar para PostgreSQL, arquivos YAML | SQLite é suficiente para single-user local; já tem backup, WAL mode, migrations |
| Migração v3 para novos campos em `prompt_artifacts` | Nova tabela, metadata separado | Campos adicionais têm cardinalidade 1:1 com artefato; ALTER TABLE é mais simples |
| Classificação de editabilidade manual inicialmente | Heurística automática, ML | Heurística seria frágil; classificação manual + review é mais confiável para MVP |

### Riscos de regressão

| Risco | Impacto | Mitigação |
|-------|---------|-----------|
| Alteração acidental de artefatos críticos (base, persona) | Geração de conteúdo degradada | Validação de placeholders antes de salvar; preview de composição; rollback imediato |
| Concorrência entre editor e runtime | Prompt resolvido com versão errada | O resolver sempre carrega a versão `ACTIVE` do banco; transações SQLite com `BEGIN IMMEDIATE` |
| Placeholder removido sem querer | Erro em runtime na renderização | Validação client-side com diff de placeholders; validação server-side no `create_version()` |
| Registro de dados sensíveis em snapshots | Vazamento de informações | Sanitização automática via `_sanitize()`; snapshots usam `redacted:var_name` |
| Performance com 38 artefatos e 13 operações | Tela lenta | Dados já estão em cache no SQLite; API retorna <10KB; frontend usa React.memo e virtualização |

### Riscos específicos mencionados no briefing

| Risco | Status no projeto | Tratamento |
|-------|-----------------|------------|
| Tentar editar código Python pela interface | **Não se aplica**: prompts estão 100% no SQLite | N/A |
| Catalogar strings irrelevantes | **Não se aplica**: catálogo é o próprio registry, não scan de código | N/A |
| Não detectar prompts dinâmicos | **Baixo risco**: o único prompt "dinâmico" é a concatenação condicional, já modelada no registry | Visualizador de composição mostra condições |
| Divergir do payload real | **Baixo risco**: o resolver é o único ponto de construção de prompts; a instrumentação futura confirmará | Preview + snapshots |
| Alterar prompts sem invalidar caches | **Baixo risco**: não há cache de prompts; cada chamada lê do SQLite | N/A |
| Migrar conteúdo embedded sem testes | **Não se aplica**: não há conteúdo embedded para migrar | N/A |

---

## 11. Critérios de aceite

### MVP (Etapas 1-7)

1. **API de leitura funcionando**: `GET /api/prompt-registry/catalog` retorna JSON completo com operações, artefatos, composições, diagnósticos
2. **Stepper funcional**: 11 fases renderizadas, navegação por clique e teclado, indicador de fase ativa
3. **Operações visíveis**: Ao selecionar fase, painel esquerdo lista operações LLM com provider, modelo, condição, status
4. **Artefatos visíveis**: Painel direito lista artefatos com tipo, status, editabilidade, número de variáveis
5. **Composição visual**: Para operações com composição (post_generate, editorial_compose, etc.), visualizador mostra ordem dos fragmentos com condições
6. **Editor funcional**: Abrir artefato → editar conteúdo → salvar → nova versão criada e ativada
7. **Validação de placeholders**: Editor alerta se placeholder obrigatório for removido
8. **Preview de resolução**: Botão "Preview" mostra como o prompt ficaria resolvido com contexto de exemplo sanitizado
9. **Rollback**: Selecionar versão anterior → preview → confirmar → versão restaurada
10. **Diagnósticos**: Painel mostra problemas (se houver) com severidade e ação sugerida
11. **Acesso por atalho**: `Cmd+Shift+P` (ou equivalente) abre o Observatory
12. **Sem regressão**: Todos os testes existentes passam; geração de conteúdo funciona normalmente

### Pós-MVP (Etapas 8-12)

1. **Acabamento visual**: Animações de transição, glow nos conectores do stepper, microinterações
2. **Responsividade**: Layout funcional em 1024px, 1280px, 1440px+
3. **Acessibilidade**: Navegação completa por teclado, ARIA labels, alto contraste
4. **Execuções recentes**: Timeline mostra últimas N execuções com hashes e status
5. **Snapshots sanitizados**: Payloads reais capturados com dados sanitizados
6. **Cobertura de testes**: ≥80% nos novos módulos
7. **Documentação**: README atualizado com instruções de uso do Observatory

---

## 12. MVP e evolução

### O que precisa existir no MVP

1. **Tela de observabilidade somente leitura**: Stepper com fases, painéis de operações e artefatos, visualizador de composição
2. **Edição segura de artefatos**: Editor com validação de placeholders, criação de versão, rollback
3. **Preview de resolução**: Mostrar prompt resolvido com contexto sanitizado
4. **Diagnósticos básicos**: Problemas de integridade (composição sem artefatos, artefatos sem versão, orphans)
5. **Acesso integrado**: Botão/atalho no ContextBar, sem quebrar o fluxo existente

### O que pode entrar depois

1. **Instrumentação runtime com snapshots**: Capturar payloads reais sanitizados
2. **Timeline de execuções**: Visualização histórica de resoluções
3. **Editor avançado**: Diff visual entre versões, syntax highlighting mais sofisticado
4. **Simulação de caminhos condicionais**: "O que acontece se content_type=article?"
5. **Exportação de configuração**: Exportar/importar versões de artefatos entre ambientes
6. **Métricas de uso**: Quais artefatos são mais modificados, quais operações mais falham
7. **Alertas proativos**: Notificar se uma versão de artefato está há X dias sem ser ativada

### Quais prompts podem ser editados inicialmente (MVP)

**Todos os 33 artefatos ativos** são `EDITABLE_CONTENT` ou `EDITABLE_WITH_VALIDATION`. Nenhum está embedded em código Python.

A classificação inicial será:
- `EDITABLE_CONTENT` (default para artefatos sem restrições): ~25 artefatos
- `EDITABLE_WITH_VALIDATION` (artefatos com placeholders ou contratos): ~8 artefatos (`policy.anti_ia`, `contract.slidemark`, bases, personas)

### Quais devem permanecer somente leitura inicialmente

- `router.suggest_content_type` (ORPHAN) — `REFERENCE_ONLY`
- Artefatos LEGACY (4) — `LEGACY`
- Artefatos REFERENCE_ONLY (3: interview.explore, interview.evaluate_authorship, interview.deepen) — `REFERENCE_ONLY`

### Quais migrações devem ser evitadas neste momento

1. **Não migrar conteúdo do SQLite para outro formato** — o SQLite é adequado
2. **Não extrair strings de código Python** — não há conteúdo de prompt em código
3. **Não adicionar framework web** — o `ThreadingHTTPServer` + stdlib é suficiente
4. **Não substituir o build system do frontend** — Vite + Tailwind 4 funciona bem
5. **Não reestruturar o design system** — os tokens existentes são adequados e consistentes
