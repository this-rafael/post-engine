# SPEC-050 — Loader de prompts Markdown

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Implementa carregamento de prompts Markdown versionados. O loader deve servir templates de entrevista, avaliação, memory pack, segmentação, geração, regras e personas.

## Plan
1. Definir raiz de prompts e nomes lógicos.
2. Carregar arquivos Markdown de forma previsível e testável.
3. Retornar erro claro quando arquivo obrigatório estiver ausente.
4. Manter personas versionadas em arquivo, sem edição via TUI no MVP.

## Tasks
- [ ] T01 — Implementar função `load_prompt(path_or_name)`.
- [ ] T02 — Definir paths para prompts de entrevista, geração, segmentação, avaliação e personas.
- [ ] T03 — Tratar arquivo ausente e erro de leitura com mensagens claras.
- [ ] T04 — Evitar acoplamento do loader com `PromptBuilder` além do carregamento de texto.
- [ ] T05 — Testar carregamento válido, arquivo ausente e encoding UTF-8.

