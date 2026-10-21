// The instrument that produced sim-planarity.json.
//
// Evaluated in a HEADED browser pane against the vendored Origami Simulator at
//   web/frontend/dist/simulator/index.html?embed=1
// It replicates `mcp_harness/sim_capture.py`'s SimSession.capture protocol
// (loadFold -> setFold -> settle -> getFoldedGeometry) because playwright is
// not installed in this venv and no browser cache exists.
//
// WHAT LICENSES THE READINGS. The anchor star-4 base reproduced
// `sim_capture.ANCHOR_DISP` = 1.3109 EXACTLY through this path. Without that
// control none of the other numbers would be worth anything -- and the control
// earned its keep: the first dense run returned NO geometry at all, which would
// have read as "the dense CP does not fold". The real cause was the solver
// parked while the browser pane was not fronted, with no exception and no
// warning on any channel. `modelNodes` going 0 -> 380 is the reliable signal
// that the solver is live; `document.visibilityState` is NOT (it read "hidden"
// on both the failed and the successful run).
//
// WHAT PLANARITY MEANS. A flat-folded sheet is a PLANE, so the smallest
// principal standard deviation of the folded vertex cloud must collapse.
// planarity = smallest/largest principal std dev. This solver has NO
// self-collision (thickenModel/thickenOffset are rendering options), so a
// residual is NOT paper thickness -- the solver would collapse to a plane if
// that were its local minimum. A residual means it is stuck.

function planarity(P) {
  const n = P.length, m = [0, 0, 0];
  for (const p of P) for (let k = 0; k < 3; k++) m[k] += p[k] / n;
  const A = [[0,0,0],[0,0,0],[0,0,0]];
  for (const p of P) {
    const d = [p[0]-m[0], p[1]-m[1], p[2]-m[2]];
    for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) A[i][j] += d[i]*d[j]/n;
  }
  // analytic symmetric-3x3 eigenvalues (Smith)
  const p1 = A[0][1]**2 + A[0][2]**2 + A[1][2]**2;
  const q = (A[0][0] + A[1][1] + A[2][2]) / 3;
  const p2 = (A[0][0]-q)**2 + (A[1][1]-q)**2 + (A[2][2]-q)**2 + 2*p1;
  const pp = Math.sqrt(p2 / 6);
  const B = [[0,0,0],[0,0,0],[0,0,0]];
  for (let i = 0; i < 3; i++) for (let j = 0; j < 3; j++) B[i][j] = (A[i][j] - (i===j?q:0)) / pp;
  const det = B[0][0]*(B[1][1]*B[2][2]-B[1][2]*B[2][1])
            - B[0][1]*(B[1][0]*B[2][2]-B[1][2]*B[2][0])
            + B[0][2]*(B[1][0]*B[2][1]-B[1][1]*B[2][0]);
  const r = Math.max(-1, Math.min(1, det/2));
  const phi = Math.acos(r) / 3;
  const e1 = q + 2*pp*Math.cos(phi);
  const e3 = q + 2*pp*Math.cos(phi + 2*Math.PI/3);
  const e2 = 3*q - e1 - e3;
  const sd = [e1, e2, e3].map(v => Math.sqrt(Math.max(v, 0))).sort((a,b) => b-a);
  return { sd: sd.map(v => +v.toFixed(5)), planarity: +(sd[2]/sd[0]).toFixed(5) };
}

// Install once per page load, BEFORE loadFold. Capture the error branch too:
// omitting it turns a bridge exception into an indistinguishable "no reply".
function install() {
  window.__cap = null; window.__err = null;
  window.addEventListener('message', function (e) {
    const d = e.data || {};
    if (d.type === 'foldedGeometry') window.__cap = d;
    else if (d.type === 'error') window.__err = d.message;
  });
}

async function load(path, percent) {
  const fold = await (await fetch(path)).json();
  window.postMessage({ type: 'loadFold', fold }, location.origin);
  window.postMessage({ type: 'setFold', percent: percent }, location.origin);
  return { verts: fold.vertices_coords.length,
           creases: fold.edges_assignment.filter(a => a === 'M' || a === 'V').length };
}

// The documented alternative drive: memory records clean bases jamming when
// driven straight to 100%. Measured here to make no difference (0.0725 ramped
// vs 0.0648 jumped on dense lizard), so the non-flatness is not a drive artifact.
async function ramp(fromPct, toPct, stepPct, holdMs) {
  for (let p = fromPct; p <= toPct; p += stepPct) {
    window.postMessage({ type: 'setFold', percent: p }, location.origin);
    await new Promise(r => setTimeout(r, holdMs));
  }
}

async function grab(label) {
  window.__cap = null;
  window.postMessage({ type: 'getFoldedGeometry' }, location.origin);
  const t = Date.now();
  while (!window.__cap && Date.now() - t < 8000) await new Promise(r => setTimeout(r, 200));
  if (!window.__cap) return { label, FAIL: 'no reply', err: window.__err };
  const V = window.__cap.vertices_coords, F = window.__cap.flat_coords;
  let md = 0, nan = 0;
  for (let i = 0; i < V.length; i++) {
    if (!V[i].every(Number.isFinite)) { nan++; continue; }
    let s = 0; for (let k = 0; k < 3; k++) { const d = V[i][k] - F[i][k]; s += d*d; }
    md = Math.max(md, Math.sqrt(s));
  }
  // DISP_GATE 0.10 is sim_capture's anti-vacuous gate: the fold must MOVE.
  // It is not a correctness gate -- a tangle also displaces.
  return Object.assign({ label, verts: V.length, nonFinite: nan,
                         maxDisp: +md.toFixed(4), pastDispGate: md >= 0.10 },
                       planarity(V));
}
