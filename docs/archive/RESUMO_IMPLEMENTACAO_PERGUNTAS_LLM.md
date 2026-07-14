# Resumo da Implementação

## Objetivo
Corrigir o fluxo da aba de perguntas e respostas para que as perguntas iniciais e recursivas venham da LLM, sem exibir ou persistir placeholders literais como `{tema}` e `{contextoDoTema}`.

## O que foi feito
- Endureci o gerador de perguntas em `src/content_engine/questions.py`.
- Adicionei validação para rejeitar perguntas com placeholders não resolvidos.
- Mantive a extração tolerante de JSON, mas agora o payload só é aceito se a pergunta for textual e válida.
- Ajustei o prompt inicial em `prompts/interview/initial-questions.md` para instruir explicitamente a LLM a não devolver placeholders literais.
- Sanitizei a restauração de sessão na TUI em `src/tui/app.py`.
- Se a sessão carregada contém perguntas inválidas, elas são descartadas na inicialização.
- Quando isso acontece, a interface não reutiliza o texto corrompido como pergunta atual.
- A TUI passa a sinalizar que uma nova pergunta deve ser gerada pela LLM.

## Implementação técnica
- Criei a função `tem_placeholder_nao_resolvido()` em `src/content_engine/questions.py` para detectar tokens entre chaves.
- A normalização de perguntas agora ignora entradas vazias ou com placeholders.
- O fluxo de restauração em `PostEngineApp` foi ajustado para não executar geração automática quando a sessão já trouxe uma pergunta inválida persistida.
- A tela continua funcional mesmo com sessão antiga corrompida; o estado inválido é limpo e a entrevista pode ser retomada corretamente.

## Regressoes cobertas
- Adicionei teste para garantir que o gerador descarte perguntas com placeholders literais.
- Adicionei teste para garantir que a TUI descarte perguntas persistidas com placeholders ao restaurar sessão.

## Validação
- `tests/test_spec_010_021.py`
- `tests/test_spec_041_048.py`
- `tests/test_spec_038_040.py`
- `tests/test_spec_058.py`

## Resultado
A aba de perguntas e respostas deixa de exibir a string com placeholders como se fosse uma pergunta válida. O sistema agora prefere gerar nova pergunta via LLM ou, se necessário, cair em fallback limpo sem reutilizar o texto corrompido.
