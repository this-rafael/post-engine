# Research — Persistência relacional do Post Engine

## 1. Objetivo e método

Este documento registra o estado real do Post Engine antes da migração da
persistência de sessão para SQLite. Ele foi produzido a partir da leitura de:

- `README.md`;
- `docs/PRD.md`;
- `specs/global.md`;
- `specs/checklist.md`;
- especificações 058 a 061;
- implementação de persistência, schemas, controllers, servidor HTTP e serviços
  editoriais;
- store, API e tipos do frontend React;
- implementação e banco local do Prompt Registry;
- testes de persistência, entrevista, fluxo editorial, GUI, Prompt Registry e
  E2E;
- artefatos existentes em `.data/` e `exports/`.

Quando o código, a documentação e os artefatos divergem, este documento trata o
código e os dados atuais como evidência primária e registra a divergência.

## 2. Resumo executivo

O Post Engine possui hoje uma única raiz de estado mutável,
`TuiSessionState`, carregada de `.data/sessions/current-session.json` por uma
única instância de `SessionController`. O servidor HTTP usa
`ThreadingHTTPServer`, mas todas as requisições de domínio passam por um único
`GuiController` protegido por um único `RLock`. Na prática:

- existe uma sessão de domínio ativa por processo;
- todos os clientes HTTP compartilham e podem alterar a mesma sessão;
- ações diferentes são serializadas, inclusive chamadas longas de LLM;
- o frontend envia uma cópia ampla do estado de volta em cada ação;
- não existe `session_id` explícito nos contratos editoriais;
- não existe compare-and-swap, `lock_version` ou proteção entre processos;
- a gravação do JSON não é atômica;
- reiniciar a aplicação restaura apenas o último snapshot válido;
- resetar substitui o snapshot atual, sem preservar uma entidade de sessão
  consultável;
- os logs JSONL retêm rastros extensos, mas não constituem uma fonte relacional
  reconstruível nem possuem ligação estável com o Prompt Registry.

O Prompt Registry já usa SQLite com migrations, foreign keys, WAL,
`busy_timeout` e transações explícitas. Ele é, contudo, um banco de
infraestrutura de prompts, não o banco do domínio editorial. O banco de domínio
deve permanecer separado e referenciar execuções do registry por identificador
textual e metadados copiados, sem foreign key entre bancos.

O JSON atual contém dados úteis, projeções derivadas, dados transitórios e
duplicações exatas. No arquivo real analisado:

- `evidence_ledger` no topo é igual ao ledger dentro de `interview_state`;
- `gateway_result` no topo é igual ao gateway dentro de `interview_state`;
- partes importantes de `briefing_autoral` repetem entrevista, evidências,
  sinais, dimensões e gateway;
- a composição editorial repete `conteudo_gerado` e `conteudo_json`.

Portanto, migrar o documento integral para uma coluna JSON preservaria os
problemas atuais. A fonte de verdade precisa ser relacional, com snapshots
reconstruídos para compatibilidade e apresentação.

## 3. Persistência atual

### 3.1 Inventário de arquivos

| Artefato | Formato | Responsabilidade atual | Criação | Leitura | Atualização | Exclusão |
| --- | --- | --- | --- | --- | --- | --- |
| `.data/sessions/current-session.json` | JSON indentado, schema `4.0` | Snapshot completo da única sessão corrente | `salvar_sessao()` e inicialização do app | `carregar_sessao()` | Diversas ações chamam `_persistir()` | Não há função de exclusão; reset sobrescreve |
| `.data/sessions/logs/*.jsonl` | Uma linha JSON por evento | Log de sessão e de execução de agentes | `SessionLogger` | Uso humano/testes; não é restaurado para o domínio | `append` por evento | Não há rotação ou exclusão |
| `.data/agent-config.yml` | YAML | Configuração global de provider/model/reasoning/sandbox por operação | `ensure_default_config_file()` | Resolução de configuração das operações | Endpoint/configuração de LLM | Não há fluxo normal de exclusão |
| `.data/prompt-registry.sqlite3` | SQLite | Artefatos, versões, operações, composições e referências de resolução de prompts | Migration runner do Prompt Registry | Repositories/resolver/API do registry | Transações do registry | Sem exclusão destrutiva normal de versões |
| `.data/prompt-registry.backup-*.sqlite3` | SQLite | Backups do Prompt Registry | Migrações/manutenção do registry | Recuperação manual | Não atualizado | Manual |
| `.data/sessions/*.json` adicionais | JSON | Snapshots/importações/regressões manuais | Fluxos auxiliares e uso manual | Restauração/importação manual | Variável | Manual |
| `exports/*` | Markdown, JSON ou SlideMark JSON | Resultado exportado pelo usuário | `exporter.py` | Fora do fluxo de restauração | Pode ser sobrescrito pelo mesmo caminho | Manual |

No workspace analisado havia:

- um `current-session.json` de aproximadamente 385 KB;
- um snapshot `import-terminal-ready.json`;
- 16 arquivos JSONL totalizando aproximadamente 59 MB;
- um `prompt-registry.sqlite3` com dados reais;
- nenhum `.data/post-engine.sqlite3`;
- nenhuma saída presente em `exports/` no momento da inspeção.

Os números são evidência local, não requisitos de capacidade.

### 3.2 `current-session.json`

#### Localização e formato

`src/content_engine/persistence.py` define:

- diretório padrão `.data/sessions`;
- nome fixo `current-session.json`;
- schema obrigatório `4.0`;
- serialização de todo o `TuiSessionState` em um único objeto JSON.

O payload contém `schema_version` e 35 campos de sessão. Os objetos de
entrevista e fluxo editorial ficam aninhados.

#### Criação

`PostEngineApp.__init__` chama `carregar_sessao()`, normaliza o estado, garante
um logger e chama `_persistir()` imediatamente. Assim, o arquivo é criado mesmo
quando não havia sessão anterior.

O argumento `restore_session` é armazenado, mas não altera esse comportamento:
a restauração ocorre de forma incondicional.

#### Leitura e restauração

`carregar_sessao()`:

1. retorna estado novo se o arquivo não existir;
2. lê o arquivo inteiro;
3. faz parse JSON;
4. exige objeto no topo;
5. exige schema `4.0` no topo e na entrevista;
6. converte o documento de volta para `TuiSessionState`.

Erros de I/O, Unicode e parse JSON retornam silenciosamente uma sessão nova.
Schema ausente ou diferente também resulta em sessão nova no caminho de carga
normal. A restauração explícita pela API é mais estrita e rejeita payload
inválido.

#### Atualização

`salvar_sessao()` usa escrita direta no caminho final. Não existe:

- arquivo temporário;
- `fsync`;
- rename atômico;
- file lock;
- checksum;
- geração de snapshot;
- compare-and-swap;
- journal próprio;
- backup anterior à escrita.

Qualquer `_persistir()` reserializa o documento inteiro.

#### Pontos de persistência automática

Há persistência após ou durante:

