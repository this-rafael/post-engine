# Tarefas — Persistência relacional SQLite

## Legenda

- **[BLOQUEADORA]**: bloqueia fases posteriores.
- **[P]**: pode ser executada em paralelo com outras tarefas que tenham as
  dependências satisfeitas.
- **[ALTO RISCO]**: exige backup, revisão adicional ou ensaio de rollback.

Cada tarefa deve resultar em um commit coerente. Não combinar schema,
repository, API e frontend no mesmo commit.

## Fase 1 — Infraestrutura SQLite

## T001 — Definir configuração do banco e feature mode [BLOQUEADORA]

- [ ] **Objetivo:** estabelecer paths, pragmas configuráveis e modos `legacy`, `dual_write`, `sqlite_shadow_read` e `sqlite`.
- [ ] **Dependências:** nenhuma.
- [ ] **Arquivos prováveis:** módulo novo de configuração, bootstrap da CLI/GUI, documentação de ambiente.
- [ ] **Passos de implementação:** definir `.data/post-engine.sqlite3`, defaults, override de teste e validação de valores.
- [ ] **Testes:** defaults, overrides, mode inválido e garantia de que o path do Prompt Registry permanece separado.
- [ ] **Critério de conclusão:** aplicação inicia em `legacy` sem mudar o comportamento atual.
- [ ] **Riscos/observações:** fechar nesta tarefa `busy_timeout` inicial e `synchronous` por ambiente.

## T002 — Criar factory de conexão SQLite [BLOQUEADORA]

- [ ] **Objetivo:** abrir uma conexão independente por request/UoW.
- [ ] **Dependências:** T001.
- [ ] **Arquivos prováveis:** `src/content_engine/db/connection.py`, testes de conexão.
- [ ] **Passos de implementação:** configurar row factory, foreign keys, WAL, busy timeout e fechamento seguro.
- [ ] **Testes:** pragmas em toda conexão, duas conexões simultâneas, erro de path e fechamento.
- [ ] **Critério de conclusão:** nenhuma conexão de domínio é global ou compartilhada entre threads.
- [ ] **Riscos/observações:** não abrir nem alterar `.data/prompt-registry.sqlite3`.

## T003 — Implementar migration runner com checksum [BLOQUEADORA]

- [ ] **Objetivo:** aplicar migrations numeradas, imutáveis e transacionais.
- [ ] **Dependências:** T002.
- [ ] **Arquivos prováveis:** `src/content_engine/db/migrations.py`, diretório de SQL, testes.
- [ ] **Passos de implementação:** criar `schema_migrations`, ordenar arquivos, calcular checksum e controlar commit/rollback.
- [ ] **Testes:** banco vazio, reexecução, gap de versão, checksum divergente e migration com falha.
- [ ] **Critério de conclusão:** startup bloqueia schema inconsistente e não reaplica migrations.
- [ ] **Riscos/observações:** migration aplicada nunca deve ser editada; correções são forward-only.

## T004 — Criar banco e fixtures isoladas de teste [BLOQUEADORA]

- [ ] **Objetivo:** garantir um SQLite temporário por teste.
- [ ] **Dependências:** T003.
- [ ] **Arquivos prováveis:** `tests/conftest.py`, helpers de banco, fixtures.
- [ ] **Passos de implementação:** criar arquivo temporário, aplicar migrations reais e descartar ao final.
- [ ] **Testes:** isolamento entre testes, pragmas idênticos e ausência de acesso à `.data/`.
- [ ] **Critério de conclusão:** suites de repository/migration não dependem do banco local do desenvolvedor.
- [ ] **Riscos/observações:** testes concorrentes devem abrir conexões diferentes.

## T005 — Adicionar observabilidade básica do SQLite [P]

- [ ] **Objetivo:** medir migration, conexão, transação, busy e tamanho de WAL sem conteúdo sensível.
- [ ] **Dependências:** T002 e T003.
- [ ] **Arquivos prováveis:** logging/metrics do backend, testes de observabilidade.
- [ ] **Passos de implementação:** emitir IDs de correlação, duração e códigos de erro.
- [ ] **Testes:** eventos de sucesso/falha sem prompt, resposta ou stdout.
- [ ] **Critério de conclusão:** problemas de banco podem ser diagnosticados sem ler dados editoriais.
- [ ] **Riscos/observações:** não transformar logs em nova persistência de domínio.

## Fase 2 — Schema principal

## T006 — Criar migration de `users` e `posts` [BLOQUEADORA]

- [ ] **Objetivo:** criar as duas raízes de catálogo.
- [ ] **Dependências:** T003.
- [ ] **Arquivos prováveis:** migration SQL de users/posts, teste de schema.
- [ ] **Passos de implementação:** criar colunas, checks, FKs, índices e unicidade parcial de slug.
- [ ] **Testes:** usuário ativo/arquivado, posts por usuário, FK e filtros.
- [ ] **Critério de conclusão:** dois usuários podem possuir catálogos isolados.
- [ ] **Riscos/observações:** não introduzir autenticação ou credenciais.

## T007 — Criar migration de `sessions` e constraints [BLOQUEADORA]

- [ ] **Objetivo:** representar tentativas, lock otimista e restrições.
- [ ] **Dependências:** T006.
- [ ] **Arquivos prováveis:** migration SQL de sessions/session_constraints, testes.
- [ ] **Passos de implementação:** criar attempts, status, fases, timestamps, `lock_version` e índices.
- [ ] **Testes:** attempt único, post arquivado, checks, constraints ordenadas e FK.
- [ ] **Critério de conclusão:** um post aceita múltiplas sessões distintas.
- [ ] **Riscos/observações:** não criar coluna ou tabela de “sessão atual”.

## T008 — Criar migration de `session_events` [P]

- [ ] **Objetivo:** criar trilha append-only ordenada por sessão.
- [ ] **Dependências:** T007.
- [ ] **Arquivos prováveis:** migration SQL de eventos, testes.
- [ ] **Passos de implementação:** criar sequência, ator, entidade relacionada e payload diagnóstico opcional.
- [ ] **Testes:** ordem, unicidade, filtros e FK.
- [ ] **Critério de conclusão:** eventos podem ser consultados deterministicamente.
- [ ] **Riscos/observações:** decisões de negócio não podem existir somente em `payload_json`.

## T009 — Definir enums e transições das raízes [P]

- [ ] **Objetivo:** centralizar estados de user, post, sessão e fase.
- [ ] **Dependências:** T006 e T007.
- [ ] **Arquivos prováveis:** modelos de domínio principais, testes unitários.
- [ ] **Passos de implementação:** declarar valores e validadores conforme `spec.md`.
- [ ] **Testes:** todas as transições permitidas e rejeitadas.
- [ ] **Critério de conclusão:** não há strings de estado divergentes entre serviços novos.
- [ ] **Riscos/observações:** aliases legados ficam no boundary de importação.

## T010 — Validar migration principal em upgrades [BLOQUEADORA]

- [ ] **Objetivo:** provar criação do zero e upgrade até o schema principal.
- [ ] **Dependências:** T006 a T009.
- [ ] **Arquivos prováveis:** testes de migrations.
- [ ] **Passos de implementação:** montar bases em cada versão e aplicar sequência.
- [ ] **Testes:** schema, índices, checks, FKs e rollback de migration.
- [ ] **Critério de conclusão:** Fase 2 passa integralmente em banco temporário.
- [ ] **Riscos/observações:** não usar introspecção apenas superficial; testar invariantes.

## Fase 3 — Schema autoral

## T011 — Criar migration de rodadas, perguntas e issues [BLOQUEADORA]

- [ ] **Objetivo:** preservar candidatas, perguntas selecionadas e seus problemas.
- [ ] **Dependências:** T010.
- [ ] **Arquivos prováveis:** migration SQL de interview_rounds/questions/issues, testes.
- [ ] **Passos de implementação:** modelar ordem, status, scores, riscos e execução de origem.
- [ ] **Testes:** candidatas rejeitadas, pergunta pendente, ordenação e FKs.
- [ ] **Critério de conclusão:** nenhuma rodada precisa sobrescrever candidatas anteriores.
- [ ] **Riscos/observações:** chaves de risco desconhecidas vão ao relatório legado, não à regra nova.

