# SPEC-017 — Meta-prompt de sentimento

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Define o meta-prompt para extrair percepção subjetiva sem cair em tom terapêutico. O objetivo é capturar incômodo, alívio, frustração, orgulho ou tensão humana quando isso existir no relato.

## Plan
1. Buscar percepção subjetiva vinculada ao tema e ao contexto do post.
2. Evitar sentimentalismo artificial e linguagem terapêutica.
3. Permitir tom técnico, prático ou analítico quando sentimento for baixo.
4. Gerar sinais úteis para `sentimentos`, `tensoes_ou_conflitos` e restrições de geração.

## Tasks
- [ ] T01 — Criar meta-prompt de sentimento em Markdown.
- [ ] T02 — Incluir exemplos de emoções e tensões relevantes ao PRD.
- [ ] T03 — Proibir perguntas invasivas, terapêuticas ou melodramáticas.
- [ ] T04 — Orientar o LLM a aceitar ausência de emoção forte.
- [ ] T05 — Testar perguntas que extraem tensão subjetiva sem forçar dramatização.

