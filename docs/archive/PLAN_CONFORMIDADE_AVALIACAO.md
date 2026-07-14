# Plano de Conformidade — Avaliacao short_carousel

Alinhamento entre o novo prompt `prompts/generator/evaluate-post-short-carousel.md` e a UI/parser.

## 1. Divergencia atual

O novo prompt define um shape de saida que o codigo nao consome:

| Campo novo no prompt            | Suporte atual                                            |
| ------------------------------- | -------------------------------------------------------- |
| `score.tese`                    | Ausente (zerado por `_SCORE_KEYS`)                        |
| `score.progressao`              | Ausente                                                  |
| `score.concretude`              | Ausente                                                  |
| `score.precisaoTecnica`         | Ausente                                                  |
| `score.retencao`                | Ausente                                                  |
| `score.autoridade`              | Ausente                                                  |
| `score.autoria`                 | Ausente                                                  |
| `score.slidemark`               | Ausente                                                  |
| `score.revisaoTextual`          | Ausente                                                  |
| `veredito`                      | Descartado                                               |
| `slidesFracos[]`                | Descartado                                               |
| `redundancias[]`                | Descartado                                               |
| `falhasTecnicas[]`              | Descartado                                               |
| Total com peso (nao media)      | `ScoreDoPost.total` faz soma simples                     |

Resultado: todos os 8 cards da Fase 8 ficam zerados e nenhuma informacao editorial nova chega a UI.

## 2. Arquivos impactados

- `prompts/generator/evaluate-post-short-carousel.md` (ja reescrito)
- `src/content_engine/schemas.py` — `ScoreDoPost` (linha 252)
- `src/content_engine/post_evaluation.py` — `_SCORE_KEYS` (linha 14), `avaliar()` (linha 66), retorno
- `src/content_engine/__init__.py` — exports
- `src/tui/app.py` — `action_evaluate` (linha 3808), `_avaliar` (linha 3866), `_compose_phase_8` (linha 973), `_render_post_score` (linha 1745), `_serialize_avaliacao_post` (linha 1736)
- `src/content_engine/persistence.py` — `avaliacao_post` (linha 70, 270) — apenas `dict`; sem mudanca estrutural obrigatoria, mas validar retrocompatibilidade
- `src/content_engine/exporter.py` — `avaliacao_post` (linha 85, 138) — idem
- `tests/` — novos casos para o parser e TUI

## 3. Etapas

### 3.1. Schema (`schemas.py`)

- Substituir `ScoreDoPost` (linha 252) por nova dataclass com os 9 criterios + `total` ponderado:

  ```python
  class ScoreDoPost:
      tese: int
      progressao: int
      concretude: int
      precisao_tecnica: int
      retencao: int
      autoridade: int
      autoria: int
      slidemark: int
      revisao_textual: int
  ```

- Adicionar `total` como `@property` com pesos: `progressao=2`, `concretude=2`, `precisao_tecnica=2`, demais=1, normalizado para 0–10.
- Criar tipos auxiliares:
  - `SlideFraco` (dataclass: `slide: int`, `problema: str`, `severidade: Literal["baixa","media","alta"]`, `motivo: str`)
  - `AvaliacaoSlideMark` (dataclass agregando `score: ScoreDoPost`, `veredito: str`, `pontos_fortes: list[str]`, `pontos_fracos: list[str]`, `slides_fracos: list[SlideFraco]`, `redundancias: list[str]`, `falhas_tecnicas: list[str]`, `sugestoes_melhoria: list[str]`)
- Manter aliases de retrocompatibilidade para `experiencia`/`opiniao`/`sentimento`/`aprendizado`/`personalidade`/`fidelidade`/`naturalidade` apenas se outros modulos (`exporter`, `tests`, payloads antigos) ainda dependerem; caso contrario, remover.

### 3.2. Parser (`post_evaluation.py`)

- Trocar `_SCORE_KEYS` (linha 14) por:
  ```python
  _SCORE_KEYS: tuple[str, ...] = (
      "tese", "progressao", "concretude", "precisaoTecnica",
      "retencao", "autoridade", "autoria", "slidemark", "revisaoTextual",
  )
  ```
- Adicionar helper `_coerce_severidade` para `baixa|media|alta`.
- Em `avaliar()` (linha 66):
  - Manter a selecao de template (`generator.evaluate_post_short_carousel`).
  - Trocar o retorno de `tuple[ScoreDoPost, list[str], list[str], list[str]]` para `AvaliacaoSlideMark`.
  - Extrair `veredito`, `slidesFracos`, `redundancias`, `falhasTecnicas` com coerce seguro.
  - Calcular `total` ponderado localmente; nao confiar no valor retornado pela LLM.