## T012 — Criar migration de respostas e assessments [BLOQUEADORA]

- [ ] **Objetivo:** preservar resposta original e avaliações revisionadas.
- [ ] **Dependências:** T011.
- [ ] **Arquivos prováveis:** migration SQL de answers/assessments/items, testes.
- [ ] **Passos de implementação:** criar unicidade por pergunta, revisão por sessão e itens tipados.
- [ ] **Testes:** resposta imutável, uma resposta por pergunta, revisions e itens.
- [ ] **Critério de conclusão:** múltiplas avaliações coexistem sem overwrite.
- [ ] **Riscos/observações:** assessment é cumulativo e pode apontar para a resposta que o disparou.

## T013 — Criar migration de evidências e sinais [P]

- [ ] **Objetivo:** normalizar proveniência, tipos e sinais autorais.
- [ ] **Dependências:** T012.
- [ ] **Arquivos prováveis:** migration SQL de evidence/types/signals/joins, testes.
- [ ] **Passos de implementação:** criar ordens, IDs legados e relações N:N.
- [ ] **Testes:** deduplicação por chave, N:N, status de sinal e FK.
- [ ] **Critério de conclusão:** evidência pode ser rastreada até resposta e sinais.
- [ ] **Riscos/observações:** texto de evidência não deve ser inferido no importer.

## T014 — Criar migration de dimensões e regras [P]

- [ ] **Objetivo:** armazenar scores dimensionais por revisão.
- [ ] **Dependências:** T012 e T013.
- [ ] **Arquivos prováveis:** migration SQL de dimensions/evidence/rules, testes.
- [ ] **Passos de implementação:** criar estado, score, flags, rationale e joins.
- [ ] **Testes:** dimensão única por assessment, score 0–100, evidências e regras ordenadas.
- [ ] **Critério de conclusão:** duas revisões guardam scores independentes.
- [ ] **Riscos/observações:** `id` alias legado não vira segunda identidade.

## T015 — Criar migration de gaps e gateways [BLOQUEADORA]

- [ ] **Objetivo:** preservar diagnóstico e decisões de aprofundamento.
- [ ] **Dependências:** T014.
- [ ] **Arquivos prováveis:** migration SQL de gaps/gateways/items, testes.
- [ ] **Passos de implementação:** criar revisions, tipos, selected gap e itens.
- [ ] **Testes:** gateways sequenciais, gaps ordenados, estados e vínculos.
- [ ] **Critério de conclusão:** gateway novo não apaga o anterior.
- [ ] **Riscos/observações:** aliases `gateway_type`/`tipo_gateway` são colapsados.

## T016 — Criar migration de briefings e relações congeladas [BLOQUEADORA]

- [ ] **Objetivo:** consolidar a matéria-prima usada pelo editorial sem snapshot autoritativo.
- [ ] **Dependências:** T015.
- [ ] **Arquivos prováveis:** migration SQL de briefings e tabelas de join, testes.
- [ ] **Passos de implementação:** criar revisão, fingerprint, status e posições das relações.
- [ ] **Testes:** um consolidado ativo, composição exata e supersede.
- [ ] **Critério de conclusão:** briefing é reconstruível por joins.
- [ ] **Riscos/observações:** JSON de briefing fica restrito à compatibilidade.

## T017 — Testar cenário autoral completo [BLOQUEADORA]

- [ ] **Objetivo:** validar o agregado de ponta a ponta no schema.
- [ ] **Dependências:** T011 a T016.
- [ ] **Arquivos prováveis:** testes de integração do schema autoral.
- [ ] **Passos de implementação:** inserir duas rodadas, respostas, revisões, gateway e briefing.
- [ ] **Testes:** restart da conexão, consultas e integridade.
- [ ] **Critério de conclusão:** cenário é reconstruído sem `interview_state` JSON.
- [ ] **Riscos/observações:** cobrir extensão e dados históricos.

## Fase 4 — Schema editorial

## T018 — Criar migration de storyboards e blocos [BLOQUEADORA]

- [ ] **Objetivo:** armazenar revisões de storyboard e blocos ordenados.
- [ ] **Dependências:** T016.
- [ ] **Arquivos prováveis:** migration SQL de storyboards/blocks, testes.
- [ ] **Passos de implementação:** criar status, revision, fingerprint, origem LLM e índices.
- [ ] **Testes:** duas revisões, posições, supersede e FK de briefing.
- [ ] **Critério de conclusão:** revisão anterior permanece consultável.
- [ ] **Riscos/observações:** não reaproveitar IDs de bloco como PK entre revisões.

## T019 — Criar migration de abordagens e drafts [BLOQUEADORA]

- [ ] **Objetivo:** guardar abordagens e todas as tentativas de draft.
- [ ] **Dependências:** T018.
- [ ] **Arquivos prováveis:** migration SQL de approaches/drafts, testes.
- [ ] **Passos de implementação:** modelar persona, conteúdo, status, revision e execução.
- [ ] **Testes:** três opções, retry, falha parcial e supersede.
- [ ] **Critério de conclusão:** retry não sobrescreve draft disponível.
- [ ] **Riscos/observações:** provider/model pertencem à execução, não ao bloco.

## T020 — Criar migration de seleções de draft [BLOQUEADORA]

- [ ] **Objetivo:** preservar histórico e garantir uma seleção ativa por bloco.
- [ ] **Dependências:** T019.
- [ ] **Arquivos prováveis:** migration SQL de selections, testes.
- [ ] **Passos de implementação:** criar revisão, active e índice parcial único.
- [ ] **Testes:** selecionar, trocar seleção e rejeitar duas ativas.
- [ ] **Critério de conclusão:** seleção anterior fica superseded.
- [ ] **Riscos/observações:** draft de outro bloco deve ser rejeitado pelo serviço e teste.

## T021 — Criar migration de versões e segmentos [BLOQUEADORA]

- [ ] **Objetivo:** criar conteúdo imutável, versões sequenciais e segmentos.
- [ ] **Dependências:** T007 e T020.
- [ ] **Arquivos prováveis:** migration SQL de post_versions/segments/bullets, testes.
- [ ] **Passos de implementação:** criar origem, status, hash, documento permitido e ordem.
- [ ] **Testes:** sequência, imutabilidade, status e segmentos por versão.
- [ ] **Critério de conclusão:** duas versões coexistem sem alteração da primeira.
- [ ] **Riscos/observações:** JSON só para SlideMark/metadata sem regra.

## T022 — Criar migration de ajustes [P]

- [ ] **Objetivo:** preservar propostas e resultado de ajustes.
- [ ] **Dependências:** T021.
- [ ] **Arquivos prováveis:** migration SQL de segment_adjustments, testes.
- [ ] **Passos de implementação:** ligar versão/segmento de origem, lote, execução e resultado.
- [ ] **Testes:** proposed, accepted, rejected, failed e FKs.
- [ ] **Critério de conclusão:** ajuste aceito aponta para nova versão.
- [ ] **Riscos/observações:** nenhum update de segmento de origem.

## T023 — Criar migration de avaliações e itens [P]

- [ ] **Objetivo:** normalizar scores, veredito e listas de avaliação.
- [ ] **Dependências:** T021.
- [ ] **Arquivos prováveis:** migration SQL de evaluations/items, testes.
- [ ] **Passos de implementação:** criar scopes, alvos válidos, itens e índices.
- [ ] **Testes:** content/slidemark/authorial, scores, weak segments e alvo inválido.
- [ ] **Critério de conclusão:** avaliações históricas são filtráveis por versão.
- [ ] **Riscos/observações:** total derivado deve ser comparável, não duplicado sem validação.

## T024 — Criar migration de exports [P]

