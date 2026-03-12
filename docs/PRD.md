Analise o PRD anexado e diga OK se entende ele plenamente 

# PRD — Engine de Entrevista Autoral para Geração de Conteúdo Humano

Versão: final atualizada  
Linguagem de referência dos blocos de implementação: Python  
Interface operacional prevista: Textual TUI  
Execução LLM prevista: Codex ou OpenCode via `AgentWrapper`

---

## 1. Visão geral

Este documento descreve uma engine de entrevista autoral baseada em LLM, cujo objetivo é extrair do usuário material humano, original e utilizável para geração de posts, artigos, carrosséis ou outros formatos de conteúdo.

A engine recebe um tema, entrevista o usuário de forma progressiva, avalia as respostas com base em critérios autorais e, ao atingir um gateway mínimo de qualidade, gera um briefing autoral estruturado para criação de conteúdo.

O sistema não busca apenas respostas tecnicamente corretas. Ele busca traços humanos que tornem o conteúdo menos genérico e mais fiel ao usuário.

Os principais aspectos analisados são:

* Experiência
* Opinião
* Sentimento
* Aprendizado
* Personalidade

A engine aceita dois tipos de aprovação:

* Gateway equilibrado: 500 pontos, com todas as categorias completas.
* Gateway desequilibrado: 600 pontos brutos, quando existe forte material autoral concentrado em uma ou mais categorias.

A premissa central é:

> Humanos nem sempre falam apenas sobre o que viveram. Mas o sistema não deve transformar ausência de experiência em falsa vivência.

---

## 2. Problema

Conteúdos gerados por IA tendem a soar genéricos quando não possuem material humano suficiente.

Mesmo quando o tema é bom, o texto pode parecer artificial se não houver:

* Vivências reais
* Opiniões próprias
* Sentimentos autênticos
* Aprendizados pessoais
* Traços de linguagem do usuário

A solução proposta é criar uma entrevista guiada por LLM que colete esses elementos antes da geração do conteúdo.

---

## 3. Objetivo do produto

Criar uma engine que:

1. Receba um tema.
2. Entenda o tema com ajuda de LLM.
3. Gere perguntas abertas e contextuais.
4. Colete respostas do usuário.
5. Avalie o valor autoral de cada resposta.
6. Some pontuações por categoria.
7. Continue perguntando até atingir um gateway autoral.
8. Gere um briefing autoral.
9. Gere um post fiel ao material coletado.
10. Segmente o conteúdo em partes editáveis.
11. Permita ajustes por segmento.
12. Avalie o conteúdo gerado após a segmentação.
13. Permita exportação para Markdown e arquivo local.

---

## 4. Não objetivos

A primeira versão da engine não tem como objetivo:

* Validar se a opinião do usuário está correta.
* Corrigir tecnicamente todas as afirmações do usuário.
* Fazer checagem factual completa de todos os relatos pessoais.
* Criar uma rede social.
* Automatizar publicação em plataformas externas.
* Criar um editor visual avançado.
* Substituir revisão humana em conteúdos sensíveis.
* Permitir múltiplas gerações concorrentes.
* Editar personas pela TUI.
* Anexar arquivos ao OpenCode no MVP.
* Validar o JSON final por schema antes da exibição no MVP.

---

## 5. Usuários-alvo

A engine pode ser usada por:

* Profissionais que querem produzir posts autorais.
* Criadores de conteúdo.
* Especialistas técnicos.
* Consultores.
* Fundadores.
* Pessoas que querem transformar vivências e opiniões em conteúdo.
* Agências que produzem conteúdo para clientes.
* Produtos SaaS de escrita assistida por IA.

---

## 6. Entrada inicial da engine

A entrevista começa com os seguintes dados:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


TipoDePost = Literal["post", "article", "short_carousel", "long_slide"]


@dataclass(frozen=True)
class InicioEntrevista:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    personalidade: str | None = None
```

Exemplo:

```python
inicio = InicioEntrevista(
    tema="Single Responsibility Principle",
    plataforma="LinkedIn",
    objetivo_do_post="Gerar autoridade técnica e reflexão sobre qualidade de código",
    tipo_de_post="post",
    personalidade="escritor técnico, direto e reflexivo",
)
```

---

## 6.0 Quatro trilhas editoriais (PersoGenIA)

| Trilha | ID | Regra mental | Profundidade |
| --- | --- | --- | --- |
| Post | `post` | Uma ideia defendida pessoalmente | Média |
| Artigo | `article` | Uma pergunta investigada profundamente | Alta |
| Carrossel Curto | `short_carousel` | Uma ideia explicada visualmente (4–8 slides) | Baixa/Média |
| Slide Longo | `long_slide` | Um assunto ensinado visualmente (9+ slides) | Alta |

Valores legados migrados automaticamente: `feed` → `post`, `slide` → `short_carousel`.

O roteamento automático (`content_type_router`) sugere a trilha via LLM a partir de `tema` + `objetivo_do_post`, com override manual no TUI.

Entrevista e geração usam prompts dedicados por trilha (`prompts/interview/initial-{tipo}.md`, `prompts/generator/rules-{tipo}.md`).

---

## 6.1 Persona oficial para conteúdo do tipo `post`

Quando `tipo_de_post` for igual a `"post"`, a engine deve utilizar explicitamente a persona `DevInterlocutorPost` como referência principal de voz, estilo, ritmo, guardrails e regras de geração.

Essa persona define que conteúdos de post devem defender uma ideia pessoalmente: opinativos, diretos, críticos, técnicos, humanos, com atrito produtivo, sem virar artigo ou tutorial completo.

A definição completa da persona deve ficar versionada em:

```txt
prompts/generator/personas/dev-interlocutor-post.md
```

Resumo operacional obrigatório:

```yaml
name: DevInterlocutorPost
content_type: post
forced_content_shape: "conteúdo opinativo e direto"
use_emojis: false
max_length_linkedin: 1600
technical_depth: media
friction: alta
humor: medio
avoid_fake_autobiography: true
avoid_article_density: true
```

Regras essenciais:

* Abrir com atrito produtivo.
* Identificar o inimigo comum do tema.
* Corrigir premissas erradas quando surgirem.
* Preferir exemplos concretos e situações de trabalho.
* Usar humor como ferramenta de clareza, não como enfeite.
* Não inventar fatos, métricas, cases ou experiências pessoais reais.
* Não transformar post em artigo.
* Não usar CTA agressivo.
* Não escrever como guru, coach ou vendedor de curso.

---

## 6.2 Persona oficial para conteúdo do tipo `article`

Quando `tipo_de_post` for igual a `"article"`, a engine deve utilizar explicitamente a persona `DevInterlocutorArticle` como referência principal de voz, estilo, profundidade técnica, estrutura argumentativa, guardrails e regras de geração.

Essa persona define que conteúdos de artigo devem ser profundos, analíticos, tecnicamente rigorosos, claros, críticos, humanos, com atrito produtivo, com definição de conceitos, trade-offs, riscos, limitações e contraargumentos quando o tema exigir.

A definição completa da persona deve ficar versionada em:

```txt
prompts/generator/personas/dev-interlocutor-article.md
```

Resumo operacional obrigatório:

```yaml
name: DevInterlocutorArticle
content_type: article
forced_content_shape: "conteúdo técnico profundo acadêmico"
use_emojis: false
min_length: 2500
max_length: 9000
technical_depth: alta
friction: media
humor: baixo
avoid_fake_autobiography: true
avoid_post_style: true
include_concept_definitions: true
include_limitations: true
include_counterarguments: true
include_operational_consequences: true
```

Regras essenciais:

* Começar com tese clara.
* Definir conceitos importantes.
* Explicar trade-offs, riscos, limites e contraargumentos.
* Diferenciar fato, inferência e opinião técnica.
* Não inventar estudos, autores, dados ou referências.
* Não escrever artigo como post alongado.
* Não transformar nuance em enrolação.
* Não usar CTA agressivo.

---

## 6.3 Persona oficial para conteúdo do tipo `short_carousel`

Quando `tipo_de_post` for igual a `"short_carousel"`, a engine utiliza a persona `DevInterlocutorShortCarousel` para carrosséis curtos (4–8 slides) sobre UMA ideia visual.

```txt
prompts/generator/personas/dev-interlocutor-short-carousel.md
```

## 6.4 Persona oficial para conteúdo do tipo `long_slide`

Quando `tipo_de_post` for igual a `"long_slide"`, a engine utiliza a persona `DevInterlocutorLongSlide` para guias visuais longos (9+ slides) de ensino progressivo.

```txt
prompts/generator/personas/dev-interlocutor-long-slide.md
```

## 6.5 Legado `slide` (deprecado)

O tipo `slide` foi substituído por `short_carousel` e `long_slide`. Sessões antigas migram `slide` → `short_carousel`.

---

## 7. Aspectos autorais avaliados

### 7.1 Experiência

Mede vivências reais do usuário.

Evidências possíveis:

* Projetos reais
* Situações vividas
* Problemas enfrentados
* Decisões tomadas
* Contexto prático
* Antes e depois
* Consequências observáveis

Exemplo:

> Já trabalhei em um service que validava lead, integrava com CRM e calculava comissão ao mesmo tempo.

---

### 7.2 Opinião

Mede visão própria sobre o tema.

Evidências possíveis:

* Concordância
* Discordância
* Crítica
* Preferência
* Julgamento
* Nuance
* Visão de mundo
* Trade-offs

Exemplo:

> Para mim, SRP não é sobre deixar a classe pequena. É sobre deixar a responsabilidade explicável.

---

### 7.3 Sentimento

Mede percepção emocional ou subjetiva.

Evidências possíveis:

* Incômodo
* Frustração
* Alívio
* Orgulho
* Insegurança
* Entusiasmo
* Cansaço
* Ansiedade
* Impaciência

Exemplo:

> Eu fico desconfortável quando preciso mexer em um código onde qualquer alteração pode quebrar outra coisa.

---

### 7.4 Aprendizado

Mede transformação, maturidade ou mudança de visão.

Evidências possíveis:

* Lição prática
* Mudança de comportamento
* Critério adquirido
* Nova forma de trabalhar
* Erro que ensinou algo
* Conclusão amadurecida

Exemplo:

> Depois disso, comecei a separar validação, integração e regra de comissão desde o início.

---

### 7.5 Personalidade

Mede o quanto a resposta revela o jeito próprio do usuário pensar e falar.

Evidências possíveis:

* Frases naturais
* Metáforas
* Estilo de argumentação
* Vocabulário técnico ou informal
* Intensidade da opinião
* Tipo de incômodo
* Forma de concluir ideias
* Traços de pragmatismo, cautela, provocação ou humor

Exemplo:

> Código que precisa de contexto demais para ser alterado já começou a cobrar juros do time.

A personalidade é uma métrica transversal. Ela pode ser capturada em respostas sobre experiência, opinião, sentimento ou aprendizado.

---

## 8. Modelo de score

A engine usa dois tipos de score:

* Score bruto
* Score normalizado

O scoring autoral será feito via LLM.

A engine envia para o LLM:

* tema;
* pergunta feita;
* resposta do usuário;
* scores atuais;
* memory pack atual.

O LLM retorna:

* deltas por aspecto;
* evidências por aspecto;
* lacunas por aspecto;
* aspecto mais fraco;
* próxima melhor pergunta sugerida.

Heurísticas podem existir apenas como validação auxiliar, fallback ou proteção contra valores inválidos. O scoring principal é via LLM.

---

## 8.1 Score bruto

O score bruto acumula todo material autoral fornecido pelo usuário ao longo da entrevista.

Ele pode passar de 100 em cada categoria.

Exemplo:

```python
score_bruto = {
    "experiencia": 40,
    "opiniao": 260,
    "sentimento": 140,
    "aprendizado": 80,
    "personalidade": 120,
}
```

O score bruto representa volume total de material autoral.

---

## 8.2 Score normalizado

O score normalizado limita cada categoria a no máximo 100.

Exemplo:

```python
ASPECTOS_AUTORAIS = (
    "experiencia",
    "opiniao",
    "sentimento",
    "aprendizado",
    "personalidade",
)


