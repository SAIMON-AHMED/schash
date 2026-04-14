"""Security analysis and attack complexity estimation for SCH."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

from .params import SCHParams


# ---------------------------------------------------------------------------
# Shared complexity-estimation helpers — used by both security_analysis.py
# and cryptanalysis.py so that every table in the paper comes from one
# formula.
# ---------------------------------------------------------------------------

def _binomial(n: int, k: int) -> int:
    """Exact binomial coefficient C(n, k)."""
    if k > n or k < 0:
        return 0
    if k == 0 or k == n:
        return 1
    k = min(k, n - k)
    result = 1
    for i in range(k):
        result = result * (n - i) // (i + 1)
    return result


def estimated_degree(d_tri: int, k: int, p: int) -> int:
    """Upper bound on the total degree of P after *k* composition rounds.

    Each unitriangular layer has coordinate degree <= d_tri and each affine
    layer preserves degree, so one round multiplies the degree by at most
    d_tri.  The degree is capped at p (the field size).
    """
    return min(d_tri ** k, p)


def dreg_estimate(n: int, d: int) -> int:
    """Heuristic degree-of-regularity for n equations of degree d in n vars.

    Uses the semi-regular (Macaulay) bound
        D_reg = floor( n(d - 1) / 2 ) + 1
    following Bardet, Faugère, Salvy & Yang (2004/2005).

    For very high d this is dominated by d*n/2; for d=2 it gives roughly n/2+1,
    which agrees with known random quadratic benchmarks.
    """
    return n * (d - 1) // 2 + 1


def groebner_log2_complexity(n: int, d: int, p: int, omega: float = 2.8) -> float:
    """Estimated log2 of Gröbner-basis attack complexity.

    complexity ≈ C(n + D_reg, D_reg)^ω   (field operations)

    where D_reg is the semi-regular degree-of-regularity bound and ω is the
    linear-algebra exponent (2.37 ≤ ω ≤ 3; we use 2.8 conservatively).

    The result is capped at n·log2(p) (exhaustive search).
    """
    dreg = dreg_estimate(n, d)
    mono = _binomial(n + dreg, dreg)
    if mono <= 0:
        return 0.0
    bits = math.log2(mono) * omega
    max_bits = n * math.log2(p)
    return min(bits, max_bits)


def interpolation_log2_complexity(n: int, d: int, p: int, omega: float = 2.8) -> float:
    """Estimated log2 of interpolation-attack complexity.

    The attacker must solve for the coefficients of P, which lives in a
    space of dimension C(n + d, d).  The system is solved via linear
    algebra, so the cost is roughly C(n + d, d)^ω.
    """
    mono = _binomial(n + d, d)
    if mono <= 0:
        return 0.0
    bits = math.log2(mono) * omega
    max_bits = n * math.log2(p)
    return min(bits, max_bits)


@dataclass
class SecurityEstimate:
    """Security level estimates for a parameter set."""
    
    params_name: str
    
    # Generic sponge attacks
    collision_bits: float
    preimage_bits: float
    
    # Algebraic attack estimates
    interpolation_complexity: float
    groebner_complexity: float
    
    # System characteristics
    num_variables: int
    max_degree: int
    num_equations: int
    
    # Security margin
    target_security: int
    margin_collision: float
    margin_preimage: float


def estimate_security_level(params: SCHParams) -> SecurityEstimate:
    """
    Estimate security levels for given parameters.
    
    Returns bits of security against various attack types.
    """
    log2_p = math.log2(params.p)
    
    # Generic sponge attacks
    collision_bits = (params.c * log2_p) / 2  # Birthday bound on capacity
    preimage_bits = params.c * log2_p  # Capacity-based preimage resistance
    
    # Algebraic system characteristics after k rounds
    deg = estimated_degree(params.d_tri, params.k, params.p)
    
    # Interpolation attack
    interp = interpolation_log2_complexity(params.n, deg, params.p)
    
    # Gröbner basis attack
    grob = groebner_log2_complexity(params.n, deg, params.p)
    
    # Target security level based on capacity
    target_security = min(128, int(collision_bits))
    
    # Security margins
    margin_collision = collision_bits / target_security if target_security > 0 else 1.0
    margin_preimage = preimage_bits / (target_security * 2) if target_security > 0 else 1.0
    
    return SecurityEstimate(
        params_name=params.name,
        collision_bits=collision_bits,
        preimage_bits=preimage_bits,
        interpolation_complexity=interp,
        groebner_complexity=grob,
        num_variables=params.n,
        max_degree=deg,
        num_equations=params.n,
        target_security=target_security,
        margin_collision=margin_collision,
        margin_preimage=margin_preimage,
    )


def analyze_all_parameters() -> Dict[str, SecurityEstimate]:
    """Generate security estimates for all standard parameter sets."""
    from .params import PARAMS
    
    results = {}
    for name, params in PARAMS.items():
        if params.toy:
            continue
        results[name] = estimate_security_level(params)
    return results


def print_security_summary(estimate: SecurityEstimate) -> None:
    """Print human-readable security summary."""
    print(f"\n{'='*60}")
    print(f"Security Analysis: {estimate.params_name}")
    print(f"{'='*60}")
    print(f"\nGeneric Sponge Attacks:")
    print(f"  Collision resistance:  {estimate.collision_bits:>6.1f} bits")
    print(f"  Preimage resistance:   {estimate.preimage_bits:>6.1f} bits")
    print(f"\nAlgebraic Attack Estimates:")
    print(f"  Interpolation attack:  {estimate.interpolation_complexity:>6.1f} bits")
    print(f"  Gröbner basis attack:  {estimate.groebner_complexity:>6.1f} bits")
    print(f"\nSystem Characteristics:")
    print(f"  Variables (n):         {estimate.num_variables:>6}")
    print(f"  Estimated max degree:  {estimate.max_degree:>6}")
    print(f"  Equations:             {estimate.num_equations:>6}")
    print(f"\nSecurity Margins:")
    print(f"  Target level:          {estimate.target_security:>6} bits")
    print(f"  Collision margin:      {estimate.margin_collision:>6.2f}x")
    print(f"  Preimage margin:       {estimate.margin_preimage:>6.2f}x")


if __name__ == "__main__":
    results = analyze_all_parameters()
    for estimate in results.values():
        print_security_summary(estimate)
