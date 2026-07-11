import { AnimatePresence, motion } from "motion/react";
import { useEffect, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function ModalShell({
  children,
  onClose,
  testId,
  maxWidth = "max-w-md",
  closeOnBackdrop = true,
}: {
  children: ReactNode;
  onClose: () => void;
  testId?: string;
  maxWidth?: string;
  closeOnBackdrop?: boolean;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && closeOnBackdrop) onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, closeOnBackdrop]);

  return (
    <>
      <motion.div
        className="fixed inset-0 z-50 bg-[oklch(0.06_0.01_265/0.62)] backdrop-blur-[3px]"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
        onClick={closeOnBackdrop ? onClose : undefined}
      />
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.96, y: 16 }}
        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
        className={cn(
          "fixed left-1/2 top-1/2 z-50 -translate-x-1/2 -translate-y-1/2 panel flex max-h-[85vh] w-full flex-col overflow-hidden",
          maxWidth,
        )}
        data-testid={testId}
      >
        {children}
      </motion.div>
    </>
  );
}

export function ModalHeader({
  eyebrow,
  title,
  onClose,
}: {
  eyebrow?: string;
  title: string;
  onClose: () => void;
}) {
  return (
    <div className="flex items-start justify-between border-b border-hairline px-5 py-4">
      <div>
        {eyebrow && <div className="mono-tag">{eyebrow}</div>}
        <h2 className="mt-0.5 font-display text-[17px] font-semibold text-ink">{title}</h2>
      </div>
      <button
        type="button"
        onClick={onClose}
        className="grid h-7 w-7 place-items-center rounded-md text-ink-faint hover:bg-surface-2 hover:text-ink"
        aria-label="Fechar"
      >
        ✕
      </button>
    </div>
  );
}

export function ModalFooter({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center justify-end gap-2 border-t border-hairline bg-surface-2/40 px-5 py-3.5">
      {children}
    </div>
  );
}
