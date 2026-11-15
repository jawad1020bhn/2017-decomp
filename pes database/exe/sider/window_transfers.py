#!/usr/bin/env python3
"""The transfers of the current window of a Master League save, the most expensive first.

    python3 window_transfers.py <PES2017.exe> <save> [out.csv]
                                                    needs: pip install lupa unicorn

Writes <save>.transfers.csv (or out.csv) and prints the 20 most expensive.

Save the game while the window is open (its last day, 31 August or 31 January, is fine)
and run this on the save file (`ML00000013` or the like). All of it is read from the one
save; `Save` and the field readers are those of window_report.py.

Who moved: every player with a club whose contract began (+0xd8) inside the window that
holds the date of the save: 1 July to 31 August, or 1 to 31 January.
From where: +0xd0 holds the club he left for as long as the window is open; without it
he had no club. After the window has closed the game clears it for nearly all, so a save
from later lists the signings with "?" and cannot tell a free signing from a bought one.

The price:
- the user's own deals: the amount of the account line of the deal ("paid");
- a signing of a player without a club costs nothing ("free");
- any other: the game does not keep it (a computer club has no money, the fee is worked
  out and dropped: ../MASTER_LEAGUE.md, 9.7). It is worked out again here the way the game
  did, with MLMoney.lua's settings from this folder ("formula"). The game then moved it up
  or down by up to 19 percent at random; that part is lost. Rating, age and popularity
  are those of the save, not of the day of the move.

Amounts are as the game shows them (100 times the stored number).
"""
import collections
import csv
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools')]
import money_cave as mc                          # noqa: E402
import overall                                   # noqa: E402
import savefile                                  # noqa: E402
import test_money                                # noqa: E402
import window_report as wr                       # noqa: E402

# found by their content in the four saves of `ML saves/`, not read in the code
TODAY = 0x75bea8                # u16 day of the year (0 = 1 January), u16 year
ACCOUNT, LINES, LINE = 0x868144, 100, 0x28      # the user's deals: player id, ..., amount +0x20, kind +0x24
BEFORE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)      # the game's year has no 29 February
COLUMNS = ('price', 'how', 'player', 'age', 'position', 'rating', 'from', 'to', 'date')


def window(day, year):
    """The window that holds the day, or the last one before it: (first day, last day) as (y, m, d)."""
    if day >= BEFORE[6]:
        return (year, 7, 1), (year, 8, 31)
    return (year, 1, 1), (year, 1, 31)


def transfers(t, path, rate):
    """-> (rows by price, the most expensive first; the window; whether it is still open)"""
    save, data = wr.Save(path), savefile.read(path)['data']
    day, year = struct.unpack_from('<HH', data, TODAY)
    assert day < 365 and 2000 <= year < 2300, 'the date of the save is not where it was'
    first, last = window(day, year)
    month = max(m for m in range(12) if BEFORE[m] <= day)
    is_open = (year, month + 1, day - BEFORE[month] + 1) <= last
    paid = {}                                    # the last line of a player is his last deal
    for i in range(LINES):
        low, high, amount, kind = struct.unpack_from('<II24xiI', data, ACCOUNT + i * LINE)
        if high:
            paid[low, high] = abs(amount)
    signed = collections.defaultdict(list)
    for k, r in save.players.items():
        if wr.club(r) != wr.NONE and first <= wr.date(wr.u32(r, 0xd8)) <= last:
            signed[wr.date(wr.u32(r, 0xd8))].append(k)
    # shortcut: a new career dates every contract on its first day; a day with more than 1000
    # is that, not signings (a whole window has about 500). Upgrade if a window ever has more.
    rows = []
    for k in (k for when, some in signed.items() if len(some) <= 1000 for k in some):
        r = save.players[k]
        old, new, rating = wr.u32(r, 0xd0), wr.club(r), rate(r)
        if save.user in (old, new) and k in paid:
            price, how = paid[k], 'paid'
        elif old == wr.NONE and is_open:
            price, how = 0, 'free'
        else:
            price, how = mc.fee(t, rating, wr.age(r), wr.popularity(r), wr.position(r), k), 'formula'
        rows.append(dict(zip(COLUMNS, (
            price * 100, how, wr.name(r), wr.age(r), overall.POSITIONS[overall.FILE_POS[wr.position(r)]], rating,
            save.teams.get(old, 'no club' if is_open else '?'), save.teams[new],
            '%d-%02d-%02d' % wr.date(wr.u32(r, 0xd8))))))
    rows.sort(key=lambda row: (-row['price'], row['player']))
    return rows, (first, last), is_open


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = sys.argv[3] if len(sys.argv) > 3 else sys.argv[2] + '.transfers.csv'
    sys.stdout.reconfigure(errors='replace')          # a Windows console may not have every letter of a name
    rows, (first, last), is_open = transfers(test_money.settings(test_money.two_modules()), sys.argv[2],
                                             wr.Rater(sys.argv[1]))
    with open(out, 'w', newline='', encoding='utf-8-sig') as f:            # the mark makes Excel read the names right
        w = csv.DictWriter(f, COLUMNS)
        w.writeheader()
        w.writerows(rows)
    print('window %d.%d.%d to %d.%d.%d, %s: %d transfers (%s) -> %s' % (
        first[2], first[1], first[0], last[2], last[1], last[0], 'open' if is_open else 'CLOSED', len(rows),
        ', '.join('%s %d' % x for x in collections.Counter(r['how'] for r in rows).most_common()), out))
    if not is_open:
        print('The window has closed: the save no longer says where the players came from, so "from" is "?"\n'
              'and a free signing has a price like any other. Save before the window closes.')
    for row in rows[:20]:
        print('%13s %-7s %-24s %2d %-3s %2d  %-28s -> %s  %s' % (
            format(row['price'], ','), row['how'], row['player'][:24], row['age'], row['position'], row['rating'],
            row['from'][:28], row['to'], row['date']))
