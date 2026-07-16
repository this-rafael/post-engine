import type { PromptRegistryCatalog } from "@/lib/pe-api";

export type PhaseNode = PromptRegistryCatalog["phases"][number];
export type OpRecord = Record<string, unknown>;

export type GraphEdgeKind = "main" | "conditional" | "retry";

export interface LayoutNode {
  key: string;
  phase: PhaseNode;
  x: number;
  y: number;
  width: number;
  height: number;
  group: string;
  groupIndex: number;
  shortLabel: string;
  opCount: number;
  artifactCount: number;
  conditional: boolean;
  hasRetry: boolean;
  hasDiagnostics: boolean;
  lastExecution: string | null;
  status: "idle" | "ok" | "warn" | "danger";
}

export interface LayoutEdge {
  id: string;
  from: string;
  to: string;
  kind: GraphEdgeKind;
}

export interface LayoutGroup {
  id: string;
  label: string;
  x: number;
  y: number;
  width: number;
  height: number;
  hueShift: number;
}

export interface CompositionLayoutNode {
  key: string;
  title: string;
  position: number;
  x: number;
  y: number;
  width: number;
  height: number;
  required: boolean;
  conditional: boolean;
  runtimeSlot: string | null;
  type: string;
}

export interface GraphLayout {
  nodes: LayoutNode[];
  edges: LayoutEdge[];
  groups: LayoutGroup[];
  bounds: { minX: number; minY: number; maxX: number; maxY: number; width: number; height: number };
  nodeByKey: Map<string, LayoutNode>;
}

const NODE_W = 188;
const NODE_H = 96;
const GROUP_GAP_X = 56;
const NODE_GAP_Y = 36;
const PAD_X = 72;
const PAD_Y = 64;
const GROUP_PAD = 28;

export function shortPhaseLabel(label: string, group: string): string {
  const stripped = label.replace(`${group} / `, "").replace(`${group}/`, "").trim();
  return stripped || label;
}

function asRecord(value: unknown): OpRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as OpRecord) : {};
}

export function buildGraphLayout(
  phases: PhaseNode[],
  operations: OpRecord[],
  diagnostics: OpRecord[],
): GraphLayout {
  const opsByPhase = new Map<string, OpRecord[]>();
  for (const op of operations) {
    const phase = String(op.phase ?? "");
    const bucket = opsByPhase.get(phase) ?? [];
    bucket.push(op);
    opsByPhase.set(phase, bucket);
  }

  const diagOps = new Set(
    diagnostics.map((d) => String(d.operation ?? d.operation_key ?? "")).filter(Boolean),
  );

  const sorted = [...phases].sort((a, b) => a.order - b.order || a.key.localeCompare(b.key));
  const groupOrder: string[] = [];
  for (const phase of sorted) {
    if (!groupOrder.includes(phase.group)) groupOrder.push(phase.group);
  }

  const byGroup = new Map<string, PhaseNode[]>();
  for (const phase of sorted) {
    const list = byGroup.get(phase.group) ?? [];
    list.push(phase);
    byGroup.set(phase.group, list);
  }

  const nodes: LayoutNode[] = [];
  const groups: LayoutGroup[] = [];
  let cursorX = PAD_X;

  groupOrder.forEach((groupLabel, groupIndex) => {
    const members = byGroup.get(groupLabel) ?? [];
    const colH = members.length * NODE_H + Math.max(0, members.length - 1) * NODE_GAP_Y;
    const groupW = NODE_W + GROUP_PAD * 2;
    const groupH = colH + GROUP_PAD * 2 + 22;
    const groupY = PAD_Y;
    const groupX = cursorX;

    groups.push({
      id: groupLabel,
      label: groupLabel,
      x: groupX,
      y: groupY,
      width: groupW,
      height: groupH,
      hueShift: (groupIndex * 28) % 120,
    });

    members.forEach((phase, index) => {
      const ops = opsByPhase.get(phase.key) ?? [];
      const conditional = ops.some((op) => Boolean(op.is_conditional));
      const hasRetry = ops.some((op) => String(op.retry_policy ?? "").trim().length > 0);
      const hasDiagnostics = ops.some((op) => diagOps.has(String(op.key ?? "")));
      const lastExecution = ops
        .map((op) => asRecord(op.last_execution).resolved_at)
        .filter((v): v is string => typeof v === "string" && v.length > 0)
        .sort()
        .at(-1) ?? null;
      const status: LayoutNode["status"] = hasDiagnostics ? "danger" : lastExecution ? "ok" : conditional ? "warn" : "idle";

      nodes.push({
        key: phase.key,
        phase,
        x: groupX + GROUP_PAD,
        y: groupY + GROUP_PAD + 22 + index * (NODE_H + NODE_GAP_Y),
        width: NODE_W,
        height: NODE_H,
        group: groupLabel,
        groupIndex,
        shortLabel: shortPhaseLabel(phase.label, phase.group),
        opCount: phase.operations.length,
        artifactCount: phase.artifact_count,
        conditional,
        hasRetry,
        hasDiagnostics,
        lastExecution,
        status,
      });
    });

    cursorX += groupW + GROUP_GAP_X;
  });

  const edges: LayoutEdge[] = [];
  for (let i = 0; i < nodes.length - 1; i += 1) {
    const from = nodes[i];
    const to = nodes[i + 1];
    edges.push({
      id: `${from.key}->${to.key}`,
      from: from.key,
      to: to.key,
      kind: to.conditional ? "conditional" : "main",
    });
    if (to.hasRetry) {
      edges.push({
        id: `${to.key}::retry`,
        from: to.key,
        to: to.key,
        kind: "retry",
      });
    }
  }

  const xs = nodes.flatMap((n) => [n.x, n.x + n.width]);
  const ys = nodes.flatMap((n) => [n.y, n.y + n.height]);
  const groupXs = groups.flatMap((g) => [g.x, g.x + g.width]);
  const groupYs = groups.flatMap((g) => [g.y, g.y + g.height]);
  const allX = [...xs, ...groupXs];
  const allY = [...ys, ...groupYs];
  const minX = Math.min(...allX, 0) - 40;
  const minY = Math.min(...allY, 0) - 40;
  const maxX = Math.max(...allX, 800) + 40;
  const maxY = Math.max(...allY, 500) + 160;
  const nodeByKey = new Map(nodes.map((n) => [n.key, n]));

  return {
    nodes,
    edges,
    groups,
    bounds: { minX, minY, maxX, maxY, width: maxX - minX, height: maxY - minY },
    nodeByKey,
  };
}

