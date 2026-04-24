```txt
Segmente o documento SlideMark gerado em partes editaveis por slide.

Conteudo:
{conteudoDoPost}

Regras:
- Cada segmento corresponde a um slide em slidemark.slides (use id e type do slide).
- Mantenha ordem sequencial a partir de 1.
- papelInterno pode ser: capa, problema, contexto, explicacao, exemplo, insight, conclusao, fundamentos, edge-case, etc.
- Inclua slideType com o valor de type do slide (ex.: content.code, content.bullets).

Retorne apenas JSON:
{
  "segmentos": [
    {
      "id": "slide-1",
      "ordem": 1,
      "slideType": "cover.hero",
      "texto": "Titulo do slide\n- ponto principal",
      "papelInterno": "capa"
    }
  ]
}
```
