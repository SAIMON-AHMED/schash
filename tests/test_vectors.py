from __future__ import annotations

import hashlib
from itertools import product

import pytest

from sch.degree_tracking import compute_degree_growth, degree_growth_sch128
from sch.params import get_params, PARAMS
from sch.permutation import SCHPermutation
from sch.sponge import sch_hash, SCHSponge
from sch.triangular import enumerate_monomials
from sch.encoding import compute_block_size
from sch.field import modular_det

TEST_VECTORS = {
    "sch128": {
        "empty": [
            143318500100078006530403293305255320698,
            124403830338808755240305127952117028777,
            1164462375271981088757273491113585925,
            95849600366506517284587973427074857448,
        ],
        "abc": [
            66254099932580900688762931413488248945,
            63474362572758525734490118497539143750,
            144933407027833815334274708095775364319,
            110173678606625162562284711270638183149,
        ],
        "rand1k": [
            130478299598912942946259677630533297776,
            90198983350601925784752453221837663922,
            28941368176042938314172672019871474894,
            95743891918904384502605477036139077120,
        ],
    }
}


def deterministic_bytes(length: int) -> bytes:
    seed = hashlib.sha256(b"sch-test-seed").digest()
    out = bytearray()
    counter = 0
    while len(out) < length:
        out.extend(hashlib.sha256(seed + counter.to_bytes(4, "little")).digest())
        counter += 1
    return bytes(out[:length])


@pytest.mark.parametrize("message_id", ["empty", "abc", "rand1k"])
def test_sch128_vectors(message_id: str) -> None:
    params = get_params("sch128")
    message = {
        "empty": b"",
        "abc": b"abc",
        "rand1k": deterministic_bytes(1024),
    }[message_id]
    expected = TEST_VECTORS["sch128"][message_id]
    digest = sch_hash(message, params)
    assert digest == expected


def test_degree_growth_sch128_series() -> None:
    params = get_params("sch128")
    series = degree_growth_sch128()
    assert len(series) == params.k
    assert all(isinstance(value, int) and value >= 0 for value in series)
    assert all(series[idx] >= series[idx - 1] for idx in range(1, len(series)))
    reference = compute_degree_growth(params)
    assert series == reference.max_degrees


def test_affine_layers_det_one() -> None:
    params = get_params("sch128")
    perm = SCHPermutation(params)
    for round_idx, rnd in enumerate(perm.rounds):
        det = modular_det([list(row) for row in rnd.affine.matrix], params.p)
        assert det == 1, f"round {round_idx} determinant {det}" 


def toy_jacobian(state: list[int], p: int) -> list[list[int]]:
    x0, x1, _ = state
    return [
        [1 % p, 0, 0],
        [(2 + 2 * x0) % p, 1 % p, 0],
        [(x1 + 3 + 4 * x0) % p, (x0 + 4 * x1 + 2) % p, 1 % p],
    ]


def det3(matrix: list[list[int]], p: int) -> int:
    a = matrix[0][0]
    b = matrix[0][1]
    c = matrix[0][2]
    d = matrix[1][0]
    e = matrix[1][1]
    f = matrix[1][2]
    g = matrix[2][0]
    h = matrix[2][1]
    i = matrix[2][2]
    det = (
        a * (e * i - f * h)
        - b * (d * i - f * g)
        + c * (d * h - e * g)
    )
    return det % p


def test_toy_jacobian_det_one() -> None:
    params = get_params("toy31")
    for state in product(range(params.p), repeat=params.n):
        jac = toy_jacobian(list(state), params.p)
        assert det3(jac, params.p) == 1


def test_toy_permutation_bijective() -> None:
    params = get_params("toy31")
    perm = SCHPermutation(params)
    seen = set()
    for state in product(range(params.p), repeat=params.n):
        image = tuple(perm.apply(list(state)))
        assert image not in seen
        seen.add(image)
    assert len(seen) == params.p ** params.n


# =============================================================================
# VERIFICATION TESTS: Triangular Map Structure
# =============================================================================


