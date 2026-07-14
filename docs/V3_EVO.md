# Planejamento Técnico: Storyboard Narrativo, Rascunhador de Blocos e Composição Editorial

## 1. Resumo executivo

A evolução deve ser implementada de forma incremental no código, mas o resultado operacional alvo é uma migração única da V3, sem manter o fluxo antigo de escrita em produção.

O objetivo é introduzir Storyboard Narrativo, Rascunhador de Blocos e Composição Editorial no meio do pipeline atual, compatibilizando os artefatos já esperados pelas etapas posteriores e removendo o antigo caminho de geração integral ao final do rollout técnico.

Diretriz de escopo: a evolução da V3 não exige evolução da TUI como produto. `src/tui/app.py` permanece apenas como ponto técnico já existente no código e pode receber adaptações mínimas de compatibilidade quando inevitáveis, mas o plano não depende de expandir, polir ou sustentar uma nova experiência TUI.

Diretriz de execução: durante a evolução do sistema, nenhum teste automatizado deve ser feito a priori como pré-condição para avançar fases intermediárias. A prioridade é concluir a convergência arquitetural e funcional; a automação de testes fica concentrada na etapa de estabilização/hardening.

Ponto de convergência: depois da **Composição Editorial**, o sistema deve preencher os mesmos artefatos que a geração atual já produz: `TuiSessionState.conteudo_gerado` e `TuiSessionState.conteudo_json`. A partir daí, `PostEngineApp.action_continue_segmentacao()`, `_segmentar()`, `action_evaluate()`, ajustes e exportação continuam operando sem conhecer Storyboard/Rascunhos.

## 2. Estado atual do Post Engine

Comportamento confirmado no código:

- Entrada principal TUI: `src/tui/app.py`, classe `PostEngineApp`.
- Entrada GUI React/HTTP: `src/gui/server.py`, classe `GuiController`, que reutiliza `PostEngineApp`.
- Fluxo de fases atual em `src/tui/app.py`: `PHASE_ENTRADA`, `PHASE_ENTREVISTA`, `PHASE_BRIEFING`, `PHASE_PROMPT`, `PHASE_EXECUCAO`, `PHASE_SEGMENTACAO`, `PHASE_AVALIACAO`, `PHASE_EXPORTACAO`.
- Briefing batch: `PostEngineApp._finalizar_entrevista_batch()` cria `state.briefing_autoral` via `content_engine.briefing.montar_briefing_do_interview_pack()`.
- Briefing legado: `PostEngineApp._montar_briefing_quando_aprovado()` cria `BriefingAutoral` via `content_engine.briefing.montar_briefing_autoral()`.
- Geração atual: `PostEngineApp.action_continue_phase3()` chama `_garantir_prompt_para_fase4()`, que chama `build_generation_prompt()`. Depois `action_run()` chama `_executar_agente()`, que usa `ContentGenerator.generate()`.
- Segmentação: `action_continue_segmentacao()` e `action_segment()` chamam `_segmentar(self.state.conteudo_gerado)`.
- Avaliação: `action_evaluate()` chama `_conteudo_final()` e `PostEvaluator.avaliar()`.
- Ajuste: `action_rewrite_segment()` usa `SegmentAdjuster.ajustar()` e `action_apply_segment_adjustment()` substitui o texto do segmento.
- Exportação: `action_export_output()` usa `_conteudo_final()` e `exportar_conteudo()`.

Fluxo real atual:

```text
Entrada inicial
-> Entrevista autoral
-> Briefing autoral
-> Prompt renderizado
-> Execução LLM
-> Conteúdo integral em conteudo_gerado/conteudo_json
-> Segmentação editável
-> Avaliação
-> Ajuste de segmentos
-> Exportação
```

## 3. Arquitetura atual relevante

