# Plano — Migração incremental para SQLite

## 1. Estratégia geral

A implementação será incremental e reversível. O JSON atual continua
operacional enquanto a infraestrutura, o schema, os repositories e a
reconstrução de snapshots são comprovados.

Sequência de modos:

```text
legacy
    ↓
dual_write
    ↓
sqlite_shadow_read
    ↓
sqlite
```

O plano evita big bang por quatro razões:

1. o estado atual mistura verdade, projeções e transitórios;
2. o histórico legado é incompleto;
3. backend e frontend dependem do documento completo;
4. concorrência e versionamento exigem nova fronteira de comandos.

## 2. Regras de execução do plano

- Cada fase precisa cumprir seu critério de avanço.
- Migrations são aplicadas antes de repositories que as usam.
- SQL de domínio fica restrito a migrations e repositories.
- Todo novo repository recebe teste próprio.
- Todo endpoint recebe teste de integração HTTP.
- O Prompt Registry não é alterado por migrations do domínio.
- Feature flags controlam o modo de persistência.
- Métricas de divergência são requisito de rollout.
- A remoção do legado só ocorre após auditoria de uso.
- Nenhuma transação fica aberta durante LLM ou escrita de export.
- Commits devem ser pequenos e reversíveis conforme a ordem recomendada.

## 3. Componentes previstos

Estrutura indicativa, sujeita aos nomes já usados pelo projeto:

```text
src/content_engine/
  db/
    connection.py
    migrations.py
    unit_of_work.py
    migrations/
  domain/
    users.py
    posts.py
    sessions.py
    interview.py
    editorial.py
    versions.py
    evaluations.py
    llm_executions.py
    legacy_imports.py
  repositories/
  snapshots/
  legacy/
  services/
```

O objetivo não é obrigar uma reorganização total. Os módulos existentes podem
ser adaptados gradualmente, desde que as responsabilidades da spec sejam
mantidas.

## 4. Fase 1 — Infraestrutura SQLite

### Objetivo

Criar conexão, configuração, migration runner e banco isolado de testes sem
alterar o fluxo funcional atual.

### Dependências

- nenhuma fase anterior;
- decisões de path e pragmas da spec;
- definição de feature mode inicial `legacy`.

### Arquivos ou módulos afetados

- novo pacote de banco em `src/content_engine/`;
- configuração de paths;
- arquivos SQL de migration;
- bootstrap da CLI/GUI;
- fixtures de testes;
- documentação de operação.

### Alterações esperadas

- default `.data/post-engine.sqlite3`;
- conexão por unidade de trabalho/request;
- `foreign_keys=ON`;
- WAL;
- `busy_timeout` configurável;
- decisão documentada de `synchronous`;
- controle explícito de transação;
- migration runner com checksum;
- primeira migration de `schema_migrations`;
- banco temporário por teste;
- feature mode `legacy | dual_write | sqlite_shadow_read | sqlite`;
- startup valida migrations sem tocar no Prompt Registry.

### Testes necessários

- conexão aplica todos os pragmas;
- duas conexões independentes funcionam;
- banco novo recebe migrations;
- reexecução é no-op;
- checksum alterado falha;
- falha de migration faz rollback;
- Prompt Registry não é aberto pelo runner;
- arquivo temporário é descartado após teste.

### Riscos

- reutilizar conexão entre threads;
- confundir migration do domínio com registry;
- copiar comportamento do runner existente sem checksum/rollback suficiente;
- WAL não ser considerado no backup.

### Critério para avançar

Infraestrutura inicia em modo `legacy`, cria/valida o banco de domínio e todos
os testes da fase passam sem mudar `current-session.json`.

### Rollback

Desabilitar bootstrap do banco e remover apenas o arquivo SQLite ainda vazio ou
de desenvolvimento. O fluxo JSON permanece intacto.

## 5. Fase 2 — Schema principal

### Objetivo

Criar as raízes relacionais e a trilha básica de sessão.

### Dependências

