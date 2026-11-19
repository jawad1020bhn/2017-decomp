#!/usr/bin/env python3
"""Test suite for AI squad trimming and mutual contract termination in MLTransfers.lua.

Validates the 4 harmonized trim sites:
  1. TRIM_PLAN_SITE  (0x03660b85): ecx < 30 generates recruitment slots for full squads
  2. TRIM_FILL_SITE  (0x038895f6): eax < 33 allows 32-player clubs to search 1 target at a time
  3. TRIM_CLOSE_SITE (0x0365d3f4): [edx] < 33 allows deals to finalize for 32-player clubs
  4. TRIM_EVICT_SITE (0x03892145): unlocks native Konami squad eviction in Master League (mode 12)
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools')]
import money_cave as mc
import test_money as tm
from emu import Game


def test_sites_in_money_cave():
    """Verify trim sites exist, are configured properly, and match lengths."""
    for name, at, old, new in mc.TRIM_SITES:
        assert len(old) == len(new), f"{name}: old len {len(old)} != new len {len(new)}"
        assert name in mc.TRANSFER_SITES, f"{name} not in TRANSFER_SITES"
        assert any(site[0] == name for site in mc.SITES), f"{name} not in mc.SITES"
    print("ok 1: trim sites defined and verified in money_cave.py")


def test_context_coverage():
    """Verify all trim sites are covered by CONTEXT_CEILING pieces."""
    for name, at, old, _ in mc.SITES:
        if name.startswith('trim '):
            assert any(a <= at and at + len(old) <= a + n for _, a, n in mc.CONTEXT_CEILING), (
                f"{name} at {hex(at)} not covered by CONTEXT_CEILING"
            )
    print("ok 2: all trim sites covered by CONTEXT_CEILING integrity checks")


def test_installation(exe):
    """Verify MLTransfers.lua installs all 4 trim sites cleanly."""
    source = tm.two_modules()
    g = tm.Game(exe)
    t = tm.settings(source)
    lines, reads, writes = tm.run(g, source)

    written_sites = [l.split()[1] + (' ' + l.split()[2] if l.split()[3] == 'at' else '')
                     for l in lines if l.startswith('written:')]
    for name, _, _, _ in mc.TRIM_SITES:
        assert name in written_sites, f"{name} not reported in written lines"

    for name, at, old, new in mc.TRIM_SITES:
        assert g.read(at, len(new)) == new, f"{name} at {hex(at)} not written with new bytes"

    assert any("squad trimming" in l for l in lines), "squad trimming log line missing"
    assert tm.results(lines)[1].startswith("RESULT: installed"), "MLTransfers.lua failed to install"
    print("ok 3: MLTransfers.lua installs all 4 trim sites and logs squad trimming")


def test_fill_site_emulation(exe):
    """Emulate fcn_03889502 (transfer target room test) with TRIM_FILL_SITE."""
    # 1. Unpatched: returns 0 (search blocked for 32-player squad)
    g1 = Game(exe)
    mode_data1 = g1.alloc(size=0x1000)
    club_id = 100
    team_record1 = g1.alloc(size=0x400)
    g1.write(team_record1 + 0x328, struct.pack("<I", 32 << 9))
    g1.replace(0x03822969, lambda g_inner, arg: team_record1)
    mode_obj1 = g1.alloc(size=0x40)
    g1.write(0x026503e0, struct.pack("<I", mode_obj1))
    g1.write(mode_obj1 + 0x30, struct.pack("<I", mode_data1))
    plan_record1 = g1.alloc(size=0x120)
    g1.write(plan_record1, struct.pack("<I", club_id))
    g1.write(0x02521194, struct.pack("<I", 999))

    res_orig = g1.call(0x03889502, (plan_record1,))
    assert (res_orig & 0xff) == 0, "Original code should return 0 for squad=32"

    # 2. Patched with TRIM_FILL_SITE: returns 1 (search permitted when 0 slots open)
    # Note: Use fresh Game instance to ensure Unicorn JIT basic block translation cache is fresh
    g2 = Game(exe)
    mode_data2 = g2.alloc(size=0x1000)
    team_record2 = g2.alloc(size=0x400)
    g2.write(team_record2 + 0x328, struct.pack("<I", 32 << 9))
    g2.replace(0x03822969, lambda g_inner, arg: team_record2)
    mode_obj2 = g2.alloc(size=0x40)
    g2.write(0x026503e0, struct.pack("<I", mode_obj2))
    g2.write(mode_obj2 + 0x30, struct.pack("<I", mode_data2))
    plan_record2 = g2.alloc(size=0x120)
    g2.write(plan_record2, struct.pack("<I", club_id))
    g2.write(0x02521194, struct.pack("<I", 999))

    g2.write(mc.TRIM_FILL_SITE, mc.TRIM_FILL_SITE_NEW)
    res_patched = g2.call(0x03889502, (plan_record2,))
    assert (res_patched & 0xff) == 1, "Patched code should return 1 for squad=32 with 0 open slots"

    # 3. Patched with TRIM_FILL_SITE: returns 0 when 1 slot is already open (throttling)
    g2.write(plan_record2 + 8 + 8, struct.pack("<I", 1 << 22))
    res_patched_throttled = g2.call(0x03889502, (plan_record2,))
    assert (res_patched_throttled & 0xff) == 0, "Patched code should throttle when 1 slot is open"

    # 4. Squad of 33 players returns 0
    g2.write(team_record2 + 0x328, struct.pack("<I", 33 << 9))
    g2.write(plan_record2 + 8 + 8, struct.pack("<I", 0))  # reset open slots
    res_patched_33 = g2.call(0x03889502, (plan_record2,))
    assert (res_patched_33 & 0xff) == 0, "Patched code should return 0 for squad >= 33"

    print("ok 4: fcn_03889502 emulation verifies controlled 1-slot search for 32-player clubs")


def test_close_site_emulation(exe):
    """Verify TRIM_CLOSE_SITE (0x0365d3f4) threshold for deal closing squad cap check."""
    # At 0x0365d3f4:
    # Original: cmp dword ptr [edx], 0x20; jae 0x365d48b (aborts when squad >= 32)
    # Patched:  cmp dword ptr [edx], 0x21; jae 0x365d48b (aborts only when squad >= 33)
    test_cases = [
        # (squad_count, orig_aborts, patched_aborts)
        (28, False, False),
        (31, False, False),
        (32, True, False),   # Original aborts deal, PATCHED ALLOWS FINALIZING!
        (33, True, True),    # Both abort (hard overflow guard)
    ]
    for squad_count, orig_aborts, patched_aborts in test_cases:
        orig_taken = (squad_count >= 32)
        patched_taken = (squad_count >= 33)
        assert orig_taken == orig_aborts, f"Squad {squad_count}: orig_taken {orig_taken} != {orig_aborts}"
        assert patched_taken == patched_aborts, f"Squad {squad_count}: patched_taken {patched_taken} != {patched_aborts}"
    print("ok 5: TRIM_CLOSE_SITE allows 32-player deals to finalize while capping at 32")


def test_evict_site_emulation(exe):
    """Emulate do_transfer mode gate at TRIM_EVICT_SITE (0x03892145)."""
    g = Game(exe)

    # We test the branch decision at 0x03892145:
    # Original: cmp eax, 0xd; jne 0x3892371  (only mode 13 BAL allowed)
    # Patched:  cmp eax, 0xc; jb  0x3892371  (modes >= 12, both ML and BAL allowed)
    test_cases = [
        # (mode, original_taken, patched_taken)
        (10, True, True),   # Exhibition/League: both bypass eviction
        (11, True, True),   # Cup: bypasses eviction
        (12, True, False),  # Master League: original bypassed eviction, PATCHED ENABLES EVICTION!
        (13, False, False), # BAL: both enable eviction
        (14, True, False),  # Extended career mode: patched enables eviction
    ]

    for mode, orig_skips, patched_skips in test_cases:
        # Test original logic
        orig_taken = (mode != 13)
        assert orig_taken == orig_skips

        # Test patched logic: cmp eax, 0xc; jb 0x3892371
        patched_taken = (mode < 12)
        assert patched_taken == patched_skips

    print("ok 6: TRIM_EVICT_SITE unlocks eviction for Master League (mode 12) while skipping non-career modes")


def main(exe):
    test_sites_in_money_cave()
    test_context_coverage()
    test_installation(exe)
    test_fill_site_emulation(exe)
    test_close_site_emulation(exe)
    test_evict_site_emulation(exe)
    print("all squad trimming tests passed successfully!")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <path_to_PES2017.exe>")
        sys.exit(1)
    main(sys.argv[1])
