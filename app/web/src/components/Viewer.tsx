import { useState } from "react";
import { downloadName, fileUrl } from "../api";
import { isCard } from "../runStore";
import { downloadFiles, viewFiles } from "../viewerFiles";
import type { Output } from "../types";
import { CPView } from "./CPView";
import { LayoutCompare } from "./LayoutCompare";
import { ImageView } from "./ImageView";
import { MeshView } from "./MeshView";
import { ModelView } from "./ModelView";
import { Tools } from "./ViewerHeader";

const ext = (f: string) => f.slice(f.lastIndexOf(".")).toLowerCase();
const IMG = [".png", ".jpg", ".jpeg", ".webp"];

export function Viewer({ runId, output, allOutputs, onSelect }: {
  runId: string; output: Output | null; allOutputs: Output[]; onSelect: (key: string) => void;
}) {
  const [fileIx, setFileIx] = useState(0);
  if (!output) return <div className="viewer-empty">Outputs appear here as each stage finishes.</div>;
  if (isCard(output.summary.layout_choice)) return <LayoutCompare runId={runId} output={output} />;
  const files = viewFiles(output);
  if (files.length === 0)
    return <div className="viewer-empty">{String(output.summary.note ?? "nothing to show")}</div>;
  const f = files[Math.min(fileIx, files.length - 1)];
  const url = fileUrl(runId, f);
  const overviewFile = output.files.find((x) => x.endsWith("overview.png"));
  const overviewSrc = overviewFile ? fileUrl(runId, overviewFile) : undefined;
  const rounds = output.round != null ? allOutputs.filter((o) => o.stage === output.stage && o.round != null) : [];
  const downloads = downloadFiles(output, f, allOutputs);
  return (
    <>
      {/* a model output has only model.fold; ModelView puts its own tools in the header */}
      {ext(f) !== ".fold" && <Tools>
        {rounds.map((o) => (
          <button key={o.key} className={o.key === output.key ? "on" : ""}
                  aria-current={o.key === output.key ? "true" : undefined}
                  onClick={() => onSelect(o.key)}>round {(o.round ?? 0) + 1}</button>))}
        {files.length > 1 && files.map((x, i) => (
          <button key={x} className={x === f ? "on" : ""} aria-current={x === f ? "true" : undefined} onClick={() => setFileIx(i)}>
            {x.split("/").pop()}</button>))}
      </Tools>}
      {downloads.length > 0 && <Tools>
        {downloads.map((x) => (
          <a key={x} className="dl" href={fileUrl(runId, x)} download={downloadName(runId, x)}
             title={`Download ${x.split("/").pop()}`}>↓ {x.split("/").pop()}</a>))}
      </Tools>}
      {IMG.includes(ext(f)) && <ImageView key={url} src={url} />}
      {ext(f) === ".svg" && <CPView key={url} src={url} />}
      {ext(f) === ".glb" && <MeshView key={url} src={url} />}
      {ext(f) === ".fold" && <ModelView key={url} foldSrc={url} overviewSrc={overviewSrc} />}
    </>
  );
}