- Fase 1 concluída.

### Arquivos ou módulos afetados

- migrations de `users`, `posts`, `sessions`, `session_constraints` e
  `session_events`;
- testes de migration/schema;
- modelos mínimos de estado e enums.

### Alterações esperadas

- PKs UUID textuais;
- timestamps UTC;
- status e transições de user/post/session;
- `attempt_number` único por post;
- `lock_version`;
- índices de catálogo;
- archive timestamps;
- sequência única de eventos.

### Testes necessários

- foreign keys;
- checks de enum e boolean;
- uniqueness de attempt;
- índices esperados;
- arquivamento sem cascata destrutiva;
- inserção de evento ordenado;
- upgrade de migration anterior.

### Riscos

- modelar “sessão atual” no domínio;
- permitir criação sob usuário/post arquivado;
- esquecer índice em FK;
- usar hard delete como fluxo comum.

### Critério para avançar

É possível criar dois usuários, vários posts e várias sessões com isolamento de
chaves e eventos append-only, ainda sem integrar o workflow.

### Rollback

Reverter a feature que cria entidades. Em desenvolvimento, recriar banco a
partir da migration anterior; em ambiente com dados, usar migration forward de
correção, nunca editar migration aplicada.

## 6. Fase 3 — Schema autoral

### Objetivo

Representar entrevista, avaliações, evidências, dimensões, lacunas, gateways e
briefings sem um documento de sessão.

### Dependências

- Fase 2;
- enums e contratos atuais de entrevista mapeados.

### Arquivos ou módulos afetados

- migrations do agregado autoral;
- modelos de entrevista;
- testes de schema e integridade.

### Alterações esperadas

- `interview_rounds`;
- `interview_questions` e issues;
- `interview_answers`;
- `interview_answer_assessments` e itens;
- `authorial_evidence` e tipos;
- sinais e vínculos;
- `authorial_dimensions`, evidências e regras;
- `authorial_gaps`;
- `authorial_gateways` e itens;
- `briefings` e relações congeladas.

### Testes necessários

- preservação de candidatas rejeitadas;
- uma resposta por pergunta;
- resposta original imutável;
- avaliação revisionada;
- N:N de sinais/evidências;
- dimensão única por avaliação;
- gateway sequencial;
- um briefing consolidado ativo;
- restrições de estado e FK.

### Riscos

- reproduzir duplicações do JSON;
- salvar apenas o “último” gateway;
- não preservar ordem;
- tornar briefing outro snapshot autoritativo.

### Critério para avançar

Um cenário completo de entrevista pode ser inserido, consultado e reconstruído
sem `interview_state` armazenado como JSON.

### Rollback

Manter migrations aplicadas, mas não ativar writers autorais. Como o modo ainda
é `legacy`, o fluxo atual continua sendo a fonte.

## 7. Fase 4 — Schema editorial

### Objetivo

Representar storyboard, drafts, seleção, versões, segmentos, ajustes,
avaliações e exports.

### Dependências

- Fase 3;
- briefing relacional;
- regras de versionamento aprovadas.

### Arquivos ou módulos afetados

- migrations editoriais;
- enums/modelos de conteúdo;
- testes de schema e índices.

### Alterações esperadas

- cabeçalho `storyboards` e blocos;
- abordagens;
- drafts revisionados;
- seleções históricas;
- `post_versions`;
- segmentos e bullets;
- ajustes;
- avaliações e itens;
- exports.

### Testes necessários

- storyboard revisions;
- blocos ordenados;
- draft por approach/revisão;
- índice parcial de seleção ativa;
- versão sequencial por post;
- imutabilidade de conteúdo;
- segmentos por versão;
- ajuste ligado à origem e resultado;
- alvos válidos de avaliação;
- export completo exige hash/path/tamanho.

### Riscos

- usar status de composição como versão;
- atualizar versão existente;
- alocar `version_number` fora de transação;
- remover drafts obsoletos em vez de supersedê-los.

