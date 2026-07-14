# SPEC — Post Engine V4

## 1. Objetivo

Reconstruir completamente o mecanismo de entrevista.

A V4 será uma quebra de contrato com as versões anteriores, preservando apenas a essência do produto:

> Extrair conteúdo humano, autoral e utilizável antes de qualquer organização editorial.

A entrevista não deve montar o post por meio das perguntas. Primeiro ela explora o tema, coleta respostas humanas e identifica sinais autorais. Somente depois avalia suficiência, lacunas e necessidade de aprofundamento.

---

## 2. Princípio central

### Fluxo atual

```text
EIXO PREDEFINIDO
→ PERGUNTA DIRECIONADA
→ RESPOSTA PREVISÍVEL
→ EIXO PREENCHIDO
→ POST PRATICAMENTE ESCRITO PELA ENTREVISTA
```

### Fluxo V4

```text
TEMA
→ EXPLORAÇÃO ABERTA
→ RESPOSTA HUMANA
→ EXTRAÇÃO DE SINAIS
→ GATEWAY HÍBRIDO
→ ANÁLISE DE LACUNAS
→ APROFUNDAMENTO QUANDO NECESSÁRIO
→ ENCERRAMENTO
```

As dimensões não controlam o início da entrevista.

Elas são usadas posteriormente para interpretar o material e identificar oportunidades de aprofundamento.

---

# 3. Fase 0 — Pesquisa e engenharia reversa

Nenhuma implementação da V4 começa antes da conclusão desta fase.

A pesquisa deve ser longa o suficiente para compreender o comportamento real da ferramenta, não apenas sua estrutura de código.

## 3.1 Inventário funcional

Mapear:

* início da entrevista;
* geração e seleção de perguntas;
* validação das perguntas;
* armazenamento das respostas;
* avaliação das respostas;
* extração de evidências;
* atualização do estado autoral;
* gateway;
* encerramento;
* briefing;
* geração;
* exportação;
* retomada de sessões.

Para cada fluxo, registrar:

```text
ENTRADA
SAÍDA
ESTADO ALTERADO
PROMPT UTILIZADO
MODELO UTILIZADO
COMPONENTE RESPONSÁVEL
CONSUMIDORES POSTERIORES
COMPORTAMENTO DE ERRO
```

## 3.2 Inventário de contratos

Levantar:

* schemas persistidos;
* contratos HTTP;
* entidades;
* arquivos de sessão;
* tipos do frontend;
* prompts estruturados;
* `question_brief`;
* `question_quality`;
* `answer_assessment`;
* `evidence_ledger`;
* `interview_plan`;
* `gateway`;
* `memory_pack`;
* briefing autoral.

Classificar cada campo como:

```text
ESSENCIAL
DERIVADO
DUPLICADO
LEGADO
EDITORIAL
AUTORAL
INCONSISTENTE
SEM CONSUMIDOR
```

## 3.3 Rastreamento de dados

Criar o mapa completo:

```text
PERGUNTA
→ RESPOSTA ORIGINAL
→ NORMALIZAÇÃO
→ EXTRAÇÃO
→ EVIDÊNCIA
→ SINAL
→ DIMENSÃO
→ GATEWAY
→ BRIEFING
→ CONTEÚDO
```

Deve ser possível descobrir:

* a origem de cada informação;
* qual IA realizou cada transformação;
* onde o texto original foi preservado;
* onde a interpretação foi adicionada;
* se alguma informação editorial foi tratada como fala do usuário.

## 3.4 Auditoria dos prompts

Para cada prompt, verificar:

* se pressupõe uma tese;
* se pressupõe experiência;
* se entrega o conflito;
* se entrega a conclusão;
* se recebe a estrutura futura do post;
* se recebe `expected_evidence`;
* se exige formato artificial de resposta;
* se mistura entrevista com organização editorial;
* se gera perguntas compostas;
* se gera perguntas impossíveis de responder;
* se perguntas rejeitadas ainda são exibidas.

Regra obrigatória:

```text
PERGUNTA_REJEITADA
→ NÃO_PODE_SER_EXIBIDA
```

## 3.5 Corpus de avaliação

Criar um corpus com sessões de:

* post;
* artigo;
* short carousel;
* long slide;
* entrevistas boas;
* entrevistas condicionadas;
* entrevistas excessivamente longas;
* respostas curtas;
* histórias fortes;
* pouca autoria;
* encerramento prematuro;
* prolongamento por lacunas opcionais.

## 3.6 Baseline da V3

Medir:

