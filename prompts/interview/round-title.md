# Geracao de titulo da rodada

Gere um titulo curto (2-5 palavras, sem aspas, sem ponto final) que capture
o foco tematico desta rodada da entrevista. O titulo sera exibido na interface
ao lado do numero da rodada (ex.: "Rodada 03: Escolha tecnica").

Diretrizes:
- Titulo em portugues brasileiro.
- Reflete a direcao de exploracao da pergunta atual.
- Nao use "Entrevista", "Rodada", numeros ou prefixos genericos.
- Pode ser: um aspecto tecnico, uma escolha, um trade-off, uma experiencia,
  um aprendizado, uma posicao, um diagnostico, etc.
- Maximo 5 palavras. Seja conciso e descritivo.

Contexto:
- Tema geral: {{theme}}
- Formato: {{format}}
- Numero da rodada: {{round_number}}
- Pergunta atual: {{question}}
- Direcao da pergunta: {{direction}}
- Sinais ja observados: {{signals_summary}}

Retorne APENAS o titulo, sem aspas, sem explicacao, sem prefixo.
