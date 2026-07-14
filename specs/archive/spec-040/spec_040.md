# SPEC-040 — Validação de entrada da TUI

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Valida campos operacionais da TUI antes de preview, execução e persistência crítica. A validação deve impedir prompts inválidos sem bloquear exibição de resultados brutos quando a execução já ocorreu.

## Plan
1. Validar campos obrigatórios: tema, plataforma, objetivo, tipo de post e briefing JSON.
2. Validar scores e restrições quando informados.
3. Validar tool, modelo e sandbox conforme executor selecionado.
4. Retornar erros claros para a interface.

## Tasks
- [ ] T01 — Implementar validação de entrada para preview e execução.
- [ ] T02 — Validar `tipo_de_post` em `feed`, `article` ou `slide`.
- [ ] T03 — Validar briefing autoral como JSON válido.
- [ ] T04 — Validar scores numéricos e restrições como lista de strings.
- [ ] T05 — Testar campos vazios, briefing inválido, tipo inválido e restrições inválidas.

