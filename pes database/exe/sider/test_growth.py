"""Runs MLGrowth.lua outside the game and then runs the game's own growth code with
its changes.

    python3 test_growth.py <PES2017.exe>        needs: pip install lupa unicorn capstone keystone-engine

The exe is loaded into a CPU emulator (../tools/emu.py) and the module runs as in
test_money.py.  Then the game's own functions run as machine code on made-up players:
the exp award fcn_038b2fc4 (hook A) and the season age walk fcn_036236a2 (hook E), with
the lookups the hooks need (growth record test/find, news) answered by stubs.  The
amounts the cave leaves in the exp argument are compared with growth_cave.py's Python
arithmetic, and the points hook E adds to a position ability with its season_levels().

What this shows: the module's logic and byte discipline, and that with it a tracked
18-year-old with ten appearances gets 1000 x 2.0 x playtime(10) exp while the vanilla
game gives everyone the flat 1000. It also verifies that the moderated curve retains
its potential and playtime rules, decline is dampened but not for the physical fields
from 31 on, and the frozen majority gains curve points a season. What it does not show:
Sider, Windows, the running game, a season.
"""
from pathlib import Path
import struct
import sys

from unicorn import UC_HOOK_MEM_WRITE
from unicorn.x86_const import UC_X86_REG_FPSW

import test_money as tm
from test_money import Game, run

import growth_cave as gc

MODULE = tm.MODULE.replace('MLMoney.lua', 'MLGrowth.lua')
MODE_OBJECT = 0x026503e0                   # [this] -> +0x30 -> mode data
AWARD, SEASON, SEASON_COUNT = gc.AWARD, gc.SEASON, 0x05fecdc
PLAYER_OVR, GETTER, SETTER = gc.PLAYER_OVR, 0x038278b0, 0x038281b0
NEWS = 0x03623150                          # the news push of the award

INSTALLED = ('RESULT: installed. The moderated age curve is scaled by potential and '
             'playtime, the training focus follows it, and every other player gains a '
             'few position-specific points a season until the curve flattens.')
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


def award(g, player, sel, exp, kind=0):
    """Run the game's exp award on the player; -> the exp argument afterwards."""
    e, f = g.alloc(struct.pack('<f', exp)), g.alloc(struct.pack('<I', sel))
    g.call(AWARD, [player, f, e, kind, 1], limit=500000)
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


def native_awards(g):
    """Real 50-slot lookups, including misses; UI/report publication alone is stubbed."""
    def low_write(mu, access, address, size, value, user):
        assert address == 0 and size == 4, ('growth wrote through a lost pointer', hex(address), size)

    guard = g.mu.hook_add(UC_HOOK_MEM_WRITE, low_write, begin=0, end=0xfff)
    init_fpu = 0x00301fe0
    g.write(init_fpu, b'\xdb\xe3\xc3')  # fninit; ret: detect underflow rather than inherit earlier FP flags
    checked = 0
    try:
        for slot in (-1, 0, 49):
            for age in (18, 35):
                for apps in (0, 10, 40):
                    for kind in (0, 2):
                        mode, _ = world(g)
                        for address in (gc.TRACKED, gc.GROWTH_REC):
                            del g.replaced[address]
                        for address in (0x024b4fc0, 0x024b4fc4, 0x024b3df4, 0x024b3df8):
                            g.write(address, b'\0' * 4)
                        g.replace(0x0364527c, lambda game, arg: 0)  # untracked-player report publication
                        table = mode + 0xd10140
                        if slot >= 0:
                            record = table + 0x493ec + slot * 0x204
                            g.write(record, struct.pack('<II', 5, 77))
                            g.write(record + 0x1a0, struct.pack('<I', apps))
                        player = g.alloc(craft({0x13: 60}, age, 0))
                        assert g.call(gc.TRACKED, [5, 77], ecx=table) & 255 == (slot >= 0)
                        rating = ovr(g, player)
                        g.call(init_fpu)
                        got = award(g, player, 0x13, 1000.0, kind)
                        want = gc.award_exp(1000, age, rating, apps if slot >= 0 else gc.PLAYTIME_FULL, kind)
                        assert abs(got - want) < 1e-3, (slot, age, apps, kind, got, want)
                        assert not g.mu.reg_read(UC_X86_REG_FPSW) & 0x41, 'x87 invalid/stack fault'
                        checked += 1
    finally:
        g.mu.hook_del(guard)
    return checked


