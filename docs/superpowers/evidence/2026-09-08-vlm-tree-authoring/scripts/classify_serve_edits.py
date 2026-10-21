"""What did the pipeline actually DO to each tree -- and did the anatomy survive?"""
import json, os, sys
R="<repo>"
H=f"{R}/mcp_harness"; E=f"{R}/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
sys.path.insert(0,H); os.chdir(H)
import pair_fusion as PF

def root_of(ns):
    return next((n["id"] for n in ns if n["parent_id"] is None), None)

def classify(x):
    req, srv = x["requested"], x["served_nodes"]
    if not srv: return "not served"
    st = x["stage"]
    if st == "stub":            return "engine ADDED a flap (stub)"
    if st == "flatten":         return f"joints merged ({len(req)}->{len(srv)})"
    if st == "placement":       return "initial x/y seeds added"
    if st == "order":           return "node list reordered"
    # stage 'none' -- attempt-0 exact. Did anything move anyway?
    same_ids = {n["id"] for n in req} == {n["id"] for n in srv}
    same_lens = (sorted(round(float(n["length"]),9) for n in req)
                 == sorted(round(float(n["length"]),9) for n in srv))
    if same_ids and same_lens and root_of(req) != root_of(srv):
        return f"RE-ROOTED ({root_of(req)} -> {root_of(srv)})"
    if [n["id"] for n in req] != [n["id"] for n in srv]:
        return "node list reordered (attempt-0)"
    return "no change -- packed as authored"

def main():
    D=f"{E}/data"
    rows=json.load(open(f"{D}/rule6_serve.json"))
    print(f"{'subject':12}{'stage':>11}   what changed")
    bad=[]
    for x in rows:
        what=classify(x)
        # ANATOMY CHECK: leaf-to-leaf distances must be identical
        keep=""
        if x["served_nodes"]:
            a=PF.leaf_distance_matrix(x["requested"])[1]
            b=PF.leaf_distance_matrix(x["served_nodes"])[1]
            same=({k:round(v,9) for k,v in a.items()}=={k:round(v,9) for k,v in b.items()})
            keep = "" if same else "   *** ANATOMY CHANGED ***"
            if not same: bad.append(x["subject"])
        x["what"]=what
        print(f"  {x['subject']:12}{str(x['stage']):>11}   {what}{keep}")
    json.dump(rows, open(f"{D}/rule6_serve.json","w"), indent=1)
    print(f"\nserves whose leaf-to-leaf distances changed: {bad if bad else 'NONE'}")
    import collections
    print("what changed, census:", dict(collections.Counter(x['what'].split(' (')[0] for x in rows)))

if __name__=="__main__": main()
