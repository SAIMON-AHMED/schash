from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.encoding import compute_block_size, serialize_elements
from sch.params import PARAMS, get_params
from sch.permutation import SCHPermutation, Round
from sch.sponge import sch_hash


@dataclass
class RoundDiffusionMetrics:
    rounds: int
    trials: int
    changed_coordinate_ratio: float
    changed_bit_ratio: float


@dataclass
class BitBalanceMetrics:
    samples: int
    message_bytes: int
    digest_bytes: int
    mean_bias: float
    max_bias: float
    min_one_ratio: float
    max_one_ratio: float


@dataclass(frozen=True)
class AnalysisConfig:
    trials: int
    samples: int
    message_bytes: int


@dataclass
class ParameterSummary:
    params_name: str
    full_rounds: int
    trials: int
    samples: int
    message_bytes: int
    changed_coordinate_ratio: float
    changed_bit_ratio: float
    mean_bias: float
    max_bias: float
    min_one_ratio: float
    max_one_ratio: float


@dataclass
class MultiCoordDiffusionMetrics:
    """Metrics for multi-coordinate perturbation experiments."""
    rounds: int
    perturbation_coords: int
    trials: int
    changed_coordinate_ratio: float
    changed_bit_ratio: float


PAPER_PROFILE = {
    "sch128": AnalysisConfig(trials=128, samples=128, message_bytes=64),
    "sch192": AnalysisConfig(trials=64, samples=64, message_bytes=64),
    "sch256": AnalysisConfig(trials=32, samples=16, message_bytes=64),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run differential and statistical sanity checks for SCH"
    )
    parser.add_argument(
        "--params",
        nargs="+",
        default=["sch128"],
        help="Parameter set name(s), or 'all' for every published parameter set",
    )
    parser.add_argument(
        "--trials",
        type=int,
        default=128,
        help="Number of random differential trials per round count",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=128,
        help="Number of random messages for output-bit balance",
    )
    parser.add_argument(
        "--message-bytes",
        type=int,
        default=64,
        help="Message length in bytes for the output-balance experiment",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0x534348,
        help="Deterministic PRNG seed for reproducible sampling",
    )
    parser.add_argument(
        "--rounds",
        nargs="*",
        type=int,
        default=None,
        help="Specific reduced-round counts to analyze (default: 1 2 3 k)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON in addition to the text report",
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only compute full-round summary rows instead of the detailed reduced-round table",
    )
    parser.add_argument(
        "--paper-profile",
        action="store_true",
        help="Use the fixed sample budgets referenced by the paper for the published parameter sets",
    )
    parser.add_argument(
        "--multi-coord",
        action="store_true",
        help="Also run multi-coordinate perturbation experiments",
    )
    return parser.parse_args()


def _published_parameter_names() -> List[str]:
    return [name for name, params in PARAMS.items() if not params.toy]


def _resolve_param_names(raw_names: Sequence[str]) -> List[str]:
    names: List[str] = []
    for raw_name in raw_names:
        if raw_name.lower() == "all":
            names.extend(_published_parameter_names())
            continue
        get_params(raw_name)
        names.append(raw_name)

    ordered_unique: List[str] = []
    for name in names:
        if name not in ordered_unique:
            ordered_unique.append(name)
    return ordered_unique


def _analysis_config_for(param_name: str, args: argparse.Namespace) -> AnalysisConfig:
    if args.paper_profile:
        try:
            return PAPER_PROFILE[param_name]
        except KeyError as exc:
            raise ValueError(
                f"paper profile is only defined for published parameter sets, not {param_name!r}"
            ) from exc
    return AnalysisConfig(
        trials=args.trials,
        samples=args.samples,
        message_bytes=args.message_bytes,
    )


