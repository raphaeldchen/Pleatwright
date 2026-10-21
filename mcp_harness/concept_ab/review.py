"""Draft scores, and the page the owner scores on (spec §2).

The owner's reading is final. Claude's draft only pre-fills the toggles. The
page is BLIND: rows carry arm letters, never a model name, so anatomy is judged
without knowing which generator drew it. The owner first corrects the checklist
(inline count inputs), then marks each mesh AND each concept image pass/fail.
The image labels are what calibrates arm E's picker without a second pass.
"Download scores" saves `scores_r<n>.json`; the owner puts it in the root.
"""
from __future__ import annotations

import html
import json
import os
import shutil

import vlm_render
from concept_ab import arms as A
from concept_ab import judge
from concept_ab.run import concept_path

ROW_ORDER = ("photo", "A", "B", "C", "D", "E")


def ensure_photo_cells(root: str, library_dir: str) -> None:
    """The owner's library photos and meshes, as the reference row (round 1)."""
    for subject in A.SUBJECTS:
        s = A.slug(subject)
        mesh = os.path.join(library_dir, "meshes", s + ".glb")
        photo = os.path.join(library_dir, "photos", s + ".png")
        if not (os.path.isfile(mesh) and os.path.isfile(photo)):
            continue
        cell = A.cell_dir(root, "photo", subject, 1)
        os.makedirs(cell, exist_ok=True)
        for src, name in ((mesh, "mesh.glb"), (photo, "concept.png")):
            if not os.path.exists(os.path.join(cell, name)):
                shutil.copyfile(src, os.path.join(cell, name))


def has_mesh(cell: str) -> bool:
    return os.path.isfile(os.path.join(cell, "mesh.glb"))


def cells(root: str, round_: int | None = None, *, unlifted: bool = False):
    """(arm, subject, round, cell_dir) for every cell with a mesh. With
    `unlifted`, also the cells whose concept exists but whose lift failed
    (final review I2): those are failures of their arm, not missing rows."""
    out = []
    for arm in ROW_ORDER:
        for subject in A.SUBJECTS:
            rounds = [1] if arm == "photo" else ([round_] if round_ else [1, 2])
            for r in rounds:
                cell = A.cell_dir(root, arm, subject, r)
                if has_mesh(cell) or (unlifted and concept_path(cell)
                                      and os.path.isfile(os.path.join(cell, "meta.json"))):
                    out.append((arm, subject, r, cell))
    return out


async def draft_scores(root: str, client, *, only=None) -> int:
    """Claude's draft per cell: the mesh sheet and the concept, against the checklist."""
    checklist = A.load_checklist()
    n = 0
    for arm, subject, r, cell in cells(root, unlifted=True):
        if only and A.cell_id(arm, subject, r) not in only:
            continue
        if os.path.exists(os.path.join(cell, "draft.json")):
            continue
        text = A.checklist_text(subject, checklist)
        parts = checklist[subject]
        mesh = None
        if has_mesh(cell):
            sheet = os.path.join(cell, "mesh_views.png")
            if not os.path.exists(sheet):
                vlm_render.render_mesh_views(os.path.join(cell, "mesh.glb"), sheet,
                                             label=A.cell_id(arm, subject, r))
            mesh = await judge.assess(client, sheet, text, expected_parts=parts)
        d = {"mesh": mesh,
             "image": await judge.assess(client, concept_path(cell), text, expected_parts=parts)}
        with open(os.path.join(cell, "draft.json"), "w") as f:
            json.dump(d, f, indent=1)
        n += 1
    return n


def _toggle(cid: str, kind: str, verdict: str) -> str:
    return " ".join(
        f'<label><input type="radio" name="{cid}|{kind}" value="{v}"'
        + (" checked" if v == verdict else "") + f"> {v}</label>"
        for v in ("pass", "fail"))


def _draft_verdict(a: dict | None) -> str | None:
    """Pre-fill only from a draft that exists and read cleanly: an unmarked
    toggle saves as null, which scoring reports as unscored, never as a fail."""
    if not a or a.get("error"):
        return None
    return "pass" if a["passed"] else "fail"


def _draft_table(a: dict | None) -> str:
    if not a:
        return "<p class=muted>no draft</p>"
    if a.get("error"):
        return f"<p class=muted>draft failed: {html.escape(a['error'])}</p>"
    rows = "".join(
        f"<tr class={'ok' if p['seen'] == p['expected'] and p['attached'] else 'bad'}>"
        f"<td>{html.escape(p['part'])}</td><td>{p['seen']}/{p['expected']}</td>"
        f"<td>{'attached' if p['attached'] else 'DETACHED'}</td></tr>" for p in a["parts"])
    extras = "".join(f"<tr class=bad><td colspan=3>extra: {html.escape(x)}</td></tr>"
                     for x in a["extras"])
    artifacts = "".join(f"<tr class=muted><td colspan=3>artifact (ok): {html.escape(x)}</td></tr>"
                        for x in a.get("artifacts", []))
    return f"<table>{rows}{extras}{artifacts}</table>"


