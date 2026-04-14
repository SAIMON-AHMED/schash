"""Finite field helpers for prime fields F_p."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PrimeField:
    """Simple prime field wrapper that exposes common operations modulo p."""

    p: int

    def mod(self, x: int) -> int:
        return x % self.p

    def add(self, a: int, b: int) -> int:
        return (a + b) % self.p

    def sub(self, a: int, b: int) -> int:
        return (a - b) % self.p

    def mul(self, a: int, b: int) -> int:
        return (a * b) % self.p

    def neg(self, a: int) -> int:
        return (-a) % self.p

    def pow(self, base: int, exponent: int) -> int:
        return pow(base % self.p, exponent, self.p)

    def inv(self, a: int) -> int:
        a = a % self.p
        if a == 0:
            raise ZeroDivisionError("cannot invert zero in a field")
        return pow(a, self.p - 2, self.p)

    def scalar_vector_mul(self, scalar: int, vector: list[int]) -> list[int]:
        return [self.mul(scalar, v) for v in vector]

    def dot(self, a: list[int], b: list[int]) -> int:
        if len(a) != len(b):
            raise ValueError("dot product dimension mismatch")
        acc = 0
        for x, y in zip(a, b):
            acc = (acc + x * y) % self.p
        return acc


def field_from_params(params: "SCHParams") -> PrimeField:
    """Helper to construct a PrimeField from a parameter object."""

    return PrimeField(params.p)


def modular_det(matrix: list[list[int]], p: int) -> int:
    """Compute the determinant of a square integer matrix modulo prime *p*."""
    size = len(matrix)
    work = [[entry % p for entry in row] for row in matrix]
    det = 1
    for pivot_idx in range(size):
        pivot_row = None
        for row_idx in range(pivot_idx, size):
            if work[row_idx][pivot_idx] % p:
                pivot_row = row_idx
                break
        if pivot_row is None:
            return 0
        if pivot_row != pivot_idx:
            work[pivot_idx], work[pivot_row] = work[pivot_row], work[pivot_idx]
            det = (-det) % p
        pivot_val = work[pivot_idx][pivot_idx] % p
        det = (det * pivot_val) % p
        inv_pivot = pow(pivot_val, -1, p)
        for col_idx in range(pivot_idx, size):
            work[pivot_idx][col_idx] = (work[pivot_idx][col_idx] * inv_pivot) % p
        for row_idx in range(pivot_idx + 1, size):
            factor = work[row_idx][pivot_idx]
            if factor == 0:
                continue
            for col_idx in range(pivot_idx, size):
                work[row_idx][col_idx] = (
                    work[row_idx][col_idx] - factor * work[pivot_idx][col_idx]
                ) % p
    return det % p
