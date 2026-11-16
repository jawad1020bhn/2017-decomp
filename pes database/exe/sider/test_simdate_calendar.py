"""Exercise MLSimToDate's in-game Schedule hooks without Windows or a running game.

    python3 test_simdate_calendar.py <PES2017.exe>

Requires lupa, unicorn, keystone-engine and capstone. Runs the real game input
handler and date conversion, with stand-ins for Windows, the controller and UI.
This is not a test of Sider, the real game UI, keyboard mapping or an actual save.
"""
import struct
import sys

from unicorn import UC_HOOK_CODE, UC_PROT_EXEC, UC_PROT_READ, UC_PROT_WRITE
from unicorn.x86_const import UC_X86_REG_EAX, UC_X86_REG_EIP, UC_X86_REG_ESP

import simdate_calendar as sc
import test_money as tm
import test_simdate as sd
from layout import off

SCHEDULE_INPUT, READINESS = 0x03231df4, 0x033c7f90
INPUT_LOOKUP, REFRESH, SET_TEXT = 0x03dbf687, 0x03230bb2, 0x033cdaf7
IMPORTS = {'foreground': 0x047d7948, 'window_pid': 0x047d7974, 'own_pid': 0x047d7170,
           'module': 0x047d71e4, 'proc': 0x047d71ec, 'sprintf': 0x047d75cc}


def number(g, address):
    return struct.unpack('<I', g.read(address, 4))[0]


def put(g, address, value):
    g.write(address, struct.pack('<I', value & 0xffffffff))


def string(g, address, limit=512):
    return g.read(address, limit).split(b'\0', 1)[0]


def api(g, address, slot, argc, callback):
    """A fake Windows function: stdcall except argc=0 for the cdecl sprintf_s."""
    g.write(address, b'\xc3')
    if slot:
        put(g, slot, address)

    def call(mu, _address, _size, _user):
        esp = mu.reg_read(UC_X86_REG_ESP)
        ret = number(g, esp)
        arg = lambda i: number(g, esp + 4 + 4 * i)
        result = callback(arg)
        mu.reg_write(UC_X86_REG_EAX, result & 0xffffffff)
        mu.reg_write(UC_X86_REG_ESP, esp + 4 + 4 * argc)
        mu.reg_write(UC_X86_REG_EIP, ret)

    g.mu.hook_add(UC_HOOK_CODE, call, begin=address, end=address)