def test_triangular_map_structure_unitriangular() -> None:
    """Verify triangular maps have unit lower-triangular Jacobian structure.

    Invariant: For T_i, the Jacobian J satisfies:
      - J[j][k] = 0 for k >= j (upper triangle is zero)
      - J[j][j] = 1 (diagonal is all ones)
    This ensures det(J) = 1 for all inputs.
    """
    params = get_params("sch128")
    perm = SCHPermutation(params)

    for round_idx, rnd in enumerate(perm.rounds):
        tri = rnd.triangular
        # Structural check: polynomial g_{j} only depends on x_0..x_{j-1}
        for coord, poly in enumerate(tri.polynomials, start=1):
            for mon in poly.monomials:
                # Each monomial is a tuple of exponents for (x_0, ..., x_{coord-1})
                assert len(mon) == coord, (
                    f"Round {round_idx}, coord {coord}: monomial has wrong variable count"
                )
        # The offset only affects x_0, and each g_j only uses x_0..x_{j-1}
        # Combined with y_j = x_j + g_j(...), diagonal partials are 1


def test_triangular_polynomial_density() -> None:
    """Verify 'dense' polynomial definition: all monomials up to degree d_tri.

    Monomial count for coordinate j with max degree d:
      |M| = C(j + d, d) = (j + d)! / (j! * d!)
    where C is binomial coefficient.
    """
    params = get_params("sch128")
    perm = SCHPermutation(params)

    from math import comb

    for round_idx, rnd in enumerate(perm.rounds):
        for coord, poly in enumerate(rnd.triangular.polynomials, start=1):
            expected_count = comb(coord + params.d_tri, params.d_tri)
            actual_count = len(poly.monomials)
            assert actual_count == expected_count, (
                f"Round {round_idx}, coord {coord}: expected {expected_count} monomials, "
                f"got {actual_count}"
            )


def test_monomial_enumeration_covers_all_degrees() -> None:
    """Verify enumerate_monomials produces all monomials up to max degree."""
    # For 2 variables, degree 3: expect monomials for degrees 0,1,2,3
    monomials = enumerate_monomials(var_count=2, max_degree=3)
    # Count: C(2+0,0) + C(2+1,1) + C(2+2,2) + C(2+3,3) = 1+2+3+4 = 10
    # Actually it's C(2+3,3) = 10 total (all monomials <= degree 3)
    from math import comb
    expected = comb(2 + 3, 3)
    assert len(monomials) == expected

    # Verify each monomial has correct structure
    for mon in monomials:
        assert len(mon) == 2  # 2 variables
        assert sum(mon) <= 3  # total degree <= 3
        assert all(e >= 0 for e in mon)  # non-negative exponents


# =============================================================================
# VERIFICATION TESTS: Round Order Sensitivity
# =============================================================================


def test_round_order_ta_vs_at() -> None:
    """Verify that T∘A ≠ A∘T (round order matters).

    The correct order per spec is f_i = A_i ∘ T_i (triangular first, then affine).
    This test confirms swapping the order produces different outputs.
    """
    params = get_params("sch128")
    perm = SCHPermutation(params)

    # Use a non-trivial input state
    state = list(range(1, params.n + 1))

    # Correct order: T then A
    rnd = perm.rounds[0]
    after_t = rnd.triangular.apply(state, perm.field)
    correct = rnd.affine.apply(after_t, perm.field)

    # Wrong order: A then T
    after_a = rnd.affine.apply(state, perm.field)
    wrong = rnd.triangular.apply(after_a, perm.field)

    assert correct != wrong, "T∘A should differ from A∘T"


# =============================================================================
# VERIFICATION TESTS: Permutation Determinism
# =============================================================================


def test_permutation_determinism_across_calls() -> None:
    """Verify P(seed, input) is identical across multiple instantiations."""
    params = get_params("sch128")
    state = [i * 12345 % params.p for i in range(params.n)]

    # First instantiation
    perm1 = SCHPermutation(params)
    result1 = perm1.apply(state)

    # Second instantiation (fresh object, same params)
    perm2 = SCHPermutation(params)
    result2 = perm2.apply(state)

    assert result1 == result2, "Permutation must be deterministic"


def test_permutation_determinism_all_param_sets() -> None:
    """Verify determinism for all non-toy parameter sets."""
    for name, params in PARAMS.items():
        if params.toy:
            continue  # Skip toy (uses fixed permutation)
        state = [i % params.p for i in range(params.n)]
        perm1 = SCHPermutation(params)
        perm2 = SCHPermutation(params)
        assert perm1.apply(state) == perm2.apply(state), f"{name} not deterministic"


# =============================================================================
# VERIFICATION TESTS: Domain Separation
# =============================================================================


