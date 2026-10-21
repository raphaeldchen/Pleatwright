import { fileUrl } from "../api";
import { outputTitle, summaryLine } from "../runStore";
import { stageNum, type Output } from "../types";

export function StageBlock({ runId, o, selected, onClick }: {
  runId: string; o: Output; selected: boolean; onClick: () => void;
}) {
  const img = o.files.find((f) => /\.(png|jpe?g|webp|svg)$/i.test(f));
  return (
    <button className={`block${selected ? " sel" : ""}`} onClick={onClick}>
      {img ? <img className="thumb" src={fileUrl(runId, img)} alt={outputTitle(o)} />
           : <span className="thumb">{o.stage === "mesh" || o.stage === "model" ? "3D" : "—"}</span>}
      <span className="num">{stageNum(o.stage)}</span>
      <span className="title">{outputTitle(o)}</span>
      <span className="sum">{summaryLine(o)}</span>
    </button>
  );
}
