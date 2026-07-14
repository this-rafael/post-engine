# SPEC-007 — Restrições de geração

## Table of contents
- [Executive resume](#executive-resume)
- [Plan](#plan)
- [Tasks](#tasks)

## Executive resume
Gera restrições narrativas com base nos scores brutos para impedir invenção de autoridade. As restrições são guardrails do prompt final e protegem a premissa central do PRD: não transformar ausência de experiência em falsa vivência.

## Plan
1. Derivar restrições por categoria abaixo dos limiares definidos no PRD.
2. Diferenciar ausência de experiência, opinião fraca, emoção fraca, aprendizado fraco e personalidade baixa.
3. Produzir mensagens claras que possam ser enviadas ao prompt gerador.
4. Manter restrições cumulativas e auditáveis no `ResultadoGateway`.

## Tasks
- [ ] T01 — Implementar `gerar_restricoes_de_geracao(score_bruto)`.
- [ ] T02 — Criar restrições para experiência baixa sem bloquear opinião, reflexão ou provocação.
- [ ] T03 — Criar restrições para opinião, sentimento, aprendizado e personalidade abaixo do limiar.
- [ ] T04 — Garantir que a função não gere restrições quando o gateway equilibrado for aprovado.
- [ ] T05 — Testar combinações de scores baixos e múltiplas restrições simultâneas.

