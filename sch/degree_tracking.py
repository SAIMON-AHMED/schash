from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .params import SCHParams, get_params
from .permutation import SCHPermutation


@dataclass
class DegreeGrowthResult:
    """Container for tracking per-round algebraic degree data."""

    max_degrees: List[int]
    degree_vectors: List[List[int]]
    initial_degrees: List[int]
    absorption_rounds: List[int]


def _inject_rate_variables(state: List[int], rate: int) -> List[int]:
    updated = list(state)
    for idx in range(min(rate, len(updated))):
        updated[idx] = max(updated[idx], 1)
    return updated


def _polynomial_degree(poly, input_degrees: Sequence[int], modulus: int) -> int:
    max_degree = 0
    for coeff, mon in zip(poly.coefficients, poly.monomials):
        if coeff % modulus == 0:
            continue
        term_degree = 0
        for exponent, degree in zip(mon, input_degrees):
            term_degree += exponent * degree
        if term_degree > max_degree:
            max_degree = term_degree
    return max_degree


def _triangular_degree_step(degrees: Sequence[int], triangular, modulus: int) -> List[int]:
    if not degrees:
        return []
    source = list(degrees)
    updated = list(degrees)
    updated[0] = source[0]
    for coord, poly in enumerate(triangular.polynomials, start=1):
        g_degree = _polynomial_degree(poly, source[:coord], modulus)
        updated[coord] = max(source[coord], g_degree)
    return updated


def _affine_degree_step(degrees: Sequence[int], affine, modulus: int) -> List[int]:
    updated: List[int] = []
    for row in affine.matrix:
        row_degree = 0
        for coeff, degree in zip(row, degrees):
            if coeff % modulus == 0:
                continue
            if degree > row_degree:
                row_degree = degree
        updated.append(row_degree)
    return updated


def compute_degree_growth(
    params: SCHParams,
    rounds: int | None = None,
    absorb_rounds: Iterable[int] | None = None,
) -> DegreeGrowthResult:
    if params.toy:
        raise ValueError("Degree tracking is only defined for non-toy permutations.")
    permutation = SCHPermutation(params)
    total_rounds = rounds if rounds is not None else len(permutation.rounds)
    if total_rounds > len(permutation.rounds):
        raise ValueError("Requested rounds exceed permutation definition")
    schedule = sorted(set(absorb_rounds if absorb_rounds is not None else [0]))
    schedule = [r for r in schedule if 0 <= r < total_rounds]
    degrees = [0] * params.n
    initial_degrees: List[int] | None = None
    max_degrees: List[int] = []
    per_round: List[List[int]] = []
    for round_idx in range(total_rounds):
        if round_idx in schedule:
            degrees = _inject_rate_variables(degrees, params.r)
        if round_idx == 0 and initial_degrees is None:
            initial_degrees = degrees.copy()
        round_data = permutation.rounds[round_idx]
        degrees = _triangular_degree_step(degrees, round_data.triangular, params.p)
        degrees = _affine_degree_step(degrees, round_data.affine, params.p)
        per_round.append(degrees.copy())
        max_degrees.append(max(degrees) if degrees else 0)
    if initial_degrees is None:
        initial_degrees = [0] * params.n
    return DegreeGrowthResult(
        max_degrees=max_degrees,
        degree_vectors=per_round,
        initial_degrees=initial_degrees,
        absorption_rounds=schedule,
    )


def degree_growth_sch128(rounds: int | None = None) -> List[int]:
    params = get_params("sch128")
    result = compute_degree_growth(params, rounds)
    return result.max_degrees
