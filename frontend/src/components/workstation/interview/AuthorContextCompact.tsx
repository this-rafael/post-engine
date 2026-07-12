import { motion } from "motion/react";
import { AnimatedNumber } from "../ui";
import { cn } from "@/lib/utils";
import { useMotionSafe } from "./motion";

interface AxisRow {
  key: string;
  label: string;
  covered: number;
  total: number;
  highlight?: boolean;
}

export function AuthorContextCompact({
  coveredTotal,
  totalAxes,
  axes,
  onExploreMap,
}: {
  coveredTotal: number;
  totalAxes: number;
  axes: AxisRow[];
  onExploreMap: () => void;
}) {
  const { spring } = useMotionSafe();

  return (
    <div className="panel p-4">
      <div className="mono-tag">contexto autoral</div>
      <div className="mt-2 font-display text-[16px] font-semibold">
        <AnimatedNumber value={coveredTotal} />
        <span className="text-ink-faint"> / {totalAxes} eixos</span>
      </div>

      <div className="mt-4 space-y-2">
        {axes.map((a) => {
          const pct = a.total ? (a.covered / a.total) * 100 : 0;
          return (
            <div key={a.key}>
              <div className="mb-0.5 flex items-center justify-between">
                <span className="text-[11px] text-ink-dim">{a.label}</span>
                <span className="font-mono text-[10px] text-ink-faint">
                  <AnimatedNumber value={a.covered} /> / {a.total}
                </span>
              </div>
              <div className="relative h-1 overflow-hidden rounded-full bg-surface-2">
                <motion.div
                  className={cn(
                    "h-full rounded-full",
                    a.highlight && "flux-glow",
                  )}
                  style={{
                    background:
                      "linear-gradient(90deg, color-mix(in oklab, var(--flux) 60%, transparent), var(--flux))",
                  }}
                  animate={{ width: `${pct}%` }}
                  transition={spring}
                />
              </div>
            </div>
          );
        })}
      </div>

      <button
        type="button"
        onClick={onExploreMap}
        className="mt-4 w-full rounded-md border border-hairline bg-surface/50 px-3 py-2 text-left font-mono text-[10px] uppercase tracking-wide text-ink-dim transition-colors hover:border-[color-mix(in_oklab,var(--flux)_35%,transparent)] hover:text-ink"
      >
        Explorar mapa →
      </button>
    </div>
  );
}
