"""Runs MLSimMatch.lua outside the game and then runs PES2017.exe's match simulation
machine code with its changes in the Unicorn CPU emulator.

    python3 test_sim.py <PES2017.exe>    needs: pip install lupa unicorn

Tests:
  1. Generated block in MLSimMatch.lua matches sim_cave.py lua_block(), and Lua's
     build_image() + build_data_d() match sim_cave.py byte-for-byte.
  2. Settings validation refuses bad inputs cleanly (all v1 + v2 settings); WRITE=false,
     all-off, and independent partial modes (SKIP_SUBS-only, RATINGS-only, SCORERS-only,
     ASSISTS-only) patch only their intended sites and caves.
  3. Tamper detection: changing any byte of CONTEXT or active SITES, non-empty CAVE or
     CAVE_D, pre-hooked e9 jump, or sticky write failures all report cleanly.
  4. Real PES2017.exe machine code (`fcn_03707a1f` outcome + `fcn_03705feb` scoreline)
     with MLSimMatch.lua installed matches Python reference probabilities and scoreline
     distributions across equal, favorite, underdog, huge-mismatch, captain-bonus, and
     draw cases.
  5. SCOPE="skip_only" applies only when Skip Match flag (`+0xdcb61c`) is non-zero AND
     at least one team is user-controlled; otherwise falls back to vanilla logic across
     all hooks. Special mode 0x27/0x28 + comp 0x3c/0x3d also falls back to vanilla logic.
  6. Knockout / 2-leg replay loop in `fcn_03708de9` + `fcn_03706175` terminates cleanly
     even on extreme mismatches (e.g. 90 vs 60) and produces valid decisive ties.
  7. SKIP_SUBS patch at `0x03708230` skips the `sub1=sub2=sub3=11` overwrite in
     `fcn_03707e71` during Skip Match.
  8. Feature 1 (`fcn_03708cc4` dynamic match ratings): real PES2017.exe machine code
     matches Python `compute_rating()` across wins, draws, losses, goal margins, clean
     sheets (defenders vs attackers), heavy conceded penalties, goals, assists, variance,
     clamping, dummy-player guard, and RATINGS=false vanilla fallback.
  9. Feature 2 (`fcn_03706ef6` realistic scorers & assists): real PES2017.exe machine
     code matches Python `SCORER_W` / `ASSIST_W` exponential weights across all 10
     outfielders, skips GK (stat=0), honors UNASSISTED_PCT, produces zero self-assists,
     increments stat_rec +0x08/+0x09, and supports independent SCORERS/ASSISTS toggles.
 10. Coexistence with MLMoney.lua, MLTransfers.lua, and MLYear.lua in any sider.ini order.
"""
import collections
import os
import random
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import sim_cave as sc
import test_money as tm
from test_money import Game, REG, STACK, STACK_SIZE, poke, run


def set_lua(source, name, new):
    out, n = re.subn(
        r"^local %s = (?:\"[^\"]*\"|\{[^\n]*\}|[\w.]+)" % name,
        lambda m: f"local {name} = {new}",
        source,
        flags=re.M,
    )
    assert n == 1, name
    return out


MODULE = os.path.join(HERE, "MLSimMatch.lua")
YEAR_MODULE = os.path.join(HERE, "MLYear.lua")

# Game addresses used by the harness
OUTCOME_FN = 0x03707a1f
SCORE_FN = 0x03705feb
ET_FN = 0x037062ca
PK_FN = 0x037063bb
SIM_MATCH_FN = 0x03708de9
SCORER_FN = 0x03706ef6
RATINGS_FN = 0x03708cc4
STAT_REC_BY_ID = 0x037035c3
RECORD_BY_ID = 0x03822663
TEAM_STRENGTH = 0x03865b0a
COMP_RECORD = 0x03822ab9
MODE_RANDOM = 0x03855998
TEAM_RECORD = 0x03822969
CAP_ROLES_VEC = 0x038ba942
CAP_BONUS_FN = 0x038b6e3d
VEC_FREE = 0x02bc5b9a

ALLOWED_CAVE = (sc.CAVE, len(sc.build_image()))
ALLOWED_DATA_D = (sc.CAVE_D, sc.CAVE_D_SIZE)
ALLOWED_DATA_D2 = (sc.CAVE_D2, sc.CAVE_D2_SIZE)
ALLOWED_CAVE_ET = (sc.CAVE_ET, len(sc.build_et_image()))
ET_WRITES = ((sc.CAVE_ET, sc.CAVE_ET_CODE_SIZE),
             (sc.WIN_CDF_2D_ADDR, sc.CAVE_ET_SIZE - sc.WIN_CDF_2D_OFF))
ALLOWED_CAVE_PK = (sc.CAVE_PK, len(sc.build_pk_image()))
ALLOWED_CAVE_C = (sc.CAVE_C, len(bytes.fromhex(sc.CODE_PARTS["cards"][1])))
ALLOWED_SITES = (
    (sc.OUTCOME_SITE, 7),
    (sc.SCORE_SITE, 5),
    (sc.SMART_SUBS_SITE, 15),
    (sc.GK_PROTECT_SITE, 2),
    (sc.SKIP_SUBS_SITE, 2),
    (sc.RATINGS_SITE, 6),
    (sc.SCORER_SITE, 8),
    (sc.SIM_VEC_SITE, 6),
    (sc.ET_SITE, 5),
    (sc.PK_SITE, 6),
    (sc.CARDS_SITE, 6),
    (sc.FATIGUE_SITE, 6),
    (sc.AI_FATIGUE_SITE, 6),
)


class SimHarness:
    """Sets up minimal PES 2017 mode/menu/competition/team/match structs in Unicorn."""

    def __init__(self, exe):
        self.g = g = Game(exe)
        self.mode_data = g.alloc(size=0xe00000)
        self.mode_obj = g.alloc(size=0x40)
        self.menu_obj = g.alloc(size=0x40)
        g.write(self.mode_obj + 0x30, struct.pack("<I", self.mode_data))
        g.write(tm.MODE_OBJECT, struct.pack("<I", self.mode_obj))
        g.write(self.menu_obj + 0x20, struct.pack("<I", 0x13))  # Master League
        g.write(tm.MENU_OBJECT, struct.pack("<I", self.menu_obj))

        self.comp = g.alloc(size=0x100)
        self.team0 = g.alloc(size=0x400)
        self.team1 = g.alloc(size=0x400)
        self.mgr_rec = g.alloc(size=0x400)
        self.match = g.alloc(size=0x40)
        self.sim_obj = g.alloc(size=0x40)
        self.res_buf = g.alloc(size=4)
        self.dummy_player = g.alloc(size=0xe0)
        self.stat_map = {}
        self.player_map = {}
        self.player_team_map = {}
        self.ovr_map = {}
        self.ovr_pos_map = {}
        self.tactics_map = {}
        self.ban_set = set()

        self.state = {
            "ovr0": 80,
            "ovr1": 80,
            "cap0": 0,
            "cap1": 0,
            "rand_fn": lambda n: random.randrange(n),
            "leg1_h": 0,
            "leg1_a": 0,
            "away_goals": 1,
            "et_flag": 0,
            "pk_flag": 0,
            "vec0": None,
            "vec1": None,
        }

        self.set_team_user(0, False)
        self.set_team_user(1, False)
        self.set_skip_flag(False)
        self.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)

        g.replace(COMP_RECORD, lambda gm, a: self.comp)
        g.replace(TEAM_RECORD, lambda gm, a: self.team0 if a(0) == 100 else self.team1)
        g.replace(0x03822a29, lambda gm, a: self.tactics_map.get((a(0), a(1)), self.mgr_rec))
        g.replace(
            TEAM_STRENGTH,
            lambda gm, a: self.state["ovr0"] if struct.unpack("<I", gm.read(a(0), 4))[0] == 100 else self.state["ovr1"],
        )

        def get_rand(gm, a):
            n = struct.unpack("<I", gm.read(a(0), 4))[0]
            return 0 if n == 0 else self.state["rand_fn"](n)

        g.replace(MODE_RANDOM, get_rand)

        def get_cap_vec(gm, a):
            out = a(1)
            gm.write(out, b"\x00" * 12)
            return out

        g.replace(CAP_ROLES_VEC, get_cap_vec)
        g.replace(0x03822835, lambda gm, a: self.player_map.get((a(0), a(1)), self.dummy_player))
        g.replace(VEC_FREE, lambda gm, a: 0)

        # Player/stat/fixture lookups for fcn_03708cc4, fcn_03706ef6, CARDS_HOOK, eff_strength & fcn_038556f1
        g.replace(RECORD_BY_ID, lambda gm, a: self.player_map.get((a(0), a(1)), self.dummy_player))
        g.replace(sc.FIX_RECORD, lambda gm, a: self.match)
        g.replace(0x03857359, lambda gm, a: 1)
        g.replace(0x0385662c, lambda gm, a: 0)
        g.replace(0x0329d6ae, lambda gm, a: 0)

        def get_player_team(gm, a):
            p_ptr = gm.mu.reg_read(REG["ecx"])
            gm.write(a(0), struct.pack("<I", self.player_team_map.get(p_ptr, 100)))
            return a(0)

        g.replace(0x0382b087, get_player_team)

        def get_player_ovr(gm, a):
            id_ptr = a(0)
            pos = struct.unpack("<I", gm.read(a(1), 4))[0]
            id_lo, id_hi = struct.unpack("<II", gm.read(id_ptr, 8))
            return self.ovr_pos_map.get((id_lo, id_hi, pos), self.ovr_map.get((id_lo, id_hi), 75))

        g.replace(sc.PLAYER_OVR, get_player_ovr)

        def get_player_ban(gm, a):
            id_ptr = a(0)
            id_lo, id_hi = struct.unpack("<II", gm.read(id_ptr, 8))
            return 1 if (id_lo, id_hi) in self.ban_set else 0

        g.replace(0x0385b4f9, get_player_ban)

        def get_stat_rec(gm, a):
            id_ptr = a(0)
            id_lo = struct.unpack("<H", gm.read(id_ptr, 2))[0]
            id_hi = struct.unpack("<I", gm.read(id_ptr + 4, 4))[0]
            return self.stat_map.get((id_lo, id_hi), 0)

        g.replace(STAT_REC_BY_ID, get_stat_rec)

        # Cup / 2-leg flags for fcn_03706175 / fcn_03708de9
        g.replace(0x03856ca8, lambda gm, a: self.state["et_flag"])
        g.replace(0x03856d18, lambda gm, a: self.state["pk_flag"])
        g.replace(0x03856db8, lambda gm, a: self.state["away_goals"])
        g.replace(0x03856ef8, lambda gm, a: self.state["leg1_h"] if a(1) == 0 else self.state["leg1_a"])
        g.replace(0x03707e71, lambda gm, a: 0)

        def sim_vec_stub(gm, a):
            side = a(0)
            out_vec = a(2)
            src_vec = self.state["vec0"] if side == 0 else self.state["vec1"]
            if src_vec is not None:
                gm.write(out_vec, gm.read(src_vec, 12))
            else:
                gm.write(out_vec, b"\x00" * 12)
            return 0

        g.replace(0x037085b5, sim_vec_stub)

        self.clean_snapshot = [
            (sc.CAVE, g.read(sc.CAVE, ALLOWED_CAVE[1])),
            (sc.CAVE_D, g.read(sc.CAVE_D, ALLOWED_DATA_D[1])),
            (sc.CAVE_D2, g.read(sc.CAVE_D2, ALLOWED_DATA_D2[1])),
            (sc.CAVE_ET, g.read(sc.CAVE_ET, ALLOWED_CAVE_ET[1])),
            (sc.CAVE_PK, g.read(sc.CAVE_PK, ALLOWED_CAVE_PK[1])),
            (sc.CAVE_C, g.read(sc.CAVE_C, ALLOWED_CAVE_C[1])),
        ] + [(addr, g.read(addr, sz)) for addr, sz in ALLOWED_SITES]

    def restore(self):
        for addr, data in self.clean_snapshot:
            poke(self.g, addr, data)

    def set_menu_mode(self, mode):
        self.g.write(self.menu_obj + 0x20, struct.pack("<I", mode))

    def set_mode_kind(self, kind):
        self.g.write(self.mode_obj + 0x20, struct.pack("<I", kind))

    def set_skip_flag(self, on):
        self.g.write(self.mode_data + sc.SKIP_FLAG_OFF, bytes([1 if on else 0]))

    def set_team_user(self, side, is_user):
        t = self.team0 if side == 0 else self.team1
        val = (0x00 if is_user else 0xff) << 7
        self.g.write(t + 0x314, struct.pack("<I", val))

    def set_match(self, comp_id=1, team0_id=100, team1_id=200, tie_kind=0, hg=0, ag=0):
        self.g.write(self.match + 0x00, struct.pack("<H", 1))
        self.g.write(self.match + 0x04, struct.pack("<I", (comp_id & 0xffff) | ((tie_kind & 3) << 28)))
        self.g.write(self.match + 0x0c, struct.pack("<II", team0_id, team1_id))
        self.g.write(self.match + 0x14, struct.pack("<BBBB", hg, 0, 0, ag) + b"\x00" * 4)

    def alloc_squad(self, players, clear=True):
        """players: list of (id_lo, id_hi, stat_val, pos, goals, assists).
        Returns (vec_ptr, recs_dict).
        """
        if clear:
            self.stat_map.clear()
        buf = bytearray()
        recs = {}
        for id_lo, id_hi, stat_val, pos, goals, assists in players:
            buf += struct.pack("<III", id_lo, id_hi, stat_val)
            rec = self.g.alloc(size=0x20)
            self.g.write(rec + 0x00, struct.pack("<II", id_lo, id_hi))
            self.g.write(rec + 0x08, bytes([goals, assists]))
            self.g.write(rec + 0x0c, struct.pack("<I", (pos & 0xf) << 14))
            self.stat_map[(id_lo, id_hi)] = rec
            recs[(id_lo, id_hi)] = rec
        arr = self.g.alloc(bytes(buf))
        vec = self.g.alloc(struct.pack("<III", arr, arr + len(buf), arr + len(buf)))
        return vec, recs

    def run_outcome(self, ovr0, ovr1):
        self.state["ovr0"] = ovr0
        self.state["ovr1"] = ovr1
        return self.g.call(OUTCOME_FN, [self.match], ecx=self.sim_obj)

    def run_score(self, res, ovr0, ovr1):
        self.state["ovr0"] = ovr0
        self.state["ovr1"] = ovr1
        self.g.write(self.res_buf, struct.pack("<I", res))
        self.g.call(SCORE_FN, [self.res_buf, self.match], ecx=self.sim_obj)
        hg = self.g.read(self.match + 0x14, 1)[0]
        ag = self.g.read(self.match + 0x17, 1)[0]
        return hg, ag

    def read_rating(self, rec):
        bits = struct.unpack("<I", self.g.read(rec + 0x0c, 4))[0]
        return (bits & 0x3f80) >> 7

    def read_cards(self, rec):
        bits = struct.unpack("<I", self.g.read(rec + 0x0c, 4))[0]
        red = (bits >> 18) & 1
        yellows = (bits >> 19) & 3
        return yellows, red

    def alloc_player(
        self,
        id_lo,
        id_hi,
        *,
        team_id=100,
        ovr=80,
        pos=9,
        stamina=75,
        inj_res=1,
        inj_days=0,
        fitness=100,
        arrow=2,
        atk_prow=75,
        dribbling=75,
        ball_ctrl=75,
        finishing=75,
        low_pass=75,
        lofted_pass=75,
        header=75,
    ):
        p = self.g.alloc(size=0xe0)
        self.g.write(p + 0x02, bytes([inj_days & 0xff, atk_prow & 0x7f]))
        self.g.write(
            p + 0x04,
            struct.pack("<I", ((dribbling & 0x7f) << 14) | ((ball_ctrl & 0x7f) << 21) | ((pos & 0xf) << 28)),
        )
        self.g.write(
            p + 0x08,
            struct.pack(
                "<I",
                (finishing & 0x7f)
                | ((low_pass & 0x7f) << 7)
                | ((lofted_pass & 0x7f) << 14)
                | ((header & 0x7f) << 21),
            ),
        )
        self.g.write(p + 0x18, struct.pack("<I", (stamina & 0x7f) << 7))
        self.g.write(p + 0x1c, struct.pack("<I", (fitness & 0x7f) | ((arrow & 7) << 21)))
        self.g.write(p + 0x23, bytes([inj_res & 3]))
        self.g.write(p + 0x2c, struct.pack("<II", id_lo, id_hi))
        self.player_map[(id_lo, id_hi)] = p
        self.player_team_map[p] = team_id
        self.ovr_map[(id_lo, id_hi)] = ovr
        return p

    def set_team_squad(self, side, player_ids):
        t = self.team0 if side == 0 else self.team1
        n = min(32, len(player_ids))
        for i, (id_lo, id_hi) in enumerate(player_ids[:n]):
            self.g.write(t + 0xf8 + i * 8, struct.pack("<II", id_lo, id_hi))
        self.g.write(t + 0x328, struct.pack("<I", (n & 0x7f) << 9))

    def set_team_tactics(self, side, indices, pos_ids=None, *, sentinel=False):
        t = self.team0 if side == 0 else self.team1
        tid = (900 + side, 1)
        self.g.write(t + 0x1f8, struct.pack("<II", *tid))
        if sentinel:
            self.tactics_map[tid] = self.mode_data + 0x5fea64
            return
        rec = self.g.alloc(size=0x280)
        self.g.write(rec + 0x248, bytes(indices))
        if pos_ids is None:
            pos_ids = [0, 1, 2, 2, 3, 6, 7, 8, 9, 9, 10]
        self.g.write(rec + 0x68, bytes(pos_ids))
        self.tactics_map[tid] = rec

    def clear_squads(self):
        self.set_team_squad(0, [])
        self.set_team_squad(1, [])
        self.g.write(self.team0 + 0x1f8, b"\x00" * 8)
        self.g.write(self.team1 + 0x1f8, b"\x00" * 8)
        self.player_map.clear()
        self.player_team_map.clear()
        self.ovr_map.clear()
        self.ovr_pos_map.clear()
        self.tactics_map.clear()
        self.ban_set.clear()

    def read_player_fitness(self, p):
        return struct.unpack("<I", self.g.read(p + 0x1c, 4))[0] & 0x7f

    def read_player_injury(self, p):
        return self.g.read(p + 0x02, 1)[0]


