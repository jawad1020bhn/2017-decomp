#!/usr/bin/env python3
"""Checks the position need of MLTransfers.lua (NEED) in the emulated game.

    python3 test_need.py <PES2017.exe>          needs: pip install lupa unicorn

The two modules are installed as test_money.py does it. Then
  1. the changed place of club_squad_plan is run on a made-up frame of that function: the
     plan record must come out as money_cave.need_slot says, and nothing else may change;
  2. ai_pick_candidate itself is run from its first instruction to the end of its two
     searches, with ai_candidates answered by a recorder: the range each search gets must
     be the game's, raised by money_cave.need_lowest;
  3. with NEED off, and with no module, both are as in the game.
The made-up frame is also given to the game's own loop of club_squad_plan that writes a
slot for a place without a player: it must read the lineup list and write the slots as
this file takes them to be.
What this does not show: club_squad_plan run whole (it needs a career in memory), so that
the list is in that frame when the changed place is reached is read from the disassembly,
not run; and that no code of the game uses the two bytes of the plan record (they are 0
in every record of the four saves; not all the code that handles the records is read).
"""
import os
import random
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools')]
import money_cave as mc                          # noqa: E402
import test_money as tm                          # noqa: E402
from emu import REG, RETURN, STACK, STACK_SIZE   # noqa: E402
from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_ESP    # noqa: E402

SAVES = [os.path.join(HERE, '..', 'ML saves', *x) for x in (
    ('ML00000013 (before)',), ('ML00000013 (after)',), ('2nd test', 'ML00000013 (before)'),
    ('2nd test', 'ML00000013 (after)'))]
# club_squad_plan: its loop over the lineup list that gives a place without a player a slot
GAME_LOOP = (0x0366085c, 0x03660961)
NO_PLAYERS = ((0, 0), (0xffff, 0xffffffff), (0x1234, 7))    # id pairs the game may hold for "no player"


def made_up_club(h, gap):
    """A random lineup list, plan record and frame of club_squad_plan in the emulator's memory.
    -> what was written, and the lineup as (rating, position) or None for a place without a player."""
    g = h.g
    frame = h.pick_frame
    if not hasattr(h, 'lineup'):
        h.lineup = g.alloc(size=16 * 20)                     # 20 entries
        h.heap = g.top                                       # where the harness starts again for each case
    lineup = h.lineup
    none = random.choice(NO_PLAYERS)
    g.write(mc.NO_PLAYER_AT, struct.pack('<II', *none))
    index = random.choice([0, 1, 497, 850, random.randint(0, 850)])
    plan = h.mode_data + mc.PLAN_RECORDS + mc.PLAN_SIZE * index
    # the eleven: a level, a weakest player at, just under or just over the gap, some places empty
    count = random.choice([11] * 6 + [12, 16, 20, 10, 5, 0])
    base = random.randint(45, 95)
    ratings = [min(99, max(1, base + random.randint(-3, 3))) for _ in range(count)]
    if count and random.randint(0, 5):
        others = sum(ratings[:mc.ELEVEN]) - ratings[0]
        edge = others // max(1, min(count, mc.ELEVEN) - 1) - gap
        ratings[random.randrange(min(count, mc.ELEVEN))] = min(99, max(0, edge + random.choice([-9, -2, -1, 0, 0, 1, 2])))
    if random.randint(0, 9) == 0:
        ratings = [random.choice([0, 99, 127, base]) for _ in range(count)]
    positions = [random.choice([0, 0, 0] + list(range(13))) for _ in range(count)]
    empty = [random.randint(0, 7) == 0 for _ in range(count)]
    if random.randint(0, 19) == 0:
        empty = [random.randint(0, 3) != 0 for _ in range(count)]
    entries, eleven = b'', []
    for r, p, e in zip(ratings, positions, empty):
        ident = none if e else (random.getrandbits(32), random.getrandbits(32) | 1)
        if not e and random.randint(0, 9) == 0:          # half the pair of "no player": a player
            ident = (none[0], none[1] ^ 1) if random.randint(0, 1) else (none[0] ^ 1, none[1] or 1)
        entries += struct.pack('<IIII', ident[0], ident[1], r | p << 7 | random.getrandbits(18) << 14, random.getrandbits(32))
        # as the game tells it: the second number, and with it the low word of the first (not looked at when 0 stands for nobody)
        nobody = ident[1] == none[1] and (none[1] == 0 or ident[0] & 0xffff == none[0] & 0xffff)
        eleven.append(None if nobody else (r, p))
    g.write(lineup, entries + bytes(random.getrandbits(8) for _ in range(16 * 20 - len(entries))))
    kind = random.choice([0] * 6 + [1, 1, 2, 3, 4])
    looks = [random.choice([mc.NO_POSITION] * 5 + list(range(13))) for _ in range(mc.PLAN_SLOTS)]
    if random.randint(0, 9) == 0:
        looks = [random.randint(0, 12) for _ in range(mc.PLAN_SLOTS)]
    record = struct.pack('<II', random.getrandbits(32), kind)
    for p in looks:
        record += struct.pack('<IIII', random.getrandbits(32), random.getrandbits(32),
                              random.getrandbits(7) | p << 7 | random.getrandbits(18) << 14, random.getrandbits(32))
    record += bytes(random.getrandbits(8) for _ in range(mc.PLAN_SIZE - len(record)))
    around = bytes(random.getrandbits(8) for _ in range(mc.PLAN_SIZE))
    g.write(plan - mc.PLAN_SIZE, around + record + around)
    locals_ = bytearray(random.getrandbits(8) for _ in range(0x100))
    struct.pack_into('<I', locals_, 0x100 - 0x50, h.mode_data)
    struct.pack_into('<I', locals_, 0x100 - 0x4c, index)
    struct.pack_into('<II', locals_, 0x100 - 0x60, lineup, lineup + len(entries))
    struct.pack_into('<I', locals_, 0x100 - 0x20, plan)      # the game keeps the record's address here until it sorts
    g.write(frame - 0x100, bytes(locals_))
    return dict(frame=frame, lineup=lineup, entries=entries, eleven=eleven, plan=plan, record=record, around=around,
                locals=locals_, kind=kind, looks=looks)


