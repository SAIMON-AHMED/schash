"""Attack complexity estimation for SCH."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List

from .params import SCHParams, get_params
from .security_analysis import (
    estimated_degree as _est_degree,
    interpolation_log2_complexity,
    groebner_log2_complexity,
)


@dataclass
class AttackResult:
    """Results from an attack attempt."""
    
    attack_name: str
    params_name: str
    rounds_attacked: int
    success: bool
    time_seconds: float
    complexity_estimate: str
    details: str


def interpolation_complexity_estimate(
    params: SCHParams,
    reduced_rounds: int,
) -> AttackResult:
    """Estimate interpolation attack complexity on reduced-round SCH.

    This does *not* attempt an actual interpolation; it computes the
    theoretical monomial-count bound and reports whether the resulting
    linear-algebra cost is feasible.
    """
    start_time = time.time()

    degree = _est_degree(params.d_tri, reduced_rounds, params.p)
    interp_bits = interpolation_log2_complexity(params.n, degree, params.p)

    if interp_bits < 64:
        complexity = f"~2^{int(interp_bits)} operations (feasible)"
        success = True
    else:
        complexity = f"~2^{int(interp_bits)} operations (infeasible)"
        success = False

    elapsed = time.time() - start_time

    details = (
        f"Estimated degree: {degree}, variables: {params.n}. "
        f"Interpolation complexity: ~2^{int(interp_bits)} (shared formula)."
    )

    return AttackResult(
        attack_name="Interpolation (estimate)",
        params_name=params.name,
        rounds_attacked=reduced_rounds,
        success=success,
        time_seconds=elapsed,
        complexity_estimate=complexity,
        details=details,
    )


def groebner_complexity_estimate(
    params: SCHParams,
    reduced_rounds: int,
) -> AttackResult:
    """Estimate Gröbner basis attack complexity on reduced-round SCH.

    This does *not* run a solver; it applies the semi-regular
    degree-of-regularity bound to estimate cost.
    """
    start_time = time.time()

    degree = _est_degree(params.d_tri, reduced_rounds, params.p)
    n = params.n
    grob_bits = groebner_log2_complexity(n, degree, params.p)
    
    if grob_bits < 64:
        complexity = f"~2^{int(grob_bits)} operations (feasible)"
        success = True
    elif grob_bits < 128:
        complexity = f"~2^{int(grob_bits)} operations (borderline)"
        success = False
    else:
        complexity = f"~2^{int(grob_bits)} operations (infeasible)"
        success = False
    
    elapsed = time.time() - start_time
    
    details = (
        f"System: {n} equations in {n} variables over F_p (log2(p) ≈ {params.p.bit_length()}). "
        f"Max degree after {reduced_rounds} rounds: ~{degree}. "
        f"D_reg (semi-regular bound): ~{n * (degree - 1) // 2 + 1}. "
        f"Gröbner complexity: ~2^{int(grob_bits)} (shared formula)."
    )
    
    return AttackResult(
        attack_name="Gröbner Basis / XL (estimate)",
        params_name=params.name,
        rounds_attacked=reduced_rounds,
        success=success,
        time_seconds=elapsed,
        complexity_estimate=complexity,
        details=details,
    )


def exhaustive_search_complexity(params: SCHParams) -> AttackResult:
    """
    Calculate exhaustive search complexity for preimage/collision.
    
    This serves as an upper bound on attack complexity.
    """
    start_time = time.time()
    
    field_size_bits = params.n * params.p.bit_length()
    
    # Collision: birthday bound on capacity
    collision_bits = (params.c * params.p.bit_length()) / 2
    
    # Preimage: full capacity
    preimage_bits = params.c * params.p.bit_length()
    
    elapsed = time.time() - start_time
    
    complexity = f"Collision: 2^{collision_bits:.1f}, Preimage: 2^{preimage_bits:.1f}"
    
    details = (
        f"State space: 2^{field_size_bits:.1f}. "
        f"Capacity: {params.c} elements of log2(p)={params.p.bit_length()} bits. "
        f"Generic attacks limited by capacity under sponge security model."
    )
    
    return AttackResult(
        attack_name="Exhaustive Search (Upper Bound)",
        params_name=params.name,
        rounds_attacked=params.k,
        success=False,
        time_seconds=elapsed,
        complexity_estimate=complexity,
        details=details,
    )


def run_complexity_estimates(params_name: str = "sch128") -> List[AttackResult]:
    """Compute complexity estimates for all attack classes on a parameter set."""
    params = get_params(params_name)
    results: List[AttackResult] = []

    print(f"\n{'='*70}")
    print(f"Complexity Estimates: {params_name}")
    print(f"{'='*70}\n")

    for rounds in sorted(set([1, 2, 3, params.k // 2, params.k])):
        if rounds > params.k or rounds < 1:
            continue

        print(f"Estimating {rounds}/{params.k} rounds...")

        result = interpolation_complexity_estimate(params, rounds)
        results.append(result)
        print(f"  [Interpolation] {result.complexity_estimate}")

        result = groebner_complexity_estimate(params, rounds)
        results.append(result)
        print(f"  [Algebraic]     {result.complexity_estimate}")

    result = exhaustive_search_complexity(params)
    results.append(result)
    print(f"\n  [Exhaustive]    {result.complexity_estimate}")

    return results


def print_attack_summary(result: AttackResult) -> None:
    """Print detailed attack result."""
    print(f"\n{'='*70}")
    print(f"{result.attack_name} on {result.params_name} ({result.rounds_attacked} rounds)")
    print(f"{'='*70}")
    print(f"Success:    {result.success}")
    print(f"Time:       {result.time_seconds:.6f}s")
    print(f"Complexity: {result.complexity_estimate}")
    print(f"\nDetails: {result.details}")


if __name__ == "__main__":
    results = run_complexity_estimates("sch128")

    print(f"\n\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}\n")

    feasible = sum(1 for r in results if r.success)
    print(f"Feasible attacks: {feasible}/{len(results)}")
    print(f"Reduced-round estimates show increasing complexity with round count.")
