import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";
import { usePE } from "@/lib/pe-store";
import type { WeakSegmentItem } from "@/lib/pe-types";
import { cn } from "@/lib/utils";
import { PeButton } from "./ui";
import { FormattedText } from "./FormattedText";
import { ModalFooter, ModalHeader, ModalShell } from "./ModalShell";

interface ReadjustAllModalProps {
  open: boolean;
  onClose: () => void;
}

export function ReadjustAllModal({ open, onClose }: ReadjustAllModalProps) {
  const {
    weakSegments,
    bulkRewrites,
    busy,
    requestBulkAdjust,
    applyBulkAdjust,
    applyAllBulkAdjust,
    discardBulkAdjust,
    reBulkAdjustItem,
  } = usePE();

  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [pedidos, setPedidos] = useState<Record<number, string>>({});
  const [editing, setEditing] = useState<Set<number>>(new Set());
  const [itemBusy, setItemBusy] = useState<number | null>(null);

  const hasPreviews = Object.keys(bulkRewrites).length > 0;
  const allPedidosFilled = weakSegments.length > 0
    && weakSegments.every((s) => pedidos[s.index]?.trim());

  useEffect(() => {
    if (!open) return;
    setExpanded(new Set());
    setPedidos({});
    setEditing(new Set());
  }, [open]);

  const toggleExpanded = (index: number) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const handleBulkAdjust = async () => {
    const ajustes = weakSegments.map((s) => ({
      index: s.index,
      pedido: pedidos[s.index]?.trim() ?? "",
    }));
    await requestBulkAdjust(ajustes);
  };

  const handleReedit = (index: number) => {
    setEditing((prev) => new Set(prev).add(index));
    setExpanded((prev) => new Set(prev).add(index));
  };

  const handleCancelReedit = (index: number) => {
    setEditing((prev) => {
      const next = new Set(prev);
      next.delete(index);
      return next;
    });
  };

  const handleReBulkItem = async (segment: WeakSegmentItem) => {
    const pedido = pedidos[segment.index]?.trim();
    if (!pedido) return;
    setItemBusy(segment.index);
    try {
      await reBulkAdjustItem(segment.index, pedido);
      setEditing((prev) => {
        const next = new Set(prev);
        next.delete(segment.index);
        return next;
      });
    } finally {
      setItemBusy(null);
    }
  };

  const handleDiscard = async () => {
    await discardBulkAdjust();
    onClose();
  };

  const previewCount = useMemo(
    () => weakSegments.filter((s) => bulkRewrites[s.index]).length,
    [bulkRewrites, weakSegments],
  );

  if (!open) return null;

  return (
    <AnimatePresence>
      <ModalShell onClose={onClose} testId="readjust-all-modal" maxWidth="max-w-2xl">
        <ModalHeader
          eyebrow="ajuste editorial em lote"
          title="Reajustar segmentos fracos"
          onClose={onClose}
        />

        <div className="flex-1 space-y-2 overflow-y-auto px-5 py-4">
          {weakSegments.map((segment) => (
            <WeakSegmentRow
              key={segment.index}
              segment={segment}
              open={expanded.has(segment.index)}
              pedido={pedidos[segment.index] ?? ""}
              preview={bulkRewrites[segment.index]}
              isEditing={editing.has(segment.index)}
              busy={busy || itemBusy === segment.index}
              onToggle={() => toggleExpanded(segment.index)}
              onPedidoChange={(value) => setPedidos((prev) => ({ ...prev, [segment.index]: value }))}
              onApply={() => applyBulkAdjust(segment.index)}
              onReedit={() => handleReedit(segment.index)}
              onCancelReedit={() => handleCancelReedit(segment.index)}
              onRegenerate={() => handleReBulkItem(segment)}
            />
          ))}
        </div>

        <ModalFooter>
          {hasPreviews ? (
            <>
              <PeButton variant="ghost" onClick={handleDiscard} disabled={busy}>
                Descartar
              </PeButton>
              <PeButton
                variant="flux"
                onClick={() => applyAllBulkAdjust()}
                loading={busy}
                disabled={previewCount === 0}
              >
                Aplicar todos ({previewCount})
              </PeButton>
            </>
          ) : (
            <>
              <PeButton variant="ghost" onClick={onClose} disabled={busy}>
                Cancelar
              </PeButton>
              <PeButton
                variant="flux"
                onClick={handleBulkAdjust}
                loading={busy}
                disabled={!allPedidosFilled}
              >
                Ajustar com IA
              </PeButton>
            </>
          )}
        </ModalFooter>
      </ModalShell>
    </AnimatePresence>
  );
}

