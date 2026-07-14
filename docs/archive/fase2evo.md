# Fase 2 Evo

## Objetivo
Transformar a fase 2 em um motor de entrevista por lotes que alimenta um contrato estruturado para todo o pipeline.

A nova fase 2 nao coleta mais apenas os 5 aspectos originais. Ela passa a produzir um `InterviewPack` com dois blocos:

- humanos
- organizacionais

Sem fallback silencioso. Se a LLM nao gerar perguntas validas, a execucao deve falhar de forma explicita e alarmante.

## Premissas inegociaveis
- Nenhum passo pode seguir com schema invalido.
- Nenhuma resposta da LLM pode ser aceita sem validacao estrita.
- Nenhum eixo pode ser inventado fora da taxonomia oficial.
- Nenhuma pergunta pode ficar sem eixo associado.
- Nenhum fallback local pode mascarar falha da LLM.
- Toda fase subsequente deve consumir o mesmo contrato estruturado.
- Toda sessao persistida precisa ser versionada.

## Taxonomia Oficial

### Humanos
```text
interno:
  sentimento, desejo, medo, vulnerabilidade, personalidade

cognitivo:
  opiniao, crencas, aprendizado, valores

biografico:
  experiencia, identidade, repertorio

relacional:
  intencao, relacao_com_publico, conflito, transformacao, limite
```

### Organizacionais
```text
argumento:
  tese, contexto, evidencia, tensao

arquitetura:
  estrutura, didatica, aplicabilidade

formato:
  transicoes, escaneabilidade, chamada
```

### Regras de aplicacao por formato
- `post`: pode operar com perfil organizacional reduzido e configuravel.
- `short_carousel`: deve cobrir a taxonomia organizacional completa.
- `long_slide`: deve cobrir a taxonomia organizacional completa.
- `article`: deve cobrir a taxonomia organizacional completa.

## Contrato Central

O plano assume a criacao de um conjunto pequeno de contratos compartilhados:

- `AxisDefinition`
- `QuestionBatch`
- `InterviewAnswer`
- `InterviewCoverage`
- `InterviewPack`
- `QuestionGenerationError`

### `AxisDefinition`
Responsavel por registrar a fonte unica de verdade de cada eixo.

Campos esperados:
- `id`
- `label`
- `kind` (`humano` ou `organizacional`)
- `group`
- `description`
- `required_by_formats`
- `weight_by_format`

Safeguards:
- IDs unicos.
- Grupo obrigatorio.
- Tipo obrigatorio.
- Nenhum eixo fora da taxonomia entra no sistema.
- O contrato deve cobrir os eixos antigos por mapeamento explicito.

### `QuestionBatch`
Responsavel por carregar o retorno da LLM em cada lote.

Campos esperados:
- `kind`
- `group`
- `expected_axes`
- `questions`

Cada pergunta deve carregar:
- `axis`
- `question`
- opcionalmente `rationale` ou metadado de trace, se isso ja existir no sistema

Safeguards:
- JSON estrito.
- Grupo retornado deve bater com o grupo solicitado.
- Eixos retornados devem bater com os esperados.
- Nenhum eixo extra.
- Nenhum eixo faltando.
- Nenhuma pergunta vazia.
- Nenhuma duplicidade por eixo.

### `InterviewPack`
Responsavel por consolidar a entrevista em uma estrutura pronta para briefing, prompt, execucao, segmentacao, ajuste e avaliacao.

Safeguards:
- Serializacao deterministica.
- Round-trip de persistencia sem perda de dados.
- Validacao de completude antes de qualquer consumo downstream.

### `QuestionGenerationError`
Erro explicito para falha da LLM.

Precisa carregar:
- formato
- lote
- eixos esperados
- eixos recebidos
- erro de parse ou validacao
- payload bruto, quando seguro registrar

Safeguards:
- Nunca converter erro em fallback.
- Nunca deixar o sistema continuar com lote parcial.
- Nunca ocultar a causa raiz.

## Fase 2: Entrevista

### Task 1: Definir a estrutura dos lotes
Criar a ordenacao oficial dos lotes:

1. `humano.interno`
2. `humano.cognitivo`
3. `humano.biografico`
4. `humano.relacional`
5. `organizacional.argumento`
6. `organizacional.arquitetura`
7. `organizacional.formato`

Safeguards:
- Ordem deterministicamente definida.
- O fluxo nao pode pular lote sem decisao explicita.
- O lote atual deve ser sempre derivado do estado persistido.

