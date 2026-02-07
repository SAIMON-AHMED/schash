from __future__ import annotations

import secrets
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sch.encoding import compute_block_size
from sch.params import get_params
from sch.sponge import sch_hash


def run_bench(params_name: str, size: int, iterations: int) -> None:
    params = get_params(params_name)
    payload = secrets.token_bytes(size)
    start = time.perf_counter()
    digest_bytes = compute_block_size(params.p) * params.digest_length
    for idx in range(iterations):
        sch_hash(payload, params, out_bytes=digest_bytes)
        if len(payload) >= 2:
            prefix = (int.from_bytes(payload[:2], "little") + idx + 1) % (1 << 16)
            payload = prefix.to_bytes(2, "little") + payload[2:]
    elapsed = time.perf_counter() - start
    total_bytes = size * iterations
    rate = total_bytes / elapsed if elapsed else 0
    print(
        f"Params={params_name} | {iterations} iters of {size} bytes in {elapsed:.3f}s | "
        f"{rate/1e6:.2f} MB/s"
    )


if __name__ == "__main__":
    run_bench("sch128", 1024, 100)
