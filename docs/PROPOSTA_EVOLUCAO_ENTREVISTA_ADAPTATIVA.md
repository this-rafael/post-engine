# Proposta de evolução — entrevista híbrida com núcleo autoral e gates de qualidade

## Decisão

Não substituir a entrevista atual por uma conversa curta e permissiva. Evoluí-la para um modelo **híbrido**:

1. preservar um **núcleo autoral obrigatório**, para não gerar conteúdo tecnicamente correto e humanamente genérico;
2. usar a taxonomia atual como **mapa de investigação e de rastreabilidade**, não como uma fila fixa de 27 slots;
3. aprofundar de forma **adaptativa**, apenas quando uma nova pergunta tiver ganho editorial mensurável;
4. separar a extração do autor da composição de hook, slides, transições e recursos visuais;
5. impedir que perguntas fracas sejam feitas e que respostas fracas sejam aceitas como material suficiente.

Essa é uma mudança de **motor comum para todos os tipos de conteúdo**, não uma exceção para `long_slide`. Cada formato configura profundidade, evidências exigidas e orçamento; todos usam os mesmos gates de pergunta, resposta, autoria, suficiência e saturação.

O problema atual não é existir rigor. É confundir rigor com completar campos. O novo sistema deve ser rigoroso sobre **qualidade da evidência**, não sobre a quantidade de eixos que receberam algum texto.

## O que a entrevista atual acerta — e deve ser preservado

A entrevista atual tem méritos importantes:

- obriga o conteúdo a ir além da primeira opinião técnica;
- tenta capturar experiência, convicção, medo, aprendizado, limite e relação com o leitor;
- reduz a chance de o compositor inventar uma persona genérica para o autor;
- cria rastreabilidade entre o que o autor disse e o que será publicado;
- força a existência de contrapontos, limites e aplicação prática em formatos longos.

O erro é tratar cada dimensão como uma pergunta obrigatória e considerar qualquer resposta não vazia como evidência completa. Isso dilui justamente o valor dos traços humanos: na sessão analisada, `experiência`, `opinião`, `sentimento`, `aprendizado` e `personalidade` chegam a 100, mesmo quando algumas respostas são curtas, repetem uma tese ou não trazem detalhe reutilizável.

Portanto, os traços humanos **não serão removidos**. Eles passam a ser:

- necessidades de autoria com qualidade mínima;
- tags de cada evidência coletada;
- critérios para encerrar a entrevista;
- sinais para decidir o melhor follow-up.

## Diagnóstico do sistema atual

O comportamento observado é consequência de quatro regras combinadas:

- `required_batches_for_format()` em `src/content_engine/taxonomy.py` soma todos os lotes humanos aos lotes organizacionais exigidos pelo formato. Para `long_slide`, isso produz sete lotes e 27 eixos.
- `batch_state_to_pack()` em `src/content_engine/interview_state.py` considera um eixo coberto quando existe qualquer texto não vazio.
- `interview_pack_completo()` em `src/content_engine/briefing.py` aceita o pack quando `covered_axes >= total_axes`; não mede relevância, especificidade, novidade ou autoria.
- `_finalizar_entrevista_batch()` em `src/content_engine/session_app.py` mantém a sessão aberta até a cobertura binária estar completa.

O resultado é burocrático porque o sistema não consegue distinguir estes estados:

| Estado | Exemplo | Tratamento correto |
| --- | --- | --- |
| Resposta forte | “Separar checkout e financeiro duplicou decisões; deploys precisavam andar juntos.” | Reutilizar em várias necessidades e aprofundar somente o detalhe que falta. |
| Resposta genérica | “Microsserviços adicionam complexidade.” | Não fechar uma necessidade; pedir uma consequência, caso ou limite. |
| Resposta fora de foco | A pergunta pede evidência e a pessoa repete o hook. | Reparar uma vez ou registrar ausência; não marcar cobertura. |
| Limite honesto | “Nunca vivi isso; só vi em outro time.” | Preservar a limitação e trocar a estratégia de pergunta. |
| Necessidade editorial | “Qual hook você usaria?” | Resolver depois, na composição; não cobrar do autor. |

