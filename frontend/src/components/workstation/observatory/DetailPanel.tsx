import { useEffect, useState } from "react";
import {
  activatePromptVersion, createPromptVersion, previewPrompt, rollbackPromptVersion,
} from "@/lib/pe-api";
import { cn } from "@/lib/utils";
import { ErrorAccordion, PeButton, Reveal } from "../ui";
import { shortPhaseLabel, type OpRecord } from "./graph-layout";

const record = (value: unknown): OpRecord => value && typeof value === "object" && !Array.isArray(value) ? value as OpRecord : {};
const list = (value: unknown): OpRecord[] => Array.isArray(value) ? value.map(record) : [];
const text = (value: unknown) => value == null ? "—" : String(value);

export function DetailPanel({
  open,
  phase,
  phaseOps,
  operationKey,
  operation,
  artifact,
  onSelectOperation,
  onSelectArtifact,
  onChanged,
  onClose,
  mobile,
}: {
  open: boolean;
  phase: { key: string; label: string; group: string; order: number; artifact_count: number } | null;
  phaseOps: OpRecord[];
  operationKey: string;
  operation: OpRecord | null;
  artifact: OpRecord | null;
  onSelectOperation: (key: string) => void;
  onSelectArtifact: (key: string) => void;
  onChanged: () => void;
  onClose: () => void;
  mobile: boolean;
}) {
  if (!open) return null;
  const items = list(record(operation?.composition).items);

  return (
    <>
      {mobile && (
        <button
          type="button"
          aria-label="Fechar painel"
          className="absolute inset-0 z-20 bg-[oklch(0.06_0.01_265/0.45)]"
          onClick={onClose}
        />
      )}
      <aside
      className={cn(
        "z-30 flex min-h-0 flex-col border-hairline bg-[color-mix(in_oklab,var(--void)_55%,var(--surface))] shadow-[-24px_0_60px_-40px_oklch(0_0_0/0.75)] backdrop-blur-md",
        mobile
          ? "absolute inset-x-0 bottom-0 max-h-[min(88dvh,88vh)] w-full rounded-t-xl border-t"
          : "absolute inset-y-0 right-0 w-[min(420px,42vw)] border-l",
      )}
      aria-label="Detalhes da fase"
      style={
        mobile
          ? { paddingBottom: "env(safe-area-inset-bottom, 0px)" }
          : undefined
      }
    >
      {mobile && (
        <div className="flex shrink-0 justify-center pt-2" aria-hidden>
          <span className="h-1 w-10 rounded-full bg-hairline-strong" />
        </div>
      )}
      <div className="flex items-start justify-between gap-3 border-b border-hairline px-4 py-3">
        <div className="min-w-0">
          <div className="mono-tag">{phase ? `${String(phase.order).padStart(2, "0")} · ${phase.group}` : "fase"}</div>
          <h2 className="mt-1 truncate font-display text-lg font-semibold tracking-tight">
            {phase ? shortPhaseLabel(phase.label, phase.group) : "Selecione uma fase"}
          </h2>
          <p className="mt-1 text-xs text-ink-faint">
            {phaseOps.length} operações · {phase?.artifact_count ?? 0} artefatos
          </p>
        </div>
        <PeButton variant="ghost" onClick={onClose} aria-label="Fechar painel">✕</PeButton>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {!phase ? (
          <div className="grid place-items-center p-8 text-center mono-tag">Selecione uma fase no canvas</div>
        ) : (
          <>
            <section className="border-b border-hairline px-4 py-3">
              <div className="mono-tag mb-2">operações</div>
              <div className="space-y-2">
                {phaseOps.map((item) => {
                  const selected = operationKey === text(item.key);
                  return (
                    <button
                      key={text(item.key)}
                      type="button"
                      onClick={() => onSelectOperation(text(item.key))}
                      className={cn(
                        "w-full rounded-lg border p-3 text-left transition",
                        selected
                          ? "border-[color-mix(in_oklab,var(--flux)_50%,transparent)] bg-[color-mix(in_oklab,var(--flux)_9%,transparent)]"
                          : "border-hairline bg-surface/70 hover:bg-surface-2",
                      )}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="text-sm font-medium">{text(item.label)}</span>
                        <span className="font-mono text-[9px] flux-text">v{text(item.composition_version)}</span>
                      </div>
                      <div className="mt-1 font-mono text-[10px] text-ink-faint">{text(item.key)}</div>
                      <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-ink-dim">
                        <span>{text(record(item.configured).provider)} · {text(record(item.configured).model)}</span>
                        {Boolean(item.is_conditional) && <span className="rounded border border-hairline px-1">condicional</span>}
                        {String(item.retry_policy ?? "").trim() && <span className="rounded border border-hairline px-1">retry</span>}
                      </div>
                      <div className="mt-1 truncate font-mono text-[9px] text-ink-faint">{text(item.consumer_symbol)}</div>
                    </button>
                  );
                })}
              </div>
            </section>

            {operation && (
              <section className="border-b border-hairline px-4 py-3">
                <div className="mono-tag mb-2">composição · provider · diagnóstico</div>
                <div className="inset-panel space-y-2 p-3 text-[11px] text-ink-dim">
                  <div><span className="text-ink-faint">provider</span> · {text(record(operation.configured).provider)} / {text(record(operation.configured).model)}</div>
                  <div><span className="text-ink-faint">consumer</span> · {text(operation.consumer_symbol)}</div>
                  <div><span className="text-ink-faint">rollout</span> · {text(operation.rollout_mode)}</div>
                  {String(operation.retry_policy ?? "").trim() && <div><span className="text-ink-faint">retry</span> · {text(operation.retry_policy)}</div>}
                  {String(operation.description ?? "").trim() && <p className="text-ink-dim">{text(operation.description)}</p>}
                </div>
                <div className="mt-3 space-y-2">
                  {items.map((item) => {
                    const art = record(item.artifact);
                    const key = text(art.key);
                    return (
                      <button
                        key={`${key}-${text(item.position)}`}
                        type="button"
                        onClick={() => onSelectArtifact(key)}
                        className={cn(
                          "w-full rounded-lg border p-2.5 text-left",
                          artifact && text(artifact.key) === key
                            ? "border-[color-mix(in_oklab,var(--flux)_50%,transparent)] bg-[color-mix(in_oklab,var(--flux)_9%,transparent)]"
                            : "border-hairline bg-surface/60 hover:bg-surface-2",
                        )}
                      >
                        <div className="flex gap-2">
                          <span className="font-mono text-[10px] text-ink-faint">{text(item.position)}</span>
                          <span className="min-w-0 flex-1 truncate text-sm">{text(art.title)}</span>
                        </div>
                        <div className="mt-1 truncate font-mono text-[10px] text-ink-faint">{key}</div>
                      </button>
                    );
                  })}
                </div>
                {list(operation.diagnostics).length > 0 && (
                  <div className="mt-3 space-y-2">
                    {list(operation.diagnostics).map((diag, i) => (
                      <div key={i} className="rounded-lg border border-[color-mix(in_oklab,var(--danger)_35%,transparent)] p-2 text-[11px] text-[var(--danger)]">
                        {text(diag.message ?? diag.code ?? diag)}
                      </div>
                    ))}
                  </div>
                )}
                {list(operation.executions)[0] && (
                  <div className="mt-3 text-[10px] text-ink-faint">
                    última execução · {text(record(list(operation.executions)[0]).resolved_at)}
                  </div>
                )}
              </section>
            )}

            <section className="px-4 py-3">
              <ArtifactInspector artifact={artifact} operation={operation} onChanged={onChanged} />
            </section>
          </>
        )}
      </div>
    </aside>
    </>
  );
}

