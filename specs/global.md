Abaixo está uma lista de specs sugeridas para implementar o projeto de forma organizada, separando domínio, prompts, execução LLM, TUI, persistência, exportação e testes.

## SPEC-001 — Modelos de domínio e contratos Python

Define todos os tipos, `dataclasses`, `TypedDicts` e `Literal`s centrais da engine.

Inclui:

`InicioEntrevista`, `ScoresAutorais`, `AvaliacaoAutoralDaResposta`, `MemoryPack`, `ResultadoGateway`, `EstadoEntrevista`, `BriefingAutoral`, `SegmentoPost`, `ScoreDoPost`, `GenerationPromptInput` e `AgentResult`.

Essa spec deve garantir padronização de nomes em `snake_case` no código e compatibilidade com os contratos JSON enviados ou recebidos do LLM.

---

## SPEC-002 — Inicialização do estado da entrevista

Implementa a criação do estado inicial da entrevista.

Inclui:

criação dos scores zerados, gateway inicial reprovado, `memory_pack` vazio, lista de interações vazia, contador de rodadas e configuração de `max_rodadas`.

Também deve validar os dados iniciais obrigatórios:

`tema`, `plataforma`, `objetivo_do_post` e `tipo_de_post`.

---

## SPEC-003 — Scoring autoral

Implementa a atualização dos scores autorais.

Inclui:

score bruto, score normalizado, total bruto e total normalizado.

A função principal deve receber o score atual e a avaliação de uma resposta, somar os deltas no bruto e aplicar `min(valor, 100)` no normalizado.

Também deve impedir valores inválidos vindos do LLM, como deltas negativos, valores acima de 100 ou categorias ausentes.

---

## SPEC-004 — Gateway equilibrado

Implementa a regra de aprovação equilibrada.

Critério:

todas as categorias normalizadas precisam atingir 100 pontos.

Categorias:

`experiencia`, `opiniao`, `sentimento`, `aprendizado`, `personalidade`.

Essa spec deve ter testes cobrindo aprovação, reprovação e casos de borda.

---

## SPEC-005 — Gateway desequilibrado

Implementa a regra de aprovação desequilibrada.

Critérios:

total bruto maior ou igual a 600, personalidade maior ou igual a 80 e pelo menos uma categoria principal com 200 pontos ou mais.

Categorias principais:

`experiencia`, `opiniao`, `sentimento`, `aprendizado`.

Personalidade não pode ser usada como categoria dominante principal.

---

## SPEC-006 — Classificação do tipo de autoria

Implementa a classificação da autoria quando o gateway desequilibrado for aprovado.

Tipos possíveis:

`experiencial`, `opinativa`, `emocional`, `reflexiva`, `provocativa`, `hibrida`.

A classificação deve retornar `hibrida` quando experiência, opinião e aprendizado forem fortes. Caso contrário, deve escolher a categoria dominante entre experiência, opinião, sentimento e aprendizado.

---

## SPEC-007 — Restrições de geração

Implementa a geração de restrições narrativas com base nos scores brutos.

Objetivo:

impedir que o conteúdo final invente vivências, opiniões fortes, emoções ou aprendizados que o usuário não demonstrou.

Exemplos de restrições:

não escrever como relato prático se experiência for baixa, não forçar emoção se sentimento for baixo, não criar transformação pessoal artificial se aprendizado for baixo.

---

## SPEC-008 — Avaliação consolidada do gateway

Implementa a função `avaliar_gateway`.

Essa função deve decidir entre:

`equilibrado`, `desequilibrado` ou `reprovado`.

Quando aprovado, deve retornar tipo de autoria e restrições de geração. Quando reprovado, deve retornar próximas lacunas.

Essa spec depende das specs de scoring, gateway, classificação e restrições.

---

## SPEC-009 — Identificação de lacunas autorais

Implementa a função `identificar_lacunas`.

A função deve analisar os scores atuais e indicar quais aspectos ainda precisam melhorar.

Também deve diferenciar lacunas para gateway equilibrado e oportunidades para gateway desequilibrado.

Exemplo:

experiência baixa, personalidade baixa, opinião dominante ainda insuficiente para aprovação desequilibrada.

---

## SPEC-010 — Prompt de avaliação de resposta

Implementa o template responsável por avaliar uma resposta do usuário.

Entrada:

