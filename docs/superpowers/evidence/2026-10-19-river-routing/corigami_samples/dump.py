import re, sys
from collections import deque
f, N = sys.argv[1], int(sys.argv[2])
LINE = re.compile(r'<line stroke="(\w+)" x1="([\d.-]+)" y1="([\d.-]+)" x2="([\d.-]+)" y2="([\d.-]+)"')
s = N / 1000
hw, vw = set(), set()
for col, *c in LINE.findall(open(f).read()):
    if col != "green": continue
    X1, Y1, X2, Y2 = (round(float(v) * s) for v in c)
    if Y1 == Y2:
        for i in range(min(X1, X2), max(X1, X2)): hw.add((i, Y1))
    elif X1 == X2:
        for j in range(min(Y1, Y2), max(Y1, Y2)): vw.add((X1, j))
seen = {}; k = 0
for i in range(N):
    for j in range(N):
        if (i, j) in seen: continue
        q = deque([(i, j)]); seen[(i, j)] = k
        while q:
            a, b = q.popleft()
            for na, nb, bl in ((a+1,b,(a+1,b) in vw),(a-1,b,(a,b) in vw),(a,b+1,(a,b+1) in hw),(a,b-1,(a,b) in hw)):
                if 0<=na<N and 0<=nb<N and not bl and (na,nb) not in seen:
                    seen[(na,nb)] = k; q.append((na,nb))
        k += 1
sym = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
for j in range(N):
    print("".join(sym[seen[(i, j)] % len(sym)] for i in range(N)))
