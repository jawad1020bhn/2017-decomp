"""Runs MLSimToDate.lua outside the game, then runs the game's own day loop with its change.

    python3 test_simdate.py <PES2017.exe>      needs: pip install lupa unicorn keystone-engine capstone

The exe is loaded into a CPU emulator (../tools/emu.py) and the module runs as in
test_money.py. Then two pieces of the game run as machine code, with the module's routine
in: the stop test of the day loop (fcn_0360b713) and the day loop itself (fcn_0360dbf0).

What the game does on a day is NOT run (a day needs a whole career in memory). The four
steps of a day and the question "what is on this day" are answered by small Python
stand-ins that follow what was read in the game's code: the day end moves the date to the
next day with something on it, names the user's match of that day and asks the game's own
stop test; the match step simulates the user's match only if the Skip Match switch is on.

The text file with the date (MLSimToDate.txt) is a Python stand-in too: a table of file
contents, a clock, and the function the module registers, called by hand.

What this shows: the module's logic, that the routine is the source below, and that the
game's loop with the routine in walks a made-up calendar the way the module promises.
What it does not show: Sider, Windows, the running game, a real career, whether the
game's own switches do in the game what their code was read to do, and whether this Sider
calls a module when the game loads a file in the menus of a career.
"""
import random
import struct
import sys

import capstone
from keystone import Ks, KS_ARCH_X86, KS_MODE_32

from lupa.luajit21 import LuaRuntime

import test_money as tm
import simdate_calendar as sc
from test_money import Game, run, setting

MODULE = tm.MODULE.replace('MLMoney.lua', 'MLSimToDate.lua')
OTHERS = [tm.MODULE.replace('MLMoney.lua', n) for n in ('MLMoney.lua', 'MLTransfers.lua', 'MLYear.lua', 'MLSimMatch.lua')]
ROUTINE, SIZE, SITE = 0x047d6f60, 141, 0x0360b786
PLACES = ((SITE, 32), (0x0387a831, 16), (0x035fe5aa, 7), (0x038ae460, 7), (0x0387a865, 6),
          (0x038093f1, 18), (0x0251d454, 4), (0x0251d4a8, 4),
          (0x03231df4, 16), (0x03231a90, 21), (0x03231c9e, 35),
          (0x03231d41, 40), (0x033680c6, 38), (0x038ae33c, 32),
          (0x03231ea0, 37), (0x033b7cd2, 7),
          (sc.POLL_SITE, 16), (sc.TITLE_SITE, 16), (0x03230bb2, 16),
          (0x033c7f90, 16), (0x033cdaf7, 16), (0x038ae3cc, 16), (0x0216bb60, 144))
WRITES = [(sc.DATA, sc.DATA_SIZE), (sc.CAVE, sc.SIZE), (ROUTINE, SIZE),
          (sc.TITLE_SITE, 5), (sc.POLL_SITE, 5), (SITE, 5), (sc.READY, 1)]
MODE_OBJECT, MENU_OBJECT = 0x026503e0, 0x0264f3e8
STOP_TEST, DAY_LOOP, GAME_STOP, DAY_STATE = 0x0360b713, 0x0360dbf0, 0x0387a831, 0x03877938
DAY_BEGIN, MATCHES, AFTER, DAY_END = 0x0360a350, 0x03611277, 0x036101d9, 0x0360bf0c
DATE_OF_DAY = 0x038ae3cc                        # (&date, &year, &day number)
UNUSED = 0x0382b2b8                             # a function none of these runs reaches
TODAY, FLAG, SKIP, CALENDAR, MATCH = 0xc2cbb0, 0xdcb6a0, 0xdcb61c, 0xbfd52c, 0x537b8
INSTALLED = 'RESULT: installed. A Master League before %d.%d.%d runs on to that date when you advance; ' \
            'your matches on the way are simulated.'
NOTHING = 'RESULT: nothing written. '
FILE = b'.\\MLSimToDate.txt'
LIVE = ' The date is read from MLSimToDate.txt while the game runs.'
BEFORE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)

# The routine as written. At the call: esi = the career's data, bl = the game's answer.
SOURCE = '''
    cmp byte ptr [0x0298c0e7], 1            ; installation is complete?
    jne normal
    mov eax, dword ptr [0x264f3e8]          ; the mode
    test eax, eax
    jz normal
    cmp dword ptr [eax + 0x20], 0x13        ; Master League mode numbers 19 and 40
    je master_league
    cmp dword ptr [eax + 0x20], 0x28
    jne normal
master_league:
    mov eax, dword ptr [0x0298c0e0]         ; target (year and day)
    cmp dword ptr [esi + 0xc2cbb0], eax     ; year and day of today against the date
    jae past
    mov byte ptr [esi + 0xdcb6a0], 1        ; before the date: keep advancing,
    mov byte ptr [esi + 0xdcb61c], 2        ; and the user's match is skipped (2: set by this routine)
    mov eax, dword ptr [0x26503e0]
    mov eax, dword ptr [eax + 0x34]
    cmp word ptr [eax + 0x537b8], 0xffff    ; a match of the user today?
    je no_match
    mov al, {big}
    test al, al
    jnz ask
    xor bl, bl                              ; go on: the match is simulated
    jmp done
no_match:
    mov al, byte ptr [{news}]              ; F10 switches stop-for-news while the game runs
    and al, bl                              ; the game would stop today, and that is wanted
    jz ask
    mov byte ptr [esi + 0xdcb6a0], 0
    jmp ended
ask:
    mov eax, 0x0387a831                     ; the game's own stop test of its switch
    call eax
    test al, al
    jnz ended                               ; it switched off: today goes the normal way
    xor bl, bl
    jmp done
ended:
    mov byte ptr [esi + 0xdcb61c], 0
done:
    add dword ptr [esp], 0x13               ; back behind the game's own handling of the switch
    ret
past:
    jmp 0x047d6b50                         ; clears a calendar target and our switches
normal:
    mov eax, dword ptr [0x26503e0]          ; what the replaced call did
    ret
'''