tema, pergunta feita, resposta do usuário, scores atuais e memory pack atual.

Saída esperada do LLM:

JSON com deltas, evidências, lacunas, aspecto mais fraco e próxima melhor pergunta.

Essa spec deve incluir validação defensiva do JSON retornado, sem confiar cegamente no LLM.

---

## SPEC-011 — Cliente de avaliação autoral

Implementa a camada que chama o LLM para avaliar respostas.

Responsabilidades:

montar prompt de avaliação, chamar executor configurado, receber resposta, parsear JSON, normalizar campos e retornar `AvaliacaoAutoralDaResposta`.

Essa camada pertence ao domínio de produto, não ao `AgentWrapper`.

---

## SPEC-012 — Atualização do memory pack

Implementa a atualização estruturada do `MemoryPack`.

Entrada:

tema, pergunta, resposta, avaliação da resposta e memory pack atual.

Saída:

memory pack atualizado sem duplicar informações e sem inventar fatos.

A spec deve garantir separação entre fatos vividos, opiniões, sentimentos, aprendizados, frases do usuário e traços de personalidade.

---

## SPEC-013 — Prompt de atualização do memory pack

Implementa o template usado pelo LLM para extrair sinais autorais da resposta.

O prompt deve preservar fatos concretos, frases naturais, lacunas e tensões.

Também deve impedir que opinião seja convertida em fato vivido.

---

## SPEC-014 — Geração de perguntas iniciais

Implementa a geração inicial de perguntas da entrevista.

A engine deve gerar perguntas para:

experiência, opinião, sentimento e aprendizado.

As perguntas precisam ser abertas, contextuais, específicas e não devem parecer formulário genérico.

---

## SPEC-015 — Meta-prompt de experiência

Implementa o prompt especializado em extrair vivência factual.

Deve buscar contexto prático, caso real, problema, decisão, consequência, antes/depois e envolvidos quando relevante.

Também deve evitar forçar experiência quando o usuário ainda não confirmou que viveu algo.

---

## SPEC-016 — Meta-prompt de opinião

Implementa o prompt especializado em extrair visão própria.

Deve buscar crítica, concordância, discordância, nuance, trade-off, posicionamento e premissas que o usuário acha erradas.

Não deve pedir apenas “qual sua opinião?”.

---

## SPEC-017 — Meta-prompt de sentimento

Implementa o prompt especializado em extrair percepção subjetiva.

Deve buscar incômodo, alívio, frustração, orgulho, ansiedade, entusiasmo, cansaço ou tensão emocional.

Não deve soar terapêutico nem forçar sentimentalismo.

---

## SPEC-018 — Meta-prompt de aprendizado

Implementa o prompt especializado em extrair transformação ou maturidade.

Deve buscar mudança de visão, critério prático, erro que ensinou algo, conselho ou conclusão amadurecida.

Não deve criar lição de moral artificial.

---

## SPEC-019 — Perguntas recursivas

Implementa a geração de novas perguntas após cada rodada.

A engine deve considerar:

scores atuais, memory pack, últimas interações, lacunas, proximidade dos gateways e categoria dominante.

A pergunta seguinte deve priorizar os aspectos mais fracos, mas também pode aprofundar a categoria dominante quando o gateway desequilibrado estiver próximo.

---

## SPEC-020 — Loop principal da entrevista

Implementa o fluxo completo da entrevista.

Responsabilidades:

criar estado inicial, obter contexto do tema, gerar perguntas, coletar respostas, avaliar respostas, atualizar scores, atualizar memory pack, avaliar gateway, gerar novas perguntas e encerrar quando aprovado ou quando atingir `max_rodadas`.

A saída deve ser um `BriefingAutoral`.

---

## SPEC-021 — Montagem do briefing autoral

Implementa a transformação do estado da entrevista em `BriefingAutoral`.

Deve agrupar respostas por aspecto autoral:

experiência, opinião, sentimento, aprendizado e personalidade.

Também deve incluir scores, gateway aprovado, restrições, memory pack, plataforma, objetivo, tipo de post e personalidade desejada.

O briefing não deve ser salvo automaticamente como arquivo separado.

---

## SPEC-022 — Personas oficiais

Implementa os arquivos Markdown das personas oficiais.

Arquivos:

`prompts/generator/personas/dev-interlocutor-feed.md`

