from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.params import get_params, PARAMS
from sch.sponge import sch_hash


def deterministic_bytes(length: int) -> bytes:
    seed = hashlib.sha256(b"sch-test-seed").digest()
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(seed + counter.to_bytes(4, "little")).digest())
        counter += 1
    return bytes(out[:length])


MESSAGES = {
    "empty": b"",
    "abc": b"abc",
    "hello_world": b"Hello, World!",
    "zeros_64": b"\x00" * 64,
    "ones_256": b"\xff" * 256,
    "rand1k": deterministic_bytes(1024),
    "rand4k": deterministic_bytes(4096),
}


def dump_vectors() -> Dict[str, Dict[str, list[int]]]:
    results: Dict[str, Dict[str, list[int]]] = {}
    for params_name, params in PARAMS.items():
        if params.toy:
            continue
        print(f"  Generating vectors for {params_name}...")
        per_param: Dict[str, list[int]] = {}
        for label, msg in MESSAGES.items():
            per_param[label] = sch_hash(msg, params)
        results[params_name] = per_param
    return results


def main() -> None:
    print("Generating test vectors for all parameter sets...")
    vectors = dump_vectors()
    out_path = ROOT / "tests" / "test_vectors_generated.json"
    out_path.write_text(json.dumps(vectors, indent=2))
    print(f"Vectors written to {out_path}")
    print(f"Parameter sets: {list(vectors.keys())}")
    for name, vecs in vectors.items():
        print(f"  {name}: {len(vecs)} messages")


if __name__ == "__main__":
    main()