def main(exe):
    g = sd.Game(exe)
    # The stubbed calls below must occupy the actual import slots in this executable.
    names = {'foreground': b'GetForegroundWindow', 'window_pid': b'GetWindowThreadProcessId',
             'own_pid': b'GetCurrentProcessId', 'module': b'GetModuleHandleA',
             'proc': b'GetProcAddress', 'sprintf': b'sprintf_s'}
    for name, slot in IMPORTS.items():
        rva = struct.unpack_from('<I', g.exe, off(slot))[0]
        at = off(0x400000 + rva + 2)
        assert g.exe[at:at + 64].split(b'\0', 1)[0] == names[name], name
    pe = struct.unpack_from('<I', g.exe, 0x3c)[0]
    count = struct.unpack_from('<H', g.exe, pe + 6)[0]
    headers = pe + 24 + struct.unpack_from('<H', g.exe, pe + 20)[0]
    flags = {g.exe[headers + 40*i:headers + 40*i + 8].rstrip(b'\0'):
             struct.unpack_from('<I', g.exe, headers + 40*i + 36)[0] for i in range(count)}
    assert flags[b'.link'] & 0xe0000000 == 0x60000000      # read/execute
    assert flags[b'.text'] & 0xe0000000 == 0xc0000000      # read/write
    source = open(sd.MODULE, encoding='utf-8').read()
    lines, _, writes = tm.run(g, source)
    assert writes == sd.WRITES and lines[-1].startswith('RESULT: installed, switched off.')
    assert g.read(sc.CAVE, sc.SIZE) == sc.build()
    # Match the relevant PE page protections: .link is RX, .text is RW.
    # Emulated game code must not write to its own code page.
    g.mu.mem_protect(0x047d6000, 0x1000, UC_PROT_READ | UC_PROT_EXEC)
    g.mu.mem_protect(0x0298c000, 0x1000, UC_PROT_READ | UC_PROT_WRITE)

    w = sd.World(g)
    schedule, parent, pad, vtable, ui = [g.alloc(size=n) for n in (0x200, 0x100, 0x40, 0x40, 0x40)]
    zero_button = g.alloc(bytes.fromhex('31c0c20800'))       # xor eax,eax; ret 8
    put(g, schedule + 0x58, parent)
    put(g, parent + 0xdc, 1)
    put(g, parent + 0x7c, ui)
    put(g, pad, vtable)
    put(g, vtable + 0x1c, zero_button)

    state = {'focus': True, 'same_pid': True, 'f8': False, 'f9': False,
             'first_ready': True, 'second_ready': True, 'pad': True,
             'lookups': 0, 'keys': 0, 'refresh': 0, 'text': []}
    pid = 1234
    api(g, 0x00301800, IMPORTS['foreground'], 0, lambda a: 0x1234 if state['focus'] else 0)

    def window_pid(a):
        assert a(0) == 0x1234
        put(g, a(1), pid if state['same_pid'] else pid + 1)
        return 1

    api(g, 0x00301810, IMPORTS['window_pid'], 2, window_pid)
    api(g, 0x00301820, IMPORTS['own_pid'], 0, lambda a: pid)

    def module(a):
        assert string(g, a(0)) == b'user32.dll'
        state['lookups'] += 1
        return 0x10000

    def proc(a):
        assert a(0) == 0x10000 and string(g, a(1)) == b'GetAsyncKeyState'
        return 0x00301850

    def key(a):
        assert a(0) in (0x77, 0x78)
        state['keys'] += 1
        return 0x8000 if state['f8' if a(0) == 0x77 else 'f9'] else 0

    api(g, 0x00301830, IMPORTS['module'], 1, module)
    api(g, 0x00301840, IMPORTS['proc'], 2, proc)
    api(g, 0x00301850, None, 1, key)

    def sprintf(a):
        buf, size, fmt = a(0), a(1), string(g, a(2)).decode('ascii')
        original = string(g, a(3)).decode('ascii')
        if '%02u' in fmt:
            result = fmt % (original, a(4), a(5), a(6))
        else:
            result = fmt % original
        assert buf == sc.BUFFER and len(result) < size == 256
        g.write(buf, result.encode('ascii') + b'\0')
        return len(result)

    api(g, 0x00301860, IMPORTS['sprintf'], 0, sprintf)

    def input_lookup(game, arg):
        assert number(game, arg(0)) == 1
        return pad if state['pad'] else 0

    def ready(game, arg):
        assert game.reg('ecx') == ui
        if arg(0) == 0x01fe3334:
            return int(state['first_ready'])
        assert arg(0) == 0x01fe3340
        return int(state['second_ready'])

    def refresh(game, arg):
        assert game.reg('ecx') == schedule and arg(0) == 0
        state['refresh'] += 1
        return 0

    def set_text(game, arg):
        state['text'].append((game.reg('ecx'), string(game, arg(0))))
        return 0x2345

    g.replace(INPUT_LOOKUP, input_lookup)
    g.replace(READINESS, ready)
    g.replace(REFRESH, refresh)
    g.replace(SET_TEXT, set_text)

    def mode(value):
        put(g, number(g, sd.MENU_OBJECT) + 0x20, value)

    def setup(year, today, month=7):
        w.today(year, today)
        g.write(w.mode + 0xdcb690, bytes([month]))
        first = sd.BEFORE[month - 1]
        put(g, schedule + 0x68, first)
        put(g, schedule + 0x6c, (first - 1) % 365)

    def target():
        return number(g, sc.DATE)

    def press(f8=False, f9=False):
        state['f8'], state['f9'] = f8, f9
        return g.call(SCHEDULE_INPUT, [], ecx=schedule)

    def status():
        return g.read(sc.OWNER, 2)

    # Selected day is relative to the season, not necessarily today's calendar year.
    cases = 0
    for month in (1, 7):
        first = sd.BEFORE[month - 1]
        for year in (2000, 2024, 2200):
            for today in (0, 30, 58, 59, 180, 181, 364):
                setup(year, today, month)
                _, today_raw = sd.date_of(g, year, today)
                season = g.alloc(size=4)
                g.call(0x038ae33c, [season, g.alloc(today_raw)])  # game's own season-start date
                raw = g.read(season, 4)
                season_year = struct.unpack('<H', raw[:2])[0]
                assert (season_year, raw[2], raw[3]) == (year - (today < first), month, 1)
                for selected in range(365):
                    put(g, schedule + 0xa8, selected)
                    expected_year = season_year + (selected < first)
                    expected = expected_year << 16 | selected
                    valid = 2000 <= expected_year <= 2200 and expected > (year << 16 | today)
                    assert g.call(sc.SELECT, [], ecx=schedule) == 1
                    assert (target(), status()) == ((expected, b'\1\0') if valid else (0, b'\0\1'))
                    cases += 1
    for cursor in (365, 999, 0xffffffff):
        setup(2025, 0, 1)
        put(g, schedule + 0xa8, cursor)
        assert g.call(sc.SELECT, [], ecx=schedule) == 1 and (target(), status()) == (0, b'\0\1')
    for month, first in ((0, 0), (13, 0), (7, 0), (1, 181)):
        g.write(w.mode + 0xdcb690, bytes([month]))
        put(g, schedule + 0x68, first)
        assert g.call(sc.SELECT, [], ecx=schedule) == 1 and (target(), status()) == (0, b'\0\1')
    setup(2025, 0, 1)
    put(g, schedule + 0x6c, 0)                    # wrong end of season
    assert g.call(sc.SELECT, [], ecx=schedule) == 1 and (target(), status()) == (0, b'\0\1')
    print('ok 1: %d calendar dates, Jan/July seasons, New Year, year limits, past/same days and invalid bounds' % cases)

    # Exercise the real Schedule input handler, not just the injected routine.
    setup(2024, 364)
    put(g, schedule + 0xa8, 0)
    put(g, sc.DATE, 0)
    put(g, sc.LAST_DATE, 0)
    g.write(sc.OWNER, b'\0\0\0')
    g.write(sc.LAST_ERROR, b'\0')
    press()
    press(f8=True)
    assert target() == 2025 << 16 and status() == b'\1\0' and state['refresh'] == 1
    assert state['lookups'] == 1
    put(g, schedule + 0xa8, 1)
    press(f8=True)                                  # hold does not reselect
    assert target() == 2025 << 16 and state['refresh'] == 1
    press()
    press(f8=True)
    assert target() == (2025 << 16 | 1) and state['refresh'] == 2 and state['lookups'] == 1
    press()
    press(f9=True)
    assert (target(), status(), state['refresh']) == (0, b'\0\0', 3)
    press(f9=True)
    assert state['refresh'] == 3
    press()
    put(g, schedule + 0xa8, 364)                    # same day is refused
    press(f8=True)
    assert (target(), status(), state['refresh']) == (0, b'\0\1', 4)
    press()
    print('ok 2: real Schedule handler sets, replaces and cancels a date once per key press; same day is refused')

    # Neither background input nor an incomplete screen may arm or cancel a run.
    for blocked in ('focus', 'same_pid', 'first_ready', 'second_ready', 'pad'):
        put(g, sc.DATE, 2025 << 16 | 30)
        g.write(sc.OWNER, b'\1\0\0')
        state[blocked] = False
        keys, refreshes = state['keys'], state['refresh']
        press(f8=True, f9=True)
        assert (target(), state['keys'], state['refresh']) == (2025 << 16 | 30, keys, refreshes), blocked
        state[blocked] = True
        press()                                     # release keys before testing the next condition
    for raw_mode in list(range(0x46)) + [0xffffffff]:
        if raw_mode in (0x13, 0x28):
            continue                                 # raw 0x0c is NOT Master League kind 12
        mode(raw_mode)
        put(g, sc.DATE, 2025 << 16 | 30)
        keys = state['keys']
        press(f8=True, f9=True)
        assert target() == 2025 << 16 | 30 and state['keys'] == keys, raw_mode
        mode(0x13)
        press()
    for null_at in (sd.MENU_OBJECT, sd.MODE_OBJECT, number(g, sd.MODE_OBJECT) + 0x30):
        old = number(g, null_at)
        put(g, null_at, 0)
        keys = state['keys']
        press(f8=True, f9=True)
        assert target() == 2025 << 16 | 30 and state['keys'] == keys
        put(g, null_at, old)
        press()
    # After refocusing, a held key must be released before it can be used again.
    state['focus'] = False
    press(f8=True)
    state['focus'] = True
    press(f8=True)
    assert target() == 2025 << 16 | 30
    press()
    put(g, schedule + 0xa8, 1)
    press(f8=True)
    assert target() == 2025 << 16 | 1
    press()
    # Cancel wins if both keys are pressed, including a configured file target.
    put(g, sc.DATE, 2025 << 16 | 30)
    g.write(sc.OWNER, b'\0\0')
    press(f8=True, f9=True)
    assert target() == 0 and status() == b'\0\0'
    press()
    mode(0x28)                                      # the second Master League mode
    put(g, sc.DATE, 0)
    press(f8=True)
    assert target() == 2025 << 16 | 1 and status() == b'\1\0'
    press()
    mode(0x13)
    print('ok 3: both ML modes work; no shortcuts in other modes, background or before UI readiness')

    # The original game's text setter receives a bounded, visible status.
    widget = g.alloc(size=0x80)
    original = g.alloc(b'July 2024/2025\0', size=512)

    def title():
        got = g.call(sc.TITLE, [original], ecx=widget)
        assert got == 0x2345 and state['text'][-1][0] == widget
        return state['text'][-1][1]

    put(g, sc.DATE, 0)
    g.write(sc.ERROR, b'\0')
    assert title() == b'July 2024/2025 | SIM OFF | F8 SET'
    put(g, sc.DATE, 2025 << 16 | 73)
    assert title() == b'July 2024/2025 | SIM 15.03.2025 | F9 OFF'
    g.write(sc.ERROR, b'\1')
    assert title() == b'July 2024/2025 | FUTURE DATE ONLY | SIM OFF'
    mode(0x28)
    g.write(sc.ERROR, b'\0')
    assert title() == b'July 2024/2025 | SIM 15.03.2025 | F9 OFF'
    mode(0x0c)
    assert title() == b'July 2024/2025'
    mode(0x13)
    g.write(original, b'x' * 300 + b'\0')
    assert title() == b'x' * 64 + b' | SIM 15.03.2025 | F9 OFF'
    # A file update while the screen is open must not leave a stale headline.
    put(g, sc.LAST_DATE, 2025 << 16 | 73)
    g.write(sc.LAST_ERROR, b'\0')
    put(g, sc.DATE, 2025 << 16 | 74)
    refreshes = state['refresh']
    press()
    assert state['refresh'] == refreshes + 1
    press()
    assert state['refresh'] == refreshes + 1
    assert title() == b'x' * 64 + b' | SIM 16.03.2025 | F9 OFF'
    print('ok 4: headline shows current, invalid and off states, including live file changes; other modes are untouched')

    # If Sider aborts a partial installation, all installed hooks behave as their originals.
    g.write(sc.READY, b'\0')
    setup(2024, 0, 1)
    put(g, schedule + 0xa8, 20)
    put(g, sc.DATE, 2024 << 16 | 20)
    g.write(sc.OWNER, b'\1\0')
    keys, refreshes = state['keys'], state['refresh']
    press(f8=True, f9=True)
    assert target() == 2024 << 16 | 20 and (state['keys'], state['refresh']) == (keys, refreshes)
    assert title() == b'x' * 300
    g.replace(sd.DAY_STATE, lambda game, arg: 2)
    w.match(True)
    w.byte(sd.FLAG, 0)
    w.byte(sd.SKIP, 0)
    assert w.stop_test() == 1 and not w.byte(sd.FLAG) and not w.byte(sd.SKIP)
    del g.replaced[sd.DAY_STATE]
    g.write(sc.READY, b'\1')
    press()
    print('ok 5: before activation, all three hooks preserve the unmodified game behavior')

    # An in-game selection is consumed on reaching the date; legacy settings persist.
    setup(2024, 0, 1)
    put(g, schedule + 0xa8, 20)
    press(f8=True)
    assert (target(), status()) == (2024 << 16 | 20, b'\1\0')
    kinds = ['plain'] * 50
    for day in (2, 5, 20):
        kinds[day] = 'match'
    menus, played, seen, faults = sd.walk(w, kinds, set(), set(), 0, 1)
    assert menus == [20] and played == {2: 'sim', 5: 'sim'} and not faults
    assert target() == 0 and status() == b'\0\0' and not w.byte(sd.FLAG) and not w.byte(sd.SKIP)
    # Mode 40 has the same behavior as mode 19, not just the same UI.
    mode(0x28)
    setup(2024, 0, 1)
    press()
    press(f8=True)
    menus, played, _, faults = sd.walk(w, kinds, set(), set(), 0, 1)
    assert menus == [20] and played == {2: 'sim', 5: 'sim'} and not faults and target() == 0
    mode(0x13)
    put(g, sc.DATE, 2024 << 16 | 20)
    g.write(sc.OWNER, b'\0')
    w.today(2024, 20)
    w.byte(sd.FLAG, 1)
    w.byte(sd.SKIP, 2)
    g.replace(sd.DAY_STATE, lambda game, arg: 2)
    assert w.stop_test() == 1 and target() == 2024 << 16 | 20
    assert not w.byte(sd.FLAG) and not w.byte(sd.SKIP)
    print('ok 6: both ML modes run to a selected date and clear it; configured dates stay persistent')


if __name__ == '__main__':
    main(sys.argv[1])
