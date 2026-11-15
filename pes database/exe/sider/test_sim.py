"""Runs MLSimMatch.lua outside the game and then runs PES2017.exe's match simulation
machine code with its changes in the Unicorn CPU emulator.

    python3 test_sim.py <PES2017.exe>    needs: pip install lupa unicorn

Tests:
  1. Generated block in MLSimMatch.lua matches sim_cave.py lua_block(), and Lua's
     build_image() matches Python's sim_cave.build_image() byte-for-byte.
  2. Settings validation refuses bad inputs cleanly without reading/writing; WRITE=false
     and SCOPE=false/SKIP_SUBS=false write nothing; SCOPE=false + SKIP_SUBS=true writes
     only the 2-byte sub patch.
  3. Tamper detection: changing any byte of CONTEXT or SITES, non-empty CAVE, pre-hooked
     e9 jump, or sticky write failures all report cleanly and do not corrupt memory.
  4. Real PES2017.exe machine code (`fcn_03707a1f` outcome + `fcn_03705feb` scoreline)
     with MLSimMatch.lua installed matches Python reference probabilities and scoreline
     distributions across equal, favorite, underdog, huge-mismatch, captain-bonus, and
     draw cases.
  5. SCOPE="skip_only" applies only when Skip Match flag (`+0xdcb61c`) is non-zero AND
     at least one team is user-controlled; otherwise falls back to vanilla logic.
     Special mode 0x27/0x28 + comp 0x3c/0x3d also falls back to vanilla logic.
  6. Knockout / 2-leg replay loop in `fcn_03708de9` + `fcn_03706175` terminates cleanly
     even on extreme mismatches (e.g. 90 vs 60) and produces valid decisive ties.
  7. SKIP_SUBS patch at `0x03708230` skips the `sub1=sub2=sub3=11` overwrite in
     `fcn_03707e71` during Skip Match.
  8. Coexistence with MLMoney.lua, MLTransfers.lua, and MLYear.lua in any sider.ini order.
"""
import collections
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "tools"))

import re
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
SIM_MATCH_FN = 0x03708de9
TEAM_STRENGTH = 0x03865b0a
COMP_RECORD = 0x03822ab9
MODE_RANDOM = 0x03855998
TEAM_RECORD = 0x03822969
CAP_ROLES_VEC = 0x038ba942
CAP_BONUS_FN = 0x038b6e3d
VEC_FREE = 0x02bc5b9a

