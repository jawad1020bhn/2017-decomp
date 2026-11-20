"""Patches PES2017.exe to enable the native in-game 36-team UEFA Swiss Format UI.

Integrates the UEFA 36-team Swiss format directly into PES 2017's native UI:
1. UCL Layout Router (0x03120b2d): changes jump table selector from 0x00 (groups)
   to 0x07 (Case 7: unified scrollable league table view).
2. Standings Stats Unpacker (0x0323a3af): raises team clamp from 0x20 (32) to 0x40 (64)
   in fcn_0323a336 so points, wins, draws, losses, GF, GA, GD are unpacked for all 36 teams.
3. Standings Row Generator (0x0323abc3): raises loop clamp from 0x20 (32) to 0x40 (64)
   in fcn_0323a885 so native UI choice rows are created with emblem/name for all 36 teams.
4. Rank Arrow Entry Selector (0x03239e9c): raises clamp from 0x20 to 0x40 in fcn_03239e2f.
5. Rank Arrow Prev Table Lookup (0x03239edd): raises clamp from 0x20 to 0x40 in fcn_03239e2f.
6. Rank Arrow Match Loop (0x03239f31): raises clamp from 0x20 to 0x40 in fcn_03239e2f.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import layout

EXE_PATH = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'PES2017.exe'))

# Patch definitions: (Virtual Address, Expected Old Bytes, New Bytes, Description)
PATCHES = [
    (0x03120b2d, b'\x00', b'\x07', "UCL Layout Router -> Case 7 (Unified League Table)"),
    (0x0323a3af, b'\x20', b'\x40', "fcn_0323a336 Stats Unpacker 32 -> 64 teams"),
    (0x0323abc3, b'\x20', b'\x40', "fcn_0323a885 Standings Choice Rows 32 -> 64 teams"),
    (0x03239e9c, b'\x20', b'\x40', "fcn_03239e2f Rank Arrow Current Entry 32 -> 64 teams"),
    (0x03239edd, b'\x20', b'\x40', "fcn_03239e2f Rank Arrow Previous Entry 32 -> 64 teams"),
    (0x03239f31, b'\x20', b'\x40', "fcn_03239e2f Rank Arrow Match Loop 32 -> 64 teams"),
]

def apply_patches(exe_path=EXE_PATH):
    if not os.path.exists(exe_path):
        raise FileNotFoundError(f"Executable not found: {exe_path}")

    with open(exe_path, 'rb') as f:
        data = bytearray(f.read())

    print(f"Loaded {exe_path} ({len(data):,} bytes)")
    applied = 0
    already_patched = 0

    for va, old_b, new_b, desc in PATCHES:
        fo = layout.off(va)
        if fo is None:
            raise ValueError(f"VA {hex(va)} could not be mapped to file offset")
        cur = bytes(data[fo:fo+len(new_b)])
        if cur == new_b:
            print(f"  [ALREADY PATCHED] VA {hex(va)} (file {hex(fo)}): {desc}")
            already_patched += 1
        elif cur == old_b:
            data[fo:fo+len(new_b)] = new_b
            print(f"  [PATCHED] VA {hex(va)} (file {hex(fo)}): {cur.hex()} -> {new_b.hex()} ({desc})")
            applied += 1
        else:
            raise RuntimeError(f"Unexpected bytes at VA {hex(va)} (file {hex(fo)}): expected {old_b.hex()}, found {cur.hex()}")

    if applied > 0:
        with open(exe_path, 'wb') as f:
            f.write(data)
        print(f"Successfully applied {applied} patch(es) to {exe_path}.")
    else:
        print(f"All {already_patched} patch(es) already in place.")

    return True

def verify_patches(exe_path=EXE_PATH):
    with open(exe_path, 'rb') as f:
        data = f.read()
    for va, old_b, new_b, desc in PATCHES:
        fo = layout.off(va)
        cur = data[fo:fo+len(new_b)]
        assert cur == new_b, f"Verification failed at VA {hex(va)}: expected {new_b.hex()}, found {cur.hex()}"
    return True

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else EXE_PATH
    apply_patches(target)
    verify_patches(target)
    print("PES 2017 executable verified: 36-team Swiss Format UI integration fully active!")