- [ ] **Objetivo:** catalogar tentativas e arquivos exportados.
- [ ] **Dependências:** T021.
- [ ] **Arquivos prováveis:** migration SQL de exports, testes.
- [ ] **Passos de implementação:** criar formato, status, path, hash, tamanho e timestamps.
- [ ] **Testes:** completed exige metadata; failed preserva erro; archive não apaga arquivo.
- [ ] **Critério de conclusão:** export pode ser consultado por versão e sessão.
- [ ] **Riscos/observações:** path precisa de validação no serviço, não só no schema.

## T025 — Testar cenário editorial completo [BLOQUEADORA]

- [ ] **Objetivo:** validar storyboard até export no schema.
- [ ] **Dependências:** T018 a T024.
- [ ] **Arquivos prováveis:** testes de integração do schema editorial.
- [ ] **Passos de implementação:** criar revisões, opções, seleção, versões, ajuste, avaliação e export.
- [ ] **Testes:** histórico e integridade após reabrir conexão.
- [ ] **Critério de conclusão:** nenhuma etapa depende de `editorial_flow` JSON.
- [ ] **Riscos/observações:** cobrir falha parcial e entidades superseded.

## Fase 5 — Execuções de LLM

## T026 — Criar migration de execuções e eventos LLM [BLOQUEADORA]

- [ ] **Objetivo:** criar rastreabilidade concreta de agentes.
- [ ] **Dependências:** T007.
- [ ] **Arquivos prováveis:** migration SQL de llm_executions/events, testes.
- [ ] **Passos de implementação:** criar estados, metadata efetiva, campos brutos permitidos e índice ativo.
- [ ] **Testes:** checks, eventos ordenados e uma ativa por sessão.
- [ ] **Critério de conclusão:** `is_running` não é necessário para representar execução.
- [ ] **Riscos/observações:** fechar política inicial de retenção.

## T027 — Criar modelo e state machine de execução LLM [BLOQUEADORA]

- [ ] **Objetivo:** validar transições queued/running/terminais.
- [ ] **Dependências:** T026.
- [ ] **Arquivos prováveis:** domínio de LLM, testes unitários.
- [ ] **Passos de implementação:** declarar transições, timestamps e invariantes.
- [ ] **Testes:** toda transição permitida/rejeitada e estado terminal.
- [ ] **Critério de conclusão:** nenhuma execução terminal pode ser reaberta.
- [ ] **Riscos/observações:** `interrupted` é terminal e exige nova tentativa.

## T028 — Propagar UUID ao Prompt Registry [BLOQUEADORA]

- [ ] **Objetivo:** usar a mesma identidade na resolução e execução.
- [ ] **Dependências:** T027.
- [ ] **Arquivos prováveis:** resolver/adapter do Prompt Registry, testes.
- [ ] **Passos de implementação:** criar UUID antes de resolver e passar `execution_id`.
- [ ] **Testes:** IDs iguais, metadata copiada e registry ausente na consulta histórica.
- [ ] **Critério de conclusão:** vínculo ponta a ponta não depende de horário.
- [ ] **Riscos/observações:** não criar FK cross-database.

## T029 — Implementar repository inicial de execuções LLM [BLOQUEADORA]

- [ ] **Objetivo:** reservar, iniciar, finalizar e consultar execuções/eventos antes da integração à UoW geral.
- [ ] **Dependências:** T026 e T027.
- [ ] **Arquivos prováveis:** repository de LLM, testes próprios e factory de conexão.
- [ ] **Passos de implementação:** criar operações SQL parametrizadas e controle transacional explícito.
- [ ] **Testes:** create/get/list, índice ativo, state machine, events e rollback.
- [ ] **Critério de conclusão:** suite exclusiva do repository passa sem commit oculto em operações compostas.
- [ ] **Riscos/observações:** a integração à UoW comum será concluída em T043.

## T030 — Separar reserva, chamada externa e finalização [BLOQUEADORA]

- [ ] **Objetivo:** impedir transação aberta durante a LLM.
- [ ] **Dependências:** T028 e T029.
- [ ] **Arquivos prováveis:** service de execução, `agent_wrapper.py`, adapter e testes transacionais.
- [ ] **Passos de implementação:** reservar/commit, emitir ID/eventos, executar e finalizar/commit.
- [ ] **Testes:** fake agent bloqueante, sucesso, erro, timeout, falha entre etapas e retry.
- [ ] **Critério de conclusão:** outra sessão consegue escrever enquanto a LLM aguarda.
- [ ] **Riscos/observações:** preservar mudanças locais preexistentes em `agent_wrapper.py`; resultado externo concluído e falha no commit devem ficar diagnosticáveis.

## T031 — Reconciliar execuções órfãs no startup

- [ ] **Objetivo:** converter `running` não recuperável em `interrupted`.
- [ ] **Dependências:** T030.
- [ ] **Arquivos prováveis:** bootstrap, service de recovery, testes.
- [ ] **Passos de implementação:** identificar órfãs, registrar evento e timestamp.
- [ ] **Testes:** running órfã, execução terminal e múltiplas sessões.
- [ ] **Critério de conclusão:** restart não deixa sessão bloqueada por booleano obsoleto.
- [ ] **Riscos/observações:** não interromper execução de outro processo sem política aprovada.

## T032 — Testar concorrência e retenção de LLM [BLOQUEADORA]

- [ ] **Objetivo:** provar exclusão por sessão e paralelismo entre sessões.
- [ ] **Dependências:** T026 a T031.
- [ ] **Arquivos prováveis:** testes de concorrência/LLM.
- [ ] **Passos de implementação:** usar barreiras, duas conexões e payloads de tamanhos variados.
- [ ] **Testes:** mesma sessão rejeitada, sessões diferentes simultâneas, busy e retenção.
- [ ] **Critério de conclusão:** invariantes de execução da spec passam.
- [ ] **Riscos/observações:** incluir multi-processo se a decisão de suporte for positiva.

## Fase 6 — Modelos, mapeadores e repositories

## T033 — Criar modelos e mapeadores comuns [BLOQUEADORA]

- [ ] **Objetivo:** mapear UUIDs, timestamps, enums e rows sem depender da UI.
- [ ] **Dependências:** T010, T017, T025 e T027.
- [ ] **Arquivos prováveis:** pacote `domain/`, pacote de mapeadores, testes.
- [ ] **Passos de implementação:** criar modelos por agregado e conversões explícitas.
- [ ] **Testes:** round-trip, campos nulos, enums inválidos e UTC.
- [ ] **Critério de conclusão:** repositories podem retornar objetos consistentes.
- [ ] **Riscos/observações:** não transformar snapshot compatível em modelo de domínio.

## T034 — Implementar unidade de trabalho [BLOQUEADORA]

- [ ] **Objetivo:** controlar conexão e transação de múltiplos repositories.
- [ ] **Dependências:** T002 e T033.
- [ ] **Arquivos prováveis:** `unit_of_work.py`, testes.
- [ ] **Passos de implementação:** begin, commit, rollback, context manager e factories.
- [ ] **Testes:** sucesso, exceção, rollback e fechamento.
- [ ] **Critério de conclusão:** nenhum repository precisa fazer commit.
- [ ] **Riscos/observações:** proibir UoW viva durante I/O externo.

## T035 — Implementar `UserRepository`

- [ ] **Objetivo:** criar, obter, listar, renomear e arquivar usuários.
- [ ] **Dependências:** T033 e T034.
- [ ] **Arquivos prováveis:** repository de user e teste próprio.
- [ ] **Passos de implementação:** SQL parametrizado, filtros e conflito de slug.
- [ ] **Testes:** create/get/list/archive e usuário arquivado.
- [ ] **Critério de conclusão:** suite exclusiva do repository passa.
- [ ] **Riscos/observações:** sem campos de autenticação.

## T036 — Implementar `PostRepository`

- [ ] **Objetivo:** gerenciar posts no escopo de usuário.
- [ ] **Dependências:** T035.
- [ ] **Arquivos prováveis:** repository de post e teste próprio.
- [ ] **Passos de implementação:** create/get/list/update/status/archive.
- [ ] **Testes:** isolamento por usuário, estados e post arquivado.
- [ ] **Critério de conclusão:** repository nunca retorna post de outro usuário no catálogo.
- [ ] **Riscos/observações:** reabertura é transição explícita.

