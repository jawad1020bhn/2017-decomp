#!/usr/bin/env python3
"""Checks window_transfers.py against the four saves of `../ML saves/`.

    python3 test_transfers.py <PES2017.exe>          needs: pip install lupa unicorn

The list read from ONE save must be the moves that two saves of the same career show
(the same players, the same clubs), with the prices where they belong.
What this does not show: a January window, a second season, a career without MLMoney.lua
(none of the saves is one), and that a price by the formula is the one the game had.
"""
import csv
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE]
import money_cave as mc                          # noqa: E402
import test_money                                # noqa: E402
import window_report as wr                       # noqa: E402
import window_transfers as wt                    # noqa: E402

SAVES = os.path.join(HERE, '..', 'ML saves')
FIRST = [os.path.join(SAVES, 'ML00000013 (%s)' % x) for x in ('before', 'after')]            # 1 July, 15 September
SECOND = [os.path.join(SAVES, '2nd test', 'ML00000013 (%s)' % x) for x in ('before', 'after')]   # 1 July, 31 August


def moved(before, after, none):
    """What two saves show: (name, club before, club after) of every player whose club changed, in order."""
    return sorted((wr.name(r), before.teams.get(wr.club(r), none), after.teams[wr.club(after.players[k])])
                  for k, r in before.players.items() if wr.club(r) != wr.club(after.players[k]))


def main(exe):
    t, rate = test_money.settings(test_money.two_modules()), wr.Rater(exe)

    # 1. a save of the last day of the window
    rows, span, is_open = wt.transfers(t, SECOND[1], rate)
    before, after = wr.Save(SECOND[0]), wr.Save(SECOND[1])
    assert span == ((2024, 7, 1), (2024, 8, 31)) and is_open and len(rows) == 438
    assert sorted((r['player'], r['from'], r['to']) for r in rows) == moved(before, after, 'no club')
    for row in rows:
        assert (row['how'] == 'free') == (row['price'] == 0 and row['from'] == 'no club') or row['how'] == 'paid', row
        assert span[0] < tuple(map(int, row['date'].split('-'))) <= span[1]
    assert [r['price'] for r in rows] == sorted((r['price'] for r in rows), reverse=True)
    user = after.teams[after.user]
    paid = {r['player']: r['price'] for r in rows if r['how'] == 'paid'}
    assert paid == {'Endrick': 55263500, 'David Neres': 32752800, 'Kaoru Mitoma': 26283500,
                    'Mathías Olivera': 9188700, 'Nikita Contini': 399900, 'David Spinelli': 295700,
                    'Mauro Icardi': 0, 'Malcom': 0}                          # the eight account lines of the save
    assert set(paid) == {r['player'] for r in rows if user in (r['from'], r['to'])}
    position = {r['player']: r['position'] for r in rows if r['how'] == 'paid'}
    assert [position[x] for x in ('Mauro Icardi', 'Kaoru Mitoma', 'David Neres', 'Mathías Olivera', 'Nikita Contini')] \
        == ['CF', 'LWF', 'RWF', 'LB', 'GK']
    by_move = {(wr.name(r), after.teams.get(wr.club(r))): (k, r) for k, r in after.players.items()}
    for row in rows:
        k, r = by_move[row['player'], row['to']]
        assert (row['age'], row['rating']) == (wr.age(r), rate(r))
        if row['how'] == 'formula':
            assert row['price'] == 100 * mc.fee(t, rate(r), wr.age(r), wr.popularity(r), wr.position(r), k) > 0
    how = [sum(r['how'] == x for r in rows) for x in ('formula', 'free', 'paid')]
    assert how == [254, 176, 8]
    print('ok 1: the save of 31 August alone gives the %d moves that the saves of 1 July and 31 August show '
          'together, each with the club left and the club joined; %d have a price by the formula, %d were '
          'without a club and cost nothing, %d are deals of %s with the amounts of its account lines; the '
          'most expensive is first (%s, %s)' % (len(rows), how[0], how[1], how[2], user, rows[0]['player'],
                                                format(rows[0]['price'], ',')))

    # 2. a save from after the window
    rows, span, is_open = wt.transfers(t, FIRST[1], rate)
    two = moved(wr.Save(FIRST[0]), wr.Save(FIRST[1]), None)
    assert span == ((2024, 7, 1), (2024, 8, 31)) and not is_open and len(rows) == 511
    assert sorted((r['player'], r['to']) for r in rows) == [(name, new) for name, old, new in two]
    known = [r for r in rows if r['from'] != '?']
    assert all((r['player'], r['from'], r['to']) in two for r in known) and len(known) == 5
    assert not any(r['how'] == 'free' for r in rows)
    print('ok 2: the save of 15 September, after the window: the same %d players as its two saves show, each '
          'with the club joined; the club left is still in the save for %d of them and is "?" for the '
          'others, and none is called free' % (len(rows), len(known)))

    # 3. the first day of a career, the windows, the file
    for path in (FIRST[0], SECOND[0]):
        assert wt.transfers(t, path, rate) == ([], ((2024, 7, 1), (2024, 8, 31)), True)
    july, january = ((2030, 7, 1), (2030, 8, 31)), ((2030, 1, 1), (2030, 1, 31))
    assert [wt.window(d, 2030) for d in (0, 30, 31, 180, 181, 242, 243, 364)] == [january] * 4 + [july] * 4
    with tempfile.TemporaryDirectory() as folder:
        out = os.path.join(folder, 'x.csv')
        text = subprocess.run([sys.executable, os.path.join(HERE, 'window_transfers.py'), exe, SECOND[1], out],
                              check=True, capture_output=True, text=True).stdout
        with open(out, 'rb') as f:
            assert f.read(3) == b'\xef\xbb\xbf'                   # without it Excel shows "MathÃ­as"
        with open(out, newline='', encoding='utf-8-sig') as f:
            lines = list(csv.DictReader(f))
    assert len(lines) == 438 and tuple(lines[0]) == wt.COLUMNS and lines[0]['player'] == 'Endrick'
    assert lines[0]['price'] == '55263500' and lines[-1]['price'] == '0' and '438 transfers' in text
    assert any(r['player'] == 'Mathías Olivera' and r['to'] == 'RB Leipzig' for r in lines)      # letters outside ASCII
    print('ok 3: a save of the first day of a new career lists nothing (the 19,921 contracts dated that day '
          'are not signings); the window is January up to 30 June and July to August after; the file has '
          'the nine columns and the 438 rows, the most expensive first')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