### Critério para avançar

O banco representa duas revisões de storyboard, múltiplos drafts, troca de
seleção, duas versões e seus históricos sem overwrite.

### Rollback

Não ativar o writer editorial. Dados experimentais podem ser descartados com o
banco de teste; migrations de ambientes persistentes recebem correções forward.

## 8. Fase 5 — Execuções de LLM

### Objetivo

Criar rastreabilidade ponta a ponta de cada chamada e substituir `is_running`
por estado durável de execução.

### Dependências

- Fases 2 a 4;
- contrato atual do Prompt Registry compreendido;
- política inicial de retenção definida.

### Arquivos ou módulos afetados

- migration de `llm_executions` e `llm_execution_events`;
- repository/gateway mínimo de execução, depois integrado à UoW comum;
- adapter do Prompt Registry;
- `agent_wrapper.py`;
- `llm_workspace.py`;
- services que resolvem prompts;
- reconciliação de startup;
- testes de execução.

### Alterações esperadas

- UUID criado antes da resolução;
- mesmo UUID passado ao Prompt Registry;
- provider/model/tool/reasoning/sandbox efetivos persistidos;
- prompt, stdout, stderr, retorno e erro por execução;
- eventos ordenados;
- índice parcial para uma execução ativa por sessão;
- estados `queued`, `running` e terminais;
- heartbeat/reconciliação para `interrupted`;
- nenhum FK cross-database;
- chamadas externas fora da transação.

### Testes necessários

- vínculo por ID com referência do registry;
- domínio funciona sem registry disponível para leitura histórica;
- segunda execução na mesma sessão é rejeitada;
- sessões distintas podem reservar execuções;
- falha, timeout, cancelamento e interrupção;
- ordenação de eventos;
- rollback da reserva;
- nenhuma transação aberta no fake agent bloqueante.

### Riscos

- guardar volume ilimitado;
- registrar prompt em logs além do necessário;
- abrir transação antes da LLM e só fechar depois;
- criar ID diferente no registry;
- considerar JSONL como segunda fonte.

### Critério para avançar

Uma chamada fake completa produz registro, eventos, referência ao registry e
resultado terminal; chamadas de sessões diferentes não compartilham lock.

### Rollback

Manter o logger JSONL e o fluxo antigo como fallback enquanto o feature mode é
`legacy`. Desabilitar o writer de execução sem remover tabelas.

## 9. Fase 6 — Modelos, mapeadores e repositories

### Objetivo

Introduzir a camada de acesso transacional e impedir SQL disperso.

### Dependências

- schemas das Fases 2 a 5 estáveis.

### Arquivos ou módulos afetados

- modelos de domínio;
- mapeadores row↔objeto;
- repositories por agregado;
- unidade de trabalho;
- factories de services;
- testes unitários e de repository.

### Alterações esperadas

- repositories definidos na spec;
- UoW com commit/rollback;
- queries de catálogo;
- queries para reconstrução;
- compare-and-swap de sessão;
- alocação transacional de attempts, versões e sequências;
- erros de domínio para `not found`, conflito e estado inválido;
- nenhuma dependência do React/HTTP nos repositories.

### Testes necessários

- teste próprio por repository;
- round-trip de cada modelo;
- paginação/ordenação;
- rollback entre múltiplos repositories;
- optimistic locking;
- alocação concorrente de número;
- archive filters;
- conexão fechada no sucesso e erro.

### Riscos

- repository fazer commit implícito;
- misturar row model e snapshot;
- criar conexão singleton;
- N+1 excessivo na reconstrução;
- invariantes duplicadas de forma divergente.

### Critério para avançar

Todos os agregados podem ser criados e consultados exclusivamente por
repositories/UoW, com testes transacionais passando.

### Rollback

Services atuais ainda não dependem obrigatoriamente dos repositories.
Desabilitar factories novas preserva o caminho legado.

## 10. Fase 7 — Compatibilidade com estado legado

### Objetivo