- Estado persistido: `TuiSessionState` em `src/content_engine/schemas.py`.
- Persistência manual: `src/content_engine/persistence.py`, funções `_state_to_dict()` e `_dict_to_state()`.
- Não há banco relacional, migrations, fila externa, Celery, Redis ou workers persistentes. Persistência é JSON em `.data/sessions/current-session.json`.
- Prompts são arquivos Markdown carregados por chave em `prompt_loader.PROMPT_PATHS` e renderizados por `template_renderer.render_template()`.
- Chamadas LLM principais usam `AgentWrapper.run()` em `src/content_engine/agent_wrapper.py`, com providers `codex`, `opencode`, `cursor`.
- Modelos/providers são configurados por operação em `src/content_engine/llm_config.py`, hoje com `questions`, `answer_evaluate`, `content_generate`, `segment`, `adjust_segment`, `post_evaluate`, `slidemark_export`.
- Observabilidade atual: `SessionLogger.write()` registra JSONL; `PostEngineApp._log_event()` registra `llm_request` e `llm_response`.
- Frontend React: `frontend/src/lib/pe-store.tsx` consome `/api/session` e dispara `/api/action`; fases são mapeadas em `frontend/src/lib/mappers/phase.ts`.

Inferência arquitetural:

- O núcleo real do pipeline não é um orquestrador genérico de etapas, mas um conjunto de actions em `PostEngineApp` operando sobre `TuiSessionState`.
- A compatibilidade deve ser resolvida preservando os contratos de saída e fazendo o novo fluxo convergir para `conteudo_gerado`/`conteudo_json`.

## 4. Gaps entre o sistema atual e o novo fluxo

Confirmado:

- O sistema só representa uma geração integral por `conteudo_gerado`; não há artefato intermediário narrativo.
- `GenerationPromptInput` não aceita storyboard, blocos, abordagem, persona editorial ou seleções.
- `ContentGenerator.generate()` executa uma única chamada de conteúdo, não N blocos independentes.
- `TuiSessionState` não possui estado persistido para storyboard, opções por bloco, seleção por bloco, composição ou invalidação.
- O frontend só possui estágios `briefing`, `prompt`, `execution`, `segmentation`; não há UX para edição de fluxo narrativo ou comparação de rascunhos.
- Não há retry granular por bloco/opção. Erros de geração integral ficam em `state.error`, `returncode`, `parse_error` ou `conteudo_json`.

Recomendação:

- Não reescrever o pipeline.
- Adicionar uma camada editorial antes do ponto de convergência atual.
- Remover a dependência do caminho antigo de geração integral quando a V3 estiver concluída.
- Não tratar evolução da TUI como frente de produto da V3; qualquer ajuste nela deve ser estritamente de compatibilidade técnica.

## 5. Estratégia arquitetural proposta

Substituir o miolo do pipeline atual por um fluxo editorial estruturado:

```text
Entrevista
-> Briefing
-> Storyboard Narrativo
-> Rascunhador de Blocos
-> Composição Editorial
-> conteudo_gerado/conteudo_json
-> Segmentação atual
-> Avaliação atual
-> Ajuste atual
-> Exportação atual
```

Implementar no backend:

- Novo campo persistido `editorial_flow`, contendo storyboard, drafts, seleções e composição.
- Novo módulo recomendado: `src/content_engine/editorial_flow.py` para tipos, normalização, fingerprints e invalidação.
- Novo módulo recomendado: `src/content_engine/editorial_generation.py` com serviços `StoryboardGenerator`, `BlockDraftGenerator`, `EditorialComposer`.
- Novos prompts em `prompts/editorial/`.
- Novas actions em `GuiController._dispatch()` e `PostEngineApp`.

Diagrama textual:

```text
BriefingAutoral / InterviewPack
        |
        v
StoryboardGenerator
        |
        v
editorial_flow.storyboard.blocks[]
        |
        v
BlockDraftGenerator
        |
        v
editorial_flow.drafts.by_block[block_id].options[]
        |
        v
Seleção do usuário
        |
        v
EditorialComposer
        |
        v
state.conteudo_gerado + state.conteudo_json
        |
        v
Segmenter / PostEvaluator / SegmentAdjuster / Exporter atuais
```

## 6. Estratégia de compatibilidade

