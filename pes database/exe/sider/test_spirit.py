"""Runs MLTeamSpirit.lua outside the game and then runs the game's own code with its change.

    python3 test_spirit.py <PES2017.exe>        needs: pip install lupa unicorn capstone

The exe is loaded into a CPU emulator (../tools/emu.py) and the module runs as in
test_money.py: only the names Sider gives a Lua module, and a memory.read / memory.write
that work on the emulator's memory. Then two functions of the game run as machine code on a
made-up player: the one that gives a player his Team Spirit value (fcn_038df4c9) and the one
of the match set-up that stores the values of 3 formations x 13 positions for the match
(fcn_04177a65); the stored values are read back with the game's own reader
(fcn_02f7d891), which is what the match asks.

The rules are tested on careers of the test: a mode data block is filled with match records,
competition records, club records with rivals and a day of the year, and the function the
module registers for the conditions of a match is called on it with a Sider ctx. What is
checked is the one byte the module writes and the rule it names in the log.

What this shows: the module's logic, that the change puts the value into the game's own code,
and what the rules answer for careers written out. What it does not show: Sider, Windows,
the running game, a match. The code that multiplies the abilities by the value
(fcn_02f903a7) is not run.
"""
import os
import re
import struct
import sys

import test_money as tm
from test_money import Game, run
from unicorn.x86_const import UC_X86_REG_ESP
from lupa.luajit21 import LuaRuntime

MODULE = tm.MODULE.replace('MLMoney.lua', 'MLTeamSpirit.lua')
PLACE, OLD = 0x038df6c1, bytes.fromhex('8b4524d985f0ffffff8b4d20')   # mov eax,[ebp+0x24] ...
VALUE_AT = 0x038df6c2                       # the byte the module writes again and again
VALUE, FILL, READER, GETTER = 0x038df4c9, 0x04177a65, 0x02f7d891, 0x038278b0
SELECTOR, MODE_OBJECT = 0x0264f3e8, 0x026503e0      # pointers; selector +0x20 = mode number
USER_CLUB = 0x024fea5c                      # dword: the club of the user
MATCH = 0x537b8                             # the match in the object at mode object +0x34
MASTER_LEAGUE, OTHERS = (0x13, 0x28), (0x12, 0x34)  # mode numbers: kind 12; League (11), kind 21
KNOWN = (3, 30, 60, 90)                     # how well the player knows a tactic setting
INSTALLED = ('RESULT: installed. In a Master League match the Team Spirit of every player of '
             'your club')
NOTHING = 'RESULT: nothing written. This game does not hold'

# what the rules answer, and the settings they answer it with (read from the module)
RULES = dict(BASE=95, FLOOR=90, CEILING=99, FORM_SCALE=0.4, FORM_MATCHES=5, TWO_LOSS_CAP=92,
             WIN_RUN=3, WIN_RUN_VALUE=98, FINAL_VALUE=99, CUP_NEAR_BONUS=2, DERBY_BONUS=2,
             BIG_MATCH_BONUS=2, BIG_TOP=4, BIG_BOTTOM=3)
WEIGHTS = [3, 2, 2, 1, 1]
# the mode data of a career of the test
MATCHES_AT, MATCH_STRIDE, MATCH_COUNT = 0x6f154c, 0x24c, 9000
COMPETITIONS_AT, COMP_STRIDE, C_KIND = 0x552e80, 0x224, 0x5c
COMP_COUNT_AT = 0x5fece8             # how many of the competition records are in use
CLUBS_AT, CLUB_STRIDE, CLUB_COUNT_AT, CLUB_RIVALS = 0x481be0, 0x520, 0x5fece0, 0x514
TODAY_AT, YEAR_AT = 0xc2cbb0, 0xc2cbb2
MODE_SIZE = 0xd00000                        # room for the match records and for the day
LEAGUE, CUP = 29, 30                        # the two competitions of a career of the test
FINAL_ROUND, NEAR_ROUND, EARLY_ROUND = 53, 52, 46     # the rounds of the cup, as in a career
OURS, OTHER, THIRD, FOURTH, FIFTH, RIVAL = 7, 8, 9, 10, 11, 12   # club numbers
TODAY = (305, 2024)                         # the day of the career: 2 November
OTHER_COMP = 31                             # a second competition, for the form of the club


