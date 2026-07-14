# SPEC-030 — Segmentação do post

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Divide o conteúdo gerado em segmentos editáveis. Cada segmento deve ter id, ordem, texto e papel interno, permitindo revisão isolada sem obrigar avaliação prévia do post.

## Plan
1. Receber conteúdo completo gerado.
2. Chamar prompt ou função de segmentação e validar retorno.
3. Converter JSON em lista de `SegmentoPost`.
4. Garantir ordem estável, ids únicos e texto editável.

## Tasks
- [ ] T01 — Implementar serviço de segmentação do post.
- [ ] T02 — Integrar prompt de segmentação e executor LLM quando aplicável.
- [ ] T03 — Validar ids, ordem, texto e `papel_interno`.
- [ ] T04 — Permitir segmentação antes da avaliação do conteúdo gerado.
- [ ] T05 — Testar segmentos válidos, JSON inválido, ids duplicados e ordem inconsistente.

