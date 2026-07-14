# SPEC-010 — Prompt de avaliação de resposta

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define o template que pede ao LLM para avaliar uma resposta do usuário. O prompt deve retornar deltas, evidências, lacunas, aspecto mais fraco e próxima pergunta, sempre com validação defensiva antes de afetar scores.

## Plan
1. Montar o prompt com tema, pergunta, resposta, scores atuais e `memory_pack`.
2. Explicitar os cinco aspectos autorais e o significado de cada evidência.
3. Exigir JSON estrito com deltas e justificativas por aspecto.
4. Reforçar que o LLM não deve inventar fatos nem converter opinião em vivência.

## Tasks
- [ ] T01 — Criar template Markdown do prompt de avaliação de resposta.
- [ ] T02 — Definir contrato JSON esperado para deltas, evidências, lacunas e próxima pergunta.
- [ ] T03 — Incluir regras para diferenciar experiência, opinião, sentimento, aprendizado e personalidade.
- [ ] T04 — Incluir instruções contra inferência de vivências não declaradas.
- [ ] T05 — Criar parser/validador defensivo para o JSON retornado pelo LLM.

