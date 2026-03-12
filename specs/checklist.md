# Checklist das specs

Use este arquivo para acompanhar conclusão por spec e por tarefa. Cada item referencia a spec detalhada correspondente.

## SPEC-001 — Modelos de domínio e contratos Python
- [ ] SPEC-001 concluída — [spec_001.md](spec-001/spec_001.md)
- [ ] T01 — Definir `Literal`s e constantes para tipos de post, aspectos autorais, gateways, autoria e ferramentas LLM.
- [ ] T02 — Implementar `TypedDicts` e `dataclasses` centrais do PRD com nomes internos em `snake_case`.
- [ ] T03 — Separar contratos de entrevista, geração, segmentação, avaliação de post, sessão TUI e `AgentWrapper`.
- [ ] T04 — Definir defaults seguros para listas, `memory_pack`, eventos e campos opcionais.
- [ ] T05 — Criar validações leves para impedir categorias ausentes, tipos inválidos e divergência entre contrato Python e JSON esperado.

## SPEC-002 — Inicialização do estado da entrevista
- [ ] SPEC-002 concluída — [spec_002.md](spec-002/spec_002.md)
- [ ] T01 — Implementar validação de campos obrigatórios e `tipo_de_post` permitido.
- [ ] T02 — Criar função `criar_scores_iniciais` com todas as categorias em zero.
- [ ] T03 — Criar `ResultadoGateway` inicial reprovado e sem aprovação implícita.
- [ ] T04 — Inicializar `MemoryPack`, interações, contador de rodadas e `max_rodadas`.
- [ ] T05 — Cobrir casos de entrada vazia, tipo inválido e estado inicial completo em testes.

## SPEC-003 — Scoring autoral
- [ ] SPEC-003 concluída — [spec_003.md](spec-003/spec_003.md)
- [ ] T01 — Implementar validação de deltas para aspectos obrigatórios, inteiros e intervalo permitido.
- [ ] T02 — Implementar `atualizar_scores` preservando imutabilidade do score anterior.
- [ ] T03 — Calcular `total_bruto` e `total_normalizado` a partir das categorias oficiais.
- [ ] T04 — Garantir clamp do normalizado sem limitar o bruto.
- [ ] T05 — Testar soma incremental, clamp, categorias ausentes, negativos e valores acima de 100.

## SPEC-004 — Gateway equilibrado
- [ ] SPEC-004 concluída — [spec_004.md](spec-004/spec_004.md)
- [ ] T01 — Implementar `passou_gateway_equilibrado(score_normalizado)`.
- [ ] T02 — Usar a lista oficial `ASPECTOS_AUTORAIS` como única fonte de categorias.
- [ ] T03 — Garantir que todas as categorias precisem estar `>= 100`.
- [ ] T04 — Testar aprovação com cinco categorias completas.
- [ ] T05 — Testar reprovação com uma categoria abaixo de 100, mesmo com total alto.

## SPEC-005 — Gateway desequilibrado
- [ ] SPEC-005 concluída — [spec_005.md](spec-005/spec_005.md)
- [ ] T01 — Implementar `passou_gateway_desequilibrado(score_bruto)`.
- [ ] T02 — Calcular total bruto usando todos os aspectos autorais.
- [ ] T03 — Calcular categoria dominante apenas entre experiência, opinião, sentimento e aprendizado.
- [ ] T04 — Validar personalidade como sustentação de autoria, não como eixo principal.
- [ ] T05 — Testar total insuficiente, personalidade insuficiente, dominante insuficiente e aprovação válida.

## SPEC-006 — Classificação do tipo de autoria
- [ ] SPEC-006 concluída — [spec_006.md](spec-006/spec_006.md)
- [ ] T01 — Implementar `classificar_tipo_autoria(score_bruto)`.
- [ ] T02 — Mapear `experiencia` para `experiencial`, `opiniao` para `opinativa`, `sentimento` para `emocional` e `aprendizado` para `reflexiva`.
- [ ] T03 — Retornar `hibrida` quando experiência, opinião e aprendizado forem `>= 100`.
- [ ] T04 — Definir regra determinística para empate entre categorias dominantes.
- [ ] T05 — Testar cada tipo possível, incluindo caso híbrido.

