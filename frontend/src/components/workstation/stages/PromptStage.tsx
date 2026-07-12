import { motion } from "motion/react";
import { useState } from "react";
import { usePE } from "@/lib/pe-store";
import { PeButton } from "../ui";
import { StageHeader, StageScroll } from "./common";
import { cn } from "@/lib/utils";

const SOURCES = [
  "instruções de sistema",
  "persona",
  "regras editoriais",
  "contexto da entrada",
  "dados da entrevista",
  "briefing",
  "restrições da plataforma",
  "restrições do tipo",
  "formato de saída",
];

export function PromptStage() {
  const { promptRendered, promptText, renderPrompt, goto, snapshot, busy } = usePE();
  const [connected, setConnected] = useState(0);
  const state = snapshot?.state ?? {};

  const sourceReady = [
    true,
    Boolean(state.personalidade),
    Boolean((state.restricoes_de_geracao as unknown[])?.length),
    Boolean(state.tema && state.objetivo_do_post),
    Boolean(state.interview_state),
    Boolean(state.briefing_autoral && Object.keys(state.briefing_autoral as object).length),
    Boolean(state.plataforma),
    Boolean(state.tipo_de_post),
    Boolean(state.tipo_de_post),
  ];

  const render = async () => {
    setConnected(0);
    const t = setInterval(() => setConnected((c) => Math.min(c + 1, SOURCES.length)), 180);
    await renderPrompt();
    clearInterval(t);
    setConnected(SOURCES.length);
  };

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 04 · compilação de contexto"
        title="Compilar o prompt de geração"
        desc="Renderizar significa fundir todas as fontes na instrução final enviada ao agente de geração. Antes disso, não existe prompt compilado."
        aside={
          <PeButton variant={promptRendered ? "outline" : "flux"} onClick={render} loading={busy}>
            {promptRendered ? "Renderizar novamente" : "Renderizar prompt"}
          </PeButton>
        }
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
        <div className="lg:col-span-2">
          <div className="panel p-5">
            <div className="mono-tag mb-3">fontes de compilação</div>
            <div className="space-y-1.5">
              {SOURCES.map((s, i) => {
                const on = i < connected || promptRendered || sourceReady[i];
                return (
                  <motion.div
                    key={s}
                    className="flex items-center gap-3 rounded-md px-2 py-1.5"
                    animate={{ backgroundColor: on ? "color-mix(in oklab, var(--flux) 8%, transparent)" : "transparent" }}
                  >
                    <motion.span
                      className="grid h-5 w-5 shrink-0 place-items-center rounded-full border font-mono text-[9px]"
                      animate={{
                        borderColor: on ? "color-mix(in oklab, var(--flux) 55%, transparent)" : "var(--hairline)",
                        color: on ? "var(--flux)" : "var(--ink-faint)",
                      }}
                    >
                      {on ? "✓" : i + 1}
                    </motion.span>
                    <span className={cn("text-[12.5px]", on ? "text-ink-dim" : "text-ink-faint")}>{s}</span>
                  </motion.div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="lg:col-span-3">
          <div className="panel flex h-full min-h-[360px] flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-hairline px-4 py-2.5">
              <div className="mono-tag">prompt compilado</div>
              <div className="flex items-center gap-1.5">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: promptRendered ? "var(--ok)" : "var(--ink-faint)" }}
                />
                <span className="font-mono text-[10px] text-ink-faint">
                  {promptRendered ? "resolved" : "unrendered"}
                </span>
              </div>
            </div>
            <div className="flex-1 overflow-auto p-4">
              {promptRendered && promptText ? (
                <pre className="whitespace-pre-wrap font-mono text-[12px] leading-relaxed text-ink-dim">
                  {promptText}
                </pre>
              ) : (
                <div className="mono-tag py-8 text-center">prompt ainda não renderizado</div>
              )}
            </div>
          </div>
        </div>
      </div>

      {promptRendered && (
        <div className="mt-6 flex justify-end">
          <PeButton variant="flux" onClick={() => goto("execution")}>
            Ir para execução →
          </PeButton>
        </div>
      )}
    </StageScroll>
  );
}