## T037 — Implementar `SessionRepository`

- [ ] **Objetivo:** gerenciar attempts, constraints, eventos e lock otimista.
- [ ] **Dependências:** T036.
- [ ] **Arquivos prováveis:** repository de session e teste próprio.
- [ ] **Passos de implementação:** alocar attempt, CAS de lock, eventos e queries.
- [ ] **Testes:** concorrência, 0/1 row update, ordem de eventos e archive.
- [ ] **Critério de conclusão:** stale write gera conflito sem linhas parciais.
- [ ] **Riscos/observações:** tarefa bloqueadora para refatoração da sessão.

## T038 — Implementar `InterviewRepository`

- [ ] **Objetivo:** persistir e consultar todo o agregado autoral.
- [ ] **Dependências:** T037.
- [ ] **Arquivos prováveis:** repository autoral e teste próprio.
- [ ] **Passos de implementação:** rounds, questions, answers, assessments, evidence, gateways e briefings.
- [ ] **Testes:** cenário completo, revisions, joins e ordem.
- [ ] **Critério de conclusão:** briefing e entrevista são reconstruídos sem JSON.
- [ ] **Riscos/observações:** controlar número de queries do snapshot.

## T039 — Implementar `EditorialRepository`

- [ ] **Objetivo:** persistir storyboard, approaches, drafts e selections.
- [ ] **Dependências:** T037.
- [ ] **Arquivos prováveis:** repository editorial e teste próprio.
- [ ] **Passos de implementação:** revisions, retries, supersede e seleção ativa.
- [ ] **Testes:** fluxo parcial/completo e troca de seleção.
- [ ] **Critério de conclusão:** nenhuma operação atualiza conteúdo histórico.
- [ ] **Riscos/observações:** validar parent scope de todos os IDs.

## T040 — Implementar `PostVersionRepository`

- [ ] **Objetivo:** criar/listar versões, segmentos e ajustes.
- [ ] **Dependências:** T036 e T037.
- [ ] **Arquivos prováveis:** repository de versions e teste próprio.
- [ ] **Passos de implementação:** alocar número em transação e aplicar status.
- [ ] **Testes:** criação concorrente, imutabilidade e ajuste.
- [ ] **Critério de conclusão:** números são únicos e sequenciais por post.
- [ ] **Riscos/observações:** `MAX + 1` só pode ocorrer sob transação protegida.

## T041 — Implementar `EvaluationRepository`

- [ ] **Objetivo:** persistir avaliações e itens por alvo.
- [ ] **Dependências:** T040.
- [ ] **Arquivos prováveis:** repository de evaluation e teste próprio.
- [ ] **Passos de implementação:** create, transition, complete, list e archive.
- [ ] **Testes:** scopes, itens, falha e filtros.
- [ ] **Critério de conclusão:** cada versão mantém todo seu histórico.
- [ ] **Riscos/observações:** validar exatamente o alvo aplicável.

## T042 — Implementar `ExportRepository`

- [ ] **Objetivo:** registrar lifecycle e metadata de arquivos.
- [ ] **Dependências:** T040.
- [ ] **Arquivos prováveis:** repository de export e teste próprio.
- [ ] **Passos de implementação:** pending/running/completed/failed/list/archive.
- [ ] **Testes:** transições, metadata obrigatória e arquivo inexistente.
- [ ] **Critério de conclusão:** completed só ocorre após hash e tamanho.
- [ ] **Riscos/observações:** repository não grava o arquivo.

## T043 — Integrar `LlmExecutionRepository` à unidade de trabalho

- [ ] **Objetivo:** usar o repository de T029 na UoW comum e completar consultas.
- [ ] **Dependências:** T029 e T034.
- [ ] **Arquivos prováveis:** repository de LLM, UoW e teste próprio.
- [ ] **Passos de implementação:** remover transações locais residuais, injetar conexão e adicionar heartbeat/recovery.
- [ ] **Testes:** state machine, concorrência, recovery e rollback multi-repository.
- [ ] **Critério de conclusão:** uma execução ativa por sessão é garantida sem commit interno.
- [ ] **Riscos/observações:** manter compatibilidade com o service já criado em T030.

## T044 — Criar migration de `legacy_imports`

- [ ] **Objetivo:** criar a tabela de idempotência, relatório, alvos e rollback.
- [ ] **Dependências:** T003 e T007.
- [ ] **Arquivos prováveis:** migration SQL de `legacy_imports` e teste de schema.
- [ ] **Passos de implementação:** criar colunas, estados, FKs, unicidade e índices.
- [ ] **Testes:** constraints, estados, source hash e upgrade.
- [ ] **Critério de conclusão:** schema de importação existe sem serviço ou repository acoplado.
- [ ] **Riscos/observações:** manter esta migration separada da lógica de decomposição.

## T044A — Implementar `LegacyImportRepository`

- [ ] **Objetivo:** consultar e atualizar idempotência, relatório, alvos e rollback.
- [ ] **Dependências:** T034 e T044.
- [ ] **Arquivos prováveis:** repository de legacy import e teste próprio.
- [ ] **Passos de implementação:** create/find/update status e queries por hash.
- [ ] **Testes:** unicidade, estados, relatório e rollback marker.
- [ ] **Critério de conclusão:** reexecução da mesma fonte é detectável pela suite do repository.
- [ ] **Riscos/observações:** não implementar decomposição do JSON nesta tarefa.

## T045 — Testar UoW multi-repository [BLOQUEADORA]

- [ ] **Objetivo:** provar atomicidade entre agregados.
- [ ] **Dependências:** T035 a T044A.
- [ ] **Arquivos prováveis:** testes transacionais.
- [ ] **Passos de implementação:** combinar session, event, version e execution na mesma UoW.
- [ ] **Testes:** commit, rollback, CAS e alocação concorrente.
- [ ] **Critério de conclusão:** falha em qualquer repository reverte todos.
- [ ] **Riscos/observações:** usar conexões reais SQLite, não mocks.

## Fase 7 — Compatibilidade com estado legado

## T046 — Implementar parser estrito do snapshot legado [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** ler schema `4.0` sem ativar estado global.
- [ ] **Dependências:** T033.
- [ ] **Arquivos prováveis:** pacote `legacy/`, fixtures e testes.
- [ ] **Passos de implementação:** validar estrutura, preservar raw e emitir diagnóstico.
- [ ] **Testes:** atual, ausente, inválido, schema antigo e campos desconhecidos.
- [ ] **Critério de conclusão:** nenhum erro é convertido silenciosamente em sessão vazia.
- [ ] **Riscos/observações:** preservar comportamento antigo apenas no adapter legado.

## T047 — Implementar `SessionSnapshotAssembler` [BLOQUEADORA]

- [ ] **Objetivo:** reconstruir snapshot de UI a partir das relações.
- [ ] **Dependências:** T038 a T043.
- [ ] **Arquivos prováveis:** pacote `snapshots/`, testes.
- [ ] **Passos de implementação:** montar entrevista, briefing, editorial, versão, avaliação e execução.
- [ ] **Testes:** estados vazios, parciais, completos e queries ordenadas.
- [ ] **Critério de conclusão:** snapshot não lê `payload_json` de sessão.
- [ ] **Riscos/observações:** campos derivados devem ser calculados deterministicamente.

## T048 — Implementar comparador canônico de snapshots [BLOQUEADORA]

- [ ] **Objetivo:** classificar igualdade, diferença derivada e divergência real.
- [ ] **Dependências:** T046 e T047.
- [ ] **Arquivos prováveis:** comparador, normalizadores, testes.
- [ ] **Passos de implementação:** remover transitórios, aliases e duplicações antes de comparar.
- [ ] **Testes:** fixtures iguais, aliases, ordem, divergência de conteúdo e gateway.
- [ ] **Critério de conclusão:** relatório aponta path e severidade de cada diferença.
- [ ] **Riscos/observações:** normalização não pode esconder perda de dado autoritativo.

