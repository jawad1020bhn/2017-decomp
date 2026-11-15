#!/usr/bin/env python3
"""Does test_money.py notice faults? Planted faults for MLTransfers.lua.

    python3 planted_faults.py <PES2017.exe> routine [first byte, byte after the last [, 2: every second bit; 8: one bit of each byte]]
    python3 planted_faults.py <PES2017.exe> routine again <output of an earlier run> <part> <parts>
    python3 planted_faults.py <PES2017.exe> files [numbers of faults]

routine: every bit of the routine of MLTransfers.lua is flipped in turn in the emulator's
memory, after the two modules are in, and 1,800 cases of Harness.choose_cases are run: 500
with the settings of the files and 1,300 with five other sets of settings, whose tables are
put into the memory for it. Printed: the flips after which all cases still passed.
"again" runs those of an earlier run once more, with twice the cases.
files: one line of MLTransfers.lua or money_cave.py is changed in a copy of this folder and
the whole test is run there. It must fail every time.

Last run (version 2 of MLTransfers.lua): files, 92 of 92 noticed (about 100 minutes).
routine, one bit of each of the 1,345 bytes (`routine 0 1345 8`, about 70 minutes of
processor time): 1,283 noticed after the test was made stricter with what the first run
showed; the 62 others are in bitflips_v2.tsv and are sorted in README.md.
"""
import gc
import os
import random
import re
import shutil
import struct
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
FAULTS = (
    # MLTransfers.lua. The ceilings and the ratings in the wrong order, a place not written,
    # checks left out
    ('MLTransfers.lua', 'local v = CEILING and CEILING[10 - level] or 0', 'local v = CEILING and CEILING[level + 1] or 0'),
    ('MLTransfers.lua', 'RANGE_TOP[level + 1] or 255', 'RANGE_TOP[10 - level] or 255'),
    ('MLTransfers.lua', '    memory.write(SITE[2], new)\n', ''),
    ('MLTransfers.lua', 'if not (good and empty) then', 'if not good then'),
    ('MLTransfers.lua', 'for _, c in ipairs(CONTEXT) do\n        if not same(c[1], c[2], c[3]) then good = false end',
     'for _, c in ipairs(CONTEXT) do\n        if not same(c[1], c[2], c[3]) then good = true end'),
    # "no ceiling" written as 0, wrong limits of the amounts, the rating rule always on
    ('MLTransfers.lua', '(v == 0) and 0xffffffff or', '(v == 0) and 0 or'),
    ('MLTransfers.lua', 'clamp(amount(v), 100, 99990000)', 'clamp(amount(v), 100, 9999000)'),
    ('MLTransfers.lua', 'clamp(amount(v), 100, 99990000)', 'clamp(amount(v), 1000, 99990000)'),
    ('MLTransfers.lua', 'string.char((CEILING and CEILING_RATING) and RANGE_TOP', 'string.char(CEILING and RANGE_TOP'),
    ('MLTransfers.lua', '(v ~= 0 and (v < 0.01 or v > 9999))', '(v ~= 0 and (v < 0.01 or v > 99999))'),
    ('MLTransfers.lua', '(v ~= 0 and (v < 0.01 or v > 9999))', '(v ~= 0 and (v < 0.001 or v > 9999))'),
    # the memory: not read back, not written, a faulty setting let through, a wrong rating,
    # a wrong size, a wrong address
    ('MLTransfers.lua', 'if memory.read(CAVE, CAVE_SIZE) ~= memory_image then', 'if false then'),
    ('MLTransfers.lua', '    memory.write(CAVE, memory_image)\n', ''),
    ('MLTransfers.lua', 'if type(CEILING_RATING) ~= "boolean" then', 'if false then'),
    ('MLTransfers.lua', 'local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 86, 99 }',
     'local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 85, 99 }'),
    ('MLTransfers.lua', 'local RANGE_LOW = { 47, 51, 55, 59, 63, 67, 70, 73, 76, 83 }',
     'local RANGE_LOW = { 47, 51, 55, 59, 63, 67, 70, 73, 76, 82 }'),
    ('MLTransfers.lua', 'local CAVE_SIZE = 0x930', 'local CAVE_SIZE = 0x92c'),
    ('MLTransfers.lua', 'local CAVE = 0x047d4200 ', 'local CAVE = 0x047d41f8 '),
    # the numbers of the limit: the two discounts swapped, a negative number let through
    ('MLTransfers.lua', 'ceiling and round(CEILING_FREE) or 100, ceiling and round(CEILING_LISTED) or 100',
     'ceiling and round(CEILING_LISTED) or 100, ceiling and round(CEILING_FREE) or 100'),
    ('MLTransfers.lua', 'if not is_number(c[1], 0, c[3]) then', 'if type(c[1]) ~= "number" or c[1] > c[3] then'),
    # the selling side never switched on; the personas: half the spread, the strength without
    # its rounding, two numbers swapped, the groups in the wrong order, a short group filled
    # with its last name, scouting always on, the two places of the second search swapped,
    # two places and two numbers of a persona swapped, checks left out, the persona of a
    # named club one too low
    ('MLTransfers.lua', 'SELL_SIDE and 1 or 0, 0 }', '0, 0 }'),
    ('MLTransfers.lua', 'numbers[5], numbers[6] = 1000 - 10 * spread, 20 * spread', 'numbers[5], numbers[6] = 1000 - 10 * spread, 10 * spread'),
    ('MLTransfers.lua', 'round(STRENGTH[2] * 65536) + 32768', 'round(STRENGTH[2] * 65536)'),
    ('MLTransfers.lua', 'numbers[9], numbers[10], numbers[12] = WINTER_MONTH, round(SQUAD_NEED), #CLUBS',
     'numbers[9], numbers[10], numbers[12] = round(SQUAD_NEED), WINTER_MONTH, #CLUBS'),
    ('MLTransfers.lua', 'local group = PERSONA_GROUPS[10 - level]', 'local group = PERSONA_GROUPS[level + 1]'),
    ('MLTransfers.lua', 'group[k % #group + 1]', 'group[math.min(k + 1, #group)]'),
    ('MLTransfers.lua', '    if not SCOUTING then t[5] = string.char(255) end\n', ''),
    ('MLTransfers.lua', 'PLACE[a.second[1]], PLACE[a.second[2]], 0, 0)', 'PLACE[a.second[2]], PLACE[a.second[1]], 0, 0)'),
    ('MLTransfers.lua', 'local PLACE = { free = 0, listed = 1, clubs = 2 }', 'local PLACE = { free = 1, listed = 0, clubs = 2 }'),
    ('MLTransfers.lua', '{ "ambition", 0, 99 }, { "prestige", 0, 99 }', '{ "prestige", 0, 99 }, { "ambition", 0, 99 }'),
    ('MLTransfers.lua', 'if a.free + a.listed + a.clubs > 100 then', 'if false then'),
    ('MLTransfers.lua', 'if persona_number(a[1]) ~= i then', 'if false then'),
    ('MLTransfers.lua', '#CLUBS > MOST_CLUBS then', '#CLUBS > MOST_CLUBS + 1 then'),
    ('MLTransfers.lua', 'types[i] = string.char(persona_number(c[2]))', 'types[i] = string.char(persona_number(c[2]) - 1)'),
    ('MLTransfers.lua', 'if persona_number(c[2]) == nil then', 'if false then'),
    ('MLTransfers.lua', 'if CEILING == false and not SELL_SIDE and not PERSONA then', 'if CEILING == false then'),
    # the two files: MLTransfers.lua does not look for MLMoney.lua, looks at the wrong place,
    # does not compare the value routine, does not see that the place is changed already,
    # writes with WRITE = false
    ('MLTransfers.lua', 'local found = (mark ~= nil and string.sub(mark, 1, 3) == "MLM")', 'local found = (mark ~= nil)'),
    ('MLTransfers.lua', 'local MONEY_MARK = 0x047b065c', 'local MONEY_MARK = 0x047b0658'),
    ('MLTransfers.lua', 'if not same(c[1], c[2], c[3]) then money = false end', 'if not same(c[1], c[2], c[3]) then money = true end'),
    ('MLTransfers.lua', 'if there ~= nil and string.sub(hex(there), 1, 2) == "e8" and hex(there) ~= SITE[3] then', 'if false then'),
    ('MLTransfers.lua', '    if not WRITE then\n', '    if false then\n'),
    # money_cave.py, the model of the routine. The price: a rating equal to the top refused,
    # the rating rule in both searches, a value equal to the limit refused, the lowest list
    # searched too, the order of the ceilings, the place counted as written when it is off,
    # need without the second search and without the slot, a wrong divisor, the club left
    # out of the draw, the discount for status 2 only, the two discounts swapped
    ('money_cave.py', "if wide and seen > t.ceiling_top[level]:", "if wide and seen >= t.ceiling_top[level]:"),
    ('money_cave.py', "if wide and seen > t.ceiling_top[level]:", "if seen > t.ceiling_top[level]:"),
    ('money_cave.py', 'return price <= limit(', 'return price < limit('),
    ('money_cave.py', 'for overall in range(highest, lowest, -1):', 'for overall in range(highest, lowest - 1, -1):'),
    ('money_cave.py', 'if m else NO_CEILING for m in reversed(ceiling)]', 'if m else NO_CEILING for m in ceiling]'),
    ('money_cave.py', "'transfers': self.transfers}", "'transfers': True}"),
    ('money_cave.py', "need or wide, numbers, player['popularity'])", "need, numbers, player['popularity'])"),
    ('money_cave.py', "need or wide, numbers, player['popularity'])", "wide, numbers, player['popularity'])"),
    ('money_cave.py', '* stretch & M32, 25600), M32)', '* stretch & M32, 25500), M32)'),
    ('money_cave.py', "    both = key ^ club_key(buyer['id'])\n", "    both = key\n"),
    ('money_cave.py', 'where = 0 if status in (1, 2) else', 'where = 0 if status in (2,) else'),
    ('money_cave.py', 'price = price * (t.ceiling_free, t.ceiling_listed)[where] // 100',
     'price = price * (t.ceiling_listed, t.ceiling_free)[where] // 100'),
    # the selling side: 23 players are enough, band 7 may go, a club of level 8 lets go, the
    # three cases in which a buyer may take anybody each a step off, the rule also in the
    # first search, what a club keeps one percent off
    ('money_cave.py', "or seller['count'] <= POOL_KEEPS:", "or seller['count'] < POOL_KEEPS:"),
    ('money_cave.py', "if not wanted and (band >= 7 or seller['level'] >= 8):", "if not wanted and (band > 7 or seller['level'] >= 8):"),
    ('money_cave.py', "if not wanted and (band >= 7 or seller['level'] >= 8):", "if not wanted and (band >= 7 or seller['level'] > 8):"),
    ('money_cave.py', "(level >= 9 and search['band'] > 0)", "(level >= 8 and search['band'] > 0)"),
    ('money_cave.py', "(search['kind'] == 1 and level >= 8)", "(search['kind'] == 1 and level >= 9)"),
    ('money_cave.py', "(search['kind'] == 4 and level > band)", "(search['kind'] == 4 and level >= band)"),
    ('money_cave.py', "            if not search['first']:\n", "            if True:\n"),
    ('money_cave.py', "^ key ^ date, HASH_KEEPS) < keeps:", "^ key ^ date, HASH_KEEPS) <= keeps:"),
    ('money_cave.py', "^ key ^ date, HASH_KEEPS) < keeps:", "^ key, HASH_KEEPS) < keeps:"),
    # scouting, the player's say, need, the place a club looks in, winter, the ages, the fog,
    # ambition: each a step off or with a part left out
    ('money_cave.py', "if where != 1 and draw(both, HASH_KNOWS) >= g['knows']:", "if draw(both, HASH_KNOWS) >= g['knows']:"),
    ('money_cave.py', "if where != 1 and draw(both, HASH_KNOWS) >= g['knows']:", "if where != 1 and draw(both, HASH_KNOWS) > g['knows']:"),
    ('money_cave.py', "if player['rating'] > own + g['prestige']:", "if player['rating'] >= own + g['prestige']:"),
    ('money_cave.py', "need = bool(search['band']) or (buyer['count']", "need = (buyer['count']"),
    ('money_cave.py', "buyer['count'] < t.squad)", "buyer['count'] <= t.squad)"),
    ('money_cave.py', "else 2 if d < g['free'] + g['listed'] + g['clubs'] else None)", "else 2)"),
    ('money_cave.py', "month == t.winter and draw(turn, HASH_WINTER) >= g['winter']:", "month == t.winter and draw(turn, HASH_WINTER) > g['winter']:"),
    ('money_cave.py', "if not need and month == t.winter and draw(turn", "if not need and draw(turn"),
    ('money_cave.py', "if not need and month == t.winter and draw(turn", "if month == t.winter and draw(turn"),
    ('money_cave.py', "first = mine[THEN_1] if mine[THEN_1] != first else mine[THEN_2]", "first = mine[THEN_1]"),
    ('money_cave.py', "<= mine[AGE_TO] and draw(both, HASH_AGE) < g['strict']:", "<= mine[AGE_TO] and draw(both, HASH_AGE) <= g['strict']:"),
    ('money_cave.py', "not mine[AGE_FROM] <= player['age'] <= mine[AGE_TO]", "not mine[AGE_FROM] < player['age'] <= mine[AGE_TO]"),
    ('money_cave.py', "(2 * g['fog'] + 1) >> 8) - g['fog']", "(2 * g['fog']) >> 8) - g['fog']"),
    ('money_cave.py', "if not need and seen < own - g['ambition']:", "if not need and seen <= own - g['ambition']:"),
    ('money_cave.py', "if not need and seen < own - g['ambition']:", "if seen < own - g['ambition']:"),
    ('money_cave.py', "date = (year | month << 16) * HASH_A & M32", "date = year * HASH_A & M32"),
    ('money_cave.py', "    if not search['band'] and mine[THEN_1] != NO_CHANNELS:", "    if not search['band']:"),
    ('money_cave.py', "    if not search['band'] and mine[THEN_1] != NO_CHANNELS:", "    if not need and mine[THEN_1] != NO_CHANNELS:"),
    ('money_cave.py', "            if not need:\n                return False\n            first = mine[THEN_1]", "            return False"),
    ('money_cave.py', "    if not need and not mine[AGE_FROM] <= player['age']", "    if not mine[AGE_FROM] <= player['age']"),
    # the numbers of a persona in the limit left out; the spread from club to club left out;
    # the first entry for a club counts; another draw for the persona of a level; the
    # strength of the eleven not kept above the range; without its rounding
    ('money_cave.py', "x = muldiv(t.ceiling[level], g['wealth'], 100)", "x = t.ceiling[level]"),
    ('money_cave.py', "(muldiv(t.ceiling_need, g['panic'], 100) + 100) & M32", "(t.ceiling_need + 100) & M32"),
    ('money_cave.py', "stretch = muldiv(t.ceiling_stretch, g['premium'], 100)", "stretch = t.ceiling_stretch"),
    ('money_cave.py', "muldiv(x, popularity * g['fame'] & M32, 100000)", "0"),
    ('money_cave.py', "return record[i] * (t.persona_low + (h * t.persona_range >> 8)) // 1000", "return record[i]"),
    ('money_cave.py', "return named[-1] if named else", "return named[0] if named else"),
    ('money_cave.py', "[club_key(club) >> 29]", "[club_key(club) >> 28 & 7]"),
    ('money_cave.py', ">> 16, WINDOW_LOW[level], WINDOW_TOP[level])", ">> 16, 0, WINDOW_TOP[level])"),
    ('money_cave.py', "self.strength_b = int(clamp(base, 0, MAX_BASE) * 65536 + 0.5) + 32768", "self.strength_b = int(clamp(base, 0, MAX_BASE) * 65536 + 0.5)"),
    ('money_cave.py', "or not from_pick or not 0 <= level < LEVELS:", "or not from_pick or not 0 <= level <= LEVELS:"),
)