## SPEC-007 — Restrições de geração
- [ ] SPEC-007 concluída — [spec_007.md](spec-007/spec_007.md)
- [ ] T01 — Implementar `gerar_restricoes_de_geracao(score_bruto)`.
- [ ] T02 — Criar restrições para experiência baixa sem bloquear opinião, reflexão ou provocação.
- [ ] T03 — Criar restrições para opinião, sentimento, aprendizado e personalidade abaixo do limiar.
- [ ] T04 — Garantir que a função não gere restrições quando o gateway equilibrado for aprovado.
- [ ] T05 — Testar combinações de scores baixos e múltiplas restrições simultâneas.

## SPEC-008 — Avaliação consolidada do gateway
- [ ] SPEC-008 concluída — [spec_008.md](spec-008/spec_008.md)
- [ ] T01 — Implementar `avaliar_gateway(scores)`.
- [ ] T02 — Retornar `tipo_autoria="hibrida"` e restrições vazias para gateway equilibrado.
- [ ] T03 — Integrar classificação e restrições no gateway desequilibrado.
- [ ] T04 — Integrar `identificar_lacunas` no caso reprovado.
- [ ] T05 — Testar precedência do equilibrado sobre o desequilibrado e todos os caminhos de retorno.

## SPEC-009 — Identificação de lacunas autorais
- [ ] SPEC-009 concluída — [spec_009.md](spec-009/spec_009.md)
- [ ] T01 — Implementar `identificar_lacunas(scores)`.
- [ ] T02 — Gerar lacunas para categorias normalizadas abaixo de 100.
- [ ] T03 — Gerar oportunidades para total bruto, personalidade e categoria dominante do gateway desequilibrado.
- [ ] T04 — Evitar recomendar mais perguntas para categoria já saturada sem motivo.
- [ ] T05 — Testar lacunas equilibradas, oportunidades desequilibradas e combinação das duas.

## SPEC-010 — Prompt de avaliação de resposta
- [ ] SPEC-010 concluída — [spec_010.md](spec-010/spec_010.md)
- [ ] T01 — Criar template Markdown do prompt de avaliação de resposta.
- [ ] T02 — Definir contrato JSON esperado para deltas, evidências, lacunas e próxima pergunta.
- [ ] T03 — Incluir regras para diferenciar experiência, opinião, sentimento, aprendizado e personalidade.
- [ ] T04 — Incluir instruções contra inferência de vivências não declaradas.
- [ ] T05 — Criar parser/validador defensivo para o JSON retornado pelo LLM.

## SPEC-011 — Cliente de avaliação autoral
- [ ] SPEC-011 concluída — [spec_011.md](spec-011/spec_011.md)
- [ ] T01 — Criar função/serviço de avaliação autoral da resposta.
- [ ] T02 — Integrar template da SPEC-010 com loader/renderizador de prompts.
- [ ] T03 — Chamar executor configurado e preservar `stdout` bruto para depuração.
- [ ] T04 — Converter JSON validado em `AvaliacaoAutoralDaResposta`.
- [ ] T05 — Testar sucesso, JSON inválido, campos ausentes e falha do executor com mock.

## SPEC-012 — Atualização do memory pack
- [ ] SPEC-012 concluída — [spec_012.md](spec-012/spec_012.md)
- [ ] T01 — Implementar função de atualização de `MemoryPack`.
- [ ] T02 — Definir estratégia de merge por campo com deduplicação simples e previsível.
- [ ] T03 — Preservar frases naturais do usuário sem reescrita excessiva.
- [ ] T04 — Registrar pontos ainda fracos para orientar perguntas recursivas.
- [ ] T05 — Testar merge incremental, deduplicação e separação entre fatos, opiniões e sentimentos.

## SPEC-013 — Prompt de atualização do memory pack
- [ ] SPEC-013 concluída — [spec_013.md](spec-013/spec_013.md)
- [ ] T01 — Criar template Markdown de atualização do memory pack.
- [ ] T02 — Definir contrato JSON com campos `fatosVividos`, `opinioes`, `sentimentos`, `aprendizados` e demais listas.
- [ ] T03 — Incluir regras explícitas de deduplicação e preservação de informações anteriores.
- [ ] T04 — Incluir guardrail contra invenção de experiências ou conversão indevida de categorias.
- [ ] T05 — Criar validação do JSON para listas, tipos e campos ausentes.

## SPEC-014 — Geração de perguntas iniciais
- [ ] SPEC-014 concluída — [spec_014.md](spec-014/spec_014.md)
- [ ] T01 — Criar prompt ou função de geração inicial de perguntas.
- [ ] T02 — Garantir cobertura de experiência, opinião, sentimento e aprendizado.
- [ ] T03 — Incluir regras para perguntas abertas, contextuais e não genéricas.
- [ ] T04 — Evitar pressão por vivência quando ela ainda não foi confirmada.
- [ ] T05 — Testar estrutura de saída, quantidade mínima e ausência de perguntas genéricas.

