import { motion } from "motion/react";
import { AnimatedNumber, PeButton } from "../ui";
import type { NewAxisCapture } from "./useInterviewUx";
import { useMotionSafe } from "./motion";

export function CoverageUpdated({
  newAxes,
  coveredTotal,
  totalAxes,
  prevCovered,
  onContinue,
}: {
  newAxes: NewAxisCapture[];
  coveredTotal: number;
  totalAxes: number;
  prevCovered: number;
  onContinue: () => void;
}) {
  const { spring } = useMotionSafe();

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-1 flex-col items-center justify-center py-12 text-center"
    >
      <div className="mono-tag">cobertura atualizada</div>
      <h2 className="mt-4 font-display text-[32px] font-semibold tracking-tight flux-text">
        <AnimatedNumber value={newAxes.length} />{" "}
        {newAxes.length === 1 ? "novo eixo capturado" : "novos eixos capturados"}
      </h2>

      <motion.div
        className="mt-4 font-display text-[20px] font-medium text-ink-dim"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
      >
        <AnimatedNumber value={prevCovered} />
        <span className="mx-2 text-ink-faint">→</span>
        <AnimatedNumber value={coveredTotal} />
        <span className="ml-2 text-[14px] text-ink-faint">/ {totalAxes}</span>
      </motion.div>

      <ul className="mt-8 w-full max-w-md space-y-2 text-left">
        {newAxes.map((axis, i) => (
          <motion.li
            key={axis.axisId}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ ...spring, delay: 0.15 + i * 0.08 }}
            className="panel flex items-center gap-3 p-3"
          >
            <span
              className="h-2 w-2 shrink-0 rounded-full"
              style={{ background: "var(--flux)", boxShadow: "0 0 12px var(--flux)" }}
            />
            <span className="text-[13px]">
              <span className="text-ink-faint">{axis.groupLabel}</span>
              <span className="mx-1.5 text-ink-faint">/</span>
              <span className="font-medium text-ink">{axis.axisLabel}</span>
            </span>
          </motion.li>
        ))}
      </ul>

      <PeButton variant="flux" className="mt-10" onClick={onContinue}>
        Continuar →
      </PeButton>
    </motion.div>
  );
}
