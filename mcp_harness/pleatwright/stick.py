"""COrigami §3.1 semantic stick figure, built from the artifact's metric trees.

The trees served in "Bases in Triplicate III" (fixtures/full17_v3_sticks) are
authored node lists ``{name, parent, length, direction}`` in the mesh's own
axes (+Y up, profile in the XY panel).  COrigami's stick figure is the same
object written as sticks: each non-root node is the END of one stick whose
``start`` is its parent, with an integer ``length`` and an ``azimuth_angle`` /
``elevation_angle`` (App. C.1 example).  We keep both forms.

Box pleating needs integer lengths on the grid.  COrigami's sticks are small
integers (the C.1 cat: 1, 3, 4); the authored trees use the mesh's grid
(4-23).  ``scale`` maps authored lengths to grid units, rounding half up and
never below 1; symmetric partners therefore stay equal.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

UP = np.array([0.0, 1.0, 0.0])


@dataclass
class Stick:
    name: str           # = name of the end node
    start: str
    end: str
    length: int         # grid units
    raw_length: float   # authored units
    direction: np.ndarray   # unit vector, mesh axes

    @property
    def azimuth(self) -> float:
        d = self.direction
        return math.degrees(math.atan2(-d[2], -d[0]))

    @property
    def elevation(self) -> float:
        return math.degrees(math.asin(max(-1.0, min(1.0, float(self.direction[1])))))


@dataclass
class StickFigure:
    name: str
    roll: str
    root: str
    sticks: list                    # list[Stick] in authored (BFS-compatible) order
    pairs: list                     # [(nodeA, nodeB)] symmetric leaf pairs
    scale: float
    readings: list = field(default_factory=list)

    # ---- topology -------------------------------------------------------
    def by_end(self) -> dict:
        return {s.end: s for s in self.sticks}

    def children(self) -> dict:
        ch = defaultdict(list)
        for s in self.sticks:
            ch[s.start].append(s.end)
        return ch

    def degree(self, node: str) -> int:
        d = sum(1 for s in self.sticks if s.start == node or s.end == node)
        return d

    def nodes(self) -> list:
        out = [self.root]
        for s in self.sticks:
            out.append(s.end)
        return out

    def leaves(self) -> list:
        ch = self.children()
        return [n for n in self.nodes() if not ch.get(n)]

    @property
    def complexity(self) -> int:
        """Number of branching levels (hubs on the longest hub chain)."""
        return max(1, len(self.hubs()))

    def hubs(self) -> list:
        return [n for n in self.nodes() if self.degree(n) >= 3]

    def positions(self, unit: bool = False) -> dict:
        """3-D node positions (mesh axes): root at origin, each stick laid
        along its direction with its grid length (or raw length)."""
        P = {self.root: np.zeros(3)}
        for s in self.sticks:
            L = s.raw_length * self.scale if not unit else 1.0
            P[s.end] = P[s.start] + s.direction * L
        return P

    def to_corigami_json(self) -> dict:
        return {
            "name": self.name, "complexity": self.complexity, "root": self.root,
            "children": [{"name": s.name, "start": s.start, "end": s.end,
                          "length": s.length,
                          "azimuth_angle": round(s.azimuth, 2),
                          "elevation_angle": round(s.elevation, 2)} for s in self.sticks],
            "symmetric_pairs": [list(p) for p in self.pairs],
        }


def load_roll(path: str, scale: float = 0.5) -> StickFigure:
    return load_tree(json.load(open(path)), scale)


def load_tree(d: dict, scale: float = 0.5) -> StickFigure:
    """`load_roll` for a tree already in memory (the artifact-fixture schema)."""
    nodes = d["nodes"]
    root = next(n["name"] for n in nodes if n["parent"] is None)
    # BFS order from root so every stick's start is placed before it
    ch = defaultdict(list)
    for n in nodes:
        if n["parent"] is not None:
            ch[n["parent"]].append(n)
    sticks, q = [], [root]
    while q:
        u = q.pop(0)
        for n in ch[u]:
            v = np.asarray(n["direction"], float)
            nv = np.linalg.norm(v)
            v = v / nv if nv > 0 else np.array([1.0, 0, 0])
            L = max(1, int(math.floor(n["length"] * scale + 0.5)))
            sticks.append(Stick(n["name"], u, n["name"], L, float(n["length"]), v))
            q.append(n["name"])
    pairs = [tuple(p) for p in d.get("pairs", [])]
    return StickFigure(d.get("subject", d.get("roll", "tree")), d.get("roll", d.get("subject", "tree")), root, sticks, pairs, scale,
                       d.get("readings", []))


# ---------------------------------------------------------------- contraction
@dataclass
class Chain:
    """A contracted tree edge: hub/root ``u`` -> ``v`` through degree-2 joints."""
    id: int
    u: str              # proximal node (towards the packing root)
    v: str              # distal node (hub or leaf)
    length: int
    sticks: list        # stick names from u outwards
    offsets: list       # cumulative start offset of each stick along the chain
    leaf: bool
    reversed: list = field(default_factory=list)   # stick traversed end -> start


@dataclass
class Contracted:
    root: str
    chains: list                    # list[Chain]
    hubs: list                      # hub names (degree >= 3, or the root)
    pairs: list                     # symmetric chain-id pairs (leaf chains)

    def chain_children(self) -> dict:
        out = defaultdict(list)
        for c in self.chains:
            out[c.u].append(c)
        return out

    def by_id(self, i) -> Chain:
        return self.chains[i]


def contract(sf: StickFigure, root: str | None = None) -> Contracted:
    """Merge degree-2 joints (COrigami App. C.2 / the packing view).

    The contraction root is the authored root if it is a hub, else the hub
    nearest it.  Chains are oriented away from that root.
    """
    adj = defaultdict(dict)
    for s in sf.sticks:
        adj[s.start][s.end] = s.name
        adj[s.end][s.start] = s.name
    deg = {n: len(adj[n]) for n in adj}
    hubs = [n for n in adj if deg[n] >= 3]
    if root is None:
        root = sf.root
        if deg.get(root, 0) < 3 and hubs:
            # nearest hub by BFS
            seen, q = {root}, [root]
            while q:
                u = q.pop(0)
                if deg[u] >= 3:
                    root = u
                    break
                for w in adj[u]:
                    if w not in seen:
                        seen.add(w)
                        q.append(w)
    length = {s.name: s.length for s in sf.sticks}
    start_of = {s.name: s.start for s in sf.sticks}
    chains = []
    seen = {root}
    stack = [root]
    while stack:
        u = stack.pop(0)
        for w in sorted(adj[u], key=lambda x: list(adj[u]).index(x)):
            if w in seen:
                continue
            names, offs, L, rev = [], [], 0, []
            prev, cur = u, w
            while True:
                seen.add(cur)
                sname = adj[prev][cur]
                names.append(sname)
                rev.append(start_of[sname] != prev)
                offs.append(L)
                L += length[sname]
                if deg[cur] != 2:
                    break
                nxt = [x for x in adj[cur] if x != prev][0]
                prev, cur = cur, nxt
            leaf = deg[cur] == 1
            chains.append(Chain(len(chains), u, cur, L, names, offs, leaf, rev))
            if not leaf:
                stack.append(cur)
    hubset = [root] + [c.v for c in chains if not c.leaf]
    end_to_chain = {c.v: c.id for c in chains}
    pairs = []
    for a, b in sf.pairs:
        if a in end_to_chain and b in end_to_chain:
            pairs.append((end_to_chain[a], end_to_chain[b]))
    # Declared pairs can name nodes the authored tree does not have (octopus_0
    # pairs arm*_tip_* while its leaves are arm*_base_*).  Recover mirrored
    # leaf chains by name: equal hub, equal length, names equal after the
    # left/right token.
    paired = {i for p in pairs for i in p}
    leaves = [c for c in chains if c.leaf and c.id not in paired]
    for c in leaves:
        if c.id in paired:
            continue
        for tok_l, tok_r in (("_L", "_R"), ("L_", "R_"), ("left", "right"), ("Left", "Right")):
            if tok_l in c.v:
                twin = c.v.replace(tok_l, tok_r)
                d = next((x for x in leaves if x.v == twin and x.id not in paired), None)
                if d is not None and d.u == c.u and d.length == c.length:
                    pairs.append((c.id, d.id))
                    paired |= {c.id, d.id}
                    break
    return Contracted(root, chains, hubset, pairs)