## SPEC-015 — Meta-prompt de experiência
- [ ] SPEC-015 concluída — [spec_015.md](spec-015/spec_015.md)
- [ ] T01 — Criar meta-prompt de experiência em Markdown.
- [ ] T02 — Incluir critérios de evidência factual do PRD.
- [ ] T03 — Incluir alternativa para observação, leitura ou opinião quando não houver vivência.
- [ ] T04 — Proibir invenção de empresas, números, cargos, incidentes ou casos reais.
- [ ] T05 — Testar exemplos de pergunta aceitável e pergunta que força falsa vivência.

## SPEC-016 — Meta-prompt de opinião
- [ ] SPEC-016 concluída — [spec_016.md](spec-016/spec_016.md)
- [ ] T01 — Criar meta-prompt de opinião em Markdown.
- [ ] T02 — Incluir padrões de pergunta sobre crítica, nuance, trade-off e premissas erradas.
- [ ] T03 — Bloquear perguntas vagas como “qual sua opinião?”.
- [ ] T04 — Garantir que a saída ajude a pontuar `opiniao` e `personalidade`.
- [ ] T05 — Testar perguntas para temas técnicos e temas não técnicos.

## SPEC-017 — Meta-prompt de sentimento
- [ ] SPEC-017 concluída — [spec_017.md](spec-017/spec_017.md)
- [ ] T01 — Criar meta-prompt de sentimento em Markdown.
- [ ] T02 — Incluir exemplos de emoções e tensões relevantes ao PRD.
- [ ] T03 — Proibir perguntas invasivas, terapêuticas ou melodramáticas.
- [ ] T04 — Orientar o LLM a aceitar ausência de emoção forte.
- [ ] T05 — Testar perguntas que extraem tensão subjetiva sem forçar dramatização.

## SPEC-018 — Meta-prompt de aprendizado
- [ ] SPEC-018 concluída — [spec_018.md](spec-018/spec_018.md)
- [ ] T01 — Criar meta-prompt de aprendizado em Markdown.
- [ ] T02 — Incluir padrões de pergunta sobre mudança de visão, erro e critério prático.
- [ ] T03 — Bloquear moralização genérica e frases motivacionais vagas.
- [ ] T04 — Orientar fallback para reflexão quando não houver transformação concreta.
- [ ] T05 — Testar perguntas que diferenciam aprendizado de opinião repetida.

## SPEC-019 — Perguntas recursivas
- [ ] SPEC-019 concluída — [spec_019.md](spec-019/spec_019.md)
- [ ] T01 — Criar função ou prompt de geração recursiva de perguntas.
- [ ] T02 — Integrar `identificar_lacunas`, scores, memory pack e últimas interações.
- [ ] T03 — Definir heurística de prioridade entre lacuna fraca e dominante promissora.
- [ ] T04 — Evitar perguntas repetidas ou redundantes com o que já está no memory pack.
- [ ] T05 — Testar cenários de gateway equilibrado próximo, desequilibrado próximo e experiência baixa.

## SPEC-020 — Loop principal da entrevista
- [ ] SPEC-020 concluída — [spec_020.md](spec-020/spec_020.md)
- [ ] T01 — Implementar `executar_entrevista` ou orquestrador equivalente.
- [ ] T02 — Integrar criação de estado, perguntas iniciais, avaliação de resposta, scoring e memory pack.
- [ ] T03 — Integrar avaliação de gateway e geração de perguntas recursivas.
- [ ] T04 — Controlar `rodadas` e encerramento por aprovação ou `max_rodadas`.
- [ ] T05 — Testar fluxo aprovado, fluxo reprovado por limite e propagação de erros controlados.

## SPEC-021 — Montagem do briefing autoral
- [ ] SPEC-021 concluída — [spec_021.md](spec-021/spec_021.md)
- [ ] T01 — Implementar `montar_briefing_autoral(state)`.
- [ ] T02 — Agrupar perguntas e respostas por aspecto autoral com base na avaliação.
- [ ] T03 — Incluir tema, plataforma, objetivo, tipo de post, personalidade, scores e memory pack.
- [ ] T04 — Garantir que briefing não seja salvo automaticamente como artefato separado.
- [ ] T05 — Testar briefing equilibrado, desequilibrado com restrições e estado sem aprovação.

