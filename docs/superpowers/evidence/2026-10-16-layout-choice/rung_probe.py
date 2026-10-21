"""First-certified N per ladder rung, each rung run on its own (not first-fit)."""
import json, os, sys, time
sys.path.insert(0, os.getcwd())
from pleatwright import stick as ST, pack as PK, base as B, shape as SH
STICKS = os.path.join(os.getcwd(), "fixtures", "full17_v3_sticks")
rung, sc, symm = sys.argv[2], float(sys.argv[3]), sys.argv[4] == "1"
maxN = int(sys.argv[5])
fo = open(sys.argv[1], "a")
for roll in sorted(f[:-5] for f in os.listdir(STICKS) if f.endswith(".json")):
    t0 = time.perf_counter()
    sf = ST.load_roll(os.path.join(STICKS, roll + ".json"), sc)
    con = ST.contract(sf); sigma = SH.choose_sigma(sf, con)
    n_max = min(maxN, max(2 * PK.grid_init(con), PK.grid_init(con) + 60))
    N = None; tried = 0
    for lay in PK.candidates(con, symmetric=symm, N_max=n_max):
        tried += 1
        if not B.build(lay, con, sigma).errors:
            N = lay.N; break
        if tried >= 400: break
    fo.write(json.dumps({"roll": roll, "rung": rung, "N": N, "tried": tried, "grid_init": PK.grid_init(con), "secs": round(time.perf_counter()-t0,2)}) + "\n"); fo.flush()
