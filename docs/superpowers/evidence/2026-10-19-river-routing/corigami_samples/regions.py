"""Probe: segment COrigami packing_cp.svg into hinge-bounded regions; report region shapes."""
import os, re, sys
from collections import deque, Counter

root = sys.argv[1]
LINE = re.compile(r'<line stroke="(\w+)" x1="([\d.-]+)" y1="([\d.-]+)" x2="([\d.-]+)" y2="([\d.-]+)"')

def corners(cells):
    # count vertices of the rectilinear boundary: a lattice point is a vertex if the 2x2 occupancy around it is 1 or 3 cells, or a diagonal 2
    pts = Counter()
    s = set(cells)
    cand = set()
    for (i, j) in s:
        for dx in (0, 1):
            for dy in (0, 1):
                cand.add((i + dx, j + dy))
    n = 0
    for (x, y) in cand:
        occ = [(x - 1, y - 1) in s, (x, y - 1) in s, (x - 1, y) in s, (x, y) in s]
        k = sum(occ)
        if k in (1, 3):
            n += 1
        elif k == 2 and occ[0] == occ[3]:
            n += 2
    return n

rows = []
for d in sorted(os.listdir(root)):
    f = os.path.join(root, d, "packing_cp.svg")
    if not os.path.exists(f):
        continue
    N = int(d.rsplit("_", 1)[1])
    s = N / 1000.0
    txt = open(f).read()
    hwall, vwall = set(), set()   # hwall[(i,j)]: wall on horizontal line y=j between cell rows j-1 and j, at column i
    nlines = Counter()
    for col, x1, y1, x2, y2 in LINE.findall(txt):
        nlines[col] += 1
        if col not in ("green",):
            continue
        X1, Y1, X2, Y2 = (round(float(v) * s) for v in (x1, y1, x2, y2))
        if Y1 == Y2:
            for i in range(min(X1, X2), max(X1, X2)):
                hwall.add((i, Y1))
        elif X1 == X2:
            for j in range(min(Y1, Y2), max(Y1, Y2)):
                vwall.add((X1, j))
        else:
            nlines["green_diag"] += 1
    seen = {}
    regions = []
    for i in range(N):
        for j in range(N):
            if (i, j) in seen:
                continue
            q = deque([(i, j)]); seen[(i, j)] = len(regions); cells = [(i, j)]
            while q:
                a, b = q.popleft()
                for na, nb, blocked in ((a + 1, b, (a + 1, b) in vwall), (a - 1, b, (a, b) in vwall),
                                        (a, b + 1, (a, b + 1) in hwall), (a, b - 1, (a, b) in hwall)):
                    if 0 <= na < N and 0 <= nb < N and not blocked and (na, nb) not in seen:
                        seen[(na, nb)] = len(regions); cells.append((na, nb)); q.append((na, nb))
            regions.append(cells)
    shapes = []
    for cells in regions:
        xs = [c[0] for c in cells]; ys = [c[1] for c in cells]
        bw, bh = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1
        nv = corners(cells)
        rect = (bw * bh == len(cells))
        span = (bw == N) or (bh == N)
        shapes.append((len(cells), bw, bh, nv, rect, span))
    nonrect = [sh for sh in shapes if not sh[4]]
    rows.append((d, N, len(regions), len(nonrect), sorted(sh[3] for sh in nonrect), sum(1 for sh in shapes if sh[4] and sh[5]), sum(sh[0] for sh in nonrect) / (N * N), dict(nlines)))
for r in rows:
    print(f"{r[0][:40]:40s} N={r[1]:3d} regions={r[2]:3d} nonrect={r[3]:2d} vertices={r[4]} fullspan_rects={r[5]} nonrect_area_frac={r[6]:.2f} {r[7]}")
