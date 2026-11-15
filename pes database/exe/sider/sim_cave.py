"""What MLSimMatch.lua puts into PES2017.exe, and the same arithmetic as Python.

    python3 sim_cave.py            print the layout and the code bytes
    python3 sim_cave.py build      assemble the code again (needs: pip install keystone-engine)
                                   and compare it with the bytes kept in this file
    python3 sim_cave.py lua <PES2017.exe>
                                   print the generated tables/hooks block for MLSimMatch.lua
                                   (test_sim.py checks that MLSimMatch.lua matches this)

MLSimMatch.lua improves simulated matches (Skip Match and AI-vs-AI) in PES 2017
(sha256 44b0caaa...). It replaces the game's flat linear win-chance and uniform scoreline
draws with:

  1. Outcome probabilities (hook at 0x03707d56 inside fcn_03707a1f):
     A Davidson/Bradley-Terry model with home advantage, smooth tails (no 0%/100%
     cliff at diff >= 12), realistic draw rates, and scaled Master League captain role
     bonuses. Guarantees non-zero home and away win chances so knockout / 2-leg replay
     loops in fcn_03708de9 always terminate.

  2. Realistic scorelines (hook at 0x0370606c inside fcn_03705feb):
     Weighted scoreline distributions precomputed from a conditional Poisson model across
     7 strength-gap bands (1-0, 2-0, 2-1, 3-0, ... up to 6-5) plus weighted draw scores
     (0-0, 1-1, 2-2, 3-3, 4-4), replacing the game's flat uniform rand() % max_goals.

  3. Skip Match substitutions (patch at 0x03708230 inside fcn_03707e71):
     Changes `je 0x3708249` (74 17) to `jmp 0x3708249` (eb 17) so the user's team makes
     its 3 CPU substitutions during Skip Match instead of forcing sub1 = sub2 = sub3 = 11.

All data and code live in the unused tail of `.xcode` (0x047d3a50..0x047d3dff, 944 B,
-rwx, zeroed in PES2017.exe) and do not touch `.trace` (MLMoney.lua) or `.data1`
(MLTransfers.lua).
"""
import math
import struct
import sys

# =====================================================================
# Memory addresses in PES2017.exe (sha256 44b0caaac6703459f1a674ab7defc98d39613008b9254646f2543431fa9d954f)
# =====================================================================

CAVE = 0x047d3a50
CAVE_END = 0x047d3e00
CAVE_SIZE_MAX = CAVE_END - CAVE  # 944 bytes

# Game functions & globals
MENU_STATUS = 0x03808865    # returns obj; [obj+0x20] = menu_mode
TEAM_RECORD = 0x03822969    # __thiscall(ecx=mode_data, team_id) -> team_ptr
MODE_RANDOM = 0x03855998    # __cdecl(&n, &flag) -> 0..n-1
SKIP_FLAG_OFF = 0xdcb61c    # byte [mode_data + 0xdcb61c] != 0 during Skip Match

# Hook / patch sites
OUTCOME_SITE = 0x03707d56       # 7 bytes: movzx edi, byte ptr [ebp - 0xd]
OUTCOME_FALLBACK = 0x03707d5d
OUTCOME_DONE = 0x03707e10       # restores SEH, pops regs, ret 4

SCORE_SITE = 0x0370606c         # 5 bytes: mov eax, [ebp+8]; mov eax, [eax]
SCORE_FALLBACK = 0x03706071
SCORE_DONE_H = 0x03706110       # home win / draw epilogue ([ebx+0x14]=cl, [ebx+0x17]=al)
SCORE_DONE_A = 0x03706159       # away win epilogue ([ebx+0x17]=cl, [ebx+0x14]=al)

SKIP_SUBS_SITE = 0x03708230     # 2 bytes: 74 17 (je 0x3708249) -> eb 17 (jmp 0x3708249)

