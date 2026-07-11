import { useEffect, useRef } from "react";
import { usePE } from "@/lib/pe-store";

/**
 * Living ambient background. A canvas-free, transform/opacity-driven field of
 * drifting light blooms plus a cursor-reactive glow. Intensity is bound to the
 * global --amb / --flux CSS variables that the phase engine animates.
 */
export function AmbientField() {
  const { phase } = usePE();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf = 0;
    let tx = 0.5;
    let ty = 0.4;
    let cx = 0.5;
    let cy = 0.4;
    const onMove = (e: PointerEvent) => {
      tx = e.clientX / window.innerWidth;
      ty = e.clientY / window.innerHeight;
    };
    window.addEventListener("pointermove", onMove);
    const loop = () => {
      cx += (tx - cx) * 0.06;
      cy += (ty - cy) * 0.06;
      el.style.setProperty("--mx", (cx * 100).toFixed(2) + "%");
      el.style.setProperty("--my", (cy * 100).toFixed(2) + "%");
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
    };
  }, []);

  const active = phase !== "idle";

  return (
    <div ref={ref} className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      {/* deep base vignette */}
      <div
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(140% 120% at 50% -20%, color-mix(in oklab, var(--flux) calc(var(--amb) * 55%), transparent), transparent 55%), radial-gradient(120% 100% at 0% 100%, oklch(0.11 0.02 265), var(--void))",
        }}
      />
      {/* cursor-reactive bloom */}
      <div
        className="absolute inset-0 transition-opacity duration-700"
        style={{
          opacity: active ? 0.9 : 0.5,
          background:
            "radial-gradient(420px 420px at var(--mx,50%) var(--my,40%), color-mix(in oklab, var(--flux) calc(var(--amb) * 60%), transparent), transparent 70%)",
        }}
      />
      {/* drifting blooms */}
      <div
        className="absolute -left-40 top-1/3 h-[40rem] w-[40rem] rounded-full blur-[120px]"
        style={{
          background: "conic-gradient(from 120deg, color-mix(in oklab, var(--flux) 30%, transparent), transparent 60%)",
          animation: "flux-pan 26s linear infinite",
          opacity: 0.5,
        }}
      />
      <div
        className="absolute -right-52 bottom-0 h-[46rem] w-[46rem] rounded-full blur-[140px]"
        style={{
          background: "radial-gradient(circle, color-mix(in oklab, var(--flux) 26%, transparent), transparent 62%)",
          animation: "breathe 9s ease-in-out infinite",
        }}
      />
      {/* fine grid */}
      <div
        className="absolute inset-0 opacity-[0.5]"
        style={{
          backgroundImage:
            "linear-gradient(oklch(1 0 0 / 0.02) 1px, transparent 1px), linear-gradient(90deg, oklch(1 0 0 / 0.02) 1px, transparent 1px)",
          backgroundSize: "64px 64px",
          maskImage: "radial-gradient(120% 100% at 50% 0%, black, transparent 80%)",
        }}
      />
      {/* grain */}
      <div
        className="absolute inset-0 opacity-[0.035] mix-blend-overlay"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='120'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
    </div>
  );
}
