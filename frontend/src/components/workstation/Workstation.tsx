import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import { PostEngineProvider, usePE } from "@/lib/pe-store";
import { AmbientField } from "./AmbientField";
import { ContextBar } from "./ContextBar";
import { DevDrawer } from "./DevDrawer";
import { GamePopup } from "./GamePopup";
import { PipelineRail } from "./PipelineRail";
import { ErrorAccordion } from "./ui";
import { AgentsStage } from "./stages/AgentsStage";
import { EntryStage } from "./stages/EntryStage";
import { InterviewStage } from "./stages/InterviewStage";
import { BriefingStage } from "./stages/BriefingStage";
import { StoryboardStage } from "./stages/StoryboardStage";
import { DraftsStage } from "./stages/DraftsStage";
import { CompositionStage } from "./stages/CompositionStage";
import { SegmentationStage } from "./stages/SegmentationStage";
import { EvaluationStage } from "./stages/EvaluationStage";
import { ExportStage } from "./stages/ExportStage";

export function Workstation() {
  return (
    <PostEngineProvider>
      <Shell />
    </PostEngineProvider>
  );
}

type Appearance = "dark" | "light";

function Shell() {
  const { stage, error, statusText, interviewFocus } = usePE();
  const [dev, setDev] = useState(false);
  const [appearance, setAppearance] = useState<Appearance>("dark");
  const collapseChrome = stage === "interview" && interviewFocus;

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setDev((d) => !d);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  useEffect(() => {
    const stored = window.localStorage.getItem("pe-ui-theme");
    if (stored === "dark" || stored === "light") {
      setAppearance(stored);
      return;
    }
    const preferredDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    setAppearance(preferredDark ? "dark" : "light");
  }, []);

  useEffect(() => {
    document.documentElement.dataset.uiTheme = appearance;
    document.documentElement.classList.toggle("dark", appearance === "dark");
    window.localStorage.setItem("pe-ui-theme", appearance);
  }, [appearance]);

  const toggleAppearance = () => {
    setAppearance((current) => (current === "dark" ? "light" : "dark"));
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg text-ink">
      <AmbientField />
      <AnimatePresence initial={false}>
        {!collapseChrome && (
          <motion.div
            key="pipeline"
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 248, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: "spring", stiffness: 320, damping: 34 }}
            className="shrink-0 overflow-hidden"
          >
            <PipelineRail />
          </motion.div>
        )}
      </AnimatePresence>
      <div className="flex min-w-0 flex-1 flex-col">
        {!collapseChrome && (
          <ContextBar
            appearance={appearance}
            onToggleAppearance={toggleAppearance}
            onOpenDev={() => setDev(true)}
          />
        )}
        {error ? (
          <div className="px-3 py-2">
            <ErrorAccordion
              title="Erro na execução"
              details={error}
            />
          </div>
        ) : statusText ? (
          <div className="border-b border-hairline px-5 py-1.5 font-mono text-[11px] text-ink-faint">
            {statusText}
          </div>
        ) : null}
        <main className="relative min-h-0 flex-1">
          <AnimatePresence mode="wait">
            <motion.div
              key={stage}
              initial={{ opacity: 0, y: 18, filter: "blur(6px)" }}
              animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
              exit={{ opacity: 0, y: -14, filter: "blur(6px)" }}
              transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
              className="absolute inset-0"
            >
              <StageView stage={stage} />
            </motion.div>
          </AnimatePresence>
        </main>
      </div>
      <DevDrawer open={dev} onClose={() => setDev(false)} />
      <GamePopup />
    </div>
  );
}

function StageView({ stage }: { stage: string }) {
  switch (stage) {
    case "agents": return <AgentsStage />;
    case "entry": return <EntryStage />;
    case "interview": return <InterviewStage />;
    case "briefing": return <BriefingStage />;
    case "storyboard": return <StoryboardStage />;
    case "drafts": return <DraftsStage />;
    case "composition": return <CompositionStage />;
    case "segmentation": return <SegmentationStage />;
    case "evaluation": return <EvaluationStage />;
    case "export": return <ExportStage />;
    default: return null;
  }
}
