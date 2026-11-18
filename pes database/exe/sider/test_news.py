"""Emulate MLNews's real native ticker caller, strings and RNG, not a log-only feed.

    python test_news.py <PES2017.exe>

Requires lupa, unicorn, keystone-engine and capstone (as the other Sider tests).
CRT allocation/formatting/random APIs and the final UI widgets are stand-ins. The
native MainMenuInfoFL reader, its shuffle, vectors, string copies and destructors
execute. Save-table replay is NOT a full career load or a live Windows/PES test.
"""
import calendar
import hashlib
from pathlib import Path
import random
import struct
import sys

from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ, UC_HOOK_MEM_WRITE, UC_PROT_ALL, UC_PROT_EXEC, UC_PROT_READ
from unicorn.x86_const import UC_X86_REG_ESP

import news_cave as n
import test_money as tm
from test_simdate_calendar import api
from layout import off
import savefile

HERE = Path(__file__).resolve().parent
MODULE = HERE / 'MLNews.lua'
MODE, MENU, SEED = 0x026503e0, 0x0264f3e8, 0xddcf02
MATCHES, STRIDE, COUNT = 0x6f154c, 0x24c, 9000
CLUBS, CLUB_SIZE, CLUB_COUNT = 0x481be0, 0x520, 0x5fece0
COMPS, COMP_SIZE, COMP_COUNT = 0x552e80, 0x224, 0x5fece8
TODAY, DESTROY, SET_TEXT = 0xc2cbb0, 0x03554793, 0x033c664f


def u32(g, a):
    return struct.unpack('<I', g.read(a, 4))[0]


def put(g, a, v):
    g.write(a, struct.pack('<I', v & 0xffffffff))


def cstr(g, a, limit=1024):
    return g.read(a, limit).split(b'\0', 1)[0]


def text(g, a):
    size, capacity = struct.unpack('<II', g.read(a + 0x10, 8))
    return g.read(u32(g, a) if capacity > 15 else a, size)


def scalar(y, m, d):
    if not 2000 <= y <= 2200 or not 1 <= m <= 12 or not 1 <= d <= calendar.monthrange(2001, m)[1]:
        return 0
    return y * 365 + sum(calendar.monthrange(2001, i)[1] for i in range(1, m)) + d - 1


