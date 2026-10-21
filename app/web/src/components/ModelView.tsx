import { OrbitControls } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";
import {
  bounds, fitOnto, framePositions, makeGeometries, posePositions, setPose, validateFold, viewPose, VIEW_UP, type FoldFile,
} from "../fold";
import { ImageView } from "./ImageView";
import { Tools } from "./ViewerHeader";

type Sphere = { center: [number, number, number]; radius: number };

function Paper({ fold, pct, end }: { fold: FoldFile; pct: number; end: Sphere }) {
  // One geometry set per fold. A pose change rewrites the positions in place (setPose) before paint, so
  // the shared index buffer is never freed and re-uploaded while the fold animates.
  const geos = useMemo(() => makeGeometries(fold, fold.file_frames.length - 1), [fold]);
  useEffect(() => {
    return () => { geos.sheet.dispose(); geos.m.dispose(); geos.v.dispose(); };
  }, [geos]);
  const P = useMemo(() => posePositions(fold, pct), [fold, pct]);
  const fit = fitOnto(end, P);
  useLayoutEffect(() => { setPose(geos, fold, P); }, [geos, fold, P]);
  // frustumCulled is off: the model is always in view, and a stale bounding sphere must never hide it.
  // polygonOffset pushes the sheet back so the crease lines drawn on it do not z-fight.
  // `fit` scales the pose onto the folded model's bounding sphere (fitOnto), so the flat sheet and
  // the folded model fill the same space and the camera never has to move during the fold.
  return (
    <group scale={fit.scale} position={fit.position}>
      <mesh geometry={geos.sheet} frustumCulled={false}>
        <meshStandardMaterial color="#f4efe6" side={THREE.FrontSide} flatShading
                              polygonOffset polygonOffsetFactor={1} polygonOffsetUnits={1} />
      </mesh>
      <mesh geometry={geos.sheet} frustumCulled={false}>
        <meshStandardMaterial color="#d08a2a" side={THREE.BackSide} flatShading
                              polygonOffset polygonOffsetFactor={1} polygonOffsetUnits={1} />
      </mesh>
      {/* --mountain / --valley from styles.css; three.js cannot read CSS variables */}
      <lineSegments geometry={geos.m} frustumCulled={false}><lineBasicMaterial color="#e33b2e" /></lineSegments>
      <lineSegments geometry={geos.v} frustumCulled={false}><lineBasicMaterial color="#2f55d4" /></lineSegments>
    </group>
  );
}

const FOLD_MS = 3000;

type Orbit = { target: THREE.Vector3; update: () => void };

/**
 * Places the camera and orbit target. This is the ONLY code that frames the model: it runs once the
 * controls exist (nonce 0 = the initial view) and again whenever the nonce changes ("reset view").
 * Every frame is drawn fitted onto the folded model's bounding sphere, so both frame that sphere.
 * It never runs because the slider moved.
 */
function Refit({ b, nonce }: { b: Sphere; nonce: number }) {
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as Orbit | null;
  const size = useThree((s) => s.size);
  const latest = useRef({ b, aspect: 1 });
  latest.current = { b, aspect: size.width / Math.max(size.height, 1) };
  const applied = useRef(-1);
  useEffect(() => {
    if (!controls || applied.current === nonce) return;
    applied.current = nonce;
    const { b, aspect } = latest.current;
    const pose = viewPose(b, aspect);
    camera.position.set(...pose.position);
    camera.near = pose.near;
    camera.far = pose.far;
    camera.updateProjectionMatrix();
    controls.target.set(...b.center);
    controls.update();
  }, [nonce, camera, controls]);
  return null;
}

export function ModelView({ foldSrc, overviewSrc }: { foldSrc: string; overviewSrc?: string }) {
  const [fold, setFold] = useState<FoldFile | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pct, setPct] = useState(100);
  const [playing, setPlaying] = useState(false);
  const [overview, setOverview] = useState(false);
  const [resetNonce, setResetNonce] = useState(0);

  useEffect(() => {
    let live = true;
    setFold(null);
    setError(null);
    fetch(foldSrc)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((j: unknown) => {
        const bad = validateFold(j);
        if (bad) throw new Error(bad);
        if (live) setFold(j as FoldFile);
      })
      .catch((e: unknown) => { if (live) setError(e instanceof Error ? e.message : String(e)); });
    return () => { live = false; };
  }, [foldSrc]);

  // Play runs the fold once, flat -> folded, in FOLD_MS, and stops on the folded model (100%).
  // Driven by animation frames (not a timer) so each painted frame shows a fresh blended pose.
  useEffect(() => {
    if (!playing) return;
    let raf = 0, last = performance.now();
    const tick = (now: number) => {
      const dt = now - last;
      last = now;
      setPct((p) => Math.min(100, p + (dt / FOLD_MS) * 100));
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [playing]);
  useEffect(() => { if (playing && pct >= 100) setPlaying(false); }, [playing, pct]);
  const play = () => {
    if (playing) { setPlaying(false); return; }
    if (pct >= 100) setPct(0);          // from the folded end, replay from the flat sheet
    setPlaying(true);
  };

  // Only the initial camera props come from here (the controls are placed by Refit); framed on the last frame.
  const b = useMemo(() => (fold ? bounds(framePositions(fold, fold.file_frames.length - 1)) : null), [fold]);

  if (error) return <div className="viewer-empty">could not load the model: {error}</div>;
  if (!fold || !b) return <div className="viewer-empty">loading model…</div>;
  const pose = viewPose(b);
  return (
    <>
      <Tools>
        {!overview && <button onClick={() => setResetNonce((n) => n + 1)}>reset view</button>}
        {overviewSrc && (
          <button className={overview ? "on" : ""} aria-pressed={overview}
                  onClick={() => { setPlaying(false); setResetNonce(0); setOverview(!overview); }}>overview.png</button>)}
      </Tools>
      {overview && overviewSrc ? <ImageView src={overviewSrc} /> : (
        <>
          <div style={{ position: "absolute", inset: 0 }}>
            <Canvas camera={{ position: pose.position, up: [...VIEW_UP], fov: 40, near: pose.near, far: pose.far }}
                    gl={{ alpha: true }}>
              <ambientLight intensity={0.6} />
              <directionalLight position={[pose.position[0], pose.position[1] + b.radius * 2, pose.position[2]]}
                                intensity={1.3} />
              <Paper fold={fold} pct={pct} end={b} />
              <OrbitControls makeDefault />
              <Refit b={b} nonce={resetNonce} />
            </Canvas>
          </div>
          <div className="foldbar">
            <button className="btn ghost" aria-label={playing ? "Pause" : "Play"} onClick={play}>{playing ? "❚❚" : "▶"}</button>
            <input type="range" min={0} max={100} step="any" value={pct} aria-label="Fold"
                   onChange={(e) => { setPlaying(false); setPct(Number(e.target.value)); }} />
            <span className="pct">{Math.round(pct)}%</span>
          </div>
        </>
      )}
    </>
  );
}
