import { useState, useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "motion/react";
import { usePE } from "@/lib/pe-store";
import { frontierBlockId, isBlockUnlocked } from "@/lib/mappers/editorial";
import { PeButton } from "../ui";
import { FormattedText } from "../FormattedText";
import { StageHeader, StageScroll } from "./common";
import type { EditorialBlock, EditorialDraftOption } from "@/lib/pe-types";

interface ChosenDraft {
  block: EditorialBlock;
  option: EditorialDraftOption;
}

function buildChosenDrafts(
  blocks: EditorialBlock[],
  draftByBlock: Record<string, { options?: EditorialDraftOption[]; selected_option_id?: string | null }>,
): ChosenDraft[] {
  return blocks
    .filter((b) => draftByBlock[b.id]?.selected_option_id)
    .map((b) => {
      const entry = draftByBlock[b.id];
      const opt = entry.options?.find((o) => o.id === entry.selected_option_id);
      return { block: b, option: opt! };
    })
    .filter((d) => d.option);
}

export function DraftsStage() {
  const {
    storyboardBlocks,
    draftByBlock,
    editorialStatus,
    generateBlockDrafts,
    retryBlockDraft,
    selectBlockDraft,
    goto,
    busy,
  } = usePE();

  const [activeBlockId, setActiveBlockId] = useState<string | null>(null);
  const activeId = activeBlockId ?? storyboardBlocks[0]?.id ?? null;
  const frontierId = frontierBlockId(storyboardBlocks, draftByBlock);
  const canGenerate = Boolean(activeId && activeId === frontierId);
  const entry = activeId ? draftByBlock[activeId] : undefined;
  const options = entry?.options ?? [];

  const [showReader, setShowReader] = useState(false);
  const [readerIndex, setReaderIndex] = useState(0);
  const chosenDrafts = buildChosenDrafts(storyboardBlocks, draftByBlock);

  const openReader = useCallback(() => {
    setReaderIndex(0);
    setShowReader(true);
  }, []);

  const closeReader = useCallback(() => setShowReader(false), []);

  const goPrev = useCallback(() => setReaderIndex((i) => Math.max(0, i - 1)), []);
  const goNext = useCallback(() => setReaderIndex((i) => Math.min(chosenDrafts.length - 1, i + 1)), [chosenDrafts.length]);

  useEffect(() => {
    if (!showReader) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") closeReader();
      if (e.key === "ArrowLeft") goPrev();
      if (e.key === "ArrowRight") goNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [showReader, closeReader, goPrev, goNext]);

  const handleSelect = async (optionId: string) => {
    if (!activeId) return;
    const idx = storyboardBlocks.findIndex((b) => b.id === activeId);
    await selectBlockDraft(activeId, optionId);
    if (idx >= 0 && idx < storyboardBlocks.length - 1) {
      const nextBlockId = storyboardBlocks[idx + 1].id;
      setActiveBlockId(nextBlockId);
      await generateBlockDrafts(nextBlockId);
    }
  };

  const current = chosenDrafts[readerIndex];

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 05 · rascunhos por bloco"
        title="Rascunhador de blocos"
        desc="Gere e selecione um rascunho por bloco, em ordem. Cada bloco usa o texto já escolhido nos anteriores."
        aside={
          activeId && (
            <PeButton
              variant="flux"
              onClick={() => generateBlockDrafts(activeId)}
              loading={busy}
              disabled={!canGenerate}
            >
              Gerar bloco atual
            </PeButton>
          )
        }
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {storyboardBlocks.map((block, index) => {
          const sel = draftByBlock[block.id]?.selected_option_id;
          const unlocked = isBlockUnlocked(index, storyboardBlocks, draftByBlock);
          return (
            <button
              key={block.id}
              type="button"
              disabled={!unlocked}
              onClick={() => unlocked && setActiveBlockId(block.id)}
              className={`rounded-md border px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40 ${activeId === block.id ? "border-[var(--flux)] bg-[color-mix(in_oklab,var(--flux)_12%,transparent)]" : "border-hairline"}`}
              data-testid={`draft-block-tab-${block.order}`}
            >
              {block.role} {sel ? "✓" : ""}
            </button>
          );
        })}
      </div>

      <div className="grid gap-3 md:grid-cols-3" data-testid="draft-options">
        {options.map((opt, i) => (
          <div key={opt.id} className="panel flex flex-col p-4" data-testid={`draft-option-${i + 1}`}>
            <div className="mono-tag">{opt.persona_name}</div>
            <div className="mt-1 text-sm font-medium">{opt.approach.title}</div>
            <p className="mt-1 text-xs text-ink-faint">{opt.approach.description}</p>
            <p className="mt-3 flex-1 text-[13px] leading-relaxed text-ink-dim">
              <FormattedText text={opt.content || (opt.status === "failed" ? `Erro: ${opt.error}` : "…")} />
            </p>
            <div className="mt-3 flex gap-2">
              <PeButton
                variant={entry?.selected_option_id === opt.id ? "flux" : "outline"}
                disabled={opt.status !== "available"}
                onClick={() => handleSelect(opt.id)}
              >
                Selecionar
              </PeButton>
              {opt.status === "failed" && activeId && canGenerate && (
                <PeButton variant="ghost" onClick={() => retryBlockDraft(activeId, opt.id)} loading={busy}>
                  Retry
                </PeButton>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-6 flex justify-end">
        <PeButton
          variant="flux"
          disabled={!editorialStatus.can_compose}
          onClick={() => goto("composition")}
          data-testid="goto-composition"
        >
          Composição →
        </PeButton>
      </div>

      {chosenDrafts.length > 0 && (
        <motion.button
          type="button"
          onClick={openReader}
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0, opacity: 0 }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full px-4 py-3 text-sm font-medium shadow-lg"
          style={{
            background: "linear-gradient(180deg, color-mix(in oklab, var(--flux) 36%, var(--surface-2)), color-mix(in oklab, var(--flux) 18%, var(--surface)))",
            border: "1px solid color-mix(in oklab, var(--flux) 50%, transparent)",
            color: "var(--ink)",
          }}
          data-testid="reader-fab"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
          </svg>
          {chosenDrafts.length} {chosenDrafts.length === 1 ? "rascunho" : "rascunhos"}
        </motion.button>
      )}

      <AnimatePresence>
        {showReader && current && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-6"
            style={{ background: "color-mix(in oklab, var(--bg) 85%, transparent)", backdropFilter: "blur(8px)" }}
            onClick={closeReader}
            data-testid="reader-overlay"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              transition={{ duration: 0.25, ease: [0.22, 1, 0.36, 1] }}
              className="panel relative flex max-h-[80vh] w-full max-w-2xl flex-col overflow-hidden"
              onClick={(e) => e.stopPropagation()}
            >
              <button
                type="button"
                onClick={closeReader}
                className="absolute right-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-md text-ink-dim transition-colors hover:bg-surface-2 hover:text-ink"
                data-testid="reader-close"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>

              <div className="flex items-center justify-between border-b border-hairline px-6 py-3">
                <div className="flex items-center gap-3">
                  <span className="eyebrow">{current.block.role}</span>
                  <span className="mono-tag">{current.option.persona_name}</span>
                </div>
                <span className="text-xs text-ink-faint">
                  {readerIndex + 1} de {chosenDrafts.length}
                </span>
              </div>

              <div className="flex-1 overflow-y-auto px-6 py-5">
                <div className="text-sm font-medium text-ink">{current.option.approach.title}</div>
                <p className="mt-1 text-xs text-ink-faint">{current.option.approach.description}</p>
                <p className="mt-4 text-[14px] leading-relaxed text-ink-dim">
                  <FormattedText text={current.option.content} />
                </p>
              </div>

              <div className="flex items-center justify-between border-t border-hairline px-6 py-3">
                <PeButton
                  variant="outline"
                  onClick={goPrev}
                  disabled={readerIndex === 0}
                  data-testid="reader-prev"
                >
                  ← Anterior
                </PeButton>
                <div className="flex gap-1">
                  {chosenDrafts.map((_, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => setReaderIndex(i)}
                      className={`h-1.5 rounded-full transition-all ${i === readerIndex ? "w-6 bg-[var(--flux)]" : "w-1.5 bg-hairline hover:bg-hairline-strong"}`}
                    />
                  ))}
                </div>
                <PeButton
                  variant="outline"
                  onClick={goNext}
                  disabled={readerIndex === chosenDrafts.length - 1}
                  data-testid="reader-next"
                >
                  Próximo →
                </PeButton>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </StageScroll>
  );
}
