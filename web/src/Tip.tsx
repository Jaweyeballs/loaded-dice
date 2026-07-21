import type { ReactNode } from "react";

type Props = {
  text: string;
  children: ReactNode;
  className?: string;
  /** Prefer tip growing inward from screen edges (power left / trading right). */
  tipAlign?: "center" | "start" | "end";
};

/** Hover/focus textbox for card ability copy. */
export function Tip({ text, children, className = "", tipAlign = "center" }: Props) {
  const alignClass =
    tipAlign === "start" ? "tip-start" : tipAlign === "end" ? "tip-end" : "";
  return (
    <span className={`tip-wrap ${alignClass} ${className}`.trim()}>
      {children}
      <span className="tip-box" role="tooltip">
        {text}
      </span>
    </span>
  );
}