- Aplicar regra "se tese>=8 mas progressao<5, cap total em 7" no calculo do `total` (ja prevista no prompt).

### 3.3. UI TUI (`app.py`)

- `_compose_phase_8` (linha 973):
  - Substituir os 8 `Static` atuais por 9 cards novos (`tese`, `progressao`, `concretude`, `precisaoTecnica`, `retencao`, `autoridade`, `autoria`, `slidemark`, `revisaoTextual`, `total`).
  - Adicionar secoes novas:
    - `Veredito` (TextArea read-only)
    - `Slides fracos` (DataTable com colunas `slide`, `problema`, `severidade`, `motivo`)
    - `Redundancias` (TextArea read-only)
    - `Falhas tecnicas` (TextArea read-only)
  - Manter secoes `Pontos fortes`, `Pontos fracos`, `Sugestoes de melhoria`.
- `_render_post_score` (linha 1745): atualizar o dicionario `labels` para os novos identificadores.
- `action_evaluate` (linha 3808): popular `state.avaliacao_post` com o novo shape (incluindo `slides_fracos`, `veredito`, `redundancias`, `falhas_tecnicas`).
- `_avaliar` (linha 3866): ajustar tipo de retorno e o fallback de erro para `AvaliacaoSlideMark`.
- `_serialize_avaliacao_post` (linha 1736): incluir os novos campos no JSON exibido no `#avaliacao_post`.
- Atualizar todos os pontos que checam `state.avaliacao_post` (linhas 1009, 1064, 2659, 2712, 2731, 3007, 3016, 3561, 3695, 3710) para o novo contrato.

### 3.4. Persistencia e exportacao

- `persistence.py` (linhas 70 e 270) e `exporter.py` (linhas 85 e 138): nenhuma alteracao obrigatoria — tratam `avaliacao_post` como `dict` generico. Validar:
  - Sessao antiga com chaves legadas ainda consegue ser carregada sem erro.
  - Exportacao MD/JSON inclui `veredito`, `slides_fracos`, `redundancias`, `falhas_tecnicas` quando presentes.
- Decidir politica: migrar sessoes antigas (descartar scores legados) ou manter `score` antigo como campo opcional.

### 3.5. Testes

Adicionar em `tests/`:

- `test_post_evaluation_parser.py`:
  - Parse de payload com todos os campos novos.
  - Coerção de `severidade` invalida para `"media"`.
  - Calculo do `total` ponderado.
  - Cap em 7 quando `tese>=8` e `progressao<5`.
  - Campos faltantes viram vazios (sem exceção).
- `test_post_evaluation_prompt.py`:
  - Confirmar que `generator.evaluate_post_short_carousel` existe e contem as secoes "AVALIE A TESE", "AVALIE A PROGRESSAO", "SCORE".
- `test_tui_phase8_layout.py` (se já houver padrao de teste Textual):
  - Cards renderizam com labels novos.
  - Botao `Avaliar` desabilitado enquanto nao houver `avaliacao_post` valido.

## 4. Riscos

- **Retrocompatibilidade**: sessoes salvas com o shape antigo de `score` nao terao os 9 criterios novos. Decidir entre "zerar e reavaliar" ou "manter para consulta".
- **Peso do total**: definicao de pesos nao foi fixada numericamente no prompt; o codigo precisa documentar a formula usada para que a UI mostre a nota esperada.
- **Latencia**: o novo prompt é maior; o parser deve continuar tolerante a truncamento do JSON.

## 5. Ordem de execucao sugerida

1. Schema (`schemas.py`) + tipos auxiliares.
2. Parser (`post_evaluation.py`) com testes unitarios.
3. UI (`app.py`) — `_render_post_score`, `_compose_phase_8`, `action_evaluate`, `_avaliar`.
4. Teste manual: rodar `scripts/run.fish`, gerar carrossel, clicar `Avaliar`, validar cards e secoes novas.
5. Persistencia/exportacao: validar carregamento de sessao antiga e exportacao.
6. Atualizar `tests/` e rodar suite.

## 6. Checklist de aceite

- [ ] 9 cards + `Total` renderizam com valores nao zero apos `Avaliar`.
- [ ] `Veredito`, `Slides fracos`, `Redundancias`, `Falhas tecnicas` aparecem populados.
- [ ] `Total` respeita regra de cap (tese>=8 + progressao<5 → total<=7).
- [ ] Sessao antiga carrega sem erro de schema.
- [ ] Exportacao MD/JSON contem os novos campos quando aplicavel.
- [ ] Suite de testes verde.
