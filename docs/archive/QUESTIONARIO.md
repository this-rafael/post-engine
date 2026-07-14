# Questionario - Diagnostico e correcao da geracao de perguntas

## Problema observado

Ao iniciar a entrevista, as perguntas apareciam como fallback fixo, por exemplo:

```text
Me conta um caso concreto em que serena mcp apareceu em um projeto, estudo, decisao tecnica ou situacao pratica. O que estava acontecendo, qual problema voce tentou resolver e o que mudou depois? Se ainda nao viveu algo assim, responda pela sua observacao ou leitura honesta do tema.
```

O comportamento esperado era a chamada da IA para compor perguntas abertas e contextuais a partir do tema.

## Causa raiz

A IA era chamada pelo fluxo da TUI, mas uma variante antiga do modelo dedicado de perguntas usava a string com espaco:

```text
gpt-5.4 mini
```

Essa string nao era aceita pelo Codex CLI autenticado via ChatGPT. A chamada local confirmou o erro:

```text
The 'gpt-5.4 mini' model is not supported when using Codex with a ChatGPT account.
```

Como `QuestionGenerator._invoke()` retornava apenas `stdout` e nao validava `returncode`/`error`, a falha do agente era tratada como uma resposta vazia ou invalida. O TUI entao caia no fallback em `_pergunta_para_lacunas()`, exibindo o template canonico de experiencia.

## Fluxo afetado

1. `src/tui/app.py::_gerar_perguntas_iniciais_llm()` chama `QuestionGenerator.gerar_iniciais()`.
2. `src/content_engine/questions.py::QuestionGenerator._invoke()` chama o agente via `agent.run()`.
3. O Codex CLI falha por modelo invalido.
4. A resposta sem JSON valido e normalizada como lista vazia.
5. O TUI usa fallback:

```text
Me conta um caso concreto em que {tema} apareceu em um projeto...
```

## Solucao aplicada

### 1. Usar a string correta do modelo dedicado por padrao

`QUESTION_MODEL_DEFAULT` usa:

```python
"gpt-5.4-mini"
```

Com isso, o Codex CLI recebe `-m gpt-5.4-mini`, que foi validado localmente com `codex exec`.

Arquivo:

```text
src/content_engine/schemas.py
```

### 2. Migrar sessoes antigas com modelo obsoleto

Sessoes persistidas que ainda contenham a variante antiga:

```json
{ "question_model": "gpt-5.4 mini" }
```

sao carregadas como:

```python
question_model = "gpt-5.4-mini"
```

Arquivo:

```text
src/content_engine/persistence.py
```

### 3. Parar de mascarar falha do agente

`QuestionGenerator._invoke()` agora valida `resultado.ok`. Se o agente falhar, levanta `RuntimeError` com `returncode` e detalhe de `error`, `stderr` ou `stdout`.

Isso evita diagnosticos falsos como "LLM nao retornou perguntas validas" quando o problema real e falha de subprocesso/modelo.

Arquivo:

```text
src/content_engine/questions.py
```

### 4. Cobertura de testes

Foram ajustados/adicionados testes para:

- default de `question_model` usar `gpt-5.4-mini`;
- preservar modelo dedicado quando configurado explicitamente;
- explicar falhas do agente com mensagem util;
- migrar `gpt-5.4 mini` em sessoes antigas;
- preservar `gpt-5.4-mini` quando ja estiver configurado.

Arquivo:

```text
tests/test_spec_061.py
```

## Validacao

Comando executado:

```bash
rtk pytest -q
```

Resultado:

```text
338 passed
```

## Resultado esperado apos a correcao

Quando `question_model` estiver vazio/`None`, a sessao carrega o default `gpt-5.4-mini`. O fallback continua existindo, mas passa a ser usado apenas quando a LLM realmente nao retornar perguntas validas ou quando houver falha explicita registrada no estado.