function WeakSegmentRow({
  segment,
  open,
  pedido,
  preview,
  isEditing,
  busy,
  onToggle,
  onPedidoChange,
  onApply,
  onReedit,
  onCancelReedit,
  onRegenerate,
}: {
  segment: WeakSegmentItem;
  open: boolean;
  pedido: string;
  preview?: string;
  isEditing: boolean;
  busy: boolean;
  onToggle: () => void;
  onPedidoChange: (value: string) => void;
  onApply: () => void;
  onReedit: () => void;
  onCancelReedit: () => void;
  onRegenerate: () => void;
}) {
  const showForm = !preview || isEditing;

  return (
    <div className="panel overflow-hidden">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center gap-3 p-3.5 text-left"
      >
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-md border border-hairline font-mono text-[11px] flux-text">
          {String(segment.order).padStart(2, "0")}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[13px] font-medium">Segmento {String(segment.order).padStart(2, "0")}</div>
          <div className="truncate text-[12px] text-ink-faint">{segment.text}</div>
        </div>
        <span className={cn("font-mono text-[10px] text-ink-faint transition-transform", open && "rotate-90")}>
          ›
        </span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden border-t border-hairline"
          >
            <div className="space-y-3 p-3.5">
              <div>
                <div className="mono-tag mb-1">conteúdo atual</div>
                <p className="text-[12.5px] leading-relaxed text-ink-dim">
                  <FormattedText text={segment.text} />
                </p>
              </div>

              {segment.problem && (
                <div>
                  <div className="mono-tag mb-0.5">problema</div>
                  <p className="text-[12.5px] leading-relaxed text-ink-dim">
                    <FormattedText text={segment.problem} />
                  </p>
                </div>
              )}

              {segment.direction && (
                <div>
                  <div className="mono-tag mb-0.5">direção sugerida</div>
                  <p className="text-[12.5px] leading-relaxed text-ink-dim">
                    <FormattedText text={segment.direction} />
                  </p>
                </div>
              )}

              {showForm && (
                <div>
                  <div className="mono-tag mb-1">instrução de ajuste</div>
                  <textarea
                    value={pedido}
                    onChange={(e) => onPedidoChange(e.target.value)}
                    rows={3}
                    placeholder="Ex: torne esse trecho mais concreto com um exemplo de deploy."
                    className="field field-focus w-full resize-none px-3 py-2 text-[13px] outline-none"
                  />
                  {preview && isEditing && (
                    <div className="mt-2 flex gap-2">
                      <PeButton
                        variant="flux"
                        onClick={onRegenerate}
                        loading={busy}
                        disabled={!pedido.trim()}
                        className="!py-1.5 !text-[12px]"
                      >
                        Gerar nova versão
                      </PeButton>
                      <PeButton
                        variant="ghost"
                        onClick={onCancelReedit}
                        className="!py-1.5 !text-[12px]"
                      >
                        Cancelar
                      </PeButton>
                    </div>
                  )}
                </div>
              )}

              {preview && !isEditing && (
                <div
                  className="inset-panel border-l-2 p-3"
                  style={{ borderLeftColor: "var(--flux)" }}
                >
                  <div className="mono-tag mb-1">nova versão proposta</div>
                  <p className="text-[13px] leading-relaxed text-ink-dim">
                    <FormattedText text={preview} />
                  </p>
                  <div className="mt-2.5 flex flex-wrap gap-2">
                    <PeButton
                      variant="flux"
                      onClick={onApply}
                      loading={busy}
                      className="!py-1.5 !text-[12px]"
                    >
                      Aplicar
                    </PeButton>
                    <button
                      type="button"
                      onClick={onReedit}
                      className="font-mono text-[10px] uppercase tracking-wide text-ink-faint hover:text-ink-dim"
                    >
                      Reeditar instrução
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