def _bit_diff_ratio(a: bytes, b: bytes) -> float:
    if len(a) != len(b):
        raise ValueError("bit-diff inputs must have equal length")
    total_bits = len(a) * 8
    if total_bits == 0:
        return 0.0
    diff_bits = sum((x ^ y).bit_count() for x, y in zip(a, b))
    return diff_bits / total_bits


def _serialize_state(state: Sequence[int], block_size: int) -> bytes:
    return serialize_elements(state, block_size)


def _apply_rounds(state: Sequence[int], rounds: Sequence[Round], field, count: int) -> List[int]:
    output = list(state)
    for rnd in rounds[:count]:
        output = rnd.apply(output, field)
    return output


def _default_rounds(k: int) -> List[int]:
    return sorted(set([1, 2, 3, k]))


def reduced_round_diffusion(
    params_name: str,
    trials: int = 128,
    rounds_list: Sequence[int] | None = None,
    seed: int = 0x534348,
) -> List[RoundDiffusionMetrics]:
    params = get_params(params_name)
    if params.toy:
        raise ValueError("differential analysis is intended for non-toy parameter sets")

    perm = SCHPermutation(params)
    field = perm.field
    block_size = compute_block_size(params.p)
    selected_rounds = rounds_list or _default_rounds(params.k)

    results: List[RoundDiffusionMetrics] = []
    for round_count in selected_rounds:
        if round_count < 1 or round_count > params.k:
            raise ValueError(f"invalid round count {round_count} for params {params.name}")

        # Use a round-specific RNG stream so each reported round is stable
        # regardless of what other round counts are requested in the same run.
        rng = random.Random(seed ^ (round_count << 20) ^ params.n ^ params.k)
        coord_ratio_sum = 0.0
        bit_ratio_sum = 0.0
        for _ in range(trials):
            state = [rng.randrange(params.p) for _ in range(params.n)]
            perturbed = list(state)
            coord_idx = rng.randrange(params.n)
            perturbed[coord_idx] = field.add(perturbed[coord_idx], 1)

            out_a = _apply_rounds(state, perm.rounds, field, round_count)
            out_b = _apply_rounds(perturbed, perm.rounds, field, round_count)

            changed_coords = sum(a != b for a, b in zip(out_a, out_b))
            coord_ratio_sum += changed_coords / params.n
            bit_ratio_sum += _bit_diff_ratio(
                _serialize_state(out_a, block_size),
                _serialize_state(out_b, block_size),
            )

        results.append(
            RoundDiffusionMetrics(
                rounds=round_count,
                trials=trials,
                changed_coordinate_ratio=coord_ratio_sum / trials,
                changed_bit_ratio=bit_ratio_sum / trials,
            )
        )
    return results


