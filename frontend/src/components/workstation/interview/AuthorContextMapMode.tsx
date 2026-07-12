import { motion } from "motion/react";
import { useState } from "react";
import type { InterviewUi } from "@/lib/mappers/interview";
import { AnimatedNumber, PeButton } from "../ui";
import { AuthorialMap } from "./AuthorialMap";
import { AxisDetailPanel } from "./AxisDetailPanel";
import { useMotionSafe } from "./motion";

export function AuthorContextMapMode({
  interviewUi,
  coveredTotal,
  totalAxes,
  editorialFeedback,
  onClose,
}: {
  interviewUi: InterviewUi;
  coveredTotal: number;
  totalAxes: number;
  editorialFeedback: string | null;
  onClose: () => void;
}) {
  const dimensions = interviewUi.dimensions ?? [];
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const selectedDimensionId = selectedId ?? dimensions[0]?.id ?? null;
  const percent = interviewUi.counter?.percent ?? (totalAxes ? Math.round((coveredTotal / totalAxes) * 100) : 0);
  const { spring } = useMotionSafe();

  return (
    <motion.div
      initial={{ opacity: 0, x: 24 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 24 }}
      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
      className="flex h-full min-h-0 flex-1 flex-col"
    >
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <div className="mono-tag">mapa autoral V4</div>
          <h2 className="mt-1 font-display text-[20px] font-semibold">Contexto autoral completo</h2>
        </div>
        <PeButton variant="outline" onClick={onClose}>
          Voltar a entrevista
        </PeButton>
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-5 xl:grid-cols-12">
        <div className="space-y-4 xl:col-span-5">
          <div className="panel p-5">
            <div className="font-display text-[28px] font-semibold">
              <AnimatedNumber value={coveredTotal} />
              <span className="text-[16px] text-ink-faint"> / {totalAxes} dimensoes observadas</span>
            </div>
            {editorialFeedback && (
              <p className="mt-4 text-[14px] leading-relaxed text-ink-dim">{editorialFeedback}</p>
            )}
            <div className="mt-4 h-2 overflow-hidden rounded-full bg-surface-2">
              <motion.div
                className="h-full rounded-full bg-flux"
                animate={{ width: `${Math.min(100, percent)}%` }}
                transition={spring}
              />
            </div>
          </div>
          <AuthorialMap dimensions={dimensions} expanded />
        </div>

        <div className="min-h-0 overflow-y-auto xl:col-span-7">
          <AxisDetailPanel
            dimensions={dimensions}
            selectedDimensionId={selectedDimensionId}
            onSelect={setSelectedId}
          />
        </div>
      </div>
    </motion.div>
  );
}
