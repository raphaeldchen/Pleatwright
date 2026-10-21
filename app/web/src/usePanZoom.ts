import { useCallback, useRef, useState } from "react";

/** Wheel to zoom about the cursor, drag to pan, double-click to reset. */
export function usePanZoom() {
  const [t, setT] = useState({ x: 0, y: 0, k: 1 });
  const drag = useRef<{ x: number; y: number } | null>(null);
  const onWheel = useCallback((e: React.WheelEvent) => {
    const r = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    setT((p) => {
      const k = Math.min(40, Math.max(0.2, p.k * Math.exp(-e.deltaY * 0.0015)));
      return { k, x: px - ((px - p.x) * k) / p.k, y: py - ((py - p.y) * k) / p.k };
    });
  }, []);
  const onPointerDown = (e: React.PointerEvent) => {
    drag.current = { x: e.clientX, y: e.clientY };
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    const dx = e.clientX - drag.current.x, dy = e.clientY - drag.current.y;
    drag.current = { x: e.clientX, y: e.clientY };
    setT((p) => ({ ...p, x: p.x + dx, y: p.y + dy }));
  };
  const onPointerUp = () => { drag.current = null; };
  const reset = () => setT({ x: 0, y: 0, k: 1 });
  return {
    handlers: { onWheel, onPointerDown, onPointerMove, onPointerUp, onPointerCancel: onPointerUp,
                onLostPointerCapture: onPointerUp, onDoubleClick: reset },
    style: { transform: `translate(${t.x}px, ${t.y}px) scale(${t.k})`, width: "100%", height: "100%" },
    reset,
  };
}
