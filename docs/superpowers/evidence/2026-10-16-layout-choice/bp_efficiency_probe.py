"""Packing-only efficiency probe over the 51 artifact trees (no solve/shape).

Replicates pipeline._run's packing ladder, then measures the accepted layout.
Run from the worktree's mcp_harness/:  PY bp_efficiency_probe.py OUT.jsonl
"""
import json, math, os, sys, time
sys.path.insert(0, os.getcwd())
from pleatwright import stick as ST, pack as PK, base as B, shape as SH

STICKS = os.path.join(os.getcwd(), "fixtures", "full17_v3_sticks")


def clipped_ball(t, L, N):
    x0, x1 = max(0, t[0] - L), min(N, t[0] + L)
    y0, y1 = max(0, t[1] - L), min(N, t[1] + L)
    return max(0, x1 - x0) * max(0, y1 - y0)


def flap_metrics(r, N):
    """Area of the flap region vs the smallest L-inf ball (radius L, clipped to
    the paper) centred on any tip point of the region (d == L)."""
    area = sum(max(0, min(N, x1) - max(0, x0)) * max(0, min(N, y1) - max(0, y0))
               for x0, y0, x1, y1 in r.rects)
    x0, y0, x1, y1 = r.rect
    best = None
    for i in range(2 * max(0, x0), 2 * min(N, x1) + 1):
        for j in range(2 * max(0, y0), 2 * min(N, y1) + 1):
            p = (i / 2, j / 2)
            if abs(B._dist(r, p) - r.L) < 1e-9:
                a = clipped_ball(p, r.L, N)
                best = a if best is None else min(best, a)
    return area, best


def main(out):
    rolls = sorted(f[:-5] for f in os.listdir(STICKS) if f.endswith(".json"))
    fo = open(out, "w")
    for roll in rolls:
        t0 = time.perf_counter()
        src = os.path.join(STICKS, roll + ".json")
        scale = 1.0
        sf = ST.load_roll(src, scale)
        con = ST.contract(sf)
        sigma = SH.choose_sigma(sf, con)
        rec = {"roll": roll}
        flaps = [c for c in con.chains if c.leaf]
        rivers = [c for c in con.chains if not c.leaf]
        rec.update(n_flaps=len(flaps), n_rivers=len(rivers), n_hubs=len(con.hubs),
                   n_pairs=len(con.pairs), sum_flap=sum(c.length for c in flaps),
                   sum_river=sum(c.length for c in rivers),
                   max_flap=max(c.length for c in flaps),
                   diameter=PK._diameter(con), grid_init=PK.grid_init(con))
        base = lay = None
        tried = 0
        for rung, sc, symm in [("symmetric", 1.0, True), ("asymmetric", 1.0, False),
                               ("symmetric x2", 2.0, True)]:
            if sc != sf.scale:
                sf = ST.load_roll(src, sc)
                con = ST.contract(sf)
                sigma = SH.choose_sigma(sf, con)
            n_max = max(2 * PK.grid_init(con), PK.grid_init(con) + 60)
            for lay in PK.candidates(con, symmetric=symm, N_max=n_max):
                tried += 1
                b = B.build(lay, con, sigma)
                if not b.errors:
                    base = b
                    break
                if tried >= 400:
                    break
            if base is not None:
                rec["rung"] = rung
                break
            lay = None
        rec["tried"] = tried
        if base is None:
            rec["failure"] = "packing"
            fo.write(json.dumps(rec) + "\n"); fo.flush()
            continue
        N = lay.N
        rec["N"] = N
        flap_cells = river_cells = 0
        ball_sum = 0
        exp = []
        for r in lay.regions:
            if r.kind == "river":
                river_cells += sum(max(0, min(N, x1) - max(0, x0)) * max(0, min(N, y1) - max(0, y0))
                                   for x0, y0, x1, y1 in r.rects)
            else:
                a, bmin = flap_metrics(r, N)
                flap_cells += a
                ball_sum += bmin or 0
                exp.append(round(a / bmin, 3) if bmin else None)
        virt = 0
        for r in lay.regions:
            virt += sum(1 for v in r.vlines if v < 0 or v > N) + sum(1 for h in r.hlines if h < 0 or h > N)
        crease = {"H": 0, "R": 0, "P": 0}
        for k, v in base.creases.items():
            crease[v["kind"]] += 1
        rec.update(flap_cells=flap_cells, river_cells=river_cells, min_ball_sum=ball_sum,
                   flap_expansion=exp, virtual_lines=virt, unit_creases=crease,
                   hub_order=lay.hub_order, slabs=lay.slabs, bands=lay.bands,
                   secs=round(time.perf_counter() - t0, 2))
        fo.write(json.dumps(rec) + "\n"); fo.flush()
        print(roll, N, rec["grid_init"], rec["diameter"], rec.get("rung"), rec["secs"], flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