* número médio de perguntas;
* repetição semântica;
* perguntas compostas;
* perguntas condicionadas;
* respostas que apenas confirmam a pergunta;
* perguntas rejeitadas e exibidas;
* material humano aproveitado;
* material coletado e descartado;
* quantidade de texto efetivamente produzido pelo usuário;
* quantidade de conteúdo implicitamente produzido pela própria pergunta.

## 3.7 Entregáveis da pesquisa

A Fase 0 termina apenas com:

1. Arquitetura atual documentada.
2. Máquina de estados da entrevista.
3. Diagrama de sequência completo.
4. Catálogo de prompts.
5. Matriz de contratos e consumidores.
6. Mapa de persistência.
7. Inventário de inconsistências.
8. Corpus de avaliação.
9. Relatório comparativo V2 e V3.
10. Contratos removidos na V4.
11. Comportamentos preservados.
12. Plano de testes comparativos.

---

# 4. Novo vocabulário

## Sinal autoral

Informação identificada em uma resposta humana.

Exemplos:

* experiência;
* opinião;
* critério próprio;
* aprendizado;
* conflito;
* limite;
* evidência;
* emoção;
* linguagem característica;
* exemplo concreto.

## Evidência

Trecho exato da resposta que sustenta um sinal.

## Dimensão autoral

Área usada para interpretar sinais.

Exemplos:

* experiência vivida;
* posição própria;
* concretude;
* aprendizado;
* voz;
* tensão;
* aplicabilidade;
* autoridade;
* integridade epistêmica.

## Lacuna

Material relevante que ainda não apareceu ou apareceu com baixa sustentação.

## Oportunidade de aprofundamento

Lacuna cujo preenchimento pode aumentar significativamente a qualidade do conteúdo.

## Grupo

Organização visual de dimensões.

Um grupo não é uma dimensão e não pode ser contabilizado como uma.

---

# 5. Arquitetura da entrevista

## 5.1 Exploração aberta

A entrevista começa apenas com:

* tema;
* objetivo geral;
* formato;
* respostas anteriores;
* perguntas anteriores;
* sinais extraídos;
* restrições explícitas.

A pergunta inicial não recebe:

* estrutura do post;
* seções;
* CTA;
* conclusão esperada;
* lacuna editorial obrigatória;
* evidência esperada;
* dimensão obrigatória.

A geração deve explorar direções variadas.

Exemplos de direções internas:

```text
EXPERIÊNCIA
OPINIÃO
MEMÓRIA
ERRO
DECISÃO
MUDANÇA DE CRENÇA
CONTRADIÇÃO
INCÔMODO
CASO CONCRETO
LIMITE
```

Essas direções não são um checklist.

---

## 5.2 Geração de candidatas

O sistema pode gerar múltiplas perguntas internamente.

Cada candidata deve ser avaliada por:

```text
RISCO_DE_INDUÇÃO
RISCO_DE_REPETIÇÃO
RISCO_DE_PERGUNTA_COMPOSTA
RELAÇÃO_COM_O_TEMA
POTENCIAL_DE_DESCOBERTA
FACILIDADE_DE_RESPOSTA
```

Regra:

```text
PERGUNTA_SELECIONADA =
  RELACIONADA_AO_TEMA
  E NÃO_INDUZ_RESPOSTA
  E NÃO_REPETITIVA
  E NÃO_COMPOSTA
  E RESPONDÍVEL
```

---

## 5.3 Preservação da resposta

A resposta deve possuir três representações separadas:

```text
RESPOSTA_ORIGINAL
RESPOSTA_NORMALIZADA
SINAIS_EXTRAÍDOS
```

A resposta original é imutável.

Nenhuma síntese, correção ou interpretação pode substituir o texto do usuário.

---

## 5.4 Extração de sinais

Após cada resposta, extrair:

* fatos declarados;
* histórias;
* experiências;
* opiniões;
* critérios;
* aprendizados;
* tensões;
* limites;
* consequências;
* artefatos técnicos;
* mecanismos;
* dados;
* frases próprias;
* incertezas;
* contradições;
* afirmações que precisam de confirmação.

Cada sinal deve possuir:

```text
TIPO
RESUMO
CONFIANÇA
ORIGEM
EVIDÊNCIAS
STATUS
```

Status possíveis:

```text
CONFIRMADO
INFERIDO
INCERTO
CONFLITANTE
```

---

# 6. Gateway de autoria híbrido

O gateway não pode ser aprovado exclusivamente pela LLM.

Ele combina:

```text
AVALIAÇÃO_NÃO_DETERMINÍSTICA_DA_LLM
+
HEURÍSTICA_DETERMINÍSTICA
```

