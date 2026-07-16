import { AnimatePresence, motion } from "motion/react";
import { useEffect, useState } from "react";
import Tetris from "react-tetris";
import { usePE } from "@/lib/pe-store";
import { PeButton } from "./ui";
import { cn } from "@/lib/utils";
import { ModalShell } from "./ModalShell";

const STORAGE_KEY = "pe-tetris-enabled";

type GameTab = "play" | "settings";

export function GamePopup() {
  const { busy } = usePE();
  const [tetrisEnabled, setTetrisEnabled] = useState<boolean>(() => {
    try {
      return window.localStorage.getItem(STORAGE_KEY) === "true";
    } catch {
      return false;
    }
  });
  const [askOpen, setAskOpen] = useState(false);
  const [tetrisOpen, setTetrisOpen] = useState(false);
  const [tab, setTab] = useState<GameTab>("play");
  const [showFloating, setShowFloating] = useState(false);
  const [hasFired, setHasFired] = useState(false);

  useEffect(() => {
    try {
      window.localStorage.setItem(STORAGE_KEY, tetrisEnabled ? "true" : "false");
    } catch {
      // ignore quota / privacy mode errors
    }
  }, [tetrisEnabled]);

  useEffect(() => {
    if (!busy) {
      setHasFired(false);
      return;
    }
    if (busy && tetrisEnabled && !hasFired) {
      setHasFired(true);
      setTetrisOpen(true);
      setTab("play");
    }
  }, [busy, tetrisEnabled, hasFired]);

  useEffect(() => {
    if (busy && !tetrisEnabled) {
      const t = window.setTimeout(() => setShowFloating(true), 2500);
      return () => window.clearTimeout(t);
    }
    setShowFloating(false);
    return undefined;
  }, [busy, tetrisEnabled]);

  const handleEnable = () => {
    setTetrisEnabled(true);
    setAskOpen(false);
  };

  const handleDisable = () => {
    setTetrisEnabled(false);
    setTetrisOpen(false);
    setAskOpen(false);
  };

  return (
    <>
      <AnimatePresence>
        {showFloating && !askOpen && !tetrisOpen && (
          <motion.button
            key="floating-prompt"
            type="button"
            initial={{ opacity: 0, y: 24, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.9 }}
            transition={{ type: "spring", stiffness: 280, damping: 22 }}
            onClick={() => setAskOpen(true)}
            className="fixed z-40 flex items-center gap-2 rounded-full border border-[color-mix(in_oklab,var(--flux)_55%,transparent)] bg-surface/80 px-4 py-2.5 text-[13px] font-medium text-ink shadow-[0_8px_32px_color-mix(in_oklab,var(--flux)_22%,transparent)] backdrop-blur-md hover:border-[color-mix(in_oklab,var(--flux)_80%,transparent)] hover:bg-surface-2"
            style={{
              bottom: "calc(1.5rem + env(safe-area-inset-bottom, 0px))",
              right: "calc(1.5rem + env(safe-area-inset-right, 0px))",
            }}
            data-testid="game-floating-button"
          >
            <motion.span
              aria-hidden
              className="grid h-6 w-6 place-items-center rounded-full bg-[color-mix(in_oklab,var(--flux)_30%,transparent)] text-[12px]"
              animate={{ rotate: [0, -10, 10, -8, 8, 0] }}
              transition={{ duration: 1.4, repeat: Infinity, repeatDelay: 1.6, ease: "easeInOut" }}
            >
              ◯
            </motion.span>
            <span>Vai uma partidinha?</span>
          </motion.button>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {askOpen && (
          <ModalShell onClose={() => setAskOpen(false)} testId="game-ask-modal">
            <div className="px-6 py-5">
              <div className="mono-tag">um minutinho…</div>
              <h2 className="mt-1 font-display text-[18px] font-semibold text-ink">
                Vai uma partidinha de Tetris?
              </h2>
              <p className="mt-2 text-[13px] leading-relaxed text-ink-dim">
                Enquanto a requisição termina, posso abrir um jogo clássico para você
                espairecer. Você poderá desativar essa oferta quando quiser.
              </p>
            </div>
            <div className="flex items-center justify-end gap-2 border-t border-hairline bg-surface-2/40 px-6 py-3.5">
              <PeButton
                variant="ghost"
                onClick={() => setAskOpen(false)}
                data-testid="game-ask-no"
              >
                Não, valeu
              </PeButton>
              <PeButton
                variant="flux"
                onClick={handleEnable}
                data-testid="game-ask-yes"
              >
                Sim, abrir o Tetris
              </PeButton>
            </div>
          </ModalShell>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {tetrisOpen && (
          <ModalShell
            onClose={() => setTetrisOpen(false)}
            testId="game-tetris-modal"
            maxWidth="max-w-3xl"
            closeOnBackdrop={false}
          >
            <div className="flex items-center justify-between border-b border-hairline px-5 py-3">
              <div className="flex items-center gap-2">
                <div className="mono-tag">game break</div>
                <div className="font-display text-[15px] font-semibold text-ink">
                  Tetris
                </div>
              </div>
              <button
                type="button"
                onClick={() => setTetrisOpen(false)}
                className="grid h-7 w-7 place-items-center rounded-md text-ink-faint hover:bg-surface-2 hover:text-ink"
                data-testid="game-close"
                aria-label="Fechar"
              >
                ✕
              </button>
            </div>
            <div className="flex gap-1 border-b border-hairline px-3 py-2">
              {(["play", "settings"] as GameTab[]).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTab(t)}
                  className={cn(
                    "relative rounded-md px-3 py-1.5 font-mono text-[11px] uppercase tracking-wide transition-colors",
                    tab === t ? "text-ink" : "text-ink-faint hover:text-ink-dim",
                  )}
                  data-testid={`game-tab-${t}`}
                >
                  {tab === t && (
                    <motion.span
                      layoutId="game-tab"
                      className="absolute inset-0 rounded-md bg-surface-2"
                    />
                  )}
                  <span className="relative z-10">
                    {t === "play" ? "Jogo" : "Configurações"}
                  </span>
                </button>
              ))}
            </div>
            <div className="flex-1 overflow-auto" data-testid={`game-panel-${tab}`}>
              {tab === "play" ? (
                <TetrisCanvas />
              ) : (
                <GameSettings enabled={tetrisEnabled} onDisable={handleDisable} />
              )}
            </div>
          </ModalShell>
        )}
      </AnimatePresence>
    </>
  );
}

function TetrisCanvas() {
  return (
    <div
      className="flex items-center justify-center bg-[oklch(0.10_0.012_265)] p-6"
      style={{ minHeight: 480 }}
      data-testid="game-tetris-canvas"
    >
      <Tetris
        keyboardControls={{
          down: "MOVE_DOWN",
          left: "MOVE_LEFT",
          right: "MOVE_RIGHT",
          space: "HARD_DROP",
          z: "FLIP_COUNTERCLOCKWISE",
          x: "FLIP_CLOCKWISE",
          up: "FLIP_CLOCKWISE",
          p: "TOGGLE_PAUSE",
          c: "HOLD",
          shift: "HOLD",
        }}
      >
        {({ Gameboard, HeldPiece, PieceQueue, points, linesCleared, level, state, controller }) => (
          <div className="flex items-start gap-4">
            <div className="flex flex-col gap-2">
              <div className="inset-panel px-3 py-2">
                <div className="mono-tag !text-[9px]">hold</div>
                <div className="mt-1">
                  <HeldPiece />
                </div>
              </div>
              <div className="inset-panel px-3 py-2 font-mono text-[11px] text-ink-dim">
                <Stat label="pontos" value={points} />
                <Stat label="linhas" value={linesCleared} />
                <Stat label="nível" value={level} />
                <Stat label="estado" value={state} />
              </div>
              <div className="flex flex-col gap-1">
                <PeButton variant="ghost" onClick={controller.pause}>Pausar</PeButton>
                <PeButton variant="ghost" onClick={controller.resume}>Retomar</PeButton>
                <PeButton variant="ghost" onClick={controller.restart}>Reiniciar</PeButton>
              </div>
            </div>
            <div className="inset-panel p-2">
              <Gameboard />
            </div>
            <div className="inset-panel px-3 py-2">
              <div className="mono-tag !text-[9px]">próximas</div>
              <div className="mt-1">
                <PieceQueue />
              </div>
            </div>
          </div>
        )}
      </Tetris>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="flex items-center justify-between gap-3 py-0.5">
      <span className="text-ink-faint">{label}</span>
      <span className="text-ink">{value}</span>
    </div>
  );
}

function GameSettings({
  enabled,
  onDisable,
}: {
  enabled: boolean;
  onDisable: () => void;
}) {
  return (
    <div className="space-y-5 p-6">
      <div>
        <div className="mono-tag">popup de jogo</div>
        <h3 className="mt-1 font-display text-[16px] font-semibold text-ink">
          Abrir o Tetris durante requisições
        </h3>
        <p className="mt-1 text-[12.5px] leading-relaxed text-ink-dim">
          Quando ativado, o jogo abre automaticamente em uma janela flutuante toda
          vez que uma requisição demorar mais que o normal. Desative para voltar a
          ver apenas o botão "Vai uma partidinha?".
        </p>
      </div>
      <div className="inset-panel flex items-center justify-between gap-4 p-4">
        <div>
          <div className="text-[13px] font-medium text-ink">
            Popup automático
          </div>
          <div className="mt-0.5 text-[11.5px] text-ink-faint">
            Status atual: <span className="text-ink">{enabled ? "ativado" : "desativado"}</span>
          </div>
        </div>
        <button
          type="button"
          onClick={onDisable}
          role="switch"
          aria-checked={enabled}
          data-testid="game-toggle"
          className={cn(
            "relative h-6 w-11 rounded-full border transition-colors",
            enabled
              ? "border-[color-mix(in_oklab,var(--flux)_60%,transparent)] bg-[color-mix(in_oklab,var(--flux)_45%,var(--surface))]"
              : "border-hairline bg-surface-2",
          )}
        >
          <motion.span
            layout
            transition={{ type: "spring", stiffness: 500, damping: 32 }}
            className={cn(
              "absolute top-0.5 h-4 w-4 rounded-full bg-white shadow",
              enabled ? "left-[22px]" : "left-0.5",
            )}
          />
        </button>
      </div>
      <div className="text-[11.5px] text-ink-faint">
        Dica: o jogo usa as setas do teclado. <kbd className="inset-panel px-1.5 py-0.5 font-mono text-[10px]">Espaço</kbd> derruba a peça.
      </div>
    </div>
  );
}
