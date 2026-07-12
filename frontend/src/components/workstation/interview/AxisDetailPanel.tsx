import { motion } from "motion/react";
import type { InterviewDimension } from "@/lib/mappers/interview";
import { cn } from "@/lib/utils";

function clampScore(score: number) {
  return Math.max(0, Math.min(100, Math.round(score)));
}

function levelLabel(score: number) {
  if (score >= 70) return "Explorado";
  if (score > 0) return "Parcial";
  return "Pendente";
}

export function AxisDetailPanel({
  dimensions,
  selectedDimensionId,
  onSelect,
}: {
  dimensions: InterviewDimension[];
  selectedDimensionId: string | null;
  onSelect: (id: string) => void;
}) {
  const dimension = dimensions.find((item) => item.id === selectedDimensionId) ?? dimensions[0];
  if (!dimension) return null;

  const score = clampScore(dimension.score ?? 0);
  const status = dimension.covered ? "Explorado" : levelLabel(score);

  return (
    <div className="panel p-4">
      <div className="mono-tag mb-3">dimensoes V4</div>
      <div className="mb-4 flex flex-wrap gap-1.5">
        {dimensions.map((item) => {
          const active = item.id === dimension.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onSelect(item.id)}
              className={cn(
                "relative rounded-md border px-2.5 py-1.5 font-mono text-[10px] transition-colors",
                active ? "border-transparent text-ink" : "border-hairline text-ink-faint hover:text-ink-dim",
              )}
            >
              {active && (
                <motion.span
                  layoutId="dimension-tab"
                  className="absolute inset-0 rounded-md border border-[color-mix(in_oklab,var(--flux)_45%,transparent)] bg-[color-mix(in_oklab,var(--flux)_14%,transparent)]"
                />
              )}
              <span className="relative z-10">{item.covered ? "●" : "○"} {item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mb-3 flex items-baseline justify-between">
        <div>
          <div className="font-display text-[15px] font-semibold">{dimension.label}</div>
          <div className="text-[12px] text-ink-faint">{dimension.description ?? "Dimensao autoral V4"}</div>
        </div>
        <span className="font-mono text-[11px] text-flux">{status}</span>
      </div>

      <div className="space-y-3">
        <p className="text-[12px] leading-relaxed text-ink-faint">{dimension.rationale ?? "Nenhuma evidencia observada."}</p>
        <div className="h-1 overflow-hidden rounded-full bg-surface-2">
          <div className="h-full rounded-full bg-flux" style={{ width: `${score}%` }} />
        </div>
        {(dimension.signals?.length || dimension.evidence?.length || dimension.rules_triggered?.length) ? (
          <div className="space-y-1 font-mono text-[10px] text-ink-faint">
            {dimension.signals?.length ? <div>sinais: {dimension.signals.length}</div> : null}
            {dimension.evidence?.length ? <div>evidencias: {dimension.evidence.length}</div> : null}
            {dimension.rules_triggered?.length ? <div>regras: {dimension.rules_triggered.join(", ")}</div> : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
