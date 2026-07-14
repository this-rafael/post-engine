# Uso das configurações LLM

## Conclusão principal

O endpoint `GET /api/llm-config` não chama nenhuma LLM. Ele apenas lê a configuração global em `src/gui/server.py`, através de `llm_config_snapshot()`.

A ordem declarada em `LLM_OPERATIONS` não é a ordem de execução. A ordem real depende das ações executadas pelo usuário na interface.

## Como o endpoint `/api/llm-config` funciona

1. A requisição `GET /api/llm-config` é recebida em `src/gui/server.py`.
2. O servidor chama `controller.llm_config_snapshot()`.
3. `llm_config_snapshot()` chama `load_global_config()`.
4. `load_global_config()` lê `.data/agent-config.yml`.
5. Cada configuração é combinada com seu default.
6. Todas as operações configuráveis aparecem explicitamente em `operations`.
7. O endpoint retorna configurações, labels, providers e status dos executáveis.

`provider_status.available: true` significa apenas que o executável foi encontrado no `PATH`. Não significa que uma chamada à API foi executada com sucesso.

Não existe mais herança entre operações. Cada fase (`post_generate`, `storyboard_generate`, `block_approaches_generate`, `block_draft_generate`, `editorial_compose`, etc.) tem provider, modelo, agent, reasoning effort, sandbox e timeout próprios.

A chave legada `content_generate` é migrada automaticamente para `post_generate` ao carregar o YAML.

## Configuração efetiva atual

Todas as configurações atuais usam `sandbox: read-only`.

| Operação | Provider | Modelo | Raciocínio |
|---|---|---|---|
| `interview_questions` | OpenCode | `opencode-go/qwen3.7-plus` | `max` |
| `interview_validate` | OpenCode | `opencode-go/glm-5.2` | `max` |
| `interview_evaluate` | Cursor | `auto` | — |
| `post_generate` | Codex | `gpt-5.5` | `xhigh` |
| `storyboard_generate` | Codex | `gpt-5.6-terra` | `max` |
| `block_approaches_generate` | Codex | `gpt-5.6-luna` | `medium` |
| `block_draft_generate` | Codex | `gpt-5.6-terra` | `max` |
| `editorial_compose` | Codex | `gpt-5.6-sol` | `max` |
| `segment` | OpenCode | `opencode-go/qwen3.6-plus` | `medium` |
| `adjust_segment` | OpenCode | `opencode-go/qwen3.6-plus` | `max` |
| `adjust_segments_bulk` | Cursor | `auto` | — |
| `post_evaluate` | Codex | `gpt-5.6-terra` | `max` |
| `slidemark_export` | OpenCode | `opencode-go/qwen3.6-plus` | `max` |

No Codex, `reasoning_effort` é encaminhado como `model_reasoning_effort` na
configuração do comando. No OpenCode, os valores `medium` e `max` são
encaminhados como a opção CLI `--variant`; são mecanismos diferentes do
backend, embora a matriz use os mesmos nomes de nível.

Exemplo de configuração independente por fase:

```yaml
operations:
  post_generate:
    provider: codex
    model: gpt-5.5
    agent: null
    reasoning_effort: xhigh
    sandbox: read-only
  storyboard_generate:
    provider: codex
    model: gpt-5.5
    reasoning_effort: high
    sandbox: read-only
  editorial_compose:
    provider: cursor
    model: auto
    agent: composer
    reasoning_effort: xhigh
    sandbox: read-only
```

## Pipeline principal numerada

### 1. Início da entrevista — `interview_questions`

O ponto de configuração é `PostEngineApp._v4_controller()`.

O ponto da chamada é `interview.exploration.generate_next_question()`.

O prompt pede várias perguntas candidatas. A resposta esperada é:

```json
{
  "candidatas": [
    {
      "pergunta": "...",
      "direcao": "...",
      "por_que_agora": "..."
    }
  ]
}
```

Depois da resposta da LLM, o sistema:

1. extrai as candidatas;
2. valida cada pergunta;
3. elimina perguntas inválidas ou repetidas;
4. seleciona uma pergunta;
5. grava a pergunta selecionada em `current_question`;
6. grava as candidatas em `candidates`.

Resultado: uma pergunta pronta para o usuário.

### 2. Resposta da entrevista — `interview_evaluate`

Cada resposta enviada passa por `InterviewController.process_answer()`.

Antes da LLM, são executadas etapas determinísticas:

1. registro da resposta;
2. extração de sinais autorais;
3. avaliação heurística das dimensões;
4. identificação de lacunas.

Depois é chamada `evaluate_authorship_llm()`.

A resposta esperada é:

```json
{
  "aprovou": true,
  "confianca": 0.85,
  "forcas": [],
  "fraquezas": [],
  "riscos": [],
  "justificativa": "...",
  "integridade_epistemica": "..."
}
```

Resultado: um `LlmAssessment` com aprovação, confiança, forças, fraquezas, riscos e justificativa.

### 3. Gateway da entrevista

O resultado da LLM é combinado com a avaliação determinística.

A aprovação final só acontece quando:

```text
LLM aprovou
E
heurística aprovou
```

O gateway produz:

- `approved`;
- `llm_approved`;
- `heuristic_approved`;
- `global_score`;
- dimensões fracas e excepcionais;
- lacunas relevantes;
- vetos;
- justificativa;
- confiança da LLM.

### 4. Decisão de aprofundamento

O sistema decide se deve fazer outra pergunta.

Se `should_ask == true`, a pipeline volta para `interview_questions`.

O ciclo real da entrevista é:

```text
pergunta
→ resposta
→ interview_evaluate
→ gateway
→ decisão
→ nova pergunta, se necessário
```

O limite máximo é de 12 perguntas.

### 5. Encerramento da entrevista

Ao encerrar, o sistema monta o briefing autoral a partir da entrevista.

Essa fase não chama LLM.

Resultado:

- `briefing_autoral`;
- histórico de perguntas e respostas;
- evidências;
- resultado do gateway;
- contexto da entrevista.

### 6. Geração principal — `post_generate`

Caminho tradicional (`run`): gera o post direto a partir do briefing, sem passar pelo ramo editorial.

O gerador é criado em `PostEngineApp.get_generator()`.

A chamada efetiva ocorre em `ContentGenerator.generate()`.

A entrada contém:

- tema;
- plataforma;
- objetivo;
- tipo de post;
- briefing autoral;
- contexto da entrevista;
- resultado do gateway;
- restrições;
- personalidade.

A LLM retorna JSON com campos como:

```json
{
  "conteudo": "...",
  "metadados": {},
  "alertas": [],
  "slides": [],
  "sugestoesImagem": [],
  "slidemark": {}
}
```

O parser normaliza o resultado em `ConteudoGerado`.

Resultado salvo no estado:

- `conteudo_gerado`;
- `conteudo_json`;
- `slides_gerados`;
- `sugestoesImagem`;
- `slidemark`;
- `stdout`;
- `stderr`;
- `returncode`;
- eventos da execução.

### 7. Segmentação — `segment`

Existe uma condição importante:

```text
Se já existir um SlideMark válido:
    segmenta diretamente os slides
    não chama a LLM
Caso contrário:
    chama segment
```

Quando a LLM é chamada, o retorno esperado é:

```json
{
  "segmentos": [
    {
      "id": "seg_1",
      "ordem": 1,
      "papelInterno": "abertura",
      "texto": "..."
    }
  ]
}
```

Resultado:

```text
state.segmentos = [
  {
    id,
    ordem,
    texto,
    papel_interno
  }
]
```

Para conteúdo SlideMark, normalmente há um segmento para cada slide.

### 8. Ajuste de um segmento — `adjust_segment`

É disparado pela ação `rewrite_segment`.

Entrada:

- conteúdo completo;
- segmento atual;
- pedido do usuário;
- briefing;
- contexto da entrevista;
- restrições.

Retorno:

```json
{
  "segmentoReescrito": "..."
}
```

O texto não substitui imediatamente o original. Ele fica pendente para revisão e somente é aplicado na ação `apply_segment`.

### 9. Ajuste em lote — `adjust_segments_bulk`

É disparado pela ação `rewrite_segments_bulk`.

Usa a própria configuração de `adjust_segments_bulk` (default: Codex com `gpt-5.4-mini`).

É feita uma única chamada LLM para vários segmentos.

Retorno:

```json
{
  "segmentosReescritos": [
    {
      "id": "seg_1",
      "ordem": 1,
      "segmentoReescrito": "..."
    }
  ]
}
```

Todos os segmentos solicitados precisam aparecer na resposta. O resultado fica pendente até `apply_segments_bulk`.

### 10. Avaliação do post — `post_evaluate`

É disparada pela ação `evaluate`.