### Task 2: Gerar perguntas por lote
A LLM recebe apenas:
- briefing resumido
- formato atual
- lote atual
- eixos esperados
- respostas ja coletadas
- lacunas detectadas

O retorno deve ser validado antes de ser exibido.

Safeguards:
- Prompt especifico por lote.
- Nenhum contexto irrelevante.
- Nenhuma pergunta fora do lote.
- Nenhuma tentativa de continurar com retorno invalido.

### Task 3: Validar retorno da LLM
Implementar validacao rigida antes de persistir ou exibir qualquer pergunta.

Regras:
- o grupo retornado deve ser o grupo solicitado;
- todos os eixos esperados devem estar presentes;
- nenhum eixo extra pode existir;
- cada eixo precisa de pelo menos uma pergunta;
- perguntas vazias sao rejeitadas;
- duplicidade por eixo e rejeitada;
- JSON invalido gera erro explicito.

Safeguards:
- Teste de parser com payload invalido.
- Teste de eixo faltante.
- Teste de eixo extra.
- Teste de grupo divergente.
- Teste de pergunta vazia.

### Task 4: Persistir estado da entrevista
O estado precisa registrar:
- lote atual
- grupos concluido e pendente
- perguntas apresentadas
- respostas por `kind.group.axis`
- cobertura por eixo
- historico de falhas da LLM

Safeguards:
- Versao de schema obrigatoria.
- Sessao restaurada precisa reconstruir o lote correto.
- Round-trip de persistencia precisa preservar tudo.
- Migracao de sessoes antigas deve ser explicita.

### Task 5: Exibir erro de forma alarmante na UI
A interface da fase 2 deve deixar claro quando a LLM falhou.

Safeguards:
- Nenhuma mensagem generica do tipo "algo deu errado" sem detalhe.
- Mostrar lote, eixos esperados e eixos recebidos.
- Bloquear avance enquanto o lote nao estiver valido.
- Nao permitir que o erro seja confundido com estado normal.

### Task 6: Calcular cobertura
Calcular cobertura por eixo e por grupo.

Safeguards:
- Cobertura nao pode ser inferida de forma vaga.
- Cobertura precisa ser derivada das respostas reais.
- Um eixo sem resposta nunca pode aparecer como coberto.

## Impacto nas Fases Subsequentes

### Briefing
O briefing passa a alimentar a fase 2 com informacoes suficientes para decidir profundidade, obrigatoriedade e priorizacao dos eixos.

Mudancas necessarias:
- registrar formato de saida;
- registrar objetivo do conteudo;
- registrar publico;
- registrar canal;
- registrar nivel de profundidade;
- registrar transformacao esperada;
- registrar restricoes editoriais;
- usar essas informacoes para definir o perfil de entrevista.

Safeguards:
- Formato obrigatorio.
- Formato desconhecido deve falhar.
- Briefing incompleto nao pode iniciar entrevista.
- Regras de obrigatoriedade precisam vir da taxonomia, nao de texto solto.

### Prompt
O prompt final nao pode receber um texto concatenado solto. Ele precisa consumir o `InterviewPack`.

Mudancas necessarias:
- separar materia humana de arquitetura editorial;
- organizar respostas por grupo e eixo;
- gerar instrucoes especificas por formato;
- explicitar o que e prioridade no formato atual;
- manter rastreabilidade entre eixo e trecho do prompt.

Safeguards:
- Todo eixo obrigatorio para o formato precisa aparecer no prompt.
- Nenhum eixo pode ser inventado na montagem.
- Prompt deve falhar se o `InterviewPack` estiver incompleto.
- Teste de snapshot por formato para evitar regressao de contrato.

### Execucao
A execucao passa a ser um orquestrador de contrato, nao apenas um disparador de LLM.

Mudancas necessarias:
- validar briefing antes de gerar;
- validar entrevista antes de chamar a LLM de geracao final;
- enviar payload estruturado;
- registrar requisicao e resposta com rastreabilidade;
- interromper imediatamente quando algum eixo obrigatorio faltar.

Safeguards:
- Preflight obrigatorio.
- Falha antes da chamada quando o contrato estiver incompleto.
- Nenhuma execucao parcial silenciosa.
- Logs devem permitir diagnostico sem depender da UI.

### Segmentacao
A segmentacao deve usar os eixos organizacionais como guia de estrutura e ritmo.

