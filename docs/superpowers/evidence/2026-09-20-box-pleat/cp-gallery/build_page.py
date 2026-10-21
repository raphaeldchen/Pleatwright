"""Assemble the CP gallery page from the rendered SVGs + index.json."""
import json, os, sys

D = sys.argv[1]
rows = json.load(open(os.path.join(D, "index.json")))

HEAD = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Box-pleat crease patterns after pleat reassignment</title>
<style>
 :root{--bg:#f7f5f0;--card:#fff;--ink:#1a1a1a;--dim:#6b6b6b;--rule:#e0dbd0;--flip:#f9a825}
 @media(prefers-color-scheme:dark){:root:not([data-theme=light]){
   --bg:#16171a;--card:#1e2024;--ink:#e8e6e1;--dim:#9a978f;--rule:#31343a}}
 *{box-sizing:border-box}
 body{margin:0;padding:32px 16px 64px;background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
 .wrap{max-width:1180px;margin:0 auto}
 h1{font-size:25px;margin:0 0 6px;letter-spacing:-.2px}
 .sub{color:var(--dim);margin:0 0 26px;max-width:72ch}
 .key{display:flex;gap:20px;flex-wrap:wrap;align-items:center;padding:12px 16px;
  background:var(--card);border:1px solid var(--rule);border-radius:10px;margin-bottom:26px;font-size:13px}
 .k{display:flex;gap:7px;align-items:center}
 .sw{width:26px;height:0;border-top-width:2px;border-top-style:solid;display:inline-block}
 table.sum{width:100%;border-collapse:collapse;margin-bottom:34px;font-size:13.5px;
  background:var(--card);border:1px solid var(--rule);border-radius:10px;overflow:hidden}
 table.sum th,table.sum td{padding:8px 11px;text-align:right;border-bottom:1px solid var(--rule)}
 table.sum th:first-child,table.sum td:first-child{text-align:left}
 table.sum th{font-weight:600;color:var(--dim);font-size:12px;text-transform:uppercase;letter-spacing:.4px}
 table.sum tr:last-child td{border-bottom:none}
 .zero{color:var(--dim)}
 .card{background:var(--card);border:1px solid var(--rule);border-radius:12px;
  padding:18px;margin-bottom:22px}
 .card h2{margin:0 0 2px;font-size:19px}
 .meta{color:var(--dim);font-size:13px;margin:0 0 14px;font-variant-numeric:tabular-nums}
 .pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}
 @media(max-width:820px){.pair{grid-template-columns:1fr}}
 .pane{min-width:0}
 .pane h3{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.5px;color:var(--dim)}
 .pane svg,.pane img{width:100%;height:auto;display:block;border:1px solid var(--rule);border-radius:7px}
 code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.92em}
</style></head><body><div class="wrap">
<h1>Box-pleat crease patterns after pleat reassignment</h1>
<p class="sub">The crease <em>set</em> is identical to what the compiler produced before this
work &mdash; same vertices, same edges, same count of folded creases. Only which creases are
mountains and which are valleys has moved. <strong>Amber highlights every crease whose label
changed</strong>, so the repair is visible rather than something you have to diff by eye.</p>
<div class="key">
 <span class="k"><span class="sw" style="border-color:#c62828"></span> M (mountain)</span>
 <span class="k"><span class="sw" style="border-color:#1565c0;border-top-style:dashed"></span> V (valley)</span>
 <span class="k"><span class="sw" style="border-color:#111;border-top-width:3px"></span> paper edge</span>
 <span class="k"><span class="sw" style="border-color:var(--flip);border-top-width:5px"></span> label flipped by the search</span>
</div>
"""

sumrows = []
for r in rows:
    flip = (f'<td>{r["flipped"]}</td>' if r["flipped"]
            else '<td class="zero">0</td>')
    sumrows.append(
        f'<tr><td><code>{r["subject"]}</code></td><td>{r["N"]}</td>'
        f'<td>{r["creases"]}</td>{flip}<td>{r["tries"]}</td>'
        f'<td>{r["faces"]}</td><td>{r["closure"]:.1e}</td><td>{r["secs"]:.1f}</td></tr>')

body = [HEAD,
        '<table class="sum"><tr><th>subject</th><th>grid N</th><th>creases</th>'
        '<th>flipped</th><th>candidates</th><th>faces</th><th>closure</th><th>secs</th></tr>',
        "\n".join(sumrows), "</table>"]

for r in rows:
    s = r["subject"]
    # reference the SVGs rather than inlining them: inlining duplicates
    # ~408 KB of identical content into the page, which is wasteful in a
    # committed artifact. The page and the SVGs travel together.
    cp = f'<img src="{s}-cp.svg" alt="{s} crease pattern">'
    bs = f'<img src="{s}-base.svg" alt="{s} flat-folded base">'
    if r["flipped"]:
        what = (f'<strong>{r["flipped"]} of {r["creases"]} creases relabelled</strong> '
                f'over {r["tries"]} candidate labellings')
    else:
        what = ('accepted on the first candidate &mdash; this one was already '
                'consistent, so nothing moved')
    geom = ("" if r["same_geom"] else
            ' <strong style="color:#c62828">&mdash; GEOMETRY DIFFERS, see note</strong>')
    body.append(
        f'<div class="card"><h2>{s}</h2>'
        f'<p class="meta">{what}{geom} &middot; grid {r["N"]}&times;{r["N"]} &middot; '
        f'{r["creases"]} creases ({r["M"]} M / {r["V"]} V) &middot; {r["faces"]} faces &middot; '
        f'closure {r["closure"]:.1e}</p>'
        f'<div class="pair">'
        f'<div class="pane"><h3>Crease pattern</h3>{cp}</div>'
        f'<div class="pane"><h3>Flat-folded base</h3>{bs}</div>'
        f'</div></div>')

body.append("</div></body></html>")
out = os.path.join(D, "gallery.html")
open(out, "w").write("\n".join(body))
print(f"wrote {out} ({os.path.getsize(out)} bytes, {len(rows)} subjects)")
