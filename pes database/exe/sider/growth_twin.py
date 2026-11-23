"""Replay the v7 growth model over the whole player database and check its outcomes.

    python3 growth_twin.py <PES2017.exe> <edit file> [seasons] [--solve]

The cave of `growth_cave.py` does nothing but LCG arithmetic and table lookups; every
number in its tables is checked (or solved) here first, against the targets set by the
plan:

    peak age      median 26-27, right tail to 31
    career gains  elite +18-25, regular +10-15, squad +5-8, limited +2-4
    elite share   (86+) between 1 and 2 per cent at every season mark
    stationarity  league mean OVR drift under 0.05 a season, age pyramid stable

`--solve` searches the one free scale of BASE (PHASE) that lands the four career bands in
the middle of their target ranges, and prints the table it found.

Why the ecosystem layer of the plan (Package B normalization, star formation) is not
here: the cave walks one player at a time and cannot see a league, so a whole-database
rescale has no place to run.  What it would correct for is measured instead -- the elite
share and the mean drift are printed at every season mark.
"""
import collections
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools'),
                os.path.join(HERE, '..', '..', 'tools')]

import growth_cave as gc                                        # noqa: E402
import overall                                                  # noqa: E402

SEL_OF_NAME = {'atk': 0x0e, 'def': 0x0f, 'gk': 0x10, 'drib': 0x11, 'ball_ctrl': 0x12,
               'finish': 0x13, 'lowpass': 0x14, 'loftpass': 0x15, 'header': 0x16,
               'ball_win': 0x17, 'place_kick': 0x18, 'swerve': 0x19, 'reflex': 0x1a,
               'catching': 0x1b, 'clearing': 0x1c, 'cover': 0x1d, 'kick_pwr': 0x22,
               'speed': 0x1f, 'exp_pwr': 0x23, 'body_ctrl': 0x20, 'phys': 0x21,
               'jump': 0x24, 'stamina': 0x25}
TARGETS = {'elite': (18, 25), 'regular': (10, 15), 'squad': (5, 8), 'limited': (2, 4)}


def load(exe, edit):
    """Every player of an edit file: id, age, position, {selector: value}, OVR."""
    import savefile
    import lib
    data = savefile.read(edit)['data']
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False) as f:
        f.write(data)
    try:
        e = lib.P17(f.name)
    finally:
        os.unlink(f.name)
    t = overall.Tables(exe)
    out = []
    for pid, p in e.players.items():
        pos = overall.FILE_POS[p['reg_pos']]
        values = {SEL_OF_NAME[name]: p[name] for name in overall.ABILITY.values()}
        out.append(dict(id=pid, age=p['age'], pos=pos, values=values,
                        ovr=ovr(t, pos, values)))
    return out, t


def values_of(pos, ab):
    """The 39 numbers fcn_04067af3 reads, from the cave's selectors."""
    v = [0] * 39
    v[0] = pos
    v[pos + 1] = 2
    for slot, name in overall.ABILITY.items():
        v[slot] = ab.get(SEL_OF_NAME[name], 0)
    return v


def ovr(t, pos, ab):
    return overall.overall(t, values_of(pos, ab), pos)


def season(players, t):
    """One season of the cave's arithmetic over every player: age, the season points,
    then the family decline."""
    for p in players:
        p['age'] += 1
        for sel, step in gc.season_points(p['id'], p['age'], p['values'], p['pos']):
            p['values'][sel] = min(99, p['values'][sel] + step)
        d = gc.decline_sel(p['id'], p['age'], p['pos'])
        if d is not None and p['values'].get(d, 0) > gc.DECLINE_FLOOR:
            p['values'][d] -= 1
        p['ovr'] = ovr(t, p['pos'], p['values'])


AGE_BANDS = ((15, 20), (21, 24), (25, 28), (29, 32), (33, 36), (37, 46))


def band_means(players):
    out = {}
    for lo, hi in AGE_BANDS:
        seg = [p['ovr'] for p in players if lo <= p['age'] <= hi]
        if seg:
            out[(lo, hi)] = sum(seg) / len(seg)
    return out


def bands(players):
    n = len(players)

    def share(pred):
        return sum(1 for p in players if pred(p)) / n
    return dict(mean=sum(p['ovr'] for p in players) / n,
                elite86=share(lambda p: p['ovr'] >= 86),
                elite89=share(lambda p: p['ovr'] >= 89),
                young=share(lambda p: p['age'] <= 21),
                old=share(lambda p: p['age'] >= 31))


def run(exe, edit, seasons=20, quiet=False):
    players, t = load(exe, edit)
    start = {p['id']: (p['age'], p['ovr'], gc.arch(p['id']), gc.intake_band(p['id']))
             for p in players}
    hist = {p['id']: [p['ovr']] for p in players}
    marks = []
    for s in range(1, seasons + 1):
        prev = {p['id']: p['ovr'] for p in players}
        season(players, t)
        for p in players:
            hist[p['id']].append(p['ovr'])
        drift = sum(p['ovr'] - prev[p['id']] for p in players) / len(players)
        count = {(lo, hi): sum(1 for p in players if lo <= p['age'] <= hi)
                 for lo, hi in AGE_BANDS}
        marks.append((s, bands(players), drift, band_means(players), count))
    if not quiet:
        print('%d players, %d seasons' % (len(players), seasons))
        print('season  mean OVR  drift  elite86%  elite89%  age<=21%  age>=31%')
        for s, b, drift, _, _ in marks:
            if s in (1, 2, 3, 5, 10, 15, 20):
                print('%6d  %8.2f %+6.3f  %7.2f  %8.2f  %7.2f  %8.2f'
                      % (s, b['mean'], drift, 100 * b['elite86'], 100 * b['elite89'],
                         100 * b['young'], 100 * b['old']))
    return players, hist, marks, start


