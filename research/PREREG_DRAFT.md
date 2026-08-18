# Pre-registration draft — the confirmatory design Phase 4 freezes

**Status: DRAFT pending the owner's approval (D-010).** Everything in Part A
is already fixed by protocol and decision log and will be transcribed
verbatim. Part B contains the values the Phase 3 pilot now makes it possible
to set; each carries a proposed value and is *not* frozen until approved.
Registry: OSF (no account exists yet; creating one is the owner's step).

## Part A — fixed by PROTOCOL.md and DECISIONS.md (transcription)

- **Operational definition** (§1): attested, conventional, independent use by
  multiple unrelated authors; form rule `^[a-z]+$` (D-025).
- **Frame**: 9,787,841 words = the pinned universe (revision `c1139698`) plus
  binary-source contributions (D-026/D-030).
- **Confirmatory specification: S4** — feature-augmented two-class latent
  class model — selected by BIC among gate-survivors. S2, S3 and S5 were
  excluded by pre-declared recovery gates (D-035) and their exclusions are
  reported as results, not omissions: S5's three-class OCR structure is
  **exploratory only**.
- **Identifiability evidence**: S1 passes all five §5 checks (one optimum in
  50 starts, Fisher rank 25/25 at condition 4.4e5, no flat profiles); S4
  passes D-035 recovery in 5/5 replicates with max rate error 0.0027.
- **Adjudication protocol** (§8): four gates, fixed instrument order,
  90-second budget, mandatory search with observed tier, verdict table;
  the adjudicator is a noisy detector corrected by Rogan–Gladen (§6.4), with
  anchors, repeats, and a sensitivity band.
- **Stopping rules** SR1–SR5 with their thresholds (§7; D-032, D-035).

## Part B — set from the pilot, PROPOSED, awaiting approval

| Item | Proposed | Basis |
|---|---|---|
| Calibration sample | 1,500 items: **150 per posterior decile** over the frame, with the no-evidence stratum (845,150 words; D-032) sampled explicitly as its own 150-item stratum folded into the bottom decile's allocation | Pilot deciles in `fits/pilot.json`; D-032's stratification requirement |
| Oversample of disagreement cells | Within-decile sampling weights ×3 for the two structural disagreement families: valid-but-all-zero (76,951) and sowpods+csw21-not-valid (14,242) | Pilot §held-out: these are where old method and model disagree for knowable reasons |
| Expected-calibration-error bound | **ECE ≤ 0.05** (10 equal-mass bins, Rogan–Gladen-corrected, computed as the sensitivity band's midpoint) | At 150/bin, Wilson ±8pts at p=0.5; 0.05 is detectable without being trivially passable |
| Anchor items | 60 positives from the strong-positive test partition (never model-trained); 60 pseudo-words drawn from the Phase 2 char model, verified absent from every source | §6.4; leakage rule (features manifest) |
| Self-consistency | 150 re-presentations; report Cohen's κ; **no gate** (measurement, not criterion) | §6.4 |
| Primary outcomes | (1) reliability diagram + corrected ECE vs bound; (2) per-source α, β with intervals; (3) held-out agreement rate and the two disagreement families' adjudicated error split | §6.6 |
| Population estimate | Reported as the S4/S1 lower bound **with the homogeneity caveat stated as rendering it weak** (pilot: the bound barely exceeds the caught count); heterogeneity-robust estimation is declared future work, not smuggled in | §4; pilot capture section |

## What the pilot showed (context for the reviewer, not claims)

- π̂ = 0.0400 → 391,873 expected words in frame; 96.65% agreement with the
  held-out valid list at P > 0.5.
- The disagreements are structural, not noise: 142,232 valid-list words score
  low because their only attestation (Merriam-Webster) is deliberately not a
  detector; 186,106 non-list words score high, led by the Collins lineage the
  old pipeline never ingested. Phase 4's sample design targets both.
- The no-evidence stratum's posterior collapses to ~0 under S4 (expected
  words ≈ 1): with no detector and no corpus signal, orthotactics alone
  cannot overcome the prior — stated so the registration promises nothing
  there beyond adjudicated measurement.