## SPEC-022 — Personas oficiais
- [ ] SPEC-022 concluída — [spec_022.md](spec-022/spec_022.md)
- [ ] T01 — Criar `prompts/generator/personas/dev-interlocutor-feed.md`.
- [ ] T02 — Criar `prompts/generator/personas/dev-interlocutor-article.md`.
- [ ] T03 — Criar `prompts/generator/personas/dev-interlocutor-slide.md`.
- [ ] T04 — Incluir regras de voz, estilo, ritmo, profundidade, guardrails e limites narrativos.
- [ ] T05 — Garantir que a TUI apenas selecione personas oficiais por `tipo_de_post`, sem edição no MVP.

## SPEC-023 — Regras por tipo de post
- [ ] SPEC-023 concluída — [spec_023.md](spec-023/spec_023.md)
- [ ] T01 — Criar `prompts/generator/rules-feed.md`.
- [ ] T02 — Criar `prompts/generator/rules-article.md`.
- [ ] T03 — Criar `prompts/generator/rules-slide.md`.
- [ ] T04 — Incluir limites de formato, tom, estrutura e profundidade em cada bloco.
- [ ] T05 — Testar que o `PromptBuilder` seleciona somente o arquivo do formato ativo.

## SPEC-024 — PromptBuilder
- [ ] SPEC-024 concluída — [spec_024.md](spec-024/spec_024.md)
- [ ] T01 — Implementar `build_generation_prompt(data: GenerationPromptInput)`.
- [ ] T02 — Criar mapeamento `tipo_de_post -> persona` e `tipo_de_post -> regras`.
- [ ] T03 — Serializar briefing, scores e restrições com JSON legível e sem corromper caracteres.
- [ ] T04 — Renderizar template base com apenas persona e regras ativas.
- [ ] T05 — Testar erro para tipo inválido e ausência de blocos concorrentes.

## SPEC-025 — Contrato do PromptBuilder
- [ ] SPEC-025 concluída — [spec_025.md](spec-025/spec_025.md)
- [ ] T01 — Criar testes de contrato para `feed`, `article` e `slide`.
- [ ] T02 — Verificar que `feed` contém apenas `DevInterlocutorFeed`.
- [ ] T03 — Verificar que `article` contém apenas `DevInterlocutorArticle`.
- [ ] T04 — Verificar que `slide` contém apenas `DevInterlocutorSlide`.
- [ ] T05 — Verificar que o prompt não contém condicionais textuais como “se for feed”.

## SPEC-026 — Prompt gerador base
- [ ] SPEC-026 concluída — [spec_026.md](spec-026/spec_026.md)
- [ ] T01 — Criar `prompts/generator/base.md`.
- [ ] T02 — Incluir placeholders para tema, plataforma, objetivo, tipo, personalidade, gateway e autoria.
- [ ] T03 — Incluir regras globais de honestidade narrativa do PRD.
- [ ] T04 — Definir contrato JSON de saída com metadados e alertas.
- [ ] T05 — Testar renderização com restrições baixas e briefing completo.

## SPEC-027 — Geração de conteúdo
- [ ] SPEC-027 concluída — [spec_027.md](spec-027/spec_027.md)
- [ ] T01 — Implementar serviço de geração de conteúdo.
- [ ] T02 — Integrar `PromptBuilder` e `AgentWrapper` sem acoplar domínio ao executor.
- [ ] T03 — Parsear JSON esperado com fallback para `stdout` bruto.
- [ ] T04 — Retornar conteúdo, metadados, alertas e dados de execução.
- [ ] T05 — Testar sucesso, JSON inválido, erro de executor e preservação de `AgentResult`.

## SPEC-028 — AgentWrapper genérico
- [ ] SPEC-028 concluída — [spec_028.md](spec-028/spec_028.md)
- [ ] T01 — Implementar `AgentWrapper.run` com suporte a `codex` e `opencode`.
- [ ] T02 — Montar comandos CLI sem incluir persona, briefing, scoring ou regras de post.
- [ ] T03 — Capturar `stdout`, `stderr`, `returncode` e comando final.
- [ ] T04 — Parsear eventos JSONL quando `json_output=True`.
- [ ] T05 — Testar montagem de comandos com `subprocess.run` mockado.

## SPEC-029 — Robustez do AgentWrapper
- [ ] SPEC-029 concluída — [spec_029.md](spec-029/spec_029.md)
- [ ] T01 — Implementar timeout configurável na execução.
- [ ] T02 — Tratar `FileNotFoundError`, `PermissionError` e `subprocess.TimeoutExpired`.
- [ ] T03 — Tratar `returncode != 0`, `stdout` vazio e `stderr` não vazio.
- [ ] T04 — Tratar eventos JSONL inválidos preservando linhas brutas quando útil.
- [ ] T05 — Testar cada falha com mocks, sem chamar ferramentas reais.

