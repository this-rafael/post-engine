import { motion } from "motion/react";
import type { ReactNode } from "react";
import { Eyebrow } from "../ui";

export function StageHeader({
  eyebrow,
  title,
  desc,
  aside,
}: {
  eyebrow: string;
  title: string;
  desc: string;
  aside?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-4 pb-4 sm:flex-row sm:items-end sm:justify-between sm:gap-6 sm:pb-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="min-w-0 max-w-2xl"
      >
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1 className="font-display text-[22px] font-semibold leading-tight tracking-tight sm:text-[26px]">
          {title}
        </h1>
        <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-faint">{desc}</p>
      </motion.div>
      {aside && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.08 }}
          className="shrink-0"
        >
          {aside}
        </motion.div>
      )}
    </div>
  );
}

export function StageScroll({ children }: { children: ReactNode }) {
  return (
    <div className="h-full min-h-0 overflow-y-auto overscroll-contain px-4 py-5 sm:px-8 sm:py-7 [scrollbar-gutter:stable]">
      <div className="mx-auto max-w-5xl pb-24">{children}</div>
    </div>
  );
}