def says(lines, text):
    """Does any of the log lines hold `text`?"""
    return any(text in l for l in lines)


def club(number):
    """The id of one of the clubs of a career of the test."""
    return (number << 14) | 0x96


def new_bytes(value):
    """The bytes of the change, with `value` in them."""
    return bytes([0xb8, value, 0x00, 0x00, 0x00, 0x5b, 0x5f]) + b'\xe9\xd8\x00\x00\x00'


def settings(source):
    """The numbers of the rules, as they are written in the module."""
    def number(name):
        found = re.search(r'^local %s = (-?[\d.]+)' % name, source, re.M)
        return float(found.group(1)) if found else None

    def whole(name):
        found = re.search(r'^local %s = (\d+)' % name, source, re.M)
        return int(found.group(1)) if found else None

    def ints(name):
        found = re.search(r'^local %s = \{([^}]*)\}' % name, source, re.M)
        return [int(x) for x in re.findall(r'-?\d+', found.group(1))] if found else None

    got = {name: (whole(name) if isinstance(want, int) else number(name))
           for name, want in RULES.items()}
    got['FORM_WEIGHTS'] = ints('FORM_WEIGHTS')
    return got


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


KEEP = {'ebx': 0x1b1b1b1b, 'esi': 0x2e2e2e2e, 'edi': 0x3d3d3d3d}


def value_kept(g):
    """The value function for a player of the match, with numbers in the three registers
    it has to give back as they were. -> (value, the registers after, esp after)"""
    player, own = world(g, 0x13, 30, 2)
    team = g.alloc(bytes([1, 0] * 7) + bytes(64))
    got = g.call(VALUE, [player, g.alloc(own), team, 12, 0, 0, 0, g.alloc(size=0x40)],
                 limit=200000, **KEEP) & 0xffffffff
    return got, {k: g.reg(k) for k in KEEP}, g.mu.reg_read(UC_X86_REG_ESP)


def game_values(g):
    """Every case of this test. -> {(function, mode, known, rating): value(s)}"""
    out = {}
    for mode in MASTER_LEAGUE + OTHERS:
        for known in KNOWN:
            for rating in (2, 1, 0):
                out['value', mode, known, rating] = value(g, mode, known, rating)
                out['match', mode, known, rating] = match_values(g, mode, known, rating)
    return out


def install(g, source, sticky=True):
    """Runs the module's init on the emulator's memory, as test_money.run does, but keeps
    what it registers for an event. -> (log lines, reads, writes, fire)"""
    lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
    lines, reads, writes, handlers = [], [], [], {}

    def read(address, count):
        reads.append((int(address), int(count)))
        return g.read(int(address), int(count))

    def write(address, data):
        writes.append((int(address), len(data)))
        if sticky(int(address)) if callable(sticky) else sticky:
            tm.poke(g, int(address), data)

    def register(event, function):
        handlers[event.decode() if isinstance(event, bytes) else str(event)] = function

    def fire(event, **ctx):
        """Calls what the module registered for `event` with a Sider ctx. -> its log lines"""
        assert event in handlers, 'the module registered nothing for %s' % event
        table = lua.table()
        for name, v in ctx.items():            # the runtime takes no str: bytes are the keys
            table[name.encode() if isinstance(name, str) else name] = v
        at = len(lines)
        handlers[event](table)
        return lines[at:]

    make = lua.eval('''function(source, log, read, write, register)
        local env = { assert = assert, table = table, pairs = pairs, ipairs = ipairs, string = string,
                      math = math, tonumber = tonumber, tostring = tostring, unpack = unpack,
                      error = error, _VERSION = _VERSION, type = type,
                      os = { time = os.time, clock = os.clock, date = os.date },
                      log = log, memory = { read = read, write = write } }
        local chunk = assert(loadstring(source, "module"))
        setfenv(chunk, env)
        local module = chunk()
        assert(type(module) == "table" and type(module.init) == "function")
        module.init({ sider_dir = ".\\\\", register = register })
    end''')
    make(source.encode(), lambda text: lines.append(text.decode()), read, write, register)
    return lines, reads, writes, fire


# ---------------- a career of the test ----------------