## 6.1 Regra principal

```text
GATEWAY_APROVADO =
  LLM_APROVOU
  E
  (
    GATEWAY_EQUILIBRADO
    OU
    GATEWAY_DESEQUILIBRADO_FORTE
  )
  E
  NÃO_EXISTE_VETO_ABSOLUTO
```

A LLM é necessária, mas não suficiente.

A heurística determinística é necessária, mas não suficiente.

---

## 6.2 Gateway equilibrado

O gateway equilibrado aprova quando todas as dimensões essenciais atingem o mínimo aceitável.

```text
GATEWAY_EQUILIBRADO =
  PARA_TODA_DIMENSÃO_ESSENCIAL:
    PONTUAÇÃO_DA_DIMENSÃO >= MÍNIMO_ACEITÁVEL
```

Perfil:

```text
NENHUMA_DIMENSÃO_EXCEPCIONAL_OBRIGATÓRIA
E
NENHUMA_DIMENSÃO_ESSENCIAL_FRACA
```

---

## 6.3 Gateway desequilibrado forte

Permite aprovação quando o material possui pontos extremamente fortes, mesmo que algumas dimensões estejam abaixo do perfil equilibrado.

```text
GATEWAY_DESEQUILIBRADO_FORTE =
  QUANTIDADE_DE_DIMENSÕES_EXCEPCIONAIS >= MÍNIMO_EXCEPCIONAL
  E
  PONTUAÇÃO_GLOBAL >= MÍNIMO_DESEQUILIBRADO
  E
  NENHUMA_DIMENSÃO_CRÍTICA < PISO_ABSOLUTO
```

Exemplo conceitual:

```text
EXPERIÊNCIA_VIVIDA = EXCEPCIONAL
CONCRETUDE = EXCEPCIONAL
POSIÇÃO_PRÓPRIA = FORTE
APLICABILIDADE = PARCIAL
TENSÃO = FRACA
```

Esse perfil pode passar porque suas forças excepcionais sustentam o conteúdo.

---

## 6.4 Papel da LLM

A LLM avalia elementos difíceis de medir com regras fixas:

* autenticidade percebida;
* coerência narrativa;
* força da posição;
* originalidade;
* riqueza editorial;
* contradições semânticas;
* indução causada pelas perguntas;
* integridade epistêmica;
* relevância para o tema;
* possibilidade de produzir conteúdo sem inventar material.

A LLM deve retornar:

```text
APROVOU
CONFIANÇA
FORÇAS
FRAQUEZAS
RISCOS
JUSTIFICATIVA
```

---

## 6.5 Papel da heurística determinística

A heurística usa somente sinais rastreáveis.

Pode considerar:

* quantidade de evidências;
* respostas com experiência real;
* presença de exemplos concretos;
* presença de critérios próprios;
* densidade de detalhes;
* diversidade de sinais;
* repetição semântica;
* respostas vazias;
* respostas excessivamente curtas;
* afirmações sem evidência;
* contradições;
* dependência da formulação da pergunta;
* cobertura de dimensões essenciais;
* intensidade dos sinais;
* quantidade de evidências independentes.

Toda pontuação deve informar:

```text
DIMENSÃO
PONTUAÇÃO
EVIDÊNCIAS
REGRAS_ACIONADAS
```

---

## 6.6 Vetos absolutos

```text
VETO_ABSOLUTO =
  NENHUMA_EVIDÊNCIA_DO_USUÁRIO
  OU EXPERIÊNCIA_NÃO_CONFIRMADA
  OU CONTRADIÇÃO_GRAVE_NÃO_RESOLVIDA
  OU RESPOSTA_CONSTRUÍDA_PELA_PERGUNTA
  OU MATERIAL_INSUFICIENTE_PARA_O_FORMATO
  OU FALHA_DE_INTEGRIDADE_EPISTÊMICA
```

Quando existir veto:

```text
GATEWAY_APROVADO = FALSO
```

---

## 6.7 Resultado do gateway

O resultado deve informar:

```text
APROVADO
TIPO_DO_GATEWAY
LLM_APROVOU
HEURÍSTICA_APROVOU
GATEWAY_EQUILIBRADO
GATEWAY_DESEQUILIBRADO_FORTE
PONTUAÇÃO_GLOBAL
DIMENSÕES_EXCEPCIONAIS
DIMENSÕES_FRACAS
VETOS
LACUNAS_RELEVANTES
JUSTIFICATIVA
```

Tipos possíveis:

```text
EQUILIBRADO
DESEQUILIBRADO_FORTE
REPROVADO
```

---

# 7. Análise de lacunas