class World:
    def __init__(self, g):
        self.g = g
        self.base = g.alloc(size=0x1000000)
        self.owner, self.menu, self.buffer = g.alloc(size=0x40), g.alloc(size=0x40), g.alloc(size=0x110)
        put(g, self.owner + 0x30, self.base)
        put(g, MODE, self.owner)
        put(g, MENU, self.menu)
        self.reset()
        # Direct feature code must never write career memory, even accidentally.
        g.mu.mem_protect(self.base, 0x1000000, UC_PROT_READ)
        self.check_reads = False
        g.mu.hook_add(UC_HOOK_MEM_READ, self.read_guard,
                      begin=self.base, end=self.base + 0xffffff)

        def only_native_rng(mu, access, address, size, value, user):
            assert (address, size) == (self.base + SEED, 2), ('career write', hex(address), size)
        g.mu.hook_add(UC_HOOK_MEM_WRITE, only_native_rng,
                      begin=self.base, end=self.base + 0xffffff)

    def reset(self):
        g, b = self.g, self.base
        g.write(b + CLUBS, b'\xff' * (651 * CLUB_SIZE))
        g.write(b + COMPS, b'\xff' * (300 * COMP_SIZE))
        g.write(b + MATCHES, b'\0' * (COUNT * STRIDE))
        put(g, self.menu + 0x20, 0x13)
        put(g, b + 0xec1408, 2)  # native career load/progression selects indexed access
        put(g, b + CLUB_COUNT, 3)
        put(g, b + COMP_COUNT, 1)
        self.club(0, 1, b'User Club', user=True)
        self.club(1, 2, b'North FC')
        self.club(2, 3, b'South FC')
        self.comp(0, 1001)
        self.today(2024, 9, 15)

    def today(self, y, m=None, d=None, index=None):
        if index is None:
            index = scalar(y, m, d) - y * 365
        self.g.write(self.base + TODAY, struct.pack('<HH', index, y))

    def club(self, slot, key, name, user=False):
        a = self.base + CLUBS + slot * CLUB_SIZE
        ident = key << 14 | slot
        put(self.g, a, ident)
        self.g.write(a + 4, name + b'\0')
        put(self.g, a + 0x314, (0 if user else 255) << 7)
        return ident

    def comp(self, slot, ident, kind=1):
        a = self.base + COMPS + slot * COMP_SIZE
        self.g.write(a, struct.pack('<H', ident))
        put(self.g, a + 0x5c, kind)

    def match(self, slot=0, date=(2024, 9, 14), goals=(3, 1), home=1, away=2,
              played=True, comp=1001, ident=None):
        a = self.base + MATCHES + slot * STRIDE
        data = bytearray(STRIDE)
        struct.pack_into('<H', data, 0, slot if ident is None else ident)
        struct.pack_into('<HHHBBII', data, 4, comp, 0x4000 if played else 0,
                         *date, u32(self.g, self.base + CLUBS + home * CLUB_SIZE),
                         u32(self.g, self.base + CLUBS + away * CLUB_SIZE))
        data[0x14], data[0x17] = goals
        self.g.write(a, data)
        return a

    def read_guard(self, mu, access, address, size, value, user):
        if not self.check_reads:
            return
        b, g = self.base, self.g
        indexed = u32(g, b + 0xec1408) == 2
        allowed = ((TODAY, 4), (CLUB_COUNT, 4), (COMP_COUNT, 4), (0xec1408, 4),
                   (CLUBS, (651 if indexed else min(u32(g, b + CLUB_COUNT), 651)) * CLUB_SIZE),
                   (COMPS, (300 if indexed else min(u32(g, b + COMP_COUNT), 300)) * COMP_SIZE),
                   (MATCHES, COUNT * STRIDE), (SEED, 2))
        assert any(b + a <= address and address + size <= b + a + count for a, count in allowed), (
            'out-of-bounds career read', hex(address - b), size)

    def build(self):
        self.g.write(self.buffer, b'\xa5' * 0x110)
        self.check_reads = True
        length = self.g.call(n.BUILD, [], ecx=self.buffer, limit=1500000)
        self.check_reads = False
        assert self.g.read(self.buffer + 256, 16) == b'\xa5' * 16
        result = cstr(self.g, self.buffer, 256) if length else b''
        assert not length or len(result) == length
        return result

    def expected(self):
        g, b = self.g, self.base
        nc, np = u32(g, b + CLUB_COUNT), u32(g, b + COMP_COUNT)
        lookup = u32(g, b + 0xec1408)
        if lookup not in (0, 1, 2) or not 1 <= nc <= 651 or not 1 <= np <= 300:
            return b''
        if lookup == 2:
            nc, np = 651, 300
        clubs, user = {}, []
        for i in range(nc):
            r = g.read(b + CLUBS + i * CLUB_SIZE, CLUB_SIZE)
            ident = struct.unpack_from('<I', r)[0]
            if ident == 0xffffffff:
                continue
            control = struct.unpack_from('<I', r, 0x314)[0] >> 7 & 255
            if control == 0:
                user.append(ident >> 14 & 65535)
            if control != 255:
                continue
            name = r[4:74].split(b'\0', 1)
            if len(name) == 2 and name[0] and all(c >= 32 and c not in (60, 62, 127) for c in name[0]):
                clubs[ident] = name[0]
        if len(user) != 1 or user[0] in (0, 65535):
            return b''
        comps = {struct.unpack_from('<H', g.read(b + COMPS + i * COMP_SIZE, 2))[0]:
                 u32(g, b + COMPS + i * COMP_SIZE + 0x5c) for i in range(np)}
        index, year = struct.unpack('<HH', g.read(b + TODAY, 4))
        today = year * 365 + index
        choices = []
        for i in range(COUNT):
            r = g.read(b + MATCHES + i * STRIDE, 0x1a)
            ident, comp, flags = struct.unpack_from('<H2xHH', r)
            y, m, d = struct.unpack_from('<HBB', r, 8)
            a, z = struct.unpack_from('<II', r, 12)
            keys = a >> 14 & 65535, z >> 14 & 65535
            date, gf, ga = scalar(y, m, d), r[0x14], r[0x17]
            if (ident >= COUNT or not flags & 0x4000 or any(r[j] for j in (21, 22, 24, 25))
                    or date == 0 or not 0 <= today - date <= 7 or max(gf, ga) > 99
                    or comps.get(comp) != 1 or a not in clubs or z not in clubs
                    or user[0] in keys or keys[0] == keys[1]):
                continue
            headline = b'WORLD RESULT %02u/%02u/%04u: %s %u-%u %s | ' % (d, m, y, clubs[a], gf, ga, clubs[z])
            choices.append(((date, abs(gf - ga), -i), headline))
        return max(choices)[1] if choices else b''