- Publicações e sessões antigas continuam válidas como dados históricos, mas devem ser migradas para o novo shape de estado ao serem carregadas.
- O caminho antigo de geração integral não será mantido como modo de operação da V3 depois da entrega final.
- Endpoints existentes não mudam de semântica: `/api/session`, `/api/action`, `/api/llm-config`, `PATCH /api/session`.
- O novo fluxo converge ao preencher `state.conteudo_gerado` e `state.conteudo_json` com o mesmo contrato consumido hoje por segmentação, avaliação e exportação.
- Segmentação continua recebendo string integral por `_segmentar(conteudo)`.
- Avaliação e ajustes continuam usando `_conteudo_final()`.
- Para `short_carousel` e `long_slide`, a composição deve poder produzir `conteudo_json.slidemark` e `sugestoesImagem`, preservando o caminho especial de `segmentar_slidemark()`.

Compatibilização exigida:

- Compatibilidade de dados persistidos: sessões antigas devem carregar sem quebra.
- Compatibilidade de contratos downstream: segmentação, avaliação, ajuste e exportação continuam recebendo os mesmos artefatos finais.
- Compatibilidade de frontend: a navegação passa a refletir o novo pipeline, sem necessidade de preservar a UX antiga como alternativa funcional.
- Compatibilidade de TUI: manter apenas o nível mínimo necessário para não romper integrações internas já acopladas a `PostEngineApp`, sem expandir a TUI como interface alvo da V3.

Ponto de convergência:

```text
Composição Editorial concluída
-> state.conteudo_gerado preenchido
-> state.conteudo_json preenchido
-> state.segmentos limpo
-> state.avaliacao_post limpa
-> fluxo atual retomado em Segmentação
```

## 7. Modelo de domínio e persistência

Persistir em `TuiSessionState`:

- `editorial_flow: dict[str, Any] = field(default_factory=dict)`.

Estrutura conceitual mínima:

```json
{
  "schema_version": "1.0",
  "briefing_fingerprint": "...",
  "storyboard": {
    "version": 1,
    "status": "available",
    "blocks": [
      {
        "id": "blk_...",
        "order": 1,
        "role": "Gancho",
        "focus": "...",
        "revision": 1
      }
    ]
  },
  "drafts": {
    "storyboard_version": 1,
    "by_block": {
      "blk_...": {
        "status": "available",
        "options": [
          {
            "id": "opt_...",
            "approach": {
              "title": "...",
              "description": "..."
            },
            "persona_id": "observador",
            "persona_name": "O Observador",
            "content": "...",
            "status": "available",
            "obsolete": false
          }
        ],
        "selected_option_id": "opt_..."
      }
    }
  },
  "composition": {
    "status": "available",
    "selection_fingerprint": "...",
    "conteudo": "...",
    "conteudo_json": {}
  }
}
```

Estado persistido:

- Storyboard atual, versão e blocos.
- Rascunhos por bloco, abordagem, persona, conteúdo, modelo/provider, prompt version e erro.
- Seleção por bloco.
- Composição final e fingerprint das seleções usadas.

Estado derivado, não persistir como enum separado:

- `storyboard_available`
- `drafts_partial`
- `drafts_available`
- `selection_incomplete`
- `selection_complete`
- `composition_stale`

## 8. Storyboard Narrativo

Backend:

- Serviço `StoryboardGenerator.gerar(input)` recebe briefing, `interview_pack`, tema, plataforma, objetivo, tipo e personalidade.
- Prompt `editorial.storyboard` retorna apenas blocos com `role` e `focus`; IDs e `order` devem ser atribuídos pela aplicação.
- Parser deve rejeitar bloco sem papel/foco ou foco com parágrafos longos.
- Ações:
  - `generate_storyboard`
  - `update_storyboard`
  - `clear_storyboard`, opcional para reset editorial.

Frontend:

- Novo estágio `storyboard`.
- Renderização em fluxo ordenado.
- Edição inline de `role` e `focus`.
- Reordenação por drag and drop.
- Adição/remoção de blocos.
- Ao salvar qualquer alteração, chamar `update_storyboard` com lista completa ordenada para centralizar validação e invalidação no backend.

Critérios técnicos:

- O Storyboard não contém texto final.
- A quantidade de blocos não é fixa.
- A aplicação não deve assumir sequência universal como `Gancho -> Desenvolvimento -> Conclusão`.
- Alterações do usuário são decisões autorais e incrementam a versão do storyboard.