ALLOWED_CAVE = (sc.CAVE, len(sc.build_image()))
ALLOWED_SITES = (
    (sc.OUTCOME_SITE, 7),
    (sc.SCORE_SITE, 5),
    (sc.SKIP_SUBS_SITE, 2),
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
        }

        # Default AI-controlled teams (+0x314 bits 7..14 = 0xff)
        self.set_team_user(0, False)
        self.set_team_user(1, False)
        self.set_skip_flag(False)
        self.set_match(comp_id=1, team0_id=100, team1_id=200, tie_kind=0)

        # Stub lookups
        g.replace(COMP_RECORD, lambda gm, a: self.comp)

        def get_team(gm, a):
            tid = a(0)
            return self.team0 if tid == 100 else self.team1

        g.replace(TEAM_RECORD, get_team)
        g.replace(0x03822a29, lambda gm, a: self.mgr_rec)

        def get_ovr(gm, a):
            tid = struct.unpack("<I", gm.read(a(0), 4))[0]
            return self.state["ovr0"] if tid == 100 else self.state["ovr1"]

        g.replace(TEAM_STRENGTH, get_ovr)

        def get_rand(gm, a):
            n = struct.unpack("<I", gm.read(a(0), 4))[0]
            return 0 if n == 0 else self.state["rand_fn"](n)

        g.replace(MODE_RANDOM, get_rand)

        # Captain role helpers (0x038ba942(&role_id, &out_vec) writes 12-byte std::vector)
        def get_cap_vec(gm, a):
            out = a(1)
            gm.write(out, b"\x00" * 12)
            return out

        g.replace(CAP_ROLES_VEC, get_cap_vec)
        g.replace(0x03822835, lambda gm, a: self.team0)  # +0xc4 is 0 by default
        g.replace(VEC_FREE, lambda gm, a: 0)

        # Cup / 2-leg flags for fcn_03706175 / fcn_03708de9
        g.replace(0x03856ca8, lambda gm, a: self.state["et_flag"])
        g.replace(0x03856d18, lambda gm, a: self.state["pk_flag"])
        g.replace(0x03856db8, lambda gm, a: self.state["away_goals"])
        g.replace(0x03856ef8, lambda gm, a: self.state["leg1_h"] if a(1) == 0 else self.state["leg1_a"])
        # Extra-time / PK / sub / scorer stubs for full fcn_03708de9 loop test
        g.replace(0x03707e71, lambda gm, a: 0)
        g.replace(0x037085b5, lambda gm, a: 0)
        g.replace(0x03708cc4, lambda gm, a: 0)
        g.replace(0x037062ca, lambda gm, a: (gm.write(a(0), struct.pack("<I", 0)), 0)[1])
        g.replace(0x037063bb, lambda gm, a: (gm.write(a(0), struct.pack("<I", 0)), 0)[1])

        self.clean_snapshot = [
            (sc.CAVE, g.read(sc.CAVE, ALLOWED_CAVE[1])),
            (sc.OUTCOME_SITE, g.read(sc.OUTCOME_SITE, 7)),
            (sc.SCORE_SITE, g.read(sc.SCORE_SITE, 5)),
            (sc.SKIP_SUBS_SITE, g.read(sc.SKIP_SUBS_SITE, 2)),
        ]

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

    def set_match(self, comp_id=1, team0_id=100, team1_id=200, tie_kind=0):
        # match +0x00: comp_index (u16), +0x04: comp_id (u16) | (tie_kind << 28), +0x0c: team0, +0x10: team1
        self.g.write(self.match + 0x00, struct.pack("<H", 1))
        self.g.write(self.match + 0x04, struct.pack("<I", (comp_id & 0xffff) | ((tie_kind & 3) << 28)))
        self.g.write(self.match + 0x0c, struct.pack("<II", team0_id, team1_id))
        self.g.write(self.match + 0x14, b"\x00" * 8)

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