score_normalizado = {
    aspecto: min(score_bruto[aspecto], 100)
    for aspecto in ASPECTOS_AUTORAIS
}
```

Exemplo completo:

```python
score_bruto = {
    "experiencia": 40,
    "opiniao": 100,
    "sentimento": 1000,
    "aprendizado": 100,
    "personalidade": 90,
}

score_normalizado = {
    aspecto: min(score_bruto[aspecto], 100)
    for aspecto in ASPECTOS_AUTORAIS
}
```

Resultado esperado:

```python
{
    "experiencia": 40,
    "opiniao": 100,
    "sentimento": 100,
    "aprendizado": 100,
    "personalidade": 90,
}
```

Mesmo que `sentimento` tenha 1000 pontos brutos, no score normalizado ele vale no máximo 100.

---

## 9. Avaliação de cada resposta

Cada resposta do usuário gera deltas de pontuação.

Uma pergunta pode ter foco em uma categoria, mas a resposta pode pontuar em várias.

Exemplo de pergunta:

> Você já aplicou SRP em algum projeto real?

Exemplo de resposta:

> Já trabalhei em um service que validava lead, integrava com CRM e calculava comissão. Eu achava aquilo perigoso porque qualquer mudança podia quebrar outra parte. Quando separamos as responsabilidades, senti um alívio porque ficou mais fácil testar.

Avaliação possível:

```python
avaliacao = {
    "deltas": {
        "experiencia": 60,
        "opiniao": 35,
        "sentimento": 30,
        "aprendizado": 40,
        "personalidade": 20,
    }
}
```

Essa resposta pontua em várias categorias porque contém:

* Experiência: projeto real com service acumulando responsabilidades.
* Opinião: o usuário considera perigoso misturar responsabilidades.
* Sentimento: alívio após a separação.
* Aprendizado: separar responsabilidades facilitou teste.
* Personalidade: modo pragmático de enxergar manutenção.

---

## 10. Estrutura da avaliação autoral

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict


AspectoAutoral = Literal[
    "experiencia",
    "opiniao",
    "sentimento",
    "aprendizado",
    "personalidade",
]


class PontuacaoAspectos(TypedDict):
    experiencia: int
    opiniao: int
    sentimento: int
    aprendizado: int
    personalidade: int


class ListaAspectos(TypedDict):
    experiencia: list[str]
    opiniao: list[str]
    sentimento: list[str]
    aprendizado: list[str]
    personalidade: list[str]


@dataclass(frozen=True)
class ProximaMelhorPergunta:
    aspecto: AspectoAutoral
    pergunta: str
    motivo: str


@dataclass(frozen=True)
class AvaliacaoAutoralDaResposta:
    resposta_id: str
    deltas: PontuacaoAspectos
    evidencias: ListaAspectos
    lacunas: ListaAspectos
    proxima_melhor_pergunta: ProximaMelhorPergunta | None = None
```

---

## 11. Prompt de avaliação de resposta

```txt
Você é um avaliador de material autoral para criação de conteúdo humano.

Tema:
{tema}

Pergunta feita:
{pergunta}

Resposta do usuário:
{resposta}

Scores atuais:
{scoresAtuais}

Memory pack atual:
{memoryPack}

Avalie quanto essa resposta acrescenta de material autoral em cada aspecto.

Aspectos:
- experiencia: fatos vividos, situações reais, contexto, projeto, caso concreto
- opiniao: visão própria, julgamento, concordância, discordância, crítica, nuance
- sentimento: emoção, incômodo, alívio, frustração, orgulho, insegurança, entusiasmo
- aprendizado: mudança de visão, maturidade, lição prática, transformação
- personalidade: jeito de falar, metáforas, estilo, preferências, traços individuais

Regras:
- Cada delta deve ir de 0 a 100.
- O delta representa apenas o que esta resposta adicionou.
- Não dê pontos por informação repetida que já estava nos scores ou no memory pack.
- Não avalie se o usuário está tecnicamente certo.
- Avalie se a resposta ajuda a criar um post autoral, humano e específico.
- Se algum aspecto já está completo no score normalizado, ainda extraia evidências, mas evite sugerir novas perguntas para ele.
- Nunca deixe um score passar de 100 no campo normalizado. O sistema fará clamp depois.

Retorne apenas JSON:

{
  "deltas": {
    "experiencia": 0,
    "opiniao": 0,
    "sentimento": 0,
    "aprendizado": 0,
    "personalidade": 0
  },
  "evidencias": {
    "experiencia": [],
    "opiniao": [],
    "sentimento": [],
    "aprendizado": [],
    "personalidade": []
  },
  "lacunas": {
    "experiencia": [],
    "opiniao": [],
    "sentimento": [],
    "aprendizado": [],
    "personalidade": []
  },
  "aspectoMaisFracoDepoisDessaResposta": "...",
  "proximaMelhorPergunta": {
    "aspecto": "...",
    "pergunta": "...",
    "motivo": "..."
  }
}
```

---

## 12. Atualização dos scores

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import cast


ASPECTOS_AUTORAIS = (
    "experiencia",
    "opiniao",
    "sentimento",
    "aprendizado",
    "personalidade",
)


@dataclass(frozen=True)
class ScoresAutorais:
    bruto: PontuacaoAspectos
    normalizado: PontuacaoAspectos
    total_bruto: int
    total_normalizado: int


def atualizar_scores(
    score_atual: ScoresAutorais,
    avaliacao: AvaliacaoAutoralDaResposta,
) -> ScoresAutorais:
    bruto = cast(
        PontuacaoAspectos,
        {
            aspecto: score_atual.bruto[aspecto] + avaliacao.deltas[aspecto]
            for aspecto in ASPECTOS_AUTORAIS
        },
    )

    normalizado = cast(
        PontuacaoAspectos,
        {
            aspecto: min(bruto[aspecto], 100)
            for aspecto in ASPECTOS_AUTORAIS
        },
    )

    return ScoresAutorais(
        bruto=bruto,
        normalizado=normalizado,
        total_bruto=sum(bruto[aspecto] for aspecto in ASPECTOS_AUTORAIS),
        total_normalizado=sum(
            normalizado[aspecto]
            for aspecto in ASPECTOS_AUTORAIS
        ),
    )
```

---

## 13. Gateways de aprovação

A entrevista pode ser aprovada de duas formas:

1. Gateway equilibrado
2. Gateway desequilibrado

---

## 14. Gateway equilibrado

O gateway equilibrado exige 500 pontos normalizados.

Ou seja, todas as categorias precisam estar completas.

```python
def passou_gateway_equilibrado(
    score_normalizado: PontuacaoAspectos,
) -> bool:
    return all(
        score_normalizado[aspecto] >= 100
        for aspecto in ASPECTOS_AUTORAIS
    )
```

Interpretação:

* O usuário viveu ou observou algo relevante.
* O usuário tem opinião própria.
* O usuário expressou sentimento ou percepção subjetiva.
* O usuário apresentou aprendizado ou transformação.
* O usuário demonstrou traços próprios de linguagem ou personalidade.

Esse gateway permite gerar posts mais completos, narrativos e pessoais.

---

## 15. Gateway desequilibrado

O gateway desequilibrado permite aprovar a entrevista mesmo quando as categorias não estão balanceadas.

Ele existe porque uma pessoa pode ser muito autoral mesmo sem ter muita experiência prática.

Exemplo:

```python
score_bruto = {
    "experiencia": 20,
    "opiniao": 260,
    "sentimento": 140,
    "aprendizado": 80,
    "personalidade": 120,
}

total_bruto = sum(score_bruto.values())
```

Nesse caso, o usuário não tem muita experiência factual, mas tem opinião, sentimento e personalidade suficientes para um post opinativo ou provocativo.

Regra:

```python
ASPECTOS_PRINCIPAIS = (
    "experiencia",
    "opiniao",
    "sentimento",
    "aprendizado",
)


def passou_gateway_desequilibrado(
    score_bruto: PontuacaoAspectos,
) -> bool:
    total_bruto = sum(
        score_bruto[aspecto]
        for aspecto in ASPECTOS_AUTORAIS
    )

    maior_categoria_principal = max(
        score_bruto[aspecto]
        for aspecto in ASPECTOS_PRINCIPAIS
    )

    return (
        total_bruto >= 600
        and score_bruto["personalidade"] >= 80
        and maior_categoria_principal >= 200
    )
```

Condições:

* Total bruto maior ou igual a 600.
* Personalidade maior ou igual a 80.
* Pelo menos uma categoria principal com 200 pontos ou mais.

Categorias principais:

* Experiência
* Opinião
* Sentimento
* Aprendizado

Personalidade não conta como categoria dominante principal. Ela atua como sustentação de autoria.

---

## 16. Avaliação do gateway

```python
from dataclasses import dataclass, field
from typing import Literal


TipoGateway = Literal["equilibrado", "desequilibrado", "reprovado"]

TipoAutoria = Literal[
    "experiencial",
    "opinativa",
    "emocional",
    "reflexiva",
    "provocativa",
    "hibrida",
]


@dataclass(frozen=True)
class ResultadoGateway:
    aprovado: bool
    tipo_gateway: TipoGateway
    tipo_autoria: TipoAutoria | None = None
    restricoes_de_geracao: list[str] = field(default_factory=list)
    proximas_lacunas: list[str] = field(default_factory=list)


def avaliar_gateway(scores: ScoresAutorais) -> ResultadoGateway:
    bruto = scores.bruto
    normalizado = scores.normalizado

    passou_equilibrado = passou_gateway_equilibrado(normalizado)

    maior_categoria_principal = max(
        bruto[aspecto]
        for aspecto in ASPECTOS_PRINCIPAIS
    )

    passou_desequilibrado = (
        scores.total_bruto >= 600
        and bruto["personalidade"] >= 80
        and maior_categoria_principal >= 200
    )

    if passou_equilibrado:
        return ResultadoGateway(
            aprovado=True,
            tipo_gateway="equilibrado",
            tipo_autoria="hibrida",
            restricoes_de_geracao=[],
        )

    if passou_desequilibrado:
        return ResultadoGateway(
            aprovado=True,
            tipo_gateway="desequilibrado",
            tipo_autoria=classificar_tipo_autoria(bruto),
            restricoes_de_geracao=gerar_restricoes_de_geracao(bruto),
        )

    return ResultadoGateway(
        aprovado=False,
        tipo_gateway="reprovado",
        proximas_lacunas=identificar_lacunas(scores),
    )
```

---

## 17. Classificação do tipo de autoria

Quando o gateway desequilibrado é aprovado, a engine deve identificar o eixo dominante do conteúdo.

```python
TipoAutoria = Literal[
    "experiencial",
    "opinativa",
    "emocional",
    "reflexiva",
    "provocativa",
    "hibrida",
]


def classificar_tipo_autoria(
    score_bruto: PontuacaoAspectos,
) -> TipoAutoria:
    if (
        score_bruto["experiencia"] >= 100
        and score_bruto["opiniao"] >= 100
        and score_bruto["aprendizado"] >= 100
    ):
        return "hibrida"

    categorias: dict[TipoAutoria, int] = {
        "experiencial": score_bruto["experiencia"],
        "opinativa": score_bruto["opiniao"],
        "emocional": score_bruto["sentimento"],
        "reflexiva": score_bruto["aprendizado"],
    }

    return max(categorias, key=lambda categoria: categorias[categoria])
