from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .params import get_params
from .sponge import sch_hash


def _load_message(args: argparse.Namespace) -> bytes:
    if args.file:
        return Path(args.file).read_bytes()
    if args.hex:
        return bytes.fromhex(args.hex)
    if args.text is not None:
        return args.text.encode("utf-8")
    return b""


def cmd_hash(args: argparse.Namespace) -> None:
    params = get_params(args.params)
    msg = _load_message(args)
    if args.out_bytes:
        digest = sch_hash(msg, params, out_bytes=args.out_bytes)
        print(digest.hex())
    else:
        elements = sch_hash(msg, params)
        print("[" + ", ".join(str(x) for x in elements) + "]")


def cmd_bench(args: argparse.Namespace) -> None:
    from scripts.bench import run_bench

    run_bench(args.params, args.size, args.iterations)


def cmd_plots(args: argparse.Namespace) -> None:
    from scripts.plots import run_plots

    run_plots(args.params, args.output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Symbolic Composition Hashing CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    parser_hash = sub.add_parser("hash", help="hash a message")
    parser_hash.add_argument("--params", default="sch128")
    parser_hash.add_argument("--text", help="interprets input as UTF-8 text")
    parser_hash.add_argument("--hex", help="hex-encoded input")
    parser_hash.add_argument("--file", help="path to binary file")
    parser_hash.add_argument("--out-bytes", type=int, help="number of digest bytes")
    parser_hash.set_defaults(func=cmd_hash)

    parser_bench = sub.add_parser("bench", help="benchmark hashing")
    parser_bench.add_argument("--params", default="sch128")
    parser_bench.add_argument("--size", type=int, default=1024, help="message size in bytes")
    parser_bench.add_argument("--iterations", type=int, default=100)
    parser_bench.set_defaults(func=cmd_bench)

    parser_plots = sub.add_parser("plots", help="generate analysis plots")
    parser_plots.add_argument("--params", default="sch128")
    parser_plots.add_argument("--output", default="plots")
    parser_plots.set_defaults(func=cmd_plots)

    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