Mudancas necessarias:
- mapear formato para segmentos editoriais;
- usar `estrutura`, `transicoes`, `escaneabilidade`, `didatica` e `chamada` como sinais de corte;
- segmentar por funcao editorial, nao apenas por tamanho.

Safeguards:
- Cada segmento precisa ter funcao clara.
- Segmentos sem eixo associado devem ser rejeitados.
- Formatos longos devem ter cobertura minima de estrutura.
- Carousel deve exigir `transicoes` e `chamada`.

### Ajuste
O ajuste deixa de ser uma revisao textual generica e passa a operar por eixo e trecho.

Mudancas necessarias:
- indicar eixo alvo do ajuste;
- indicar trecho afetado;
- indicar tipo de melhoria esperada;
- preservar restricoes de formato;
- reforcar o que estiver fraco sem destruir o contrato editorial.

Safeguards:
- Ajuste precisa declarar o eixo alvo.
- Ajuste nao pode apagar tese, chamada ou estrutura sem reposicao.
- Ajuste precisa falhar se a resposta vier fora do schema.
- O formato final deve continuar reconhecivel.

### Avaliacao
A avaliacao deve medir todos os eixos relevantes e ponderar por formato.

Mudancas necessarias:
- expandir score para eixos humanos e organizacionais;
- manter pesos diferentes por formato;
- normalizar score de maneira previsivel;
- expor cobertura por eixo e por grupo;
- manter compatibilidade com os 5 eixos antigos via mapeamento.

Safeguards:
- Score fora da faixa deve ser rejeitado.
- Eixo inventado nao entra na avaliacao.
- Todos os eixos obrigatorios do formato precisam aparecer no relatorio.
- Pesos devem ser testados por snapshot ou tabela canonica.

## Modulos Provaveis de Impacto

O plano deve afetar principalmente estes pontos do codigo:

- `src/content_engine/schemas.py`
- `src/content_engine/questions.py`
- `src/content_engine/interview.py`
- `src/content_engine/interview_state.py`
- `src/content_engine/briefing.py`
- `src/content_engine/prompt_builder.py`
- `src/content_engine/gateway.py`
- `src/content_engine/adjust_segment.py`
- `src/content_engine/scoring.py`
- `src/tui/app.py`

## Ordem Recomendada de Implementacao

1. Criar taxonomia central e schemas compartilhados.
2. Implementar validacao estrita para batch de perguntas.
3. Implementar fase 2 por lotes, sem fallback.
4. Atualizar persistencia e migracao de sessao.
5. Atualizar briefing para produzir o perfil de entrevista.
6. Atualizar prompt para consumir `InterviewPack`.
7. Atualizar execucao com preflight e falha explicita.
8. Atualizar segmentacao para usar eixos organizacionais.
9. Atualizar ajuste para operar por eixo.
10. Atualizar avaliacao com pesos por formato.
11. Atualizar UI para mostrar progresso, falhas e cobertura.

## Safeguards Transversais

### Corretude de contrato
- Validar entrada.
- Processar.
- Validar saida.
- Falhar se qualquer contrato quebrar.

### Corretude de LLM
- Nao aceitar payload parcial.
- Nao aceitar pergunta vaga.
- Nao aceitar eixo extra.
- Nao aceitar JSON invalido.
- Nao aceitar silencio operacional.

### Corretude de persistencia
- Versionar tudo.
- Migrar explicitamente.
- Testar round-trip.
- Preservar compatibilidade com sessoes antigas.

### Corretude de avaliacao
- Garantir cobertura por eixo.
- Garantir pesos por formato.
- Garantir comparabilidade entre formatos.

### Corretude de UX
- Erro deve ser visivel e util.
- O usuario precisa saber qual lote falhou.
- O usuario precisa saber quais eixos faltaram.
- A interface nao pode fingir que a fase terminou.

## Definicao de Pronto
A implementacao so pode ser considerada pronta quando:

- a fase 2 gera perguntas por lote para todos os grupos;
- a LLM falha de forma explicita quando o contrato nao bate;
- a entrevista pode ser persistida e restaurada sem perda;
- briefing, prompt, execucao, segmentacao, ajuste e avaliacao leem o mesmo contrato;
- os eixos novos estao mapeados e avaliados;
- os 5 eixos antigos continuam suportados por migracao ou mapeamento;
- testes cobrem schema valido, schema invalido e falha da LLM.
