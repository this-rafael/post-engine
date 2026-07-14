# Plano de isolamento do contexto local nas execuções LLM

## Objetivo

Evitar que os agentes recebam, por inferência do `cwd`/workspace, contexto
irrelevante do repositório `post-engine`, mantendo nas chamadas apenas:

- o prompt específico da operação;
- os dados da sessão necessários para aquela operação;
- arquivos auxiliares explicitamente autorizados;
- instruções de execução controladas pela aplicação.

O agente não deve precisar navegar pelo repositório para responder a uma
operação de geração, entrevista, segmentação ou avaliação.

## Situação atual

- `PostEngineApp._build_default_agent()` usa `Path.cwd()` como workspace.
- `AgentWrapper` passa esse diretório para `cwd`, `codex --cd`,
  `opencode --dir` e `agent --workspace`.
- O sandbox `read-only` impede alterações, mas não impede leitura do projeto.
- O Codex não recebe `--ignore-user-config` por padrão.
- O prompt renderizado já contém boa parte do contexto de domínio necessário,
  mas o agente continua com acesso implícito ao workspace completo.
- `CodexLlmClient` possui um caminho de execução separado que também aceita um
  workspace amplo.

## Decisão proposta

Introduzir um `LlmExecutionWorkspace` temporário e por chamada, criado pela
aplicação, contendo somente os artefatos explicitamente necessários. O agente
será executado nesse diretório, e não na raiz do projeto.

O workspace original continuará sendo usado pela aplicação para carregar
prompts, persistir sessões e gerar exportações; ele não será usado como
workspace de descoberta pelo agente.

## Fases de implementação

### 1. Mapear e declarar dependências por operação

Criar uma tabela central de operações LLM e seus insumos permitidos:

| Operação | Entrada mínima | Arquivos locais permitidos |
|---|---|---|
| Entrevista | tema, contexto, histórico, sinais | nenhum |
| Validação/avaliação de entrevista | pergunta, respostas, evidências | nenhum |
| Geração de post | briefing, entrevista, regras, contrato | regras/prompt já renderizados |
| Storyboard/rascunho/composição | estado editorial projetado | nenhum ou prompt renderizado |
| Segmentação/ajuste | conteúdo e contexto editorial | nenhum |
| Avaliação | conteúdo, briefing e contexto | nenhum |
| Exportação SlideMark | conteúdo e contrato necessário | contrato mínimo, se indispensável |

Critério: nenhuma operação deve depender de o agente encontrar código-fonte,
`.git`, `.data`, `tests`, documentação ou configurações do projeto.

### 2. Criar o workspace isolado

Adicionar um módulo dedicado, por exemplo
`src/content_engine/llm_workspace.py`, responsável por:

- criar diretório temporário por execução;
- aplicar permissões compatíveis com o sandbox escolhido;
- copiar somente arquivos explicitamente declarados;
- rejeitar caminhos fora de uma lista allowlist;
- impedir symlinks e travessia (`..`);
- limpar o diretório ao final da execução;
- oferecer modo persistente somente para diagnóstico controlado.

O workspace deve conter, preferencialmente, apenas um arquivo de entrada ou
nenhum arquivo, já que o prompt é enviado por stdin/argumento.

### 3. Alterar o contrato do `AgentWrapper`

Trocar o significado atual de `workspace`:

- `project_root`: diretório da aplicação, usado apenas pela aplicação;
- `execution_workspace`: diretório isolado usado pelo CLI.

Manter compatibilidade temporária com `workspace`, mas emitir erro ou aviso
quando ele apontar diretamente para a raiz do projeto em produção.

O wrapper deverá:

- usar o workspace isolado como `cwd` e como `--cd`, `--dir` ou
  `--workspace`;
- aceitar `ignore_user_config=True` por padrão para Codex, quando suportado;
- não herdar arquivos de configuração do projeto para o agente;
- continuar registrando no log o workspace lógico e o workspace efetivo,
  sem registrar segredos.

### 4. Ajustar a criação dos agentes

Alterar `_build_default_agent()` e os serviços que criam agentes para que cada
operação faça:

1. montar o prompt e os dados estruturados;
2. criar um workspace temporário;
3. executar o agente nesse workspace;
4. coletar a resposta;
5. destruir o workspace.