## Princípios do meio-termo

1. **Núcleo humano obrigatório; taxonomia total não obrigatória.** O sistema não encerra sem autoria reconhecível, mas também não exige que toda sessão responda a todos os subeixos.
2. **Resposta aceita não é resposta preenchida.** Cada necessidade tem sua própria definição de evidência suficiente.
3. **Uma pergunta deve revelar uma descoberta.** Perguntas compostas, genéricas ou que apenas reformulam tese são inválidas.
4. **Profundidade vem de sondar a evidência certa.** Uma boa entrevista pode voltar ao mesmo caso duas vezes, desde que cada retorno extraia fato, consequência, critério ou limite novo.
5. **A autoria não é um adorno.** Experiência, vocabulário, convicção e ambivalência são gates de qualidade do conteúdo final.
6. **O formato não deve fazer o autor executar trabalho de composição.** Storyboard, hook, transição e escaneabilidade são derivados pelo sistema e apresentados para revisão.
7. **Não existe entrevista infinita.** Quando a falta é de fonte, repertório ou escopo — e não de uma pergunta melhor — o sistema deve declarar isso em vez de insistir.

## Modelo proposto

### 1. Taxonomia preservada, com papéis diferentes

Os eixos atuais continuam existindo, mas deixam de ter a mesma força de finalização.

| Grupo atual | Papel no modelo híbrido |
| --- | --- |
| `humano.interno` | Fonte principal do núcleo autoral. `sentimento`, `desejo`, `medo`, `vulnerabilidade` e `personalidade` permanecem como sinais investigáveis. |
| `humano.cognitivo` e `humano.biografico` | Sondas adaptativas para obter critério, mudança de opinião, experiência e repertório. |
| `humano.relacional` | Evidência de intenção, limite, relação com o leitor e transformação desejada. |
| `organizacional.argumento` | Necessidades de tese, mecanismo, evidência e tensão. São condicionais ao formato e à força do material já obtido. |
| `organizacional.arquitetura` | Exigência de aplicação para conteúdos técnicos longos: exemplo, artefato, sequência, decisão ou edge case. |
| `organizacional.formato` | Especificação para o compositor. Não abre perguntas obrigatórias, salvo quando o autor explicitamente pede coautoria de formato. |

O objetivo é conservar a inteligência da taxonomia sem transformar seu inventário em roteiro literal da conversa.

### 2. Núcleo autoral obrigatório

Todo conteúdo precisa passar por este núcleo. Não significa uma pergunta para cada linha: uma resposta forte pode satisfazer duas necessidades, mas uma resposta genérica não pode satisfazer todas.

| Necessidade autoral | Evidência aceitável | O que não basta |
| --- | --- | --- |
| Âncora situada | caso vivido, observação direta, cena, decisão concreta ou limite de experiência declarado | definição abstrata sem contexto |
| Posição própria | tese com convicção, discordância, preferência ou princípio do autor | “depende” sem critério |
| Custo ou aprendizado | consequência observada, erro, mudança de opinião, arrependimento ou trade-off aceito | lista genérica de prós e contras |
| Tensão ou limite | onde a tese falha, risco de interpretação, contexto em que não se aplica | ressalva decorativa (“claro que depende”) |
| Voz e intenção | frase, vocabulário recorrente, preocupação com o leitor ou forma própria de explicar | slogan genérico intercambiável |

Regras de suficiência do núcleo:

- `posição própria` e `tensão ou limite` são sempre obrigatórios;
- deve existir uma `âncora situada` ou uma limitação honesta de experiência;
- para `long_slide` e `article`, pelo menos quatro das cinco necessidades precisam estar em nível forte;
- uma única resposta pode fechar no máximo duas necessidades do núcleo, e precisa trazer trechos de evidência distintos para cada uma;
- se não houver experiência própria, o sistema não inventa uma. Registra o limite e exige mais precisão em posição, critério ou observação.