```

---

## 18. Restrições de geração

As restrições servem para evitar que o post final invente autoridade que o usuário não demonstrou.

```python
def gerar_restricoes_de_geracao(
    score_bruto: PontuacaoAspectos,
) -> list[str]:
    restricoes: list[str] = []

    if score_bruto["experiencia"] < 50:
        restricoes.extend(
            [
                "Não escrever como relato de experiência prática.",
                "Não sugerir que o usuário viveu algo que não contou.",
                "Gerar o texto como opinião, reflexão, provocação ou leitura pessoal.",
            ]
        )

    if score_bruto["opiniao"] < 50:
        restricoes.extend(
            [
                "Evitar tom opinativo forte.",
                "Basear o texto mais em vivência, aprendizado ou observação.",
            ]
        )

    if score_bruto["sentimento"] < 50:
        restricoes.extend(
            [
                "Não forçar emoção.",
                "Manter tom mais analítico ou prático.",
            ]
        )

    if score_bruto["aprendizado"] < 50:
        restricoes.extend(
            [
                "Não criar transformação pessoal artificial.",
                "Evitar frases como “isso me ensinou que” se o usuário não demonstrou aprendizado.",
            ]
        )

    if score_bruto["personalidade"] < 80:
        restricoes.extend(
            [
                "Usar linguagem mais neutra.",
                "Evitar simular um estilo pessoal muito marcado.",
            ]
        )

    return restricoes
```

---

## 19. Memory pack

A engine não deve reenviar todo o histórico bruto para o LLM em todas as rodadas.

Ela deve manter um resumo estruturado chamado `memory_pack`.

```python
from dataclasses import dataclass, field


@dataclass
class MemoryPack:
    fatos_vividos: list[str] = field(default_factory=list)
    exemplos_concretos: list[str] = field(default_factory=list)
    opinioes: list[str] = field(default_factory=list)
    sentimentos: list[str] = field(default_factory=list)
    aprendizados: list[str] = field(default_factory=list)
    tracos_de_personalidade: list[str] = field(default_factory=list)
    frases_do_usuario: list[str] = field(default_factory=list)
    tensoes_ou_conflitos: list[str] = field(default_factory=list)
    pontos_ainda_fracos: list[str] = field(default_factory=list)
```

O `memory_pack` serve para:

* Gerar perguntas melhores.
* Evitar perguntas repetidas.
* Preservar contexto.
* Identificar lacunas.
* Alimentar o prompt de geração do post.
* Reduzir custo de contexto.
* Melhorar a coerência da entrevista.

O `memory_pack` pode ser salvo no estado persistido da sessão da TUI, mas o briefing autoral não deve ser salvo automaticamente como arquivo local separado.

---

## 20. Prompt para atualizar o memory pack

```txt
Extraia sinais autorais da resposta do usuário.

Tema:
{tema}

Pergunta:
{pergunta}

Resposta:
{resposta}

Avaliação da resposta:
{avaliacao}

Memory pack atual:
{memoryPackAtual}

Atualize o memory pack sem perder informações anteriores.

Regras:
- Preserve fatos concretos.
- Preserve frases naturais do usuário.
- Não invente experiências.
- Não transforme opinião em fato vivido.
- Não duplique informações já existentes.
- Marque lacunas que ainda precisam ser exploradas.

Retorne apenas JSON:

{
  "fatosVividos": [],
  "exemplosConcretos": [],
  "opinioes": [],
  "sentimentos": [],
  "aprendizados": [],
  "tracosDePersonalidade": [],
  "frasesDoUsuario": [],
  "tensoesOuConflitos": [],
  "pontosAindaFracos": []
}
```

---

## 21. Estratégia de perguntas

A engine deve gerar perguntas abertas, específicas e progressivas.

As perguntas devem evitar aparência de formulário genérico.

A cada rodada, a engine deve considerar:

* Scores atuais.
* Memory pack.
* Últimas perguntas e respostas.
* Lacunas restantes.
* Proximidade do gateway equilibrado.
* Proximidade do gateway desequilibrado.
* Categoria dominante, se houver.
* Personalidade capturada até o momento.

---

## 22. Decisão da próxima pergunta

A próxima pergunta deve priorizar:

1. Categorias abaixo de 100 no score normalizado.
2. Categorias necessárias para atingir gateway equilibrado.
3. Se houver excesso em uma categoria, evitar insistir nela.
4. Se o gateway desequilibrado estiver próximo, aprofundar a categoria dominante.
5. Se personalidade estiver baixa, puxar linguagem mais pessoal.
6. Se experiência estiver baixa, não forçar vivência; pedir caso real ou leitura honesta.
7. Se a pessoa não tiver experiência, adaptar para opinião, observação ou reflexão.

Exemplo:

```python
score_normalizado = {
    "experiencia": 40,
    "opiniao": 100,
    "sentimento": 100,
    "aprendizado": 100,
    "personalidade": 100,
}
```

Pergunta ruim:

> Qual sua opinião sobre isso?

Pergunta boa:

> Me conta um caso específico em que isso aconteceu: qual era o projeto, o que estava misturado no código e qual foi a consequência prática?

---

## 23. Algoritmo principal da entrevista

```python
from dataclasses import dataclass


@dataclass
class RespostaUsuario:
    pergunta: str
    texto: str


@dataclass
class InteracaoEntrevista:
    pergunta: str
    resposta: str
    avaliacao: AvaliacaoAutoralDaResposta


async def executar_entrevista(
    input_data: InicioEntrevista,
) -> "BriefingAutoral":
    state = criar_estado_inicial(input_data)

    contexto_do_tema = await pesquisar_ou_resumir_tema(input_data.tema)

    perguntas = await gerar_perguntas_iniciais(
        tema=input_data.tema,
        contexto_do_tema=contexto_do_tema,
        aspectos=[
            "experiencia",
            "opiniao",
            "sentimento",
            "aprendizado",
        ],
    )

    while not state.gateway.aprovado and state.rodadas < state.max_rodadas:
        respostas = await coletar_respostas_do_usuario(perguntas)

        for resposta in respostas:
            avaliacao = await avaliar_resposta(
                tema=state.tema,
                pergunta=resposta.pergunta,
                resposta=resposta.texto,
                scores_atuais=state.scores,
                memory_pack=state.memory_pack,
            )

            state.scores = atualizar_scores(state.scores, avaliacao)

            state.memory_pack = await atualizar_memory_pack(
                memory_pack_atual=state.memory_pack,
                resposta=resposta,
                avaliacao=avaliacao,
            )

            state.perguntas_e_respostas.append(
                InteracaoEntrevista(
                    pergunta=resposta.pergunta,
                    resposta=resposta.texto,
                    avaliacao=avaliacao,
                )
            )

        state.gateway = avaliar_gateway(state.scores)

        if not state.gateway.aprovado:
            perguntas = await gerar_perguntas_recursivas(
                tema=state.tema,
                scores=state.scores,
                memory_pack=state.memory_pack,
                ultimas_interacoes=obter_ultimas_interacoes(state, 3),
                lacunas=identificar_lacunas(state.scores),
            )

        state.rodadas += 1

    return montar_briefing_autoral(state)
```

---

## 24. Estado da entrevista

```python
@dataclass
class EstadoEntrevista:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    scores: ScoresAutorais
    gateway: ResultadoGateway
    memory_pack: MemoryPack
    perguntas_e_respostas: list[InteracaoEntrevista]
    rodadas: int
    max_rodadas: int
    personalidade: str | None = None
```

Exemplo de criação do estado inicial:

```python
def criar_scores_iniciais() -> ScoresAutorais:
    bruto = PontuacaoAspectos(
        experiencia=0,
        opiniao=0,
        sentimento=0,
        aprendizado=0,
        personalidade=0,
    )

    normalizado = PontuacaoAspectos(
        experiencia=0,
        opiniao=0,
        sentimento=0,
        aprendizado=0,
        personalidade=0,
    )

    return ScoresAutorais(
        bruto=bruto,
        normalizado=normalizado,
        total_bruto=0,
        total_normalizado=0,
    )


def criar_estado_inicial(
    input_data: InicioEntrevista,
    max_rodadas: int = 6,
) -> EstadoEntrevista:
    return EstadoEntrevista(
        tema=input_data.tema,
        plataforma=input_data.plataforma,
        objetivo_do_post=input_data.objetivo_do_post,
        tipo_de_post=input_data.tipo_de_post,
        personalidade=input_data.personalidade,
        scores=criar_scores_iniciais(),
        gateway=ResultadoGateway(
            aprovado=False,
            tipo_gateway="reprovado",
            restricoes_de_geracao=[],
        ),
        memory_pack=MemoryPack(),
        perguntas_e_respostas=[],
        rodadas=0,
        max_rodadas=max_rodadas,
    )
```

---

## 25. Meta-prompt para Experiência

Objetivo: extrair vivência factual, caso real, contexto prático, situação concreta e consequência observável.

```txt
Você é uma IA entrevistadora especializada em extrair experiências reais de um usuário para criação de conteúdo autoral.

Tema da entrevista:
{tema}

Resumo do tema:
{contextoDoTema}

Scores atuais:
{scoresAtuais}

Memory pack atual:
{memoryPack}

Últimas perguntas e respostas:
{ultimasInteracoes}

Aspecto principal desta pergunta:
experiencia

Sua tarefa é gerar uma pergunta aberta para extrair uma vivência factual do usuário sobre o tema.

A pergunta deve tentar descobrir:
- se o usuário já viveu algo relacionado ao tema;
- em qual contexto isso aconteceu;
- qual era o problema, cenário ou situação;
- quem estava envolvido, se for relevante;
- qual decisão foi tomada;
- qual foi a consequência prática;
- o que mudou antes e depois.

Regras:
- Não faça pergunta genérica.
- Não pergunte algo que o usuário já respondeu.
- Não use tom de formulário.
- Não force o usuário a dizer que viveu algo se ele ainda não confirmou isso.
- Se o usuário ainda não trouxe nenhum caso real, peça um exemplo específico.
- Se o usuário já trouxe um caso, aprofunde contexto, consequência ou antes/depois.
- Prefira perguntas que comecem com “Me conta um caso...”, “Você lembra de uma situação...”, “Em algum projeto...”, “Na prática...”.
- A pergunta deve incentivar o usuário a responder com detalhes concretos.
- Capture também traços de personalidade se eles aparecerem naturalmente.

Evite perguntas como:
- “Você já teve experiência com isso?”
- “Fale sobre sua experiência.”
- “Você conhece esse tema?”

Prefira perguntas como:
- “Me conta uma situação real em que esse tema apareceu no seu trabalho ou na sua vida. O que estava acontecendo, qual era o problema e como você lidou com isso?”

Retorne apenas JSON:

{
  "aspecto": "experiencia",
  "pergunta": "...",
  "intencao": "...",
  "porQueEssaPerguntaAjuda": "...",
  "tipoDeRespostaEsperada": "caso real, contexto, problema, decisão e consequência"
}
```

---

## 26. Meta-prompt para Opinião

Objetivo: extrair visão própria, julgamento, discordância, crítica, preferência, nuance e posicionamento.

```txt
Você é uma IA entrevistadora especializada em extrair opiniões próprias de um usuário para criação de conteúdo autoral.

Tema da entrevista:
{tema}

Resumo do tema:
{contextoDoTema}

Scores atuais:
{scoresAtuais}

Memory pack atual:
{memoryPack}

Últimas perguntas e respostas:
{ultimasInteracoes}

Aspecto principal desta pergunta:
opiniao

Sua tarefa é gerar uma pergunta aberta para extrair a opinião real do usuário sobre o tema.

A pergunta deve tentar descobrir:
- o que o usuário pensa sobre o tema;
- com o que ele concorda;
- com o que ele discorda;
- o que ele acha exagerado, subestimado ou mal interpretado;
- qual nuance ele enxerga;
- qual posição ele defenderia publicamente;
- quais limites, riscos ou trade-offs ele percebe.

Regras:
- Não peça uma definição técnica.
- Não faça pergunta com resposta óbvia.
- Não conduza o usuário para uma opinião específica.
- Não pergunte apenas “qual sua opinião?”.
- Se o usuário já deu uma opinião genérica, peça uma posição mais clara.
- Se o usuário já trouxe uma opinião forte, peça o contraponto, limite ou nuance.
- Se o usuário não tem experiência prática, permita que ele fale como leitura pessoal, hipótese, crítica ou provocação.
- Capture frases fortes e naturais que possam ser usadas no post.
- A pergunta deve ajudar a revelar o jeito próprio do usuário pensar.