## 9. Rascunhador de Blocos

Backend:

- `BlockDraftGenerator.gerar_abordagens(block, contexto)` retorna exatamente três abordagens distintas.
- Seleção de personas: `random.sample(EDITORIAL_PERSONAS, 3)`, persistindo o resultado. Retry de opção mantém persona/abordagem; regenerar bloco inteiro pode sortear novamente.
- `BlockDraftGenerator.gerar_rascunho()` recebe briefing, planejamento, storyboard completo, posição do bloco, outros blocos, papel/foco atual, abordagem e persona.
- Para N blocos, custo inicial estimado: `1 + (N * 1 abordagem) + (N * 3 rascunhos) + 1 composição`, ou `4N + 2` chamadas incluindo storyboard e composição.
- Estado por bloco/opção deve guardar `status`, `error`, `provider`, `model`, `prompt_version`, `obsolete`.

Personas editoriais:

- `provocador`: O Provocador.
- `analitico`: O Analítico.
- `contador_de_historias`: O Contador de Histórias.
- `observador`: O Observador.
- `cetico`: O Cético.
- `pragmatico`: O Pragmático.
- `filosofo`: O Filósofo.
- `contrapontista`: O Contrapontista.
- `investigador`: O Investigador.
- `sintetizador`: O Sintetizador.

Frontend:

- Novo estágio `drafts`.
- Exibir bloco selecionado com três opções.
- Mostrar abordagem, persona e conteúdo.
- Permitir gerar todos, gerar apenas um bloco, retry de bloco/opção, selecionar uma opção por bloco.
- Exibir seleção incompleta antes de liberar composição.

Regras:

- Cada bloco deve ter exatamente três opções válidas para ser considerado completo.
- As três personas de um mesmo bloco não podem repetir.
- Cada rascunho desenvolve apenas o bloco atual.
- A LLM conhece a publicação completa, mas escreve apenas o bloco atual.

## 10. Composição Editorial

Backend:

- `EditorialComposer.compose()` recebe briefing, storyboard atual e rascunhos selecionados em ordem.
- Prompt `editorial.compose` deve ter o mesmo contrato de saída de geração final:
  - `conteudo`
  - `metadados`
  - `alertas`
  - opcionalmente `slidemark`, `sugestoesImagem`, `slides`.
- Reutilizar ou extrair com testes a lógica de parsing de `ContentGenerator.generate()` para produzir um `ConteudoGerado` equivalente.
- Ao sucesso:
  - `state.conteudo_gerado = resultado.conteudo`
  - `state.conteudo_json = payload compatível`
  - `state.prompt_renderizado` pode guardar o prompt de composição ou manter prompt legado separado em `editorial_flow.composition.prompt_renderizado`
  - `state.segmentos = []`
  - `state.avaliacao_post = {}`
  - `current_phase = PHASE_SEGMENTACAO` ou nova fase de composição com botão para segmentar.

Regra central:

- A composição pode alterar forma, transição, ritmo e voz.
- A composição não pode trocar ideias selecionadas.
- A composição não é uma nova geração livre.

## 11. Infraestrutura de LLM e prompts

Adicionar operações em `llm_config.py`:

- `storyboard_generate`
- `block_approaches_generate`
- `block_draft_generate`
- `editorial_compose`

Default recomendado:

- Herdar de `content_generate` usando `OPERATION_INHERITS`, permitindo override por `.data/agent-config.yml`.

Adicionar prompts em `prompt_loader.PROMPT_PATHS`:

- `editorial.storyboard`
- `editorial.block_approaches`
- `editorial.block_draft`
- `editorial.compose`

Structured outputs:

```json
{
  "blocks": [
    { "role": "...", "focus": "..." }
  ]
}
```

```json
{
  "approaches": [
    { "title": "...", "description": "..." }
  ]
}
```

```json
{
  "draft": {
    "content": "..."
  }
}
```

Composição:

```json
{
  "conteudo": "...",
  "metadados": {},
  "alertas": []
}
```

Falhas:

