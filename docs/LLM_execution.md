# Execução de Prompts na LLM

Este documento descreve como o post-engine executa prompts em diferentes provedores LLM (Codex, OpenCode e Cursor/AK Agent).

## Arquitetura Geral

O sistema segue um fluxo em camadas:

1. **Prompt Loader** (`prompt_loader.py`): Carrega templates Markdown do diretório `prompts/`
2. **Prompt Builder** (`prompt_builder.py`): Monta o prompt final com contexto (entrevista, scores, regras)
3. **LLM Config** (`llm_config.py`): Resolve qual provedor/modelo usar por operação
4. **Agent Wrapper** (`agent_wrapper.py`): Executa o prompt no CLI do provedor escolhido
5. **Codex LLM Client** (`codex_llm_client.py`): Cliente especializado para Codex com protocolo unificado

## 1. Carregamento de Prompts

Os prompts são arquivos Markdown versionados em `prompts/`:

```
prompts/
├── generator/          # Geração de conteúdo
│   ├── base.md        # Template base
│   ├── rules-post.md  # Regras específicas
│   └── personas/      # Personas por tipo
├── interview/         # Entrevistas
├── editorial/         # Fluxo editorial
└── router/            # Roteamento
```

### Exemplo de uso do loader:

```python
from content_engine.prompt_loader import load_prompt

# Carrega template base de geração
template_base = load_prompt("generator.base")

# Carrega regras específicas do formato
regras = load_prompt("generator.rules_post")

# Carrega persona
persona = load_prompt("generator.persona_post")
```

O loader resolve caminhos automaticamente via dicionário `PROMPT_PATHS`:

```python
PROMPT_PATHS = {
    "generator.base": "generator/base.md",
    "generator.rules_post": "generator/rules-post.md",
    "interview.initial_post": "interview/initial-post.md",
    # ...
}
```

## 2. Construção do Prompt Final

O `prompt_builder.py` monta o prompt completo combinando:

- Template base com placeholders `{{variavel}}`
- Contexto da entrevista (InterviewPack)
- Scores autorais
- Restrições de geração
- Políticas anti-IA
- Persona selecionada
- Regras do formato

### Exemplo de construção:

```python
from content_engine.prompt_builder import build_generation_prompt
from content_engine.schemas import GenerationPromptInput

input_data = GenerationPromptInput(
    tema="Arquitetura de eventos",
    plataforma="LinkedIn",
    objetivo_do_post="Ensinar conceitos",
    tipo_de_post="post",
    personalidade="Didático e direto",
    interview_pack=interview_pack_dict,
    scores=scores_dict,
    briefing_autoral=briefing_dict,
)

prompt_final = build_generation_prompt(input_data)
```

### Template rendering:

O template usa placeholders que são substituídos pelo contexto:

```markdown
## Entrada

Tema:
{{tema}}

Plataforma:
{{plataforma}}

Persona ativa:
{{personaSelecionada}}

## Scores autorais

{{scores}}

## Políticas anti-IA obrigatórias

{{politicasAntiIa}}
```

## 3. Configuração de Provedores

O `llm_config.py` define qual provedor/modelo usar por operação:

### Operações suportadas:

```python
LLM_OPERATIONS = (
    "questions",              # Geração de perguntas
    "answer_evaluate",        # Avaliação de respostas
    "content_generate",       # Geração de conteúdo
    "segment",                # Segmentação
    "adjust_segment",         # Ajuste de segmento
    "post_evaluate",          # Avaliação do post
    "slidemark_export",       # Export SlideMark
    # ...
)
```

### Configuração padrão:

```python
DEFAULT_OPERATION_CONFIGS = {
    "questions": {
        "provider": "opencode",
        "model": "qwen-3.6-plus",
    },
    "content_generate": {
        "provider": "codex",
        "model": "gpt-5.5",
        "reasoning_effort": "xhigh",
        "sandbox": "read-only",
    },
    "segment": {
        "provider": "codex",
        "model": "gpt-5.4-mini",
        "sandbox": "read-only",
    },
}
```

### Resolução de configuração:

```python
from content_engine.llm_config import resolve

# Resolve configuração para geração de conteúdo
config = resolve("content_generate")
# config.provider = "codex"
# config.model = "gpt-5.5"
# config.reasoning_effort = "xhigh"
# config.sandbox = "read-only"
```

A configuração pode ser sobrescrita via `.data/agent-config.yml`:

