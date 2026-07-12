import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { usePE } from "@/lib/pe-store";
import type { ImageSuggestion, Segment } from "@/lib/pe-types";
import { PeButton } from "../ui";
import { FormattedText } from "../FormattedText";
import { StageHeader, StageScroll } from "./common";

export function SegmentationStage() {
  const { segments, segment, requestAdjust, applyAdjust, discardAdjust, goto, focusSegment, busy } =
    usePE();
  const reseg = async () => {
    await segment();
  };

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 06 · estrutura editorial"
        title="Segmentar e reorganizar"
        desc="O conteúdo é dividido em partes lógicas. Selecione um segmento e peça um ajuste — a versão antiga permanece como camada ghost enquanto a nova assume por morph."
        aside={
          <PeButton variant="outline" onClick={reseg} loading={busy}>
            Re-segmentar
          </PeButton>
        }
      />

      {segments.length === 0 ? (
        <div className="panel grid min-h-[300px] place-items-center p-8">
          <p className="mono-tag">nenhum segmento — execute a segmentação</p>
        </div>
      ) : (
        <div className="space-y-3">
          <AnimatePresence mode="popLayout">
            {segments.map((seg, i) => (
              <SegmentRow
                key={seg.id}
                seg={seg}
                order={i}
                highlight={focusSegment === seg.index}
                onRequest={(r) => requestAdjust(seg.index, r)}
                onApply={() => applyAdjust(seg.index)}
                onDiscard={() => discardAdjust(seg.index)}
              />
            ))}
          </AnimatePresence>
        </div>
      )}

      {segments.length > 0 && (
        <div className="mt-6 flex justify-end">
          <PeButton variant="flux" onClick={() => goto("evaluation")}>
            Avaliar post →
          </PeButton>
        </div>
      )}
    </StageScroll>
  );
}

function SegmentRow({
  seg,
  order,
  highlight,
  onRequest,
  onApply,
  onDiscard,
}: {
  seg: Segment;
  order: number;
  highlight: boolean;
  onRequest: (r: string) => Promise<void>;
  onApply: () => void;
  onDiscard: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [req, setReq] = useState("");
  const [busy, setBusy] = useState(false);

  const send = async () => {
    if (!req.trim()) return;
    setBusy(true);
    await onRequest(req);
    setBusy(false);
  };

  return (
    <motion.div
      layout
      layoutId={seg.id}
      initial={{ opacity: 0, y: 20, scale: 0.98 }}
      animate={{
        opacity: 1,
        y: 0,
        scale: 1,
        boxShadow: highlight
          ? "0 0 0 1px color-mix(in oklab, var(--flux) 55%, transparent), 0 0 30px -6px var(--flux)"
          : "0 20px 50px -30px oklch(0 0 0 / 0.9)",
      }}
      exit={{ opacity: 0, scale: 0.96 }}
      transition={{ type: "spring", stiffness: 240, damping: 28 }}
      className="panel relative overflow-hidden p-4"
    >
      <div className="flex items-start gap-4">
        <div className="flex flex-col items-center gap-1 pt-0.5">
          <span
            className="grid h-7 w-7 place-items-center rounded-md border border-hairline font-mono text-[11px] flux-text"
          >
            {String(order + 1).padStart(2, "0")}
          </span>
          <span className="mono-tag !text-[8px]">segmento</span>
        </div>

        <div className="min-w-0 flex-1">
          <div className="relative">
            <AnimatePresence>
              {seg.ghost && (
                <motion.p
                  key="ghost"
                  initial={{ opacity: 0.5 }}
                  animate={{ opacity: 0, y: -8, filter: "blur(4px)" }}
                  transition={{ duration: 1.1 }}
                  className="pointer-events-none absolute inset-0 text-[14px] leading-relaxed text-ink-faint"
                >
                  <FormattedText text={seg.ghost} />
                </motion.p>
              )}
            </AnimatePresence>
            <motion.p
              layout
              initial={seg.ghost ? { opacity: 0, y: 8, filter: "blur(4px)" } : false}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              transition={{ duration: 0.8, delay: seg.ghost ? 0.2 : 0 }}
              className="text-[14px] leading-relaxed text-ink-dim"
            >
              <FormattedText text={seg.text} />
            </motion.p>

            {seg.imageSuggestion && (
              <ImageSuggestionPanel suggestion={seg.imageSuggestion} />
            )}
          </div>

          <button
            onClick={() => setOpen((o) => !o)}
            className="mt-2.5 font-mono text-[10px] uppercase tracking-wide text-ink-faint hover:text-ink-dim"
          >
            {open ? "fechar ajuste" : "ajustar com IA ↓"}
          </button>

          <AnimatePresence>
            {open && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="mt-3 space-y-2">
                  <textarea
                    value={req}
                    onChange={(e) => setReq(e.target.value)}
                    rows={2}
                    placeholder="Ex: deixe essa crítica mais concreta e use um exemplo de deploy."
                    className="field field-focus w-full resize-none px-3 py-2 text-[13px] outline-none"
                  />
                  <div className="flex gap-2">
                    <PeButton variant="flux" onClick={send} loading={busy}>
                      Gerar nova versão
                    </PeButton>
                    {seg.pendingVersion && (
                      <>
                        <PeButton variant="outline" onClick={onApply}>
                          Aplicar versão
                        </PeButton>
                        <PeButton variant="ghost" onClick={onDiscard}>
                          Descartar
                        </PeButton>
                      </>
                    )}
                  </div>

                  <AnimatePresence>
                    {seg.pendingVersion && (
                      <motion.div
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="inset-panel border-l-2 p-3"
                        style={{ borderLeftColor: "var(--flux)" }}
                      >
                        <div className="mono-tag mb-1">nova versão proposta</div>
                        <p className="text-[13px] leading-relaxed text-ink-dim">
                          <FormattedText text={seg.pendingVersion} />
                        </p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}

function ImageSuggestionPanel({ suggestion }: { suggestion: ImageSuggestion }) {
  const isLink = suggestion.modo === "link" && suggestion.url;

  return (
    <div
      className="mt-3 rounded-md border border-hairline bg-[color-mix(in_oklab,var(--flux)_6%,transparent)] px-3 py-2.5"
    >
      <div className="mono-tag mb-1.5">
        {isLink ? "imagem sugerida · link" : "imagem sugerida · descrição"}
      </div>
      <p className="text-[12.5px] leading-relaxed text-ink-dim">{suggestion.descricao}</p>
      {isLink && (
        <a
          href={suggestion.url}
          target="_blank"
          rel="noreferrer"
          className="mt-1.5 inline-block font-mono text-[11px] text-[var(--flux)] underline-offset-2 hover:underline"
        >
          {suggestion.url}
        </a>
      )}
      {suggestion.fonte && (
        <div className="mt-1 font-mono text-[10px] text-ink-faint">fonte · {suggestion.fonte}</div>
      )}
    </div>
  );
}
