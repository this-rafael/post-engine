# SPEC-013 — Prompt de atualização do memory pack

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define o template usado pelo LLM para atualizar o `MemoryPack`. O prompt deve extrair sinais autorais, preservar frases e lacunas, e impedir extrapolações narrativas que comprometam a fidelidade do produto.

## Plan
1. Montar prompt com tema, pergunta, resposta, avaliação e memory pack atual.
2. Exigir retorno JSON com os campos oficiais do `MemoryPack`.
3. Instruir preservação de fatos concretos, tensões e frases naturais.
4. Reforçar proibição de inventar ou reclassificar opinião como vivência.

## Tasks
- [ ] T01 — Criar template Markdown de atualização do memory pack.
- [ ] T02 — Definir contrato JSON com campos `fatosVividos`, `opinioes`, `sentimentos`, `aprendizados` e demais listas.
- [ ] T03 — Incluir regras explícitas de deduplicação e preservação de informações anteriores.
- [ ] T04 — Incluir guardrail contra invenção de experiências ou conversão indevida de categorias.
- [ ] T05 — Criar validação do JSON para listas, tipos e campos ausentes.