- Erro de uma opção não deve invalidar opções já geradas.
- Erro de um bloco deixa bloco `partial|failed`.
- Retry granular deve reaproveitar abordagem/persona persistidas.
- Sem fila externa no v1; usar execução síncrona no GUI como hoje, com persistência após cada bloco/opção.

## 12. Ciclo de vida, edição e invalidação

Estados persistidos necessários: status coarse por artefato (`generating`, `available`, `failed`, `obsolete`) e version/fingerprint.

Estados como `selection_incomplete` e `drafts_partial` são derivados.

Matriz de invalidação:

| Alteração | Artefatos afetados | Artefatos invalidados | Ação necessária |
|---|---|---|---|
| Briefing alterado | Storyboard, drafts, composição | todos artefatos editoriais | marcar obsoleto; limpar `conteudo_gerado/conteudo_json/segmentos/avaliacao` se origem editorial |
| Papel/foco editado | Storyboard inteiro | drafts e composição | incrementar `storyboard.version`; manter dados antigos como `obsolete` |
| Reordenar blocos | Storyboard inteiro | drafts e composição | invalidar drafts porque prompts usam posição e contexto global |
| Remover bloco | Storyboard, seleção | drafts e composição | bloco removido fica histórico obsoleto; seleção removida |
| Adicionar bloco | Storyboard inteiro | drafts e composição | gerar novos drafts para versão atual |
| Regenerar bloco | Drafts daquele bloco | seleção do bloco e composição | manter outras seleções se mesma versão |
| Retry de opção | Uma opção | nenhuma outra | manter abordagem/persona |
| Seleção alterada | Composição | composição e downstream editorial | recalcular `selection_fingerprint`; limpar segmentação/avaliação se conteúdo veio da composição |
| Composição gerada | Pipeline atual | nenhum | preencher `conteudo_gerado/conteudo_json` e liberar segmentação |

Regra:

- Problemas de estado devem ser resolvidos pelo domínio e pela aplicação, não por prompt pedindo para a LLM inferir mudanças.

## 13. Alterações de backend

Arquivos/módulos impactados:

- `src/content_engine/schemas.py`: novos campos em `TuiSessionState`; tipos conceituais se forem dataclasses.
- `src/content_engine/persistence.py`: serializar/carregar `editorial_flow` com defaults tolerantes e migração de sessões antigas.
- `src/content_engine/llm_config.py`: novas operações LLM e labels.
- `src/content_engine/prompt_loader.py`: novas chaves de prompt.
- `src/content_engine/generator.py`: extrair parser reutilizável de payload final, com teste de caracterização.
- Novo `src/content_engine/editorial_flow.py`: normalização, fingerprints, invalidação.
- Novo `src/content_engine/editorial_generation.py`: serviços LLM.
- `src/tui/app.py`: somente ajustes mínimos de compatibilidade/orquestração já que a TUI não faz parte da evolução funcional alvo.
- `src/gui/server.py`: novas actions em `_dispatch()`, snapshot derivado editorial.

Responsabilidades:

- Domínio: versões, fingerprints, validade e obsolescência.
- Serviços LLM: chamadas específicas, parsing e erro controlado.
- Orquestração: actions de geração, edição, seleção e composição.
- Persistência: migração tolerante e round-trip.
- Observabilidade: eventos por operação editorial.

## 14. Alterações de frontend

Arquivos/módulos impactados:

- `frontend/src/lib/pe-types.ts`: novos `StageId`, tipos de storyboard/drafts/composição.
- `frontend/src/lib/mappers/phase.ts`: mapear novas fases.
- `frontend/src/lib/mappers/operations.ts`: expor novas operações LLM.
- `frontend/src/lib/pe-store.tsx`: mapear `editorial_flow`, actions e estados derivados.
- `frontend/src/components/workstation/PipelineRail.tsx`: trilha atualizada para o novo pipeline.
- `frontend/src/components/workstation/Workstation.tsx`: registrar novos stages.
- Novos stages: `StoryboardStage.tsx`, `DraftsStage.tsx`, `CompositionStage.tsx`.
- `PromptStage` e `ExecutionStage` deixam de ser etapas principais da V3; podem ser removidos ou absorvidos por uma etapa interna de composição/execução, conforme a refatoração final.