def record(at, comp, round_no, home, away, g1=None, g2=None, month=1, day=10, played=True):
    """One match record, as the game writes them. `at` is its place in the table."""
    rec = bytearray(MATCH_STRIDE)
    struct.pack_into('<H', rec, 0x00, at)
    struct.pack_into('<H', rec, 0x04, comp)
    struct.pack_into('<H', rec, 0x06, round_no | (0x6000 if played else 0x2000))
    struct.pack_into('<H', rec, 0x08, TODAY[1])
    rec[0x0a], rec[0x0b] = month, day
    struct.pack_into('<I', rec, 0x0c, home)
    struct.pack_into('<I', rec, 0x10, away)
    if played:
        rec[0x14], rec[0x17] = g1, g2
    return at, bytes(rec)


def career(g, matches, kinds=None, clubs=(), today=TODAY, user=OURS):
    """Fills a mode data block with `matches`, the kinds of the competitions, the club
    records and the day, and points the game's pointers at it."""
    g.free_all()
    mode = g.alloc(size=MODE_SIZE)
    table = bytearray(MATCH_COUNT * MATCH_STRIDE)
    for i in range(MATCH_COUNT):
        struct.pack_into('<H', table, i * MATCH_STRIDE, 0xffff)     # every place is free
    for at, rec in matches:
        table[at * MATCH_STRIDE:(at + 1) * MATCH_STRIDE] = rec
    g.write(mode + MATCHES_AT, bytes(table))
    table = bytearray(300 * COMP_STRIDE)
    kinds = kinds or {LEAGUE: 1, CUP: 3}
    for place, (comp, kind) in enumerate(sorted(kinds.items())):
        struct.pack_into('<H', table, place * COMP_STRIDE, comp)      # +0x00 its own number
        table[place * COMP_STRIDE + C_KIND] = kind
        # a decoy in the place whose number is the competition's: the game does not answer
        # a competition by the place it is in (fcn_03822ab9 walks the table and compares
        # the number in +0x00), so a module that read by place would find this, not it
        if comp < 300:
            table[comp * COMP_STRIDE + C_KIND] = 1 if kind != 1 else 3
    g.write(mode + COMPETITIONS_AT, bytes(table))
    g.write(mode + COMP_COUNT_AT, struct.pack('<I', len(kinds)))
    for n, (one, rivals) in enumerate(clubs):
        at = mode + CLUBS_AT + n * CLUB_STRIDE
        g.write(at, struct.pack('<I', club(one)))
        g.write(at + CLUB_RIVALS, struct.pack('<3I', *[club(r) if r else 0xffffffff for r in rivals]))
    g.write(mode + CLUB_COUNT_AT, struct.pack('<I', len(clubs)))
    g.write(mode + TODAY_AT, struct.pack('<HH', today[0], today[1]))
    selector, mode_object = g.alloc(size=0x100), g.alloc(size=0x100)
    g.write(selector + 0x20, struct.pack('<I', 0x13))               # Master League
    g.write(SELECTOR, struct.pack('<I', selector))
    g.write(mode_object + 0x30, struct.pack('<I', mode))
    g.write(MODE_OBJECT, struct.pack('<I', mode_object))
    g.write(USER_CLUB, struct.pack('<I', club(user)))
    return mode


def played_run(rounds, score, opp=OTHER, month=1, comp=OTHER_COMP):
    """`rounds` matches our club has played, one a month from January on, all with `score`."""
    return [record(i + 1, comp, rounds[i], club(OURS), club(opp), score[0], score[1],
                   month=month + i, day=2) for i in range(len(rounds))]


def league():
    """A league of six clubs, played to the end. Our club wins its first five matches and
    draws its last five and is first; the others follow in order, the rival last."""
    out, at = [], 0
    order = [OTHER, THIRD, FOURTH, FIFTH, RIVAL]
    for round_no in range(10):                      # a round a month, January to October
        at += 1
        one = order[round_no % 5]                   # every other club twice
        win = round_no < 5
        out.append(record(at, LEAGUE, round_no, club(OURS), club(one), 2 if win else 1,
                          0 if win else 1, month=1 + round_no, day=10))
    for i, one in enumerate(order):                 # the other twenty: the better club wins
        for other in order[i + 1:]:
            at += 1
            out.append(record(at, LEAGUE, at % 10, club(one), club(other), 2, 0,
                              month=1 + at % 10, day=20))
            at += 1
            out.append(record(at, LEAGUE, at % 10, club(other), club(one), 0, 2,
                              month=1 + at % 10, day=20))
    return out