Evite perguntas como:
- “Qual sua opinião sobre o tema?”
- “Você acha isso importante?”
- “Você concorda com isso?”

Prefira perguntas como:
- “O que você acha que as pessoas costumam entender errado sobre esse tema?”
- “Qual parte desse assunto você defenderia mesmo sabendo que outras pessoas podem discordar?”
- “Onde você acha que esse conceito ajuda de verdade e onde ele começa a virar exagero?”

Retorne apenas JSON:

{
  "aspecto": "opiniao",
  "pergunta": "...",
  "intencao": "...",
  "porQueEssaPerguntaAjuda": "...",
  "tipoDeRespostaEsperada": "posição própria, crítica, nuance, trade-off ou provocação"
}
```

---

## 27. Meta-prompt para Sentimento

Objetivo: extrair reação emocional, incômodo, alívio, frustração, orgulho, medo, entusiasmo ou percepção subjetiva.

```txt
Você é uma IA entrevistadora especializada em extrair sentimentos e percepções subjetivas de um usuário para criação de conteúdo autoral.

Tema da entrevista:
{tema}

Resumo do tema:
{contextoDoTema}

Scores atuais:
{scoresAtuais}

Memory pack atual:
{memoryPack}

Últimas perguntas e respostas:
{ultimasInteracoes}

Aspecto principal desta pergunta:
sentimento

Sua tarefa é gerar uma pergunta aberta para extrair o que o usuário sente em relação ao tema.

A pergunta deve tentar descobrir:
- qual emoção o tema desperta;
- o que incomoda o usuário;
- o que gera alívio, orgulho, frustração, ansiedade, entusiasmo ou cansaço;
- como o usuário reage quando encontra esse tema na prática;
- qual tensão emocional existe por trás da opinião;
- o que o tema representa subjetivamente para ele.

Regras:
- Não force sentimentalismo.
- Não exagere o drama.
- Não pergunte de forma artificial.
- Não use linguagem terapêutica demais.
- Se o usuário for mais técnico, formule a pergunta de maneira prática.
- Se o usuário já mencionou um sentimento, aprofunde a causa.
- Se ele ainda não expressou sentimento, pergunte sobre reação, incômodo ou alívio.
- A pergunta deve soar natural e adulta.
- Capture expressões espontâneas do usuário, porque elas ajudam na métrica de personalidade.

Evite perguntas como:
- “Como você se sente sobre isso?”
- “Quais emoções esse tema desperta em você?”
- “Esse tema te deixa triste ou feliz?”

Prefira perguntas como:
- “Quando você vê esse problema acontecendo na prática, o que mais te incomoda?”
- “Existe alguma parte desse tema que te dá alívio, frustração ou impaciência?”
- “O que passa pela sua cabeça quando você precisa lidar com isso de novo?”

Retorne apenas JSON:

{
  "aspecto": "sentimento",
  "pergunta": "...",
  "intencao": "...",
  "porQueEssaPerguntaAjuda": "...",
  "tipoDeRespostaEsperada": "incômodo, alívio, frustração, orgulho, tensão ou reação subjetiva"
}
```

---

## 28. Meta-prompt para Aprendizado

Objetivo: extrair transformação, maturidade, lição prática, mudança de visão e critério adquirido.

```txt
Você é uma IA entrevistadora especializada em extrair aprendizados pessoais de um usuário para criação de conteúdo autoral.

Tema da entrevista:
{tema}

Resumo do tema:
{contextoDoTema}

Scores atuais:
{scoresAtuais}

Memory pack atual:
{memoryPack}

Últimas perguntas e respostas:
{ultimasInteracoes}

Aspecto principal desta pergunta:
aprendizado

Sua tarefa é gerar uma pergunta aberta para extrair o que o usuário aprendeu ou passou a enxergar de forma diferente sobre o tema.

A pergunta deve tentar descobrir:
- que mudança de visão aconteceu;
- o que o usuário faria diferente hoje;
- qual erro, atrito ou situação ensinou algo;
- qual critério prático ele passou a usar;
- que conselho ele daria para alguém;
- qual conclusão ele tirou depois de pensar ou viver aquilo;
- qual maturidade foi adquirida.

Regras:
- Não force uma “lição de moral”.
- Não invente transformação se o usuário não demonstrou isso.
- Se o usuário trouxe uma experiência, pergunte o que ela mudou na prática.
- Se o usuário trouxe opinião, pergunte como ele chegou a essa opinião.
- Se o usuário trouxe sentimento, pergunte o que esse incômodo ensinou.
- Se o usuário ainda não tem experiência, permita aprendizado por observação, estudo, erro dos outros ou reflexão.
- A pergunta deve gerar material útil para fechamento de post.
- Capture frases que possam virar conclusão, conselho ou tese central.

Evite perguntas como:
- “O que você aprendeu?”
- “Qual foi seu aprendizado?”
- “Que lição você tirou disso?”

Prefira perguntas como:
- “Depois de lidar com esse tema, o que você passou a fazer diferente?”
- “Qual critério você usa hoje que talvez não usasse antes?”
- “Se você fosse explicar esse aprendizado para alguém menos experiente, o que você diria sem romantizar o assunto?”

Retorne apenas JSON:

{
  "aspecto": "aprendizado",
  "pergunta": "...",
  "intencao": "...",
  "porQueEssaPerguntaAjuda": "...",
  "tipoDeRespostaEsperada": "mudança de visão, critério prático, conselho, conclusão ou maturidade adquirida"
}
```

---

## 29. Prompt para perguntas recursivas

```txt
Você é uma IA entrevistadora.

Tema:
{tema}

Scores atuais:
{scoresAtuais}

Aspectos que ainda precisam melhorar:
{aspectosFracos}

Resumo autoral já extraído:
{memoryPack}

Últimas perguntas e respostas:
{ultimasInteracoes}

Sua tarefa:
Gerar novas perguntas apenas para os aspectos que ainda precisam melhorar.

Regras:
- Não repita perguntas já feitas.
- Não peça algo que o usuário já respondeu.
- Faça perguntas mais específicas conforme o contexto acumulado.
- Prefira perguntas que puxem exemplos, cenas reais, decisões, conflitos, emoções e aprendizados.
- Se uma resposta anterior foi vaga, peça um caso concreto.
- Se uma resposta anterior teve bom exemplo, aprofunde impacto, consequência ou sentimento.
- Se o usuário não tiver experiência prática, não force relato pessoal.
- Se o gateway desequilibrado estiver próximo, aprofunde a categoria dominante.
- Se personalidade estiver baixa, peça que o usuário explique com suas palavras, metáforas ou jeito natural de falar.

Retorne apenas JSON:

{
  "perguntas": [
    {
      "aspecto": "...",
      "pergunta": "...",
      "motivo": "..."
    }
  ]
}
```

---

## 30. Briefing autoral final

Quando a entrevista é aprovada, a engine gera um briefing autoral.

O briefing autoral não será salvo automaticamente em arquivo local. Ele será usado no fluxo ativo da engine e poderá compor a sessão persistida da TUI, mas não será exportado como artefato separado por padrão.

```python
TipoGatewayAprovado = Literal["equilibrado", "desequilibrado"]


@dataclass(frozen=True)
class GatewayAprovado:
    aprovado: bool
    tipo_gateway: TipoGatewayAprovado
    tipo_autoria: TipoAutoria
    restricoes_de_geracao: list[str]


@dataclass(frozen=True)
class RespostaAutoral:
    pergunta: str
    resposta: str


class RespostasAutorais(TypedDict):
    experiencia: list[RespostaAutoral]
    opiniao: list[RespostaAutoral]
    sentimento: list[RespostaAutoral]
    aprendizado: list[RespostaAutoral]
    personalidade: list[RespostaAutoral]


@dataclass(frozen=True)
class BriefingAutoral:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    gateway: GatewayAprovado
    scores: ScoresAutorais
    respostas_autorais: RespostasAutorais
    memory_pack: MemoryPack
    personalidade: str | None = None
```

---

## 31. Prompt para geração do post

Este prompt é mantido como referência conceitual. Na versão atualizada, o prompt final deve ser construído pelo `PromptBuilder`, conforme as seções 38 a 44, para evitar envio simultâneo das regras de `feed`, `article` e `slide`.

```txt
Você é {personalidade || "um escritor de posts autorais"}.

Crie um post para {plataforma} sobre o tema "{tema}".

Objetivo do post:
{objetivoDoPost}

Tipo de post:
{tipoDePost}

Tipo de autoria:
{tipoAutoria}

Tipo de gateway aprovado:
{tipoGateway}

Use o material autoral abaixo como fonte principal.

Experiências:
{respostasAutorais.experiencia}

Opiniões:
{respostasAutorais.opiniao}

Sentimentos:
{respostasAutorais.sentimento}

Aprendizados:
{respostasAutorais.aprendizado}

Traços de personalidade:
{respostasAutorais.personalidade}

Resumo autoral:
{memoryPack}

Restrições obrigatórias:
{restricoesDeGeracao}

Regras:
- Não invente experiências pessoais.
- Não atribua vivências que o usuário não contou.
- Se a experiência for baixa, escreva como opinião, reflexão ou provocação.
- Se a experiência for alta, pode usar narrativa pessoal.
- Preserve a voz e os traços do usuário.
- Evite linguagem genérica de IA.
- Evite frases vagas, clichês e conclusões artificiais.
- O texto deve parecer escrito por uma pessoa real, não por uma IA tentando parecer humana.
```

---

## 32. Score do post gerado

Depois de gerar e segmentar o conteúdo, a engine pode avaliar se o texto respeitou o material autoral.

A avaliação do conteúdo gerado não é obrigatória antes da segmentação. Ela ocorre depois, como etapa posterior de análise, revisão ou melhoria.

```python
@dataclass(frozen=True)
class ScoreDoPost:
    experiencia: int
    opiniao: int
    sentimento: int
    aprendizado: int
    personalidade: int
    fidelidade: int
    naturalidade: int

    @property
    def total(self) -> int:
        return (
            self.experiencia
            + self.opiniao
            + self.sentimento
            + self.aprendizado
            + self.personalidade
            + self.fidelidade
            + self.naturalidade
        )
```

Critérios:

* Experiência: o texto usa corretamente vivências reais?
* Opinião: o texto expressa visão própria?
* Sentimento: o texto transmite percepção humana?
* Aprendizado: o texto mostra transformação, conclusão ou maturidade?
* Personalidade: o texto preserva jeito próprio?
* Fidelidade: o texto evita inventar fatos?
* Naturalidade: o texto parece escrito por uma pessoa?

Prompt:

```txt
Avalie o conteúdo abaixo em relação ao grau de autoria humana.

Tema:
{tema}

Conteúdo:
{conteudoGerado}

Material autoral original fornecido pelo usuário:
{briefingAutoral}

Avalie os seguintes critérios de 0 a 100:
- experiencia: o texto usa fatos e vivências concretas do usuário?
- opiniao: o texto expressa uma visão própria?
- sentimento: o texto transmite percepção emocional ou subjetiva?
- aprendizado: o texto mostra transformação, conclusão ou maturidade?
- personalidade: o texto preserva traços do usuário?
- fidelidade: o texto evita inventar fatos não informados?
- naturalidade: o texto parece escrito por uma pessoa real?

Retorne apenas JSON:

{
  "score": {
    "experiencia": 0,
    "opiniao": 0,
    "sentimento": 0,
    "aprendizado": 0,
    "personalidade": 0,
    "fidelidade": 0,
    "naturalidade": 0,
    "total": 0
  },
  "pontosFortes": [],
  "pontosFracos": [],
  "sugestoesDeMelhoria": []
}
```

---

## 33. Segmentação do post

Depois de gerar o post, a engine divide o conteúdo em segmentos editáveis.

Internamente:

```python
@dataclass(frozen=True)
class SegmentoPost:
    id: str
    ordem: int
    texto: str
    papel_interno: str
