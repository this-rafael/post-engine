import { AnimatePresence, motion } from "motion/react";
import { usePE } from "@/lib/pe-store";
import { PeButton, Reveal } from "../ui";
import { FormattedText } from "../FormattedText";
import { StageHeader, StageScroll } from "./common";

export function BriefingStage() {
  const { briefingReady, briefingCards, buildBriefing, goto, busy } = usePE();

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 03 · síntese estruturada"
        title="Briefing editorial"
        desc="Uma síntese de tudo que foi descoberto: entrada, entrevista e contexto identificado, organizados em uma estrutura editorial inspecionável."
        aside={
          <PeButton variant={briefingReady ? "outline" : "flux"} onClick={() => buildBriefing()} loading={busy}>
            {briefingReady ? "Recompilar briefing" : "Gerar briefing"}
          </PeButton>
        }
      />

      <AnimatePresence mode="wait">
        {!briefingReady ? (
          <motion.div
            key="empty"
            exit={{ opacity: 0, y: -10 }}
            className="panel grid min-h-[340px] place-items-center p-8 text-center"
          >
            <div>
              <motion.div
                className="mx-auto mb-4 h-16 w-16 rounded-xl"
                style={{ background: "conic-gradient(from 0deg, var(--flux), transparent, var(--flux))" }}
                animate={{ rotate: busy ? 360 : 0, opacity: busy ? [0.4, 1, 0.4] : 0.35 }}
                transition={{ rotate: { duration: 3, repeat: busy ? Infinity : 0, ease: "linear" }, opacity: { duration: 1.4, repeat: busy ? Infinity : 0 } }}
              />
              <p className="mono-tag">
                {busy ? "sintetizando contexto…" : "briefing ainda não compilado"}
              </p>
            </div>
          </motion.div>
        ) : (
          <motion.div key="brief" className="grid grid-cols-1 gap-3 md:grid-cols-2">
            {briefingCards.map((b, i) => (
              <Reveal key={b.k + i} delay={i * 0.05}>
                <div className="panel group relative h-full overflow-hidden p-4">
                  <div
                    className="absolute left-0 top-0 h-full w-[3px]"
                    style={{ background: "linear-gradient(var(--flux), transparent)" }}
                  />
                  <div className="mono-tag">{b.k}</div>
                  <p className="mt-1.5 text-[13.5px] leading-relaxed text-ink-dim">
                    <FormattedText text={b.v} />
                  </p>
                </div>
              </Reveal>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {briefingReady && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="mt-6 flex justify-end"
          >
            <PeButton variant="flux" onClick={() => goto("storyboard")} data-testid="goto-storyboard">
              Storyboard →
            </PeButton>
          </motion.div>
        )}
      </AnimatePresence>
    </StageScroll>
  );
}