`prompts/generator/personas/dev-interlocutor-article.md`

`prompts/generator/personas/dev-interlocutor-slide.md`

Cada persona deve conter regras de voz, estilo, ritmo, profundidade, guardrails e limites narrativos.

---

## SPEC-023 — Regras por tipo de post

Implementa os blocos separados de regras para cada formato.

Arquivos sugeridos:

`prompts/generator/rules-feed.md`

`prompts/generator/rules-article.md`

`prompts/generator/rules-slide.md`

Esses blocos não devem ser enviados simultaneamente ao LLM.

---

## SPEC-024 — PromptBuilder

Implementa a renderização condicional do prompt final de geração.

Entrada:

`GenerationPromptInput`.

Saída:

prompt final renderizado.

Responsabilidades:

selecionar persona por `tipo_de_post`, selecionar regras por `tipo_de_post`, serializar briefing, serializar scores, serializar restrições e montar o prompt final.

O `PromptBuilder` deve falhar se `tipo_de_post` for inválido.

---

## SPEC-025 — Contrato do PromptBuilder

Define os critérios de aceite do `PromptBuilder`.

Para `feed`, o prompt deve conter apenas `DevInterlocutorFeed`.

Para `article`, apenas `DevInterlocutorArticle`.

Para `slide`, apenas `DevInterlocutorSlide`.

O prompt não pode conter blocos condicionais concorrentes como “se for feed”, “se for article” ou “se for slide”.

Também deve conter briefing serializado, restrições e contrato de saída JSON.

---

## SPEC-026 — Prompt gerador base

Implementa o template base do gerador de conteúdo autoral.

O prompt deve receber:

tema, plataforma, objetivo, tipo de post, personalidade, tipo de gateway, tipo de autoria, persona ativa, regras do formato, scores, restrições e briefing autoral.

A saída obrigatória deve ser JSON válido com:

`conteudo`, `metadados` e `alertas`.

---

## SPEC-027 — Geração de conteúdo

Implementa a camada de produto que usa o `PromptBuilder` e o `AgentWrapper` para gerar o conteúdo final.

Responsabilidades:

montar input do prompt, renderizar prompt, executar LLM, capturar resultado, tentar parsear JSON e preservar stdout bruto em caso de erro.

Essa camada não deve fazer scoring da entrevista.

---

## SPEC-028 — AgentWrapper genérico

Implementa ou consolida o `AgentWrapper`.

Responsabilidades:

executar `codex` ou `opencode`, montar comandos CLI, passar workspace, modelo, sandbox, flags de JSON, capturar `stdout`, `stderr`, `returncode` e eventos.

O `AgentWrapper` não pode conhecer persona, briefing, scoring, tipo de post ou regras de produto.

---

## SPEC-029 — Robustez do AgentWrapper

Adiciona tratamento para falhas de subprocesso.

Deve cobrir:

timeout, CLI inexistente, erro de permissão, retorno diferente de zero, stdout vazio, stderr não vazio e JSONL inválido.

A função deve sempre retornar um `AgentResult` ou erro controlado pela aplicação.

---

## SPEC-030 — Segmentação do post

Implementa a divisão do conteúdo gerado em segmentos editáveis.

Entrada:

conteúdo completo.

Saída:

lista de `SegmentoPost`.

Cada segmento deve ter:

id, ordem, texto e papel interno.

O papel interno não precisa ser exibido ao usuário final.

---

## SPEC-031 — Prompt de segmentação

Implementa o template que pede ao LLM para dividir o conteúdo em segmentos editáveis.

Regras:

não adicionar títulos visíveis, não nomear seções no texto final, cada segmento deve ter sentido próprio e poder ser reescrito isoladamente.

Saída obrigatória:

JSON com array de segmentos.

---

## SPEC-032 — Ajuste por segmento

Implementa a reescrita isolada de um segmento.

Entrada:

conteúdo completo, segmento atual, pedido do usuário, personalidade e restrições.

Saída:

somente o segmento reescrito.

A engine não deve reescrever o post inteiro nem inventar novas experiências.

---

## SPEC-033 — Prompt de ajuste por segmento

Implementa o template específico para reescrita parcial.

O prompt deve preservar:

coerência com o post completo, tipo de autoria, objetivo do post, plataforma, restrições e voz do usuário.

