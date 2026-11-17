#!/usr/bin/env python3
"""Does test_money.py notice faults? Planted faults for MLTransfers.lua.

    python3 planted_faults.py <PES2017.exe> routine [first byte, byte after the last [, 2: every second bit; 8: one bit of each byte]]
    python3 planted_faults.py <PES2017.exe> routine again <output of an earlier run> <part> <parts>
    python3 planted_faults.py <PES2017.exe> pressure [first byte, byte after the last]
    python3 planted_faults.py <PES2017.exe> files [numbers of faults]

routine: every bit of the routine of MLTransfers.lua is flipped in turn in the emulator's
memory, after the two modules are in, and 2,000 cases of Harness.choose_cases are run: 500
with the settings of the files and 1,500 with six other sets of settings, whose tables are
put into the memory for it. Printed: the flips after which all cases still passed.
"again" runs those of an earlier run once more, with twice the cases.
pressure: the same for the routine of SQUAD_PRESSURE (version 9), which is not a part of
that routine: every bit flipped in turn, then 1,500 cases of Harness.pressure_cases with
each of three sets of limits and drop.
files: one line of MLTransfers.lua or money_cave.py is changed in a copy of this folder and
test_need.py and then the whole of test_money.py are run there. One of them must fail every time.

Last runs. Version 9 of MLTransfers.lua (squad pressure), files: the list has 165; the
12 new ones (153 to 164) were run, all noticed; the other 153 were not run, and 14 of
them (27 35 36 55 56 57 65 78 88 128 129 130 140 142) no longer find their line since
versions 7 and 8 and were not repaired. pressure (`pressure 0 89`, `pressure 89 178`;
run with the routine at 0x047d6e68, before it moved to 0x047d6c68 with the same
source): 1,374 of 1,424 noticed. Of the 50 others, 43 are
the same in effect for the numbers the routine can meet (a byte for a dword compare of
numbers below 256, a shift count the processor masks, `sub` for `cmp` where the register
is dead, a jump into the same end by another way); six change the address of the game's
"no player" id to a place whose second half is zero too, which the cases cannot tell
apart (the address is the one the game's own goalkeeper count uses, and test_money.py
compares the written routine with the bytes kept in money_cave.py); one (the first `ret`
as `jecxz`) differs only if ecx is 0 when the count ends, which no case has. The first
run of all bits found two things the test did not cover (a `keeps` above 255 and a
squad of more than 31 entries); test_money.py was changed for them. routine: not run
for version 9; of its 1,559 bytes three instructions changed (`push; pop` for a `mov`
twice, and the call of the new routine for the compare).
Version 6 of MLTransfers.lua (the position need), files: the list has 153; the
16 new ones (137 to 152) and the six whose text changed (2 11 35 36 53 60) were run, all
noticed; the other 131 were not run. routine: not run; the routine is version 4's byte
for byte, and the two new routines of the position need are not in it (test_need.py runs
them; no bit flips were made on them).
Version 4 of MLTransfers.lua (routine 1,555 bytes), files: the list has 137; the
13 new ones and the seven whose text changed were run (76 77 86 111 112 118 119 124 to
136), all noticed; the other 117 were not run. routine: only the two new pieces, every bit
(`routine 633 650 1`, `routine 986 1007 1`): 291 of 304 noticed, the 13 others are in
bitflips_v4.tsv and are the same in effect. Two flips that are faults passed the first
runs (popularity "above" for "at or above", the draw x 101); test_money.py was changed
for them. The other 1,517 bytes of the routine were not flipped for version 4.
Version 3, files: the list has 124; the 18 new ones and the six
whose text changed with version 3 were run (numbers 16 76 77 86 87 95 106 to 123). Two were
not noticed: one was no fault and was replaced, the other (number 86, the age draw equal to
`strict`) is why test_money.py now puts one player in four on a limit; with that both are
noticed, and so are five others that were run again. The other 100 were not run on version 3.
routine, one bit of each of the 1,520 bytes (`routine 0 1520 8`, about two hours of
processor time, then `routine again` for the 77 flips not noticed): 1,456 noticed; the 64
others are in bitflips_v3.tsv and are sorted in README.md. That run had 1,800 cases and
five other sets, and AGE_SHIFT = 5 in the set with SQUAD_NEED = 32, where nearly every club
is in need and no age is asked. Two flips that are faults passed it (age shift, winter
draw); test_money.py was changed for them and the set with the ages alone was added here.
After that only those two pieces of code were run again, all eight bits (`routine 895 953
1`, `routine 829 857 1`): what is still not noticed there is the same in effect.
Version 2: files 92 of 92 before the rivals were added, then 22 of 22 (the 14 for the
rivals and eight others); routine 1,354 of 1,413, the 59 others are in bitflips_v2.tsv.
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
    ('MLTransfers.lua', '        memory.write(site[2], new)\n', ''),
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
    ('MLTransfers.lua', 'local written = (memory.read(CAVE, CAVE_SIZE) == memory_image)', 'local written = true'),
    ('MLTransfers.lua', '    memory.write(CAVE, memory_image)\n', ''),
    ('MLTransfers.lua', 'if type(CEILING_RATING) ~= "boolean" then', 'if false then'),
    ('MLTransfers.lua', 'local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 86, 99 }',
     'local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 85, 99 }'),
    ('MLTransfers.lua', 'local RANGE_LOW = { 47, 51, 55, 59, 63, 67, 70, 73, 76, 83 }',
     'local RANGE_LOW = { 47, 51, 55, 59, 63, 67, 70, 73, 76, 82 }'),
    ('MLTransfers.lua', 'local CAVE_SIZE = 0xe00', 'local CAVE_SIZE = 0xdfc'),
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
    ('MLTransfers.lua', 'if CEILING == false and not SELL_SIDE and not PERSONA and not NEED and #RIVALS == 0 then',
     'if CEILING == false and not NEED and #RIVALS == 0 then'),
    # the rivals: the part alone writes nothing, the last pair is left out, the table one dword
    # too high, one pair too many let through, a club that is its own rival, three clubs in a
    # pair or a faulty RIVALS let through, not named in the RESULT line
    ('MLTransfers.lua', 'if CEILING == false and not SELL_SIDE and not PERSONA and not NEED and #RIVALS == 0 then',
     'if CEILING == false and not SELL_SIDE and not PERSONA and not NEED then'),
    ('MLTransfers.lua', '.. u32(#RIVALS)\n', '.. u32(#RIVALS - 1)\n'),
    ('MLTransfers.lua', 'local RIVALS_AT = 0x5c8', 'local RIVALS_AT = 0x5cc'),
    ('MLTransfers.lua', '#RIVALS > MOST_RIVALS then', '#RIVALS > MOST_RIVALS + 1 then'),
    ('MLTransfers.lua', '\n            or pair[1] == pair[2] then', ' then'),
    ('MLTransfers.lua', 'if type(pair) ~= "table" or #pair ~= 2 or', 'if type(pair) ~= "table" or'),
    ('MLTransfers.lua', 'not is_club_id(pair[1]) or not is_club_id(pair[2])', 'not is_club_id(pair[1])'),
    ('MLTransfers.lua', 'return ceiling_fault() or persona_fault() or rivals_fault()', 'return ceiling_fault() or persona_fault()'),
    ('MLTransfers.lua', 'changed[#changed + 1] = "rivals"', 'changed[#changed + 1] = "rival"'),
    # the same in the model: listed players left out, players without a contract taken in, one
    # direction only, the part alone not counted as on
    ('money_cave.py', "if where != 0 and seller is not None and ((buyer['id'], seller['id']) in t.rivals",
     "if where == 2 and seller is not None and ((buyer['id'], seller['id']) in t.rivals"),
    ('money_cave.py', "if where != 0 and seller is not None and ((buyer['id'], seller['id']) in t.rivals",
     "if seller is not None and ((buyer['id'], seller['id']) in t.rivals"),
    ('money_cave.py', "or (seller['id'], buyer['id']) in t.rivals):", "):"),
    ('money_cave.py', "if where != 0 and seller is not None and ((buyer['id'], seller['id']) in t.rivals",
     "if where != 0 and seller is not None and ((seller['id'], seller['id']) in t.rivals"),
    ('money_cave.py', 'self.has_ceiling or self.sell or self.has_persona or bool(self.rivals)', 'self.has_ceiling or self.sell or self.has_persona'),
    # the two files: MLTransfers.lua does not look for MLMoney.lua, looks at the wrong place,
    # does not compare the value routine, does not see that the place is changed already,
    # writes with WRITE = false
    ('MLTransfers.lua', 'local found = (mark ~= nil and string.sub(mark, 1, 3) == "MLM")', 'local found = (mark ~= nil)'),
    ('MLTransfers.lua', 'local MONEY_MARK = 0x047b065c', 'local MONEY_MARK = 0x047b0658'),
    ('MLTransfers.lua', 'if not same(c[1], c[2], c[3]) then money = false end', 'if not same(c[1], c[2], c[3]) then money = true end'),
    ('MLTransfers.lua', 'if there ~= nil and string.sub(hex(there), 1, 2) == "e8" and hex(there) ~= site[3] then', 'if false then'),
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
    ('money_cave.py', "'transfers': self.transfers, 'need plan'", "'transfers': True, 'need plan'"),
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
    ('money_cave.py', "if (where != 1 and player['rating'] < t.known and player['popularity']", "if (player['rating'] < t.known and player['popularity']"),
    ('money_cave.py', "            and draw(both, HASH_KNOWS) >= g['knows']):", "            and draw(both, HASH_KNOWS) > g['knows']):"),
    ('money_cave.py', "if player['rating'] > own + g['prestige']:", "if player['rating'] >= own + g['prestige']:"),
    ('money_cave.py', "need = bool(search['band']) or (buyer['count']", "need = (buyer['count']"),
    ('money_cave.py', "buyer['count'] < t.squad)", "buyer['count'] <= t.squad)"),
    ('money_cave.py', "else 2 if d < g['free'] + g['listed'] + g['clubs'] else None)", "else 2)"),
    ('money_cave.py', "month == t.winter and draw(turn, HASH_WINTER) >= g['winter']:", "month == t.winter and draw(turn, HASH_WINTER) > g['winter']:"),
    ('money_cave.py', "if not need and month == t.winter and draw(turn", "if not need and draw(turn"),
    ('money_cave.py', "if not need and month == t.winter and draw(turn", "if month == t.winter and draw(turn"),
    ('money_cave.py', "first = mine[THEN_1] if mine[THEN_1] != first else mine[THEN_2]", "first = mine[THEN_1]"),
    ('money_cave.py', "            and draw(both, HASH_AGE) * 100 < strict):", "            and draw(both, HASH_AGE) * 100 <= strict):"),
    ('money_cave.py', "not mine[AGE_FROM] <= player['age'] - age_shift(", "not mine[AGE_FROM] < player['age'] - age_shift("),
    ('money_cave.py', "(2 * g['fog'] + 1) >> 8) - g['fog']", "(2 * g['fog']) >> 8) - g['fog']"),
    ('money_cave.py', "if not need and seen < own - g['ambition']:", "if not need and seen <= own - g['ambition']:"),
    ('money_cave.py', "if not need and seen < own - g['ambition']:", "if seen < own - g['ambition']:"),
    ('money_cave.py', "date = (year | month << 16) * HASH_A & M32", "date = year * HASH_A & M32"),
    ('money_cave.py', "    if not search['band'] and mine[THEN_1] != NO_CHANNELS:", "    if not search['band']:"),
    ('money_cave.py', "    if not search['band'] and mine[THEN_1] != NO_CHANNELS:", "    if not need and mine[THEN_1] != NO_CHANNELS:"),
    ('money_cave.py', "            if not need:\n                return False\n            first = mine[THEN_1]", "            return False"),
    ('money_cave.py', "    if (not need and not mine[AGE_FROM] <= player['age']", "    if (not mine[AGE_FROM] <= player['age']"),
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
    # version 3. The first team: the line one point off, kept against a bigger club too, the
    # bigger club one point off, measured from the buyer's eleven, the step left out; the star:
    # one point off, listed players not known; the ages moved the other way, by half, not at all
    ('money_cave.py', "and player['rating'] + t.keep_from > his:", "and player['rating'] + t.keep_from > his + 1:"),
    ('money_cave.py', "if own - his < t.keep_bigger and player['rating']", "if player['rating']"),
    ('money_cave.py', "if own - his < t.keep_bigger and player['rating']", "if own - his <= t.keep_bigger and player['rating']"),
    ('money_cave.py', "keeps += (player['rating'] + t.keep_from - his) * t.keep_step", "keeps += (player['rating'] + t.keep_from - own) * t.keep_step"),
    ('money_cave.py', "keeps += (player['rating'] + t.keep_from - his) * t.keep_step", "keeps += t.keep_step"),
    ('money_cave.py', "if (where != 1 and player['rating'] < t.known and player['popularity']", "if (where != 1 and player['rating'] <= t.known and player['popularity']"),
    ('money_cave.py', "if (where != 1 and player['rating'] < t.known and player['popularity']", "if (where != 1 and player['popularity']"),
    ('money_cave.py', "<= player['age'] - age_shift(t, buyer['id']) <=", "<= player['age'] + age_shift(t, buyer['id']) <="),
    ('money_cave.py', "<= player['age'] - age_shift(t, buyer['id']) <=", "<= player['age'] <="),
    ('money_cave.py', "* (2 * t.age_shift + 1) >> 8) - t.age_shift", "* (2 * t.age_shift) >> 8) - t.age_shift"),
    ('money_cave.py', "return (high_byte(club_key(club), HASH_SHIFT)", "return (high_byte(club, HASH_SHIFT)"),
    # the same in MLTransfers.lua: the five numbers in another order, one place too low, not
    # written with PERSONA, a faulty one let through, the duplicate note left out
    ('MLTransfers.lua', 'round(KEEP_BEST[1]), round(KEEP_BEST[2]), round(KEEP_BEST[3]), round(KNOWN_FROM),\n',
     'round(KEEP_BEST[2]), round(KEEP_BEST[1]), round(KEEP_BEST[3]), round(KNOWN_FROM),\n'),
    ('MLTransfers.lua', 'local LAST_AT = 0xde4', 'local LAST_AT = 0xde0'),
    ('MLTransfers.lua', 'round(AGE_SHIFT) } or { 0, 0, 0, 0, 0, 0, 0 }', 'round(KNOWN_FROM) } or { 0, 0, 0, 0, 0, 0, 0 }'),
    ('MLTransfers.lua', 'if not is_number(KNOWN_FROM, 0, 100) then', 'if false then'),
    ('MLTransfers.lua', 'if not is_number(AGE_SHIFT, 0, 5) then', 'if not is_number(AGE_SHIFT, 0, 6) then'),
    ('MLTransfers.lua', 'or not is_number(KEEP_BEST[2], 0, 100)', 'or not is_number(KEEP_BEST[2], 0, 101)'),
    ('MLTransfers.lua', 'if seen[c[1]] then twice = twice + 1 end', 'if seen[c[1]] then twice = 0 end'),
    # version 4. The famous player: one point off, not asked, asked of listed players only; the
    # number written without its limit, a bit too low; the ages of a player without a contract:
    # as for every other player, for listed players too, for all, the draw one off, the draw
    # times 101 (a flipped bit of the routine does that; it shows with STRICT_FREE = 99 only)
    ('money_cave.py', "and player['popularity'] < t.known_fame\n", "and player['popularity'] <= t.known_fame\n"),
    ('money_cave.py', " and player['popularity'] < t.known_fame\n", "\n"),
    ('money_cave.py', "d + struct.pack('<7I', min(t.known_fame << 20, M32),", "d + struct.pack('<7I', t.known_fame << 20 & M32,"),
    ('money_cave.py', "d + struct.pack('<7I', min(t.known_fame << 20, M32),", "d + struct.pack('<7I', min(t.known_fame << 19, M32),"),
    ('money_cave.py', "strict = g['strict'] * (t.strict_free if where == 0 else 100)", "strict = g['strict'] * 100"),
    ('money_cave.py', "strict = g['strict'] * (t.strict_free if where == 0 else 100)", "strict = g['strict'] * (t.strict_free if where != 2 else 100)"),
    ('money_cave.py', "strict = g['strict'] * (t.strict_free if where == 0 else 100)", "strict = g['strict'] * t.strict_free"),
    ('money_cave.py', "            and draw(both, HASH_AGE) * 100 < strict):", "            and draw(both, HASH_AGE) * 100 < strict - 100):"),
    ('money_cave.py', "            and draw(both, HASH_AGE) * 100 < strict):", "            and draw(both, HASH_AGE) * 101 < strict):"),
    # the same in MLTransfers.lua: "off" written as 0, the two numbers in the other order, a
    # faulty one let through
    ('MLTransfers.lua', 'fame < 4096 and fame * 0x100000 or 0xffffffff, round(STRICT_FREE),', 'fame * 0x100000, round(STRICT_FREE),'),
    ('MLTransfers.lua', 'fame < 4096 and fame * 0x100000 or 0xffffffff, round(STRICT_FREE),', 'round(STRICT_FREE), fame < 4096 and fame * 0x100000 or 0xffffffff,'),
    ('MLTransfers.lua', 'if not is_number(KNOWN_FAME, 0, 4096) then', 'if not is_number(KNOWN_FAME, 0, 4097) then'),
    ('MLTransfers.lua', 'if not is_number(STRICT_FREE, 0, 100) then', 'if false then'),
    # version 6, the position need. MLTransfers.lua: the two numbers in the other order, the
    # second not one less, its memory not written, not looked at before, its places written
    # with NEED off, NEED alone taken for nothing to do, a faulty number let through
    ('MLTransfers.lua', 'u32(round(NEED_GAP)) .. u32(round(NEED_BETTER) - 1)', 'u32(round(NEED_BETTER) - 1) .. u32(round(NEED_GAP))'),
    ('MLTransfers.lua', 'u32(round(NEED_GAP)) .. u32(round(NEED_BETTER) - 1)', 'u32(round(NEED_GAP)) .. u32(round(NEED_BETTER))'),
    ('MLTransfers.lua', '    if written and NEED then\n', '    if false then\n'),
    ('MLTransfers.lua', '        empty = empty and free\n', ''),
    ('MLTransfers.lua', '    local sites = { SITE }\n    if NEED then\n', '    local sites = { SITE }\n    if true then\n'),
    ('MLTransfers.lua', 'if CEILING == false and not SELL_SIDE and not PERSONA and not NEED and #RIVALS == 0 then',
     'if CEILING == false and not SELL_SIDE and not PERSONA and #RIVALS == 0 then'),
    ('MLTransfers.lua', 'if not is_number(NEED_GAP, 1, 30) then', 'if not is_number(NEED_GAP, 0, 30) then'),
    ('MLTransfers.lua', 'if not is_number(NEED_BETTER, 1, 20) then', 'if not is_number(NEED_BETTER, 1, 21) then'),
    # money_cave.py, the model: the gap a point off, the last of equals, a second slot for a
    # position the club looks for already, a plan of kind 2, the goalkeeper left out, the
    # starter himself good enough, the search raised for every position, lowered
    ('money_cave.py', '< (len(have) - 1) * (rating + t.need_gap):', '<= (len(have) - 1) * (rating + t.need_gap):'),
    ('money_cave.py', "rating, position = min(have, key=lambda e: e[0])", "rating, position = min(reversed(have), key=lambda e: e[0])"),
    ('money_cave.py', 'if position in slots or NO_POSITION not in slots:', 'if NO_POSITION not in slots:'),
    ('money_cave.py', 'or not t.need or kind > 1 or len(eleven) < ELEVEN', 'or not t.need or kind > 2 or len(eleven) < ELEVEN'),
    ('money_cave.py', 'have = [e for e in eleven[:ELEVEN] if e is not None]', 'have = [e for e in eleven[:ELEVEN] if e is not None and e[1]]'),
    ('money_cave.py', 'position, min(rating + t.need_more, 99)', 'position, min(rating + t.need_more + 1, 99)'),
    ('money_cave.py', 'return max(lowest, mark[1]) if mark[0] == position + 1 else lowest', 'return max(lowest, mark[1]) if mark[0] else lowest'),
    ('money_cave.py', 'return max(lowest, mark[1]) if mark[0] == position + 1 else lowest', 'return mark[1] if mark[0] == position + 1 else lowest'),
    # version 9, SQUAD_PRESSURE. MLTransfers.lua: two limits in the other order, a position
    # in another group, drop and limits cut off instead of rounded, the drop written without
    # PERSONA, its memory not written, not looked at before, faulty numbers let through.
    # money_cave.py, the model: "at the limit" for "above", the drop a point off, the second
    # striker a midfielder (model and memory together; then the Lua file no longer agrees)
    ('MLTransfers.lua', 'local PRESSURE_GROUPS = { "GK", "DF", "MF", "FW" }', 'local PRESSURE_GROUPS = { "GK", "MF", "DF", "FW" }'),
    ('MLTransfers.lua', 'local GROUP_OF = "00010101020202020203030303"', 'local GROUP_OF = "00010101020202020202030303"'),
    ('MLTransfers.lua', 'local out = u32(on and round(on.keeps_drop) or 0)', 'local out = u32(on and math.floor(on.keeps_drop) or 0)'),
    ('MLTransfers.lua', 'string.char(on and round(on.positions[name]) or 0)', 'string.char(on and math.floor(on.positions[name]) or 0)'),
    ('MLTransfers.lua', 'local on = PERSONA and SQUAD_PRESSURE', 'local on = SQUAD_PRESSURE'),
    ('MLTransfers.lua', '    if written then\n        memory.write(PRESSURE_CAVE, pressure_memory)', '    if false then\n        memory.write(PRESSURE_CAVE, pressure_memory)'),
    ('MLTransfers.lua', '    empty = empty and spare\n', ''),
    ('MLTransfers.lua', 'if not is_number(p.positions[name], 0, 99) then return fault end', 'if not is_number(p.positions[name], 0, 100) then return fault end'),
    ('MLTransfers.lua', 'or not is_number(p.keeps_drop, 0, 100) then', 'or not is_number(p.keeps_drop, 0, 101) then'),
    ('money_cave.py', 'if groups[group] > t.pressure_limits[group]:', 'if groups[group] >= t.pressure_limits[group]:'),
    ('money_cave.py', 'return max(0, keeps - t.pressure_drop)', 'return max(0, keeps - t.pressure_drop - 1)'),
    ('money_cave.py', 'GROUP_OF = (0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3)', 'GROUP_OF = (0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 2, 3)'),
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
    # the settings of the files and six other sets, each with its number of cases: personas
    # that refuse for the age alone (second, because it is quick to notice a fault), the selling
    # side alone, the ceiling alone (version 1, no rivals), made-up personas for made-up clubs
    # without the selling side and with 64 pairs of rivals among 12 clubs, the file's personas
    # without scouting and the ceiling, with other numbers, the made-up personas with the
    # highest ceilings (amounts that do not fit 32 bits) and 64 pairs of rivals among 128 clubs
    random.seed(5)
    kinds = tm.some_archetypes(15)
    groups = '{\n%s\n}' % '\n'.join('    { %s },' % ', '.join('"P%d"' % random.randint(1, 15) for _ in range(random.randint(1, 8)))
                                    for _ in range(10))
    named = '{\n%s\n}' % '\n'.join('    { 0x%08x, "P%d" },' % (random.getrandbits(18) << 14 | random.randint(1, mc.POOL_CLUBS - 1),
                                                               random.randint(1, 15)) for _ in range(192))
    def some_rivals(clubs):
        ids = [random.getrandbits(18) << 14 | c for c in random.sample(range(1, mc.POOL_CLUBS), clubs)]
        return '{\n%s\n}' % '\n'.join('    { 0x%08x, 0x%08x },' % tuple(random.sample(ids, 2) if clubs < 128 else ids[2 * k:2 * k + 2])
                                        for k in range(64))
    dense, wide = some_rivals(12), some_rivals(128)
    sets = ((t, 500),
            (changed(('CEILING', 'false'), ('SELL_SIDE', 'false'), ('RIVALS', '{ }'), *tm.ages_alone(5)), 200),
            (changed(('CEILING', 'false'), ('PERSONA', 'false')), 300),
            (changed(('SELL_SIDE', 'false'), ('PERSONA', 'false'), ('RIVALS', '{ }')), 200),
            (changed(('SELL_SIDE', 'false'), ('ARCHETYPES', tm.archetypes_text(kinds)),
                     ('PERSONA_GROUPS', groups), ('CLUBS', named), ('PERSONA_SPREAD', '50'), ('RIVALS', dense),
                     ('KEEP_BEST', '{ 0, 100, 99 }'), ('KNOWN_FROM', '100'), ('AGE_SHIFT', '0'), ('KNOWN_FAME', '1000'),
                     ('STRICT_FREE', '99')), 400),
            (changed(('CEILING', 'false'), ('SCOUTING', 'false'), ('STRENGTH', '{ 0.02, 40 }'), ('SQUAD_NEED', '32'),
                     ('WINTER_MONTH', '12'), ('PERSONA_SPREAD', '0'), ('KEEP_BEST', '{ 10, 3, 0 }'), ('KNOWN_FROM', '60')), 200),
            (changed(('CEILING', '{ %s }' % ', '.join(['9999'] * 10)), ('CEILING_STRETCH', '300'), ('CEILING_NEED', '300'),
                     ('ARCHETYPES', tm.archetypes_text(kinds)), ('PERSONA_GROUPS', groups), ('CLUBS', named), ('RIVALS', wide), ('AGE_SHIFT', '5')), 200))
    tables = [mc.image_2(u)[:mc.CEILING_CODE - mc.CAVE_2] for u, _ in sets]
    ends = [mc.image_2(u)[mc.FAME_KNOWN_AT - mc.CAVE_2:] for u, _ in sets]    # the seven numbers behind the routine
    fifth = [mc.image_5(u) for u, _ in sets]                                # the memory of SQUAD_PRESSURE
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
            for (u, n), table, numbers, five in zip(sets, tables, ends, fifth):
                tm.poke(h.g, mc.CAVE_2, table)
                tm.poke(h.g, mc.FAME_KNOWN_AT, numbers)
                tm.poke(h.g, mc.CAVE_5, five)
                h.choose_cases(n, u)
            return True
        except BaseException:                                # a failed case or a fault of the emulated processor
            return False
        finally:
            tm.poke(h.g, mc.CEILING_CODE + k, bytes([good[k]]))
            tm.poke(h.g, mc.CAVE_2, tables[0])
            tm.poke(h.g, mc.FAME_KNOWN_AT, ends[0])
            tm.poke(h.g, mc.CAVE_5, fifth[0])

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


def pressure(exe):
    """Every bit of the routine of SQUAD_PRESSURE flipped in turn; 1,500 cases of
    Harness.pressure_cases with each of three sets of limits and drop."""
    sys.path.insert(0, HERE)
    import capstone
    import money_cave as mc
    import test_money as tm
    source = tm.two_modules()
    sets = [tm.settings(tm.setting(source, 'SQUAD_PRESSURE', '{ positions = { GK = %d, DF = %d, MF = %d, FW = %d }, keeps_drop = %d }' % x))
            for x in ((0, 0, 0, 0, 100), (1, 2, 4, 3, 10), (0, 2, 3, 3, 25))]
    good, h = mc.PRESSURE_BYTES, None

    def fresh():
        nonlocal h
        h = None
        gc.collect()
        h = tm.Harness(exe)
        tm.run(h.g, source)
    fresh()
    text = {}
    for i in capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm(good, mc.PRESSURE_CODE):
        for k in range(i.size):
            text[i.address + k - mc.PRESSURE_CODE] = '%s %s' % (i.mnemonic, i.op_str)

    def flip(k, bit):
        h.squads.seed(12)
        try:
            for u in sets:
                tm.poke(h.g, mc.CAVE_5, mc.image_5(u))
                if bit is not None:
                    tm.poke(h.g, mc.PRESSURE_CODE + k, bytes([good[k] ^ 1 << bit]))
                h.pressure_cases(1500, u)
            return True
        except BaseException:
            return False
    assert flip(0, None), 'the cases fail without a fault'
    first, last = (int(a) for a in sys.argv[3:5]) if sys.argv[3:] else (0, len(good))
    count = missed = 0
    for k in range(first, min(last, len(good))):
        for bit in range(8):
            count += 1
            if flip(k, bit):
                missed += 1
                print('  not noticed: byte %d (+0x%x), bit %d: %s' % (k, k, bit, text[k]), flush=True)
            elif not flip(0, None):                          # the fault wrote somewhere else
                fresh()
                assert flip(0, None)
    print('bytes %d to %d: %d faults, %d noticed, %d not noticed' % (first, min(last, len(good)) - 1, count, count - missed, missed))


def files(exe, which):
    root = tempfile.mkdtemp()

    def one(i):
        name, old, new = FAULTS[i]
        d = os.path.join(root, str(i))
        for sub in ('sider', 'tools'):
            shutil.copytree(os.path.join(HERE, '..', sub), os.path.join(d, sub), ignore=shutil.ignore_patterns('__pycache__'))
        os.symlink(os.path.join(HERE, '..', 'ML saves'), os.path.join(d, 'ML saves'))    # test_need.py reads the saves
        path = os.path.join(d, 'sider', name)
        s = open(path, encoding='utf-8').read()
        assert s.count(old) == 1, (i, s.count(old))
        open(path, 'w', encoding='utf-8').write(s.replace(old, new))
        for test in ('test_need.py', 'test_money.py'):       # the short one first
            r = subprocess.run([sys.executable, test, exe], cwd=os.path.join(d, 'sider'), capture_output=True, text=True)
            if r.returncode:
                break
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
    if len(sys.argv) < 3 or sys.argv[2] not in ('routine', 'pressure', 'files'):
        sys.exit(__doc__)
    if sys.argv[2] in ('routine', 'pressure'):
        (routine if sys.argv[2] == 'routine' else pressure)(os.path.abspath(sys.argv[1]))
    else:
        files(os.path.abspath(sys.argv[1]), [int(a) for a in sys.argv[3:]])
