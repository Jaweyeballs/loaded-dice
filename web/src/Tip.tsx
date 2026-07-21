import {
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";

type Props = {
  text: string;
  children: ReactNode;
  className?: string;
  /** Prefer tip growing inward from screen edges (power left / trading right). */
  tipAlign?: "center" | "start" | "end";
};

type TipPos = {
  top: number;
  left: number;
  transform: string;
};

/** Hover/focus textbox for card ability copy (portaled so panels can't clip it). */
export function Tip({ text, children, className = "", tipAlign = "center" }: Props) {
  const wrapRef = useRef<HTMLSpanElement>(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState<TipPos | null>(null);
  const preferBelow = className.includes("tip-below");

  useLayoutEffect(() => {
    if (!open || !wrapRef.current) {
      setPos(null);
      return;
    }
    const rect = wrapRef.current.getBoundingClientRect();
    const gap = 8;
    if (preferBelow) {
      const left =
        tipAlign === "start"
          ? rect.left
          : tipAlign === "end"
            ? rect.right
            : rect.left + rect.width / 2;
      const transform =
        tipAlign === "start"
          ? "translate(0, 0)"
          : tipAlign === "end"
            ? "translate(-100%, 0)"
            : "translate(-50%, 0)";
      setPos({ top: rect.bottom + gap, left, transform });
      return;
    }
    const left =
      tipAlign === "start"
        ? rect.left
        : tipAlign === "end"
          ? rect.right
          : rect.left + rect.width / 2;
    const transform =
      tipAlign === "start"
        ? "translate(0, -100%)"
        : tipAlign === "end"
          ? "translate(-100%, -100%)"
          : "translate(-50%, -100%)";
    setPos({ top: rect.top - gap, left, transform });
  }, [open, tipAlign, preferBelow, text]);

  return (
    <span
      ref={wrapRef}
      className={`tip-wrap ${className}`.trim()}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      {children}
      {open &&
        pos &&
        createPortal(
          <span
            className="tip-box tip-portal"
            role="tooltip"
            style={
              {
                top: pos.top,
                left: pos.left,
                transform: pos.transform,
              } as CSSProperties
            }
          >
            {text}
          </span>,
          document.body,
        )}
    </span>
  );
}