# Cave layout offsets (relative to CAVE)
#   +0x000 (16 B)  : CFG (scope, home_adv, cap_div, magic)
#   +0x010 (204 B) : OUTCOME_TABLE (51 entries x 4 B: u16 p_home, u16 p_home_plus_draw, / 1000)
#   +0x0dc (5 B)   : DRAW_CDF (5 x u8 cumulative thresholds / 255)
#   +0x0e1 (21 B)  : PAIR_SCORES (21 x u8: (g_win << 4) | g_lose)
#   +0x0f6 (147 B) : WIN_CDF (7 bands x 21 x u8 cumulative thresholds / 255)
#   +0x189 (3 B)   : pad to 4-byte alignment
#   +0x18c (...)   : Machine-code routines

CFG_OFF = 0x000
CFG_SCOPE = CAVE + 0x000
CFG_HOME_ADV = CAVE + 0x004
CFG_CAP_DIV = CAVE + 0x008
CFG_MAGIC = CAVE + 0x00c

OUTCOME_TABLE_OFF = 0x010
OUTCOME_TABLE = CAVE + OUTCOME_TABLE_OFF
DIFF_MIN = -25
DIFF_MAX = 25
DIFF_COUNT = DIFF_MAX - DIFF_MIN + 1  # 51

DRAW_CDF_OFF = OUTCOME_TABLE_OFF + DIFF_COUNT * 4  # 0x0dc
DRAW_CDF = CAVE + DRAW_CDF_OFF
DRAW_MAX_GOALS = 4  # 0-0 .. 4-4 (5 outcomes)

PAIR_SCORES_OFF = DRAW_CDF_OFF + (DRAW_MAX_GOALS + 1)  # 0x0e1
PAIR_SCORES = CAVE + PAIR_SCORES_OFF
PAIRS = tuple((gw, gl) for gw in range(1, 7) for gl in range(gw))  # 21 pairs

WIN_CDF_OFF = PAIR_SCORES_OFF + len(PAIRS)  # 0x0f6
WIN_CDF = CAVE + WIN_CDF_OFF
BAND_THRESHOLDS = (-6, -1, 3, 7, 11, 15)  # 7 bands: <=-6, -5..-1, 0..3, 4..7, 8..11, 12..15, >=16
NUM_BANDS = len(BAND_THRESHOLDS) + 1

CODE_OFF = (WIN_CDF_OFF + NUM_BANDS * len(PAIRS) + 3) & ~3  # 0x18c
CODE_BASE = CAVE + CODE_OFF

# Default settings (matching MLSimMatch.lua)
DEFAULT_SETTINGS = {
    "SCOPE": "all",
    "HOME_ADVANTAGE": 3.0,
    "ELO_SCALE": 7.5,
    "BASE_DRAW": 0.28,
    "CAPTAIN_WEIGHT": 0.2,
    "GOAL_SCALE": 1.0,
    "DRAW_WEIGHTS": (28.0, 46.0, 21.0, 4.5, 0.5),
    "SKIP_SUBS": True,
}

# =====================================================================
# Reference mathematical model (Python mirror of Lua table builder)
# =====================================================================

def outcome_probs(diff_raw, cap_home=0, *, home_adv=3.0, elo_scale=7.5, base_draw=0.28, cap_weight=0.2):
    """Return (p_home, p_draw, p_away) in [0, 1] summing to 1.0."""
    cap_ovr = int(cap_home * cap_weight) if cap_weight > 0 else 0
    clamped = max(DIFF_MIN, min(DIFF_MAX, diff_raw + cap_ovr))
    eff = clamped + home_adv
    a = math.exp(eff / elo_scale)
    nu = 2.0 * base_draw / (1.0 - base_draw)
    d = nu * math.sqrt(a)
    z = a + 1.0 + d
    return a / z, d / z, 1.0 / z


def build_outcome_table(*, home_adv=3.0, elo_scale=7.5, base_draw=0.28):
    """51 x (u16 p_home, u16 p_home_plus_draw) scaled to 1000."""
    rows = []
    nu = 2.0 * base_draw / (1.0 - base_draw)
    for diff in range(DIFF_MIN, DIFF_MAX + 1):
        eff = diff + home_adv
        a = math.exp(eff / elo_scale)
        d = nu * math.sqrt(a)
        z = a + 1.0 + d
        ph = max(1, min(998, int(round(1000.0 * (a / z)))))
        pd = max(1, min(999 - ph, int(round(1000.0 * (d / z)))))
        rows.append((ph, ph + pd))
    return rows


