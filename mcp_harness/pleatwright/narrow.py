"""COrigami §3.5 / App. G.2: narrowing by the clip pattern algorithm.

A narrowing template is a 2-D crease pattern drawn in the local frame of a
folded flap: u along the flap from the adapter start, w across it.  The clip
pattern algorithm projects it onto every layer of the flap through that
layer's own affine map (paper -> folded frame), swaps M/V on Z-flipped
layers, and clips the result to each face.

In this implementation the folded frame of every face is known exactly (the
strip map of `base.build`), so a template is represented by what it DOES to
the folded flap: a piecewise isometry psi of the strip.  Pre-images of psi's
crease lines through each face's map are the projected/clipped creases; the
composed maps psi o B give the narrowed folded state, and M/V (including the
Z-flip swap) falls out of the composed transforms.

Template ``asym2`` is Fig. 13(d), "2x asymmetric flap narrowing (simplified
base)", with template height H = current flap width, y down:

    D1  (0,0)-(H/2,H/2)     D2 (H/2,H/2)-(H,0)     Vc (H/2,H/2)-(H/2,H)
    Vb  u = H (full width)  Hm  w = H/2 for u >= H/2  (the narrowing pleat)

Solving for the regions' maps (each pair of neighbours related by the
reflection across their shared crease; all six close consistently):

    R1  u <= H/2, w >= u            identity           (the base adapter)
    R2  w <= u, w <= H - u          (w, u)
    R4  H/2 <= u <= H, w >= H/2     (H - u, w)
    R3  u + w >= H, w <= H/2, u<=H  (H - u, H - w)
    R5  u >= H, w <= H/2            (u - H, H - w)
    R6  u >= H, w >= H/2            (u - H, w)

so beyond the adapter the flap has width H/2 and is H shorter; the starting
edge u = 0 carries no interior vertex, as App. G.2 requires.  ``asym4`` is
asym2 applied twice (the second on the narrowed half).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Narrowing:
    stick: str
    chain: int
    s0: float          # strip position of the adapter start
    sigma: int         # +1 / -1: direction of the flap along the strip
    w_off: float       # current flap occupies w in [w_off, w_off + H]
    H: float

    # local <-> strip
    def local(self, s, w):
        return self.sigma * (s - self.s0), w - self.w_off

    def lines(self):
        """Template crease lines as (n, c) with n.(s, w) = c in strip coords."""
        H, sg, s0, wo = self.H, self.sigma, self.s0, self.w_off
        out = []
        # u = sg (s - s0); w' = w - wo
        # D1: w' = u        -> w - wo - sg s + sg s0 = 0
        out.append((np.array([-sg, 1.0]), wo - sg * s0))
        # D2: u + w' = H     -> sg s + w = H + wo + sg s0
        out.append((np.array([sg, 1.0]), H + wo + sg * s0))
        # Vc: u = H/2, Vb: u = H      -> s = s0 + sg u
        out.append((np.array([1.0, 0.0]), s0 + sg * H / 2))
        out.append((np.array([1.0, 0.0]), s0 + sg * H))
        # Hm: w' = H/2
        out.append((np.array([0.0, 1.0]), wo + H / 2))
        return out

    def map_at(self, s, w):
        """2x3 affine (strip -> strip) of the region containing (s, w)."""
        H = self.H
        u, v = self.local(s, w)
        e = 1e-12
        if u <= e:
            L = np.eye(2), np.zeros(2)                                # before adapter
        elif u <= H / 2 + e and v >= u - e:
            L = np.eye(2), np.zeros(2)                                # R1
        elif v <= u + e and v <= H - u + e and u <= H + e:
            L = np.array([[0, 1.0], [1.0, 0]]), np.zeros(2)           # R2 (w, u)
        elif u <= H + e and v >= H / 2 - e:
            L = np.array([[-1.0, 0], [0, 1.0]]), np.array([H, 0.0])   # R4
        elif u <= H + e:
            L = np.array([[-1.0, 0], [0, -1.0]]), np.array([H, H])    # R3
        elif v <= H / 2:
            L = np.array([[1.0, 0], [0, -1.0]]), np.array([-H, H])    # R5
        else:
            L = np.eye(2), np.array([-H, 0.0])                        # R6
        A, b = L
        # local = P (strip) + q ; strip = P^-1 (local) - ...
        P = np.array([[self.sigma, 0.0], [0.0, 1.0]])
        q = np.array([-self.sigma * self.s0, -self.w_off])
        # strip' = P^-1 (A (P x + q) + b - q)
        Pi = P  # P is its own inverse (sigma = +-1)
        M = Pi @ A @ P
        t = Pi @ (A @ q + b - q)
        return M, t

    def label_at(self, s, w, eps=1e-6):
        """Template M/V of the crease through strip point (s, w), read off
        Fig. 13(d): D1, D2, Vc mountain; Vb valley; the midline pleat Hm is
        valley inside the adapter (H/2 <= u <= H) and mountain beyond it.
        None if (s, w) is on no template crease."""
        H = self.H
        u, v = self.local(s, w)
        if u < -eps:
            return None
        if abs(v - u) < eps and u <= H / 2 + eps:
            return "M"                                   # D1
        if abs(u + v - H) < eps and H / 2 - eps <= u <= H + eps:
            return "M"                                   # D2
        if abs(u - H / 2) < eps and v >= H / 2 - eps:
            return "M"                                   # Vc
        if abs(u - H) < eps:
            return "V"                                   # Vb
        if abs(v - H / 2) < eps and u >= H / 2 - eps:
            return "V" if u <= H + eps else "M"          # Hm
        return None

    @property
    def new_width(self):
        return (self.w_off + self.H / 2, self.w_off + self.H)


TEMPLATES = {"asym2": 1, "asym4": 2}
