import { motion, useReducedMotion } from "motion/react";
import { useCallback, useEffect, useMemo, useRef, useState, type WheelEvent } from "react";
import { cn } from "@/lib/utils";
import {
  CAMERA,
  buildCompositionLayout,
  compositionEdgePath,
  edgePath,
  relationOf,
  type CompositionLayoutNode,
  type GraphLayout,
  type LayoutNode,
  type OpRecord,
} from "./graph-layout";

type Camera = { x: number; y: number; zoom: number };

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n));
}

function statusColor(status: LayoutNode["status"]) {
  if (status === "ok") return "var(--ok)";
  if (status === "danger") return "var(--danger)";
  if (status === "warn") return "var(--flux)";
  return "var(--hairline-strong)";
}

function artifactKindClass(node: CompositionLayoutNode) {
  const t = node.type.toUpperCase();
  if (node.runtimeSlot) return "runtime";
  if (t.includes("PERSONA")) return "persona";
  if (t.includes("POLICY") || t.includes("ANTI")) return "policy";
  if (t.includes("CONTRACT")) return "contract";
  if (t.includes("RETRY")) return "retry";
  if (node.conditional) return "conditional";
  return "base";
}

export function PipelineCanvas({
  layout,
  selectedPhase,
  softPhase,
  selectedArtifact,
  compositionItems,
  onSelectPhase,
  onSelectArtifact,
  focusToken,
  panelOpen,
}: {
  layout: GraphLayout;
  selectedPhase: string;
  softPhase: string;
  selectedArtifact: string;
  compositionItems: OpRecord[];
  onSelectPhase: (key: string) => void;
  onSelectArtifact: (key: string) => void;
  focusToken: number;
  panelOpen: boolean;
}) {
  const reduceMotion = useReducedMotion();
  const viewportRef = useRef<HTMLDivElement>(null);
  const [camera, setCamera] = useState<Camera>({ x: 0, y: 0, zoom: 0.85 });
  const [dragging, setDragging] = useState(false);
  const dragRef = useRef<{ px: number; py: number; cx: number; cy: number } | null>(null);
  const didFit = useRef(false);

  const compositionNodes = useMemo(() => {
    if (!panelOpen || !selectedPhase || compositionItems.length === 0) return [] as CompositionLayoutNode[];
    const anchor = layout.nodeByKey.get(selectedPhase);
    if (!anchor) return [];
    return buildCompositionLayout(compositionItems, anchor);
  }, [compositionItems, layout.nodeByKey, panelOpen, selectedPhase]);

  const fitView = useCallback((padding = 64) => {
    const el = viewportRef.current;
    if (!el) return;
    const { width, height } = el.getBoundingClientRect();
    const { bounds } = layout;
    const zoom = clamp(
      Math.min((width - padding * 2) / bounds.width, (height - padding * 2) / bounds.height),
      CAMERA.minZoom,
      1,
    );
    setCamera({
      zoom,
      x: width / 2 - (bounds.minX + bounds.width / 2) * zoom,
      y: height / 2 - (bounds.minY + bounds.height / 2) * zoom,
    });
  }, [layout]);

  const centerOn = useCallback((key: string, zoom = CAMERA.selectZoom) => {
    const el = viewportRef.current;
    const node = layout.nodeByKey.get(key);
    if (!el || !node) return;
    const { width, height } = el.getBoundingClientRect();
    const z = clamp(zoom, CAMERA.minZoom, CAMERA.maxZoom);
    setCamera({
      zoom: z,
      x: width / 2 - (node.x + node.width / 2) * z,
      y: height / 2 - (node.y + node.height / 2) * z,
    });
  }, [layout.nodeByKey]);

  useEffect(() => {
    if (didFit.current || layout.nodes.length === 0) return;
    didFit.current = true;
    requestAnimationFrame(() => fitView());
  }, [fitView, layout.nodes.length]);

  useEffect(() => {
    if (!panelOpen || !selectedPhase || focusToken === 0) return;
    centerOn(selectedPhase);
  }, [centerOn, focusToken, panelOpen, selectedPhase]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) return;
      const ordered = [...layout.nodes].sort((a, b) => a.phase.order - b.phase.order);
      const activeKey = panelOpen ? selectedPhase : softPhase;
      const index = ordered.findIndex((n) => n.key === activeKey);
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        event.preventDefault();
        const next = ordered[(index + 1 + ordered.length) % ordered.length];
        if (next) onSelectPhase(next.key);
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        event.preventDefault();
        const prev = ordered[(index - 1 + ordered.length) % ordered.length];
        if (prev) onSelectPhase(prev.key);
      } else if (event.key === "f" || event.key === "F") {
        fitView();
      } else if (event.key === "c" || event.key === "C") {
        if (selectedPhase && panelOpen) centerOn(selectedPhase);
      } else if (event.key === "0") {
        fitView();
      } else if (event.key === "+" || event.key === "=") {
        setCamera((c) => ({ ...c, zoom: clamp(c.zoom * 1.12, CAMERA.minZoom, CAMERA.maxZoom) }));
      } else if (event.key === "-") {
        setCamera((c) => ({ ...c, zoom: clamp(c.zoom / 1.12, CAMERA.minZoom, CAMERA.maxZoom) }));
      } else if (event.key === "Enter" && softPhase && !panelOpen) {
        onSelectPhase(softPhase);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [centerOn, fitView, layout.nodes, onSelectPhase, panelOpen, selectedPhase, softPhase]);

  const onWheel = (event: WheelEvent) => {
    event.preventDefault();
    const el = viewportRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const mx = event.clientX - rect.left;
    const my = event.clientY - rect.top;
    const factor = event.deltaY > 0 ? 0.92 : 1.08;
    setCamera((c) => {
      const nextZoom = clamp(c.zoom * factor, CAMERA.minZoom, CAMERA.maxZoom);
      const wx = (mx - c.x) / c.zoom;
      const wy = (my - c.y) / c.zoom;
      return { zoom: nextZoom, x: mx - wx * nextZoom, y: my - wy * nextZoom };
    });
  };

  const worldWidth = Math.max(layout.bounds.width + 200, 1200);
  const worldHeight = Math.max(
    layout.bounds.height + (compositionNodes.length ? 220 : 80),
    640,
  );

  return (
    <div className="relative min-h-0 flex-1 overflow-hidden bg-[color-mix(in_oklab,var(--void)_72%,var(--bg))]">
      <div
        ref={viewportRef}
        role="application"
        aria-label="Canvas do pipeline de prompts"
        tabIndex={0}
        className={cn("absolute inset-0 cursor-grab outline-none focus-visible:ring-1 focus-visible:ring-[color-mix(in_oklab,var(--flux)_45%,transparent)]", dragging && "cursor-grabbing")}
        onWheel={onWheel}
        onPointerDown={(e) => {
          if (e.button !== 0) return;
          if ((e.target as HTMLElement).closest("[data-node], [data-artifact], button")) return;
          dragRef.current = { px: e.clientX, py: e.clientY, cx: camera.x, cy: camera.y };
          setDragging(true);
          (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (!dragRef.current) return;
          const dx = e.clientX - dragRef.current.px;
          const dy = e.clientY - dragRef.current.py;
          setCamera({ zoom: camera.zoom, x: dragRef.current.cx + dx, y: dragRef.current.cy + dy });
        }}
        onPointerUp={() => { dragRef.current = null; setDragging(false); }}
        onPointerCancel={() => { dragRef.current = null; setDragging(false); }}
      >
        <motion.div
          className="origin-top-left will-change-transform"
          style={{ width: worldWidth, height: worldHeight }}
          animate={{ x: camera.x, y: camera.y, scale: camera.zoom }}
          transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 220, damping: 28, mass: 0.9 }}
        >
          <svg className="absolute inset-0" width={worldWidth} height={worldHeight} aria-hidden>
            <defs>
              <pattern id="obs-grid" width="32" height="32" patternUnits="userSpaceOnUse">
                <path d="M 32 0 L 0 0 0 32" fill="none" stroke="color-mix(in oklab, var(--hairline) 55%, transparent)" strokeWidth="0.6" />
              </pattern>
              <linearGradient id="obs-flow" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stopColor="color-mix(in oklab, var(--flux) 15%, transparent)" />
                <stop offset="50%" stopColor="var(--flux)" />
                <stop offset="100%" stopColor="color-mix(in oklab, var(--flux) 15%, transparent)" />
              </linearGradient>
            </defs>
            <rect width={worldWidth} height={worldHeight} fill="url(#obs-grid)" opacity="0.35" />

            {layout.groups.map((group) => (
              <g key={group.id}>
                <rect
                  x={group.x}
                  y={group.y}
                  width={group.width}
                  height={group.height}
                  rx={16}
                  fill={`color-mix(in oklab, oklch(0.45 0.08 calc(var(--flux-hue) + ${group.hueShift})) 8%, transparent)`}
                  stroke="color-mix(in oklab, var(--hairline) 80%, transparent)"
                  strokeWidth={1}
                />
                <text
                  x={group.x + 16}
                  y={group.y + 18}
                  fill="var(--ink-faint)"
                  style={{ fontFamily: "var(--font-mono)", fontSize: 10, letterSpacing: "0.14em", textTransform: "uppercase" }}
                >
                  {group.label}
                </text>
              </g>
            ))}

            {layout.edges.map((edge) => {
              const from = layout.nodeByKey.get(edge.from);
              const to = layout.nodeByKey.get(edge.to);
              if (!from || !to) return null;
              const focusKey = panelOpen ? selectedPhase : "";
              const active = focusKey && (edge.from === focusKey || edge.to === focusKey || (edge.kind === "retry" && edge.from === focusKey));
              const faded = Boolean(focusKey) && !active;
              const d = edgePath(from, to, edge.kind);
              return (
                <g key={edge.id} opacity={faded ? 0.18 : edge.kind === "retry" && !active ? 0.35 : 0.9}>
                  <path
                    d={d}
                    fill="none"
                    stroke={active ? "url(#obs-flow)" : "color-mix(in oklab, var(--ink-faint) 55%, transparent)"}
                    strokeWidth={active ? 2.4 : 1.4}
                    strokeDasharray={edge.kind === "conditional" ? "7 6" : edge.kind === "retry" ? "3 5" : undefined}
                    strokeLinecap="round"
                  />
                  {active && !reduceMotion && edge.kind !== "retry" && (
                    <path
                      d={d}
                      fill="none"
                      stroke="var(--flux)"
                      strokeWidth={2}
                      strokeDasharray="10 18"
                      strokeLinecap="round"
                      opacity={0.85}
                    >
                      <animate attributeName="stroke-dashoffset" from="56" to="0" dur="1.2s" repeatCount="indefinite" />
                    </path>
                  )}
                </g>
              );
            })}

            {compositionNodes.length > 1 && compositionNodes.slice(0, -1).map((node, index) => {
              const next = compositionNodes[index + 1];
              return (
                <path
                  key={`${node.key}-${next.key}`}
                  d={compositionEdgePath(node, next)}
                  fill="none"
                  stroke="color-mix(in oklab, var(--flux) 55%, transparent)"
                  strokeWidth={1.5}
                  strokeDasharray={next.conditional ? "5 4" : undefined}
                  markerEnd="url(#obs-arrow)"
                />
              );
            })}
            <defs>
              <marker id="obs-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L6,3 L0,6 Z" fill="color-mix(in oklab, var(--flux) 70%, transparent)" />
              </marker>
            </defs>
          </svg>

          {layout.nodes.map((node) => {
            const relation = panelOpen ? relationOf(selectedPhase || null, node.key, layout.nodes) : "unrelated";
            const selected = panelOpen && relation === "selected";
            const soft = !panelOpen && softPhase === node.key;
            const dim = panelOpen && relation === "unrelated";
            const mid = panelOpen && (relation === "upstream" || relation === "downstream");
            return (
              <button
                key={node.key}
                type="button"
                data-node={node.key}
                aria-pressed={selected}
                aria-label={`Fase ${node.shortLabel}`}
                onClick={() => onSelectPhase(node.key)}
                className={cn(
                  "absolute rounded-xl border text-left transition-[opacity,box-shadow,transform] duration-300",
                  selected
                    ? "z-20 border-[color-mix(in_oklab,var(--flux)_70%,transparent)] bg-[color-mix(in_oklab,var(--void)_35%,var(--surface))] flux-glow"
                    : soft
                      ? "z-10 border-[color-mix(in_oklab,var(--flux)_40%,transparent)] bg-[color-mix(in_oklab,var(--flux)_8%,var(--surface))]"
                      : "border-hairline bg-[color-mix(in_oklab,var(--surface)_88%,transparent)] hover:border-[color-mix(in_oklab,var(--flux)_40%,transparent)]",
                  dim && "opacity-28 scale-[0.92]",
                  mid && "opacity-70",
                  relation === "adjacent" && "opacity-100 ring-1 ring-[color-mix(in_oklab,var(--flux)_28%,transparent)]",
                )}
                style={{
                  left: node.x,
                  top: node.y,
                  width: selected ? node.width + 28 : node.width,
                  minHeight: selected ? node.height + 36 : node.height,
                  transform: selected ? "translate(-14px, -18px) scale(1.06)" : undefined,
                  transformOrigin: "center center",
                }}
              >
                <div className="flex h-full flex-col p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="mono-tag !text-[8px]">{String(node.phase.order).padStart(2, "0")} · {node.group}</span>
                    <span className="h-2 w-2 rounded-full" style={{ background: statusColor(node.status), boxShadow: `0 0 10px ${statusColor(node.status)}` }} />
                  </div>
                  <div className={cn("mt-1 font-display font-semibold tracking-tight", selected ? "text-base" : "text-sm")}>{node.shortLabel}</div>
                  <div className="mt-1 font-mono text-[10px] text-ink-faint">{node.opCount} op · {node.artifactCount} artefatos</div>
                  <div className="mt-2 flex flex-wrap gap-1">
                    {node.conditional && <span className="rounded border border-hairline px-1.5 py-0.5 font-mono text-[8px] text-ink-dim">condicional</span>}
                    {node.hasRetry && <span className="rounded border border-hairline px-1.5 py-0.5 font-mono text-[8px] text-ink-dim">retry</span>}
                    {node.hasDiagnostics && <span className="rounded border border-[color-mix(in_oklab,var(--danger)_45%,transparent)] px-1.5 py-0.5 font-mono text-[8px] text-[var(--danger)]">diag</span>}
                  </div>
                  {selected && (
                    <p className="mt-2 text-[11px] leading-snug text-ink-dim">
                      {node.opCount} operações · {node.artifactCount} artefatos na composição ativa
                    </p>
                  )}
                </div>
              </button>
            );
          })}

          {compositionNodes.map((node) => {
            const kind = artifactKindClass(node);
            const selected = selectedArtifact === node.key;
            return (
              <button
                key={`art-${node.key}-${node.position}`}
                type="button"
                data-artifact={node.key}
                onClick={() => onSelectArtifact(node.key)}
                className={cn(
                  "absolute rounded-lg border p-2 text-left transition",
                  selected
                    ? "z-30 border-[color-mix(in_oklab,var(--flux)_65%,transparent)] bg-[color-mix(in_oklab,var(--flux)_12%,var(--surface))] flux-glow"
                    : "border-hairline bg-surface/90 hover:bg-surface-2",
                  kind === "conditional" && "border-dashed",
                )}
                style={{ left: node.x, top: node.y, width: node.width, height: node.height }}
              >
                <div className="font-mono text-[8px] flux-text">{String(node.position).padStart(2, "0")} · {kind}</div>
                <div className="mt-1 truncate text-[11px] font-medium">{node.title}</div>
                <div className="mt-1 truncate font-mono text-[9px] text-ink-faint">
                  {node.runtimeSlot ? `slot:${node.runtimeSlot}` : node.required ? "obrigatório" : "opcional"}
                </div>
              </button>
            );
          })}

          {selectedPhase && compositionNodes.length > 0 && (
            <div
              className="pointer-events-none absolute mono-tag"
              style={{
                left: compositionNodes[0].x,
                top: compositionNodes[0].y - 22,
              }}
            >
              composição ativa
            </div>
          )}
        </motion.div>
      </div>

      <CanvasControls
        onZoomIn={() => setCamera((c) => ({ ...c, zoom: clamp(c.zoom * 1.15, CAMERA.minZoom, CAMERA.maxZoom) }))}
        onZoomOut={() => setCamera((c) => ({ ...c, zoom: clamp(c.zoom / 1.15, CAMERA.minZoom, CAMERA.maxZoom) }))}
        onFit={() => fitView()}
        onCenter={() => selectedPhase && centerOn(selectedPhase)}
        onReset={() => { didFit.current = false; fitView(); }}
      />

      {!panelOpen && (
        <div className="pointer-events-none absolute bottom-5 left-1/2 z-10 max-w-md -translate-x-1/2 rounded-full border border-hairline bg-surface/80 px-4 py-2 text-center text-xs text-ink-dim backdrop-blur-md">
          Selecione uma fase para explorar operações e artefatos
        </div>
      )}
    </div>
  );
}

