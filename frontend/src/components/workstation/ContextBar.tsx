import { AnimatePresence, motion } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { usePE } from "@/lib/pe-store";
import type { StageId } from "@/lib/pe-types";
import { PeButton } from "./ui";

const STAGE_LABELS: Record<StageId, string> = {
  agents: "Agentes",
  entry: "Entrada",
  interview: "Entrevista",
  briefing: "Briefing",
  storyboard: "Storyboard",
  drafts: "Rascunhos",
  composition: "Composição",
  prompt: "Prompt",
  execution: "Execução",
  segmentation: "Segmentação",
  evaluation: "Avaliação",
  export: "Exportação",
};

function compactPersona(value: string) {
  return value.replace(/^Persona ativa:\s*/i, "").trim() || "—";
}

export function ContextBar({
  appearance,
  onToggleAppearance,
  onOpenDev,
  onOpenObservatory,
  onOpenRail,
}: {
  appearance: "dark" | "light";
  onToggleAppearance: () => void;
  onOpenDev: () => void;
  onOpenObservatory: () => void;
  onOpenRail?: () => void;
}) {
  const { session, stage, saveSession, reload, busy } = usePE();

  return (
    <header className="shrink-0 border-b border-hairline px-3 py-2.5 sm:px-5">
      <div className="flex min-w-0 items-center gap-2 sm:gap-5">
        {onOpenRail && (
          <IconButton
            onClick={onOpenRail}
            title="Etapas do pipeline"
            aria-label="Abrir menu de etapas"
          >
            <span className="font-mono text-[14px]" aria-hidden>
              ≡
            </span>
          </IconButton>
        )}
        <SessionContext
          session={session}
          stage={stage}
          busy={busy}
        />
        <div className="ml-auto flex shrink-0 items-center gap-1.5">
          <ToolbarDivider />
          <ThemeToggle appearance={appearance} onToggle={onToggleAppearance} />
          <ResetButton />
          <IconButton
            onClick={onOpenObservatory}
            title="Prompt Pipeline Observatory"
            aria-label="Abrir Prompt Pipeline Observatory"
          >
            <span className="font-mono text-[13px]">◈</span>
          </IconButton>
          <IconButton
            onClick={onOpenDev}
            title="Inspector (⌘K)"
            aria-label="Abrir inspector"
          >
            <InspectorIcon />
          </IconButton>
          <ToolbarDivider />
          <PeButton
            variant="ghost"
            onClick={() => reload()}
            disabled={busy}
            icon={<ReloadIcon />}
            className="!px-2.5 !text-[11px] max-sm:hidden"
          >
            <span className="hidden lg:inline">Recalcular</span>
          </PeButton>
          <PeButton
            variant="outline"
            onClick={() => saveSession()}
            disabled={busy}
            loading={busy}
            className="!px-3 !text-[11px]"
          >
            Salvar
          </PeButton>
        </div>
      </div>
    </header>
  );
}