```

Para o usuário, não é necessário mostrar o `papel_interno`.

Prompt:

```txt
Divida o conteúdo abaixo em segmentos editáveis.

Não adicione títulos visíveis.
Não nomeie as seções no texto final.
Cada segmento deve ter sentido próprio e poder ser reescrito isoladamente.

Conteúdo:
{conteudoDoPost}

Retorne apenas JSON:

{
  "segmentos": [
    {
      "id": "seg_1",
      "ordem": 1,
      "papelInterno": "abertura",
      "texto": "..."
    }
  ]
}
```

---

## 34. Ajuste por segmento

Quando o usuário pedir alteração em uma parte específica, a engine reescreve somente aquele segmento.

Prompt:

```txt
A respeito do conteúdo completo abaixo:
{conteudoCompleto}

Reescreva apenas este segmento:
{segmentoAtual}

Pedido do usuário:
{ajusteDoUsuario}

Personalidade:
{personalidade}

Restrições:
{restricoesDeGeracao}

Regras:
- Reescreva apenas o segmento informado.
- Mantenha coerência com o post completo.
- Não invente novas experiências.
- Não contradiga o restante do conteúdo.
- Preserve o tipo de autoria aprovado.
- Preserve o objetivo do post.
- Preserve a plataforma.
- Preserve a voz do usuário quando houver traços suficientes para isso.

Retorne apenas JSON:

{
  "segmentoReescrito": "..."
}
```

---

## 35. Fluxo completo da engine

```txt
1. Usuário informa tema, plataforma, objetivo e tipo de post.

2. Engine pesquisa ou resume o tema.

3. LLM gera perguntas iniciais sobre:
   - experiência
   - opinião
   - sentimento
   - aprendizado

4. Usuário responde.

5. LLM avalia cada resposta e gera deltas de score para:
   - experiência
   - opinião
   - sentimento
   - aprendizado
   - personalidade

6. Engine soma os deltas no score bruto.

7. Engine calcula o score normalizado.

8. Engine atualiza o memory pack.

9. Engine verifica gateways:
   - 500 pontos equilibrados
   - ou 600 pontos brutos desequilibrados

10. Se não aprovado:
    - identifica lacunas
    - gera novas perguntas específicas
    - repete o ciclo

11. Se aprovado:
    - classifica o tipo de autoria
    - gera restrições de escrita
    - monta o briefing autoral em memória

12. PromptBuilder gera o prompt final.

13. LLM gera o conteúdo.

14. Engine segmenta o conteúdo.

15. Usuário pode ajustar segmentos individuais.

16. Engine reescreve apenas os segmentos alterados.

17. Engine avalia o conteúdo gerado após a segmentação.

18. Usuário exporta o conteúdo final em Markdown ou arquivo local.
```

---

## 36. Regras de honestidade narrativa

A engine deve preservar a diferença entre:

* Vivência
* Opinião
* Sentimento
* Aprendizado
* Personalidade

Regras obrigatórias:

1. Se o usuário não relatou uma experiência, o post não deve inventar experiência.
2. Se a experiência é baixa, o texto deve assumir tom opinativo, reflexivo ou provocativo.
3. Se a opinião é baixa, o texto não deve fingir posicionamento forte.
4. Se o sentimento é baixo, o texto não deve forçar emoção.
5. Se o aprendizado é baixo, o texto não deve criar transformação artificial.
6. Se a personalidade é baixa, o texto deve evitar simular estilo muito marcado.
7. O sistema pode aceitar desequilíbrio autoral, mas não pode converter ausência de experiência em autoridade prática falsa.

Resumo:

```txt
Pouca experiência + muita opinião = post opinativo.
Pouca opinião + muita experiência = relato prático.
Muito sentimento + pouca experiência = reflexão emocional.
Muito aprendizado + pouca experiência = ensaio reflexivo.
Tudo alto = post autoral completo.
```

---

## 37. Critérios de sucesso do produto

A engine será considerada bem-sucedida se:

* Conseguir gerar perguntas menos genéricas que um formulário comum.
* Reduzir a quantidade de conteúdo artificial ou impessoal.
* Conseguir adaptar perguntas com base nas respostas anteriores.
* Conseguir diferenciar experiência real de opinião.
* Conseguir aprovar usuários com autoria desequilibrada sem inventar vivência.
* Gerar briefings úteis para criação de posts.
* Gerar posts com maior naturalidade, fidelidade e originalidade.
* Permitir ajustes por segmento sem reescrever o conteúdo inteiro.
* Preservar o tom e a intenção do usuário ao longo do processo.
* Permitir operação do fluxo pela TUI sem scripts manuais.
* Permitir exportação final em Markdown e arquivo.

---

# ADENDO — PromptBuilder, renderização condicional e TUI com Textual

Este adendo complementa o PRD com decisões sobre arquitetura de prompt, separação de responsabilidades, execução LLM, persistência local e interface TUI.

---

## 38. Decisão de produto: renderização condicional do prompt gerador

A renderização das regras específicas por tipo de conteúdo deve ser feita no código antes da chamada ao LLM.

O modelo não deve receber simultaneamente blocos como:

```txt
Se tipoDePost for "feed":
...

Se tipoDePost for "article":
...

Se tipoDePost for "slide":
...
```

Esse formato funciona, mas deixa uma decisão determinística sob responsabilidade do modelo. Como `tipo_de_post` já é conhecido pelo sistema, o roteamento deve ser feito pela aplicação.

O prompt final enviado ao LLM deve conter apenas a persona ativa e as regras do formato ativo.

Exemplo para `tipo_de_post = "feed"`:

```txt
Tipo de post:
feed

Persona ativa:
DevInterlocutorFeed

Regras específicas do formato:
[apenas regras de feed]
```

---

## 38.1 Justificativa

A renderização condicional no código:

1. reduz tokens;
2. evita conflito entre instruções;
3. reduz ambiguidade;
4. torna o comportamento mais previsível;
5. facilita testes unitários;
6. mantém o LLM focado na geração;
7. permite versionar personas e regras separadamente;
8. evita que roteamento determinístico seja delegado ao modelo;
9. reduz risco de mistura entre formatos, por exemplo artigo com ritmo de feed ou slide com densidade de artigo.

---

## 38.2 Regra obrigatória

O `PromptBuilder` deve garantir que apenas um bloco de regras de formato entre no prompt final.

Critério:

```txt
Dado tipo_de_post = "feed"
Então o prompt contém DevInterlocutorFeed
E não contém DevInterlocutorArticle
E não contém DevInterlocutorSlide
```

A mesma regra vale para `article` e `slide`.

---

## 39. Nova arquitetura operacional

A engine passa a ter uma separação explícita entre produto, montagem de prompt, execução e interface.

```txt
┌──────────────────────────────┐
│ Textual TUI                  │
│ Interface operacional        │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ PromptBuilder                │
│ Renderização condicional     │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ AgentWrapper                 │
│ Execução codex/opencode      │
└───────────────┬──────────────┘
                │
                ▼
┌──────────────────────────────┐
│ LLM CLI                      │
│ Codex ou OpenCode            │
└──────────────────────────────┘
```

---

## 39.1 Responsabilidades da Textual TUI

A TUI é responsável por:

* coletar entrada do usuário;
* permitir edição do briefing autoral no fluxo ativo;
* selecionar tipo de conteúdo;
* selecionar executor LLM;
* selecionar modelo;
* selecionar sandbox;
* gerar preview do prompt;
* executar o LLM;
* bloquear gerações concorrentes;
* mostrar `stdout`, `stderr`, `returncode` e eventos;
* tentar parsear JSON final sem bloquear exibição;
* persistir sessão automaticamente;
* permitir exportação final para Markdown e arquivo;
* permitir depuração visual do fluxo.

---

## 39.2 Responsabilidades do PromptBuilder

O `PromptBuilder` é responsável por:

* receber dados estruturados;
* selecionar persona conforme `tipo_de_post`;
* selecionar regras conforme `tipo_de_post`;
* serializar briefing, scores e restrições;
* montar prompt final;
* garantir que o prompt enviado ao LLM contenha apenas o necessário;
* impedir que blocos de outros formatos sejam enviados ao modelo.

---

## 39.3 Responsabilidades do AgentWrapper

O `AgentWrapper` é responsável por:

* executar `codex` ou `opencode`;
* montar comandos CLI;
* passar diretório de trabalho;
* controlar sandbox;
* passar modelo;
* configurar saída JSON quando aplicável;
* capturar `stdout`, `stderr` e `returncode`;
* parsear eventos JSONL quando `json_output = True`;
* retornar um `AgentResult`.

O `AgentWrapper` não deve conhecer regra de produto, persona, score autoral, tipo de autoria ou tipo de post. Ele é infraestrutura.

---

## 40. Estrutura de pastas sugerida

```txt
src/
  content_engine/
    agent_wrapper.py
    prompt_builder.py
    schemas.py
    scoring.py
    interview.py
    generator.py
    evaluator.py
    segmentation.py
    persistence.py
    exporter.py

  tui/
    app.py
    screens/
      interview_screen.py
      generator_screen.py
      review_screen.py

prompts/
  interview/
    evaluate-answer.md
    update-memory-pack.md
    questions-experience.md
    questions-opinion.md
    questions-feeling.md
    questions-learning.md
    recursive-questions.md

  generator/
    base.md
    rules-feed.md
    rules-article.md
    rules-slide.md
    personas/
      dev-interlocutor-feed.md
      dev-interlocutor-article.md
      dev-interlocutor-slide.md

.data/
  sessions/
    current-session.json

exports/

tests/
  test_prompt_builder.py
  test_gateway.py
  test_generation_contract.py
  test_agent_wrapper.py
  test_tui_prompt_preview.py
  test_session_persistence.py
  test_exporter.py
```

---

## 41. Prompt gerador atualizado

O prompt gerador é usado depois da entrevista aprovada e depois da criação do briefing autoral.

Ele deve receber:

* entrada do conteúdo;
* persona ativa;
* regras do formato ativo;
* briefing autoral;
* scores;
* restrições;
* contrato de saída.

Ele não deve receber todos os blocos condicionais de todos os formatos.

---

## 41.1 Template base

```txt
Você é o Gerador de Conteúdo Autoral da engine.

Sua função é transformar um briefing autoral em um conteúdo pronto para publicação, preservando a voz, as ideias, os limites narrativos e os traços humanos do usuário.

Você NÃO está criando um texto genérico sobre o tema.
Você está criando um texto fiel ao material autoral coletado na entrevista.

## Entrada

Tema:
{{tema}}

Plataforma:
{{plataforma}}

Objetivo do post:
{{objetivoDoPost}}

Tipo de post:
{{tipoDePost}}

Personalidade desejada:
{{personalidade}}

Tipo de gateway:
{{tipoGateway}}

Tipo de autoria:
{{tipoAutoria}}

Persona ativa:
{{personaSelecionada}}

## Regras específicas do formato

{{regrasDoTipoDePost}}

## Scores autorais

{{scores}}

## Restrições obrigatórias de geração

{{restricoesDeGeracao}}

## Briefing autoral

{{briefingAutoral}}

## Regras globais

1. Não invente experiências pessoais.
2. Não atribua ao usuário vivências que ele não contou.
3. Não invente empresas, cargos, números, métricas, incidentes ou casos reais.
4. Se a experiência autoral for baixa, escreva como opinião, reflexão ou provocação.
5. Se a experiência autoral for alta, pode usar narrativa pessoal em primeira pessoa.
6. Se a opinião for baixa, não force posicionamento forte.
7. Se o sentimento for baixo, não force emoção.
8. Se o aprendizado for baixo, não crie transformação artificial.
9. Se a personalidade for baixa, não exagere no estilo.
10. Preserve a diferença entre vivência, opinião, sentimento, aprendizado e personalidade.
11. Evite linguagem genérica de IA.
12. Evite clichês, frases motivacionais vagas e conclusões artificiais.
13. Não escreva como guru, coach ou vendedor de curso.
14. Não use CTA agressivo.
15. Não use emojis, salvo se explicitamente permitido.

