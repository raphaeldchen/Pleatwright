import { usePanZoom } from "../usePanZoom";

export function ImageView({ src }: { src: string }) {
  const pz = usePanZoom();
  return (
    <div className="pz" {...pz.handlers}>
      <img src={src} style={{ ...pz.style, objectFit: "contain" }} draggable={false} />
    </div>
  );
}
