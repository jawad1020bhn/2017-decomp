"""Runs MLYear.lua outside the game and then runs the game's own code with its change.

    python3 test_year.py <PES2017.exe>        needs: pip install lupa unicorn

The exe is loaded into a CPU emulator (../tools/emu.py) and the module runs as in
test_money.py. Then the pieces of the game's set-up of a new career that hold the year are
run as machine code: the year of the first day, the stored first day, and the start and
end of a contract. The set-up as a whole is not run (it needs a whole career in memory).

What this shows: the module's logic, and that the changed instructions give the dates of
the chosen year. What it does not show: Sider, Windows, the running game, a new career.
"""
import struct
import sys

from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_ESP

import test_money as tm
from test_money import Game, REG, STACK, STACK_SIZE, run, setting

MODULE = tm.MODULE.replace('MLMoney.lua', 'MLYear.lua')
GAME_YEAR = 2024
# address of the instruction, its length, where the year is in it, years added
PLACES = ((0x035f44b4, 5, 1, 0), (0x035f452e, 10, 6, 0), (0x035f458f, 10, 6, 0), (0x036653b3, 6, 2, 0),
          (0x036653bf, 10, 6, 0), (0x036653f2, 6, 2, 1), (0x036653fa, 6, 2, 0), (0x0366540c, 10, 6, 0))
ALLOWED = tuple((at, n) for at, n, _, _ in PLACES)
YEAR, FIRST_DAY = 0xc2cbb2, 0xdcb68c            # in the mode data
DATE_OF_DAY = 0x038ae3cc                        # (&date, &year, &day number)
MODE_SIZE = 0xe00000
INSTALLED = 'RESULT: installed. A new career starts in %d (season %d/%02d). A saved career keeps its year.'
NOTHING = 'RESULT: nothing written. '


def date(value):
    """The game's four bytes of a date -> (year, month, day)."""
    return value & 0xffff, value >> 16 & 0xff, value >> 24


def piece(g, begin, end, frame=0, **regs):
    """Runs the game's code from `begin` until `end`. -> registers after."""
    g.mu.reg_write(UC_X86_REG_ESP, STACK + STACK_SIZE - 0x1000)
    g.mu.reg_write(UC_X86_REG_EBP, frame)
    for k in REG:
        g.mu.reg_write(REG[k], regs.get(k, 0) & 0xffffffff)
    g.mu.emu_start(begin, end)
    return {k: g.mu.reg_read(REG[k]) for k in REG}


def game_dates(g, year):
    """Runs the eight changed instructions and compares what they write with `year`."""
    g.free_all()
    mode = g.alloc(size=MODE_SIZE)
    u32 = lambda a: struct.unpack('<I', g.read(a, 4))[0]
    piece(g, 0x035f44b4, 0x035f44c5, esi=mode)                  # the year of the first day
    assert struct.unpack('<H', g.read(mode + YEAR, 2))[0] == year
    piece(g, 0x035f452e, 0x035f4538, esi=mode)                  # first day, season from January
    assert date(u32(mode + FIRST_DAY)) == (year, 1, 1)
    piece(g, 0x035f458f, 0x035f4599, esi=mode)                  # first day, season from July
    assert date(u32(mode + FIRST_DAY)) == (year, 7, 1)
    # the game's date of a day number, from the year the set-up wrote
    out, day = g.alloc(size=4), g.alloc(size=4)
    for number, month, of_month in ((0, 1, 1), (181, 7, 1), (242, 8, 31), (364, 12, 31)):
        g.write(day, struct.pack('<I', number))
        g.call(DATE_OF_DAY, [out, mode + YEAR, day])
        assert date(u32(out)) == (year, month, of_month), (number, date(u32(out)))
    # contracts: ebx = years the game gives the player, edi = his record
    player, frame, runs = g.alloc(size=0x100), g.alloc(size=0x1000) + 0xf00, 0
    for years in range(0, 8):
        r = piece(g, 0x036653b3, 0x036653cf, ebx=years, edi=player)
        assert date(u32(player + 0xd8)) == (year, 7, 1) and date(r['ecx']) == (year + years, 8, 31)
        for flag in (0, 1):                                     # season from January
            g.write(frame - 0xa4c, struct.pack('<I', flag))
            r = piece(g, 0x036653eb, 0x03665416, frame=frame, ebx=years, edi=player)
            assert date(u32(player + 0xd8)) == (year, 1, 1)
            assert date(r['ecx']) == (year + years + (0 if flag else 1), 1, 31), (years, flag, date(r['ecx']))
            runs += 2
    return runs