## SPEC-030 — Segmentação do post
- [ ] SPEC-030 concluída — [spec_030.md](spec-030/spec_030.md)
- [ ] T01 — Implementar serviço de segmentação do post.
- [ ] T02 — Integrar prompt de segmentação e executor LLM quando aplicável.
- [ ] T03 — Validar ids, ordem, texto e `papel_interno`.
- [ ] T04 — Permitir segmentação antes da avaliação do conteúdo gerado.
- [ ] T05 — Testar segmentos válidos, JSON inválido, ids duplicados e ordem inconsistente.

## SPEC-031 — Prompt de segmentação
- [ ] SPEC-031 concluída — [spec_031.md](spec-031/spec_031.md)
- [ ] T01 — Criar template Markdown de segmentação.
- [ ] T02 — Definir contrato JSON com array `segmentos`.
- [ ] T03 — Incluir regra para não adicionar títulos ou rótulos ao texto final.
- [ ] T04 — Incluir regra de reescrita isolável por segmento.
- [ ] T05 — Testar prompt renderizado e validação de saída mínima.

## SPEC-032 — Ajuste por segmento
- [ ] SPEC-032 concluída — [spec_032.md](spec-032/spec_032.md)
- [ ] T01 — Implementar serviço de ajuste por segmento.
- [ ] T02 — Validar existência do segmento alvo antes da execução.
- [ ] T03 — Enviar restrições de geração e contexto completo ao prompt.
- [ ] T04 — Aplicar resultado somente ao segmento solicitado.
- [ ] T05 — Testar alteração isolada, segmento inexistente e tentativa de reescrever o post inteiro.

## SPEC-033 — Prompt de ajuste por segmento
- [ ] SPEC-033 concluída — [spec_033.md](spec-033/spec_033.md)
- [ ] T01 — Criar template Markdown de ajuste por segmento.
- [ ] T02 — Incluir placeholders para conteúdo completo, segmento, pedido, personalidade e restrições.
- [ ] T03 — Incluir guardrails de coerência, fidelidade e escopo de edição.
- [ ] T04 — Definir contrato JSON com `segmentoReescrito`.
- [ ] T05 — Testar prompt com restrições de experiência baixa e personalidade baixa.

## SPEC-034 — Avaliação do conteúdo gerado
- [ ] SPEC-034 concluída — [spec_034.md](spec-034/spec_034.md)
- [ ] T01 — Implementar serviço de avaliação do post gerado.
- [ ] T02 — Garantir execução apenas após geração e preferencialmente após segmentação.
- [ ] T03 — Validar scores de 0 a 100 e calcular total.
- [ ] T04 — Retornar pontos fortes, pontos fracos e sugestões de melhoria.
- [ ] T05 — Testar avaliação válida, JSON inválido e conteúdo que inventa fatos.

## SPEC-035 — Prompt de avaliação do post
- [ ] SPEC-035 concluída — [spec_035.md](spec-035/spec_035.md)
- [ ] T01 — Criar template Markdown de avaliação do post.
- [ ] T02 — Definir contrato JSON com `score`, `pontosFortes`, `pontosFracos` e `sugestoesDeMelhoria`.
- [ ] T03 — Incluir critérios de fidelidade e naturalidade além dos cinco aspectos autorais.
- [ ] T04 — Incluir instrução para penalizar falsa vivência e exagero de personalidade.
- [ ] T05 — Testar validação do contrato com campos ausentes e score fora do intervalo.

## SPEC-036 — Exportação Markdown
- [ ] SPEC-036 concluída — [spec_036.md](spec-036/spec_036.md)
- [ ] T01 — Implementar função `exportar_markdown`.
- [ ] T02 — Sanitizar tema, plataforma ou tipo de post para nome de arquivo seguro.
- [ ] T03 — Criar `exports/` se o diretório não existir.
- [ ] T04 — Salvar conteúdo com extensão `.md` sem disparo automático após geração.
- [ ] T05 — Testar conteúdo salvo, extensão correta, diretório criado e nome sanitizado.