A fábrica de agentes deve receber a operação e o conjunto de artefatos
permitidos, em vez de capturar implicitamente `Path.cwd()`.

### 5. Tratar provedores individualmente

Verificar e documentar as flags de isolamento de cada CLI:

- Codex: `--cd`, `--sandbox`, `--ephemeral` e
  `--ignore-user-config`;
- OpenCode: `--dir`, lista explícita de `--file` e configuração de agente;
- Cursor/AK Agent: `--workspace` e política de confiança/permissões.

Se algum provedor não oferecer isolamento suficiente, executá-lo em processo
ou container separado com diretório mínimo e desabilitar esse provedor para
operações que exijam garantia forte.

### 6. Reduzir contexto implícito no prompt

Revisar os prompts para que contenham todas as regras necessárias de forma
autossuficiente:

- incorporar contratos e regras mínimas no prompt renderizado;
- remover instruções que mandem o agente consultar arquivos do projeto;
- distinguir claramente dados do autor, instruções e conteúdo não confiável;
- limitar campos de entrada a tamanhos definidos para evitar excesso de
  contexto explícito.

Essa fase não deve duplicar indiscriminadamente documentos grandes; deve gerar
versões resumidas e versionadas dos contratos necessários.

### 7. Corrigir observabilidade e diagnóstico

Adicionar aos eventos `llm_request`:

- `operation`;
- `project_root` apenas como metadado técnico, se necessário;
- `execution_workspace` temporário;
- lista de arquivos permitidos;
- tamanho do prompt e dos arquivos;
- `isolation_mode`.

Não registrar conteúdo duplicado em múltiplos campos nem expor tokens,
credenciais ou variáveis sensíveis do ambiente.

### 8. Testes de regressão

Adicionar testes unitários para garantir que:

- o subprocesso recebe `cwd` diferente da raiz do projeto;
- `--cd`, `--dir` e `--workspace` apontam para o diretório temporário;
- `.git`, `.data`, `src`, `tests` e arquivos não permitidos não são copiados;
- symlinks e caminhos fora da allowlist são rejeitados;
- o workspace é removido em sucesso, erro e timeout;
- `ignore_user_config` é aplicado conforme o provedor;
- prompts não contêm o caminho absoluto do projeto salvo quando isso for
  explicitamente necessário;
- todas as operações atuais continuam recebendo os dados de domínio corretos.

Adicionar pelo menos um teste de integração com um CLI falso que tente ler um
arquivo conhecido do projeto e confirme que esse arquivo não existe no
workspace de execução.

Executar a suíte existente de wrapper, cliente Codex, configuração LLM,
entrevista, geração, editorial e GUI.

## Critérios de aceite

- Nenhuma execução de produção usa `Path.cwd()` como workspace do agente.
- O agente não consegue ler o repositório original através do diretório de
  trabalho da execução.
- Cada operação declara seus insumos permitidos.
- Falhas de criação/limpeza do workspace são explícitas e observáveis.
- Codex, OpenCode e Cursor têm comportamento documentado e testado.
- Os fluxos de entrevista, geração, editorial, segmentação e avaliação passam
  sem depender de arquivos arbitrários do projeto.
- Os logs permitem auditar o isolamento sem armazenar segredos.

## Ordem recomendada de entrega

1. Implementar workspace temporário e testes do utilitário.
2. Integrar o `AgentWrapper` e corrigir testes de montagem de comando.
3. Migrar a fábrica padrão e as operações legadas.
4. Migrar `CodexLlmClient` ou removê-lo se não houver mais consumidor.
5. Revisar prompts e allowlists por operação.
6. Adicionar teste de integração com tentativa de leitura indevida.
7. Atualizar `LLM_execution.md` e `LLM_USAGE.md`.
8. Executar a suíte completa e fazer uma execução manual por provedor.

## Riscos e decisões em aberto

- Alguns CLIs podem carregar configuração global mesmo com workspace vazio;
  por isso a aplicação deve preferir `--ignore-user-config` ou equivalente.
- Prompts que atualmente dependem de contratos encontrados no filesystem
  precisarão receber esses contratos explicitamente.
- Workspaces temporários aumentam custo de criação e dificultam depuração;
  o modo persistente deve ser opt-in e nunca o padrão.
- A política de sandbox do agente não substitui o isolamento de arquivos; as
  duas camadas devem permanecer independentes.