Decompor o JSON, reconstruir snapshot relacional, importar dados e comprovar
equivalência antes da refatoração final.

### Dependências

- Fase 6;
- matriz de mapeamento do research;
- política de usuário alvo e JSONL decidida.

### Arquivos ou módulos afetados

- `src/content_engine/persistence.py`;
- novo pacote `legacy/`;
- assemblers de snapshot;
- comparador canônico;
- dual writer;
- migration/import service;
- CLI/API administrativa temporária;
- testes de fixtures legadas.

### Alterações esperadas

- parser estrito do schema `4.0`;
- importador idempotente;
- dry run;
- relatório e backup;
- deduplicação de cópias;
- registro de dados não recuperáveis;
- montagem de snapshot compatível a partir do SQLite;
- comparação campo a campo;
- feature modes;
- dual write sem esconder falhas;
- shadow read;
- telemetria de divergência.

### Testes necessários

- fixtures reais anonimizadas;
- JSON válido, ausente, inválido e schema antigo;
- dry run sem escrita;
- idempotência;
- rollback total;
- duplicações exatas;
- cópias divergentes;
- `is_running` para `interrupted`;
- JSONL válido/inválido/ambíguo;
- comparação de snapshot;
- falha de um dos writers.

### Riscos

- alto risco de perda ou duplicação;
- inventar histórico;
- atribuir log a sessão errada;
- dual write divergir;
- rollback remover dependências posteriores.

### Critério para avançar

O JSON real e fixtures representativas são importados idempotentemente; o
snapshot reconstruído coincide nos campos autoritativos ou produz divergências
explicadas e catalogadas.

### Rollback

Voltar feature mode a `legacy`. Manter banco/import reports para análise.
Restaurar backup apenas se a importação tiver alterado uma base compartilhada.

## 11. Fase 8 — Refatoração da sessão

### Objetivo

Remover o estado de sessão global dos serviços e tornar `session_id` e
`lock_version` explícitos.

### Dependências

- Fases 6 e 7;
- snapshot assembler validado;
- repositories capazes de carregar agregados por ID.

### Arquivos ou módulos afetados

- `session_app.py`;
- `session_controller.py`;
- `session_log.py`;
- `editorial_flow.py`;
- `editorial_actions.py`;
- `generator.py`;
- `exporter.py`;
- serviços de entrevista/avaliação/ajuste;
- factories/controllers;
- testes existentes.

### Alterações esperadas

- services recebem IDs, parâmetros e UoW;
- `TuiSessionState` deixa de ser objeto mutável global;
- compatibilidade temporária usa mapeadores;
- ações carregam somente o agregado necessário;
- compare-and-swap em cada comando;
- lock em memória por `session_id`;
- lock global removido das operações de domínio;
- fases e downstream são transacionados;
- flags `is_running` e `_segmento_index` deixam o domínio;
- reset vira nova tentativa/revisão/limpeza local.

### Testes necessários

- cada ação com sessão explícita;
- duas instâncias de serviço sem vazamento;
- conflito de lock;
- rollback de regra inválida;
- falha de LLM não avança fase;
- sessões diferentes executam em paralelo;
- sessão terminal rejeita mutação;
- compatibilidade de snapshots antigos durante rollout.

### Riscos

- refatoração ampla;
- mutações ocultas em métodos existentes;
- double persist durante compatibilidade;
- lock em memória vazar entradas;
- fase derivada divergir do banco.

### Critério para avançar

Nenhum serviço editorial depende de uma instância global de
`TuiSessionState`; todas as mutações de domínio usam `session_id`, UoW e lock
otimista.

### Rollback

Manter adapters que chamam os serviços novos a partir do controller legado.
Retornar o roteamento aos adapters sem remover repositories nem dados.

## 12. Fase 9 — Serviços e APIs

### Objetivo

Expor catálogos, sessões, versões, ações e importação pelos contratos novos.

### Dependências

- Fase 8;
- services transacionais;
- tratamento de erros definido.

