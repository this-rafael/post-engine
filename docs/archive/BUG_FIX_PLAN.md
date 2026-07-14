# Plano de Correção: Bug tipo_de_post sendo resetado para "post"

## Status: CORRIGIDO

## Causa Raiz Identificada

O bug tinha **duas causas** que se combinavam:

### 1. Backend: `_atualizar_estado_do_formulario` sobrescrevia `tipo_de_post` sem verificar widget

**Arquivo**: `src/content_engine/session_app.py` (linha ~2447)

Na GUI React, os widgets Textual não existem. O método `_coletar_formulario()` retornava `tipo_de_post: ""` (widget inexistente), e `migrate_tipo_de_post("")` retornava `"post"`. Como `"post"` está em `_TIPOS_VALIDOS`, o `state.tipo_de_post` era sobrescrito com `"post"`, apagando o valor correto que havia sido aplicado via `_apply_state_patch`.

Todos os outros campos (tema, plataforma, objetivo, personalidade, model) já verificavam `_safe_query(self, "#id") is not None` antes de sobrescrever. O `tipo_de_post` era o único que não fazia essa verificação.

### 2. Frontend: `syncDraftFromSession` sobrescrevia `draftRef` com React state desatualizado

**Arquivo**: `frontend/src/lib/pe-store.tsx` (linha ~498)

O `continueToInterview` chamava `syncDraftFromSession()`, que copiava os valores do React state (`session`) para o `draftRef.current`. Como o `setSessionState` do React é assíncrono, o `session` podia estar desatualizado (ainda com `contentTypeValue: "post"`), sobrescrevendo o `draftRef.current` que já tinha o valor correto (atualizado sincronamente pelo `setSession`).

## Correções Aplicadas

### Correção 1: Backend (principal)
```python
# Antes:
if migrate_tipo_de_post(dados["tipo_de_post"]) in _TIPOS_VALIDOS:
    self.state.tipo_de_post = migrate_tipo_de_post(dados["tipo_de_post"])

# Depois:
if _safe_query(self, "#tipo_de_post") is not None and migrate_tipo_de_post(dados["tipo_de_post"]) in _TIPOS_VALIDOS:
    self.state.tipo_de_post = migrate_tipo_de_post(dados["tipo_de_post"])
```

### Correção 2: Frontend
```typescript
// Antes:
const continueToInterview = useCallback(async () => {
    syncDraftFromSession();
    try { ... }
}, [syncDraftFromSession, withAction]);

// Depois:
const continueToInterview = useCallback(async () => {
    // draftRef já está atualizado pelo setSession
    try { ... }
}, [withAction]);
```

## Testes

5 testes adicionados em `tests/test_tipo_de_post_bug.py`, todos passando.
