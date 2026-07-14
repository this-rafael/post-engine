# Plano: remover `content_generate` como configuração genérica

## Objetivo

Remover o ID genérico `content_generate` e permitir que cada fase da pipeline tenha sua própria configuração de provider, modelo, agent, reasoning effort, sandbox e timeout.

Para não quebrar o caminho tradicional `run`, a capacidade atual de gerar um post será mantida com um novo ID explícito: `post_generate`.

## Configurações finais

As operações deverão ser:

```text
interview_questions
interview_evaluate
post_generate
storyboard_generate
block_approaches_generate
block_draft_generate
editorial_compose
segment
adjust_segment
adjust_segments_bulk
post_evaluate
slidemark_export
```

Cada operação deverá aceitar:

```yaml
provider:
model:
agent:
reasoning_effort:
sandbox:
timeout_seconds:
```

Não deverá existir mais herança entre as operações editoriais e `content_generate`.

## Etapas de implementação

### 1. Atualizar o contrato de operações

Alterar `src/content_engine/llm_config.py`:

- remover `content_generate`;
- adicionar `post_generate`;
- remover ou esvaziar `OPERATION_INHERITS`;
- manter as operações editoriais como operações independentes;
- adicionar defaults específicos para `post_generate`;
- adicionar defaults independentes para `storyboard_generate`, `block_approaches_generate`, `block_draft_generate` e `editorial_compose`;
- garantir que `resolve(operation)` resolva diretamente a operação solicitada.

O resultado esperado é:

```python
resolve("storyboard_generate")
```

retornar a configuração própria do storyboard, sem consultar outra operação.

### 2. Migrar o arquivo de configuração

Atualizar `.data/agent-config.yml`.

Exemplo:

```yaml
operations:
  interview_questions:
    provider: codex
    model: gpt-5.5
    agent: null
    reasoning_effort: medium
    sandbox: read-only

  interview_evaluate:
    provider: codex
    model: gpt-5.5
    agent: null
    reasoning_effort: high
    sandbox: read-only

  post_generate:
    provider: codex
    model: gpt-5.5
    agent: null
    reasoning_effort: xhigh
    sandbox: read-only

  storyboard_generate:
    provider: codex
    model: gpt-5.5
    agent: null
    reasoning_effort: high
    sandbox: read-only

  block_approaches_generate:
    provider: codex
    model: gpt-5.5
    agent: null
    reasoning_effort: high
    sandbox: read-only

  block_draft_generate:
    provider: codex
    model: gpt-5.5
    agent: null
    reasoning_effort: xhigh
    sandbox: read-only

  editorial_compose:
    provider: codex
    model: gpt-5.5
    agent: null
    reasoning_effort: xhigh
    sandbox: read-only
```

A migração deve copiar a configuração antiga de `content_generate` para `post_generate`, evitando quebrar instalações existentes.

Depois da migração, o YAML não deverá conter `content_generate`.

### 3. Migrar o caminho tradicional

Alterar `src/content_engine/session_app.py`:

- `_garantir_prompt_para_fase4()` deverá usar `post_generate`;
- `get_generator()` deverá usar `post_generate`;
- `_executar_agente()` deverá registrar a operação como `post_generate`;
- atualizar logs de `content.generate` para `post.generate` ou `post_generate`;
- manter a classe `ContentGenerator` apenas se ela continuar representando a geração direta do post, sem depender do nome antigo da operação.

O fluxo tradicional ficará:

```text
briefing
→ post_generate
→ segment
→ post_evaluate
→ export
```

### 4. Tornar o ramo editorial independente

As chamadas editoriais já usam IDs próprios em `src/content_engine/editorial_generation.py`:

```python
_run_json_llm(..., operation="storyboard_generate")
_run_json_llm(..., operation="block_approaches_generate")
_run_json_llm(..., operation="block_draft_generate")
_run_json_llm(..., operation="editorial_compose")
```

O que deverá mudar:

- remover a herança para `content_generate`;
- garantir que cada operação busque sua própria configuração;
- passar independentemente `model`, `agent`, `reasoning_effort`, `sandbox` e `timeout_seconds`;
- manter os logs identificando a fase real executada.

O fluxo editorial ficará:

```text
briefing
→ storyboard_generate
→ block_approaches_generate
→ block_draft_generate
→ seleção do rascunho
→ editorial_compose
→ segment
→ post_evaluate
→ export
```

### 5. Atualizar o frontend

Alterar `frontend/src/lib/mappers/operations.ts`:

```diff
- content: "content_generate",
+ postGenerate: "post_generate",
```

Também será necessário:

- trocar o label `Geração de conteúdo` por `Geração de post`;
- atualizar `OP_ORDER`;
- remover referências a `content_generate`;
- garantir que storyboard, abordagens, rascunhos e composição apareçam como configurações independentes;
- permitir editar o campo `agent` na interface;
- garantir que o payload do `PUT /api/llm-config` grave todas as operações;
- manter o mapeamento de operações do frontend compatível com o backend.

### 6. Atualizar snapshots e API

Verificar:

- `llm_config_snapshot()`;
- `resolve_all()`;
- `effective_llm_config`;
- `operation_labels`;
- `list_operations()`;
- `save_global_config()`;
- `load_global_config()`.

O endpoint deverá retornar configurações explícitas para:

```json
{
  "post_generate": {},
  "storyboard_generate": {},
  "block_approaches_generate": {},
  "block_draft_generate": {},
  "editorial_compose": {}
}
```

Não deverá existir mais `content_generate` no snapshot efetivo.

### 7. Atualizar testes

Alterar:

- `tests/test_llm_config.py`;
- `tests/test_gui_llm_config.py`;
- testes de geração;
- testes editoriais;
- testes do frontend relacionados aos mappers.

Adicionar testes para confirmar que:

1. `content_generate` não existe mais;
2. `post_generate` resolve corretamente;
3. cada operação editorial resolve sua própria configuração;
4. alterar `storyboard_generate` não altera `editorial_compose`;
5. alterar `block_draft_generate` não altera `block_approaches_generate`;
6. cada chamada usa o provider, modelo e agent corretos;
7. a migração do YAML antigo funciona;
8. o caminho tradicional `run` continua funcionando com `post_generate`;
9. o ramo editorial não chama `post_generate` implicitamente;
10. os logs identificam a operação real executada.

### 8. Atualizar documentação

Atualizar `LLM_USAGE.md`:

- remover `content_generate` como operação;
- documentar `post_generate`;
- explicar que as fases editoriais não herdam mais configuração;
- mostrar a ordem real da pipeline;
- incluir exemplos de configuração independente por fase;
- diferenciar claramente operação, configuração herdada e provider/modelo.

## Critérios de aceitação

A mudança estará completa quando:

```text
content_generate não existir mais no backend, frontend, testes ou configuração;
```

e quando for possível configurar separadamente:

```text
post_generate
storyboard_generate
block_approaches_generate
block_draft_generate
editorial_compose
```

com provider, modelo, agent, reasoning effort, sandbox e timeout próprios.

Além disso:

- o caminho tradicional deverá continuar funcionando através de `post_generate`;
- o caminho editorial deverá executar apenas as operações editoriais correspondentes;
- alterar o modelo de uma fase não deverá alterar nenhuma outra fase;
- o endpoint `/api/llm-config` deverá exibir todas as operações configuráveis;
- os testes de configuração, geração e composição editorial deverão passar.