## Modelo interno de decisão narrativa

Antes de escrever, identifique internamente:

- Qual é a tese principal?
- Qual premissa comum será tensionada?
- Qual é o inimigo comum do tema?
- O texto será mais baseado em experiência, opinião, sentimento, aprendizado ou personalidade?
- Existe material suficiente para primeira pessoa?
- Quais restrições impedem exageros ou invenções?
- Qual tom combina com a persona selecionada?
- Qual formato a plataforma exige?

Não mostre esse raciocínio. Use apenas para orientar a geração.

## Saída obrigatória

Retorne apenas JSON válido, sem markdown, no formato:

{
  "conteudo": "...",
  "metadados": {
    "tipoDePost": "{{tipoDePost}}",
    "plataforma": "{{plataforma}}",
    "personaUsada": "{{personaSelecionada}}",
    "tipoAutoria": "{{tipoAutoria}}",
    "tipoGateway": "{{tipoGateway}}",
    "usoDePrimeiraPessoa": true,
    "baseNarrativaPrincipal": "experiencia | opiniao | sentimento | aprendizado | personalidade | misto",
    "restricoesAplicadas": []
  },
  "alertas": []
}
```

---

## 42. Regras condicionais do formato

As regras abaixo são blocos separados e devem ser renderizadas de forma condicional pelo `PromptBuilder`.

---

## 42.1 Feed

```txt
Use a persona DevInterlocutorFeed.

Regras do conteúdo:
- Escreva um post rápido, direto, crítico, opinativo e humano.
- Abra com atrito produtivo.
- Não transforme em artigo.
- Use parágrafos curtos.
- Use profundidade baixa ou média.
- Pode usar humor seco, ironia moderada e uma imagem concreta.
- Máximo recomendado: 1600 caracteres para LinkedIn.
```

---

## 42.2 Article

```txt
Use a persona DevInterlocutorArticle.

Regras do conteúdo:
- Escreva um artigo técnico, analítico e estruturado.
- Comece com uma tese clara.
- Use título e subtítulos.
- Defina conceitos importantes.
- Explique trade-offs, riscos, limites e contraargumentos.
- Não transforme o artigo em feed alongado.
- Não invente estudos, autores ou referências.
```

---

## 42.3 Slide

```txt
Use a persona DevInterlocutorSlide.

Regras do conteúdo:
- Crie uma sequência narrativa em slides.
- Uma ideia principal por slide.
- Use títulos fortes.
- Use bullets objetivos.
- Não transforme artigo em slides quebrados.
- Não transforme feed em frases soltas.
- Estruture progressão: tensão, problema, premissa errada, correção, exemplo, trade-off, decisão e fechamento.
```

---

## 43. Modelo de dados da geração

### 43.1 Entrada do PromptBuilder

```python
from dataclasses import dataclass
from typing import Any, Literal


TipoDePost = Literal["post", "article", "short_carousel", "long_slide"]


@dataclass(frozen=True)
class GenerationPromptInput:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    briefing_autoral: dict[str, Any]
    scores: dict[str, Any] | None = None
    restricoes_de_geracao: list[str] | None = None
    personalidade: str | None = None
    tipo_gateway: str | None = None
    tipo_autoria: str | None = None
```

---

### 43.2 Resultado do AgentWrapper

```python
from dataclasses import dataclass
from typing import Literal


ToolName = Literal["codex", "opencode"]


@dataclass
class AgentResult:
    tool: ToolName
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    events: list[dict] | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0
```

---

## 44. PromptBuilder

O `PromptBuilder` deve selecionar persona e regras antes da chamada ao LLM.

### 44.1 Exemplo de implementação

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Literal


TipoDePost = Literal["post", "article", "short_carousel", "long_slide"]


@dataclass(frozen=True)
class GenerationPromptInput:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    briefing_autoral: dict[str, Any]
    scores: dict[str, Any] | None = None
    restricoes_de_geracao: list[str] | None = None
    personalidade: str | None = None
    tipo_gateway: str | None = None
    tipo_autoria: str | None = None


PERSONAS_POR_TIPO: dict[TipoDePost, str] = {
    "feed": "DevInterlocutorFeed",
    "article": "DevInterlocutorArticle",
    "slide": "DevInterlocutorSlide",
}


REGRAS_POR_TIPO: dict[TipoDePost, str] = {
    "feed": RULES_FEED,
    "article": RULES_ARTICLE,
    "slide": RULES_SLIDE,
}


def build_generation_prompt(data: GenerationPromptInput) -> str:
    try:
        persona = PERSONAS_POR_TIPO[data.tipo_de_post]
        regras_do_tipo = REGRAS_POR_TIPO[data.tipo_de_post]
    except KeyError as exc:
        raise ValueError(
            f"tipo_de_post inválido: {data.tipo_de_post}"
        ) from exc

    briefing_json = json.dumps(
        data.briefing_autoral,
        ensure_ascii=False,
        indent=2,
    )

    scores_json = json.dumps(
        data.scores or {},
        ensure_ascii=False,
        indent=2,
    )

    restricoes_json = json.dumps(
        data.restricoes_de_geracao or [],
        ensure_ascii=False,
        indent=2,
    )

    return render_template(
        "generator/base.md",
        {
            "tema": data.tema,
            "plataforma": data.plataforma,
            "objetivoDoPost": data.objetivo_do_post,
            "tipoDePost": data.tipo_de_post,
            "personalidade": data.personalidade or "não informada",
            "tipoGateway": data.tipo_gateway or "não informado",
            "tipoAutoria": data.tipo_autoria or "não informado",
            "personaSelecionada": persona,
            "regrasDoTipoDePost": regras_do_tipo,
            "scores": scores_json,
            "restricoesDeGeracao": restricoes_json,
            "briefingAutoral": briefing_json,
        },
    )
```

---

### 44.2 Critérios de aceite do PromptBuilder

* Dado `tipo_de_post = "feed"`, o prompt final deve conter `DevInterlocutorFeed`.
* Dado `tipo_de_post = "feed"`, o prompt final não deve conter `DevInterlocutorArticle` nem `DevInterlocutorSlide`.
* Dado `tipo_de_post = "article"`, o prompt final deve conter `DevInterlocutorArticle`.
* Dado `tipo_de_post = "article"`, o prompt final não deve conter `DevInterlocutorFeed` nem `DevInterlocutorSlide`.
* Dado `tipo_de_post = "slide"`, o prompt final deve conter `DevInterlocutorSlide`.
* Dado `tipo_de_post = "slide"`, o prompt final não deve conter `DevInterlocutorFeed` nem `DevInterlocutorArticle`.
* O prompt final deve conter o briefing autoral serializado.
* O prompt final deve conter as restrições de geração.
* O prompt final deve solicitar JSON válido.
* O builder deve falhar caso `tipo_de_post` seja inválido.

---

## 45. Código-base atual do AgentWrapper

```python
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional


ToolName = Literal["codex", "opencode"]


@dataclass
class AgentResult:
    tool: ToolName
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    events: list[dict] | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class AgentWrapper:
    def __init__(
        self,
        workspace: str | Path,
        timeout: int = 900,
        env: Optional[dict[str, str]] = None,
    ) -> None:
        self.workspace = Path(workspace).resolve()
        self.timeout = timeout
        self.env = {**os.environ, **(env or {})}

    def run_codex(
        self,
        prompt: str,
        *,
        model: str | None = None,
        sandbox: Literal[
            "read-only",
            "workspace-write",
            "danger-full-access",
        ] = "read-only",
        json_output: bool = False,
        extra_context: str | None = None,
        ephemeral: bool = True,
        ignore_user_config: bool = False,
    ) -> AgentResult:
        cmd = [
            "codex",
            "exec",
            "--cd",
            str(self.workspace),
            "--sandbox",
            sandbox,
            "--color",
            "never",
        ]

        if ephemeral:
            cmd.append("--ephemeral")

        if ignore_user_config:
            cmd.append("--ignore-user-config")

        if model:
            cmd.extend(["--model", model])

        if json_output:
            cmd.append("--json")

        cmd.append(prompt)

        return self._run(
            "codex",
            cmd,
            stdin=extra_context,
            parse_jsonl=json_output,
        )

    def run_opencode(
        self,
        prompt: str,
        *,
        model: str | None = None,
        agent: str | None = None,
        files: list[str | Path] | None = None,
        json_output: bool = False,
        attach_url: str | None = None,
        dangerously_skip_permissions: bool = False,
    ) -> AgentResult:
        cmd = [
            "opencode",
            "run",
            "--dir",
            str(self.workspace),
        ]

        if model:
            cmd.extend(["--model", model])

        if agent:
            cmd.extend(["--agent", agent])

        if json_output:
            cmd.extend(["--format", "json"])

        if attach_url:
            cmd.extend(["--attach", attach_url])

        if dangerously_skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        for file in files or []:
            cmd.extend(["--file", str(Path(file))])

        cmd.append(prompt)

        return self._run(
            "opencode",
            cmd,
            parse_jsonl=json_output,
        )

    def run(
        self,
        tool: ToolName,
        prompt: str,
        **kwargs,
    ) -> AgentResult:
        if tool == "codex":
            return self.run_codex(prompt, **kwargs)

        if tool == "opencode":
            return self.run_opencode(prompt, **kwargs)

        raise ValueError(f"Unsupported tool: {tool}")

    def _run(
        self,
        tool: ToolName,
        cmd: list[str],
        *,
        stdin: str | None = None,
        parse_jsonl: bool = False,
    ) -> AgentResult:
        proc = subprocess.run(
            cmd,
            input=stdin,
            text=True,
            cwd=str(self.workspace),
            env=self.env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.timeout,
            check=False,
        )

        events = None
        if parse_jsonl:
            events = []
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue

                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    events.append(
                        {
                            "type": "raw",
                            "message": line,
                        }
                    )

        return AgentResult(
            tool=tool,
            command=cmd,
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            events=events,
        )
```

---

## 45.1 Decisão sobre o AgentWrapper

Esse código deve permanecer como camada genérica de infraestrutura.

Ele não deve receber conhecimento sobre:

* persona;
* `tipo_de_post`;
* scoring autoral;
* gateway;
* briefing;
* regras de feed, article ou slide;
* avaliação do conteúdo gerado;
* segmentação.

Essas responsabilidades pertencem às camadas de produto e prompt.

---

## 46. TUI com Textual

A TUI é a interface operacional da engine. Ela não substitui a engine, apenas permite operá-la, testar prompts e depurar execuções de forma mais segura e produtiva.

---

## 46.1 Objetivo da TUI

Criar uma interface terminal para:

* preencher dados de entrada;
* editar briefing autoral no fluxo ativo;
* selecionar tipo de conteúdo;
* visualizar prompt renderizado;
* selecionar executor LLM;
* selecionar modelo;
* rodar o modelo;
* ver resultado;
* segmentar conteúdo;
* editar segmentos;
* avaliar conteúdo após segmentação;
* exportar resultado;
* depurar erros;
* validar comportamento do `PromptBuilder`.

---

## 46.2 Layout inicial

```txt
┌──────────────────────────────┬─────────────────────────────────────┐
│ Entrada do conteúdo           │ Prompt renderizado                  │
│                               │                                     │
│ Tema                          │ [TextArea read-only]                │
│ Plataforma                    │                                     │
│ Objetivo                      │                                     │
│ Personalidade                 │                                     │
│ Tipo: feed/article/slide      ├─────────────────────────────────────┤
│ Tool: codex/opencode          │ Resultado                           │
│ Model                         │                                     │
│ Sandbox                       │ stdout                              │
│ Briefing autoral JSON         │ stderr                              │
│                               │ events                              │
│ [Preview] [Rodar] [Limpar]    │                                     │
│ [Segmentar] [Avaliar]         │                                     │
│ [Exportar MD] [Exportar TXT]  │                                     │
└──────────────────────────────┴─────────────────────────────────────┘
```

