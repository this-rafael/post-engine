# SPEC-011 — Cliente de avaliação autoral

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa a camada de produto que chama o LLM para avaliar respostas da entrevista. Ela monta prompt, chama executor configurado, valida JSON e retorna `AvaliacaoAutoralDaResposta`, sem misturar responsabilidades com o `AgentWrapper`.

## Plan
1. Receber dados estruturados da rodada e renderizar o prompt de avaliação.
2. Chamar o executor LLM por interface genérica, sem acoplar comandos CLI ao domínio.
3. Parsear e normalizar o JSON retornado.
4. Retornar objeto de domínio ou erro controlado sem atualizar scores diretamente.

## Tasks
- [ ] T01 — Criar função/serviço de avaliação autoral da resposta.
- [ ] T02 — Integrar template da SPEC-010 com loader/renderizador de prompts.
- [ ] T03 — Chamar executor configurado e preservar `stdout` bruto para depuração.
- [ ] T04 — Converter JSON validado em `AvaliacaoAutoralDaResposta`.
- [ ] T05 — Testar sucesso, JSON inválido, campos ausentes e falha do executor com mock.