- inicialização do app;
- início da entrevista;
- envio de resposta;
- diagnóstico de lacunas;
- início e envio de extensão;
- geração de pergunta;
- encerramento da entrevista;
- atualização e continuação do gateway;
- limpeza da entrada;
- reset global e reset de fase;
- mudanças de navegação/fase;
- geração, retry e limpeza do conteúdo;
- segmentação;
- avaliação;
- aplicação de ajustes;
- export;
- restauração de payload;
- geração, edição e limpeza de storyboard;
- início, progresso parcial e conclusão de rascunhos por bloco;
- retry de rascunho;
- seleção de opção;
- composição.

No fluxo de rascunhos, o JSON pode ser regravado várias vezes para uma única
ação: `generating`, abordagens disponíveis, cada opção em execução, cada
resultado e status final.

`GuiController.update()` e `GuiController.action()` também persistem no
`finally`, o que pode repetir uma gravação já realizada pelo serviço.

#### Falhas

Falha de escrita em `_persistir()` é capturada como `OSError` e ignorada. O
estado em memória pode avançar enquanto o snapshot em disco permanece antigo.

Falha ou interrupção durante `Path.write_text()` pode deixar arquivo parcial ou
inválido. Na próxima inicialização, esse erro é tratado como ausência de estado;
o app cria uma sessão nova e a persiste no mesmo caminho. Isso pode apagar a
principal evidência do snapshot corrompido.

Não há transação envolvendo:

- mudança em memória;
- log JSONL;
- resolução do Prompt Registry;
- escrita do snapshot;
- criação do arquivo exportado.

Cada artefato pode refletir um ponto diferente da execução.

#### Reinício

Com JSON válido, o reinício recupera somente o último snapshot. Com JSON
ausente, inválido ou incompatível, começa uma sessão vazia. Estados
intermediários já persistidos, como geração parcial de opções, reaparecem, mas
não há mecanismo geral de recuperação de uma execução LLM que estava em curso.

`is_running` é persistido como booleano. Se o processo morrer com o campo
verdadeiro, não existe reconciliação durável baseada em uma entidade de
execução; o valor pode ficar obsoleto.

### 3.3 Logs JSONL

`SessionLogger` cria um identificador textual baseado em timestamp e fragmento
aleatório e grava em `.data/sessions/logs/{session_id}.jsonl`.

Cada linha contém:

- timestamp UTC;
- `session`;
- tipo de evento;
- operação;
- payload variável.

`AgentWrapper` registra, entre outros dados:

- prompt renderizado;
- stdin;
- comando;
- stdout;
- stderr;
- eventos estruturados;
- retorno;
- erro.

O logger usa append simples e pode suprimir `OSError` quando configurado para
escrita segura. Não existe:

- schema versionado por evento;
- sequência transacional;
- rotação;
- retenção;
- índice;
- associação obrigatória a uma entidade de execução LLM;
- associação garantida a usuário, post ou sessão relacional;
- importação no reinício;
- replay como mecanismo suportado.

O reset global cria novo logger e novo caminho, mas mantém os arquivos antigos.
Isso preserva rastros, porém sem catálogo consultável.

### 3.4 Configuração YAML dos agentes

`.data/agent-config.yml` guarda configurações por operação, incluindo provider,
model, reasoning e sandbox. O arquivo é global à instalação, não à sessão.

Ele é:

- criado com defaults na inicialização;
- lido durante a resolução de cada operação;
- atualizado pela API de configuração;
- usado para escolher a execução efetiva.

Os campos `tool`, `model` e `sandbox` no topo da sessão não são uma fonte
confiável para auditoria de cada chamada. A configuração efetiva deve ser
copiada para cada futura `llm_execution`.

Não há motivo identificado para mover a configuração global ao banco de
domínio nesta migração.

### 3.5 Prompt Registry SQLite

O Prompt Registry já usa `sqlite3` e possui:

- tabela de migrations;
- artefatos e versões imutáveis;
- operações;
- composições e itens;
- referências de resolução de prompt;
- foreign keys habilitadas por conexão;
- WAL;
- `busy_timeout`;
- transações explícitas, incluindo `BEGIN IMMEDIATE`;
- backups e verificações de versão/hash.

No banco local analisado havia três migrations aplicadas e centenas de
referências de resolução.

O resolver gera ou recebe um `execution_id` e registra:

- operação;
- composição e versão;
- versões dos artefatos em JSON;
- hash do template;
- hash do prompt resolvido;
- provider;
- model;
- horário;
- origem, rollout e fallback;
- erro de resolução.

Hoje os consumidores normalmente pegam apenas `resolved_content` e descartam os
metadados de resolução. O `AgentWrapper` cria seu log separadamente. Portanto,
não há vínculo estável, ponta a ponta, entre:

1. resolução no Prompt Registry;
2. sessão editorial;
3. chamada do processo/agente;
4. stdout/stderr;
5. entidade produzida.

Esse vínculo deverá ser introduzido no banco de domínio por um UUID de execução
criado antes da resolução e reutilizado como referência textual no registry.

### 3.6 Arquivos exportados

`src/content_engine/exporter.py` grava:

- Markdown;
- JSON auxiliar;
- SlideMark JSON, quando aplicável.

O caminho é derivado de slug/nome e pode ser explicitamente informado. A
escrita ocorre diretamente no filesystem. A sessão não mantém um catálogo
durável de exports com:

- versão de origem;
- hash;
- tamanho;
- status;
- timestamps;
- erro;
- histórico de tentativas.

O arquivo pode ser sobrescrito pelo mesmo caminho. A ação atualiza apenas
mensagens de estado da sessão e o snapshot.

## 4. Estrutura atual da sessão

### 4.1 Convenções da análise

Nas tabelas:

- **Verdade**: dado autoritativo atual;
- **Derivado**: projeção reproduzível a partir de outros dados;
- **Transitório**: estado operacional ou exclusivamente de interface;
- **Compatibilidade**: existe para transportar/reconstruir o documento atual;
- **JSON admissível**: somente quando o conteúdo é bruto, flexível ou não
  participa de relacionamentos, filtros, ordenação, status, concorrência,
  versionamento ou auditoria.

### 4.2 Campos de topo de `TuiSessionState`

