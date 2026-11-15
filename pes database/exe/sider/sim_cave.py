"""What MLSimMatch.lua puts into PES2017.exe, and the same arithmetic as Python.

    python3 sim_cave.py            print the layout and the code bytes
    python3 sim_cave.py build      assemble the code again (needs: pip install keystone-engine)
                                   and compare it with the bytes kept in this file
    python3 sim_cave.py lua <PES2017.exe>
                                   print the generated tables/hooks block for MLSimMatch.lua
                                   (test_sim.py checks that MLSimMatch.lua matches this)

MLSimMatch.lua (version 6) improves simulated matches (Skip Match and AI-vs-AI) in
PES 2017 (sha256 44b0caaa...):

  1. Outcome probabilities (hook at 0x03707d56 inside fcn_03707a1f, cave .reloc):
     Davidson/Bradley-Terry model with home advantage, smooth tails, realistic draw
     rates, scaled Master League captain role bonuses, and guaranteed non-zero W/L
     chances so knockout / 2-leg replay loops in fcn_03708de9 always terminate.

  2. Realistic scorelines (hook at 0x0370606c inside fcn_03705feb, cave .xcode):
     Weighted scoreline distributions precomputed from a conditional Poisson model across
     7 strength-gap bands (1-0..6-5) plus weighted draw scores (0-0..4-4).

  3. Skip Match substitutions, GK protection & smart CPU subs (patches/hook inside
     fcn_03707e71):
     - Patch at 0x03708230 (`74 17` -> `eb 17`) restores the user's 3 CPU substitutions
       during Skip Match instead of forcing sub1 = sub2 = sub3 = 11.
     - Patch at 0x0370818d (`31 ff` -> `90 90`) protects slot 0 (GK) from being subbed
       off for an outfielder (1 + rand(4) instead of 0..4).
     - Hook at 0x037080d9 ranks bench candidates by effective OVR (arrow & fatigue) +
       small 0..3 jitter instead of pure rand(100).

  4. Dynamic match ratings (hook at 0x03708d39 inside fcn_03708cc4, cave .xcode):
     Replaces the fixed 11-slot rating tables (0x2105a40..0x2105a98) with ratings driven
     by result, goal difference, clean-sheet / heavy-conceded positional adjustments,
     scaled goals + assists counts, yellow/red card deductions, and per-player variance.

  5. Realistic goal scorers & assists (hook at 0x03706f35 inside fcn_03706ef6, cave .xcode):
     Replaces the top-5 cutoff and the hardcoded 20/15/10/5/50 assist split with smooth
     exponential attribute weighting across all 10 outfield players, configurable
     unassisted-goal percentage, and zero self-assists.

  6. Fair penalty shootouts & realistic extra time (hooks at 0x037062ed inside
     fcn_037062ca and 0x037063bb inside fcn_037063bb, caves .reloc + .link):
     Fixes the vanilla `rand(1)` bug where home wins 100% of simulated penalty
     shootouts, replaces uniform `rand(3)` ET goals with strength-scaled 30-min ET
     scoring, and generates authentic shootout scorelines (3-1..7-6).

  7. Yellow & red cards + suspensions (hook at 0x03708f45 inside fcn_03708de9,
     cave .trace tail):
     Issues position-weighted yellow cards (0..4 per team), second-yellow red cards, and
     straight red cards into stat_rec +0x0c (bits 18..20), feeding directly into
     fcn_0370403e's competition card tallies and suspensions.

  8. Squad condition, lineup strength, fatigue & injury simulation effects (eff_strength
     + player_eff_ovr in .reloc, fatigue hook at 0x038557dc + AI_FATIGUE at 0x038557d6
     in fcn_038556f1, and post-match injury roll called from 0x03708f45):
     - Effective team strength evaluates each club's actual Starting XI from tactics
       (tactics + 0x248[0..10] at tactical positions +0x68, replacing unavailable
       starters from the best eligible bench players), excludes injured/suspended
       players (fcn_0385b771), and adjusts each player's OVR by condition arrow (0..4)
       and low-fitness penalty.
     - Stamina-scaled match fatigue drains fitness based on Stamina (attr 0x25), applies
       to AI teams too when AI_FATIGUE=true, and adds +30 mins for extra time.
     - Match injuries (attr 0x5e) are rolled per team weighted by Injury Resistance and
       fatigue, skipping GKs and preserving >= 8 healthy players.

Memory caves used (all verified zeroed in PES2017.exe, zero overlap with MLMoney.lua,
MLTransfers.lua, or MLYear.lua):
  - CAVE    (.xcode tail)     : 0x047d3a50..0x047d3fff (<= 1456 B)
  - CAVE_D  (.data1 mid-gap)  : 0x047d4170..0x047d41ff (144 / 144 B)
  - CAVE_D2 (.data1 post-MLT) : 0x047d4f60..0x047d4f87 (40 / 160 B, RWX)
  - CAVE_ET (.reloc page)     : 0x047d5040..0x047d5fff (<= 4032 B)
  - CAVE_PK (.link page)      : 0x047d6030..0x047d6fff (<= 4048 B)
  - CAVE_C  (.trace tail)     : 0x047b0060..0x047b01fd (<= 414 B)
"""
import math
import struct
import sys

# =====================================================================
# Memory addresses in PES2017.exe (sha256 44b0caaac6703459f1a674ab7defc98d39613008b9254646f2543431fa9d954f)
# =====================================================================

CAVE = 0x047d3a50
CAVE_END = 0x047d4000
CAVE_SIZE_MAX = CAVE_END - CAVE  # 1456 bytes

CAVE_D = 0x047d4170
CAVE_D_END = 0x047d4200
CAVE_D_MAX = CAVE_D_END - CAVE_D  # 144 bytes

CAVE_D2 = 0x047d4f60
CAVE_D2_END = 0x047d5000
CAVE_D2_MAX = CAVE_D2_END - CAVE_D2  # 160 bytes post-MLTransfers (.data1 RWX)

CAVE_ET = 0x047d5040
CAVE_ET_END = 0x047d6000
CAVE_ET_MAX = CAVE_ET_END - CAVE_ET  # 4032 bytes (.reloc page)

CAVE_PK = 0x047d6030
CAVE_PK_END = 0x047d7000
CAVE_PK_MAX = CAVE_PK_END - CAVE_PK  # 4048 bytes (.link page)
CARD_ADJ_ADDR = CAVE_PK + 0xf0       # 0x047d6120 (28 bytes)
PK_TABLE_ADDR = CAVE_PK + 0x110      # 0x047d6140 (16 bytes)

CAVE_C = 0x047b0060
CAVE_C_END = 0x047b01fe
CAVE_C_MAX = CAVE_C_END - CAVE_C     # 414 bytes

# Game functions & globals
MODE_OBJ = 0x0381c0e5       # returns obj; [obj+0x30] = mode_data
MENU_STATUS = 0x03808865    # returns obj; [obj+0x20] = menu_mode
TEAM_RECORD = 0x03822969    # __thiscall(ecx=mode_data, team_id) -> team_ptr
RECORD_BY_ID = 0x03822663   # __thiscall(ecx=mode_data, id_lo, id_hi) -> player_ptr
FIX_RECORD = 0x03822b3f     # __thiscall(ecx=mode_data, fix_id) -> fix_ptr
PLAYER_SET = 0x038281b0     # __thiscall(ecx=player_ptr, attr, val)
PLAYER_OVR = 0x03838c18     # __cdecl(&player_id, &pos, arrow) -> ovr
PLAYER_ELIG = 0x0385b771    # __cdecl(&player_id, &fix_id) -> bool
TEAM_STRENGTH = 0x03865b0a  # __cdecl(&team_id, &kind, arg3) -> ovr
TEAM_TACTICS_ID = 0x03117d98  # __thiscall(ecx=team_ptr, &out_8b) -> out_8b
TACTICS_REC = 0x03822a29      # __thiscall(ecx=mode_data, id_lo, id_hi) -> tactics_ptr
TACTICS_SENTINEL_OFF = 0x5fea64  # fallback sentinel returned by TACTICS_REC
MODE_RANDOM = 0x03855998    # __cdecl(&n, &flag) -> 0..n-1
STAT_REC_BY_ID = 0x037035c3 # __thiscall(ecx=match_ptr, &player_id) -> stat_rec
SKIP_FLAG_OFF = 0xdcb61c    # byte [mode_data + 0xdcb61c] != 0 during Skip Match

# Hook / patch sites
OUTCOME_SITE = 0x03707d56       # 7 bytes: movzx edi, byte ptr [ebp - 0xd]
OUTCOME_FALLBACK = 0x03707d5d
OUTCOME_DONE = 0x03707e10       # restores SEH, pops regs, ret 4

SCORE_SITE = 0x0370606c         # 5 bytes: mov eax, [ebp+8]; mov eax, [eax]
SCORE_FALLBACK = 0x03706071
SCORE_DONE_H = 0x03706110       # home win / draw epilogue
SCORE_DONE_A = 0x03706159       # away win epilogue

SMART_SUBS_SITE = 0x037080d9    # 15 bytes: mov dword [ebp-0x14c], 0x64; call MODE_RANDOM
SMART_SUBS_RET = 0x037080e8     # mov byte [ebp-0x19c], al; add esp, 8
GK_PROTECT_SITE = 0x0370818d    # 2 bytes: xor edi, edi (31 ff) -> nop nop (90 90)
SKIP_SUBS_SITE = 0x03708230     # 2 bytes: 74 17 -> eb 17

RATINGS_SITE = 0x03708d39       # 6 bytes: mov ecx, [ebp+8]; cmp ecx, 2
RATINGS_FALLBACK = 0x03708d3f
RATINGS_DONE = 0x03708d73

SCORER_SITE = 0x03706f35        # 8 bytes: xor ecx, ecx; mov [ebp-0x1c], ecx
SCORER_FALLBACK = 0x03706f3d
SCORER_PICKED = 0x03707244
SCORER_NONE = 0x037072e5

ET_SITE = 0x037062ed            # 5 bytes: mov ebx, 3
ET_FALLBACK = 0x037062f2
ET_DONE = 0x03706329

PK_SITE = 0x037063bb            # 6 bytes: push ebp; mov ebp, esp; sub esp, 8
PK_FALLBACK = 0x037063c1

CARDS_SITE = 0x03708f45         # 6 bytes: lea edx, [ebp - 0x2c]
CARDS_FALLBACK = 0x03708f4b

AI_FATIGUE_SITE = 0x038557d6    # 6 bytes: je 0x038558ba -> nop*6 when AI_FATIGUE=true
FATIGUE_SITE = 0x038557dc       # 6 bytes: lea ecx, [ebp - 8]
FATIGUE_FALLBACK = 0x038557e2
FATIGUE_EXIT = 0x038558ba

# =====================================================================
# CAVE (.xcode tail) layout
# =====================================================================
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
DRAW_MAX_GOALS = 4

PAIR_SCORES_OFF = DRAW_CDF_OFF + (DRAW_MAX_GOALS + 1)  # 0x0e1
PAIR_SCORES = CAVE + PAIR_SCORES_OFF
PAIRS = tuple((gw, gl) for gw in range(1, 7) for gl in range(gw))  # 21 pairs

WIN_CDF_OFF = PAIR_SCORES_OFF + len(PAIRS)  # 0x0f6
WIN_CDF = CAVE + WIN_CDF_OFF
BAND_THRESHOLDS = (-6, -1, 3, 7, 11, 15)
NUM_BANDS = len(BAND_THRESHOLDS) + 1

CODE_OFF = (WIN_CDF_OFF + NUM_BANDS * len(PAIRS) + 3) & ~3  # 0x18c
CODE_BASE = CAVE + CODE_OFF

# =====================================================================
# CAVE_D (.data1 mid-gap) layout: 144 bytes
# =====================================================================
CFG_R_WIN = CAVE_D + 0x00
CFG_R_DRAW = CAVE_D + 0x04
CFG_R_LOSS = CAVE_D + 0x08
CFG_R_GD_NUM = CAVE_D + 0x0c
CFG_R_CS_DEF = CAVE_D + 0x10
CFG_R_CS_ATT = CAVE_D + 0x14
CFG_R_GOAL = CAVE_D + 0x18
CFG_R_ASSIST = CAVE_D + 0x1c
CFG_R_VAR = CAVE_D + 0x20
CFG_R_MIN = CAVE_D + 0x24
CFG_R_MAX = CAVE_D + 0x28
CFG_R_GA_PEN_CAP = CAVE_D + 0x2c

