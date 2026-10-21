"""Pleatwright: tree -> folded, shaped model pipeline, a reimplementation of
COrigami (arXiv:2606.26299).

    python -m pleatwright author "a dog" --out DIR [--open]   # mesh + VLM tree, human review
    python -m pleatwright fold DIR/tree.json --out DIR        # tree -> DIR/<Subject>_<grid>/
    python -m pleatwright run "a dog" --out DIR [--open]      # author, then fold

`pleatwright/__main__.py` is the front door; `pipeline.run` is the fold stage.
See docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md.
"""
