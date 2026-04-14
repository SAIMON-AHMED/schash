# Submission Status

This repository is in a solid research-prototype state: the code is tested,
the paper compiles, and the core numerical claims in the current draft are
traceable to code. It is better described as "review-ready with explicit
caveats" than as unconditionally submission-ready.

## Confirmed State

- `python -m pytest tests/ -v --tb=short` passes: **24/24 tests**
- `main.tex` compiles cleanly to `main.pdf`
- Paper parameter tables match `sch/params.py`
- `sch/security_analysis.py` and `sch/cryptanalysis.py` use shared attack-cost formulas
- The sponge construction uses standard rate-$r$ absorption (absorbing $r$ elements per permutation call) and rate-$r$ squeezing
- `tests/test_vectors_generated.json` contains deterministic vectors for `sch128`, `sch192`, and `sch256`

## Current Quantitative Results

### Security estimates

| Parameter | Collision | Preimage | Interpolation | Gr\"obner |
| --------- | --------: | -------: | ------------: | --------: |
| `sch128`  |       254 |      508 |           292 |       379 |
| `sch192`  |       573 |     1146 |           515 |       650 |
| `sch256`  |      1020 |     2040 |          1061 |      1247 |

### Reduced-round SCH-128

| Rounds | Interpolation | Gr\"obner | Status                  |
| ------ | ------------: | --------: | ----------------------- |
| `1/7`  |        `2^24` |    `2^62` | Feasible                |
| `2/7`  |        `2^50` |   `2^113` | Infeasible / borderline |
| `3/7`  |        `2^89` |   `2^166` | Infeasible              |
| `7/7`  |       `2^292` |   `2^378` | Infeasible              |

### Reduced Gr\"obner experiments

- Toy instance `(p=31, n=3, d_tri=3)`
- `k=1`: solved in `0.003s`
- `k=2`: solved in `0.122s`
- `k=3`: did not terminate within `>300s` using SymPy's pure-Python solver

### Reference benchmark framing

- `scripts/benchmark_comparison.py` reports reference-Python wall-clock timings
- SHA3 uses `hashlib` (compiled backend)
- Poseidon uses the vendored `galois`-based implementation
- SCH uses pure Python big-integer modular arithmetic
- The sponge absorbs $r$ field elements per permutation call (standard rate-$r$ sponge), so throughput scales with the rate parameter
- These numbers are useful for reproducibility, not for optimized-implementation claims

## Important Caveats

1. SCIP remains a new heuristic assumption; there is no reduction to a standard hard problem.
2. The Gr\"obner experiments are on toy/reduced instances only.
3. The reference implementation is intentionally unoptimized.
4. The repository now includes linear bias screening, higher-order differential tests, multi-coordinate perturbation experiments, and output-balance sweeps. No exploitable biases were found, but sample budgets are limited and dedicated distinguisher analyses remain open.
5. Benchmark wall-clock comparisons and circuit-cost comparisons should be interpreted separately.
6. Polynomial system export scripts (`scripts/export_system.py`) are provided for Sage and Magma, enabling external solver experiments.

## Reproduce The Current State

```bash
python reproduce.py           # full reproduction (tests + all analyses + PDF)
python reproduce.py --quick    # fast check (~30s): tests + basic analysis only
```

Or run individual steps:

```bash
python -m pytest tests/ -v --tb=short
python scripts/formal_verification.py
python scripts/differential_analysis.py --params all --paper-profile --summary-only
python scripts/linear_analysis.py --params sch128 --mask-trials 32 --samples 128
python scripts/higher_order_diff.py --params sch128 --trials 32
python scripts/groebner_experiment.py
python scripts/export_system.py --params toy31 --format both
pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
```

## Recommended Next Pass Before External Submission

1. Get an external mathematical review of the formal claims and proofs.
2. Run Gr\"obner experiments with a faster solver (for example Magma/FGb/Sage-backed tooling).
3. Sharpen the benchmark wording so small-state wall-clock comparisons are not conflated with comparable-state constraint estimates.
4. ~~Expand the preliminary differential/statistical section into stronger screening.~~ **Done**: linear bias, higher-order differential, and multi-coordinate perturbation analyses are now included.
5. Run the Sage/Magma export scripts on larger instances with production solvers.