### Arquivos ou módulos afetados

- `src/gui/server.py`;
- controllers HTTP;
- serialização de respostas;
- serviços de aplicação;
- testes HTTP;
- endpoints legados sob flag.

### Alterações esperadas

- endpoints de usuários, posts, sessões, versões e imports;
- `/sessions/{id}/snapshot`;
- `/sessions/{id}/actions/{action}`;
- body de comando específico;
- `expected_lock_version`;
- status 404/409/422/503/500;
- paginação de eventos/catálogos;
- ID de correlação;
- deprecation/telemetria dos endpoints antigos;
- nenhuma restauração direta de documento no contrato novo.

### Testes necessários

- teste HTTP por endpoint;
- validação de parent ownership;
- conflito 409;
- regra inválida 422;
- busy 503;
- erro interno sanitizado;
- action não aceita full state;
- clientes simultâneos em sessões diferentes;
- endpoints antigos atrás da flag.

### Riscos

- controller novo manter cache global mutável;
- retornar 200 com erro embutido, como hoje;
- aceitar IDs de entidades de outra sessão;
- vazar prompts/paths internos.

### Critério para avançar

Um cliente HTTP consegue executar o fluxo por IDs, e os testes provam que o
snapshot enviado pelo cliente não é aceito como fonte de verdade.

### Rollback

Manter endpoints antigos ativos por feature flag durante `dual_write` e
`sqlite_shadow_read`. Reverter frontend para cliente antigo sem apagar dados.

## 13. Fase 10 — Frontend

### Objetivo

Introduzir seleção de usuário/post/sessão, biblioteca e comandos pequenos.

### Dependências

- Fase 9;
- contratos HTTP estáveis;
- UX de criação/arquivamento definida.

### Arquivos ou módulos afetados

- `frontend/src/lib/pe-store.tsx`;
- `frontend/src/lib/pe-api.ts`;
- `frontend/src/lib/pe-types.ts`;
- `ContextBar.tsx`;
- `Workstation.tsx`;
- `DevDrawer.tsx`;
- novos componentes de biblioteca/seleção;
- testes frontend/E2E.

### Alterações esperadas

- `selectedUserId`, `selectedPostId`, `selectedSessionId`;
- catálogos;
- snapshot por sessão;
- commands com IDs/lock;
- tratamento de 409;
- preservação de entrada local;
- navegação por biblioteca;
- sessão terminal read-only;
- nova tentativa;
- ContextBar com identidade de contexto;
- remoção de save/restore de estado inteiro;
- reset local ou histórico;
- Dev Drawer orientado a comandos/IDs.

### Testes necessários

- reducers/provider de seleção;
- troca rápida de sessão sem mistura;
- commands sem campo `state`;
- conflito e refresh;
- criação de usuário/post/sessão;
- retomada após reload;
- reset não chama endpoint destrutivo;
- E2E com dois usuários e múltiplas sessões;
- E2E com duas abas/sessões.

### Riscos

- cache antigo reaparecer ao trocar seleção;
- ação terminar depois da troca e atualizar sessão errada;
- manter `draftRef` amplo por compatibilidade indefinida;
- estados de loading globais bloquearem outras sessões.

### Critério para avançar

O frontend completo opera somente pelos endpoints novos em
`sqlite_shadow_read`, sem enviar estado completo e com critérios E2E aprovados.

### Rollback

Feature flag seleciona UI antiga enquanto endpoints legados ainda existem.
Persistência SQLite continua recebendo dual write para não perder validação.

## 14. Fase 11 — Corte definitivo

### Objetivo

Tornar SQLite a única fonte de verdade e remover dependências ativas do legado.

### Dependências

- Fases 1 a 10;
- período de shadow read concluído;
- divergências críticas zeradas;
- backup e rollback ensaiados.

### Arquivos ou módulos afetados

- bootstrap/configuração default;
- `persistence.py`;
- `session_log.py`;
- `server.py`;
- store/API frontend;
- CLI;
- documentação;
- scripts administrativos;
- testes de aceitação e auditoria.

