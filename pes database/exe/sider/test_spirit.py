"""Runs MLTeamSpirit.lua outside the game and then runs the game's own code with its change.

    python3 test_spirit.py <PES2017.exe>        needs: pip install lupa unicorn capstone

The exe is loaded into a CPU emulator (../tools/emu.py) and the module runs as in
test_money.py. Then two functions of the game run as machine code on a made-up player:
the one that gives a player his Team Spirit value (fcn_038df4c9) and the one of the match
set-up that stores the values of 3 formations x 13 positions for the match
(fcn_04177a65); the stored values are read back with the game's own reader
(fcn_02f7d891), which is what the match asks.

What this shows: the module's logic, and that with the change every value a Master League
match gets is 99. What it does not show: Sider, Windows, the running game, a match. The
code that multiplies the abilities by the value (fcn_02f903a7) is not run.
"""
import struct
import sys

import test_money as tm
from test_money import Game, run

MODULE = tm.MODULE.replace('MLMoney.lua', 'MLTeamSpirit.lua')
PLACE, OLD, NEW = 0x038df528, bytes.fromhex('e8b8cbf3ff'), bytes.fromhex('e974020000')
VALUE, FILL, READER, GETTER = 0x038df4c9, 0x04177a65, 0x02f7d891, 0x038278b0
SELECTOR, MODE_OBJECT = 0x0264f3e8, 0x026503e0      # pointers; selector +0x20 = mode number
MATCH = 0x537b8                                     # the match in the object at mode object +0x34
MASTER_LEAGUE, OTHERS = (0x13, 0x28), (0x12, 0x34)  # mode numbers: kind 12; League (11), kind 21
KNOWN = (3, 30, 60, 90)                             # how well the player knows a tactic setting
INSTALLED = ('RESULT: installed. In Master League the Team Spirit of every player is 99: '
             'no ability is lowered in a match.')
NOTHING = 'RESULT: nothing written. This game does not hold'


def world(g, mode, known, rating):
    """A game in mode `mode` with one player who is in the match. -> (player, his 14 bytes)"""
    g.free_all()
    selector, mode_object = g.alloc(size=0x100), g.alloc(size=0x100)
    match = g.alloc(size=MATCH + 0x1024 + 0x40 * 0xe8)
    player = g.alloc(size=0x400)
    g.write(selector + 0x20, struct.pack('<I', mode))
    g.write(SELECTOR, struct.pack('<I', selector))
    g.write(mode_object + 0x34, struct.pack('<I', match))       # +0x30 stays 0: no career loaded
    g.write(MODE_OBJECT, struct.pack('<I', mode_object))
    g.write(player + 0x2c, struct.pack('<II', 5, 77))           # his id
    g.write(match + MATCH + 0x1024 + 3 * 0xe8 + 0x2c, struct.pack('<II', 5, 77))   # fourth of team 0
    # the game's attribute getter: no playing style, `rating` (2 A, 1 B, 0 C) at every position
    g.replace(GETTER, lambda game, arg: game.write(arg(1), struct.pack('<I', 0 if arg(0) == 0x3a else rating)) or 1)
    return player, bytes([known, known] * 7) + b'\0\0'


def value(g, mode, known, rating, position=12):
    """The game's Team Spirit value of the player."""
    player, own = world(g, mode, known, rating)
    team = g.alloc(bytes([1, 0] * 7) + bytes(64))               # the club's seven tactic settings
    return g.call(VALUE, [player, g.alloc(own), team, position, 0, 0, 0, g.alloc(size=0x40)], limit=200000) & 0xff


def match_values(g, mode, known, rating):
    """The match set-up for the player's team. -> the 39 values the match reads."""
    player, own = world(g, mode, known, rating)
    team, plan = g.alloc(size=0x100), g.alloc(size=4 + 3 * 0xa0)
    g.call(FILL, [team, player, *struct.unpack('<4I', own), 0, 1, 0, plan], limit=2000000)
    stored = g.read(team + 0x56, 39)
    assert not any(g.read(team, 0x56)) and not any(g.read(team + 0x56 + 39, 0x100 - 0x56 - 39))
    assert bytes(g.call(READER, [f, p], ecx=team) & 0xff for f in range(3) for p in range(13)) == stored
    return stored


