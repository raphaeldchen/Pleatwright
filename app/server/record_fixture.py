"""Record a fake-provider guided run's events for the frontend tests (spec §7).

    cd mcp_harness && PYTHONPATH=.:tests:../app/server $PY ../app/server/record_fixture.py

Artifact tree bird_1 (owner rule). Writes app/web/src/__fixtures__/bird_run.events.jsonl
with timestamps kept, so the frontend replays exactly what the server emits."""
import asyncio
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "..", "mcp_harness"),
                os.path.join(HERE, "..", "..", "mcp_harness", "tests")]
os.environ.setdefault("IDE_MESH_PROVENANCE", "0")
os.environ["MESH_PROVIDER"] = "fake"

import gated_pipeline as GP                                       # noqa: E402
import mesh_acquire                                               # noqa: E402
from artifact_trees import authored                               # noqa: E402
from pleatwright_app.guided import Manager                        # noqa: E402
from pleatwright_app.runs import RunStore                         # noqa: E402
from test_gated_pipeline import FakeClient, _fake_mesh_views      # noqa: E402
import pathlib                                                    # noqa: E402

OUT = os.path.join(HERE, "..", "web", "src", "__fixtures__", "bird_run.events.jsonl")


async def main(tmp, write_fixture=True):
    mesh_acquire.output_dir = lambda: os.path.join(tmp, "meshes")
    GP.vlm_render.render_mesh_views = lambda *a, **k: _fake_mesh_views(pathlib.Path(tmp))
    bird = authored("bird_1")
    m = Manager(RunStore(os.path.join(tmp, "runs")), lambda model: FakeClient([bird, bird]))
    rid = await m.create("a bird")
    await m.wait_idle()
    await m.approve(rid)                 # the mesh review comes first (2026-10-11)
    await m.wait_idle()
    await m.message(rid, "make the tail longer")
    await m.wait_idle()
    await m.approve(rid)
    await m.wait_idle()
    if write_fixture:
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        shutil.copyfile(os.path.join(m.store.dir(rid), "events.jsonl"), OUT)
        print("wrote", os.path.relpath(OUT))
    else:
        print("kept run", m.store.dir(rid))


if __name__ == "__main__":
    if len(sys.argv) > 1:          # keep the run to browse it: PLEATWRIGHT_RUNS_DIR=<dir>/runs
        os.makedirs(sys.argv[1], exist_ok=True)
        asyncio.run(main(sys.argv[1], write_fixture=False))
    else:
        with tempfile.TemporaryDirectory() as t:
            asyncio.run(main(t))
