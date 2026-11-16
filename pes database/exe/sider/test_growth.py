"""Runs MLGrowth.lua outside the game and then runs the game's own growth code with
its changes.

    python3 test_growth.py <PES2017.exe>        needs: pip install lupa unicorn capstone

The exe is loaded into a CPU emulator (../tools/emu.py) and the module runs as in
test_money.py.  Then the game's own functions run as machine code on made-up players:
the exp award fcn_038b2fc4 (hook A) and the season age walk fcn_036236a2 (hook E), with
the lookups the hooks need (growth record test/find, news) answered by stubs.  The
amounts the cave leaves in the exp argument are compared with growth_cave.py's Python
arithmetic, and the points hook E adds to a position ability with its season_levels().

What this shows: the module's logic and byte discipline, and that with it a tracked
18-year-old with ten appearances gets 1000 x 2.5 x playtime(10) exp while the vanilla
game gives everyone the flat 1000, that decline exp is dampened but not for the physical
fields from 31 on, and that the frozen majority gains curve points a season.  What it
does not show: Sider, Windows, the running game, a season.
"""
import struct
import sys

import test_money as tm
from test_money import Game, run

import growth_cave as gc

MODULE = tm.MODULE.replace('MLMoney.lua', 'MLGrowth.lua')
MODE_OBJECT = 0x026503e0                   # [this] -> +0x30 -> mode data
AWARD, SEASON, SEASON_COUNT = gc.AWARD, gc.SEASON, 0x05fecdc
PLAYER_OVR, GETTER, SETTER = gc.PLAYER_OVR, 0x038278b0, 0x038281b0
NEWS = 0x03623150                          # the news push of the award

INSTALLED = ('RESULT: installed. Players with a growth record grow and decline by an age '
             'curve scaled by potential and playtime; every other player gains a few '
             'points a season on the ability of his position until the curve flattens.')
NOTHING = 'RESULT: nothing written. This game does not hold'
ALREADY = 'RESULT: nothing written. A growth hook is already modified'

# The player record of the emulator players.  Ground truth: the case handlers of the
# game's attribute getter fcn_038278b0 (jump table 0x0382801c).
#     rec+0 bits 24..30 atk;  rec+4: position (bits 28..31), def, gk, drib, ball_ctrl;
#     rec+8: finish, lowpass, loftpass, header;  rec+0xc: ball_win, place_kick, swerve,
#     reflex;  rec+0x10: catching, clearing, cover, speed;  rec+0x14: body_ctrl, phys,
#     kick_pwr, exp_pwr;  rec+0x18: jump, stamina;  rec+0x1c bits 7..12 age;
#     rec+0x2c: id (lo, hi).
SLOT = {0x0e: (0, 24), 0x0f: (4, 0), 0x10: (4, 7), 0x11: (4, 14), 0x12: (4, 21),
        0x13: (8, 0), 0x14: (8, 7), 0x15: (8, 14), 0x16: (8, 21),
        0x17: (0xc, 0), 0x18: (0xc, 7), 0x19: (0xc, 14), 0x1a: (0xc, 21),
        0x1b: (0x10, 0), 0x1c: (0x10, 7), 0x1d: (0x10, 14), 0x1f: (0x10, 21),
        0x20: (0x14, 0), 0x21: (0x14, 7), 0x22: (0x14, 14), 0x23: (0x14, 21),
        0x24: (0x18, 0), 0x25: (0x18, 7)}
NAME = {0x13: 'finish', 0x1f: 'speed', 0x24: 'jump', 0x11: 'drib', 0x10: 'gk', 0x17: 'ball_win'}


def field(rec, sel):
    off, shift = SLOT[sel]
    return (struct.unpack_from('<I', rec, off)[0] >> shift) & 0x7f


def craft(abilities, age, pos, id_lo=5, id_hi=77):
    """A player record with 7-bit abilities, age and position set."""
    rec = bytearray(0xe0)
    for sel, value in abilities.items():
        off, shift = SLOT[sel]
        d = struct.unpack_from('<I', rec, off)[0]
        struct.pack_into('<I', rec, off, d | ((value & 0x7f) << shift))
    d = struct.unpack_from('<I', rec, 4)[0]
    struct.pack_into('<I', rec, 4, (d & 0x0fffffff) | ((pos & 0xf) << 28))
    d = struct.unpack_from('<I', rec, 0x1c)[0]
    struct.pack_into('<I', rec, 0x1c, (d & ~0x3f80) | ((age & 0x3f) << 7))
    struct.pack_into('<II', rec, 0x2c, id_lo, id_hi)
    return bytes(rec)


def world(g, tracked=1, apps=10):
    """A mode object with one growth record of `apps` appearances, and the lookups the
    hooks need answered by stubs.  -> (mode data, growth record)."""
    g.free_all()
    holder, mode, growth = g.alloc(size=0x40), g.alloc(size=0x1000000), g.alloc(size=0x400)
    g.write(holder + 0x30, struct.pack('<I', mode))
    g.write(MODE_OBJECT, struct.pack('<I', holder))
    g.write(growth + 0x1a0, struct.pack('<I', apps))
    g.replace(gc.TRACKED, lambda game, arg: tracked)
    g.replace(gc.GROWTH_REC, lambda game, arg: growth)
    g.replace(NEWS, lambda game, arg: 0)
    return mode, growth


