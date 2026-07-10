import type { ProviderId } from "./pe-types";
import type { OperationConfig } from "./pe-types";
import { OP_LABELS, OP_ORDER, OP_UI_TO_BACKEND } from "./mappers/operations";

export interface ApiSnapshot {
  state: Record<string, unknown>;
  derived: Record<string, unknown>;
  options: Record<string, unknown>;
}

export interface LlmConfigSnapshot {
  operations: Record<string, Record<string, unknown>>;
  operation_labels: Record<string, string>;
  providers: Array<{ value: string; label: string }>;
  provider_status: Array<{ id: string; label: string; available: boolean }>;
}

export async function fetchSession(): Promise<ApiSnapshot> {
  const res = await fetch("/api/session");
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.error || "Falha ao carregar sessao");
  return payload;
}

export async function patchSession(state: Record<string, unknown>): Promise<ApiSnapshot> {
  const res = await fetch("/api/session", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(state),
  });
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.error || "Falha ao salvar sessao");
  return payload;
}

export async function runAction(
  action: string,
  body: Record<string, unknown> = {},
): Promise<ApiSnapshot> {
  const res = await fetch("/api/action", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, ...body }),
  });
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.error || `Falha na acao ${action}`);
  return payload;
}

export async function restoreSession(state: Record<string, unknown>): Promise<ApiSnapshot> {
  const res = await fetch("/api/restore", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ state }),
  });
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.error || "Falha ao restaurar sessao");
  return payload;
}

export async function fetchLlmConfig(): Promise<LlmConfigSnapshot> {
  const res = await fetch("/api/llm-config");
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.error || "Falha ao carregar config");
  return payload;
}

export async function saveLlmConfig(operations: Record<string, Record<string, unknown>>): Promise<LlmConfigSnapshot> {
  const res = await fetch("/api/llm-config", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ operations }),
  });
  const payload = await res.json();
  if (!res.ok) throw new Error(payload.error || "Falha ao salvar config");
  return payload;
}

export function opsFromConfig(
  llmConfig: LlmConfigSnapshot,
  effective?: Record<string, Record<string, unknown>>,
): OperationConfig[] {
  const source = effective ?? llmConfig.operations;
  return OP_ORDER.map((uiId: string) => {
    const backendId = OP_UI_TO_BACKEND[uiId] ?? uiId;
    const raw = source[backendId] ?? source[uiId] ?? {};
    return {
      id: uiId,
      label: OP_LABELS[uiId] ?? llmConfig.operation_labels[backendId] ?? uiId,
      provider: (String(raw.provider || "codex")) as ProviderId,
      model: String(raw.model || ""),
      agent: raw.agent ? String(raw.agent) : undefined,
      reasoning: raw.reasoning_effort ? String(raw.reasoning_effort) : undefined,
      sandbox: (String(raw.sandbox || "read-only")) as OperationConfig["sandbox"],
      timeoutSeconds:
        typeof raw.timeout_seconds === "number" ? raw.timeout_seconds : undefined,
    };
  });
}

export function llmConfigPayloadFromOps(ops: OperationConfig[]): Record<string, Record<string, unknown>> {
  const out: Record<string, Record<string, unknown>> = {};
  for (const op of ops) {
    const backendId = OP_UI_TO_BACKEND[op.id] ?? op.id;
    out[backendId] = {
      provider: op.provider,
      model: op.model,
      agent: op.agent || undefined,
      reasoning_effort: op.reasoning || undefined,
      sandbox: op.sandbox,
      timeout_seconds: op.timeoutSeconds || undefined,
    };
  }
  return out;
}

export function eventsFromState(events: unknown[]): Array<{ id: string; t: number; kind: string; label: string }> {
  if (!Array.isArray(events)) return [];
  return events.map((entry, index) => {
    const item = entry as Record<string, unknown>;
    const kind = String(item.type ?? item.kind ?? "event");
    const label = String(item.message ?? item.label ?? item.status ?? JSON.stringify(item));
    return { id: `evt-${index}`, t: index, kind, label };
  });
}

export function tipoLabel(tipo: string, options: Array<{ label: string; value: string }>): string {
  const found = options.find((o) => o.value === tipo);
  return found?.label ?? tipo;
}

export function providersFromStatus(
  status: Array<{ id: string; label: string; available: boolean }>,
): Array<{ id: ProviderId; label: string; available: boolean }> {
  return status.map((p) => ({
    id: p.id as ProviderId,
    label: p.label,
    available: p.available,
  }));
}
