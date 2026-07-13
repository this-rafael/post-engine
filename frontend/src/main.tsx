import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Workstation } from "@/components/workstation/Workstation";
import "@/styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Workstation />
  </StrictMode>,
);