| Campo | Tipo atual | Significado e origem | Quem altera | Classificação | Persistir? | Destino provável | JSON admissível? |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `schema_version` | texto | Versão do documento, acrescentada pelo serializer | Persistência | Compatibilidade | Em `legacy_imports`; schema do banco usa migrations | `schema_migrations`, `legacy_imports` | Só no payload legado |
| `session_id` | texto | ID do logger/sessão corrente | Inicialização e reset | Verdade atual, formato legado | Sim | `sessions.id` novo UUID e `legacy_session_id` | Não |
| `session_log_path` | texto | Caminho do JSONL | Inicialização/reset | Derivado/diagnóstico | Não como domínio | referência de importação ou metadado de diagnóstico | Sim, apenas relatório |
| `current_phase` | texto | Fase macro do workflow | App e reconciliação de fase | Verdade de workflow | Sim | `sessions.workflow_phase` | Não |
| `current_stage` | texto | Tela/estágio selecionado | Navegação e frontend | Transitório de UI | Não no domínio | estado React/localStorage | Não necessário |
| `fases_liberadas` | lista de texto | Fases liberadas | Reconciliação | Derivado | Não | calculado no snapshot | Não |
| `tema` | texto | Tema inicial do conteúdo | Frontend/entrada | Verdade editorial | Sim | `posts.theme` e snapshot da tentativa quando necessário | Não |
| `plataforma` | texto | Plataforma de destino | Frontend/entrada | Verdade editorial | Sim | `posts.platform` e/ou `post_versions.platform` | Não |
| `objetivo_do_post` | texto | Objetivo editorial | Frontend/entrada | Verdade editorial | Sim | `posts.objective` | Não |
| `personalidade` | texto | Personalidade/voz escolhida | Frontend/entrada | Verdade configurável | Sim | default do `post` e snapshot em sessão/versão | Não |
| `tipo_de_post` | enum texto | `post`, `article`, `short_carousel`, `long_slide` | Frontend/entrada | Verdade editorial | Sim | `posts.content_type` e `post_versions.content_type` | Não |
| `slides_gerados` | lista de objetos | Projeção de slides | Generator/parser | Derivado de conteúdo estruturado | Sim apenas se compuser versão | `segments` e documento SlideMark | Documento SlideMark pode ser JSON |
| `tool` | enum texto | Ferramenta exibida no estado | Frontend/legado | Compatibilidade; não prova execução | Não como auditoria | configuração global; valor efetivo em `llm_executions` | Não |
| `model` | texto nulo | Modelo exibido no estado | Frontend/legado | Compatibilidade; potencialmente obsoleto | Não como auditoria | `llm_executions.model` | Não |
| `sandbox` | enum texto | Sandbox exibido no estado | Frontend/legado | Compatibilidade; potencialmente obsoleto | Não como auditoria | config global e `llm_executions.sandbox` | Não |
| `briefing_autoral` | objeto | Projeção consolidada da entrevista | `build_briefing()` | Derivado, hoje usado como entrada | Sim, mas normalizado | `briefings` e associações | Snapshot só para compatibilidade/diagnóstico |
| `restricoes_de_geracao` | lista texto | Restrições editoriais | Entrada/serviços | Verdade de decisão | Sim | restrições da sessão/post em linhas ordenadas | Não |
| `interview_state` | objeto nulo | Estado completo da entrevista V4 | Controller de entrevista | Mistura verdade, derivados e transitórios | Sim decomposto | agregado autoral relacional | Apenas respostas LLM brutas |
| `evidence_ledger` | lista objetos | Cópia do ledger da entrevista | Sincronização de estado | Duplicado derivado | Sim uma vez | `authorial_evidence` | Não |
| `gateway_result` | objeto | Cópia do gateway da entrevista | Sincronização de estado | Duplicado derivado | Sim uma vez | `authorial_gateways` e itens | Não |
| `fase_atual` | texto | Rótulo operacional legado | Serviços | Derivado/transitório | Não | snapshot/evento | Não |
| `status_operacional` | texto | Mensagem humana da última operação | Serviços | Transitório | Opcional como evento | `session_events.message` | Não |
| `prompt_renderizado` | texto | Último prompt utilizado | Serviços de LLM | Auditoria da última execução, não da sessão | Sim por execução | `llm_executions.prompt_text` | Texto, não JSON |
| `stdout` | texto | Último stdout | `AgentWrapper`/serviços | Auditoria da última execução | Sim por execução | `llm_executions.stdout_text` | Texto |
| `stderr` | texto | Último stderr | `AgentWrapper`/serviços | Auditoria da última execução | Sim por execução | `llm_executions.stderr_text` | Texto |
| `returncode` | inteiro nulo | Retorno da última execução | `AgentWrapper`/serviços | Auditoria | Sim por execução | `llm_executions.return_code` | Não |
| `events` | lista objetos | Eventos do último agente | `AgentWrapper` | Auditoria variável | Sim por execução | `llm_execution_events`; payload bruto opcional | Sim para payload externo residual |
| `error` | texto nulo | Último erro apresentado | Serviços/controller | Transitório e auditoria | Evento e execução | `session_events`, `llm_executions.error_message` | Não |
| `conteudo_gerado` | texto | Conteúdo composto/gerado atual | Generator/composição/ajuste | Verdade de uma versão, mas sobrescrita hoje | Sim imutável por versão | `post_versions.content_text` | Não |
| `conteudo_json` | objeto | Conteúdo estruturado e metadados | Parser/composição | Mistura estrutura consultável e documento flexível | Sim decomposto | `post_versions`, `segments`; documento SlideMark residual | Apenas documento/metadata flexível justificada |
| `segmentos` | lista objetos | Segmentos ordenados do conteúdo | Segmentador/ajustes | Verdade da versão atual | Sim | `segments` | Não |
| `avaliacao_post` | objeto | Última avaliação do conteúdo | Avaliador | Verdade histórica atualmente sobrescrita | Sim | `evaluations`, `evaluation_items` | Raw LLM opcional |
| `is_running` | booleano | Flag de execução atual | App/controller | Transitório e inseguro após crash | Não como booleano | derivado de `llm_executions.status` | Não |
| `_segmento_index` | inteiro nulo | Segmento em foco na UI | Ajustes/UI | Transitório | Não | estado React | Não |
| `editorial_flow` | objeto | Storyboard, opções, seleção e composição | `editorial_actions.py` | Mistura verdade, derivados e status | Sim decomposto | agregado editorial e versões | Só raw LLM/metadados residuais |

### 4.3 `interview_state`

