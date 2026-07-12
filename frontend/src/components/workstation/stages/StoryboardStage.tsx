import { useCallback, useState } from "react";
import { usePE } from "@/lib/pe-store";
import type { EditorialBlock } from "@/lib/pe-types";
import { PeButton } from "../ui";
import { StageHeader, StageScroll } from "./common";

export function StoryboardStage() {
  const { storyboardBlocks, generateStoryboard, updateStoryboard, goto, busy, editorialStatus } = usePE();
  const [localBlocks, setLocalBlocks] = useState<EditorialBlock[]>([]);
  const [dirty, setDirty] = useState(false);

  const blocks = dirty ? localBlocks : storyboardBlocks;

  const syncLocal = useCallback(() => {
    setLocalBlocks([...storyboardBlocks]);
    setDirty(true);
  }, [storyboardBlocks]);

  const patchBlock = (id: string, patch: Partial<EditorialBlock>) => {
    syncLocal();
    setLocalBlocks((prev) => {
      const base = dirty ? prev : [...storyboardBlocks];
      return base.map((b) => (b.id === id ? { ...b, ...patch } : b));
    });
    setDirty(true);
  };

  const moveBlock = (id: string, dir: -1 | 1) => {
    const base = dirty ? localBlocks : [...storyboardBlocks];
    const idx = base.findIndex((b) => b.id === id);
    const next = idx + dir;
    if (idx < 0 || next < 0 || next >= base.length) return;
    const copy = [...base];
    [copy[idx], copy[next]] = [copy[next], copy[idx]];
    setLocalBlocks(copy.map((b, i) => ({ ...b, order: i + 1 })));
    setDirty(true);
  };

  const addBlock = () => {
    const base = dirty ? localBlocks : [...storyboardBlocks];
    const id = `blk_local_${Date.now()}`;
    setLocalBlocks([
      ...base,
      { id, order: base.length + 1, role: "Novo bloco", focus: "Descreva o foco", revision: 1 },
    ]);
    setDirty(true);
  };

  const removeBlock = (id: string) => {
    const base = dirty ? localBlocks : [...storyboardBlocks];
    setLocalBlocks(base.filter((b) => b.id !== id).map((b, i) => ({ ...b, order: i + 1 })));
    setDirty(true);
  };

  const save = async () => {
    const payload = (dirty ? localBlocks : storyboardBlocks).map(({ id, role, focus, revision }) => ({
      id,
      role,
      focus,
      revision,
    }));
    await updateStoryboard(payload);
    setDirty(false);
  };

  const hasBlocks = blocks.length > 0;

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 04 · fluxo narrativo"
        title="Storyboard narrativo"
        desc="Defina papéis e focos de cada bloco. O texto final ainda não é escrito aqui."
        aside={
          <div className="flex gap-2">
            <PeButton variant="outline" onClick={() => generateStoryboard()} loading={busy} data-testid="generate-storyboard">
              Gerar storyboard
            </PeButton>
            {hasBlocks && (
              <PeButton variant="flux" onClick={() => save()} loading={busy} data-testid="save-storyboard">
                Salvar alterações
              </PeButton>
            )}
          </div>
        }
      />

      <div className="space-y-3" data-testid="storyboard-list">
        {blocks.map((block) => (
          <div key={block.id} className="panel p-4" data-testid={`storyboard-block-${block.order}`}>
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="mono-tag">bloco {block.order}</span>
              <div className="flex gap-1">
                <PeButton variant="ghost" onClick={() => moveBlock(block.id, -1)}>↑</PeButton>
                <PeButton variant="ghost" onClick={() => moveBlock(block.id, 1)}>↓</PeButton>
                <PeButton variant="ghost" onClick={() => removeBlock(block.id)}>✕</PeButton>
              </div>
            </div>
            <label className="mono-tag">papel</label>
            <input
              className="mt-1 w-full rounded-md border border-hairline bg-surface-2 px-3 py-2 text-sm"
              value={block.role}
              onChange={(e) => patchBlock(block.id, { role: e.target.value })}
              data-testid={`block-role-${block.order}`}
            />
            <label className="mono-tag mt-3 block">foco</label>
            <textarea
              className="mt-1 w-full rounded-md border border-hairline bg-surface-2 px-3 py-2 text-sm"
              rows={2}
              value={block.focus}
              onChange={(e) => patchBlock(block.id, { focus: e.target.value })}
              data-testid={`block-focus-${block.order}`}
            />
          </div>
        ))}
      </div>

      <div className="mt-4 flex justify-between">
        <PeButton variant="outline" onClick={addBlock}>Adicionar bloco</PeButton>
        {editorialStatus.storyboard_available && (
          <PeButton variant="flux" onClick={() => goto("drafts")} data-testid="goto-drafts">
            Rascunhos →
          </PeButton>
        )}
      </div>
    </StageScroll>
  );
}