```yaml
operations:
  content_generate:
    provider: codex
    model: gpt-5.5
    reasoning_effort: xhigh
    sandbox: read-only
  questions:
    provider: opencode
    model: qwen-3.6-plus
```

## 4. Execução via Agent Wrapper

O `AgentWrapper` é a camada que invoca os CLIs dos provedores:

### 4.1 Codex (OpenAI)

```python
from content_engine.agent_wrapper import AgentWrapper

wrapper = AgentWrapper(workspace="/path/to/project")

result = wrapper.run_codex(
    prompt="Gere um post sobre...",
    model="gpt-5.5",
    reasoning_effort="xhigh",
    sandbox="read-only",
)

print(result.stdout)  # Resposta da LLM
print(result.returncode)  # 0 se sucesso
```

**Comando executado:**

```bash
codex exec \
  --cd /path/to/project \
  --sandbox read-only \
  --color never \
  --ephemeral \
  --model gpt-5.5 \
  -c 'model_reasoning_effort="xhigh"' \
  -
```

O prompt é enviado via stdin (argumento `-`).

### 4.2 OpenCode

```python
result = wrapper.run_opencode(
    prompt="Gere perguntas de entrevista sobre...",
    model="opencode-go/qwen3.7-plus",
    agent="interviewer",
    reasoning_effort="max",
    files=["context.md"],
)
```

**Comando executado:**

```bash
opencode run \
  --dir /path/to/project \
  --model opencode-go/qwen3.7-plus \
  --variant max \
  --agent interviewer \
  --file context.md \
  "Gere perguntas de entrevista sobre..."
```

No backend, `reasoning_effort` é o campo comum da configuração. Para Codex,
ele vira `model_reasoning_effort`; para OpenCode, `medium`/`max` viram
`--variant medium`/`--variant max`. Se o nível não estiver configurado,
nenhuma variante é acrescentada ao comando OpenCode.

### 4.3 Cursor (AK Agent)

```python
result = wrapper.run_cursor(
    prompt="Avalie esta resposta...",
    model="auto",
    reasoning_effort="medium",
)
```

**Comando executado:**

```bash
agent \
  --print \
  --output-format stream-json \
  --trust \
  --force \
  --approve-mcps \
  --workspace /path/to/project \
  --sandbox disabled \
  --model auto[effort=medium] \
  "Avalie esta resposta..."
```

**Parsing de output:**

O Cursor retorna JSON stream que é parseado por `cursor_output.py`:

```python
from content_engine.cursor_output import parse_cursor_output

output_text, error_msg = parse_cursor_output(
    stdout=result.stdout,
    stderr=result.stderr,
    returncode=result.returncode,
)
```

### 4.4 Método unificado `run()`

```python
result = wrapper.run(
    tool="codex",  # ou "opencode" ou "cursor"
    prompt="...",
    model="gpt-5.5",
    reasoning_effort="xhigh",
    sandbox="read-only",
)
```

## 5. Codex LLM Client (Protocolo Unificado)

O `CodexLlmClient` oferece uma interface de alto nível compatível com o protocolo `_LLMRunner`:

```python
from content_engine.codex_llm_client import CodexLlmClient, LlmRequest

client = CodexLlmClient(
    timeout_seconds=600,
    workspace="/path/to/project",
)

# Via método complete()
request = LlmRequest(
    system_prompt="Você é um especialista em...",
    user_prompt="Gere um post sobre...",
    model="gpt-5.5",
    reasoning_effort="xhigh",
    metadata={"stage": "content_generate"},
)

response = client.complete(request)
print(response.text)  # Texto da resposta
print(response.json_data)  # Se for JSON válido

# Via método run() (protocolo _LLMRunner)
result = client.run(
    tool="codex",
    prompt="Gere um post sobre...",
    model="gpt-5.5",
    reasoning_effort="xhigh",
    stage="content_generate",
)

print(result.stdout)  # Resposta
print(result.returncode)  # 0 se sucesso
```

### Execução com Popen (concorrente):

O client usa threads para ler stdout/stderr concorrentemente e evitar deadlocks:

```python
def _execute_via_popen(self, command: list[str], prompt: str) -> str:
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    
    # Threads para leitura concorrente
    stdout_thread = threading.Thread(target=_read_stdout, daemon=True)
    stderr_thread = threading.Thread(target=_read_stderr, daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    
    # Envia prompt via stdin
    proc.stdin.write(prompt)
    proc.stdin.close()
    
    # Aguarda conclusão com timeout
    exit_code = proc.wait(timeout=self.timeout_seconds)
    
    return "".join(stdout_buf).strip()
```

