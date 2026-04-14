#!/usr/bin/env python
"""Export SCH polynomial systems to SageMath format.

Generates .sage files that define the SCH permutation as a polynomial
system over GF(p) for use with Sage's own Gröbner basis solvers
(Singular, Magma interface, or FGb if available).  This enables
reviewers and collaborators to run algebraic experiments on reduced
SCH instances using production-grade solvers.

Usage:
    python scripts/export_system.py                 # default: toy31 k=1..3
    python scripts/export_system.py --params sch128 --n 3 4 5 --k 1 2 3
    python scripts/export_system.py --format magma  # export .magma instead
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import List, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.params import SCHParams, PARAMS
from sch.permutation import SCHPermutation
from sch.field import field_from_params


def build_polynomial_strings(params: SCHParams) -> tuple[list[str], list[str]]:
    """Build SCH permutation as string polynomial expressions over GF(p).

    Returns (variable_names, polynomial_strings) where each polynomial
    string is a valid expression in both Sage and Magma syntax (with
    minor formatting differences handled by the exporter).
    """
    perm = SCHPermutation(params)
    n = params.n
    p = params.p

    var_names = [f"x{i}" for i in range(n)]

    # We build the polynomials by tracking symbolic string expressions
    # and doing explicit coefficient arithmetic mod p.
    # For small instances this is tractable; for large ones the
    # expressions will be huge (which is the point -- to test solvers).

    # Use Python integers for coefficient arithmetic.
    # Represent each state element as a dict: monomial_tuple -> coefficient.
    # monomial_tuple is a tuple of (var_index, exponent) pairs, sorted.

    # For simplicity with larger instances, use sympy to build then serialize.
    try:
        import sympy
        from sympy import symbols, GF as SymGF, Poly
        return _build_with_sympy(params, var_names)
    except ImportError:
        raise RuntimeError("sympy is required for polynomial export")


def _build_with_sympy(params: SCHParams, var_names: list[str]):
    import sympy
    from sympy import symbols, GF as SymGF, Poly

    n = params.n
    p = params.p
    F = SymGF(p)
    xs = symbols(var_names)

    perm = SCHPermutation(params)
    state = list(xs)

    def _reduce(expr):
        return Poly(expr, *xs, domain=F).as_expr()

    for rnd in perm.rounds:
        tri = rnd.triangular
        new_state = list(state)
        new_state[0] = state[0] + tri.offset
        for idx in range(1, n):
            poly = tri.polynomials[idx - 1]
            g_val = sympy.Integer(0)
            for coeff, exponents in zip(poly.coefficients, poly.monomials):
                if coeff == 0:
                    continue
                term = sympy.Integer(coeff)
                for var_idx, exp in enumerate(exponents):
                    if exp:
                        term = term * state[var_idx] ** exp
                g_val = g_val + term
            new_state[idx] = state[idx] + g_val
        state = new_state

        aff = rnd.affine
        new_state = []
        for row_idx in range(n):
            val = sympy.Integer(aff.bias[row_idx])
            for col_idx in range(n):
                val += sympy.Integer(aff.matrix[row_idx][col_idx]) * state[col_idx]
            new_state.append(val)
        state = new_state

        state = [_reduce(s) for s in state]

    poly_strs = [str(s) for s in state]
    return var_names, poly_strs


def _generate_target(params: SCHParams) -> list[int]:
    """Generate a known-input target for inversion experiments."""
    perm = SCHPermutation(params)
    field = field_from_params(params)
    test_input = [field.mod(i + 1) for i in range(params.n)]
    return perm.apply(test_input)


def export_sage(
    params: SCHParams,
    output_dir: Path,
    target: list[int] | None = None,
) -> Path:
    """Export polynomial system as a .sage file."""
    var_names, poly_strs = build_polynomial_strings(params)
    if target is None:
        target = _generate_target(params)

    n = params.n
    p = params.p
    filename = f"sch_{params.name}_n{n}_k{params.k}.sage"
    filepath = output_dir / filename

    lines = [
        f'"""SCH polynomial system: {params.name} (p={p}, n={n}, k={params.k}, d_tri={params.d_tri})"""',
        f"",
        f"p = {p}",
        f"n = {n}",
        f"k = {params.k}",
        f"d_tri = {params.d_tri}",
        f"",
        f"# Define polynomial ring over GF(p)",
        f"F = GF(p)",
        f'R = PolynomialRing(F, {n}, "{", ".join(var_names)}", order="degrevlex")',
        f"({', '.join(var_names)},) = R.gens()",
        f"",
        f"# Target output (for inversion experiment)",
        f"target = {target}",
        f"",
        f"# Permutation polynomials P_i(x)",
        f"P = [None] * {n}",
    ]

    for i, ps in enumerate(poly_strs):
        lines.append(f"P[{i}] = {ps}")

    lines.extend([
        f"",
        f"# System: P_i(x) - target_i = 0",
        f"system = [P[i] - F(target[i]) for i in range({n})]",
        f"",
        f"# Solve via Groebner basis",
        f"import time",
        f"print(f'Computing Groebner basis for {{params.name}} (n={{n}}, k={{k}}) over GF({{p}})...')",
        f"t0 = time.time()",
        f"I = R.ideal(system)",
        f"try:",
        f"    gb = I.groebner_basis()",
        f"    elapsed = time.time() - t0",
        f"    print(f'Solved in {{elapsed:.3f}}s')",
        f"    print(f'Basis size: {{len(gb)}}')",
        f"    print(f'Max degree: {{max(f.degree() for f in gb)}}')",
        f"    # Extract solution",
        f"    V = I.variety()",
        f"    if V:",
        f"        print(f'Solutions: {{V}}')",
        f"    else:",
        f"        print('No solutions found in variety')",
        f"except Exception as e:",
        f"    elapsed = time.time() - t0",
        f"    print(f'Failed after {{elapsed:.3f}}s: {{e}}')",
    ])

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return filepath


def export_magma(
    params: SCHParams,
    output_dir: Path,
    target: list[int] | None = None,
) -> Path:
    """Export polynomial system as a Magma script."""
    var_names, poly_strs = build_polynomial_strings(params)
    if target is None:
        target = _generate_target(params)

    n = params.n
    p = params.p
    filename = f"sch_{params.name}_n{n}_k{params.k}.magma"
    filepath = output_dir / filename

    lines = [
        f"// SCH polynomial system: {params.name} (p={p}, n={n}, k={params.k}, d_tri={params.d_tri})",
        f"",
        f"p := {p};",
        f"F := GF(p);",
        f'R<{", ".join(var_names)}> := PolynomialRing(F, {n}, "grevlex");',
        f"",
        f"// Target output",
        f"target := [{', '.join(str(t) for t in target)}];",
        f"",
        f"// Permutation polynomials",
    ]

    for i, ps in enumerate(poly_strs):
        # Convert Python ** to Magma ^
        magma_ps = ps.replace("**", "^")
        lines.append(f"P{i} := {magma_ps};")

    lines.extend([
        f"",
        f"// System: P_i - target_i",
        f"I := ideal<R |",
    ])
    for i in range(n):
        comma = "," if i < n - 1 else ""
        lines.append(f"    P{i} - F!target[{i+1}]{comma}")
    lines.append(">;")
    lines.extend([
        f"",
        f"// Compute Groebner basis using F4",
        f"time gb := GroebnerBasis(I);",
        f'printf "Basis size: %o\\n", #gb;',
        f'printf "Max degree: %o\\n", Max([TotalDegree(f) : f in gb]);',
        f"",
        f"// Try to extract variety",
        f"V := Variety(I);",
        f'printf "Solutions: %o\\n", V;',
    ])

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return filepath


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export SCH polynomial systems for external solvers"
    )
    parser.add_argument(
        "--format", choices=["sage", "magma", "both"], default="both",
        help="Output format (default: both)",
    )
    parser.add_argument(
        "--output-dir", type=str, default="exported_systems",
        help="Output directory for exported files",
    )
    parser.add_argument(
        "--params", nargs="+", default=["toy31"],
        help="Base parameter set name(s)",
    )
    parser.add_argument(
        "--n", nargs="+", type=int, default=None,
        help="Override state sizes to generate (creates reduced instances)",
    )
    parser.add_argument(
        "--k", nargs="+", type=int, default=None,
        help="Override round counts to generate",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for param_name in args.params:
        base_params = PARAMS[param_name]

        # Default grid: use parameter's own n and k values
        n_values = args.n or [base_params.n]
        k_values = args.k or list(range(1, min(base_params.k + 1, 4)))

        for n_val in n_values:
            for k_val in k_values:
                # Create a reduced-instance parameter set
                reduced = SCHParams(
                    name=f"{param_name}_n{n_val}_k{k_val}",
                    p=base_params.p,
                    n=n_val,
                    r=max(1, n_val - 1),
                    c=1,
                    k=k_val,
                    d_tri=base_params.d_tri,
                    seed=base_params.seed,
                    domain_tag=base_params.domain_tag,
                    digest_length=1,
                    shear_steps=base_params.shear_steps,
                )

                print(f"Exporting {reduced.name} (p={reduced.p}, n={n_val}, k={k_val})...")
                try:
                    if args.format in ("sage", "both"):
                        path = export_sage(reduced, output_dir)
                        print(f"  -> {path}")
                    if args.format in ("magma", "both"):
                        path = export_magma(reduced, output_dir)
                        print(f"  -> {path}")
                except Exception as e:
                    print(f"  ERROR: {e}")

    print(f"\nAll files written to {output_dir}/")
    print("To run in Sage:  sage exported_systems/sch_*.sage")
    print("To run in Magma: magma exported_systems/sch_*.magma")


if __name__ == "__main__":
    main()