## T049 — Implementar dry run de importação [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** planejar decomposição sem escrever domínio.
- [ ] **Dependências:** T044A, T046 e decisão de usuário alvo.
- [ ] **Arquivos prováveis:** service de importação, relatório, testes.
- [ ] **Passos de implementação:** hash, contagens, deduplicação, warnings e plano de IDs.
- [ ] **Testes:** nenhuma escrita, duplicações, campos transitórios e usuário ausente.
- [ ] **Critério de conclusão:** relatório cobre toda a matriz de `research.md`.
- [ ] **Riscos/observações:** não criar usuário implicitamente sem política aprovada.

## T050 — Implementar apply idempotente da importação [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** criar user target/post/session/histórico em uma transação.
- [ ] **Dependências:** T045 e T049.
- [ ] **Arquivos prováveis:** service de importação, mapeadores e testes.
- [ ] **Passos de implementação:** gerar UUIDs, preservar legacy IDs, colapsar cópias e gravar relatório.
- [ ] **Testes:** sucesso, erro no meio, reexecução, divergência e `is_running`.
- [ ] **Critério de conclusão:** mesma fonte não duplica e falha não deixa dados parciais.
- [ ] **Riscos/observações:** não inventar rodadas/execuções históricas.

## T051 — Implementar política de JSONL legado [P] [ALTO RISCO]

- [ ] **Objetivo:** importar ou catalogar logs conforme decisão aprovada.
- [ ] **Dependências:** T049 e T050.
- [ ] **Arquivos prováveis:** parser JSONL, importer, testes.
- [ ] **Passos de implementação:** validar linhas, correlacionar somente quando inequívoco e reportar ambiguidade.
- [ ] **Testes:** arquivo grande, linha inválida, sessão diferente e correlação ausente.
- [ ] **Critério de conclusão:** nenhum log é atribuído por suposição silenciosa.
- [ ] **Riscos/observações:** controlar memória e conteúdo sensível.

## T052 — Implementar política de exports legados [P] [ALTO RISCO]

- [ ] **Objetivo:** executar scan seguro ou registrar explicitamente que não será feito.
- [ ] **Dependências:** T049 e decisão de scan.
- [ ] **Arquivos prováveis:** importer/export scanner, relatório e testes.
- [ ] **Passos de implementação:** validar paths, hash e associação demonstrável.
- [ ] **Testes:** arquivo conhecido, duplicado, path fora do diretório e origem ambígua.
- [ ] **Critério de conclusão:** relatório descreve todos os arquivos considerados.
- [ ] **Riscos/observações:** não inferir versão apenas pelo nome.

## T053 — Implementar backup e rollback de importação [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** permitir aplicar e desfazer importação sem afetar dados posteriores.
- [ ] **Dependências:** T050.
- [ ] **Arquivos prováveis:** backup service, import service, runbook e testes.
- [ ] **Passos de implementação:** backup consistente, ownership das linhas e validação de dependências.
- [ ] **Testes:** rollback permitido, bloqueado por dependência e restore do backup.
- [ ] **Critério de conclusão:** rollback nunca remove entidade não pertencente ao import.
- [ ] **Riscos/observações:** considerar WAL e não alterar backups do registry.

## T054 — Implementar dual writer [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** gravar JSON e SQLite com resultado explícito de ambos.
- [ ] **Dependências:** T047, T050 e services/repositories.
- [ ] **Arquivos prováveis:** adapter de persistência, feature flags, testes.
- [ ] **Passos de implementação:** manter JSON autoritativo, decompor mutação e registrar falhas.
- [ ] **Testes:** ambos sucesso, JSON falha, SQLite falha e retry.
- [ ] **Critério de conclusão:** divergência nunca é ocultada.
- [ ] **Riscos/observações:** não há transação cross-store; documentar ordem escolhida.

## T055 — Implementar shadow read e métricas [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** reconstruir e comparar SQLite sem mudar resposta funcional.
- [ ] **Dependências:** T048 e T054.
- [ ] **Arquivos prováveis:** rollout adapter, métricas, testes.
- [ ] **Passos de implementação:** comparar após ações, classificar divergências e agregar métricas.
- [ ] **Testes:** match, divergência crítica, timeout de comparação e conteúdo parcial.
- [ ] **Critério de conclusão:** há evidência quantitativa para o corte.
- [ ] **Riscos/observações:** comparação não deve bloquear indefinidamente a ação.

## T056 — Criar suite de migração com snapshots representativos [BLOQUEADORA]

- [ ] **Objetivo:** provar decomposição e reconstrução em dados reais anonimizados.
- [ ] **Dependências:** T046 a T055.
- [ ] **Arquivos prováveis:** fixtures, testes de migração e relatórios esperados.
- [ ] **Passos de implementação:** cobrir vazio, entrevista, editorial parcial, completo e corrompido.
- [ ] **Testes:** dry run, apply, idempotência, compare e rollback.
- [ ] **Critério de conclusão:** todos os limites conhecidos do research aparecem nos relatórios.
- [ ] **Riscos/observações:** fixtures não podem conter dados pessoais reais.

## Fase 8 — Refatoração da sessão

## T057 — Criar command boundary com `session_id` e lock [BLOQUEADORA]

- [ ] **Objetivo:** padronizar comandos pequenos e `expected_lock_version`.
- [ ] **Dependências:** T037, T045 e T047.
- [ ] **Arquivos prováveis:** services/commands, erros de domínio, testes.
- [ ] **Passos de implementação:** definir contexto, validação, CAS e resposta.
- [ ] **Testes:** comando válido, stale lock, sessão terminal e ID ausente.
- [ ] **Critério de conclusão:** nenhum comando recebe snapshot completo.
- [ ] **Riscos/observações:** comandos específicos, sem “patch genérico de sessão”.

## T058 — Implementar registry de locks por sessão [BLOQUEADORA]

- [ ] **Objetivo:** remover serialização global no processo.
- [ ] **Dependências:** T057.
- [ ] **Arquivos prováveis:** lock manager, controller factory, testes.
- [ ] **Passos de implementação:** lock keyed, cleanup e `finally`.
- [ ] **Testes:** mesma chave serializa, chaves diferentes paralelizam e exceção libera.
- [ ] **Critério de conclusão:** não existe lock único para todas as sessões.
- [ ] **Riscos/observações:** garantia durável continua sendo SQLite.

## T059 — Remover estado mutável global do controller [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** tornar controller stateless por request.
- [ ] **Dependências:** T057 e T058.
- [ ] **Arquivos prováveis:** `session_controller.py`, `session_app.py`, factories e testes.
- [ ] **Passos de implementação:** carregar por ID/UoW e usar snapshot somente na resposta.
- [ ] **Testes:** dois controllers, duas sessões e clientes independentes.
- [ ] **Critério de conclusão:** nenhum singleton contém `TuiSessionState`.
- [ ] **Riscos/observações:** preservar adapters temporários do frontend antigo.

## T060 — Refatorar início e respostas da entrevista [BLOQUEADORA]

- [ ] **Objetivo:** migrar os primeiros comandos autorais para repositories.
- [ ] **Dependências:** T038, T057 e T059.
- [ ] **Arquivos prováveis:** interview controller/services, testes atuais adaptados.
- [ ] **Passos de implementação:** criar round/question/answer/assessment/evento em UoW.
- [ ] **Testes:** início, resposta, falha de LLM, retry e restart.
- [ ] **Critério de conclusão:** comandos não mutam `interview_state` global.
- [ ] **Riscos/observações:** manter resposta original imutável.

## T061 — Refatorar extensão, gateway e briefing [BLOQUEADORA]