def game_values(g):
    """Every case of this test. -> {(function, mode, known, rating): value(s)}"""
    out = {}
    for mode in MASTER_LEAGUE + OTHERS:
        for known in KNOWN:
            for rating in (2, 1, 0):
                out['value', mode, known, rating] = value(g, mode, known, rating)
                out['match', mode, known, rating] = match_values(g, mode, known, rating)
    return out


def main(exe):
    source = open(MODULE, encoding='utf-8').read()
    image = Game(exe)
    before = image.read(PLACE - 0x100, 0x200)
    assert image.read(PLACE, 5) == OLD

    control = game_values(image)
    for (what, mode, known, rating), got in control.items():
        if what == 'value':
            assert 1 <= got <= known < 99, (mode, known, rating, got)
            stored = control['match', mode, known, rating]       # kind 21: lower in formations 2 and 3
            assert stored[:13] == bytes([got]) * 13 and 1 <= min(stored) and max(stored) == got
        if rating != 2:                                         # out of position: lower
            assert got < control[what, mode, known, 2] or known == 3
    print('ok 1: without the module the game gives the made-up player a value below 99 in every mode '
          '(%d cases: he knows the tactics at %s, plays a position rated A, B or C), lower out of '
          'position, and the match set-up stores it for 3 formations x 13 positions'
          % (len(control) // 2, ', '.join(map(str, KNOWN))))

    lines, reads, writes = run(image, source)
    assert lines[-1] == INSTALLED and len(lines) == 3 and 'as expected' in lines[1], lines
    assert writes == [(PLACE, 5)] and tm.inside(reads, ((PLACE, 5),))
    after = image.read(PLACE - 0x100, 0x200)
    assert after == before[:0x100] + NEW + before[0x105:]
    print('ok 2: the module writes the five bytes of the one place and nothing else')

    with_module = game_values(image)
    for (what, mode, known, rating), got in with_module.items():
        if mode in MASTER_LEAGUE:
            assert got == (99 if what == 'value' else b'\x63' * 39), (what, mode, known, rating, got)
        else:
            assert got == control[what, mode, known, rating]
    print('ok 3: with the module the same code gives 99 in Master League (mode numbers 19 and 40), '
          'whatever the player knows and wherever he plays, and the match reads 99 for all 3 '
          'formations x 13 positions; in League mode and mode kind 21 the values are as without the module')

    count = 0
    for k in range(5):                          # every byte of the place, one at a time
        tm.poke(image, PLACE, OLD)
        tm.poke(image, PLACE + k, bytes([OLD[k] ^ 0x02]))
        lines, reads, writes = run(image, source)
        assert lines[-1].startswith(NOTHING) and not writes and 'DIFFERENT' in lines[1], (k, lines)
        count += 1
    tm.poke(image, PLACE, NEW)                  # a game that holds the change already
    lines, reads, writes = run(image, source)
    assert lines[-1].startswith(NOTHING) and not writes
    tm.poke(image, PLACE, OLD)
    lines, reads, writes = run(image, source, sticky=False)
    assert lines[-1].startswith('RESULT: the change did not go in.'), lines[-1]
    print('ok 4: with one byte of the place changed (%d cases) or the change in already nothing is '
          'written and the place is named; a write that does not go in is reported' % count)

    for order in ((source, tm.two_modules()), (tm.two_modules(), source)):
        del image
        image = Game(exe)
        lines, reads, writes = run(image, tm.SPLIT.join(order))
        got = [l for l in lines if l.startswith('RESULT')]
        assert len(got) == 3 and all(l.startswith('RESULT: installed.') for l in got), got
        assert value(image, 0x13, 30, 1) == 99
    print('ok 5: with MLMoney.lua and MLTransfers.lua in the same game, above or below them, all three '
          'are installed and the value is 99')


if __name__ == '__main__':
    main(sys.argv[1])