| Seção/campo | Tipo | Significado/origem | Responsável | Natureza | Destino relacional |
| --- | --- | --- | --- | --- | --- |
| `schema_version` | texto | Versão V4 da entrevista | Serializer | Compatibilidade | `legacy_imports` |
| `context.tema` | texto | Tema congelado para a entrevista | Início da entrevista | Verdade | post/snapshot de sessão |
| `context.objetivo` | texto | Objetivo congelado | Início | Verdade | post/snapshot de sessão |
| `context.formato` | texto | Formato congelado | Início | Verdade | post/snapshot de sessão |
| `context.personalidade` | texto | Voz congelada | Início | Verdade | sessão/versão |
| `context.restricoes[]` | textos | Restrições de contexto | Início | Verdade | restrições ordenadas |
| `progress_state` | enum texto | Progresso autoral | Controller | Verdade de workflow | `sessions` ou último estado autoral |
| `question_count` | inteiro | Número corrente | Controller | Derivado de perguntas | consulta/contador validado |
| `max_questions` | inteiro | Limite da tentativa | Controller | Regra da sessão | `sessions.max_questions` |
| `questions[]` | objetos | Perguntas efetivamente selecionadas | Exploração | Verdade histórica | `interview_questions` |
| `candidates[]` | objetos | Candidatas da rodada corrente | Exploração | Verdade parcial, sobrescrita | `interview_questions` com status candidato |
| `answers[]` | objetos | Respostas originais/normalizadas | Usuário/controller | Verdade imutável | `interview_answers` |
| `evidence_ledger[]` | objetos | Evidências extraídas | Validação | Verdade autoral derivada com proveniência | `authorial_evidence` |
| `signals[]` | objetos | Sinais autorais | Validação | Verdade derivada versionável | tabela auxiliar de sinais e vínculos |
| `dimensions{}` | mapa | Último score por dimensão | Avaliação determinística | Última projeção; histórico perdido | `authorial_dimensions` por avaliação/revisão |
| `deterministic_assessment` | objeto nulo | Última avaliação por regras | Validação | Resultado histórico hoje sobrescrito | avaliação autoral, dimensões e regras |
| `llm_assessment` | objeto nulo | Última avaliação LLM | Validação | Resultado histórico hoje sobrescrito | `interview_answer_assessments` e itens |
| `gateway_result` | objeto nulo | Último gateway | Gateway | Resultado histórico hoje sobrescrito | `authorial_gateways` e itens |
| `gaps[]` | objetos | Lacunas atuais | Diagnóstico/gateway | Resultado histórico hoje sobrescrito | `authorial_gaps` |
| `deepening_decision` | objeto nulo | Decisão de perguntar/encerrar | Exploração | Resultado de decisão | gateway/evento/rodada |
| `current_question` | objeto nulo | Pergunta aguardando resposta | Controller | Estado de workflow | pergunta com status pendente |
| `closure_reason` | texto | Razão do encerramento | Controller | Verdade histórica | sessão/rodada |
| `round_title` | texto | Título da rodada atual | Title service | Verdade apresentacional | `interview_rounds.title` |
| `round_titles{}` | mapa inteiro→texto | Títulos anteriores | Controller | Verdade apresentacional | `interview_rounds.title` |
| `extension_batches_completed` | inteiro | Lotes extras concluídos | Controller | Derivado/controle | consulta de rodadas ou coluna de controle |
| `pending_batch[]` | perguntas | Lote de extensão ainda em edição | Controller/UI | Estado incompleto | perguntas com status pendente |
| `pending_answers{}` | mapa ID→texto | Rascunhos de respostas do lote | Frontend/controller | Transitório de UI | não persistir no domínio; opcional draft explícito futuro |
| `gap_diagnosis` | texto | Diagnóstico textual atual | Serviço de gaps | Resultado histórico | rodada/gateway ou execução associada |

#### Objetos aninhados da entrevista

| Objeto | Campos persistidos | Destino |
| --- | --- | --- |
| Candidata | `text`, `direction`, `risk_scores`, `relation_score`, `discovery_score`, `answerability_score`, `accepted`, `issues`, `source`, `why_now` | pergunta; riscos e issues em colunas/linhas explícitas |
| Pergunta selecionada | `question`, `why_now`, `source`, `direction`, `candidate_id` | `interview_questions` |
| Resposta | `id`, `question_id`, `question`, `original`, `normalized`, `sequence` | `interview_answers`; texto da pergunta no objeto é cópia de compatibilidade |
| Evidência | `id`, `text`, `source_answer_id`, `signal_types`, `origin` | `authorial_evidence` e vínculos de tipo |
| Sinal | `id`, `type`, `summary`, `confidence`, `origin`, `source_answer_id`, `evidence_ids`, `status` | sinais e tabela de associação com evidências |
| Dimensão | `dimension_id`, alias `id`, `score`, `state`, `evidence_ids`, `rules_triggered`, `rationale`, `essential`, `critical` | `authorial_dimensions`, associações de evidência e regras; alias não é persistido duas vezes |
| Avaliação determinística | `dimensions`, `global_score`, `vetos`, `evidence_count`, `answer_count`, `rules_triggered`, `approved` derivado | avaliação autoral, itens e dimensões |
| Avaliação LLM | `approved`, alias `llm_approved`, `confidence`, `strengths`, `weaknesses`, `risks`, `justification`, `epistemic_integrity`, `parse_error`, `source` | `interview_answer_assessments` e itens; alias removido |
| Lacuna | `type`, `dimension`, `relevance`, `expected_gain`, `critical`, `reason`, `suggested_question` | `authorial_gaps` |
| Decisão de aprofundamento | `should_ask`, `reason`, `selected_gap`, `why_now`, `marginal_gain`, `closure_reason` | rodada/gateway/evento e referência à lacuna |
| Gateway | `approved`, `gateway_type`, alias `tipo_gateway`, `llm_approved`, `heuristic_approved`, `balanced`, `strong_imbalanced`, `global_score`, `exceptional_dimensions`, `weak_dimensions`, `vetoes`, `relevant_gaps`, `justification`, `llm_confidence` | `authorial_gateways`, `authorial_gaps` e itens; alias removido |

`risk_scores` é um mapa hoje. Os riscos conhecidos usados na validação devem
virar colunas ou itens tipados. Chaves desconhecidas podem ser preservadas em
metadata de importação, mas não devem controlar regras sem normalização.

### 4.4 `briefing_autoral`

`build_briefing()` produz:

- `schema_version`;
- `theme`;
- `objective`;
- `format`;
- `personality`;
- `progress_state`;
- `answers`;
- `evidence`;
- `signals`;
- `dimensions`;
- `gateway`;
- `gaps`;
- `closure_reason`.

É uma projeção quase integral do agregado de entrevista. Hoje ela é usada como
entrada para geração e, por isso, funciona como snapshot conveniente, mas não
deve duplicar a fonte de verdade. O banco deve registrar uma revisão de
`briefings` ligada ao gateway que a consolidou e reconstruir seu conteúdo por
joins. Um snapshot JSON pode ser retido apenas:

- durante compatibilidade;
- para comparação shadow;
- para auditoria de um prompt já executado.

### 4.5 `editorial_flow`

