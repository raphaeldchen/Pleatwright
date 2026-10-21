"""Emit trees.json + parts/<subject>.md for the hand-authored trees."""
from __future__ import annotations
import json, os, sys

S = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, S)
sys.path.insert(0, "<repo>/"
                   ".claude/worktrees/silly-tereshkova-7d463f/mcp_harness")
import hand_trees_data as H
import hand_trees_build as B
import tree_contract

OUT = os.path.expanduser("~/Downloads/photo_meshes/hand_trees")
EXP = json.load(open("<repo>/"
                     ".claude/worktrees/silly-tereshkova-7d463f/mcp_harness/"
                     "fixtures/anatomy_expectation.json"))


def parts_table(subject, variant, nodes):
    lf = set(B.leaves_of(nodes))
    rows = ["| edge | from | to | length (grid) | leaf |",
            "|---|---|---|---|---|"]
    for name, parent, _, ln in nodes:
        if parent is None:
            rows.append(f"| _(root)_ | — | `{name}` | — | — |")
            continue
        rows.append(f"| `{name}` | `{parent}` | `{name}` | {ln} | "
                    f"{'**leaf**' if name in lf else ''} |")
    return "\n".join(rows)


def main():
    os.makedirs(f"{OUT}/parts", exist_ok=True)
    bundle = {
        "_meta": {
            "what": "HAND-AUTHORED metric trees for the nine photo-derived "
                    "meshes. Written by a person reading proportions off a "
                    "24-unit grid laid over orthographic renders of each "
                    "mesh. NOTHING here was produced by, checked against, or "
                    "tuned toward any extraction pipeline.",
            "not_compiled": "These trees have NOT been run through TreeMaker. "
                            "Nobody knows whether they pack. Several faithful "
                            "variants exceed MAX_LEAVES=8 and certainly will "
                            "not. Treat 'packable' as 'inside the leaf-count "
                            "window', which is a necessary condition and not "
                            "a sufficient one.",
            "reference": "Structure follows COrigami's stick figures "
                         "(~/Desktop/origami_samples): a body "
                         "spine of internal nodes, multi-segment limbs with "
                         "named joints, integer edge lengths on a stated grid.",
            "frame": "+x forward (toward the head), +y up, +z to the "
                     "animal's LEFT. Directions are drawing hints; the tree "
                     "is (parent, length) and directions never affect it.",
            "edge_naming": "An edge is named for the node it ENTERS. "
                           "`hock_l: 4` is the segment ending at the left "
                           "hock.",
            "length_units": "`length_grid` is the authored integer. `length` "
                            "in tree_nodes is scaled so the longest edge in "
                            "that tree is 0.40, matching "
                            "mesh_to_tree.LONGEST_LIMB_TARGET.",
            "variants": {
                "faithful": "COrigami's convention, which gives ears, crests "
                            "and pedipalps their own leaves.",
                "packable": "This repo's convention "
                            "(fixtures/anatomy_expectation.json): one leaf "
                            "per terminal appendage, sub-flap detail "
                            "excluded, and never more than MAX_LEAVES=8.",
            },
        },
        "subjects": {},
    }

    print(f"{'subject':9} {'variant':9} {'nodes':>5} {'leaves':>6} "
          f"{'pairs':>5} {'exp':>4} {'contract':>9}")
    for subject, spec in H.SUBJECTS.items():
        entry = {
            "grid": spec["grid"],
            "common_name": spec.get("common"),
            "how_measured": spec["read"],
            "anatomy_expected_feature_count":
                EXP.get(subject, {}).get("expected_feature_count"),
            "node_order_rationale": spec.get("order_note"),
            "merges_faithful_to_packable": spec.get("merges", []),
        }
        for k in ("identical_note", "symmetry_note", "caveat"):
            if spec.get(k):
                entry[k] = spec[k]

        md = [f"# {subject} — hand-authored metric tree",
              "", f"**{spec.get('common','')}**  ·  grid = {spec['grid']} "
                  f"units across the mesh's longest extent", "",
              f"**How the proportions were read.** {spec['read']}", ""]
        for k, title in (("caveat", "Caveat"),
                         ("symmetry_note", "Symmetry"),
                         ("identical_note", "Why the two variants match")):
            if spec.get(k):
                md += [f"**{title}.** {spec[k]}", ""]

        for var in ("faithful", "packable"):
            nodes, pairs = spec[var]["nodes"], spec[var]["pairs"]
            tn, sp, labels = B.metric_tree(nodes, pairs)
            rep = tree_contract.check(tn, sp)
            lf = B.leaves_of(nodes)
            entry[var] = {
                "n_nodes": len(nodes),
                "leaves": lf,
                "leaf_count": len(lf),
                "tree_nodes": tn,
                "symmetric_pairs": sp,
                "labels": {str(i): n for i, n in labels.items()},
                "length_grid": {n[0]: n[3] for n in nodes},
                "parents": {n[0]: n[1] for n in nodes},
                "contract_errors": rep.get("errors", []),
                "contract_warnings": rep.get("warnings", []),
            }
            md += [f"## {var} — {len(lf)} leaves", "",
                   parts_table(subject, var, nodes), "",
                   "Leaves: " + ", ".join(f"`{n}`" for n in lf), "",
                   "Symmetric pairs: " +
                   (", ".join(f"`{a}`↔`{b}`" for a, b in pairs) or "none"),
                   ""]
            if var == "packable" and spec.get("merges"):
                md += ["**Reductions applied:**", ""]
                md += [f"- {m}" for m in spec["merges"]] + [""]
            print(f"{subject:9} {var:9} {len(nodes):>5} {len(lf):>6} "
                  f"{len(pairs):>5} "
                  f"{entry['anatomy_expected_feature_count'] or 0:>4} "
                  f"{('OK' if not rep.get('errors') else 'ERRORS'):>9}")
        bundle["subjects"][subject] = entry
        open(f"{OUT}/parts/{subject}.md", "w").write("\n".join(md))

    json.dump(bundle, open(f"{OUT}/trees.json", "w"), indent=2)
    return bundle


if __name__ == "__main__":
    main()
