from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.degree_tracking import compute_degree_growth
from sch.encoding import compute_block_size
from sch.params import get_params
from sch.sponge import sch_hash


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate SCH degree and diffusion plots")
    parser.add_argument("--params", default="sch128", help="Parameter set name (default: sch128)")
    parser.add_argument("--output", default="plots", help="Directory for generated figures")
    parser.add_argument("--trials", type=int, default=64, help="Diffusion trials (default: 64)")
    parser.add_argument(
        "--rounds",
        type=int,
        default=None,
        help="Number of rounds to simulate for degree growth (default: all rounds)",
    )
    parser.add_argument(
        "--absorb-every",
        type=int,
        default=0,
        help="Inject a fresh message block every k rounds (0 = single block)",
    )
    parser.add_argument(
        "--skip-diffusion",
        action="store_true",
        help="Skip the diffusion histogram to focus on degree growth",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the per-round degree report",
    )
    return parser.parse_args()


def _bit_diff_ratio(a: bytes, b: bytes) -> float:
    diff_bits = 0
    total_bits = len(a) * 8
    for x, y in zip(a, b):
        diff_bits += (x ^ y).bit_count()
    return diff_bits / total_bits if total_bits else 0.0


def diffusion_distribution(params_name: str, trials: int = 64) -> List[float]:
    params = get_params(params_name)
    digest_bytes = compute_block_size(params.p) * params.digest_length
    ratios: List[float] = []
    for _ in range(trials):
        msg = bytearray(secrets.token_bytes(2 * params.r))
        msg_flip = msg.copy()
        bit_index = secrets.randbelow(len(msg_flip) * 8)
        byte_index, bit_offset = divmod(bit_index, 8)
        msg_flip[byte_index] ^= 1 << bit_offset
        digest_a = sch_hash(bytes(msg), params, out_bytes=digest_bytes)
        digest_b = sch_hash(bytes(msg_flip), params, out_bytes=digest_bytes)
        ratios.append(_bit_diff_ratio(digest_a, digest_b))
    return ratios


def _absorption_schedule(total_rounds: int, absorb_every: int) -> List[int]:
    if absorb_every is None or absorb_every <= 0:
        return [0]
    absorb_every = max(1, absorb_every)
    return list(range(0, total_rounds, absorb_every))


def _print_degree_report(result) -> None:
    print(f"Absorption rounds: {result.absorption_rounds or ['<none>']}")
    print(f"Initial degree vector: {result.initial_degrees}")
    prev_max = max(result.initial_degrees) if result.initial_degrees else 0
    ints_only = all(isinstance(deg, int) for deg in result.initial_degrees)
    monotone = True
    for round_idx, (vector, max_deg) in enumerate(zip(result.degree_vectors, result.max_degrees), start=1):
        if max_deg < prev_max:
            monotone = False
        prev_max = max_deg
        ints_only = ints_only and all(isinstance(deg, int) for deg in vector)
        print(f"Round {round_idx:02d}: max={max_deg:4d} state={vector}")
    print("All tracked degrees are integers." if ints_only else "Warning: non-integer degree detected.")
    if monotone:
        print("Max degrees are non-decreasing across rounds.")
    else:
        print("Warning: Max degrees decreased at some round.")


def _save_degree_plot(degrees: List[int], params_name: str, out_dir: Path) -> None:
    plt.figure(figsize=(6, 4))
    plt.plot(range(1, len(degrees) + 1), degrees, marker="o")
    plt.xlabel("Rounds")
    plt.ylabel("Max total algebraic degree")
    plt.title(f"Degree growth for {params_name}")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "figure1_degree_growth.png", dpi=200)
    plt.close()


def _save_diffusion_plot(ratios: List[float], params_name: str, out_dir: Path) -> None:
    plt.figure(figsize=(6, 4))
    plt.hist(ratios, bins=12, range=(0, 1), color="#1f77b4", edgecolor="black")
    plt.xlabel("Fraction of differing bits")
    plt.ylabel("Frequency")
    plt.title(f"Diffusion for {params_name}")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(out_dir / "figure2_diffusion.png", dpi=200)
    plt.close()


def run_plots() -> None:
    args = parse_args()
    params = get_params(args.params)
    total_rounds = args.rounds or params.k
    absorb_rounds = _absorption_schedule(total_rounds, args.absorb_every)
    result = compute_degree_growth(params, rounds=total_rounds, absorb_rounds=absorb_rounds)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not args.quiet:
        _print_degree_report(result)

    _save_degree_plot(result.max_degrees, params.name, out_dir)

    if not args.skip_diffusion:
        ratios = diffusion_distribution(params.name, trials=args.trials)
        _save_diffusion_plot(ratios, params.name, out_dir)

    print(f"Plots stored in {out_dir}")


if __name__ == "__main__":
    run_plots()