def game_slots(h, n):
    """The game's own loop over the lineup list in club_squad_plan (a place without a player
    gets a slot), run on the made-up frame: it must find the places without a player, their
    positions and the slots where this file puts them. -> slots written."""
    g, mu = h.g, h.g.mu
    written = 0
    for case in range(n):
        c = made_up_club(h, 4)
        frame, record = c['frame'], c['record']
        esp = frame - 0x200
        for k in REG:
            mu.reg_write(REG[k], random.getrandbits(32))
        mu.reg_write(UC_X86_REG_ESP, esp)
        mu.reg_write(UC_X86_REG_EBP, frame)
        mu.emu_start(GAME_LOOP[0], GAME_LOOP[1], count=20000)
        assert mu.reg_read(UC_X86_REG_ESP) == esp and mu.reg_read(UC_X86_REG_EBP) == frame, 'stack'
        want, looks, slots = bytearray(record), list(c['looks']), 0
        for e, entry in zip(c['eleven'], struct.iter_unpack('<IIII', c['entries'])):
            if e is not None:
                continue
            slots += 1
            if mc.NO_POSITION in looks:
                at = looks.index(mc.NO_POSITION)
                looks[at] = entry[2] >> 7 & 0x7f
                word = struct.unpack_from('<I', record, 0x10 + 16 * at)[0]
                struct.pack_into('<I', want, 0x10 + 16 * at, word & ~0x3f80 | looks[at] << 7)
                if c['kind'] == 3:
                    struct.pack_into('<H', want, 0x16 + 16 * at, 23)         # the age such a plan puts on its slots
                written += 1
        assert g.read(c['plan'] - mc.PLAN_SIZE, 3 * mc.PLAN_SIZE) == c['around'] + bytes(want) + c['around'], (case, c['eleven'], c['looks'])
        assert struct.unpack('<I', g.read(frame - 0x1c, 4))[0] == slots and g.read(c['lineup'], len(c['entries'])) == c['entries']
    return written