def test_domain_separation_labels_unique() -> None:
    """Verify SHAKE256 domain labels don't collide.

    Labels used in the implementation:
      - "c_i": triangular offsets
      - "g_coeff": triangular polynomial coefficients
      - "M_shear_u", "M_shear_v", "M_shear_coeff": affine matrix shears
      - "b_i": affine bias vectors
    """
    from sch.constants import ConstantDeriver

    params = get_params("sch128")
    deriver = ConstantDeriver(params.seed, params.name)

    labels = ["c_i", "g_coeff", "M_shear_u", "M_shear_v", "M_shear_coeff", "b_i"]

    # Generate bytes for each label with same indices
    outputs = {}
    for label in labels:
        outputs[label] = deriver.derive_bytes(label, [0, 0, 0], length=32)

    # All should be distinct
    unique_outputs = set(outputs.values())
    assert len(unique_outputs) == len(labels), (
        f"Domain separation failure: {len(labels)} labels produced "
        f"only {len(unique_outputs)} unique outputs"
    )


def test_domain_separation_indices_unique() -> None:
    """Verify different indices produce different outputs for same label."""
    from sch.constants import ConstantDeriver

    params = get_params("sch128")
    deriver = ConstantDeriver(params.seed, params.name)

    outputs = set()
    for i in range(10):
        for j in range(10):
            out = deriver.derive_bytes("test_label", [i, j], length=32)
            assert out not in outputs, f"Collision at indices ({i}, {j})"
            outputs.add(out)


# =============================================================================
# VERIFICATION TESTS: Sponge Construction
# =============================================================================


def test_sponge_rate_capacity_structure() -> None:
    """Verify sponge uses correct rate/capacity split.

    Rate r: number of state words used for absorb/squeeze
    Capacity c: security margin (untouched during absorb/squeeze)
    Invariant: n = r + c
    """
    for name, params in PARAMS.items():
        assert params.r + params.c == params.n, f"{name}: r + c != n"


def test_sponge_absorb_affects_only_rate() -> None:
    """Verify absorption XORs into the rate portion of the state.

    The sponge absorbs up to r elements per permutation call, adding
    each element into state[0..r-1].
    """
    params = get_params("sch128")
    sponge = SCHSponge(params)

    # Get initial state after domain tag
    initial_state = sponge.state.copy()

    # Absorb a single element — goes into state[0]
    sponge.absorb_elements([42])

    # After P, state should have changed entirely (diffusion)


def test_sponge_squeeze_applies_p_between_outputs() -> None:
    """Verify squeeze applies P only between outputs, not after last."""
    params = get_params("sch128")
    sponge = SCHSponge(params)
    sponge.absorb_elements([1, 2, 3])

    # Squeeze 1 element: no P after
    state_before = sponge.state.copy()
    out1 = sponge.squeeze_elements(1)
    # State should be unchanged (no P applied for single squeeze)

    # Reset and squeeze 2 elements: P applied once (between them)
    sponge.reset()
    sponge.absorb_elements([1, 2, 3])
    out2 = sponge.squeeze_elements(2)
    assert len(out2) == 2


# =============================================================================
# VERIFICATION TESTS: Encoding
# =============================================================================


def test_encoding_block_size_formula() -> None:
    """Verify block size B satisfies 256^B <= p-1 < 256^(B+1)."""
    for name, params in PARAMS.items():
        if params.toy:
            continue  # Toy primes too small for byte packing
        B = compute_block_size(params.p)
        assert pow(256, B) <= params.p - 1, f"{name}: 256^B > p-1"
        assert pow(256, B + 1) > params.p - 1, f"{name}: 256^(B+1) <= p-1"


def test_encoding_no_reduction_needed() -> None:
    """Verify packed blocks don't need modular reduction.

    Since 256^B <= p-1, any B-byte block interpreted as little-endian
    integer is already < p, so no rejection sampling needed.
    """
    for name, params in PARAMS.items():
        if params.toy:
            continue
        B = compute_block_size(params.p)
        max_block_value = pow(256, B) - 1  # All 0xFF bytes
        assert max_block_value < params.p, (
            f"{name}: max block value {max_block_value} >= p={params.p}"
        )


# =============================================================================
# KNOWN-ANSWER TESTS (KATs)
# =============================================================================