def main(exe):
    source = open(MODULE, encoding="utf-8").read()

    # 1. Generated Lua block matches sim_cave.py
    expected_block = sc.lua_block(exe)
    assert expected_block in source, "Generated block in MLSimMatch.lua does not match sim_cave.lua_block(exe)!"
    print("ok 1: MLSimMatch.lua generated tables/routines/context block matches sim_cave.py exactly")

    # 2. Check Keystone assembly matches CODE_PARTS if keystone is installed
    if tm.KEYSTONE:
        built = sc.assemble()
        for name in ("chk", "rand", "score", "ratings", "scorer", "sim_vec", "eff_strength", "player_eff_ovr", "smart_subs", "et", "outcome", "pk", "card_adj", "fatigue", "injury", "cards"):
            assert (built[name][0], built[name][1].hex()) == sc.CODE_PARTS[name], name
    print("ok 2: Keystone assembly matches pre-assembled CODE_PARTS byte-for-byte (all 16 routines)")

    h = SimHarness(exe)
    g = h.g

    # 3. Verify Lua cave builders match Python byte-for-byte
    lines, reads, writes = run(g, source)
    assert lines[-1].startswith("RESULT: installed."), lines
    assert g.read(sc.CAVE, ALLOWED_CAVE[1]) == sc.build_image(), "Lua build_image() != Python!"
    assert g.read(sc.CAVE_D, ALLOWED_DATA_D[1]) == sc.pack_data_d(), "Lua build_data_d() != Python!"
    assert g.read(sc.CAVE_D2, ALLOWED_DATA_D2[1]) == sc.pack_data_d2(), "Lua build_data_d2() != Python!"
    assert g.read(sc.CAVE_ET, ALLOWED_CAVE_ET[1]) == sc.build_et_image()
    assert g.read(sc.CAVE_PK, ALLOWED_CAVE_PK[1]) == sc.build_pk_image()
    assert g.read(sc.CAVE_C, ALLOWED_CAVE_C[1]) == bytes.fromhex(sc.CODE_PARTS["cards"][1])
    assert tm.inside(
        writes,
        (ALLOWED_CAVE, ALLOWED_DATA_D, ALLOWED_DATA_D2, ALLOWED_CAVE_PK, ALLOWED_CAVE_C) + ET_WRITES + ALLOWED_SITES,
    )
    print(f"ok 3: Lua cave images ({ALLOWED_CAVE[1]}+{ALLOWED_DATA_D[1]}+{ALLOWED_DATA_D2[1]}+{ALLOWED_CAVE_ET[1]}+{ALLOWED_CAVE_PK[1]}+{ALLOWED_CAVE_C[1]} B) match Python byte-for-byte")

    # 4. Settings fault validation + dry-run + partial modes
    h.restore()
    faulty = [
        ("WRITE", '"yes"'),
        ("SCOPE", '"broken"'),
        ("SCOPE", "123"),
        ("HOME_ADVANTAGE", "-1"),
        ("HOME_ADVANTAGE", "16"),
        ("ELO_SCALE", "1.5"),
        ("ELO_SCALE", "31"),
        ("BASE_DRAW", "0.04"),
        ("BASE_DRAW", "0.60"),
        ("CAPTAIN_WEIGHT", "-0.1"),
        ("CAPTAIN_WEIGHT", "1.5"),
        ("GOAL_SCALE", "0.4"),
        ("GOAL_SCALE", "2.1"),
        ("DRAW_WEIGHTS", "{ 1, 2, 3 }"),
        ("DRAW_WEIGHTS", "{ 0, 0, 0, 0, 0 }"),
        ("DRAW_WEIGHTS", "{ 10, -1, 5, 1, 1 }"),
        ("ATTACK_DEFENSE_SPLIT", "1"),
        ("GK_SCORE_MOD", "1"),
        ("GK_CONDITION_OVR", "{ -6, -3, 0, 3 }"),
        ("GK_CONDITION_OVR", "{ -11, -3, 0, 3, 6 }"),
        ("SKIP_SUBS", '"true"'),
        ("GK_PROTECT", '"yes"'),
        ("SMART_SUBS", "1"),
        ("RATINGS", '"true"'),
        ("RATING_BASE", "{ 6.4, 6.1 }"),
        ("RATING_BASE", "{ 3.5, 6.1, 5.7 }"),
        ("RATING_BASE", "{ 9.0, 6.1, 5.7 }"),
        ("RATING_GD", "-0.1"),
        ("RATING_GD", "3.5"),
        ("RATING_CLEAN_SHEET", "{ 0.3 }"),
        ("RATING_CLEAN_SHEET", "{ -0.1, 0.1 }"),
        ("RATING_GOAL", "2.5"),
        ("RATING_ASSIST", "-0.1"),
        ("RATING_YELLOW", "-0.1"),
        ("RATING_YELLOW", "2.5"),
        ("RATING_RED", "-0.1"),
        ("RATING_RED", "3.5"),
        ("RATING_VARIANCE", "2.0"),
        ("RATING_RANGE", "{ 7.0, 6.0 }"),
        ("RATING_RANGE", "{ 0.5, 9.5 }"),
        ("SCORERS", "1"),
        ("ASSISTS", "0"),
        ("SCORER_SHARPNESS", "0.005"),
        ("ASSIST_SHARPNESS", "0.6"),
        ("UNASSISTED_PCT", "-5"),
        ("UNASSISTED_PCT", "101"),
        ("EXTRA_TIME_PK", "1"),
        ("ET_GOAL_SCALE", "0.2"),
        ("ET_GOAL_SCALE", "2.5"),
        ("PK_HOME_BIAS", "-26"),
        ("PK_HOME_BIAS", "26"),
        ("PK_OVR_WEIGHT", "-0.1"),
        ("PK_OVR_WEIGHT", "2.5"),
        ("CARDS", '"yes"'),
        ("YELLOW_AVG", "-0.1"),
        ("YELLOW_AVG", "4.5"),
        ("RED_PCT", "-1"),
        ("RED_PCT", "31"),
        ("CONDITION_STRENGTH", "1"),
        ("LINEUP_STRENGTH", "0"),
        ("CONDITION_OVR", "{ -4, -2, 0, 2 }"),
        ("CONDITION_OVR", "{ -11, -2, 0, 2, 4 }"),
        ("FATIGUE_THRESHOLD", "35"),
        ("FATIGUE_THRESHOLD", "105"),
        ("FATIGUE_PENALTY", "-1"),
        ("FATIGUE_PENALTY", "21"),
        ("STAMINA_FATIGUE", "1"),
        ("STAMINA_WEIGHT", "-0.1"),
        ("STAMINA_WEIGHT", "2.1"),
        ("AI_FATIGUE", '"yes"'),
        ("INJURY_PCT", "-1"),
        ("INJURY_PCT", "21"),
        ("INJURY_DAYS", "{ 7 }"),
        ("INJURY_DAYS", "{ 20, 10 }"),
        ("INJURY_DAYS", "{ 0, 10 }"),
        ("INJURY_DAYS", "{ 7, 65 }"),
    ]
    for name, val in faulty:
        l2, r2, w2 = run(g, set_lua(source, name, val))
        assert l2[-1].startswith("RESULT: nothing written. Settings:") and not r2 and not w2, (name, val, l2)

    l2, r2, w2 = run(g, set_lua(source, "WRITE", "false"))
    assert l2[-1] == "RESULT: nothing written (WRITE = false). All checks passed." and not w2, l2

    all_off = source
    for k in ("SCOPE", "SKIP_SUBS", "GK_PROTECT", "SMART_SUBS", "RATINGS", "SCORERS", "ASSISTS", "EXTRA_TIME_PK", "CARDS", "STAMINA_FATIGUE"):
        all_off = set_lua(all_off, k, "false")
    all_off = set_lua(all_off, "INJURY_PCT", "0")
    l2, r2, w2 = run(g, all_off)
    assert "All features are off" in l2[-1] and not r2 and not w2, l2

    # Partial modes: SKIP_SUBS-only, GK_PROTECT-only, SMART_SUBS-only, RATINGS-only, ASSISTS-only, ET/PK-only, CARDS-only, STAMINA_FATIGUE-only, INJURY-only
    subs_only = set_lua(all_off, "SKIP_SUBS", "true")
    l2, _, w2 = run(g, subs_only)
    assert l2[-1] == "RESULT: installed. Active: Skip Match CPU substitutions." and w2 == [(sc.SKIP_SUBS_SITE, 2)], (l2, w2)

    h.restore()
    gk_only = set_lua(all_off, "GK_PROTECT", "true")
    l2, _, w2 = run(g, gk_only)
    assert l2[-1] == "RESULT: installed. Active: GK sub protection." and w2 == [(sc.GK_PROTECT_SITE, 2)], (l2, w2)

    h.restore()
    smart_only = set_lua(all_off, "SMART_SUBS", "true")
    l2, _, w2 = run(g, smart_only)
    assert l2[-1] == "RESULT: installed. Active: smart CPU subs." and set(w2) == {
        ALLOWED_CAVE, ALLOWED_DATA_D2, *ET_WRITES, (sc.SMART_SUBS_SITE, 15)
    }, (l2, w2)

    h.restore()
    ratings_only = set_lua(all_off, "RATINGS", "true")
    l2, _, w2 = run(g, ratings_only)
    assert "dynamic ratings" in l2[-1] and set(w2) == {ALLOWED_CAVE, ALLOWED_DATA_D, ALLOWED_CAVE_PK, (sc.RATINGS_SITE, 6)}, (l2, w2)

    h.restore()
    assists_only = set_lua(all_off, "ASSISTS", "true")
    l2, _, w2 = run(g, assists_only)
    assert "assists (unassisted 28%)" in l2[-1] and set(w2) == {
        ALLOWED_CAVE, ALLOWED_DATA_D, ALLOWED_DATA_D2, *ET_WRITES, (sc.SCORER_SITE, 8), (sc.SIM_VEC_SITE, 6)
    }, (l2, w2)

    h.restore()
    etpk_only = set_lua(all_off, "EXTRA_TIME_PK", "true")
    l2, _, w2 = run(g, etpk_only)
    assert "ET/PK" in l2[-1] and set(w2) == {
        ALLOWED_CAVE, ALLOWED_DATA_D, ALLOWED_DATA_D2, *ET_WRITES, ALLOWED_CAVE_PK, (sc.ET_SITE, 5), (sc.PK_SITE, 6)
    }, (l2, w2)

    h.restore()
    cards_only = set_lua(all_off, "CARDS", "true")
    l2, _, w2 = run(g, cards_only)
    assert "cards" in l2[-1] and set(w2) == {
        ALLOWED_CAVE, ALLOWED_DATA_D, ALLOWED_DATA_D2, ALLOWED_CAVE_C, (sc.CARDS_SITE, 6)
    }, (l2, w2)

    h.restore()
    fat_only = set_lua(all_off, "STAMINA_FATIGUE", "true")
    l2, _, w2 = run(g, fat_only)
    assert "stamina fatigue" in l2[-1] and set(w2) == {
        ALLOWED_DATA_D2, ALLOWED_CAVE_PK, (sc.FATIGUE_SITE, 6), (sc.AI_FATIGUE_SITE, 6)
    }, (l2, w2)

    h.restore()
    inj_only = set_lua(all_off, "INJURY_PCT", "5")
    l2, _, w2 = run(g, inj_only)
    assert "injuries (5%, 7-28d)" in l2[-1] and set(w2) == {
        ALLOWED_CAVE, ALLOWED_DATA_D2, ALLOWED_CAVE_PK, ALLOWED_CAVE_C, (sc.CARDS_SITE, 6)
    }, (l2, w2)
    h.restore()
    print("ok 4: 76 faulty settings refused; WRITE=false, all-off, and 9 partial modes verified")

    # 5. Tamper & sticky checks
    for name, addr, expected_hex in [
        ("outcome site", sc.OUTCOME_SITE, "0fb6bdf3ffffff"),
        ("score site", sc.SCORE_SITE, "8b45088b00"),
        ("smart_subs site", sc.SMART_SUBS_SITE, "c785b4feffff64000000e8b0d81400"),
        ("gk_protect site", sc.GK_PROTECT_SITE, "31ff"),
        ("skip_subs site", sc.SKIP_SUBS_SITE, "7417"),
        ("ratings site", sc.RATINGS_SITE, "8b4d0883f902"),
        ("scorer site", sc.SCORER_SITE, "31c9898de4ffffff"),
        ("sim_vec site", sc.SIM_VEC_SITE, "8d95d8ffffff"),
        ("et site", sc.ET_SITE, "bb03000000"),
        ("pk site", sc.PK_SITE, "5589e583ec08"),
        ("cards site", sc.CARDS_SITE, "8d95d4ffffff"),
        ("fatigue site", sc.FATIGUE_SITE, "8d8df8ffffff"),
        ("ai_fatigue site", sc.AI_FATIGUE_SITE, "0f84de000000"),
    ]:
        h.restore()
        orig = g.read(addr, len(expected_hex) // 2)
        poke(g, addr, bytes([orig[0] ^ 0x01]) + orig[1:])
        l2, _, w2 = run(g, source)
        assert l2[-1].startswith("RESULT: nothing written.") and not w2, (name, l2)

    h.restore()
    poke(g, sc.OUTCOME_SITE, b"\xe9\x11\x22\x33\x44\x90\x90")
    l2, _, w2 = run(g, source)
    assert "already modified" in l2[-1] and not w2, l2

    for cave_addr in (sc.CAVE + 100, sc.CAVE_D + 20, sc.CAVE_D2 + 10, sc.CAVE_ET + 20, sc.WIN_CDF_2D_ADDR + 20, sc.CAVE_PK + 20, sc.CAVE_C + 20):
        h.restore()
        poke(g, cave_addr, b"\xaa")
        l2, _, w2 = run(g, source)
        assert l2[-1].startswith("RESULT: nothing written.") and not w2, (hex(cave_addr), l2)

    h.restore()
    l2, _, _ = run(g, source, sticky=lambda a: a != sc.FATIGUE_SITE)
    assert l2[-1].startswith("RESULT: a change did not go in."), l2
    print("ok 5: tamper detection across all 13 sites & all 6 caves, e9 check, and sticky failure verified")

    # 6. Install and run REAL PES2017.exe machine code (`fcn_03707a1f` + `fcn_03705feb`)
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2

    for ovr0, ovr1 in [(80, 80), (85, 75), (75, 85), (90, 65), (65, 90), (82, 79)]:
        diff = ovr0 - ovr1
        counts = [0, 0, 0]
        idx = [0]
        h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
        for _ in range(1000):
            counts[h.run_outcome(ovr0, ovr1)] += 1
        exp_row = sc.build_outcome_table()[diff - sc.DIFF_MIN]
        assert counts[0] == exp_row[0], (ovr0, ovr1, counts, exp_row)
        assert counts[2] == exp_row[1] - exp_row[0], (ovr0, ovr1, counts, exp_row)
        assert counts[1] == 1000 - exp_row[1], (ovr0, ovr1, counts, exp_row)
        assert counts[0] >= 1 and counts[1] >= 1
    print("ok 6: real fcn_03707a1f outcome counts across 1000-point sweeps match Python table exactly")

    rng = random.Random(2026)
    h.state["rand_fn"] = lambda n: rng.randrange(n)

    draw_scores = collections.Counter()
    for _ in range(2000):
        hg, ag = h.run_score(2, 80, 80)
        assert hg == ag and 0 <= hg <= 4, (hg, ag)
        draw_scores[(hg, ag)] += 1
    assert abs(draw_scores[(1, 1)] / 2000 - 0.46) < 0.04, draw_scores
    assert abs(draw_scores[(0, 0)] / 2000 - 0.28) < 0.04, draw_scores

    for res, ovr0, ovr1, label in [
        (0, 80, 80, "equal home win"),
        (1, 80, 80, "equal away win"),
        (0, 90, 68, "giant home win"),
        (1, 70, 88, "giant away win"),
        (0, 70, 85, "upset home win"),
    ]:
        total_w = total_l = blowouts_4gd = blowouts_50 = 0
        for _ in range(1000):
            hg, ag = h.run_score(res, ovr0, ovr1)
            if res == 0:
                assert 1 <= hg <= 6 and 0 <= ag < hg, (label, hg, ag)
                total_w += hg
                total_l += ag
                if hg - ag >= 4:
                    blowouts_4gd += 1
                if (hg, ag) == (5, 0):
                    blowouts_50 += 1
            else:
                assert 1 <= ag <= 6 and 0 <= hg < ag, (label, hg, ag)
                total_w += ag
                total_l += hg
                if ag - hg >= 4:
                    blowouts_4gd += 1
                if (ag, hg) == (5, 0):
                    blowouts_50 += 1
        avg_w, avg_l = total_w / 1000, total_l / 1000
        assert 1.75 <= avg_w <= 3.1 and 0.2 <= avg_l <= 0.7, (label, avg_w, avg_l)
        if label == "upset home win":
            assert blowouts_50 == 0 and blowouts_4gd <= 10, (blowouts_50, blowouts_4gd)
    print("ok 7: real fcn_03705feb scorelines satisfy invariants and realistic Poisson frequencies")

    # 7. Master League captain role bonus scaling
    cap_player_ptr = g.alloc(size=0x20)
    cap_vec_buf = g.alloc(struct.pack("<I", cap_player_ptr))
    g.write(cap_player_ptr + 0x18, struct.pack("<I", 0))
    cap_rec_home = g.alloc(size=0x100)
    g.write(cap_rec_home + 0xc4, bytes([5]))
    cap_rec_away = g.alloc(size=0x100)
    h.set_mode_kind(0x0c)

    cap_calls = [0]

    def cap_player_lookup(gm, a):
        idx_c = cap_calls[0] % 2
        cap_calls[0] += 1
        return cap_rec_home if idx_c == 0 else cap_rec_away

    def cap_vec_one(gm, a):
        role = struct.unpack("<I", gm.read(a(0), 4))[0]
        out = a(1)
        if role == 5:
            gm.write(out, struct.pack("<III", cap_vec_buf, cap_vec_buf + 4, cap_vec_buf + 4))
        else:
            gm.write(out, b"\x00" * 12)
        return out

    g.replace(0x03822835, cap_player_lookup)
    g.replace(CAP_ROLES_VEC, cap_vec_one)
    g.replace(CAP_BONUS_FN, lambda gm, a: 20)
    idx = [0]
    h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
    counts = [0, 0, 0]
    for _ in range(1000):
        counts[h.run_outcome(80, 80)] += 1
    cap_ovr = int(20 * sc.DEFAULT_SETTINGS["CAPTAIN_WEIGHT"])
    assert cap_ovr == 2
    exp_row = sc.build_outcome_table()[cap_ovr - sc.DIFF_MIN]
    assert counts[0] == exp_row[0], (counts, exp_row)
    g.replace(0x03822835, lambda gm, a: h.player_map.get((a(0), a(1)), h.dummy_player))
    g.replace(CAP_ROLES_VEC, lambda gm, a: (gm.write(a(1), b"\x00" * 12), a(1))[1])
    h.set_mode_kind(0x13)
    print("ok 8: ML captain role bonus scales cleanly (+20 raw -> +2 OVR)")

    # 8. Feature 1: Dynamic Match Ratings (real fcn_03708cc4)
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2

    # Build an 11-player XI with varied positions, goals, and assists
    squad_spec = [
        (1, 1001, 0, 0, 0, 0),   # GK (pos 0)
        (2, 1002, 10, 1, 0, 0),  # CB (pos 1)
        (3, 1003, 12, 2, 0, 1),  # FB (pos 2) + 1 assist
        (4, 1004, 15, 3, 0, 0),  # DMF (pos 3)
        (5, 1005, 45, 4, 1, 0),  # CMF (pos 4) + 1 goal
        (6, 1006, 65, 6, 0, 2),  # AMF (pos 6) + 2 assists
        (7, 1007, 72, 8, 1, 1),  # WF (pos 8) + 1 goal, 1 assist
        (8, 1008, 82, 9, 2, 0),  # CF (pos 9) + 2 goals
        (9, 1009, 20, 1, 0, 0),  # CB (pos 1)
        (10, 1010, 40, 2, 0, 0), # FB (pos 2)
        (11, 1011, 55, 8, 0, 0), # WF (pos 8)
    ]

    for res, side, hg, ag in [
        (0, 0, 4, 0),  # Home clean-sheet 4-0 win
        (0, 1, 4, 0),  # Away 0-4 heavy loss
        (0, 1, 5, 0),  # Away 0-5 loss (tests conceded penalty cap=3 and min clamp 4.5)
        (2, 0, 1, 1),  # 1-1 draw
        (1, 0, 1, 3),  # Home 1-3 loss (heavy conceded for defenders)
    ]:
        vec, recs = h.alloc_squad(squad_spec)
        h.set_match(comp_id=1, team0_id=100, team1_id=200, hg=hg, ag=ag)
        # Test exact deterministic match against Python compute_rating() across rand values
        for r_val in (0, 4, 8):
            h.state["rand_fn"] = (lambda rv: lambda n: rv % n)(r_val)
            g.call(RATINGS_FN, [res, side, h.match, vec], ecx=h.sim_obj)
            gf, ga = (hg, ag) if side == 0 else (ag, hg)
            for id_lo, id_hi, _, pos, goals, assists in squad_spec:
                got = h.read_rating(recs[(id_lo, id_hi)])
                exp = sc.compute_rating(res, side, gf, ga, pos, goals, assists, r_val)
                assert got == exp, (res, side, hg, ag, pos, goals, assists, r_val, got, exp)

    # Max clamp check (hat-trick + 2 assists on 4-0 win -> clamped at 9.5 = 95)
    vec_hi, recs_hi = h.alloc_squad([(77, 7077, 90, 9, 3, 2)])
    h.set_match(comp_id=1, team0_id=100, team1_id=200, hg=4, ag=0)
    h.state["rand_fn"] = lambda n: 8
    g.call(RATINGS_FN, [0, 0, h.match, vec_hi], ecx=h.sim_obj)
    assert h.read_rating(recs_hi[(77, 7077)]) == 95

    # Dummy player (stat_rec + 0x04 == 0) must keep 0 rating
    vec_dum, recs_dum = h.alloc_squad([(99, 9099, 50, 9, 2, 1)])
    g.write(recs_dum[(99, 9099)] + 0x04, struct.pack("<I", 0))  # dummy marker
    g.write(recs_dum[(99, 9099)] + 0x00, struct.pack("<I", 0))
    # Ensure non-dummy checks match: [0x24fff60] is 0, so [rec + 4] == 0 skips write
    h.set_match(comp_id=1, team0_id=100, team1_id=200, hg=2, ag=0)
    h.state["rand_fn"] = lambda n: 4
    g.call(RATINGS_FN, [0, 0, h.match, vec_dum], ecx=h.sim_obj)
    assert h.read_rating(recs_dum[(99, 9099)]) == 0

    # Card rating deductions (1 yellow = -0.3, 2 yellows = -0.6, red = -1.0)
    vec_c, recs_c = h.alloc_squad([(1, 3001, 50, 4, 0, 0), (2, 3002, 50, 4, 0, 0), (3, 3003, 50, 4, 0, 0)])
    g.write(recs_c[(1, 3001)] + 0x0c, struct.pack("<I", (4 << 14) | (1 << 19)))  # 1 yellow
    g.write(recs_c[(2, 3002)] + 0x0c, struct.pack("<I", (4 << 14) | (1 << 18) | (2 << 19)))  # 2nd yellow red
    g.write(recs_c[(3, 3003)] + 0x0c, struct.pack("<I", (4 << 14) | (1 << 18)))  # straight red
    h.set_match(comp_id=1, team0_id=100, team1_id=200, hg=1, ag=1)
    h.state["rand_fn"] = lambda n: 4  # zero variance
    g.call(RATINGS_FN, [2, 0, h.match, vec_c], ecx=h.sim_obj)
    assert h.read_rating(recs_c[(1, 3001)]) == sc.compute_rating(2, 0, 1, 1, 4, 0, 0, 4, yellows=1)  # 6.1 - 0.3 = 5.8
    assert h.read_rating(recs_c[(2, 3002)]) == sc.compute_rating(2, 0, 1, 1, 4, 0, 0, 4, yellows=2, red=1)  # 6.1 - 1.0 = 5.1
    assert h.read_rating(recs_c[(3, 3003)]) == sc.compute_rating(2, 0, 1, 1, 4, 0, 0, 4, red=1)  # 6.1 - 1.0 = 5.1

    # RATINGS=false falls back to vanilla rating tables (0x2105a40..a98)
    h.restore()
    l2, _, _ = run(g, set_lua(source, "RATINGS", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    vec_v, recs_v = h.alloc_squad(squad_spec)
    h.set_match(comp_id=1, team0_id=100, team1_id=200, hg=2, ag=0)
    g.call(RATINGS_FN, [0, 0, h.match, vec_v], ecx=h.sim_obj)
    # In vanilla win: slot 0 (sorted desc by +8 -> CF with stat=82) gets win[0]=6.2 + 0.3 (goals>0) = 6.5 (65)
    assert h.read_rating(recs_v[(8, 1008)]) == 65, h.read_rating(recs_v[(8, 1008)])
    print("ok 9: real fcn_03708cc4 dynamic ratings match Python across W/D/L, GD, CS, goals, assists, and vanilla fallback")

    # 9. Feature 2: Realistic Goal Scorers & Assists (real fcn_03706ef6)
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2

    # Realistic 11-man squad sorted descending by stat (+0x08): CF(84), WF(81), WF(80), AMF(77), CMF(71), CMF(69), DMF(62), FB(58), FB(56), CB(42), CB(40), GK(0)
    scorer_squad = [
        (1, 2001, 84, 9, 0, 0),  # CF
        (2, 2002, 81, 8, 0, 0),  # WF
        (3, 2003, 80, 8, 0, 0),  # WF
        (4, 2004, 77, 6, 0, 0),  # AMF
        (5, 2005, 71, 4, 0, 0),  # CMF
        (6, 2006, 69, 4, 0, 0),  # CMF
        (7, 2007, 62, 3, 0, 0),  # DMF
        (8, 2008, 58, 2, 0, 0),  # FB
        (9, 2009, 56, 2, 0, 0),  # FB
        (10, 2010, 42, 1, 0, 0), # CB
        (11, 2011, 0, 0, 0, 0),  # GK (stat=0 -> must never score or assist!)
    ]
    vec_s, recs_s = h.alloc_squad(scorer_squad)
    h.set_match(comp_id=1, team0_id=100, team1_id=200, hg=3, ag=1)
    out_id = g.alloc(size=8)

    # Exact deterministic sweep for goal scorer distribution (matches SCORER_W weights!)
    sw = sc.build_scorer_weights()
    exp_gw = [sw[min(23, (84 - st) >> 2)] if st > 0 else 0 for _, _, st, _, _, _ in scorer_squad]
    tot_gw = sum(exp_gw)
    got_g_counts = collections.Counter()
    for r_i in range(tot_gw):
        # Reset goals byte on all stat recs so they don't hit 0x63 cap
        for rec in recs_s.values():
            g.write(rec + 0x08, b"\x00\x00")
        h.state["rand_fn"] = (lambda rv: lambda n: rv % n)(r_i)
        g.write(out_id, b"\x00" * 8)
        g.call(SCORER_FN, [1, h.match, vec_s, out_id], stdcall=True)
        picked_lo = struct.unpack("<H", g.read(out_id, 2))[0]
        picked_hi = struct.unpack("<I", g.read(out_id + 4, 4))[0]
        got_g_counts[(picked_lo, picked_hi)] += 1
        assert g.read(recs_s[(picked_lo, picked_hi)] + 0x08, 1)[0] == 1
    assert got_g_counts.get((11, 2011), 0) == 0, "GK scored!"
    for i, (id_lo, id_hi, _, _, _, _) in enumerate(scorer_squad[:10]):
        assert got_g_counts[(id_lo, id_hi)] == exp_gw[i], (i, got_g_counts[(id_lo, id_hi)], exp_gw[i])

    # Assist test: 28% unassisted + 72% weighted across non-scorer outfielders, zero self-assists
    for rec in recs_s.values():
        g.write(rec + 0x08, b"\x00\x00")
    h.state["rand_fn"] = lambda n: rng.randrange(n)
    unassisted = 0
    assist_counts = collections.Counter()
    N_ASSISTS = 1500
    for _ in range(N_ASSISTS):
        for rec in recs_s.values():
            g.write(rec + 0x08, b"\x00\x00")
        # Pretend CF (1, 2001) scored the goal
        g.write(out_id, struct.pack("<HIH", 1, 0, 2001)[:4] + struct.pack("<I", 2001))
        g.write(out_id, struct.pack("<II", 1, 2001))
        g.call(SCORER_FN, [0, h.match, vec_s, out_id], stdcall=True)
        total_a = sum(g.read(rec + 0x09, 1)[0] for rec in recs_s.values())
        if total_a == 0:
            unassisted += 1
        else:
            assert total_a == 1
            for k, rec in recs_s.items():
                if g.read(rec + 0x09, 1)[0] == 1:
                    assist_counts[k] += 1
    assert assist_counts.get((1, 2001), 0) == 0, "Self-assist occurred!"
    assert assist_counts.get((11, 2011), 0) == 0, "GK assisted!"
    assert abs(unassisted / N_ASSISTS - 0.28) < 0.04, (unassisted, N_ASSISTS)
    # Defenders (FB/CB) actually contribute assists instead of vanilla top-5 cutoff
    assert assist_counts[(8, 2008)] > 0 and assist_counts[(9, 2009)] > 0, assist_counts

    # Independent gating: SCORERS=false, ASSISTS=true runs vanilla scorer + enhanced assist
    h.restore()
    l2, _, _ = run(g, set_lua(source, "SCORERS", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    # In vanilla scorer, slot >= 5 can NEVER score even at rand = n-1
    h.state["rand_fn"] = lambda n: n - 1
    for rec in recs_s.values():
        g.write(rec + 0x08, b"\x00\x00")
    g.write(out_id, b"\x00" * 8)
    g.call(SCORER_FN, [1, h.match, vec_s, out_id], stdcall=True)
    assert struct.unpack("<H", g.read(out_id, 2))[0] <= 5  # vanilla top-5 only!

    # UNASSISTED_PCT = 100 -> every assist call produces 0 assists; short 4-player squad works cleanly
    h.restore()
    l2, _, _ = run(g, set_lua(source, "UNASSISTED_PCT", "100"))
    assert l2[-1].startswith("RESULT: installed."), l2
    vec_short, recs_short = h.alloc_squad(scorer_squad[:4])
    for rec in recs_short.values():
        g.write(rec + 0x08, b"\x00\x00")
    h.state["rand_fn"] = lambda n: 0
    g.write(out_id, struct.pack("<II", 1, 2001))
    g.call(SCORER_FN, [0, h.match, vec_short, out_id], stdcall=True)
    assert sum(g.read(rec + 0x09, 1)[0] for rec in recs_short.values()) == 0
    g.call(SCORER_FN, [1, h.match, vec_short, out_id], stdcall=True)
    assert sum(g.read(rec + 0x08, 1)[0] for rec in recs_short.values()) == 1
    print("ok 10: real fcn_03706ef6 scorers & assists match Python weights, 0% GK, 0% self-assist, ~28% unassisted")

    # 10. Special fallback cases: mode 0x27/0x28 + comp 0x3c/0x3d, and SCOPE="skip_only"
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2

    h.set_menu_mode(0x28)
    h.set_match(comp_id=0x3c, team0_id=100, team1_id=200)
    idx = [0]
    h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
    counts = [0, 0, 0]
    for _ in range(100):
        counts[h.run_outcome(80, 80)] += 1
    assert counts == [8, 67, 25], counts
    idx = [0]
    counts2 = [0, 0, 0]
    for _ in range(100):
        counts2[h.run_outcome(81, 80)] += 1
    assert counts2 == [67, 8, 25], counts2
    h.set_menu_mode(0x13)
    h.set_match(comp_id=1, team0_id=100, team1_id=200)

    h.restore()
    l2, _, _ = run(g, set_lua(source, "SCOPE", '"skip_only"'))
    assert l2[-1].startswith("RESULT: installed."), l2
    h.set_skip_flag(True)
    h.set_team_user(0, False)
    h.set_team_user(1, False)
    assert h.run_outcome(90, 75) == 0
    # In skip_only for AI-vs-AI, RATINGS also falls back to vanilla
    vec_ai, recs_ai = h.alloc_squad(squad_spec)
    h.set_match(comp_id=1, team0_id=100, team1_id=200, hg=2, ag=0)
    g.call(RATINGS_FN, [0, 0, h.match, vec_ai], ecx=h.sim_obj)
    assert h.read_rating(recs_ai[(8, 1008)]) == 65  # vanilla win[0]=62 + 3

    h.set_skip_flag(False)
    h.set_team_user(0, True)
    h.state["rand_fn"] = lambda n: n - 1
    assert h.run_outcome(90, 75) == 0
    h.set_skip_flag(True)
    assert h.run_outcome(90, 75) == 1
    h.set_team_user(0, False)
    h.set_skip_flag(False)
    print('ok 11: mode 0x27/0x28+comp 0x3c/0x3d fallback and SCOPE="skip_only" gating verified')

    # 11. Feature 3: Extra Time (fcn_037062ca) & Penalty Shootout (fcn_037063bb)
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2

    # 11a. Extra Time: strength-scaled 0..2 ET goals, match+0x15/0x18 written, no-PK & 2-leg away-goal preserved
    h.state["ovr0"] = 80
    h.state["ovr1"] = 80
    h.state["et_flag"] = 1
    h.state["pk_flag"] = 1
    h.state["rand_fn"] = lambda n: rng.randrange(n)
    et_h_sum = et_a_sum = et_draws = 0
    for _ in range(1000):
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=2, hg=1, ag=1)
        g.write(h.res_buf, struct.pack("<I", 2))
        g.call(ET_FN, [h.res_buf, h.match], ecx=h.sim_obj)
        et_h = g.read(h.match + 0x15, 1)[0]
        et_a = g.read(h.match + 0x18, 1)[0]
        res_et = struct.unpack("<I", g.read(h.res_buf, 4))[0]
        assert 0 <= et_h <= 2 and 0 <= et_a <= 2, (et_h, et_a)
        if et_h > et_a:
            assert res_et == 0
        elif et_a > et_h:
            assert res_et == 1
        else:
            et_draws += 1
        et_h_sum += et_h
        et_a_sum += et_a
    # Equal teams (with +3 home advantage): total ~0.52 ET goals, ~55-68% ET draws
    assert 0.35 <= (et_h_sum + et_a_sum) / 1000 <= 0.70, (et_h_sum, et_a_sum)
    assert 500 <= et_draws <= 720, et_draws

    # Favorite (90 vs 70) outscores underdog in ET
    h.state["ovr0"] = 90
    h.state["ovr1"] = 70
    fav_et = dog_et = 0
    for _ in range(1000):
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=2, hg=1, ag=1)
        g.call(ET_FN, [h.res_buf, h.match], ecx=h.sim_obj)
        fav_et += g.read(h.match + 0x15, 1)[0]
        dog_et += g.read(h.match + 0x18, 1)[0]
    assert fav_et > dog_et * 1.4, (fav_et, dog_et)

    # No-PK rule (0x03856ca8 == 0): when ET ends level, match+0x15 gets +1 and res=0
    h.state["et_flag"] = 0
    h.state["rand_fn"] = lambda n: n - 1  # both 0 ET goals -> draw
    h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=2, hg=1, ag=1)
    g.call(ET_FN, [h.res_buf, h.match], ecx=h.sim_obj)
    assert g.read(h.match + 0x15, 1)[0] == 1 and struct.unpack("<I", g.read(h.res_buf, 4))[0] == 0

    # 2-leg ET away-goals rule (0x03856e48 == 1): 0-0 in ET after 1-1 -> away advances (res=1)
    g.replace(0x03856e48, lambda gm, a: 1)
    h.state["et_flag"] = 1
    h.state["rand_fn"] = lambda n: 100 if n == 1000 else 0  # wait: p2 < 100 < p1 -> 1 goal each!
    h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=1, hg=1, ag=1)
    g.call(ET_FN, [h.res_buf, h.match], ecx=h.sim_obj)
    assert g.read(h.match + 0x15, 1)[0] == 1 and g.read(h.match + 0x18, 1)[0] == 1
    assert struct.unpack("<I", g.read(h.res_buf, 4))[0] == 1  # away-goals rule!
    g.replace(0x03856e48, lambda gm, a: 0)

    # 11b. Penalty Shootout: fixes vanilla rand(1) 100%-home-win bug + OVR weighting + realistic scores
    # Equal teams (80 vs 80): exact deterministic sweep -> 50% home, 50% away
    h.state["ovr0"] = 80
    h.state["ovr1"] = 80
    pk_wins = [0, 0]
    pk_scores = set()
    for i in range(100):
        h.state["rand_fn"] = (lambda rv: lambda n: rv % n)(i)
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=2, hg=1, ag=1)
        g.call(PK_FN, [h.res_buf, h.match], ecx=h.sim_obj)
        res_pk = struct.unpack("<I", g.read(h.res_buf, 4))[0]
        pkh = g.read(h.match + 0x16, 1)[0]
        pka = g.read(h.match + 0x19, 1)[0]
        pk_wins[res_pk] += 1
        if res_pk == 0:
            assert pkh > pka and (pkh, pka) in sc.PK_PAIRS, (pkh, pka)
        else:
            assert pka > pkh and (pka, pkh) in sc.PK_PAIRS, (pkh, pka)
        pk_scores.add((max(pkh, pka), min(pkh, pka)))
    assert pk_wins == [50, 50], pk_wins
    assert len(pk_scores) >= 6, pk_scores

    # OVR shift: 90 vs 70 (+20 OVR * 0.5 = +10% -> 60% home win)
    h.state["ovr0"] = 90
    h.state["ovr1"] = 70
    pk_wins_fav = [0, 0]
    for i in range(100):
        h.state["rand_fn"] = (lambda rv: lambda n: rv % n)(i)
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=2, hg=1, ag=1)
        g.call(PK_FN, [h.res_buf, h.match], ecx=h.sim_obj)
        pk_wins_fav[struct.unpack("<I", g.read(h.res_buf, 4))[0]] += 1
    assert pk_wins_fav == [60, 40], pk_wins_fav

    # EXTRA_TIME_PK=false falls back to vanilla (PK rand(1) -> 100% home win!)
    h.restore()
    l2, _, _ = run(g, set_lua(source, "EXTRA_TIME_PK", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    h.state["rand_fn"] = lambda n: rng.randrange(n)
    for _ in range(20):
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=2, hg=1, ag=1)
        g.call(PK_FN, [h.res_buf, h.match], ecx=h.sim_obj)
        assert struct.unpack("<I", g.read(h.res_buf, 4))[0] == 0  # vanilla bug!
    print("ok 12: real ET (0x037062ca) & PK (0x037063bb) fix 100%-home PK bug, scale by OVR, preserve rules")

    # 12. Feature 4: Yellow & Red Cards (0x03708f45 inside fcn_03708de9) + Rating Integration
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.state["ovr0"] = 80
    h.state["ovr1"] = 80
    h.state["rand_fn"] = lambda n: rng.randrange(n)

    # Run 300 full SIM_MATCH_FN simulations with real 11-player home + away squads and real RATINGS_FN
    card_squad_h = [
        (1, 4001, 0, 0, 0, 0),   # GK (w=2)
        (2, 4002, 10, 1, 0, 0),  # CB (w=18)
        (3, 4003, 12, 1, 0, 0),  # CB (w=18)
        (4, 4004, 15, 2, 0, 0),  # FB (w=16)
        (5, 4005, 20, 2, 0, 0),  # FB (w=16)
        (6, 4006, 30, 3, 0, 0),  # DMF (w=20)
        (7, 4007, 45, 4, 0, 0),  # CMF (w=14)
        (8, 4008, 60, 6, 0, 0),  # AMF (w=8)
        (9, 4009, 70, 8, 0, 0),  # WF (w=7)
        (10, 4010, 75, 8, 0, 0), # WF (w=7)
        (11, 4011, 82, 9, 0, 0), # CF (w=8)
    ]
    card_squad_a = [(100 + lo, 5000 + lo, st, pos, 0, 0) for lo, _, st, pos, _, _ in card_squad_h]
    tot_y = tot_r = gk_cards = def_cards = att_cards = second_y_reds = straight_reds = 0
    N_CARD_MATCHES = 300
    for _ in range(N_CARD_MATCHES):
        vec_h, recs_h = h.alloc_squad(card_squad_h, clear=True)
        vec_a, recs_a = h.alloc_squad(card_squad_a, clear=False)
        h.state["vec0"] = vec_h
        h.state["vec1"] = vec_a
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)
        g.call(SIM_MATCH_FN, [h.match], ecx=h.sim_obj)
        for side_recs in (recs_h, recs_a):
            for idx_p, (k, rec) in enumerate(side_recs.items()):
                y, r = h.read_cards(rec)
                assert 0 <= y <= 2 and r in (0, 1)
                tot_y += y
                tot_r += r
                if r and y == 2:
                    second_y_reds += 1
                elif r and y < 2:
                    straight_reds += 1
                if idx_p == 0:
                    gk_cards += y + r
                elif 1 <= idx_p <= 5:
                    def_cards += y + r
                elif idx_p >= 8:
                    att_cards += y + r
                # Every player received a valid rating in [4.5, 9.5]
                rat = h.read_rating(rec)
                assert 45 <= rat <= 95, rat
    h.state["vec0"] = None
    h.state["vec1"] = None
    avg_y_per_team = tot_y / (2 * N_CARD_MATCHES)
    assert 1.2 <= avg_y_per_team <= 2.1, avg_y_per_team
    assert straight_reds > 0 and second_y_reds > 0, (straight_reds, second_y_reds)
    assert def_cards > att_cards * 2 and def_cards > gk_cards * 8, (gk_cards, def_cards, att_cards)

    # CARDS=false leaves stat_rec card bits at 0
    h.restore()
    l2, _, _ = run(g, set_lua(source, "CARDS", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    for _ in range(20):
        vec_h, recs_h = h.alloc_squad(card_squad_h, clear=True)
        vec_a, recs_a = h.alloc_squad(card_squad_a, clear=False)
        h.state["vec0"] = vec_h
        h.state["vec1"] = vec_a
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)
        g.call(SIM_MATCH_FN, [h.match], ecx=h.sim_obj)
        for rec in list(recs_h.values()) + list(recs_a.values()):
            assert h.read_cards(rec) == (0, 0)
    h.state["vec0"] = None
    h.state["vec1"] = None
    print(f"ok 13: CARDS_HOOK produces avg {avg_y_per_team:.2f} Y/team, 2nd-Y ({second_y_reds}) + straight-R ({straight_reds}), position-weighted, rating-integrated")

    # 13. Knockout & 2-leg loop termination in fcn_03708de9
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.state["rand_fn"] = lambda n: rng.randrange(n)
    h.state["et_flag"] = 0
    h.state["pk_flag"] = 1
    for ovr0, ovr1 in [(80, 80), (95, 60), (60, 95)]:
        h.state["ovr0"] = ovr0
        h.state["ovr1"] = ovr1
        for _ in range(20):
            h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=2)
            g.call(SIM_MATCH_FN, [h.match], ecx=h.sim_obj)
            hg = g.read(h.match + 0x14, 1)[0]
            ag = g.read(h.match + 0x17, 1)[0]
            pkh = g.read(h.match + 0x16, 1)[0]
            pka = g.read(h.match + 0x19, 1)[0]
            assert (hg != ag) or (pkh != pka), (ovr0, ovr1, hg, ag, pkh, pka)
    h.state["ovr0"] = 80
    h.state["ovr1"] = 80
    h.state["leg1_h"] = 1
    h.state["leg1_a"] = 0
    h.state["away_goals"] = 1
    for _ in range(30):
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=1)
        g.call(SIM_MATCH_FN, [h.match], ecx=h.sim_obj)
        hg = g.read(h.match + 0x14, 1)[0]
        ag = g.read(h.match + 0x17, 1)[0]
        assert not (hg == 1 and ag == 0), "2-leg tie stayed tied at 1-0 agg (1-1)!"
    print("ok 14: fcn_03708de9 knockout and 2-leg aggregate tie-breaker loops terminate cleanly")

    # 14. SKIP_SUBS instruction check at 0x03708230
    h.restore()
    poke(g, sc.SKIP_SUBS_SITE, b"\xeb\x17")
    frame = g.alloc(size=0x400) + 0x300
    g.write(frame - 0x160, struct.pack("<I", h.mode_data))
    g.write(frame - 0x120, struct.pack("<III", 3, 5, 7))
    h.set_skip_flag(True)
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EBP, UC_X86_REG_ESP
    g.mu.reg_write(UC_X86_REG_ESP, STACK + STACK_SIZE - 0x1000)
    g.mu.reg_write(UC_X86_REG_EBP, frame)
    g.mu.reg_write(UC_X86_REG_ECX, 0)
    g.mu.emu_start(0x03708224, 0x03708249)
    assert struct.unpack("<III", g.read(frame - 0x120, 12)) == (3, 5, 7)
    print("ok 15: SKIP_SUBS patch at 0x03708230 skips sub=11 overwrite during Skip Match")

    # 16. Feature 5a: CONDITION_STRENGTH (eff_strength + real fcn_0385b771)
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)
    h.state["ovr0"] = 80
    h.state["ovr1"] = 80

    # Empty squads fall back cleanly to TEAM_STRENGTH
    h.clear_squads()
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 80
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=200) == 80

    # Build 13-player home squad (11 starters + 2 bench) & 11-player neutral away squad
    h_ids = []
    for i in range(13):
        pid = (i + 1, 6001 + i)
        h_ids.append(pid)
        h.alloc_player(*pid, team_id=100, ovr=80 if i < 11 else 70, pos=0 if i == 0 else 9, arrow=2, fitness=100)
    a_ids = []
    for i in range(11):
        pid = (100 + i + 1, 7001 + i)
        a_ids.append(pid)
        h.alloc_player(*pid, team_id=200, ovr=80, pos=0 if i == 0 else 9, arrow=2, fitness=100)
    h.set_team_squad(0, h_ids)
    h.set_team_squad(1, a_ids)
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 80
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=200) == 80

    # Blue arrows (+3) vs red arrows (-3) match Python compute_eff_ovr
    for i, pid in enumerate(h_ids[:11]):
        h.alloc_player(*pid, team_id=100, ovr=80, arrow=4, fitness=100)
    for i, pid in enumerate(a_ids):
        h.alloc_player(*pid, team_id=200, ovr=80, arrow=0, fitness=100)
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 83
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=200) == 77

    # Low fitness (36 < 72, penalty 5 -> -3 OVR) drops eff_ovr from 83 to 80
    for pid in h_ids[:11]:
        h.alloc_player(*pid, team_id=100, ovr=80, arrow=4, fitness=36)
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 80

    # Injured (attr 0x5e > 0) & banned players excluded via real fcn_0385b771 -> bench (70) + 40-fill!
    for i, pid in enumerate(h_ids):
        h.alloc_player(*pid, team_id=100, ovr=80 if i < 11 else 70, arrow=2, fitness=100, inj_days=5 if i < 2 else 0)
    h.ban_set.add(h_ids[2])  # 3rd starter suspended -> 8 starters (80) + 2 bench (70) + 1 empty slot (40)
    exp_inj = sc.compute_eff_ovr([(80, 2, 100, True)] * 8 + [(70, 2, 100, True)] * 2)
    got_inj = g.call(sc.CAVE_ET, [], ecx=h.match, edx=100)
    assert got_inj == exp_inj, (got_inj, exp_inj)

    # Effective OVR propagates into OUTCOME_FN (even when base ovr0 == ovr1 == 80!)
    h.ban_set.clear()
    for pid in h_ids[:11]:
        h.alloc_player(*pid, team_id=100, ovr=80, arrow=4, fitness=100)  # eff = 83
    for pid in a_ids:
        h.alloc_player(*pid, team_id=200, ovr=80, arrow=0, fitness=36)   # eff = 74 (+9 eff diff!)
    idx = [0]
    h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
    counts = [0, 0, 0]
    for _ in range(1000):
        counts[h.run_outcome(80, 80)] += 1
    exp_row = sc.build_outcome_table()[9 - sc.DIFF_MIN]
    assert counts[0] == exp_row[0] and counts[2] == exp_row[1] - exp_row[0], (counts, exp_row)

    # CONDITION_STRENGTH=false (with LINEUP_STRENGTH=true) evaluates raw OVR without arrow/fatigue
    h.restore()
    l2, _, _ = run(g, set_lua(source, "CONDITION_STRENGTH", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 80
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=200) == 80

    # LINEUP_STRENGTH: Starting XI via tactics+0x248, positional OVR via tactics+0x68,
    # injured/banned starter bench replacement, and invalid tactics fallback
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.clear_squads()
    h.state["ovr0"] = 80
    lineup_ids = [(10 + i, 6500 + i) for i in range(18)]
    # Squad 0..6 weak (65), 7..17 strong (85); Starting XI uses indices [11..17, 7..10] -> all 85!
    for i, pid in enumerate(lineup_ids):
        h.alloc_player(*pid, team_id=100, ovr=65 if i < 7 else 85, pos=0 if i == 11 else 9, arrow=2, fitness=100)
    h.set_team_squad(0, lineup_ids)
    # Without tactics, top-11 of squad = all 11 of 85 -> 85; now pick weak starters [0..6, 11..14] -> 7*65 + 4*85 = 72.27 -> 72
    weak_xi = [0, 1, 2, 3, 4, 5, 6, 11, 12, 13, 14]
    h.set_team_tactics(0, weak_xi)
    exp_weak = sc.compute_eff_ovr([(65, 2, 100, True)] * 7 + [(85, 2, 100, True)] * 4)
    assert exp_weak == 72
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == exp_weak

    # Positional OVR (tactics+0x68): starter slot 7 (lineup_ids[11]) plays at pos=8 where OVR is 55 -> drops team!
    h.ovr_pos_map[(lineup_ids[11][0], lineup_ids[11][1], 8)] = 55
    exp_oop = sc.compute_eff_ovr([(65, 2, 100, True)] * 7 + [(55, 2, 100, True)] + [(85, 2, 100, True)] * 3)
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == exp_oop
    h.ovr_pos_map.clear()

    # Injured/banned starter in weak_xi is replaced by top eligible non-starter (85) -> 6*65 + 5*85 = 74
    h.alloc_player(*lineup_ids[0], team_id=100, ovr=65, pos=0, arrow=2, fitness=100, inj_days=4)
    h.ban_set.add(lineup_ids[1])  # 2 unavailable starters -> replaced by two 85s from bench (15, 16)
    exp_rep = sc.compute_eff_ovr([(65, 2, 100, True)] * 5 + [(85, 2, 100, True)] * 6)
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == exp_rep
    h.ban_set.clear()
    h.alloc_player(*lineup_ids[0], team_id=100, ovr=65, pos=0, arrow=2, fitness=100, inj_days=0)

    # Sentinel tactics_rec (mode_data+0x5fea64), out-of-range index, or duplicate index falls back to squad top-11 (85)
    h.set_team_tactics(0, weak_xi, sentinel=True)
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 85
    h.set_team_tactics(0, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 25])  # 25 >= n_squad (18)
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 85
    h.set_team_tactics(0, [0, 0, 2, 3, 4, 5, 6, 7, 8, 9, 10])  # duplicate 0
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 85

    # LINEUP_STRENGTH=false (with CONDITION_STRENGTH=true) ignores valid weak_xi and uses squad top-11 (85)
    h.set_team_tactics(0, weak_xi)
    h.restore()
    l2, _, _ = run(g, set_lua(source, "LINEUP_STRENGTH", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 85

    # Both CONDITION_STRENGTH=false and LINEUP_STRENGTH=false restore base TEAM_STRENGTH (80)
    h.restore()
    l2, _, _ = run(g, set_lua(set_lua(source, "CONDITION_STRENGTH", "false"), "LINEUP_STRENGTH", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=100) == 80
    assert g.call(sc.CAVE_ET, [], ecx=h.match, edx=200) == 80
    h.clear_squads()
    print("ok 16: eff_strength evaluates tactics Starting XI + position, bench replacement, fallbacks, arrow & fitness, and outcomes")

    # 17. Feature 5b: STAMINA_FATIGUE + AI_FATIGUE in real fcn_038556f1
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    FAT_FN = 0x038556f1
    mins_buf = g.alloc(size=4)
    fix_buf = g.alloc(size=4)
    g.write(fix_buf, struct.pack("<I", 1))

    def run_fatigue(p_ptr, mins, et=False):
        g.write(mins_buf, struct.pack("<I", mins))
        g.write(h.match + 0x15, bytes([1 if et else 0, 0, 0, 0]))
        g.call(FAT_FN, [p_ptr, mins_buf, fix_buf])

    # AI team (user=False) drains when AI_FATIGUE=true; Stamina 95 < 75 < 55; GK 0.9x; ET +30 min
    h.set_team_user(0, False)
    p_hi = h.alloc_player(1, 8001, team_id=100, pos=9, stamina=95, fitness=100)
    p_md = h.alloc_player(2, 8002, team_id=100, pos=9, stamina=75, fitness=100)
    p_lo = h.alloc_player(3, 8003, team_id=100, pos=9, stamina=55, fitness=100)
    p_gk = h.alloc_player(4, 8004, team_id=100, pos=0, stamina=75, fitness=100)
    p_et = h.alloc_player(5, 8005, team_id=100, pos=9, stamina=75, fitness=100)
    p_120 = h.alloc_player(6, 8006, team_id=100, pos=9, stamina=75, fitness=100)

    run_fatigue(p_hi, 90, et=False)
    run_fatigue(p_md, 90, et=False)
    run_fatigue(p_lo, 90, et=False)
    run_fatigue(p_gk, 90, et=False)
    run_fatigue(p_et, 90, et=True)   # simulated ET -> 90 + 30 = 120 mins
    run_fatigue(p_120, 120, et=True)  # played ET already 120 mins -> no double +30!

    loss_hi = 100 - h.read_player_fitness(p_hi)
    loss_md = 100 - h.read_player_fitness(p_md)
    loss_lo = 100 - h.read_player_fitness(p_lo)
    loss_gk = 100 - h.read_player_fitness(p_gk)
    loss_et = 100 - h.read_player_fitness(p_et)
    loss_120 = 100 - h.read_player_fitness(p_120)
    assert loss_hi == sc.compute_fatigue_loss(90, 95, 9) == 22, loss_hi
    assert loss_md == sc.compute_fatigue_loss(90, 75, 9) == 27, loss_md
    assert loss_lo == sc.compute_fatigue_loss(90, 55, 9) == 32, loss_lo
    assert loss_gk == sc.compute_fatigue_loss(90, 75, 0) == 24, loss_gk
    assert loss_et == sc.compute_fatigue_loss(90, 75, 9, extra_time=True) == 36, loss_et
    assert loss_120 == loss_et, (loss_120, loss_et)

    # AI_FATIGUE=false skips AI team (fitness stays 100) while draining user team
    h.restore()
    l2, _, _ = run(g, set_lua(source, "AI_FATIGUE", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    p_ai = h.alloc_player(7, 8007, team_id=100, pos=9, stamina=75, fitness=100)
    h.set_team_user(0, False)
    run_fatigue(p_ai, 90, et=False)
    assert h.read_player_fitness(p_ai) == 100
    h.set_team_user(0, True)
    run_fatigue(p_ai, 90, et=False)
    assert h.read_player_fitness(p_ai) == 100 - 27
    h.set_team_user(0, False)

    # STAMINA_FATIGUE=false leaves vanilla AI skip + vanilla 0.3*mins
    h.restore()
    l2, _, _ = run(g, set_lua(source, "STAMINA_FATIGUE", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    p_van = h.alloc_player(8, 8008, team_id=100, pos=9, stamina=55, fitness=100)
    h.set_team_user(0, True)
    run_fatigue(p_van, 90, et=False)
    assert h.read_player_fitness(p_van) == 100 - 27  # ignores stamina=55
    h.set_team_user(0, False)
    h.clear_squads()
    print("ok 17: real fcn_038556f1 stamina fatigue, GK 0.9x, ET +30m (no double-add), and AI_FATIGUE toggle verified")

    # 18. Feature 5c: INJURY_PCT & INJURY_DAYS via CARDS_HOOK -> INJURY_FN
    h.restore()
    inj_src = set_lua(set_lua(source, "INJURY_PCT", "20"), "CARDS", "false")
    inj_src = set_lua(inj_src, "INJURY_DAYS", "{ 10, 20 }")
    l2, _, _ = run(g, inj_src)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.state["ovr0"] = 80
    h.state["ovr1"] = 80
    h.state["rand_fn"] = lambda n: rng.randrange(n)

    inj_squad = [
        (1, 9001, 0, 0, 0, 0),   # GK -> never injured
        (2, 9002, 10, 1, 0, 0),  # IR=2, fit=100 -> w=1
        (3, 9003, 12, 1, 0, 0),
        (4, 9004, 15, 2, 0, 0),
        (5, 9005, 20, 2, 0, 0),
        (6, 9006, 30, 3, 0, 0),
        (7, 9007, 45, 4, 0, 0),
        (8, 9008, 60, 6, 0, 0),
        (9, 9009, 70, 8, 0, 0),
        (10, 9010, 75, 8, 0, 0),
        (11, 9011, 82, 9, 0, 0), # IR=0, fit=50 -> w=3+2=5 (5x slot 2)
    ]
    inj_hits = [0] * 11
    inj_days_seen = []
    for _ in range(300):
        vec_i, recs_i = h.alloc_squad(inj_squad, clear=True)
        ptrs = []
        for idx_p, (lo, hi, _, pos, _, _) in enumerate(inj_squad):
            ir = 2 if idx_p == 1 else (0 if idx_p == 10 else 1)
            fit = 50 if idx_p == 10 else 100
            ptrs.append(h.alloc_player(lo, hi, team_id=100, pos=pos, inj_res=ir, fitness=fit, inj_days=0))
        h.state["vec0"] = vec_i
        h.state["vec1"] = None
        h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)
        g.call(SIM_MATCH_FN, [h.match], ecx=h.sim_obj)
        # CARDS=false -> zero cards issued
        for rec in recs_i.values():
            assert h.read_cards(rec) == (0, 0)
        for idx_p, p_ptr in enumerate(ptrs):
            d = h.read_player_injury(p_ptr)
            if d > 0:
                inj_hits[idx_p] += 1
                inj_days_seen.append(d)
                assert 10 <= d <= 20, d
    assert inj_hits[0] == 0, "GK must never be injured!"
    assert 35 <= sum(inj_hits) <= 95, inj_hits
    assert inj_hits[10] > inj_hits[1] * 2, (inj_hits[10], inj_hits[1])

    # Guard: <= 7 healthy players in squad -> never injures!
    h.state["rand_fn"] = lambda n: 0
    vec_g, _ = h.alloc_squad(inj_squad, clear=True)
    ptrs_g = [
        h.alloc_player(lo, hi, team_id=100, pos=pos, inj_days=5 if idx_p >= 7 else 0)
        for idx_p, (lo, hi, _, pos, _, _) in enumerate(inj_squad)
    ]
    h.state["vec0"] = vec_g
    h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)
    g.call(SIM_MATCH_FN, [h.match], ecx=h.sim_obj)
    for idx_p in range(7):
        assert h.read_player_injury(ptrs_g[idx_p]) == 0
    h.state["vec0"] = None
    h.clear_squads()
    print(f"ok 18: INJURY_FN issued {sum(inj_hits)}/300 injuries (GK=0, IR0+tired={inj_hits[10]} vs IR2+fresh={inj_hits[1]}), <=7 guard & CARDS=false verified")

    # 19. Feature 6: GK_PROTECT (0x0370818d) + SMART_SUBS (0x037080d9) in fcn_03707e71
    from unicorn.x86_const import UC_X86_REG_EBX, UC_X86_REG_EBP, UC_X86_REG_ESI, UC_X86_REG_ESP
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    frame6 = g.alloc(size=0x400) + 0x300
    g.write(frame6 + 0x08, struct.pack("<I", h.match))
    g.write(frame6 - 0x160, struct.pack("<I", h.mode_data))

    # 19a. GK_PROTECT: even when rand(5)==0 and rand(4)==0, sub1 is 1..4 (never slot 0 GK!)
    for r0 in range(5):
        for r1 in range(4):
            seq = iter([r0, r1, 0, 0])
            h.state["rand_fn"] = lambda n, s=seq: next(s) % n
            g.mu.reg_write(UC_X86_REG_ESP, STACK + STACK_SIZE - 0x1010)
            g.mu.reg_write(UC_X86_REG_EBP, frame6)
            g.mu.reg_write(UC_X86_REG_ESI, h.team0)
            g.mu.emu_start(0x03708152, 0x03708220)
            sub1 = struct.unpack("<i", g.read(frame6 - 0x1c, 4))[0]
            assert 1 <= sub1 <= 4, (r0, r1, sub1)

    # GK_PROTECT=false allows vanilla rand(5)==0 + rand(5)==0 -> sub1 == 0 (GK subbed off!)
    h.restore()
    l2, _, _ = run(g, set_lua(source, "GK_PROTECT", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    seq = iter([0, 0, 0, 0])
    h.state["rand_fn"] = lambda n, s=seq: next(s) % n
    g.mu.reg_write(UC_X86_REG_ESP, STACK + STACK_SIZE - 0x1010)
    g.mu.reg_write(UC_X86_REG_EBP, frame6)
    g.mu.reg_write(UC_X86_REG_ESI, h.team0)
    g.mu.emu_start(0x03708152, 0x03708220)
    assert struct.unpack("<i", g.read(frame6 - 0x1c, 4))[0] == 0

    # 19b. SMART_SUBS: bench sort key = eff_ovr + rand(4), descending via fcn_03705ef2
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)
    p_star = h.alloc_player(1, 9101, team_id=100, ovr=84, pos=9, arrow=4, fitness=100)  # 84 + 3 = 87
    p_tired = h.alloc_player(2, 9102, team_id=100, ovr=80, pos=9, arrow=0, fitness=40)  # 80 - 3 - 2 = 75
    p_low = h.alloc_player(3, 9103, team_id=100, ovr=68, pos=9, arrow=2, fitness=100)   # 68

    def eval_sub_key(p_ptr, jitter):
        h.state["rand_fn"] = lambda n, j=jitter: j % n
        g.write(frame6 - 0x14c, struct.pack("<I", p_ptr))
        g.mu.reg_write(UC_X86_REG_ESP, STACK + STACK_SIZE - 0x1000)
        g.mu.reg_write(UC_X86_REG_EBP, frame6)
        g.mu.reg_write(UC_X86_REG_EBX, 0xdeadbeef)
        g.mu.emu_start(0x037080ac, 0x037080f1)
        assert g.mu.reg_read(UC_X86_REG_EBX) == 0xdeadbeef, "ebx clobbered by smart_subs!"
        return g.read(frame6 - 0x19c, 1)[0]

    k_star = eval_sub_key(p_star, 0)
    k_tired = eval_sub_key(p_tired, 3)
    k_low = eval_sub_key(p_low, 3)
    assert k_star == 87, k_star
    assert k_tired == 78, k_tired
    assert k_low == 71, k_low
    assert k_star > k_tired > k_low

    # Verify PES2017.exe comparator fcn_03705ef2 sorts k_star BEFORE k_tired (descending)
    ent_a = g.alloc(struct.pack("<IIB", 1, 9101, k_star) + b"\x00\x00\x00")
    ent_b = g.alloc(struct.pack("<IIB", 2, 9102, k_tired) + b"\x00\x00\x00")
    assert g.call(0x03705ef2, [ent_a, ent_b]) == 1
    assert g.call(0x03705ef2, [ent_b, ent_a]) == 0

    # SCOPE="skip_only" when NOT skip-match falls back to vanilla rand(100)
    h.restore()
    l2, _, _ = run(g, set_lua(source, "SCOPE", '"skip_only"'))
    assert l2[-1].startswith("RESULT: installed."), l2
    h.set_skip_flag(False)
    h.set_team_user(0, False)
    assert eval_sub_key(p_star, 42) == 42
    h.set_skip_flag(True)
    h.set_team_user(0, True)
    assert eval_sub_key(p_star, 2) == 89
    h.set_skip_flag(False)
    h.set_team_user(0, False)

    # SMART_SUBS=false falls back to vanilla rand(100)
    h.restore()
    l2, _, _ = run(g, set_lua(source, "SMART_SUBS", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    assert eval_sub_key(p_star, 77) == 77
    h.clear_squads()
    print("ok 19: GK_PROTECT (never sub1==0) & SMART_SUBS (eff_ovr + rand(4), descending fcn_03705ef2, scope/toggle fallbacks) verified")

    # 21. v7 Feature: ATTACK_DEFENSE_SPLIT (eff_strength ATK/DEF + 7x7 WIN_CDF_2D + 5-band DRAW_CDF_BANDS)
    from unicorn.x86_const import UC_X86_REG_EDX
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.clear_squads()
    h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)

    # Verify parity between WIN_CDF diagonal and WIN_CDF_2D diagonal, and DRAW_CDF vs DRAW_CDF_BANDS[2]
    wc1d = sc.build_win_cdf()
    wc2d = sc.build_win_cdf_2d()
    for b in range(7):
        assert wc2d[b * 7 + b] == wc1d[b], b
    assert sc.build_draw_cdf_bands()[2] == sc.build_draw_cdf()

    # Build asymmetric squads: Home = high ATK (90), low DEF (68) (with CMF=80); Away = low ATK (68), high DEF (90)
    # Default tactics pos_ids = [0, 1, 2, 2, 3, 6, 7, 8, 9, 9, 10] -> 5 DEF (pos<=4), 6 ATK (pos>=6)
    h_as_ids = [(10 + i, 9200 + i) for i in range(11)]
    a_as_ids = [(30 + i, 9300 + i) for i in range(11)]
    for i, pid in enumerate(h_as_ids):
        h.alloc_player(*pid, team_id=100, ovr=68 if i < 5 else 90, pos=1 if i < 5 else 9, arrow=2, fitness=100)
    for i, pid in enumerate(a_as_ids):
        h.alloc_player(*pid, team_id=200, ovr=90 if i < 5 else 68, pos=1 if i < 5 else 9, arrow=2, fitness=100)
    h.set_team_squad(0, h_as_ids)
    h.set_team_squad(1, a_as_ids)
    h.set_team_tactics(0, list(range(11)), [0, 1, 2, 2, 4, 5, 6, 7, 9, 9, 12])  # 5 DEF, 1 CMF (slot 5), 5 ATK
    h.set_team_tactics(1, list(range(11)), [0, 1, 2, 2, 4, 5, 6, 7, 9, 9, 12])

    exp_h_ovr, exp_h_atk, exp_h_def = sc.compute_eff_atk_def(
        [(68 if i < 5 else 90, [0, 1, 2, 2, 4, 5, 6, 7, 9, 9, 12][i]) for i in range(11)]
    )
    exp_a_ovr, exp_a_atk, exp_a_def = sc.compute_eff_atk_def(
        [(90 if i < 5 else 68, [0, 1, 2, 2, 4, 5, 6, 7, 9, 9, 12][i]) for i in range(11)]
    )
    ovr_h = g.call(sc.CAVE_ET, [], ecx=h.match, edx=100)
    edx_h = g.mu.reg_read(UC_X86_REG_EDX)
    assert (ovr_h, edx_h & 0xff, (edx_h >> 8) & 0xff) == (exp_h_ovr, exp_h_atk, exp_h_def), (ovr_h, edx_h, exp_h_ovr, exp_h_atk, exp_h_def)
    ovr_a = g.call(sc.CAVE_ET, [], ecx=h.match, edx=200)
    edx_a = g.mu.reg_read(UC_X86_REG_EDX)
    assert (ovr_a, edx_a & 0xff, (edx_a >> 8) & 0xff) == (exp_a_ovr, exp_a_atk, exp_a_def), (ovr_a, edx_a, exp_a_ovr, exp_a_atk, exp_a_def)

    # Also test no-tactics reg_pos fallback (without setting tactics)
    h.tactics_map.clear()
    h.g.write(h.team0 + 0x1f8, b"\x00" * 8)
    h.alloc_player(*h_as_ids[5], team_id=100, ovr=90, pos=5, arrow=2, fitness=100)
    exp_nt = sc.compute_eff_atk_def(
        [(68 if i < 5 else 90, 1 if i < 5 else (5 if i == 5 else 9)) for i in range(11)]
    )
    ovr_nt = g.call(sc.CAVE_ET, [], ecx=h.match, edx=100)
    edx_nt = g.mu.reg_read(UC_X86_REG_EDX)
    assert (ovr_nt, edx_nt & 0xff, (edx_nt >> 8) & 0xff) == exp_nt, (ovr_nt, edx_nt, exp_nt)

    # Scoreline test: high-ATK vs low-DEF (both 90 ATK / 68 DEF) vs low-ATK vs high-DEF (both 68 ATK / 90 DEF)
    for i, pid in enumerate(h_as_ids):
        h.alloc_player(*pid, team_id=100, ovr=68 if i < 5 else 90, pos=1 if i < 5 else 9, arrow=2, fitness=100)
    for i, pid in enumerate(a_as_ids):
        h.alloc_player(*pid, team_id=200, ovr=68 if i < 5 else 90, pos=1 if i < 5 else 9, arrow=2, fitness=100)
    h.set_team_tactics(0, list(range(11)), [0, 1, 2, 2, 4, 6, 7, 8, 9, 9, 12])
    h.set_team_tactics(1, list(range(11)), [0, 1, 2, 2, 4, 6, 7, 8, 9, 9, 12])
    h.state["rand_fn"] = lambda n: rng.randrange(n)

    hi_win_goals = sum(sum(h.run_score(0, 80, 80)) for _ in range(1000))
    hi_draw_goals = sum(sum(h.run_score(2, 80, 80)) for _ in range(1000))

    for i, pid in enumerate(h_as_ids):
        h.alloc_player(*pid, team_id=100, ovr=90 if i < 5 else 68, pos=1 if i < 5 else 9, arrow=2, fitness=100)
    for i, pid in enumerate(a_as_ids):
        h.alloc_player(*pid, team_id=200, ovr=90 if i < 5 else 68, pos=1 if i < 5 else 9, arrow=2, fitness=100)
    lo_win_goals = sum(sum(h.run_score(0, 80, 80)) for _ in range(1000))
    lo_draw_goals = sum(sum(h.run_score(2, 80, 80)) for _ in range(1000))
    assert hi_win_goals > lo_win_goals + 300, (hi_win_goals, lo_win_goals)
    assert hi_draw_goals > lo_draw_goals + 300, (hi_draw_goals, lo_draw_goals)

    # ATTACK_DEFENSE_SPLIT=false -> eff_strength returns atk == def == overall_ovr
    h.restore()
    l2, _, _ = run(g, set_lua(source, "ATTACK_DEFENSE_SPLIT", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    ovr_off = g.call(sc.CAVE_ET, [], ecx=h.match, edx=100)
    edx_off = g.mu.reg_read(UC_X86_REG_EDX)
    assert (edx_off & 0xff) == ovr_off and ((edx_off >> 8) & 0xff) == ovr_off, (ovr_off, edx_off)
    h.clear_squads()
    print(f"ok 21: ATTACK_DEFENSE_SPLIT (eff_strength ATK/DEF + 7x7 WIN_CDF_2D + 5-band DRAW_CDF_BANDS: high {hi_win_goals/1000:.2f}/{hi_draw_goals/1000:.2f} vs low {lo_win_goals/1000:.2f}/{lo_draw_goals/1000:.2f} GPG) verified")

    # 22. v7 Feature: sim_vec_hook at 0x0370875c (fcn_037085b5 scorer/assist weights, pos, arrow & fatigue)
    from unicorn.x86_const import UC_X86_REG_EDI
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    saved_sv_stub = g.replaced.pop(0x037085b5)
    g.replace(0x03853d91, lambda gm, a: 0)
    frame_sv = g.alloc(size=0x400) + 0x300
    g.write(frame_sv + 0x0c, struct.pack("<I", h.match))
    g.write(frame_sv - 0x1c, struct.pack("<I", h.mode_data))

    def eval_sim_vec(p_ptr):
        g.mu.reg_write(UC_X86_REG_ESP, STACK + STACK_SIZE - 0x1000)
        g.mu.reg_write(UC_X86_REG_EBP, frame_sv)
        g.mu.reg_write(UC_X86_REG_ESI, p_ptr)
        g.mu.reg_write(UC_X86_REG_EDI, 5)
        g.mu.emu_start(0x037086b6, 0x037087e1)
        assert g.mu.reg_read(UC_X86_REG_ESI) == p_ptr, "esi clobbered by sim_vec!"
        assert g.mu.reg_read(UC_X86_REG_EDI) == 5, "edi clobbered by sim_vec!"
        sw = struct.unpack("<i", g.read(frame_sv - 0x14, 4))[0]
        aw = g.mu.reg_read(UC_X86_REG_EBX)
        return sw, aw

    h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)
    sv_cases = [
        # (pos, fin, atk_prow, header, low_pass, lofted_pass, arrow, fitness)
        (0,  99, 99, 99, 99, 99, 4, 100),  # GK -> always (0, 0)
        (1,  50, 50, 75, 65, 65, 2, 100),  # CB -> scorer -22, assist -20
        (2,  55, 60, 60, 75, 78, 2, 100),  # LB -> scorer -24, assist -10
        (4,  65, 65, 70, 82, 80, 3, 100),  # DMF -> scorer -18, assist -8, green arrow +2
        (5,  72, 74, 65, 86, 84, 2, 100),  # CMF -> scorer -4, assist +0
        (8,  80, 84, 60, 90, 88, 4, 100),  # AMF -> scorer +8, assist +6, blue arrow +6
        (9,  88, 90, 65, 85, 82, 2, 100),  # LWF -> scorer +10, assist +4
        (12, 95, 96, 92, 72, 65, 4, 100),  # CF -> scorer +12, assist +0, blue arrow +6
        (12, 99, 99, 99, 99, 99, 4, 100),  # High values: (119, 204)
        (1,  40, 40, 40, 40, 40, 0, 36),   # Low values with red arrow and fatigue: (7, 49)
        (1,  10, 10, 10, 10, 10, 0, 36),   # Clamp floor to 1!
    ]
    for idx_c, (pos, fin, ap, hdr, lp, loft, arr, fit) in enumerate(sv_cases):
        p = h.alloc_player(
            idx_c + 1, 9500 + idx_c, pos=pos, finishing=fin, atk_prow=ap,
            header=hdr, low_pass=lp, lofted_pass=loft, arrow=arr, fitness=fit,
        )
        got = eval_sim_vec(p)
        exp = sc.compute_sim_vec_weights(pos, fin, ap, hdr, lp, loft, arr, fit)
        assert got == exp, (idx_c, pos, got, exp)

    # CONDITION_STRENGTH=false disables arrow & fatigue adjustment in sim_vec
    h.restore()
    l2, _, _ = run(g, set_lua(source, "CONDITION_STRENGTH", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    p_cf = h.alloc_player(20, 9520, pos=12, finishing=85, atk_prow=85, header=80, low_pass=70, lofted_pass=70, arrow=4, fitness=36)
    assert eval_sim_vec(p_cf) == sc.compute_sim_vec_weights(
        12, 85, 85, 80, 70, 70, 4, 36, settings={"CONDITION_STRENGTH": False}
    )

    # SCORERS=false + ASSISTS=true: vanilla CB(-10)/FB(-5) scorer, v7 assist
    h.restore()
    l2, _, _ = run(g, set_lua(source, "SCORERS", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    p_cb = h.alloc_player(21, 9521, pos=1, finishing=50, atk_prow=90, header=90, low_pass=75, lofted_pass=75, arrow=4, fitness=100)
    assert eval_sim_vec(p_cb) == (40, 136)  # vanilla CB scorer 50-10=40, v7 assist 150-20+6=136

    # SCORERS=true + ASSISTS=false: v8 scorer, vanilla CB(-20)/FB(-10) assist
    h.restore()
    l2, _, _ = run(g, set_lua(source, "ASSISTS", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    assert eval_sim_vec(p_cb) == (58, 130)  # v8 scorer 74-22+6=58, vanilla CB assist 150-20=130

    # SCOPE="skip_only" when not skip-match falls back to vanilla for both
    h.restore()
    l2, _, _ = run(g, set_lua(source, "SCOPE", '"skip_only"'))
    assert l2[-1].startswith("RESULT: installed."), l2
    h.set_skip_flag(False)
    h.set_team_user(0, False)
    assert eval_sim_vec(p_cb) == (40, 130)
    h.set_skip_flag(True)
    h.set_team_user(0, True)
    assert eval_sim_vec(p_cb) == sc.compute_sim_vec_weights(1, 50, 90, 90, 75, 75, 4, 100)
    h.set_skip_flag(False)
    h.set_team_user(0, False)

    g.replaced[0x037085b5] = saved_sv_stub
    del g.replaced[0x03853d91]
    h.clear_squads()
    print("ok 22: real fcn_037085b5 sim_vec_hook (scorer/assist formulas, pos, GK=0, [1,255] clamp, arrow/fatigue, toggles) verified")

    # 23. Dedicated GK OVR & 1.5x condition arrow modifier on goals conceded (eff_strength -> score_hook)
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)
    h_gk_ids = [(10 + i, 9600 + i) for i in range(12)]  # 11 starters + 1 backup GK
    a_gk_ids = [(30 + i, 9700 + i) for i in range(11)]
    for i, pid in enumerate(h_gk_ids):
        if i == 0:
            h.alloc_player(*pid, team_id=100, ovr=86, pos=0, arrow=4, fitness=100)  # 86 + 6 = 92
        elif i == 11:
            h.alloc_player(*pid, team_id=100, ovr=78, pos=0, arrow=1, fitness=100)  # backup GK: 78 - 3 = 75
        else:
            h.alloc_player(*pid, team_id=100, ovr=78, pos=1 if i <= 4 else 9, arrow=2, fitness=100)
    for i, pid in enumerate(a_gk_ids):
        h.alloc_player(*pid, team_id=200, ovr=68 if i == 0 else 78, pos=0 if i == 0 else (1 if i <= 4 else 9),
                       arrow=0 if i == 0 else 2, fitness=100)  # Away GK: 68 - 6 = 62
    h.set_team_squad(0, h_gk_ids)
    h.set_team_squad(1, a_gk_ids)
    t_pos = [0, 1, 2, 2, 4, 5, 6, 7, 9, 9, 12]
    h.set_team_tactics(0, list(range(11)), t_pos)
    h.set_team_tactics(1, list(range(11)), t_pos)

    # Check eff_strength packs gk_eff in edx[16..23] and excludes GK from def_ovr (78)
    g.call(sc.CAVE_ET, [], ecx=h.match, edx=100)
    edx_h_gk = g.mu.reg_read(UC_X86_REG_EDX)
    assert (edx_h_gk & 0xff) == 78 and ((edx_h_gk >> 8) & 0xff) == 78, hex(edx_h_gk)
    assert ((edx_h_gk >> 16) & 0xff) == sc.compute_gk_eff_ovr(86, 4, 100) == 92, hex(edx_h_gk)

    g.call(sc.CAVE_ET, [], ecx=h.match, edx=200)
    edx_a_gk = g.mu.reg_read(UC_X86_REG_EDX)
    assert (edx_a_gk & 0xff) == 78 and ((edx_a_gk >> 8) & 0xff) == 78, hex(edx_a_gk)
    assert ((edx_a_gk >> 16) & 0xff) == sc.compute_gk_eff_ovr(68, 0, 100) == 62, hex(edx_a_gk)

    # Injured starter GK replaced by backup GK (slot 11: 78 - 3 = 75)
    h.alloc_player(*h_gk_ids[0], team_id=100, ovr=86, pos=0, arrow=4, fitness=100, inj_days=5)
    g.call(sc.CAVE_ET, [], ecx=h.match, edx=100)
    edx_bk = g.mu.reg_read(UC_X86_REG_EDX)
    assert ((edx_bk >> 16) & 0xff) == 75, hex(edx_bk)
    # Restore elite starter GK (92)
    h.alloc_player(*h_gk_ids[0], team_id=100, ovr=86, pos=0, arrow=4, fitness=100, inj_days=0)

    # An injured OUTFIELD starter is filled by a bench outfielder (60 CMF), never by the
    # higher-rated backup GK (75): bench GKs only enter once the XI has no keeper,
    # mirroring the game's own sub picker fcn_03706d2e (playable proficiency 0 outfield).
    # (The GK counts in the overall at his outfield-arrow eff 86+3; the gk byte stays 92.)
    h.set_team_squad(0, h_gk_ids + [(22, 9622)])
    h.alloc_player(22, 9622, team_id=100, ovr=60, pos=5, arrow=2, fitness=100)
    h.alloc_player(*h_gk_ids[10], team_id=100, ovr=78, pos=9, arrow=2, fitness=100, inj_days=5)
    ovr_cf_out = g.call(sc.CAVE_ET, [], ecx=h.match, edx=100)
    edx_cf_out = g.mu.reg_read(UC_X86_REG_EDX)
    exp_cf_out = sc.compute_eff_atk_def([(89, 0)] + [(78, p) for p in t_pos[1:10]] + [(60, 5)])
    assert (ovr_cf_out, edx_cf_out & 0xff, (edx_cf_out >> 8) & 0xff) == exp_cf_out, (
        ovr_cf_out, hex(edx_cf_out), exp_cf_out)
    assert ((edx_cf_out >> 16) & 0xff) == 92, hex(edx_cf_out)  # starter GK still in goal
    h.alloc_player(*h_gk_ids[10], team_id=100, ovr=78, pos=9, arrow=2, fitness=100, inj_days=0)

    # Scoreline impact: Home win (Home GK 92 vs Away GK 62) vs Away win (Home GK 92 vs Away GK 62)
    # In Home wins, Winner=Home(GK=92 -> high CS, low gl); in Away wins, Winner=Away(GK=62) vs Loser=Home(GK=92 -> low gw)
    idx = [0]
    h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
    elite_conceded = 0
    elite_cs = 0
    for _ in range(1000):
        gh, ga = h.run_score(0, 78, 78)  # Home wins, Home GK=92
        elite_conceded += ga
        if ga == 0:
            elite_cs += 1

    # Flip Home GK to weak red-arrow (62)
    h.alloc_player(*h_gk_ids[0], team_id=100, ovr=68, pos=0, arrow=0, fitness=100)
    weak_conceded = 0
    weak_cs = 0
    for _ in range(1000):
        gh, ga = h.run_score(0, 78, 78)  # Home wins, Home GK=62
        weak_conceded += ga
        if ga == 0:
            weak_cs += 1
    assert elite_conceded + 200 < weak_conceded, (elite_conceded, weak_conceded)
    assert elite_cs > weak_cs + 120, (elite_cs, weak_cs)

    # Also test draws: both GKs=92 produces lower-scoring draws than both GKs=62
    h.alloc_player(*h_gk_ids[0], team_id=100, ovr=86, pos=0, arrow=4, fitness=100)
    h.alloc_player(*a_gk_ids[0], team_id=200, ovr=86, pos=0, arrow=4, fitness=100)
    gk_hi_draw = sum(sum(h.run_score(2, 78, 78)) for _ in range(1000))
    h.alloc_player(*h_gk_ids[0], team_id=100, ovr=68, pos=0, arrow=0, fitness=100)
    h.alloc_player(*a_gk_ids[0], team_id=200, ovr=68, pos=0, arrow=0, fitness=100)
    gk_lo_draw = sum(sum(h.run_score(2, 78, 78)) for _ in range(1000))
    assert gk_hi_draw + 300 < gk_lo_draw, (gk_hi_draw, gk_lo_draw)

    # calc_gk_delta (version 8): a keeper rated GK_BASELINE = 82 is neutral, and the
    # machine code agrees with compute_gk_delta for every rating
    score_code = bytes.fromhex(sc.CODE_PARTS["score"][1])
    gkd = sc.CODE_PARTS["score"][0] + score_code.index(bytes.fromhex("515283e8")) - 9  # push ecx; push edx; sub eax, imm8
    gk_delta = lambda gk: (g.call(gkd, [], eax=gk) ^ 0x80000000) - 0x80000000
    assert sc.GK_BASELINE == 82
    assert [sc.compute_gk_delta(x) for x in (62, 76, 79, 80, 82, 84, 85, 92, 99)] == [-4, -2, -1, 0, 0, 0, 1, 3, 5]
    for gk in range(1, 110):
        assert gk_delta(gk) == sc.compute_gk_delta(gk), (gk, gk_delta(gk))

    # GK_SCORE_MOD=false disables GK delta & clean-sheet boost
    h.restore()
    l2, _, _ = run(g, set_lua(source, "GK_SCORE_MOD", "false"))
    assert l2[-1].startswith("RESULT: installed."), l2
    h.alloc_player(*h_gk_ids[0], team_id=100, ovr=86, pos=0, arrow=4, fitness=100)
    off_hi = sum(h.run_score(0, 78, 78)[1] for _ in range(500))
    h.alloc_player(*h_gk_ids[0], team_id=100, ovr=68, pos=0, arrow=0, fitness=100)
    off_lo = sum(h.run_score(0, 78, 78)[1] for _ in range(500))
    assert abs(off_hi - off_lo) <= 25, (off_hi, off_lo)
    assert gk_delta(92) == 0 and gk_delta(62) == 0
    h.clear_squads()
    print(f"ok 23: GK_SCORE_MOD (1.5x GK arrow, GK_delta with neutral keeper 82 = mirror for 1..109, CS boost: elite {elite_conceded/1000:.2f} GA / {elite_cs/10:.1f}% CS vs weak {weak_conceded/1000:.2f} GA / {weak_cs/10:.1f}% CS) verified")

    # 20. Coexistence with MLMoney.lua, MLTransfers.lua, and MLYear.lua in any order
    del h
    money_src = open(tm.MODULE, encoding="utf-8").read()
    trans_src = open(tm.MODULE_T, encoding="utf-8").read()
    year_src = open(YEAR_MODULE, encoding="utf-8").read()
    for order in (
        (source, money_src, trans_src, year_src),
        (money_src, trans_src, year_src, source),
        (year_src, money_src, source, trans_src),
    ):
        g2 = Game(exe)
        l_all, _, _ = run(g2, tm.SPLIT.join(order))
        res_lines = [l for l in l_all if l.startswith("RESULT")]
        assert len(res_lines) == 4 and all(l.startswith("RESULT: installed.") for l in res_lines), res_lines
    print("ok 20: installs cleanly alongside MLMoney.lua, MLTransfers.lua, and MLYear.lua in any order")

    calibration(exe)


SAVE = os.path.join(HERE, "..", "ML saves", "ML00000013 (before)")


def calibration(exe):
    """Version 8 defaults on the clubs of a real save (best eleven of each club, all fit):
    who scores the goals, and how far the twenty best clubs spread in a league of their own."""
    import window_report as wr
    save, rate = wr.Save(SAVE), wr.Rater(exe)
    squads = collections.defaultdict(list)
    for r in save.players.values():
        if wr.club(r) in save.ranking:
            squads[wr.club(r)].append((rate(r), wr.position(r), r))
    table, share, top, strength = sc.build_scorer_weights(), collections.Counter(), [], {}
    for club, squad in squads.items():
        squad.sort(key=lambda t: -t[0])
        xi = []
        for positions, count in (((0,), 1), ((1,), 2), ((2,), 1), ((3,), 1)):
            xi += [t for t in squad if t[1] in positions][:count]
        for t in squad:                                  # six more: no keeper, at most two SS/CF
            if len(xi) < 11 and t not in xi and t[1] and (t[1] < 11 or sum(x[1] > 10 for x in xi) < 2):
                xi.append(t)
        if len(xi) < 11:
            continue
        stat = [sc.compute_sim_vec_weights(pos, wr.u32(r, 8) & 0x7f, r[3] & 0x7f, wr.u32(r, 8) >> 21 & 0x7f, 0, 0, 2, 100)[0]
                for _, pos, r in xi]
        w = [table[min(23, (max(stat) - x) >> 2)] if x else 0 for x in stat]
        top.append(max(w) / sum(w))
        for (_, pos, _), x in zip(xi, w):
            share["CF" if pos == 12 else "defenders" if 1 <= pos <= 3 else "others"] += x / sum(w)
        strength[save.ranking[club]["place"]] = sc.compute_eff_atk_def([(o, pos) for o, pos, _ in xi])[0]
    n = len(top)
    cf, defenders, median = share["CF"] / n, share["defenders"] / n, sorted(top)[n // 2]
    assert n > 400 and 0.27 <= cf <= 0.38 and defenders <= 0.15 and median <= 0.35 and max(top) <= 0.60, (n, cf, defenders, median, max(top))

    best = [strength[k] for k in sorted(strength)[:20]]
    out = sc.build_outcome_table()
    wins, draws, home, games = [0.0] * 20, 0.0, 0.0, 0
    for i, j in ((i, j) for i in range(20) for j in range(20) if i != j):
        ph, phd = out[max(sc.DIFF_MIN, min(sc.DIFF_MAX, best[i] - best[j])) - sc.DIFF_MIN]
        wins[i] += ph / 1000; wins[j] += 1 - phd / 1000; draws += (phd - ph) / 1000; home += ph / 1000; games += 1
    first, last = max(wins) / 38, min(wins) / 38
    # home wins up to 50%: HOME_ADVANTAGE was raised to 2.5 after the suggestion audit
    # (just above version 7's 2.4), putting home wins a touch above real football's ~45%
    assert 0.55 <= first <= 0.75 and last <= 0.28 and 0.23 <= draws / games <= 0.27 and 0.42 <= home / games <= 0.50, (first, last, draws / games, home / games)
    print(f"ok 24: version 8 defaults on {n} clubs of a save: CF {cf:.0%} of the goals, defenders {defenders:.0%}, best scorer of a club {median:.0%} "
          f"(most {max(top):.0%}); the 20 best clubs among themselves: first wins {first:.0%}, last {last:.0%}, draws {draws / games:.0%}, home wins {home / games:.0%}")


if __name__ == "__main__":
    main(sys.argv[1])