CFG_S_SCORERS_ON = CAVE_D + 0x30
CFG_S_ASSISTS_ON = CAVE_D + 0x34
CFG_S_UNASSISTED = CAVE_D + 0x38

SCORER_W_OFF = 0x3c
SCORER_W = CAVE_D + SCORER_W_OFF  # 24 bytes
ASSIST_W_OFF = 0x54
ASSIST_W = CAVE_D + ASSIST_W_OFF  # 24 bytes

CFG_R_YELLOW = CAVE_D + 0x6c
CFG_R_RED = CAVE_D + 0x70
CFG_ET_SCALE_X100 = CAVE_D + 0x74
CFG_PK_BASE_PCT = CAVE_D + 0x78
CFG_PK_OVR_TENTHS = CAVE_D + 0x7c
CFG_C_RED_PCT = CAVE_D + 0x80       # u8
CARD_Y_CDF = CAVE_D + 0x81          # 5 bytes (0..4 yellows)
CARD_POS_W = CAVE_D + 0x86          # 10 bytes (pos 0..9)
CAVE_D_SIZE = 0x90                  # 144 bytes

# =====================================================================
# CAVE_D2 (.data1 post-MLTransfers RWX) layout: 40 bytes
# =====================================================================
CFG_V5_COND_STRENGTH = CAVE_D2 + 0x00   # u32 (0/1)
CFG_V5_FATIGUE_THRESH = CAVE_D2 + 0x04  # u32 (40..100)
CFG_V5_FATIGUE_PEN = CAVE_D2 + 0x08     # u32 (0..20)
CFG_V5_STAMINA_ON = CAVE_D2 + 0x0c      # u32 (0/1)
CFG_V5_STAMINA_W_X10 = CAVE_D2 + 0x10   # u32 (0..20)
CFG_V5_INJURY_PCT = CAVE_D2 + 0x14      # u8  (0..20)
CFG_V5_INJURY_MIN = CAVE_D2 + 0x15      # u8  (1..60)
CFG_V5_INJURY_SPAN = CAVE_D2 + 0x16     # u8  (1..60)
CFG_C_CARDS_ON = CAVE_D2 + 0x17         # u8  (0/1)
CFG_V5_COND_OVR = CAVE_D2 + 0x18        # int8[5] (arrows 0..4)
CFG_V6_SMART_SUBS = CAVE_D2 + 0x20      # u32 (0/1)
CFG_V6_LINEUP_STRENGTH = CAVE_D2 + 0x24 # u32 (0/1)
CAVE_D2_SIZE = 0x28                     # 40 bytes

# Shootout scoreline table placed inside CAVE_PK (16 bytes: 8 CDF + 8 Nibbles)
PK_TABLE_SIZE = 16
PK_CDF_DEFAULT = (24, 44, 62, 74, 84, 90, 96, 255)
PK_PAIRS = ((5, 4), (4, 3), (4, 2), (5, 3), (6, 5), (3, 1), (4, 1), (7, 6))

# Card positional weights (pos 0..9: GK, CB, FB, DMF, CMF, WMF, AMF, SS, WF, CF)
DEFAULT_CARD_POS_W = (2, 18, 16, 20, 14, 10, 8, 7, 7, 8)

# Default settings (matching MLSimMatch.lua v6)
DEFAULT_SETTINGS = {
    "SCOPE": "all",
    "HOME_ADVANTAGE": 2.4,
    "ELO_SCALE": 6.2,
    "BASE_DRAW": 0.27,
    "CAPTAIN_WEIGHT": 0.2,
    "GOAL_SCALE": 1.0,
    "DRAW_WEIGHTS": (28.0, 46.0, 21.0, 4.5, 0.5),
    "SKIP_SUBS": True,
    "GK_PROTECT": True,
    "SMART_SUBS": True,
    "RATINGS": True,
    "RATING_BASE": (6.4, 6.1, 5.7),
    "RATING_GD": 1.5,
    "RATING_CLEAN_SHEET": (0.3, 0.1),
    "RATING_GOAL": 0.7,
    "RATING_ASSIST": 0.4,
    "RATING_YELLOW": 0.3,
    "RATING_RED": 1.0,
    "RATING_VARIANCE": 0.4,
    "RATING_RANGE": (4.5, 9.5),
    "SCORERS": True,
    "ASSISTS": True,
    "SCORER_SHARPNESS": 0.11,
    "ASSIST_SHARPNESS": 0.045,
    "UNASSISTED_PCT": 28,
    "EXTRA_TIME_PK": True,
    "ET_GOAL_SCALE": 1.0,
    "PK_HOME_BIAS": 0,
    "PK_OVR_WEIGHT": 0.5,
    "CARDS": True,
    "YELLOW_AVG": 1.7,
    "RED_PCT": 4,
    "CONDITION_STRENGTH": True,
    "LINEUP_STRENGTH": True,
    "CONDITION_OVR": (-3, -1, 0, 1, 3),
    "FATIGUE_THRESHOLD": 72,
    "FATIGUE_PENALTY": 5,
    "STAMINA_FATIGUE": True,
    "STAMINA_WEIGHT": 1.0,
    "AI_FATIGUE": True,
    "INJURY_PCT": 3,
    "INJURY_DAYS": (7, 28),
}

# =====================================================================
# Reference mathematical models
# =====================================================================

def outcome_probs(
    diff_raw,
    cap_home=0,
    *,
    home_adv=DEFAULT_SETTINGS["HOME_ADVANTAGE"],
    elo_scale=DEFAULT_SETTINGS["ELO_SCALE"],
    base_draw=DEFAULT_SETTINGS["BASE_DRAW"],
    cap_weight=DEFAULT_SETTINGS["CAPTAIN_WEIGHT"],
):
    cap_ovr = int(cap_home * cap_weight) if cap_weight > 0 else 0
    clamped = max(DIFF_MIN, min(DIFF_MAX, diff_raw + cap_ovr))
    eff = clamped + home_adv
    a = math.exp(eff / elo_scale)
    nu = 2.0 * base_draw / (1.0 - base_draw)
    d = nu * math.sqrt(a)
    z = a + 1.0 + d
    return a / z, d / z, 1.0 / z


def build_outcome_table(
    *,
    home_adv=DEFAULT_SETTINGS["HOME_ADVANTAGE"],
    elo_scale=DEFAULT_SETTINGS["ELO_SCALE"],
    base_draw=DEFAULT_SETTINGS["BASE_DRAW"],
):
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


BAND_LAMBDAS = (
    (0.76, 1.58),  # Band 0 (d <= -6, Big Upset)
    (1.02, 1.32),  # Band 1 (d -5..-1, Slight Upset)
    (1.35, 1.00),  # Band 2 (d  0..3, Equal)
    (1.55, 0.85),  # Band 3 (d  4..7, Slight Fav)
    (1.76, 0.72),  # Band 4 (d  8..11, Clear Fav)
    (1.98, 0.60),  # Band 5 (d 12..15, Strong Fav)
    (2.22, 0.50),  # Band 6 (d >= 16, Huge Fav)
)


def build_win_cdf(*, goal_scale=1.0):
    bands = []
    for bi, (lw_base, ll_base) in enumerate(BAND_LAMBDAS):
        lam_w = lw_base * goal_scale
        lam_l = ll_base * goal_scale
        damp = max(0.20, 0.58 - 0.065 * bi)
        weights = []
        for gw, gl in PAIRS:
            w = _poisson_pmf(lam_w, gw) * _poisson_pmf(lam_l, gl)
            if gw - gl >= 4:
                w *= math.exp(-damp * (gw - gl - 3))
            weights.append(w)
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


def build_scorer_weights(sharpness=0.11):
    return [max(1, min(255, int(round(120.0 * math.exp(-sharpness * (2 * i)))))) for i in range(24)]


def build_assist_weights(sharpness=0.045):
    return [max(1, min(255, int(round(120.0 * math.exp(-sharpness * (4 * i)))))) for i in range(24)]


def build_card_y_cdf(yellow_avg=1.7):
    if yellow_avg <= 0:
        return [255, 255, 255, 255, 255]
    lam = yellow_avg
    weights = [_poisson_pmf(lam, k) for k in range(5)]
    total = sum(weights)
    cdf = []
    acc = 0.0
    for k, w in enumerate(weights):
        acc += w / total
        val = 255 if k == 4 else min(255, max(0, int(round(acc * 255.0))))
        if cdf and val < cdf[-1]:
            val = cdf[-1]
        cdf.append(val)
    cdf[-1] = 255
    return cdf


def compute_rating(res, side, gf, ga, pos, goals, assists, rand_val, *, yellows=0, red=0, settings=None):
    """Exact Python mirror of RATINGS_HOOK (returns integer tenths 0..100)."""
    s = dict(DEFAULT_SETTINGS)
    if settings:
        s.update(settings)
    if res == 2:
        base = int(round(s["RATING_BASE"][1] * 10))
    elif res == side:
        base = int(round(s["RATING_BASE"][0] * 10))
    else:
        base = int(round(s["RATING_BASE"][2] * 10))

    gd = max(-4, min(4, gf - ga))
    gd_num = int(round(s["RATING_GD"] * 2))
    rating = base + int((gd * gd_num) / 2)

    if ga == 0:
        rating += int(round(s["RATING_CLEAN_SHEET"][0] * 10)) if pos <= 3 else int(round(s["RATING_CLEAN_SHEET"][1] * 10))
    elif ga >= 3 and pos <= 2:
        rating -= min(3, ga - 2)

    rating += goals * int(round(s["RATING_GOAL"] * 10))
    rating += assists * int(round(s["RATING_ASSIST"] * 10))

    if red:
        rating -= int(round(s["RATING_RED"] * 10))
    else:
        rating -= yellows * int(round(s["RATING_YELLOW"] * 10))

    r_var = int(round(s["RATING_VARIANCE"] * 10))
    rating += (rand_val - r_var)
    r_min = int(round(s["RATING_RANGE"][0] * 10))
    r_max = int(round(s["RATING_RANGE"][1] * 10))
    return max(r_min, min(r_max, rating))


def pack_tables(settings=None):
    """Pack CAVE tables (Plan A) as bytes."""
    s = dict(DEFAULT_SETTINGS)
    if settings:
        s.update(settings)
    scope_int = 1 if s["SCOPE"] == "skip_only" else 0
    home_adv_int = int(round(s["HOME_ADVANTAGE"]))
    cap_div = int(round(1.0 / s["CAPTAIN_WEIGHT"])) if s["CAPTAIN_WEIGHT"] > 0 else 0
    cfg = struct.pack("<IiII", scope_int, home_adv_int, cap_div, 0x4D4C5335)  # "MLS5"

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


def pack_data_d(settings=None):
    """Pack CAVE_D (144 bytes)."""
    s = dict(DEFAULT_SETTINGS)
    if settings:
        s.update(settings)
    r_win, r_draw, r_loss = (int(round(x * 10)) for x in s["RATING_BASE"])
    r_gd_num = int(round(s["RATING_GD"] * 2))
    r_cs_def, r_cs_att = (int(round(x * 10)) for x in s["RATING_CLEAN_SHEET"])
    r_goal = int(round(s["RATING_GOAL"] * 10))
    r_assist = int(round(s["RATING_ASSIST"] * 10))
    r_var = int(round(s["RATING_VARIANCE"] * 10))
    r_min, r_max = (int(round(x * 10)) for x in s["RATING_RANGE"])
    r_ga_pen_cap = 3

    cfg_r = struct.pack(
        "<12I",
        r_win, r_draw, r_loss, r_gd_num,
        r_cs_def, r_cs_att, r_goal, r_assist,
        r_var, r_min, r_max, r_ga_pen_cap,
    )
    cfg_s = struct.pack(
        "<3I",
        1 if s["SCORERS"] else 0,
        1 if s["ASSISTS"] else 0,
        int(round(s["UNASSISTED_PCT"])),
    )
    sw = bytes(build_scorer_weights(s["SCORER_SHARPNESS"]))
    aw = bytes(build_assist_weights(s["ASSIST_SHARPNESS"]))
    cfg_v3 = struct.pack(
        "<IIIII",
        int(round(s["RATING_YELLOW"] * 10)),
        int(round(s["RATING_RED"] * 10)),
        int(round(s["ET_GOAL_SCALE"] * 100)),
        int(round(50 + s["PK_HOME_BIAS"])),
        int(round(s["PK_OVR_WEIGHT"] * 10)),
    )
    red_pct = bytes([int(round(s["RED_PCT"]))])
    cy = bytes(build_card_y_cdf(s["YELLOW_AVG"]))
    cp = bytes(DEFAULT_CARD_POS_W)
    out = cfg_r + cfg_s + sw + aw + cfg_v3 + red_pct + cy + cp
    assert len(out) == CAVE_D_SIZE
    return out


