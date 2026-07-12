import { motion } from "motion/react";
import type { Question } from "@/lib/pe-types";
import { PeButton } from "../ui";

function excerpt(text: string, max = 80) {
  const t = text.trim();
  if (t.length <= max) return t;
  return `${t.slice(0, max)}…`;
}

export function RoundReview({
  round,
  roundNumber,
  onEdit,
  onBack,
  onAnalyze,
  loading,
}: {
  round: Question[];
  roundNumber: number;
  onEdit: (index: number) => void;
  onBack: () => void;
  onAnalyze: () => void;
  loading?: boolean;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-1 flex-col"
    >
      <div className="mono-tag">rodada {String(roundNumber).padStart(2, "0")} completa</div>
      <h2 className="mt-2 font-display text-[24px] font-semibold tracking-tight">
        {round.length} respostas capturadas
      </h2>
      <p className="mt-2 max-w-xl text-[14px] leading-relaxed text-ink-faint">
        Revise suas respostas antes de permitir que o motor da entrevista analise esta rodada.
      </p>

      <ul className="mt-8 space-y-3">
        {round.map((q, i) => (
          <motion.li
            key={q.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="panel p-4"
          >
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-[10px] text-ink-faint">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span className="h-1 w-1 rounded-full bg-ink-faint" />
                  <span className="mono-tag !text-[9px]">{q.axis}</span>
                </div>
                <p className="mt-2 text-[13.5px] italic leading-relaxed text-ink-dim">
                  &ldquo;{excerpt(q.answer, 120)}&rdquo;
                </p>
              </div>
              <button
                type="button"
                onClick={() => onEdit(i)}
                className="shrink-0 font-mono text-[10px] uppercase tracking-wide text-ink-faint hover:text-flux"
              >
                Editar →
              </button>
            </div>
          </motion.li>
        ))}
      </ul>

      <div className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-6">
        <PeButton variant="ghost" onClick={onBack}>
          ← Voltar às perguntas
        </PeButton>
        <PeButton variant="flux" onClick={onAnalyze} loading={loading}>
          Analisar respostas →
        </PeButton>
      </div>
    </motion.div>
  );
}