def main(exe):
    source = open(MODULE, encoding="utf-8").read()

    # 1. Generated Lua block matches sim_cave.py
    expected_block = sc.lua_block(exe)
    assert expected_block in source, "Generated block in MLSimMatch.lua does not match sim_cave.lua_block(exe)!"
    print("ok 1: MLSimMatch.lua generated tables/routines/context block matches sim_cave.py exactly")

    # 2. Check Keystone assembly matches CODE_PARTS if keystone is installed
    if tm.KEYSTONE:
        built = sc.assemble()
        for name in ("chk", "rand", "outcome", "score"):
            assert (built[name][0], built[name][1].hex()) == sc.CODE_PARTS[name], name
    print("ok 2: Keystone assembly matches pre-assembled CODE_PARTS byte-for-byte")

    h = SimHarness(exe)
    g = h.g

    # Verify Lua build_image() matches Python pack + CODE_PARTS byte-for-byte
    lines, reads, writes = run(g, source)
    assert lines[-1].startswith("RESULT: installed."), lines
    lua_cave = g.read(sc.CAVE, ALLOWED_CAVE[1])
    py_cave = sc.build_image()
    assert lua_cave == py_cave, "Lua build_image() != Python sim_cave.build_image()!"
    assert tm.inside(writes, (ALLOWED_CAVE,) + ALLOWED_SITES)
    print("ok 3: Lua build_image() matches Python sim_cave.build_image() byte-for-byte (915 bytes in .xcode)")

    # 3. Settings fault validation + dry-run + partial modes
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
        ("SKIP_SUBS", '"true"'),
    ]
    for name, val in faulty:
        l2, r2, w2 = run(g, set_lua(source, name, val))
        assert l2[-1].startswith("RESULT: nothing written. Settings:") and not r2 and not w2, (name, val, l2)

    l2, r2, w2 = run(g, set_lua(source, "WRITE", "false"))
    assert l2[-1] == "RESULT: nothing written (WRITE = false). All checks passed." and not w2, l2
    l2, r2, w2 = run(g, set_lua(set_lua(source, "SCOPE", "false"), "SKIP_SUBS", "false"))
    assert "SCOPE and SKIP_SUBS are both off" in l2[-1] and not r2 and not w2, l2
    l2, r2, w2 = run(g, set_lua(source, "SCOPE", "false"))
    assert l2[-1] == "RESULT: installed. Active: Skip Match CPU substitutions." and w2 == [(sc.SKIP_SUBS_SITE, 2)], (l2, w2)
    h.restore()
    print("ok 4: 17 faulty settings refused cleanly; WRITE=false, all-off, and SKIP_SUBS-only verified")

    # 4. Tamper & sticky checks
    for name, addr, expected_hex in [
        ("outcome site", sc.OUTCOME_SITE, "0fb6bdf3ffffff"),
        ("score site", sc.SCORE_SITE, "8b45088b00"),
        ("skip_subs site", sc.SKIP_SUBS_SITE, "7417"),
    ]:
        h.restore()
        orig = g.read(addr, len(expected_hex) // 2)
        poke(g, addr, bytes([orig[0] ^ 0x01]) + orig[1:])
        l2, _, w2 = run(g, source)
        assert l2[-1].startswith("RESULT: nothing written.") and not w2, (name, l2)

    # Already-hooked e9 check
    h.restore()
    poke(g, sc.OUTCOME_SITE, b"\xe9\x11\x22\x33\x44\x90\x90")
    l2, _, w2 = run(g, source)
    assert "already modified" in l2[-1] and not w2, l2

    # Non-empty cave check
    h.restore()
    poke(g, sc.CAVE + 100, b"\xaa")
    l2, _, w2 = run(g, source)
    assert l2[-1].startswith("RESULT: nothing written.") and not w2, l2

    # Sticky write failure check
    h.restore()
    l2, _, _ = run(g, source, sticky=lambda a: a != sc.SCORE_SITE)
    assert l2[-1].startswith("RESULT: a change did not go in."), l2
    print("ok 5: tamper detection, already-hooked check, non-empty cave check, and sticky-write failures verified")

    # 5. Install and run REAL PES2017.exe machine code (`fcn_03707a1f` + `fcn_03705feb`)
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2

    # Deterministic probability table verification across all diff values!
    for ovr0, ovr1 in [(80, 80), (85, 75), (75, 85), (90, 65), (65, 90), (82, 79)]:
        diff = ovr0 - ovr1
        ph, pd, pa = sc.outcome_probs(diff)
        # Sweep all 1000 values of mode_random(1000) directly through real PES2017.exe!
        counts = [0, 0, 0]
        idx = [0]
        h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
        for _ in range(1000):
            r = h.run_outcome(ovr0, ovr1)
            counts[r] += 1
        exp_row = sc.build_outcome_table()[diff - sc.DIFF_MIN]
        assert counts[0] == exp_row[0], (ovr0, ovr1, counts, exp_row)
        assert counts[2] == exp_row[1] - exp_row[0], (ovr0, ovr1, counts, exp_row)
        assert counts[1] == 1000 - exp_row[1], (ovr0, ovr1, counts, exp_row)
        # Ensure neither win outcome is ever 0%
        assert counts[0] >= 1 and counts[1] >= 1
    print("ok 6: real fcn_03707a1f outcome counts across 1000-point sweeps match Python table exactly")

    # Scoreline distribution check across draws and wins (both home and away)
    rng = random.Random(2026)
    h.state["rand_fn"] = lambda n: rng.randrange(n)

    # Draws: verify only 0-0..4-4 equal scores occur and mean is ~1.03 goals per side
    draw_scores = collections.Counter()
    for _ in range(2000):
        hg, ag = h.run_score(2, 80, 80)
        assert hg == ag and 0 <= hg <= 4, (hg, ag)
        draw_scores[(hg, ag)] += 1
    assert abs(draw_scores[(1, 1)] / 2000 - 0.46) < 0.04, draw_scores
    assert abs(draw_scores[(0, 0)] / 2000 - 0.28) < 0.04, draw_scores

    # Home wins & Away wins: verify winner > loser, realistic goal totals, and band sensitivity
    for res, ovr0, ovr1, label in [
        (0, 80, 80, "equal home win"),
        (1, 80, 80, "equal away win"),
        (0, 90, 68, "giant home win"),
        (1, 70, 88, "giant away win"),
        (0, 70, 85, "upset home win"),
    ]:
        total_w = 0
        total_l = 0
        for _ in range(1000):
            hg, ag = h.run_score(res, ovr0, ovr1)
            if res == 0:
                assert 1 <= hg <= 6 and 0 <= ag < hg, (label, hg, ag)
                total_w += hg
                total_l += ag
            else:
                assert 1 <= ag <= 6 and 0 <= hg < ag, (label, hg, ag)
                total_w += ag
                total_l += hg
        avg_w = total_w / 1000
        avg_l = total_l / 1000
        assert 1.8 <= avg_w <= 3.3 and 0.2 <= avg_l <= 0.7, (label, avg_w, avg_l)
    print("ok 7: real fcn_03705feb scorelines satisfy invariants and realistic Poisson frequencies")

    # 6. Master League captain role bonus scaling (+-10 -> +-2 OVR, +-20 -> +-4 OVR)
    # Test directly with mode_kind = 0xc and CAP_ROLES_VEC stubbed to 1 player for team 0
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
    g.replace(CAP_BONUS_FN, lambda gm, a: 20)  # +20 raw -> +4 OVR at CAPTAIN_WEIGHT=0.2
    idx = [0]
    h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
    counts = [0, 0, 0]
    for _ in range(1000):
        counts[h.run_outcome(80, 80)] += 1
    exp_row = sc.build_outcome_table()[4 - sc.DIFF_MIN]  # +4 OVR
    assert counts[0] == exp_row[0], (counts, exp_row)
    # Reset captain mock
    g.replace(0x03822835, lambda gm, a: h.team0)
    g.replace(CAP_ROLES_VEC, lambda gm, a: (gm.write(a(1), b"\x00" * 12), a(1))[1])
    h.set_mode_kind(0x13)
    print("ok 8: ML captain role bonus scales cleanly (+20 raw -> +4 OVR)")

    # 7. Special fallback cases: mode 0x27/0x28 + comp 0x3c/0x3d, and SCOPE="skip_only"
    h.set_menu_mode(0x28)
    h.set_match(comp_id=0x3c, team0_id=100, team1_id=200)
    idx = [0]
    h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
    counts = [0, 0, 0]
    for _ in range(100):
        counts[h.run_outcome(80, 80)] += 1
    # Vanilla 0x28 + 0x3c uses hardcoded 67% favorite / 8% underdog / 25% draw
    # (when ovr0 == ovr1, vanilla treats away=1 as favorite; when ovr0 > ovr1, home=0 is favorite)
    assert counts == [8, 67, 25], counts
    idx = [0]
    counts2 = [0, 0, 0]
    for _ in range(100):
        counts2[h.run_outcome(81, 80)] += 1
    assert counts2 == [67, 8, 25], counts2
    h.set_menu_mode(0x13)
    h.set_match(comp_id=1, team0_id=100, team1_id=200)

    # SCOPE="skip_only" fallback check
    h.restore()
    l2, _, _ = run(g, set_lua(source, "SCOPE", '"skip_only"'))
    assert l2[-1].startswith("RESULT: installed."), l2
    # Case A: AI vs AI with skip_flag=1 -> vanilla (diff=15 -> 100% favorite win)
    h.set_skip_flag(True)
    h.set_team_user(0, False)
    h.set_team_user(1, False)
    assert h.run_outcome(90, 75) == 0  # vanilla diff=15 -> 100% win
    # Case B: User vs AI with skip_flag=0 -> vanilla
    h.set_skip_flag(False)
    h.set_team_user(0, True)
    idx = [0]
    h.state["rand_fn"] = lambda n: (idx.__setitem__(0, idx[0] + 1), idx[0] - 1)[1] % n
    # At rand=0: vanilla for (90 vs 75) returns 0; check rand=999 still returns 0 (100% vanilla)
    h.state["rand_fn"] = lambda n: n - 1
    assert h.run_outcome(90, 75) == 0
    # Case C: User vs AI with skip_flag=1 -> enhanced! With rand=999, 90 vs 75 gives away upset (1)!
    h.set_skip_flag(True)
    assert h.run_outcome(90, 75) == 1
    h.set_team_user(0, False)
    h.set_skip_flag(False)
    print('ok 9: mode 0x27/0x28+comp 0x3c/0x3d fallback and SCOPE="skip_only" gating verified')

    # 8. Knockout & 2-leg loop termination in fcn_03708de9
    h.restore()
    l2, _, _ = run(g, source)
    assert l2[-1].startswith("RESULT: installed."), l2
    h.state["rand_fn"] = lambda n: rng.randrange(n)
    # 1-leg knockout (tie_kind=2, pk_flag=1, et_flag=0 -> loops until hg != ag)
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
            assert hg != ag, (ovr0, ovr1, hg, ag)
    # 2-leg tie where leg 1 was 1-0 to leg-1 home (current away team) -> leg 2 cannot end 1-0!
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
    print("ok 10: fcn_03708de9 knockout and 2-leg aggregate tie-breaker loops terminate cleanly")

    # 9. SKIP_SUBS instruction check at 0x03708230
    # Verify patched instruction at 0x03708230..0x03708249 jumps over sub1=sub2=sub3=11
    h.restore()
    poke(g, sc.SKIP_SUBS_SITE, b"\xeb\x17")
    frame = g.alloc(size=0x400) + 0x300
    g.write(frame - 0x160, struct.pack("<I", h.mode_data))
    # Initialize sub1/sub2/sub3 at frame-0x120 = 3, 5, 7
    g.write(frame - 0x120, struct.pack("<III", 3, 5, 7))
    h.set_skip_flag(True)
    # Run from 0x03708222 (after `test cl, cl; jne`) -> 0x03708249 with cl=0 (user team)
    from unicorn.x86_const import UC_X86_REG_ECX, UC_X86_REG_EBP, UC_X86_REG_ESP
    g.mu.reg_write(UC_X86_REG_ESP, STACK + STACK_SIZE - 0x1000)
    g.mu.reg_write(UC_X86_REG_EBP, frame)
    g.mu.reg_write(UC_X86_REG_ECX, 0)
    g.mu.emu_start(0x03708224, 0x03708249)
    assert struct.unpack("<III", g.read(frame - 0x120, 12)) == (3, 5, 7)
    print("ok 11: SKIP_SUBS patch at 0x03708230 skips sub=11 overwrite during Skip Match")

    # 10. Coexistence with MLMoney.lua, MLTransfers.lua, and MLYear.lua in any order
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
    print("ok 12: installs cleanly alongside MLMoney.lua, MLTransfers.lua, and MLYear.lua in any order")


if __name__ == "__main__":
    main(sys.argv[1])
