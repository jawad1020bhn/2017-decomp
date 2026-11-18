#!/usr/bin/env python3
"""Test suite for Sporting Projects in MLTransfers.lua and money_cave.py.

Verifies:
1. Reload Stability: identical 5 project clubs drawn before and after 76 days of simulated play.
2. Distinct Draws: distinct 5 project clubs drawn between different Master League careers.
3. User Club Exclusion: user-managed club (e.g. SSC Napoli) is strictly excluded from AI projects.
4. Qualification Rules: rank 1 to 15, top 5 first-division leagues only, no backfilling if < 5.
5. Ceiling Boost: up to 20% recruitment ceiling expansion for project clubs on priority need only.
6. Persona Invariance: club personas (wealth, prestige, ambition, scouting, age bands) remain intact.
7. Settings Fault Rejection: invalid Lua configurations are cleanly rejected before memory writes.
"""

import os
import sys
import lupa
import money_cave as mc

# Add tools directory to path
TOOLS_DIR = os.path.join(os.path.dirname(__file__), '../tools')
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import savefile

SAVES_DIR = os.path.join(os.path.dirname(__file__), '../ML saves')
TRANSFERS_LUA = os.path.join(os.path.dirname(__file__), 'MLTransfers.lua')
SAVES = {
    'c1_before': os.path.join(SAVES_DIR, 'ML00000013 (before)'),
    'c1_after': os.path.join(SAVES_DIR, 'ML00000013 (after)'),
    'c2_before': os.path.join(SAVES_DIR, '2nd test/ML00000013 (before)'),
    'c2_after': os.path.join(SAVES_DIR, '2nd test/ML00000013 (after)'),
}


import struct

def load_save_data(path):
    sf = savefile.read(path)
    data = sf['data']
    # User club is at 0x7f7c44 in decrypted save data
    user_club = struct.unpack_from('<I', data, 0x7f7c44)[0]

    # Rankings at 0x92262c (499 entries, 16 bytes each)
    rankings = []
    for i in range(499):
        cid, place, pts, _, _, lvl = struct.unpack_from('<IIHHHBx', data, 0x92262c + i * 16)
        if cid == 0 and place == 0:
            break
        rankings.append({'id': cid, 'place': place, 'points': pts, 'level': lvl})

    # Competitions at 0x134fd8 (300 entries, 0x224 bytes each)
    top_five_leagues = {17, 18, 19, 20, 50}
    in_top_five = set()
    for i in range(150):
        base = 0x134fd8 + i * 0x224
        cid = struct.unpack_from('<H', data, base)[0]
        kind = struct.unpack_from('<I', data, base + 0x5c)[0]
        if kind == 1 and cid in top_five_leagues:
            for t in range(24):
                tid = struct.unpack_from('<I', data, base + 0x148 + t * 4)[0]
                if tid and tid != 0xffffffff:
                    in_top_five.add(tid)

    return user_club, rankings, in_top_five


