"""Comparative benchmark: SCH vs SHA-3 vs Poseidon.

Measures hashing throughput for each algorithm across multiple input sizes
and prints a summary table suitable for inclusion in the research paper.

The vendored Poseidon measurement uses a small reproducible reference instance
(state size t=4, input rate=3). It is useful as a reference-Python timing
baseline, not as a same-state-size comparison with SCH-128.
"""

import hashlib
import importlib
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Add vendor directory so the Poseidon package is importable
VENDOR = ROOT / "vendor"
if str(VENDOR) not in sys.path:
    sys.path.insert(0, str(VENDOR))

from sch.params import get_params
from sch.sponge import sch_hash
from sch.encoding import compute_block_size


# ---------------------------------------------------------------------------
# Individual benchmarking helpers
# ---------------------------------------------------------------------------

def benchmark_sch(data: bytes, params_name: str = "sch128") -> float:
    """Return wall-clock seconds for one SCH hash invocation."""
    params = get_params(params_name)
    digest_bytes = compute_block_size(params.p) * params.digest_length
    start = time.perf_counter()
    sch_hash(data, params, out_bytes=digest_bytes)
    return time.perf_counter() - start


def benchmark_sha3(data: bytes) -> float:
    """Return wall-clock seconds for one SHA3-256 hash invocation."""
    start = time.perf_counter()
    hashlib.sha3_256(data).digest()
    return time.perf_counter() - start


def _try_import_poseidon():
    """Try to import the vendored Poseidon implementation.  Returns class or None."""
    try:
        module = importlib.import_module("poseidon")
        return getattr(module, "Poseidon", None)
    except Exception:
        return None


def _make_poseidon_instance():
    """Create the small reproducible Poseidon reference instance used here."""
    Poseidon = _try_import_poseidon()
    if Poseidon is None:
        return None
    # BLS12-381 scalar field
    p = 0x73eda753299d7d483339d80809a1d80553bda402fffe5bfeffffffff00000001
    security_level = 128
    alpha = 5
    input_rate = 3
    t = 4
    try:
        instance = Poseidon(p, security_level, alpha, input_rate, t)
        return instance
    except Exception as exc:
        print(f"  [!] Could not initialise Poseidon: {exc}")
        return None


def benchmark_poseidon(data: bytes, poseidon_instance) -> float:
    """Return wall-clock seconds for one Poseidon hash invocation."""
    # Convert bytes to list of field elements (31-byte chunks → integers)
    chunks = [data[i:i + 31] for i in range(0, len(data), 31)]
    input_vec = [int.from_bytes(c, "little") for c in chunks]
    # Trim to input_rate (Poseidon has fixed input width)
    input_vec = input_vec[: poseidon_instance.input_rate]
    if len(input_vec) < poseidon_instance.input_rate:
        input_vec.extend([0] * (poseidon_instance.input_rate - len(input_vec)))
    start = time.perf_counter()
    poseidon_instance.run_hash(input_vec)
    return time.perf_counter() - start


# ---------------------------------------------------------------------------
# Main benchmark driver
# ---------------------------------------------------------------------------

def run_benchmarks():
    """Run comparative benchmarks and print a summary table."""
    sizes = [64, 256, 1024, 4096]
    iterations = 20
    warmup = 3

    poseidon_instance = _make_poseidon_instance()
    has_poseidon = poseidon_instance is not None

    if has_poseidon:
        print("Note: Poseidon timings use a reference instance with t=4 and input_rate=3.")

    results: dict[str, dict[int, dict]] = {
        "SCH-128": {},
        "SHA3-256": {},
    }
    if has_poseidon:
        results["Poseidon"] = {}

    for size in sizes:
        data = bytes(range(256)) * (size // 256 + 1)
        data = data[:size]

        # --- SCH ---
        for _ in range(warmup):
            benchmark_sch(data)
        times = [benchmark_sch(data) for _ in range(iterations)]
        results["SCH-128"][size] = {
            "mean": statistics.mean(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
        }

        # --- SHA-3 ---
        for _ in range(warmup):
            benchmark_sha3(data)
        times = [benchmark_sha3(data) for _ in range(iterations)]
        results["SHA3-256"][size] = {
            "mean": statistics.mean(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
        }

        # --- Poseidon ---
        if has_poseidon:
            for _ in range(warmup):
                benchmark_poseidon(data, poseidon_instance)
            times = [benchmark_poseidon(data, poseidon_instance) for _ in range(iterations)]
            results["Poseidon"][size] = {
                "mean": statistics.mean(times),
                "stdev": statistics.stdev(times) if len(times) > 1 else 0.0,
            }

    # ---- Print results ----
    print("\n" + "=" * 75)
    print("COMPARATIVE HASHING PERFORMANCE")
    print("=" * 75)
    print(f"{'Algorithm':<14} {'Size (B)':<10} {'Mean (ms)':<12} {'StdDev (ms)':<12} {'Throughput':<12}")
    print("-" * 75)
    for algo in results:
        for size in sizes:
            m = results[algo][size]["mean"]
            s = results[algo][size]["stdev"]
            tp = (size / m) / 1e6 if m > 0 else 0.0
            print(f"{algo:<14} {size:<10} {m * 1000:<12.4f} {s * 1000:<12.4f} {tp:<10.2f} MB/s")
        print()

    # ---- LaTeX table ----
    print("\n% --- LaTeX table ---")
    print("\\begin{table}[H]")
    print("\\centering")
    print("\\caption{Comparative hashing performance (mean of %d runs).}" % iterations)
    print("\\label{tab:comparison}")
    col_count = len(results) + 1
    print("\\begin{tabular}{@{}l" + "r" * len(results) + "@{}}")
    print("\\toprule")
    header = "Input Size"
    for algo in results:
        header += f" & {algo} (ms)"
    header += " \\\\"
    print(header)
    print("\\midrule")
    for size in sizes:
        row = f"{size} B"
        for algo in results:
            row += f" & {results[algo][size]['mean'] * 1000:.4f}"
        row += " \\\\"
        print(row)
    print("\\bottomrule")
    print("\\end{tabular}")
    print("\\end{table}")


if __name__ == "__main__":
    run_benchmarks()
