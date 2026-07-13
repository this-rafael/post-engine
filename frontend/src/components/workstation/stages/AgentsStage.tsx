import { motion } from "motion/react";
import { usePE } from "@/lib/pe-store";
import type { ProviderId } from "@/lib/pe-types";
import { PeButton, Reveal } from "../ui";
import { StageHeader, StageScroll } from "./common";
import { cn } from "@/lib/utils";

const MODEL_OPTIONS: Record<ProviderId, string[]> = {
  codex: ["gpt-5.6-terra", "gpt-5.6-luna", "gpt-5.6-sol", "gpt-5.5", "gpt-5.4-mini", "gpt-5.5-thinking"],
  opencode: ["opencode-go/qwen3.7-plus", "opencode-go/glm-5.2", "opencode-go/qwen3.6-plus", "opencode-go/deepseek-r2", "qwen-3.6-plus"],
  cursor: ["auto", "cursor-fast", "cursor-max"],
};
const REASONING = ["", "low", "medium", "high", "xhigh", "max"];
const SANDBOX = ["read-only", "workspace-write", "danger-full"] as const;

export function AgentsStage() {
  const { ops, updateOp, goto, saveOps, busy } = usePE();
  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 00 · roteamento de agentes"
        title="Central de inteligências"
        desc="Cada transformação do pipeline é conduzida por um agente. Aqui você define qual inteligência é responsável por cada operação — não são configurações comuns, é o roteamento da máquina editorial."
        aside={<ProviderStatus />}
      />

      <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
        {ops.map((op, i) => (
          <Reveal key={op.id} delay={i * 0.05}>
            <div className="group panel relative overflow-hidden p-4">
              <div
                className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full opacity-0 blur-2xl transition-opacity duration-500 group-hover:opacity-100"
                style={{ background: "color-mix(in oklab, var(--flux) 30%, transparent)" }}
              />
              <div className="relative flex items-center justify-between">
                <div>
                  <div className="mono-tag">operação</div>
                  <div className="font-display text-[15px] font-semibold">{op.label}</div>
                </div>
                <div className="flex items-center gap-1.5 rounded-full border border-hairline bg-surface/60 px-2.5 py-1">
                  <span
                    className="h-1.5 w-1.5 rounded-full"
                    style={{ background: "var(--flux)" }}
                  />
                  <span className="font-mono text-[10px] uppercase tracking-wide text-ink-dim">
                    {op.provider}
                  </span>
                </div>
              </div>

              <div className="relative mt-4 space-y-3">
                <Selector
                  label="provider"
                  value={op.provider}
                  options={["codex", "opencode", "cursor"]}
                  onChange={(v) =>
                    updateOp(op.id, {
                      provider: v as ProviderId,
                      model: MODEL_OPTIONS[v as ProviderId]?.[0] ?? op.model,
                    })
                  }
                />
                <ModelSelector
                  label="modelo"
                  value={op.model}
                  provider={op.provider}
                  onChange={(v) => updateOp(op.id, { model: v })}
                />
                <AgentField
                  value={op.agent ?? ""}
                  onChange={(v) => updateOp(op.id, { agent: v || undefined })}
                />
                <div className="grid grid-cols-2 gap-3">
                  <Selector
                    label="reasoning"
                    value={op.reasoning ?? ""}
                    options={REASONING}
                    placeholder="n/a"
                    onChange={(v) => updateOp(op.id, { reasoning: v || undefined })}
                  />
                  <Selector
                    label="sandbox"
                    value={op.sandbox}
                    options={SANDBOX as unknown as string[]}
                    onChange={(v) => updateOp(op.id, { sandbox: v as never })}
                  />
                </div>
              </div>
            </div>
          </Reveal>
        ))}
      </div>

      <div className="mt-6 flex items-center justify-between">
        <PeButton variant="ghost" onClick={() => saveOps()} loading={busy}>
          Salvar como padrão do workspace
        </PeButton>
        <PeButton variant="flux" onClick={() => goto("entry")}>
          Iniciar sessão editorial →
        </PeButton>
      </div>
    </StageScroll>
  );
}

function ProviderStatus() {
  const { providers } = usePE();
  return (
    <div className="panel flex items-center gap-4 px-4 py-3">
      {providers.map((p) => (
        <div key={p.id} className="flex items-center gap-2">
          <motion.span
            className="relative flex h-2 w-2"
            animate={{ opacity: [1, 0.5, 1] }}
            transition={{ duration: 2.4, repeat: Infinity }}
          >
            <span
              className="inline-flex h-2 w-2 rounded-full"
              style={{ background: p.available ? "var(--ok)" : "var(--ink-faint)" }}
            />
          </motion.span>
          <div className="leading-tight">
            <div className="text-[12px] font-medium">{p.label}</div>
            <div className="mono-tag !text-[9px]">{p.available ? "disponível" : "offline"}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ModelSelector({
  label,
  value,
  provider,
  onChange,
}: {
  label: string;
  value: string;
  provider: ProviderId;
  onChange: (v: string) => void;
}) {
  const presets = MODEL_OPTIONS[provider] ?? [];
  const options = presets.includes(value) ? presets : value ? [value, ...presets] : presets;
  return (
    <Selector label={label} value={value} options={options} onChange={onChange} />
  );
}

function AgentField({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div>
      <div className="mono-tag mb-1">agent</div>
      <input
        type="text"
        value={value}
        placeholder="opcional"
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-hairline bg-surface/60 px-2.5 py-1.5 font-mono text-[11px] text-ink outline-none transition-colors placeholder:text-ink-faint focus:border-hairline-strong"
      />
    </div>
  );
}

function Selector({
  label,
  value,
  options,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <div className="mono-tag mb-1">{label}</div>
      <div className="flex flex-wrap gap-1.5">
        {options.map((o) => {
          const active = o === value;
          const display = o === "" ? placeholder ?? "—" : o;
          return (
            <button
              key={o || "none"}
              onClick={() => onChange(o)}
              className={cn(
                "relative rounded-md border px-2.5 py-1.5 font-mono text-[11px] transition-colors",
                active
                  ? "border-transparent text-ink"
                  : "border-hairline text-ink-faint hover:border-hairline-strong hover:text-ink-dim",
              )}
            >
              {active && (
                <motion.span
                  layoutId={`sel-${label}-${value}`}
                  className="absolute inset-0 rounded-md border border-[color-mix(in_oklab,var(--flux)_45%,transparent)] bg-[color-mix(in_oklab,var(--flux)_14%,transparent)]"
                  transition={{ type: "spring", stiffness: 400, damping: 32 }}
                />
              )}
              <span className="relative z-10">{display}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