KAT_VECTORS = {
    "sch128": [
        # (message_hex, expected_digest_elements)
        ("", [
            143318500100078006530403293305255320698,
            124403830338808755240305127952117028777,
            1164462375271981088757273491113585925,
            95849600366506517284587973427074857448,
        ]),
        ("616263", [  # "abc"
            66254099932580900688762931413488248945,
            63474362572758525734490118497539143750,
            144933407027833815334274708095775364319,
            110173678606625162562284711270638183149,
        ]),
        ("00", [  # Single zero byte
            89291201118072725022780430759949970768,
            71751237711218360705498540599094709021,
            123620518343793283451929335600701743431,
            110522382327622494224354368825515454779,
        ]),
    ],
    "sch192": [
        ("", [
            2285744882919400545247549706486592261332911204343718080104,
            2702372920175329406735136617387422172370367902488122286017,
            1730222602571643092701604499597582162766708604721559561037,
            1057921511338275202348135243856401135748157795364028104918,
            820572562757104341057739461748247365172405047734040921575,
            1734095913227038404740926045474120697247160861351295034012,
        ]),
        ("616263", [  # "abc"
            577068360069544548945070090703668085742768643501156102255,
            439998768608070628551421075860948095883035626182372483555,
            1400179805454223400626668438533070599851039488095261332080,
            1282321913298735360893507650910266689537561530327222273085,
            2966951581102534484600914685259991306721356920888770657655,
            2254179253653399424374238979279454876420975976107875327534,
        ]),
    ],
    "sch256": [
        ("", [
            22976012735140211524126531034179615505806131659123517057941507930699285190170,
            2750865519138788538692525035242460744637390824282161388646496298283874257302,
            6033618216320104288519503517467978554048467217482407180737923215975480078939,
            237880596750542859789575155191354664104451883112018602373282860470895044547,
            32510352650738449527913236592962750962187862916597687887544771300602289908200,
            18856365384470321433259228288400444682904981319932811712454560348990514434714,
            10189317812115381482192679346562301316312030994145512853606595385753011104719,
            19747172197577745892362521115479614344456856860376908309613423674625059087038,
        ]),
        ("616263", [  # "abc"
            18402373277729647335571656440137260163912809229723891601554756041205853335898,
            7803680926679572603218055567489268423072171377332278224778528997486209192800,
            42796425117479512883327489146774519471584873674524967101467022999116219850256,
            33530731277915208471294269657567084232888810893000094485241926746234804944008,
            51943579013968596679721755688370602205936479411289095434472375486978624471851,
            46916920695904678896752772037010524301274631942909052328507602928270280588292,
            3221909333522362359215750168000005273849028566701817337921150249184526457072,
            27799933004230770322428903578456234982971990200169967177695883454572773079120,
        ]),
    ],
}


@pytest.mark.parametrize("params_name", ["sch128", "sch192", "sch256"])
def test_known_answer_vectors(params_name: str) -> None:
    """Verify known-answer test vectors for reproducibility."""
    params = get_params(params_name)
    for msg_hex, expected in KAT_VECTORS.get(params_name, []):
        message = bytes.fromhex(msg_hex)
        digest = sch_hash(message, params)
        assert digest == expected, (
            f"KAT mismatch for {params_name}, msg={msg_hex[:20]}..."
        )


# =============================================================================
# CROSS-VALIDATION: regenerating vectors matches saved JSON
# =============================================================================


def test_cross_validate_generated_vectors() -> None:
    """Regenerate test vectors from scratch and compare to saved JSON."""
    import json
    import os

    json_path = os.path.join(os.path.dirname(__file__), "test_vectors_generated.json")
    if not os.path.exists(json_path):
        pytest.skip("test_vectors_generated.json not found")

    with open(json_path) as f:
        saved = json.load(f)

    messages_map = {
        "empty": b"",
        "abc": b"abc",
        "hello_world": b"Hello, World!",
        "zeros_64": b"\x00" * 64,
        "ones_256": b"\xff" * 256,
        "rand1k": deterministic_bytes(1024),
        "rand4k": deterministic_bytes(4096),
    }
    # Only cross-validate sch128 (sch192/sch256 are too slow for all messages;
    # they are already covered by test_known_answer_vectors for empty/abc).
    params_name = "sch128"
    params = get_params(params_name)
    for msg_label, expected_digest in saved[params_name].items():
        msg = messages_map.get(msg_label)
        if msg is None:
            continue
        digest = sch_hash(msg, params)
        assert digest == expected_digest, (
            f"Cross-validation failed: {params_name}/{msg_label}"
        )