Diretriz de interface:

- A evolução visível da V3 acontece no fluxo GUI/HTTP e no domínio de backend.
- Não há entrega planejada de novos estágios, ergonomia ou paridade funcional na TUI.

Fluxo esperado no React:

```text
Briefing -> Storyboard -> Rascunhos -> Composição -> Segmentação
```

## 15. APIs e contratos

Sem novos endpoints REST obrigatórios. Manter padrão atual:

- `GET /api/session`: passa a incluir `state.editorial_flow` e derivados editoriais.
- `PATCH /api/session`: não deve ser o caminho principal para mutar storyboard/drafts, porque invalidação precisa ser centralizada.
- `POST /api/action` novas ações:
  - `generate_storyboard`
  - `update_storyboard`
  - `generate_block_drafts`
  - `generate_all_block_drafts`
  - `select_block_draft`
  - `compose_editorial`
  - `retry_block_draft`

Contratos existentes preservados:

- `segment`, `evaluate` e `export` continuam.
- `render_prompt` e `run` deixam de representar a experiência principal da V3 e passam a ser candidatos a remoção ou reinterpretação interna.
- `conteudo_json` final deve preservar shape aceito por exportação e segmentação.

## 16. Estratégia de implementação incremental

### Fase 0 - Caracterização e preparação

- Objetivo: preparar a base de evolução sem bloquear o avanço por automação prévia.
- Escopo: leitura de contratos atuais, mapeamento de pontos de convergência e extrações pontuais necessárias no parser de `ContentGenerator`.
- Arquivos/módulos impactados: `generator.py`, documentação técnica do fluxo atual e pontos de integração.
- Dependências: nenhuma.
- Risco: baixo.
- Validação: contratos atuais identificados e pontos de convergência explicitados no código/plano.
- Critério de conclusão: base pronta para introduzir `editorial_flow` sem exigir testes automatizados prévios.

### Fase 1 - Estado editorial inerte

- Objetivo: adicionar `editorial_flow` e a base de migração de estado sem UI ativa.
- Escopo: estado, persistência, snapshot.
- Arquivos/módulos impactados: `schemas.py`, `persistence.py`, `gui/server.py`.
- Dependências: Fase 0.
- Risco: carregar sessões antigas.
- Validação: sessão antiga sem campos novos carrega com `editorial_flow` vazio e sem erro.
- Critério de conclusão: snapshots incluem campos novos e o pipeline atual continua operacional enquanto o novo miolo ainda não foi acoplado.

### Fase 2 - Storyboard backend

- Objetivo: gerar e editar storyboard sem alterar geração final.
- Escopo: serviço, prompt, parser, actions.
- Arquivos/módulos impactados: `editorial_flow.py`, `editorial_generation.py`, prompts, `tui/app.py` apenas se necessário para compatibilidade, `gui/server.py`.
- Dependências: Fase 1.
- Risco: invalidação incorreta.
- Validação: parser, geração fake, update com reorder/add/remove.
- Critério de conclusão: storyboard persiste e pode ser editado sem quebrar `render_prompt/run`.

### Fase 3 - Storyboard frontend

- Objetivo: inserir etapa visual entre briefing e geração editorial.
- Escopo: store, stage, rail, edição.
- Arquivos/módulos impactados: `pe-store.tsx`, `PipelineRail.tsx`, `StoryboardStage.tsx`.
- Dependências: Fase 2.
- Risco: navegação híbrida inconsistente durante a transição.
- Validação: o frontend já reflete o novo pipeline mesmo antes do restante do miolo estar completo.
- Critério de conclusão: usuário edita e salva storyboard.

### Fase 4 - Rascunhador backend

- Objetivo: gerar abordagens/personas/rascunhos por bloco com falha parcial.
- Escopo: serviços editoriais, prompts, estado por bloco.
- Arquivos/módulos impactados: `editorial_generation.py`, `editorial_flow.py`, prompts, actions.
- Dependências: Fase 2.
- Risco: custo LLM e estados parciais.
- Validação: 3 abordagens, 3 personas distintas, retry por opção/bloco.
- Critério de conclusão: seleções por bloco persistem.