### Alterações esperadas

- modo default `sqlite`;
- escrita JSON desligada;
- JSONL deixa de ser persistência primária;
- endpoints `/api/session`, estado amplo e `/api/restore` removidos;
- adapters legados removidos;
- backups finais;
- checkpoint/backup SQLite;
- documentação de operação e recuperação;
- alarmes/observabilidade;
- auditoria por busca de dependências antigas.

### Testes necessários

- suite completa;
- aceitação da spec;
- reinício sem `current-session.json`;
- duas sessões simultâneas;
- restauração de backup;
- migration de banco anterior;
- import final;
- ausência de tráfego legado;
- busca estática e runtime por APIs/métodos antigos.

### Riscos

- cliente antigo ainda ativo;
- rollback usar JSON estagnado;
- remover logger antes de confirmar eventos no banco;
- backup incompleto de WAL;
- dependência oculta em teste/script.

### Critério de conclusão

Todos os critérios de aceite da spec passam e SQLite é a única fonte de verdade
de domínio.

### Rollback

Restaurar backup consistente do banco ou gerar snapshot de compatibilidade a
partir dele. Não reativar automaticamente o JSON pré-corte. O rollback é
executado por runbook e registrado.

## 15. Coexistência temporária

### 15.1 Pode coexistir

| Componente legado | Componente novo | Limite |
| --- | --- | --- |
| JSON writer | SQLite writer | somente em `dual_write`, com divergência registrada |
| Snapshot JSON | Snapshot relacional | somente comparação/compatibilidade |
| Endpoints antigos | Endpoints por ID | endpoints antigos deprecated e medidos |
| Frontend antigo | Frontend novo | feature flag, sem misturar contratos na mesma ação |
| JSONL | eventos LLM no SQLite | JSONL como fallback/diagnóstico temporário |
| `TuiSessionState` | modelos relacionais | dataclass apenas como DTO compatível |
| Prompt Registry SQLite | domínio SQLite | permanentemente separados |
| arquivos exportados | catálogo `exports` | permanentemente: conteúdo em arquivo, metadata no DB |

### 15.2 Não pode coexistir como fonte autoritativa

- JSON e SQLite decidindo fase independentemente;
- alocação de versão nos dois stores;
- duas seleções ativas para o mesmo bloco;
- `is_running` e `llm_executions.status` como verdades concorrentes;
- estado completo do frontend sobrescrevendo banco;
- restauração arbitrária após SQLite virar default;
- controller global e controllers por sessão no mesmo endpoint;
- conteúdo mutável em `post_versions`.

## 16. Ordem recomendada de commits

Cada item deve permanecer pequeno o suficiente para revisão e rollback:

1. configuração/path/feature mode sem mudança funcional;
2. conexão SQLite e pragmas;
3. migration runner e `schema_migrations`;
4. fixtures/banco de teste;
5. migration users/posts;
6. migration sessions/events/constraints;
7. migration entrevista básica;
8. migration avaliações/evidências/sinais;
9. migration dimensões/gaps/gateway/briefing;
10. migration storyboard/blocks;
11. migration approaches/drafts/selections;
12. migration versions/segments/adjustments;
13. migration evaluations/exports;
14. migration LLM executions/events;
15. modelos e mapeadores principais;
16. repositories de users/posts;
17. repository de sessions/events;
18. repositories autorais;
19. repositories editoriais;
20. repositories de versions/evaluations/exports;
21. repository de LLM;
22. UoW e testes transacionais;
23. snapshot assembler;
24. comparador canônico;
25. importer dry run;
26. importer apply/rollback;
27. dual writer;
28. shadow read e métricas;
29. execução LLM com ID compartilhado;
30. lock otimista;
31. refatoração de uma ação simples por vez;
32. refatoração de entrevista;
33. refatoração editorial;
34. refatoração versions/evaluation/export;
35. endpoints de catálogos;
36. endpoints de sessões/snapshot;
37. endpoints de ações;
38. endpoints de versions/import;
39. frontend tipos/API;
40. frontend seleção e biblioteca;
41. frontend Workstation/ContextBar;
42. frontend conflitos/reset/Dev Drawer;
43. ativação `sqlite_shadow_read`;
44. correções de divergência;
45. ativação `sqlite`;
46. remoção de endpoints/writers legados;
47. documentação e auditoria final.

