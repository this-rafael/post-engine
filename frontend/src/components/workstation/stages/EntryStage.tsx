import { AnimatePresence, motion } from "motion/react";
import { usePE } from "@/lib/pe-store";
import { Field, PeButton, Reveal } from "../ui";
import { StageHeader, StageScroll } from "./common";

export function EntryStage() {
  const {
    session,
    setSession,
    continueToInterview,
    saveSession,
    busy,
    snapshot,
  } = usePE();

  const plataformas = (snapshot?.options?.plataformas ?? []) as Array<{ label: string; value: string }>;
  const tipos = (snapshot?.options?.tipos_de_post ?? []) as Array<{ label: string; value: string }>;

  return (
    <StageScroll>
      <StageHeader
        eyebrow="etapa 01 · intenção editorial"
        title="Definir a intenção do conteúdo"
        desc="A entrada inicial semeia a sessão. A partir daqui, cada etapa herda e enriquece esse estado."
      />

      <Reveal>
        <div className="panel space-y-4 p-5">
          <Field
            label="tema"
            value={session.theme}
            onChange={(v) => setSession({ theme: v })}
            placeholder="Assunto principal do conteúdo"
          />
          <div className="grid grid-cols-2 gap-4">
            <SelectField
              label="plataforma"
              value={session.platformValue}
              options={plataformas}
              onChange={(value, label) => setSession({ platformValue: value, platform: label })}
            />
            <SelectField
              label="tipo de conteúdo"
              value={session.contentTypeValue}
              options={tipos}
              onChange={(value, label) => setSession({ contentTypeValue: value, contentType: label })}
            />
          </div>
          <Field
            label="objetivo"
            multiline
            rows={3}
            value={session.objective}
            onChange={(v) => setSession({ objective: v })}
            placeholder="Resultado editorial que o autor quer provocar"
          />
          <Field
            label="personalidade"
            value={session.personality}
            onChange={(v) => setSession({ personality: v })}
            placeholder="Tom pretendido"
          />
          <div className="flex gap-3">
            <PeButton variant="outline" onClick={() => saveSession()} disabled={busy}>
              Salvar entrada
            </PeButton>
            <PeButton variant="flux" onClick={() => continueToInterview()} loading={busy}>
              Ir para entrevista →
            </PeButton>
          </div>
        </div>
      </Reveal>
    </StageScroll>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: Array<{ label: string; value: string }>;
  onChange: (value: string, label: string) => void;
}) {
  return (
    <label className="block">
      <div className="eyebrow mb-1.5">{label}</div>
      <select
        className="field w-full px-3 py-2.5 text-[14px] outline-none"
        value={value}
        onChange={(e) => {
          const opt = options.find((o) => o.value === e.target.value);
          onChange(e.target.value, opt?.label ?? e.target.value);
        }}
      >
        <option value="" disabled>
          Selecione...
        </option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}