export function relationOf(selectedKey: string | null, nodeKey: string, nodes: LayoutNode[]): "selected" | "adjacent" | "upstream" | "downstream" | "unrelated" {
  if (!selectedKey) return "unrelated";
  if (nodeKey === selectedKey) return "selected";
  const ordered = [...nodes].sort((a, b) => a.phase.order - b.phase.order);
  const selectedIndex = ordered.findIndex((n) => n.key === selectedKey);
  const index = ordered.findIndex((n) => n.key === nodeKey);
  if (selectedIndex < 0 || index < 0) return "unrelated";
  if (Math.abs(selectedIndex - index) === 1) return "adjacent";
  if (index < selectedIndex) return "upstream";
  if (index > selectedIndex) return "downstream";
  return "unrelated";
}

export function edgePath(from: LayoutNode, to: LayoutNode, kind: GraphEdgeKind): string {
  if (kind === "retry") {
    const sx = from.x + from.width / 2;
    const sy = from.y + from.height;
    const ey = sy + 42;
    return `M ${sx} ${sy} C ${sx + 48} ${sy + 8}, ${sx + 48} ${ey}, ${sx} ${ey} C ${sx - 48} ${ey}, ${sx - 48} ${sy + 8}, ${sx} ${sy}`;
  }
  const startX = from.x + from.width;
  const startY = from.y + from.height / 2;
  const endX = to.x;
  const endY = to.y + to.height / 2;
  const dx = Math.max(48, (endX - startX) * 0.45);
  return `M ${startX} ${startY} C ${startX + dx} ${startY}, ${endX - dx} ${endY}, ${endX} ${endY}`;
}

export function buildCompositionLayout(
  items: OpRecord[],
  anchor: LayoutNode,
): CompositionLayoutNode[] {
  const W = 132;
  const H = 64;
  const gap = 18;
  const startX = anchor.x - ((items.length - 1) * (W + gap)) / 2;
  const y = anchor.y + anchor.height + 72;
  return items.map((item, index) => {
    const art = asRecord(item.artifact);
    const condition = asRecord(item.condition);
    return {
      key: String(art.key ?? `item-${index}`),
      title: String(art.title ?? art.key ?? "artefato"),
      position: Number(item.position ?? index + 1),
      x: startX + index * (W + gap),
      y,
      width: W,
      height: H,
      required: Boolean(item.required ?? true),
      conditional: Boolean(condition.operator),
      runtimeSlot: item.runtime_slot ? String(item.runtime_slot) : null,
      type: String(art.type ?? "FRAGMENT"),
    };
  });
}

export function compositionEdgePath(a: CompositionLayoutNode, b: CompositionLayoutNode): string {
  const sx = a.x + a.width;
  const sy = a.y + a.height / 2;
  const ex = b.x;
  const ey = b.y + b.height / 2;
  const dx = Math.max(24, (ex - sx) * 0.4);
  return `M ${sx} ${sy} C ${sx + dx} ${sy}, ${ex - dx} ${ey}, ${ex} ${ey}`;
}

export const CAMERA = {
  minZoom: 0.35,
  maxZoom: 1.85,
  selectZoom: 1.15,
};
