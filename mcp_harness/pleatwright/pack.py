"""COrigami §3.2 / App. E: discrete packing of a stick figure on a square grid.

Model (box pleating, L-infinity elevation).  Every grid cell belongs to one
contracted tree edge (a *flap* = leaf chain, or a *river* = hub-to-hub
chain).  Within an edge's region the elevation d(p) is the L-infinity
distance from p to that region's hinge lines; a flap of length L must reach
d = L and never exceed it, a river of length W is a band of L-infinity width
W.  Hinges are region boundaries and map to tree nodes; every hinge inside a
pocket belongs to that pocket's hub.

Search (following §3.2):

* grid size starts at the App. E.1 heuristic G_init and grows until a
  packing is found (even sizes for symmetric figures, as in E.1);
* rivers are placed first.  The first river spans the full grid width
  (straight river); every subsequent river is placed by wall-following:
  it runs parallel to the previous pocket's wall, so the hub chain becomes a
  stack of slabs separated by bands;
* each pocket (slab) is packed with its hub's flaps.  A pocket is tiled as
  rows of columns, mirror-symmetric about x = N/2: symmetric pairs take
  mirrored columns, unpaired flaps are centred on the axis.  Each flap
  column is a rectangle whose width/height realise exactly its length
  (a clipped 2L x 2L tip rectangle, Lang's minimum polygon);
* tiling via flap expansion: a column absorbs the cells around it by
  growing along its ridge (taller than L) or across its tip (wider than 2L
  when its depth is exactly L), or by a virtual hinge beyond the paper edge
  (the raw edge then sits at elevation delta > 0, as in COrigami's Avocet).

Candidates are ranked by a scoring heuristic (fewest virtual hinges, most
balanced rows) and the first one the base builder certifies is kept.
"""
from __future__ import annotations

import contextlib
import contextvars
import itertools
import math
from dataclasses import asdict, dataclass, field

from .stick import Contracted


@dataclass
class Region:
    chain: int
    rect: tuple                 # (x0, y0, x1, y1) integer grid, x right, y down
    vlines: list                # x of vertical hinge lines (may be virtual, outside paper)
    hlines: list                # y of horizontal hinge lines
    kind: str                   # 'flap' | 'river'
    L: int
    u_line: float | None = None  # river: y of its proximal (u) hinge
    virtual: list = field(default_factory=list)
    more: list = field(default_factory=list)   # further rectangles of the SAME region

    @property
    def rects(self) -> list:
        """Every rectangle of the region: a nested river band is several."""
        return [self.rect, *self.more]


@dataclass
class Layout:
    N: int
    regions: list               # list[Region]
    hub_order: list             # hubs top -> bottom
    bands: list                 # [(chain, y0, y1)]
    slabs: list                 # [(hub, y0, y1)]
    score: float = 0.0
    pockets: list = field(default_factory=list)   # nested layouts: [(hub, rect, sides)]
    family: str = "today"       # 'today' | 'beside' (nest.beside_candidates, river routing)


def layout_to_dict(lay: Layout) -> dict:
    """A JSON-safe copy of `lay` (tuples become lists; see layout_from_dict)."""
    return asdict(lay)


def layout_from_dict(d: dict) -> Layout:
    """Inverse of layout_to_dict: JSON turns every tuple into a list, so put
    back the ones the builder relies on (rects, bands, slabs, pockets)."""
    regions = [Region(**{**r, "rect": tuple(r["rect"]),
                         "more": [tuple(m) for m in r["more"]]})
               for r in d["regions"]]
    return Layout(d["N"], regions, list(d["hub_order"]),
                  [tuple(b) for b in d["bands"]], [tuple(s) for s in d["slabs"]],
                  d["score"],
                  [(h, tuple(rect), tuple(sides)) for h, rect, sides in d["pockets"]],
                  d.get("family", "today"))


# ------------------------------------------------------------------ App. E.1
def grid_init(con: Contracted) -> int:
    """G_init = max(ceil(sqrt(sum a_i)), D)  (App. E.1, eqs. 1-5)."""
    flaps = [c for c in con.chains if c.leaf]
    rivers = [c for c in con.chains if not c.leaf]
    big = sorted(flaps, key=lambda c: -c.length)[:4]
    area = sum(c.length ** 2 for c in big)
    area += sum(2 * c.length ** 2 for c in flaps if c not in big)
    for r in rivers:
        nb = [c for c in con.chains if c is not r and (c.u in (r.u, r.v) or c.v in (r.u, r.v))]
        if all(c.leaf for c in nb):
            m = max((c.length for c in nb), default=0)
            area += max(r.length * m, r.length ** 2)
        else:
            area += r.length ** 2
    # diameter: longest leaf-to-leaf path
    D = _diameter(con)
    G = max(math.ceil(math.sqrt(area)), D)
    if con.pairs and G % 2:
        G += 1
    return G


