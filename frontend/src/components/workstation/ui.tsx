import { animate, useInView, useMotionValue, useTransform, motion, AnimatePresence } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";

export function AnimatedNumber({
  value,
  className,
  duration = 0.9,
}: {
  value: number;
  className?: string;
  duration?: number;
}) {
  const mv = useMotionValue(value);
  const rounded = useTransform(mv, (v) => Math.round(v).toString());
  const [text, setText] = useState(value.toString());
  useEffect(() => {
    const controls = animate(mv, value, {
      duration,
      ease: [0.22, 1, 0.36, 1],
    });
    const unsub = rounded.on("change", (v) => setText(v));
    return () => {
      controls.stop();
      unsub();
    };
  }, [value, duration, mv, rounded]);
  return <span className={cn("tabular-nums", className)}>{text}</span>;
}

type ButtonVariant = "flux" | "ghost" | "outline" | "danger";

export function PeButton({
  children,
  variant = "outline",
  className,
  loading,
  icon,
  ...props
}: {
  children: ReactNode;
  variant?: ButtonVariant;
  loading?: boolean;
  icon?: ReactNode;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base =
    "group relative inline-flex items-center justify-center gap-2 overflow-hidden rounded-md px-3.5 py-2 text-[13px] font-medium transition-all duration-200 disabled:opacity-40 disabled:pointer-events-none select-none";
  const styles: Record<ButtonVariant, string> = {
    flux:
      "text-ink [background:linear-gradient(180deg,color-mix(in_oklab,var(--flux)_36%,var(--surface-2)),color-mix(in_oklab,var(--flux)_18%,var(--surface)))] border border-[color-mix(in_oklab,var(--flux)_50%,transparent)] hover:flux-glow",
    ghost: "text-ink-dim hover:text-ink hover:bg-surface-2",
    outline:
      "text-ink-dim border border-hairline bg-surface/60 hover:text-ink hover:border-hairline-strong hover:bg-surface-2",
    danger:
      "text-ink border border-[color-mix(in_oklab,var(--danger)_45%,transparent)] bg-[color-mix(in_oklab,var(--danger)_16%,var(--surface))] hover:bg-[color-mix(in_oklab,var(--danger)_28%,var(--surface))]",
  };
  return (
    <motion.button
      whileTap={{ scale: 0.97 }}
      animate={loading ? { scale: [1, 1.015, 1] } : { scale: 1 }}
      transition={loading ? { duration: 1.4, repeat: Infinity, ease: "easeInOut" } : undefined}
      aria-busy={loading || undefined}
      data-loading={loading ? "true" : undefined}
      className={cn(base, styles[variant], loading && "shadow-[0_0_24px_color-mix(in_oklab,var(--flux)_18%,transparent)]", className)}
      {...(props as React.ComponentProps<typeof motion.button>)}
    >
      <AnimatePresence>
        {loading && (
          <motion.span
            aria-hidden
            className="pointer-events-none absolute inset-0 opacity-60"
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.6 }}
            exit={{ opacity: 0 }}
          >
            <motion.span
              className="absolute inset-y-0 -left-1/2 w-1/2 bg-gradient-to-r from-transparent via-white/16 to-transparent"
              animate={{ x: ["0%", "320%"] }}
              transition={{ duration: 1.25, repeat: Infinity, ease: "easeInOut" }}
            />
          </motion.span>
        )}
      </AnimatePresence>
      <span className="relative z-10 inline-flex items-center gap-2">
        {loading ? <LoadingDots /> : icon}
        {children}
      </span>
    </motion.button>
  );
}

function LoadingDots() {
  return (
    <span className="inline-flex h-3 w-4 items-center justify-between" aria-hidden>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1 w-1 rounded-full bg-current"
          animate={{ opacity: [0.35, 1, 0.35], y: [0, -2, 0] }}
          transition={{ duration: 0.75, repeat: Infinity, delay: i * 0.12, ease: "easeInOut" }}
        />
      ))}
    </span>
  );
}

