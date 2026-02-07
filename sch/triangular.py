"""Triangular maps used inside Symbolic Composition Hashing rounds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence

from .constants import ConstantDeriver
from .field import PrimeField
from .params import SCHParams


def enumerate_monomials(var_count: int, max_degree: int) -> List[tuple[int, ...]]:
    if var_count == 0:
        return []
    monomials: List[tuple[int, ...]] = []
    exponents = [0] * var_count

    def rec(position: int, remaining: int, target_degree: int) -> None:
        if position == var_count - 1:
            exponents[position] = remaining
            monomials.append(tuple(exponents))
            return
        for exp in range(remaining + 1):
            exponents[position] = exp
            rec(position + 1, remaining - exp, target_degree)

    for total_degree in range(max_degree + 1):
        rec(0, total_degree, total_degree)
    return monomials


@dataclass
class TriangularPolynomial:
    monomials: Sequence[tuple[int, ...]]
    coefficients: Sequence[int]

    def evaluate(self, values: Sequence[int], field: PrimeField) -> int:
        if len(values) != len(self.monomials[0]):
            raise ValueError("value length mismatch for polynomial evaluation")
        total = 0
        for coeff, exponents in zip(self.coefficients, self.monomials):
            term = coeff
            if term == 0:
                continue
            for value, exponent in zip(values, exponents):
                if exponent == 0:
                    continue
                term = field.mul(term, field.pow(value, exponent))
            total = field.add(total, term)
        return total


@dataclass
class TriangularMap:
    offset: int
    polynomials: Sequence[TriangularPolynomial]

    def apply(self, state: Sequence[int], field: PrimeField) -> List[int]:
        if len(state) == 0:
            return []
        source = list(state)
        result = list(state)
        result[0] = field.add(source[0], self.offset)
        for idx in range(1, len(state)):
            poly = self.polynomials[idx - 1]
            g_val = poly.evaluate(source[:idx], field)
            result[idx] = field.add(source[idx], g_val)
        return result


_MAX_COEFF_RETRIES = 256


def generate_triangular_maps(
    params: SCHParams, field: PrimeField, deriver: ConstantDeriver
) -> List[TriangularMap]:
    """Generate k triangular maps with SHAKE256-derived coefficients.

    Each triangular map T_i applies:
      y_0 = x_0 + c_i  (constant offset)
      y_j = x_j + g_{i,j}(x_0, ..., x_{j-1})  for j in 1..n-1

    The polynomials g_{i,j} are dense over all monomials up to total degree d_tri.
    Monomial count for coordinate j: C(j + d_tri, d_tri) where C is binomial.
    Coefficients are uniform in F_p via SHAKE256 rejection sampling.

    The retry mechanism ensures at least one non-zero coefficient per polynomial.
    For p >> monomial_count, all-zero is probability ~(1/p)^|monomials|, but we
    bound retries to _MAX_COEFF_RETRIES for provable termination.
    """
    maps: List[TriangularMap] = []
    for round_idx in range(params.k):
        offset = deriver.derive_int("c_i", [round_idx], field.p)
        polynomials: List[TriangularPolynomial] = []
        for coord in range(1, params.n):
            monomials = enumerate_monomials(coord, params.d_tri)
            coeffs: List[int] = []
            for retry in range(_MAX_COEFF_RETRIES):
                coeffs = [
                    deriver.derive_int(
                        "g_coeff", [round_idx, coord, mono_idx] if retry == 0
                        else [round_idx, coord, mono_idx, retry], field.p
                    )
                    for mono_idx in range(len(monomials))
                ]
                if any(coeffs):
                    break
            else:
                raise RuntimeError(
                    f"Failed to derive non-zero polynomial after {_MAX_COEFF_RETRIES} "
                    f"retries for round={round_idx}, coord={coord}. "
                    f"This indicates a PRNG or parameter configuration issue."
                )
            polynomials.append(TriangularPolynomial(monomials, coeffs))
        maps.append(TriangularMap(offset, polynomials))
    return maps
