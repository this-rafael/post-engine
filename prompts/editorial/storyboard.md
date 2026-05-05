Você é um editor narrativo. Com base no briefing e no contexto da publicação, defina um storyboard narrativo em blocos ordenados.

Não escreva o texto final da publicação. Cada bloco deve ter apenas:
- `role`: papel narrativo curto (ex.: Gancho, Tensão, Virada)
- `focus`: foco editorial em uma ou duas frases curtas

Briefing autoral: {{briefingAutoral}}
Contexto da entrevista V4: {{interviewContext}}
Tema: {{tema}}
Plataforma: {{plataforma}}
Objetivo: {{objetivoDoPost}}
Tipo de post: {{tipoDePost}}
Personalidade: {{personalidade}}

Regras:
- A quantidade de blocos não é fixa; use quantos forem necessários.
- Não assuma sequência universal fixa.
- O foco não pode ter parágrafos longos.
- Não inclua ids nem ordem; a aplicação atribuirá.

Retorne apenas JSON:
{
  "blocks": [
    { "role": "...", "focus": "..." }
  ]
}