def main(exe):
    source = open(MODULE, encoding='utf-8').read()
    got = settings(source)
    wrong = {k: (got[k], want) for k, want in RULES.items() if got[k] != want}
    if got['FORM_WEIGHTS'] != WEIGHTS:
        wrong['FORM_WEIGHTS'] = (got['FORM_WEIGHTS'], WEIGHTS)
    assert not wrong, 'the rules of the module changed; these expectations are for %s: %s' % (
        RULES, wrong)
    new = new_bytes(RULES['BASE'])

    image = Game(exe)
    before = image.read(PLACE - 0x100, 0x200)
    assert image.read(PLACE, len(OLD)) == OLD

    control = game_values(image)
    kept = value_kept(image)
    for (what, mode, known, rating), got_v in control.items():
        if what == 'value':
            assert 1 <= got_v <= known < 99, (mode, known, rating, got_v)
            stored = control['match', mode, known, rating]       # kind 21: lower in formations 2 and 3
            assert stored[:13] == bytes([got_v]) * 13 and 1 <= min(stored) and max(stored) == got_v
        if rating != 2:                                         # out of position: lower
            assert got_v < control[what, mode, known, 2] or known == 3
    print('ok 1: without the module the game gives the made-up player a value below 99 in every mode '
          '(%d cases: he knows the tactics at %s, plays a position rated A, B or C), lower out of '
          'position, and the match set-up stores it for 3 formations x 13 positions'
          % (len(control) // 2, ', '.join(map(str, KNOWN))))

    lines, reads, writes = run(image, source)
    assert lines[-1].startswith(INSTALLED) and says(lines, 'as expected'), lines
    assert writes == [(PLACE, len(OLD))] and tm.inside(reads, ((PLACE, len(OLD)), (0x038df528, 5)))
    after = image.read(PLACE - 0x100, 0x200)
    assert after == before[:0x100] + new + before[0x100 + len(new):], (
        after[0x100:0x100 + len(new)].hex(), new.hex())
    assert image.read(VALUE_AT, 1) == bytes([RULES['BASE']])
    print('ok 2: the module writes the %d bytes of the one place and nothing else, and the byte '
          'in them is the base value %d' % (len(OLD), RULES['BASE']))

    with_module = game_values(image)
    for (what, mode, known, rating), got_v in with_module.items():
        if mode in MASTER_LEAGUE:
            assert got_v == (RULES['BASE'] if what == 'value' else bytes([RULES['BASE']]) * 39), (
                what, mode, known, rating, got_v)
        else:
            assert got_v == control[what, mode, known, rating]
    got = value_kept(image)
    assert got == (RULES['BASE'], KEEP, kept[2]), (got, KEEP, kept)
    print('ok 3: with the module the same code gives %d in Master League (mode numbers 19 and 40), '
          'whatever the player knows and wherever he plays, and the match reads it for all 3 '
          'formations x 13 positions; in League mode and mode kind 21 the values are as without '
          'the module. It gives back ebx, esi and edi as it was given them and leaves the stack '
          'where the game leaves it' % RULES['BASE'])

    # ---------------- the rules, on careers of the test ----------------
    g = Game(exe)
    lines, reads, writes, fire = install(g, source)
    assert lines[-1].startswith(INSTALLED), lines

    def answer(matches, comp=LEAGUE, round_no=5, opp=OTHER, number=0, clubs=(), kinds=None):
        """Builds the career and calls the module for one match of it. -> (value, its lines)"""
        career(g, matches, kinds, clubs)
        said = fire('after_set_conditions', home_team=club(OURS), away_team=club(opp),
                    tournament_id=comp, match_id=number)
        return g.read(VALUE_AT, 1)[0], ' | '.join(said)

    now = [record(0, LEAGUE, 5, club(OURS), club(OTHER), month=7, day=9, played=False)]
    cases = [
        ('a club that has played nothing', now, RULES['BASE'], ''),
        ('one loss', now + played_run([0], (0, 2)), 94, 'form -3'),
        ('two losses one after the other', now + played_run([0, 1], (0, 2)),
         RULES['TWO_LOSS_CAP'], 'two losses'),
        ('three wins one after the other', now + played_run([0, 1, 2], (2, 0)),
         RULES['WIN_RUN_VALUE'], '3 wins in a row'),
        ('five wins', now + played_run([0, 1, 2, 3, 4], (3, 1)), 99, 'form +9'),
        ('five losses', now + played_run([0, 1, 2, 3, 4], (1, 3)), 91, 'form -9'),
        ('a draw and then a win', now + played_run([0], (1, 1))
         + [record(90, OTHER_COMP, 2, club(OURS), club(OTHER), 2, 1, month=6, day=20)], 96, 'form +3'),
    ]
    for name, matches, want, reason in cases:
        got_v, said = answer(matches)
        assert got_v == want, '%s: %d, expected %d (%s)' % (name, got_v, want, said)
        assert reason in said, '%s: the log does not say %r: %s' % (name, reason, said)
    print('ok 4: the form of the club is the last five matches (%d careers written out: nothing '
          'played, one loss, two losses, three wins, five wins, five losses, a draw and a win), '
          'and every rule that fires is named in the log' % len(cases))

    clubs = [(OURS, (RIVAL, 0, 0)), (OTHER, (0, 0, 0)), (THIRD, (0, 0, 0)), (RIVAL, (OURS, 0, 0))]
    # every round of the cup is in the records from the day the cup is made (as in a career)
    top = [record(601, CUP, FINAL_ROUND, club(OTHER), club(THIRD), month=11, day=1, played=False),
           record(602, CUP, NEAR_ROUND, club(THIRD), club(FOURTH), month=11, day=1, played=False)]
    for name, round_no, opp, want, reason in (
            ('a cup final', FINAL_ROUND, OTHER, RULES['FINAL_VALUE'], 'final'),
            ('the round before a final', NEAR_ROUND, OTHER,
             RULES['BASE'] + RULES['CUP_NEAR_BONUS'], 'last but one round'),
            ('an early round of a cup', EARLY_ROUND, OTHER, RULES['BASE'], ''),
            ('a derby', EARLY_ROUND, RIVAL, RULES['BASE'] + RULES['DERBY_BONUS'], 'derby')):
        this = [record(600, CUP, round_no, club(OURS), club(opp), month=11, day=1, played=False)] + top
        got_v, said = answer(this, CUP, round_no, opp, number=600, clubs=clubs)
        assert got_v == want, '%s: %d, expected %d (%s)' % (name, got_v, want, said)
        assert reason in said, '%s: the log does not say %r: %s' % (name, reason, said)

    table = league()
    for name, opp, want, reason in (
            ('the club in second place', OTHER, RULES['BASE'] + RULES['BIG_MATCH_BONUS'], 'big match'),
            ('the club in last place', RIVAL, RULES['BASE'] + RULES['DERBY_BONUS'], 'derby'),
            ('a club in the middle', FIFTH, RULES['BASE'], '')):
        this = [record(700, LEAGUE, 4, club(OURS), club(opp), month=11, day=1, played=False)]
        got_v, said = answer(table + this, LEAGUE, 4, opp, number=700, clubs=clubs)
        assert got_v == want, '%s: %d, expected %d (%s)' % (name, got_v, want, said)
        assert ('big match' in said) == (reason == 'big match'), '%s: %s' % (name, said)
    print('ok 5: the last round of a cup, the round before it, a rival the club record names and '
          'a league match of two clubs at the top raise the value; an early round, a club that is '
          'no rival and a match against a club in the middle do not')

    # a match that is not ours, and a mode that is not a career
    base_value, _ = answer(now)
    assert base_value == RULES['BASE']
    career(g, now)
    fire('after_set_conditions', home_team=club(OTHER), away_team=club(THIRD),
         tournament_id=LEAGUE, match_id=0)
    assert g.read(VALUE_AT, 1) == bytes([RULES['BASE']])
    career(g, now)
    selector = struct.unpack('<I', g.read(SELECTOR, 4))[0]
    g.write(selector + 0x20, struct.pack('<I', 0x12))           # League, not Master League
    fire('after_set_conditions', home_team=club(OURS), away_team=club(OTHER),
         tournament_id=LEAGUE, match_id=0)
    assert g.read(VALUE_AT, 1) == bytes([RULES['BASE']])
    print('ok 6: a match of two other clubs and a mode that is not a career leave the value '
          'where it is')

    # what the module writes is what the game's own code answers
    wanted = 0x5d                                   # 93: a value the rules reach
    tm.poke(image, VALUE_AT, bytes([wanted]))       # poke, so that the run sees the new byte
    assert value(image, 0x13, 30, 1) == wanted
    assert match_values(image, 0x13, 30, 1) == bytes([wanted]) * 39
    assert value(image, 0x34, 30, 1) == control['value', 0x34, 30, 1]     # kind 21: unchanged
    print('ok 7: every value the byte holds, %d here, is what the game gives a player of your club '
          'in Master League and what the match reads for 3 formations x 13 positions; the other '
          'modes keep the value the game works out' % wanted)

    # ---------------- a game that does not hold what the module expects ----------------
    count = 0
    for k in range(len(OLD)):                   # every byte of the place, one at a time
        tm.poke(image, PLACE, OLD)
        tm.poke(image, PLACE + k, bytes([OLD[k] ^ 0x02]))
        lines, reads, writes = run(image, source)
        assert lines[-1].startswith(NOTHING) and not writes and says(lines, 'DIFFERENT'), (k, lines)
        count += 1
    tm.poke(image, PLACE, new)                  # a game that holds the change already
    lines, reads, writes = run(image, source)
    assert lines[-1].startswith(NOTHING) and not writes
    tm.poke(image, PLACE, OLD)
    lines, reads, writes = run(image, source, sticky=False)
    assert lines[-1].startswith('RESULT: the change did not go in.'), lines[-1]
    print('ok 8: with one byte of the place changed (%d cases) or the change in already nothing is '
          'written and the place is named; a write that does not go in is reported' % count)

    for order in ((source, tm.two_modules()), (tm.two_modules(), source)):
        del image
        image = Game(exe)
        lines, reads, writes = run(image, tm.SPLIT.join(order))
        got_lines = [l for l in lines if l.startswith('RESULT')]
        assert len(got_lines) == 3 and all(l.startswith('RESULT: installed.') for l in got_lines), got_lines
        assert value(image, 0x13, 30, 1) == RULES['BASE']
    print('ok 9: with MLMoney.lua and MLTransfers.lua in the same game, above or below them, all '
          'three are installed and the value is %d' % RULES['BASE'])

    # the kind of a competition is answered by the game's own look-up: the table is walked
    # and the number in +0x00 compared (fcn_03822ab9), not read at the number's own place
    mode = career(g, now, {LEAGUE: 1, CUP: 3})
    decoy = g.read(mode + COMPETITIONS_AT + CUP * COMP_STRIDE + C_KIND, 1)[0]
    assert decoy == 1, decoy       # a league sits in the place the cup's number would be
    this = [record(600, CUP, FINAL_ROUND, club(OURS), club(OTHER), month=11, day=1, played=False)] + top
    career(g, this)
    said = fire('after_set_conditions', home_team=club(OURS), away_team=club(OTHER),
                tournament_id=CUP, match_id=600)
    got = g.read(VALUE_AT, 1)[0]
    assert got == RULES['FINAL_VALUE'], 'the cup rules did not fire: %d (%s)' % (got, ' | '.join(said))

    unseen = 77                                     # a competition the table does not hold
    theirs = [record(601, unseen, FINAL_ROUND, club(OTHER), club(THIRD), month=11, day=1, played=False),
              record(602, unseen, NEAR_ROUND, club(THIRD), club(FOURTH), month=11, day=1, played=False)]
    career(g, [record(600, unseen, FINAL_ROUND, club(OURS), club(OTHER),
                      month=11, day=1, played=False)] + theirs)
    said = fire('after_set_conditions', home_team=club(OURS), away_team=club(OTHER),
                tournament_id=unseen, match_id=600)
    got = g.read(VALUE_AT, 1)[0]
    assert got == RULES['BASE'], (got, ' | '.join(said))
    assert 'final' not in ' | '.join(said), said
    print('ok 10: the kind of a competition is the one of the record that carries its number, not '
          'the one of the record that sits at that number\'s place in the table (a league was put '
          'in the cup\'s place and the cup rules still fired); a competition the table does not '
          'hold is no cup')


if __name__ == '__main__':
    main(sys.argv[1])
