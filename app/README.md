# Pleatwright app

A local web app for the Pleatwright pipeline. The conversation is on the left and the outputs (concept image, mesh, tree, crease patterns, folded model) on the right. Design: `docs/superpowers/specs/2026-10-07-pleatwright-app-design.md`.

```bash
make app        # build the UI, serve http://127.0.0.1:8000
make app-dev    # API on :8000 + Vite hot reload on http://127.0.0.1:5173
make test-app   # server tests;  cd app/web && npm test  for the UI
```

* Runs are stored in `~/Pleatwright/runs/` (`PLEATWRIGHT_RUNS_DIR` overrides). Each is the CLI's `--out DIR` layout plus `events.jsonl` (the run's history), `model.fold` (the folded model, with fold-slider frames) and `layout/` (both packed layouts, and the layout card when the run asked which to fold). `python -m pleatwright fold DIR/tree.json --out DIR` works on any app run.
* After you approve the tree the app packs the sheet two ways: the mirror-symmetric layout, and the smaller unmirrored one (grid capped at `N_sym*10//11`, found within a fixed work budget). When the unmirrored layout makes the folded model at least 10% larger from the same sheet (`gain >= 1.10`), the run pauses at the packing stage on a layout card: both packing creases side by side with their grid sizes, a pros-and-cons line for each, a recommendation (always the smaller grid) and a short VLM explanation (a template one if the VLM is unavailable). Choose an option to fold at that grid; reloading the page shows the same card, and a failed fold retries back to the card. Below the threshold no question is asked and the symmetric layout is folded, byte-identical to before. Spec: `docs/superpowers/specs/2026-10-16-packing-layout-choice-design.md`.
* Keys and providers come from the repo-root `.env`, as for the CLI (`.env.example`). Without a usable LLM configuration the app shows a banner and refuses new runs; past runs stay browsable. The server reads `.env` once at startup, so after fixing a key, restart the app.
* The server listens on 127.0.0.1 only.
* The look follows `docs/superpowers/specs/2026-10-08-pleatwright-app-restyle-design.md`. The theme follows macOS by default; the button at the foot of the runs sidebar cycles System → Light → Dark (remembered per browser). Press `N` to start a new run.
* The model pill in the composer picks the VLM for the next tree (first draft, revision or retry): Haiku 5.5 by default, or Sonnet 5. Each tree round records which model wrote it. The UI needs a current browser (Chrome 123+, Safari 17.5+, Firefox 120+) for CSS `light-dark()`.
