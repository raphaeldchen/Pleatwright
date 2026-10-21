"""Nested pockets: packing for branching hub graphs (spec 2026-10-10).

`pack.py` lays rivers as full-width bands, which needs the hubs in one chain.
Here every hub owns a rectangular *pocket*: the root's is the whole paper; a
child hub's region is a strip of its parent's pocket, its river is the band of
width W along every side of that strip that is not paper edge (an L-infinity
offset band, Box Pleating Studio's river contour), and its pocket is the strip
shrunk by W on those sides.  A pocket is a vertical stack of strips: the hub's
flap block (pack's row model) and one strip per child.  On the mirror axis a
mirrored pair of hub subtrees shares one strip, split at x = N/2: the left
child is packed, the right is its mirror image.

River routing (spec 2026-10-19 §4.2): a *beside strip* is a full-width strip
cut left to right into a box C for one child hub (its river is `band()` around
C's hinge sides: an L, a U or a ring) and one or two flank blocks of the
parent hub's own flaps.  In a symmetric pocket on the axis the strip is
[F | C | mirror(F)], C centred on x = N/2 (a U or a ring) and F the left
members of some of the hub's mirrored pairs.  `beside_candidates` yields only
layouts that use one.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

from .pack import (Item, Layout, Region, _items, _max_d, _parity_ok, _pocket_solutions,
                   _row_concrete_span, _row_concrete_sym_span, _row_regions, _score,
                   grid_init, hub_pairs, tick)

#: strip orders tried per pocket (5! = every order of a pocket of five strips)
ORDER_CAP = 120
#: beside strips per pocket (child strips replaced by a beside strip)
BESIDE_PER_POCKET = 2
#: items per flank set (a mirrored pair counts as one)
FLANK_MAX = 2


@dataclass(frozen=True)
class Box:
    """A rectangle of the grid and what lies past each side."""
    x0: int
    y0: int
    x1: int
    y1: int
    top: str        # 'paper' | 'hinge'
    bot: str
    left: str
    right: str

    def rows(self, y0: int, y1: int) -> "Box":
        """The full-width strip [y0, y1] of this box; inner edges are hinges."""
        return Box(self.x0, y0, self.x1, y1,
                   self.top if y0 == self.y0 else "hinge",
                   self.bot if y1 == self.y1 else "hinge", self.left, self.right)

    def key(self) -> tuple:
        """What feasibility depends on (translation in y keeps parity)."""
        return (self.x0, self.x1, self.y0 % 2, self.y1 - self.y0,
                self.top, self.bot, self.left, self.right)


def band(chain: int, W: int, box: Box) -> tuple[Region, Box] | None:
    """The river band of width W around `box`'s hinge sides, and the pocket it
    encloses; None if the box has no hinge side or no room for a pocket."""
    hinge = {s: getattr(box, s) == "hinge" for s in ("top", "bot", "left", "right")}
    if not any(hinge.values()):
        return None
    px0 = box.x0 + (W if hinge["left"] else 0)
    px1 = box.x1 - (W if hinge["right"] else 0)
    py0 = box.y0 + (W if hinge["top"] else 0)
    py1 = box.y1 - (W if hinge["bot"] else 0)
    if px1 <= px0 or py1 <= py0:
        return None
    rects = [r for r in ((box.x0, box.y0, box.x1, py0), (box.x0, py1, box.x1, box.y1),
                         (box.x0, py0, px0, py1), (px1, py0, box.x1, py1))
             if r[0] < r[2] and r[1] < r[3]]
    vl = sorted([box.x0] * hinge["left"] + [box.x1] * hinge["right"])
    hl = sorted([box.y0] * hinge["top"] + [box.y1] * hinge["bot"])
    reg = Region(chain, rects[0], vl, hl, "river", W, more=rects[1:])
    pocket = Box(px0, py0, px1, py1, box.top, box.bot, box.left, box.right)
    return reg, pocket


def mirror(reg: Region, N: int, m: dict) -> Region:
    """`reg` reflected in x = N/2, its chain swapped through the pair map."""
    def flip(r):
        return (N - r[2], r[1], N - r[0], r[3])
    return Region(m[reg.chain], flip(reg.rect), sorted(N - v for v in reg.vlines),
                  list(reg.hlines), reg.kind, reg.L, more=[flip(r) for r in reg.more])


class _Search:
    """Candidate layouts of one grid size N."""

    def __init__(self, con, N: int, symmetric: bool, beside: bool = False, shared=None):
        """`shared`: caches kept across the grid sizes of one beside search
        (beside_candidates); every key that could depend on N carries it."""
        self.con, self.N, self.symmetric, self.beside = con, N, symmetric, beside
        self.pairs = hub_pairs(con)
        self.kids = {}
        for c in con.chains:
            self.kids.setdefault(c.u, []).append(c)
        self.fcache = {} if shared is None else shared.setdefault("f", {})
        self.rcache = {} if shared is None else shared.setdefault("r", {})   # _span_row
        self._plists = {}               # (hub, axial) -> part_lists result
        self.pm = {}                    # chain -> its mirror image (flap and hub pairs)
        for a, b in con.pairs:
            self.pm[a], self.pm[b] = b, a
        for _, _, m in self.pairs:
            self.pm.update(m)

    def parts(self, hub: str, axial: bool) -> list:
        """The strips of `hub`'s pocket: ('flaps',), ('child', river),
        ('pair', index into self.pairs).  Pairs split only on the axis; off it,
        each member is its own strip."""
        kids = self.kids.get(hub, [])
        out = [("flaps",)] if any(c.leaf for c in kids) else []
        mine = [i for i, p in enumerate(self.pairs) if self.con.chains[p[0]].u == hub] \
            if axial else []
        paired = {x for i in mine for x in self.pairs[i][:2]}
        out += [("child", c.id) for c in kids if not c.leaf and c.id not in paired]
        out += [("pair", i) for i in mine]
        return out

    def part_lists(self, hub: str, axial: bool) -> list:
        """Every strip list tried for `hub`'s pocket.  Without beside strips it
        is today's one list.  With them: also the lists in which up to
        BESIDE_PER_POCKET child strips become ('beside', river, flank), `flank`
        a tuple of the hub's item chain-tuples that leave the hub's flap strip
        ('flaps', remaining), which is omitted when no item remains.  In a
        symmetric pocket on the axis the items are the mirrored ones (pairs and
        axial flaps) and only pairs flank.  Those lists come first; today's
        list is last.  Memoized per (hub, axial); the lists are tuples, so a
        caller cannot mutate the cache."""
        key = (hub, axial)
        hit = self._plists.get(key)
        if hit is None:
            hit = self._plists[key] = tuple(tuple(l) for l in self._part_lists(hub, axial))
        return hit

    def _part_lists(self, hub: str, axial: bool) -> list:
        plain = self.parts(hub, axial)
        if not self.beside:
            return [plain]
        kids = [i for i, p in enumerate(plain) if p[0] == "child"]
        sym = self.symmetric and axial
        items = sorted(_items(self.con, hub, sym), key=lambda it: (-it.L, it.chains))
        chains = [it.chains for it in items]
        pool = [it.chains for it in items if not it.axial]
        flanks = [f for k in range(1, FLANK_MAX + 1) for f in itertools.combinations(pool, k)]
        out = []
        for j in range(1, min(BESIDE_PER_POCKET, len(kids)) + 1):
            for which in itertools.combinations(kids, j):
                for fs in itertools.product(flanks, repeat=j):
                    used = [ch for f in fs for ch in f]
                    if len(set(used)) != len(used):
                        continue
                    rest = tuple(ch for ch in chains if ch not in used)
                    lst = []
                    for i, p in enumerate(plain):
                        if p[0] == "flaps":
                            if rest:
                                lst.append(("flaps", rest))
                        elif i in which:
                            lst.append(("beside", p[1], fs[which.index(i)]))
                        else:
                            lst.append(p)
                    out.append(lst)
        return out + [plain]

    def orders(self, parts: list) -> list:
        """Strip orders, those putting children against the paper first (a band
        side against paper is a band side not drawn).  At most ORDER_CAP: a
        pocket of many strips never enumerates its k! orders."""
        k = len(parts)
        if k <= 5:
            return sorted(itertools.permutations(parts),
                          key=lambda o: sum(1 for i, p in enumerate(o)
                                            if p[0] != "flaps" and 0 < i < k - 1))
        flaps = [p for p in parts if p[0] == "flaps"]
        kids = [p for p in parts if p[0] != "flaps"]
        best = kids[:len(kids) // 2] + flaps + kids[len(kids) // 2:]   # children at both ends
        return list(itertools.islice(itertools.permutations(best), ORDER_CAP))

    def feasible(self, hub: str, part: tuple, box: Box, axial: bool) -> bool:
        key = (hub, part, box.key(), axial)
        if self.beside:
            # off the axis nothing depends on x but its parity (span rows, band
            # corners) nor on N, so beside searches share one entry per even
            # shift; on the axis the entry is N's own
            key = (hub, part, (box.x0 % 2, box.x1 - box.x0) + box.key()[2:], axial) \
                if not axial else key + (self.N,)
        if key not in self.fcache:
            self.fcache[key] = next(self.part(hub, part, box, axial), None) is not None
        return self.fcache[key]

    def heights(self, hub: str, box: Box, axial: bool, order: tuple):
        """Strip heights summing to the box height, each strip feasible."""
        k = len(order)
        reach = [dict() for _ in range(k + 1)]
        reach[0][box.y0] = []
        for i, part in enumerate(order):
            for y in reach[i]:
                hs = [box.y1 - y] if i == k - 1 else range(1, box.y1 - y - (k - 1 - i) + 1)
                for hh in hs:
                    tick()
                    if hh >= 1 and self.feasible(hub, part, box.rows(y, y + hh), axial):
                        reach[i + 1].setdefault(y + hh, []).append((y, hh))

        def back(i, y, acc):
            if i == 0:
                yield acc[::-1]
                return
            for py, hh in reach[i].get(y, [])[:4]:
                yield from back(i - 1, py, acc + [hh])
        yield from back(k, box.y1, [])

    def fill(self, hub: str, box: Box, axial: bool, limit: int = 24, need: bool = False):
        """Yield (regions, pockets, nbeside) tilings of `hub`'s pocket `box`;
        nbeside counts the beside strips used.  `need`: only tilings that use
        at least one (beside_candidates' root)."""
        found = 0
        for parts in self.part_lists(hub, axial):
            for order in self.orders(parts):
                tick()
                for hs in itertools.islice(self.heights(hub, box, axial, order), 6):
                    tick()
                    ys = list(itertools.accumulate(hs, initial=box.y0))
                    sols = []
                    for part, a, b in zip(order, ys, ys[1:]):
                        sols.append(list(itertools.islice(
                            self.part(hub, part, box.rows(a, b), axial), 8)))
                        if not sols[-1]:
                            break
                    else:
                        for combo in itertools.product(*sols):
                            tick()
                            nb = sum(n for _, _, n in combo)
                            if need and not nb:
                                continue
                            regs = [r for rs, _, _ in combo for r in rs]
                            pockets = [(hub, (box.x0, box.y0, box.x1, box.y1),
                                        (box.top, box.bot, box.left, box.right))]
                            pockets += [p for _, ps, _ in combo for p in ps]
                            yield regs, pockets, nb
                            found += 1
                            if found >= limit:
                                return

    def part(self, hub: str, part: tuple, box: Box, axial: bool):
        """Yield (regions, pockets, nbeside) for one strip of `hub`'s pocket."""
        N = self.N
        if part[0] == "flaps":
            yield from self.flaps(hub, box, axial, part[1] if len(part) > 1 else None)
        elif part[0] == "child":
            yield from self.child(part[1], box, axial)
        elif part[0] == "beside":
            if self.symmetric and axial:
                yield from self.beside_centred(hub, part[1], part[2], box)
            else:
                yield from self.beside_strip(hub, part[1], part[2], box)
        else:
            a, b, m = self.pairs[part[1]]
            half = Box(box.x0, box.y0, N // 2, box.y1, box.top, box.bot, box.left, "hinge")
            for regs, pockets, nb in self.child(a, half, False):
                yield regs + [mirror(r, N, m) for r in regs], pockets, 2 * nb

    def child(self, river: int, box: Box, axial: bool):
        c = self.con.chains[river]
        made = band(river, c.length, box)
        if made is None or not _parity_ok(made[0]):
            return
        reg, pocket = made
        for regs, pockets, nb in self.fill(c.v, pocket, axial):
            yield [reg] + regs, pockets, nb

    def beside_strip(self, hub: str, river: int, flank: tuple, box: Box):
        """Yield (regions, pockets, nbeside) for a beside strip `box`: child box
        C of `river` (its band and the child's pocket, filled off the axis) and
        flank blocks of `flank`, in the arrangements [C | F], [F | C] and
        [F1 | C | F2]."""
        c = self.con.chains[river]
        W = c.length
        if box.y1 - box.y0 <= W * ((box.top == "hinge") + (box.bot == "hinge")):
            return                                  # no band of width W fits across C
        by = {it.chains: it for it in _items(self.con, hub, False)}
        items = [by[ch] for ch in flank]
        for C, blocks in self._arrangements(items, W, box):
            tick()
            made = band(river, W, C)
            if made is None or not _parity_ok(made[0]):
                continue
            reg, pocket = made
            ckey = ("fill", c.v, pocket.x0 % 2, pocket.x1 - pocket.x0, pocket.y0 % 2,
                    pocket.y1 - pocket.y0, pocket.top, pocket.bot, pocket.left, pocket.right)
            if ckey not in self.fcache:
                self.fcache[ckey] = next(self.fill(c.v, pocket, False), None) is not None
            if not self.fcache[ckey]:
                continue
            fsols = [list(itertools.islice(self._span(its, a, b, l, r, box), 3))
                     for its, a, b, l, r in blocks]
            for regs, pockets, nb in self.fill(c.v, pocket, False):
                for combo in itertools.product(*fsols):
                    tick()
                    yield [reg] + regs + [x for rs in combo for x in rs], pockets, 1 + nb

    def beside_centred(self, hub: str, river: int, flank: tuple, box: Box):
        """Yield (regions, pockets, nbeside) for a beside strip `box` of a
        symmetric pocket on the axis: [F | C | mirror(F)], C centred on the
        box's centre (x = N/2), its band a U or a ring and the child's pocket
        filled on the axis; F packs the left members of the flank's mirrored
        pairs as single flaps.  A flank holding an axial item yields nothing."""
        c = self.con.chains[river]
        W = c.length
        if box.y1 - box.y0 <= W * ((box.top == "hinge") + (box.bot == "hinge")):
            return
        by = {it.chains: it for it in _items(self.con, hub, True)}
        if any(ch not in by or by[ch].axial for ch in flank):
            return
        items = [by[ch] for ch in flank]
        lefts = [Item((it.chains[0],), it.L, False, True) for it in items]
        span = box.x1 - box.x0
        cx = (box.x0 + box.x1) // 2
        f = max(it.L for it in lefts)
        for wc in range(2 * W + 1, span - 2 * f + 1):
            if (span - wc) % 2:
                continue
            a, b = cx - wc // 2, cx + wc // 2
            if not self._span_ok(lefts, box.x0, a, box.left, "hinge", box):
                continue
            tick()
            C = Box(a, box.y0, b, box.y1, box.top, box.bot, "hinge", "hinge")
            made = band(river, W, C)
            if made is None or not _parity_ok(made[0]):
                continue
            reg, pocket = made
            ckey = ("fill", c.v, True, self.N) + pocket.key()
            if ckey not in self.fcache:
                self.fcache[ckey] = next(self.fill(c.v, pocket, True), None) is not None
            if not self.fcache[ckey]:
                continue
            fsols = list(itertools.islice(self._span(lefts, box.x0, a, box.left, "hinge", box), 3))
            for regs, pockets, nb in self.fill(c.v, pocket, True):
                for fs in fsols:
                    tick()
                    yield ([reg] + regs + fs + [mirror(r, self.N, self.pm) for r in fs],
                           pockets, 1 + nb)

    def _arrangements(self, items: list, W: int, box: Box):
        """(C, flank blocks) of a beside strip whose flank blocks can be packed,
        a flank block being (items, x0, x1, left, right).  C is at least W + 1
        wide per hinge side across it, a block at least its longest flap."""
        x0, x1 = box.x0, box.x1

        def lo(its):
            return max(it.L for it in its)

        def cmin(left, right):
            return 1 + W * ((left == "hinge") + (right == "hinge"))

        def ok(its, a, b, left, right):
            return self._span_ok(its, a, b, left, right, box)
        f = lo(items)
        for wc in range(cmin(box.left, "hinge"), x1 - x0 - f + 1):          # [C | F]
            if ok(items, x0 + wc, x1, "hinge", box.right):
                yield (Box(x0, box.y0, x0 + wc, box.y1, box.top, box.bot, box.left, "hinge"),
                       [(items, x0 + wc, x1, "hinge", box.right)])
        for wc in range(cmin("hinge", box.right), x1 - x0 - f + 1):         # [F | C]
            if ok(items, x0, x1 - wc, box.left, "hinge"):
                yield (Box(x1 - wc, box.y0, x1, box.y1, box.top, box.bot, "hinge", box.right),
                       [(items, x0, x1 - wc, box.left, "hinge")])
        cm = cmin("hinge", "hinge")
        for k in range(1, len(items)):                                      # [F1 | C | F2]
            f1, f2 = items[:k], items[k:]
            As = [a for a in range(x0 + lo(f1), x1 - lo(f2) - cm + 1)
                  if ok(f1, x0, a, box.left, "hinge")]
            Bs = [b for b in range(x0 + lo(f1) + cm, x1 - lo(f2) + 1)
                  if ok(f2, b, x1, "hinge", box.right)] if As else []
            for a in As:
                for b in Bs:
                    if b - a >= cm:
                        yield (Box(a, box.y0, b, box.y1, box.top, box.bot, "hinge", "hinge"),
                               [(f1, x0, a, box.left, "hinge"), (f2, b, x1, "hinge", box.right)])

    def _span_row(self, its, x0, x1, left, right, h, t, b, yp, p, limit):
        """`_row_concrete_span`, cached per search.  Every check it makes on x is
        a parity, so it is computed once on the span shifted to x0 % 2 and its
        columns shifted back (all of its hinge lines are explicit).  `yp` only
        enters through `_vline_parity_ok` (is it 0, and its parity)."""
        dx = x0 - x0 % 2
        key = (tuple([it.chains for it in its]), x0 % 2, x1 - x0, left, right, h, t, b,
               yp == 0, yp % 2, p, limit)
        sols = self.rcache.get(key)
        if sols is None:
            sols = self.rcache[key] = _row_concrete_span(
                its, x0 - dx, x1 - dx, left, right, h, t, b, yp, p, limit)
        if not dx:
            return sols
        return [[(it, a + dx, c + dx, my, (vt, (ht[0], [v + dx for v in ht[1]])))
                 for it, a, c, my, (vt, ht) in sol] for sol in sols]

    def _span(self, items: list, x0: int, x1: int, left: str, right: str, box: Box):
        """Regions of `items` packed in rows on the span [x0, x1] of strip `box`."""
        def rowfn(its, hw, h, t, b, yp, p, limit=6):
            return self._span_row(its, x0, x1, left, right, h, t, b, yp, p, limit)
        yield from self._good(_pocket_solutions(items, self.N, box.y0, box.y1, box.top,
                                                box.bot, rowfn=rowfn))

    def _span_ok(self, items: list, x0: int, x1: int, left: str, right: str, box: Box) -> bool:
        """Whether `_span` yields anything (cached; an even shift in x or y
        keeps every parity the span rows check)."""
        key = ("span", tuple(it.chains for it in items), x0 % 2, x1 - x0, left, right,
               box.y0 % 2, box.y1 - box.y0, box.top, box.bot)
        if key not in self.fcache:
            self.fcache[key] = next(self._span(items, x0, x1, left, right, box), None) is not None
        return self.fcache[key]

    def _good(self, gen):
        """Regions of each row tiling from `gen` whose flaps all reach their
        length and keep hinge-corner parity."""
        for rows in gen:
            regs = []
            for ry0, ry1, sol, t, b in rows:
                regs += _row_regions(self.N, ry0, ry1, sol, t, b)
            if all(abs(_max_d(r) - r.L) < 1e-9 and _parity_ok(r) for r in regs):
                yield regs

    def flaps(self, hub: str, box: Box, axial: bool, only: tuple | None = None):
        """The hub's flap strip; `only`: the chain-tuples of the items it packs
        (the rest flank beside strips)."""
        items = _items(self.con, hub, self.symmetric if axial else False)
        if only is not None:
            items = [it for it in items if it.chains in only]
        if axial and (box.x0, box.x1) != (0, self.N):
            # a centred pocket on the axis (beside_centred): box.left == box.right
            def rowfn(its, hw, h, t, b, yp, p, limit=6):
                return _row_concrete_sym_span(its, box.x0, box.x1, box.left, h, t, b, yp, p,
                                              limit)
            gen = self._good(_pocket_solutions(items, self.N, box.y0, box.y1, box.top, box.bot,
                                               rowfn=rowfn))
        elif axial:
            gen = self._good(_pocket_solutions(items, self.N, box.y0, box.y1, box.top, box.bot))
        else:
            gen = self._span(items, box.x0, box.x1, box.left, box.right, box)
        for regs in gen:
            yield regs, [], 0


def candidates(con, *, N_min=None, N_max=160, per_N=60, symmetric=True):
    """Yield nested Layouts in increasing grid size (pack.candidates' contract)."""
    yield from _layouts(con, N_min, N_max, per_N, symmetric, beside=False)


def beside_candidates(con, *, N_min=None, N_max=160, per_N=60, symmetric=True):
    """Yield Layouts (family 'beside') that use at least one beside strip, in
    increasing grid size; nothing for a tree with a single hub."""
    if len(con.hubs) == 1:
        return
    yield from _layouts(con, N_min, N_max, per_N, symmetric, beside=True)


def _layouts(con, N_min, N_max, per_N, symmetric, beside):
    G = grid_init(con) if N_min is None else N_min
    G = max(G, 2)
    G += G % 2
    hub_order = [con.root] + [c.v for c in con.chains if not c.leaf]
    shared = {} if beside else None
    for N in range(G, N_max + 1, 2):
        search = _Search(con, N, symmetric, beside=beside, shared=shared)
        paper = Box(0, 0, N, N, "paper", "paper", "paper", "paper")
        for regs, pockets, _ in itertools.islice(
                search.fill(con.root, paper, True, limit=per_N, need=beside), per_N):
            lay = Layout(N, regs, hub_order, [], [], pockets=pockets,
                         family="beside" if beside else "today")
            lay.score = _score(lay)
            yield lay