def plan_cases(h, t, n):
    """The place in club_squad_plan, with the module in (t) or not (t = None).
    -> (clubs that got a slot, of them for the goalkeeper)."""
    g, mu = h.g, h.g.mu
    got, keepers = 0, 0
    mu.ctl_remove_cache(mc.NEED_PLAN_SITE, mc.NEED_PLAN_SITE + 16)
    for case in range(n):
        c = made_up_club(h, t.need_gap if t is not None and t.need else 4)
        frame, lineup, entries, eleven, plan = c['frame'], c['lineup'], c['entries'], c['eleven'], c['plan']
        record, around, locals_, kind, looks = c['record'], c['around'], c['locals'], c['kind'], c['looks']
        esp = frame - 0x200
        for k in REG:
            mu.reg_write(REG[k], random.getrandbits(32))
        before = {k: mu.reg_read(REG[k]) for k in REG}
        mu.reg_write(UC_X86_REG_ESP, esp)
        mu.reg_write(UC_X86_REG_EBP, frame)
        mu.emu_start(mc.NEED_PLAN_SITE, mc.NEED_PLAN_SITE + len(mc.NEED_PLAN_SITE_OLD), count=5000)
        after = {k: mu.reg_read(REG[k]) for k in REG}
        assert mu.reg_read(UC_X86_REG_ESP) == esp and mu.reg_read(UC_X86_REG_EBP) == frame, 'stack'
        assert after.pop('eax') == struct.unpack_from('<I', locals_, 0x100 - 0x48)[0], 'eax'
        before.pop('eax')
        assert after == before, 'registers'
        assert g.read(frame - 0x100, 0x100) == bytes(locals_) and g.read(lineup, len(entries)) == entries, 'frame or lineup'
        want = bytearray(record)
        slot = mc.need_slot(t, eleven, looks, kind)
        if t is not None and t.need:
            want[mc.PLAN_NEED_AT:mc.PLAN_NEED_AT + 2] = b'\0\0'
        if slot is not None:
            at, position, above = slot
            word = struct.unpack_from('<I', record, 0x10 + 16 * at)[0]
            struct.pack_into('<I', want, 0x10 + 16 * at, word & ~0x3f80 | position << 7)
            want[mc.PLAN_NEED_AT:mc.PLAN_NEED_AT + 2] = bytes([position + 1, above])
            assert looks[at] == mc.NO_POSITION and position not in looks and above <= 99
            got += 1
            keepers += position == 0
        assert g.read(plan - mc.PLAN_SIZE, 3 * mc.PLAN_SIZE) == around + bytes(want) + around, (
            case, eleven, looks, kind, slot, g.read(plan, mc.PLAN_SIZE).hex(), bytes(want).hex())
    return got, keepers