---

## 46.3 Campos da TUI

Entrada textual:

* `tema`
* `plataforma`
* `objetivo_do_post`
* `personalidade`

Seletores:

* `tipo_de_post`: `feed`, `article`, `slide`
* `tool`: `codex`, `opencode`
* `model`: string opcional
* `sandbox`: `read-only`, `workspace-write`, `danger-full-access`

Áreas editáveis:

* briefing autoral JSON;
* scores;
* restrições de geração;
* contexto extra opcional;
* segmentos gerados.

Áreas somente leitura:

* prompt renderizado;
* stdout;
* stderr;
* eventos JSONL;
* JSON final extraído, quando possível.

Observação: a TUI não deve permitir edição de personas no MVP.

---

## 47. Fluxo da TUI

### 47.1 Gerar preview

1. Usuário preenche campos.
2. Usuário clica em `Preview`.
3. TUI valida campos obrigatórios.
4. TUI parseia briefing JSON.
5. TUI chama `build_generation_prompt`.
6. TUI mostra o prompt renderizado.
7. TUI persiste automaticamente a sessão.

---

### 47.2 Rodar LLM

1. Usuário clica em `Rodar`.
2. TUI verifica se não existe execução em andamento.
3. TUI garante que existe prompt renderizado.
4. TUI chama `AgentWrapper.run`.
5. Execução roda em worker/thread para não travar a interface.
6. Enquanto a execução estiver ativa, a TUI bloqueia nova geração.
7. TUI mostra `stdout`, `stderr`, `returncode` e eventos.
8. Se possível, TUI tenta parsear o JSON final.
9. Se o JSON for inválido, TUI exibe o erro de parse e mantém o `stdout` bruto visível.
10. O resultado pode ser segmentado mesmo sem avaliação prévia.
11. TUI persiste automaticamente a sessão.

---

### 47.3 Limpar saída

1. Usuário clica em `Limpar`.
2. TUI limpa área de resultado.
3. Prompt renderizado permanece.
4. TUI persiste automaticamente a sessão.

---

### 47.4 Persistência automática de sessão

A TUI deve persistir automaticamente o estado da sessão.

Eventos que podem disparar persistência:

* alteração de campos principais;
* geração de preview;
* execução finalizada;
* edição de briefing;
* edição de segmentos;
* exportação de conteúdo.

Estado mínimo persistido:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TuiSessionState:
    tema: str = ""
    plataforma: str = ""
    objetivo_do_post: str = ""
    personalidade: str = ""
    tipo_de_post: TipoDePost = "feed"
    tool: ToolName = "codex"
    model: str | None = None
    sandbox: str = "read-only"

    briefing_autoral: dict[str, Any] = field(default_factory=dict)
    scores: dict[str, Any] = field(default_factory=dict)
    restricoes_de_geracao: list[str] = field(default_factory=list)

    prompt_renderizado: str = ""
    stdout: str = ""
    stderr: str = ""
    returncode: int | None = None
    events: list[dict[str, Any]] = field(default_factory=list)

    conteudo_gerado: str = ""
    segmentos: list[dict[str, Any]] = field(default_factory=list)
```

Arquivo local sugerido:

```txt
.data/sessions/current-session.json
```

Regra:

```txt
A persistência automática serve para retomada da sessão.
Ela não substitui exportação do conteúdo final.
```

---

### 47.5 Exportação

A TUI deve permitir exportar o conteúdo final como Markdown e arquivo local.

Formatos mínimos:

```txt
.md
.txt
```

Sugestão de destino:

```txt
exports/
  single-responsibility-principle-feed.md
  single-responsibility-principle-feed.txt
```

A exportação deve ser uma ação explícita do usuário.

---

## 48. Requisitos funcionais adicionais

### RF-011 — Renderizar prompt condicional

A engine deve renderizar apenas a persona e as regras correspondentes ao `tipo_de_post`.

### RF-012 — Exibir prompt na TUI

A TUI deve exibir o prompt final renderizado antes da execução.

### RF-013 — Executar LLM pela TUI

A TUI deve executar `codex` ou `opencode` usando `AgentWrapper`.

### RF-014 — Exibir resultado da execução

A TUI deve exibir `stdout`, `stderr`, `returncode` e eventos JSONL quando existirem.

### RF-015 — Validar briefing JSON

A TUI deve validar se o briefing autoral informado é JSON válido antes de montar o prompt.

### RF-016 — Selecionar sandbox

A TUI deve permitir selecionar sandbox quando o executor for `codex`.

### RF-017 — Não anexar arquivos ao OpenCode no MVP

A TUI não deve permitir anexar arquivos ao `opencode` no MVP, mesmo que o `AgentWrapper` suporte esse recurso internamente.

### RF-018 — Persistir sessão automaticamente

A TUI deve persistir automaticamente o estado da sessão para permitir retomada posterior.

### RF-019 — Bloquear gerações concorrentes

A TUI deve impedir que uma nova execução LLM seja iniciada enquanto outra estiver em andamento.

### RF-020 — Exportar conteúdo

A TUI deve permitir exportar o conteúdo final em Markdown e arquivo local.

Formatos mínimos:

```txt
.md
.txt
```

### RF-021 — Avaliar conteúdo após segmentação

A avaliação do conteúdo gerado deve ocorrer depois da segmentação, e não como pré-requisito para segmentar.

### RF-022 — Exibir JSON sem validação rígida por schema

A TUI deve tentar parsear o JSON final, mas não deve bloquear a exibição se o schema estiver inválido ou incompleto.

---

## 49. Requisitos não funcionais adicionais

### RNF-009 — Separação de responsabilidades

A engine deve manter separadas as camadas de produto, prompt, execução e interface.

### RNF-010 — Testabilidade

O `PromptBuilder` deve ser testável sem chamar LLM.

### RNF-011 — Robustez

A execução deve capturar erros de subprocesso, timeout, JSON inválido e falhas de CLI.

### RNF-012 — Não bloqueio da interface

A TUI deve rodar chamadas demoradas em worker/thread.

### RNF-013 — Observabilidade local

A TUI deve mostrar informações suficientes para depuração: comando, return code, stdout, stderr e eventos.

### RNF-014 — Baixo acoplamento

O `AgentWrapper` deve poder ser usado fora da TUI.

### RNF-015 — Extensibilidade

Novos tipos de conteúdo devem ser adicionáveis com novos blocos de persona e regras, sem alterar o executor LLM.

### RNF-016 — Persistência local simples

A persistência automática da sessão deve usar armazenamento local simples, preferencialmente JSON, sem exigir banco de dados no MVP.

### RNF-017 — Execução sequencial

O MVP deve operar com uma execução LLM por vez, evitando concorrência e conflitos de estado.

---

## 50. Validações adicionais

### 50.1 Entrada da TUI

* `tema` não pode ser vazio.
* `plataforma` não pode ser vazia.
* `objetivo_do_post` não pode ser vazio.
* `tipo_de_post` deve ser `feed`, `article` ou `slide`.
* `briefing_autoral` deve ser JSON válido.
* `scores`, se informados, devem conter números.
* `restricoes_de_geracao`, se informadas, devem ser lista de strings.

---

### 50.2 Prompt renderizado

* Deve conter apenas uma persona ativa.
* Deve conter apenas um bloco de regras por formato.
* Deve conter contrato de saída JSON.
* Não deve conter condicionais textuais redundantes do tipo `Se for feed...`.
* Deve conter briefing serializado.
* Deve conter restrições de geração.

---

### 50.3 Saída do gerador

* Deve tentar retornar JSON válido.
* Deve conter `conteudo`.
* Deve conter `metadados`.
* Deve conter `alertas`.
* Deve declarar se usou primeira pessoa.
* Deve declarar base narrativa principal.
* Deve listar restrições aplicadas.
* Se o JSON estiver inválido, a TUI deve exibir o `stdout` bruto e o erro de parse.

O JSON final não será validado por schema antes de ser exibido no MVP.

---

### 50.4 Persistência de sessão

* A sessão deve ser salva automaticamente.
* A sessão deve poder ser restaurada ao abrir a TUI.
* Falha ao restaurar sessão não deve impedir o uso da TUI.
* Sessão persistida não equivale a exportação final.

---

### 50.5 Exportação

* O conteúdo final deve poder ser exportado como `.md`.
* O conteúdo final deve poder ser exportado como arquivo simples `.txt`.
* O nome do arquivo deve ser sanitizado.
* A exportação deve ser ação explícita do usuário.

---

## 51. Roadmap atualizado

### 51.1 MVP operacional

* `AgentWrapper` funcional;
* `PromptBuilder` funcional;
* renderização condicional por tipo de post;
* TUI com tela única;
* preview de prompt;
* execução via `codex` ou `opencode`;
* bloqueio de execução concorrente;
* persistência automática de sessão;
* exibição de resultado;
* tentativa de parse do JSON final;
* fallback para exibição de `stdout` bruto;
* segmentação sem avaliação prévia obrigatória;
* exportação para Markdown e arquivo;
* contrato JSON de saída;
* testes do `PromptBuilder`.

---

### 51.2 V1

* tela de entrevista;
* scoring autoral via LLM;
* geração automática de briefing;
* tela de review;
* avaliação do conteúdo gerado após segmentação;
* segmentação editável;
* restauração de sessões anteriores;
* carregamento de personas por arquivo Markdown.

---

### 51.3 V2

* histórico de entrevistas;
* comparação entre versões de prompt;
* avaliação automática entre múltiplos modelos;
* exportação avançada;
* suporte a múltiplas personas customizadas;
* editor segmentado mais avançado;
* validação opcional com schema;
* anexos no `opencode`, se necessário.

---

## 52. Critérios de sucesso atualizados

Além dos critérios já definidos no PRD original, a versão atualizada será considerada bem-sucedida se:

* a renderização condicional reduzir ruído no prompt;
* o conteúdo final respeitar o tipo de post;
* a TUI permitir operar o fluxo sem scripts manuais;
* o `PromptBuilder` puder ser testado isoladamente;
* o `AgentWrapper` continuar genérico e reutilizável;
* o usuário conseguir visualizar o prompt antes da execução;
* a execução LLM puder ser depurada por `stdout`, `stderr`, `returncode` e eventos;
* o sistema impedir mistura acidental entre regras de feed, article e slide;
* a TUI persistir automaticamente sessões;
* a TUI bloquear múltiplas gerações concorrentes;
* a exportação em Markdown e arquivo funcionar sem etapas manuais externas.

---

## 53. Decisões fechadas nesta revisão

1. O PRD original permanece como fonte base do produto.
2. O `AgentWrapper` permanece como camada de infraestrutura.
3. A renderização condicional fica fora do LLM.
4. O `PromptBuilder` seleciona persona e regras por `tipo_de_post`.
5. A TUI será construída com Python e Textual.
6. A TUI deve mostrar o prompt renderizado antes da execução.
7. Execuções demoradas devem rodar em worker/thread.
8. O output do gerador deve ser JSON válido como contrato esperado.
9. O sistema não pode inventar vivências pessoais.
10. Feed, article e slide possuem personas oficiais diferentes.
11. A primeira versão da TUI pode ser uma tela única.
12. A versão completa deve evoluir para três telas: entrevista, geração e revisão.
13. Os blocos de implementação do PRD devem usar Python como linguagem de referência.
14. A nomenclatura interna do código deve usar `snake_case`.
15. A nomenclatura enviada ao LLM pode usar `camelCase` quando fizer sentido para preservar contratos JSON de prompt.
16. O scoring autoral será feito via LLM.
17. O briefing autoral não será salvo automaticamente em arquivo local.
18. A TUI deve persistir sessões automaticamente.
19. O usuário não poderá editar personas pela TUI.
20. A avaliação do conteúdo gerado não será obrigatória antes da segmentação.
21. O sistema não deve permitir múltiplas gerações concorrentes.
22. O JSON final não será validado por schema antes de ser exibido.
23. A exportação direta deve suportar Markdown e arquivo.
24. A TUI não permitirá anexar arquivos ao `opencode` no MVP.

---

## 54. Questões que continuam em aberto

As questões abaixo ainda não foram fechadas explicitamente.

* A TUI deve permitir `danger-full-access` ou esconder essa opção por segurança?
* O projeto deve usar `dataclass`, `pydantic` ou ambos?
* Os contratos JSON retornados pelo LLM devem ser validados com `pydantic` em uma versão futura?
* O `memory_pack` deve ser salvo como JSON puro ou como modelo tipado?
* Os prompts devem ser versionados por arquivo Markdown, banco local ou ambos?

---

## 55. Fluxo completo atualizado

```txt
1. Usuário informa tema, plataforma, objetivo e tipo de post.
2. TUI persiste automaticamente o estado da sessão.
3. Engine inicia entrevista.
4. LLM gera pergunta.
5. Usuário responde.
6. LLM avalia resposta e retorna deltas de scoring autoral.
7. Engine atualiza scores.
8. Engine verifica gateway.
9. Se gateway não atingido, gera nova pergunta.
10. Se gateway atingido, gera briefing autoral em memória.
11. PromptBuilder seleciona persona ativa.
12. PromptBuilder seleciona regras do formato ativo.
13. PromptBuilder monta prompt final sem blocos condicionais concorrentes.
14. TUI exibe prompt renderizado.
15. Usuário executa LLM.
16. TUI bloqueia novas execuções enquanto a atual estiver em andamento.
17. AgentWrapper chama codex ou opencode.
18. Engine recebe conteúdo em JSON ou stdout bruto.
19. Engine segmenta conteúdo.
20. Usuário edita segmentos.
21. Engine reescreve apenas segmentos alterados.
22. Engine avalia o conteúdo gerado após segmentação.
23. Usuário exporta conteúdo final em Markdown ou arquivo.
24. TUI mantém sessão persistida para retomada futura.
```

---

# Apêndice A — Contratos Python recomendados

Este apêndice consolida os modelos principais em Python para orientar a implementação.

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, TypedDict


TipoDePost = Literal["post", "article", "short_carousel", "long_slide"]

AspectoAutoral = Literal[
    "experiencia",
    "opiniao",
    "sentimento",
    "aprendizado",
    "personalidade",
]

TipoGateway = Literal["equilibrado", "desequilibrado", "reprovado"]
TipoGatewayAprovado = Literal["equilibrado", "desequilibrado"]

TipoAutoria = Literal[
    "experiencial",
    "opinativa",
    "emocional",
    "reflexiva",
    "provocativa",
    "hibrida",
]

ToolName = Literal["codex", "opencode"]


ASPECTOS_AUTORAIS = (
    "experiencia",
    "opiniao",
    "sentimento",
    "aprendizado",
    "personalidade",
)

ASPECTOS_PRINCIPAIS = (
    "experiencia",
    "opiniao",
    "sentimento",
    "aprendizado",
)


class PontuacaoAspectos(TypedDict):
    experiencia: int
    opiniao: int
    sentimento: int
    aprendizado: int
    personalidade: int


class ListaAspectos(TypedDict):
    experiencia: list[str]
    opiniao: list[str]
    sentimento: list[str]
    aprendizado: list[str]
    personalidade: list[str]


@dataclass(frozen=True)
class InicioEntrevista:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    personalidade: str | None = None


@dataclass(frozen=True)
class ScoresAutorais:
    bruto: PontuacaoAspectos
    normalizado: PontuacaoAspectos
    total_bruto: int
    total_normalizado: int


@dataclass(frozen=True)
class ProximaMelhorPergunta:
    aspecto: AspectoAutoral
    pergunta: str
    motivo: str


@dataclass(frozen=True)
class AvaliacaoAutoralDaResposta:
    resposta_id: str
    deltas: PontuacaoAspectos
    evidencias: ListaAspectos
    lacunas: ListaAspectos
    proxima_melhor_pergunta: ProximaMelhorPergunta | None = None


@dataclass
class MemoryPack:
    fatos_vividos: list[str] = field(default_factory=list)
    exemplos_concretos: list[str] = field(default_factory=list)
    opinioes: list[str] = field(default_factory=list)
    sentimentos: list[str] = field(default_factory=list)
    aprendizados: list[str] = field(default_factory=list)
    tracos_de_personalidade: list[str] = field(default_factory=list)
    frases_do_usuario: list[str] = field(default_factory=list)
    tensoes_ou_conflitos: list[str] = field(default_factory=list)
    pontos_ainda_fracos: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ResultadoGateway:
    aprovado: bool
    tipo_gateway: TipoGateway
    tipo_autoria: TipoAutoria | None = None
    restricoes_de_geracao: list[str] = field(default_factory=list)
    proximas_lacunas: list[str] = field(default_factory=list)


@dataclass
class RespostaUsuario:
    pergunta: str
    texto: str


@dataclass
class InteracaoEntrevista:
    pergunta: str
    resposta: str
    avaliacao: AvaliacaoAutoralDaResposta


@dataclass
class EstadoEntrevista:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    scores: ScoresAutorais
    gateway: ResultadoGateway
    memory_pack: MemoryPack
    perguntas_e_respostas: list[InteracaoEntrevista]
    rodadas: int
    max_rodadas: int
    personalidade: str | None = None


@dataclass(frozen=True)
class GatewayAprovado:
    aprovado: bool
    tipo_gateway: TipoGatewayAprovado
    tipo_autoria: TipoAutoria
    restricoes_de_geracao: list[str]


@dataclass(frozen=True)
class RespostaAutoral:
    pergunta: str
    resposta: str


class RespostasAutorais(TypedDict):
    experiencia: list[RespostaAutoral]
    opiniao: list[RespostaAutoral]
    sentimento: list[RespostaAutoral]
    aprendizado: list[RespostaAutoral]
    personalidade: list[RespostaAutoral]


@dataclass(frozen=True)
class BriefingAutoral:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    gateway: GatewayAprovado
    scores: ScoresAutorais
    respostas_autorais: RespostasAutorais
    memory_pack: MemoryPack
    personalidade: str | None = None


@dataclass(frozen=True)
class ScoreDoPost:
    experiencia: int
    opiniao: int
    sentimento: int
    aprendizado: int
    personalidade: int
    fidelidade: int
    naturalidade: int

    @property
    def total(self) -> int:
        return (
            self.experiencia
            + self.opiniao
            + self.sentimento
            + self.aprendizado
            + self.personalidade
            + self.fidelidade
            + self.naturalidade
        )


@dataclass(frozen=True)
class SegmentoPost:
    id: str
    ordem: int
    texto: str
    papel_interno: str


@dataclass(frozen=True)
class GenerationPromptInput:
    tema: str
    plataforma: str
    objetivo_do_post: str
    tipo_de_post: TipoDePost
    briefing_autoral: dict[str, Any]
    scores: dict[str, Any] | None = None
    restricoes_de_geracao: list[str] | None = None
    personalidade: str | None = None
    tipo_gateway: str | None = None
    tipo_autoria: str | None = None


@dataclass
class AgentResult:
    tool: ToolName
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    events: list[dict] | None = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0
```

