import { motion } from "motion/react";
import { ActivityGlyph } from "../ui";

const STEPS = [
  { id: "send", label: "Enviando respostas" },
  { id: "wait", label: "Aguardando avaliação" },
  { id: "coverage", label: "Atualizando cobertura" },
] as const;

export function AnalyzingState({
  roundNumber,
  answerCount,
  phase,
  busy,
}: {
  roundNumber: number;
  answerCount: number;
  phase: string;
  busy: boolean;
}) {
  const activeStep =
    phase === "interviewing" && busy ? 1 : busy ? 0 : 2;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-1 flex-col items-center justify-center py-16 text-center"
    >
      <ActivityGlyph kind="analisando" />
      <h2 className="mt-6 font-display text-[22px] font-semibold">
        Analisando rodada {String(roundNumber).padStart(2, "0")}
      </h2>
      <p className="mt-2 font-mono text-[12px] text-ink-faint">
        {answerCount} respostas recebidas
      </p>

      <div className="relative mt-8 h-1 w-full max-w-sm overflow-hidden rounded-full bg-surface-2">
        <motion.div
          className="absolute inset-y-0 w-1/2 rounded-full bg-[color-mix(in_oklab,var(--flux)_70%,transparent)]"
          animate={{ x: ["-120%", "240%"] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        />
        <motion.div
          className="absolute inset-0 rounded-full bg-[var(--flux)]"
          animate={{ opacity: [0.05, 0.18, 0.05] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>

      <ul className="mt-10 w-full max-w-sm space-y-3">
        {STEPS.map((step, i) => {
          const done = i < activeStep;
          const active = i === activeStep;
          return (
            <motion.li
              key={step.id}
              animate={{
                opacity: done || active ? 1 : 0.35,
                x: active ? [0, 3, 0] : 0,
              }}
              transition={{
                duration: active ? 1.1 : 0.25,
                repeat: active ? Infinity : 0,
                ease: "easeInOut",
              }}
              className="flex items-center gap-3 text-left"
            >
              <motion.span
                className="grid h-5 w-5 place-items-center rounded-full border font-mono text-[9px]"
                animate={
                  active
                    ? {
                        boxShadow: [
                          "0 0 0 0 color-mix(in oklab, var(--flux) 22%, transparent)",
                          "0 0 0 7px color-mix(in oklab, var(--flux) 0%, transparent)",
                        ],
                      }
                    : undefined
                }
                transition={active ? { duration: 1.2, repeat: Infinity, ease: "easeOut" } : undefined}
                style={
                  done || active
                    ? {
                        borderColor: "color-mix(in oklab, var(--flux) 50%, transparent)",
                        color: "var(--flux)",
                      }
                    : undefined
                }
              >
                {done ? "✓" : active ? "●" : "○"}
              </motion.span>
              <span className="text-[13px] text-ink-dim">{step.label}</span>
            </motion.li>
          );
        })}
      </ul>
    </motion.div>
  );
}
