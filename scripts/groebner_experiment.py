#!/usr/bin/env python
"""Gröbner basis experiments on reduced SCH instances.

Uses SymPy to build the SCH permutation *symbolically* over F_p and then
attempts to invert it via Gröbner-basis computation.  This produces
real wall-clock timings and measured Gröbner-basis degrees that can be
compared against the heuristic D_reg estimates used in the paper.

Usage:
    python scripts/groebner_experiment.py
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sch.params import SCHParams, PARAMS
from sch.permutation import SCHPermutation
from sch.field import field_from_params
from sch.security_analysis import dreg_estimate

import sympy
from sympy import symbols, groebner, GF, Poly


# ── helpers ─────────────────────────────────────────────────────────────

@dataclass
class ExperimentResult:
    name: str
    p: int
    n: int
    k: int
    d_tri: int
    degree_actual: int          # max degree observed in Gröbner basis
    dreg_predicted: int         # heuristic D_reg from the formula
    solve_time_s: float         # wall-clock seconds
    solved: bool                # whether solver succeeded


def build_symbolic_permutation(params: SCHParams):
    """Build the SCH permutation as sympy expressions over GF(p).

    Expressions are reduced modulo p after each round using sympy Poly
    objects to prevent exponential coefficient/expression swell.  The
    returned expressions are ordinary sympy expressions (not Poly), ready
    to be handed to the Gröbner-basis solver.
    """
    perm = SCHPermutation(params)
    n = params.n
    p = params.p
    F = GF(p)

    xs = symbols([f"x{i}" for i in range(n)])
    state = list(xs)

    def _reduce_mod_p(expr):
        """Canonicalize *expr* modulo p via Poly arithmetic."""
        return Poly(expr, *xs, domain=F).as_expr()

    for rnd in perm.rounds:
        # Triangular layer
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
                    if exp == 0:
                        continue
                    term = term * state[var_idx] ** exp
                g_val = g_val + term
            new_state[idx] = state[idx] + g_val
        state = new_state

        # Affine layer
        aff = rnd.affine
        new_state = []
        for row_idx in range(n):
            val = sympy.Integer(aff.bias[row_idx])
            for col_idx in range(n):
                val = val + sympy.Integer(aff.matrix[row_idx][col_idx]) * state[col_idx]
            new_state.append(val)
        state = new_state

        # Reduce every component mod p to keep expressions compact
        state = [_reduce_mod_p(s) for s in state]

    return xs, state


def run_inversion_experiment(params: SCHParams) -> ExperimentResult:
    """Try to invert P on a random target using SymPy Gröbner basis over F_p."""
    n = params.n
    p = params.p
    d = params.d_tri ** params.k
    dreg_pred = dreg_estimate(n, d)

    # Build symbolic permutation
    xs, P_exprs = build_symbolic_permutation(params)

    # Pick a random target by evaluating P on a known input
    perm_num = SCHPermutation(params)
    field = field_from_params(params)
    test_input = [field.mod(i + 1) for i in range(n)]
    target = perm_num.apply(test_input)

    # System of equations: P_i(x) - target_i = 0 (mod p)
    F = GF(p)
    equations = [P_exprs[i] - target[i] for i in range(n)]

    # Attempt Gröbner basis computation
    t0 = time.time()
    solved = False
    max_gb_deg = 0
    try:
        gb = groebner(equations, *xs, order="grevlex", domain=F)
        elapsed = time.time() - t0
        solved = True
        # Measure the max degree of basis elements
        for poly in gb:
            try:
                max_gb_deg = max(max_gb_deg, Poly(poly, *xs).total_degree())
            except Exception:
                pass
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  Solver error: {e}")

    return ExperimentResult(
        name=params.name,
        p=p, n=n, k=params.k, d_tri=params.d_tri,
        degree_actual=max_gb_deg,
        dreg_predicted=dreg_pred,
        solve_time_s=elapsed,
        solved=solved,
    )


# ── experiment configurations ──────────────────────────────────────────

def experiment_toy31():
    """Run on the toy31 parameters (p=31, n=3) with varying k."""
    print("\n" + "=" * 72)
    print("Experiment 1: toy-sized field (p=31, n=3, d_tri=3) varying k")
    print("=" * 72)

    results = []
    for k in range(1, 7):
        params = SCHParams(
            name=f"toy_k{k}", p=31, n=3, r=2, c=1, k=k, d_tri=3,
            seed=b"groebner-experiment", shear_steps=9, toy=False,
        )
        print(f"\n  k={k}, expected degree d={3**k}, D_reg(pred)={dreg_estimate(3, 3**k)} ...")
        result = run_inversion_experiment(params)
        results.append(result)
        print(f"    solved={result.solved}  time={result.solve_time_s:.3f}s  "
              f"GB_max_deg={result.degree_actual}  D_reg(pred)={result.dreg_predicted}")
        if result.solve_time_s > 300:
            print("    Stopping: exceeded 5 min threshold.")
            break
    return results


def experiment_reduced_sch128():
    """Run on reduced instances of sch128 parameters (p=127, n=4-6, k=1-3)."""
    print("\n" + "=" * 72)
    print("Experiment 2: reduced sch128 instances (p=127, d_tri=3)")
    print("=" * 72)

    base = PARAMS["sch128"]
    results = []
    for n in [3, 4, 5]:
        for k in [1, 2, 3]:
            params = SCHParams(
                name=f"red128_n{n}_k{k}", p=127, n=n,
                r=max(n - 1, 1), c=1, k=k, d_tri=3,
                seed=b"groebner-reduced", shear_steps=n * 3, toy=False,
            )
            deg = 3 ** k
            print(f"\n  n={n}, k={k}, d={deg}, D_reg(pred)={dreg_estimate(n, deg)} ...")
            result = run_inversion_experiment(params)
            results.append(result)
            print(f"    solved={result.solved}  time={result.solve_time_s:.3f}s  "
                  f"GB_max_deg={result.degree_actual}  D_reg(pred)={result.dreg_predicted}")
            if result.solve_time_s > 300:
                print("    Stopping: exceeded 5 min threshold for this n.")
                break
    return results


def print_latex_table(results: List[ExperimentResult]):
    """Print a LaTeX table of experiment results."""
    print("\n" + "=" * 72)
    print("LaTeX table for paper")
    print("=" * 72)
    print(r"\begin{table}[H]")
    print(r"\centering")
    print(r"\caption{Gr\"obner basis experiments on reduced SCH instances.}")
    print(r"\label{tab:groebner}")
    print(r"\begin{tabular}{@{}lccccrrr@{}}")
    print(r"\toprule")
    print(r"Instance & $p$ & $n$ & $k$ & $d = d_{\mathrm{tri}}^k$ & "
          r"$D_{\mathrm{reg}}$ (pred.) & GB max deg. & Time (s) \\")
    print(r"\midrule")
    for r in results:
        if r.solved:
            deg = r.d_tri ** r.k
            print(f"{r.name} & {r.p} & {r.n} & {r.k} & {deg} & "
                  f"{r.dreg_predicted} & {r.degree_actual} & {r.solve_time_s:.3f} \\\\")
        else:
            deg = r.d_tri ** r.k
            print(f"{r.name} & {r.p} & {r.n} & {r.k} & {deg} & "
                  f"{r.dreg_predicted} & --- & timeout \\\\")
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\vspace{0.5em}")
    print(r"\begin{minipage}{0.95\linewidth}")
    print(r"\small")
    print(r"\textbf{Notes.} Predicted $D_{\mathrm{reg}}$ uses the semi-regular bound "
          r"$\lfloor n(d-1)/2 \rfloor + 1$.")
    print(r"``GB max deg.'' is the maximum total degree among Gr\"obner basis elements.")
    print(r"Experiments used SymPy's \texttt{groebner} over $\mathrm{GF}(p)$ with "
          r"\texttt{grevlex} ordering.")
    print(r"\end{minipage}")
    print(r"\end{table}")


if __name__ == "__main__":
    all_results: List[ExperimentResult] = []
    all_results.extend(experiment_toy31())
    all_results.extend(experiment_reduced_sch128())
    print_latex_table([r for r in all_results if r.solved])

    print("\n" + "=" * 72)
    print("Summary")
    print("=" * 72)
    solved = sum(1 for r in all_results if r.solved)
    total = len(all_results)
    print(f"Solved: {solved}/{total}")
    for r in all_results:
        if r.solved:
            deg = r.d_tri ** r.k
            ratio = r.degree_actual / r.dreg_predicted if r.dreg_predicted > 0 else 0
            print(f"  {r.name}: GB_deg={r.degree_actual}, D_reg_pred={r.dreg_predicted}, "
                  f"ratio={ratio:.2f}, time={r.solve_time_s:.3f}s")
