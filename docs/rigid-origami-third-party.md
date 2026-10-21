# Rigid origami third-party and licensing posture

**Review date:** 2026-07-12
**Phase-0 policy:** Until the product/repository license is chosen, only
permissively licensed dependencies may enter the rigid runtime. GPL,
noncommercial, missing-license, or unclear-license projects are reference-only.
Paper access never grants permission to copy associated code, figures, meshes,
or data.

| Project/source | License/status | Phase-0 use | Decision |
|---|---|---|---|
| Pydantic 2.13 | MIT | strict contracts/schema generation | direct dependency |
| NumPy 2.4 | BSD-3-Clause | rotation primitives | direct dependency |
| jsonschema 4.26 | MIT | independent Draft 2020-12 checks | test dependency |
| FOLD project/spec | MIT code; spec describes itself as a rough draft | pinned interchange profile | integrate profile, do not copy API code |
| Origami Simulator | MIT | approximate comparison viewer | retain, never certificate authority |
| Oriedita | MIT plus Orihime provenance text | optional flat-endpoint lint | retain full notices; lint copy only |
| IPC Toolkit | MIT core; optional `filib` is LGPL-2.1 | future nonlinear CCD spike | candidate; disable `filib` absent approval |
| FCL | BSD-3-Clause | future distance/discrete/CCD cross-check | candidate |
| python-fcl | BSD-3-Clause | Python FCL binding | candidate |
| Trimesh | MIT; collision manager delegates to python-fcl | mesh preprocessing only | optional candidate |
| ORIPA | GPL | external comparison | reference-only pending license decision |
| Rabbit Ear | GPLv3 | graph behavior reference | reference-only |
| Tachi software | proprietary/research-use terms | canonical behavioral comparison | reference/collaboration only |
| Crane | proprietary/noncommercial | UX/manual comparison | reference-only; no commercial use absent permission |
| Unified 2026 research implementation | no repository license observed | paper architecture comparison | reference-only |
| Automating Rigid Origami code | custom noncommercial research/education | inverse-design reference | reference-only |
| SWOMPS repository | no repository license observed | mechanics reference | reference-only |
| Sim-FAST / Sim-FAST-PY | README CC-BY assertion, no conventional license; bundled third-party code | mechanics reference | reference-only pending written review |
| ORI-REVO | MIT | specialized later generator reference | eligible after scope review |

## Dependency admission checklist

Before a new runtime/library dependency is added, record:

- package and pinned version/commit/hash;
- SPDX identifier and primary license URL;
- transitive native dependencies and build flags;
- embedded/library/subprocess/reference-only use;
- required notices and redistribution obligations;
- commercial-use status;
- reviewer and review date;
- fixture/code bytes copied, if any.

## Research-paper handling

Mathematical equations may be independently implemented with citation. Golden
fixtures are generated from documented parameters/equations by an independent
evaluator. They do not copy paper figures or research-repository artifacts.

Key sources:

- Foschi/Hull/Ku paper: CC BY 4.0 author manuscript; independently implement and
  attribute the mathematics.
- He/Guest arXiv paper: arXiv distribution terms; cite, do not copy assets.
- Lang/Magleby/Howell flasher paper: ASME-copyrighted publication; use documented
  construction only after a clean derivation/provenance review.