def _diameter(con: Contracted) -> int:
    adj = {}
    for c in con.chains:
        adj.setdefault(c.u, []).append((c.v, c.length))
        adj.setdefault(c.v, []).append((c.u, c.length))

    def far(src):
        best, dist, st = (src, 0), {src: 0}, [src]
        while st:
            u = st.pop()
            for v, L in adj[u]:
                if v not in dist:
                    dist[v] = dist[u] + L
                    if dist[v] > best[1]:
                        best = (v, dist[v])
                    st.append(v)
        return best
    a, _ = far(con.root)
    _, d = far(a)
    return d


# ------------------------------------------------------------------ helpers
def _hub_graph(con: Contracted) -> tuple[list, dict]:
    hubs = list(dict.fromkeys(con.hubs))
    nb = {h: [] for h in hubs}
    for c in con.chains:
        if not c.leaf:
            nb[c.u].append(c.v)
            nb[c.v].append(c.u)
    return hubs, nb


def hub_path(con: Contracted) -> list:
    """Hubs ordered along their (path-shaped) hub graph."""
    hubs, nb = _hub_graph(con)
    if len(hubs) == 1:
        return hubs
    if any(len(v) > 2 for v in nb.values()):
        raise PackError("hub graph is not a path; only straight/wall-following "
                        "river stacks are implemented")
    end = next(h for h in hubs if len(nb[h]) == 1)
    order, prev = [end], None
    while len(order) < len(hubs):
        cur = order[-1]
        nxt = [h for h in nb[cur] if h != prev][0]
        prev = cur
        order.append(nxt)
    return order


def _mirror(con: Contracted, a: int, b: int, pair: dict, kids: dict) -> dict | None:
    """Chain-id map {a: b, b: a, ...} over two subtrees that mirror each other
    (equal lengths, leaves matched through `pair`), or None."""
    ca, cb = con.chains[a], con.chains[b]
    if ca.length != cb.length or ca.leaf != cb.leaf:
        return None
    if ca.leaf:
        return {a: b, b: a} if pair.get(a) == b else None
    A, B = kids.get(ca.v, []), kids.get(cb.v, [])
    if len(A) != len(B):
        return None
    out, used = {a: b, b: a}, set()
    for x in A:
        for y in B:
            if y in used:
                continue
            m = _mirror(con, x, y, pair, kids)
            if m is not None:
                out.update(m)
                used.add(y)
                break
        else:
            return None
    return out


def hub_pairs(con: Contracted) -> list:
    """Mirrored pairs of hub subtrees, as (river_a, river_b, chain map): two
    child hubs of one parent whose rivers have equal length and whose subtrees
    match leaf for leaf through the declared leaf pairs (spec 2026-10-10 §1)."""
    pair = {}
    for a, b in con.pairs:
        pair[a], pair[b] = b, a
    kids = {}
    for c in con.chains:
        kids.setdefault(c.u, []).append(c.id)
    out = []
    for cs in kids.values():
        rivers = [i for i in cs if not con.chains[i].leaf]
        used = set()
        for i, a in enumerate(rivers):
            for b in rivers[i + 1:]:
                if a in used or b in used:
                    continue
                m = _mirror(con, a, b, pair, kids)
                if m is not None:
                    out.append((a, b, m))
                    used |= {a, b}
    return out


class PackError(Exception):
    pass


class BudgetExhausted(Exception):
    """The packer spent its `work_budget` before the search finished."""


#: [ticks used, limit] of the innermost `work_budget`; None = unlimited.
_BUDGET: contextvars.ContextVar = contextvars.ContextVar("pack_budget", default=None)


@contextlib.contextmanager
def work_budget(limit):
    """Bound the packer's search by a deterministic count of loop iterations
    (`tick`), not by wall-clock time, so the same tree is cut off at the same
    point on every machine.  `limit=None` is unlimited, as is code outside any
    `with`."""
    token = _BUDGET.set(None if limit is None else [0, limit])
    try:
        yield
    finally:
        _BUDGET.reset(token)


def tick(n: int = 1) -> None:
    """Spend `n` units of the current work budget; raise BudgetExhausted once
    more have been spent than the limit."""
    b = _BUDGET.get()
    if b is None:
        return
    b[0] += n
    if b[0] > b[1]:
        raise BudgetExhausted(f"packer work budget {b[1]} exhausted")