function SessionContext({
  session,
  stage,
  busy,
}: {
  session: {
    theme: string;
    persona: string;
    platform: string;
    contentType: string;
    personality: string;
  };
  stage: StageId;
  busy: boolean;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  const theme = session.theme || "Sem tema definido";
  const persona = compactPersona(session.persona);
  const meta = [session.platform, session.contentType, session.personality].filter(Boolean);

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  const details = [
    { label: "Tema", value: session.theme },
    { label: "Persona", value: session.persona },
    { label: "Plataforma", value: session.platform },
    { label: "Formato", value: session.contentType },
    { label: "Tom", value: session.personality },
  ];

  return (
    <div ref={rootRef} className="relative min-w-0 flex-1">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="dialog"
        disabled={busy}
        className="group flex w-full min-w-0 items-start gap-3 rounded-lg px-1 py-0.5 text-left transition-colors hover:bg-surface-2/60 disabled:opacity-60"
      >
        <span
          className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
          style={{
            background: session.contentType ? "var(--flux)" : "var(--hairline-strong)",
            boxShadow: session.contentType
              ? "0 0 10px color-mix(in oklab, var(--flux) 55%, transparent)"
              : undefined,
          }}
        />
        <span className="min-w-0 flex-1">
          <span className="flex min-w-0 items-center gap-2">
            <span className="truncate font-display text-[14px] font-semibold tracking-tight text-ink">
              {theme}
            </span>
            <StageBadge stage={stage} />
          </span>
          <span className="mt-0.5 block truncate text-[11px] text-ink-faint">
            {persona}
            {meta.length > 0 && (
              <>
                <span className="mx-1.5 text-hairline-strong">·</span>
                {meta.join(" · ")}
              </>
            )}
          </span>
        </span>
        <ChevronIcon open={open} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            role="dialog"
            aria-label="Detalhes da sessão"
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
            className="absolute left-0 top-[calc(100%+6px)] z-50 w-[min(420px,calc(100vw-2.5rem))] panel !rounded-lg p-4"
          >
            <div className="mb-3 flex items-center justify-between gap-3">
              <span className="eyebrow">sessão ativa</span>
              {session.contentType && (
                <span className="inline-flex items-center gap-1.5 rounded-full border border-[color-mix(in_oklab,var(--flux)_35%,transparent)] bg-[color-mix(in_oklab,var(--flux)_10%,transparent)] px-2 py-0.5 text-[10px] font-medium flux-text">
                  regra · {session.contentType}
                </span>
              )}
            </div>
            <dl className="space-y-2.5">
              {details.map((item) => (
                <div key={item.label} className="grid grid-cols-[88px_1fr] gap-3 text-[12px]">
                  <dt className="mono-tag !text-[9px] pt-px">{item.label}</dt>
                  <dd className="font-medium leading-snug text-ink-dim">
                    {item.value || "—"}
                  </dd>
                </div>
              ))}
            </dl>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StageBadge({ stage }: { stage: StageId }) {
  return (
    <span className="mono-tag shrink-0 rounded-full border border-hairline bg-surface/70 px-2 py-0.5 !text-[9px]">
      {STAGE_LABELS[stage] ?? stage}
    </span>
  );
}

function ToolbarDivider() {
  return <span className="mx-0.5 hidden h-5 w-px bg-hairline sm:block" />;
}

function IconButton({
  children,
  title,
  className,
  ...props
}: {
  children: React.ReactNode;
  title: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      title={title}
      className={`grid h-8 w-8 place-items-center rounded-md border border-transparent text-ink-faint transition-colors hover:border-hairline hover:bg-surface-2 hover:text-ink ${className ?? ""}`}
      {...props}
    >
      {children}
    </button>
  );
}

function ThemeToggle({
  appearance,
  onToggle,
}: {
  appearance: "dark" | "light";
  onToggle: () => void;
}) {
  const isDark = appearance === "dark";
  return (
    <IconButton
      className="!border-hairline"
      onClick={onToggle}
      title={`Alternar para tema ${isDark ? "claro" : "escuro"}`}
      aria-label={`Alternar para tema ${isDark ? "claro" : "escuro"}`}
    >
      <span className="text-[13px]">{isDark ? "◐" : "◑"}</span>
    </IconButton>
  );
}

function ResetButton() {
  const { resetContext } = usePE();
  const [armed, setArmed] = useState(false);
  return (
    <div className="relative">
      <AnimatePresence>
        {armed && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.96 }}
            className="absolute right-0 top-11 z-50 w-64 panel !rounded-lg p-3.5"
          >
            <div className="text-[13px] font-medium">Resetar contexto da sessão</div>
            <p className="mt-1 text-[12px] leading-relaxed text-ink-faint">
              Isso apaga todo o contexto acumulado do fluxo. Não é reversível.
            </p>
            <div className="mt-3 flex justify-end gap-2">
              <PeButton variant="ghost" onClick={() => setArmed(false)}>
                Cancelar
              </PeButton>
              <PeButton
                variant="danger"
                onClick={() => {
                  resetContext();
                  setArmed(false);
                }}
              >
                Resetar
              </PeButton>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
      <IconButton
        onClick={() => setArmed((a) => !a)}
        title="Resetar contexto"
        aria-label="Resetar contexto"
        className="hover:border-[color-mix(in_oklab,var(--danger)_50%,transparent)] hover:text-[var(--danger)]"
      >
        <ResetIcon />
      </IconButton>
    </div>
  );
}

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      className={`mt-1 shrink-0 text-ink-faint transition-transform ${open ? "rotate-180" : ""}`}
    >
      <path d="M6 9l6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ReloadIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 12a9 9 0 1 0 9-9 9 9 0 0 0-6.7 3M3 4v5h5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function ResetIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M3 12a9 9 0 1 0 9-9 9 9 0 0 0-6.7 3M3 4v5h5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function InspectorIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M4 7h16M4 12h10M4 17h14" strokeLinecap="round" />
    </svg>
  );
}
