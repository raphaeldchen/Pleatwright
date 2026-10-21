import { useEffect, useRef, useState } from "react";
import { usePanZoom } from "../usePanZoom";
import { Tools } from "./ViewerHeader";

const DROP = "script, foreignObject, style, iframe, object, embed, image, use";

/** Strip anything active from a parsed SVG: dangerous elements, on* handlers and
 * any href that is not a plain #fragment. */
function sanitize(svg: Element) {
  svg.querySelectorAll(DROP).forEach((n) => n.remove());
  for (const el of [svg, ...Array.from(svg.querySelectorAll("*"))]) {
    for (const a of Array.from(el.attributes)) {
      const name = a.name.toLowerCase();
      const isHref = name === "href" || name === "xlink:href" || name.endsWith(":href");
      if (name.startsWith("on") || (isHref && !/^#[^\s]*$/.test(a.value.trim()))) {
        el.removeAttribute(a.name);
      }
    }
  }
}

/** A Pleatwright CP SVG, inlined so its creases can be toggled by colour
 * (COrigami semantics: red mountain, blue valley, black border, green hinge). The file is never
 * changed; styles.css only recolours red/blue on screen to --mountain/--valley. */
export function CPView({ src, controls }: { src: string; controls?: { hinges: boolean; mv: boolean } }) {
  const host = useRef<HTMLDivElement>(null);
  const [hinges, setHinges] = useState(true);
  const [mv, setMv] = useState(true);
  const [failed, setFailed] = useState(false);
  const pz = usePanZoom();
  // With `controls` the parent owns the toggles (and their header buttons), so several views share them.
  const showHinges = controls ? controls.hinges : hinges, showMv = controls ? controls.mv : mv;
  useEffect(() => {
    let live = true;
    setFailed(false);
    fetch(src)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => {
        if (!live || !host.current) return;
        const doc = new DOMParser().parseFromString(text, "image/svg+xml");
        const svg = doc.documentElement;
        if (svg.nodeName !== "svg") throw new Error("not an svg");
        sanitize(svg);
        host.current.replaceChildren(document.importNode(svg, true));
      })
      .catch(() => { if (live) setFailed(true); });
    return () => { live = false; };
  }, [src]);
  if (failed) return <div className="viewer-empty">could not load {src.split("/").pop()}</div>;
  return (
    <>
      {!controls && <Tools>
        <button className={hinges ? "on" : ""} aria-pressed={hinges} onClick={() => setHinges(!hinges)}>hinges</button>
        <button className={mv ? "on" : ""} aria-pressed={mv} onClick={() => setMv(!mv)}>M/V colours</button>
      </Tools>}
      <div className="pz" {...pz.handlers}>
        <div ref={host} style={pz.style}
             className={`cp${showHinges ? "" : " no-hinges"}${showMv ? "" : " mono"}`} />
      </div>
    </>
  );
}