def pick_cases(h, t, n):
    """ai_pick_candidate up to the end of its two searches: the range each search is handed.
    -> searches whose range the position need raised."""
    g, mu = h.g, h.g.mu
    sel, top, low, pos, flag, age_low, age_high, band, level_at = h.cells
    calls, raised = [], 0

    def recorder(g, a):
        calls.append((struct.unpack('<I', g.read(a(1), 4))[0], struct.unpack('<I', g.read(a(2), 4))[0],
                      g.read(a(6), 1)[0], struct.unpack('<I', g.read(a(3), 4))[0], a(4)))
        return 0
    assert mc.AI_CANDIDATES not in g.replaced
    g.replace(mc.AI_CANDIDATES, recorder)
    try:
        for case in range(n):
            mu.ctl_remove_cache(mc.AI_PICK, tm.PICK_SEARCHED + 16)
            level, kind = random.randint(0, 9), random.choice([0, 0, 0, 1, 2, 3, 4])
            handed = random.choice([0, 0, mc.WINDOW_LOW[level], random.randint(1, 99)])
            position = random.randint(0, 13)
            mark = random.choice([(0, 0), (position + 1, random.randint(0, 99)), (position + 1, random.randint(40, 99)),
                                  (random.randint(1, 14), random.randint(0, 99)), (0, random.randint(1, 99))])
            record = bytearray(struct.pack('<II', random.getrandbits(32), kind) + bytes(
                random.getrandbits(8) for _ in range(mc.PLAN_SIZE - 8)))
            record[mc.PLAN_NEED_AT:mc.PLAN_NEED_AT + 2] = bytes(mark)
            g.write(h.plan, bytes(record))
            g.write(h.found, struct.pack('<III', h.found_data, h.found_data, h.found_data + 64))
            for cell, value in ((low, handed), (pos, position), (level_at, level), (age_low, 0), (age_high, 99), (band, 0)):
                g.write(cell, struct.pack('<I', value))
            esp = STACK + STACK_SIZE - 0x1000
            mu.mem_write(esp - 0x1000, random.getrandbits(8 * 0x1000).to_bytes(0x1000, 'little'))
            mu.mem_write(esp, struct.pack('<10I', RETURN, h.found_data, pos, h.plan, 0, low, level_at, age_low, age_high, band))
            for k in REG:
                mu.reg_write(REG[k], random.getrandbits(32))
            mu.reg_write(REG['ecx'], h.pool)
            mu.reg_write(UC_X86_REG_ESP, esp)
            mu.reg_write(UC_X86_REG_EBP, random.getrandbits(32))
            del calls[:]
            mu.emu_start(mc.AI_PICK, tm.PICK_SEARCHED, count=tm.STEPS)
            assert mu.reg_read(UC_X86_REG_EBP) == esp - 4, 'frame'
            above = mc.need_lowest(handed, position, mark) if t is not None and t.need else handed
            wide = above == 0
            want = (99 if wide else mc.WINDOW_TOP[level], max(above, 40), int(wide), position, h.plan)
            # the first set of lists, then the second; a plan of kind 1 or 4 the second only
            assert calls == [want] * (1 if kind in (1, 4) else 2), (case, level, kind, handed, position, mark, calls, want)
            assert g.read(h.plan, mc.PLAN_SIZE) == bytes(record) and struct.unpack('<I', g.read(low, 4))[0] == handed
            raised += above != handed
    finally:
        del g.replaced[mc.AI_CANDIDATES]
        g.top = h.heap
    return raised


def saves_spare_bytes():
    """The two bytes of the plan record the position need uses, in the saves of this folder."""
    import savefile
    import window_report as wr
    records = 0
    for path in SAVES:
        data = savefile.read(path)['data']
        for i in range(wr.PLANNED):
            record = data[wr.PLANS + wr.PLAN * i:wr.PLANS + wr.PLAN * (i + 1)]
            assert record[mc.PLAN_NEED_AT:mc.PLAN_NEED_AT + 2] == b'\0\0', (path, i)
            records += 1
    assert wr.PLAN == mc.PLAN_SIZE
    return records