Isso preserva a ambição humana da entrevista atual, mas impede que “sentimento” ou “personalidade” virem perguntas artificiais como “qual é o seu traço de personalidade ao explicar arquitetura?”. O sistema deve inferir esses sinais de respostas naturais e perguntar por eles apenas se ainda não houver voz autoral reconhecível.

### 3. Profundidade técnica e editorial por formato

Depois do núcleo autoral, o sistema investiga apenas as lacunas que o formato realmente exige.

| Formato | Material autoral mínimo | Profundidade adicional |
| --- | --- | --- |
| `post` | posição, âncora ou observação, limite e ação para o leitor | uma consequência ou microexemplo se a tese ainda for ampla |
| `short_carousel` | posição visual, contraste concreto, limite e ação | um mecanismo curto ou antes/depois que sustente os cards |
| `long_slide` | quatro sinais fortes do núcleo, incluindo âncora e aprendizado/custo | mecanismo aplicável, exemplo/artefato e critério de decisão |
| `article` | quatro ou cinco sinais fortes do núcleo, incluindo contraponto | mecanismo causal, evidência, edge case e critério defensável |

Para `long_slide`, um “artefato” pode ser um fluxo, uma mudança real, uma comparação, uma métrica, uma árvore de decisão ou um plano de corte. Não precisa ser uma pergunta sobre slides.

### 4. Invariantes para todos os tipos de conteúdo

Os formatos não devem ter controladores de entrevista diferentes. O que varia é o perfil declarativo, nunca a qualidade mínima do processo.

| Invariante | `post` | `short_carousel` | `long_slide` | `article` |
| --- | --- | --- | --- | --- |
| Pergunta com `need_id`, `why_now` e evidência esperada | obrigatório | obrigatório | obrigatório | obrigatório |
| Avaliação semântica da resposta | obrigatório | obrigatório | obrigatório | obrigatório |
| Gate de traços humanos | proporcional ao formato | proporcional ao formato | mais alto | mais alto |
| Reparo único para resposta promissora | obrigatório | obrigatório | obrigatório | obrigatório |
| Separação entre autoria e composição editorial | obrigatório | obrigatório | obrigatório | obrigatório |
| Encerramento por riqueza/saturação, não por texto não vazio | obrigatório | obrigatório | obrigatório | obrigatório |

Consequência de arquitetura: um novo formato só pode ser adicionado por meio de um `InterviewProfile`, com:

- necessidades autorais mínimas;
- necessidades técnicas/editoriais condicionais;
- gate humano;
- mínimo, alvo e guarda de perguntas;
- política de composição posterior.

Ele não pode cair silenciosamente no fluxo legado de lotes obrigatórios. Isso evita que `post`, carrossel ou artigo continuem com o problema atual enquanto `long_slide` recebe um tratamento mais sofisticado.

### 5. Ledger de evidências, não apenas respostas por eixo

Cada trecho útil vira uma evidência canônica e pode receber várias tags.

```json
{
  "id": "ev_checkout_financeiro",
  "texto_fonte": "A independência existia mais no diagrama do que no domínio.",
  "origem": "autor",
  "tipos": ["caso_vivido", "posicao", "aprendizado", "frase_autoral"],
  "eixos_legados": [
    "interno.vulnerabilidade",
    "cognitivo.aprendizado",
    "argumento.tese"
  ],
  "qualidade": {
    "especificidade": "forte",
    "autoria": "forte",
    "novidade": "alta"
  },
  "usos_editoriais": ["hook", "caso", "tensao", "criterio_de_decisao"]
}
```

Assim, o sistema preserva rastreabilidade e cobertura humana, sem duplicar a mesma fala em `memory_pack`, `flat_answers`, histórico e vários eixos como se fossem descobertas independentes.

## Gate 1 — qualidade da pergunta

O entrevistador não deve receber liberdade para perguntar qualquer coisa plausível. Antes de mostrar uma pergunta, o sistema deve exigir um `QuestionBrief` estruturado:

