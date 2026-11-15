#!/usr/bin/env python3
"""One transfer window of a Master League career, read from two saves, against the rules
of MLTransfers.lua.

    python3 window_report.py <PES2017.exe> <save before> <save after> [year month]
                                                    needs: pip install lupa unicorn

The player records of a save are the last part of its data: 21,033 records of 0xe0 bytes
as zlib chunks (big-endian: size of all records, a second number; then per chunk its
size, its packed size, a running offset, the stream). A signing is a player whose club
id (+0xa8) differs between the two saves. Where he was before: no contract (status 1 or
2 in +0xb4 bits 0-3), on the list of his club (mark 29 or 30 of +0xb8), or any other
player of a club.

Then every signing by a computer club is put to the steps of money_cave.accepts that need
nothing but the two clubs, the player and the month in which the club chose (every month
from `year month`, default 2024 7, to the month of the signing is tried): rivals, what
the selling club keeps, scouting, prestige, the price. The steps that also hang on the
slot of the plan (the position asked for, a status band, the second search) are taken
with the player's own position and are shares, not proof. "By chance" is what a club that
does not look would pass; a window played without these rules gives about that number
(the pair in `ML saves/` does), a window played with them nearly all.

The rating is the game's own (fcn_03853b42 run in the emulator on the record); age,
position and popularity are read from the record as the game's field reader does.
"""
import collections
import os
import statistics
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools')]
import money_cave as mc                          # noqa: E402
import savefile                                  # noqa: E402
import test_money                                # noqa: E402
from emu import Game                             # noqa: E402

RECORD, NONE, TEAMS, RANKING, RANKED = 0xe0, 0xffffffff, 0x50, 0x92262c, 499
PLANS, PLAN, PLANNED = 0x92596c, 0x118, 498
CHANNELS = ('no contract', 'listed', 'other club players')


def player_block(data):
    """The unpacked player records of the save's data: the walk that ends exactly at the
    end of the data is the right one."""
    o = 0
    while True:
        o = data.index(b'\x00\x04\x00\x00', o + 1)        # the size of the first chunk
        total = struct.unpack_from('>I', data, o - 8)[0]
        if data[o + 12] != 0x78 or total % RECORD or not 0 < total < 1 << 25:
            continue
        at, out = o, b''
        try:
            while len(out) < total:
                size, used, _ = struct.unpack_from('>III', data, at)
                out += zlib.decompress(data[at + 12:at + 12 + used])
                at += 12 + used
        except (zlib.error, struct.error):
            continue
        if len(out) == total and at == len(data):
            return out


