"""SCH permutation builder (Section 5.3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .affine import AffineLayer, generate_affine_layers
from .constants import ConstantDeriver
from .field import PrimeField, field_from_params
from .params import SCHParams
from .triangular import TriangularMap, generate_triangular_maps


@dataclass
class Round:
    triangular: TriangularMap
    affine: AffineLayer

    def apply(self, state: Sequence[int], field: PrimeField) -> List[int]:
        after_tri = self.triangular.apply(state, field)
        return self.affine.apply(after_tri, field)


class ToyPermutation:
    """Fixed small permutation used for Section 6 toy example."""

    def __init__(self, p: int) -> None:
        self.p = p

    def apply(self, state: Sequence[int]) -> List[int]:
        if len(state) != 3:
            raise ValueError("toy permutation expects n=3 state")
        x0, x1, x2 = state
        y0 = (x0 + 7) % self.p
        y1 = (x1 + x0 + x0 * x0 + 3) % self.p
        y2 = (x2 + x0 * x1 + 2 * x1 * x1 + 5) % self.p
        z0 = y0 % self.p
        z1 = (y1 + y0) % self.p
        z2 = (y2 + 2 * y1 + y0) % self.p
        return [z0, z1, z2]


class SCHPermutation:
    def __init__(self, params: SCHParams) -> None:
        self.params = params
        self.field = field_from_params(params)
        if params.toy:
            self._toy = ToyPermutation(params.p)
            self.rounds: list[Round] = []
        else:
            deriver = ConstantDeriver(params.seed, params.name)
            triangular_layers = generate_triangular_maps(params, self.field, deriver)
            affine_layers = generate_affine_layers(params, self.field, deriver)
            self.rounds = [Round(t, a) for t, a in zip(triangular_layers, affine_layers)]
            self._toy = None

    def apply(self, state: Sequence[int]) -> List[int]:
        if len(state) != self.params.n:
            raise ValueError("state length mismatch")
        if self.params.toy and self._toy:
            return self._toy.apply(state)
        output = list(state)
        for rnd in self.rounds:
            output = rnd.apply(output, self.field)
        return output

    __call__ = apply
