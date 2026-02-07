"""Parameter definitions for Symbolic Composition Hashing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class SCHParams:
    name: str
    p: int
    n: int
    r: int
    c: int
    k: int
    d_tri: int
    seed: bytes
    domain_tag: str = "SCH"
    digest_length: int = 4
    shear_steps: int | None = None
    toy: bool = False

    def __post_init__(self) -> None:
        if self.r + self.c != self.n:
            raise ValueError("state size must equal rate + capacity")
        if self.p <= self.n:
            raise ValueError("prime must exceed state size for practical security")


PARAMS: Dict[str, SCHParams] = {
    "toy31": SCHParams(
        name="toy31",
        p=31,
        n=3,
        r=2,
        c=1,
        k=3,
        d_tri=3,
        seed=b"toy-example",
        digest_length=2,
        toy=True,
    ),
    "sch128": SCHParams(
        name="sch128",
        p=(1 << 127) - 1,
        n=12,
        r=8,
        c=4,
        k=7,
        d_tri=3,
        seed=b"table1-sch128",
        shear_steps=36,
        digest_length=4,
    ),
    "sch192": SCHParams(
        name="sch192",
        p=(1 << 191) - 1,
        n=16,
        r=10,
        c=6,
        k=9,
        d_tri=3,
        seed=b"table1-sch192",
        shear_steps=48,
        digest_length=6,
    ),
    "sch256": SCHParams(
        name="sch256",
        p=2 ** 255 - 19,
        n=20,
        r=12,
        c=8,
        k=11,
        d_tri=4,
        seed=b"table1-sch256",
        shear_steps=60,
        digest_length=8,
    ),
}


def get_params(name: str) -> SCHParams:
    try:
        return PARAMS[name]
    except KeyError as exc:
        raise KeyError(f"unknown SCH parameter set '{name}'") from exc
