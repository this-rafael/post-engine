# Exportacao simultanea de Output para Markdown + JSON

## Resumo

Hoje o projeto ja consegue gerar `JSON` no dominio (`src/content_engine/exporter.py`), mas isso nao esta conectado ao fluxo principal da TUI: a fase 9 ainda expoe exportacoes separadas para `Markdown` e `TXT`, e o `JSON` so e emitido por `exportar_conteudo` quando a trilha e visual e ha `slides`.

A mudanca proposta e transformar a exportacao principal em um unico fluxo que sempre salve `MD + JSON` ao mesmo tempo, para todos os tipos de post, usando o mesmo basename e o mesmo diretorio de destino. `TXT` deixa de ser a saida principal; pode ser mantido temporariamente como compatibilidade interna se houver testes/codigo dependentes.

## Mudancas de implementacao

- Consolidar o dominio de exportacao em torno de `exportar_conteudo(...)`.
- Fazer `exportar_conteudo` sempre retornar dois arquivos: `<base>.md` e `<base>.json`.
- Parar de restringir o `.json` apenas a trilhas visuais.
- Definir um payload JSON estavel, minimo e comum a todos os posts:
  - `tema`
  - `plataforma`
  - `tipo_de_post`
  - `conteudo`
  - `metadados` (do `state.conteudo_json` quando existir; `{}` no fallback)
  - `alertas` (quando existir; `[]` no fallback)
  - `slides` (lista quando existir; `[]` no fallback)
  - `segmentos` (conteudo segmentado atual, quando existir; `[]` no fallback)
  - `avaliacao_post` (quando existir; `{}` no fallback)
  - `parse_error` (quando existir; `null`/ausente no caso normal)
- Ajustar a TUI da fase 9 em `src/tui/app.py`.
- Substituir os dois campos `#destino_markdown` e `#destino_txt` por um unico campo de destino baseado em `.md`.
- Substituir `btn_export_md` e `btn_export_txt` por um unico botao, por exemplo `btn_export_output`.
- Ao exportar, derivar automaticamente o `.json` do mesmo caminho informado para o `.md`.
- Trocar `action_export_md` / `action_export_txt` por uma unica acao que:
  - resolve o path `.md`
  - monta o payload JSON a partir do estado atual
  - chama `exportar_conteudo(...)`
  - atualiza status/notificacao listando os dois arquivos gerados
- Manter compatibilidade interna com o que ja existe.
- `exportar_markdown` e `exportar_json` continuam como helpers de baixo nivel.
- `exportar_txt` pode permanecer exportado por enquanto para evitar quebra desnecessaria em testes antigos, mas deixa de ser usado na TUI.
- Atualizar a API publica de `content_engine.__init__`.
- Garantir que `exportar_conteudo` e `exportar_json` continuem publicos.
- Se `exportar_txt` deixar de ser interface desejada do produto, so remover do fluxo da TUI nesta etapa; nao remover da API publica sem decisao explicita.

## APIs e contratos

- `exportar_conteudo(...)` passa a ser o contrato principal de exportacao final.
- O payload do `.json` deixa de depender apenas de `slides` e passa a representar o output final completo do produto.
- Interface da TUI na fase 9 muda de:
  - dois destinos (`md`, `txt`)
  - dois botoes (`Exportar Markdown`, `Exportar TXT`)
- Para:
  - um destino principal
  - um botao unico de exportacao final `Markdown + JSON`

## Testes

- Atualizar testes do exporter para validar:
  - exportacao simultanea gera `.md` e `.json`
  - ambos usam o mesmo stem
  - `.json` existe para `post`, `article`, `short_carousel` e `long_slide`
  - payload JSON contem `conteudo` e campos default quando nao houver dados ricos
  - payload JSON inclui `slides` quando houver trilha visual
- Adicionar/ajustar testes da TUI para validar:
  - fase 9 renderiza um unico botao de exportacao principal
  - acao de exportacao persiste estado e atualiza `status_operacional`
  - exportacao sem conteudo continua bloqueada
  - caminho informado com extensao nao-`.md` e normalizado para `.md`, e o `.json` e derivado do mesmo basename
- Preservar teste de "nao exporta automaticamente apos geracao".

## Assumptions

- Decisao adotada: a exportacao principal do produto passa a ser `MD + JSON` em um unico passo.
- Decisao adotada: o `.json` deve existir para todos os tipos de post, nao so para trilhas visuais.
- Decisao adotada: `TXT` deixa de ser a saida principal da interface, mas nao precisa ser removido do codigo nesta etapa.
- Quando nao houver dados estruturados suficientes no estado, o `.json` usa defaults vazios em vez de falhar.