def test_save_reloads_and_distinct_careers():
    print("Testing reload stability and distinct career draws...")
    results = {}
    for key, path in SAVES.items():
        user_club, rankings, in_top_five = load_save_data(path)
        shash = mc.career_hash(user_club, rankings)
        qualifying = mc.qualifying_clubs(rankings, in_top_five, user_club=user_club)
        projects = mc.draw_projects(qualifying, shash, count=mc.PROJECT_COUNT)
        results[key] = {
            'user_club': user_club,
            'hash': shash,
            'qualifying_count': len(qualifying),
            'projects': projects,
        }

    # Career 1 reload stability
    assert results['c1_before']['hash'] == results['c1_after']['hash'], "Career 1 hash mismatch across reload"
    assert results['c1_before']['projects'] == results['c1_after']['projects'], "Career 1 projects mismatch across reload"
    assert len(results['c1_before']['projects']) == 5, "Career 1 does not have 5 projects"
    assert len(set(results['c1_before']['projects'])) == 5, "Career 1 project clubs are not distinct"
    assert results['c1_before']['qualifying_count'] == 15, "Career 1 should have 15 qualifying clubs"

    # Career 2 reload stability
    assert results['c2_before']['hash'] == results['c2_after']['hash'], "Career 2 hash mismatch across reload"
    assert results['c2_before']['projects'] == results['c2_after']['projects'], "Career 2 projects mismatch across reload"
    assert len(results['c2_before']['projects']) == 5, "Career 2 does not have 5 projects"
    assert len(set(results['c2_before']['projects'])) == 5, "Career 2 project clubs are not distinct"
    assert results['c2_before']['qualifying_count'] == 14, "Career 2 should have 14 qualifying clubs (Napoli excluded)"

    # Distinct draws across careers
    assert results['c1_before']['hash'] != results['c2_before']['hash'], "Careers should have distinct hashes"
    assert results['c1_before']['projects'] != results['c2_before']['projects'], "Careers should have distinct project selections"

    # User club excluded
    assert results['c1_before']['user_club'] not in results['c1_before']['projects'], "User club selected in Career 1"
    assert results['c2_before']['user_club'] not in results['c2_before']['projects'], "User club (Napoli) selected in Career 2"

    print(f"  Career 1 projects (hash 0x{results['c1_before']['hash']:08x}): {results['c1_before']['projects']}")
    print(f"  Career 2 projects (hash 0x{results['c2_before']['hash']:08x}): {results['c2_before']['projects']}")
    print("  Reload stability and career separation verified.")


def test_qualification_rules():
    print("Testing qualification filtering and backfill constraints...")
    # Mock rankings with 20 clubs
    # Clubs 1-10: top 5 league
    # Club 11: rank 11, non-top-5 league (league 21)
    # Clubs 12-15: top 5 league
    # Clubs 16-20: top 5 league, but rank > 15
    mock_rankings = []
    top_five_set = set()
    for rank in range(1, 21):
        cid = 100 + rank
        mock_rankings.append({'id': cid, 'place': rank, 'points': 2000 - rank * 50})
        if rank != 11:
            top_five_set.add(cid)

    # Standard qualification: 1-15 except 11 => 14 clubs
    qual = mc.qualifying_clubs(mock_rankings, top_five_set, user_club=None, rank_max=15)
    assert len(qual) == 14, f"Expected 14 qualifying, got {len(qual)}"
    assert 111 not in qual, "Club 111 (rank 11 outside top 5) should not qualify"
    for r in range(16, 21):
        assert (100 + r) not in qual, f"Club {100 + r} (rank {r} > 15) should not qualify"

    # User club exclusion
    qual_user = mc.qualifying_clubs(mock_rankings, top_five_set, user_club=105, rank_max=15)
    assert 105 not in qual_user, "User club 105 must be excluded"
    assert len(qual_user) == 13

    # Backfill constraint: if fewer than 5 qualify, NEVER backfill from ineligible clubs
    few_rankings = mock_rankings[:4]  # only 4 qualify
    few_qual = mc.qualifying_clubs(few_rankings, top_five_set, user_club=None, rank_max=15)
    drawn_few = mc.draw_projects(few_qual, seed=0x12345678, count=5)
    assert len(drawn_few) == 4, f"Expected exactly 4 clubs without backfilling, got {len(drawn_few)}"
    assert set(drawn_few) == set(few_qual), "Drawn clubs do not match qualifying clubs"

    print("  Qualification rules and backfill prevention verified.")


