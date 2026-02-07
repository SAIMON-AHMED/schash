"""Sponge construction for Symbolic Composition Hashing."""

from __future__ import annotations

from typing import List, Sequence

from .encoding import (
    compute_block_size,
    pack_message,
    pack_tag,
    serialize_elements,
)
from .field import PrimeField, field_from_params
from .params import SCHParams
from .permutation import SCHPermutation


class SCHSponge:
    def __init__(self, params: SCHParams) -> None:
        self.params = params
        self.field = field_from_params(params)
        self.permutation = SCHPermutation(params)
        self.block_size = compute_block_size(params.p)
        self.state = self._initial_state()

    def _initial_state(self) -> List[int]:
        tag_element = pack_tag(self.params.domain_tag, self.block_size) % self.field.p
        state = [0] * self.params.n
        state[0] = tag_element
        return state

    def reset(self) -> None:
        self.state = self._initial_state()

    def absorb_elements(self, elements: Sequence[int]) -> None:
        for alpha in elements:
            self.state[0] = self.field.add(self.state[0], alpha % self.field.p)
            self.state = self.permutation.apply(self.state)

    def squeeze_elements(self, count: int) -> List[int]:
        outputs: List[int] = []
        for idx in range(count):
            outputs.append(self.state[0])
            if idx + 1 < count:
                self.state = self.permutation.apply(self.state)
        return outputs


def sch_hash(
    message: bytes,
    params: SCHParams,
    out_elements: int | None = None,
    out_bytes: int | None = None,
) -> bytes | List[int]:
    sponge = SCHSponge(params)
    block_size, packed = pack_message(message, params.p)
    if block_size != sponge.block_size:
        raise RuntimeError("block size mismatch between sponge and encoder")
    sponge.absorb_elements(packed)
    elements = sponge.squeeze_elements(out_elements or params.digest_length)
    if out_bytes is None:
        return elements
    return serialize_elements(elements, sponge.block_size, out_bytes)