## 6. Fluxo Completo de Geração

Exemplo de fluxo completo de geração de conteúdo:

```python
from content_engine.prompt_builder import build_generation_prompt
from content_engine.agent_wrapper import AgentWrapper
from content_engine.llm_config import resolve

# 1. Monta o prompt
prompt = build_generation_prompt(input_data)

# 2. Resolve configuração
config = resolve("content_generate")

# 3. Executa no provedor
wrapper = AgentWrapper(workspace="/path/to/project")

result = wrapper.run(
    tool=config.provider,
    prompt=prompt,
    model=config.model,
    reasoning_effort=config.reasoning_effort,
    sandbox=config.sandbox or "read-only",
)

# 4. Processa resposta
if result.returncode == 0:
    content = result.stdout
    # Parse JSON se necessário
    # Valida SlideMark se for formato de slides
else:
    error = result.error or result.stderr
    raise RuntimeError(f"LLM failed: {error}")
```

## 7. Estrutura de Resposta

Todas as execuções retornam `AgentResult`:

```python
@dataclass
class AgentResult:
    tool: str              # "codex", "opencode", "cursor"
    command: list[str]     # Comando executado
    returncode: int        # 0 = sucesso
    stdout: str            # Resposta da LLM
    stderr: str            # Logs de erro
    events: list[dict]     # Eventos JSON (se parse_jsonl=True)
    error: str | None      # Mensagem de erro
```

## 8. Logging de Sessão

Todas as execuções são logadas via `SessionLogger`:

```python
from content_engine.session_log import SessionLogger

logger = SessionLogger(session_dir="/path/to/session")

wrapper = AgentWrapper(
    workspace="/path/to/project",
    session_logger=logger,
)

# Log automático de request e response
result = wrapper.run_codex(prompt="...")
```

Eventos logados:

- `llm_request`: Comando, prompt, parâmetros
- `llm_response`: stdout, stderr, returncode, error

## 9. Tratamento de Erros

### Timeout:

```python
try:
    result = wrapper.run_codex(prompt="...", timeout=600)
except subprocess.TimeoutExpired:
    # Kill do processo após timeout
    raise RuntimeError("Timeout após 600 segundos")
```

### CLI não encontrado:

```python
if result.returncode == 127:
    raise RuntimeError(f"CLI not found: {result.command[0]}")
```

### Erro de execução:

```python
if result.returncode != 0:
    error_msg = result.error or result.stderr
    raise RuntimeError(f"Codex falhou com exit code {result.returncode}: {error_msg}")
```

## 10. Exemplos de Uso Real

### Geração de perguntas de entrevista:

```python
from content_engine.questions import QuestionGenerator

generator = QuestionGenerator(
    workspace="/path/to/project",
    tool="opencode",
    model="qwen-3.6-plus",
)

questions = generator.generate_initial_questions(
    tema="Arquitetura de eventos",
    tipo_de_post="post",
    memory_pack=memory_pack,
)
```

### Geração de conteúdo:

```python
from content_engine.generator import ContentGenerator

generator = ContentGenerator(
    workspace="/path/to/project",
)

content = generator.generate(
    prompt_input=input_data,
    tool="codex",
    model="gpt-5.5",
    reasoning_effort="xhigh",
)
```

### Avaliação de post:

```python
from content_engine.post_evaluation import PostEvaluator

evaluator = PostEvaluator(workspace="/path/to/project")

evaluation = evaluator.evaluate(
    post_content=content,
    tipo_de_post="post",
    tool="codex",
    model="gpt-5.4-mini",
)
```

## Resumo dos Provedores

| Provedor | CLI | Modelo padrão | Caso de uso |
|----------|-----|---------------|-------------|
| **Codex** | `codex exec` | gpt-5.5, gpt-5.4-mini | Geração de conteúdo, segmentação |
| **OpenCode** | `opencode run` | qwen-3.6-plus | Geração de perguntas |
| **Cursor** | `agent` | auto | Avaliação de respostas |

## Referências

- `src/content_engine/codex_llm_client.py`: Cliente Codex de alto nível
- `src/content_engine/agent_wrapper.py`: Wrapper unificado de CLIs
- `src/content_engine/prompt_builder.py`: Construção de prompts
- `src/content_engine/prompt_loader.py`: Carregamento de templates
- `src/content_engine/llm_config.py`: Configuração de provedores
- `prompts/`: Templates Markdown versionados
