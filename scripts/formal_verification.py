"""Structural verification for SCH permutation construction.

This script checks the construction invariants that imply bijectivity:
1. Every affine layer matrix lies in SL_n(F_p), i.e. det(M_i) = 1.
2. Every triangular layer has the unitriangular form
   x_j -> x_j + g_j(x_0, ..., x_{j-1}).
3. The toy31 permutation is bijective by exhaustive enumeration.

For the published non-toy parameter sets, bijectivity follows mathematically
from these verified layer properties and the proof in main.tex. The script does
not use finite differences or approximate Jacobians.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.params import get_params, PARAMS, SCHParams
from sch.permutation import SCHPermutation
from sch.triangular import enumerate_monomials
from sch.field import modular_det


def verify_affine_determinants(params: SCHParams, perm: SCHPermutation) -> bool:
    """Verify that every affine layer matrix has determinant exactly 1 mod p."""
    print(f"  [1/2] Checking affine layer determinants ({params.k} rounds)...")
    all_ok = True
    for round_idx, rnd in enumerate(perm.rounds, start=1):
        matrix = [list(row) for row in rnd.affine.matrix]
        if len(matrix) != params.n or any(len(row) != params.n for row in matrix):
            print(f"        Round {round_idx}: matrix dimension mismatch  *** FAIL ***")
            all_ok = False
            continue
        if len(rnd.affine.bias) != params.n:
            print(f"        Round {round_idx}: bias dimension mismatch  *** FAIL ***")
            all_ok = False
            continue

        det = modular_det(matrix, params.p)
        if det != 1:
            print(f"        Round {round_idx}: det = {det}  *** FAIL (expected 1) ***")
            all_ok = False
        else:
            print(f"        Round {round_idx}: det = 1")
    return all_ok


def verify_triangular_structure(params: SCHParams, perm: SCHPermutation) -> bool:
    """Verify that every triangular layer matches the declared unitriangular basis."""
    print("  [2/2] Checking triangular layer structure...")
    all_ok = True
    for round_idx, rnd in enumerate(perm.rounds, start=1):
        tri = rnd.triangular
        if len(tri.polynomials) != params.n - 1:
            print(
                f"        Round {round_idx}: expected {params.n - 1} polynomials, "
                f"found {len(tri.polynomials)}  *** FAIL ***"
            )
            all_ok = False
            continue

        round_ok = True
        for coord_idx, poly in enumerate(tri.polynomials, start=1):
            expected_monomials = enumerate_monomials(coord_idx, params.d_tri)
            if list(poly.monomials) != expected_monomials:
                print(
                    f"        Round {round_idx}, coord {coord_idx}: monomial basis mismatch"
                    "  *** FAIL ***"
                )
                all_ok = False
                round_ok = False
            if len(poly.coefficients) != len(expected_monomials):
                print(
                    f"        Round {round_idx}, coord {coord_idx}: coefficient count mismatch"
                    "  *** FAIL ***"
                )
                all_ok = False
                round_ok = False
            if not any(coeff % params.p for coeff in poly.coefficients):
                print(
                    f"        Round {round_idx}, coord {coord_idx}: all-zero polynomial"
                    "  *** FAIL ***"
                )
                all_ok = False
                round_ok = False
        if round_ok:
            print(
                f"        Round {round_idx}: unitriangular basis matches "
                f"degree d_tri = {params.d_tri}"
            )
    return all_ok


def verify_toy_permutation_exhaustive() -> bool:
    """Exhaustively verify that the toy31 permutation is bijective."""
    params = get_params("toy31")
    perm = SCHPermutation(params)
    print("\n" + "=" * 70)
    print(f"Verifying: {params.name}  (exhaustive bijectivity over {params.p}^{params.n} states)")
    print("=" * 70)

    seen: dict[tuple[int, ...], tuple[int, ...]] = {}
    for state in itertools.product(range(params.p), repeat=params.n):
        output = tuple(perm.apply(list(state)))
        if output in seen:
            print(
                f"  Collision found: {seen[output]} and {state} both map to {output}"
                "  *** FAIL ***"
            )
            return False
        seen[output] = state

    print(f"  Exhaustive check passed: {len(seen)} unique outputs from {params.p ** params.n} inputs")
    return True


def verify_parameter_set(params_name: str) -> bool:
    """Verify the structural invariants for one non-toy parameter set."""
    params = get_params(params_name)
    if params.toy:
        return verify_toy_permutation_exhaustive()

    print("\n" + "=" * 70)
    print(f"Verifying: {params.name}  (p ≈ 2^{params.p.bit_length()}, n={params.n}, k={params.k})")
    print("=" * 70)
    perm = SCHPermutation(params)

    ok_affine = verify_affine_determinants(params, perm)
    ok_tri = verify_triangular_structure(params, perm)
    passed = ok_affine and ok_tri

    if passed:
        print(
            "\n  >>> Overall verdict: PASSED "
            "(bijectivity follows from composition of verified layer types)"
        )
    else:
        print("\n  >>> Overall verdict: FAILED")
    return passed


if __name__ == "__main__":
    print("=" * 70)
    print("STRUCTURAL VERIFICATION OF SCH PERMUTATION")
    print("=" * 70)

    all_passed = verify_toy_permutation_exhaustive()
    for name, params in PARAMS.items():
        if params.toy:
            continue
        all_passed = verify_parameter_set(name) and all_passed

    print("\n" + "=" * 70)
    if all_passed:
        print("ALL CHECKS PASSED.")
    else:
        print("SOME CHECKS FAILED.")
    print("=" * 70)