export function Reveal({
  children,
  delay = 0,
  className,
  y = 14,
}: {
  children: ReactNode;
  delay?: number;
  className?: string;
  y?: number;
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: "-40px" });
  return (
    <motion.div
      ref={ref}
      className={className}
      initial={{ opacity: 0, y }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <div className="eyebrow mb-2">{children}</div>;
}

export function Field({
  label,
  value,
  onChange,
  placeholder,
  multiline,
  rows = 3,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  multiline?: boolean;
  rows?: number;
}) {
  const [focused, setFocused] = useState(false);
  const shared =
    "field w-full px-3 py-2.5 text-[14px] outline-none placeholder:text-ink-faint/60 resize-none";
  return (
    <label className="block">
      <div className="eyebrow mb-1.5 flex items-center gap-2">
        <span>{label}</span>
        <motion.span
          className="h-px flex-1"
          style={{ background: "var(--hairline)" }}
          animate={{ opacity: focused ? 1 : 0.4 }}
        />
      </div>
      {multiline ? (
        <textarea
          className={cn(shared, focused && "field-focus")}
          rows={rows}
          value={value}
          placeholder={placeholder}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          className={cn(shared, focused && "field-focus")}
          value={value}
          placeholder={placeholder}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}

/** Distinct per-phase activity glyph — never a generic spinner. */
export function ActivityGlyph({ kind }: { kind: string }) {
  return (
    <div className="relative h-12 w-12">
      <motion.span
        className="absolute inset-0 rounded-full border border-[color-mix(in_oklab,var(--flux)_35%,transparent)]"
        animate={{ scale: [0.82, 1.2, 0.82], opacity: [0.7, 0, 0.7] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
      />
      <motion.span
        className="absolute inset-2 rounded-full border border-[color-mix(in_oklab,var(--flux)_50%,transparent)] border-t-[var(--flux)]"
        animate={{ rotate: 360 }}
        transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
      />
      <motion.span
        className="absolute inset-[15px] rounded-[4px]"
        style={{ background: "color-mix(in oklab, var(--flux) 78%, transparent)" }}
        animate={{ rotate: [0, 90, 180, 270, 360], borderRadius: ["4px", "10px", "4px"] }}
        transition={{ duration: 2.2, repeat: Infinity, ease: "easeInOut" }}
      />
      <span className="sr-only">{kind}</span>
    </div>
  );
}

export function ErrorAccordion({
  title,
  details,
  variant = "danger",
}: {
  title: string;
  details: string;
  variant?: "danger" | "warning";
}) {
  const [open, setOpen] = useState(false);

  const colors = {
    danger: {
      border: "border-[color-mix(in_oklab,var(--danger)_45%,transparent)]",
      bg: "bg-[color-mix(in_oklab,var(--danger)_12%,var(--surface))]",
      hoverBg: "hover:bg-[color-mix(in_oklab,var(--danger)_18%,var(--surface))]",
      icon: "text-[var(--danger)]",
    },
    warning: {
      border: "border-[color-mix(in_oklab,var(--flux)_45%,transparent)]",
      bg: "bg-[color-mix(in_oklab,var(--flux)_12%,var(--surface))]",
      hoverBg: "hover:bg-[color-mix(in_oklab,var(--flux)_18%,var(--surface))]",
      icon: "text-[var(--flux)]",
    },
  };

  const c = colors[variant];

  return (
    <div className={cn("rounded-lg border overflow-hidden", c.border, c.bg)}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={cn(
          "flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-[12px] transition-colors",
          c.hoverBg,
        )}
      >
        <div className="flex items-center gap-2 min-w-0">
          <motion.span
            className={cn("shrink-0", c.icon)}
            animate={{ rotate: open ? 90 : 0 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
          >
            ▶
          </motion.span>
          <span className="text-ink-dim truncate">{title}</span>
        </div>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            <div className="border-t border-hairline px-4 py-3">
              <pre className="whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-ink-dim">
                {details}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