- [ ] **Objetivo:** concluir o agregado autoral por IDs.
- [ ] **Dependências:** T060.
- [ ] **Arquivos prováveis:** gap/gateway/briefing services, testes.
- [ ] **Passos de implementação:** revisions, extensão, fechamento e consolidação.
- [ ] **Testes:** gateway reprovado/aprovado, extensão e histórico.
- [ ] **Critério de conclusão:** briefing relacional alimenta o editorial.
- [ ] **Riscos/observações:** falha não avança a fase.

## T062 — Refatorar storyboard e revisões [BLOQUEADORA]

- [ ] **Objetivo:** substituir mutação de `editorial_flow.storyboard`.
- [ ] **Dependências:** T039, T057 e T061.
- [ ] **Arquivos prováveis:** `editorial_actions.py`, `editorial_flow.py`, testes.
- [ ] **Passos de implementação:** gerar/revisar/clear como nova revisão ou supersede.
- [ ] **Testes:** geração, falha, revisão e histórico.
- [ ] **Critério de conclusão:** storyboard antigo não é removido.
- [ ] **Riscos/observações:** fingerprint é derivado/validado, não fonte única.

## T063 — Refatorar drafts, retries, seleção e composição [BLOQUEADORA]

- [ ] **Objetivo:** substituir `drafts.by_block` e composição mutável.
- [ ] **Dependências:** T062.
- [ ] **Arquivos prováveis:** editorial actions/generation, repositories, testes.
- [ ] **Passos de implementação:** criar approaches/drafts, retries, selections e versão composta.
- [ ] **Testes:** parcial, três opções, retry, seleção inválida e compose.
- [ ] **Critério de conclusão:** composição cria `post_version`.
- [ ] **Riscos/observações:** persistências intermediárias viram entidades/eventos, não rewrites.

## T064 — Refatorar geração, segmentação, avaliação e ajustes [BLOQUEADORA]

- [ ] **Objetivo:** mover conteúdo downstream para versões imutáveis.
- [ ] **Dependências:** T040, T041 e T063.
- [ ] **Arquivos prováveis:** `generator.py`, evaluator, adjustment services, testes.
- [ ] **Passos de implementação:** criar versão, segmentos, avaliação e nova versão ajustada.
- [ ] **Testes:** geração, parse, avaliação, ajuste aceito/rejeitado e falha.
- [ ] **Critério de conclusão:** nenhum serviço atualiza `conteudo_gerado` como verdade.
- [ ] **Riscos/observações:** preservar SlideMark permitido em documento JSON.

## T065 — Refatorar export para catálogo transacional

- [ ] **Objetivo:** registrar lifecycle do export em torno da escrita do arquivo.
- [ ] **Dependências:** T042 e T064.
- [ ] **Arquivos prováveis:** `exporter.py`, export service, testes.
- [ ] **Passos de implementação:** criar pending/running, escrever fora da transação e finalizar com hash.
- [ ] **Testes:** sucesso, path inválido, falha de escrita e arquivo sobrescrito.
- [ ] **Critério de conclusão:** nenhum export completed carece de arquivo verificável.
- [ ] **Riscos/observações:** não manter transação durante I/O.

## T066 — Substituir reset e restore globais [BLOQUEADORA]

- [ ] **Objetivo:** aplicar nova tentativa, revisão, limpeza local e importação auditável.
- [ ] **Dependências:** T059 a T065.
- [ ] **Arquivos prováveis:** session app/controller, compat adapters e testes.
- [ ] **Passos de implementação:** remover substituição de state e encaminhar restore ao importer.
- [ ] **Testes:** nova tentativa preserva antiga; reset local não escreve; restore vira import.
- [ ] **Critério de conclusão:** nenhuma ação destrói histórico da sessão.
- [ ] **Riscos/observações:** endpoints antigos ainda podem existir apenas sob flag.

## T067 — Provar isolamento e concorrência de serviços [BLOQUEADORA]

- [ ] **Objetivo:** validar duas ações e duas sessões no novo boundary.
- [ ] **Dependências:** T057 a T066.
- [ ] **Arquivos prováveis:** testes de integração/concurrency.
- [ ] **Passos de implementação:** barreiras, stale versions, falhas e múltiplas UoWs.
- [ ] **Testes:** uma confirma/uma 409, sessões paralelas e rollback.
- [ ] **Critério de conclusão:** todos os critérios 14.4–14.7 da spec passam no service layer.
- [ ] **Riscos/observações:** não confundir lock de workspace de agente com sessão.

## Fase 9 — Serviços e APIs

## T068 — Criar infraestrutura HTTP de erros e correlação [BLOQUEADORA]

- [ ] **Objetivo:** padronizar 404, 409, 422, 503 e 500.
- [ ] **Dependências:** T057 e T059.
- [ ] **Arquivos prováveis:** `src/gui/server.py`, serializadores e testes HTTP.
- [ ] **Passos de implementação:** mapear erros, validar JSON e gerar correlation ID.
- [ ] **Testes:** cada status e sanitização de resposta.
- [ ] **Critério de conclusão:** erro de domínio não retorna HTTP 200.
- [ ] **Riscos/observações:** manter compatibilidade antiga somente no handler legado.

## T069 — Implementar endpoints de usuários

- [ ] **Objetivo:** expor list/create/get/update/archive de usuários.
- [ ] **Dependências:** T035 e T068.
- [ ] **Arquivos prováveis:** server/controller de users, testes HTTP.
- [ ] **Passos de implementação:** rotas, validação e serialização.
- [ ] **Testes:** um teste de integração para cada endpoint e usuário arquivado.
- [ ] **Critério de conclusão:** contratos 9.2 da spec passam.
- [ ] **Riscos/observações:** não adicionar autenticação.

## T070 — Implementar endpoints de posts

- [ ] **Objetivo:** expor catálogo, criação, detalhe, update, complete, reopen e archive.
- [ ] **Dependências:** T036 e T068.
- [ ] **Arquivos prováveis:** server/controller de posts, testes HTTP.
- [ ] **Passos de implementação:** rotas parent-scoped e transições.
- [ ] **Testes:** um teste por endpoint, parent mismatch e post arquivado.
- [ ] **Critério de conclusão:** contratos 9.3 da spec passam.
- [ ] **Riscos/observações:** post de outro usuário não pode vazar no catálogo.

## T071 — Implementar endpoints de lifecycle de sessões

- [ ] **Objetivo:** listar/criar/detalhar/concluir/cancelar/arquivar sessões.
- [ ] **Dependências:** T037, T057 e T068.
- [ ] **Arquivos prováveis:** server/controller de sessions, testes HTTP.
- [ ] **Passos de implementação:** routes, attempts e expected lock.
- [ ] **Testes:** um por endpoint, attempts sequenciais, 409 e sessão terminal.
- [ ] **Critério de conclusão:** contratos de lifecycle 9.4 passam.
- [ ] **Riscos/observações:** criar sessão nunca retorna a última terminal.

## T072 — Implementar endpoints de snapshot e eventos

- [ ] **Objetivo:** carregar snapshot selecionado e eventos paginados.
- [ ] **Dependências:** T047, T068 e T071.
- [ ] **Arquivos prováveis:** handlers de snapshot/events, testes HTTP.
- [ ] **Passos de implementação:** GET por ID, paginação e lock version.
- [ ] **Testes:** um por endpoint, sessão ausente, ordem e isolamento.
- [ ] **Critério de conclusão:** frontend não precisa de `/api/session` global.
- [ ] **Riscos/observações:** snapshot é read-only.

## T073 — Implementar endpoints de ações autorais

- [ ] **Objetivo:** expor entrevista, extensão, gateway e briefing por comandos.
- [ ] **Dependências:** T060, T061 e T068.
- [ ] **Arquivos prováveis:** action router, handlers e testes HTTP.
- [ ] **Passos de implementação:** mapear cada action para parâmetros específicos.
- [ ] **Testes:** um teste por ação, lock stale, fase inválida e falha LLM.
- [ ] **Critério de conclusão:** nenhuma ação aceita campo `state`.
- [ ] **Riscos/observações:** validar que IDs pertencem à sessão do path.

## T074 — Implementar endpoints de ações editoriais