| Caminho | Tipo | Natureza atual | Destino |
| --- | --- | --- | --- |
| `schema_version` | texto | Compatibilidade | importação/migration |
| `briefing_fingerprint` | texto | Hash derivado para invalidação | calculado ou snapshot de revisão |
| `storyboard.version` | inteiro | Revisão | entidade `storyboards.revision_number` |
| `storyboard.status` | texto | Estado | `storyboards.status` |
| `storyboard.blocks[]` | lista | Verdade editorial | `storyboard_blocks` |
| bloco `id` | texto | ID legado | UUID novo + legacy ID |
| bloco `order` | inteiro | Ordenação | coluna explícita |
| bloco `role` | texto | Papel do bloco | coluna explícita |
| bloco `focus` | texto | Foco | coluna explícita |
| bloco `revision` | inteiro | Revisão de origem | storyboard/revisão |
| `drafts.storyboard_version` | inteiro | Referência à revisão | foreign key |
| `drafts.by_block` | mapa | Agrupamento por ID | relações por `block_id` |
| entrada `status` | texto | Estado agregado de geração | derivado dos drafts ou job |
| entrada `options[]` | lista | Opções geradas | approaches e drafts |
| entrada `selected_option_id` | texto nulo | Seleção ativa | `block_draft_selections` |
| entrada `error` | texto nulo | Último erro | execução/evento |
| entrada `provider`, `model` | texto | Config efetiva de abordagens | `llm_executions` |
| opção `id` | texto | ID legado | `block_drafts.id`/legacy ID |
| opção `approach` | objeto | `title` e `description` gerados | `block_approaches` |
| opção `persona_id`, `persona_name` | texto | Persona sorteada | `block_drafts` |
| opção `content` | texto | Rascunho | `block_drafts.content_text` |
| opção `status` | texto | Estado do rascunho | coluna explícita |
| opção `obsolete` | booleano | Invalidação | status/superseded timestamp |
| opção `error` | texto nulo | Falha | execução/draft |
| opção `provider`, `model` | texto | Config efetiva | `llm_executions` |
| `composition.status` | texto | Estado da composição | versão/execução |
| `composition.selection_fingerprint` | texto | Hash derivado | calculado e opcionalmente auditado |
| `composition.conteudo` | texto | Cópia do conteúdo final | `post_versions` |
| `composition.conteudo_json` | objeto | Cópia da estrutura final | versão/segmentos/documento |

Atualizar o storyboard invalida e apaga `drafts.by_block` no snapshot, marcando
opções antigas como obsoletas apenas antes de remover a coleção. O modelo
relacional deve manter as revisões e marcar relações antigas como superseded,
sem destruição.

### 4.6 Conteúdo, segmentos e avaliação

`conteudo_json` é um objeto variável produzido pelos parsers. Foram observadas
chaves como conteúdo, metadata, alertas, slides, sugestões, SlideMark,
`parse_error` e resposta bruta. A migração deve separar:

- conteúdo textual e status em `post_versions`;
- slides/segmentos ordenados em `segments`;
- campos de decisão em colunas;
- documento SlideMark em JSON permitido;
- resposta bruta e erro de parse na execução LLM;
- metadata flexível sem uso em regras em JSON limitado.

Cada segmento atual contém:

- `id`;
- `ordem`;
- `texto`;
- `papel_interno`.

Estruturas de slide podem conter:

- `numero`;
- `titulo`;
- `bullets`;
- `notas_visuais`;
- sugestão de imagem com `modo`, `descricao`, `url` e `fonte`.

`avaliacao_post` contém:

- `score.tese`;
- `score.progressao`;
- `score.concretude`;
- `score.precisao_tecnica`;
- `score.retencao`;
- `score.autoridade`;
- `score.autoria`;
- `score.slidemark`;
- `score.revisao_textual`;
- `score.total`, derivado;
- `veredito`;
- `pontos_fortes`;
- `pontos_fracos`;
- `trechos_fracos`, com `trecho`, `problema`, `severidade`, `motivo`;
- `redundancias`;
- `falhas_tecnicas`;
- `sugestoes_melhoria`.

Esses dados participam de filtro, auditoria e decisões de ajuste; devem ser
normalizados em `evaluations` e `evaluation_items`.

## 5. Premissas de sessão única

### 5.1 Backend

| Premissa | Evidência | Consequência |
| --- | --- | --- |
| Um controller mutável global | `run_gui_server()` cria um `GuiController` e um `SessionController` | Todos os clientes compartilham estado |
| Um arquivo fixo | `SESSION_FILE = current-session.json` | Nova tentativa sobrescreve a anterior |
| Um lock global | `GuiController` usa um único `RLock` | Sessões hipotéticas seriam serializadas |
| Endpoints sem ID | `/api/session`, `/api/action`, `/api/restore` | Não há roteamento para uma sessão |
| Estado completo entra na ação | body possui `state` | Frontend pode reintroduzir estado obsoleto |
| Estado completo sai da API | snapshot inclui `asdict(state)` | Forte acoplamento ao documento interno |
| Flag global | `state.is_running` | Não identifica execução nem sessão concorrente |
| Reset global | substitui `self.state` | Histórico do snapshot corrente é perdido |
| Restauração global | `/api/restore` ativa um documento inteiro | Documento enviado vira fonte de verdade |
| Eventos sem identidade de domínio | JSONL usa ID textual do logger | Não há user/post/session/LLM FK |

`SessionController` herda `PostEngineApp` e adapta métodos da antiga UI, mas não
introduz repositório ou isolamento.

### 5.2 Frontend

`PostEngineProvider` mantém:

- um único `snapshot`;
- uma única `session`;
- um `draftRef` contendo cópia ampla do estado;
- um único `busy`/`runState`;
- ações globais de salvar, recarregar, restaurar e resetar.

Não existem:

- `selectedUserId`;
- `selectedPostId`;
- `selectedSessionId`;
- catálogo de usuários;
- catálogo de posts;
- catálogo de sessões;
- cache de snapshots por sessão.

`withAction()` envia `state: draftRef.current` junto da ação. `saveSession()`
também envia o draft amplo. O Dev Drawer explicita e permite copiar o estado
enviado a `/api/action`, além de restaurar JSON de sessão.

`ContextBar` edita atributos da única sessão e oferece ações globais.
`Workstation` apresenta um único pipeline. O reset é descrito como irreversível
porque efetivamente substitui o documento corrente.

### 5.3 Riscos de vazamento

- Dois navegadores conectados ao mesmo servidor observam e alteram a mesma
  sessão.
- Um cliente com snapshot antigo pode enviar campos editáveis antigos antes de
  uma ação nova e sobrescrever alterações já aceitas.
- Mensagens, stdout, erro e conteúdo da última operação são globais.
- Configuração de navegação e segmento selecionado mistura interface e domínio.
- Uma restauração enviada por qualquer cliente troca o estado para todos.
- Um reset em um cliente afeta todos.
- Se múltiplos processos usarem o caminho padrão, ambos escrevem o mesmo JSON
  sem lock interprocesso.

## 6. Fluxo de dados atual

```text
Componentes React
    ↓ usam
PostEngineProvider / pe-store
    ↓ envia snapshot amplo
pe-api
    ↓ HTTP
GuiRequestHandler
    ↓ usa controller singleton
GuiController + RLock global
    ↓ aplica patch de state
SessionController / PostEngineApp
    ↓ muta
TuiSessionState
    ↓ entrega cópias amplas a
entrevista / editorial / generator / evaluator / exporter
    ↓ chama
_persistir()
    ↓ reserializa tudo
current-session.json
```

Em paralelo, uma execução LLM segue:

```text
serviço de domínio
    ↓ resolve operação
agent-config.yml + Prompt Registry SQLite
    ↓ retorna prompt resolvido
AgentWrapper
    ↓ processo externo
stdout/stderr/events
    ↓
TuiSessionState + JSONL
    ↓
current-session.json ao fim ou em pontos intermediários
```