def work_used() -> int:
    """Ticks spent in the current budget (0 outside any budget)."""
    b = _BUDGET.get()
    return 0 if b is None else b[0]


@dataclass
class Item:
    """A packing unit inside a pocket: a mirrored pair, an axial flap, or (for
    asymmetric figures) a single flap."""
    chains: tuple       # (left, right) for pairs, (c,) for axial/single
    L: int
    axial: bool
    single: bool = False   # asymmetric mode: an unmirrored column


def _items(con: Contracted, hub: str, symmetric: bool) -> list:
    if not symmetric:
        return [Item((c.id,), c.length, False, True) for c in con.chains if c.leaf and c.u == hub]
    return _items_sym(con, hub)


def _items_sym(con: Contracted, hub: str) -> list:
    symmetric = True
    flaps = [c for c in con.chains if c.leaf and c.u == hub]
    paired = {}
    for a, b in con.pairs:
        paired[a] = b
        paired[b] = a
    items, used = [], set()
    for c in flaps:
        if c.id in used:
            continue
        p = paired.get(c.id)
        if symmetric and p is not None and con.chains[p].u == hub and \
                con.chains[p].length == c.length:
            items.append(Item((c.id, p), c.length, False))
            used |= {c.id, p}
        else:
            items.append(Item((c.id,), c.length, True))
            used.add(c.id)
    return items


# ------------------------------------------------------------------ row model
INF = 10 ** 9