- [ ] **Objetivo:** expor storyboard, drafts, seleção e composição.
- [ ] **Dependências:** T062, T063 e T068.
- [ ] **Arquivos prováveis:** action router editorial e testes HTTP.
- [ ] **Passos de implementação:** comandos com block/draft IDs e lock.
- [ ] **Testes:** um por ação, seleção cruzada, execução ativa e retry.
- [ ] **Critério de conclusão:** contratos editoriais 9.5 passam.
- [ ] **Riscos/observações:** body não contém `editorial_flow`.

## T075 — Implementar endpoints de versões, avaliações e exports

- [ ] **Objetivo:** listar/detalhar/transicionar versões e consultar históricos.
- [ ] **Dependências:** T064, T065 e T068.
- [ ] **Arquivos prováveis:** handlers de versions/evaluations/exports, testes HTTP.
- [ ] **Passos de implementação:** rotas da seção 9.6 e ações downstream.
- [ ] **Testes:** um por endpoint, imutabilidade, archive e export failure.
- [ ] **Critério de conclusão:** conteúdo de versão não possui endpoint de update.
- [ ] **Riscos/observações:** publicação é status local, não integração externa.

## T076 — Implementar endpoints de importação legada [ALTO RISCO]

- [ ] **Objetivo:** expor dry run, apply, report/comparison e rollback.
- [ ] **Dependências:** T049 a T056 e T068.
- [ ] **Arquivos prováveis:** handlers de legacy imports, testes HTTP.
- [ ] **Passos de implementação:** validar paths/usuário, chamar services e serializar relatório.
- [ ] **Testes:** um por endpoint, idempotência, path inválido e rollback bloqueado.
- [ ] **Critério de conclusão:** `/api/restore` não é necessário no cliente novo.
- [ ] **Riscos/observações:** limitar tamanho e diretórios de entrada.

## T077 — Deprecar endpoints antigos e medir uso

- [ ] **Objetivo:** manter compatibilidade temporária com telemetria.
- [ ] **Dependências:** T069 a T076.
- [ ] **Arquivos prováveis:** `server.py`, feature flags, logs/metrics e testes.
- [ ] **Passos de implementação:** marcar headers/logs deprecated e bloquear fora dos modos legados.
- [ ] **Testes:** ativo em legacy, desativado em sqlite e contador de uso.
- [ ] **Critério de conclusão:** existe evidência de clientes legados remanescentes.
- [ ] **Riscos/observações:** não remover ainda.

## T078 — Testar concorrência HTTP

- [ ] **Objetivo:** provar isolamento no servidor real.
- [ ] **Dependências:** T071 a T075.
- [ ] **Arquivos prováveis:** testes de integração HTTP concorrente.
- [ ] **Passos de implementação:** iniciar servidor temporário e usar clientes/barreiras.
- [ ] **Testes:** same-session 409, different-session parallel e resposta correta por ID.
- [ ] **Critério de conclusão:** não há `RLock` global serializando sessões diferentes.
- [ ] **Riscos/observações:** evitar testes que só chamem controller diretamente.

## Fase 10 — Frontend

## T079 — Atualizar tipos do frontend

- [ ] **Objetivo:** modelar User, Post, Session, Snapshot, Version, conflitos e comandos.
- [ ] **Dependências:** contratos da Fase 9.
- [ ] **Arquivos prováveis:** `frontend/src/lib/pe-types.ts`, testes de tipos.
- [ ] **Passos de implementação:** remover dependência de request em state completo.
- [ ] **Testes:** build/typecheck e fixtures de resposta.
- [ ] **Critério de conclusão:** tipos incluem selected IDs e lock version.
- [ ] **Riscos/observações:** tipos compatíveis ficam isolados e temporários.

## T080 — Atualizar cliente de API do frontend

- [ ] **Objetivo:** consumir endpoints por ID e comandos pequenos.
- [ ] **Dependências:** T079 e T069 a T076.
- [ ] **Arquivos prováveis:** `frontend/src/lib/pe-api.ts`, testes.
- [ ] **Passos de implementação:** clients de catálogo, snapshot, actions, versions e imports.
- [ ] **Testes:** request paths/bodies e erros 409/422/503.
- [ ] **Critério de conclusão:** nenhum método novo envia `state`.
- [ ] **Riscos/observações:** manter adapter antigo somente sob flag.

## T081 — Refatorar store para seleção explícita [BLOQUEADORA]

- [ ] **Objetivo:** adicionar selected IDs, catálogos e snapshot selecionado.
- [ ] **Dependências:** T079 e T080.
- [ ] **Arquivos prováveis:** `pe-store.tsx`, testes de provider/reducer.
- [ ] **Passos de implementação:** estado por seleção, loading/error e invalidação de cache.
- [ ] **Testes:** troca user/post/session, reload e seleção inexistente.
- [ ] **Critério de conclusão:** não existe uma `session` global sem ID.
- [ ] **Riscos/observações:** resposta tardia não pode atualizar a sessão atualmente selecionada errada.

## T082 — Criar biblioteca de usuários e posts

- [ ] **Objetivo:** listar, criar, selecionar e arquivar raízes.
- [ ] **Dependências:** T081.
- [ ] **Arquivos prováveis:** novos componentes de library, testes.
- [ ] **Passos de implementação:** views, empty states e filtros.
- [ ] **Testes:** dois usuários, vários posts, archive e seleção.
- [ ] **Critério de conclusão:** catálogos refletem isolamento do backend.
- [ ] **Riscos/observações:** User é seleção editorial, sem UI de login.

## T083 — Criar biblioteca de sessões e versões

- [ ] **Objetivo:** listar attempts, retomar, criar tentativa e consultar versões.
- [ ] **Dependências:** T081 e T082.
- [ ] **Arquivos prováveis:** componentes de sessions/versions, testes.
- [ ] **Passos de implementação:** status, timestamps, read-only e ações de lifecycle.
- [ ] **Testes:** múltiplas sessões, sessão terminal e versões.
- [ ] **Critério de conclusão:** retomar não sobrescreve sessão anterior.
- [ ] **Riscos/observações:** seleção pertence à UI.

## T084 — Adaptar Workstation para sessão selecionada [BLOQUEADORA]

- [ ] **Objetivo:** executar workflow por `selectedSessionId`.
- [ ] **Dependências:** T081 e T083.
- [ ] **Arquivos prováveis:** `Workstation.tsx`, store e testes.
- [ ] **Passos de implementação:** carregar snapshot, enviar comandos e tratar terminal/read-only.
- [ ] **Testes:** ações em A não alteram B, troca durante ação e reload.
- [ ] **Critério de conclusão:** Workstation nunca envia snapshot completo.
- [ ] **Riscos/observações:** loading deve ser por sessão/operação.

## T085 — Adaptar ContextBar

- [ ] **Objetivo:** mostrar usuário, post, tentativa, status e versão em foco.
- [ ] **Dependências:** T082 a T084.
- [ ] **Arquivos prováveis:** `ContextBar.tsx`, testes.
- [ ] **Passos de implementação:** breadcrumb/selectors, refresh e nova tentativa.
- [ ] **Testes:** mudança de contexto, sessão arquivada e versão.
- [ ] **Critério de conclusão:** botões globais save/reload/reset são removidos ou redefinidos.
- [ ] **Riscos/observações:** metadata do post não é draft amplo da sessão.

## T086 — Implementar tratamento de conflitos e execução ativa

- [ ] **Objetivo:** reagir a 409 sem perda de entrada local.
- [ ] **Dependências:** T080, T081 e T084.
- [ ] **Arquivos prováveis:** store, componentes de feedback e testes.
- [ ] **Passos de implementação:** preservar input, refetch, informar e reaplicar comando seguro.
- [ ] **Testes:** stale lock, LLM ativa e sessões diferentes.
- [ ] **Critério de conclusão:** cliente nunca reenvia snapshot antigo.
- [ ] **Riscos/observações:** reaplicação automática somente para comandos comprovadamente seguros.

## T087 — Substituir reset e restore no frontend

