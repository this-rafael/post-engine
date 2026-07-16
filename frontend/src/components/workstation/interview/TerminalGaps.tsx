import { useEffect, useRef } from "react";
import { motion } from "motion/react";
import { PeButton } from "../ui";
import type { InterviewTerminal } from "@/lib/mappers/interview";

export function TerminalGaps({
  terminal,
  busy,
  onDiagnose,
  onExtend,
  onForceFinish,
  onRestart,
  onBriefing,
  gatewayApproved,
}: {
  terminal: InterviewTerminal;
  busy?: boolean;
  onDiagnose: () => Promise<void>;
  onExtend: () => Promise<void>;
  onForceFinish: () => Promise<void>;
  onRestart: () => Promise<void>;
  onBriefing: () => Promise<void>;
  gatewayApproved?: boolean;
}) {
  const diagnosedRef = useRef(false);

  useEffect(() => {
    if (diagnosedRef.current) return;
    if (terminal.gapDiagnosis) return;
    if (busy) return;
    diagnosedRef.current = true;
    void onDiagnose();
  }, [terminal.gapDiagnosis, busy, onDiagnose]);

  const { questionCount, maxQuestions } = terminal.counts;

  if (gatewayApproved) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-1 flex-col items-center justify-center py-12 text-center"
      >
        <div className="mono-tag">gateway aprovado</div>
        <h2 className="mt-4 font-display text-[24px] font-semibold tracking-tight">
          Material suficiente
        </h2>
        <p className="mt-2 max-w-lg text-[14px] leading-relaxed text-ink-faint">
          A entrevista atingiu o mínimo autoral. Você pode gerar o briefing.
        </p>
        <PeButton variant="flux" className="mt-10" onClick={() => void onBriefing()} loading={busy}>
          Gerar briefing →
        </PeButton>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-1 flex-col items-center justify-center py-12 text-center"
    >
      <div className="mono-tag">limite da entrevista</div>
      <h2 className="mt-4 font-display text-[24px] font-semibold tracking-tight">
        Ainda faltam lacunas autorais
      </h2>

      <div className="mt-3 inline-flex items-center gap-2 rounded-md border border-hairline px-3 py-1.5 font-mono text-[11px] text-ink-dim">
        <span>
          {questionCount}/{maxQuestions || "—"} perguntas
        </span>
        {terminal.counts.extensionBatchesCompleted > 0 && (
          <>
            <span className="text-ink-faint">·</span>
            <span>{terminal.counts.extensionBatchesCompleted} lote(s) extra</span>
          </>
        )}
      </div>

      <div className="mt-8 w-full max-w-2xl rounded-lg border border-hairline bg-surface/40 px-5 py-4 text-left">
        <div className="mono-tag mb-2">o que falta</div>
        {terminal.gapDiagnosis ? (
          <p className="whitespace-pre-wrap text-[14px] leading-relaxed text-ink-dim">
            {terminal.gapDiagnosis}
          </p>
        ) : (
          <p className="text-[13.5px] text-ink-faint">
            {busy ? "Diagnosticando lacunas…" : "Diagnóstico ainda não disponível."}
          </p>
        )}
      </div>

      <div className="mt-10 flex flex-wrap justify-center gap-3">
        {terminal.canExtend && (
          <PeButton variant="flux" onClick={() => void onExtend()} loading={busy}>
            Gerar 5 perguntas →
          </PeButton>
        )}
        {terminal.canForceFinish && (
          <PeButton variant="outline" onClick={() => void onForceFinish()} loading={busy}>
            Finalizar entrevista
          </PeButton>
        )}
        {terminal.canRestart && (
          <PeButton variant="ghost" onClick={() => void onRestart()} loading={busy}>
            Reiniciar
          </PeButton>
        )}
      </div>

      {terminal.counts.extensionBatchesCompleted === 0 && (
        <p className="mt-4 max-w-md text-[12.5px] leading-relaxed text-ink-faint">
          Gere um lote de 5 perguntas focadas nas lacunas. Finalizar e reiniciar
          ficam disponíveis após a primeira reavaliação extra.
        </p>
      )}
    </motion.div>
  );
}