As lacunas aparecem somente após a extração.

O sistema não pergunta porque uma dimensão existe no catálogo.

Ele pergunta porque o material atual apresenta uma deficiência relevante.

Exemplos:

```text
EXISTE_OPINIÃO
E NÃO_EXISTE_CASO_CONCRETO
→ LACUNA_DE_CONCRETUDE
```

```text
EXISTE_EXPERIÊNCIA
E NÃO_EXISTE_APRENDIZADO
→ LACUNA_DE_REFLEXÃO
```

```text
EXISTE_TESE
E NÃO_EXISTE_LIMITE
→ LACUNA_DE_TENSÃO
```

```text
EXISTE_HISTÓRIA
E MECANISMO_TÉCNICO_ESTÁ_CONFUSO
→ LACUNA_DE_CLAREZA
```

---

# 8. Seleção do aprofundamento

Nem toda lacuna gera uma nova pergunta.

```text
DEVE_APROFUNDAR =
  LACUNA_RELEVANTE
  E GANHO_ESPERADO_ALTO
  E ENTREVISTA_NÃO_APROVADA
  E LIMITE_DE_PERGUNTAS_NÃO_ATINGIDO
```

Quando o gateway já estiver aprovado:

```text
LACUNA_OPCIONAL
→ NÃO_PROLONGA_ENTREVISTA_AUTOMATICAMENTE
```

---

# 9. Encerramento

```text
ENCERRAR_ENTREVISTA =
  GATEWAY_APROVADO
  E NÃO_EXISTE_LACUNA_CRÍTICA
```

Também encerrar quando:

```text
GANHO_MARGINAL_DA_PRÓXIMA_PERGUNTA = BAIXO
OU LIMITE_DE_PERGUNTAS_ATINGIDO
OU USUÁRIO_SOLICITOU_ENCERRAMENTO
```

A quantidade de dimensões preenchidas não é critério isolado de encerramento.

---

# 10. Modelo conceitual V4

Entidades principais:

```text
SESSÃO_DE_ENTREVISTA
CONTEXTO_DO_TEMA
PERGUNTA_CANDIDATA
PERGUNTA_SELECIONADA
RESPOSTA_DO_USUÁRIO
EVIDÊNCIA
SINAL_AUTORAL
DIMENSÃO_AUTORAL
PERFIL_AUTORAL
AVALIAÇÃO_LLM
AVALIAÇÃO_DETERMINÍSTICA
RESULTADO_DO_GATEWAY
LACUNA
DECISÃO_DE_APROFUNDAMENTO
ENCERRAMENTO
```

---

# 11. Quebra de contrato

A V4 terá contratos próprios.

Sessões antigas poderão:

* ser visualizadas;
* ser exportadas;
* ser abertas em modo legado;
* ser convertidas por um migrador separado.

A V4 não deve persistir como conceitos centrais:

* cobertura fixa de eixos;
* `required_axes`;
* percentual de preenchimento editorial;
* 27 eixos obrigatórios;
* perguntas organizacionais misturadas à entrevista humana;
* estrutura do post durante a entrevista;
* scores sem evidência rastreável;
* `memory_pack` duplicando informações já presentes nas evidências.

---

# 12. GUI V4

## 12.1 Problema atual

A interface informa:

```text
6 / 8 EIXOS CAPTURADOS
```

Mas o gráfico mostra apenas:

```text
EVIDÊNCIAS OBRIGATÓRIAS
LACUNAS DO FORMATO
```

Esses dois elementos são grupos, não eixos.

O contador usa os itens internos, enquanto o gráfico usa os grupos.

```text
COLEÇÃO_DO_CONTADOR != COLEÇÃO_DO_GRÁFICO
```

Essa divergência produz uma visualização semanticamente incorreta.

---

## 12.2 Regra da nova GUI

```text
COLEÇÃO_CONTABILIZADA
=
COLEÇÃO_LISTADA
=
COLEÇÃO_RENDERIZADA
```

Grupos podem organizar dimensões, mas nunca substituí-las no gráfico ou no contador.

---

## 12.3 Tela principal

Exibir:

```text
ESTADO_DA_ENTREVISTA
QUALIDADE_AUTORAL
SINAIS_ENCONTRADOS
DIMENSÕES_OBSERVADAS
LACUNAS_RELEVANTES
EVIDÊNCIAS
HISTÓRICO
```

Não exibir cobertura de taxonomia como objetivo principal.

---

## 12.4 Estados das dimensões

```text
NÃO_OBSERVADA
FRACA
PARCIAL
SUFICIENTE
FORTE
EXCEPCIONAL
CONFLITANTE
NÃO_APLICÁVEL
```

