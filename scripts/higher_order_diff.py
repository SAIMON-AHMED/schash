"""Higher-order differential screening for SCH.

A k-th order differential tests whether the k-th order discrete derivative
of the permutation is zero (or has low algebraic degree).  For a random
permutation of degree d, the k-th order derivative vanishes when k > d.
If the SCH permutation's k-th derivative vanishes for k << d_tri^rounds,
it would indicate that the effective algebraic degree is lower than the
theoretical bound, revealing potential structural weakness.

This script computes empirical higher-order derivative norms for reduced
and full-round SCH permutations.  A non-zero result is expected (and
desired) for all orders below the theoretical degree bound.
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

from sch.params import PARAMS, get_params
from sch.permutation import SCHPermutation, Round
from sch.field import field_from_params


@dataclass
class HigherOrderResult:
    rounds: int
    order: int
    trials: int
    zero_fraction: float
    theoretical_degree: int


def _apply_rounds(state: Sequence[int], rounds: Sequence[Round], field, count: int) -> List[int]:
    output = list(state)
    for rnd in rounds[:count]:
        output = rnd.apply(output, field)
    return output


def _higher_order_derivative(
    base_state: List[int],
    directions: List[List[int]],
    rounds: Sequence[Round],
    field,
    round_count: int,
    n: int,
    p: int,
) -> List[int]:
    """Compute the k-th order discrete derivative of P at base_state
    along the given directions.

    The k-th derivative is:
      Delta_{a_1,...,a_k} P(x) = sum_{S subset {1..k}} (-1)^{k-|S|} P(x + sum_{i in S} a_i)

    Returns the derivative as a vector in F_p^n.
    """
    order = len(directions)
    # Enumerate all 2^k subsets
    result = [0] * n
    for mask in range(1 << order):
        # Compute x + sum of selected directions
        point = list(base_state)
        subset_size = 0
        for bit in range(order):
            if mask & (1 << bit):
                subset_size += 1
                for j in range(n):
                    point[j] = (point[j] + directions[bit][j]) % p

        sign = (-1) ** (order - subset_size)
        output = _apply_rounds(point, rounds, field, round_count)

        for j in range(n):
            result[j] = (result[j] + sign * output[j]) % p

    return result


def higher_order_screening(
    params_name: str,
    orders: Sequence[int] | None = None,
    trials: int = 64,
    rounds_list: Sequence[int] | None = None,
    seed: int = 0x484F44,
) -> List[HigherOrderResult]:
    """Screen for vanishing higher-order derivatives."""
    params = get_params(params_name)
    if params.toy:
        raise ValueError("higher-order analysis is for non-toy params")

    perm = SCHPermutation(params)
    field = perm.field
    n = params.n
    p = params.p

    if rounds_list is None:
        rounds_list = sorted(set([1, 2, 3, params.k]))
    if orders is None:
        # Test orders 2, 3, 4 (higher orders are exponentially expensive)
        orders = [2, 3, 4]

    results: List[HigherOrderResult] = []

    for round_count in rounds_list:
        theoretical_deg = min(params.d_tri ** round_count, p)

        for order in orders:
            # Skip if order exceeds theoretical degree (derivative expected zero)
            if order > theoretical_deg:
                continue
            # Skip very high orders due to 2^order evaluations
            if order > 8:
                continue

            rng = random.Random(seed ^ (round_count << 20) ^ (order << 10))
            zero_count = 0

            for _ in range(trials):
                base = [rng.randrange(p) for _ in range(n)]
                # Random linearly independent-ish directions
                directions = [
                    [rng.randrange(1, p) for _ in range(n)]
                    for _ in range(order)
                ]

                deriv = _higher_order_derivative(
                    base, directions, perm.rounds, field,
                    round_count, n, p,
                )

                if all(d == 0 for d in deriv):
                    zero_count += 1

            results.append(HigherOrderResult(
                rounds=round_count,
                order=order,
                trials=trials,
                zero_fraction=zero_count / trials,
                theoretical_degree=theoretical_deg,
            ))

    return results


def _print_table(results: List[HigherOrderResult], params_name: str) -> None:
    print(f"\nHigher-order differential screening for {params_name}")
    print("=" * 80)
    print(f"{'Rounds':<8} {'Order':<8} {'Trials':<8} {'d_theory':<12} "
          f"{'Zero frac':<12} {'Status':<12}")
    print("-" * 80)
    for r in results:
        status = "PASS" if r.zero_fraction == 0.0 else "INVESTIGATE"
        print(
            f"{r.rounds:<8} {r.order:<8} {r.trials:<8} {r.theoretical_degree:<12} "
            f"{r.zero_fraction:<12.4f} {status}"
        )


def _print_latex(results: List[HigherOrderResult], params_name: str) -> None:
    print("\n% --- Higher-order differential LaTeX snippet ---")
    print(r"\begin{table}[H]")
    print(r"\centering")
    print(rf"\caption{{Higher-order differential screening for {params_name} "
          rf"({results[0].trials} trials per cell).}}")
    print(rf"\label{{tab:{params_name}-higher-order}}")
    print(r"\begin{tabular}{@{}lrrrr@{}}")
    print(r"\toprule")
    print(r"Rounds & Order & $d_{\mathrm{theory}}$ & Zero fraction & Status \\")
    print(r"\midrule")
    for r in results:
        status = r"Pass" if r.zero_fraction == 0.0 else r"Investigate"
        print(
            f"{r.rounds} & {r.order} & {r.theoretical_degree} & "
            f"{r.zero_fraction:.4f} & {status} \\\\"
        )
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\vspace{0.5em}")
    print(r"\begin{minipage}{0.95\linewidth}")
    print(r"\small")
    print(r"\textbf{Notes.} A $k$-th order derivative is evaluated as "
          r"$\Delta_{a_1, \ldots, a_k} P(x) = \sum_{S \subseteq \{1, \ldots, k\}} "
          r"(-1)^{k - |S|} P(x + \sum_{i \in S} a_i)$.")
    print(r"Zero fraction $> 0$ at order $k < d_{\mathrm{theory}}$ would indicate "
          r"effective algebraic degree lower than the theoretical bound.")
    print(r"\end{minipage}")
    print(r"\end{table}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Higher-order differential screening for SCH"
    )
    parser.add_argument(
        "--params", nargs="+", default=["sch128"],
        help="Parameter set name(s), or 'all'",
    )
    parser.add_argument(
        "--orders", nargs="+", type=int, default=[2, 3, 4],
        help="Derivative orders to test (default: 2 3 4)",
    )
    parser.add_argument(
        "--trials", type=int, default=64,
        help="Number of random trials per (rounds, order) pair",
    )
    parser.add_argument(
        "--rounds", nargs="*", type=int, default=None,
        help="Specific round counts (default: 1 2 3 k)",
    )
    parser.add_argument(
        "--seed", type=int, default=0x484F44,
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
            param_names.extend(n for n, p in PARAMS.items() if not p.toy)
        else:
            param_names.append(name)

    seen = set()
    unique_names = []
    for name in param_names:
        if name not in seen:
            seen.add(name)
            unique_names.append(name)

    all_results = {}
    for name in unique_names:
        results = higher_order_screening(
            name,
            orders=args.orders,
            trials=args.trials,
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