### 6.1 Onde o estado completo circula

- `GET /api/session` retorna o dataclass inteiro e projeções adicionais;
- `PATCH /api/session` aceita múltiplos campos do estado;
- `POST /api/action` recebe `action`, `state` e parâmetros;
- `GuiController.action()` aplica o `state` recebido antes do dispatch;
- serviços recebem `TuiSessionState` e o mutam;
- `_persistir()` serializa o estado inteiro;
- `/api/restore` aceita e ativa um documento completo;
- o frontend mantém e reenvia o documento.

Não existe um comando editorial pequeno do tipo “selecionar draft X na sessão
Y, se lock_version for N” como fronteira da fonte de verdade.

## 7. Concorrência

### 7.1 Duas ações na mesma sessão

Dentro de um processo, o `RLock` impede execução simultânea física, mas não
impede perda lógica de atualização:

1. clientes A e B leem o mesmo snapshot;
2. A altera e persiste;
3. B envia seu snapshot antigo junto de outra ação;
4. o controller aplica os campos de B;
5. a ação de B persiste o documento combinado.

Não há versão esperada nem conflito HTTP.

O backend também não usa `is_running` como trava robusta. Uma segunda ação longa
pode esperar o lock e executar depois, mesmo que tenha sido solicitada com uma
visão antiga.

### 7.2 Duas sessões diferentes

O servidor atual não possui duas sessões de domínio. Mesmo se o controller
fosse duplicado em memória, o caminho padrão fixo ainda colidiria.

Instâncias programáticas podem receber caminhos diferentes em alguns testes,
mas a CLI/GUI normal não oferece seleção ou roteamento por sessão.

### 7.3 Execução simultânea de agentes

As chamadas são síncronas e realizadas enquanto o lock global do
`GuiController` está retido. O fluxo editorial gera as três opções de um bloco
sequencialmente. Portanto, a implementação atual não explora concorrência entre
sessões e mantém requisições não relacionadas bloqueadas durante a LLM.

### 7.4 Escrita concorrente no JSON

Entre processos:

- não há lock;
- a gravação não é atômica;
- o último escritor vence;
- um leitor pode observar conteúdo parcial;
- duas instâncias podem compartilhar o mesmo `session_id` carregado;
- appends JSONL concorrentes não têm garantia de transação ou sequência.

### 7.5 Requisitos inferidos

O modelo futuro precisa de duas proteções diferentes:

1. **optimistic locking da sessão**: `sessions.lock_version`, incrementado em
   cada comando transacional; versão antiga gera conflito;
2. **lock de execução por sessão**: no máximo uma `llm_execution` ativa por
   sessão, reforçada no banco e por lock curto no processo.

Sessões diferentes devem poder executar LLMs simultaneamente. A transação
SQLite não deve permanecer aberta durante a chamada externa. O fluxo esperado
é:

1. transação curta reserva a execução;
2. commit;
3. chamada externa sem transação;
4. transação curta grava resultado e aplica transição válida;
5. commit ou rollback.

WAL melhora concorrência entre leitores e escritor, mas SQLite continua com um
escritor por vez. Isso exige transações curtas e índices adequados.

## 8. Prompt Registry e separação de bancos

### 8.1 O que pertence ao Prompt Registry

- catálogo de artefatos de prompt;
- versões;
- operações;
- composições;
- itens de composição;
- rollout/fallback;
- hashes;
- referências de resolução.

### 8.2 O que pertence ao banco de domínio

- usuários, posts e sessões;
- entrevista e decisões autorais;
- storyboard, drafts e seleções;
- versões, segmentos e ajustes;
- avaliações e exports;
- execução concreta da LLM, seu estado, saída, erro e entidade resultante;
- eventos de domínio;
- importação do legado.

### 8.3 Por que manter separado

- ciclos de vida e responsabilidades são diferentes;
- o registry pode ser atualizado/restaurado independentemente;
- o banco de domínio não deve depender da presença física de uma versão antiga
  do registry para consultar seu histórico;
- reduz risco de migrations editoriais alterarem prompts;
- preserva o caminho `.data/prompt-registry.sqlite3` e contratos existentes;
- permite backup e retenção específicos.

### 8.4 Referências possíveis

`llm_executions` pode armazenar:

- `prompt_registry_execution_id`;
- operação;
- composição e versão;
- hashes de template e prompt resolvido;
- versões dos artefatos;
- provider/model efetivos;
- eventual estado de fallback.

Esses valores são cópias de auditoria, não foreign keys.

### 8.5 Ausência de foreign key entre bancos

SQLite aplica foreign keys dentro do mesmo schema/banco. Anexar bancos com
`ATTACH` não fornece uma foreign key portátil e durável entre arquivos
independentes. Além disso, uma FK acoplaria backup, restore, migrations e
retenção dos dois bancos.

A integridade deve ser:

- identidade textual compartilhada;
- validação na aplicação quando disponível;
- metadados denormalizados no momento da execução;
- tolerância a registry ausente, restaurado ou podado.

## 9. Testes existentes e lacunas

### 9.1 Cobertura existente

Há testes para:

- round-trip do JSON schema `4.0`;
- rejeição de schema antigo;
- sessão nova em arquivo ausente;
- persistência de entrevista e fluxo editorial após reinício;
- persistência após falha inicial de LLM e retry;
- logger e registro de prompt/stdout;
- fluxo de storyboard, drafts, composição, avaliação e SlideMark;
- migrations, transações, imutabilidade e optimistic checks do Prompt Registry;
- comportamento direto do `GuiController`;
- visibilidade e ordem de elementos em E2E.

### 9.2 Lacunas

Não foi encontrada cobertura específica para:

- escrita atômica do snapshot;
- corrupção no meio da escrita;
- múltiplos processos no JSON;
- duas ações concorrentes na mesma sessão;
- duas sessões diferentes;
- conflito por versão;
- transação de domínio e rollback;
- migrations do domínio;
- importer idempotente;
- comparação shadow;
- integração HTTP real por endpoint de domínio;
- ausência de envio do estado inteiro pelo frontend;
- vínculo estável entre Prompt Registry e execução concreta;
- recuperação de execução interrompida;
- isolamento entre usuários/posts/sessões.

Os testes chamados de “isolation” encontrados tratam principalmente do
workspace temporário de agentes, não de isolamento de sessões de domínio.

## 10. Alternativas arquiteturais

### 10.1 `sqlite3` nativo

**Vantagens**

- já é usado com sucesso pelo Prompt Registry;
- não adiciona dependência;
- expõe claramente transações e locking;
- adequado ao volume local esperado;
- facilita SQL explícito e migrations auditáveis.

**Desvantagens**

- mapeamento manual;
- maior disciplina para evitar SQL repetido;
- testes de repository e conversões precisam ser extensos;
- evolução do schema exige uma camada bem definida.

