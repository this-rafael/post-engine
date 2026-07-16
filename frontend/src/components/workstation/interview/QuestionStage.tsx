import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import type { Question } from "@/lib/pe-types";
import { PeButton } from "../ui";
import { cn } from "@/lib/utils";
import { questionEnter, questionExit, questionInitial, useMotionSafe } from "./motion";

export function QuestionStage({
  question,
  index,
  total,
  groupLabel,
  onAnswer,
  onPrev,
  onNext,
  onReview,
  allAnswered,
  focusMode,
}: {
  question: Question;
  index: number;
  total: number;
  groupLabel?: string;
  onAnswer: (text: string) => void;
  onPrev: () => void;
  onNext: () => void;
  onReview: () => void;
  allAnswered: boolean;
  focusMode?: boolean;
}) {
  const { reduced, spring, duration, ease } = useMotionSafe();
  const [direction, setDirection] = useState(1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const max = window.innerWidth < 640
      ? (focusMode ? 320 : 220)
      : (focusMode ? 480 : 360);
    ta.style.height = "auto";
    ta.style.height = `${Math.min(ta.scrollHeight, max)}px`;
  }, [question.answer, focusMode]);

  const goNext = () => {
    setDirection(1);
    if (index === total - 1 && allAnswered) onReview();
    else onNext();
  };

  const goPrev = () => {
    setDirection(-1);
    onPrev();
  };

  return (
    <div className={cn("flex min-h-0 flex-1 flex-col", focusMode && "max-w-3xl mx-auto w-full")}>
      <AnimatePresence mode="popLayout" custom={direction}>
        <motion.div
          key={question.id}
          custom={direction}
          initial={questionInitial(reduced)}
          animate={questionEnter(reduced)}
          exit={questionExit(reduced)}
          transition={{ duration, ease }}
          className="flex flex-1 flex-col"
        >


          <motion.div layoutId="question-axis" className="mb-4 flex items-center gap-2">
            <span className="font-mono text-[11px] uppercase tracking-wide flux-text">
              {groupLabel || question.category || "entrevista"}
            </span>
            <span className="h-1 w-1 rounded-full bg-ink-faint" />
            <span className="font-mono text-[11px] text-ink-dim">
              {question.roundTitle || question.axis || "entrevista"}
            </span>
          </motion.div>

          <h2
            className={cn(
              "font-display font-semibold leading-snug tracking-tight text-ink",
              focusMode ? "text-[22px] sm:text-[28px]" : "text-[18px] sm:text-[22px] xl:text-[26px]",
            )}
          >
            {question.prompt}
          </h2>

          <textarea
            ref={textareaRef}
            value={question.answer}
            onChange={(e) => onAnswer(e.target.value)}
            placeholder="Sua experiência, opinião ou história real…"
            rows={focusMode ? 12 : 8}
            className={cn(
              "field mt-5 w-full resize-none px-3 py-3 outline-none placeholder:text-ink-faint/50 sm:mt-8 sm:px-4 sm:py-4",
              "text-[15px] leading-[1.75] field-focus",
              focusMode
                ? "min-h-[180px] sm:min-h-[280px]"
                : "min-h-[140px] max-h-[min(40dvh,360px)] sm:min-h-[200px] sm:max-h-[360px]",
            )}
          />

          <div className="mt-6 border-t border-hairline pt-5">
            <div className="mono-tag mb-2">por que estamos perguntando</div>
            <p className="text-[13px] leading-relaxed text-ink-faint italic">
              {question.rationale}
            </p>
          </div>
        </motion.div>
      </AnimatePresence>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-hairline pt-4 sm:mt-8 sm:gap-4 sm:pt-5">
        <PeButton
          variant="ghost"
          onClick={goPrev}
          disabled={index === 0}
          className="!px-2"
        >
          ← Anterior
        </PeButton>
        <PeButton variant="flux" onClick={goNext}>
          {index === total - 1 && allAnswered
            ? "Revisar rodada →"
            : "Próxima pergunta →"}
        </PeButton>
      </div>
    </div>
  );
}