### Fase 5 - Rascunhador frontend

- Objetivo: comparar e selecionar opções.
- Escopo: stage de rascunhos, seleção, feedback parcial.
- Arquivos/módulos impactados: `DraftsStage.tsx`, `pe-store.tsx`, tipos.
- Dependências: Fase 4.
- Risco: seleção incompleta liberando composição.
- Validação: composição bloqueada até uma seleção válida por bloco atual.
- Critério de conclusão: usuário escolhe uma opção por bloco.

### Fase 6 - Composição e convergência

- Objetivo: compor conteúdo final e preencher artefatos atuais.
- Escopo: `EditorialComposer`, parser final, action de composição.
- Arquivos/módulos impactados: `editorial_generation.py`, `generator.py`, `tui/app.py` apenas se necessário para compatibilidade, `gui/server.py`.
- Dependências: Fase 5.
- Risco: composição virar geração livre.
- Validação: seleção fingerprint, saída compatível com `conteudo_gerado/conteudo_json`.
- Critério de conclusão: segmentação atual recebe conteúdo composto.

### Fase 7 - Hardening, rollout e docs

- Objetivo: regressão, observabilidade, automação de testes e preparação para a virada final da V3.
- Escopo: testes, logs, GUI inspector, documentação.
- Arquivos/módulos impactados: testes, `DevDrawer.tsx`, docs.
- Dependências: Fase 6.
- Risco: remover cedo demais partes do caminho antigo antes da convergência estar estável.
- Validação: a V3 completa passa nos cenários principais e substitui o caminho antigo.
- Critério de conclusão: pipeline novo é o único caminho operacional de geração e a automação de testes cobre os contratos críticos pós-convergência.

## 17. Estratégia de testes

Prioridade máxima: preservar os contratos downstream que o pipeline atual já atende.

Diretriz operacional:

- Não executar nem exigir testes automatizados a priori durante a evolução intermediária do sistema.
- Concentrar criação, revisão e execução da suíte automatizada depois que storyboard, rascunhos e composição já estiverem convergindo para os artefatos finais.
- Usar validação incremental por contrato, inspeção de estado, snapshots e verificação manual enquanto a arquitetura ainda estiver em movimento.

Testes de caracterização:

- `build_generation_prompt()` mantém persona, regras, briefing, `interview_pack`.
- `ContentGenerator.generate()` mantém parsing de `conteudo`, `slidemark`, `sugestoesImagem`, `parse_error`.
- `PostEngineApp.action_run()` é protegido enquanto existir durante a transição de código.
- `_segmentar()` continua usando `segmentar_slidemark()` quando `conteudo_json.slidemark` existe.
- `action_evaluate()` continua avaliando `_conteudo_final()`.
- Sessões antigas sem `editorial_flow` carregam.

Novos testes:

- Storyboard parser rejeita blocos inválidos e não aceita texto final.
- Edição de storyboard incrementa versão e invalida drafts/composição.
- Abordagens: exatamente 3 e semanticamente distintas no contrato estrutural.
- Personas: 3 distintas por bloco, persistidas, retry não resorteia.
- Falha parcial: uma opção falha sem apagar as outras.
- Seleção incompleta bloqueia composição.
- Alterar seleção invalida composição e downstream editorial.
- Composição gera contrato compatível com geração atual.
- Publicações antigas continuam exportáveis.

Observação operacional:

- Durante a investigação, `rtk pytest -q`, `rtk python -m pytest -q` e `rtk .venv/bin/python -m pytest -q` não conseguiram executar a suíte porque `pytest` não estava disponível no ambiente.

## 18. Observabilidade e operação

Reaproveitar `SessionLogger`:

- Registrar operações:
  - `editorial.storyboard.generate`
  - `editorial.block_approaches.generate`
  - `editorial.block_draft.generate`
  - `editorial.compose`
- Em cada evento: `session_id`, `block_id`, `option_id`, `provider`, `model`, `prompt_version`, duração, tamanho do prompt, tamanho da resposta, status e erro.
- Persistir no artefato: modelo/provider usados, persona, abordagem e `selection_fingerprint`.
- Sem métricas externas no v1; custo deve ser estimado por número de chamadas e tamanho de prompt/resposta, já que `AgentWrapper` não normaliza token usage.
- Diagnóstico de falha parcial deve aparecer no snapshot e no frontend por bloco/opção.