## SPEC-037 — Exportação TXT
- [ ] SPEC-037 concluída — [spec_037.md](spec-037/spec_037.md)
- [ ] T01 — Implementar função `exportar_txt`.
- [ ] T02 — Reutilizar utilitário comum de sanitização de nomes.
- [ ] T03 — Criar `exports/` quando necessário.
- [ ] T04 — Salvar conteúdo com extensão `.txt`.
- [ ] T05 — Testar extensão correta, conteúdo salvo e consistência com exportação `.md`.

## SPEC-038 — Persistência de sessão
- [ ] SPEC-038 concluída — [spec_038.md](spec-038/spec_038.md)
- [ ] T01 — Implementar modelo/estrutura de estado persistido da TUI.
- [ ] T02 — Implementar `salvar_sessao` com criação de diretório `.data/sessions`.
- [ ] T03 — Serializar briefing, scores, restrições, stdout, stderr, returncode, eventos, conteúdo e segmentos.
- [ ] T04 — Disparar persistência após preview, execução, edição, limpeza e exportação.
- [ ] T05 — Testar escrita bem-sucedida e preservação dos campos mínimos.

## SPEC-039 — Restauração de sessão
- [ ] SPEC-039 concluída — [spec_039.md](spec-039/spec_039.md)
- [ ] T01 — Implementar `carregar_sessao`.
- [ ] T02 — Retornar estado vazio quando arquivo não existir.
- [ ] T03 — Tratar JSON inválido, permissões e campos ausentes.
- [ ] T04 — Reidratar campos da TUI sem executar LLM automaticamente.
- [ ] T05 — Testar arquivo ausente, corrompido, parcial e válido.

## SPEC-040 — Validação de entrada da TUI
- [ ] SPEC-040 concluída — [spec_040.md](spec-040/spec_040.md)
- [ ] T01 — Implementar validação de entrada para preview e execução.
- [ ] T02 — Validar `tipo_de_post` em `feed`, `article` ou `slide`.
- [ ] T03 — Validar briefing autoral como JSON válido.
- [ ] T04 — Validar scores numéricos e restrições como lista de strings.
- [ ] T05 — Testar campos vazios, briefing inválido, tipo inválido e restrições inválidas.

## SPEC-041 — Tela única da TUI MVP
- [ ] SPEC-041 concluída — [spec_041.md](spec-041/spec_041.md)
- [ ] T01 — Criar aplicação Textual com layout de tela única.
- [ ] T02 — Adicionar campos para tema, plataforma, objetivo, personalidade, briefing, scores e restrições.
- [ ] T03 — Adicionar seletores de tipo de post, tool, modelo e sandbox.
- [ ] T04 — Adicionar áreas de prompt, stdout, stderr, eventos e JSON parseado.
- [ ] T05 — Adicionar botões Preview, Rodar, Limpar, Segmentar, Avaliar, Exportar MD e Exportar TXT.

## SPEC-042 — Preview do prompt na TUI
- [ ] SPEC-042 concluída — [spec_042.md](spec-042/spec_042.md)
- [ ] T01 — Implementar handler do botão `Preview`.
- [ ] T02 — Integrar validação de entrada da SPEC-040.
- [ ] T03 — Montar input do `PromptBuilder` com briefing, scores e restrições.
- [ ] T04 — Exibir prompt renderizado em área read-only.
- [ ] T05 — Persistir sessão após preview bem-sucedido.

## SPEC-043 — Execução LLM pela TUI
- [ ] SPEC-043 concluída — [spec_043.md](spec-043/spec_043.md)
- [ ] T01 — Implementar handler do botão `Rodar`.
- [ ] T02 — Bloquear execução quando não houver prompt renderizado.
- [ ] T03 — Executar `AgentWrapper.run` fora da thread principal da TUI.
- [ ] T04 — Atualizar áreas de resultado com `AgentResult`.
- [ ] T05 — Persistir sessão ao finalizar execução, com sucesso ou erro.

## SPEC-044 — Bloqueio de gerações concorrentes
- [ ] SPEC-044 concluída — [spec_044.md](spec-044/spec_044.md)
- [ ] T01 — Adicionar estado `is_running` ou equivalente na TUI.
- [ ] T02 — Desabilitar/bloquear botão `Rodar` durante execução.
- [ ] T03 — Impedir dupla chamada mesmo com eventos rápidos de teclado/mouse.
- [ ] T04 — Restaurar estado ao finalizar worker/thread.
- [ ] T05 — Testar tentativa de execução concorrente e liberação após erro.

