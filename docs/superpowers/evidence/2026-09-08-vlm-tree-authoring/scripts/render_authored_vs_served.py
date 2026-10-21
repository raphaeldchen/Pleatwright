"""Authored tree vs the tree the backend actually served.

The served panel is drawn from the AUTHORED node positions and the SERVED
parent links. Nothing is invented: a metric tree carries no geometry, only
lengths, so the only honest source of a picture is the directions the author
supplied. Where the backend merged two joints, the surviving nodes sit exactly
where the author put them and the edge between them is drawn straight and
labelled with its new, summed length.
"""
import json, os, sys
R="<repo>"
sys.path.insert(0,R)
from PIL import Image, ImageDraw
from mcp_harness import vlm_render as V

S=os.environ["S"]; D=f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data"
OUT=f"{S}/pairs"; os.makedirs(OUT, exist_ok=True)
SZ=380

def tuples_from(ns, names, directions=None):
    out=[]
    for n in ns:
        nm=names[str(n["id"])] if str(n["id"]) in names else names[n["id"]]
        pn=None
        if n["parent_id"] is not None:
            pn=names[str(n["parent_id"])] if str(n["parent_id"]) in names else names[n["parent_id"]]
        out.append((nm, pn, (directions or {}).get(nm), n["length"]))
    return out

def main():
    rows=json.load(open(f"{D}/rule6_serve.json"))
    raw={r["subject"]: r["tree"] for r in json.load(open(f"{D}/rule6_raw.json")) if r.get("tree")}
    man={}
    for x in rows:
        s=x["subject"]; names=x["names"]; dirs=x["directions"]
        auth=tuples_from(x["requested"], names, dirs)
        pos=V.positions([(n, p, d, l) for n, p, d, l in auth])
        srv=tuples_from(x["served_nodes"], names) if x["served_nodes"] else None

        # FOUR VIEWS EACH, authored on the top row and served below, so a
        # column is one camera and the two rows differ only in the tree.
        VIEWS = V.TREE_VIEWS          # top, side, front, isometric
        rowA=[V._tree_panel(auth, pos, v, SZ) for v in VIEWS]
        rowB=([V._tree_panel(srv, pos, v, SZ) for v in VIEWS] if srv else
              [Image.new("RGB",(SZ,SZ),(250,246,246)) for _ in VIEWS])
        W=SZ*len(VIEWS); HDR=54; LAB=22
        sheet=Image.new("RGB",(W, HDR + (SZ+LAB)*2),(253,253,251))
        dr=ImageDraw.Draw(sheet)
        for r,(row,tag,col) in enumerate(((rowA,"AUTHORED  —  as the model wrote it",(20,20,20)),
                                          (rowB,f"SERVED  —  {x['what']}",(20,20,20)))):
            y = HDR + r*(SZ+LAB)
            dr.text((8, y+4), tag, fill=col, font=V._font(12))
            for i,im in enumerate(row):
                sheet.paste(im,(i*SZ, y+LAB))
        dr.text((8,7), f"{s}", fill=(20,20,20), font=V._font(17))
        dr.text((8,30),
                f"authored {len(auth)} nodes  ·  served {len(srv) if srv else 0} nodes  ·  "
                f"stage {x['stage']}  ·  views: top / side / front / isometric",
                fill=(110,110,110), font=V._font(11))
        p=f"{OUT}/{s}.png"; sheet.save(p); man[s]=p
        print(f"  {s:12} {x['what']}")
    json.dump(man, open(f"{OUT}/manifest.json","w"), indent=1)

if __name__=="__main__": main()
