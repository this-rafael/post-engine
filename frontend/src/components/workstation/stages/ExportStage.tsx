import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { usePE } from "@/lib/pe-store";
import { PeButton } from "../ui";
import { StageHeader, StageScroll } from "./common";

export function ExportStage() {
  const { exportState, doExport, goto, exportPath, isTrilhaVisual, evaluation } = usePE();
  const canExport = Boolean(evaluation?.length);

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 08 · artefatos"
        title="Exportação"
        desc="A etapa final materializa o conteúdo editado em artefatos utilizáveis fora do Post Engine."
        aside={
          <PeButton variant="ghost" onClick={() => goto("evaluation")}>
            ← Voltar à avaliação
          </PeButton>
        }
      />

      {!canExport && (
        <div className="mb-4 panel p-4 text-[12.5px] text-ink-faint">
          Execute a avaliação antes de exportar os artefatos finais.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <ArtifactCard
          title="Markdown"
          kind="markdown"
          state={exportState.markdown}
          onRun={() => doExport("markdown")}
          fileName={exportPath ? exportPath.split("/").pop() ?? "export.md" : "export.md"}
          dest={exportPath || "exports/"}
          note="Conteúdo editorial final exportado como arquivo Markdown."
          disabled={!canExport}
        />
        {isTrilhaVisual && (
          <ArtifactCard
            title="SlideMark"
            kind="slidemark"
            state={exportState.slidemark}
            onRun={() => doExport("slidemark")}
            fileName="slidemark-v1.json"
            dest={exportPath ? exportPath.replace(/\.md$/, ".json") : "exports/slidemark-v1.json"}
            note="Uma LLM converte o conteúdo final em um documento SlideMark v1, pronto para renderização em slides."
            transform
            disabled={!canExport}
          />
        )}
      </div>
    </StageScroll>
  );
}

function ArtifactCard({
  title,
  kind,
  state,
  onRun,
  fileName,
  dest,
  note,
  transform,
  disabled,
}: {
  title: string;
  kind: "markdown" | "slidemark";
  state: "idle" | "running" | "done";
  onRun: () => void;
  fileName: string;
  dest: string;
  note: string;
  transform?: boolean;
  disabled?: boolean;
}) {
  const running = state === "running";
  const done = state === "done";
  return (
    <motion.div layout className="panel relative flex flex-col overflow-hidden p-5">
      <div
        className="pointer-events-none absolute inset-0 transition-opacity"
        style={{
          opacity: running ? 0.4 : 0,
          background: "radial-gradient(120% 80% at 50% 0%, color-mix(in oklab, var(--flux) 30%, transparent), transparent)",
        }}
      />
      <div className="relative flex items-center justify-between">
        <div>
          <div className="mono-tag">{transform ? "transformação de artefato" : "artefato"}</div>
          <div className="font-display text-[18px] font-semibold">{title}</div>
        </div>
        <span
          className="grid h-9 w-9 place-items-center rounded-lg border border-hairline font-mono text-[11px]"
          style={done ? { borderColor: "color-mix(in oklab, var(--ok) 50%, transparent)", color: "var(--ok)" } : undefined}
        >
          {done ? "✓" : kind === "markdown" ? "md" : "{}"}
        </span>
      </div>
      <p className="relative mt-2 text-[12.5px] leading-relaxed text-ink-faint">{note}</p>
      <div className="relative mt-4 space-y-2 inset-panel p-3">
        <Row k="nome" v={fileName} />
        <Row k="destino" v={dest} copyable />
        <Row
          k="estado"
          v={running ? "exportando…" : done ? "concluído" : "pronto"}
          accent={done ? "var(--ok)" : running ? "var(--flux)" : undefined}
        />
      </div>
      <div className="relative mt-5">
        <PeButton variant="flux" className="w-full" onClick={onRun} loading={running} disabled={disabled || running}>
          {done ? "Exportar novamente" : `Exportar ${title}`}
        </PeButton>
      </div>
    </motion.div>
  );
}

function Row({ k, v, accent, copyable }: { k: string; v: string; accent?: string; copyable?: boolean }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(v);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="mono-tag !text-[9px]">{k}</span>
      <div className="flex items-center gap-1.5">
        <span className="truncate font-mono text-[11px]" style={accent ? { color: accent } : undefined}>
          {v}
        </span>
        {copyable && (
          <button
            onClick={handleCopy}
            className="shrink-0 rounded border border-hairline px-1.5 py-0.5 font-mono text-[10px] text-ink-faint transition-colors hover:border-ink-faint hover:text-ink"
            title="Copiar"
          >
            {copied ? "✓" : "⎘"}
          </button>
        )}
      </div>
    </div>
  );
}