```json
{
  "need_id": "custo_ou_aprendizado",
  "intent": "concretizar_consequencia",
  "evidencia_esperada": "uma mudança, incidente ou decisão que revele o custo do corte checkout/financeiro",
  "why_now": "há um caso forte, mas ainda não há consequência operacional citável",
  "pergunta": "Qual mudança concreta mostrou que checkout e financeiro ainda precisavam evoluir juntos?",
  "estrategia_se_nao_houver_caso": "pedir observação ou limite honesto",
  "risco_de_repeticao": "baixo"
}
```

Uma pergunta só pode ser exibida se passar nestes critérios:

1. tem **uma descoberta principal**, não uma lista de cinco pedidos;
2. aponta para uma necessidade realmente ausente ou fraca;
3. descreve a evidência esperada e por que ela alteraria o conteúdo final;
4. está ancorada no briefing ou em uma fala anterior do autor;
5. não é semanticamente equivalente a pergunta ou evidência já existente;
6. é respondível sem exigir que o autor invente números, casos ou certezas;
7. não delega ao autor decisão de storyboard, hook, número de slides ou escaneabilidade;
8. prevê uma saída honesta quando o autor não viveu o caso.

Implementação recomendada:

- gerar de duas a três candidatas para a mesma lacuna;
- aplicar validadores determinísticos para tamanho, múltiplas interrogações, repetição textual e campos obrigatórios;
- aplicar um avaliador semântico para aderência ao `need_id`, novidade e carga cognitiva;
- escolher apenas a candidata de maior ganho e descartar as demais;
- regenerar se nenhuma atingir o mínimo.

Se o sistema não consegue explicar `why_now` e `evidencia_esperada`, ele não tem motivo suficiente para interromper o autor com outra pergunta.

## Gate 2 — qualidade da resposta

Depois de cada resposta, o sistema a classifica como `aceita`, `reparo`, `limite_declarado` ou `não_aproveitável`. Não existe mais “texto não vazio = eixo coberto”.

```json
{
  "relevancia": 0,
  "especificidade": 0,
  "autoria": 0,
  "alavancagem_editorial": 0,
  "novidade": 0,
  "integridade_epistemica": "confirmada",
  "estado": "reparo",
  "necessidades_parcialmente_atendidas": ["posicao"],
  "lacuna_restante": "falta uma consequência observável",
  "reparo_sugerido": "Que efeito isso trouxe para deploy, contrato ou incidente?"
}
```

Cada dimensão pode usar escala `0–2`:

| Dimensão | 0 | 1 | 2 |
| --- | --- | --- | --- |
| Relevância | foge da pergunta | toca no alvo | responde diretamente ao alvo |
| Especificidade | abstração | exemplo parcial | fato, decisão, consequência ou limite identificável |
| Autoria | frase intercambiável | opinião reconhecível | voz, convicção, vivência ou vocabulário próprio |
| Alavancagem editorial | não gera conteúdo útil | gera um ponto | sustenta hook, caso, contraste, critério ou fechamento |
| Novidade | repete o ledger | nuance pequena | amplia materialmente o mapa de evidências |

Não usar uma soma cega para aceitar tudo. A aceitação é específica por necessidade:

- **âncora situada:** relevância ≥ 1, especificidade ≥ 1 e autoria ≥ 1;
- **posição:** relevância ≥ 1 e autoria = 2;
- **mecanismo/artefato:** relevância ≥ 1 e especificidade = 2;
- **tensão/limite:** relevância ≥ 1, autoria ≥ 1 e existência explícita de condição, risco ou contraexemplo;
- **voz/intenção:** autoria = 2 ou padrão autoral consistente em duas evidências.

### Reparo, não punição

Quando a resposta for promissora, mas insuficiente, o sistema pode fazer **um** reparo focalizado. Não deve voltar a uma pergunta enorme nem abrir interrogatório.

| Sinal encontrado | Reparo útil |
| --- | --- |
| tese sem caso | “Em qual decisão isso apareceu?” |
| caso sem consequência | “O que passou a exigir coordenação depois do corte?” |
| opinião sem custo | “Que risco você aceita quando escolhe esse caminho?” |
| regra sem limite | “Em que contexto você não aplicaria isso?” |
| fato sem voz | “Qual frase você diria para um time prestes a repetir esse erro?” |

