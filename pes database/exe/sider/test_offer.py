#!/usr/bin/env python3
"""Checks the offers for the user's players (MLTransfers.lua, INCOMING) in the emulated game.

    python3 test_offer.py <PES2017.exe>       needs: pip install keystone unicorn lupa

The bytes are the ones MLTransfers.lua ships (assembled by money_cave.py, and compared with
the text of the module), written into the free memory the module uses, with the tables of
the module (money_cave.image_2) around them. Then the club look-up fcn_0381e2eb, changed at
its prologue, is run on a made-up mode data: a club table, a club ranking, plan records and
a player record, with the two game routines the chooser asks (the player record by id and
the rating for a position) replaced by stubs this test writes over them.

For every case the answer must be the one money_cave.offer_pick says, and:

  * a club whose slot is the key is kept when it passes the rules (nothing changes);
  * a rival of the club of the player is never answered;
  * a club whose persona does not want the player (age band, ambition, prestige) is not
    answered with the player, and neither is one whose plan has no place for his position
    and no position need for it, and neither is one that cannot afford him;
  * when no club passes, the game's own answer stands (the module answers nothing);
  * the club answered is the one whose slot is nearest to the game's own among those that
    pass;
  * the room of that club is not tested here: fcn_03652df0 runs the game's own room test on
    whatever the look-up answers, so this test says nothing about it.

What this does not show: that the club table of a real career, its ranking, its plan records
and `[0x0251f85c]` hold what this test makes them hold (that is read from the disassembly),
and that fcn_03822835 is the player record by id (the test stubs it).
"""
import os
import random
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools')]
import money_cave as mc                          # noqa: E402
import test_money as tm                          # noqa: E402
from emu import Game                             # noqa: E402

SELLER = 0x00424039
MODE_SIZE = 0xd10000                              # past the plan records (+0xccb80c) and their count
MODE_DAY = 0xc2cbb0                               # word: the day of the year, then the year
CLUB_STRIDE = mc.CLUB_STRIDE


def module_text():
    """The two constants of MLTransfers.lua the bytes must agree with."""
    text = open(os.path.join(HERE, 'MLTransfers.lua')).read()
    start = text.index('local INCOMING_ROUTINE = ')
    routine = ''.join(re.findall(r'"([0-9a-f]+)"', text[start:text.index('local INCOMING_SITE', start)]))
    site = re.search(r'local INCOMING_SITE = \{ "incoming", (0x[0-9a-f]+), "([0-9a-f]+)", "([0-9a-f]+)" \}',
                     text)
    return routine, int(site.group(1), 16), site.group(2), site.group(3)