def assembled(big):
    code, _ = Ks(KS_ARCH_X86, KS_MODE_32).asm('\n'.join(l.split(';')[0] for l in SOURCE.splitlines()).format(
        big=int(big), news=sc.NEWS), ROUTINE)
    return bytes(code)


def with_date(source, year, month, day, news='true', big='false'):
    for name, new in (('SIM_YEAR', year), ('SIM_MONTH', month), ('SIM_DAY', day),
                      ('STOP_FOR_NEWS', news), ('STOP_AT_BIG_MATCHES', big)):
        source = setting(source, name, str(new))
    return source


def run_live(g, source, files, clock, sticky=True, sider_dir=b'.\\', register_failure=False):
    """As test_money.run for one module, with what the text file needs: io.open on `files`
    (path -> bytes), os.time from clock[0], ctx.register. -> (log lines, reads, writes,
    registered functions by event, paths opened)"""
    lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
    lines, reads, writes, handlers, opened = [], [], [], {}, []

    def read(address, count):
        reads.append((int(address), int(count)))
        return g.read(int(address), int(count))

    def write(address, data):
        writes.append((int(address), len(data)))
        if sticky(int(address)) if callable(sticky) else sticky:
            tm.poke(g, int(address), data)

    def open_file(path):
        opened.append(path)
        return files.get(path)

    def register(name, fn):
        if register_failure:
            raise RuntimeError('simulated ctx.register failure')
        assert name not in handlers
        handlers[name] = fn

    lua.eval('''function(source, log, read, write, open, time, register, sider_dir)
        local env = { assert = assert, table = table, pairs = pairs, ipairs = ipairs, string = string,
                      math = math, tonumber = tonumber, tostring = tostring, unpack = unpack,
                      error = error, _VERSION = _VERSION, type = type,
                      os = { time = time, clock = os.clock, date = os.date },
                      io = { open = function(path, mode)
                          local text = open(path)
                          if text == nil then return nil end
                          return { close = function() end,
                                   read = function(self, n)                 -- nil at the end, as Lua does
                                       if text == "" then return nil end
                                       return string.sub(text, 1, n)
                                   end }
                      end },
                      log = log, memory = { read = read, write = write } }
        local chunk = assert(loadstring(source, "module"))
        setfenv(chunk, env)
        local module = chunk()
        module.init({ sider_dir = sider_dir, register = function(name, fn) register(name, fn) end })
    end''')(source.encode(), lambda text: lines.append(text.decode()), read, write, open_file,
            lambda: clock[0], register, sider_dir)
    return lines, reads, writes, handlers, opened


class World:
    """A career as far as the stop test and the day loop look at it, and a made-up calendar."""

    def __init__(self, g, kind=0x13):
        self.g = g
        g.free_all()
        self.mode = g.alloc(size=0xe00000)
        self.other = g.alloc(size=MATCH + 0x100)
        obj, menu, task = g.alloc(size=0x40), g.alloc(size=0x40), g.alloc(size=0x60)
        self.this = g.alloc(struct.pack('<4I', 0, 0, 0, task))
        g.write(obj + 0x30, struct.pack('<2I', self.mode, self.other))
        g.write(menu + 0x20, struct.pack('<I', kind))
        g.write(MODE_OBJECT, struct.pack('<I', obj))
        g.write(MENU_OBJECT, struct.pack('<I', menu))
        self.state_now = 1                              # what the day-state stand-in answers

    def byte(self, o, value=None):
        if value is None:
            return self.g.read(self.mode + o, 1)[0]
        self.g.write(self.mode + o, bytes([value]))

    def today(self, year=None, index=None):
        if year is None:
            return struct.unpack('<2H', self.g.read(self.mode + TODAY, 4))[::-1]
        self.g.write(self.mode + TODAY, struct.pack('<2H', index, year))

    def match(self, there):
        self.g.write(self.other + MATCH, struct.pack('<H', 1 if there else 0xffff))

    def stop_test(self):
        return self.g.call(STOP_TEST, [], ecx=self.this) & 0xff


def date_of(g, year, index):
    """The game's own date of a day number -> (year, month, day), and its four bytes."""
    out = g.alloc(size=4)
    g.call(DATE_OF_DAY, [out, g.alloc(struct.pack('<I', year)), g.alloc(struct.pack('<I', index))])
    raw = g.read(out, 4)
    return (struct.unpack('<H', raw[:2])[0], raw[2], raw[3]), raw


