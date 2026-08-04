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

function tipTarget(wrap: HTMLElement): HTMLElement {
  // Prefer the raised fan-card so portaled tips follow hover/armed lift.
  return (
    (wrap.querySelector(".fan-card") as HTMLElement | null) ?? wrap
  );
}

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
    const wrap = wrapRef.current;
    const gap = 8;

    const update = () => {
      const rect = tipTarget(wrap).getBoundingClientRect();
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
    };

    update();

    // Follow CSS lift transitions and armed/expand class changes while open.
    let raf = 0;
    let frames = 0;
    const tick = () => {
      update();
      frames += 1;
      if (frames < 24) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    const obs = new MutationObserver(() => {
      frames = 0;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(tick);
    });
    obs.observe(wrap, {
      attributes: true,
      subtree: true,
      attributeFilter: ["class", "style"],
    });

    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      cancelAnimationFrame(raf);
      obs.disconnect();
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
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
