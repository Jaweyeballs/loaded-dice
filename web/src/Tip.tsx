import type { ReactNode } from "react";

type Props = {
  text: string;
  children: ReactNode;
  className?: string;
};

/** Hover/focus textbox for card ability copy. */
export function Tip({ text, children, className = "" }: Props) {
  return (
    <span className={`tip-wrap ${className}`.trim()}>
      {children}
      <span className="tip-box" role="tooltip">
        {text}
      </span>
    </span>
  );
}