class Harness:
    """The game in the emulator with the module's memory in it and the mode data this test
    writes: a club table, a club ranking, plan records and one player record."""

    def __init__(self, exe):
        g = self.g = Game(exe)
        self.t = tm.settings(tm.two_modules())
        self.mode = g.alloc(size=MODE_SIZE)
        holder = g.alloc(size=0x40)
        g.write(holder + 0x30, struct.pack('<I', self.mode))          # the mode object -> the mode data
        g.write(mc.MODE_OBJECT_AT, struct.pack('<I', holder))
        g.write(mc.CURRENT_CLUB_AT, struct.pack('<I', SELLER))
        g.write(mc.CAVE, mc.image(self.t))                            # MLMoney.lua: the value routine
        g.write(mc.CAVE_2, mc.image_2(self.t))                        # MLTransfers.lua: personas, ceiling
        g.write(mc.INCOMING_CODE, mc.build()['INCOMING_BYTES'])
        g.write(mc.INCOMING_SITE, mc.INCOMING_SITE_NEW)
        self.record = g.alloc(size=0x200)                             # the player record
        self.ptr = g.alloc(struct.pack('<I', self.record))
        self.position = g.alloc(size=4)
        self.rating = g.alloc(size=4)
        self.out = g.alloc(struct.pack('<I', 0xdeadbeef))
        self.flag = g.alloc(size=4)
        self.frame = g.alloc(size=0x20)
        self.deal = g.alloc(size=0x80)                                # what [ebp + 8] points at
        # emu.Game.call cannot set ebp, and the routine is entered from a caller that has a
        # frame: a small wrapper sets ebp and goes on to the module's routine
        self.frameglobal = g.alloc(size=4)
        self.wrapper = g.alloc(size=0x10)
        g.write(self.wrapper, b'\x8b\x2d' + struct.pack('<I', self.frameglobal)
                + b'\xe9' + struct.pack('<i', mc.INCOMING_CODE - (self.wrapper + 11)))
        g.write(mc.INCOMING_SITE, b'\xe9' + struct.pack('<i', self.wrapper - (mc.INCOMING_SITE + 5)) + b'\x90')
        self.install()

    def install(self):
        """The two game routines the chooser asks, replaced by stubs over the exe's bytes:
        the player record by id, and the rating for a position."""
        g = self.g
        g.write(mc.FIND_PLAYER, b'\xa1' + struct.pack('<I', self.ptr) + b'\xc2\x08\x00')
        g.write(mc.RATING, b'\x8b\x44\x24\x08'                        # mov eax, [esp + 8]: -> position
              + b'\x8b\x0d' + struct.pack('<I', self.position) + b'\x89\x08'
              + b'\xa1' + struct.pack('<I', self.rating) + b'\xc3')

    def case(self, key, seller, player, clubs, date=(0, 0)):
        """Writes the mode data and the player record; clubs: [(id, slot, flagged, plan)] with
        plan = (slots, need, points, level); date: (day of the year, year), as the mode data
        holds them at +0xc2cbb0."""
        g, mode = self.g, self.mode
        g.write(mc.CURRENT_CLUB_AT, struct.pack('<I', seller))
        g.write(mc.INCOMING_KEY, bytes([key]))
        g.write(mode + MODE_DAY, struct.pack('<HH', *date))
        g.write(mode + mc.CLUB_TABLE_COUNT, struct.pack('<I', len(clubs)))
        g.write(mode + mc.RANK_COUNT, struct.pack('<I', len(clubs)))
        g.write(mode + mc.PLAN_COUNT, struct.pack('<I', len(clubs)))
        for i, (club, slot, flagged, plan) in enumerate(clubs):
            at = mode + mc.CLUB_TABLE + CLUB_STRIDE * i
            g.write(at, struct.pack('<I', club) + bytes(0x314 - 4)
                    + struct.pack('<I', slot << 7) + bytes(0x31e - 0x314 - 4)
                    + struct.pack('<I', 1 if flagged else 0)
                    + bytes(0x520 - 0x31e - 4))
            rank = mode + mc.RANK_TABLE + 16 * i
            points = plan[2] if plan else 0
            club_level = plan[3] if plan else 0
            g.write(rank, struct.pack('<IIH', club, 0, points) + bytes(4)
                    + bytes([club_level]) + bytes(1))              # the level is the byte at +0xe
            at = mode + mc.PLAN_RECORDS + mc.PLAN_SIZE * i
            record = bytearray(mc.PLAN_SIZE)
            struct.pack_into('<I', record, 0, club)
            if plan:
                for n, (looks, state, kind) in enumerate(plan[0]):
                    struct.pack_into('<I', record, 8 + 16 * n + 8, looks << 7 | kind << 14 | state << 22)
                record[mc.PLAN_NEED_AT] = plan[1][0]
                record[mc.PLAN_NEED_AT + 1] = plan[1][1]
                record[0x114] = plan[3]
            g.write(at, bytes(record))
        at = self.record
        g.write(at, bytes(0x200))
        g.write(at + 4, struct.pack('<I', player['position'] << 28))
        g.write(at + 0x1c, struct.pack('<I', player['age'] << 7))
        g.write(at + 0x2c, struct.pack('<H', player['id'][0] & 0xffff))
        g.write(at + 0x30, struct.pack('<I', player['id'][1]))
        g.write(at + 0xb4, struct.pack('<I', player.get('status', 0) & 0xf | player['popularity'] << 11))
        g.write(at + 0xb8, struct.pack('<I', 0x40000000 if player.get('listed') else 0))
        g.write(self.position, struct.pack('<I', player['position']))
        g.write(self.rating, struct.pack('<I', player['rating']))
        g.write(self.deal, struct.pack('<IIQ', player['id'][0], player['id'][1], 0))
        g.write(self.frame + 8, struct.pack('<I', self.deal))
        g.write(self.frameglobal, struct.pack('<I', self.frame))

    def answer(self):
        g = self.g
        g.write(self.out, struct.pack('<I', 0xdeadbeef))
        g.call(mc.INCOMING_SITE, [self.out, mc.INCOMING_KEY, self.flag], ecx=self.mode)
        return struct.unpack('<I', g.read(self.out, 4))[0]


