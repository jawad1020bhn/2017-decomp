"""Runs MLGrowth.lua outside the game and then runs the game's own growth code with
its changes.

    python3 test_growth.py <PES2017.exe>        needs: pip install lupa unicorn capstone keystone-engine

The exe is loaded into a CPU emulator (../tools/emu.py) and the module runs as in
test_money.py.  Then the game's own functions run as machine code on made-up players:
the exp award fcn_038b2fc4 (hook A) and the season age walk fcn_036236a2 (hook E), with
the lookups the hooks need (growth record test/find, news) answered by stubs.  The
amounts the cave leaves in the exp argument are compared with growth_cave.py's Python
arithmetic, and the points the season walk adds to a player's abilities with growth_cave.season_points().

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

INSTALLED = ("RESULT: installed. The season awards AI players points on the abilities "
             "their position is rated by (archetype x form x role x ceiling), veterans "
             "decline family by family, and the tracked squad's exp and training follow "
             "the age curve.")
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


def craft(abilities, age, pos, id_lo=5, id_hi=77, club=0):
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
    struct.pack_into('<I', rec, 0xa8, club)
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


def test_walk_standalone():
    """Run HB and the season walk in a standalone CPU, without PES2017.exe: the tables,
    the hash chain and the two setters are all it needs.  Every case is compared with
    growth_cave.season_points() and growth_cave.decline_sel(), so the machine code and
    the Python twin must agree point for point."""
    from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_PROT_ALL, UC_HOOK_CODE
    from unicorn.x86_const import (UC_X86_REG_ESP, UC_X86_REG_EBP, UC_X86_REG_EDI,
                                   UC_X86_REG_EBX, UC_X86_REG_ESI, UC_X86_REG_EIP,
                                   UC_X86_REG_EAX)

    mu = Uc(UC_ARCH_X86, UC_MODE_32)
    mu.mem_map(0x02e8b000, 0x1000, UC_PROT_ALL)     # HB, WALK, tables
    mu.mem_map(0x03827000, 0x3000, UC_PROT_ALL)     # GETTER / SETTER
    mu.mem_map(0x0313b000, 0x1000, UC_PROT_ALL)     # TRACKED (stubbed below)
    mu.mem_map(0x02650000, 0x1000, UC_PROT_ALL)     # [MODE_OBJECT] -> mode data
    mu.mem_map(0x03623000, 0x1000, UC_PROT_ALL)     # SEASON_NEXT
    mu.mem_map(0x024fe000, 0x1000, UC_PROT_ALL)     # [0x24fe518]
    mu.mem_map(0x10000000, 0x10000, UC_PROT_ALL)    # stack and player
    data, season = gc.tables()
    mu.mem_write(gc.HB, bytes.fromhex(gc.part('HB')[1]))
    mu.mem_write(gc.WALK_CODE, bytes.fromhex(gc.part('walk')[1]))
    mu.mem_write(gc.TBL, season)

    # [MODE_OBJECT] -> +0x30 -> the record table; TRACKED then says whether a player
    # has a growth record (the tracked squad is hook A's, the walk must leave it alone)
    mu.mem_write(MODE_OBJECT, struct.pack('<I', 0x02650200))
    mu.mem_write(0x02650200 + 0x30, struct.pack('<I', 0x03000000))

    attrs, last_set = {}, []
    state = {'done': False}
    tracked = {'on': set()}

    def hook(uc, address, size, user):
        if address == gc.GETTER:
            esp = uc.reg_read(UC_X86_REG_ESP)
            sel = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
            out = struct.unpack('<I', uc.mem_read(esp + 8, 4))[0]
            uc.mem_write(out, struct.pack('<I', attrs.get(sel, 0)))
            uc.reg_write(UC_X86_REG_EIP, struct.unpack('<I', uc.mem_read(esp, 4))[0])
            uc.reg_write(UC_X86_REG_ESP, esp + 12)
        elif address == gc.SETTER:
            esp = uc.reg_read(UC_X86_REG_ESP)
            sel = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
            val = struct.unpack('<I', uc.mem_read(esp + 8, 4))[0]
            last_set.append((sel, val))
            uc.mem_write(uc.reg_read(UC_X86_REG_ESP) + 8, struct.pack('<I', val))
            attrs[sel] = val
            uc.reg_write(UC_X86_REG_EIP, struct.unpack('<I', uc.mem_read(esp, 4))[0])
            uc.reg_write(UC_X86_REG_ESP, esp + 12)
        elif address == gc.TRACKED:      # (id lo, id hi) -> al, the caller's ret 8
            esp = uc.reg_read(UC_X86_REG_ESP)
            pid = struct.unpack('<I', uc.mem_read(esp + 4, 4))[0]
            uc.reg_write(UC_X86_REG_EAX, 1 if pid in tracked['on'] else 0)
            uc.reg_write(UC_X86_REG_EIP, struct.unpack('<I', uc.mem_read(esp, 4))[0])
            uc.reg_write(UC_X86_REG_ESP, esp + 12)
        elif address == gc.SEASON_NEXT:
            state['done'] = True
            uc.emu_stop()

    mu.hook_add(UC_HOOK_CODE, hook)

    def run_one(pid, age, pos, values, club=10):
        nonlocal attrs, last_set
        attrs = dict(values)
        last_set = []
        player = 0x10008000
        rec = bytearray(0xe0)
        struct.pack_into('<I', rec, 4, pos << 28)
        struct.pack_into('<I', rec, 0x1c, age << 7)
        struct.pack_into('<I', rec, 0x2c, pid)
        struct.pack_into('<I', rec, 0xa8, club)
        mu.mem_write(player, bytes(rec))
        esp = 0x10005000
        mu.reg_write(UC_X86_REG_ESP, esp)
        mu.reg_write(UC_X86_REG_ESI, player)
        mu.reg_write(UC_X86_REG_EIP, gc.WALK_CODE)
        state['done'] = False
        mu.emu_start(gc.WALK_CODE, gc.SEASON_NEXT + 16, timeout=2000000)
        assert state['done'], 'the walk did not reach the game loop'
        ag = (struct.unpack_from('<I', rec, 0x1c)[0] >> 7) & 0x3f
        return last_set, ag

    checked = 0
    for age in (16, 18, 21, 26, 31, 36):
        for pos in (0, 5, 9, 12):
            for pid in (1, 2, 3, 17, 99, 1234):
                six = gc.six(pos)
                values = {sel: 60 for sel in six}
                values[six[0]] = 74
                got, _ = run_one(pid, age, pos, values)
                # the walk applies the season's points first, then the family decline,
                # and the decline reads the value the points may already have raised
                want = []
                after = dict(values)
                for sel, step in gc.season_points(pid, age, values, pos):
                    after[sel] = min(99, values[sel] + step)
                    want.append((sel, after[sel]))
                d = gc.decline_sel(pid, age, pos)
                if d is not None and after.get(d, 0) > gc.DECLINE_FLOOR:
                    want.append((d, after[d] - 1))
                assert got == want, (pid, age, pos, got, want)
                checked += 1
    # the gates: a free agent is left alone, and the ceiling is a wall
    got, _ = run_one(5, 18, 0, {0x13: 60}, club=0xffffffff)
    assert got == [], 'a free agent grew'
    top = gc.ceiling(5)
    got, _ = run_one(5, 18, 0, {sel: top for sel in gc.six(0)})
    assert got == [], ('an attribute at the personal ceiling grew', got, top)
    tracked['on'].add(7)                            # a player of the tracked squad
    got, _ = run_one(7, 18, 0, {0x13: 60})
    assert got == [], ('a tracked player grew twice (hook A and the walk)', got)
    tracked['on'].clear()
    for pid in (11, 12, 13):
        assert gc.hashb(pid, 0) == gc.hashb(pid, 0)
    print('ok 0b: the season walk in a standalone CPU agrees with growth_cave.season_points '
          'and decline_sel point for point over %d player/age/position cases, and leaves '
          'a free agent and a full attribute alone' % checked)


def main(exe):
    # Version 8: the tracked squad keeps hook A with an eased youth curve; the AI
    # season follows a calibrated archetype table (growth_twin.py is the spec).
    expected_curve = {15: 1.50, 18: 1.25, 22: 1.00, 25: 0.75, 28: 0.50, 30: 0.25}
    assert {age: gc.mult(age) for age in expected_curve} == expected_curve
    assert gc.award_exp(1000, 18, 60) == 1250
    # BASE, the shape of the AI season: each archetype peaks where its name says
    assert gc.phase(1, 40) == 0 and gc.phase(0, 32) == 0
    assert gc.phase(0, 15) > gc.phase(1, 15)            # the early developer starts fast
    assert gc.phase(2, 26) > gc.phase(1, 26)            # the late bloomer is not done
    assert gc.phase(3, 23) == 0 and gc.phase(3, 22) > 0  # the limited one has stopped
    print('ok 0: version 8 eases the tracked squad\'s youth steps (1.50 at 15, 1.25 at 18) '
          'and the AI season follows a calibrated archetype curve (normal peaks at 26-28)')

    source = open(MODULE, encoding='utf-8').read()
    assert gc.lua_block() in source, 'MLGrowth.lua does not hold the block of growth_cave.py'
    print('ok 0a: MLGrowth.lua holds exactly the code and tables growth_cave.py builds '
          '(the generated block matches)')

    test_walk_standalone()

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
    expect = [(gc.part(k)[0], len(bytes.fromhex(gc.lua_block_hex(k))))
              for k in ('curve', 'B1', 'focus', 'B2', 'HB', 'walk', 'data', 'season')]
    expect += [(at, len(new)) for at, old, new in gc.patches()]
    assert writes == expect, (writes, expect)
    print('ok 2: the module checks the nine context anchors and all four hook sites, '
          'finds its caves empty, writes them and the four patches, and nothing '
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

    # -- 5: the season walk over the game's own array, with the module -----------
    mode, _ = world(image, tracked=0)
    players = [craft({0x13: 64, 0x11: 61}, 17, 0, id_lo=1),
               craft({0x13: 70, 0x0f: 58}, 30, 9, id_lo=1),
               craft({0x13: 40, 0x17: 30}, 22, 9, id_lo=1),
               craft({0x1a: 50}, 16, 12, id_lo=1),
               craft({0x11: 50}, 17, 13, id_lo=1),
               craft({0x13: 64}, 17, 0, id_lo=5, club=0xffffffff)]
    after = season(image, mode, players)
    for i, rec in enumerate(after):
        age = (struct.unpack_from('<I', rec, 0x1c)[0] >> 7) & 0x3f
        pos = struct.unpack_from('<I', rec, 4)[0] >> 28
        assert age == (17, 30, 22, 16, 17, 17)[i] + 1, (i, age)
        if i == 5:
            assert field(rec, 0x13) == 64, 'a free agent grew'
            continue
        # 0x1e is not an attribute selector: walk the ones the game has
        sels = [s_ for s_ in range(0x0e, 0x26) if s_ in SLOT]
        before = {sel: field(players[i], sel) for sel in sels}
        want = dict(before)
        for sel, step in gc.season_points(1, age, before, pos):
            want[sel] = min(99, before[sel] + step)
        d = gc.decline_sel(1, age, pos)
        if d is not None and want.get(d, 0) > gc.DECLINE_FLOOR:
            want[d] = want[d] - 1
        got = {sel: field(rec, sel) for sel in sels}
        assert got == want, (i, age, pos, got, want)
    mode, _ = world(image, tracked=1)
    after = season(image, mode, [craft({0x13: 64}, 17, 0)])
    assert field(after[0], 0x13) == 64, 'a tracked player gets no season points'
    print('ok 5: the season walk over the game\'s own player array gives each AI player '
          'exactly growth_cave.season_points, declines him by decline_sel, and leaves a '
          'tracked player and a free agent alone')

    # -- 5a: the tables and the code agree with growth_cave ----------------------
    assert gc.build() == {name: (gc.part(name)[0], bytes.fromhex(gc.part(name)[1]))
                          for name in gc.CODE_PARTS}
    data, season_img = gc.tables()
    assert season_img[gc.T_PHASE - gc.TBL:gc.T_PHASE - gc.TBL + 18] == bytes(gc.PHASE[0])
    assert season_img[gc.T_SIX - gc.TBL:gc.T_SIX - gc.TBL + 12] == bytes(gc.six(0))
    for pid in range(1, 60):
        for age in (16, 18, 22, 27, 33):
            f = gc.form(pid, age)
            assert 0 <= f < 256 and isinstance(gc.hashb(pid, age), int)
    print('ok 5a: the assembled code matches every embedded block, the tables the cave '
          'reads are growth_cave\'s own, and the hash chain is in range')

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
    # a cave that will not take its bytes: the module stops before any patch goes in
    stick = Game(exe)
    lines, _, writes = run(stick, source, sticky=lambda a: a != gc.CODE_PARTS['curve'][0])
    assert 'could not be written' in lines[-1], lines[-1]
    sites = [site for site, _, _ in gc.patches()]
    assert not [w for w in writes if w[0] in sites], writes
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
                 'MLTeamSpirit', 'MLSimToDate'):
        text = (Path(MODULE).parent / (name + '.lua')).read_text(encoding='utf-8')
        lines, _, _ = run(image, text)
        result = tm.results(lines)[0]
        assert result.startswith('RESULT: 6 of 6 as expected.' if name == 'MLCheck' else 'RESULT: installed'), (name, result)
    checked = native_awards(image)
    mode, _ = world(image, tracked=0)
    sels = [s_ for s_ in range(0x0e, 0x26) if s_ in SLOT]
    before = {sel: field(craft({0x13: 64}, 17, 0), sel) for sel in sels}
    after = season(image, mode, [craft({0x13: 64}, 17, 0)])
    want = dict(before)
    for sel, step in gc.season_points(5, 18, before, 0):
        want[sel] = min(99, before[sel] + step)
    assert all(field(after[0], sel) == want[sel] for sel in sels)
    for which, menu_code, sel, expected in focus_results:
        assert focus_exp(image, which, menu_code, sel) == expected
    print('ok 9: all eight modules coexist during %d native-lookup awards, the season walk '
          'and both training-focus paths' % checked)

    print('all ok')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else
         'C:/Program Files/PRO EVOLUTION SOCCER 2017/PES2017.exe')
