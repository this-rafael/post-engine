import { motion } from "motion/react";
import { usePE } from "@/lib/pe-store";
import type { StageId } from "@/lib/pe-types";
import { cn } from "@/lib/utils";

const STAGES: { id: StageId; num: string; label: string; sub: string }[] = [
  { id: "agents", num: "00", label: "Agentes", sub: "Roteamento" },
  { id: "entry", num: "01", label: "Entrada", sub: "Intenção" },
  { id: "interview", num: "02", label: "Entrevista", sub: "Contexto" },
  { id: "briefing", num: "03", label: "Briefing", sub: "Síntese" },
  { id: "storyboard", num: "04", label: "Storyboard", sub: "Fluxo" },
  { id: "drafts", num: "05", label: "Rascunhos", sub: "Opções" },
  { id: "composition", num: "06", label: "Composição", sub: "Convergência" },
  { id: "segmentation", num: "07", label: "Segmentação", sub: "Estrutura" },
  { id: "evaluation", num: "08", label: "Avaliação", sub: "Diagnóstico" },
  { id: "export", num: "09", label: "Exportação", sub: "Artefatos" },
];

export function PipelineRail({ onNavigate }: { onNavigate?: () => void }) {
  const { stage, goto, reachable, phase, phaseProgress } = usePE();
  const activeIndex = STAGES.findIndex((s) => s.id === stage);

  return (
    <nav className="flex h-full w-full max-w-[248px] shrink-0 flex-col panel !rounded-none !rounded-r-xl border-l-0 py-4">
      <div className="px-5 pb-5">
        <div className="flex items-center gap-2.5">
          <motion.div
            className="relative h-7 w-7 shrink-0 rounded-[7px]"
            style={{
              background:
                "conic-gradient(from 0deg, var(--flux), color-mix(in oklab,var(--flux) 30%, transparent), var(--flux))",
            }}
            animate={{ rotate: 360 }}
            transition={{ duration: phase === "idle" ? 22 : 6, repeat: Infinity, ease: "linear" }}
          >
            <span className="absolute inset-[3px] rounded-[4px] bg-surface" />
            <span className="absolute inset-0 grid place-items-center font-display text-[11px] font-bold flux-text">
              P
            </span>
          </motion.div>
          <div className="leading-tight">
            <div className="font-display text-[14px] font-semibold tracking-tight">Post Engine</div>
            <div className="mono-tag !text-[9px]">editorial machine</div>
          </div>
        </div>
      </div>

      <div className="relative flex-1 overflow-y-auto px-3">
        <ul className="relative space-y-0.5">
          {STAGES.map((s, i) => {
            const isActive = s.id === stage;
            const locked = !reachable[s.id];
            const done = i < activeIndex && reachable[s.id];
            return (
              <li key={s.id}>
                <button
                  disabled={locked}
                  onClick={() => {
                    goto(s.id);
                    onNavigate?.();
                  }}
                  data-testid={`rail-${s.id}`}
                  className={cn(
                    "group relative flex w-full items-center gap-3 rounded-md px-2.5 py-2 text-left transition-colors",
                    locked ? "cursor-not-allowed opacity-35" : "hover:bg-surface-2",
                  )}
                >
                  {isActive && (
                    <motion.span
                      layoutId="rail-active"
                      className="absolute inset-0 rounded-md border border-[color-mix(in_oklab,var(--flux)_40%,transparent)] bg-[color-mix(in_oklab,var(--flux)_10%,transparent)]"
                      transition={{ type: "spring", stiffness: 380, damping: 34 }}
                    />
                  )}
                  <span
                    className={cn(
                      "relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded font-mono text-[10px]",
                      isActive ? "bg-[color-mix(in_oklab,var(--flux)_20%,transparent)] flux-text" : "text-ink-faint",
                    )}
                  >
                    {done ? "✓" : s.num}
                  </span>
                  <span className="relative z-10 min-w-0">
                    <div className={cn("text-[12.5px] font-medium leading-tight", isActive && "flux-text")}>
                      {s.label}
                    </div>
                    <div className="mono-tag !text-[9px]">{s.sub}</div>
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        <section className="mt-4 border-t border-hairline/50 pt-3" data-testid="phase-progress">
          <div className="mb-2 flex items-center gap-1.5">
            <div className="h-1 w-1 rounded-full bg-ink-faint/50" />
            <span className="mono-tag !text-[9px] text-ink-faint/70">Fases da sessão</span>
          </div>
          <div className="flex items-center gap-[3px]">
            {phaseProgress.phases.map((item) => {
              const released = item.status !== "pending";
              const active = item.status === "active";
              return (
                <div
                  key={item.id}
                  className={cn(
                    "h-[3px] flex-1 rounded-full transition-colors",
                    active ? "bg-[color-mix(in_oklab,var(--flux)_60%,transparent)]" : released ? "bg-ink-faint/40" : "bg-ink-faint/10",
                  )}
                />
              );
            })}
          </div>
        </section>
      </div>
    </nav>
  );
}