class Save:
    def __init__(self, path):
        data = savefile.read(path)['data']
        block = player_block(data)
        self.players = {}
        for i in range(len(block) // RECORD):
            r = block[i * RECORD:(i + 1) * RECORD]
            ident = struct.unpack_from('<II', r, 0x2c)
            if ident[1]:
                self.players[ident] = r
        self.teams = {}
        for i in range(626):
            t = data[TEAMS + i * 0x520:TEAMS + (i + 1) * 0x520]
            self.teams[struct.unpack_from('<I', t, 0)[0]] = t[4:0x4a].split(b'\0')[0].decode('utf-8', 'replace')
        rows = [struct.unpack_from('<IIHHHH', data, RANKING + 16 * i) for i in range(RANKED)]
        assert [r[1] for r in rows] == list(range(1, RANKED + 1)), 'the club ranking is not where it was'
        self.ranking = {r[0]: dict(id=r[0], place=r[1], points=r[2], level=r[5]) for r in rows}
        self.first = dict(self.ranking[rows[0][0]])
        plans = {struct.unpack_from('<I', data, PLANS + PLAN * i)[0] for i in range(PLANNED)}
        assert plans < set(self.ranking), 'the plan records are not where they were'
        (self.user,) = set(self.ranking) - plans             # the one club of the ranking without a plan
        self.count = collections.Counter(club(r) for r in self.players.values())


def u32(r, o): return struct.unpack_from('<I', r, o)[0]
def club(r): return u32(r, 0xa8)
def status(r): return u32(r, 0xb4) & 15
def deal(r): return u32(r, 0xb4) >> 4 & 3
def listed(r): return u32(r, 0xb8) >> 29 & 3 != 0
def age(r): return u32(r, 0x1c) >> 7 & 0x3f
def position(r): return u32(r, 4) >> 28
def popularity(r): return u32(r, 0xb4) >> 11 & 0xfff
def name(r): return r[0x38:0x66].split(b'\0')[0].decode('utf-8', 'replace')
def date(v): return v & 0xffff, v >> 16 & 0xff, v >> 24


def where(r):
    return 0 if status(r) in (1, 2) else 1 if listed(r) else 2


class Rater:
    """The game's rating of a player record (fcn_03853b42 with position 13 and kind 2, as the routine asks)."""
    def __init__(self, exe):
        self.g = Game(exe)
        self.rec, self.pos = self.g.alloc(size=0x400), self.g.alloc(size=4)

    def __call__(self, record):
        self.g.write(self.rec, record)
        self.g.write(self.pos, struct.pack('<I', 13))
        return self.g.call(mc.RATING, [self.rec, self.pos, 2]) & 0xff


def moves(before, after, user):
    """Every player whose club changed and whose new club is a computer club."""
    out = []
    for k, r in before.players.items():
        new = after.players.get(k)
        if new is not None and club(r) != club(new) and club(new) not in (NONE, user):
            out.append((k, r, new))
    return out


def judge(t, before, rate, k, r, new, start):
    """One signing against the steps of money_cave.accepts. -> dict of what was found.
    The month in which the club chose is not in the save: every month from `start` to the
    month of the signing is tried, and a step that hangs on the month counts as passed if
    one of them passes it (`months` says how many were tried, for the chance)."""
    buyer = dict(before.ranking.get(club(new), before.first), id=club(new), count=before.count[club(new)])
    seller = None if club(r) == NONE else dict(before.ranking.get(club(r), before.first), id=club(r),
                                               count=before.count[club(r)])
    w, key = where(r), mc.player_key(k)
    both = key ^ mc.club_key(buyer['id'])
    signed = date(u32(new, 0xd8))
    months = [(y, m) for y in range(start[0], signed[0] + 1) for m in range(1, 13)
              if start <= (y, m) <= signed[:2]] or [start]
    stamps = [(y | m << 16) * mc.HASH_A & mc.M32 for y, m in months]
    index = mc.persona_index(t, buyer['id'], buyer['level'])
    mine = t.genes[index]
    g = dict(zip(mc.GENE_NAMES, [mc.gene(t, mine, i, buyer['id']) for i in range(mc.GENES)]))
    rating, own = rate(r), mc.eleven(t, buyer['points'], buyer['level'])
    seen = rating + (mc.high_byte(both, mc.HASH_FOG) * (2 * g['fog'] + 1) >> 8) - g['fog']
    out = dict(where=w, buyer=buyer, seller=seller, persona=t.names[index], rating=rating, own=own, years=age(r),
               name=name(r), position=position(r), signed=signed, months=len(months),
               value=mc.value(t, rating, age(r), popularity(r), position(r), k) / 10000.0,
               top=rating <= mc.WINDOW_TOP[min(buyer['level'], mc.LEVELS - 1)])
    out['rivals'] = not (w != 0 and seller and ((buyer['id'], seller['id']) in t.rivals
                                               or (seller['id'], buyer['id']) in t.rivals))
    if w == 2 and seller:
        s = t.genes[mc.persona_index(t, seller['id'], seller['level'])]
        keeps = mc.gene(t, s, mc.GENE_NAMES.index('keeps'), seller['id'])
        out['keeps'] = any(mc.draw(mc.club_key(seller['id']) ^ key ^ stamp, mc.HASH_KEEPS) >= keeps for stamp in stamps)
        out['keeps chance'] = 100 - 100 * (min(keeps, 100) / 100.0) ** len(months)
        out['seller count'] = seller['count'] > mc.POOL_KEEPS
    if w != 1:
        out['knows'] = mc.draw(both, mc.HASH_KNOWS) < g['knows']
        out['knows chance'] = min(100, g['knows'])
    out['prestige'] = rating <= own + g['prestige']
    numbers = [g[n] for n in mc.GENE_NAMES]
    price = mc.value(t, seen & mc.M32, age(r), popularity(r), position(r), k)
    if w != 2:
        price = price * (t.ceiling_free, t.ceiling_listed)[w] // 100
    out['price'] = price <= mc.limit(t, buyer['level'], k, buyer['id'], True, numbers, popularity(r))
    out['price, no need'] = price <= mc.limit(t, buyer['level'], k, buyer['id'], False, numbers, popularity(r))
    # the steps that hang on the slot: counted with the player's own position, without a band
    out['small squad'] = buyer['count'] < t.squad
    out['in age range'] = mine[mc.AGE_FROM] <= age(r) <= mine[mc.AGE_TO]
    out['age'] = out['in age range'] or mc.draw(both, mc.HASH_AGE) >= g['strict']
    out['age chance'] = 100 - g['strict']
    out['ambition'] = seen >= own - g['ambition']
    if mine[mc.THEN_1] != mc.NO_CHANNELS:
        def place(pos, stamp):
            turn = (pos * mc.HASH_POSITION & mc.M32) ^ mc.club_key(buyer['id']) ^ stamp
            d = mc.draw(turn, mc.HASH_C)
            first = (0 if d < g['free'] else 1 if d < g['free'] + g['listed']
                     else 2 if d < g['free'] + g['listed'] + g['clubs'] else None)
            second = mine[mc.THEN_1] if mine[mc.THEN_1] != first else mine[mc.THEN_2]
            return w == first, w == first or w == second or (first is None and w == mine[mc.THEN_1])
        out['first place'] = any(place(position(r), stamp)[0] for stamp in stamps)
        out['place'] = any(place(position(r), stamp)[1] for stamp in stamps)
        # what a club that does not look would pass: the same with every other position
        others = [any(place(pos, stamp)[0] for stamp in stamps) for pos in range(13) if pos != position(r)]
        out['first place chance'] = 100.0 * sum(others) / len(others)
    return out


def share(found, key):
    some = [f for f in found if key in f]
    text = '%4d of %4d' % (sum(f[key] for f in some), len(some)) if some else '   -'
    if some and key + ' chance' in some[0]:
        text += '   by chance %4.0f' % (sum(f[key + ' chance'] for f in some) / 100.0)
    return text


def report(t, exe, before_path, after_path, start, rate=None):
    before, after = Save(before_path), Save(after_path)
    rate = rate or Rater(exe)
    user = before.user
    every = [(m, judge(t, before, rate, *m, start)) for m in moves(before, after, user)]
    sold = [f for (k, r, new), f in every if club(r) == user]
    found = [f for (k, r, new), f in every if club(r) != user]
    by = collections.Counter(f['where'] for f in found)
    print('user club: %s; players %d; computer clubs %d' % (before.teams[user], len(before.players),
                                                           len(before.ranking) - 1))
    print('signings by computer clubs: %d (no contract %d, listed %d, other club players %d); '
          'and from the user club %d' % (len(found), by[0], by[1], by[2], len(sold)))
    print('listed before / after: %d / %d' % (sum(listed(r) for r in before.players.values()),
                                              sum(listed(r) for r in after.players.values())))
    print('signed in month: %s' % ', '.join('%d-%02d: %d' % (y, m, n) for (y, m), n in sorted(
        collections.Counter(f['signed'][:2] for f in found).items())))
    print('steps that need no slot of the plan: passed, of those the step applies to, and how many a club')
    print('that does not look would pass')
    for title, key, some in (('rivals', 'rivals', found), ('seller above 23', 'seller count', found),
                             ('seller keeps', 'keeps', found),
                             ('  signed in the first month', 'keeps', [f for f in found if f['months'] == 1]),
                             ('scouting', 'knows', found),
                             ('  no contract', 'knows', [f for f in found if f['where'] == 0]),
                             ('  other club players', 'knows', [f for f in found if f['where'] == 2]),
                             ('prestige', 'prestige', found), ('top of the level', 'top', found),
                             ('price, in need', 'price', found), ('price, no need', 'price, no need', found)):
        print('  %-28s %s' % (title, share(some, key)))
    print('steps that hang on the slot (taken with the player\'s own position, no band; a buyer under %d '
          'players is in need and skips some):' % t.squad)
    for title, key in (('age', 'age'), ('ambition', 'ambition'), ('place, first or second', 'place'),
                       ('place, first', 'first place')):
        failed = [f for f in found if key in f and not f[key]]
        print('  %-28s %s   failed %d, of them in need %d' % (title, share(found, key), len(failed),
                                                             sum(f['small squad'] for f in failed)))
    print('  %-28s %s' % ('inside the age range', share(found, 'in age range')))
    return before, after, found, sold, user


def tables(t, before, after, found, sold, user):
    print('\nby the persona of the buyer: signings; no contract / listed / other; clubs that signed of clubs; '
          'mean age; mean rating; the same minus the rating of its eleven; values in millions')
    groups, clubs = collections.defaultdict(list), collections.Counter()
    for f in found:
        groups[f['persona']].append(f)
    for c, row in before.ranking.items():
        if c != user:
            clubs[t.names[mc.persona_index(t, c, row['level'])]] += 1
    for persona, n in sorted(clubs.items(), key=lambda x: -len(groups[x[0]])):
        some = groups[persona]
        c = collections.Counter(f['where'] for f in some)
        mean = (lambda key: statistics.mean(key(f) for f in some)) if some else (lambda key: 0)
        print('  %-17s %4d  %3d /%3d /%3d   %3d of %3d   age %4.1f  rating %4.1f  %+5.1f  %8.1f' % (
            persona or '(none)', len(some), c[0], c[1], c[2], len({f['buyer']['id'] for f in some}), n,
            mean(lambda f: f['years']), mean(lambda f: f['rating']), mean(lambda f: f['rating'] - f['own']),
            sum(f['value'] for f in some)))
    print('by the level of the buyer: signings; no contract / listed / other; clubs that signed of clubs; '
          'mean rating; highest rating')
    for level in range(9, -1, -1):
        some = [f for f in found if f['buyer']['level'] == level]
        c = collections.Counter(f['where'] for f in some)
        n = sum(row['level'] == level and club_id != user for club_id, row in before.ranking.items())
        print('  level %d  %4d  %3d /%3d /%3d   %3d of %3d   rating %4.1f   %2d' % (
            level, len(some), c[0], c[1], c[2], len({f['buyer']['id'] for f in some}), n,
            statistics.mean(f['rating'] for f in some) if some else 0, max([f['rating'] for f in some] or [0])))
    paid = [f for f in found if f['seller']]
    if paid:
        up = sum(f['buyer']['place'] < f['seller']['place'] for f in paid)
        print('from club to club: %d; to a club higher in the ranking %d, lower %d; median places moved %d' % (
            len(paid), up, len(paid) - up,
            statistics.median(abs(f['buyer']['place'] - f['seller']['place']) for f in paid)))
        print('  by the level of the seller: %s' % ', '.join('%d: %d' % (level, n) for level, n in sorted(
            collections.Counter(f['seller']['level'] for f in paid).items(), reverse=True)))
    print('ratings of the players who moved: %s' % ', '.join(
        '%s: %d' % (title, sum(low <= f['rating'] <= high for f in found))
        for title, low, high in (('85 and more', 85, 99), ('80-84', 80, 84), ('75-79', 75, 79), ('70-74', 70, 74),
                                 ('under 70', 0, 69))))
    print('the 30 best players who moved: rating, age, value, name, from (place) -> to (place, persona)')
    for f in sorted(found + sold, key=lambda f: (-f['rating'], -f['value']))[:30]:
        s = f['seller']
        print('  %2d %2d %6.1f  %-24s %-30s -> %s (%d, %s)' % (
            f['rating'], f['years'], f['value'], f['name'][:24],
            ('%s (%d)' % (before.teams[s['id']], s['place']))[:30] if s else CHANNELS[0],
            before.teams[f['buyer']['id']], f['buyer']['place'], f['persona']))
    ins = collections.Counter(f['buyer']['id'] for f in found)
    outs = collections.Counter(f['seller']['id'] for f in found if f['seller'])
    print('clubs that signed: %d of %d; most by one club: %s' % (
        len(ins), len(before.ranking) - 1, ', '.join('%s %d' % (before.teams[c], n) for c, n in ins.most_common(5))))
    print('clubs that sold: %d; most by one club: %s' % (
        len(outs), ', '.join('%s %d' % (before.teams[c], n) for c, n in outs.most_common(5))))
    for title, save in (('before', before), ('after', after)):
        sizes = sorted(save.count[c] for c in before.ranking if c != user)
        print('squads %s: smallest %d, largest %d, under %d players: %d clubs' % (
            title, sizes[0], sizes[-1], t.squad, sum(n < t.squad for n in sizes)))
    mine = ['%s: %s -> %s' % (name(r), before.teams.get(club(r), '-'), before.teams.get(club(after.players[k]), '-'))
            for k, r in before.players.items() if club(r) != club(after.players[k]) and user in (club(r), club(after.players[k]))]
    print('moves of the user club: %s' % ('; '.join(mine) or 'none'))


if __name__ == '__main__':
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    settings = test_money.settings(test_money.two_modules())
    month = (int(sys.argv[4]), int(sys.argv[5])) if len(sys.argv) > 5 else (2024, 7)
    tables(settings, *report(settings, sys.argv[1], sys.argv[2], sys.argv[3], month))