A avaliação recebe o conteúdo final, normalmente juntando os segmentos já editados.

O retorno contém notas de 0 a 10:

```json
{
  "score": {
    "tese": 0,
    "progressao": 0,
    "concretude": 0,
    "precisaoTecnica": 0,
    "retencao": 0,
    "autoridade": 0,
    "autoria": 0,
    "slidemark": 0,
    "revisaoTextual": 0
  },
  "veredito": "...",
  "pontosFortes": [],
  "pontosFracos": [],
  "trechosFracos": [],
  "redundancias": [],
  "falhasTecnicas": [],
  "sugestoesDeMelhoria": []
}
```

Resultado salvo em `state.avaliacao_post`.

### 11. Exportação comum

A ação `export` não chama LLM.

Ela grava o conteúdo final em Markdown e JSON usando os dados já existentes no estado.

### 12. Exportação SlideMark — `slidemark_export`

Só é permitida para formatos visuais e depois de uma avaliação válida.

A LLM recebe:

- conteúdo final;
- segmentos;
- briefing;
- sugestões de imagem;
- SlideMark original;
- contrato SlideMark atual.

Retorno esperado:

```json
{
  "slidemark": {
    "version": "1.0.0",
    "document": {},
    "canvas": {},
    "theme": "...",
    "author": {},
    "settings": {},
    "export": {},
    "slides": []
  }
}
```

Depois o sistema:

1. normaliza o documento;
2. aplica defaults de autor;
3. valida o contrato SlideMark;
4. grava `conteudo_json["slidemark"]`;
5. exporta Markdown;
6. exporta `.slidemark.json`.

## Ramo editorial alternativo

Esse ramo é disparado separadamente e não acontece automaticamente em todas as execuções.

### 13. `storyboard_generate`

Retorna blocos editoriais:

```json
{
  "blocks": [
    {
      "role": "...",
      "focus": "..."
    }
  ]
}
```

O resultado é validado, recebe IDs e é salvo no fluxo editorial.

### 14. `block_approaches_generate`

É executada para cada bloco.

Retorna exatamente três abordagens:

```json
{
  "approaches": [
    {
      "title": "...",
      "description": "..."
    }
  ]
}
```

### 15. `block_draft_generate`

Para cada bloco:

1. são escolhidas três personas;
2. são criadas três opções;
3. ocorre uma chamada LLM para cada opção.

Assim, a geração inicial de um bloco normalmente faz:

```text
1 chamada block_approaches_generate
+
3 chamadas block_draft_generate
```

Cada rascunho retorna:

```json
{
  "draft": {
    "content": "..."
  }
}
```

O usuário escolhe uma das três opções antes de avançar.

A ação `generate_all_block_drafts` está atualmente desabilitada. O sistema informa que a geração deve ocorrer bloco a bloco, em ordem.

### 16. `editorial_compose`

Só ocorre depois que os rascunhos necessários foram selecionados.

O resultado é validado contra âncoras de preservação editorial. Se houver perda de material importante, a mesma operação é chamada novamente com um prompt de correção.

Portanto, pode haver:

```text
1 chamada normal
ou
2 chamadas se for necessário retry de preservação
```

O resultado final é convertido pelo mesmo parser usado em `post_generate` e volta para o fluxo de segmentação, avaliação e exportação.

## Camada final dos providers

Todas as operações convergem para `AgentWrapper.run()`.

O dispatch é:

- Codex: `codex exec`, com modelo, sandbox, reasoning effort e JSON;
- OpenCode: `opencode run`, com modelo e formato JSON;
- Cursor: `agent --print`, com saída em stream JSON.

O subprocesso retorna:

- `stdout`;
- `stderr`;
- `returncode`;
- `events`;
- `error`.

O resumo do caminho tradicional é:

```text
1. interview_questions
2. usuário responde
3. interview_evaluate
4. gateway determinístico
5. interview_questions novamente, se necessário
6. encerramento e briefing
7. post_generate
8. segment, exceto quando o SlideMark permite segmentação direta
9. adjust_segment ou adjust_segments_bulk, opcional
10. post_evaluate
11. export comum ou slidemark_export
```

No ramo editorial (em vez de `post_generate`):

```text
briefing
→ storyboard_generate
→ block_approaches_generate
→ block_draft_generate × 3
→ seleção do rascunho
→ editorial_compose
→ segment
→ post_evaluate
→ export
```

Cada fase editorial resolve a própria configuração; nenhuma herda de `post_generate`.