function CanvasControls({
  onZoomIn, onZoomOut, onFit, onCenter, onReset,
}: {
  onZoomIn: () => void; onZoomOut: () => void; onFit: () => void; onCenter: () => void; onReset: () => void;
}) {
  const btn = "grid h-9 w-9 place-items-center rounded-md border border-hairline bg-surface/90 text-sm text-ink-dim backdrop-blur hover:border-[color-mix(in_oklab,var(--flux)_40%,transparent)] hover:text-ink";
  return (
    <div className="absolute bottom-4 left-4 z-10 flex flex-col gap-1.5 sm:bottom-5 sm:left-5" role="toolbar" aria-label="Controles do canvas">
      <button type="button" className={btn} onClick={onZoomIn} aria-label="Zoom in" title="Zoom in (+)">+</button>
      <button type="button" className={btn} onClick={onZoomOut} aria-label="Zoom out" title="Zoom out (-)">−</button>
      <button type="button" className={btn} onClick={onFit} aria-label="Fit view" title="Fit view (F)">⤢</button>
      <button type="button" className={btn} onClick={onCenter} aria-label="Centralizar seleção" title="Centralizar seleção (C)">◎</button>
      <button type="button" className={btn} onClick={onReset} aria-label="Reset" title="Reset (0)">↺</button>
    </div>
  );
}
