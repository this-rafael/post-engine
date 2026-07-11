import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { usePE } from "@/lib/pe-store";
import { PeButton } from "./ui";
import { cn } from "@/lib/utils";

type Tab = "state" | "operations" | "events" | "payload" | "fullstate" | "restore";

export function DevDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const pe = usePE();
  const [tab, setTab] = useState<Tab>("state");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (open) window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!copied) return;
    const t = window.setTimeout(() => setCopied(false), 1600);
    return () => window.clearTimeout(t);
  }, [copied]);

  const copyFullState = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(pe.actionState, null, 2));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const generationOp = pe.ops.find((o) => o.id === "postGenerate");

  const inspectorState = {
    stage: pe.stage,
    phase: pe.phase,
    runState: pe.runState,
    returnCode: pe.returnCode,
    rounds: pe.rounds,
    segments: pe.segments.length,
    evalScore: pe.evalScore,
    coverage: `${pe.axes.reduce((a, x) => a + x.covered, 0)} / ${pe.axes.reduce((a, x) => a + x.total, 0)}`,
    briefingReady: pe.briefingReady,
    promptRendered: pe.promptRendered,
    status: pe.statusText,
    error: pe.error,
  };

  const payload = {
    provider: generationOp?.provider,
    model: generationOp?.model,
    reasoning: generationOp?.reasoning ?? null,
    sandbox: generationOp?.sandbox,
    session: pe.session,
    exportPath: pe.exportPath,
    state: pe.snapshot?.state ?? {},
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            className="fixed inset-0 z-40 bg-[oklch(0.06_0.01_265/0.6)] backdrop-blur-[2px]"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className="fixed right-0 top-0 z-50 flex h-full w-[440px] max-w-[92vw] flex-col panel !rounded-none !rounded-l-xl"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 320, damping: 36 }}
          >
            <div className="flex items-center justify-between border-b border-hairline px-4 py-3.5">
              <div>
                <div className="mono-tag">developer inspector</div>
                <div className="font-display text-[15px] font-semibold">Camada técnica</div>
              </div>
              <button
                onClick={onClose}
                className="grid h-7 w-7 place-items-center rounded-md text-ink-faint hover:bg-surface-2 hover:text-ink"
              >
                ✕
              </button>
            </div>

            <div className="flex flex-wrap gap-1 border-b border-hairline px-3 py-2">
              {(["state", "operations", "events", "payload", "fullstate", "restore"] as Tab[]).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  className={cn(
                    "relative rounded-md px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide transition-colors",
                    tab === t ? "text-ink" : "text-ink-faint hover:text-ink-dim",
                  )}
                >
                  {tab === t && (
                    <motion.span
                      layoutId="dev-tab"
                      className="absolute inset-0 rounded-md bg-surface-2"
                    />
                  )}
                  <span className="relative z-10">{t}</span>
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              {tab === "state" && <Json data={inspectorState} />}
              {tab === "payload" && <Json data={payload} />}
              {tab === "fullstate" && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="mono-tag">state enviado em /api/action</div>
                    <PeButton variant="ghost" onClick={copyFullState}>
                      {copied ? "Copiado" : "Copiar"}
                    </PeButton>
                  </div>
                  <Json data={pe.actionState} />
                </div>
              )}
              {tab === "operations" && (
                <div className="space-y-2">
                  {pe.ops.map((op) => (
                    <div key={op.id} className="inset-panel p-3">
                      <div className="text-[12px] font-medium text-ink-dim">{op.label}</div>
                      <div className="mt-1 font-mono text-[11px] leading-relaxed text-ink-faint">
                        {op.provider} · {op.model}
                        {op.reasoning ? ` · reasoning:${op.reasoning}` : ""} · {op.sandbox}
                      </div>
                    </div>
                  ))}
                </div>
              )}
              {tab === "events" && (
                <div className="space-y-3">
                  <div className="space-y-1.5">
                    {pe.events.length === 0 && (
                      <div className="mono-tag py-8 text-center">nenhum evento de execução</div>
                    )}
                    {pe.events.map((e, i) => (
                      <motion.div
                        key={e.id}
                        initial={{ opacity: 0, x: 8 }}
                        animate={{ opacity: 1, x: 0 }}
                        className="flex items-center gap-2 font-mono text-[11px]"
                      >
                        <span className="text-ink-faint">{String(i).padStart(2, "0")}</span>
                        <span className="h-1 w-1 rounded-full" style={{ background: "var(--flux)" }} />
                        <span className="text-ink-dim">{e.kind}</span>
                        <span className="text-ink-faint">{e.label}</span>
                      </motion.div>
                    ))}
                  </div>
                  {pe.rawOutput && (
                    <div>
                      <div className="mono-tag mb-1">raw output</div>
                      <pre className="inset-panel max-h-64 overflow-auto whitespace-pre-wrap p-3 font-mono text-[11px] leading-relaxed text-ink-dim">
                        {pe.rawOutput}
                      </pre>
                    </div>
                  )}
                  {Object.keys(pe.serialized).length > 0 && (
                    <div>
                      <div className="mono-tag mb-1">serialized</div>
                      <Json data={pe.serialized} />
                    </div>
                  )}
                </div>
              )}
              {tab === "restore" && (
                <div className="space-y-3">
                  <div className="mono-tag">restaurar sessão JSON</div>
                  <textarea
                    className="field min-h-[240px] w-full resize-y px-3 py-2 font-mono text-[11px]"
                    value={pe.restoreText}
                    onChange={(e) => pe.setRestoreText(e.target.value)}
                    placeholder='{ "session_id": "..." } ou { "state": { ... } }'
                  />
                  <PeButton variant="flux" onClick={() => pe.restore()} disabled={!pe.restoreText.trim()}>
                    Restaurar sessão
                  </PeButton>
                </div>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function Json({ data }: { data: unknown }) {
  return (
    <pre className="inset-panel overflow-auto whitespace-pre-wrap p-3 font-mono text-[11.5px] leading-relaxed text-ink-dim">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}