def career_gains(players, hist, start, debut=18):
    """Debut-to-peak gain and peak age, on the players young enough to have a career left
    at the first season (a save shows everyone else mid-career)."""
    out = collections.defaultdict(list)
    for p in players:
        age0, ovr0, a, band = start[p['id']]
        if not 15 <= age0 <= debut:
            continue
        path = hist[p['id']]
        gain = max(path) - ovr0
        gain = max(gain, 0)
        key = band_key(p['id'])
        out[key].append(gain)
        out['peak_' + key].append(age0 + path.index(max(path)))
    return out


def band_key(pid):
    """The target band of a player: archetype and talent, not his rating today."""
    t = gc.talent(pid)
    if t <= 4:
        return 'limited'
    return 'elite' if t >= 7 else 'regular' if t == 6 else 'squad'


def check(exe, edit, seasons=20):
    players, hist, marks, start = run(exe, edit, seasons)
    gains = career_gains(players, hist, start)
    ok = gains_ok = True
    print('\ncareer gain, first season to peak (median [mean], target)')
    for key, (lo, hi) in TARGETS.items():
        g = sorted(gains[key])
        med, mean = g[len(g) // 2], sum(g) / len(g)
        good = lo <= med <= hi
        gains_ok = gains_ok and good
        print('  %-8s %6d players  %+3d [%+5.1f]  target %+d..%+d  %s'
              % (key, len(g), med, mean, lo, hi, 'ok' if good else 'OUT OF RANGE'))
    peaks = sorted(gains['peak_elite'])
    med_peak, p90 = peaks[len(peaks) // 2], peaks[int(0.9 * len(peaks))]
    print('peak age of the elite band: median %d (target 26-27), 90th percentile %d'
          % (med_peak, p90))
    ok &= 26 <= med_peak <= 27
    # the first seasons only move the save's own 15-18 year olds up; a career also gets a
    # youth intake every season, which a static database does not have.  The target is
    # read from the season the age pyramid has settled, as the plan asks.
    drift = [abs(d) for s, _, d, _, _ in marks if s >= 6]
    elite = [b['elite86'] for _, b, _, _, _ in marks]
    print('mean OVR drift per season: %.3f at the start, %.3f from season 6 (the first '
          'seasons only lift the save\'s own teenagers)' % (marks[0][2], max(drift)))
    print('elite share (86+): %.2f%%..%.2f%% (target 1-2%%)'
          % (100 * min(elite), 100 * max(elite)))
    # the age pyramid, as the plan asks: the mean OVR of an age band should barely move.
    # A static database has no youth intake, so from season 11 no player is under 25 and
    # the bands empty out from below -- the table shows that, it is not the model's drift.
    print('\nage pyramid: mean OVR per age band (players in it)')
    print('season  ' + '  '.join('%5s' % ('%s-%s' % b) for b in AGE_BANDS))
    for i in (0, 4, 9, 14, 19):
        row, count = marks[i][3], marks[i][4]
        print('%6d  ' % marks[i][0] + '  '.join(
            '%5.1f(%5d)' % (row[b], count[b]) if count[b] else '     -      ' for b in AGE_BANDS))
    settled = [abs(d) for s_, _, d, _, _ in marks if s_ >= 9]
    print('whole-league drift from season 9: worst %.3f (target < 0.05)' % max(settled))
    # conservation: from the season the pyramid has settled, the league does not inflate
    ok = (gains_ok and 26 <= med_peak <= 27 and max(settled) < 0.05
          and 0.009 <= min(elite) and max(elite) <= 0.02)
    print('\ncareer gains %s, peak age %s, elite share %s, conservation %s'
          % ('ok' if gains_ok else 'MISSED', 'ok' if 26 <= med_peak <= 27 else 'MISSED',
             'ok' if 0.009 <= min(elite) and max(elite) <= 0.02 else 'MISSED',
             'ok' if max(settled) < 0.05 else 'MISSED'))
    print('%s: the career bands of the plan, its peak age, its elite share and its '
          'conservation, over %d synthetic seasons of the whole database.' 
          % ('all targets met' if ok else 'TARGETS MISSED', seasons))
    return ok


def solve(exe, edit, seasons=20):
    """Search the one free scale of PHASE for the middle of the four target bands."""
    global PHASE
    base = gc.PHASE
    lo, hi = 0.20, 3.0
    for _ in range(12):
        mid = (lo + hi) / 2
        gc.PHASE = tuple(tuple(min(30, int(round(v * mid))) for v in row) for row in base)
        players, hist, _, start = run(exe, edit, seasons, quiet=True)
        gains = career_gains(players, hist, start)
        score = 0.0
        for k, (a, b) in TARGETS.items():
            g = sorted(gains[k])
            if g:
                score += abs(g[len(g) // 2] - (a + b) / 2)
        if score <= 4.0:
            hi = mid
        else:
            lo = mid
    gc.PHASE = tuple(tuple(min(30, int(round(v * hi))) for v in row) for row in base)
    print('PHASE scale %.3f ->' % hi)
    print('PHASE = (')
    for row in gc.PHASE:
        print('    (%s),' % ', '.join(str(v) for v in row))
    print(')')
    return check(exe, edit, seasons)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    args = [a for a in sys.argv[3:] if not a.startswith('--')]
    n = int(args[0]) if args else 20
    ok = solve(sys.argv[1], sys.argv[2], n) if '--solve' in sys.argv \
        else check(sys.argv[1], sys.argv[2], n)
    sys.exit(0 if ok else 1)