**Avaliação:** melhor ponto de partida, desde que encapsulado em repositories e
unidade de trabalho.

### 10.2 ORM completo

**Vantagens**

- relações e mapeamento declarativos;
- migrations e consultas compostas podem ganhar produtividade;
- menos montagem manual de objetos.

**Desvantagens**

- nova dependência e convenções;
- maior mudança arquitetural simultânea à migração;
- abstrações podem esconder o comportamento de locking do SQLite;
- não há ORM atual no projeto;
- integração com dataclasses e serviços existentes exigiria adaptação ampla.

**Avaliação:** possível no futuro, mas aumenta o risco do primeiro corte.

### 10.3 Micro ORM

**Vantagens**

- menor volume de boilerplate;
- abstração mais leve.

**Desvantagens**

- ainda adiciona dependência;
- pode não cobrir migrations, optimistic locking e UoW;
- cria uma camada intermediária sem eliminar SQL específico.

**Avaliação:** não demonstra benefício suficiente sobre uma camada própria
pequena neste projeto.

### 10.4 Repositories próprios sobre `sqlite3`

**Vantagens**

- mantém SQL explícito;
- centraliza consultas e mapeamento;
- permite unidade de trabalho e testes por agregado;
- encaixa na arquitetura atual sem framework web.

**Desvantagens**

- exige regras claras para impedir acesso SQL disperso;
- mais código de infraestrutura próprio;
- cuidado com N+1 na montagem de snapshots.

**Avaliação:** alternativa preferencial.

### 10.5 Banco único com Prompt Registry

**Vantagens**

- transação local única seria tecnicamente possível;
- foreign keys internas;
- um arquivo para backup.

**Desvantagens**

- mistura domínio editorial e infraestrutura de prompts;
- acopla migrations e restore;
- ameaça um componente já estável;
- amplia blast radius;
- viola a separação operacional desejada.

**Avaliação:** não recomendada.

### 10.6 Bancos separados

**Vantagens**

- ownership claro;
- migrations e backups independentes;
- nenhuma alteração indevida no registry;
- histórico de domínio continua legível mesmo se o registry mudar.

**Desvantagens**

- não há atomicidade entre resolução e domínio;
- referência é validada pela aplicação;
- backup consistente dos dois arquivos requer coordenação.

**Avaliação:** recomendada; a execução deve copiar metadados suficientes para
auditoria autônoma.

### 10.7 Estado inteiro em JSON

**Vantagens**

- compatibilidade imediata;
- baixo custo inicial;
- snapshot simples de exportar.

**Desvantagens**

- não atende consultas e relacionamentos;
- mantém duplicação;
- não resolve concorrência;
- sobrescreve histórico;
- torna migrations de dados frágeis;
- não suporta integridade referencial.

**Avaliação:** aceitável apenas como fonte legada temporária e snapshot de
diagnóstico.

### 10.8 Modelo relacional normalizado

**Vantagens**

- histórico consultável;
- regras e índices explícitos;
- isolamento por chave;
- rastreabilidade;
- versionamento e auditoria consistentes.

**Desvantagens**

- mais tabelas e joins;
- montagem de snapshot mais complexa;
- decisões de granularidade precisam ser estáveis.

**Avaliação:** deve ser a fonte de verdade final.

### 10.9 Modelo híbrido

**Vantagens**

- normaliza campos de negócio;
- preserva respostas brutas e documentos flexíveis;
- reduz perda na importação.

**Desvantagens**

- exige governança para JSON não voltar a virar fonte primária;
- campos JSON precisam de limites documentados;
- comparação e retenção podem consumir espaço.

**Avaliação:** recomendado com regra estrita: relações, ordenação, filtros,
status, decisões, concorrência, versionamento e auditoria ficam em colunas ou
tabelas; JSON fica restrito a bruto/flexível/compatibilidade.

## 11. Validação das decisões arquiteturais iniciais

| Decisão inicial | Resultado do research |
| --- | --- |
| Backend Python e React atuais | Validada; não há necessidade de substituição |
| Servidor HTTP atual | Pode continuar, mas precisa de roteamento por ID e controller sem estado global |
| SQLite de domínio | Validada para operação local |
| `sqlite3` padrão | Preferencial |
| Migrations versionadas | Obrigatórias; precedente no registry |
| UUID textual | Validado; IDs legados devem ser preservados separadamente |
| timestamps UTC | Validado; usar formato canônico com `Z` |
| foreign keys | Obrigatórias e habilitadas em toda conexão |
| WAL | Validado, com transações curtas |
| busy timeout | Validado; valor configurável, inicialmente alinhado ao registry |
| transações explícitas | Obrigatórias |
| optimistic locking | Obrigatório em `sessions` |
| soft delete/arquivamento | Adequado para raízes e histórico |
| `.data/post-engine.sqlite3` | Adequado como default |
| Prompt Registry separado | Validado |

Alternativas que permanecem abertas:

- duração exata do `busy_timeout`;
- `synchronous=NORMAL` ou `FULL`;
- granularidade final de algumas tabelas auxiliares;
- política de retenção de texto bruto e logs;
- forma de interoperar com múltiplos processos no futuro.

## 12. Mapeamento legado