Depois de um reparo sem ganho, a necessidade deve ser marcada como `limite_declarado` ou `evidência_fraca`, não deve gerar três reformulações equivalentes.

## Avaliação de traços humanos: preservar e elevar o padrão

Os cinco scores atuais permanecem, mas mudam de semântica. Em vez de `100` por haver texto, cada score armazena a melhor evidência e o nível de qualidade.

```json
{
  "experiencia": {
    "nivel": "grounded",
    "evidence_ids": ["ev_checkout_financeiro"],
    "observacao": "há caso e consequência; falta data ou métrica, que não é obrigatória"
  },
  "opiniao": {
    "nivel": "distinctive",
    "evidence_ids": ["ev_diagrama_moderno"],
    "observacao": "posição inequívoca e frase própria"
  },
  "sentimento": {
    "nivel": "grounded",
    "evidence_ids": ["ev_ceticismo"],
    "observacao": "ceticismo ligado a projeto apressado"
  },
  "aprendizado": {
    "nivel": "reusable",
    "evidence_ids": ["ev_do_feeling_ao_grafo"],
    "observacao": "mudança de critério aplicável"
  },
  "personalidade": {
    "nivel": "distinctive",
    "evidence_ids": ["ev_perguntas_em_vez_de_definicoes"],
    "observacao": "padrão explicativo recorrente"
  }
}
```

Níveis sugeridos:

- `ausente`: nenhum sinal confiável;
- `mencionado`: há declaração, mas sem contexto ou utilidade editorial;
- `grounded`: há contexto, caso, decisão ou limite;
- `distinctive`: há linguagem ou posição dificilmente intercambiável;
- `reusable`: além de distintivo, sustenta trecho do conteúdo final.

Gate humano por formato:

| Formato | Gate mínimo |
| --- | --- |
| `post` | duas dimensões em `grounded`, sendo uma `opinião` ou `personalidade` |
| `short_carousel` | três dimensões em `grounded`, com uma em `distinctive` |
| `long_slide` | três dimensões em `grounded` e duas em `distinctive` ou `reusable`; uma delas deve ser `experiência`, `aprendizado` ou limite honesto explícito |
| `article` | quatro dimensões em `grounded` e duas em `distinctive` ou `reusable` |

Isso é o meio-termo: não há obrigação de perguntar por todos os traços, mas também não há autorização para encerrar uma entrevista longa apenas com tese e procedimento técnico.

## Como a próxima pergunta é escolhida

A seleção deixa de percorrer lotes em ordem fixa. Ela calcula a prioridade de cada lacuna:

```text
prioridade = criticidade_do_formato
           × qualidade_faltante
           × ganho_editorial_esperado
           × potencial_autoral
           − risco_de_repeticao
           − custo_de_resposta
```

Ordem de decisão:

1. corrigir uma necessidade do núcleo autoral que está ausente ou só `mencionada`;
2. aprofundar uma evidência humana forte que ainda não tem consequência, critério ou limite;
3. obter mecanismo/artefato exigido pelo formato;
4. buscar contraponto que evite conteúdo dogmático;
5. encerrar ou oferecer aprofundamento opcional.

O sistema também deve classificar a natureza da lacuna antes de perguntar:

| Tipo de lacuna | Ação correta |
| --- | --- |
| Autoral | perguntar ao autor por caso, critério, custo, frase, limite ou intenção. |
| Técnica aplicável | pedir um fluxo, decisão, comparação ou métrica já conhecida pelo autor. |
| De fonte externa | não pressionar o autor a fabricar evidência; pedir fonte, assumir limitação ou encaminhar à pesquisa. |
| Editorial | resolver na composição, sem reabrir a entrevista. |
| De escopo | propor estreitar a tese ou mudar o formato. |

Essa classificação é indispensável para evitar o caso “o número de perguntas nunca é suficiente”: se a lacuna não é autoral, nenhuma nova pergunta autoral vai resolvê-la.