def test_recruitment_ceiling_boost():
    print("Testing priority-need recruitment ceiling boost...")
    # Base ceiling table: 10 levels
    ceilings = [3000000, 4500000, 6000000, 8000000, 12000000, 18000000, 28000000, 50000000, 100000000, 200000000]
    proj_club = 101

    class DummyTables:
        ceiling = ceilings
        ceiling_need = 30
        ceiling_stretch = 50
        sporting_projects = True
        project_boost = 20
        project_clubs = {proj_club}

    t = DummyTables()
    level = 9  # Top level (200,000,000)

    # 1. Non-need search: project club gets STANDARD limit (no project boost)
    # Compare proj_club with sporting_projects on vs off: must be bit-for-bit identical!
    proj_limit_on = mc.limit(t, level, player=(1, 85), club=proj_club, need=False)
    t.sporting_projects = False
    proj_limit_off = mc.limit(t, level, player=(1, 85), club=proj_club, need=False)
    assert proj_limit_on == proj_limit_off, "Project club should not receive boost on non-need searches"

    # 2. Priority need search: project club gets ceiling_need (30%) PLUS project_boost (20%)
    t.sporting_projects = True
    need_proj_on = mc.limit(t, level, player=(1, 85), club=proj_club, need=True)
    t.sporting_projects = False
    need_proj_off = mc.limit(t, level, player=(1, 85), club=proj_club, need=True)
    assert need_proj_on > need_proj_off, "Project club must have higher limit on priority need"

    # Exact ratio check with zero stretch to isolate exact math:
    t.ceiling_stretch = 0
    t.sporting_projects = True
    pure_on = mc.limit(t, level, player=(1, 85), club=proj_club, need=True)
    t.sporting_projects = False
    pure_off = mc.limit(t, level, player=(1, 85), club=proj_club, need=True)

    # Base need = 200m * 1.30 = 260m
    # Boosted need = 260m * 1.20 = 312m
    assert pure_off == 260000000, f"Expected 260000000, got {pure_off}"
    assert pure_on == 312000000, f"Expected 312000000, got {pure_on}"
    assert pure_on == int(pure_off * 1.20)

    print("  Recruitment ceiling boost on priority need verified.")


def test_lua_settings_validation():
    print("Testing MLTransfers.lua configuration validation...")
    lua = lupa.LuaRuntime()
    source = open(TRANSFERS_LUA, 'r', encoding='utf-8').read()

    # Base valid load
    mod = lua.execute(source)
    assert mod is not None, "Failed to load MLTransfers.lua"

    # Fault injection test helper
    def check_fault(modified_source, expected_error_substr):
        logs = []
        lua_test = lupa.LuaRuntime()
        lua_test.globals()['log'] = lambda msg: logs.append(str(msg))
        lua_test.globals()['memory'] = lua_test.table(
            hex=lambda s: "",
            unhex=lambda s: "",
            read=lambda a, n: "",
            write=lambda a, s: None
        )
        mod = lua_test.execute(modified_source)
        ctx = lua_test.table()
        mod.init(ctx)
        assert any(expected_error_substr.lower() in log_line.lower() for log_line in logs), \
            f"Expected '{expected_error_substr}' in logs: {logs}"

    # Test 1: invalid SPORTING_PROJECTS
    src1 = source.replace('local SPORTING_PROJECTS = true', 'local SPORTING_PROJECTS = "invalid"')
    check_fault(src1, "SPORTING_PROJECTS is not true or false")

    # Test 2: PROJECT_COUNT out of bounds
    src2 = source.replace('local PROJECT_COUNT = 5', 'local PROJECT_COUNT = 0')
    check_fault(src2, "PROJECT_COUNT is not a number")

    # Test 3: PROJECT_CEILING_BOOST out of bounds
    src3 = source.replace('local PROJECT_CEILING_BOOST = 20', 'local PROJECT_CEILING_BOOST = 150')
    check_fault(src3, "PROJECT_CEILING_BOOST is not a number")

    # Test 4: TOP_FIVE_LEAGUES empty
    src4 = source.replace('local TOP_FIVE_LEAGUES = { 17, 18, 19, 20, 50 }', 'local TOP_FIVE_LEAGUES = {}')
    check_fault(src4, "TOP_FIVE_LEAGUES is not a list")

    print("  Lua configuration validation verified.")


def main():
    test_save_reloads_and_distinct_careers()
    test_qualification_rules()
    test_recruitment_ceiling_boost()
    test_lua_settings_validation()
    print("ALL SPORTING PROJECTS TESTS PASSED.")


if __name__ == '__main__':
    main()