Saída obrigatória:

JSON com `segmentoReescrito`.

---

## SPEC-034 — Avaliação do conteúdo gerado

Implementa a avaliação pós-segmentação do conteúdo final.

Critérios:

experiência, opinião, sentimento, aprendizado, personalidade, fidelidade e naturalidade.

A avaliação deve ocorrer depois da segmentação e não pode bloquear a segmentação.

---

## SPEC-035 — Prompt de avaliação do post

Implementa o template que avalia o conteúdo gerado contra o briefing autoral.

Entrada:

tema, conteúdo gerado e material autoral original.

Saída:

JSON com score, pontos fortes, pontos fracos e sugestões de melhoria.

---

## SPEC-036 — Exportação Markdown

Implementa exportação explícita do conteúdo final para `.md`.

Deve sanitizar o nome do arquivo, criar diretório `exports/` se necessário e salvar o conteúdo final.

A exportação deve ser ação manual do usuário, não consequência automática da geração.

---

## SPEC-037 — Exportação TXT

Implementa exportação explícita do conteúdo final para `.txt`.

Deve seguir as mesmas regras de sanitização e destino da exportação Markdown.

---

## SPEC-038 — Persistência de sessão

Implementa persistência automática da sessão da TUI.

Arquivo sugerido:

`.data/sessions/current-session.json`.

A sessão deve guardar entrada, prompt renderizado, briefing, scores, restrições, stdout, stderr, returncode, eventos, conteúdo gerado e segmentos.

Essa persistência não substitui exportação final.

---

## SPEC-039 — Restauração de sessão

Implementa a restauração da sessão ao abrir a TUI.

Se o arquivo estiver ausente, inválido ou corrompido, a TUI deve continuar funcionando com estado vazio.

Falha ao restaurar sessão não pode impedir uso da aplicação.

---

## SPEC-040 — Validação de entrada da TUI

Implementa validação dos campos operacionais da TUI.

Campos obrigatórios:

tema, plataforma, objetivo do post, tipo de post e briefing autoral JSON.

Também deve validar:

tipo de post permitido, scores numéricos e restrições como lista de strings.

---

## SPEC-041 — Tela única da TUI MVP

Implementa a primeira versão da interface em Textual.

A tela deve conter:

campos de entrada, seletores, briefing JSON, scores, restrições, preview de prompt, stdout, stderr, eventos, JSON extraído e botões de ação.

Botões mínimos:

Preview, Rodar, Limpar, Segmentar, Avaliar, Exportar MD e Exportar TXT.

---

## SPEC-042 — Preview do prompt na TUI

Implementa a ação de preview.

Fluxo:

validar campos, parsear briefing JSON, chamar `PromptBuilder`, mostrar prompt renderizado e persistir sessão.

O usuário deve conseguir inspecionar o prompt antes de executar o LLM.

---

## SPEC-043 — Execução LLM pela TUI

Implementa a execução do LLM a partir da interface.

Fluxo:

verificar se há prompt renderizado, impedir execução concorrente, chamar `AgentWrapper`, capturar resultado, exibir stdout, stderr, returncode e eventos.

A execução deve rodar em worker ou thread para não travar a interface.

---

## SPEC-044 — Bloqueio de gerações concorrentes

Implementa controle de execução única no MVP.

Enquanto uma geração estiver ativa, a TUI deve impedir nova execução.

Também deve refletir esse estado na interface, desabilitando ou bloqueando o botão de rodar.

---

## SPEC-045 — Exibição de resultado bruto e JSON parseado

Implementa exibição robusta do resultado.

A TUI deve tentar parsear o JSON final, mas não deve bloquear a exibição caso o JSON esteja inválido.

Em caso de erro, deve mostrar:

stdout bruto, stderr, returncode e erro de parse.

---

## SPEC-046 — Limpeza de saída

Implementa a ação `Limpar`.

Deve limpar stdout, stderr, eventos, returncode e JSON extraído.

O prompt renderizado deve permanecer.

A sessão deve ser persistida após a limpeza.

---

## SPEC-047 — Seleção de executor LLM

Implementa a seleção entre `codex` e `opencode`.

A TUI deve permitir escolher:

tool, modelo e parâmetros compatíveis.

Para `codex`, deve permitir sandbox.

Para `opencode`, não deve permitir anexar arquivos no MVP.