## SPEC-045 — Exibição de resultado bruto e JSON parseado
- [ ] SPEC-045 concluída — [spec_045.md](spec-045/spec_045.md)
- [ ] T01 — Implementar atualização das áreas de resultado bruto.
- [ ] T02 — Implementar parser tolerante para JSON final do gerador.
- [ ] T03 — Exibir JSON parseado quando possível.
- [ ] T04 — Exibir erro de parse e manter stdout visível quando inválido.
- [ ] T05 — Testar stdout válido, inválido, vazio e stderr com returncode não zero.

## SPEC-046 — Limpeza de saída
- [ ] SPEC-046 concluída — [spec_046.md](spec-046/spec_046.md)
- [ ] T01 — Implementar handler do botão `Limpar`.
- [ ] T02 — Limpar apenas campos de saída e parse.
- [ ] T03 — Preservar prompt renderizado e briefing atual.
- [ ] T04 — Atualizar estado persistido após limpeza.
- [ ] T05 — Testar que limpar não apaga entrada nem prompt.

## SPEC-047 — Seleção de executor LLM
- [ ] SPEC-047 concluída — [spec_047.md](spec-047/spec_047.md)
- [ ] T01 — Adicionar seletor `tool` com `codex` e `opencode`.
- [ ] T02 — Adicionar campo de modelo opcional.
- [ ] T03 — Mapear seleção para parâmetros do `AgentWrapper`.
- [ ] T04 — Ocultar ou desabilitar opções incompatíveis por executor.
- [ ] T05 — Testar seleção de tool e montagem correta do comando sem chamar CLI real.

## SPEC-048 — Seleção de sandbox
- [ ] SPEC-048 concluída — [spec_048.md](spec-048/spec_048.md)
- [ ] T01 — Adicionar seletor de sandbox à TUI.
- [ ] T02 — Validar `read-only`, `workspace-write` e `danger-full-access`.
- [ ] T03 — Condicionar habilitação do sandbox ao executor `codex`.
- [ ] T04 — Preservar decisão aberta sobre esconder ou exibir `danger-full-access`.
- [ ] T05 — Testar valores válidos, valor inválido e comportamento com `opencode`.

## SPEC-049 — Estrutura de pastas do projeto
- [ ] SPEC-049 concluída — [spec_049.md](spec-049/spec_049.md)
- [ ] T01 — Criar `src/content_engine` para domínio, prompts e geração.
- [ ] T02 — Criar `src/tui` para aplicação Textual.
- [ ] T03 — Criar `prompts/interview` e `prompts/generator`.
- [ ] T04 — Criar `.data/sessions`, `exports` e `tests`.
- [ ] T05 — Adicionar arquivos de pacote/configuração necessários para imports estáveis.

## SPEC-050 — Loader de prompts Markdown
- [ ] SPEC-050 concluída — [spec_050.md](spec-050/spec_050.md)
- [ ] T01 — Implementar função `load_prompt(path_or_name)`.
- [ ] T02 — Definir paths para prompts de entrevista, geração, segmentação, avaliação e personas.
- [ ] T03 — Tratar arquivo ausente e erro de leitura com mensagens claras.
- [ ] T04 — Evitar acoplamento do loader com `PromptBuilder` além do carregamento de texto.
- [ ] T05 — Testar carregamento válido, arquivo ausente e encoding UTF-8.

## SPEC-051 — Renderização de templates
- [ ] SPEC-051 concluída — [spec_051.md](spec-051/spec_051.md)
- [ ] T01 — Implementar função `render_template(template, context)`.
- [ ] T02 — Definir padrão de placeholders aceito.
- [ ] T03 — Evitar interpolação insegura ou execução dinâmica.
- [ ] T04 — Preservar JSON, acentos e quebras de linha.
- [ ] T05 — Testar renderização completa, placeholder ausente e caracteres especiais.

## SPEC-052 — Testes do PromptBuilder
- [ ] SPEC-052 concluída — [spec_052.md](spec-052/spec_052.md)
- [ ] T01 — Criar testes para `feed`, `article` e `slide`.
- [ ] T02 — Garantir que cada prompt contenha apenas a persona correta.
- [ ] T03 — Garantir que regras de formatos inativos não apareçam no prompt.
- [ ] T04 — Verificar presença de briefing serializado, scores, restrições e saída JSON.
- [ ] T05 — Testar `tipo_de_post` inválido gerando erro.

## SPEC-053 — Testes de gateway
- [ ] SPEC-053 concluída — [spec_053.md](spec-053/spec_053.md)
- [ ] T01 — Testar gateway equilibrado aprovado e reprovado.
- [ ] T02 — Testar gateway desequilibrado aprovado com bruto concentrado válido.
- [ ] T03 — Testar reprovação por total bruto insuficiente.
- [ ] T04 — Testar reprovação por personalidade insuficiente.
- [ ] T05 — Testar reprovação quando apenas personalidade é dominante.