def build_draw_cdf(weights=(28.0, 46.0, 21.0, 4.5, 0.5)):
    """5 x u8 cumulative thresholds out of 255."""
    total = float(sum(weights))
    cdf = []
    acc = 0.0
    for i, w in enumerate(weights):
        acc += w / total
        val = 255 if i == len(weights) - 1 else min(255, max(0, int(round(acc * 255.0))))
        if cdf and val < cdf[-1]:
            val = cdf[-1]
        cdf.append(val)
    cdf[-1] = 255
    return cdf


def _poisson_pmf(lam, k):
    return (lam ** k) * math.exp(-lam) / math.factorial(k)


def build_win_cdf(*, goal_scale=1.0):
    """7 bands x 21 x u8 cumulative thresholds out of 255."""
    band_centers = (-9.0, -3.0, 1.5, 5.5, 9.5, 13.5, 19.0)
    bands = []
    for dc in band_centers:
        lam_w = 1.52 * goal_scale * math.exp(0.026 * dc)
        lam_l = 0.92 * goal_scale * math.exp(-0.026 * dc)
        weights = [_poisson_pmf(lam_w, gw) * _poisson_pmf(lam_l, gl) for gw, gl in PAIRS]
        total = sum(weights)
        cdf = []
        acc = 0.0
        for i, w in enumerate(weights):
            acc += w / total
            val = 255 if i == len(PAIRS) - 1 else min(255, max(0, int(round(acc * 255.0))))
            if cdf and val < cdf[-1]:
                val = cdf[-1]
            cdf.append(val)
        cdf[-1] = 255
        bands.append(cdf)
    return bands


def pack_tables(settings=None):
    """Pack CFG + OUTCOME_TABLE + DRAW_CDF + PAIR_SCORES + WIN_CDF as bytes."""
    s = dict(DEFAULT_SETTINGS)
    if settings:
        s.update(settings)
    scope_int = 1 if s["SCOPE"] == "skip_only" else 0
    home_adv_int = int(round(s["HOME_ADVANTAGE"]))
    cap_div = int(round(1.0 / s["CAPTAIN_WEIGHT"])) if s["CAPTAIN_WEIGHT"] > 0 else 0
    cfg = struct.pack("<IiII", scope_int, home_adv_int, cap_div, 0x4D4C5331)  # "MLS1"

    ot = b"".join(
        struct.pack("<HH", ph, phd)
        for ph, phd in build_outcome_table(
            home_adv=s["HOME_ADVANTAGE"],
            elo_scale=s["ELO_SCALE"],
            base_draw=s["BASE_DRAW"],
        )
    )
    dc = bytes(build_draw_cdf(s["DRAW_WEIGHTS"]))
    ps = bytes((gw << 4) | gl for gw, gl in PAIRS)
    wc_bands = build_win_cdf(goal_scale=s["GOAL_SCALE"])
    wc = b"".join(bytes(b) for b in wc_bands)

    blob = bytearray(CODE_OFF)
    blob[CFG_OFF : CFG_OFF + 16] = cfg
    blob[OUTCOME_TABLE_OFF : OUTCOME_TABLE_OFF + len(ot)] = ot
    blob[DRAW_CDF_OFF : DRAW_CDF_OFF + len(dc)] = dc
    blob[PAIR_SCORES_OFF : PAIR_SCORES_OFF + len(ps)] = ps
    blob[WIN_CDF_OFF : WIN_CDF_OFF + len(wc)] = wc
    return bytes(blob)


# =====================================================================
# x86 assembly & verified machine-code bytes
# =====================================================================

