Escreva o rascunho de UM único bloco da publicação, na voz da persona indicada, seguindo a abordagem escolhida.

Você conhece a publicação completa, mas deve escrever APENAS o bloco atual — não escreva os outros blocos.

Persona: {{personaName}} ({{personaId}})
Abordagem: {{approachTitle}} — {{approachDescription}}

Bloco atual — papel: {{blockRole}}, foco: {{blockFocus}}
Posição: {{blockPosition}} de {{totalBlocks}}

Blocos já escritos e selecionados (continuidade obrigatória — mantenha tom, referências e encadeamento; não reescreva): {{previousSelectedDraftsJson}}

Outros blocos (contexto, não escrever): {{otherBlocksJson}}
Storyboard: {{storyboardJson}}
Briefing: {{briefingAutoral}}
Tema: {{tema}}
Plataforma: {{plataforma}}
Tipo: {{tipoDePost}}

## Políticas anti-IA obrigatórias (hard — rascunho)

Constraints de geração, não heurísticas brandas. Severidade `hard` é veto:
reescreva o trecho antes de retornar. Proibido travessão (—), antítese-template
("não é X, é Y"), epigrama moral de fechamento e tríades abstratas decorativas.

{{politicasAntiIa}}

Antes de retornar o JSON: se o rascunho soar como essay LinkedIn (cadência
uniforme, contraste teatral, máxima final), reescreva na voz da persona, com
cena, custo ou mecanismo.

Retorne apenas JSON:
{
  "draft": {
    "content": "..."
  }
}