---

## SPEC-048 — Seleção de sandbox

Implementa o seletor de sandbox para `codex`.

Valores possíveis:

`read-only`, `workspace-write`, `danger-full-access`.

A spec deve deixar a decisão de produto aberta sobre exibir ou esconder `danger-full-access`, mas o código deve conseguir suportar os valores definidos no contrato.

---

## SPEC-049 — Estrutura de pastas do projeto

Cria a estrutura base do projeto.

Inclui:

`src/content_engine`, `src/tui`, `prompts/interview`, `prompts/generator`, `.data/sessions`, `exports` e `tests`.

Essa spec também deve garantir imports consistentes e baixo acoplamento entre engine, TUI e infraestrutura.

---

## SPEC-050 — Loader de prompts Markdown

Implementa carregamento de prompts a partir de arquivos Markdown.

Deve carregar templates de entrevista, avaliação, memory pack, segmentação, geração e personas.

No MVP, personas não serão editáveis pela TUI, mas devem estar versionadas em arquivos.

---

## SPEC-051 — Renderização de templates

Implementa função genérica para renderizar templates.

Pode ser simples, baseada em substituição de placeholders, desde que seja testável e previsível.

Deve evitar interpolação insegura e preservar JSON serializado sem corromper caracteres especiais.

---

## SPEC-052 — Testes do PromptBuilder

Cria testes automatizados para garantir renderização condicional.

Casos obrigatórios:

feed não contém article nem slide.

article não contém feed nem slide.

slide não contém feed nem article.

Prompt contém briefing, restrições, scores e contrato JSON.

Tipo inválido gera erro.

---

## SPEC-053 — Testes de gateway

Cria testes para gateway equilibrado, desequilibrado e reprovado.

Deve cobrir:

scores normalizados completos, bruto alto concentrado, personalidade insuficiente, total bruto insuficiente, categoria principal insuficiente e personalidade dominante indevida.

---

## SPEC-054 — Testes de scoring

Cria testes para atualização de scores.

Deve validar:

soma dos deltas, clamp do normalizado em 100, total bruto, total normalizado e rejeição ou correção de deltas inválidos.

---

## SPEC-055 — Testes do AgentWrapper

Cria testes unitários para montagem de comandos e parse de JSONL.

Deve mockar `subprocess.run`.

Não deve chamar `codex` ou `opencode` reais nos testes unitários.

---

## SPEC-056 — Testes de persistência

Cria testes para salvar e restaurar sessão.

Deve cobrir:

arquivo inexistente, JSON inválido, schema parcial, escrita bem-sucedida e restauração bem-sucedida.

---

## SPEC-057 — Testes do exporter

Cria testes para exportação `.md` e `.txt`.

Deve validar:

criação de diretório, sanitização de nome, conteúdo salvo e extensão correta.

---

## SPEC-058 — Testes da TUI de preview

Cria testes para validar o fluxo de preview da TUI.

Deve garantir que:

campos obrigatórios são validados, briefing inválido é rejeitado, prompt é renderizado e sessão é persistida.

---

## SPEC-059 — Testes de segmentação

Cria testes para parsear e validar segmentos retornados pelo LLM.

Deve cobrir:

segmentos válidos, JSON inválido, campos ausentes, ids duplicados e ordem inválida.

---

## SPEC-060 — Testes de contrato da geração

Cria testes para validar o contrato esperado do JSON de saída do gerador.

Campos mínimos:

`conteudo`, `metadados`, `alertas`.

Também deve validar:

`usoDePrimeiraPessoa`, `baseNarrativaPrincipal`, `restricoesAplicadas`, `tipoDePost`, `plataforma`, `personaUsada`, `tipoAutoria` e `tipoGateway`.

---

## Ordem sugerida de implementação

Para o MVP operacional, a ordem mais segura é:

1. Modelos de domínio.
2. Scoring e gateways.
3. PromptBuilder.
4. AgentWrapper.
5. Loader/renderizador de prompts.
6. Geração de conteúdo.
7. Persistência.
8. Exportação.
9. TUI tela única.
10. Preview.
11. Execução LLM.
12. Parse de resultado.
13. Segmentação.
14. Avaliação pós-segmentação.
15. Testes principais.

A entrevista completa com scoring via LLM pode entrar na V1, conforme o roadmap do PRD.
