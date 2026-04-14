"""Linear approximation screening for SCH.

This script estimates empirical linear biases for the SCH permutation
on reduced and full rounds.  For each trial it draws a random input/output
mask pair (α, β) and measures the bias

    bias(α, β) = | Pr_x[ ⟨α, x⟩ = ⟨β, P(x)⟩ ] − 1/2 |

over a uniformly sampled set of inputs.  A perfectly random permutation
would yield biases close to zero (within sampling noise); any mask pair
with a statistically significant bias would indicate a linear approximation
exploitable by a linear attack.

The script reports per-round statistics (mean, median, max bias) and
generates a LaTeX table for inclusion in the paper.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.params import PARAMS, SCHParams, get_params
from sch.permutation import SCHPermutation, Round
from sch.field import field_from_params


@dataclass
class LinearBiasResult:
    rounds: int
    mask_trials: int
    samples_per_mask: int
    mean_bias: float
    median_bias: float
    max_bias: float
    significant_count: int
    significance_threshold: float


def _inner_product_mod2(mask: List[int], state: List[int], p: int) -> int:
    """Compute ⟨mask, state⟩ mod 2 over F_p."""
    acc = 0
    for m, s in zip(mask, state):
        acc = (acc + m * s) % p
    return acc % 2


def _random_nonzero_mask(n: int, p: int, rng: random.Random) -> List[int]:
    """Generate a random non-zero mask in F_p^n."""
    while True:
        mask = [rng.randrange(p) for _ in range(n)]
        if any(m != 0 for m in mask):
            return mask


def _apply_rounds(state: Sequence[int], rounds: Sequence[Round], field, count: int) -> List[int]:
    output = list(state)
    for rnd in rounds[:count]:
        output = rnd.apply(output, field)
    return output


def linear_bias_screening(
    params_name: str,
    mask_trials: int = 64,
    samples_per_mask: int = 256,
    rounds_list: Sequence[int] | None = None,
    seed: int = 0x4C494E,
) -> List[LinearBiasResult]:
    """Screen for linear biases across reduced-round SCH permutations."""
    params = get_params(params_name)
    if params.toy:
        raise ValueError("linear analysis is intended for non-toy parameter sets")

    perm = SCHPermutation(params)
    field = perm.field
    n = params.n
    p = params.p

    if rounds_list is None:
        rounds_list = sorted(set([1, 2, 3, params.k]))

    results: List[LinearBiasResult] = []

    for round_count in rounds_list:
        if round_count < 1 or round_count > params.k:
            raise ValueError(f"invalid round count {round_count}")

        rng = random.Random(seed ^ (round_count << 20) ^ n)

        # Significance threshold: 1/(2·sqrt(samples)) is expected noise
        # for a truly random permutation.  We flag biases above 3× this.
        sig_threshold = 3.0 / (2.0 * (samples_per_mask ** 0.5))

        biases: List[float] = []

        for _ in range(mask_trials):
            alpha = _random_nonzero_mask(n, p, rng)
            beta = _random_nonzero_mask(n, p, rng)

            agreement_count = 0
            for _ in range(samples_per_mask):
                x = [rng.randrange(p) for _ in range(n)]
                y = _apply_rounds(x, perm.rounds, field, round_count)

                lhs = _inner_product_mod2(alpha, x, p)
                rhs = _inner_product_mod2(beta, y, p)

                if lhs == rhs:
                    agreement_count += 1

            empirical_prob = agreement_count / samples_per_mask
            bias = abs(empirical_prob - 0.5)
            biases.append(bias)

        biases.sort()
        median_bias = biases[len(biases) // 2]
        significant = sum(1 for b in biases if b > sig_threshold)

        results.append(LinearBiasResult(
            rounds=round_count,
            mask_trials=mask_trials,
            samples_per_mask=samples_per_mask,
            mean_bias=sum(biases) / len(biases),
            median_bias=median_bias,
            max_bias=max(biases),
            significant_count=significant,
            significance_threshold=sig_threshold,
        ))

    return results


def _print_table(results: List[LinearBiasResult], params_name: str) -> None:
    print(f"\nLinear bias screening for {params_name}")
    print("=" * 90)
    print(f"{'Rounds':<8} {'Masks':<8} {'Samples':<10} {'Mean bias':<12} "
          f"{'Median bias':<14} {'Max bias':<12} {'Signif.':<8}")
    print("-" * 90)
    for r in results:
        print(
            f"{r.rounds:<8} {r.mask_trials:<8} {r.samples_per_mask:<10} "
            f"{r.mean_bias:<12.6f} {r.median_bias:<14.6f} "
            f"{r.max_bias:<12.6f} {r.significant_count}/{r.mask_trials}"
        )
    print(f"\nSignificance threshold: bias > {results[0].significance_threshold:.6f} "
          f"(3 / (2·sqrt(samples)))")


def _print_latex(results: List[LinearBiasResult], params_name: str) -> None:
    print("\n% --- LaTeX snippet for the paper ---")
    print(r"\begin{table}[H]")
    print(r"\centering")
    print(rf"\caption{{Linear bias screening for {params_name} "
          rf"({results[0].mask_trials} random mask pairs, "
          rf"{results[0].samples_per_mask} samples each).}}")
    print(rf"\label{{tab:{params_name}-linear-bias}}")
    print(r"\begin{tabular}{@{}lrrrr@{}}")
    print(r"\toprule")
    print(r"Rounds & Mean bias & Median bias & Max bias & Significant masks \\")
    print(r"\midrule")
    for r in results:
        print(
            f"{r.rounds} & {r.mean_bias:.4f} & {r.median_bias:.4f} & "
            f"{r.max_bias:.4f} & {r.significant_count}/{r.mask_trials} \\\\"
        )
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\vspace{0.5em}")
    print(r"\begin{minipage}{0.95\linewidth}")
    print(r"\small")
    print(r"\textbf{Notes.} Bias $= |\Pr_x[\langle \alpha, x \rangle "
          r"= \langle \beta, P(x) \rangle] - 1/2|$ measured over random")
    print(r"input/output mask pairs $(\alpha, \beta) \in \mathbb{F}_p^n$.")
    threshold_str = f"{results[0].significance_threshold:.4f}"
    print(rf"A mask pair is flagged as significant if bias exceeds "
          rf"${threshold_str}$ (3$\sigma$ above expected sampling noise).")
    print(r"\end{minipage}")
    print(r"\end{table}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Linear bias screening for SCH permutation"
    )
    parser.add_argument(
        "--params", nargs="+", default=["sch128"],
        help="Parameter set name(s), or 'all'",
    )
    parser.add_argument(
        "--mask-trials", type=int, default=64,
        help="Number of random (α, β) mask pairs to test per round count",
    )
    parser.add_argument(
        "--samples", type=int, default=256,
        help="Number of random inputs per mask pair",
    )
    parser.add_argument(
        "--rounds", nargs="*", type=int, default=None,
        help="Specific round counts (default: 1 2 3 k)",
    )
    parser.add_argument(
        "--seed", type=int, default=0x4C494E,
        help="Deterministic PRNG seed",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print machine-readable JSON output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    param_names: List[str] = []
    for name in args.params:
        if name.lower() == "all":
            param_names.extend(
                n for n, p in PARAMS.items() if not p.toy
            )
        else:
            param_names.append(name)

    # Deduplicate preserving order
    seen = set()
    unique_names = []
    for name in param_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    all_results = {}
    for name in unique_names:
        results = linear_bias_screening(
            name,
            mask_trials=args.mask_trials,
            samples_per_mask=args.samples,
            rounds_list=args.rounds,
            seed=args.seed,
        )
        _print_table(results, name)
        _print_latex(results, name)
        all_results[name] = [asdict(r) for r in results]

    if args.json:
        print("\n" + json.dumps(all_results, indent=2))


if __name__ == "__main__":
    main()