## Duração: mínimo, alvo de riqueza e saturação

Quantidade de perguntas é um guardrail, não a definição de qualidade.

| Formato | Mínimo de elegibilidade | Alvo normal de riqueza | Guarda de sessão |
| --- | ---: | ---: | ---: |
| `post` | 3 | 4–5 | 6 |
| `short_carousel` | 4 | 5–6 | 7 |
| `long_slide` | 5 | 7–9 | 10 |
| `article` | 6 | 8–10 | 12 |

Regras:

- O mínimo **não encerra automaticamente**; apenas torna possível avaliar se a riqueza já é suficiente.
- A entrevista pode encerrar antes do alvo se uma ou duas respostas forem excepcionalmente densas e todos os gates estiverem atendidos.
- A entrevista pode ultrapassar o alvo uma pergunta por vez quando houver lacuna crítica com ganho alto e nenhuma repetição.
- Ao chegar à guarda, o sistema não continua no automático. Deve apresentar: o que falta, por que falta e as opções `encerrar com limite`, `mudar o escopo/formato` ou `continuar em modo de entrevista profunda`.
- O modo profundo é uma escolha explícita do autor e adiciona pequenos blocos de investigação; não cria uma entrevista infinita silenciosa.

### Critério de encerramento

A entrevista encerra automaticamente apenas quando todos os pontos abaixo forem verdadeiros:

1. o gate humano do formato foi atingido;
2. há posição, âncora/limite honesto, custo/aprendizado e tensão/limite aceitos;
3. o formato tem seu mecanismo, contraste ou artefato necessário;
4. não há lacuna crítica com ganho maior do que o custo de mais uma pergunta;
5. as duas últimas tentativas não indicam repetição ou saturação;
6. cada afirmação forte do futuro conteúdo pode ser ligada a evidência do autor ou marcada como síntese editorial.

Se a qualidade não sobe após dois reparos ou duas perguntas de alto ganho, o estado é `saturado`, não `incompleto para sempre`.

## Exemplo aplicado à sessão de microsserviços

O caso de checkout e financeiro já contém uma âncora humana excelente. O erro do fluxo atual foi voltar a pedir a mesma tese por vários eixos e, depois, pedir organização de slides.

Uma trajetória híbrida poderia ser:

1. **Âncora:** “Em qual mudança concreta vocês perceberam que checkout e financeiro ainda decidiam juntos?”
2. **Custo:** “O que essa dependência passou a exigir em deploy, contrato ou incidente?”
3. **Aprendizado:** “Que critério substituiu o feeling depois disso?”
4. **Limite:** “Em que situação você manteria isso no monólito, mesmo havendo pressão para extrair?”
5. **Aplicação:** “Que evidência você pediria numa reunião antes de aprovar uma extração?”
6. **Aprofundamento condicional:** se faltar artefato, “Quais sinais desse mapa de acoplamento fariam você adiar o corte?”

Daí o compositor deriva hook, comparação lateral, mapa de slides e CTA. O resultado ainda é exigente: coleta caso, custo, aprendizado, limite, critério, voz e aplicação. Mas não obriga o autor a responder questões que são trabalho editorial do sistema.

## Mudanças técnicas propostas

