import os, re, sys
from collections import deque
root = sys.argv[1]
LINE = re.compile(r'<line stroke="(\w+)" x1="([\d.-]+)" y1="([\d.-]+)" x2="([\d.-]+)" y2="([\d.-]+)"')
def regions(f, N):
    s = N / 1000; hw, vw = set(), set()
    for col, *c in LINE.findall(open(f).read()):
        if col != "green": continue
        X1, Y1, X2, Y2 = (round(float(v) * s) for v in c)
        if Y1 == Y2:
            for i in range(min(X1, X2), max(X1, X2)): hw.add((i, Y1))
        elif X1 == X2:
            for j in range(min(Y1, Y2), max(Y1, Y2)): vw.add((X1, j))
    seen = {}; regs = []
    for i in range(N):
        for j in range(N):
            if (i, j) in seen: continue
            q = deque([(i, j)]); seen[(i, j)] = len(regs); cells = [(i, j)]
            while q:
                a, b = q.popleft()
                for na, nb, bl in ((a+1,b,(a+1,b) in vw),(a-1,b,(a,b) in vw),(a,b+1,(a,b+1) in hw),(a,b-1,(a,b) in hw)):
                    if 0<=na<N and 0<=nb<N and not bl and (na,nb) not in seen:
                        seen[(na,nb)] = len(regs); cells.append((na,nb)); q.append((na,nb))
            regs.append(cells)
    return regs
tot = {"bent": 0, "samples_with_bent": 0, "closed": 0}
for d in sorted(os.listdir(root)):
    f = os.path.join(root, d, "packing_cp.svg")
    if not os.path.exists(f): continue
    N = int(d.rsplit("_", 1)[1])
    regs = regions(f, N)
    out = []
    for cells in regs:
        S = set(cells)
        xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
        bw, bh = max(xs)-min(xs)+1, max(ys)-min(ys)+1
        if bw * bh == len(cells): continue
        per = sum(1 for (a, b) in cells for (na, nb) in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)) if (na, nb) not in S)
        edges = "".join(e for e, cond in (("T", min(ys)==0), ("B", max(ys)==N-1), ("L", min(xs)==0), ("R", max(xs)==N-1)) if cond)
        # widths: lengths of maximal runs perpendicular... take min over cells of max(hrun, vrun)
        def run(a, b, dx, dy):
            n = 0
            while (a + dx*n, b + dy*n) in S: n += 1
            return n
        w = min(max(run(a,b,1,0)+run(a,b,-1,0)-1, run(a,b,0,1)+run(a,b,0,-1)-1) for (a,b) in cells)
        wmin = min(min(run(a,b,1,0)+run(a,b,-1,0)-1, run(a,b,0,1)+run(a,b,0,-1)-1) for (a,b) in cells)
        out.append(f"area={len(cells)} bbox={bw}x{bh} thin={wmin} edges={edges or '-'}")
        tot["bent"] += 1
        if not edges: tot["closed"] += 1
    if out: tot["samples_with_bent"] += 1
    print(f"{d[:34]:34s} N={N}: " + "; ".join(out))
print(tot)