def make_case(rng, t, most_clubs=32):
    """A key, a seller, a player and a club table; every rule is met by some of the clubs.
    most_clubs: as many as the game's own table has clubs in a competition, not a handful:
    the chooser answers another club only when one of all of them wants the player."""
    clubs, slots = [], rng.sample(range(0, 64), most_clubs)
    for i in range(most_clubs):
        club = rng.getrandbits(30) | 1
        kind = rng.random()
        if kind < 0.35:                                  # a plan with a free slot for his position
            plan = ([(rng.randrange(0, 13), 0, 1)] + [(rng.randrange(0, 14), rng.choice((0, 1, 2, 7)), 1)
                                                     for _ in range(3)], (0, 0), rng.randrange(0, 2000),
                    rng.randrange(0, 10))
        elif kind < 0.5:                                 # the position need marked his position
            plan = ([(6, 1, 1)], (1, rng.randrange(30, 90)), rng.randrange(0, 2000), rng.randrange(0, 10))
        elif kind < 0.75:                                # a plan with no place for him
            plan = ([(rng.randrange(0, 13), rng.choice((1, 2)), 1) for _ in range(4)], (0, 0),
                    rng.randrange(0, 2000), rng.randrange(0, 10))
        else:                                            # no plan record at all
            plan = None
        clubs.append([club, slots[i], rng.random() < 0.1, plan])
    player = dict(id=(rng.randrange(0, 0xffff) | 1, rng.getrandbits(32)), age=rng.randrange(16, 38),
                  popularity=rng.randrange(0, 3000), position=rng.randrange(0, 13), rating=rng.randrange(45, 88),
                  status=rng.choice((0, 0, 0, 1, 2)), listed=rng.random() < 0.2)
    return clubs, player


def main(exe):
    routine, site, old, new = module_text()
    code = mc.build()['INCOMING_BYTES']
    assert bytes.fromhex(routine) == code, 'MLTransfers.lua does not ship the bytes money_cave.py builds'
    assert site == mc.INCOMING_SITE and bytes.fromhex(old) == mc.INCOMING_SITE_OLD
    assert bytes.fromhex(new) == (b'\xe9' + struct.pack('<i', mc.INCOMING_CODE - (site + 5)) + b'\x90')

    h = Harness(exe)
    rng = random.Random(20260116)
    changed = kept = nothing = 0
    cases = 0
    for _ in range(200):
        clubs, player = make_case(rng, h.t)
        # most cases ask for a slot a club sits at, so that the game has an answer to keep
        key = rng.choice(clubs)[1] if rng.random() < 0.75 else rng.randrange(0, 64)
        date = (rng.randrange(0, 366), rng.randrange(2020, 2060))
        h.case(key, SELLER, player, clubs, date)
        got = h.answer()
        want = mc.offer_pick(h.t, key, player, clubs, SELLER, date)
        game = next((c for c, slot, _, _ in clubs if slot == key), 0)      # what the game itself answers
        assert got == (want or game or SELLER), \
            'case %d: the module answered %#x, money_cave.offer_pick says %#x (the game: %#x)' % (
                cases, got, want, game or SELLER)
        if want and want != SELLER:
            changed += 1
        elif not want and game:
            kept += 1
        else:
            nothing += 1
        cases += 1

    # the day: the club that bids is not the same club on every day of the window. A case is
    # looked for whose answer the rules change with the day, and then the module must answer
    # as they say on every one of those days
    for tries in range(50):
        clubs, player = make_case(rng, h.t)
        key = rng.choice(clubs)[1]
        days = [(rng.randrange(0, 366), rng.randrange(2020, 2060)) for _ in range(12)]
        wants = [mc.offer_pick(h.t, key, player, clubs, SELLER, day) for day in days]
        if len(set(wants)) > 1:
            break
    else:
        assert False, 'the day changed no answer in 50 cases: it does not reach the draws'
    for day, want in zip(days, wants):
        h.case(key, SELLER, player, clubs, day)
        game = next((c for c, slot, _, _ in clubs if slot == key), 0)
        assert h.answer() == (want or game or SELLER), \
            'day %s: the module answered %#x, money_cave.offer_pick says %#x' % (day, h.answer(), want)
    different = len(set(wants))

    # nothing is answered where the game's own answer is no club at all: the game's code runs
    clubs = [[0x0019000d, 3, False, ([], (0, 0), 100, 5)], [0x001b4036, 5, False, ([], (0, 0), 100, 5)]]
    player = dict(id=(0x1234, 0x5678), age=28, popularity=100, position=4, rating=70, status=0, listed=False)
    h.case(9, SELLER, player, clubs)
    assert h.answer() == SELLER, 'the game\'s own answer did not run: %#x' % h.answer()
    assert changed >= 10 and kept >= 20, 'the cases did not exercise both paths: %d, %d' % (kept, changed)
    print('offers for your players: %d cases as money_cave.offer_pick says (%d the game\'s own club '
          'kept, %d another club answered, %d no club at the game\'s slot)' % (cases, kept, changed, nothing))
    print('the day: a case with %d different answers over %d days of the career, as the rules say'
          % (different, len(days)))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '/tmp/game/PES2017.exe')
