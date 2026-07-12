import { AnimatePresence, motion } from "motion/react";
import { usePE } from "@/lib/pe-store";
import { PeButton } from "../ui";
import { StageHeader, StageScroll } from "./common";
import { cn } from "@/lib/utils";

export function ExecutionStage() {
  const { events, runState, returnCode, rawOutput, runGeneration, clearOutput, segment, goto, ops, busy } =
    usePE();
  const genOp = ops.find((o) => o.id === "postGenerate");
  const running = runState === "running" || busy;

  const run = async () => {
    await runGeneration();
  };
  const doSegment = async () => {
    await segment();
    goto("segmentation");
  };

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 05 · geração"
        title="Executar o agente de geração"
        desc="Quando um agente trabalha, o ambiente ganha vida. Os eventos abaixo refletem o estado real da execução."
        aside={
          <div className="panel flex items-center gap-3 px-4 py-2.5">
            <div className="leading-tight">
              <div className="mono-tag !text-[9px]">agente de geração</div>
              <div className="font-mono text-[12px] text-ink-dim">
                {genOp?.provider} · {genOp?.model}
                {genOp?.reasoning ? ` · ${genOp.reasoning}` : ""}
              </div>
            </div>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        {/* reactor */}
        <div className="lg:col-span-2">
          <div className="panel relative flex h-full min-h-[380px] flex-col items-center justify-center overflow-hidden p-6">
            <Reactor active={running} state={runState} />
            <div className="relative z-10 mt-6 text-center">
              <div className="font-mono text-[11px] uppercase tracking-widest text-ink-faint">
                {running ? "gerando" : runState === "done" ? "finalizado" : "em repouso"}
              </div>
              {returnCode !== null && (
                <div className="mt-1 font-mono text-[11px] text-ink-faint">
                  return code · <span style={{ color: "var(--ok)" }}>{returnCode}</span>
                </div>
              )}
            </div>
            <div className="relative z-10 mt-5 flex gap-2">
              <PeButton variant="flux" onClick={run} loading={busy} disabled={running}>
                Executar LLM
              </PeButton>
              <PeButton variant="ghost" onClick={clearOutput} disabled={running || !rawOutput}>
                Limpar saída
              </PeButton>
            </div>
          </div>
        </div>

        {/* events + output */}
        <div className="space-y-4 lg:col-span-3">
          <div className="panel p-4">
            <div className="mono-tag mb-2">eventos de execução</div>
            <div className="space-y-1">
              <AnimatePresence>
                {events.length === 0 && (
                  <motion.div className="mono-tag py-3">aguardando execução</motion.div>
                )}
                {events.map((e, i) => (
                  <motion.div
                    key={e.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="flex items-center gap-3"
                  >
                    <span className="font-mono text-[10px] text-ink-faint">
                      {String(i).padStart(2, "0")}
                    </span>
                    <motion.span
                      className="h-1.5 w-1.5 rounded-full"
                      style={{ background: "var(--flux)" }}
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                    />
                    <span className="font-mono text-[11px] flux-text">{e.kind}</span>
                    <span className="text-[12.5px] text-ink-dim">{e.label}</span>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </div>

          <div className="panel flex min-h-[220px] flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
              <div className="mono-tag">saída bruta</div>
              {running && (
                <motion.span
                  className="h-2 w-2 rounded-full"
                  style={{ background: "var(--flux)" }}
                  animate={{ opacity: [1, 0.2, 1] }}
                  transition={{ duration: 0.8, repeat: Infinity }}
                />
              )}
            </div>
            <div className="flex-1 overflow-auto p-4">
              {rawOutput ? (
                <pre className="whitespace-pre-wrap text-[13px] leading-relaxed text-ink-dim">
                  {rawOutput}
                  {running && <span className="ml-0.5 inline-block h-4 w-1.5 align-middle animate-pulse" style={{ background: "var(--flux)" }} />}
                </pre>
              ) : (
                <div className="mono-tag py-8 text-center">nenhum conteúdo gerado</div>
              )}
            </div>
          </div>

          <AnimatePresence>
            {runState === "done" && rawOutput && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between rounded-lg border border-[color-mix(in_oklab,var(--flux)_35%,transparent)] bg-[color-mix(in_oklab,var(--flux)_8%,transparent)] px-4 py-3"
              >
                <span className="text-[12.5px] text-ink-dim">Geração válida — pronta para segmentar.</span>
                <PeButton variant="flux" onClick={doSegment}>
                  Segmentar →
                </PeButton>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </StageScroll>
  );
}

function Reactor({ active, state }: { active: boolean; state: string }) {
  return (
    <div className="relative grid h-44 w-44 place-items-center">
      {[0, 1, 2].map((r) => (
        <motion.div
          key={r}
          className={cn("absolute rounded-full border")}
          style={{
            inset: r * 18,
            borderColor: "color-mix(in oklab, var(--flux) 35%, transparent)",
          }}
          animate={
            active
              ? { rotate: r % 2 ? -360 : 360, scale: [1, 1.04, 1] }
              : { rotate: r % 2 ? -360 : 360 }
          }
          transition={{
            rotate: { duration: active ? 6 + r * 2 : 40 + r * 10, repeat: Infinity, ease: "linear" },
            scale: { duration: 2, repeat: Infinity },
          }}
        />
      ))}
      <motion.div
        className="absolute inset-8 rounded-full blur-md"
        style={{ background: "radial-gradient(circle, var(--flux), transparent 70%)" }}
        animate={{ opacity: active ? [0.5, 1, 0.5] : 0.25, scale: active ? [1, 1.15, 1] : 1 }}
        transition={{ duration: 1.6, repeat: Infinity }}
      />
      <motion.div
        className="relative h-8 w-8 rounded-full"
        style={{ background: "var(--flux)" }}
        animate={{ scale: active ? [1, 1.3, 1] : 1, boxShadow: active ? "0 0 40px var(--flux)" : "0 0 12px var(--flux)" }}
        transition={{ duration: 1.2, repeat: Infinity }}
      />
      {state === "done" && (
        <motion.div
          className="absolute inset-0 rounded-full border-2"
          style={{ borderColor: "var(--ok)" }}
          initial={{ scale: 0.6, opacity: 1 }}
          animate={{ scale: 1.4, opacity: 0 }}
          transition={{ duration: 1 }}
        />
      )}
    </div>
  );
}
