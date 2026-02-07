from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.params import get_params
from sch.sponge import sch_hash


def deterministic_bytes(length: int) -> bytes:
    seed = hashlib.sha256(b"sch-test-seed").digest()
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(seed + counter.to_bytes(4, "little")).digest())
        counter += 1
    return bytes(out[:length])


def dump_vectors() -> Dict[str, Dict[str, list[int]]]:
    messages = {
        "empty": b"",
        "abc": b"abc",
        "rand1k": deterministic_bytes(1024),
    }
    results: Dict[str, Dict[str, list[int]]] = {}
    for params_name in ["sch128"]:
        params = get_params(params_name)
        per_param: Dict[str, list[int]] = {}
        for label, msg in messages.items():
            per_param[label] = sch_hash(msg, params)
        results[params_name] = per_param
    return results


def main() -> None:
    vectors = dump_vectors()
    out_path = Path("tests/test_vectors_generated.json")
    out_path.write_text(json.dumps(vectors, indent=2))
    print(f"Vectors written to {out_path}")


if __name__ == "__main__":
    main()
