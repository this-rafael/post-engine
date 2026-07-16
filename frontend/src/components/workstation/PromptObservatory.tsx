import { useEffect, useMemo, useState } from "react";
import {
  fetchPromptArtifact, fetchPromptOperation, fetchPromptRegistry,
  type PromptRegistryCatalog,
} from "@/lib/pe-api";
import { useIsNarrow } from "@/lib/use-is-narrow";
import { ActivityGlyph, AnimatedNumber, ErrorAccordion, PeButton } from "./ui";
import { DetailPanel } from "./observatory/DetailPanel";
import { buildGraphLayout, type OpRecord } from "./observatory/graph-layout";
import { PipelineCanvas } from "./observatory/PipelineCanvas";

const record = (value: unknown): OpRecord => value && typeof value === "object" && !Array.isArray(value) ? value as OpRecord : {};

export function PromptObservatory({ onClose }: { onClose: () => void }) {
  const [catalog, setCatalog] = useState<PromptRegistryCatalog | null>(null);
  const [phase, setPhase] = useState("");
  const [softPhase, setSoftPhase] = useState("");
  const [operationKey, setOperationKey] = useState("");
  const [artifactKey, setArtifactKey] = useState("");
  const [operation, setOperation] = useState<OpRecord | null>(null);
  const [artifact, setArtifact] = useState<OpRecord | null>(null);
  const [query, setQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [panelOpen, setPanelOpen] = useState(false);
  const [focusToken, setFocusToken] = useState(0);
  const mobile = useIsNarrow(900);

  const loadCatalog = async () => {
    setLoading(true);
    try {
      const data = await fetchPromptRegistry();
      setCatalog(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void loadCatalog(); }, []);

  useEffect(() => {
    if (!catalog || softPhase) return;
    const ops = (catalog.operations ?? []).map(record);
    const last = [...ops]
      .map((op) => ({ key: String(op.phase ?? ""), at: String(record(op.last_execution).resolved_at ?? "") }))
      .filter((item) => item.key && item.at)
      .sort((a, b) => a.at.localeCompare(b.at))
      .at(-1);
    setSoftPhase(last?.key || catalog.phases[0]?.key || "");
  }, [catalog, softPhase]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (panelOpen) { setPanelOpen(false); return; }
        onClose();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose, panelOpen]);

  useEffect(() => {
    if (!operationKey) { setOperation(null); return; }
    void fetchPromptOperation(operationKey).then(setOperation).catch((err) => setError(String(err)));
  }, [operationKey]);

  useEffect(() => {
    if (!artifactKey) { setArtifact(null); return; }
    void fetchPromptArtifact(artifactKey).then(setArtifact).catch((err) => setError(String(err)));
  }, [artifactKey]);

  const operations = useMemo(
    () => (catalog?.operations ?? []).map(record),
    [catalog],
  );

  const layout = useMemo(
    () => buildGraphLayout(catalog?.phases ?? [], operations, (catalog?.diagnostics ?? []).map(record)),
    [catalog, operations],
  );

  const phaseMeta = catalog?.phases.find((item) => item.key === phase) ?? null;

  const phaseOps = useMemo(() => {
    const q = query.trim().toLowerCase();
    return operations.filter((item) => {
      if (item.phase !== phase) return false;
      if (!q) return true;
      return `${String(item.label)} ${String(item.key)}`.toLowerCase().includes(q);
    });
  }, [operations, phase, query]);

  const compositionItems = useMemo(() => {
    const items = operation?.composition && typeof operation.composition === "object"
      ? (record(operation.composition).items as unknown)
      : [];
    return Array.isArray(items) ? items.map(record) : [];
  }, [operation]);

  const selectPhase = (key: string) => {
    setPhase(key);
    setSoftPhase(key);
    setOperationKey("");
    setArtifactKey("");
    setOperation(null);
    setArtifact(null);
    setPanelOpen(true);
    setFocusToken((n) => n + 1);
  };

  const selectOperation = (key: string) => {
    setOperationKey(key);
    setArtifactKey("");
    setArtifact(null);
    setPanelOpen(true);
  };

  const selectArtifact = (key: string) => {
    setArtifactKey(key);
    setPanelOpen(true);
  };

  return (
    <section className="absolute inset-0 z-20 flex min-w-0 flex-col overflow-hidden bg-bg">
      <ObservatoryHeader
        catalog={catalog}
        query={query}
        setQuery={setQuery}
        onClose={onClose}
        onRefresh={() => void loadCatalog()}
      />
      {error && (
        <div className="px-4 py-2">
          <ErrorAccordion title="Falha no Observatory" details={error} />
        </div>
      )}
      {loading && !catalog ? (
        <div className="grid flex-1 place-items-center">
          <ActivityGlyph kind="Carregando registry" />
        </div>
      ) : (
        <div className="relative flex min-h-0 flex-1 overflow-hidden">
          <PipelineCanvas
            layout={layout}
            selectedPhase={phase}
            softPhase={softPhase}
            selectedArtifact={artifactKey}
            compositionItems={compositionItems}
            onSelectPhase={selectPhase}
            onSelectArtifact={selectArtifact}
            focusToken={focusToken}
            panelOpen={panelOpen}
          />
          <DetailPanel
            open={panelOpen}
            phase={phaseMeta}
            phaseOps={phaseOps}
            operationKey={operationKey}
            operation={operation}
            artifact={artifact}
            onSelectOperation={selectOperation}
            onSelectArtifact={selectArtifact}
            onChanged={() => {
              void loadCatalog();
              if (artifactKey) void fetchPromptArtifact(artifactKey).then(setArtifact);
              if (operationKey) void fetchPromptOperation(operationKey).then(setOperation);
            }}
            onClose={() => setPanelOpen(false)}
            mobile={mobile}
          />
        </div>
      )}
    </section>
  );
}

function ObservatoryHeader({
  catalog, query, setQuery, onClose, onRefresh,
}: {
  catalog: PromptRegistryCatalog | null;
  query: string;
  setQuery: (v: string) => void;
  onClose: () => void;
  onRefresh: () => void;
}) {
  const stats = catalog?.summary;
  return (
    <header className="shrink-0 border-b border-hairline px-3 py-2.5 sm:px-4 lg:px-5">
      <div className="flex flex-wrap items-center gap-2 sm:gap-3">
        <div className="min-w-0 flex-1 basis-full sm:basis-auto sm:min-w-[200px]">
          <div className="eyebrow">runtime prompt intelligence</div>
          <h1 className="font-display text-lg font-semibold tracking-tight sm:text-xl">Prompt Pipeline Observatory</h1>
          <p className="hidden text-xs text-ink-faint sm:block">Mapa de execução das composições do registry canônico.</p>
        </div>
        <label className="field flex min-w-0 w-full flex-1 items-center gap-2 px-2.5 py-1.5 sm:min-w-[180px] sm:max-w-xs sm:w-auto">
          <span className="text-ink-faint">⌕</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="w-full min-w-0 bg-transparent text-sm outline-none"
            placeholder="Filtrar operações"
          />
        </label>
        <div className="flex flex-wrap items-center gap-1.5">
          {([["ops", stats?.operations], ["arts", stats?.artifacts], ["comp", stats?.compositions], ["diag", stats?.diagnostics]] as const).map(([label, value]) => (
            <div key={label} className="inset-panel px-2 py-1">
              <div className="mono-tag !text-[7px]">{label}</div>
              <AnimatedNumber value={Number(value ?? 0)} className="font-display text-sm leading-none" />
            </div>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <PeButton variant="ghost" onClick={onRefresh}>Atualizar</PeButton>
          <PeButton variant="outline" onClick={onClose}>Fechar</PeButton>
        </div>
      </div>
    </header>
  );
}
