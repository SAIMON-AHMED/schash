"""Encoding, padding, and serialization utilities (Section 5.2)."""

from __future__ import annotations

from typing import Iterable, List


def compute_block_size(p: int) -> int:
    """Largest B such that 256**B <= p-1."""

    if p <= 2:
        raise ValueError("prime must exceed 2 for meaningful encoding")
    block = 0
    while pow(256, block + 1) <= p - 1:
        block += 1
    if block == 0:
        raise ValueError("prime too small for byte-oriented packing")
    return block


def pad10star(message: bytes, block_size: int) -> bytes:
    """Apply 10* padding so that len(padded) is a multiple of block_size."""

    padding = bytearray(message)
    padding.append(0x80)
    while len(padding) % block_size != 0:
        padding.append(0x00)
    return bytes(padding)


def partition_blocks(padded: bytes, block_size: int) -> List[bytes]:
    if len(padded) % block_size != 0:
        raise ValueError("padded message length must be a multiple of block size")
    return [padded[i : i + block_size] for i in range(0, len(padded), block_size)]


def pack_block(block: bytes) -> int:
    acc = 0
    for idx, byte in enumerate(block):
        acc += byte << (8 * idx)
    return acc


def pack_blocks(blocks: Iterable[bytes]) -> List[int]:
    return [pack_block(block) for block in blocks]


def pack_message(message: bytes, p: int) -> tuple[int, List[int]]:
    block_size = compute_block_size(p)
    padded = pad10star(message, block_size)
    blocks = partition_blocks(padded, block_size)
    return block_size, pack_blocks(blocks)


def pack_tag(tag: str, block_size: int) -> int:
    raw = tag.encode("ascii")
    if len(raw) > block_size:
        raw = raw[:block_size]
    if len(raw) < block_size:
        raw = raw + b"\x00" * (block_size - len(raw))
    return pack_block(raw)


def serialize_field_element(value: int, block_size: int) -> bytes:
    if value < 0:
        raise ValueError("field elements must be non-negative")
    max_range = 1 << (8 * block_size)
    return (value % max_range).to_bytes(block_size, "little")


def serialize_elements(elements: Iterable[int], block_size: int, byte_length: int | None = None) -> bytes:
    chunks = b"".join(serialize_field_element(el, block_size) for el in elements)
    if byte_length is None:
        return chunks
    return chunks[:byte_length]
