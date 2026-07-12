import { motion } from "motion/react";
import { PeButton } from "../ui";

export function CurrentReadMoment({
  text,
  onContinue,
}: {
  text: string;
  onContinue: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.22, 1, 0.36, 1] }}
      className="flex flex-1 flex-col items-center justify-center py-12 text-center"
    >
      <div className="mono-tag">leitura atual</div>
      <blockquote className="mt-6 max-w-2xl font-display text-[22px] font-medium leading-relaxed tracking-tight text-ink xl:text-[26px]">
        {text}
      </blockquote>
      <p className="mt-4 max-w-md text-[13px] text-ink-faint">
        O que o sistema já entende sobre você nesta entrevista.
      </p>
      <PeButton variant="flux" className="mt-10" onClick={onContinue}>
        Continuar →
      </PeButton>
    </motion.div>
  );
}