def date_text(g, n, base_year=2024):
    """Day n of a made-up calendar as the text of the file, from the game's own date code."""
    (year, month, day), _ = date_of(g, base_year + n // 365, n % 365)
    return b'%d.%d.%d' % (day, month, year)


def calendar(seed, days=900):
    """A made-up run of days: nothing / something / news (the game stops) / a match of the
    user, plus days on which the game's own switch ends, and matches the game calls big."""
    r = random.Random(seed)
    kinds = [r.choices(('empty', 'plain', 'news', 'match'), (50, 22, 8, 20))[0] for _ in range(days)]
    kinds[0], kinds[-1] = 'plain', 'news'
    events = {n for n, k in enumerate(kinds) if k in ('plain', 'news') and r.random() < 0.15}
    big = {n for n, k in enumerate(kinds) if k == 'match' and r.random() < 0.3}
    return kinds, events, big


def promised(kinds, events, big, start, target, news, stop_big, presses):
    """What the module promises, worked out without the game: the days on which the main
    menu shows, and who played each match."""
    menus, played, n = [], {}, start
    while len(menus) < presses:
        if kinds[n] == 'match' and n not in played:
            played[n] = 'user'
        while True:
            n = next(i for i in range(n + 1, len(kinds)) if kinds[i] != 'empty')
            if n >= target:
                stop = kinds[n] in ('news', 'match')
            elif kinds[n] == 'match':
                stop = stop_big and n in big
                if not stop:
                    played[n] = 'sim'
            else:
                stop = kinds[n] == 'news' and (news or n in events)
            if stop:
                break
        menus.append(n)
    return menus, played


def walk(w, kinds, events, big, start, presses, base_year=2024):
    """The game's day loop on the made-up calendar. -> (days of the main menu, who played
    each match, what the after-match step saw, faults)."""
    g, played, seen, faults, menus = w.g, {}, [], [], []
    now = [start]

    def state(n):
        k = kinds[n]
        return 0 if k == 'empty' else 2 if k == 'news' or (k == 'match' and n not in played) else 1

    def game_stop(game=None, arg=None):                 # fcn_0387a831 as read
        n = now[0]
        if not w.byte(FLAG):
            return 0
        if (n in big) if kinds[n] == 'match' and n not in played else (n in events):
            w.byte(FLAG, 0)
            return 1
        return 0

    def day_end(game, arg):                             # fcn_0360bf0c as far as it matters here
        n = next(i for i in range(now[0] + 1, len(kinds)) if state(i))
        now[0] = n
        w.today(base_year + n // 365, n % 365)
        w.match(kinds[n] == 'match' and n not in played)
        game_stop()
        return 0

    def matches(game, arg):                             # fcn_03611277 -> fcn_03708fd5
        n = now[0]
        if kinds[n] == 'match' and n not in played:
            if w.byte(SKIP):
                played[n] = 'sim'
            else:
                faults.append('match of day %d passed and not played' % n)
        return 0

    def after(game, arg):
        seen.append((now[0], w.byte(FLAG), w.byte(SKIP)))
        return 0

    for at, fn in ((DAY_STATE, lambda game, arg: state(now[0])), (GAME_STOP, game_stop), (DAY_END, day_end),
                   (MATCHES, matches), (AFTER, after), (DAY_BEGIN, lambda game, arg: 0)):
        g.replace(at, fn)
    w.today(base_year + start // 365, start % 365)
    for _ in range(presses):
        n = now[0]
        if kinds[n] == 'match' and n not in played:
            played[n] = 'user'                          # the user plays the match of today
        while True:                                     # one press of "advance"
            g.call(DAY_LOOP, [], ecx=w.this)
            if state(now[0]) == 2:                      # the main menu; the game clears Skip Match here
                if w.byte(FLAG):
                    faults.append('main menu on day %d with the switch on' % now[0])
                if w.byte(SKIP):
                    faults.append('main menu on day %d with Skip Match on' % now[0])
                w.byte(SKIP, 0)
                break
        menus.append(now[0])
    for at in (DAY_STATE, GAME_STOP, DAY_END, MATCHES, AFTER, DAY_BEGIN):
        del g.replaced[at]
    return menus, played, seen, faults


def main(exe):
    source = open(MODULE, encoding='utf-8').read()
    image = Game(exe)
    image.replace(UNUSED, lambda game, arg: 0)          # so that the list of stand-ins is never empty
    sites = (SITE, sc.POLL_SITE, sc.TITLE_SITE)
    original = {at: image.read(at, 5) for at in sites}
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    assert sc.lua_block() in source, 'calendar bytes differ from simdate_calendar.py'

    def fresh():
        for at in sites:
            tm.poke(image, at, original[at])
        tm.poke(image, ROUTINE, bytes(SIZE))
        tm.poke(image, sc.CAVE, bytes(sc.SIZE))
        tm.poke(image, sc.DATA, bytes(sc.DATA_SIZE))

    def install(*args, **kw):
        fresh()
        lines, reads, writes = run(image, with_date(source, *args, **kw))
        assert lines[-1].startswith(INSTALLED % (args[2], args[1], args[0])), lines[-1]
        return lines, reads, writes

    # 1. as it comes: installed but off. Then: the writes, routines, calls and state.
    fresh()
    lines, reads, writes = run(image, source)
    assert lines[-1].startswith('RESULT: installed, switched off.')
    assert writes == WRITES and image.read(sc.DATE, 4) == bytes(4)
    image.replace(DAY_STATE, lambda game, arg: 2)
    for mode in (0x13, 0x28):
        w = World(image, mode)
        w.today(2025, 30)
        w.match(True)
        assert w.stop_test() == 1 and not w.byte(FLAG) and not w.byte(SKIP)
        w.byte(SKIP, 1)                       # the user's own Skip Match is not ours
        assert w.stop_test() == 1 and w.byte(SKIP) == 1
    del image.replaced[DAY_STATE]
    cases = 0
    for year, month, day in ((2024, 7, 1), (2025, 1, 15), (2031, 12, 31), (2000, 1, 1), (2200, 2, 28)):
        for news in ('true', 'false'):
            for big in ('true', 'false'):
                lines, reads, writes = install(year, month, day, news=news, big=big)
                assert writes == WRITES and tm.inside(reads, PLACES + ((ROUTINE, SIZE),
                                                (sc.CAVE, sc.SIZE), (sc.DATA, sc.DATA_SIZE)))
                assert sum('as expected' in l for l in lines) == len(PLACES)
                assert sum(l.endswith('empty') for l in lines) == 3
                target = year << 16 | BEFORE[month - 1] + day - 1
                assert image.read(sc.DATE, 4) == struct.pack('<I', target)
                assert image.read(sc.CAVE, sc.SIZE) == sc.build()
                assert image.read(ROUTINE, SIZE) == assembled(big == 'true')
                call = next(md.disasm(image.read(SITE, 5), SITE))
                assert (call.mnemonic, call.op_str) == ('call', hex(ROUTINE))
                assert ('It stops for news.' in lines[-1]) == (news == 'true')
                assert ('It stops at big matches.' in lines[-1]) == (big == 'true')
                cases += 1
    print('ok 1: as it comes the module is installed but off; %d settings write only the checked state, '
          'two code blocks and three calls; the emitted machine code matches its source' % cases)

    # 2. every day of the year: the module's number of the date is the game's
    year = 2027
    for index in range(365):
        (y, month, day), _ = date_of(image, year, index)
        image.free_all()
        install(year, month, day)
        assert struct.unpack('<I', image.read(sc.DATE, 4))[0] == year << 16 | index, (month, day)
    print('ok 2: for each of the 365 days the game\'s own date code and the module agree on the day number')

    # 3. the game's stop test, one day at a time (the day state and, on match days, the game's
    #    own stop test are stand-ins; on days without a match the game's own stop test runs)
    install(2025, 3, 1, news='true', big='false')
    w = World(image)
    asked = []
    image.replace(DAY_STATE, lambda game, arg: w.state_now)

    def one(year, index, state, match, flag=0, skip=0, kind=None, stand_in=None):
        w.today(year, index)
        w.state_now = state
        w.match(match)
        w.byte(FLAG, flag)
        w.byte(SKIP, skip)
        del asked[:]
        if stand_in is not None:
            def answer(game, arg):
                asked.append(1)
                if stand_in:
                    w.byte(FLAG, 0)
                return stand_in
            image.replace(GAME_STOP, answer)
        stop = w.stop_test()
        image.replaced.pop(GAME_STOP, None)
        return stop, w.byte(FLAG), w.byte(SKIP)

    assert one(2025, 30, 1, False) == (0, 1, 2)                 # before the date, nothing on: on, go on
    assert one(2025, 30, 2, False) == (1, 0, 0)                 # news: stop, both off
    assert one(2025, 30, 2, True) == (0, 1, 2)                  # a match: go on, it is simulated
    assert one(2024, 364, 2, True) == (0, 1, 2)                 # the year counts before the day
    assert one(2025, 58, 2, True) == (0, 1, 2)                  # 28 February: the last day before
    assert one(2025, 59, 2, True) == (1, 0, 0)                  # 1 March, a match: stop, the normal way
    assert one(2025, 59, 1, False) == (0, 0, 0)
    assert one(2025, 59, 1, False, flag=1, skip=2) == (0, 0, 0)     # arriving: both off
    assert one(2025, 59, 2, True, flag=0, skip=2) == (1, 0, 0)      # arriving, the game's switch ended already
    assert one(2025, 59, 1, False, flag=1, skip=1) == (0, 1, 1)     # not set by the routine: left alone
    assert one(2025, 59, 1, False, flag=1, skip=1, stand_in=1) == (1, 0, 1) and asked   # and the game's test is asked
    assert one(2025, 59, 1, False, flag=0, skip=1) == (0, 0, 1)     # the user's own Skip Match is left alone
    assert one(2026, 0, 2, True, flag=1, skip=2) == (1, 0, 0)       # a later year
    assert one(2025, 30, 2, True, stand_in=1) == (0, 1, 2) and not asked    # big matches not asked for
    # a day the game's switch ends on: a transfer window opens (event 3) on a day without a match
    _, raw = date_of(image, 2025, 30)
    image.write(w.mode + CALENDAR + 30 * 0x214 + 0x194, struct.pack('<I', 3) + raw)
    assert one(2025, 30, 1, False) == (0, 0, 0)                 # the game's test ran and switched off
    assert one(2025, 31, 1, False) == (0, 1, 2)                 # the next day: on again
    selector = struct.unpack('<I', image.read(MENU_OBJECT, 4))[0]
    image.write(selector + 0x20, struct.pack('<I', 0x28))
    assert one(2025, 30, 2, True) == (0, 1, 2)                 # the second ML mode
    for kind in list(range(0x46)) + [0xffffffff]:                # raw mode numbers, not kinds
        if kind in (0x13, 0x28):
            continue
        image.write(selector + 0x20, struct.pack('<I', kind))
        assert one(2025, 30, 2, True) == (1, 0, 0) and one(2025, 30, 1, False) == (0, 0, 0)
        assert one(2025, 30, 1, True, skip=1) == (0, 0, 1)
        assert one(2025, 30, 1, True, flag=1, stand_in=1) == (1, 0, 0) and asked
    image.write(MENU_OBJECT, struct.pack('<I', 0))              # no mode at all
    assert one(2025, 30, 2, True) == (1, 0, 0) and one(2025, 30, 1, False) == (0, 0, 0)
    image.write(MENU_OBJECT, struct.pack('<I', selector))       # back to mode 19
    image.write(selector + 0x20, struct.pack('<I', 0x13))
    image.write(sc.NEWS, b'\0')                  # what F10 does in Schedule: news off
    assert one(2025, 30, 2, False, stand_in=0) == (0, 1, 2) and asked       # the routine reads the byte
    image.write(sc.NEWS, b'\1')
    assert one(2025, 30, 2, False) == (1, 0, 0)                             # and stops again
    install(2025, 3, 1, news='false', big='true')
    w = World(image)
    image.replace(DAY_STATE, lambda game, arg: w.state_now)
    assert one(2025, 30, 2, False, stand_in=0) == (0, 1, 2) and asked       # news not wanted: go on
    assert one(2025, 30, 2, True, stand_in=0) == (0, 1, 2) and asked        # not a big match: go on
    assert one(2025, 30, 2, True, stand_in=1) == (1, 0, 0) and asked        # a big match: stop
    assert one(2025, 30, 1, False, stand_in=1) == (0, 0, 0) and asked       # the switch ends, no stop
    del image.replaced[DAY_STATE]
    print('ok 3: the game\'s stop test with the routine in: before the date it switches both on and goes '
          'on over a match, stops for news if asked to, lets the game\'s own test end the run (a transfer '
          'window opening, run for real); on the date both go off; other modes are as without the module')

    # 4. the game's day loop on made-up calendars
    runs = matches_simulated = 0
    for seed in range(6):
        kinds, events, big = calendar(seed)
        first = next(n for n, k in enumerate(kinds) if k == 'match')
        fresh()
        control = walk(World(image), kinds, events, big, 0, 40)
        assert control[0] == [n for n, k in enumerate(kinds) if k in ('news', 'match') and n > 0][:40]
        assert set(control[1].values()) == {'user'} and not control[3]
        assert all(not flag and not skip for _, flag, skip in control[2])
        for kind in (0x0c, 0x12, 0x14):                 # other raw modes with the module in: the same
            install(2026, 6, 1)
            assert walk(World(image, kind), kinds, events, big, 0, 40) == control
        install(2024, 1, 1)                             # a date that is past: the same
        assert walk(World(image), kinds, events, big, 0, 40) == control
        for target in (200, 365, 366, 500, first, first + 1):
            for news in (True, False):
                for stop_big in (True, False):
                    for start in (0, first):
                        (y, month, day), _ = date_of(image, 2024 + target // 365, target % 365)
                        image.free_all()
                        install(y, month, day, news=str(news).lower(), big=str(stop_big).lower())
                        menus, played, seen, faults = walk(World(image), kinds, events, big, start, 90)
                        assert not faults, faults
                        want = promised(kinds, events, big, start, target, news, stop_big, 90)
                        assert (menus, played) == want, (seed, target, news, stop_big, start)
                        before = [n for n in menus if n < target]
                        if not news and not stop_big:
                            assert all(kinds[n] == 'news' and n in events for n in before)
                        if not stop_big:
                            assert all(v == 'sim' for n, v in played.items() if start < n < target)
                        arrival = next(n for n in menus if n >= target)
                        assert arrival == next(n for n in range(max(target, start + 1), len(kinds))
                                               if kinds[n] in ('news', 'match'))
                        assert played.get(arrival) in (None, 'user')
                        assert all(v == 'user' for n, v in played.items() if n >= target)
                        assert all(not flag and not skip for n, flag, skip in seen if n >= target)
                        matches_simulated += sum(v == 'sim' for v in played.values())
                        runs += 1
    print('ok 4: the game\'s day loop on 6 made-up calendars, %d runs: every match of the user before the '
          'date is simulated (%d in all) and none is passed unplayed, the stops before the date are the '
          'ones asked for, it arrives on the first day on or after the date on which the game stops, that '
          'day\'s match is left to the user, both switches are off at every main menu and after the date; '
          'without the module, in another mode or with a past date the loop stops at every match'
          % (runs, matches_simulated))

    # 5. refusals
    refused = 0
    for name, new in (('SIM_YEAR', '1999'), ('SIM_YEAR', '2201'), ('SIM_YEAR', '2025.5'), ('SIM_YEAR', '"2025"'),
                      ('SIM_MONTH', '0'), ('SIM_MONTH', '13'), ('SIM_MONTH', 'nil'), ('SIM_DAY', '0'),
                      ('SIM_DAY', '32'), ('SIM_DAY', '1.5'), ('SIM_DAY', 'true')):
        fresh()
        text = setting(with_date(source, 2025, 3, 1), name, new)
        lines, reads, writes = run(image, text)
        assert lines[-1].startswith(NOTHING + 'Settings: SIM_YEAR') and not reads and not writes, (name, new)
        refused += 1
    for month, day in ((2, 29), (2, 30), (4, 31), (6, 31), (9, 31), (11, 31)):
        lines, reads, writes = run(image, with_date(source, 2028, month, day))
        assert lines[-1].startswith(NOTHING + 'Settings: SIM_YEAR') and not reads and not writes
        refused += 1
    for name in ('STOP_FOR_NEWS', 'STOP_AT_BIG_MATCHES'):
        for new in ('1', 'nil', '"true"'):
            lines, reads, writes = run(image, setting(with_date(source, 2025, 3, 1), name, new))
            assert lines[-1].startswith(NOTHING + 'Settings: STOP_FOR_NEWS') and not reads and not writes
            refused += 1
    count = 0
    for at, n in PLACES + ((ROUTINE, SIZE), (sc.CAVE, sc.SIZE), (sc.DATA, sc.DATA_SIZE)):
        for k in range(n):
            fresh()
            was = image.read(at + k, 1)
            tm.poke(image, at + k, bytes([was[0] ^ 0x02]))
            lines, reads, writes = run(image, with_date(source, 2025, 3, 1))
            tm.poke(image, at + k, was)
            assert lines[-1].startswith(NOTHING + 'This game does not hold') and not writes, (hex(at), k)
            assert sum('DIFFERENT' in l or 'NOT EMPTY' in l for l in lines) == 1
            count += 1
    for at, text, expected in ((sc.DATA, 'calendar state', WRITES[:1]),
                               (sc.CAVE, 'calendar', WRITES[:2]),
                               (ROUTINE, 'the routine', WRITES[:3])):
        fresh()
        lines, reads, writes = run(image, with_date(source, 2025, 3, 1), sticky=lambda a: a != at)
        assert lines[-1].startswith('RESULT: a change did not go in (' + text + ')') and writes == expected
        assert all(image.read(site, 5) == original[site] for site in sites)
    for at in (sc.TITLE_SITE, sc.POLL_SITE, SITE):
        fresh()
        lines, reads, writes = run(image, with_date(source, 2025, 3, 1), sticky=lambda a: a != at)
        assert lines[-1].startswith('RESULT: a change did not go in. Hooks restored.'), lines[-1]
        assert all(image.read(site, 5) == original[site] for site in sites)
    fresh()
    lines, _, _ = run(image, with_date(source, 2025, 3, 1), sticky=lambda a: a != sc.READY)
    assert lines[-1].startswith('RESULT: the module could not be enabled.')
    assert image.read(sc.READY, 1) == b'\0'
    # The bundled Sider has no pcall: a thrown write must leave the activation byte off.
    for at in (sc.DATA, sc.CAVE, ROUTINE, sc.TITLE_SITE, sc.POLL_SITE, SITE, sc.READY):
        fresh()
        def throws(address):
            if address == at:
                raise RuntimeError('simulated memory.write exception')
            return True
        try:
            run(image, with_date(source, 2025, 3, 1), sticky=throws)
            assert False, 'write should have raised'
        except RuntimeError as error:
            assert 'simulated memory.write exception' in str(error)
        assert image.read(sc.READY, 1) == b'\0', hex(at)
    fresh()
    try:
        run_live(image, source, {FILE: b'off'}, [1000], register_failure=True)
        assert False, 'register should have raised'
    except RuntimeError as error:
        assert 'simulated ctx.register failure' in str(error)
    assert image.read(sc.READY, 1) == b'\0'
    fresh()
    failed_files, failed_clock = {FILE: b'off'}, [1000]
    lines, _, writes, handlers, _ = run_live(image, source, failed_files, failed_clock,
                                              sticky=lambda a: a != sc.READY)
    assert lines[-1].startswith('RESULT: the module could not be enabled.')
    failed_files[FILE], failed_clock[0] = b'2025-03-01', 1001
    before = list(writes)
    handlers[b'livecpk_make_key']({}, b'file.bin')
    assert writes == before and image.read(sc.DATE, 4) == bytes(4)
    fresh()
    install(2025, 3, 1)
    lines, reads, writes = run(image, with_date(source, 2025, 3, 1))            # a second time
    assert lines[-1].startswith(NOTHING + 'This game does not hold') and not writes
    print('ok 5: %d faulty settings (29 February among them) are refused before anything is read; with one '
          'byte of a checked place or of the free memory changed (%d cases) nothing is written and the '
          'place is named; if the routine does not go in the call is not changed; a second install is '
          'refused' % (refused, count))

    # 6. the date from the text file
    def probe():
        """A match day of 31 January 2025 in a Master League: (stop, switch, Skip Match)."""
        w = World(image)
        image.replace(DAY_STATE, lambda game, arg: 2)
        w.today(2025, 30)
        w.match(True)
        got = w.stop_test(), w.byte(FLAG), w.byte(SKIP)
        del image.replaced[DAY_STATE]
        return got

    def date_in():
        return struct.unpack('<I', image.read(sc.DATE, 4))[0]

    clock, march15 = [1000], 2025 << 16 | 73
    assert date_of(image, 2025, 73)[0] == (2025, 3, 15)
    fresh()
    lines, reads, writes, handlers, opened = run_live(image, source, {}, clock)         # no file, no date
    assert lines[-1].startswith('RESULT: installed, switched off.') and writes == WRITES and not handlers
    assert opened == [FILE], opened
    assert lines[1] == 'date file: .\\MLSimToDate.txt  not there, the date in MLSimToDate.lua is used'
    fresh()
    lines, reads, writes, handlers, opened = run_live(image, with_date(source, 2025, 3, 15), {}, clock)
    assert lines[-1] == INSTALLED % (15, 3, 2025) + ' It stops for news.' and not handlers and date_in() == march15
    fresh()
    lines, reads, writes, handlers, opened = run_live(image, with_date(source, 2025, 3, 15), {}, clock,
                                                      sider_dir=b'C:\\sider')
    assert opened == [b'C:\\sider\\MLSimToDate.txt']
    fresh()
    lines, reads, writes, handlers, opened = run_live(image, source, {FILE: b'off'}, clock)
    assert lines[1] == 'date file: .\\MLSimToDate.txt  found'
    forms = 0
    for text in (b'2025-03-15', b'2025-03-15\r\n', b'15.3.2025', b'15/03/2025\n', b'2025 3 15', b'  2025-3-15  ',
                 b'\xef\xbb\xbf15.3.2025\r\n'):
        for lua_date in ((0, 1, 1), (2031, 6, 6)):                  # the file wins over the Lua file
            fresh()
            lines, reads, writes, handlers, opened = run_live(image, with_date(source, *lua_date), {FILE: text}, clock)
            assert lines[-1] == INSTALLED % (15, 3, 2025) + ' It stops for news.' + LIVE, lines[-1]
            assert date_in() == march15 and list(handlers) == [b'livecpk_make_key'], text
            assert writes == WRITES and probe() == (0, 1, 2)
            forms += 1
    for text in (b'off', b'OFF\r\n', b' Off ', b'', b'0', b'  \n'):
        fresh()
        lines, reads, writes, handlers, opened = run_live(image, with_date(source, 2031, 6, 6), {FILE: text}, clock)
        assert lines[-1].startswith('RESULT: installed, switched off.'), lines[-1]
        assert lines[-1].endswith(LIVE) and date_in() == 0 and list(handlers) == [b'livecpk_make_key']
        assert probe() == (1, 0, 0)                                 # in, and the game as it was
        forms += 1
    bad = (b'tomorrow', b'2025-02-29', b'1999-12-31', b'2201-01-01', b'32.1.2025', b'2025-13-01', b'1.2',
           b'2025-03-15 x', b'15.3.25', b'off now', b'2025-03-00')
    for text in bad:
        fresh()
        lines, reads, writes, handlers, opened = run_live(image, with_date(source, 2031, 6, 6), {FILE: text}, clock)
        assert any('invalid date; starting switched off' in line for line in lines), (text, lines)
        assert lines[-1].startswith('RESULT: installed, switched off.')
        assert writes == WRITES and list(handlers) == [b'livecpk_make_key'] and date_in() == 0

    # while the game runs: the registered function, called as Sider would on a file load
    fresh()
    files = {FILE: b'off'}
    lines, reads, writes, handlers, opened = run_live(image, source, files, clock)
    look = handlers[b'livecpk_make_key']
    del writes[:], opened[:]

    def loaded(text, seconds=1, calls=3):
        """The file now holds `text`; `seconds` later the game loads `calls` files.
        -> (new log lines, writes, times the file was opened)"""
        if text is None:
            files.pop(FILE, None)
        else:
            files[FILE] = text
        clock[0] += seconds
        before = len(lines)
        del writes[:], opened[:]
        for _ in range(calls):
            assert look({}, b'common/some/file.bin') is None            # no key of its own: Sider goes on
        allowed = ((sc.DATE, 6),)
        assert all(w in allowed for w in writes) and all(o == FILE for o in opened)
        return lines[before:], len(writes), len(opened)

    assert loaded(b'off') == ([], 0, 1) and probe() == (1, 0, 0)
    assert loaded(b'1.3.2025') == (['MLSimToDate: the date is now 1.3.2025 (from MLSimToDate.txt)'], 1, 1)
    assert date_in() == 2025 << 16 | 59 and probe() == (0, 1, 2)
    assert loaded(b'15.3.2025', seconds=0) == ([], 0, 0) and date_in() == 2025 << 16 | 59   # the same second
    assert loaded(b'15.3.2025') == (['MLSimToDate: the date is now 15.3.2025 (from MLSimToDate.txt)'], 1, 1)
    assert date_in() == march15
    assert loaded(b'15.3.2025') == ([], 0, 1)                           # nothing new
    assert loaded(b'2025-03-15\n') == ([], 0, 1) and date_in() == march15      # the same date, written otherwise
    # A changed file overrides a later calendar choice, even if its date matches an earlier file value.
    image.write(sc.DATE, struct.pack('<I', 2025 << 16 | 90))
    image.write(sc.OWNER, b'\1\1')
    assert loaded(b'15.3.2025') == (['MLSimToDate: the date is now 15.3.2025 (from MLSimToDate.txt)'], 1, 1)
    assert date_in() == march15 and image.read(sc.OWNER, 2) == b'\0\0'
    got = loaded(b'soon')
    assert got[1:] == (0, 1) and len(got[0]) == 1 and 'holds neither a date nor the word off' in got[0][0]
    assert loaded(b'soon') == ([], 0, 1) and date_in() == march15       # said once, the date stays
    assert loaded(b'29.2.2028')[1] == 0 and date_in() == march15
    assert loaded(None) == ([], 0, 1) and date_in() == march15          # the file is gone: the date stays
    assert loaded(b'31.12.2024') == (['MLSimToDate: the date is now 31.12.2024 (from MLSimToDate.txt)'], 1, 1)
    assert date_in() == 2024 << 16 | 364 and probe() == (1, 0, 0)       # a date that is past
    assert loaded(b'off') == (['MLSimToDate: switched off (from MLSimToDate.txt)'], 1, 1) and date_in() == 0
    assert image.read(ROUTINE, SIZE) == assembled(False)        # date changes never rewrite code
    fresh()
    files = {FILE: b'off'}
    can_write = [True]
    lines, reads, writes, handlers, opened = run_live(image, source, files, clock,
                                                       sticky=lambda a: a != sc.DATE or can_write[0])
    can_write[0] = False
    look = handlers[b'livecpk_make_key']
    assert loaded(b'1.3.2025') == (['MLSimToDate: the new date did not go in; send this log'], 1, 1)
    can_write[0] = True
    assert loaded(b'1.3.2025') == (['MLSimToDate: the date is now 1.3.2025 (from MLSimToDate.txt)'], 1, 1)

    # a run, a new date, a second run: the game's day loop on a made-up calendar
    kinds, events, big = calendar(3)
    fresh()
    files = {FILE: date_text(image, 200)}
    lines, reads, writes, handlers, opened = run_live(image, with_date(source, 0, 1, 1, news='false'), files, clock)
    look = handlers[b'livecpk_make_key']
    day, presses = 0, 0
    for target in (200, 201, 520, 100, 640):
        if target != 200:
            assert len(loaded(date_text(image, target))[0]) == 1
        while True:
            menus, played, seen, faults = walk(World(image), kinds, events, big, day, 1)
            assert not faults and (menus, played) == promised(kinds, events, big, day, target, False, False, 1)
            day, presses = menus[0], presses + 1
            if day >= target:
                break
    assert day >= 640 and presses < 40
    print('ok 6: the date from MLSimToDate.txt: %d ways to write a date or "off" are understood and %d are '
          'refused; the file wins over the date in the Lua file; without the file nothing is registered; '
          'while the game runs a new date goes in on the next file load, at most once a second, and '
          'calendar ownership is cleared; a faulty or missing file leaves the date as it was; the day loop '
          'runs to a first date, then on to a later one (%d presses for 640 days)' % (forms, len(bad), presses))

    # 7. with the other four modules
    mine = with_date(source, 2025, 3, 1)
    others = [open(p, encoding='utf-8').read() for p in OTHERS]
    for order in ([mine] + others, others + [mine], others[:2] + [mine] + others[2:]):
        del image
        image = Game(exe)
        lines, reads, writes = run(image, tm.SPLIT.join(order))
        got = [l for l in lines if l.startswith('RESULT')]
        assert len(got) == 5 and all(l.startswith('RESULT: installed.') for l in got), got
        assert image.read(ROUTINE, SIZE) == assembled(False)
        w = World(image)
        image.replace(DAY_STATE, lambda game, arg: 2)
        w.today(2025, 30)
        w.match(True)
        assert w.stop_test() == 0 and w.byte(FLAG) == 1 and w.byte(SKIP) == 2
    print('ok 7: with MLMoney.lua, MLTransfers.lua, MLYear.lua and MLSimMatch.lua in the same game, above, '
          'below or between them, all five are installed and the routine works')


if __name__ == '__main__':
    main(sys.argv[1])