def multi_coord_diffusion(
    params_name: str,
    trials: int = 128,
    rounds_list: Sequence[int] | None = None,
    perturbation_counts: Sequence[int] | None = None,
    seed: int = 0x534348,
) -> List[MultiCoordDiffusionMetrics]:
    """Measure diffusion under multi-coordinate perturbations.

    For each combination of (round_count, num_perturbed_coords), randomly
    select that many coordinates and add +1 to each, then measure changed
    output coordinates and bits.  This extends the single-coordinate
    experiment to detect diffusion weaknesses that only appear under
    wider input differences.
    """
    params = get_params(params_name)
    if params.toy:
        raise ValueError("multi-coord diffusion is for non-toy parameter sets")

    perm = SCHPermutation(params)
    field = perm.field
    block_size = compute_block_size(params.p)

    if rounds_list is None:
        rounds_list = sorted(set([1, 2, 3, params.k]))
    if perturbation_counts is None:
        perturbation_counts = sorted(set([1, 2, params.n // 2, params.n]))

    results: List[MultiCoordDiffusionMetrics] = []

    for round_count in rounds_list:
        for num_perturb in perturbation_counts:
            if num_perturb > params.n:
                continue
            rng = random.Random(seed ^ (round_count << 20) ^ (num_perturb << 10))
            coord_ratio_sum = 0.0
            bit_ratio_sum = 0.0

            for _ in range(trials):
                state = [rng.randrange(params.p) for _ in range(params.n)]
                perturbed = list(state)

                # Randomly select num_perturb distinct coordinates
                coords = rng.sample(range(params.n), num_perturb)
                for c in coords:
                    perturbed[c] = field.add(perturbed[c], 1)

                out_a = _apply_rounds(state, perm.rounds, field, round_count)
                out_b = _apply_rounds(perturbed, perm.rounds, field, round_count)

                changed = sum(a != b for a, b in zip(out_a, out_b))
                coord_ratio_sum += changed / params.n
                bit_ratio_sum += _bit_diff_ratio(
                    _serialize_state(out_a, block_size),
                    _serialize_state(out_b, block_size),
                )

            results.append(MultiCoordDiffusionMetrics(
                rounds=round_count,
                perturbation_coords=num_perturb,
                trials=trials,
                changed_coordinate_ratio=coord_ratio_sum / trials,
                changed_bit_ratio=bit_ratio_sum / trials,
            ))

    return results


def output_bit_balance(
    params_name: str,
    samples: int = 128,
    message_bytes: int = 64,
    seed: int = 0x534348,
) -> BitBalanceMetrics:
    params = get_params(params_name)
    digest_bytes = compute_block_size(params.p) * params.digest_length
    rng = random.Random(seed ^ 0xBADA55)

    counts = [0] * (digest_bytes * 8)
    for _ in range(samples):
        message = rng.randbytes(message_bytes)
        digest = sch_hash(message, params, out_bytes=digest_bytes)
        for byte_idx, byte in enumerate(digest):
            for bit_idx in range(8):
                counts[byte_idx * 8 + bit_idx] += (byte >> bit_idx) & 1

    ratios = [count / samples for count in counts]
    biases = [abs(ratio - 0.5) for ratio in ratios]
    return BitBalanceMetrics(
        samples=samples,
        message_bytes=message_bytes,
        digest_bytes=digest_bytes,
        mean_bias=sum(biases) / len(biases),
        max_bias=max(biases),
        min_one_ratio=min(ratios),
        max_one_ratio=max(ratios),
    )


def full_round_summary(
    params_name: str,
    config: AnalysisConfig,
    seed: int = 0x534348,
) -> ParameterSummary:
    params = get_params(params_name)
    full_round_metrics = reduced_round_diffusion(
        params_name,
        trials=config.trials,
        rounds_list=[params.k],
        seed=seed,
    )[0]
    balance = output_bit_balance(
        params_name,
        samples=config.samples,
        message_bytes=config.message_bytes,
        seed=seed,
    )
    return ParameterSummary(
        params_name=params_name,
        full_rounds=params.k,
        trials=config.trials,
        samples=config.samples,
        message_bytes=config.message_bytes,
        changed_coordinate_ratio=full_round_metrics.changed_coordinate_ratio,
        changed_bit_ratio=full_round_metrics.changed_bit_ratio,
        mean_bias=balance.mean_bias,
        max_bias=balance.max_bias,
        min_one_ratio=balance.min_one_ratio,
        max_one_ratio=balance.max_one_ratio,
    )


def _print_round_table(metrics: Iterable[RoundDiffusionMetrics]) -> None:
    print("Reduced-round differential propagation")
    print("=" * 72)
    print(f"{'Rounds':<10} {'Changed coords':<18} {'Changed bits':<18}")
    print("-" * 72)
    for row in metrics:
        print(
            f"{row.rounds:<10} "
            f"{100 * row.changed_coordinate_ratio:>7.2f}%{'':<9} "
            f"{100 * row.changed_bit_ratio:>7.2f}%"
        )


def _print_balance(balance: BitBalanceMetrics) -> None:
    print("\nOutput-bit balance sanity check")
    print("=" * 72)
    print(f"Samples:       {balance.samples}")
    print(f"Message bytes: {balance.message_bytes}")
    print(f"Digest bytes:  {balance.digest_bytes}")
    print(f"Mean bias:     {balance.mean_bias:.4f}")
    print(f"Max bias:      {balance.max_bias:.4f}")
    print(f"One-ratio min: {balance.min_one_ratio:.4f}")
    print(f"One-ratio max: {balance.max_one_ratio:.4f}")


def _print_summary_table(rows: Sequence[ParameterSummary]) -> None:
    name_width = max(len(row.params_name) for row in rows)
    print("Full-round cross-parameter sanity summary")
    print("=" * 96)
    print(
        f"{'Params':<{name_width}} {'Rounds':>6} {'Trials':>7} {'Samples':>8} "
        f"{'Changed coords':>16} {'Changed bits':>14} {'Mean bias':>11} {'Max bias':>10}"
    )
    print("-" * 96)
    for row in rows:
        print(
            f"{row.params_name:<{name_width}} {row.full_rounds:>6} {row.trials:>7} {row.samples:>8} "
            f"{100 * row.changed_coordinate_ratio:>15.2f}% "
            f"{100 * row.changed_bit_ratio:>13.2f}% "
            f"{row.mean_bias:>11.4f} {row.max_bias:>10.4f}"
        )


def _print_summary_latex(rows: Sequence[ParameterSummary]) -> None:
    message_lengths = sorted({row.message_bytes for row in rows})
    message_note = (
        f"All balance measurements use {message_lengths[0]}-byte messages."
        if len(message_lengths) == 1
        else "Message lengths vary by parameter set."
    )
    print("\n% --- LaTeX snippet for the paper ---")
    print(r"\begin{table}[H]")
    print(r"\centering")
    print(
        r"\caption{Full-round differential/statistical sanity summary for the published SCH parameter sets.}"
    )
    print(r"\label{tab:sch-published-sanity-summary}")
    print(r"\resizebox{\linewidth}{!}{%")
    print(r"\begin{tabular}{@{}lrrrrr@{}}")
    print(r"\toprule")
    print(
        r"Parameter & Rounds & Trials / samples & Changed coords (\%) & Changed bits (\%) & Mean bias / Max bias \\" 
    )
    print(r"\midrule")
    for row in rows:
        print(
            f"{row.params_name} & {row.full_rounds} & {row.trials} / {row.samples} & "
            f"{100 * row.changed_coordinate_ratio:.2f} & {100 * row.changed_bit_ratio:.2f} & "
            f"{row.mean_bias:.4f} / {row.max_bias:.4f} \\\\" 
        )
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"}%")
    print(r"\vspace{0.5em}")
    print(r"\begin{minipage}{0.95\linewidth}")
    print(r"\small")
    print(rf"\textbf{{Notes.}} {message_note}")
    print(
        r"The reported diffusion value uses a single-coordinate $+1$ perturbation and only the full-round permutation."
    )
    print(
        r"The larger parameter sets use smaller sample budgets in the current pure-Python reference implementation, so the bias statistics should be read as coarse screening results rather than distinguisher bounds."
    )
    print(r"\end{minipage}")
    print(r"\end{table}")


def _print_multi_coord_table(metrics: Sequence[MultiCoordDiffusionMetrics], params_name: str) -> None:
    print(f"\nMulti-coordinate perturbation diffusion for {params_name}")
    print("=" * 80)
    print(f"{'Rounds':<8} {'Perturbed':<12} {'Changed coords':<18} {'Changed bits':<18}")
    print("-" * 80)
    for row in metrics:
        print(
            f"{row.rounds:<8} {row.perturbation_coords:<12} "
            f"{100 * row.changed_coordinate_ratio:>7.2f}%{'':<9} "
            f"{100 * row.changed_bit_ratio:>7.2f}%"
        )


def _print_multi_coord_latex(metrics: Sequence[MultiCoordDiffusionMetrics], params_name: str) -> None:
    print("\n% --- Multi-coordinate perturbation LaTeX snippet ---")
    print(r"\begin{table}[H]")
    print(r"\centering")
    print(rf"\caption{{Multi-coordinate perturbation diffusion for {params_name}.}}")
    print(rf"\label{{tab:{params_name}-multi-coord-diffusion}}")
    print(r"\begin{tabular}{@{}lrrr@{}}")
    print(r"\toprule")
    print(r"Rounds & Perturbed coords & Changed coordinates (\%) & Changed bits (\%) \\")
    print(r"\midrule")
    for row in metrics:
        print(
            f"{row.rounds} & {row.perturbation_coords} & "
            f"{100 * row.changed_coordinate_ratio:.2f} & "
            f"{100 * row.changed_bit_ratio:.2f} \\\\"
        )
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\vspace{0.5em}")
    print(r"\begin{minipage}{0.95\linewidth}")
    print(r"\small")
    print(r"\textbf{Notes.} Each perturbed coordinate receives a $+1$ additive difference.")
    print(r"Perturbed coordinates are selected uniformly at random for each trial.")
    print(r"\end{minipage}")
    print(r"\end{table}")


def _print_latex(metrics: Sequence[RoundDiffusionMetrics], balance: BitBalanceMetrics, params_name: str) -> None:
    print("\n% --- LaTeX snippet for the paper ---")
    print(r"\begin{table}[H]")
    print(r"\centering")
    print(rf"\caption{{Reduced-round differential propagation for {params_name}.}}")
    print(rf"\label{{tab:{params_name}-diffusion-sanity}}")
    print(r"\begin{tabular}{@{}lrr@{}}")
    print(r"\toprule")
    print(r"Rounds & Changed coordinates (\%) & Changed serialized bits (\%) \\")
    print(r"\midrule")
    for row in metrics:
        print(
            f"{row.rounds} & {100 * row.changed_coordinate_ratio:.2f} & "
            f"{100 * row.changed_bit_ratio:.2f} \\\\" 
        )
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")
    print(
        "% Output-bit balance: "
        f"mean bias = {balance.mean_bias:.4f}, max bias = {balance.max_bias:.4f}, "
        f"one-ratio range = [{balance.min_one_ratio:.4f}, {balance.max_one_ratio:.4f}]"
    )


def main() -> None:
    args = parse_args()
    param_names = _resolve_param_names(args.params)

    if len(param_names) == 1 and not args.summary_only and not args.paper_profile:
        param_name = param_names[0]
        metrics = reduced_round_diffusion(
            param_name,
            trials=args.trials,
            rounds_list=args.rounds,
            seed=args.seed,
        )
        balance = output_bit_balance(
            param_name,
            samples=args.samples,
            message_bytes=args.message_bytes,
            seed=args.seed,
        )

        _print_round_table(metrics)
        _print_balance(balance)
        _print_latex(metrics, balance, param_name)

        if args.multi_coord:
            mc_metrics = multi_coord_diffusion(
                param_name,
                trials=args.trials,
                rounds_list=args.rounds,
                seed=args.seed,
            )
            _print_multi_coord_table(mc_metrics, param_name)
            _print_multi_coord_latex(mc_metrics, param_name)

        if args.json:
            payload = {
                "params": param_name,
                "round_diffusion": [asdict(item) for item in metrics],
                "bit_balance": asdict(balance),
            }
            print("\n" + json.dumps(payload, indent=2))
        return

    summaries = [
        full_round_summary(name, _analysis_config_for(name, args), seed=args.seed)
        for name in param_names
    ]
    _print_summary_table(summaries)
    _print_summary_latex(summaries)

    if args.json:
        payload = {
            "summary_rows": [asdict(row) for row in summaries],
        }
        print("\n" + json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()