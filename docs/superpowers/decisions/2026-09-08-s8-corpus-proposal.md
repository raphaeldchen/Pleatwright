# S8: candidate subjects for a corpus that can discriminate — PROPOSAL

**Status: RULED AND ADOPTED 2026-09-08.** All eight rows are now in
`anatomy_expectation.json` (15 subjects -> 22). The four rulings below were
decided by the repository owner, each matching the recommendation. What remains
before the corpus is usable is MESHES, not rows -- see "What adoption costs".

**Original status: proposal for review.** That file's contract is that every row is human-authored from published
anatomy with its own derivation and citation, and that nothing in it is
computed or read off an extraction. These rows were drafted by Claude and
require the owner's ruling before they become ground truth.

## Why the current corpus cannot discriminate

Nine subjects, and **eight are trivially exact in every arm ever run**. The
counts cluster: `5,5,6,6,6,6,6,9,9`. Five of the nine are the same body plan
(4 legs + head + tail = 6), so a model that pattern-matches "quadruped → 6"
scores five of nine correct without reading anything.

The fix is not more subjects. It is subjects **where the naive answer is
wrong** — where pattern-matching and correct anatomy disagree.

## Candidates

Every count below follows the committed convention: one leaf per terminal
appendage; each arm, leg, wing, tentacle or ray counts one; head counts one;
tail counts one when external; **digits, antennae, ears, eyes and non-skeletal
fins are excluded**. Hub precedent from the spider and octopus rows: the mass
the limbs attach to is the hub, the free axial mass is a flap.

| subject | count | naive answer | derivation | what it tests |
|---|---|---|---|---|
| **dolphin** | **4** | 5–6 | 2 pectoral flippers + tail fluke + head. The dorsal fin is excluded by the convention's own words — it has no skeletal support. Hindlimbs are absent in cetaceans. | the `MIN_LEAVES = 4` floor, and the fin exclusion |
| **guinea pig** | **5** | 6 | 4 legs + head. *Cavia porcellus* has **no external tail**, so this breaks the quadruped default the corpus is saturated with. | the tail rule on a mammal |
| **rabbit** | **6** | 8 | 4 legs + head + tail. Ears are named in the convention as sub-flap detail — on the one animal whose ears dominate its silhouette. | the ear exclusion (which my own hand-authored "faithful" dog got wrong) |
| **bat** | **6** | 4 | 2 wings + 2 legs + head + tail. Chiropteran forelimbs are wings; most microbats have an external tail. | wing-finding, which failed on the blue jay when the mesh fused them |
| **elephant** | **7** | 6 | 4 legs + head + tail + **trunk**. The trunk is a terminal muscular appendage, not a digit/antenna/ear. Ears excluded. | ⚠ RULING 1 — trunk as its own flap |
| **ant** | **8** | 7 | 6 legs + head + gaster. By the spider precedent the free axial abdomen is a flap and the thorax is the hub; an ant's gaster is joined by a petiole, so it is unambiguously free. Antennae excluded. | ⚠ RULING 2 — insect abdomen |
| **scorpion** | **9** | 11 | 8 legs + metasoma (tail). The prosoma is the hub, exactly as the spider's cephalothorax. **Pedipalps — the pincers — are excluded**, because the spider row already rules pedipalps sub-flap detail. There is no distinct head. | convention adherence against a very strong visual pull |
| **crab** | **10** | 8 | 10 legs. Decapods have five pairs of pereiopods and the **chelae are the first pair**, i.e. modified walking legs, not pedipalps. Cephalothorax is the hub; the abdomen is folded beneath and is not a free axial flap. | ⚠ RULING 3 — chelae as legs; also well above `MAX_LEAVES` |

Counts after adoption: `4,5,5,5,6,6,6,6,6,6,6,7,8,9,9,9,10` — versus today's
`5,5,6,6,6,6,6,9,9`.

## Citations

All Wikipedia, matching the style of every existing row.

* **Dolphin** — "Dolphin" / "Cetacea": forelimbs modified as flippers,
  hindlimbs absent, horizontal tail fluke; the dorsal fin is not skeletally
  supported.
* **Guinea pig** — "Guinea pig": *Cavia porcellus*, a tailless rodent.
* **Rabbit** — "Rabbit": Leporidae, four limbs, long ears, short tail.
* **Bat** — "Bat": order Chiroptera, forelimbs adapted as wings; most species
  have a tail enclosed in the uropatagium.
* **Elephant** — "Elephant": Elephantidae, characterised by a long proboscis
  (trunk), columnar limbs and large ear flaps.
* **Ant** — "Ant": Formicidae, six legs; the gaster is joined to the mesosoma
  by a narrow petiole.
* **Scorpion** — "Scorpion": order Scorpiones, eight legs, grasping pedipalps,
  narrow segmented metasoma ending in a telson.
* **Crab** — "Crab" / "Decapoda": ten pereiopods, the first pair bearing
  chelae; the abdomen is reduced and folded under the cephalothorax.

## Rulings — ALL DECIDED 2026-09-08 (owner), each as recommended

1. ✅ **Elephant trunk** — its own flap (7), or head detail (6)? Proposed: **its
   own flap.** It is long, terminal and load-bearing in a uniaxial base, which
   is what a flap is; and it is not in the convention's exclusion list.
2. ✅ **Insect abdomen** — does the spider's "free axial mass is a flap" rule
   carry to insects (ant = 8), or is it arachnid-specific (ant = 7)?
   Proposed: **it carries.** The reasoning in the spider row is about topology,
   not taxonomy.
3. ✅ **Crab chelae** — legs (10) or excluded like pedipalps (8)? Proposed:
   **legs.** Chelae are pereiopods; pedipalps are a different appendage, and
   the spider exclusion names pedipalps specifically.
4. ✅ **A below-floor subject** — should the corpus include something under
   `MIN_LEAVES = 4`, e.g. **snake = 2** (head + tail, no limbs)? Proposed:
   **not yet.** `not_a_ceiling` permits it, but a 2-flap subject tests the
   packer's refusal path rather than anatomy reading, which is a different
   question from the one S8 exists to answer.

## What adoption costs

Each subject needs a **mesh**, and the corpus is photo-derived: a source
photograph per subject, lifted through `tencent/Hunyuan3D-2` at the pinned seed
(~10 s per lift once the photo exists). The eight above are all readily
photographable in the whole-body, side-on, uncropped framing the lift needs.

⚠ **Not proposed: tardigrade / water bear.** Owner instruction, and they are
the same animal under two names at the same count — including both
double-weights one body plan, which is the failure this whole proposal exists
to fix.