def main(exe):
    # Version 3 moderation: the cave has quarter-step rates, so this guards both the
    # intended 15-27 slowdown and the deliberately unchanged 28+ tail. The existing
    # hook tests below prove that this one profile reaches awards, focus and season walk.
    expected_curve = {15: 2.5, 18: 2.0, 22: 1.25, 25: 0.75, 28: 0.5, 30: 0.25}
    assert {age: gc.mult(age) for age in expected_curve} == expected_curve
    assert gc.award_exp(1000, 18, 60) == 2000
    assert gc.season_levels(18, 90) == 0    # close to the ceiling: no forced extra point
    print('ok 0: version 3 uses the moderated 2.5/2.0/1.25/0.75 youth curve, keeps '
          'the 0.5/0.25 late tail, and still slows players near their potential ceiling')

    source = open(MODULE, encoding='utf-8').read()
    assert gc.lua_block() in source, 'MLGrowth.lua does not hold the block of growth_cave.py'
    print('ok 0a: MLGrowth.lua holds exactly the code and tables growth_cave.py builds '
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
    assert lines[-1] == INSTALLED, lines
    assert not any('DIFFERENT' in l or 'NOT EMPTY' in l or 'FAILED' in l for l in lines), lines
    expect = [(gc.part(k)[0], len(bytes.fromhex(gc.part(k)[1])))
              for k in ('E2', 'curve', 'B1', 'E1', 'B2', 'focus', 'data')]
    expect += [(at, len(new)) for at, old, new in gc.patches()]
    assert writes == expect, (writes, expect)
    print('ok 2: the module checks the nine context anchors and all four hook sites, '
          'finds its seven caves empty, writes them and the four patches, and nothing '
          'else (%d writes)' % len(writes))

    checked = native_awards(image)
    print('ok 2a: %d awards with real native growth-record scans (missing/first/last slot), '
          'no low-memory writes or x87 underflow, and correct age/playtime/kind scaling' % checked)

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
        (18, 0x13, 1000.0, 5, 'kind 2, a training award: minutes are not counted twice'),
    ]
    for age, sel, exp, apps, label in cases:
        kind = 2 if 'kind 2' in label else 0
        mode, growth = world(image, tracked=1, apps=apps)
        player = image.alloc(craft({sel: 60}, age, 9))
        got = award(image, player, sel, exp, kind)
        rating = ovr(image, player)
        want = (gc.decline_exp(exp, age, NAME[sel]) if exp < 0
                else gc.award_exp(exp, age, rating, min(apps, gc.PLAYTIME_FULL), kind))
        assert abs(got - want) < 1e-3, (label, got, want)
    print('ok 3: with the module the exp argument is curve x potential x playtime '
          '(verified against growth_cave.award_exp), the playtime factor is left out '
          'for kind-2 training awards the game already scales by minutes, and decline '
          'is a quarter except physical fields from 31 on (%d cases)' % len(cases))

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

    checked = 0
    for before_age in (14, 15, 16, 17, 20, 21, 22, 24, 28, 30, 51, 52, 62):
        cases = [(pos, value) for pos in range(16) for value in (40, 75, 80, 84, 90, 98, 99)]
        mode, _ = world(image, tracked=0)
        players = [craft({gc.POSTBL[pos]: value}, before_age, pos) for pos, value in cases]
        after = season(image, mode, players)
        for rec, (pos, was) in zip(after, cases):
            age = (struct.unpack_from('<I', rec, 0x1c)[0] >> 7) & 0x3f
            expected = was + gc.season_levels(age, was)
            assert field(rec, gc.POSTBL[pos]) == expected, (age, pos, was, field(rec, gc.POSTBL[pos]), expected)
            checked += 1
    assert gc.build() == {name: (gc.part(name)[0], bytes.fromhex(gc.part(name)[1])) for name in gc.CODE_PARTS}
    print('ok 5a: annual awards match the age-margin reference near the ceiling across '
          '%d age/position/ability cases; assembled code matches every embedded block' % checked)

    # -- 6: the training focus runs through the curve (hook C) -------------------
    INDIVIDUAL, TEAM = 0x036225f8, 0x0362274d

    def training_world(g, menu_code):
        """A mode object with the training settings on and one player of 18."""
        g.free_all()
        holder, mode = g.alloc(size=0x40), g.alloc(size=0x1000000)
        g.write(holder + 0x30, struct.pack('<I', mode))
        g.write(MODE_OBJECT, struct.pack('<I', holder))
        g.write(mode + 0xd62a8c, struct.pack('<I', menu_code))       # individual focus
        g.write(mode + 0xd62a84, b'\x01')                            # its regime byte
        g.write(mode + 0xd62a88, struct.pack('<I', 0x42))             # team focus coach
        g.write(mode + 0xd62a83, b'\x02')                            # the coach level
        player = g.alloc(craft({0x13: 60}, 18, 9))
        g.write(mode + 0xe4a528, struct.pack('<II', 5, 77))          # the id it looks up
        g.replace(0x03822835, lambda game, arg: player)              # PLAYER_RECORD
        dummy = mode + 0xd10140 + 0x493ec                            # what a miss of the
        g.replace(gc.GROWTH_REC, lambda game, arg: dummy)            # 50-slot scan returns
        return mode, player

    def focus_exp(g, which, menu_code, sel):
        """The exp the training left in the dummy growth record's slot `sel`."""
        mode, player = training_world(g, menu_code)
        mult = g.alloc(struct.pack('<I', 50))
        g.call(which, [player, mult], limit=500000)
        dummy = mode + 0xd10140 + 0x493ec
        return struct.unpack_from('<h', g.read(dummy + 0x16 + sel * 2, 2))[0]

    focus_results = []
    for which, menu_code, sel, label in ((INDIVIDUAL, 10, 10, 'individual focus'),
                                         (INDIVIDUAL, 1, 1, 'individual focus, other menu code'),
                                         (TEAM, 10, 0x42, 'team focus')):
        control = focus_exp(Game(exe), which, menu_code, sel)
        got = focus_exp(image, which, menu_code, sel)
        mode, player = training_world(image, menu_code)
        curve = gc.mult(18) * gc.scale(18, ovr(image, player))
        assert got == round(control * curve), (label, control, got, control * curve)
        focus_results.append((which, menu_code, sel, got))
    print('ok 6: with the module the after-match training focus (individual and team) '
          'runs its exp through the same age curve before the game turns it into '
          'levels; without the module the exp is the same at every age')

    # -- 7: the module refuses a wrong game --------------------------------------
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
    bad = Game(exe)
    old = bytes.fromhex('e8' + '00' * 4)                       # a training call already hooked
    tm.poke(bad, gc.FOCUS_CALLS[0], old)
    lines, _, writes = run(bad, source)
    assert lines[-1].startswith(ALREADY) and not writes, lines
    stick = Game(exe)
    lines, _, writes = run(stick, source, sticky=lambda a: a != gc.CODE_PARTS['E2'][0])
    assert 'could not be written' in lines[-1], lines[-1]
    assert not [w for w in writes if w[0] != gc.CODE_PARTS['E2'][0]], writes
    print('ok 7: a byte changed at a hook site or a context anchor, a cave not empty, or '
          'a hook already installed: nothing is written; a cave that will not hold the '
          'code leaves the game unchanged')

    # -- 8: the module twice ------------------------------------------------------
    image2 = Game(exe)
    run(image2, source)
    lines, _, writes = run(image2, source)
    assert lines[-1].startswith(ALREADY) and not writes, lines
    print('ok 8: after installation a second run refuses to overwrite itself')

    for name in ('MLCheck', 'MLMoney', 'MLYear', 'MLTransfers', 'MLSimMatch',
                 'MLTeamSpirit', 'MLSimToDate', 'MLNews'):
        text = (Path(MODULE).parent / (name + '.lua')).read_text(encoding='utf-8')
        lines, _, _ = run(image, text)
        result = tm.results(lines)[0]
        assert result.startswith('RESULT: 6 of 6 as expected.' if name == 'MLCheck' else 'RESULT: installed'), (name, result)
    checked = native_awards(image)
    mode, _ = world(image, tracked=0)
    after = season(image, mode, [craft({0x13: 64}, 17, 0)])
    assert field(after[0], 0x13) == 66
    for which, menu_code, sel, expected in focus_results:
        assert focus_exp(image, which, menu_code, sel) == expected
    print('ok 9: all nine modules coexist during %d native-lookup awards, the season walk '
          'and both training-focus paths' % checked)

    print('all ok')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         'C:/Program Files/PRO EVOLUTION SOCCER 2017/PES2017.exe')
