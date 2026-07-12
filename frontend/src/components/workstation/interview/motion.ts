import { useReducedMotion } from "motion/react";

const EASE = [0.22, 1, 0.36, 1] as const;

export function useMotionSafe() {
  const reduced = useReducedMotion() ?? false;
  return {
    reduced,
    ease: EASE,
    spring: reduced
      ? { duration: 0.01 }
      : { type: "spring" as const, stiffness: 280, damping: 30 },
    softSpring: reduced
      ? { duration: 0.01 }
      : { type: "spring" as const, stiffness: 200, damping: 26 },
    duration: reduced ? 0.01 : 0.45,
  };
}

export const questionExit = (reduced: boolean) =>
  reduced
    ? { opacity: 0 }
    : { opacity: 0, y: -18, scale: 0.98, filter: "blur(3px)" };

export const questionEnter = (reduced: boolean) =>
  reduced
    ? { opacity: 1 }
    : { opacity: 1, y: 0, scale: 1, filter: "blur(0px)" };

export const questionInitial = (reduced: boolean) =>
  reduced
    ? { opacity: 0 }
    : { opacity: 0, y: 28, scale: 0.985, filter: "blur(4px)" };