def assemble():
    """Assemble the four cave routines with Keystone at CODE_BASE."""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32

    ks = Ks(KS_ARCH_X86, KS_MODE_32)

    def asm(src, base):
        enc, _ = ks.asm(src, base)
        return bytes(enc)

    # First pass / exact layout:
    # 1. check_should_override(ecx=match_ptr, edx=mode_data) -> al in {0, 1}; preserves ebx, esi, edi, ebp
    chk_addr = CODE_BASE
    chk_src = f"""
        push ebx
        push esi
        mov esi, ecx
        mov ebx, edx

        movzx eax, word ptr [esi + 4]
        cmp eax, 0x3c
        je chk_menu
        cmp eax, 0x3d
        jne chk_scope
    chk_menu:
        mov eax, 0x{MENU_STATUS:08x}
        call eax
        mov eax, dword ptr [eax + 0x20]
        cmp eax, 0x27
        je ret_zero
        cmp eax, 0x28
        je ret_zero

    chk_scope:
        cmp dword ptr [0x{CFG_SCOPE:08x}], 0
        je ret_one
        cmp byte ptr [ebx + 0x{SKIP_FLAG_OFF:08x}], 0
        je ret_zero

        push dword ptr [esi + 0xc]
        mov ecx, ebx
        mov eax, 0x{TEAM_RECORD:08x}
        call eax
        test eax, eax
        jz chk_away
        mov eax, dword ptr [eax + 0x314]
        shr eax, 7
        cmp al, 0xff
        jne ret_one

    chk_away:
        push dword ptr [esi + 0x10]
        mov ecx, ebx
        mov eax, 0x{TEAM_RECORD:08x}
        call eax
        test eax, eax
        jz ret_zero
        mov eax, dword ptr [eax + 0x314]
        shr eax, 7
        cmp al, 0xff
        jne ret_one

    ret_zero:
        xor eax, eax
        pop esi
        pop ebx
        ret

    ret_one:
        mov eax, 1
        pop esi
        pop ebx
        ret
    """
    chk_bytes = asm(chk_src, chk_addr)

    # 2. rand_range(ecx=n) -> eax in [0, n-1]; preserves ebx, esi, edi, ebp
    rand_addr = (chk_addr + len(chk_bytes) + 3) & ~3
    rand_src = f"""
        push 0
        push ecx
        lea eax, [esp + 4]
        lea ecx, [esp]
        push eax
        push ecx
        mov eax, 0x{MODE_RANDOM:08x}
        call eax
        add esp, 16
        ret
    """
    rand_bytes = asm(rand_src, rand_addr)

    # 3. OUTCOME_HOOK (jumped from 0x03707d56; esi=match_ptr, edi=mode_data)
    outcome_addr = (rand_addr + len(rand_bytes) + 3) & ~3
    outcome_src = f"""
        mov ecx, esi
        mov edx, edi
        mov eax, 0x{chk_addr:08x}
        call eax
        test al, al
        jnz do_outcome
        movzx edi, byte ptr [ebp - 0xd]
        mov eax, 0x{OUTCOME_FALLBACK:08x}
        jmp eax

    do_outcome:
        movzx eax, byte ptr [ebp - 0xd]
        cmp dword ptr [ebp - 0x18], 0
        je diff_pos
        neg eax
    diff_pos:
        mov ebx, eax

        mov eax, dword ptr [ebp - 0x14]
        cmp dword ptr [ebp - 0x18], 0
        je cap_pos
        neg eax
    cap_pos:
        mov ecx, dword ptr [0x{CFG_CAP_DIV:08x}]
        test ecx, ecx
        jz no_cap
        cdq
        idiv ecx
        add ebx, eax
    no_cap:
        cmp ebx, {DIFF_MIN}
        jge not_low
        mov ebx, {DIFF_MIN}
    not_low:
        cmp ebx, {DIFF_MAX}
        jle not_high
        mov ebx, {DIFF_MAX}
    not_high:
        add ebx, {-DIFF_MIN}

        movzx esi, word ptr [ebx*4 + 0x{OUTCOME_TABLE:08x}]
        movzx edi, word ptr [ebx*4 + 0x{OUTCOME_TABLE + 2:08x}]

        mov ecx, 1000
        mov eax, 0x{rand_addr:08x}
        call eax

        cmp eax, esi
        jae not_home
        xor eax, eax
        mov ecx, 0x{OUTCOME_DONE:08x}
        jmp ecx
    not_home:
        cmp eax, edi
        jae away_win
        mov eax, 2
        mov ecx, 0x{OUTCOME_DONE:08x}
        jmp ecx
    away_win:
        mov eax, 1
        mov ecx, 0x{OUTCOME_DONE:08x}
        jmp ecx
    """
    outcome_bytes = asm(outcome_src, outcome_addr)

    # 4. SCORE_HOOK (jumped from 0x0370606c; eax=mode_obj, ebx=match_ptr, esi=ovr0, edi=ovr1)
    score_addr = (outcome_addr + len(outcome_bytes) + 3) & ~3
    score_src = f"""
        mov ecx, ebx
        mov edx, dword ptr [eax + 0x30]
        mov eax, 0x{chk_addr:08x}
        call eax
        test al, al
        jnz do_score
        mov eax, dword ptr [ebp + 8]
        mov eax, dword ptr [eax]
        mov ecx, 0x{SCORE_FALLBACK:08x}
        jmp ecx

    do_score:
        mov eax, dword ptr [ebp + 8]
        mov edx, dword ptr [eax]
        cmp edx, 2
        je is_draw

        push edx
        mov eax, esi
        add eax, dword ptr [0x{CFG_HOME_ADV:08x}]
        sub eax, edi
        test edx, edx
        jz d_ready
        neg eax
    d_ready:
        xor esi, esi
        cmp eax, -6
        jle band_ok
        inc esi
        cmp eax, -1
        jle band_ok
        inc esi
        cmp eax, 3
        jle band_ok
        inc esi
        cmp eax, 7
        jle band_ok
        inc esi
        cmp eax, 11
        jle band_ok
        inc esi
        cmp eax, 15
        jle band_ok
        inc esi
    band_ok:
        imul esi, esi, 21
        add esi, 0x{WIN_CDF:08x}

        mov ecx, 255
        mov eax, 0x{rand_addr:08x}
        call eax

        xor ecx, ecx
    win_scan:
        movzx edx, byte ptr [esi + ecx]
        cmp eax, edx
        jb win_found
        inc ecx
        cmp ecx, 20
        jb win_scan
    win_found:
        movzx eax, byte ptr [ecx + 0x{PAIR_SCORES:08x}]
        mov cl, al
        shr cl, 4
        and al, 0x0f
        pop edx
        test edx, edx
        jz go_home
        mov edx, 0x{SCORE_DONE_A:08x}
        jmp edx
    go_home:
        mov edx, 0x{SCORE_DONE_H:08x}
        jmp edx

    is_draw:
        mov ecx, 255
        mov eax, 0x{rand_addr:08x}
        call eax
        xor ecx, ecx
    draw_scan:
        movzx edx, byte ptr [ecx + 0x{DRAW_CDF:08x}]
        cmp eax, edx
        jb draw_found
        inc ecx
        cmp ecx, 4
        jb draw_scan
    draw_found:
        mov al, cl
        mov edx, 0x{SCORE_DONE_H:08x}
        jmp edx
    """
    score_bytes = asm(score_src, score_addr)

    # Assemble relative jumps at OUTCOME_SITE and SCORE_SITE
    outcome_patch = asm(f"jmp 0x{outcome_addr:08x}; nop; nop", OUTCOME_SITE)
    score_patch = asm(f"jmp 0x{score_addr:08x}", SCORE_SITE)

    end_addr = score_addr + len(score_bytes)
    assert end_addr <= CAVE_END, f"Overflowed cave: {hex(end_addr)} > {hex(CAVE_END)}"

    return {
        "chk": (chk_addr, chk_bytes),
        "rand": (rand_addr, rand_bytes),
        "outcome": (outcome_addr, outcome_bytes),
        "score": (score_addr, score_bytes),
        "end": end_addr,
        "outcome_patch": outcome_patch,
        "score_patch": score_patch,
    }