class NativeUI:
    """Real reader/string/vector/RNG code; only the CRT and UI boundary are stubbed."""
    def __init__(self, g, w):
        self.g, self.w = g, w
        self.active, self.texts = {}, []
        self.crt, self.format_error, self.ready, self.rng = 0, False, True, []
        self.work, self.records = g.alloc(size=0x3b4), g.alloc(size=12 * 0x3c)
        self.menu, self.screen, self.widget = g.alloc(size=0x700), g.alloc(size=0x100), g.alloc(size=0x100)
        self.widgets = g.alloc(size=24 * 4)  # menu-owned cache, not a temporary headline allocation
        put(g, self.menu + 0x60c, self.widgets)
        put(g, self.menu + 0x614, self.widgets + 24 * 4)
        put(g, 0x0261b46c, self.work)
        self.news_count = 0

        def allocate(game, a):
            p = game.alloc(size=a(1))
            self.active[p] = a(1)
            return p

        def delete(game, a):
            assert a(1) in self.active, ('double/free of non-owned memory', hex(a(1)))
            del self.active[a(1)]
            return 0

        g.replace(tm.NEW_TAGGED, allocate)
        g.replace(tm.NEW, lambda game, a: game.alloc(size=a(0)))
        g.replace(tm.FREE, delete)
        # The real mode_random runs, including its seed write and both calls to rand.
        api(g, 0x00301900, 0x047d7504, 0, self.srand)
        api(g, 0x00301910, 0x047d779c, 0, self.rand)
        api(g, 0x00301920, 0x047d75cc, 0, self.sprintf)

        def rng(mu, address, size, user):
            esp = mu.reg_read(UC_X86_REG_ESP)
            self.rng.append(u32(g, u32(g, esp + 4)))
        g.mu.hook_add(UC_HOOK_CODE, rng, begin=tm.RANDOM, end=tm.RANDOM)

        def lookup(game, a):
            assert game.reg('ecx') == self.screen + 0x64
            assert a(0) == 0x12
            return self.widget if a(1) == 0 else 0

        def show(game, a):
            assert game.reg('ecx') == self.widget and (a(1), a(2)) == (0, 0)
            s = a(0)
            # A long result must have been COPIED into native heap storage, never
            # left as a pointer into the hook's stack buffer or executable cave.
            if u32(game, s + 0x14) > 15:
                assert u32(game, s) in self.active
            self.texts.append(text(game, s))
            return 0

        g.replace(0x033c9a87, lookup)
        g.replace(SET_TEXT, show)
        g.replace(0x033c5c03, lambda game, a: int(self.ready))
        g.replace(0x033c58d3, lambda game, a: 0)
        g.replace(0x033c5933, lambda game, a: 0)

    def srand(self, a):
        self.crt = a(0)
        return 0

    def rand(self, a):
        self.crt = (self.crt * 214013 + 2531011) & 0xffffffff
        return self.crt >> 16 & 0x7fff

    def sprintf(self, a):
        assert a(1) == 256 and cstr(self.g, a(2)) == n.FMT[:-1]
        values = tuple(cstr(self.g, a(i), 70) if i in (6, 9) else a(i) for i in range(3, 10))
        result = n.FMT[:-1] % values
        assert 0 < len(result) < a(1)
        if self.format_error:
            return 0xffffffff
        self.g.write(a(0), result + b'\0')
        return len(result)

    def news(self, count):
        for i in range(self.news_count):
            self.g.call(DESTROY, [], ecx=self.records + i * 0x3c)
        for i in range(count):
            for delta, value in ((0, b'Native headline %d' % i), (0x1c, b'Native summary %d' % i)):
                self.g.call(0x03807ee4, [self.g.alloc(value + b'\0')], ecx=self.records + i * 0x3c + delta)
            put(self.g, self.records + i * 0x3c + 0x38, 0)
        put(self.g, self.work + 0x14, self.records)
        put(self.g, self.work + 0x18, self.records + count * 0x3c)
        put(self.g, self.work + 0x1c, self.records + count * 0x3c)
        self.news_count = count

    def draw(self, hooked=True):
        g, w = self.g, self.w
        call = b'\xe8' + struct.pack('<i', n.COPY - n.SITE - 5)
        tm.poke(g, n.SITE, call if hooked else g.exe[off(n.SITE):off(n.SITE) + 5])
        put(g, self.menu + 0x610, self.widgets)
        # No career writes are permitted except the game's EXISTING shuffle seed.
        seed_page = (w.base + SEED) & ~0xfff
        g.mu.mem_protect(seed_page, 0x1000, UC_PROT_ALL)
        g.write(w.base + SEED, struct.pack('<H', 4242))
        before = hashlib.sha256(g.read(w.base, 0x1000000)).digest()
        stored = g.read(self.records, 12 * 0x3c)
        stored_text = [text(g, self.records + i * 0x3c + d) for i in range(self.news_count) for d in (0, 0x1c)]
        owned = dict(self.active)
        self.texts, self.rng = [], []
        w.check_reads = True
        g.call(n.READER, [self.screen], ecx=self.menu, ebx=11, esi=22, edi=33, limit=2000000)
        w.check_reads = False
        assert (g.reg('ebx'), g.reg('esi'), g.reg('edi')) == (11, 22, 33)
        assert g.mu.reg_read(UC_X86_REG_ESP) == tm.STACK + tm.STACK_SIZE - 0x1000
        assert g.read(self.records, 12 * 0x3c) == stored, 'stored native headlines were modified'
        assert stored_text == [text(g, self.records + i * 0x3c + d)
                               for i in range(self.news_count) for d in (0, 0x1c)]
        assert self.active == owned, ('temporary native strings/vectors leaked', self.active.keys() - owned.keys())
        seed = g.read(w.base + SEED, 2)
        g.write(w.base + SEED, struct.pack('<H', 4242))
        assert hashlib.sha256(g.read(w.base, 0x1000000)).digest() == before, 'career state other than RNG changed'
        g.mu.mem_protect(seed_page, 0x1000, UC_PROT_READ)
        return list(self.texts), list(self.rng), seed


