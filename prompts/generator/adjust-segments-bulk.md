Reescreva todos os segmentos indicados em uma unica resposta coerente, preservando o formato {{tipoDePost}} e usando o briefing e o contexto V4 como contrato de autoria.

Mantenha a voz do autor e a continuidade entre trechos adjacentes quando relevante. Cada segmento deve atender ao pedido do usuario e ao diagnostico editorial correspondente.

Conteudo completo: {{conteudoCompleto}}
Segmentos a ajustar: {{segmentosParaAjustar}}
Personalidade: {{personalidade}}
Restricoes: {{restricoesDeGeracao}}
Briefing: {{briefingAutoral}}
Contexto da entrevista V4: {{interviewContext}}

Retorne apenas JSON:
{
  "segmentosReescritos": [
    { "id": "...", "ordem": 1, "segmentoReescrito": "..." }
  ]
}

O array deve conter exatamente um item para cada segmento listado em segmentosParaAjustar, com o mesmo id e ordem.