Commits de schema não devem incluir repository, API e frontend juntos.

## 17. Estratégia de testes

### 17.1 Unitários

- regras de transição;
- validação de enums;
- UUID/timestamp;
- mapeadores;
- cálculo de fingerprints;
- normalização de snapshot;
- classificação de divergência;
- regras de importação.

### 17.2 Repositories

Um arquivo/suite por repository:

- create/get/list;
- parent scope;
- ordenação;
- archive filters;
- unicidade;
- FKs;
- round-trip;
- estados inválidos;
- ausência de commits implícitos.

### 17.3 Migrations

- banco vazio até latest;
- upgrade incremental;
- reexecução;
- checksum;
- rollback em falha;
- índices, triggers/checks e FKs;
- Prompt Registry intacto.

### 17.4 Transacionais

- UoW com múltiplos repositories;
- rollback integral;
- lock_version;
- attempt/version/sequence concorrentes;
- evento atômico com ação;
- reserva/finalização de LLM em transações separadas.

### 17.5 Integração HTTP

- um teste por endpoint;
- JSON inválido;
- parent mismatch;
- 404/409/422/503/500;
- lock version;
- paginação;
- nenhum full state;
- clientes concorrentes.

### 17.6 Frontend

- store/provider;
- seleção e caches;
- API client;
- comandos;
- conflito;
- loading por sessão;
- biblioteca;
- reset;
- componentes read-only;
- Dev Drawer.

### 17.7 Concorrência

- mesma sessão, mesma versão;
- mesma sessão, execução LLM duplicada;
- sessões diferentes com barreira para provar simultaneidade;
- múltiplas conexões SQLite;
- busy timeout;
- recuperação de execução órfã;
- dois processos, se suporte for aprovado.

### 17.8 Migração

- snapshots reais anonimizados;
- duplicações;
- divergências;
- schemas inválidos;
- dry run;
- idempotência;
- rollback;
- JSONL ambíguo;
- export scan, se habilitado;
- shadow comparison.

### 17.9 Aceitação

Executar a matriz integral da seção 14 de `spec.md`, incluindo:

- dois usuários;
- vários posts;
- várias sessões;
- restart;
- isolamento;
- versões;
- concorrência;
- importação;
- rollback;
- frontend sem estado completo;
- corte sem JSON.

## 18. Estratégia de rollout

1. Aplicar migrations com modo `legacy`.
2. Importar cópia da sessão atual em ambiente de teste.
3. Ativar dual write para desenvolvimento.
4. Medir e corrigir falhas de decomposição.
5. Ativar shadow read sem alterar resposta.
6. Rodar frontend novo contra APIs por ID.
7. Definir janela de observação e limiar de divergência.
8. Criar backup e ensaiar restore.
9. Ativar `sqlite` de forma reversível.
10. Observar erros, busy, conflitos e execuções.
11. Remover legado somente após ausência comprovada de uso.

## 19. Decisões que devem ser fechadas por fase

| Decisão | Prazo máximo |
| --- | --- |
| `synchronous` e `busy_timeout` | Fase 1 |
| usuário alvo de importação | início da Fase 7 |
| retenção de payloads LLM | início da Fase 5 |
| importação de JSONL | início da Fase 7 |
| scan de exports | início da Fase 7 |
| suporte multi-processo | antes dos testes finais de Fase 8 |
| cancelamento de processo externo | Fase 5/8 |
| duração e limiar de shadow read | antes da Fase 11 |
| retenção de arquivos legados | antes do corte |