def award(g, player, sel, exp):
    """Run the game's exp award on the player; -> the exp argument afterwards."""
    e, f = g.alloc(struct.pack('<f', exp)), g.alloc(struct.pack('<I', sel))
    g.call(AWARD, [player, f, e, 0, 1], limit=500000)
    return struct.unpack('<f', g.read(e, 4))[0]


def season(g, mode, players):
    """Run the season walk over `players` (list of records); -> the records after it."""
    for i, rec in enumerate(players):
        g.write(mode + i * 0xe0, rec)
    g.write(mode + SEASON_COUNT, struct.pack('<I', len(players)))
    g.call(SEASON, [], limit=1000000)
    return [g.read(mode + i * 0xe0, 0xe0) for i in range(len(players))]


def ovr(g, player):
    return g.call(PLAYER_OVR, [player + 0x2c, g.alloc(size=4), 0], limit=200000) & 0xff


def main(exe):
    source = open(MODULE, encoding='utf-8').read()
    assert gc.lua_block() in source, 'MLGrowth.lua does not hold the block of growth_cave.py'
    print('ok 0: MLGrowth.lua holds exactly the code and tables growth_cave.py builds '
          '(the generated block matches)')

    image = Game(exe)

    # -- 1: what the vanilla game does ----------------------------------------
    g = Game(exe)
    for age, sel in ((18, 0x13), (35, 0x13)):
        _, growth = world(g)
        player = g.alloc(craft({sel: 60}, age, 9))
        award(g, player, sel, 1000.0)
        assert field(g.read(player, 0xe0), sel) == 61, (age, sel)      # +1 at every age
    for sel in (0x13, 0x1f):                                           # decline hits all fields
        _, _ = world(g)
        player = g.alloc(craft({sel: 60}, 35, 9))
        award(g, player, sel, -4000.0)
        assert field(g.read(player, 0xe0), sel) == 55, sel
    mode, _ = world(g, tracked=1)
    after = season(g, mode, [craft({0x13: 64}, 17, 0)])
    assert field(after[0], 0x13) == 64 and (struct.unpack_from('<I', after[0], 0x1c)[0] >> 7) & 0x3f == 18
    print('ok 1: without the module 1000 exp is one level at 18 as at 35, decline hits '
          'technical and physical fields alike, and the season walk raises only the age')

    # -- 2: the module ----------------------------------------------------------
    lines, reads, writes = run(image, source)
    assert lines[-1] == INSTALLED and len(lines) == 20, lines
    assert not any('DIFFERENT' in l or 'NOT EMPTY' in l or 'FAILED' in l for l in lines), lines
    expect = [(gc.part(k)[0], len(bytes.fromhex(gc.part(k)[1])))
              for k in ('E2', 'curve', 'B1', 'E1', 'B2', 'data')]
    expect += [(at, len(new)) for at, old, new in gc.patches()]
    assert writes == expect, (writes, expect)
    print('ok 2: the module checks the eight context anchors and both hook sites, finds '
          'its six caves empty, writes them and the two jumps, and nothing else (%d writes)'
          % len(writes))

    # -- 3: hook A with the module ----------------------------------------------
    cases = [                                          # (age, sel, exp, apps, label)
        (18, 0x13, 1000.0, 10, '18yo, ten appearances'),
        (18, 0x13, 1000.0, 40, 'capped at twenty appearances'),
        (18, 0x13, 1000.0, 0, 'no appearances'),
        (16, 0x13, 1000.0, 20, '16yo'),
        (26, 0x13, 1000.0, 20, '26yo'),
        (35, 0x13, 1000.0, 20, '35yo'),
        (35, 0x13, -4000.0, 20, '35yo decline, technical'),
        (35, 0x1f, -4000.0, 20, '35yo decline, physical'),
        (28, 0x1f, -4000.0, 20, '28yo decline, physical (before 31)'),
        (24, 0x13, -4000.0, 20, '24yo decline, technical'),
        (55, 0x13, 1000.0, 20, '55yo (no growth left)'),
    ]
    for age, sel, exp, apps, label in cases:
        mode, growth = world(image, tracked=1, apps=apps)
        player = image.alloc(craft({sel: 60}, age, 9))
        got = award(image, player, sel, exp)
        rating = ovr(image, player)
        want = (gc.decline_exp(exp, age, NAME[sel]) if exp < 0
                else gc.award_exp(exp, age, rating, min(apps, gc.PLAYTIME_FULL)))
        assert abs(got - want) < 1e-3, (label, got, want)
    print('ok 3: with the module the exp argument is curve x potential x playtime '
          '(verified against growth_cave.award_exp) and decline is a quarter except '
          'physical fields from 31 on (%d cases)' % len(cases))

    # -- 4: the curve fragment alone --------------------------------------------
    stub = 0x700f0000

    def curve_call(age, rating):
        """mov ebx, age; mov esi, rating; call curve; fstp [esp]; pop eax; ret."""
        code = (b'\xbb' + struct.pack('<I', age) +
                b'\xbe' + struct.pack('<I', rating) +
                b'\xe8' + struct.pack('<i', gc.CURVE - stub - 15) +
                b'\x83\xec\x04\xd9\x1c\x24\x58\xc3')
        tm.poke(image, stub, code)
        return struct.unpack('<f', struct.pack('<I', image.call(stub, [], limit=10000)))[0]

    checked = 0
    for age in (14, 15, 18, 21, 22, 25, 28, 30, 34, 52, 53, 63):
        for rating in (40, 60, 75, 80, 90, 98):
            got = curve_call(age, rating)
            want = gc.mult(age) * gc.scale(age, rating)
            assert abs(got - want) < 1e-4, (age, rating, got, want)
            checked += 1
    print('ok 4: the age-curve fragment answers mult(age) x scale(age, rating) for %d '
          'age/rating pairs, including no growth below 15 and from 53 on' % checked)

    # -- 5: hook E with the module ----------------------------------------------
    mode, _ = world(image, tracked=0)
    players = [craft({0x13: 64, 0x11: 61}, 17, 0),          # CF turning 18
               craft({0x13: 70, 0x0f: 58}, 30, 9),          # CB turning 31
               craft({0x13: 40, 0x0f: 30}, 22, 9),          # CB turning 23
               craft({0x10: 50}, 16, 12),                   # GK turning 17
               craft({0x11: 50}, 17, 13)]                   # broken position 13 -> drib
    sel_of = [0x13, 0x0f, 0x0f, 0x10, 0x11]
    before = [field(p, s) for p, s in zip(players, sel_of)]
    after = season(image, mode, players)
    for i, (rec, sel, was) in enumerate(zip(after, sel_of, before)):
        age = (struct.unpack_from('<I', rec, 0x1c)[0] >> 7) & 0x3f
        assert age == (17, 30, 22, 16, 17)[i] + 1, (i, age)
        assert field(rec, sel) == was + gc.season_levels(age, was), (i, field(rec, sel), was)
    mode, _ = world(image, tracked=1)
    after = season(image, mode, [craft({0x13: 64}, 17, 0)])
    assert field(after[0], 0x13) == 64, 'a tracked player gets no season points'
    print('ok 5: with the module the season walk raises the age of everyone and adds '
          'season_levels points on the position ability of every player without a '
          'growth record (CF finishing, CB defending, GK goalkeeping, the fallback of '
          'a broken position is dribbling); a tracked player is left to hook A')

    # -- 6: the module refuses a wrong game --------------------------------------
    for k in range(5):                          # every byte of the award site
        bad = Game(exe)
        tm.poke(bad, gc.AWARD + k, bytes([image.read(gc.AWARD, 5)[k] ^ 0x02]))
        lines, _, writes = run(bad, source)
        assert lines[-1].startswith(NOTHING) and not writes and any('DIFFERENT' in l for l in lines), (k, lines)
    bad = Game(exe)
    tm.poke(bad, gc.CONTEXT[0][1], b'\x90')
    lines, _, writes = run(bad, source)
    assert lines[-1].startswith(NOTHING) and not writes and any('DIFFERENT' in l for l in lines), lines
    bad = Game(exe)
    tm.poke(bad, gc.CODE_PARTS['data'][0], b'\x01')            # the table cave not empty
    lines, _, writes = run(bad, source)
    assert lines[-1].startswith(NOTHING) and not writes and any('NOT EMPTY' in l for l in lines), lines
    bad = Game(exe)
    tm.poke(bad, gc.AWARD, bytes.fromhex('e9' + '00' * 4))     # already hooked
    lines, _, writes = run(bad, source)
    assert lines[-1].startswith(ALREADY) and not writes, lines
    stick = Game(exe)
    lines, _, writes = run(stick, source, sticky=lambda a: a != gc.CODE_PARTS['E2'][0])
    assert 'could not be written' in lines[-1], lines[-1]
    assert not [w for w in writes if w[0] != gc.CODE_PARTS['E2'][0]], writes
    print('ok 6: a byte changed at a hook site or a context anchor, a cave not empty, or '
          'a hook already installed: nothing is written; a cave that will not hold the '
          'code leaves the game unchanged')

    # -- 7: the module twice ------------------------------------------------------
    image2 = Game(exe)
    run(image2, source)
    lines, _, writes = run(image2, source)
    assert lines[-1].startswith(ALREADY) and not writes, lines
    print('ok 7: after installation a second run refuses to overwrite itself')

    print('all ok')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         'C:/Program Files/PRO EVOLUTION SOCCER 2017/PES2017.exe')