| Campo ou seção atual | Origem atual | Destino proposto | Estratégia de migração | Observações |
| --- | --- | --- | --- | --- |
| `schema_version` | JSON | `legacy_imports.source_schema_version` | Copiar e validar | Não é versão do schema SQL |
| `session_id` | JSON/logger | `sessions.legacy_session_id` + novo UUID | Gerar UUID, preservar original | ID atual não é necessariamente UUID |
| `session_log_path` | JSON | `legacy_imports.report_json` ou catálogo de fonte | Validar caminho e hash | Não usar como FK |
| tema/objetivo/plataforma/tipo | JSON | `posts` | Criar post importado | Usuário alvo precisa ser escolhido |
| personalidade | JSON | post/sessão/versão | Copiar como snapshot | Definir semântica final de default |
| restrições | JSON/entrevista | restrições relacionais | Deduplicar mantendo ordem | Há cópias |
| fase/status de workflow | JSON | `sessions` | Mapear estados conhecidos | Rótulos apenas de UI não entram |
| `current_stage` | JSON | nenhum | Descartar ou pôr no relatório | Estado de interface |
| `fases_liberadas` | JSON | nenhum | Recalcular | Derivado |
| contexto da entrevista | JSON | post/sessão | Comparar com topo e registrar divergência | Não escolher silenciosamente se divergir |
| perguntas selecionadas | JSON | `interview_questions` | Importar em ordem | IDs legados preservados quando presentes |
| candidatas atuais | JSON | `interview_questions` | Importar na última rodada conhecida | Rodadas antigas foram sobrescritas |
| respostas | JSON | `interview_answers` | Importar imutáveis | Preservar original e normalizado |
| evidências | entrevista/topo/briefing | `authorial_evidence` | Colapsar cópias idênticas por ID/conteúdo | Divergência gera warning |
| sinais | entrevista/briefing | sinais e associações | Colapsar por ID | Nome da tabela auxiliar ainda aberto |
| dimensões | entrevista/briefing | `authorial_dimensions` | Importar como última revisão conhecida | Histórico anterior indisponível |
| avaliação determinística | entrevista | avaliações/itens autorais | Importar última | `approved` pode ser recalculado e comparado |
| avaliação LLM | entrevista | `interview_answer_assessments` | Importar última com escopo cumulativo | Não há ID de execução confiável |
| gaps | entrevista/gateway/briefing | `authorial_gaps` | Deduplicar e ligar ao gateway | Preservar ordem |
| gateway | entrevista/topo/briefing | `authorial_gateways` | Colapsar aliases/cópias | Histórico anterior indisponível |
| briefing | JSON | `briefings` e vínculos | Criar revisão importada | Comparar reconstrução |
| storyboard | `editorial_flow` | storyboards e `storyboard_blocks` | Criar revisão importada | Manter version/order |
| abordagens | opções de draft | `block_approaches` | Uma abordagem por opção | Deduplicar somente dentro do bloco |
| drafts | `by_block.options` | `block_drafts` | Importar status/conteúdo/persona | Provider/model vão para execução sintética ou metadata |
| seleção | `selected_option_id` | `block_draft_selections` | Marcar uma ativa por bloco | IDs ausentes geram divergência |
| composição | `editorial_flow.composition` | `post_versions` | Comparar com conteúdo de topo | Se divergir, não sobrescrever |
| `conteudo_gerado` | JSON | `post_versions` | Criar versão importada | Origem `imported` |
| `conteudo_json` | JSON | versão/segments/documento | Decompor chaves conhecidas | Raw preservado apenas quando justificado |
| `slides_gerados` | JSON | `segments`/documento | Importar ordenação | Comparar com SlideMark |
| `segmentos` | JSON | `segments` | Importar em ordem | IDs legados preservados em metadata se necessário |
| `avaliacao_post` | JSON | `evaluations`, `evaluation_items` | Importar como completed | Total derivado deve ser comparado |
| prompt/stdout/stderr/retorno/events/error | JSON | `llm_executions` e eventos | Criar execução legada sintética se houver evidência | Representa apenas a última execução |
| `is_running` | JSON | execução/import report | Converter para execução interrompida, nunca ativa | Requer regra explícita |
| `_segmento_index` | JSON | nenhum | Descartar | UI |
| JSONL referenciado | filesystem | execuções/eventos/imports | Parse por linha e tentar correlacionar | Correlação pode ser ambígua |
| JSONL não referenciado | filesystem | catálogo/relatório opcional | Não atribuir automaticamente | Evitar vazamento entre sessões |
| agent config | YAML | permanece YAML | Não migrar | Copiar config efetiva para execuções futuras |
| Prompt Registry refs | SQLite separado | referência textual em execução | Correlacionar quando ID existir | Legado geralmente não preservou o ID |
| exports existentes | filesystem | `exports` | Scan opcional com hash e associação confirmada | Sessão atual não registra caminho de forma estruturada |

## 13. Riscos técnicos

- Importar duplicações como entidades diferentes e inflar o histórico.
- Escolher silenciosamente uma das cópias quando elas divergem.
- Não conseguir reconstruir rodadas e avaliações antigas já sobrescritas.
- Correlacionar JSONL à execução errada por proximidade temporal.
- Manter transação SQLite aberta durante LLM e bloquear todas as escritas.
- Usar uma única conexão SQLite em threads sem política definida.
- Criar repositories, mas continuar permitindo mutação direta de snapshot.
- Tratar `lock_version` apenas no frontend, sem `WHERE` condicional no banco.
- Persistir `is_running` como fonte de verdade e deixar sessão travada após
  crash.
- Usar JSON para campos que depois precisem de filtro ou integridade.
- Permitir hard delete em raízes históricas.
- Gerar número de versão com `MAX + 1` fora de transação protegida.
- Realizar dual write sem registrar falha de um dos lados.
- Cortar o JSON antes de provar reconstrução e restart.
- Fazer rollback pós-corte usando JSON antigo e perder dados novos.
- Crescimento de stdout, stderr, eventos e respostas brutas no banco.
- WAL e arquivos `-wal`/`-shm` não incluídos corretamente em backup manual.
- Acoplar migrations do domínio às do Prompt Registry.

## 14. Incompatibilidades e dados não recuperáveis

- O JSON guarda somente as candidatas da rodada mais recente.
- Dimensões, avaliações, gateway, gaps e decisão de aprofundamento são
  sobrescritos; não há histórico completo no snapshot.
- O campo de última execução não representa todas as chamadas necessárias para
  chegar ao estado.
- As referências do Prompt Registry não são propagadas aos serviços atuais.
- JSONL não possui foreign keys nem sequência transacional de domínio.
- Reset substitui o snapshot; sessões anteriores só podem deixar logs.
- Exports não têm catálogo relacional nem ligação garantida à versão.
- Não existe usuário no legado.

Esses limites devem aparecer no relatório de importação. O importador não pode
inventar histórico.

## 15. Decisões abertas para implementação

1. Criar automaticamente um usuário “Importado do legado” ou exigir seleção do
   usuário alvo em toda importação.
2. Definir se personalidade é default do post, atributo da sessão, snapshot da
   versão ou combinação dos três.
3. Definir política de reabertura explícita de posts concluídos.
4. Definir retenção, compressão ou truncamento de prompts, stdout, stderr e raw
   responses.
5. Definir se JSONL será importado integralmente ou apenas catalogado e ligado
   quando houver correlação inequívoca.
6. Definir se exports antigos serão descobertos por scan ou somente registrados
   em novas execuções.
7. Definir granularidade final das tabelas auxiliares para sinais, regras,
   tipos de evidência e snapshots de briefing.
8. Definir o comportamento de cancelamento de processo LLM no servidor atual.
9. Definir suporte esperado a múltiplos processos além de múltiplas threads.
10. Definir o período mínimo de dual write e os limiares aceitáveis de
    divergência no shadow read.
11. Definir a política de backup consistente após o corte, incluindo WAL.
12. Confirmar se versões `published` serão usadas antes de existir publicação
    automática; o status ainda é útil para imutabilidade/consolidação.

## 16. Conclusão do research

A migração deve introduzir um banco de domínio normalizado e uma fronteira de
comandos por `session_id`. O documento atual pode continuar temporariamente
como fonte legada, destino de dual write e snapshot de comparação, mas não deve
permanecer como fonte de verdade final.

A solução de menor risco para o projeto atual é:

- `sqlite3` padrão;
- migrations SQL versionadas;
- conexão por unidade de trabalho;
- repositories explícitos;
- transações curtas;
- `lock_version` por sessão;
- lock de execução por sessão;
- montagem de snapshot a partir das relações;
- IDs compartilhados apenas por texto com o Prompt Registry;
- transição incremental com importação idempotente, dual write, shadow read e
  corte controlado.