def build_review(root: str, round_: int) -> str:
    saved_path = os.path.join(root, f"scores_r{round_}.json")
    saved = json.load(open(saved_path)) if os.path.exists(saved_path) else {}
    saved_cells = dict(saved.get("cells", {}))
    r1_path = os.path.join(root, "scores_r1.json")
    if round_ != 1 and os.path.exists(r1_path):       # the photo row is scored once, in round 1
        for cid, m in json.load(open(r1_path)).get("cells", {}).items():
            if cid.startswith("photo/"):
                saved_cells.setdefault(cid, m)
    checklist = {**A.load_checklist(), **saved.get("checklist", {})}
    by_subject: dict[str, list] = {}
    for arm, subject, r, cell in cells(root, unlifted=True):
        if arm == "photo" or r == round_:
            by_subject.setdefault(subject, []).append((arm, r, cell))
    sections = []
    for subject in A.SUBJECTS:
        if subject not in by_subject:
            continue
        cl = "".join(
            f'<label>{html.escape(p["part"])} <input type="number" min="0" '
            f'data-subject="{html.escape(subject)}" data-part="{html.escape(p["part"])}" '
            f'data-note="{html.escape(p.get("note", ""))}" value="{p["count"]}"></label> '
            for p in checklist[subject])
        rows = []
        for arm, r, cell in by_subject[subject]:
            cid = A.cell_id(arm, subject, r)
            draft = json.load(open(os.path.join(cell, "draft.json"))) \
                if os.path.exists(os.path.join(cell, "draft.json")) else {}
            prev = saved_cells.get(cid, {})
            verdict = {k: prev.get(k) or _draft_verdict(draft.get(k)) for k in ("mesh", "image")}
            concept = os.path.relpath(concept_path(cell) or cell, root)
            sheet = os.path.relpath(os.path.join(cell, "mesh_views.png"), root)
            if has_mesh(cell):
                sheet_img = f'<img src="{html.escape(sheet)}" class=sheet>'
                mesh_block = (f'<div><b>mesh</b> {_toggle(cid, "mesh", verdict["mesh"])}'
                              f'{_draft_table(draft.get("mesh"))}</div>')
            else:
                sheet_img = ""
                mesh_block = "<div><b>mesh</b> no mesh: the lift failed, which counts as a mesh fail</div>"
            rows.append(
                f'<div class=row data-cell="{cid}"><h3>{html.escape(cid)}</h3>'
                f'<div class=imgs><img src="{html.escape(concept)}" class=concept>{sheet_img}</div>'
                f'<div class=scores><div><b>image</b> {_toggle(cid, "image", verdict["image"])}'
                f'{_draft_table(draft.get("image"))}</div>'
                f'{mesh_block}'
                f'<textarea data-note-for="{cid}" placeholder="note">'
                f'{html.escape(prev.get("note", ""))}</textarea></div></div>')
        sections.append(f'<section><h2>{html.escape(subject)}</h2>'
                        f'<div class=checklist>checklist: {cl}</div>{"".join(rows)}</section>')
    page = PAGE.format(round=round_, sections="".join(sections))
    out = os.path.join(root, f"review_r{round_}.html")
    with open(out, "w") as f:
        f.write(page)
    return out


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Concept review r{round}</title>
<style>
body{{font:14px system-ui,sans-serif;margin:16px;background:#fafafa;color:#222}}
section{{border-top:2px solid #999;margin-top:24px}}
.row{{display:flex;flex-wrap:wrap;gap:12px;align-items:flex-start;border-bottom:1px solid #ddd;padding:8px 0}}
.row h3{{width:100%;margin:0;font-size:13px}}
.imgs img.concept{{height:220px}} .imgs img.sheet{{height:220px;max-width:100%}}
.scores{{min-width:260px}} table{{border-collapse:collapse;font-size:12px;margin:4px 0}}
td{{padding:1px 6px}} tr.bad td{{color:#b00}} tr.ok td{{color:#070}} .muted{{color:#888}}
textarea{{width:260px;height:40px}} .checklist input{{width:44px}}
#save{{position:fixed;top:8px;right:8px;padding:8px 14px;font-size:15px}}
</style></head><body>
<h1>Concept review, round {round}</h1>
<p>Correct each checklist first, then mark every image and mesh pass or fail. A cell
passes when every checklist part is present, attached and correctly numbered, with no
extra limbs, tails, bases or large detached pieces. Small floating specks and thin
slivers are fine. Save with the button and put the file in the experiment folder.</p>
<button id="save">Download scores_r{round}.json</button>
{sections}
<script>
document.getElementById('save').onclick = () => {{
  const out = {{round: {round}, checklist: {{}}, cells: {{}}}};
  document.querySelectorAll('input[data-part]').forEach(i => {{
    const s = i.dataset.subject;
    (out.checklist[s] = out.checklist[s] || []).push(
      Object.assign({{part: i.dataset.part, count: parseInt(i.value, 10)}},
                    i.dataset.note ? {{note: i.dataset.note}} : {{}}));
  }});
  document.querySelectorAll('.row').forEach(r => {{
    const c = r.dataset.cell, pick = k => {{
      const e = r.querySelector(`input[name="${{c}}|${{k}}"]:checked`); return e ? e.value : null; }};
    out.cells[c] = {{mesh: pick('mesh'), image: pick('image'),
                    note: r.querySelector('textarea').value}};
  }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(new Blob([JSON.stringify(out, null, 1)], {{type: 'application/json'}}));
  a.download = 'scores_r{round}.json'; a.click();
}};
</script></body></html>
"""
