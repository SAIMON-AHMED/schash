"""Security analysis and attack complexity estimation for SCH."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

from .params import SCHParams


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
    # Conservative estimate: degree grows roughly as d^k for triangular composition
    estimated_degree = min(params.d_tri ** params.k, params.p)
    
    # Number of monomials up to degree d in n variables: C(n+d, d)
    def binomial(n: int, k: int) -> int:
        if k > n or k < 0:
            return 0
        if k == 0 or k == n:
            return 1
        k = min(k, n - k)
        result = 1
        for i in range(k):
            result = result * (n - i) // (i + 1)
        return result
    
    # Monomial count grows combinatorially with degree
    monomial_count = binomial(params.n + estimated_degree, estimated_degree)
    
    # Interpolation attack: need to solve for coefficients
    # Complexity is roughly O(m^omega) where m is monomial count
    # Using omega ≈ 2.8 (Strassen-like matrix multiplication)
    omega = 2.8
    interpolation_complexity = math.log2(max(monomial_count, 1)) * omega
    
    # Gröbner basis complexity (very rough estimate using Dreg bound)
    # For regular sequences: Dreg ~ d*n, complexity ~ O(n * binomial(n + Dreg, Dreg))
    dreg_bound = min(estimated_degree * params.n, params.p)
    groebner_monomials = binomial(params.n + dreg_bound, dreg_bound)
    groebner_complexity = math.log2(max(groebner_monomials, 1)) * omega
    
    # Cap at field size (exhaustive search ceiling)
    max_complexity = params.n * log2_p
    interpolation_complexity = min(interpolation_complexity, max_complexity)
    groebner_complexity = min(groebner_complexity, max_complexity)
    
    # Target security level based on capacity
    target_security = min(128, int(collision_bits))
    
    # Security margins
    margin_collision = collision_bits / target_security if target_security > 0 else 1.0
    margin_preimage = preimage_bits / (target_security * 2) if target_security > 0 else 1.0
    
    return SecurityEstimate(
        params_name=params.name,
        collision_bits=collision_bits,
        preimage_bits=preimage_bits,
        interpolation_complexity=interpolation_complexity,
        groebner_complexity=groebner_complexity,
        num_variables=params.n,
        max_degree=estimated_degree,
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
