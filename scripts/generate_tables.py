#!/usr/bin/env python
"""Generate reproducible LaTeX tables for the paper from code.

Every number printed here should appear verbatim in main.tex so that
tables are always consistent with the implementation.
"""

from __future__ import annotations

import math
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sch.params import PARAMS
from sch.security_analysis import (
    estimate_security_level,
    estimated_degree,
    interpolation_log2_complexity,
    groebner_log2_complexity,
)


# ── Table 2: Security analysis ──────────────────────────────────────────

def table_security() -> str:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Security analysis for SCH parameter sets.}",
        r"\label{tab:security}",
        r"\begin{tabular}{@{}lrrrr@{}}",
        r"\toprule",
        r"Parameter & Collision & Preimage & Interpolation & Gr\"obner \\",
        r"Set & (bits) & (bits) & Attack (bits) & Attack (bits) \\",
        r"\midrule",
    ]
    for name in ["sch128", "sch192", "sch256"]:
        est = estimate_security_level(PARAMS[name])
        lines.append(
            f"{name} & {est.collision_bits:.0f} & {est.preimage_bits:.0f} "
            f"& {est.interpolation_complexity:.0f} & {est.groebner_complexity:.0f} \\\\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\vspace{0.5em}",
        r"\begin{minipage}{0.95\linewidth}",
        r"\small",
        r"\textbf{Notes.} Collision and preimage bounds follow standard sponge-capacity arguments.",
        r"Interpolation complexity equals $\omega \cdot \log_2 \binom{n+d}{d}$ where $d = d_{\mathrm{tri}}^k$",
        r"and $\omega = 2.8$ (practical linear-algebra exponent).",
        r"Gr\"obner complexity uses the semi-regular degree-of-regularity bound",
        r"$D_{\mathrm{reg}} = \lfloor n(d-1)/2 \rfloor + 1$ from Bardet et al.\ \cite{Bardet2005},",
        r"with complexity $\omega \cdot \log_2 \binom{n+D_{\mathrm{reg}}}{D_{\mathrm{reg}}}$.",
        r"All estimates are capped at exhaustive search ($n \cdot \log_2 p$).",
        r"\end{minipage}",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ── Table 3: Reduced-round attacks ──────────────────────────────────────

def table_attacks() -> str:
    p = PARAMS["sch128"]
    round_list = sorted(set([1, 2, 3, p.k // 2, p.k]))
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Attack complexity estimates for reduced-round SCH-128.}",
        r"\label{tab:attacks}",
        r"\begin{tabular}{@{}lccl@{}}",
        r"\toprule",
        r"Rounds & Interpolation & Gr\"obner & Status \\",
        r"\midrule",
    ]
    coll_bits = (p.c * math.log2(p.p)) / 2
    for k in round_list:
        deg = estimated_degree(p.d_tri, k, p.p)
        interp = int(interpolation_log2_complexity(p.n, deg, p.p))
        grob = int(groebner_log2_complexity(p.n, deg, p.p))
        label = f"{k}/{p.k}" if k < p.k else f"{k}/{p.k} (Full)"
        status = "Feasible" if interp < 64 else "Infeasible"
        lines.append(f"{label} & $2^{{{interp}}}$ & $2^{{{grob}}}$ & {status} \\\\")
    lines += [
        r"\addlinespace",
        f"Upper Bound & \\multicolumn{{2}}{{c}}{{$2^{{{int(coll_bits)}}}$ (collision)}} & Generic \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\vspace{0.5em}",
        r"\begin{minipage}{0.95\linewidth}",
        r"\small",
        r"\textbf{Notes.} Both interpolation and Gr\"obner estimates use the same",
        r"formulas as Table~\ref{tab:security}. At 1--2 rounds, interpolation is",
        r"feasible ($< 2^{64}$); by 3 rounds both attacks exceed practical thresholds.",
        r"\end{minipage}",
        r"\end{table}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    print("=" * 72)
    print("TABLE 2 — Security analysis")
    print("=" * 72)
    print(table_security())
    print()
    print("=" * 72)
    print("TABLE 3 — Reduced-round attacks on SCH-128")
    print("=" * 72)
    print(table_attacks())
