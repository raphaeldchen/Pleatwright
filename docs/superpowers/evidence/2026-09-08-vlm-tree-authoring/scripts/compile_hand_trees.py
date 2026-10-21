"""Compile the 18 hand-authored trees. TWO paths, because they answer
different questions.

  attempt0  runner.compile_tree -- the tree EXACTLY as authored, no nudge.
            "Do my proportions pack?"
  serve     server.draft_and_compile_full_base -- the live path, which on
            failure perturbs lengths +/-10% over 12 rungs.
            "Does a tree NEAR mine pack?"

The distinction is the whole report: a serve-path success on a tree that
failed attempt-0 is NOT evidence that the authored proportions work. It is
evidence that the rescue ladder found different ones.
"""
from __future__ import annotations
import json, os, re, sys

H = "<repo>/mcp_harness"
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)

from runner import compile_tree
import server

BUNDLE = os.path.expanduser("~/Downloads/photo_meshes/hand_trees/trees.json")


def scale_of(fold_str):
    try:
        f = json.loads(fold_str)
    except Exception:
        return None
    for k in ("ide:scale", "scale", "treemaker:scale"):
        if k in f:
            return f[k]
    md = f.get("file_metadata") or f.get("frame_metadata") or {}
    for k in ("scale", "ide:scale"):
        if k in md:
            return md[k]
    return None


def main():
    b = json.load(open(BUNDLE))
    rows = []
    for subject, e in b["subjects"].items():
        for var in ("faithful", "packable"):
            t = e[var]
            nodes = t["tree_nodes"]
            pairs = [list(p) for p in t["symmetric_pairs"]]
            rec = {"subject": subject, "variant": var,
                   "leaves": t["leaf_count"], "n_nodes": len(nodes)}

            st, payload = compile_tree(nodes, pairs, timeout=60)
            rec["attempt0"] = st
            rec["attempt0_detail"] = (None if st == "ok" else payload[:400])
            if st == "ok":
                rec["attempt0_scale"] = scale_of(payload)
                rec["attempt0_fold_bytes"] = len(payload)

            out = server.draft_and_compile_full_base(nodes, pairs)
            if out.startswith("ERROR"):
                rec["serve"] = "error"
                rec["serve_detail"] = out[-500:]
                m = re.search(r"DETAIL:\s*(\{.*\})\s*$", out, re.S)
                if m:
                    try:
                        rec["serve_detail_json"] = json.loads(m.group(1))
                    except Exception:
                        pass
            else:
                rec["serve"] = "ok"
                rec["serve_scale"] = scale_of(out)
                rec["serve_fold_bytes"] = len(out)
                rec["serve_nudged"] = ("nudge" in out.lower()
                                       or "perturb" in out.lower())
            rows.append(rec)
            print(f"{subject:9} {var:9} leaves={rec['leaves']:2d}  "
                  f"attempt0={rec['attempt0']:6s}  serve={rec['serve']:6s}  "
                  f"scale={rec.get('serve_scale')}", flush=True)
            json.dump(rows, open("/tmp/hand_tree_compile.json", "w"), indent=2)
    return rows


if __name__ == "__main__":
    main()
