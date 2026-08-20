# Phase 3 — the model, the gates, and the pilot

Measured 2026-08-18 over 9,787,841 frame words, 677 evidence patterns, K = 12 detectors. Determinism verified: the selected fit re-run from its seed produces bit-identical posteriors (sha256 match).

## Selection

| Spec | log-lik | params | BIC | SR5 (D-035) | Eligible |
|---|---:|---:|---:|---|---|
| S1 | -6,951,375 | 25 | 13,903,153 | passes | yes |
| S2 | -6,061,493 | 43 | 12,123,678 | FIRES | no |
| S3 | -5,991,592 | 37 | 11,983,779 | FIRES | no |
| S4 | -6,266,369 | 38 | 12,533,351 | passes | **selected** |
| S5 | -5,486,926 | 64 | 10,974,883 | FIRES | no |

**Selected: S4** — lowest BIC among the specifications that pass their gates. Exclusions are results: S2's interaction terms sit on a likelihood plateau at the observed near-duplicate dependence (max |λ̂−λ| ≈ 0.75–0.79 against D-035's 0.15) even as its rates and prevalence recover; S3 never converged on the real table and failed recovery in 3 of 5 replicates — the random effect absorbs the class structure at this sparsity.

## The misspecification cross (reported, never gated)

S1 fitted to S2-generated worlds — the price of ignoring the declared dependence:

| Replicate | π̂ vs π | max abs α err | max abs β err |
|---|---:|---:|---:|
| 0 | -3.9% | 0.0244 | 0.0014 |
| 1 | -4.2% | 0.0265 | 0.0015 |
| 2 | -3.9% | 0.0246 | 0.0015 |
| 3 | -3.7% | 0.0257 | 0.0015 |
| 4 | -3.8% | 0.0256 | 0.0015 |

Prevalence is biased **≈ −4% relative**; detector rates move by ≤ 0.027. Real, bounded, and now measured.

## S1 identifiability battery (PROTOCOL §5)

- **5.1 dof**: 677 observed patterns vs 25 parameters — not binding, as §5.1 predicts.
- **5.2 Fisher**: rank 25/25, condition number 4.38e+05 on the logit scale against the declared 1e8 — passes.
- **5.3 profiles**: all 24 rate profiles drop > 2.0 log-lik units within ±0.05.
- **5.4 multi-start**: 50 sha256-seeded starts, log-lik spread 0.0015, 1 distinct optimum — passes.
- **5.5 recovery at observed sparsity**: SR5 passes (simulation_gate.json).

**SR4 for S1: passes.** Feature-model batteries: multistart spreads S4 0.04, S5 0.28 over 50 starts (top-3 refined); profiles for S4/S5 are conditional on the converged prior weights and reported as such.

## Detector operating characteristics (selected specification)

| Detector | sensitivity α | specificity β |
|---|---:|---:|
| wordnet | 0.1895 | 0.9997 |
| wiktionary_english | 0.8673 | 0.9536 |
| web2 | 0.4882 | 0.9954 |
| hunspell_en_US | 0.2245 | 1.0000 |
| hunspell_en_GB | 0.3698 | 0.9967 |
| hunspell_en_CA | 0.2242 | 1.0000 |
| hunspell_en_AU | 0.2251 | 1.0000 |
| enable1 | 0.4410 | 1.0000 |
| sowpods_legacy | 0.6833 | 1.0000 |
| nwl2023 | 0.4980 | 0.9998 |
| csw21 | 0.7048 | 0.9997 |
| scowl | 0.9256 | 0.9922 |

## Capture–recapture — a lower bound, stated as one

- P(all twelve detectors silent | word) = **0.00002**
- expected real words the sources caught: **381,073**
- total under homogeneous capture: **381,082**
- implied uncaught: **8**, of which the model places 8 inside the frame's all-zero cell

**Caveat, load-bearing:** heterogeneous capture biases this DOWNWARD; report only as a lower bound on vocabulary under the operational definition (PROTOCOL §4).

## The pilot

Selected specification: **S4**. Posterior strata over the frame:

| Stratum | n | mean P(word) | median | P>0.5 share | expected words |
|---|---:|---:|---:|---:|---:|
| frame | 9,787,841 | 0.0400 | 0.0000 | 3.97% | 391,873 |
| all-zero binary | 8,858,214 | 0.0000 | 0.0000 | 0.00% | 11 |
| no evidence of any kind (D-032) | 845,150 | 0.0000 | 0.0000 | 0.00% | 1 |
| all-zero with GB data | 8,011,835 | 0.0000 | 0.0000 | 0.00% | 11 |
| strong positives (>=8 detectors) | 101,385 | 1.0000 | 1.0000 | 100.00% | 101,385 |
| thin evidence (1-2) | 568,082 | 0.0565 | 0.0002 | 4.84% | 32,122 |

## Held-out comparison — a result, never a target

Agreement with the pinned valid list at P > 0.5: **96.65%**. Of 345,103 valid-list words, 142,232 fall below 0.5 (candidates for old-method errors or model misses); 186,106 non-list words exceed 0.5 (candidates the old method never promoted). Top disagreement patterns are in fits/pilot.json for Phase 4's sample design.
