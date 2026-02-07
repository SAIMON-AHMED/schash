"""Affine layers for SCH permutation rounds."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .constants import ConstantDeriver
from .field import PrimeField
from .params import SCHParams


@dataclass
class AffineLayer:
    matrix: Sequence[Sequence[int]]
    bias: Sequence[int]

    def apply(self, state: Sequence[int], field: PrimeField) -> List[int]:
        if len(state) != len(self.matrix):
            raise ValueError("dimension mismatch for affine layer")
        output: List[int] = []
        for row, bias in zip(self.matrix, self.bias):
            accum = 0
            for coeff, value in zip(row, state):
                accum = field.add(accum, field.mul(coeff, value))
            output.append(field.add(accum, bias))
        return output


def _identity_matrix(n: int) -> List[List[int]]:
    return [[1 if i == j else 0 for j in range(n)] for i in range(n)]


def _row_shear(matrix: List[List[int]], field: PrimeField, u: int, v: int, coeff: int) -> None:
    row_u = matrix[u]
    row_v = matrix[v]
    for col in range(len(row_u)):
        row_u[col] = field.add(row_u[col], field.mul(coeff, row_v[col]))


def generate_affine_layers(
    params: SCHParams, field: PrimeField, deriver: ConstantDeriver
) -> List[AffineLayer]:
    layers: List[AffineLayer] = []
    shear_steps = params.shear_steps or (params.n * 3)
    for round_idx in range(params.k):
        matrix = _identity_matrix(params.n)
        for step in range(shear_steps):
            u = deriver.derive_range("M_shear_u", [round_idx, step], params.n)
            v = deriver.derive_range("M_shear_v", [round_idx, step], params.n)
            if u == v:
                v = (v + 1) % params.n
            coeff = deriver.derive_nonzero_field(
                "M_shear_coeff", [round_idx, step], field.p
            )
            _row_shear(matrix, field, u, v, coeff)
        bias = [
            deriver.derive_int("b_i", [round_idx, coord], field.p)
            for coord in range(params.n)
        ]
        layers.append(AffineLayer(matrix=matrix, bias=bias))
    return layers
