# Symbolic Composition Hashing (SCH)

Reference Python implementation of Symbolic Composition Hashing over prime fields \(\mathbb{F}\_p\), following the specification from the "Symbolic Composition Hashing" paper. The code is deterministic, reproducible, and keeps every constant derivation tied to a public seed via SHAKE256.

## Project layout

```
sch/
  field.py          # modular arithmetic helpers
  encoding.py       # Section 5.2 encoding + padding + packing
  triangular.py     # lower unitriangular maps T_i
  affine.py         # determinant-1 affine layers A_i
  permutation.py    # round composition P = f_k ⚬ ... ⚬ f_1
  sponge.py         # sponge absorb/squeeze logic
  params.py         # published parameter sets + toy example
  __main__.py       # CLI (`python -m sch ...`)
scripts/
  bench.py          # throughput benchmark numbers from paper abstract
  plots.py          # reproduces Figure 1 (degree growth) & Figure 2 (diffusion)
  gen_vectors.py    # helper to regenerate deterministic test vectors
tests/
  test_vectors.py   # pytest regression suite (vectors + invariants)
```

## Finite field arithmetic

`sch/field.py` exposes a light `PrimeField` helper with `mod`, `add`, `sub`, `mul`, `pow`, `inv`, and `neg`. All state values are plain Python integers reduced modulo `p`. Modules accept a `PrimeField` instance so every operation is explicit and deterministic.

## Encoding, padding, and packing (Section 5.2)

- `compute_block_size(p)` finds the largest block size `B` with `256**B <= p-1`.
- Messages are padded with the `10*` rule so their length is a multiple of `B` bytes.
- Blocks are packed little-endian into field elements without modular reduction because `256**B <= p-1`.
- Domain separation tag (default `"SCH"`) is packed once into `s[0]` before absorbing message data.

For extremely small toy primes (e.g., `p=31`) `B=0`, so the toy parameter set is only used for the algebraic permutation tests rather than hashing real messages.

## Permutation (Section 5.3)

Each round `f_i = A_i ⚬ T_i` consists of:

1. `T_i`: a lower unitriangular map with constant offset `c_i` and polynomials `g_{i,j}` built over a canonical total-degree/lexicographic monomial basis. Coefficients are sampled deterministically via SHAKE256 from the public seed.
2. `A_i`: an affine layer `M_i x + b_i` where `M_i` is assembled from shear matrices so `det(M_i)=1`. Bias vectors `b_i` again come from SHAKE256.

`sch/permutation.py` also embeds the Section 6 toy permutation (prime `p=31`, `n=3`) with explicit polynomials so bijectivity proofs can be run independently from the sponge code.

## Sponge hashing interface

`sch/sponge.py` implements the absorb/squeeze rules exactly as in Section 5.2:

- Absorb: add each packed element into `s[0]`, then apply `P`.
- Squeeze: output `s[0]`, applying `P` between outputs.
- Optional byte digests come from serialising field outputs into `B` little-endian bytes.

Use it directly via `sch.sponge.sch_hash(message, params, out_elements=None, out_bytes=None)`.

## Deterministic constants (SHAKE256)

`sch/constants.py` wraps SHAKE256 as a per-parameter expand function. Every constant incorporates the paper version, parameter-set name, label, and indices, keeping the implementation reproducible without hidden randomness.

## Parameter sets

`sch/params.py` defines:

- `toy31`: Section 6 toy example (`p=31`, `n=3`) with a fixed hand-crafted permutation for brute-force invariants.
- `sch128`, `sch192`, `sch256`: illustrative Table 1-style parameter sets covering different security targets. Each stores `(p, n, r, c, k, d_tri, seed, digest_length, shear_steps)`.

Extend `PARAMS` with new seeds or rates and they propagate everywhere deterministically.

## Command-line usage

```bash
python -m sch hash --params sch128 --text "hello world" --out-bytes 64
python -m sch bench --params sch128 --size 4096 --iterations 50
python -m sch plots --params sch128 --output out_plots/
```

- `hash`: accepts UTF-8 text (`--text`), hex (`--hex`), or binary files (`--file`).
- `bench`: measures throughput for the requested parameter set.
- `plots`: generates Figure 1 (degree growth) and Figure 2 (diffusion). Requires `matplotlib`.

## Benchmarks & plots

Install the minimal optional dependencies:

```bash
python -m pip install matplotlib pytest
```

Then reproduce the paper-style artefacts:

```bash
python scripts/bench.py                # same as `python -m sch bench`
python scripts/plots.py --params sch128 --output plots/
```

`plots.py` tracks algebraic degree through actual sampled rounds and runs an avalanche experiment (flip one input bit, measure differing digest bits) to approximate the diffusion curve.

## Tests & reproducibility

1. Install pytest if needed: `python -m pip install pytest`.
2. Run `pytest` from the repository root.

The suite covers:

- Deterministic vectors for `sch128` (`m = empty`, `m = "abc"`, `m = 1 KiB` pseudo-random).
- Brute-force bijectivity of the toy permutation (`31^3` states).
- Explicit Jacobian determinant checks for the toy permutation.
- Determinant-one validation for every affine layer in `sch128`.

To regenerate the stored vectors after any intentional change:

```bash
python scripts/gen_vectors.py
cat tests/test_vectors_generated.json   # copy numbers into tests if they change
```

## Notes & limitations

- This reference code is **not** constant-time and is intended for research/validation, not deployment.
- Triangular polynomials are dense up to `d_tri`; to tweak algebraic degree growth, change `d_tri` or the seeds in `params.py`.
- The toy permutation deliberately avoids the byte sponge due to `p < 256`, but it remains invaluable for algebraic sanity checks and educational purposes.

Enjoy experimenting with Symbolic Composition Hashing!
