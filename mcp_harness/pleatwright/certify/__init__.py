"""Global flat-foldability certification: layer-order constraints, the SAT
encoding, and the independent checks it is verified against.

PROVENANCE. These modules were written for the TreeMaker serve path and the
Lang box-pleat compiler (`box_pleat/`) and moved here on 2026-10-07. Their
docstrings and constant derivations still cite those callers, probes and
measurements (`server.py`, `mv_symmetrize`, `root_rank`, `lint_verdict`,
`box_pleat.compile`, `probe_*.py`): read those as history. That code is on
the `archive/treemaker-box-pleat` branch.

PRODUCTION USE ON MAIN. The only caller is `pleatwright.solve`, which uses
`flat_fold.flat_fold`, `layers.constraint_graph`, `sat_order.encode` /
`raw_triple_bound` and `layer_certify.verify`. Kept with NO production caller,
as independent test oracles: `layer_certify.decide`, `layers.certify`,
`layers.propagate` and `layers.Witness` (with the `layer_order.propagate`
they wrap), `sat_order.solve`, and `cp_audit`."""
