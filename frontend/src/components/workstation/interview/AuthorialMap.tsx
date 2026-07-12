import { motion } from "motion/react";
import type { InterviewDimension } from "@/lib/mappers/interview";

function clampScore(score: number) {
  return Math.max(0, Math.min(100, Math.round(score)));
}

function levelLabel(score: number) {
  if (score >= 70) return "Explorado";
  if (score > 0) return "Parcial";
  return "Pendente";
}

/** The radar and the list deliberately consume the exact V4 dimension collection. */
export function AuthorialMap({
  dimensions,
  expanded = false,
}: {
  dimensions: InterviewDimension[];
  expanded?: boolean;
}) {
  if (!dimensions.length) return null;

  const size = expanded ? 300 : 220;
  const cx = size / 2;
  const cy = size / 2;
  const maxRadius = size * 0.34;
  const step = (Math.PI * 2) / dimensions.length;
  const polygonPoints = dimensions
    .map((item, index) => {
      const angle = step * index;
      const radius = (clampScore(item.score ?? 0) / 100) * maxRadius;
      const x = cx + radius * Math.cos(angle - Math.PI / 2);
      const y = cy + radius * Math.sin(angle - Math.PI / 2);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="panel p-4">
      {!expanded && <div className="mono-tag mb-2">mapa autoral V4</div>}
      <div className={expanded ? "grid grid-cols-1 gap-4" : "grid grid-cols-1 gap-4 md:grid-cols-2"}>
        <div className="flex justify-center">
          <svg
            viewBox={`0 0 ${size} ${size}`}
            className={expanded ? "h-64 w-64 xl:h-72 xl:w-72" : "h-48 w-48"}
            role="img"
            aria-label="Radar das dimensoes autorais V4"
          >
            {[25, 50, 75, 100].map((ring) => (
              <circle key={ring} cx={cx} cy={cy} r={(ring / 100) * maxRadius} fill="none" stroke="var(--hairline)" />
            ))}
            {dimensions.map((item, index) => {
              const angle = step * index;
              const outerX = cx + maxRadius * Math.cos(angle - Math.PI / 2);
              const outerY = cy + maxRadius * Math.sin(angle - Math.PI / 2);
              return <line key={item.id} x1={cx} y1={cy} x2={outerX} y2={outerY} stroke="var(--hairline)" />;
            })}
            <polygon points={polygonPoints} fill="color-mix(in oklab, var(--flux) 25%, transparent)" stroke="var(--flux)" />
            {dimensions.map((item, index) => {
              const angle = step * index;
              const labelX = cx + (maxRadius + 16) * Math.cos(angle - Math.PI / 2);
              const labelY = cy + (maxRadius + 16) * Math.sin(angle - Math.PI / 2);
              return (
                <text key={`label-${item.id}`} x={labelX} y={labelY} textAnchor="middle" className="fill-ink-faint text-[8px]">
                  {item.label}
                </text>
              );
            })}
          </svg>
        </div>
        <div className="space-y-2">
          {dimensions.map((item) => {
            const score = clampScore(item.score ?? 0);
            return (
              <div key={item.id}>
                <div className="mb-1 flex items-center justify-between text-[12px]">
                  <span className="text-ink-dim">{item.label}</span>
                  <span className="font-mono text-[10px] text-ink-faint">{levelLabel(score)} - {score}%</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
                  <motion.div
                    className="h-full rounded-full bg-flux"
                    animate={{ width: `${score}%` }}
                    transition={{ type: "spring", stiffness: 120, damping: 20 }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
