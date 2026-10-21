import { Bounds, Center, OrbitControls, useBounds, useGLTF } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import type * as THREE from "three";
import { Component, Suspense, useEffect, useState, type ErrorInfo, type ReactNode } from "react";
import { Tools } from "./ViewerHeader";

const HOME: [number, number, number] = [2, 1.5, 2.5];

// A failed GLB load throws inside the render tree; show it instead of a blank pane.
class LoadError extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("MeshView: could not load the mesh", error, info.componentStack);
  }
  render() {
    return this.state.failed
      ? <div className="viewer-empty">could not load the mesh</div>
      : this.props.children;
  }
}

function Model({ src }: { src: string }) {
  const { scene } = useGLTF(src, false);   // false: no Draco decoder from a CDN
  useEffect(() => { return () => useGLTF.clear(src); }, [src]);
  return <Center><primitive object={scene} /></Center>;
}

/** Must sit inside <Bounds>. Returns the camera to its home direction, recentres the orbit target
 *  (also after a pan) and re-fits when `nonce` changes. */
function Refit({ nonce }: { nonce: number }) {
  const api = useBounds();
  const camera = useThree((s) => s.camera);
  const controls = useThree((s) => s.controls) as { target: THREE.Vector3; update: () => void } | null;
  useEffect(() => {
    if (nonce === 0) return;
    camera.position.set(...HOME);
    const { center } = api.refresh().getSize();
    if (controls) { controls.target.copy(center); controls.update(); }
    api.clip().fit();
  }, [nonce, api, camera, controls]);
  return null;
}

export function MeshView({ src }: { src: string }) {
  const [nonce, setNonce] = useState(0);
  return (
    <LoadError>
      <div style={{ position: "absolute", inset: 0 }}>
        <Canvas camera={{ position: HOME, fov: 40 }} gl={{ alpha: true }}>
          <ambientLight intensity={0.7} />
          <directionalLight position={[3, 5, 4]} intensity={1.4} />
          <Suspense fallback={null}>
            <Bounds fit clip observe margin={1.2}>
              <Model src={src} />
              <Refit nonce={nonce} />
            </Bounds>
          </Suspense>
          <OrbitControls makeDefault />
        </Canvas>
      </div>
      <Tools>
        <button onClick={() => setNonce((n) => n + 1)}>reset view</button>
      </Tools>
    </LoadError>
  );
}