- [ ] **Objetivo:** usar nova tentativa, limpeza local e importador.
- [ ] **Dependências:** T076, T083 e T085.
- [ ] **Arquivos prováveis:** store, dialogs, library e testes.
- [ ] **Passos de implementação:** remover reset destrutivo e restore de documento.
- [ ] **Testes:** limpar formulário, criar tentativa, importar e cancelar.
- [ ] **Critério de conclusão:** nenhuma ação da UI destrói histórico.
- [ ] **Riscos/observações:** mensagens devem explicar archive versus nova tentativa.

## T088 — Adaptar Dev Drawer

- [ ] **Objetivo:** mostrar IDs, lock, comando, parâmetros e correlação.
- [ ] **Dependências:** T080, T081 e T087.
- [ ] **Arquivos prováveis:** `DevDrawer.tsx`, testes.
- [ ] **Passos de implementação:** remover state editável/restore e adicionar snapshot read-only.
- [ ] **Testes:** ausência de full state request e controle de conteúdo sensível.
- [ ] **Critério de conclusão:** Dev Drawer não reintroduz fonte de verdade no cliente.
- [ ] **Riscos/observações:** prompt/stdout só com ação explícita de desenvolvimento.

## T089 — Executar testes frontend e E2E multi-entidade [BLOQUEADORA]

- [ ] **Objetivo:** provar fluxos de seleção, isolamento, conflito e restart.
- [ ] **Dependências:** T079 a T088.
- [ ] **Arquivos prováveis:** testes unitários frontend e E2E.
- [ ] **Passos de implementação:** cenários com dois usuários, posts, sessões e duas abas.
- [ ] **Testes:** catálogos, Workstation, 409, read-only, reset e ausência de state.
- [ ] **Critério de conclusão:** frontend novo opera só pelas APIs novas.
- [ ] **Riscos/observações:** não limitar E2E a visibilidade de componentes.

## Fase 11 — Corte definitivo

## T090 — Executar janela de shadow read e aprovar readiness [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** comprovar ausência de divergência crítica e uso relevante do legado.
- [ ] **Dependências:** T055, T077, T078 e T089.
- [ ] **Arquivos prováveis:** relatórios de rollout, dashboards e decisão registrada.
- [ ] **Passos de implementação:** observar período definido, classificar divergências e uso de endpoints.
- [ ] **Testes:** simular limiar excedido e bloqueio de corte.
- [ ] **Critério de conclusão:** gate formal aprova corte e ausência de cliente legado ativo.
- [ ] **Riscos/observações:** não remover código apenas por busca estática.

## T091 — Ensaiar backup e rollback do corte [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** validar backup consistente e recuperação sem JSON estagnado.
- [ ] **Dependências:** T053 e T090.
- [ ] **Arquivos prováveis:** runbook, scripts administrativos e testes.
- [ ] **Passos de implementação:** checkpoint/backup API, restore em cópia e export compatível.
- [ ] **Testes:** restaurar banco, reiniciar e validar hashes/contagens.
- [ ] **Critério de conclusão:** rollback ensaiado preserva dados até o ponto de corte.
- [ ] **Riscos/observações:** incluir arquivos WAL/SHM de forma correta.

## T092 — Tornar SQLite o mode default [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** promover SQLite a fonte operacional.
- [ ] **Dependências:** T090 e T091.
- [ ] **Arquivos prováveis:** configuração/bootstrap, documentação e testes.
- [ ] **Passos de implementação:** mudar default, manter flag de emergência e registrar cutover.
- [ ] **Testes:** startup, restart, catálogos e workflow sem JSON.
- [ ] **Critério de conclusão:** aplicação funciona com `current-session.json` ausente.
- [ ] **Riscos/observações:** flag de emergência deve apontar para backup/compat export, não JSON velho.

## T093 — Interromper escrita de JSON e JSONL de domínio [BLOQUEADORA] [ALTO RISCO]

- [ ] **Objetivo:** eliminar os writers legados após o corte.
- [ ] **Dependências:** T092.
- [ ] **Arquivos prováveis:** `persistence.py`, `session_log.py`, AgentWrapper e testes.
- [ ] **Passos de implementação:** desligar snapshot e logs primários, manter leitor/importer read-only.
- [ ] **Testes:** nenhuma alteração de mtime do JSON; eventos/execuções no banco.
- [ ] **Critério de conclusão:** novos comandos não dependem dos arquivos.
- [ ] **Riscos/observações:** logger de diagnóstico opcional não pode ser fonte de restauração.

## T094 — Remover endpoints e adapters de estado completo [ALTO RISCO]

- [ ] **Objetivo:** remover `/api/session` global, restore e action/update com state.
- [ ] **Dependências:** T090, T092 e T093.
- [ ] **Arquivos prováveis:** `server.py`, controllers, frontend adapters e testes.
- [ ] **Passos de implementação:** remover rotas, DTOs e feature flags expiradas.
- [ ] **Testes:** 404/410 nos endpoints removidos e suite nova intacta.
- [ ] **Critério de conclusão:** nenhuma API aceita documento completo.
- [ ] **Riscos/observações:** remoção só após a prova de uso de T090.

## T095 — Remover mutações e métodos legados de persistência [ALTO RISCO]

- [ ] **Objetivo:** eliminar código morto de sessão global e save/load operacional.
- [ ] **Dependências:** T093 e T094.
- [ ] **Arquivos prováveis:** `persistence.py`, `session_app.py`, `session_controller.py`, testes legados.
- [ ] **Passos de implementação:** manter apenas importer/export de compatibilidade necessário.
- [ ] **Testes:** suite completa, import legado e restart SQLite.
- [ ] **Critério de conclusão:** nenhum service chama `_persistir()` ou `salvar_sessao()`.
- [ ] **Riscos/observações:** remover somente após busca de runtime e testes.

## T096 — Finalizar documentação e observabilidade operacional [P]

- [ ] **Objetivo:** documentar migrations, backup, restore, conflitos, retenção e suporte.
- [ ] **Dependências:** T092 a T095.
- [ ] **Arquivos prováveis:** README/docs/runbooks e dashboards/logs.
- [ ] **Passos de implementação:** atualizar operação, troubleshooting e modelo de dados.
- [ ] **Testes:** validar comandos/runbook em ambiente temporário.
- [ ] **Critério de conclusão:** operador consegue migrar, diagnosticar e restaurar.
- [ ] **Riscos/observações:** documentar Prompt Registry como banco separado.

## T097 — Auditar dependências restantes do legado [BLOQUEADORA]

- [ ] **Objetivo:** procurar e classificar qualquer dependência ainda ativa.
- [ ] **Dependências:** T093 a T096.
- [ ] **Arquivos prováveis:** todo o repositório, relatório de auditoria e testes.
- [ ] **Passos de implementação:** busca estática, testes runtime e inspeção de tráfego/configuração.
- [ ] **Testes:** procurar `current-session.json`, JSONL como persistência, sessão global, envio de estado completo e métodos legados.
- [ ] **Critério de conclusão:** ocorrências restantes são apenas importer, fixtures ou documentação explicitamente justificada.
- [ ] **Riscos/observações:** também buscar aliases, paths construídos e chamadas indiretas.

## T098 — Validar todos os critérios de aceite [BLOQUEADORA]

- [ ] **Objetivo:** executar a matriz completa da seção 14 de `spec.md`.
- [ ] **Dependências:** T001 a T097.
- [ ] **Arquivos prováveis:** suite de aceitação, relatório final e evidências de execução.
- [ ] **Passos de implementação:** executar migrations, dois usuários, vários posts/sessões, restart, versões, concorrência, import, rollback, frontend e corte.
- [ ] **Testes:** todos os critérios 14.1 a 14.12, incluindo ausência de estado global e JSON como fonte.
- [ ] **Critério de conclusão:** todos os critérios passam; desvios bloqueiam a conclusão da migração.
- [ ] **Riscos/observações:** esta é a última tarefa e não pode ser substituída por aprovação manual sem evidência.