Compatível com a infraestrutura atual:

- JSONL por sessão em `.data/sessions/logs`.
- Campos de estado salvos em `.data/sessions/current-session.json`.
- Sem dependência de tracing externo ou plataforma de métricas.

## 19. Riscos e decisões em aberto

Riscos conhecidos:

- Custo cresce como `4N + 2` chamadas.
- Prompts de rascunho podem gerar sobreposição se invalidação for permissiva demais.
- Composição pode substituir ideias selecionadas se o prompt/schema não forem restritivos.
- UI pode ficar pesada se todos os blocos/opções forem renderizados de uma vez.
- Testes não puderam ser executados agora porque `pytest` não está instalado no Python disponível.

Trade-offs adotados:

- Persistir `editorial_flow` em JSON, não criar banco.
- Invalidar drafts em qualquer mudança de storyboard para evitar inconsistência escondida.
- Sem fila externa no v1; usar execução in-process e persistência parcial.
- Não travar a evolução por cobertura de testes ou execução de suíte antes da convergência funcional principal.

Decisões antes da implementação:

- Definir limite inicial de concorrência: recomendação v1 é sequencial com persistência por bloco, ou no máximo 3 workers dentro de um bloco.
- Definir em qual fase `PromptStage` e `ExecutionStage` serão removidos da UX principal em vez de apenas ficarem ociosos.

Decisões adiáveis:

- Métrica real de custo por token.
- Comparação visual avançada entre versões obsoletas.
- Feature flag por usuário/workspace, pois não há modelo de usuário/workspace no código atual.

## 20. Ordem recomendada de execução

1. Proteger e caracterizar o pipeline legado.
2. Adicionar estado editorial inerte e migração tolerante.
3. Implementar Storyboard backend e invalidação.
4. Implementar Storyboard frontend.
5. Implementar Rascunhador backend com personas e falha parcial.
6. Implementar seleção/comparação no frontend.
7. Implementar Composição Editorial e convergir para `conteudo_gerado/conteudo_json`.
8. Reusar segmentação, avaliação, ajuste e exportação atuais.
9. Remover o caminho antigo de geração integral e limpar a UX restante da GUI, sem investir em evolução paralela da TUI.
10. Endurecer testes, logs e documentação final da V3.

Essa ordem permite validar cada capacidade verticalmente, compatibilizar o novo miolo com o restante do pipeline e concluir a migração sem sustentar dois modos permanentes.

## Checklist interno de compatibilidade

- O fluxo atual continua funcionando sem Storyboard: apenas como condição transitória de implementação; não como operação suportada da V3 final.
- Publicações existentes continuam válidas: sim, novos campos têm defaults e a carga é migrável.
- É possível introduzir Storyboard antes do Rascunhador: sim, Storyboard é persistido e editável sem alterar geração final.
- É possível introduzir o Rascunhador antes da Composição final estar pronta: sim, seleção pode ser persistida sem convergir ainda para `conteudo_gerado`.
- Existe um ponto claro de convergência com o pipeline atual: sim, `conteudo_gerado`/`conteudo_json`.
- Edições invalidam explicitamente os artefatos dependentes: sim, por versão/fingerprint.
- Falhas parciais de LLM são recuperáveis: sim, por status/error em bloco/opção e retry granular.
- As três features utilizam as capacidades existentes sempre que possível: sim, `AgentWrapper`, prompts, `llm_config`, `SessionLogger`, `TuiSessionState`.
- O planejamento evita uma reescrita desnecessária: sim, adiciona camada editorial antes do pipeline atual.
- A ordem de implementação reduz o risco de regressão: sim, começa por caracterização, compatibilização de estado e convergência downstream antes da remoção final do caminho antigo.
- A TUI precisa evoluir junto com a V3: não; apenas compatibilidade técnica mínima quando indispensável.
- Testes automatizados são pré-condição para cada fase intermediária: não; ficam concentrados após a convergência funcional principal.