def attach_observer(g, source):
    lua = tm.LuaRuntime(encoding=None, unpack_returned_tuples=True)
    env, logs, hooks, writes, clock = lua.globals(), [], {}, [], [1]
    env.log = lambda line: logs.append(line.decode())
    env.clock = lambda: clock[0]
    env.register = lambda name, callback: hooks.__setitem__(name.decode(), callback)

    def write(address, data):
        writes.append((int(address), len(data)))
        tm.poke(g, int(address), data)

    env.memory = lua.table_from({b'read': lambda a, size: g.read(int(a), int(size)), b'write': write})
    lua.execute(b'os = { time = function() return clock() end }')
    module = lua.execute(source.encode())
    context = lua.eval(b'{ register = function(name, fn) register(name, fn) end }')
    module.init(context)
    assert logs[-1].startswith('RESULT: installed.'), logs[-1]
    assert set(hooks) == {'livecpk_make_key', 'after_set_conditions'}
    assert writes == [(n.STATE, n.STATE_SIZE), (n.CAVE, n.SIZE), (n.SITE, 5)]
    writes.clear()

    def probe(advance=True):
        if advance:
            clock[0] += 1
        before = len(logs)
        assert hooks['livecpk_make_key'](context, b'unchanged\\asset.bin') is None
        assert hooks['after_set_conditions'](context) is None
        assert not writes, 'Lua diagnostics wrote game memory or changed a CPK key'
        return logs[-1] if len(logs) != before else None
    return probe