# Pre-assembled verified bytes (checked by `python3 sim_cave.py build`)
CODE_PARTS = {
    "chk": (
        0x047d3bdc,
        "535689ce89d30fb7460483f83c740583f83d7514b865888003ffd08b402083f8"
        "27745183f828744c833d503a7d0400744880bb1cb6dc0000743aff760c89d9b8"
        "69298203ffd085c0740d8b8014030000c1e8073cff7522ff761089d9b8692982"
        "03ffd085c0740d8b8014030000c1e8073cff750531c05e5bc3b8010000005e5b"
        "c3",
    ),
    "rand": (
        0x047d3c60,
        "6a00518d4424048d0c245051b898598503ffd083c410c3",
    ),
    "outcome": (
        0x047d3c78,
        "89f189fab8dc3b7d04ffd084c0750b0fb67df3b85d7d7003ffe00fb645f3837d"
        "e8007402f7d889c38b45ec837de8007402f7d88b0d583a7d0485c9740599f7f9"
        "01c383fbe77d05bbe7ffffff83fb197e05bb1900000083c3190fb7349d603a7d"
        "040fb73c9d623a7d04b9e8030000b8603c7d04ffd039f0730931c0b9107e7003"
        "ffe139f8730cb802000000b9107e7003ffe1b801000000b9107e7003ffe1",
    ),
    "score": (
        0x047d3d18,
        "89d98b5030b8dc3b7d04ffd084c0750c8b45088b00b971607003ffe18b4508"
        "8b1083fa02747d5289f00305543a7d0429f885d27402f7d831f683f8fa7e1f46"
        "83f8ff7e194683f8037e134683f8077e0d4683f80b7e074683f80f7e01466bf6"
        "1581c6463b7d04b9ff000000b8603c7d04ffd031c90fb6140e39d072064183f9"
        "1472f20fb681313b7d0488c1c0e904240f5a85d27407ba59617003ffe2ba1061"
        "7003ffe2b9ff000000b8603c7d04ffd031c90fb6912c3b7d0439d072064183f9"
        "0472ef88c8ba10617003ffe2",
    ),
}