def routine(exe):
    sys.path.insert(0, HERE)
    import capstone
    import money_cave as mc
    import test_money as tm
    source = tm.two_modules()
    t = tm.settings(source)

    h = None

    def fresh():
        nonlocal h
        h = None                                             # the old one first: each holds the whole exe
        gc.collect()
        h = tm.Harness(exe)
        tm.run(h.g, source)
    fresh()

    def changed(*pairs):
        text = source
        for name, new in pairs:
            text = tm.setting(text, name, new)
        return tm.settings(text)
    # the settings of the files and five other sets, each with its number of cases: the selling
    # side alone, the ceiling alone (version 1), made-up personas for made-up clubs without the
    # selling side, the file's personas without scouting and the ceiling, with other numbers,
    # the made-up personas with the highest ceilings (amounts that do not fit 32 bits)
    random.seed(5)
    kinds = tm.some_archetypes(15)
    groups = '{\n%s\n}' % '\n'.join('    { %s },' % ', '.join('"P%d"' % random.randint(1, 15) for _ in range(random.randint(1, 8)))
                                    for _ in range(10))
    named = '{\n%s\n}' % '\n'.join('    { 0x%08x, "P%d" },' % (random.getrandbits(18) << 14 | random.randint(1, mc.POOL_CLUBS - 1),
                                                               random.randint(1, 15)) for _ in range(96))
    sets = ((t, 500),
            (changed(('CEILING', 'false'), ('PERSONA', 'false')), 300),
            (changed(('SELL_SIDE', 'false'), ('PERSONA', 'false')), 200),
            (changed(('SELL_SIDE', 'false'), ('ARCHETYPES', tm.archetypes_text(kinds)),
                     ('PERSONA_GROUPS', groups), ('CLUBS', named), ('PERSONA_SPREAD', '50')), 400),
            (changed(('CEILING', 'false'), ('SCOUTING', 'false'), ('STRENGTH', '{ 0.02, 40 }'), ('SQUAD_NEED', '32'),
                     ('WINTER_MONTH', '12'), ('PERSONA_SPREAD', '0')), 200),
            (changed(('CEILING', '{ %s }' % ', '.join(['9999'] * 10)), ('CEILING_STRETCH', '300'), ('CEILING_NEED', '300'),
                     ('ARCHETYPES', tm.archetypes_text(kinds)), ('PERSONA_GROUPS', groups), ('CLUBS', named)), 200))
    tables = [mc.image_2(u)[:mc.CEILING_CODE - mc.CAVE_2] for u, _ in sets]
    random.seed(1)
    print('without a fault: %d of 400 lists changed by the module, %d players refused' % h.choose_cases(400, t))
    good = h.g.read(mc.CEILING_CODE, len(mc.CEILING_BYTES))
    text = {}
    for i in capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm(mc.CEILING_BYTES, mc.CEILING_CODE):
        for k in range(i.size):
            text[i.address + k - mc.CEILING_CODE] = '%s %s' % (i.mnemonic, i.op_str)

    def flip(k, bit):
        """-> did the cases pass with this bit flipped? (bit None: with nothing flipped)"""
        tm.poke(h.g, mc.CEILING_CODE + k, bytes([good[k] ^ (1 << bit if bit is not None else 0)]))
        random.seed(7)
        try:
            for (u, n), table in zip(sets, tables):
                tm.poke(h.g, mc.CAVE_2, table)
                h.choose_cases(n, u)
            return True
        except BaseException:                                # a failed case or a fault of the emulated processor
            return False
        finally:
            tm.poke(h.g, mc.CEILING_CODE + k, bytes([good[k]]))
            tm.poke(h.g, mc.CAVE_2, tables[0])

    def sound():
        """the harness after a fault: the routine as it should be passes again"""
        random.seed(3)
        try:
            h.choose_cases(60, t)
            return True
        except BaseException:
            return False
    assert flip(0, None), 'the cases fail without a fault'
    missed, rebuilt = [], 0
    if sys.argv[3:4] == ['again']:                           # the flips an earlier run printed as not noticed, with twice the cases
        again = {}
        for line in open(sys.argv[4]):
            found = re.match(r'  not noticed: byte (\d+) \S+ bit (\d)', line)
            if found:
                again.setdefault(int(found.group(1)), []).append(int(found.group(2)))
        part, parts = int(sys.argv[5]), int(sys.argv[6])
        again = {k: again[k] for k in sorted(again)[part::parts]}
        sets = tuple((u, 2 * n) for u, n in sets)
        first, last, step = 0, len(good), 1
    else:
        again = None
        first, last = (int(a) for a in sys.argv[3:5]) if sys.argv[3:] else (0, len(good))
        step = int(sys.argv[5]) if sys.argv[5:] else 1       # 2: every second bit (bits 0, 2, 4, 6 and 1, 3, 5, 7 in turn); 8: one bit of a byte
    count = 0
    for k in range(first, min(last, len(good))):
        bits = range(k % step, 8, step) if again is None else again.get(k, [])
        if not bits:
            continue
        count += len(bits)
        passed = [bit for bit in bits if flip(k, bit)]
        if not sound():                                      # a fault wrote somewhere else: the byte again, one bit at a time
            passed = []
            for bit in bits:
                fresh()
                rebuilt += 1
                if flip(k, bit):
                    passed.append(bit)
            fresh()
        for bit in passed:
            missed.append((k, bit))
            print('  not noticed: byte %d (+0x%x), bit %d: %s' % (k, k, bit, text[k]), flush=True)
        if k % 100 == 99:
            print('  ... byte %d, %d not noticed so far, the harness built anew %d times' % (k + 1, len(missed), rebuilt), flush=True)
    print('bytes %d to %d: %d faults, %d noticed, %d not noticed' % (first, min(last, len(good)) - 1, count, count - len(missed), len(missed)))


