#!/usr/bin/env python3
"""Checks the offers for the user's players (INCOMING) in the emulated game.

    python3 test_offer.py <PES2017.exe>          needs: pip install keystone unicorn

The bytes are the ones MLTransfers.lua ships (assembled by money_cave.py, and compared with
the text of the module), written into the free memory the module uses. Then the club
look-up fcn_0381e2eb, changed at its prologue, is run on a made-up mode data: a club table
of ten entries with their slots, one rival pair, and a chosen seller. Three cases:

  1. the slot the game would ask for holds a rival  -> the answer is the club of a
     neighbouring slot, and it is not a rival;
  2. the slot holds a club that is no rival         -> the game's answer stands, unchanged;
  3. every club is a rival                          -> the game's own answer stands, so no
     offer is lost by the change.

What this does not show: the club table of a real career (its count, and whether the slot
packed into `[club + 0x314] >> 7` is the one the game asks for), and that a career holds the
seller in `[0x0251f85c]` when the offer is made. Those are read from the disassembly.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools')]
import money_cave as mc                          # noqa: E402
from emu import Game                             # noqa: E402

SELLER = 0x00424039
CLUBS = [0x0019000d, 0x001b4036, 0x00194000, 0x001b002b, 0x002b400c,
         0x005f8007, 0x0061400f, 0x002c4008, 0x001a000a, 0x00308035]
GAME = 5


def module_text():
    """The two constants of MLTransfers.lua the bytes must agree with."""
    text = open(os.path.join(HERE, 'MLTransfers.lua')).read()
    start = text.index('local INCOMING_ROUTINE = ')
    routine = ''.join(re.findall(r'"([0-9a-f]+)"', text[start:text.index('local INCOMING_SITE', start)]))
    site = re.search(r'local INCOMING_SITE = \{ "incoming", (0x[0-9a-f]+), "([0-9a-f]+)", "([0-9a-f]+)" \}',
                     text)
    return routine, int(site.group(1), 16), site.group(2), site.group(3)


def install(g, code, pairs):
    g.write(mc.RIVAL_COUNT_AT, struct.pack('<I', len(pairs)))
    g.write(mc.RIVAL_PAIRS, b''.join(struct.pack('<II', a, b) for a, b in pairs))
    g.write(mc.INCOMING_CODE, code)
    assert g.read(mc.INCOMING_SITE, 6) == mc.INCOMING_SITE_OLD, g.read(mc.INCOMING_SITE, 6).hex()
    patched = b'\xe9' + struct.pack('<i', mc.INCOMING_CODE - (mc.INCOMING_SITE + 5)) + b'\x90'
    g.write(mc.INCOMING_SITE, patched)
    return patched


def run(exe, code, game_index, pairs):
    g = Game(exe)
    holder = g.alloc(size=0x40)
    mode = g.alloc(size=0x600000)                # the club table sits at +0x481be0 of it
    g.write(holder + 0x30, struct.pack('<I', mode))
    g.write(mc.MODE_OBJECT_AT, struct.pack('<I', holder))
    g.write(mc.CURRENT_CLUB_AT, struct.pack('<I', SELLER))
    g.write(mc.INCOMING_KEY, bytes([game_index]))
    g.write(mode + mc.CLUB_TABLE_COUNT, struct.pack('<I', len(CLUBS)))
    for i, club in enumerate(CLUBS):
        at = mode + mc.CLUB_TABLE + mc.CLUB_STRIDE * i
        g.write(at, struct.pack('<I', club))                 # the id
        g.write(at + 0x314, struct.pack('<I', i << 7))       # the slot, and nothing else
        g.write(at + 0x31e, bytes(4))                        # not flagged
        g.write(at + 0x328, struct.pack('<I', 0x28 << 9))    # 40 players: room
    install(g, code, pairs)
    out = g.alloc(struct.pack('<I', 0xdeadbeef))
    flag = g.alloc(struct.pack('<I', 0))
    g.call(mc.INCOMING_SITE, [out, mc.INCOMING_KEY, flag], ecx=mode)
    return struct.unpack('<I', g.read(out, 4))[0]


def main(exe):
    routine, site, old, new = module_text()
    code = mc.build()['INCOMING_BYTES']
    assert bytes.fromhex(routine) == code, 'MLTransfers.lua does not ship the bytes money_cave.py builds'
    assert site == mc.INCOMING_SITE and bytes.fromhex(old) == mc.INCOMING_SITE_OLD
    assert bytes.fromhex(new) == (b'\xe9' + struct.pack('<i', mc.INCOMING_CODE - (site + 5)) + b'\x90')

    pairs = [(SELLER, CLUBS[GAME])]
    got = run(exe, code, GAME, pairs)
    assert got in (CLUBS[GAME - 1], CLUBS[GAME + 1]), 'a rival still bids: %#x' % got
    got = run(exe, code, 2, pairs)
    assert got == CLUBS[2], 'a sensible club was changed: %#x' % got
    got = run(exe, code, GAME, [(SELLER, club) for club in CLUBS])
    assert got == CLUBS[GAME], 'the game answer did not stand: %#x' % got
    got = run(exe, code, GAME, [])
    assert got == CLUBS[GAME], 'without RIVALS something changed: %#x' % got
    print('offers for your players: 4 of 4 cases as expected')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/game/PES2017.exe')
