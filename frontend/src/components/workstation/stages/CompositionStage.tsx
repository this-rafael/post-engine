import { usePE } from "@/lib/pe-store";
import { PeButton } from "../ui";
import { FormattedText } from "../FormattedText";
import { StageHeader, StageScroll } from "./common";

export function CompositionStage() {
  const { editorialFlow, editorialStatus, composeEditorial, goto, busy, rawOutput } = usePE();
  const preview = editorialFlow.composition?.conteudo || rawOutput;

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 06 · convergência"
        title="Composição editorial"
        desc="Una os rascunhos selecionados em um texto coeso. As ideias escolhidas são preservadas."
        aside={
          <PeButton
            variant="flux"
            disabled={!editorialStatus.selection_complete}
            onClick={() => composeEditorial()}
            loading={busy}
            data-testid="compose-editorial"
          >
            {editorialFlow.composition?.conteudo ? "Recompor publicação" : "Compor publicação"}
          </PeButton>
        }
      />

      {preview ? (
        <div className="panel p-5 text-[13.5px] leading-relaxed" data-testid="composition-preview">
          <FormattedText text={preview} />
        </div>
      ) : (
        <div className="panel grid min-h-[200px] place-items-center p-8 text-center">
          <p className="mono-tag text-ink-faint">
            {editorialStatus.selection_complete
              ? "Pronto para compor"
              : "Complete a seleção em todos os blocos"}
          </p>
        </div>
      )}

      {editorialStatus.composition_available && (
        <div className="mt-6 flex justify-end">
          <PeButton variant="flux" onClick={() => goto("segmentation")} data-testid="goto-segmentation">
            Segmentação →
          </PeButton>
        </div>
      )}
    </StageScroll>
  );
}