---

# Apêndice B — Funções Python recomendadas para scoring e gateway

```python
from typing import cast


def criar_scores_iniciais() -> ScoresAutorais:
    bruto = PontuacaoAspectos(
        experiencia=0,
        opiniao=0,
        sentimento=0,
        aprendizado=0,
        personalidade=0,
    )

    normalizado = PontuacaoAspectos(
        experiencia=0,
        opiniao=0,
        sentimento=0,
        aprendizado=0,
        personalidade=0,
    )

    return ScoresAutorais(
        bruto=bruto,
        normalizado=normalizado,
        total_bruto=0,
        total_normalizado=0,
    )


def atualizar_scores(
    score_atual: ScoresAutorais,
    avaliacao: AvaliacaoAutoralDaResposta,
) -> ScoresAutorais:
    bruto = cast(
        PontuacaoAspectos,
        {
            aspecto: score_atual.bruto[aspecto] + avaliacao.deltas[aspecto]
            for aspecto in ASPECTOS_AUTORAIS
        },
    )

    normalizado = cast(
        PontuacaoAspectos,
        {
            aspecto: min(bruto[aspecto], 100)
            for aspecto in ASPECTOS_AUTORAIS
        },
    )

    return ScoresAutorais(
        bruto=bruto,
        normalizado=normalizado,
        total_bruto=sum(bruto[aspecto] for aspecto in ASPECTOS_AUTORAIS),
        total_normalizado=sum(
            normalizado[aspecto]
            for aspecto in ASPECTOS_AUTORAIS
        ),
    )


def passou_gateway_equilibrado(
    score_normalizado: PontuacaoAspectos,
) -> bool:
    return all(
        score_normalizado[aspecto] >= 100
        for aspecto in ASPECTOS_AUTORAIS
    )


def passou_gateway_desequilibrado(
    score_bruto: PontuacaoAspectos,
) -> bool:
    total_bruto = sum(
        score_bruto[aspecto]
        for aspecto in ASPECTOS_AUTORAIS
    )

    maior_categoria_principal = max(
        score_bruto[aspecto]
        for aspecto in ASPECTOS_PRINCIPAIS
    )

    return (
        total_bruto >= 600
        and score_bruto["personalidade"] >= 80
        and maior_categoria_principal >= 200
    )


def classificar_tipo_autoria(
    score_bruto: PontuacaoAspectos,
) -> TipoAutoria:
    if (
        score_bruto["experiencia"] >= 100
        and score_bruto["opiniao"] >= 100
        and score_bruto["aprendizado"] >= 100
    ):
        return "hibrida"

    categorias: dict[TipoAutoria, int] = {
        "experiencial": score_bruto["experiencia"],
        "opinativa": score_bruto["opiniao"],
        "emocional": score_bruto["sentimento"],
        "reflexiva": score_bruto["aprendizado"],
    }

    return max(categorias, key=lambda categoria: categorias[categoria])


def gerar_restricoes_de_geracao(
    score_bruto: PontuacaoAspectos,
) -> list[str]:
    restricoes: list[str] = []

    if score_bruto["experiencia"] < 50:
        restricoes.extend(
            [
                "Não escrever como relato de experiência prática.",
                "Não sugerir que o usuário viveu algo que não contou.",
                "Gerar o texto como opinião, reflexão, provocação ou leitura pessoal.",
            ]
        )

    if score_bruto["opiniao"] < 50:
        restricoes.extend(
            [
                "Evitar tom opinativo forte.",
                "Basear o texto mais em vivência, aprendizado ou observação.",
            ]
        )

    if score_bruto["sentimento"] < 50:
        restricoes.extend(
            [
                "Não forçar emoção.",
                "Manter tom mais analítico ou prático.",
            ]
        )

    if score_bruto["aprendizado"] < 50:
        restricoes.extend(
            [
                "Não criar transformação pessoal artificial.",
                "Evitar frases como “isso me ensinou que” se o usuário não demonstrou aprendizado.",
            ]
        )

    if score_bruto["personalidade"] < 80:
        restricoes.extend(
            [
                "Usar linguagem mais neutra.",
                "Evitar simular um estilo pessoal muito marcado.",
            ]
        )

    return restricoes


def avaliar_gateway(scores: ScoresAutorais) -> ResultadoGateway:
    bruto = scores.bruto

    if passou_gateway_equilibrado(scores.normalizado):
        return ResultadoGateway(
            aprovado=True,
            tipo_gateway="equilibrado",
            tipo_autoria="hibrida",
            restricoes_de_geracao=[],
        )

    if passou_gateway_desequilibrado(bruto):
        return ResultadoGateway(
            aprovado=True,
            tipo_gateway="desequilibrado",
            tipo_autoria=classificar_tipo_autoria(bruto),
            restricoes_de_geracao=gerar_restricoes_de_geracao(bruto),
        )

    return ResultadoGateway(
        aprovado=False,
        tipo_gateway="reprovado",
        proximas_lacunas=identificar_lacunas(scores),
    )
```
