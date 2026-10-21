"""Package the nine photo-derived meshes as a self-contained handoff bundle.

Design notes worth keeping:
  * The anatomy expectation travels WITH the meshes, quoted verbatim from
    fixtures/anatomy_expectation.json including its citation. A receiving
    session that has to guess how many legs a spider has will guess, and an
    oracle that is re-derived per session is not an oracle.
  * The reference extraction is included but fenced off under a key that says
    what it is. It is one implementation's output, not ground truth, and the
    manifest says so in the record rather than in a README nobody reads.
"""
from __future__ import annotations
import hashlib, json, os, shutil, sys

HARNESS = "<repo>/mcp_harness"
SUBJECTS = ["dog", "cat", "horse", "lizard", "frog", "bird",
            "starfish", "spider", "octopus"]
ORIGINALS = {"starfish": "starfish.jpg", "spider": "spider.webp",
             "lizard": "lizard.jpg", "dog": "dog.webp", "bird": "bird.jpg",
             "octopus": "octopus.webp", "cat": "cat.avif", "frog": "frog.jpg",
             "horse": "horse.webp"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(scratch, out):
    exp = json.load(open(os.path.join(HARNESS, "fixtures",
                                      "anatomy_expectation.json")))
    runs = {r["label"]: r for r in
            json.load(open(os.path.join(scratch, "runs", "results.json")))}

    for sub in ("meshes", "photos"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)

    entries = []
    for s in SUBJECTS:
        r = runs[s]
        mesh_src = os.path.join(scratch, "runs", s, "mesh.glb")
        mesh_rel = f"meshes/{s}.glb"
        shutil.copyfile(mesh_src, os.path.join(out, mesh_rel))
        photo_rel = f"photos/{s}.png"
        shutil.copyfile(os.path.join(scratch, "photos", f"{s}.png"),
                        os.path.join(out, photo_rel))

        e = exp.get(s, {})
        t = r.get("tree", {})
        entries.append({
            "subject": s,
            "mesh": {
                "path": mesh_rel,
                "sha256": sha256(mesh_src),
                "bytes": os.path.getsize(mesh_src),
                **r.get("mesh", {}),
            },
            "source_photo": {
                "path": photo_rel,
                "original_filename": ORIGINALS[s],
                "note": "user-supplied photograph, converted to PNG; this is "
                        "the image fed to the generator, NOT a generated "
                        "concept image",
            },
            "anatomy_ground_truth": {
                "expected_feature_count": e.get("expected_feature_count"),
                "derivation": e.get("derivation"),
                "citation": e.get("citation"),
            },
            "reference_extraction_NOT_ground_truth": {
                "_what": "output of the AI-Driven-Origami-IDE extractor "
                         "(mesh_to_tree.auto_mesh_to_metric_tree) at its "
                         "shipped defaults. A COMPARISON POINT, not a target. "
                         "Where it disagrees with anatomy_ground_truth, IT is "
                         "the thing that is wrong.",
                "packed": t.get("confirmed"),
                "leaf_count": len(t.get("leaf_labels") or {}),
                "n_pairs": t.get("n_pairs"),
                "voxel_res": t.get("voxel_res"),
                "prune_fraction": t.get("prune_fraction"),
                "stub_flaps": t.get("stub_flaps"),
                "normalizer_repair": t.get("repaired"),
                "self_derived_reference_count": t.get("reference_count"),
                "self_derived_fidelity": t.get("fidelity"),
                "leaf_labels": t.get("leaf_labels"),
            },
        })

    manifest = {
        "_meta": {
            "what": "Nine 3-D meshes generated from user-supplied photographs "
                    "by tencent/Hunyuan3D-2 (/shape_generation), for testing a "
                    "mesh -> metric-tree extraction pipeline.",
            "why_these": "They are GENERATED meshes at 175k-599k faces, not "
                         "hand-modelled low-poly assets. Extraction code is "
                         "commonly calibrated on the latter and only ever fed "
                         "the former; this set is the former.",
            "generator": {
                "space": "tencent/Hunyuan3D-2",
                "api_name": "/shape_generation",
                "params": {"steps": 30, "guidance_scale": 5.0, "seed": 1234,
                           "randomize_seed": False, "octree_resolution": 256,
                           "check_box_rembg": True, "num_chunks": 8000},
                "note": "seed pinned and randomize_seed disabled, so these "
                        "meshes are reproducible from the same photos",
            },
            "how_to_score": "Score leaf counts against "
                            "anatomy_ground_truth.expected_feature_count. Do "
                            "NOT score against any reference count your own "
                            "pipeline derives from its own skeleton -- that "
                            "closes a loop in which discarding half the animal "
                            "RAISES the score.",
            "convention": exp["_meta"]["convention"],
            "ground_truth_source": "fixtures/anatomy_expectation.json from "
                                   "AI-Driven-Origami-IDE; human-authored from "
                                   "published anatomy, each row carrying its "
                                   "own derivation and citation. Nothing in it "
                                   "is computed from any extraction.",
            "subjects": len(entries),
        },
        "meshes": entries,
    }
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


if __name__ == "__main__":
    m = build(sys.argv[1], sys.argv[2])
    print(f"{len(m['meshes'])} meshes -> {sys.argv[2]}")
    for e in m["meshes"]:
        g = e["anatomy_ground_truth"]["expected_feature_count"]
        r = e["reference_extraction_NOT_ground_truth"]
        print(f"  {e['subject']:9s} {e['mesh']['n_faces']:>7} faces  "
              f"expect {g}  ref {r['leaf_count']} "
              f"{'PACKED' if r['packed'] else 'NO TREE'}")