def build_image(settings=None):
    """Return full CAVE bytes (tables + machine code) for writing at CAVE."""
    end = max(addr + len(bytes.fromhex(hx)) for addr, hx in CODE_PARTS.values())
    buf = bytearray(end - CAVE)
    tables = pack_tables(settings)
    buf[: len(tables)] = tables
    for addr, hx in CODE_PARTS.values():
        b = bytes.fromhex(hx)
        off = addr - CAVE
        buf[off : off + len(b)] = b
    return bytes(buf)


def lua_block(exe_path):
    """Emit the generated Lua code block (CONTEXT, ADDRESSES, CODE, SITES) for MLSimMatch.lua."""
    with open(exe_path, "rb") as f:
        exe = f.read()

    # File offset mapping for PES2017.exe sections:
    # .text/.rdata/.data/etc. — read using pes database/exe/tools/emu.py section map
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "tools"))
    import emu
    g = emu.Game(exe_path)

    def read_hex(va, n):
        return g.read(va, n).hex()

    # Verify cave is zero in exe
    cave_len = build_image()
    assert g.read(CAVE, len(cave_len)) == b"\x00" * len(cave_len), "Cave not empty in exe!"

    chk_addr, chk_hx = CODE_PARTS["chk"]
    rand_addr, rand_hx = CODE_PARTS["rand"]
    out_addr, out_hx = CODE_PARTS["outcome"]
    scr_addr, scr_hx = CODE_PARTS["score"]

    # Wait: check exact jmp bytes for OUTCOME_SITE and SCORE_SITE
    out_rel = (out_addr - (OUTCOME_SITE + 5)) & 0xffffffff
    scr_rel = (scr_addr - (SCORE_SITE + 5)) & 0xffffffff
    out_patch = "e9" + struct.pack("<I", out_rel).hex() + "9090"
    scr_patch = "e9" + struct.pack("<I", scr_rel).hex()

    lines = [
        "-- Generated by sim_cave.py (do not edit by hand; test_sim.py checks this block)",
        f"local CAVE = 0x{CAVE:08x}",
        f"local CAVE_SIZE = {len(cave_len)}",
        f"local CODE_OFF = 0x{CODE_OFF:04x}",
        f"local DIFF_MIN = {DIFF_MIN}",
        f"local DIFF_MAX = {DIFF_MAX}",
        f"local PAIRS_COUNT = {len(PAIRS)}",
        "",
        "local ROUTINES = {",
        f'    {{ 0x{chk_addr - CAVE:04x}, "{chk_hx}" }},',
        f'    {{ 0x{rand_addr - CAVE:04x}, "{rand_hx}" }},',
        f'    {{ 0x{out_addr - CAVE:04x}, "{out_hx}" }},',
        f'    {{ 0x{scr_addr - CAVE:04x}, "{scr_hx}" }},',
        "}",
        "",
        "local SITES = {",
        f'    outcome   = {{ "outcome probability", 0x{OUTCOME_SITE:08x}, "{read_hex(OUTCOME_SITE, 7)}", "{out_patch}" }},',
        f'    score     = {{ "scoreline model",     0x{SCORE_SITE:08x}, "{read_hex(SCORE_SITE, 5)}", "{scr_patch}" }},',
        f'    skip_subs = {{ "skip-match subs",     0x{SKIP_SUBS_SITE:08x}, "{read_hex(SKIP_SUBS_SITE, 2)}", "eb17" }},',
        "}",
        "",
        "local CONTEXT = {",
        f'    {{ "outcome entry",    0x03707a1f, "{read_hex(0x03707a1f, 8)}" }},',
        f'    {{ "outcome fallback", 0x03707d5d, "{read_hex(0x03707d5d, 7)}" }},',
        f'    {{ "outcome return",   0x03707e10, "{read_hex(0x03707e10, 16)}" }},',
        f'    {{ "score entry",      0x03705feb, "{read_hex(0x03705feb, 6)}" }},',
        f'    {{ "score fallback",   0x03706071, "{read_hex(0x03706071, 10)}" }},',
        f'    {{ "score done H",     0x03706110, "{read_hex(0x03706110, 13)}" }},',
        f'    {{ "score done A",     0x03706159, "{read_hex(0x03706159, 13)}" }},',
        f'    {{ "menu status",      0x{MENU_STATUS:08x}, "{read_hex(MENU_STATUS, 6)}" }},',
        f'    {{ "team record",      0x{TEAM_RECORD:08x}, "{read_hex(TEAM_RECORD, 6)}" }},',
        f'    {{ "mode random",      0x{MODE_RANDOM:08x}, "{read_hex(MODE_RANDOM, 6)}" }},',
        "}",
    ]
    return "\n".join(lines)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    if cmd == "build":
        built = assemble()
        print(f"Assembled end: 0x{built['end']:08x} ({built['end'] - CAVE} / {CAVE_SIZE_MAX} bytes)")
        for name in ("chk", "rand", "outcome", "score"):
            addr, b = built[name]
            print(f'    "{name}": (0x{addr:08x}, "{b.hex()}"),')
        print(f'outcome_patch: {built["outcome_patch"].hex()}')
        print(f'score_patch:   {built["score_patch"].hex()}')
        for name in ("chk", "rand", "outcome", "score"):
            exp_addr, exp_hx = CODE_PARTS[name]
            got_addr, got_b = built[name]
            if (exp_addr, exp_hx) != (got_addr, got_b.hex()):
                print(f"MISMATCH on {name}!", file=sys.stderr)
                sys.exit(1)
        print("CODE_PARTS matches Keystone assembly byte-for-byte.")
    elif cmd == "lua":
        print(lua_block(sys.argv[2]))
    else:
        img = build_image()
        print(f"CAVE: 0x{CAVE:08x}..0x{CAVE + len(img):08x} ({len(img)} / {CAVE_SIZE_MAX} bytes)")
        for name, (addr, hx) in CODE_PARTS.items():
            print(f"  {name:8s}: 0x{addr:08x} ({len(hx)//2} B)")


if __name__ == "__main__":
    main()
