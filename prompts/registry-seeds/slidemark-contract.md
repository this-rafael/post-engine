## Contrato SlideMark v1 atual (obrigatorio)

Retorne JSON estrito. Dentro de `slidemark`, emita somente propriedades abaixo.
Nao crie chaves extras, nem reutilize campos de outro tipo de slide.

Envelope obrigatorio:
- `version`: `"1.0.0"`.
- `document`: `{ "title": string, "description": string, "language": "pt-BR" | "en-US" }`.
- `canvas`: `{ "width": 1080, "height": 1080 }`.
- `theme`: um tema oficial: `rafael-io-executive-dark`, `diffvision-dark`, `diffvision-dracula`, `diffvision-lust`, `diffvision-one-light`, `diffvision-min-light`, `diffvision-papercolor-light`, `mongodb-dark`, `mongodb-light`.
- `author`: `{ "name": string, "handle": "@..." }`; `avatar` e opcional e aceita `null`, uma fonte ou `{ "src": string, "alt"?: string }`.
- `settings`: `showAuthor`, `showPageNumber`, `showSwipeHint` (booleanos) e `swipeHintText` (texto nao vazio).
- `export`: `{ "fileName": string, "formats": ["png" | "zip" | "pdf"], "pdf": { "pageMode": "square", "source": "rendered-images" } }`; a lista de formatos nao pode estar vazia nem repetir valores.
- `slides`: lista nao vazia. Primeiro slide deve ser `cover.hero` e ultimo `closing.cta` para este produto.

Todos os slides aceitam apenas `id`, `type`, `variant`, `title`, `subtitle`, `textAlign`, `decorations` e os campos especificos abaixo. `id` e `title` sao textos nao vazios. `variant` e `alpha`, `bravo` ou `charlie`; `textAlign`, se existir, e `left`, `center` ou `justify`. `decorations` e uma lista de objetos estritos com `type` (`accent-symbol`, `circle`, `arrow`), `position` opcional (`top-left`, `top-right`, `bottom-left`, `bottom-right`, `left-center`, `right-center`, `center`), `x`, `y` (0..1080), `width`, `height` (positivos, ate 1080), `label`, `symbol`, `rotation` (-360..360).

Tipos de slide e campos especificos:
- `cover.hero`: `media` opcional e `cta` opcional.
- `content.text`: `body` obrigatorio (lista nao vazia de textos), `highlight` opcional exatamente `{ "text": string, "label"?: string }`, `emphasis` opcional (lista de `{ "text": string, "style": "bold" | "accent" | "muted" | "strike" }`). Nunca use `highlight` em outro tipo.
- `content.code`: `language` e `code` obrigatorios; opcionais `description`, `highlightLines` (inteiros positivos), `showLineNumbers` (booleano), `caption`. Mantenha codigo em ate 14 linhas por seguranca visual.
- `content.image`: `media` obrigatorio; opcionais `description`, `caption`.
- `content.screenshot`: `media` obrigatorio; opcionais `description`, `caption`, `frame` (`browser`, `editor`, `plain`) e `annotations`. Cada annotation e estrita: `type` (`arrow`, `circle`, `box`, `label`), `x`, `y` (0..1080), `width`, `height` opcionais positivos ate 1080, `label` ou `text` opcionais.
- `content.bullets`: `bullets` obrigatorio, com objetos `{ "text": string, "description"?: string, "icon"?: string }`; `style` opcional: `default`, `checklist` ou `numbered`. Use no maximo 4 itens na variante `charlie`.
- `content.compare`: `left` e `right` obrigatorios. Cada lado e `{ "title"?: string, "label"?: string, "items": [string, ...] }` e precisa de `title` ou `label`; `comparisonStyle` opcional: `before-after`, `right-wrong`, `pros-cons`.
- `closing.cta`: `cta` obrigatorio; opcionais `body` (lista de textos), `text` e `media`.

Imagem: `media` e estrito e usa `{ "type": "image", "src": string, "alt"?: string, "fit"?: "contain" | "cover" | "crop-center" | "wide-banner" | "screenshot-frame" }`. `src` aceita `@placeholderImage`, URL http(s), data URL de imagem, `@uploaded...` com extensao de imagem ou caminho iniciado por `/`, `./` ou `../`.

Quando houver uma Sugestao de imagem para um slide que aceita `media`, use sua `descricao` exatamente em `media.alt`. Para sugestao sem URL real, use `"src": "@placeholderImage"`; para link real, use a URL como `src`. Sem sugestao, nao crie placeholder. Para que a imagem seja exibida, use `cover.hero` `bravo` ou `charlie`, e `closing.cta` `bravo`; todos os variantes de `content.image` e `content.screenshot` exibem media.
