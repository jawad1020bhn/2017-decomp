"""Test suite for MLSwiss.lua: UEFA 36-team Swiss Format League Phase & Knockout engine.
Tests fixture constraints, pot balance, country protection, standings tiebreakers,
progression logic, and Lua module execution via lupa.
"""
import os
import sys
from lupa.luajit21 import LuaRuntime

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.join(HERE, 'MLSwiss.lua')


def test_swiss_format():
    lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)

    lines = []
    def log(text):
        lines.append(text.decode() if isinstance(text, bytes) else str(text))

    memory_store = {}
    def mem_read(addr, size):
        buf = bytearray()
        for i in range(int(size)):
            buf.append(memory_store.get(int(addr) + i, 0))
        return bytes(buf)

    def mem_write(addr, data):
        for i, b in enumerate(data):
            memory_store[int(addr) + i] = b

    loader = lua.eval('''function(source, log, read, write)
        local env = { assert = assert, table = table, pairs = pairs, ipairs = ipairs, string = string,
                      math = math, tonumber = tonumber, tostring = tostring, unpack = unpack,
                      error = error, _VERSION = _VERSION, type = type, io = io,
                      os = { time = os.time, clock = os.clock, date = os.date },
                      log = log, memory = { read = read, write = write } }
        local f = loadstring(source)
        setfenv(f, env)
        return f()
    end''')

    source = open(MODULE, 'rb').read()
    mod = loader(source, log, mem_read, mem_write)

    ctx = lua.table_from({b'sider_dir': HERE.encode('utf-8') + b'/', b'register': lambda *a: None})
    mod.init(ctx)

    # 1. Verify 36 clubs and 4 pots
    teams = mod.get_teams()
    assert len(teams) == 36, f"Expected 36 clubs, got {len(teams)}"
    pots = {1: [], 2: [], 3: [], 4: []}
    for i in range(1, 37):
        t = teams[i]
        pots[t.pot].append(i)
    for p in range(1, 5):
        assert len(pots[p]) == 9, f"Pot {p} should have 9 clubs, got {len(pots[p])}"
    print("ok 1: 36 clubs loaded evenly into 4 seeding pots of 9 clubs each")

    # 2. Verify Swiss schedule constraints (8 rounds, 144 matches)
    schedule = mod.get_schedule()
    assert len(schedule) == 8, f"Expected 8 rounds, got {len(schedule)}"

    all_matches = []
    for r in range(1, 9):
        round_matches = schedule[r]
        assert len(round_matches) == 18, f"Round {r} must have 18 matches, got {len(round_matches)}"
        round_teams = set()
        for m_idx in range(1, 19):
            pair = round_matches[m_idx]
            h, a = pair[1], pair[2]
            round_teams.add(h)
            round_teams.add(a)
            all_matches.append((h, a))
        assert len(round_teams) == 36, f"Round {r} must involve all 36 teams"

    assert len(all_matches) == 144, f"Expected 144 total matches, got {len(all_matches)}"

    # Check 4H / 4A, 8 unique opponents, 1H/1A per pot, and country protection
    for t_idx in range(1, 37):
        home_matches = [m[1] for m in all_matches if m[0] == t_idx]
        away_matches = [m[0] for m in all_matches if m[1] == t_idx]
        assert len(home_matches) == 4, f"Team {t_idx} home matches != 4: {len(home_matches)}"
        assert len(away_matches) == 4, f"Team {t_idx} away matches != 4: {len(away_matches)}"
        opponents = set(home_matches + away_matches)
        assert len(opponents) == 8, f"Team {t_idx} unique opponents != 8: {len(opponents)}"

        # Check pot distribution
        for p in range(1, 5):
            pot_set = set(pots[p])
            p_home = [op for op in home_matches if op in pot_set]
            p_away = [op for op in away_matches if op in pot_set]
            assert len(p_home) == 1, f"Team {t_idx} must play 1 Home vs Pot {p}, got {p_home}"
            assert len(p_away) == 1, f"Team {t_idx} must play 1 Away vs Pot {p}, got {p_away}"

        # Country protection
        t_assoc = teams[t_idx].assoc
        for op in opponents:
            op_assoc = teams[op].assoc
            assert t_assoc != op_assoc, f"Country clash: Team {t_idx} ({t_assoc}) vs Team {op} ({op_assoc})"

    print("ok 2: 8-round fixture schedule satisfies exact 4H/4A, 1H/1A per pot, and UEFA country protection")

    # 3. Simulate rounds 1 through 8 and verify standings & progression
    for r in range(1, 9):
        mod.simulate_round(r)

    standings = mod.get_standings()
    assert len(standings) == 36, f"Expected 36 standings entries, got {len(standings)}"

    # Verify points ordering
    prev_pts = 999
    for rank in range(1, 37):
        s = standings[rank]
        assert s.p == 8, f"Club {s.name} played {s.p} matches instead of 8"
        assert s.w + s.d + s.l == 8, f"Record mismatch for {s.name}: {s.w}-{s.d}-{s.l}"
        assert s.pts == s.w * 3 + s.d, f"Points calculation mismatch for {s.name}"
        assert s.gd == s.gf - s.ga, f"Goal difference mismatch for {s.name}"
        assert s.pts <= prev_pts, f"Standings not sorted by points at rank {rank}"
        prev_pts = s.pts

    # Verify stage transition to PLAYOFFS
    assert mod.get_stage() in ("PLAYOFFS", b"PLAYOFFS"), f"Expected stage PLAYOFFS, got {mod.get_stage()}"

    # Verify prizes awarded (everyone has >= starting fee £15.70M)
    for rank in range(1, 37):
        s = standings[rank]
        assert s.prize > 15.70, f"Prize for {s.name} should exceed base fee: {s.prize}"
        if rank <= 8:
            # Top 8 receive R16 qualification prize (£9.3M)
            assert s.prize >= 15.70 + 9.30, f"Top 8 club {s.name} missing R16 bonus: {s.prize}"
        elif rank <= 24:
            # 9-24 receive play-off prize (£0.84M)
            assert s.prize >= 15.70 + 0.84, f"Play-off club {s.name} missing play-off bonus: {s.prize}"

    print("ok 3: full 8-matchday league phase simulated, standings sorted, top 8 direct R16 & 9-24 play-offs verified")

    # 4. Verify table output file generated
    mod.write_table(ctx)
    table_path = os.path.join(HERE, "MLSwiss_Table.txt")
    assert os.path.exists(table_path), f"Table file not found at {table_path}"
    content = open(table_path, "r").read()
    assert "UEFA CHAMPIONS LEAGUE - SWISS FORMAT STANDINGS" in content
    assert "TOP 8: DIRECT ROUND OF 16 QUALIFICATION" in content
    assert "9-24: KNOCKOUT PHASE PLAY-OFFS" in content
    assert "25-36: ELIMINATED FROM EUROPE" in content
    os.remove(table_path)
    print("ok 4: MLSwiss_Table.txt successfully generated with formatted standings and bracket preview")

    # 5. Verify ModeData competition and match schedule synchronization
    import struct
    MODE_OBJ = 0x20000000
    MODE_DATA = 0x30000000
    MENU_OBJ = 0x21000000
    mem_write(0x026503e0, struct.pack('<I', MODE_OBJ))
    mem_write(MODE_OBJ + 0x30, struct.pack('<I', MODE_DATA))
    mem_write(0x0264f3e8, struct.pack('<I', MENU_OBJ))
    mem_write(MENU_OBJ + 0x20, struct.pack('<I', 0x13))
    mem_write(MODE_DATA + 0x30, struct.pack('<I', 1))

    # Mock competition record 0 (ID 2 = UCL)
    mem_write(MODE_DATA + 0x5fece8, struct.pack('<I', 1))
    mem_write(MODE_DATA + 0x552e80, struct.pack('<H', 2))

    # Mock match record 0 (ID 2)
    mem_write(MODE_DATA + 0x8a9e40, struct.pack('<I', 1))
    mem_write(MODE_DATA + 0x6f154c + 0x04, struct.pack('<H', 2))

    assert mod.sync_mode_data(), "mod.sync_mode_data() failed"
    # Verify club written to competition record
    ucl_club_0 = struct.unpack('<I', mem_read(MODE_DATA + 0x552e80 + 0x148, 4))[0]
    assert ucl_club_0 == teams[1].id, f"Expected {hex(teams[1].id)}, got {hex(ucl_club_0)}"
    # Verify fixture written to match record
    match_home = struct.unpack('<I', mem_read(MODE_DATA + 0x6f154c + 0x0c, 4))[0]
    match_away = struct.unpack('<I', mem_read(MODE_DATA + 0x6f154c + 0x10, 4))[0]
    first_fixture = schedule[1][1]
    assert match_home == teams[first_fixture[1]].id, "Match home club mismatch"
    assert match_away == teams[first_fixture[2]].id, "Match away club mismatch"
    print("ok 5: Master League ModeData competition and match records synchronized with Swiss Format")


if __name__ == '__main__':
    test_swiss_format()
    print("ALL UEFA SWISS FORMAT TESTS PASSED SUCCESSFULLY!")