## Remaining Improvements In Detail

The repository is no longer blocked on basic implementation completeness. The
remaining work is concentrated in the places where serious journal reviewers
will look for either missing evidence or overly optimistic framing. The items
below are ordered by review impact rather than coding difficulty.

### 1. External Review Of The Mathematical Core

This is the highest-leverage improvement because the paper rests on a new
construction paradigm and a new hardness assumption. Internal consistency is no
longer the main problem; reviewer confidence is.

What needs review:

- The bijectivity argument for the permutation as a composition of unitriangular
  and affine determinant-one layers.
- The degree-growth theorem and the stated scope of its bound.
- The definition of SCIP and the exact strength of the claims made from it.
- The paper's use of heuristic algebraic-security arguments and where those
  claims should be softened.

What counts as a good outcome:

- An external algebraist or cryptographer confirms that the formal statements
  are correct as written.
- Ambiguous claims are rewritten into precise conditional statements.
- Any proof sketches that rely on unstated assumptions are either completed or
  demoted to conjectures/empirical observations.

Why this matters for publication:

- Reviewers will forgive limited experiments more readily than they will forgive
  a proof that reads stronger than the underlying argument supports.
- A new primitive with a novel assumption is judged first on technical rigor,
  then on performance.

Concrete deliverables:

- Annotated review notes from a domain expert.
- A paper revision that explicitly distinguishes theorems, propositions,
  conjectures, heuristics, and experimental observations.
- A short appendix or author note documenting any claim that was intentionally
  narrowed after review.

### 2. Solver-Backed Algebraic Cryptanalysis

The current Gr\"obner evidence is useful but still too lightweight for a strong
journal case. The problem is not that the current script is wrong; it is that
SymPy on toy instances is not persuasive enough.

What remains missing:

- Experiments with production-grade solvers such as Magma F4/F5, FGb, or a
  Sage pipeline backed by faster elimination routines.
- Larger reduced instances that vary not just the round count but also the
  state size, degree cap, and field size.
- A comparison between predicted semi-regular complexity and measured solver
  behavior.

What to implement next:

- A reproducible experiment harness that exports polynomial systems from SCH
  into a solver-friendly format.
- A parameter grid covering several reduced instances, for example varying
  $n$, $k$, and $d_{tri}$ separately rather than only showing one toy family.
- A results table with wall-clock time, memory use if available, and observed
  elimination degree or basis degree.

What reviewers will expect the paper to say afterward:

- Not that solver experiments prove full security.
- Instead, that measured reduced-instance behavior is at least directionally
  consistent with the semi-regular heuristic used in the paper.

Target outcome:

- A revised section showing that the transition from easy to hard solving is not
  an artifact of SymPy alone.
- A tighter statement on how far the empirical data supports or fails to support
  the concrete Gr\"obner estimates.

### 3. Stronger Differential, Linear, And Statistical Screening

The repository now has preliminary differential/statistical sanity checks, which
is a good baseline. For journal review, that baseline still needs to become a
real cryptanalytic section rather than a coarse screening note.

What is already present:

- Reduced-round diffusion measurements for SCH-128.
- Full-round cross-parameter sanity summaries for SCH-128, SCH-192, and
  SCH-256.
- Output-bit balance checks under small Monte Carlo budgets.

What is still missing:

- Linear-bias screening.
- Round-by-round differential trail analysis beyond simple one-coordinate
  perturbations.
- Higher-order, rebound-style, or structural distinguishers.
- Larger sample budgets, especially for SCH-256.
- A clearer statement of what the sanity checks do and do not establish.

What a stronger next pass should include:

- A linear-approximation experiment that estimates empirical bias for selected
  input/output masks on reduced rounds.
- A widened differential experiment using multiple perturbation models:
  single-coordinate, multi-coordinate, and random sparse differences.
- A paper table that reports how quickly the changed-bit ratio converges toward
  50% as a function of rounds across the published parameter sets.
- Statistical reporting that includes confidence intervals or at least explicit
  sample sizes next to every figure.

Why this matters:

- Hash-function reviewers expect at least baseline coverage of differential and
  linear behavior, even when the central security story is algebraic.
- Without that, the paper can read as if it is only defending against the attack
  classes it was built to discuss.

Practical success criterion:

- A revised evaluation section that shows no obvious low-round or full-round
  statistical pathology in the tested families, while clearly stating that this
  is screening evidence rather than proof.

### 4. Cleaner Benchmark Framing And Cost Accounting

The current benchmarking language is much better than before, but it still needs
to be publication-hardened. The risk here is not raw numbers; it is comparison
discipline.

What must be kept separate:

- Reference-Python wall-clock timings.
- Same-state-size arithmetic-cost proxies.
- Constraint-count estimates for ZK settings.
- Any claim about optimized native implementations.

What to improve:

- State explicitly in the paper and README that SHA3 uses a compiled backend,
  Poseidon uses a `galois`/NumPy-backed implementation, and SCH uses pure-Python
  big-integer arithmetic.
- Avoid prose that sounds like a direct performance race between incomparable
  implementations.
- If possible, add a small table of operation counts per permutation round so
  the comparison is less tied to one software stack.

Best next deliverable:

- A benchmark subsection with two subclaims only:
  reproducible reference timings and coarse field-operation cost.
- No broader performance claim unless a native or optimized SCH implementation
  is actually produced.

### 5. Implementation Quality For Reproducibility, Not Just Correctness

The codebase is already in good shape for a research prototype, but journal
artifacts benefit from another layer of reproducibility hardening.

Useful remaining improvements:

- Ensure every number appearing in the paper is generated by a script or traced
  to one shared formula source.
- Record solver versions, Python version, machine information, and seeds used
  for stochastic experiments.
- Add a short artifact section that lists the exact commands needed to rebuild
  tables, figures, tests, and the PDF.
- Consider one script that runs the full reproducibility pipeline and stores the
  outputs in a predictable location.

Why this matters:

- Reviewers and editors are much more receptive when they can see that every
  table is reproducible and every heuristic experiment has fixed parameters.
- This also reduces the risk of manuscript drift as new experiments are added.

### 6. Stronger Positioning Of The SCIP Assumption

Even with more experiments, the main strategic weakness remains the newness of
SCIP. A serious journal version should treat that as a research contribution,
not as a settled foundation.

What to improve in the writing:

- Be explicit that SCIP is a proposal-level assumption.
- Compare SCIP more carefully with MQ/MP-style inversion and explain the exact
  structural differences.
- Avoid language that could be read as claiming a reduction where there is only
  an intuition or an embedding.
- Add a short discussion of what types of future results would strengthen SCIP:
  reductions, average-case analysis, or counterexamples from specialized
  structural attacks.

Expected effect:

- The paper reads as a rigorous introduction of a new framework instead of a
  fully settled primitive.
- That positioning is usually more credible, and paradoxically often stronger,
  for first-publication journal review.

### 7. Submission Strategy By Venue Seriousness

The remaining work depends on what “serious journal” means operationally.

If targeting a strong but not topmost cryptography journal:

- External proof review.
- Solver-backed reduced-instance experiments.
- Stronger differential/linear screening.
- Careful performance framing.

If targeting the most demanding venues or a journal version expected to survive
top-tier reviewer standards:

- All of the above.
- Either substantially better solver evidence or a more conservative security
  section.
- A more mature cryptanalysis discussion that openly maps which attack families
  remain inadequately studied.

The key distinction is this: the current artifact is credible and reproducible,
but it still reads like a strong first proposal rather than a fully validated
hash standard candidate.

## Practical Priority Order

If time is limited, the most defensible order is:

1. External mathematical review.
2. Solver-backed Gr\"obner pipeline.
3. Linear/differential/statistical screening expansion.
4. Benchmark and cost-accounting cleanup.
5. Reproducibility packaging and manuscript polish.

That order maximizes reviewer confidence per unit of work and addresses the
remaining risks at their root rather than only improving presentation.

## Bottom Line

The repository is credible, reproducible, and materially stronger than a typical prototype. The remaining work is concentrated in external-review hardening rather than basic implementation completeness.
