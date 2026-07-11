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
    <div className="flex items-end justify-between gap-6 pb-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-2xl"
      >
        <Eyebrow>{eyebrow}</Eyebrow>
        <h1 className="font-display text-[26px] font-semibold leading-tight tracking-tight">
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
    <div className="h-full overflow-y-auto px-8 py-7 [scrollbar-gutter:stable]">
      <div className="mx-auto max-w-5xl pb-24">{children}</div>
    </div>
  );
}