def main(exe):
    random.seed(20261111)
    h = tm.Harness(exe)
    g = h.g
    source = tm.two_modules()
    off = tm.setting(source, 'NEED', 'false', part=1)

    # the model itself: the user's example, and what stands against a slot
    t = tm.settings(source)
    assert (t.need, t.need_gap, t.need_more) == (True, 4, 0)
    free = [mc.NO_POSITION] * mc.PLAN_SLOTS
    eleven = [(75, 0)] + [(82, p) for p in (1, 1, 2, 3, 4, 5, 5, 9, 10, 12)]
    assert mc.need_slot(t, eleven, free) == (0, 0, 75)                       # a goalkeeper rated above 75
    assert mc.need_slot(t, [(78, 0)] + eleven[1:], free) == (0, 0, 78)       # 4 below the mean of the others
    assert mc.need_slot(t, [(79, 0)] + eleven[1:], free) is None             # 3 below
    assert mc.need_slot(t, eleven, [0] + free[1:]) is None                   # the club looks for a goalkeeper already
    assert mc.need_slot(t, eleven, [5, mc.NO_POSITION] + [3] * 14) == (1, 0, 75)
    assert mc.need_slot(t, eleven, [3] * 16) is None                         # no empty slot
    assert mc.need_slot(t, eleven, free, 2) is None and mc.need_slot(t, eleven, free, 1) == (0, 0, 75)
    assert mc.need_slot(t, [None] + eleven[1:], free) is None                # an empty place is the game's business
    assert mc.need_slot(t, eleven[:10], free) is None and mc.need_slot(tm.settings(off), eleven, free) is None
    assert mc.need_slot(t, eleven[1:4] + [(60, 9), (60, 4)] + eleven[5:], free) == (0, 9, 60)    # the first of equals
    assert mc.need_lowest(83, 0, (1, 75)) == 83 and mc.need_lowest(67, 0, (1, 75)) == 75 and mc.need_lowest(0, 0, (1, 75)) == 75
    assert mc.need_lowest(67, 3, (1, 75)) == 67 and mc.need_lowest(0, 0, (0, 75)) == 0
    records = saves_spare_bytes()

    # 0. the game without a module
    written = game_slots(h, 2000)
    assert written > 1000
    plan_cases(h, None, 300)
    assert pick_cases(h, None, 300) == 0
    print('ok 0: without a module: the game\'s own loop of club_squad_plan, run on 2,000 made-up frames, takes '
          'the places without a player from the lineup list and writes their positions into the first empty '
          'slots (%d slots), so list, "no player" and slots are laid out as this test makes them; the place '
          'that will be changed changes no plan record; ai_pick_candidate hands its two searches the range of '
          'the club level, or 99 down to 41 when 0 is handed in (300 cases each); the two bytes of the plan '
          'record that the position need uses are 0 in all %d records of the four saves' % (written, records))

    # 1. the modules as they are
    h.restore()
    lines, _, _ = tm.run(g, source)
    assert tm.results(lines)[1] == tm.INSTALLED_T, tm.results(lines)
    got, keepers = plan_cases(h, t, 6000)
    raised = pick_cases(h, t, 3000)
    assert got > 500 and keepers > 100 and raised > 300, (got, keepers, raised)
    print('ok 1: with MLTransfers.lua in (NEED_GAP 4, NEED_BETTER 1), 6,000 made-up clubs at the end of '
          'club_squad_plan (lineups of 0 to 20 entries, places without a player in the three forms of "no '
          'player", the weakest at, just under and just over the gap, plans of every kind, slots empty and '
          'taken): the plan record comes out as money_cave.need_slot says (%d clubs got a slot, %d of them '
          'for a goalkeeper), the two bytes are cleared for the others, and frame, lineup, the records next '
          'to it, stack and registers are as the game leaves them; ai_pick_candidate run 3,000 times to the '
          'end of its searches hands them the range of money_cave.need_lowest (%d times raised), for the '
          'position of the need slot only' % (got, keepers, raised))

    # 2. other numbers, and NEED off
    for gap, better in ((1, 1), (30, 20), (6, 3), (3.4, 1.6)):
        h.restore()
        text = tm.setting(tm.setting(source, 'NEED_GAP', str(gap)), 'NEED_BETTER', str(better))
        t2 = tm.settings(text)
        assert (t2.need_gap, t2.need_more) == (int(gap + 0.5), int(better + 0.5) - 1)
        lines, _, _ = tm.run(g, text)
        assert tm.results(lines)[1] == tm.INSTALLED_T and any(
            ('when he stands %d or more rating points below the mean of '
             'the others; it takes only a player rated %d or more above him'
             % (t2.need_gap, t2.need_more + 1)) in line for line in lines)
        plan_cases(h, t2, 1500)
    h.restore()
    lines, _, _ = tm.run(g, off)
    assert tm.results(lines)[1] == tm.INSTALLED_T.replace(', position need', '')
    plan_cases(h, tm.settings(off), 300)
    assert pick_cases(h, tm.settings(off), 300) == 0
    h.restore()
    assert h.unchanged()
    print('ok 2: the same with NEED_GAP and NEED_BETTER at 1 and 1, 30 and 20, 6 and 3, 3.4 and 1.6 (1,500 clubs '
          'each); with NEED = false the two places are not changed and plan and searches are the game\'s')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