`NÃO_OBSERVADA` não significa erro obrigatório.

---

## 12.5 Painel de dimensão

Ao selecionar uma dimensão, exibir:

* estado;
* pontuação determinística;
* avaliação semântica;
* confiança;
* sinais;
* evidências literais;
* respostas de origem;
* regras acionadas;
* lacunas;
* possibilidade de aprofundamento;
* justificativa.

---

## 12.6 Visualizações

```text
SE QUANTIDADE_DE_DIMENSÕES >= 5
E DIMENSÕES_SÃO_COMPARÁVEIS
→ RADAR_PODE_SER_UTILIZADO
```

```text
SE QUANTIDADE_DE_DIMENSÕES < 5
→ UTILIZAR_BARRAS_OU_LISTA
```

```text
GRUPOS
→ NÃO_SÃO_EIXOS_DO_RADAR
```

Dimensões não aplicáveis devem ser removidas do denominador.

---

## 12.7 Progresso da entrevista

Estados:

```text
EXPLORANDO
MATERIAL_HUMANO_IDENTIFICADO
APROFUNDANDO
MATERIAL_SUFICIENTE
CONCLUÍDA
```

O progresso representa maturidade da entrevista, não quantidade de categorias preenchidas.

---

# 13. Épicos

## Épico 0 — Pesquisa

Engenharia reversa, corpus, contratos, prompts e baseline.

## Épico 1 — Domínio V4

Criar estado, persistência e contratos independentes.

## Épico 2 — Motor de exploração

Gerar perguntas abertas, variadas e não condicionadas.

## Épico 3 — Extração

Criar sinais e evidências rastreáveis.

## Épico 4 — Heurística determinística

Calcular dimensões, forças, pisos, vetos e pontuação global.

## Épico 5 — Avaliação LLM

Avaliar autoria, coerência, originalidade e integridade.

## Épico 6 — Gateway híbrido

Combinar LLM com gateway equilibrado ou desequilibrado forte.

## Épico 7 — Lacunas e aprofundamento

Gerar novas perguntas somente quando o ganho esperado justificar.

## Épico 8 — GUI

Corrigir a distinção entre grupos, dimensões e sinais.

## Épico 9 — Avaliação comparativa

Executar V3 e V4 sobre o mesmo corpus.

## Épico 10 — Migração

Manter leitura legada e remover dependências antigas gradualmente.

---

# 14. Critérios de aceitação

1. Perguntas iniciais não recebem estrutura editorial.
2. Perguntas não pressupõem respostas.
3. Perguntas compostas são bloqueadas.
4. Perguntas rejeitadas nunca são exibidas.
5. Respostas originais permanecem imutáveis.
6. Todo sinal possui evidência.
7. Toda pontuação determinística é explicável.
8. A LLM não aprova o gateway isoladamente.
9. A heurística não aprova o gateway isoladamente.
10. O gateway equilibrado exige todas as dimensões essenciais acima do mínimo.
11. O gateway desequilibrado exige forças excepcionais e ausência de falhas críticas.
12. Vetos absolutos impedem aprovação.
13. Uma história excepcional pode compensar dimensões secundárias fracas.
14. Lacunas opcionais não prolongam uma entrevista aprovada.
15. O sistema explica por que perguntou e por que encerrou.
16. A GUI diferencia grupo, dimensão, sinal e evidência.
17. Contador, lista e gráfico usam a mesma coleção.
18. O gráfico não apresenta dois grupos como oito eixos.
19. A V4 produz menos respostas induzidas que a V3.
20. A V4 preserva mais linguagem original do usuário.

---

# 15. Não objetivos

A V4 não deve:

* preservar os contratos internos da V3;
* preencher uma taxonomia completa;
* montar o post durante a entrevista;
* perguntar sobre títulos, CTAs ou transições na fase humana;
* exigir todos os tipos de evidência;
* transformar toda lacuna em pergunta;
* inventar experiências;
* aceitar como autoria conteúdo produzido pela formulação da própria pergunta;
* usar apenas a LLM como gateway;
* usar apenas regras determinísticas como gateway.

---

# 16. Resultado esperado

```text
DESCOBRIR
→ OUVIR
→ PRESERVAR
→ EXTRAIR
→ MEDIR
→ INTERPRETAR
→ APROFUNDAR
→ ENCERRAR
```

A entrevista volta a ser o coração da ferramenta.

A organização editorial passa a trabalhar sobre conteúdo humano já extraído, em vez de produzir artificialmente esse conteúdo por meio de perguntas condicionadas.