| Área | Mudança |
| --- | --- |
| `schemas.py` | Adicionar `InterviewPlan`, `InterviewNeed`, `EvidenceItem`, `QuestionBrief`, `QuestionQuality`, `AnswerAssessment`, `TraitAssessment` e `InterviewSufficiency`. Versionar o novo estado. |
| `taxonomy.py` | Manter os eixos e lotes como catálogo de tags e sondas. Adicionar `CORE_AUTHORIAL_NEEDS`, gates por formato e perfis de riqueza. Não remover eixos humanos da persistência. |
| `questions.py` | Separar `gerar_candidatas()`, `validar_qualidade_da_pergunta()`, `avaliar_resposta()` e `selecionar_proxima_pergunta()`. A geração deve ter `need_id`, `evidencia_esperada` e `why_now`. |
| `batch_validation.py` | Trocar cobertura binária por estados de evidência: `ausente`, `mencionada`, `aceita`, `limite_declarado`, `saturada`. |
| `interview_state.py` | Persistir plano, orçamento, ledger, avaliações, reparos usados, qualidade de traços e motivo de encerramento. Manter a projeção legada durante a migração. |
| `gateway.py` e `briefing.py` | Substituir `interview_pack_completo()` por uma avaliação em três níveis: `elegível`, `rico o suficiente`, `saturado/com limite`. |
| `session_app.py` | Mostrar “qual evidência ainda aumentaria o conteúdo” e “por que esta pergunta agora”. Oferecer `Pular com limite`, `Encerrar com resumo` e `Entrevista profunda`. |
| `prompt_builder.py` e prompts | Bloquear perguntas editoriais por padrão. Dar ao entrevistador resumo de evidências, não as projeções duplicadas completas. |
| composição | Receber evidências com origem e qualidade; gerar estrutura editorial separadamente e marcar `autor` versus `síntese editorial`. |

### Compatibilidade

1. O `InterviewPack` atual continua como projeção de compatibilidade para os estágios downstream.
2. Cada evidência aprovada pode preencher vários eixos legados, com referência ao mesmo `evidence_id`.
3. Os scores legados podem ser derivados de `TraitAssessment`, sem voltar a tratar texto não vazio como 100.
4. Sessões antigas ficam em modo `legacy_batch` ou são migradas explicitamente para um plano novo; nunca devem misturar os dois controladores na mesma entrevista.

## Plano de implementação

### PR 1 — contratos e preservação da taxonomia

**Objetivo:** introduzir o modelo híbrido sem alterar o fluxo atual.

- Criar os novos contratos e `schema_version`.
- Mapear cada eixo atual para `core`, `adaptive`, `editorial` ou `tag_only`.
- Adicionar `TraitAssessment` com níveis qualitativos e evidências de origem.
- Manter `answers`, `coverage` e `InterviewPack` como projeções legadas.

**Aceite:** uma sessão antiga restaura sem perda; uma sessão nova serializa plano, ledger e avaliações sem ativar o novo controlador.

### PR 2 — gate de pergunta e avaliador de qualidade

**Objetivo:** fazer a qualidade observável antes de mudar a duração da entrevista.

- Gerar `QuestionBrief` para cada pergunta legada, sem mudar sua ordem ainda.
- Implementar validadores de pergunta composta, repetição, ausência de `why_now` e delegação editorial.
- Avaliar cada resposta em relevância, especificidade, autoria, alavancagem, novidade e integridade.
- Registrar quando o fluxo atual marcou um eixo coberto, mas o avaliador classificou como `reparo` ou `não_aproveitável`.

**Aceite:** no cenário “a pergunta pede evidência e a resposta repete o hook”, a necessidade não é semanticamente aceita pelo avaliador.

**Status:** concluído e promovido ao fluxo principal. O avaliador agora decide
se uma necessidade é aceita, pede um único reparo focalizado ou registra limite
honesto; não é mais apenas telemetria de sombra.

### PR 3 — núcleo autoral e controlador híbrido

**Objetivo:** substituir lotes obrigatórios por gates de autoria mais aprofundamento adaptativo.

- Criar plano inicial por formato com mínimos, alvo de riqueza e guarda.
- Priorizar lacunas do núcleo humano antes de perguntas de formato.
- Gerar de duas a três candidatas por lacuna, validá-las e exibir apenas a melhor.
- Permitir um reparo focalizado por necessidade e registrar `limite_declarado`.
- Implementar `entrevista_elegivel()`, `entrevista_rica()` e `entrevista_saturada()`.

**Aceite:** `long_slide` com caso, custo, critério, limite, voz e artefato encerra sem percorrer todos os 27 eixos; um `long_slide` técnico sem voz ou limite não encerra só porque há tese e estrutura.

**Status:** concluído. Entrevistas novas usam o controlador adaptativo como
padrão; sessões `legacy` e `batch` persistidas continuam restauráveis.

### PR 4 — experiência de usuário e todos os formatos