def files(exe, which):
    root = tempfile.mkdtemp()

    def one(i):
        name, old, new = FAULTS[i]
        d = os.path.join(root, str(i))
        for sub in ('sider', 'tools'):
            shutil.copytree(os.path.join(HERE, '..', sub), os.path.join(d, sub), ignore=shutil.ignore_patterns('__pycache__'))
        path = os.path.join(d, 'sider', name)
        s = open(path, encoding='utf-8').read()
        assert s.count(old) == 1, (i, s.count(old))
        open(path, 'w', encoding='utf-8').write(s.replace(old, new))
        r = subprocess.run([sys.executable, 'test_money.py', exe], cwd=os.path.join(d, 'sider'), capture_output=True, text=True)
        return i, r.returncode, (r.stderr.strip().splitlines() or [''])[-1][:100]
    noticed = 0
    with ThreadPoolExecutor(2) as pool:
        for i, code, last in pool.map(one, which or range(len(FAULTS))):
            noticed += code != 0
            print('%2d %-13s %-11s %s | %s' % (i, FAULTS[i][0], 'noticed' if code else 'NOT NOTICED',
                                               FAULTS[i][2][:60].replace('\n', ' '), last), flush=True)
    print('%d of %d noticed' % (noticed, len(which or FAULTS)))
    shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[2] not in ('routine', 'files'):
        sys.exit(__doc__)
    if sys.argv[2] == 'routine':
        routine(os.path.abspath(sys.argv[1]))
    else:
        files(os.path.abspath(sys.argv[1]), [int(a) for a in sys.argv[3:]])