def _vopts(L, h, top, bot):
    """Vertical options for a flap of length L in a row of height h.
    Returns (exact, flex): exact = vtag giving my > L (column width must then
    realise L exactly), flex = vtag giving my == L (column may be wider)."""
    exact = flex = None
    if top == "hinge" and bot == "hinge":
        if 2 * L < h:
            exact = ("hh",)
        elif 2 * L == h:
            flex = ("hh",)
        return exact, flex
    if top == "paper" and bot == "paper":
        exact = ("pp",)
        if 2 * L >= h and (2 * L - h) % 2 == 0:
            flex = ("pp_virt", (2 * L - h) // 2)
        return exact, flex
    if L < h:
        exact = ("free",)
    if L == h:
        flex = ("free",)
    elif h < 2 * L < 2 * h:
        flex = ("virt", 2 * L - h)
    return exact, flex


def _vline_parity_ok(vtag, p, y_paper):
    """A virtual horizontal hinge must lie on the row's parity class."""
    if p is None or vtag is None:
        return True
    if vtag[0] == "virt":
        y = y_paper - vtag[1] if y_paper == 0 else y_paper + vtag[1]
        return (y - p) % 2 == 0
    if vtag[0] == "pp_virt":
        return (vtag[1] - p) % 2 == 0     # paper edges 0 and N are even
    return True


def _row_concrete(items, hw, h, top, bot, y_paper, p, limit=6):
    """Concrete symmetric rows: list of (item, x0, x1, my, (vtag, htag)).
    p: parity every column boundary (and virtual line) must have, or None."""
    axial = [it for it in items if it.axial]
    pairs = [it for it in items if not it.axial]
    if len(axial) > 1:
        return []
    out = []

    def vchoice(it):
        ex, fl = _vopts(it.L, h, top, bot)
        if fl is not None and not _vline_parity_ok(fl, p, y_paper):
            fl = None
        if ex is not None and not _vline_parity_ok(ex, p, y_paper):
            ex = None
        return ex, fl

    if not pairs:
        it = axial[0]
        ex, fl = vchoice(it)
        if fl is not None:
            out.append([(it, 0, hw, it.L, (fl, ("free", "free")))])
        elif ex is not None and it.L >= hw:
            out.append([(it, 0, hw, INF, (ex, ("virt2", it.L - hw)))])
        return out
    vc = {id(it): vchoice(it) for it in items}
    if any(v == (None, None) for v in vc.values()):
        return []
    for e in pairs:
        inner = [it for it in pairs if it is not e]
        ex_e, fl_e = vc[id(e)]
        # edge column widths: exact [L, 2L], flex [L, inf)
        w_lo = e.L
        w_hi = INF if fl_e is not None else 2 * e.L
        fixed = sum(2 * it.L for it in inner)
        flex_inner = [it for it in inner if vc[id(it)][1] is not None]
        if axial:
            ax = axial[0]
            ex_a, fl_a = vc[id(ax)]
            a_lo, a_hi = ax.L, (INF if fl_a is not None else ax.L)
        else:
            a_lo = a_hi = 0
        for w in range(w_lo, min(w_hi, hw) + 1):
            if p is not None and (w - p) % 2:
                continue
            rem = hw - w - fixed
            if rem < a_lo:
                break
            extra = 0
            if rem > a_hi:
                extra = rem - a_hi
                if not flex_inner or extra % 2:
                    continue
            a = rem - extra
            if not axial and p is not None and (hw - p) % 2:
                continue
            sol, x = [], 0
            use_fl = w > 2 * e.L or (ex_e is None)
            vt = fl_e if use_fl else ex_e
            if vt is None:
                continue
            ht = ("free",) if (use_fl or w == e.L) else ("virt", 2 * e.L - w)
            sol.append((e, 0, w, e.L if use_fl else INF, (vt, ht)))
            x = w
            for it in inner:
                ex_i, fl_i = vc[id(it)]
                wi = 2 * it.L
                vt_i = ex_i if ex_i is not None else fl_i
                if extra and it is flex_inner[0]:
                    wi += extra
                    vt_i = fl_i
                sol.append((it, x, x + wi, it.L, (vt_i, None)))
                x += wi
            if axial:
                ex_a, fl_a = vc[id(axial[0])]
                vt_a = ex_a if (a == axial[0].L and ex_a is not None) else fl_a
                if vt_a is None:
                    continue
                sol.append((axial[0], x, hw, axial[0].L, (vt_a, None)))
            out.append(sol)
            if len(out) >= limit:
                return out
    return out


def _row_concrete_asym(items, N, h, top, bot, y_paper, p, limit=6):
    """Unmirrored rows (asymmetric figures): a left edge column, inner
    columns, a right edge column; every column records its own hinge lines
    (virtual ones past the paper edge included)."""
    vc = {}
    for it in items:
        ex, fl = _vopts(it.L, h, top, bot)
        if fl is not None and not _vline_parity_ok(fl, p, y_paper):
            fl = None
        if ex is not None and not _vline_parity_ok(ex, p, y_paper):
            ex = None
        if ex is None and fl is None:
            return []
        vc[id(it)] = (ex, fl)
    out = []
    if len(items) == 1:
        it = items[0]
        ex, fl = vc[id(it)]
        if fl is not None:
            out.append([(it, 0, N, it.L, (fl, ("explicit", [])))])
        elif ex is not None and 2 * it.L >= N:
            d1 = (2 * it.L - N) // 2
            d2 = 2 * it.L - N - d1
            if p is None or ((-d1 - p) % 2 == 0 and (N + d2 - p) % 2 == 0):
                out.append([(it, 0, N, INF, (ex, ("explicit", [-d1, N + d2])))])
        return out
    for eL in items:
        for eR in items:
            if eR is eL:
                continue
            inner = [it for it in items if it is not eL and it is not eR]
            fixed = sum(2 * it.L for it in inner)
            flex_inner = [it for it in inner if vc[id(it)][1] is not None]
            hiL = INF if vc[id(eL)][1] is not None else 2 * eL.L
            hiR = INF if vc[id(eR)][1] is not None else 2 * eR.L
            for wL in range(eL.L, min(hiL, N) + 1):
                if p is not None and (wL - p) % 2:
                    continue
                rem = N - wL - fixed
                if rem < eR.L:
                    break
                extra = 0
                wR = rem
                if wR > hiR:
                    extra = wR - hiR
                    wR = hiR
                    if not flex_inner or extra % 2:
                        continue
                if p is not None and (N - wR - p) % 2:
                    continue
                sol = []

                def edge(it, w, left, x0, x1):
                    ex, fl = vc[id(it)]
                    use_fl = w > 2 * it.L or ex is None
                    vt = fl if use_fl else ex
                    if left:
                        vl = [x1] if (use_fl or w == it.L) else [x0 - (2 * it.L - w), x1]
                    else:
                        vl = [x0] if (use_fl or w == it.L) else [x0, x1 + (2 * it.L - w)]
                    return (it, x0, x1, it.L if use_fl else INF, (vt, ("explicit", vl)))
                sol.append(edge(eL, wL, True, 0, wL))
                x = wL
                for it in inner:
                    ex_i, fl_i = vc[id(it)]
                    wi = 2 * it.L
                    vt_i = ex_i if ex_i is not None else fl_i
                    if extra and it is flex_inner[0]:
                        wi += extra
                        vt_i = fl_i
                    sol.append((it, x, x + wi, it.L, (vt_i, ("explicit", [x, x + wi]))))
                    x += wi
                sol.append(edge(eR, wR, False, x, N))
                out.append(sol)
                if len(out) >= limit:
                    return out
    return out


def _row_concrete_span(items, x0, x1, left, right, h, top, bot, y_paper, p, limit=6):
    """`_row_concrete_asym` on the span [x0, x1] (an off-axis pocket, nest.py).
    A `hinge` side is the inner edge of a river band: the column touching it
    has its hinge line ON that side, never a virtual line past it, and is
    sized as an inner column.  A `paper` side behaves as the paper edge does
    in `_row_concrete_asym`."""
    vc = {}
    for it in items:
        ex, fl = _vopts(it.L, h, top, bot)
        if fl is not None and not _vline_parity_ok(fl, p, y_paper):
            fl = None
        if ex is not None and not _vline_parity_ok(ex, p, y_paper):
            ex = None
        if ex is None and fl is None:
            return []
        vc[id(it)] = (ex, fl)

    def on_p(x):
        return p is None or (x - p) % 2 == 0
    if (left == "hinge" and not on_p(x0)) or (right == "hinge" and not on_p(x1)):
        return []
    W = x1 - x0
    out = []
    if len(items) == 1 and left == right == "paper":
        it = items[0]
        ex, fl = vc[id(it)]
        if fl is not None:
            out.append([(it, x0, x1, it.L, (fl, ("explicit", [])))])
        elif ex is not None and 2 * it.L >= W:
            d1 = (2 * it.L - W) // 2
            d2 = 2 * it.L - W - d1
            if on_p(x0 - d1) and on_p(x1 + d2):
                out.append([(it, x0, x1, INF, (ex, ("explicit", [x0 - d1, x1 + d2])))])
        return out

    def edge(it, w, is_left, a, b):
        ex, fl = vc[id(it)]
        use_fl = w > 2 * it.L or ex is None
        vt = fl if use_fl else ex
        if is_left:
            vl = [b] if (use_fl or w == it.L) else [a - (2 * it.L - w), b]
        else:
            vl = [a] if (use_fl or w == it.L) else [a, b + (2 * it.L - w)]
        return (it, a, b, it.L if use_fl else INF, (vt, ("explicit", vl)))

    lefts = items if left == "paper" else [None]
    rights = items if right == "paper" else [None]
    for eL in lefts:
        for eR in rights:
            if eL is not None and eR is eL:
                continue
            inner = [it for it in items if it is not eL and it is not eR]
            fixed = sum(2 * it.L for it in inner)
            flex_inner = [it for it in inner if vc[id(it)][1] is not None]
            loL = eL.L if eL else 0
            hiL = (INF if vc[id(eL)][1] is not None else 2 * eL.L) if eL else 0
            loR = eR.L if eR else 0
            hiR = (INF if vc[id(eR)][1] is not None else 2 * eR.L) if eR else 0
            for wL in range(loL, min(hiL, W) + 1):
                if eL is not None and not on_p(x0 + wL):
                    continue
                rem = W - wL - fixed
                if rem < loR:
                    break
                wR = rem if eR is not None else 0
                extra = rem - wR
                if eR is not None and wR > hiR:
                    extra, wR = wR - hiR, hiR
                if extra and (not flex_inner or extra % 2):
                    continue
                if eR is not None and not on_p(x1 - wR):
                    continue
                sol, x = [], x0
                if eL is not None:
                    sol.append(edge(eL, wL, True, x0, x0 + wL))
                    x = x0 + wL
                for it in inner:
                    ex_i, fl_i = vc[id(it)]
                    wi = 2 * it.L
                    vt_i = ex_i if ex_i is not None else fl_i
                    if extra and it is flex_inner[0]:
                        wi += extra
                        vt_i = fl_i
                    sol.append((it, x, x + wi, it.L, (vt_i, ("explicit", [x, x + wi]))))
                    x += wi
                if eR is not None:
                    sol.append(edge(eR, wR, False, x, x1))
                    x = x1
                if x != x1:
                    continue
                out.append(sol)
                if len(out) >= limit:
                    return out
    return out


def _row_concrete_sym_span(items, x0, x1, side, h, top, bot, y_paper, p, limit=6):
    """A mirror-symmetric row on the span [x0, x1], x0 + x1 == N (a centred
    pocket beside its parent's flaps, river routing).  `side` is the kind of
    BOTH span ends ('paper' | 'hinge').  Each mirrored pair appears twice, as
    its left member at [a, b] and its right member at [x0 + x1 - b, x0 + x1 -
    a] with mirrored vlines; at most one axial item sits centred.  The left
    half is nest.py's pair half: `_row_concrete_span` with a hinge on the
    axis.  Every entry carries an `explicit` htag, so `_row_regions` turns it
    into one Region."""
    axials = [it for it in items if it.axial]
    pairs = [it for it in items if not it.axial]
    if len(axials) > 1 or any(len(it.chains) != 2 for it in pairs) or (x0 + x1) % 2:
        return []
    S = x0 + x1
    c = S // 2

    def on_p(x):
        return p is None or (x - p) % 2 == 0

    halves = {}
    lefts = []
    for it in pairs:
        lm = Item((it.chains[0],), it.L, False, True)
        halves[id(lm)] = Item((it.chains[1],), it.L, False, True)
        lefts.append(lm)

    def mirrored(entry):
        it, a, b, my, (vtag, (_, vl)) = entry
        return (halves[id(it)], S - b, S - a, my, (vtag, ("explicit", sorted(S - v for v in vl))))

    # (axial entry or None, end of the left half)
    centres = []
    if not axials:
        centres.append((None, c))
    else:
        ax = axials[0]
        ex, fl = _vopts(ax.L, h, top, bot)
        if ex is not None and not _vline_parity_ok(ex, p, y_paper):
            ex = None
        if fl is not None and not _vline_parity_ok(fl, p, y_paper):
            fl = None
        for wa in range(2 * ax.L, S - 2 * x0 + 1, 2):
            vt = ex if wa == 2 * ax.L and ex is not None else fl
            if vt is None:
                continue
            xl = c - wa // 2
            if not on_p(xl) or (not lefts and xl != x0) or (lefts and xl <= x0):
                continue
            centres.append(((ax, xl, c + wa // 2, ax.L, (vt, ("explicit", [xl, c + wa // 2]))), xl))

    out = []
    for axial_entry, xl in centres:
        if lefts:
            halves_sol = _row_concrete_span(lefts, x0, xl, side, "hinge", h, top, bot,
                                            y_paper, p, limit)
        else:
            halves_sol = [[]] if side != "hinge" or on_p(x0) else []
        for left_sol in halves_sol:
            sol = list(left_sol) + ([axial_entry] if axial_entry else []) + \
                [mirrored(e) for e in left_sol]
            out.append(sorted(sol, key=lambda e: e[1]))
            if len(out) >= limit:
                return out
    return out


def _pocket_solutions(items, N, y0, y1, top, bot, max_rows=4, limit=24, rowfn=None):
    """Tile pocket [0,N] x [y0,y1] with rows of symmetric columns.  Yields
    lists of rows (ry0, ry1, row_solution, top, bot).  `rowfn` replaces the
    row builder (nest.py: an off-axis span); its signature is _row_concrete's."""
    hw = N // 2
    H = y1 - y0
    n = len(items)
    asym = any(it.single for it in items)
    if rowfn is None:
        rowfn = (lambda its, hw_, h_, t_, b_, yp_, p_, limit=6:
                 _row_concrete_asym(its, N, h_, t_, b_, yp_, p_, limit)) if asym else _row_concrete
    hinge_ys = ([y0] if top == "hinge" else []) + ([y1] if bot == "hinge" else [])
    pars = sorted({y % 2 for y in hinge_ys})
    if len(pars) > 1 and top == "hinge" and bot == "hinge" and n and \
            max_rows == 1:
        return
    p_choices = pars if pars else [0, 1]
    found = 0
    cache = {}
    for p in p_choices:
        if hinge_ys and any(y % 2 != p for y in hinge_ys):
            continue
        for nrows in range(1, min(max_rows, n) + 1):
            for assign in itertools.product(range(nrows), repeat=n):
                tick()
                if len(set(assign)) != nrows:
                    continue
                rows = [tuple(i for i in range(n) if assign[i] == r) for r in range(nrows)]
                if any(sum(1 for i in r if items[i].axial) > 1 for r in rows):
                    continue
                if asym and any(len(r) > 6 for r in rows):
                    continue
                # feasible heights per row, given its position
                feas = []
                for r in range(nrows):
                    t = top if r == 0 else "hinge"
                    b = bot if r == nrows - 1 else "hinge"
                    ypap = y0 if (r == 0 and top == "paper") else (y1 if (r == nrows - 1 and bot == "paper") else None)
                    hs = []
                    for hh in range(1, H + 1):
                        key = (rows[r], hh, t, b, p, ypap)
                        if key not in cache:
                            cache[key] = rowfn([items[i] for i in rows[r]], hw, hh, t, b,
                                               0 if ypap is None else ypap, p, limit=2)
                        if cache[key]:
                            hs.append(hh)
                    if not hs:
                        break
                    feas.append(hs)
                if len(feas) != nrows:
                    continue
                # compositions with internal boundaries on parity p
                for heights in _compose(feas, H, y0, p, nrows):
                    ys = [y0]
                    for hh in heights:
                        ys.append(ys[-1] + hh)
                    rows_out = []
                    for r in range(nrows):
                        t = top if r == 0 else "hinge"
                        b = bot if r == nrows - 1 else "hinge"
                        ypap = y0 if (r == 0 and top == "paper") else (y1 if (r == nrows - 1 and bot == "paper") else None)
                        sols = rowfn([items[i] for i in rows[r]], hw, heights[r], t, b,
                                     0 if ypap is None else ypap, p, limit=3)
                        rows_out.append([(ys[r], ys[r + 1], sol, t, b) for sol in sols])
                    for combo in itertools.product(*rows_out):
                        yield list(combo)
                        found += 1
                        if found >= limit:
                            return


def _compose(feas, H, y0, p, k, cap=40):
    """Height tuples (one per row, from feas lists) summing to H whose
    internal boundaries lie on parity p."""
    out = []

    def rec(r, y, acc):
        if len(out) >= cap:
            return
        if r == k - 1:
            hh = y0 + H - y
            if hh in feas[r]:
                out.append(acc + [hh])
            return
        for hh in feas[r]:
            yy = y + hh
            if yy >= y0 + H:
                break
            if (yy - p) % 2:
                continue
            rec(r + 1, yy, acc + [hh])
    rec(0, y0, [])
    return out


def _compositions(H, k, mins):
    if k == 1:
        if H >= mins[0]:
            yield [H]
        return
    for h in range(mins[0], H - sum(mins[1:]) + 1):
        for rest in _compositions(H - h, k - 1, mins[1:]):
            yield [h] + rest


# ------------------------------------------------------------------ regions
def _row_regions(N, ry0, ry1, sol, top, bot):
    """Turn a symmetric row solution into full-paper Regions."""
    regs = []
    hw = N // 2
    for it, x0, x1, my, virt in sol:
        vtag, htag = virt
        # horizontal hinge lines for this column
        hl = []
        if top == "hinge":
            hl.append(ry0)
        if bot == "hinge":
            hl.append(ry1)
        if vtag[0] == "virt":
            d = vtag[1]
            if top == "paper":
                hl.append(ry0 - d)
            else:
                hl.append(ry1 + d)
        elif vtag[0] == "pp_virt":
            d = vtag[1]
            hl += [ry0 - d, ry1 + d]
        if htag is not None and htag[0] == "explicit":
            regs.append(Region(it.chains[0], (x0, ry0, x1, ry1), sorted(set(htag[1])),
                               sorted(set(hl)), "flap", it.L))
            continue
        if it.axial:
            # centred column [N - x1 ... ] -> full width [x0, N - x0]
            X0, X1 = x0, N - x0
            vl = []
            if htag is None:
                vl = [X0, X1]
            elif htag[0] == "free":
                vl = []
            elif htag[0] == "virt2":
                vl = [X0 - htag[1], X1 + htag[1]]
            regs.append(Region(it.chains[0], (X0, ry0, X1, ry1), sorted(set(vl)), sorted(set(hl)),
                               "flap", it.L))
        else:
            left, right = it.chains
            if htag is None:
                vl = [x0, x1]
            elif htag[0] == "free":
                vl = [x1]
            else:
                vl = [x0 - htag[1], x1]
            vl = sorted(set(vl))
            regs.append(Region(left, (x0, ry0, x1, ry1), vl, sorted(set(hl)), "flap", it.L))
            regs.append(Region(right, (N - x1, ry0, N - x0, ry1), sorted(N - v for v in vl),
                               sorted(set(hl)), "flap", it.L))
    return regs


def _max_d(reg: Region) -> float:
    x0, y0, x1, y1 = reg.rect

    def axis_max(lo, hi, lines):
        if not lines:
            return math.inf
        # max over t in [lo,hi] of min |t - c|
        cands = [lo, hi]
        ls = sorted(lines)
        for a, b in zip(ls, ls[1:]):
            m = (a + b) / 2
            if lo <= m <= hi:
                cands.append(m)
        return max(min(abs(t - c) for c in ls) for t in cands)
    return min(axis_max(x0, x1, reg.vlines), axis_max(y0, y1, reg.hlines))


def _parity_ok(reg: Region) -> bool:
    """Ridges leave every vertical/horizontal hinge corner at 45 degrees; the
    accordion coordinate w = tri(x) on one side and tri(y) on the other agree
    along that ridge only if the corner lies on the x + y even lattice."""
    for x in reg.vlines:
        for y in reg.hlines:
            if (round(2 * x) + round(2 * y)) % 4 != 0:
                return False
    return True


# ------------------------------------------------------------------ search
def candidates(con: Contracted, *, N_min=None, N_max=160, per_N=60, symmetric=True):
    """Yield candidate Layouts in increasing grid size.  `symmetric=False`
    packs unmirrored rows (for figures whose declared pairs differ).  A
    branching hub graph is laid out by nest.py (spec 2026-10-10)."""
    _, nb = _hub_graph(con)
    if any(len(v) > 2 for v in nb.values()):
        from . import nest
        yield from nest.candidates(con, N_min=N_min, N_max=N_max, per_N=per_N,
                                   symmetric=symmetric)
        return
    hubs = hub_path(con)
    rivers = {}
    for c in con.chains:
        if not c.leaf:
            rivers[frozenset((c.u, c.v))] = c
    G = grid_init(con) if N_min is None else N_min
    G = max(G, 2)
    if G % 2:
        G += 1
    orders = (hubs, hubs[::-1]) if len(hubs) > 1 else (hubs,)
    for N in range(G, N_max + 1, 2):
        produced = 0
        for order in orders:
            k = len(order)
            bandW = [rivers[frozenset((order[i], order[i + 1]))].length for i in range(k - 1)]
            free = N - sum(bandW)
            if free < k:
                continue
            items = [_items(con, h, symmetric) for h in order]
            sides = [("paper" if i == 0 else "hinge", "paper" if i == k - 1 else "hinge")
                     for i in range(k)]
            fcache = {}

            def feasible(i, y0, H):
                key = (i, H, y0 % 2)
                if key not in fcache:
                    if not items[i]:
                        fcache[key] = True
                    else:
                        g = _pocket_solutions(items[i], N, y0, y0 + H, *sides[i], limit=1)
                        fcache[key] = next(g, None) is not None
                return fcache[key]

            # slab heights: dynamic programme over the slab start positions
            # (feasibility depends only on slab, height and start parity)
            reach = [dict() for _ in range(k + 1)]     # position -> list of (prev_pos, H)
            reach[0][0] = []
            for i in range(k):
                rest = sum(bandW[i:]) if i < k - 1 else 0
                for y in list(reach[i]):
                    if i == k - 1:
                        H = N - y
                        if H >= 1 and feasible(i, y, H):
                            reach[k].setdefault(N, []).append((y, H))
                        continue
                    for H in range(1, N - y - rest - (k - 1 - i) + 1):
                        if feasible(i, y, H):
                            ny = y + H + bandW[i]
                            reach[i + 1].setdefault(ny, []).append((y, H))

            def heights_rec(i, y, acc):
                # backtrack from (slab i ending at y) to slab 0
                if i == 0:
                    yield acc[::-1]
                    return
                for py, H in reach[i].get(y, [])[:4]:
                    yield from heights_rec(i - 1, py, acc + [H])
            for heights in itertools.islice(heights_rec(k, N, []), 6):
                y = 0
                slabs, bands = [], []
                for i in range(k):
                    slabs.append((order[i], y, y + heights[i]))
                    y += heights[i]
                    if i < k - 1:
                        bands.append((rivers[frozenset((order[i], order[i + 1]))].id, y, y + bandW[i]))
                        y += bandW[i]
                pocket_sols = []
                for i in range(k):
                    hub, a_, b_ = slabs[i]
                    if not items[i]:
                        pocket_sols.append([[]])
                        continue
                    pocket_sols.append(list(itertools.islice(
                        _pocket_solutions(items[i], N, a_, b_, *sides[i]), 8)))
                for combo in itertools.product(*pocket_sols):
                    tick()
                    regs = []
                    for rows in combo:
                        for ry0, ry1, sol, t, bb in rows:
                            regs += _row_regions(N, ry0, ry1, sol, t, bb)
                    if not all(abs(_max_d(r) - r.L) < 1e-9 and _parity_ok(r) for r in regs):
                        continue
                    for i, (cid, a_, b_) in enumerate(bands):
                        c = con.chains[cid]
                        u_top = c.u == order[i]
                        regs.append(Region(cid, (0, a_, N, b_), [], [a_ if u_top else b_], "river",
                                           c.length, u_line=a_ if u_top else b_))
                    lay = Layout(N, regs, order, bands, slabs)
                    lay.score = _score(lay)
                    yield lay
                    produced += 1
                    if produced >= per_N:
                        break
                if produced >= per_N:
                    break


def _score(lay: Layout) -> float:
    s = 0.0
    for r in lay.regions:
        x0, y0, x1, y1 = r.rect
        for v in r.vlines:
            if v < 0 or v > lay.N:
                s += 1.0
        for h in r.hlines:
            if h < 0 or h > lay.N:
                s += 1.0
    return s