function ArtifactInspector({
  artifact, operation, onChanged,
}: {
  artifact: OpRecord | null;
  operation: OpRecord | null;
  onChanged: () => void;
}) {
  const [mode, setMode] = useState<"visualizar" | "atualizar">("visualizar");
  const [draft, setDraft] = useState("");
  const [resolved, setResolved] = useState<string | null>(null);
  const [showResolved, setShowResolved] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const content = record(artifact?.active).content;
    setDraft(typeof content === "string" ? content : "");
    setResolved(null);
    setShowResolved(false);
    setShowHistory(false);
    setMessage(null);
    setMode("visualizar");
  }, [artifact]);

  if (!artifact) {
    return (
      <div className="rounded-lg border border-dashed border-hairline p-6 text-center mono-tag">
        {operation ? "Selecione um artefato no canvas ou na lista" : "Selecione uma operação"}
      </div>
    );
  }

  const active = record(artifact.active);
  const original = typeof active.content === "string" ? active.content : "";
  const editability = text(artifact.editability);
  const canEdit = editability.startsWith("EDITABLE");
  const dirty = draft !== original;

  const goUpdate = () => {
    setMode("atualizar");
    setShowResolved(false);
    setMessage(null);
  };

  const cancelUpdate = () => {
    setDraft(original);
    setMode("visualizar");
    setMessage(null);
  };

  const saveUpdate = async () => {
    if (!dirty) {
      setMessage("Nenhuma alteração para salvar.");
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      const version = await createPromptVersion(text(artifact.key), {
        content: draft,
        expected_active_version: active.version,
        expected_active_hash: active.content_hash,
        reason: "Atualização pelo Observatory",
      });
      await activatePromptVersion(text(artifact.key), Number(version.version), {
        expected_active_version: active.version,
        expected_active_hash: active.content_hash,
      });
      setMessage(`Prompt atualizado · v${text(version.version)} ativa.`);
      setMode("visualizar");
      onChanged();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  const loadResolved = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const payload = await previewPrompt({
        operation: operation?.key,
        context: sampleContext(operation),
      });
      setResolved(text(payload.content));
      setShowResolved(true);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Reveal>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="mono-tag">{text(artifact.type)}</div>
          <h3 className="font-display text-base font-semibold">{text(artifact.title)}</h3>
          <div className="mt-1 font-mono text-[11px] text-ink-faint">
            {text(artifact.key)} · v{text(active.version)} · {text(active.content_hash).slice(0, 12)}
          </div>
          {Array.isArray(active.placeholders) && active.placeholders.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1">
              {(active.placeholders as unknown[]).map((ph) => (
                <span key={String(ph)} className="rounded border border-hairline px-1.5 py-0.5 font-mono text-[9px] text-ink-dim">{`{{${String(ph)}}}`}</span>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="mt-4 flex gap-1 rounded-lg border border-hairline bg-surface/60 p-1" role="tablist" aria-label="Modo do artefato">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "visualizar"}
          onClick={() => { setMode("visualizar"); setMessage(null); }}
          className={cn(
            "flex-1 rounded-md px-3 py-2 text-sm font-medium transition",
            mode === "visualizar" ? "bg-[color-mix(in_oklab,var(--flux)_14%,var(--surface))] flux-text" : "text-ink-dim hover:text-ink",
          )}
        >
          Visualizar
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "atualizar"}
          disabled={!canEdit}
          onClick={goUpdate}
          className={cn(
            "flex-1 rounded-md px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-40",
            mode === "atualizar" ? "bg-[color-mix(in_oklab,var(--flux)_14%,var(--surface))] flux-text" : "text-ink-dim hover:text-ink",
          )}
        >
          Atualizar
        </button>
      </div>

      {mode === "visualizar" && (
        <div className="mt-3 space-y-3">
          <pre className="inset-panel max-h-[360px] overflow-auto whitespace-pre-wrap p-3 font-mono text-[12px] leading-relaxed text-ink-dim">
            {original || "—"}
          </pre>
          <div className="flex flex-wrap gap-2">
            {canEdit && <PeButton variant="flux" onClick={goUpdate}>Atualizar prompt</PeButton>}
            {Boolean(operation?.key) && (
              <PeButton variant="ghost" onClick={loadResolved} loading={busy}>
                {showResolved ? "Atualizar resolução" : "Ver prompt resolvido"}
              </PeButton>
            )}
            <PeButton variant="ghost" onClick={() => setShowHistory((v) => !v)}>
              {showHistory ? "Ocultar histórico" : "Histórico"}
            </PeButton>
          </div>
          {!canEdit && <p className="text-xs text-ink-faint">Este artefato é somente leitura.</p>}
          {showResolved && (
            <div>
              <div className="mono-tag mb-2">prompt resolvido (amostra)</div>
              <pre className="inset-panel max-h-[280px] overflow-auto whitespace-pre-wrap p-3 font-mono text-[11px] leading-relaxed text-ink-dim">
                {resolved || "—"}
              </pre>
            </div>
          )}
        </div>
      )}

      {mode === "atualizar" && (
        <div className="mt-3 space-y-3">
          <p className="text-xs text-ink-faint">Edite o texto abaixo e salve para publicar a nova versão ativa.</p>
          <textarea
            aria-label="Editar conteúdo do prompt"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="field min-h-[320px] w-full resize-y p-3 font-mono text-[12px] leading-relaxed outline-none"
          />
          <div className="flex flex-wrap gap-2">
            <PeButton variant="flux" onClick={saveUpdate} loading={busy} disabled={!dirty}>
              Salvar atualização
            </PeButton>
            <PeButton variant="ghost" onClick={cancelUpdate} disabled={busy}>Cancelar</PeButton>
          </div>
          {dirty && <p className="text-[11px] text-ink-dim">Alterações não salvas.</p>}
        </div>
      )}

      {showHistory && (
        <div className="mt-4 space-y-2">
          <div className="mono-tag">histórico de versões</div>
          {list(artifact.versions).slice().reverse().map((version) => (
            <div key={text(version.version)} className="inset-panel flex items-center justify-between gap-3 p-3">
              <div>
                <div className="font-mono text-xs">v{text(version.version)} · {text(version.status)}</div>
                <div className="mt-1 text-[11px] text-ink-faint">{text(version.change_reason)} · {text(version.created_at)}</div>
              </div>
              {text(version.status) !== "ACTIVE" && canEdit && (
                <PeButton
                  variant="ghost"
                  onClick={async () => {
                    setBusy(true);
                    try {
                      await rollbackPromptVersion(text(artifact.key), Number(version.version));
                      setMessage(`Versão ${text(version.version)} restaurada.`);
                      setMode("visualizar");
                      onChanged();
                    } catch (err) {
                      setMessage(String(err));
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  Restaurar
                </PeButton>
              )}
            </div>
          ))}
        </div>
      )}

      {message && (
        <div className="mt-3"><ErrorAccordion title="Resultado" details={message} variant="warning" /></div>
      )}
    </Reveal>
  );
}

export function sampleContext(operation: OpRecord | null): OpRecord {
  return {
    content_type: "post", is_visual_track: false, retry_attempt: 0, tema: "Conteúdo de demonstração",
    plataforma: "linkedin", objetivoDoPost: "explicar o fluxo", tipoDePost: "post", personalidade: "direta",
    restricoesDeGeracao: "[]", briefingAutoral: "{}", gatewayResult: "{}", interviewContext: "{}",
    evidenceLedger: "[]", authorialSignals: "[]", authorialDimensions: "{}", interviewGaps: "[]",
    candidate_count: 2, context_json: "{}", known_issues: "", material_json: "{}",
    conteudoGerado: "conteúdo", conteudoDoPost: "conteúdo", papeisEsperados: "[]", conteudoCompleto: "conteúdo",
    segmentoAtual: "segmento", ajusteDoUsuario: "ajuste", eixoAlvo: "eixo", estruturaNarrativa: "{}",
    conteudoFinal: "conteúdo", segmentosJson: "[]", sugestoesImagem: "[]", slidemarkOriginal: "{}",
    selectedDraftsJson: "[]", editorialAnchorsJson: "[]", blockRole: "", blockFocus: "",
    previousSelectedDraftsJson: "[]", preservation_issues: "",
    ...(operation ? {} : {}),
  };
}