def pack_data_d2(settings=None):
    """Pack CAVE_D2 (40 bytes)."""
    s = dict(DEFAULT_SETTINGS)
    if settings:
        s.update(settings)
    inj_min = int(round(s["INJURY_DAYS"][0]))
    inj_max = int(round(s["INJURY_DAYS"][1]))
    cond_ovr = [int(round(x)) for x in s["CONDITION_OVR"]]
    out = struct.pack(
        "<5I4B5b3x2I",
        1 if s["CONDITION_STRENGTH"] else 0,
        int(round(s["FATIGUE_THRESHOLD"])),
        int(round(s["FATIGUE_PENALTY"])),
        1 if s["STAMINA_FATIGUE"] else 0,
        int(round(s["STAMINA_WEIGHT"] * 10)),
        int(round(s["INJURY_PCT"])),
        inj_min,
        inj_max - inj_min + 1,
        1 if s["CARDS"] else 0,
        *cond_ovr,
        1 if s["SMART_SUBS"] else 0,
        1 if s["LINEUP_STRENGTH"] else 0,
    )
    assert len(out) == CAVE_D2_SIZE
    return out


def compute_eff_ovr(players, *, settings=None):
    """Exact Python mirror of eff_strength top-11 calculation.
    players: iterable of (base_ovr, arrow, fitness, eligible).
    """
    s = dict(DEFAULT_SETTINGS)
    if settings:
        s.update(settings)
    thresh = int(round(s["FATIGUE_THRESHOLD"]))
    pen_max = int(round(s["FATIGUE_PENALTY"]))
    cond_ovr = [int(round(x)) for x in s["CONDITION_OVR"]]
    scores = []
    for base_ovr, arrow, fit, eligible in players:
        if not eligible:
            continue
        p = base_ovr
        if 0 <= arrow <= 4:
            p += cond_ovr[arrow]
        if fit < thresh and thresh > 0:
            p -= ((thresh - fit) * pen_max + (thresh >> 1)) // thresh
        p = max(30, min(109, p))
        scores.append(p)
    if not scores:
        return None
    scores.sort(reverse=True)
    top = scores[:11]
    total = sum(top)
    if len(top) < 11:
        total += (11 - len(top)) * 40
    return max(40, min(99, (total + 5) // 11))


def compute_fatigue_loss(minutes, stamina, pos, *, extra_time=False, stamina_weight=1.0):
    """Exact Python mirror of FATIGUE_HOOK fitness loss."""
    if minutes <= 0:
        return 0
    mins = minutes + 30 if (extra_time and minutes <= 90) else minutes
    st = 75 if stamina == 0 else max(40, min(99, stamina))
    w_x10 = int(round(stamina_weight * 10))
    diff = (75 - st) * w_x10
    # x86 idiv truncates toward zero
    adj = int(diff / 10)
    sf = max(50, min(150, 100 + adj))
    loss = (mins * 3 * sf + 500) // 1000
    if pos == 0 and loss > 0:
        loss = (loss * 9) // 10
    return loss


# =====================================================================
# x86 assembly & verified machine-code bytes
# =====================================================================

def assemble():
    """Assemble all routines across CAVE, CAVE_ET, CAVE_C, and CAVE_PK with Keystone."""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32

    ks = Ks(KS_ARCH_X86, KS_MODE_32)

    def asm(src, base):
        enc, _ = ks.asm(src, base)
        return bytes(enc)

    # ---- CAVE (.xcode tail) ----
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

    # ---- CAVE_ET (.reloc page): eff_strength, player_eff_ovr, smart_subs, et, outcome ----
    # Note: eff_strength stays at CAVE_ET (0x047d5040). Assemble eff_strength in 2 passes
    # so it can call player_eff_ovr placed immediately after it.
    eff_addr = CAVE_ET

    def make_eff_src(peo_target):
        return f"""
        push ebp
        mov ebp, esp
        sub esp, 104
        push ebx
        push esi
        push edi
        mov dword ptr [ebp - 4], 6
        mov dword ptr [ebp - 8], edx
        movzx eax, word ptr [ecx]
        mov dword ptr [ebp - 12], eax
        push 0
        lea eax, [ebp - 4]
        push eax
        lea eax, [ebp - 8]
        push eax
        call 0x{TEAM_STRENGTH:08x}
        add esp, 12
        movzx ebx, al
        mov eax, dword ptr [0x{CFG_V5_COND_STRENGTH:08x}]
        or eax, dword ptr [0x{CFG_V6_LINEUP_STRENGTH:08x}]
        jz eff_ret_base
        call 0x{MODE_OBJ:08x}
        mov eax, dword ptr [eax + 0x30]
        mov dword ptr [ebp - 16], eax
        push dword ptr [ebp - 8]
        mov ecx, eax
        call 0x{TEAM_RECORD:08x}
        test eax, eax
        jz eff_ret_base
        mov edx, dword ptr [eax + 0x328]
        shr edx, 9
        and edx, 0x7f
        jz eff_ret_base
        cmp edx, 32
        jbe n_ok
        mov edx, 32
    n_ok:
        mov dword ptr [ebp - 20], edx
        mov dword ptr [ebp - 36], eax
        add eax, 0xf8
        mov dword ptr [ebp - 40], eax
        mov dword ptr [ebp - 44], ebx

        cmp dword ptr [0x{CFG_V6_LINEUP_STRENGTH:08x}], 0
        je squad_top11
        cmp edx, 11
        jb squad_top11

        lea eax, [ebp - 32]
        push eax
        mov ecx, dword ptr [ebp - 36]
        call 0x{TEAM_TACTICS_ID:08x}
        push dword ptr [ebp - 28]
        push dword ptr [ebp - 32]
        mov ecx, dword ptr [ebp - 16]
        call 0x{TACTICS_REC:08x}
        test eax, eax
        jz squad_top11
        mov edx, dword ptr [ebp - 16]
        add edx, 0x{TACTICS_SENTINEL_OFF:08x}
        cmp eax, edx
        je squad_top11

        xor edx, edx
        xor ecx, ecx
    xi_val_loop:
        movzx edi, byte ptr [eax + ecx + 0x248]
        cmp edi, dword ptr [ebp - 20]
        jae squad_top11
        bt edx, edi
        jc squad_top11
        bts edx, edi
        inc ecx
        cmp ecx, 11
        jb xi_val_loop

        mov dword ptr [ebp - 48], eax
        mov dword ptr [ebp - 52], edx
        xor eax, eax
        mov dword ptr [ebp - 24], eax
        mov dword ptr [ebp - 56], eax
        mov dword ptr [ebp - 60], eax
        xor esi, esi
    xi_start_loop:
        mov eax, dword ptr [ebp - 48]
        movzx ecx, byte ptr [eax + esi + 0x248]
        mov eax, dword ptr [ebp - 40]
        lea eax, [eax + ecx*8]
        mov ecx, dword ptr [eax]
        mov edx, dword ptr [eax + 4]
        mov dword ptr [ebp - 32], ecx
        mov dword ptr [ebp - 28], edx
        push edx
        push ecx
        mov ecx, dword ptr [ebp - 16]
        call 0x{RECORD_BY_ID:08x}
        test eax, eax
        jz xi_missing
        mov edi, eax
        lea eax, [ebp - 12]
        push eax
        lea eax, [ebp - 32]
        push eax
        call 0x{PLAYER_ELIG:08x}
        add esp, 8
        test al, al
        jz xi_missing
        mov eax, dword ptr [ebp - 48]
        movzx eax, byte ptr [eax + esi + 0x68]
        cmp eax, 12
        ja xi_pos_nat
        test esi, esi
        jz xi_pos_ok
        test eax, eax
        jnz xi_pos_ok
    xi_pos_nat:
        mov eax, 13
    xi_pos_ok:
        mov ecx, edi
        lea edx, [ebp - 32]
        call 0x{peo_target:08x}
        add dword ptr [ebp - 56], eax
        inc dword ptr [ebp - 24]
        jmp xi_start_next
    xi_missing:
        inc dword ptr [ebp - 60]
    xi_start_next:
        inc esi
        cmp esi, 11
        jb xi_start_loop

        cmp dword ptr [ebp - 60], 0
        je xi_finish
        lea edi, [ebp - 104]
        xor eax, eax
        mov ecx, dword ptr [ebp - 60]
        rep stosd
        xor esi, esi
    xi_bench_loop:
        cmp esi, dword ptr [ebp - 20]
        jae xi_bench_collect
        bt dword ptr [ebp - 52], esi
        jc xi_bench_next
        mov eax, dword ptr [ebp - 40]
        lea eax, [eax + esi*8]
        mov ecx, dword ptr [eax]
        mov edx, dword ptr [eax + 4]
        mov dword ptr [ebp - 32], ecx
        mov dword ptr [ebp - 28], edx
        push edx
        push ecx
        mov ecx, dword ptr [ebp - 16]
        call 0x{RECORD_BY_ID:08x}
        test eax, eax
        jz xi_bench_next
        mov edi, eax
        lea eax, [ebp - 12]
        push eax
        lea eax, [ebp - 32]
        push eax
        call 0x{PLAYER_ELIG:08x}
        add esp, 8
        test al, al
        jz xi_bench_next
        mov ecx, edi
        lea edx, [ebp - 32]
        mov eax, 13
        call 0x{peo_target:08x}
        mov ebx, eax
        xor ecx, ecx
        xor edi, edi
        mov edx, dword ptr [ebp - 104]
    xi_min_scan:
        inc ecx
        cmp ecx, dword ptr [ebp - 60]
        jae xi_min_done
        mov eax, dword ptr [ebp + ecx*4 - 104]
        cmp eax, edx
        jge xi_min_scan
        mov edx, eax
        mov edi, ecx
        jmp xi_min_scan
    xi_min_done:
        cmp ebx, edx
        jle xi_bench_next
        mov dword ptr [ebp + edi*4 - 104], ebx
    xi_bench_next:
        inc esi
        jmp xi_bench_loop
    xi_bench_collect:
        xor ecx, ecx
    xi_coll_loop:
        cmp ecx, dword ptr [ebp - 60]
        jae xi_finish
        mov eax, dword ptr [ebp + ecx*4 - 104]
        test eax, eax
        jz xi_coll_next
        add dword ptr [ebp - 56], eax
        inc dword ptr [ebp - 24]
    xi_coll_next:
        inc ecx
        jmp xi_coll_loop
    xi_finish:
        mov edx, dword ptr [ebp - 24]
        test edx, edx
        jnz xi_has_avail
        mov eax, dword ptr [ebp - 44]
        jmp eff_ret
    xi_has_avail:
        mov eax, dword ptr [ebp - 56]
        cmp edx, 11
        jae sum_ready
        mov ecx, 11
        sub ecx, edx
        imul ecx, ecx, 40
        add eax, ecx
        jmp sum_ready

    squad_top11:
        lea edi, [ebp - 104]
        xor eax, eax
        mov ecx, 11
        rep stosd
        mov dword ptr [ebp - 24], eax
        mov esi, dword ptr [ebp - 40]
        xor ebx, ebx
    eff_loop:
        cmp ebx, dword ptr [ebp - 20]
        jae eff_sum
        mov ecx, dword ptr [esi]
        mov edx, dword ptr [esi + 4]
        add esi, 8
        mov dword ptr [ebp - 32], ecx
        mov dword ptr [ebp - 28], edx
        push edx
        push ecx
        mov ecx, dword ptr [ebp - 16]
        call 0x{RECORD_BY_ID:08x}
        test eax, eax
        jz eff_next
        mov edi, eax
        lea eax, [ebp - 12]
        push eax
        lea eax, [ebp - 32]
        push eax
        call 0x{PLAYER_ELIG:08x}
        add esp, 8
        test al, al
        jz eff_next
        mov ecx, edi
        lea edx, [ebp - 32]
        mov eax, 13
        call 0x{peo_target:08x}
        push ebx
        mov ebx, eax
        xor ecx, ecx
        xor edi, edi
        mov edx, dword ptr [ebp - 104]
    min_scan:
        inc ecx
        cmp ecx, 11
        jae min_done
        mov eax, dword ptr [ebp + ecx*4 - 104]
        cmp eax, edx
        jge min_scan
        mov edx, eax
        mov edi, ecx
        jmp min_scan
    min_done:
        cmp ebx, edx
        jle eff_cnt
        mov dword ptr [ebp + edi*4 - 104], ebx
    eff_cnt:
        pop ebx
        inc dword ptr [ebp - 24]
    eff_next:
        inc ebx
        jmp eff_loop

    eff_sum:
        mov edx, dword ptr [ebp - 24]
        test edx, edx
        jnz has_avail
        mov eax, dword ptr [ebp - 44]
        jmp eff_ret
    has_avail:
        xor eax, eax
        xor ecx, ecx
    sum_loop:
        add eax, dword ptr [ebp + ecx*4 - 104]
        inc ecx
        cmp ecx, 11
        jb sum_loop
        cmp edx, 11
        jae sum_ready
        mov ecx, 11
        sub ecx, edx
        imul ecx, ecx, 40
        add eax, ecx
    sum_ready:
        add eax, 5
        xor edx, edx
        mov ecx, 11
        div ecx
        cmp eax, 40
        jge ovr_lo
        mov eax, 40
    ovr_lo:
        cmp eax, 99
        jle eff_ret
        mov eax, 99
        jmp eff_ret
    eff_ret_base:
        mov eax, ebx
    eff_ret:
        pop edi
        pop esi
        pop ebx
        mov esp, ebp
        pop ebp
        ret
    """

    eff_pass1 = asm(make_eff_src(CAVE_ET + 0x300), eff_addr)
    peo_addr = (eff_addr + len(eff_pass1) + 3) & ~3
    eff_bytes = asm(make_eff_src(peo_addr), eff_addr)
    assert len(eff_bytes) == len(eff_pass1)

    # player_eff_ovr(ecx=player_ptr, edx=&player_id, eax=pos) -> eax in [30, 109]
    peo_src = f"""
        push ebx
        push esi
        push edi
        push eax
        mov esi, ecx
        mov eax, esp
        push 2
        push eax
        push edx
        call 0x{PLAYER_OVR:08x}
        add esp, 12
        movzx ebx, al
        cmp dword ptr [0x{CFG_V5_COND_STRENGTH:08x}], 0
        je peo_clamp
        mov eax, dword ptr [esi + 0x1c]
        mov ecx, eax
        shr ecx, 21
        and ecx, 7
        cmp ecx, 4
        ja peo_no_cond
        movsx edx, byte ptr [ecx + 0x{CFG_V5_COND_OVR:08x}]
        add ebx, edx
    peo_no_cond:
        and eax, 0x7f
        mov ecx, dword ptr [0x{CFG_V5_FATIGUE_THRESH:08x}]
        test ecx, ecx
        jz peo_clamp
        cmp eax, ecx
        jae peo_clamp
        mov edx, ecx
        sub edx, eax
        imul edx, dword ptr [0x{CFG_V5_FATIGUE_PEN:08x}]
        mov eax, ecx
        shr eax, 1
        add eax, edx
        xor edx, edx
        div ecx
        sub ebx, eax
    peo_clamp:
        cmp ebx, 30
        jge peo_lo
        mov ebx, 30
    peo_lo:
        cmp ebx, 109
        jle peo_hi
        mov ebx, 109
    peo_hi:
        mov eax, ebx
        add esp, 4
        pop edi
        pop esi
        pop ebx
        ret
    """
    peo_bytes = asm(peo_src, peo_addr)

    # ---- SMART_SUBS_HOOK (in CAVE_ET, hooked at 0x037080d9 -> returns to 0x037080e8) ----
    # Entry: [esp]=&[ebp-0x14c], [esp+4]=&[ebp-0x145], [ebp-0x14c]=player_ptr,
    #        [ebp-0x1a4]=player_id, [ebp+8]=match_ptr, [ebp-0x160]=mode_data, ebx=squad_count
    smart_subs_addr = (peo_addr + len(peo_bytes) + 3) & ~3
    smart_subs_src = f"""
        cmp dword ptr [0x{CFG_V6_SMART_SUBS:08x}], 0
        je ss_vanilla
        mov ecx, dword ptr [ebp + 8]
        mov edx, dword ptr [ebp - 0x160]
        call 0x{chk_addr:08x}
        test al, al
        jz ss_vanilla
        mov ecx, dword ptr [ebp - 0x14c]
        lea edx, [ebp - 0x1a4]
        mov eax, 13
        call 0x{peo_addr:08x}
        push eax
        mov dword ptr [ebp - 0x14c], 4
        lea eax, [ebp - 0x145]
        push eax
        lea eax, [ebp - 0x14c]
        push eax
        call 0x{MODE_RANDOM:08x}
        add esp, 8
        pop ecx
        add eax, ecx
        cmp eax, 255
        jbe ss_ret
        mov eax, 255
        jmp ss_ret
    ss_vanilla:
        mov dword ptr [ebp - 0x14c], 0x64
        call 0x{MODE_RANDOM:08x}
    ss_ret:
        jmp 0x{SMART_SUBS_RET:08x}
    """
    smart_subs_bytes = asm(smart_subs_src, smart_subs_addr)

    # ---- SCORE_HOOK (in CAVE .xcode) ----
    score_addr = (rand_addr + len(rand_bytes) + 3) & ~3
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

        mov eax, dword ptr [0x{CFG_V5_COND_STRENGTH:08x}]
        or eax, dword ptr [0x{CFG_V6_LINEUP_STRENGTH:08x}]
        jz score_ovr_ok
        push edx
        mov ecx, ebx
        mov edx, dword ptr [ebx + 0xc]
        call 0x{eff_addr:08x}
        mov esi, eax
        mov ecx, ebx
        mov edx, dword ptr [ebx + 0x10]
        call 0x{eff_addr:08x}
        mov edi, eax
        pop edx
    score_ovr_ok:
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

    pk_table_addr = PK_TABLE_ADDR
    card_adj_addr = CARD_ADJ_ADDR
    card_adj_src = f"""
        mov ecx, dword ptr [esi + 0xc]
        test ecx, 0x40000
        jz adj_yellow
        sub eax, dword ptr [ebx + 0x70]
        ret
    adj_yellow:
        shr ecx, 19
        and ecx, 3
        imul ecx, dword ptr [ebx + 0x6c]
        sub eax, ecx
        ret
    """
    card_adj_bytes = asm(card_adj_src, card_adj_addr)
    assert card_adj_addr + len(card_adj_bytes) <= pk_table_addr, (hex(card_adj_addr + len(card_adj_bytes)), hex(pk_table_addr))

    # ---- RATINGS_HOOK (in CAVE .xcode) ----
    ratings_addr = (score_addr + len(score_bytes) + 3) & ~3
    ratings_src = f"""
        push eax
        push ebx
        mov eax, 0x{MODE_OBJ:08x}
        call eax
        mov edx, dword ptr [eax + 0x30]
        mov ecx, dword ptr [ebp + 0x10]
        mov eax, 0x{chk_addr:08x}
        call eax
        test al, al
        jnz do_ratings
        pop ebx
        pop eax
        mov ecx, dword ptr [ebp + 8]
        cmp ecx, 2
        jmp 0x{RATINGS_FALLBACK:08x}

    do_ratings:
        mov ebx, 0x{CAVE_D:08x}
        mov esi, dword ptr [esp + 4]
        mov edx, dword ptr [ebp + 0x10]
        movzx eax, byte ptr [edx + 0x14]
        movzx ecx, byte ptr [edx + 0x17]
        cmp dword ptr [ebp + 0xc], 0
        je goals_ok
        xchg eax, ecx
    goals_ok:
        mov edx, eax
        sub edx, ecx
        cmp edx, -4
        jge gd_ge
        mov edx, -4
    gd_ge:
        cmp edx, 4
        jle gd_le
        mov edx, 4
    gd_le:
        imul edx, dword ptr [ebx + 0x0c]
        mov eax, edx
        cdq
        sub eax, edx
        sar eax, 1
        push ecx
        mov ecx, dword ptr [ebp + 8]
        cmp ecx, 2
        je r_draw
        cmp ecx, dword ptr [ebp + 0xc]
        je r_win
        add eax, dword ptr [ebx + 0x08]
        jmp r_base_ok
    r_draw:
        add eax, dword ptr [ebx + 0x04]
        jmp r_base_ok
    r_win:
        add eax, dword ptr [ebx + 0x00]
    r_base_ok:
        pop ecx
        mov edx, dword ptr [esi + 0xc]
        shr edx, 14
        and edx, 0xf
        test ecx, ecx
        jnz not_cs
        cmp edx, 3
        jbe cs_def
        add eax, dword ptr [ebx + 0x14]
        jmp after_cs
    cs_def:
        add eax, dword ptr [ebx + 0x10]
        jmp after_cs
    not_cs:
        cmp ecx, 3
        jb after_cs
        cmp edx, 2
        ja after_cs
        sub ecx, 2
        cmp ecx, dword ptr [ebx + 0x2c]
        jbe ga_ok
        mov ecx, dword ptr [ebx + 0x2c]
    ga_ok:
        sub eax, ecx
    after_cs:
        movzx ecx, byte ptr [esi + 8]
        imul ecx, dword ptr [ebx + 0x18]
        add eax, ecx
        movzx ecx, byte ptr [esi + 9]
        imul ecx, dword ptr [ebx + 0x1c]
        add eax, ecx
        call 0x{card_adj_addr:08x}

        push eax
        mov ecx, dword ptr [ebx + 0x20]
        lea ecx, [ecx*2 + 1]
        mov eax, 0x{rand_addr:08x}
        call eax
        pop edx
        sub eax, dword ptr [ebx + 0x20]
        add edx, eax

        cmp edx, dword ptr [ebx + 0x24]
        jge min_ok
        mov edx, dword ptr [ebx + 0x24]
    min_ok:
        cmp edx, dword ptr [ebx + 0x28]
        jle max_ok
        mov edx, dword ptr [ebx + 0x28]
    max_ok:
        mov cl, dl
        mov eax, esi
        pop ebx
        add esp, 4
        jmp 0x{RATINGS_DONE:08x}
    """
    ratings_bytes = asm(ratings_src, ratings_addr)

    # ---- SCORER_HOOK (in CAVE .xcode) ----
    scorer_addr = (ratings_addr + len(ratings_bytes) + 3) & ~3
    scorer_src = f"""
        mov edx, ecx
        mov ecx, dword ptr [ebp + 0xc]
        mov eax, 0x{chk_addr:08x}
        call eax
        test al, al
        jz s_fallback
        cmp byte ptr [ebp + 8], 0
        je chk_assist
        cmp dword ptr [0x{CFG_S_SCORERS_ON:08x}], 0
        jne do_pick
    s_fallback:
        xor ecx, ecx
        mov dword ptr [ebp - 0x1c], ecx
        jmp 0x{SCORER_FALLBACK:08x}
    chk_assist:
        cmp dword ptr [0x{CFG_S_ASSISTS_ON:08x}], 0
        je s_fallback
        mov ecx, 100
        mov eax, 0x{rand_addr:08x}
        call eax
        cmp eax, dword ptr [0x{CFG_S_UNASSISTED:08x}]
        jae do_pick
        jmp 0x{SCORER_NONE:08x}

    do_pick:
        mov eax, dword ptr [ebp + 0x10]
        mov esi, dword ptr [eax]
        mov eax, dword ptr [eax + 4]
        cmp esi, eax
        jb has_entries
        jmp 0x{SCORER_NONE:08x}

    has_entries:
        movzx edx, byte ptr [esi + 8]
        push edx
        push eax
        sub esp, 24
        xor ebx, ebx
        xor edi, edi
        mov ecx, esi
    w_loop:
        cmp ecx, dword ptr [esp + 24]
        jae w_done
        cmp ebx, 11
        jae w_done
        movzx eax, byte ptr [ecx + 8]
        test al, al
        jz w_zero
        cmp byte ptr [ebp + 8], 0
        jne w_calc
        mov edx, dword ptr [ebp + 0x14]
        mov dx, word ptr [edx]
        cmp dx, word ptr [ecx]
        jne w_calc
        mov edx, dword ptr [ebp + 0x14]
        mov edx, dword ptr [edx + 4]
        cmp edx, dword ptr [ecx + 4]
        je w_zero
    w_calc:
        mov edx, dword ptr [esp + 28]
        sub edx, eax
        jns gap_pos
        xor edx, edx
    gap_pos:
        lea eax, [0x{SCORER_W:08x}]
        shr edx, 1
        cmp byte ptr [ebp + 8], 0
        jne gap_clamped
        shr edx, 1
        add eax, 24
    gap_clamped:
        cmp edx, 23
        jbe idx_ok
        mov edx, 23
    idx_ok:
        movzx eax, byte ptr [eax + edx]
        jmp w_add
    w_zero:
        xor eax, eax
    w_add:
        add edi, eax
        mov word ptr [esp + ebx*2], di
        inc ebx
        add ecx, 12
        jmp w_loop

    w_done:
        test edi, edi
        jnz pick_draw
        add esp, 32
        jmp 0x{SCORER_NONE:08x}

    pick_draw:
        mov ecx, edi
        mov eax, 0x{rand_addr:08x}
        call eax
        xor ecx, ecx
    pick_scan:
        movzx edx, word ptr [esp + ecx*2]
        cmp eax, edx
        jb pick_found
        inc ecx
        cmp ecx, ebx
        jb pick_scan
        dec ecx
    pick_found:
        imul ecx, ecx, 12
        add esi, ecx
        mov edi, dword ptr [esi + 4]
        mov esi, dword ptr [esi]
        mov dword ptr [ebp - 0x28], esi
        mov dword ptr [ebp - 0x24], edi
        add esp, 32
        jmp 0x{SCORER_PICKED:08x}
    """
    scorer_bytes = asm(scorer_src, scorer_addr)
    cave_end_addr = scorer_addr + len(scorer_bytes)
    assert cave_end_addr <= CAVE_END, f"CAVE overflow: {hex(cave_end_addr)} > {hex(CAVE_END)}"

    # ---- CAVE_ET (.reloc page): ET_HOOK & OUTCOME_HOOK ----
    # Entry from 0x037062ed: ebx, esi, edi pushed; edi = [ebp-0xc] = match+0x15; [ebp+0xc] = match_ptr
    et_addr = (smart_subs_addr + len(smart_subs_bytes) + 3) & ~3
    et_src = f"""
        call 0x{MODE_OBJ:08x}
        mov edx, dword ptr [eax + 0x30]
        mov ecx, dword ptr [ebp + 0xc]
        call 0x{chk_addr:08x}
        test al, al
        jnz do_et
        mov ebx, 3
        jmp 0x{ET_FALLBACK:08x}

    do_et:
        mov eax, dword ptr [ebp + 0xc]
        mov ecx, eax
        mov edx, dword ptr [eax + 0xc]
        call 0x{eff_addr:08x}
        mov ebx, eax
        mov eax, dword ptr [ebp + 0xc]
        mov ecx, eax
        mov edx, dword ptr [eax + 0x10]
        call 0x{eff_addr:08x}
        sub ebx, eax
        add ebx, dword ptr [0x{CFG_HOME_ADV:08x}]
        cmp ebx, -20
        jge et_d_lo
        mov ebx, -20
    et_d_lo:
        cmp ebx, 20
        jle et_d_hi
        mov ebx, 20
    et_d_hi:
        xor esi, esi
    et_loop:
        imul eax, ebx, 3
        add eax, 230
        imul eax, dword ptr [0x{CFG_ET_SCALE_X100:08x}]
        cdq
        mov ecx, 100
        idiv ecx
        cmp eax, 60
        jge p1_lo
        mov eax, 60
    p1_lo:
        cmp eax, 480
        jle p1_hi
        mov eax, 480
    p1_hi:
        push eax
        mov ecx, 1000
        call 0x{rand_addr:08x}
        pop ecx
        mov edx, ecx
        shr edx, 3
        cmp eax, edx
        jb et_g2
        cmp eax, ecx
        sbb eax, eax
        neg eax
        jmp et_store
    et_g2:
        mov eax, 2
    et_store:
        mov dword ptr [ebp + esi*4 - 0x14], eax
        mov byte ptr [edi], al
        add edi, 3
        neg ebx
        inc esi
        cmp esi, 2
        jb et_loop
        mov ebx, dword ptr [ebp - 0x14]
        mov esi, dword ptr [ebp - 0x10]
        jmp 0x{ET_DONE:08x}
    """
    et_bytes = asm(et_src, et_addr)

    outcome_addr = (et_addr + len(et_bytes) + 3) & ~3
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
        mov eax, dword ptr [0x{CFG_V5_COND_STRENGTH:08x}]
        or eax, dword ptr [0x{CFG_V6_LINEUP_STRENGTH:08x}]
        jz use_base_diff
        mov ecx, esi
        mov edx, dword ptr [esi + 0xc]
        call 0x{eff_addr:08x}
        mov ebx, eax
        mov ecx, esi
        mov edx, dword ptr [esi + 0x10]
        call 0x{eff_addr:08x}
        sub ebx, eax
        jmp after_diff

    use_base_diff:
        movzx eax, byte ptr [ebp - 0xd]
        cmp dword ptr [ebp - 0x18], 0
        je diff_pos
        neg eax
    diff_pos:
        mov ebx, eax

    after_diff:
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
    cave_et_end = outcome_addr + len(outcome_bytes)

    # ---- CAVE_PK (.link page): PK_HOOK, card_adj, PK_TABLE, FATIGUE_HOOK, INJURY_FN ----
    # Entry from 0x037063bb: [esp+4]=out_res, [esp+8]=match_ptr
    pk_addr = CAVE_PK
    pk_src = f"""
        push ebp
        mov ebp, esp
        push ebx
        push esi
        call 0x{MODE_OBJ:08x}
        mov edx, dword ptr [eax + 0x30]
        mov ecx, dword ptr [ebp + 0xc]
        call 0x{chk_addr:08x}
        test al, al
        jnz do_pk
        pop esi
        pop ebx
        pop ebp
        push ebp
        mov ebp, esp
        sub esp, 8
        jmp 0x{PK_FALLBACK:08x}

    do_pk:
        mov eax, dword ptr [ebp + 0xc]
        mov ecx, eax
        mov edx, dword ptr [eax + 0xc]
        call 0x{eff_addr:08x}
        mov ebx, eax
        mov eax, dword ptr [ebp + 0xc]
        mov ecx, eax
        mov edx, dword ptr [eax + 0x10]
        call 0x{eff_addr:08x}
        sub ebx, eax
        cmp ebx, -20
        jge pk_d_lo
        mov ebx, -20
    pk_d_lo:
        cmp ebx, 20
        jle pk_d_hi
        mov ebx, 20
    pk_d_hi:
        mov eax, ebx
        imul eax, dword ptr [0x{CFG_PK_OVR_TENTHS:08x}]
        cdq
        mov ecx, 10
        idiv ecx
        add eax, dword ptr [0x{CFG_PK_BASE_PCT:08x}]
        cmp eax, 15
        jge pk_p_lo
        mov eax, 15
    pk_p_lo:
        cmp eax, 85
        jle pk_p_hi
        mov eax, 85
    pk_p_hi:
        mov ebx, eax
        mov ecx, 100
        call 0x{rand_addr:08x}
        cmp eax, ebx
        setae dl
        movzx edx, dl
        mov esi, dword ptr [ebp + 8]
        mov dword ptr [esi], edx

        mov ecx, 100
        call 0x{rand_addr:08x}
        xor ecx, ecx
    pk_scan:
        cmp al, byte ptr [ecx + 0x{pk_table_addr:08x}]
        jb pk_found
        inc ecx
        cmp ecx, 7
        jb pk_scan
    pk_found:
        movzx eax, byte ptr [ecx + 0x{pk_table_addr + 8:08x}]
        mov cl, al
        shr cl, 4
        and al, 0x0f
        mov edx, dword ptr [ebp + 0xc]
        cmp dword ptr [esi], 0
        jne pk_away
        mov byte ptr [edx + 0x16], cl
        mov byte ptr [edx + 0x19], al
        jmp pk_ret
    pk_away:
        mov byte ptr [edx + 0x19], cl
        mov byte ptr [edx + 0x16], al
    pk_ret:
        pop esi
        pop ebx
        pop ebp
        ret 8
    """
    pk_bytes = asm(pk_src, pk_addr)
    assert pk_addr + len(pk_bytes) <= card_adj_addr, f"CAVE_PK overflow into card_adj: {hex(pk_addr + len(pk_bytes))} > {hex(card_adj_addr)}"

    fatigue_addr = pk_table_addr + PK_TABLE_SIZE
    fatigue_src = f"""
        cmp dword ptr [0x{CFG_V5_STAMINA_ON:08x}], 0
        jne do_fat
        lea ecx, [ebp - 8]
        jmp 0x{FATIGUE_FALLBACK:08x}

    do_fat:
        mov eax, dword ptr [ebp + 0xc]
        mov ebx, dword ptr [eax]
        test ebx, ebx
        jle fat_exit
        cmp ebx, 90
        ja no_et
        mov eax, dword ptr [ebp + 0x10]
        movzx eax, word ptr [eax]
        cmp eax, 0xffff
        je no_et
        push eax
        mov ecx, esi
        call 0x{FIX_RECORD:08x}
        test eax, eax
        jz no_et
        lea ecx, [esi + 0x6f154c]
        cmp eax, ecx
        je no_et
        mov dl, byte ptr [eax + 0x15]
        or dl, byte ptr [eax + 0x18]
        or dl, byte ptr [eax + 0x16]
        or dl, byte ptr [eax + 0x19]
        jz no_et
        add ebx, 30
    no_et:
        mov eax, dword ptr [edi + 0x18]
        shr eax, 7
        and eax, 0x7f
        jnz st_nz
        mov eax, 75
    st_nz:
        cmp eax, 40
        jge st_lo
        mov eax, 40
    st_lo:
        cmp eax, 99
        jle st_hi
        mov eax, 99
    st_hi:
        mov ecx, 75
        sub ecx, eax
        imul ecx, dword ptr [0x{CFG_V5_STAMINA_W_X10:08x}]
        mov eax, ecx
        cdq
        mov ecx, 10
        idiv ecx
        add eax, 100
        cmp eax, 50
        jge sf_lo
        mov eax, 50
    sf_lo:
        cmp eax, 150
        jle sf_hi
        mov eax, 150
    sf_hi:
        imul ebx, ebx, 3
        imul eax, ebx
        add eax, 500
        xor edx, edx
        mov ecx, 1000
        div ecx
        mov ecx, dword ptr [edi + 4]
        shr ecx, 28
        test ecx, ecx
        jnz not_gk
        test eax, eax
        jz not_gk
        imul eax, eax, 9
        xor edx, edx
        mov ecx, 10
        div ecx
    not_gk:
        mov ecx, dword ptr [edi + 0x1c]
        and ecx, 0x7f
        sub ecx, eax
        jns fit_ok
        xor ecx, ecx
    fit_ok:
        push ecx
        push 0x5f
        mov ecx, edi
        call 0x{PLAYER_SET:08x}
    fat_exit:
        jmp 0x{FATIGUE_EXIT:08x}
    """
    fatigue_bytes = asm(fatigue_src, fatigue_addr)

    injury_addr = (fatigue_addr + len(fatigue_bytes) + 3) & ~3
    injury_src = f"""
        cmp byte ptr [0x{CFG_V5_INJURY_PCT:08x}], 0
        je inj_ret0
        mov eax, dword ptr [edx]
        cmp eax, dword ptr [edx + 4]
        jae inj_ret0
        push ebx
        push esi
        push edi
        push ebp
        mov ebp, esp
        sub esp, 80
        mov esi, dword ptr [edx]
        mov edi, dword ptr [edx + 4]
        mov ecx, 100
        call 0x{rand_addr:08x}
        cmp al, byte ptr [0x{CFG_V5_INJURY_PCT:08x}]
        jae inj_done
        call 0x{MODE_OBJ:08x}
        mov ebx, dword ptr [eax + 0x30]
        xor ecx, ecx
        mov dword ptr [ebp - 4], ecx
        mov dword ptr [ebp - 8], ecx
    inj_scan:
        cmp esi, edi
        jae inj_pick
        cmp ecx, 11
        jae inj_pick
        push ecx
        push dword ptr [esi + 4]
        push dword ptr [esi]
        mov ecx, ebx
        call 0x{RECORD_BY_ID:08x}
        pop ecx
        mov dword ptr [ebp + ecx*4 - 52], eax
        xor edx, edx
        test eax, eax
        jz inj_w0
        cmp byte ptr [eax + 2], 0
        jne inj_w0
        inc dword ptr [ebp - 4]
        mov edx, dword ptr [eax + 4]
        shr edx, 28
        jz inj_w0
        movzx edx, byte ptr [eax + 0x23]
        and edx, 3
        cmp edx, 2
        jbe ir_ok
        mov edx, 2
    ir_ok:
        mov eax, 3
        sub eax, edx
        mov edx, dword ptr [ebp + ecx*4 - 52]
        mov edx, dword ptr [edx + 0x1c]
        and edx, 0x7f
        cmp edx, 100
        jbe f_ok
        mov edx, 100
    f_ok:
        push eax
        mov eax, 100
        sub eax, edx
        xor edx, edx
        push ecx
        mov ecx, 25
        div ecx
        pop ecx
        pop edx
        add edx, eax
    inj_w0:
        add dword ptr [ebp - 8], edx
        mov eax, dword ptr [ebp - 8]
        mov word ptr [ebp + ecx*2 - 76], ax
        inc ecx
        add esi, 12
        jmp inj_scan
    inj_pick:
        mov dword ptr [ebp - 80], ecx
        cmp dword ptr [ebp - 4], 7
        jbe inj_done
        mov ecx, dword ptr [ebp - 8]
        test ecx, ecx
        jz inj_done
        call 0x{rand_addr:08x}
        xor ecx, ecx
        mov edx, dword ptr [ebp - 80]
        dec edx
    inj_find:
        cmp ecx, edx
        jae inj_hit
        cmp ax, word ptr [ebp + ecx*2 - 76]
        jb inj_hit
        inc ecx
        jmp inj_find
    inj_hit:
        mov ebx, dword ptr [ebp + ecx*4 - 52]
        test ebx, ebx
        jz inj_done
        movzx ecx, byte ptr [0x{CFG_V5_INJURY_SPAN:08x}]
        call 0x{rand_addr:08x}
        movzx ecx, byte ptr [0x{CFG_V5_INJURY_MIN:08x}]
        add eax, ecx
        push eax
        push 0x5e
        mov ecx, ebx
        call 0x{PLAYER_SET:08x}
    inj_done:
        mov esp, ebp
        pop ebp
        pop edi
        pop esi
        pop ebx
    inj_ret0:
        ret
    """
    injury_bytes = asm(injury_src, injury_addr)
    cave_pk_end = injury_addr + len(injury_bytes)
    assert cave_pk_end <= CAVE_PK_END, f"CAVE_PK overflow: {hex(cave_pk_end)} > {hex(CAVE_PK_END)}"

    # ---- CAVE_C (.trace tail): CARDS_HOOK ----
    # Entry from 0x03708f45 inside fcn_03708de9:
    #   esi = match_ptr, ebx = res, edi = sim_obj, [ebp-0x2c] = home_vec, [ebp-0x1c] = away_vec
    cards_addr = CAVE_C
    cards_src = f"""
        push esi
        push edi
        push ebx
        call 0x{MODE_OBJ:08x}
        mov edx, dword ptr [eax + 0x30]
        mov ecx, esi
        call 0x{chk_addr:08x}
        test al, al
        jz cards_done

        cmp byte ptr [0x{CFG_C_CARDS_ON:08x}], 0
        je chk_inj
        lea eax, [ebp - 0x2c]
        push eax
        call do_team_cards
        lea eax, [ebp - 0x1c]
        push eax
        call do_team_cards
        add esp, 8

    chk_inj:
        cmp byte ptr [0x{CFG_V5_INJURY_PCT:08x}], 0
        je cards_done
        lea edx, [ebp - 0x2c]
        call 0x{injury_addr:08x}
        lea edx, [ebp - 0x1c]
        call 0x{injury_addr:08x}

    cards_done:
        pop ebx
        pop edi
        pop esi
        lea edx, [ebp - 0x2c]
        jmp 0x{CARDS_FALLBACK:08x}

    do_team_cards:
        push ebp
        mov ebp, esp
        push ebx
        push esi
        push edi
        sub esp, 72
        mov eax, dword ptr [ebp + 8]
        mov edi, dword ptr [eax]
        mov eax, dword ptr [eax + 4]
        cmp edi, eax
        jae tc_ret

        xor ebx, ebx
        xor ecx, ecx
    tc_load:
        cmp edi, eax
        jae tc_loaded
        cmp ebx, 11
        jae tc_loaded
        push eax
        push ecx
        push edi
        mov ecx, esi
        call 0x{STAT_REC_BY_ID:08x}
        pop ecx
        mov dword ptr [esp + ebx*4 + 28], eax
        test eax, eax
        jz tc_w0
        mov edx, dword ptr [eax + 0xc]
        shr edx, 14
        and edx, 0xf
        cmp edx, 9
        jbe tc_pos_ok
        mov edx, 9
    tc_pos_ok:
        movzx eax, byte ptr [edx + 0x{CARD_POS_W:08x}]
        jmp tc_w_add
    tc_w0:
        xor eax, eax
    tc_w_add:
        add ecx, eax
        mov word ptr [esp + ebx*2 + 4], cx
        pop eax
        inc ebx
        add edi, 12
        jmp tc_load

    tc_loaded:
        mov dword ptr [esp + 68], ebx
        test ecx, ecx
        jz tc_ret
        push ecx

        mov ecx, 255
        call 0x{rand_addr:08x}
        xor edi, edi
    y_cnt_scan:
        cmp al, byte ptr [edi + 0x{CARD_Y_CDF:08x}]
        jb y_cnt_ok
        inc edi
        cmp edi, 4
        jb y_cnt_scan
    y_cnt_ok:
        pop ebx
        xor esi, esi
    y_loop:
        cmp esi, edi
        jae do_straight_red
        mov ecx, ebx
        call 0x{rand_addr:08x}
        call pick_slot
        mov ecx, dword ptr [esp + eax*4 + 24]
        test ecx, ecx
        jz y_next
        mov edx, dword ptr [ecx + 0xc]
        mov eax, edx
        shr eax, 19
        and eax, 3
        cmp eax, 2
        jae y_next
        test eax, eax
        jz y_give1
        push ecx
        mov ecx, 100
        call 0x{rand_addr:08x}
        pop ecx
        cmp eax, 20
        jae y_next
        mov edx, dword ptr [ecx + 0xc]
        and edx, 0xffe3ffff
        or edx, 0x00140000
        mov dword ptr [ecx + 0xc], edx
        jmp y_next
    y_give1:
        and edx, 0xffe7ffff
        or edx, 0x00080000
        mov dword ptr [ecx + 0xc], edx
    y_next:
        inc esi
        jmp y_loop

    do_straight_red:
        mov ecx, 100
        call 0x{rand_addr:08x}
        cmp al, byte ptr [0x{CFG_C_RED_PCT:08x}]
        jae tc_ret
        mov ecx, ebx
        call 0x{rand_addr:08x}
        call pick_slot
        mov ecx, dword ptr [esp + eax*4 + 24]
        test ecx, ecx
        jz tc_ret
        or dword ptr [ecx + 0xc], 0x40000

    tc_ret:
        add esp, 72
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret

    pick_slot:
        xor ecx, ecx
        mov edx, dword ptr [esp + 72]
    ps_loop:
        cmp ax, word ptr [esp + ecx*2 + 4]
        jb ps_hit
        inc ecx
        cmp ecx, edx
        jb ps_loop
        dec ecx
    ps_hit:
        mov eax, ecx
        ret
    """
    cards_bytes = asm(cards_src, cards_addr)
    cave_c_end = cards_addr + len(cards_bytes)
    assert cave_et_end <= CAVE_ET_END, f"CAVE_ET overflow: {hex(cave_et_end)} > {hex(CAVE_ET_END)}"
    assert cave_c_end <= CAVE_C_END, f"CAVE_C overflow: {hex(cave_c_end)} > {hex(CAVE_C_END)}"

    outcome_patch = asm(f"jmp 0x{outcome_addr:08x}; nop; nop", OUTCOME_SITE)
    score_patch = asm(f"jmp 0x{score_addr:08x}", SCORE_SITE)
    smart_subs_patch = asm(f"jmp 0x{smart_subs_addr:08x}; " + "; ".join(["nop"] * 10), SMART_SUBS_SITE)
    ratings_patch = asm(f"jmp 0x{ratings_addr:08x}; nop", RATINGS_SITE)
    scorer_patch = asm(f"jmp 0x{scorer_addr:08x}; nop; nop; nop", SCORER_SITE)
    et_patch = asm(f"jmp 0x{et_addr:08x}", ET_SITE)
    pk_patch = asm(f"jmp 0x{pk_addr:08x}; nop", PK_SITE)
    cards_patch = asm(f"jmp 0x{cards_addr:08x}; nop", CARDS_SITE)
    fatigue_patch = asm(f"jmp 0x{fatigue_addr:08x}; nop", FATIGUE_SITE)
    ai_fatigue_patch = b"\x90" * 6

    return {
        "chk": (chk_addr, chk_bytes),
        "rand": (rand_addr, rand_bytes),
        "score": (score_addr, score_bytes),
        "ratings": (ratings_addr, ratings_bytes),
        "scorer": (scorer_addr, scorer_bytes),
        "eff_strength": (eff_addr, eff_bytes),
        "player_eff_ovr": (peo_addr, peo_bytes),
        "smart_subs": (smart_subs_addr, smart_subs_bytes),
        "et": (et_addr, et_bytes),
        "outcome": (outcome_addr, outcome_bytes),
        "pk": (pk_addr, pk_bytes),
        "card_adj": (card_adj_addr, card_adj_bytes),
        "fatigue": (fatigue_addr, fatigue_bytes),
        "injury": (injury_addr, injury_bytes),
        "cards": (cards_addr, cards_bytes),
        "cave_end": cave_end_addr,
        "cave_et_end": cave_et_end,
        "cave_pk_end": cave_pk_end,
        "cave_c_end": cave_c_end,
        "outcome_patch": outcome_patch,
        "score_patch": score_patch,
        "smart_subs_patch": smart_subs_patch,
        "ratings_patch": ratings_patch,
        "scorer_patch": scorer_patch,
        "et_patch": et_patch,
        "pk_patch": pk_patch,
        "cards_patch": cards_patch,
        "fatigue_patch": fatigue_patch,
        "ai_fatigue_patch": ai_fatigue_patch,
    }


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
    "score": (
        0x047d3c78,
        "89d98b5030b8dc3b7d04ffd084c0750c8b45088b00b971607003ffe18b4508"
        "8b1083fa020f84a4000000a1604f7d040b05844f7d04741a5289d98b530ce886"
        "13000089c689d98b5310e87a13000089c75a5289f00305543a7d0429f885d274"
        "02f7d831f683f8fa7e1f4683f8ff7e194683f8037e134683f8077e0d4683f80b"
        "7e074683f80f7e01466bf61581c6463b7d04b9ff000000b8603c7d04ffd031c9"
        "0fb6140e39d072064183f91472f20fb681313b7d0488c1c0e904240f5a85d274"
        "07ba59617003ffe2ba10617003ffe2b9ff000000b8603c7d04ffd031c90fb691"
        "2c3b7d0439d072064183f90472ef88c8ba10617003ffe2",
    ),
    "ratings": (
        0x047d3d70,
        "5053b8e5c08103ffd08b50308b4d10b8dc3b7d04ffd084c0750d5b588b4d08"
        "83f902e9a84ff3febb70417d048b7424048b55100fb642140fb64a17837d0c"
        "0074019189c229ca83fafc7d05bafcffffff83fa047e05ba040000000faf53"
        "0c89d09929d0d1f8518b4d0883f902740a3b4d0c740a034308eb07034304eb"
        "020303598b560cc1ea0e83e20f85c9750f83fa037605034314eb1c034310eb"
        "1783f903721283fa02770d83e9023b4b2c76038b4b2c29c80fb64e080faf4b"
        "1801c80fb64e090faf4b1c01c8e8e4220000508b4b208d0c4d01000000b860"
        "3c7d04ffd05a2b432001c23b53247d038b53243b53287e038b532888d189f0"
        "5b83c404e9024ff3fe",
    ),
    "scorer": (
        0x047d3e74,
        "89ca8b4d0cb8dc3b7d04ffd084c0740f807d08007413833da0417d0400752c"
        "31c9894de4e9a030f3fe833da4417d040074edb964000000b8603c7d04ffd0"
        "3b05a8417d047305e92634f3fe8b45108b308b400439c67205e91534f3fe0f"
        "b65608525083ec1831db31ff89f13b4c2418736483fb0b735f0fb6410884c0"
        "7449807d080075168b5514668b12663b11750b8b55148b52043b5104742d8b"
        "54241c29c2790231d28d05ac417d04d1ea807d08007505d1ea83c01883fa17"
        "7605ba170000000fb60410eb0231c001c766893c5c4383c10ceb9685ff7508"
        "83c420e99033f3fe89f9b8603c7d04ffd031c90fb7144c39d072064139d972"
        "f3496bc90c01ce8b7e048b368975d8897ddc83c420e9be32f3fe",
    ),
    "eff_strength": (
        0x047d5040,
        "5589e583ec68535657c745fc060000008955f80fb7018945f46a008d45fc50"
        "8d45f850e8a20a09ff83c40c0fb6d8a1604f7d040b05844f7d040f84e70200"
        "00e8617004ff8b40308945f0ff75f889c1e8d5d804ff85c00f84ca0200008b"
        "9028030000c1ea0983e27f0f84b802000083fa207605ba200000008955ec89"
        "45dc05f80000008945d8895dd4833d844f7d04000f84bc01000083fa0b0f82"
        "b30100008d45e0508b4ddce8ad2c94feff75e4ff75e08b4df0e830d904ff85"
        "c00f84910100008b55f081c264ea5f0039d00f848001000031d231c90fb6bc"
        "08480200003b7dec0f836b0100000fa3fa0f82620100000fabfa4183f90b72"
        "dd8945d08955cc31c08945e88945c88945c431f68b45d00fb68c3048020000"
        "8b45d88d04c88b088b5004894de08955e452518b4df0e8f1d404ff85c07442"
        "89c78d45f4508d45e050e8ec6508ff83c40884c0742c8b45d00fb644306883"
        "f80c770885f6740985c07505b80d00000089f98d55e0e8c00100000145c8ff"
        "45e8eb03ff45c44683fe0b728b837dc4000f849b0000008d7d9831c08b4dc4"
        "f3ab31f63b75ec73720fa375cc72698b45d88d04f08b088b5004894de08955"
        "e452518b4df0e866d404ff85c0744a89c78d45f4508d45e050e8616508ff83"
        "c40884c0743489f98d55e0b80d000000e84a01000089c331c931ff8b559841"
        "3b4dc4730e8b448d9839d07df289c289cfebec39d37e04895cbd9846eb8931"
        "c93b4dc473118b448d9885c074060145c8ff45e841ebea8b55e885d275088b"
        "45d4e9f30000008b45c883fa0b0f83c3000000b90b00000029d16bc92801c8"
        "e9b20000008d7d9831c0b90b000000f3ab8945e88b75d831db3b5dec736e8b"
        "0e8b560483c608894de08955e452518b4df0e8a0d304ff85c0744f89c78d45"
        "f4508d45e050e89b6408ff83c40884c0743989f98d55e0b80d000000e88400"
        "00005389c331c931ff8b55984183f90b730e8b448d9839d07df289c289cfeb"
        "ec39d37e04895cbd985bff45e843eb8d8b55e885d275058b45d4eb4331c031"
        "c903448d984183f90b72f683fa0b730cb90b00000029d16bc92801c883c005"
        "31d2b90b000000f7f183f8287d05b82800000083f8637e09b863000000eb02"
        "89d85f5e5b89ec5dc3",
    ),
    "player_eff_ovr": (
        0x047d5370,
        "5356575089ce89e06a025052e8973806ff83c40c0fb6d8833d604f7d040074"
        "418b461c89c1c1e91583e10783f90477090fbe91784f7d0401d383e07f8b0d"
        "644f7d0485c9741b39c8731789ca29c20faf15684f7d0489c8d1e801d031d2"
        "f7f129c383fb1e7d05bb1e00000083fb6d7e05bb6d00000089d883c4045f5e"
        "5bc3",
    ),
    "smart_subs": (
        0x047d53f0,
        "833d804f7d0400745a8b4d088b95a0feffffe8d5e7ffff84c074488b8db4fe"
        "ffff8d955cfeffffb80d000000e84fffffff50c785b4feffff040000008d85"
        "bbfeffff508d85b4feffff50e8590508ff83c4085901c83dff0000007616b8"
        "ff000000eb0fc785b4feffff64000000e8360508ffe9812cf3fe",
    ),
    "et": (
        0x047d5468,
        "e8786c04ff8b50308b4d0ce864e7ffff84c0750abb03000000e96c0ef3fe8b"
        "450c89c18b500ce8adfbffff89c38b450c89c18b5010e89efbffff29c3031d"
        "543a7d0483fbec7d05bbecffffff83fb147e05bb1400000031f66bc30305e6"
        "0000000faf05e4417d0499b964000000f7f983f83c7d05b83c0000003de001"
        "00007e05b8e001000050b9e8030000e868e7ffff5989cac1ea0339d0720839"
        "c819c0f7d8eb05b8020000008944b5ec880783c703f7db4683fe0272a08b5d"
        "ec8b75f0e9fe0df3fe",
    ),
    "outcome": (
        0x047d552c,
        "89f189fab8dc3b7d04ffd084c0750b0fb67df3b85d7d7003ffe0a1604f7d04"
        "0b05844f7d04741a89f18b560ce8e3faffff89c389f18b5610e8d7faffff29"
        "c3eb0e0fb645f3837de8007402f7d889c38b45ec837de8007402f7d88b0d58"
        "3a7d0485c9740599f7f901c383fbe77d05bbe7ffffff83fb197e05bb190000"
        "0083c3190fb7349d603a7d040fb73c9d623a7d04b9e8030000b8603c7d04ff"
        "d039f0730931c0b9107e7003ffe139f8730cb802000000b9107e7003ffe1b8"
        "01000000b9107e7003ffe1",
    ),
    "pk": (
        0x047d6030,
        "5589e55356e8ab6004ff8b50308b4d0ce897dbffff84c0750e5e5b5d5589e5"
        "83ec08e96a03f3fe8b450c89c18b500ce8dcefffff89c38b450c89c18b5010"
        "e8cdefffff29c383fbec7d05bbecffffff83fb147e05bb1400000089d80faf"
        "05ec417d0499b90a000000f7f90305e8417d0483f80f7d05b80f00000083f8"
        "557e05b85500000089c3b964000000e8a0dbffff39d80f93c20fb6d28b7508"
        "8916b964000000e889dbffff31c93a8140617d0472064183f90772f20fb681"
        "48617d0488c1c0e904240f8b550c833e007508884a16884219eb06884a1988"
        "42165e5b5dc20800",
    ),
    "card_adj": (
        0x047d6120,
        "8b4e0cf7c10000040074042b4370c3c1e91383e1030faf4b6c29c8c3",
    ),
    "fatigue": (
        0x047d6150,
        "833d6c4f7d040075088d4df8e981f607ff8b450c8b1885db0f8ed200000083"
        "fb5a77348b45100fb7003dffff000074275089f1e8b7c904ff85c0741b8d8e"
        "4c156f0039c874118a50150a50180a50160a5019740383c31e8b4718c1e807"
        "83e07f7505b84b00000083f8287d05b82800000083f8637e05b863000000b9"
        "4b00000029c10faf0d704f7d0489c899b90a000000f7f983c06483f8327d05"
        "b8320000003d960000007e05b8960000006bdb030fafc305f401000031d2b9"
        "e8030000f7f18b4f04c1e91c85c9751085c0740c6bc00931d2b90a000000f7"
        "f18b4f1c83e17f29c1790231c9516a5f89f9e8701f05ffe975f607ff",
    ),
    "injury": (
        0x047d6248,
        "803d744f7d04000f84210100008b023b42040f83160100005356575589e583"
        "ec508b328b7a04b964000000e8e8d9ffff3a05744f7d040f83ec000000e85c"
        "5e04ff8b583031c9894dfc894df839fe0f838400000083f90b737f51ff7604"
        "ff3689d9e8b5c304ff5989448dcc31d285c0745380780200754dff45fc8b50"
        "04c1ea1c74420fb6502383e20383fa027605ba02000000b80300000029d08b"
        "548dcc8b521c83e27f83fa647605ba6400000050b86400000029d031d251b9"
        "19000000f7f1595a01c20155f88b45f86689444db44183c60ce974ffffff89"
        "4db0837dfc0776478b4df885c97440e82bd9ffff31c98b55b04a39d1730a66"
        "3b444db4720341ebf28b5c8dcc85db741f0fb60d764f7d04e803d9ffff0fb6"
        "0d754f7d0401c8506a5e89d9e8401e05ff89ec5d5f5e5bc3",
    ),
    "cards": (
        0x047b0060,
        "565753e87dc006ff8b503089f1e86a3b020084c07437803d774f7d04007415"
        "8d45d450e8300000008d45e450e82700000083c408803d744f7d040074108d"
        "55d4e8a36102008d55e4e89b6102005b5f5e8d55d4e9938ef5fe5589e55356"
        "5783ec488b45088b388b400439c70f830601000031db31c939c7734483fb0b"
        "733f50515789f1e8db34f5fe5989449c1c85c0741c8b500cc1ea0e83e20f83"
        "fa097605ba090000000fb682f6417d04eb0231c001c166894c5c04584383c7"
        "0cebb8895c244485c90f84ae00000051b9ff000000e82c3b020031ff3a87f1"
        "417d0472064783ff0472f25b31f639fe735f89d9e80e3b0200e8880000008b"
        "4c841885c974488b510c89d0c1e81383e00383f802733885c0742551b96400"
        "0000e8e23a02005983f81473238b510c81e2ffffe3ff81ca0000140089510c"
        "eb0f81e2ffffe7ff81ca0000080089510c46eb9db964000000e8ac3a02003a"
        "05f0417d04731b89d9e89d3a0200e8170000008b4c841885c9740781490c00"
        "00040083c4485f5e5b5dc331c98b542448663b444c0472064139d172f44989"
        "c8c3",
    ),
}


def build_image(settings=None):
    """Return full CAVE bytes (tables + machine code) for writing at CAVE."""
    keys = ("chk", "rand", "score", "ratings", "scorer")
    end = max(CODE_PARTS[k][0] + len(bytes.fromhex(CODE_PARTS[k][1])) for k in keys)
    buf = bytearray(end - CAVE)
    tables = pack_tables(settings)
    buf[: len(tables)] = tables
    for k in keys:
        addr, hx = CODE_PARTS[k]
        b = bytes.fromhex(hx)
        off = addr - CAVE
        buf[off : off + len(b)] = b
    return bytes(buf)


def build_et_image():
    """Return full CAVE_ET bytes (eff_strength + player_eff_ovr + smart_subs + ET_HOOK + OUTCOME_HOOK) for writing at CAVE_ET."""
    keys = ("eff_strength", "player_eff_ovr", "smart_subs", "et", "outcome")
    end = max(CODE_PARTS[k][0] + len(bytes.fromhex(CODE_PARTS[k][1])) for k in keys)
    buf = bytearray(end - CAVE_ET)
    for k in keys:
        addr, hx = CODE_PARTS[k]
        b = bytes.fromhex(hx)
        off = addr - CAVE_ET
        buf[off : off + len(b)] = b
    return bytes(buf)


def build_pk_image():
    """Return full CAVE_PK bytes (PK_HOOK + card_adj + PK_TABLE + FATIGUE_HOOK + INJURY_FN) for writing at CAVE_PK."""
    keys = ("pk", "card_adj", "fatigue", "injury")
    end = max(CODE_PARTS[k][0] + len(bytes.fromhex(CODE_PARTS[k][1])) for k in keys)
    buf = bytearray(end - CAVE_PK)
    for k in keys:
        addr, hx = CODE_PARTS[k]
        b = bytes.fromhex(hx)
        off = addr - CAVE_PK
        buf[off : off + len(b)] = b
    tbl_off = PK_TABLE_ADDR - CAVE_PK
    buf[tbl_off : tbl_off + 8] = bytes(PK_CDF_DEFAULT)
    buf[tbl_off + 8 : tbl_off + 16] = bytes((w << 4) | l for w, l in PK_PAIRS)
    return bytes(buf)


def lua_block(exe_path):
    """Emit the generated Lua code block for MLSimMatch.lua."""
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent / "tools"))
    import emu
    g = emu.Game(exe_path)

    def read_hex(va, n):
        return g.read(va, n).hex()

    cave_len = len(build_image())
    et_img = build_et_image()
    pk_img = build_pk_image()
    cards_hx = CODE_PARTS["cards"][1]

    assert g.read(CAVE, cave_len) == b"\x00" * cave_len
    assert g.read(CAVE_D, CAVE_D_SIZE) == b"\x00" * CAVE_D_SIZE
    assert g.read(CAVE_D2, CAVE_D2_SIZE) == b"\x00" * CAVE_D2_SIZE
    assert g.read(CAVE_ET, len(et_img)) == b"\x00" * len(et_img)
    assert g.read(CAVE_C, len(cards_hx) // 2) == b"\x00" * (len(cards_hx) // 2)
    assert g.read(CAVE_PK, len(pk_img)) == b"\x00" * len(pk_img)

    out_addr = CODE_PARTS["outcome"][0]
    scr_addr = CODE_PARTS["score"][0]
    ss_addr = CODE_PARTS["smart_subs"][0]
    rat_addr = CODE_PARTS["ratings"][0]
    sco_addr = CODE_PARTS["scorer"][0]
    et_addr = CODE_PARTS["et"][0]
    fat_addr = CODE_PARTS["fatigue"][0]

    out_patch = "e9" + struct.pack("<I", (out_addr - (OUTCOME_SITE + 5)) & 0xffffffff).hex() + "9090"
    scr_patch = "e9" + struct.pack("<I", (scr_addr - (SCORE_SITE + 5)) & 0xffffffff).hex()
    ss_patch = "e9" + struct.pack("<I", (ss_addr - (SMART_SUBS_SITE + 5)) & 0xffffffff).hex() + "90" * 10
    rat_patch = "e9" + struct.pack("<I", (rat_addr - (RATINGS_SITE + 5)) & 0xffffffff).hex() + "90"
    sco_patch = "e9" + struct.pack("<I", (sco_addr - (SCORER_SITE + 5)) & 0xffffffff).hex() + "909090"
    et_patch = "e9" + struct.pack("<I", (et_addr - (ET_SITE + 5)) & 0xffffffff).hex()
    pk_patch = "e9" + struct.pack("<I", (CAVE_PK - (PK_SITE + 5)) & 0xffffffff).hex() + "90"
    cards_patch = "e9" + struct.pack("<I", (CAVE_C - (CARDS_SITE + 5)) & 0xffffffff).hex() + "90"
    fat_patch = "e9" + struct.pack("<I", (fat_addr - (FATIGUE_SITE + 5)) & 0xffffffff).hex() + "90"

    lines = [
        "-- Generated by sim_cave.py (do not edit by hand; test_sim.py checks this block)",
        f"local CAVE = 0x{CAVE:08x}",
        f"local CAVE_SIZE = {cave_len}",
        f"local CAVE_D = 0x{CAVE_D:08x}",
        f"local CAVE_D_SIZE = {CAVE_D_SIZE}",
        f"local CAVE_D2 = 0x{CAVE_D2:08x}",
        f"local CAVE_D2_SIZE = {CAVE_D2_SIZE}",
        f"local CAVE_ET = 0x{CAVE_ET:08x}",
        f"local CAVE_ET_SIZE = {len(et_img)}",
        f"local CAVE_C = 0x{CAVE_C:08x}",
        f"local CAVE_C_SIZE = {len(cards_hx) // 2}",
        f"local CAVE_PK = 0x{CAVE_PK:08x}",
        f"local CAVE_PK_SIZE = {len(pk_img)}",
        f"local CODE_OFF = 0x{CODE_OFF:04x}",
        f"local DIFF_MIN = {DIFF_MIN}",
        f"local DIFF_MAX = {DIFF_MAX}",
        f"local PAIRS_COUNT = {len(PAIRS)}",
        "",
        "local ROUTINES = {",
    ]
    for k in ("chk", "rand", "score", "ratings", "scorer"):
        addr, hx = CODE_PARTS[k]
        lines.append(f'    {{ 0x{addr - CAVE:04x}, "{hx}" }},')
    lines.extend([
        "}",
        "",
        f'local ET_IMAGE = "{et_img.hex()}"',
        f'local CARDS_CODE = "{cards_hx}"',
        f'local PK_IMAGE = "{pk_img.hex()}"',
        "",
        "local SITES = {",
        f'    outcome    = {{ "outcome probability", 0x{OUTCOME_SITE:08x}, "{read_hex(OUTCOME_SITE, 7)}", "{out_patch}" }},',
        f'    score      = {{ "scoreline model",     0x{SCORE_SITE:08x}, "{read_hex(SCORE_SITE, 5)}", "{scr_patch}" }},',
        f'    smart_subs = {{ "smart CPU subs",      0x{SMART_SUBS_SITE:08x}, "{read_hex(SMART_SUBS_SITE, 15)}", "{ss_patch}" }},',
        f'    gk_protect = {{ "GK sub protection",   0x{GK_PROTECT_SITE:08x}, "{read_hex(GK_PROTECT_SITE, 2)}", "9090" }},',
        f'    skip_subs  = {{ "skip-match subs",     0x{SKIP_SUBS_SITE:08x}, "{read_hex(SKIP_SUBS_SITE, 2)}", "eb17" }},',
        f'    ratings    = {{ "match ratings",       0x{RATINGS_SITE:08x}, "{read_hex(RATINGS_SITE, 6)}", "{rat_patch}" }},',
        f'    scorer     = {{ "scorers & assists",   0x{SCORER_SITE:08x}, "{read_hex(SCORER_SITE, 8)}", "{sco_patch}" }},',
        f'    et         = {{ "extra time",          0x{ET_SITE:08x}, "{read_hex(ET_SITE, 5)}", "{et_patch}" }},',
        f'    pk         = {{ "penalty shootout",    0x{PK_SITE:08x}, "{read_hex(PK_SITE, 6)}", "{pk_patch}" }},',
        f'    cards      = {{ "cards & injuries",    0x{CARDS_SITE:08x}, "{read_hex(CARDS_SITE, 6)}", "{cards_patch}" }},',
        f'    fatigue    = {{ "stamina fatigue",     0x{FATIGUE_SITE:08x}, "{read_hex(FATIGUE_SITE, 6)}", "{fat_patch}" }},',
        f'    ai_fatigue = {{ "AI team fatigue",     0x{AI_FATIGUE_SITE:08x}, "{read_hex(AI_FATIGUE_SITE, 6)}", "909090909090" }},',
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
        f'    {{ "sub candidate",    0x037080ac, "{read_hex(0x037080ac, 9)}" }},',
        f'    {{ "sub return",       0x037080e8, "{read_hex(0x037080e8, 9)}" }},',
        f'    {{ "gk sub check",     0x03708189, "{read_hex(0x03708189, 4)}" }},',
        f'    {{ "ratings entry",    0x03708cc4, "{read_hex(0x03708cc4, 7)}" }},',
        f'    {{ "ratings fallback", 0x03708d3f, "{read_hex(0x03708d3f, 6)}" }},',
        f'    {{ "ratings done",     0x03708d73, "{read_hex(0x03708d73, 9)}" }},',
        f'    {{ "scorer entry",     0x03706ef6, "{read_hex(0x03706ef6, 6)}" }},',
        f'    {{ "scorer fallback",  0x03706f3d, "{read_hex(0x03706f3d, 6)}" }},',
        f'    {{ "scorer picked",    0x03707244, "{read_hex(0x03707244, 8)}" }},',
        f'    {{ "scorer none",      0x037072e5, "{read_hex(0x037072e5, 8)}" }},',
        f'    {{ "et entry",         0x037062ca, "{read_hex(0x037062ca, 6)}" }},',
        f'    {{ "et done",          0x03706329, "{read_hex(0x03706329, 8)}" }},',
        f'    {{ "pk fallback",      0x037063c1, "{read_hex(0x037063c1, 7)}" }},',
        f'    {{ "cards fallback",   0x03708f4b, "{read_hex(0x03708f4b, 7)}" }},',
        f'    {{ "fatigue entry",    0x038556f1, "{read_hex(0x038556f1, 9)}" }},',
        f'    {{ "fatigue branch",   0x038557d0, "{read_hex(0x038557d0, 6)}" }},',
        f'    {{ "fatigue fallback", 0x038557e2, "{read_hex(0x038557e2, 8)}" }},',
        f'    {{ "fatigue exit",     0x038558ba, "{read_hex(0x038558ba, 7)}" }},',
        f'    {{ "mode obj",         0x{MODE_OBJ:08x}, "{read_hex(MODE_OBJ, 6)}" }},',
        f'    {{ "menu status",      0x{MENU_STATUS:08x}, "{read_hex(MENU_STATUS, 6)}" }},',
        f'    {{ "team record",      0x{TEAM_RECORD:08x}, "{read_hex(TEAM_RECORD, 6)}" }},',
        f'    {{ "team tactics",     0x{TEAM_TACTICS_ID:08x}, "{read_hex(TEAM_TACTICS_ID, 9)}" }},',
        f'    {{ "tactics rec",      0x{TACTICS_REC:08x}, "{read_hex(TACTICS_REC, 8)}" }},',
        f'    {{ "player rec",       0x{RECORD_BY_ID:08x}, "{read_hex(RECORD_BY_ID, 6)}" }},',
        f'    {{ "fix rec",          0x{FIX_RECORD:08x}, "{read_hex(FIX_RECORD, 6)}" }},',
        f'    {{ "player set",       0x{PLAYER_SET:08x}, "{read_hex(PLAYER_SET, 6)}" }},',
        f'    {{ "player ovr",       0x{PLAYER_OVR:08x}, "{read_hex(PLAYER_OVR, 6)}" }},',
        f'    {{ "player elig",      0x{PLAYER_ELIG:08x}, "{read_hex(PLAYER_ELIG, 6)}" }},',
        f'    {{ "team strength",    0x{TEAM_STRENGTH:08x}, "{read_hex(TEAM_STRENGTH, 6)}" }},',
        f'    {{ "mode random",      0x{MODE_RANDOM:08x}, "{read_hex(MODE_RANDOM, 6)}" }},',
        f'    {{ "stat rec lookup",  0x{STAT_REC_BY_ID:08x}, "{read_hex(STAT_REC_BY_ID, 6)}" }},',
        "}",
    ])
    return "\n".join(lines)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "info"
    if cmd == "build":
        built = assemble()
        print(f"CAVE    end: 0x{built['cave_end']:08x} ({built['cave_end'] - CAVE} / {CAVE_SIZE_MAX} bytes)")
        print(f"CAVE_ET end: 0x{built['cave_et_end']:08x} ({built['cave_et_end'] - CAVE_ET} / {CAVE_ET_MAX} bytes)")
        print(f"CAVE_C  end: 0x{built['cave_c_end']:08x} ({built['cave_c_end'] - CAVE_C} / {CAVE_C_MAX} bytes)")
        print(f"CAVE_PK end: 0x{built['cave_pk_end']:08x} ({built['cave_pk_end'] - CAVE_PK} / {CAVE_PK_MAX} bytes)")
        keys = ("chk", "rand", "score", "ratings", "scorer", "eff_strength", "player_eff_ovr", "smart_subs", "et", "outcome", "pk", "card_adj", "fatigue", "injury", "cards")
        for name in keys:
            addr, b = built[name]
            print(f'    "{name}": (0x{addr:08x}, "{b.hex()}"),')
        for name in keys:
            exp_addr, exp_hx = CODE_PARTS.get(name, (0, ""))
            got_addr, got_b = built[name]
            if (exp_addr, exp_hx) != (got_addr, got_b.hex()):
                print(f"MISMATCH on {name}!", file=sys.stderr)
                sys.exit(1)
        print("CODE_PARTS matches Keystone assembly byte-for-byte.")
    elif cmd == "lua":
        print(lua_block(sys.argv[2]))
    else:
        img = build_image()
        et_img = build_et_image()
        pk_img = build_pk_image()
        print(f"CAVE   : 0x{CAVE:08x}..0x{CAVE + len(img):08x} ({len(img)} / {CAVE_SIZE_MAX} bytes)")
        print(f"CAVE_D : 0x{CAVE_D:08x}..0x{CAVE_D + CAVE_D_SIZE:08x} ({CAVE_D_SIZE} / {CAVE_D_MAX} bytes)")
        print(f"CAVE_D2: 0x{CAVE_D2:08x}..0x{CAVE_D2 + CAVE_D2_SIZE:08x} ({CAVE_D2_SIZE} / {CAVE_D2_MAX} bytes)")
        print(f"CAVE_ET: 0x{CAVE_ET:08x}..0x{CAVE_ET + len(et_img):08x} ({len(et_img)} / {CAVE_ET_MAX} bytes)")
        print(f"CAVE_PK: 0x{CAVE_PK:08x}..0x{CAVE_PK + len(pk_img):08x} ({len(pk_img)} / {CAVE_PK_MAX} bytes)")
        print(f"CAVE_C : 0x{CAVE_C:08x}..0x{CAVE_C + len(CODE_PARTS['cards'][1]) // 2:08x} ({len(CODE_PARTS['cards'][1]) // 2} / {CAVE_C_MAX} bytes)")


if __name__ == "__main__":
    main()
