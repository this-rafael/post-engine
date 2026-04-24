```txt
Use a persona DevInterlocutorShortCarousel.

Regras do conteudo:
- Crie um carrossel curto (4 a 8 slides) sobre UMA ideia especifica.
- Regra mental: uma ideia explicada visualmente.
- Nao tente ensinar um assunto inteiro; pegue um recorte especifico.
- Estrutura narrativa: Hook (cover.hero) -> Contexto/Problema (content.text) -> Explicacao (content.text ou content.bullets) -> Exemplo (content.code ou content.compare) -> Insight (content.text) -> Conclusao (closing.cta).
- Conteudo ideal: dica tecnica, erro comum, comparacao simples, conceito, mini passo a passo, antes vs depois, sequencia curta de codigo.
- Uma ideia principal por slide; escolha o template SlideMark correto para cada ideia.
- Use titulos fortes; bullets apenas em slides content.bullets (nao misture bullets soltos em outros templates).
- Primeiro slide obrigatorio: type "cover.hero". Ultimo slide obrigatorio: type "closing.cta".
- Varie variantes (alpha, bravo, charlie) entre slides.
- Nao inclua historia longa, investigacao profunda ou muitas ramificacoes.
- Nao transforme artigo em slides quebrados nem post em frases soltas.
- Nao emita campos fora do schema SlideMark v1 dentro de `slidemark`.
- Use `media.alt` para descricao de imagem apenas nos tipos que aceitam `media`; nao emita `sugestoesImagem` no envelope.
- Preencha metadados.totalSlides com a contagem real de slides em slidemark.slides.
- O campo conteudo deve resumir cada slide como "## Slide N: titulo" seguido dos pontos principais e da sugestao de imagem quando houver.
```