def main(exe):
    source = open(MODULE, encoding='utf-8').read()
    assert setting(source, 'START_YEAR', '2026') == source          # the file's own setting
    image = Game(exe)
    before = image.read(0x035f4000, 0x72000)

    def fresh():
        for at, n, _, _ in PLACES:
            tm.poke(image, at, before[at - 0x035f4000:at - 0x035f4000 + n])

    control = game_dates(image, GAME_YEAR)
    for year in (2026, 2016, 2031, 2100):
        fresh()
        lines, reads, writes = run(image, setting(source, 'START_YEAR', str(year)))
        assert lines[-1] == INSTALLED % (year, year, (year + 1) % 100), lines[-1]
        assert sum('as expected' in l for l in lines) == 8 and len(lines) == 10
        assert sorted(writes) == sorted(ALLOWED) and tm.inside(reads, ALLOWED)
        after = image.read(0x035f4000, 0x72000)
        changed = {0x035f4000 + i for i in range(len(before)) if before[i] != after[i]}
        assert changed <= {at + o + k for at, _, o, _ in PLACES for k in (0, 1)} and changed
        for at, n, o, plus in PLACES:
            assert struct.unpack('<H', image.read(at + o, 2))[0] == year + plus
        assert game_dates(image, year) == control
    print('ok 1: with START_YEAR 2026, 2016, 2031 and 2100 the module writes the eight places and nothing '
          'else; only the bytes of the year differ')
    print('ok 2: the game\'s own code then gives that year: the year of the first day, the stored first '
          'day of both season kinds, the date of a day number, and the start and end of a contract '
          '(%d contract runs a year; without the module the same code gives %d)' % (control, GAME_YEAR))

    fresh()
    for new in ('"2026"', '2026.5', '1999', '2101', 'nil', 'true', '{ 2026 }'):
        lines, reads, writes = run(image, setting(source, 'START_YEAR', new))
        assert lines[-1].startswith(NOTHING + 'Settings: START_YEAR') and not writes and not reads, (new, lines[-1])
    lines, reads, writes = run(image, setting(source, 'START_YEAR', str(GAME_YEAR)))
    assert lines[-1] == NOTHING + 'The game starts a new career in 2024 by itself.' and not writes
    print('ok 3: seven faulty settings are refused before anything is read; with START_YEAR = 2024 '
          'nothing is written')

    count = 0
    for at, n, _, _ in PLACES:                  # every byte of every place, one at a time
        for k in range(n):
            fresh()
            tm.poke(image, at + k, bytes([before[at + k - 0x035f4000] ^ 0x02]))
            lines, reads, writes = run(image, source)
            assert lines[-1].startswith(NOTHING + 'This game does not hold') and not writes, (hex(at), k)
            assert sum('DIFFERENT' in l for l in lines) == 1 and ('%08x  DIFFERENT' % at) in '\n'.join(lines)
            count += 1
    fresh()
    lines, reads, writes = run(image, source, sticky=lambda a: a != 0x036653f2)
    assert lines[-1].startswith('RESULT: a change did not go in.'), lines[-1]
    print('ok 4: with one byte of a place changed (%d cases, a game that starts in 2026 already among '
          'them) nothing is written and the place is named; a write that does not go in is reported' % count)

    for order in ((source, tm.two_modules()), (tm.two_modules(), source)):
        del image
        image = Game(exe)
        lines, reads, writes = run(image, tm.SPLIT.join(order))
        got = [l for l in lines if l.startswith('RESULT')]
        assert len(got) == 3 and all(l.startswith('RESULT: installed.') for l in got), got
        assert game_dates(image, 2026) == control
    print('ok 5: with MLMoney.lua and MLTransfers.lua in the same game, above or below them, all three '
          'are installed and the year is 2026')


if __name__ == '__main__':
    main(sys.argv[1])
