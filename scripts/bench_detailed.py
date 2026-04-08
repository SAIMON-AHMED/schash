"""Enhanced performance benchmarking for SCH with detailed metrics."""

from __future__ import annotations

import gc
import secrets
import sys
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.encoding import compute_block_size
from sch.params import get_params, PARAMS, SCHParams
from sch.sponge import sch_hash


@dataclass
class BenchmarkResult:
    """Detailed benchmark results."""
    
    params_name: str
    message_size: int
    iterations: int
    
    total_time: float
    avg_time_per_hash: float
    throughput_mbps: float
    throughput_hashes_per_sec: float
    
    peak_memory_mb: float
    permutation_calls: int
    
    # System characteristics
    state_size: int
    rounds: int
    field_bits: int


def benchmark_detailed(
    params_name: str,
    size: int = 1024,
    iterations: int = 100,
    warmup: int = 5
) -> BenchmarkResult:
    """
    Run detailed benchmark with memory profiling.
    
    Args:
        params_name: Parameter set to benchmark
        size: Message size in bytes
        iterations: Number of iterations
        warmup: Warm-up iterations (not counted)
    """
    params = get_params(params_name)
    digest_bytes = compute_block_size(params.p) * params.digest_length
    
    # Warm-up phase
    payload = secrets.token_bytes(size)
    for _ in range(warmup):
        _ = sch_hash(payload, params, out_bytes=digest_bytes)
    
    # Start memory tracking
    gc.collect()
    tracemalloc.start()
    
    # Benchmark phase
    start = time.perf_counter()
    for idx in range(iterations):
        _ = sch_hash(payload, params, out_bytes=digest_bytes)
        # Vary message slightly to avoid caching artifacts
        if len(payload) >= 2:
            prefix = (int.from_bytes(payload[:2], "little") + idx + 1) % (1 << 16)
            payload = prefix.to_bytes(2, "little") + payload[2:]
    elapsed = time.perf_counter() - start
    
    # Get memory stats
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    # Calculate metrics
    total_bytes = size * iterations
    avg_time = elapsed / iterations
    throughput_mbps = (total_bytes / elapsed) / 1e6
    hashes_per_sec = iterations / elapsed
    peak_memory_mb = peak / 1e6
    
    # Estimate permutation calls (absorb + squeeze)
    block_size = compute_block_size(params.p)
    num_blocks = (len(payload) + block_size - 1) // block_size
    permutation_calls = num_blocks + params.digest_length  # Absorb + squeeze
    
    return BenchmarkResult(
        params_name=params_name,
        message_size=size,
        iterations=iterations,
        total_time=elapsed,
        avg_time_per_hash=avg_time,
        throughput_mbps=throughput_mbps,
        throughput_hashes_per_sec=hashes_per_sec,
        peak_memory_mb=peak_memory_mb,
        permutation_calls=permutation_calls,
        state_size=params.n,
        rounds=params.k,
        field_bits=params.p.bit_length(),
    )


def benchmark_suite(sizes: List[int] = None, iterations: int = 100) -> Dict[str, List[BenchmarkResult]]:
    """
    Run comprehensive benchmark suite across parameter sets and message sizes.
    """
    if sizes is None:
        sizes = [64, 256, 1024, 4096, 16384]
    
    results: Dict[str, List[BenchmarkResult]] = {}
    
    for params_name, params in PARAMS.items():
        if params.toy:
            continue  # Skip toy parameters
        
        print(f"\nBenchmarking {params_name}...")
        results[params_name] = []
        
        for size in sizes:
            print(f"  {size} bytes...", end=" ", flush=True)
            result = benchmark_detailed(params_name, size, iterations)
            results[params_name].append(result)
            print(f"{result.throughput_mbps:.2f} MB/s")
    
    return results


def print_benchmark_summary(result: BenchmarkResult) -> None:
    """Print detailed benchmark summary."""
    print(f"\n{'='*70}")
    print(f"Benchmark: {result.params_name} ({result.message_size} bytes)")
    print(f"{'='*70}")
    print(f"Performance:")
    print(f"  Total time:           {result.total_time:.3f}s ({result.iterations} iterations)")
    print(f"  Avg time per hash:    {result.avg_time_per_hash*1000:.3f}ms")
    print(f"  Throughput:           {result.throughput_mbps:.2f} MB/s")
    print(f"  Hashes per second:    {result.throughput_hashes_per_sec:.1f}")
    print(f"\nResource Usage:")
    print(f"  Peak memory:          {result.peak_memory_mb:.2f} MB")
    print(f"  Permutation calls:    ~{result.permutation_calls} per hash")
    print(f"\nSystem Parameters:")
    print(f"  State size:           {result.state_size} elements")
    print(f"  Rounds:               {result.rounds}")
    print(f"  Field size:           2^{result.field_bits}")


def generate_comparison_table(results: Dict[str, List[BenchmarkResult]]) -> None:
    """Generate comparison table across all benchmarks."""
    print(f"\n\n{'='*70}")
    print("PERFORMANCE COMPARISON TABLE")
    print(f"{'='*70}\n")
    
    # Header
    print(f"{'Param':<12} {'Size':<8} {'MB/s':<10} {'ms/hash':<10} {'Mem(MB)':<10}")
    print("-" * 70)
    
    # Data rows
    for params_name in sorted(results.keys()):
        for result in results[params_name]:
            print(
                f"{result.params_name:<12} "
                f"{result.message_size:<8} "
                f"{result.throughput_mbps:<10.2f} "
                f"{result.avg_time_per_hash*1000:<10.3f} "
                f"{result.peak_memory_mb:<10.2f}"
            )


def generate_latex_table(results: Dict[str, List[BenchmarkResult]]) -> str:
    """Generate LaTeX table for paper."""
    lines = []
    lines.append("\\begin{table}[H]")
    lines.append("\\centering")
    lines.append("\\caption{Performance benchmarks for SCH parameter sets.}")
    lines.append("\\label{tab:performance}")
    lines.append("\\begin{tabular}{@{}lrrrrr@{}}")
    lines.append("\\toprule")
    lines.append("Parameter Set & Message & Throughput & Time & Memory & Perm.Calls \\\\")
    lines.append(" & (bytes) & (MB/s) & (ms) & (MB) & (per hash) \\\\")
    lines.append("\\midrule")
    
    for params_name in sorted(results.keys()):
        for i, result in enumerate(results[params_name]):
            prefix = result.params_name if i == 0 else ""
            lines.append(
                f"{prefix:<10} & "
                f"{result.message_size:>5} & "
                f"{result.throughput_mbps:>6.2f} & "
                f"{result.avg_time_per_hash*1000:>5.2f} & "
                f"{result.peak_memory_mb:>5.2f} & "
                f"{result.permutation_calls:>4} \\\\"
            )
        if params_name != sorted(results.keys())[-1]:
            lines.append("\\addlinespace")
    
    lines.append("\\bottomrule")
    lines.append("\\end{tabular}")
    lines.append("\\end{table}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("Running comprehensive benchmark suite...")
    print("This may take a few minutes...")
    
    results = benchmark_suite(sizes=[256, 1024, 4096], iterations=50)
    
    # Print detailed results
    for params_results in results.values():
        for result in params_results:
            print_benchmark_summary(result)
    
    # Print comparison table
    generate_comparison_table(results)
    
    # Generate LaTeX table
    print(f"\n\n{'='*70}")
    print("LATEX TABLE FOR PAPER")
    print(f"{'='*70}\n")
    print(generate_latex_table(results))
