interface FormattedTextProps {
  text: string;
  className?: string;
}

export function FormattedText({ text, className = "" }: FormattedTextProps) {
  const processed = text.replace(/\\n/g, "\n");
  return (
    <span className={`whitespace-pre-wrap ${className}`.trim()}>
      {processed}
    </span>
  );
}
