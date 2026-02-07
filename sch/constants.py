"""Deterministic constant generation based on SHAKE256."""

from __future__ import annotations

import hashlib
from typing import Iterable


def _int_to_bytes(value: int, length: int = 4) -> bytes:
    return value.to_bytes(length, "little")


class ConstantDeriver:
    """Deterministically derive bytes/field elements from a seed and labels."""

    def __init__(self, seed: bytes, params_name: str, version: str = "v1") -> None:
        self.seed = seed
        self.params_name = params_name.encode("utf-8")
        self.version = version.encode("ascii")

    def _domain_bytes(self, label: str, indices: Iterable[int]) -> bytes:
        prefix = b"|".join(
            [b"SCH", self.version, self.params_name, label.encode("ascii"), self.seed]
        )
        suffix = b"".join(_int_to_bytes(idx) for idx in indices)
        return prefix + b"|" + suffix

    def derive_bytes(self, label: str, indices: Iterable[int], length: int = 64) -> bytes:
        domain = self._domain_bytes(label, indices)
        return hashlib.shake_256(domain).digest(length)

    def derive_int(self, label: str, indices: Iterable[int], modulus: int) -> int:
        raw = self.derive_bytes(label, indices)
        return int.from_bytes(raw, "little") % modulus

    def derive_nonzero_field(self, label: str, indices: Iterable[int], modulus: int) -> int:
        value = 0
        counter = 0
        while value == 0:
            raw_idx = list(indices) + [counter]
            value = self.derive_int(label, raw_idx, modulus)
            counter += 1
        return value

    def derive_range(self, label: str, indices: Iterable[int], upper: int) -> int:
        if upper <= 0:
            raise ValueError("upper bound must be positive")
        raw = self.derive_bytes(label, indices)
        return int.from_bytes(raw, "little") % upper
