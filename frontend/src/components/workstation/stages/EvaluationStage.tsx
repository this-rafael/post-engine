import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { usePE } from "@/lib/pe-store";
import type { EvalDimension } from "@/lib/pe-types";
import { AnimatedNumber, PeButton } from "../ui";
import { FormattedText } from "../FormattedText";
import { ReadjustAllModal } from "../ReadjustAllModal";
import { StageHeader, StageScroll } from "./common";
import { cn } from "@/lib/utils";

function scoreColor(s: number) {
  if (s >= 80) return "var(--ok)";
  if (s >= 65) return "var(--flux)";
  return "var(--ember)";
}

export function EvaluationStage() {
  const { evaluation, evalScore, evaluate, goto, focus, busy, weakSegments } = usePE();
  const [readjustOpen, setReadjustOpen] = useState(false);
  const run = async () => {
    await evaluate();
  };
  const jumpToSegment = (ref?: number) => {
    if (ref === undefined) return;
    focus(ref);
    goto("segmentation");
  };

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 07 · diagnóstico editorial"
        title="Avaliação do post"
        desc="O agente avaliador mede o conteúdo por dimensão. Cada diagnóstico pode apontar para o segmento afetado — navegue direto até o trecho."
        aside={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {evaluation && weakSegments.length > 0 && (
              <PeButton
                variant="outline"
                onClick={() => setReadjustOpen(true)}
                disabled={busy}
              >
                Reajustar todos
              </PeButton>
            )}
            <PeButton variant={evaluation ? "outline" : "flux"} onClick={run} loading={busy}>
              {evaluation ? "Avaliar novamente" : "Avaliar"}
            </PeButton>
          </div>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-1">
          <div className="panel sticky top-0 flex flex-col items-center p-6">
            <div className="relative grid h-40 w-40 place-items-center">
              <svg className="absolute inset-0 -rotate-90" viewBox="0 0 100 100">
                <circle cx="50" cy="50" r="44" fill="none" stroke="var(--surface-2)" strokeWidth="6" />
                <motion.circle
                  cx="50" cy="50" r="44" fill="none"
                  stroke={scoreColor(evalScore ?? 0)}
                  strokeWidth="6" strokeLinecap="round"
                  strokeDasharray={2 * Math.PI * 44}
                  initial={{ strokeDashoffset: 2 * Math.PI * 44 }}
                  animate={{ strokeDashoffset: 2 * Math.PI * 44 * (1 - (evalScore ?? 0) / 100) }}
                  transition={{ duration: 1.4, ease: [0.22, 1, 0.36, 1] }}
                />
              </svg>
              <div className="text-center">
                <div className="font-display text-[40px] font-semibold leading-none">
                  {evalScore !== null ? <AnimatedNumber value={evalScore} /> : "—"}
                </div>
                <div className="mono-tag mt-1">score total</div>
              </div>
              {busy && (
                <motion.div
                  className="absolute inset-x-4 h-8 sheen-line"
                  animate={{ top: ["10%", "80%", "10%"] }}
                  transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
                />
              )}
            </div>
            <p className="mt-4 text-center text-[12px] leading-relaxed text-ink-faint">
              {evaluation
                ? "9 dimensões editoriais medidas. Ajuste os segmentos com menor score e reavalie."
                : busy
                  ? "varrendo · medindo · analisando…"
                  : "execute a avaliação para diagnosticar o post."}
            </p>
          </div>
        </div>

        <div className="space-y-2.5 lg:col-span-2">
          <AnimatePresence>
            {evaluation?.map((d, i) => (
              <EvalCard key={d.key} d={d} i={i} onJump={() => jumpToSegment(d.segmentRef)} />
            ))}
          </AnimatePresence>
          {!evaluation && !busy && (
            <div className="panel grid min-h-[300px] place-items-center">
              <p className="mono-tag">nenhuma avaliação executada</p>
            </div>
          )}
        </div>
      </div>

      <AnimatePresence>
        {evaluation && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 flex items-center justify-between"
          >
            <PeButton variant="ghost" onClick={() => goto("segmentation")}>
              ← Voltar aos segmentos
            </PeButton>
            <PeButton variant="flux" onClick={() => goto("export")}>
              Exportar artefatos →
            </PeButton>
          </motion.div>
        )}
      </AnimatePresence>

      <ReadjustAllModal open={readjustOpen} onClose={() => setReadjustOpen(false)} />
    </StageScroll>
  );
}

function EvalCard({ d, i, onJump }: { d: EvalDimension; i: number; onJump: () => void }) {
  const [open, setOpen] = useState(d.score < 65);
  const color = scoreColor(d.score);
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: i * 0.06, type: "spring", stiffness: 220, damping: 26 }}
      className="panel overflow-hidden"
    >
      <button
        onClick={() => setOpen((open) => !open)}
        className="flex w-full items-center gap-4 p-4 text-left"
      >
        <div className="relative h-10 w-10 shrink-0">
          <svg className="absolute inset-0 -rotate-90" viewBox="0 0 40 40">
            <circle cx="20" cy="20" r="16" fill="none" stroke="var(--surface-2)" strokeWidth="3.5" />
            <motion.circle
              cx="20" cy="20" r="16" fill="none" stroke={color} strokeWidth="3.5" strokeLinecap="round"
              strokeDasharray={2 * Math.PI * 16}
              initial={{ strokeDashoffset: 2 * Math.PI * 16 }}
              animate={{ strokeDashoffset: 2 * Math.PI * 16 * (1 - d.score / 100) }}
              transition={{ duration: 1, delay: i * 0.06 }}
            />
          </svg>
          <span className="absolute inset-0 grid place-items-center font-mono text-[10px]" style={{ color }}>
            {d.score}
          </span>
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] font-medium">{d.key}</div>
          <div className="truncate text-[12px] text-ink-faint">{d.diagnosis}</div>
        </div>
        <span className={cn("font-mono text-[10px] text-ink-faint transition-transform", open && "rotate-90")}>
          ›
        </span>
      </button>
      <AnimatePresence>
        {open && (d.problem || d.direction) && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden border-t border-hairline"
          >
            <div className="space-y-2.5 p-4">
              {d.problem && (
                <div>
                  <div className="mono-tag mb-0.5">problema</div>
                  <p className="text-[12.5px] leading-relaxed text-ink-dim">
                    <FormattedText text={d.problem} />
                  </p>
                </div>
              )}
              {d.direction && (
                <div>
                  <div className="mono-tag mb-0.5">direção sugerida</div>
                  <p className="text-[12.5px] leading-relaxed text-ink-dim">
                    <FormattedText text={d.direction} />
                  </p>
                </div>
              )}
              {d.segmentRef !== undefined && (
                <PeButton variant="outline" onClick={onJump} className="!py-1.5 !text-[12px]">
                  Ir ao segmento {String(d.segmentRef + 1).padStart(2, "0")} →
                </PeButton>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