**Objetivo:** aplicar a mesma infraestrutura aos quatro formatos, com exigências proporcionais.

- Habilitar perfis de `post`, `short_carousel`, `long_slide` e `article`.
- Mostrar o estado do núcleo autoral, as evidências aprovadas e a lacuna de maior ganho.
- Incluir ações explícitas para declarar limite, encerrar transparentemente ou iniciar entrevista profunda.

**Status:** concluído para os quatro perfis. A interface expõe núcleo autoral,
lacunas condicionais do formato, orçamento e motivo de suficiência.
- Exibir resumo de autoria antes da composição, separando fonte autoral de inferência editorial.

**Aceite:** cada formato usa o mesmo motor, mas `article` exige mais densidade de evidência que `post`; nenhum deles exige perguntas de storyboard para ser gerado.

**Regra de rollout:** a ativação pode ser gradual por risco, mas a implementação não pode criar lógica exclusiva de `long_slide`. Todo comportamento novo deve nascer em `InterviewProfile` compartilhado e ter teste para os quatro formatos.

### PR 5 — composição separada e retirada gradual do lote obrigatório

**Objetivo:** fazer a entrevista coletar autoria e a composição organizar forma.

- Remover `formato.transicoes`, `formato.escaneabilidade` e `formato.chamada` da regra de finalização.
- Fazer o compositor derivar estrutura, hook, CTA e storyboard do ledger.
- Reduzir projeções duplicadas no estado persistido.
- Comparar telemetria de sessões legadas e híbridas por formato antes de tornar o modo novo padrão.

**Aceite:** a geração preserva fontes autorais e não inventa fatos; a ausência de perguntas de formato não reduz a qualidade de storyboard.

## Testes e critérios de aceite globais

### Perguntas

- Nenhuma pergunta é exibida sem `need_id`, `why_now` e `evidencia_esperada`.
- Uma pergunta composta é rejeitada ou reescrita antes da UI.
- Uma pergunta semanticamente equivalente a uma anterior é rejeitada.
- Perguntas de hook, slides, transição e escaneabilidade não aparecem em entrevistas normais.

### Respostas e traços humanos

- Texto não vazio não eleva sozinho um score humano a `grounded`.
- Um caso concreto pode satisfazer experiência, aprendizado e tese, preservando o mesmo `evidence_id`.
- Uma tese genérica sem exemplo não fecha `âncora situada` nem `mecanismo`.
- Uma ausência honesta fecha a necessidade como limite, sem provocar repetição infinita.
- Para `long_slide`, o sistema não encerra sem o gate humano e sem artefato/mecanismo aplicável.

### Duração e encerramento

- Uma entrevista pode encerrar cedo se atingir o alvo de riqueza, não apenas o número mínimo.
- Uma entrevista pode pedir mais uma pergunta após o alvo se houver ganho crítico justificado.
- A guarda de sessão interrompe continuidade automática e apresenta decisão explícita ao autor.
- Duas tentativas sem novidade levam a `saturada`, não a novos lotes burocráticos.
- Os quatro formatos passam pelos mesmos estados: `coletando`, `reparo`, `elegível`, `rico`, `saturado` e `encerrado`.

### Geração final

- Toda afirmação factual forte pode ser ligada ao ledger ou marcada como síntese editorial.
- Citações/frases do autor são preservadas sem serem confundidas com organização editorial.
- O briefing final expõe limites e lacunas relevantes para evitar invenção na geração.

## Resultado esperado

O sistema deixa de perguntar “qual eixo ainda não recebeu texto?” e também não passa a perguntar pouco demais.

Ele passa a perguntar:

> “Qual evidência autoral ainda falta para que este conteúdo tenha caso, posição, custo, limite, voz e aplicação — e qual pergunta única tem maior chance de revelar isso?”

Esse desenho preserva o melhor da entrevista atual: exigência, humanidade, rastreabilidade e densidade. Ao mesmo tempo, elimina a parte que a torna enfadonha: repetição de tese, cobertura falsa e cobrança ao autor por escolhas que pertencem ao compositor.