def install_checks(g, source):
    original = g.read(n.SITE, 5)

    def reset():
        tm.poke(g, n.SITE, original)
        tm.poke(g, n.CAVE, b'\0' * n.SIZE)
        tm.poke(g, n.STATE, b'\0' * n.STATE_SIZE)

    lines, reads, writes = tm.run(g, source)
    assert lines[-1].startswith('RESULT: installed.'), lines[-1]
    assert writes == [(n.STATE, n.STATE_SIZE), (n.CAVE, n.SIZE), (n.SITE, 5)]
    assert g.read(n.CAVE, n.SIZE) == n.build()
    assert g.read(n.STATE, n.STATE_SIZE) == n.state()
    assert g.read(n.SITE, 5) == b'\xe8' + struct.pack('<i', n.COPY - n.SITE - 5)
    lines, _, writes = tm.run(g, source)
    assert not writes and lines[-1].startswith('RESULT: nothing written.')
    reset()
    checked = 0
    addresses = {n.SITE, n.CAVE, n.CAVE + n.SIZE - 1}
    for a, size in reads:
        addresses.update((a, a + size // 2, a + size - 1))
    for a in sorted(addresses):
        old = g.read(a, 1)
        tm.poke(g, a, bytes([old[0] ^ 0x80]))
        lines, _, writes = tm.run(g, source)
        assert not writes and lines[-1].startswith('RESULT: nothing written.'), hex(a)
        tm.poke(g, a, old)
        checked += 1
    read = g.read
    for missing in (n.READER, n.CAVE, n.STATE):
        g.read = lambda a, size: None if a == missing else read(a, size)
        try:
            lines, _, writes = tm.run(g, source)
            assert not writes and lines[-1].startswith('RESULT: nothing written.')
        finally:
            g.read = read
    for failure in (n.STATE, n.CAVE, n.SITE):
        for partial in (False, True):
            reset()
            once = [False]

            def sticky(a):
                if a != failure:
                    return True
                if partial and not once[0]:
                    once[0] = True
                    tm.poke(g, a, b'\xcc')
                    return False
                return partial

            lines, _, _ = tm.run(g, source, sticky=sticky)
            expected = {n.SITE: 'RESULT: a change did not go in.',
                        n.CAVE: 'RESULT: a change did not go in (news cave).',
                        n.STATE: 'RESULT: a change did not go in (news diagnostics).'}[failure]
            assert lines[-1].startswith(expected), lines[-1]
            assert g.read(n.SITE, 5) == original
            if failure == n.SITE:
                assert 'Hook restored.' in lines[-1]
    reset()

    def refuses_restore(a):
        if a == n.SITE:
            tm.poke(g, a, b'\xcc')
            return False
        return True

    lines, _, _ = tm.run(g, source, sticky=refuses_restore)
    assert 'Hook restore failed.' in lines[-1]
    reset()
    damaged = source.replace('string.rep(string.char(0xcc), 32)', 'string.rep(string.char(0xcc), 31)')
    assert damaged != source
    lines, _, writes = tm.run(g, damaged)
    assert not writes and lines[-1].startswith('RESULT: nothing written.')
    probe = attach_observer(g, source)
    print('ok 1: frozen assembly, exact three writes, %d mismatches, double init, damaged block and write recovery' % checked)
    return probe


def lookup_modes(w, ui, probe):
    g, b = w.g, w.base
    expected = b'WORLD RESULT 02/10/2026: North FC 3-1 South FC | '
    for lookup in (2, 0, 1):
        w.reset()
        put(g, b + 0xec1408, lookup)
        w.today(2026, 10, 3)
        w.match(date=(2026, 10, 2))
        home = u32(g, b + CLUBS + CLUB_SIZE)
        assert g.call(0x03822969, [home], ecx=b) == b + CLUBS + CLUB_SIZE
        assert g.call(0x03822ab9, [1001], ecx=b) == b + COMPS
        got = w.build()
        assert got == expected, ('valid native lookup mode rejected', lookup, got, u32(g, n.STATE + 12))
        ui.news(1)
        assert ui.draw()[0][0].startswith(expected)
    # Indexed tables may have live slots beyond the number of populated records.
    w.reset()
    w.today(2026, 10, 3)
    g.write(b + CLUBS, b'\xff' * (651 * CLUB_SIZE))
    g.write(b + COMPS, b'\xff' * (300 * COMP_SIZE))
    w.club(600, 1, b'User Club', user=True)
    home = w.club(649, 2, b'North FC')
    w.club(650, 3, b'South FC')
    w.comp(299, 1001)
    w.match(home=649, away=650, date=(2026, 10, 2))
    assert g.call(0x03822969, [home], ecx=b) == b + CLUBS + 649 * CLUB_SIZE
    assert g.call(0x03822ab9, [1001], ecx=b) == b + COMPS + 299 * COMP_SIZE
    # Decoys just outside both arrays must never be read or selected.
    w.club(651, 4, b'Outside User', user=True)
    w.comp(300, 2002)
    w.match(1, home=649, away=650, date=(2026, 10, 3), comp=2002, goals=(9, 0))
    assert w.build() == w.expected() == expected
    ui.news(2)
    assert ui.draw()[0][0].startswith(expected)
    report = probe()
    assert 'year=2026 day-index=275' in report and 'lookup=2' in report, report
    assert 'final rendering NOT verified' in report
    for lookup in (0, 1, 3, 0xffffffff):
        put(g, b + 0xec1408, lookup)
        assert not w.build()
    w.reset()
    ui.news(0)
    print('ok 1a: native getters and ticker accept modes 0/1/2 at 03 Oct 2026; indexed sparse '
          'club/competition tails work with count metadata 3/1, outside-array decoys stay unread')


def diagnostics(w, ui, probe):
    g = w.g
    cold = g.read(n.STATE, n.STATE_SIZE)
    ui.news(0)
    ui.draw()
    assert g.read(n.STATE, n.STATE_SIZE) == cold == n.state()
    assert 'waiting for a native ticker copy' in probe()
    assert probe() is None
    ui.news(1)
    cases = ((w.menu + 0x20, 18, 2), (MENU, 0, 1), (MODE, 0, 3),
             (w.base + 0xec1408, 3, 4), (w.base + TODAY, 1999 << 16, 5),
             (w.base + CLUB_COUNT, 0, 6), (w.base + COMP_COUNT, 0, 7),
             (w.base + CLUBS + 0x314, 255 << 7, 8))
    for address, value, reason in cases:
        w.reset()
        w.match()
        old = u32(g, address)
        put(g, address, value)
        ui.draw()
        assert u32(g, n.STATE + 12) == reason, (hex(address), reason)
        assert probe() and probe() is None
        put(g, address, old)
    w.reset()
    ui.draw()
    assert u32(g, n.STATE + 12) == 9 and 'no eligible recent AI league result' in probe()
    w.match()
    ui.format_error = True
    ui.draw()
    assert u32(g, n.STATE + 12) == 10 and 'formatting failed' in probe()
    ui.format_error = False
    assert w.build()
    assert u32(g, n.STATE + 12) == 11 and 'copy not completed' in probe()
    assert ui.draw()[0][0].startswith(b'WORLD RESULT')
    assert u32(g, n.STATE + 12) == 12 and 'final rendering NOT verified' in probe()
    read = g.read
    g.read = lambda a, size: None if a == n.STATE else read(a, size)
    try:
        assert 'state unreadable' in probe() and probe() is None
    finally:
        g.read = read
    assert probe()
    ui.news(0)
    assert not ui.active
    print('ok 1b: empty-feed silence and every native rejection/copy stage are observable; '
          'callbacks return nil, are throttled and never write game/CPK data')


def rules(w):
    g, b = w.g, w.base
    expected = b'WORLD RESULT 14/09/2024: North FC 3-1 South FC | '
    w.match()
    assert w.build() == expected
    # Free/malformed, unplayed, future and extra-time/penalty records never make news.
    a = w.match(1, date=(2024, 9, 16), goals=(9, 0))
    assert w.build() == expected
    w.match(1, date=(2024, 9, 15), goals=(9, 0), played=False)
    assert w.build() == expected
    w.match(1, date=(2024, 9, 15), goals=(9, 0), ident=0xffff)
    assert w.build() == expected
    for delta in (21, 22, 24, 25):
        w.match(1, date=(2024, 9, 15), goals=(9, 0))
        g.write(a + delta, b'\1')
        assert w.build() == expected
    for date in ((2024, 0, 1), (2024, 13, 1), (2024, 9, 0), (2024, 9, 31),
                 (2024, 2, 29), (1999, 9, 14), (2201, 9, 14), (2025, 1, 1)):
        w.match(1, date=date, goals=(9, 0))
        assert w.build() == expected
    for home, away in ((0, 2), (1, 0), (1, 1)):
        w.match(1, date=(2024, 9, 15), home=home, away=away, goals=(9, 0))
        assert w.build() == expected
    w.match(1, date=(2024, 9, 15), goals=(255, 0))
    assert w.build() == expected
    w.match(1, date=(2024, 9, 15), comp=999)
    assert w.build() == expected
    # New date > old margin; within a date margin > record order; exact tie stays first.
    w.match(1, date=(2024, 9, 15), goals=(1, 0))
    assert w.build() == b'WORLD RESULT 15/09/2024: North FC 1-0 South FC | '
    w.match(2, date=(2024, 9, 15), goals=(0, 4))
    w.match(3, date=(2024, 9, 15), goals=(5, 1))
    assert w.build() == b'WORLD RESULT 15/09/2024: North FC 0-4 South FC | '
    for value, a in ((0, CLUB_COUNT), (652, CLUB_COUNT), (0xffffffff, CLUB_COUNT),
                     (0, COMP_COUNT), (301, COMP_COUNT)):
        old = u32(g, b + a)
        put(g, b + a, value)
        assert w.build() == b''
        put(g, b + a, old)
    for mode in (0, 18, 20, 39, 41, 69):
        put(g, w.menu + 0x20, mode)
        assert w.build() == b''
    put(g, w.menu + 0x20, 40)
    assert w.build()
    put(g, w.menu + 0x20, 19)
    for a, value in ((b + 0xec1408, 3), (w.owner + 0x30, 0), (MODE, 0), (MENU, 0)):
        old = u32(g, a)
        put(g, a, value)
        assert w.build() == b''
        put(g, a, old)
    for year, index in ((1999, 0), (2201, 0), (2024, 365), (2024, 65535)):
        w.today(year, index=index)
        assert w.build() == b''
    w.reset()
    w.match(date=(2024, 12, 31))
    w.today(2025, 1, 7)
    assert b'31/12/2024' in w.build()
    w.today(2025, 1, 8)
    assert not w.build()
    # Missing/ambiguous user ownership, empty, unterminated and tagged names fail closed.
    w.reset()
    w.match()
    for name in (b'', b'Bad\nName', b'<tag>', b'\x7f', b'x' * 70):
        w.club(1, 2, name)
        assert not w.build()
    w.club(1, 2, 'Atlético % FC'.encode())
    assert 'Atlético % FC'.encode() in w.build()
    put(g, b + CLUBS + 2 * CLUB_SIZE + 0x314, 1 << 7)
    assert not w.build()                # a secondary controlled team is not an AI club
    put(g, b + CLUBS + 2 * CLUB_SIZE + 0x314, 255 << 7)
    put(g, b + CLUBS + 0x314, 255 << 7)
    assert not w.build()
    put(g, b + CLUBS + 0x314, 0)
    put(g, b + CLUBS + CLUB_SIZE + 0x314, 0)
    assert not w.build()
    # Last physical entries, not just record 0: no final-batch overread.
    w.reset()
    put(g, b + CLUB_COUNT, 651)
    put(g, b + COMP_COUNT, 300)
    w.club(649, 100, b'Last North')
    w.club(650, 101, b'Last South')
    w.comp(299, 32000)
    w.match(8999, home=649, away=650, comp=32000)
    assert w.build() == b'WORLD RESULT 14/09/2024: Last North 3-1 Last South | '
    print('ok 2: factual selection, AI-only ownership, dates/New Year, table ends, invalid data and safe names')

    rng = random.Random(2017)
    for run in range(30):
        w.reset()
        for i in range(25):
            w.match(rng.randrange(COUNT), date=(2024, 9, rng.randint(5, 19)),
                    goals=(rng.randrange(7), rng.randrange(7)), played=rng.random() > .2,
                    home=rng.randrange(3), away=rng.randrange(3), comp=rng.choice((1001, 7)))
        assert w.build() == w.expected(), run
    # Validate the native-date parser separately, including all days of February 2000.
    cases = 0
    for y in (1999, 2000, 2024, 2100, 2200, 2201):
        for m in range(14):
            for d in range(33):
                raw = y | m << 16 | d << 24
                assert g.call(n.DATE, [], edx=raw) == scalar(y, m, d), (y, m, d)
                cases += 1
    print('ok 3: 30 seeded fixture worlds agree with the independent selector; %d date parser cases' % cases)


def native(w, ui):
    g = w.g
    w.reset()
    w.match()
    prefix = w.build()
    for count in (1, 2, 9, 12):
        ui.news(count)
        for ready in (True, False):
            ui.ready = ready
            baseline, rng, seed = ui.draw(False)
            actual, new_rng, new_seed = ui.draw()
            assert actual == [prefix + line for line in baseline]
            assert actual and all(line.count(b'WORLD RESULT') == 1 for line in actual)
            assert new_rng == rng == list(range(1, count + 1)) and new_seed == seed
    ui.ready = True
    ui.news(1)
    w.club(1, 2, b'N' * 69)
    w.club(2, 3, b'S' * 69)
    w.match(goals=(99, 98))
    assert ui.draw()[0][0].startswith(w.build())
    w.reset()
    w.match()
    ui.news(2)
    for _ in range(8):
        actual, _, _ = ui.draw()
        assert actual[0].count(b'WORLD RESULT') == 1 and actual[0].startswith(prefix)
    ui.format_error = True
    assert ui.draw()[0] == ui.draw(False)[0]
    ui.format_error = False
    # No native item means no forced entry, extra RNG draw, stop or popup.
    ui.news(0)
    assert ui.draw() == ([], [], struct.pack('<H', 4242))
    ui.news(1)
    w.today(2024, 9, 23)
    assert ui.draw() == ui.draw(False)
    w.today(2024, 9, 13)                # reload an earlier save: no future headline
    assert ui.draw() == ui.draw(False)
    w.reset()                         # same pointer/date/user, different career data: no cache
    w.club(1, 2, b'Other North')
    w.match(goals=(0, 0))
    actual, _, _ = ui.draw()
    assert actual[0].startswith(b'WORLD RESULT 14/09/2024: Other North 0-0 South FC | ')
    ui.news(0)
    assert not ui.active, ui.active
    print('ok 4: real native reader reaches UI with one prefix; redraw/reload isolation, owned strings freed, '
          'native headlines and exact shuffle/RNG seed unchanged')


def saves(w, ui):
    # Native ML load/save routines 03787a4c/03787e30 identify these table offsets.
    # Replay only the observed fields; the supplied clock is NOT a full game load.
    paths = sorted((HERE.parent / 'ML saves').rglob('ML00000013 (after)'))
    assert len(paths) == 2
    seen = []
    for path in paths:
        original_hash = hashlib.sha256(path.read_bytes()).digest()
        data = savefile.read(str(path))['data']
        w.reset()
        for disk, memory, count, stride in ((0x50, CLUBS, 651, CLUB_SIZE),
                                            (0x134fd8, COMPS, 300, COMP_SIZE),
                                            (0x220844, MATCHES, COUNT, STRIDE)):
            w.g.write(w.base + memory, data[disk:disk + count * stride])
        nc = sum(u32(w.g, w.base + CLUBS + i * CLUB_SIZE) != 0xffffffff for i in range(651))
        np = sum(w.g.read(w.base + COMPS + i * COMP_SIZE, 2) != b'\xff\xff' for i in range(300))
        put(w.g, w.base + CLUB_COUNT, nc)
        put(w.g, w.base + COMP_COUNT, np)
        # Use the latest completed match day as the explicit replay clock.
        dates = []
        for i in range(COUNT):
            r = w.g.read(w.base + MATCHES + i * STRIDE, 12)
            if struct.unpack_from('<H', r)[0] < COUNT and r[7] & 0x40:
                dates.append(struct.unpack_from('<HBB', r, 8))
        w.today(*max(dates))
        expected = w.expected()
        assert expected and w.build() == expected
        ui.news(1)
        actual, _, _ = ui.draw()
        assert actual[0].startswith(expected)
        assert hashlib.sha256(path.read_bytes()).digest() == original_hash
        seen.append(expected.decode('utf-8'))
    ui.news(0)
    assert not ui.active
    assert any('Clube do Remo 4-0 SC Corinthians Paulista' in s for s in seen), seen
    print('ok 5: two existing saves replay real club/competition/result tables through the native reader to UI:')
    for line in seen:
        print('  ' + line)


def main(exe):
    source = MODULE.read_text(encoding='utf-8')
    assert n.lua_block() in source, 'regenerate MLNews.lua with news_cave.py --lua'
    g = tm.Game(exe)
    assert g.read(n.CAVE, n.SIZE) == b'\0' * n.SIZE
    assert n.CAVE >= 0x03fc8900 and n.CAVE + n.SIZE <= 0x03fc9da0
    for slot, name in ((0x047d75cc, b'sprintf_s'), (0x047d7504, b'srand'), (0x047d779c, b'rand')):
        rva = struct.unpack_from('<I', g.exe, off(slot))[0]
        at = off(0x400000 + rva + 2)
        assert g.exe[at:at + 32].split(b'\0', 1)[0] == name
    probe = install_checks(g, source)
    g.mu.mem_protect(n.CAVE & ~0xfff, 0x2000, UC_PROT_READ | UC_PROT_EXEC)
    w = World(g)
    ui = NativeUI(g, w)
    lookup_modes(w, ui, probe)
    # Restore cold diagnostics after the explicit lookup-mode exercise.
    g.write(n.STATE, n.state())
    diagnostics(w, ui, probe)
    rules(w)
    native(w, ui)
    saves(w, ui)
    # Initialization order is covered more broadly by test_safety.py; exercise the
    # actual UI path as well with all existing ML modules present in this process.
    for name in ('MLCheck', 'MLMoney', 'MLYear', 'MLTransfers', 'MLSimMatch',
                 'MLTeamSpirit', 'MLSimToDate', 'MLGrowth'):
        lines, _, _ = tm.run(g, (HERE / (name + '.lua')).read_text(encoding='utf-8'))
        result = tm.results(lines)[0]
        assert result.startswith('RESULT: 6 of 6 as expected.' if name == 'MLCheck' else 'RESULT: installed'), (name, result)
    lookup_modes(w, ui, probe)
    native(w, ui)
    print('ok 6: indexed/sparse native ticker/RNG/ownership checks also pass with all nine ML modules installed')
    print('all ok (emulator only; the final UI is a stand-in, not a screenshot from PES)')


if __name__ == '__main__':
    main(sys.argv[1])