## SPEC-054 — Testes de scoring
- [ ] SPEC-054 concluída — [spec_054.md](spec-054/spec_054.md)
- [ ] T01 — Testar `criar_scores_iniciais`.
- [ ] T02 — Testar `atualizar_scores` com deltas válidos.
- [ ] T03 — Testar normalizado limitado em 100 por categoria.
- [ ] T04 — Testar cálculo de `total_bruto` e `total_normalizado`.
- [ ] T05 — Testar rejeição ou correção de negativos, acima de 100 e categorias ausentes.

## SPEC-055 — Testes do AgentWrapper
- [ ] SPEC-055 concluída — [spec_055.md](spec-055/spec_055.md)
- [ ] T01 — Testar montagem de comando para `codex`.
- [ ] T02 — Testar montagem de comando para `opencode`.
- [ ] T03 — Testar parse de eventos JSONL válidos.
- [ ] T04 — Testar JSONL inválido, timeout, CLI ausente e returncode não zero.
- [ ] T05 — Garantir que nenhum teste unitário invoque executáveis reais.

## SPEC-056 — Testes de persistência
- [ ] SPEC-056 concluída — [spec_056.md](spec-056/spec_056.md)
- [ ] T01 — Testar criação de `.data/sessions/current-session.json`.
- [ ] T02 — Testar restauração de JSON válido.
- [ ] T03 — Testar comportamento com arquivo inexistente.
- [ ] T04 — Testar JSON inválido/corrompido.
- [ ] T05 — Testar schema parcial com defaults seguros.

## SPEC-057 — Testes do exporter
- [ ] SPEC-057 concluída — [spec_057.md](spec-057/spec_057.md)
- [ ] T01 — Testar exportação Markdown com conteúdo final.
- [ ] T02 — Testar exportação TXT com conteúdo final.
- [ ] T03 — Testar sanitização de nomes com espaços, acentos e caracteres especiais.
- [ ] T04 — Testar criação do diretório de exportação.
- [ ] T05 — Testar que exportação não acontece automaticamente após geração.

## SPEC-058 — Testes da TUI de preview
- [ ] SPEC-058 concluída — [spec_058.md](spec-058/spec_058.md)
- [ ] T01 — Testar erro quando tema, plataforma ou objetivo estiverem vazios.
- [ ] T02 — Testar erro quando briefing autoral não for JSON válido.
- [ ] T03 — Testar renderização do prompt para tipo de post válido.
- [ ] T04 — Testar exibição do prompt na área read-only.
- [ ] T05 — Testar persistência automática após preview.

## SPEC-059 — Testes de segmentação
- [ ] SPEC-059 concluída — [spec_059.md](spec-059/spec_059.md)
- [ ] T01 — Testar parse de segmentos válidos.
- [ ] T02 — Testar JSON inválido.
- [ ] T03 — Testar segmento com campos ausentes.
- [ ] T04 — Testar ids duplicados.
- [ ] T05 — Testar ordem inválida ou não sequencial.

## SPEC-060 — Testes de contrato da geração
- [ ] SPEC-060 concluída — [spec_060.md](spec-060/spec_060.md)
- [ ] T01 — Testar presença de `conteudo`, `metadados` e `alertas`.
- [ ] T02 — Testar metadados `tipoDePost`, `plataforma`, `personaUsada`, `tipoAutoria` e `tipoGateway`.
- [ ] T03 — Testar `usoDePrimeiraPessoa`, `baseNarrativaPrincipal` e `restricoesAplicadas`.
- [ ] T04 — Testar fallback de exibição quando JSON estiver inválido.
- [ ] T05 — Testar alertas quando restrições de geração impedirem narrativa pessoal forte.

## SPEC-061 — Post Engine V4: entrevista autoral
- [x] SPEC-061 concluída — [spec_061.md](spec-061/spec_061.md)
- [x] Domínio V4, respostas originais imutáveis e ledger de evidências.
- [x] Exploração aberta, validação fail-closed e gateway híbrido.
- [x] Lacunas, aprofundamento, briefing derivado e projeção `derived.interview`.
- [x] GUI com dimensões flat compartilhadas por contador, lista e gráfico.
- [x] Corpus e métricas determinísticas de qualidade.
- [x] Remoção final dos contratos legados conforme `specs/spec-061/tasks.md`.
