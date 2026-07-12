import { motion } from "motion/react";
import type { Question } from "@/lib/pe-types";
import { cn } from "@/lib/utils";
import { useMotionSafe } from "./motion";

type ItemState = "answered" | "current" | "pending";

function itemState(index: number, currentIndex: number, answer: string): ItemState {
  if (index === currentIndex) return "current";
  if (answer.trim().length > 0) return "answered";
  return "pending";
}

export function RoundNavigator({
  round,
  currentIndex,
  roundNumber,
  onSelect,
}: {
  round: Question[];
  currentIndex: number;
  roundNumber: number;
  onSelect: (index: number) => void;
}) {
  const { spring } = useMotionSafe();
  const answered = round.filter((q) => q.answer.trim().length > 0).length;

  return (
    <div className="panel p-4">
      <div className="mono-tag">rodada {String(roundNumber).padStart(2, "0")}</div>
      <ul className="relative mt-3 space-y-0.5">
        {round.map((q, i) => {
          const state = itemState(i, currentIndex, q.answer);
          return (
            <li key={q.id}>
              <button
                type="button"
                onClick={() => onSelect(i)}
                className={cn(
                  "relative flex w-full items-center gap-2.5 rounded-md px-2 py-1.5 text-left transition-colors",
                  state === "current" ? "text-ink" : "text-ink-dim hover:bg-surface-2 hover:text-ink",
                )}
              >
                {state === "current" && (
                  <motion.span
                    layoutId="round-nav-indicator"
                    className="absolute inset-0 rounded-md border border-[color-mix(in_oklab,var(--flux)_40%,transparent)] bg-[color-mix(in_oklab,var(--flux)_10%,transparent)]"
                    transition={spring}
                  />
                )}
                <span className="relative z-10 w-5 shrink-0 font-mono text-[10px] text-ink-faint">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="relative z-10 flex-1 truncate text-[12px]">{q.axis}</span>
                <motion.span
                  className="relative z-10 w-4 shrink-0 text-center font-mono text-[11px]"
                  animate={{
                    color:
                      state === "answered"
                        ? "var(--flux)"
                        : state === "current"
                          ? "var(--flux)"
                          : "var(--ink-faint)",
                  }}
                  transition={spring}
                >
                  {state === "answered" ? "✓" : state === "current" ? "●" : "○"}
                </motion.span>
              </button>
            </li>
          );
        })}
      </ul>
      <p className="mt-3 font-mono text-[10px] text-ink-faint">
        {answered} / {round.length} respondidas
      </p>
    </div>
  );
}
