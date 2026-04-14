#!/usr/bin/env python
"""Reproduce all results from the SCH paper.

Run:
    python reproduce.py           # full reproduction (may take several minutes)
    python reproduce.py --quick   # fast check (~30s): tests + basic analysis only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(cmd: list[str], label: str, timeout: int = 600) -> bool:
    """Run a command, print status, return True on success."""
    print(f"\n{'='*72}")
    print(f"  {label}")
    print(f"  $ {' '.join(cmd)}")
    print(f"{'='*72}")
    t0 = time.time()
    try:
        result = subprocess.run(
            cmd, cwd=str(ROOT), timeout=timeout,
            capture_output=False,
        )
        elapsed = time.time() - t0
        status = "PASS" if result.returncode == 0 else "FAIL"
        print(f"\n  [{status}] {label} ({elapsed:.1f}s)")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        elapsed = time.time() - t0
        print(f"\n  [TIMEOUT] {label} ({elapsed:.1f}s)")
        return False


def main():
    parser = argparse.ArgumentParser(description="Reproduce SCH paper results")
    parser.add_argument("--quick", action="store_true",
                        help="Quick check: tests + basic analysis only")
    parser.add_argument("--skip-pdf", action="store_true",
                        help="Skip LaTeX compilation")
    args = parser.parse_args()

    py = sys.executable
    results = []

    # 1. Test suite
    results.append(("Test suite", run(
        [py, "-m", "pytest", "tests/", "-v", "--tb=short"],
        "Test suite (24 tests)",
    )))

    # 2. Formal verification
    results.append(("Formal verification", run(
        [py, "scripts/formal_verification.py"],
        "Structural verification (det=1, unitriangular, bijectivity)",
    )))

    # 3. Differential analysis
    results.append(("Differential analysis", run(
        [py, "scripts/differential_analysis.py",
         "--params", "all", "--paper-profile", "--summary-only"],
        "Differential/statistical sanity checks (all params)",
    )))

    # 4. Linear analysis (SCH-128 only for speed)
    if not args.quick:
        results.append(("Linear analysis", run(
            [py, "scripts/linear_analysis.py",
             "--params", "sch128", "--mask-trials", "64", "--samples", "256"],
            "Linear bias screening (sch128, 64 masks, 256 samples)",
        )))

        # 5. Higher-order differential
        results.append(("Higher-order diff", run(
            [py, "scripts/higher_order_diff.py",
             "--params", "sch128", "--trials", "64"],
            "Higher-order differential screening (sch128)",
        )))

        # 6. Multi-coord differential
        results.append(("Multi-coord diff", run(
            [py, "scripts/differential_analysis.py",
             "--params", "sch128", "--multi-coord", "--trials", "64"],
            "Multi-coordinate perturbation (sch128)",
        )))

        # 7. Groebner experiments
        results.append(("Groebner experiments", run(
            [py, "scripts/groebner_experiment.py"],
            "Groebner basis experiments (toy31)",
            timeout=900,
        )))

        # 8. Security tables
        results.append(("Security tables", run(
            [py, "scripts/generate_tables.py"],
            "Generate security estimate tables",
        )))

        # 9. Benchmarks
        results.append(("Benchmarks", run(
            [py, "scripts/benchmark_comparison.py"],
            "Benchmark comparison (SCH vs SHA3 vs Poseidon)",
        )))

        # 10. Export polynomial systems
        results.append(("Poly export", run(
            [py, "scripts/export_system.py",
             "--params", "toy31", "--k", "1", "2", "3",
             "--format", "sage"],
            "Export polynomial systems for Sage",
        )))

    # 11. PDF compilation
    if not args.skip_pdf:
        results.append(("PDF (pass 1)", run(
            ["pdflatex", "-interaction=nonstopmode", "main.tex"],
            "LaTeX compilation (pass 1)",
        )))
        results.append(("PDF (pass 2)", run(
            ["pdflatex", "-interaction=nonstopmode", "main.tex"],
            "LaTeX compilation (pass 2)",
        )))

    # Summary
    print(f"\n\n{'='*72}")
    print("  REPRODUCTION SUMMARY")
    print(f"{'='*72}")
    all_pass = True
    for name, passed in results:
        icon = "PASS" if passed else "FAIL"
        print(f"  [{icon}] {name}")
        if not passed:
            all_pass = False

    print(f"{'='*72}")
    if all_pass:
        print("  All steps passed.")
    else:
        print("  Some steps failed. See output above for details.")
    print()

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
