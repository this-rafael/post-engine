import type { EditorialBlock, EditorialDraftOption, EditorialStatus } from "../pe-types";

export interface EditorialFlow {
  schema_version?: string;
  briefing_fingerprint?: string;
  storyboard?: {
    version?: number;
    status?: string;
    blocks?: EditorialBlock[];
  };
  drafts?: {
    storyboard_version?: number;
    by_block?: Record<
      string,
      {
        status?: string;
        options?: EditorialDraftOption[];
        selected_option_id?: string | null;
        error?: string | null;
      }
    >;
  };
  composition?: {
    status?: string;
    selection_fingerprint?: string;
    conteudo?: string;
    conteudo_json?: Record<string, unknown>;
  };
}

export function editorialFlowFromState(state: Record<string, unknown>): EditorialFlow {
  const raw = state.editorial_flow;
  if (!raw || typeof raw !== "object") return {};
  return raw as EditorialFlow;
}

export function editorialStatusFromDerived(derived: Record<string, unknown>): EditorialStatus {
  const e = derived.editorial;
  if (!e || typeof e !== "object") {
    return {
      storyboard_available: false,
      drafts_partial: false,
      drafts_available: false,
      selection_incomplete: true,
      selection_complete: false,
      composition_stale: false,
      composition_available: false,
      can_compose: false,
    };
  }
  return e as EditorialStatus;
}

export function storyboardBlocks(flow: EditorialFlow): EditorialBlock[] {
  return Array.isArray(flow.storyboard?.blocks) ? flow.storyboard!.blocks! : [];
}

type DraftBlockEntry = {
  status?: string;
  options?: EditorialDraftOption[];
  selected_option_id?: string | null;
  error?: string | null;
};

type DraftByBlock = Record<string, DraftBlockEntry>;

export function isBlockUnlocked(
  blockIndex: number,
  blocks: EditorialBlock[],
  draftByBlock: DraftByBlock,
): boolean {
  if (blockIndex <= 0) return true;
  for (let i = 0; i < blockIndex; i++) {
    if (!draftByBlock?.[blocks[i].id]?.selected_option_id) return false;
  }
  return true;
}

export function frontierBlockId(
  blocks: EditorialBlock[],
  draftByBlock: DraftByBlock,
): string | null {
  for (const block of blocks) {
    if (!draftByBlock?.[block.id]?.selected_option_id) return block.id;
  }
  return null;
}
