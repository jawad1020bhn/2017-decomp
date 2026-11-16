"""Build the in-game calendar hooks in MLSimToDate.lua.

    python3 simdate_calendar.py --lua

The Lua module contains the resulting bytes and needs no assembler at runtime. The
calendar uses the game's own selected day; F8, F9 and F10 are polled only while its
Schedule screen is running in a foreground Master League. See test_simdate_calendar.py.
"""
import re
import sys

from keystone import Ks, KS_ARCH_X86, KS_MODE_32

CAVE, SIZE = 0x047d6550, 0x900
POLL, SELECT, TITLE, ARRIVED = CAVE, 0x047d6750, 0x047d6950, 0x047d6b50
# .link is RX in the executable: keep mutable state in the writable .text stub,
# rather than relying on Sider accidentally leaving a code page writable.
DATA, DATA_SIZE = 0x0298c0e0, 0x120
DATE, OWNER, ERROR, LATCH, READY, KEYFUNC = DATA, DATA + 4, DATA + 5, DATA + 6, DATA + 7, DATA + 8
LAST_DATE, LAST_ERROR = DATA + 0x0c, DATA + 0x10
# F10 switches stop-for-news at runtime; the day-loop routine reads NEWS each day.
NEWS, LAST_NEWS = DATA + 0x18, DATA + 0x19
BUFFER = DATA + 0x20
USER32, KEYNAME = 0x047d6be0, 0x047d6bf0
FMT_OFF, FMT_ON, FMT_ERROR = 0x047d6c10, 0x047d6c60, 0x047d6cc0
NEWS_ON, NEWS_OFF = 0x047d6d40, 0x047d6d50
POLL_SITE, TITLE_SITE = 0x03231ec5, 0x03230d54

# Poll only after both Schedule controls say they are ready. The replaced call
# has one thiscall argument; keep its result and all registers/flags intact.
POLL_SOURCE = '''
    push dword ptr [esp + 4]
    call 0x033c7f90
    pushfd
    pushad
    test al, al
    jz done
    cmp byte ptr [{ready}], 1
    jne done
    mov eax, dword ptr [0x0264f3e8]
    test eax, eax
    jz unfocused
    cmp dword ptr [eax + 0x20], 0x13  ; shortcut: this exe's two ML modes; use mode_kind for other builds
    je master_league
    cmp dword ptr [eax + 0x20], 0x28
    jne unfocused
master_league:
    mov eax, dword ptr [0x026503e0]
    test eax, eax
    jz unfocused
    cmp dword ptr [eax + 0x30], 0
    je unfocused
    call dword ptr [0x047d7948]       ; GetForegroundWindow
    test eax, eax
    jz unfocused
    push 0
    mov edx, esp
    push edx
    push eax
    call dword ptr [0x047d7974]       ; GetWindowThreadProcessId
    pop ebx
    test eax, eax
    jz unfocused
    call dword ptr [0x047d7170]       ; GetCurrentProcessId
    cmp eax, ebx
    jne unfocused
    mov ebx, dword ptr [{keyfunc}]
    test ebx, ebx
    jnz key_checks
    push {user32}
    call dword ptr [0x047d71e4]       ; GetModuleHandleA
    test eax, eax
    jz refresh_status
    push {keyname}
    push eax
    call dword ptr [0x047d71ec]       ; GetProcAddress
    test eax, eax
    jz refresh_status
    mov ebx, eax
    mov dword ptr [{keyfunc}], eax
key_checks:
    push 0x77                         ; F8: select the highlighted date
    call ebx
    test ax, 0x8000
    jnz f8_down
    and byte ptr [{latch}], 0xfe
    jmp f9
f8_down:
    test byte ptr [{latch}], 1
    jnz f9
    or byte ptr [{latch}], 1
    mov ecx, esi
    call {select}
f9:
    push 0x78                         ; F9: cancel
    call ebx
    test ax, 0x8000
    jnz f9_down
    and byte ptr [{latch}], 0xfd
    jmp f10
f9_down:
    test byte ptr [{latch}], 2
    jnz f10
    or byte ptr [{latch}], 2
    mov dword ptr [{date}], 0
    mov byte ptr [{owner}], 0
    mov byte ptr [{error}], 0
f10:
    push 0x79                         ; F10: stop for news on/off
    call ebx
    test ax, 0x8000
    jnz f10_down
    and byte ptr [{latch}], 0xfb
    jmp refresh_status
f10_down:
    test byte ptr [{latch}], 4
    jnz refresh_status
    or byte ptr [{latch}], 4
    xor byte ptr [{news}], 1
refresh_status:
    mov eax, dword ptr [{date}]
    cmp eax, dword ptr [{last_date}]
    jne refresh
    mov al, byte ptr [{error}]
    cmp al, byte ptr [{last_error}]
    jne refresh
    mov al, byte ptr [{news}]
    cmp al, byte ptr [{last_news}]
    je done
refresh:
    mov eax, dword ptr [{date}]
    mov dword ptr [{last_date}], eax
    mov al, byte ptr [{error}]
    mov byte ptr [{last_error}], al
    mov al, byte ptr [{news}]
    mov byte ptr [{last_news}], al
    push 0
    mov ecx, esi
    call 0x03230bb2                   ; also reflect changes from the optional file
    jmp done
unfocused:
    mov byte ptr [{latch}], 7          ; require a release after the game loses focus
done:
    popad
    popfd
    ret 4
'''

# The schedule spans one season, which can cross New Year. Its +0x68 is the
# season's first day; verify it against the career's start month before using it.
SELECT_SOURCE = '''
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi
    mov esi, ecx
    mov eax, dword ptr [0x026503e0]
    test eax, eax
    jz unavailable
    mov edi, dword ptr [eax + 0x30]
    test edi, edi
    jz unavailable
    mov ecx, dword ptr [esi + 0xa8]
    cmp ecx, 364
    ja invalid
    mov eax, dword ptr [edi + 0xc2cbb0]
    movzx ebx, ax
    cmp ebx, 364
    ja invalid
    shr eax, 16
    cmp eax, 2000
    jb invalid
    cmp eax, 2200
    ja invalid
    movzx edx, byte ptr [edi + 0xdcb690]
    cmp edx, 1
    jb invalid
    cmp edx, 12
    ja invalid
    dec edx
    imul edx, edx, 12
    mov edx, dword ptr [edx + 0x0216bb64]
    cmp edx, 364
    ja invalid
    cmp dword ptr [esi + 0x68], edx
    jne invalid
    push edx
    test edx, edx
    jnz season_end
    mov edx, 365
season_end:
    dec edx
    cmp dword ptr [esi + 0x6c], edx
    pop edx
    jne invalid
    cmp ebx, edx
    jae season_year
    dec eax
season_year:
    cmp ecx, edx
    jae selected_year
    inc eax
selected_year:
    cmp eax, 2000
    jb invalid
    cmp eax, 2200
    ja invalid
    shl eax, 16
    or eax, ecx
    cmp eax, dword ptr [edi + 0xc2cbb0]
    jbe invalid
    mov dword ptr [{date}], eax
    mov byte ptr [{owner}], 1
    mov byte ptr [{error}], 0
    mov eax, 1
    jmp finish
invalid:
    mov dword ptr [{date}], 0
    mov byte ptr [{owner}], 0
    mov byte ptr [{error}], 1
    mov eax, 1
    jmp finish
unavailable:
    xor eax, eax
finish:
    pop edi
    pop esi
    pop ebx
    mov esp, ebp
    pop ebp
    ret
'''

# This replaces only the headline's text-setter call, not the calendar's layout.
# sprintf_s's precision bounds the original game text before appending the status.
TITLE_SOURCE = '''
    push ebp
    mov ebp, esp
    sub esp, 12
    push ebx
    push esi
    push edi
    mov edi, ecx
    mov esi, dword ptr [ebp + 8]
    cmp byte ptr [{ready}], 1
    jne original
    mov eax, dword ptr [0x0264f3e8]
    test eax, eax
    jz original
    cmp dword ptr [eax + 0x20], 0x13
    je master_league
    cmp dword ptr [eax + 0x20], 0x28
    jne original
master_league:
    mov edx, {news_off}               ; the heading always shows whether it stops for news
    cmp byte ptr [{news}], 0
    je news_text
    mov edx, {news_on}
news_text:
    push edx
    cmp byte ptr [{error}], 0
    jne invalid
    mov eax, dword ptr [{date}]
    mov ebx, eax
    shr ebx, 16
    cmp ebx, 2000
    jb off
    cmp ebx, 2200
    ja off
    and eax, 0xffff
    cmp eax, 364
    ja off
    mov dword ptr [ebp - 4], ebx
    mov dword ptr [ebp - 8], eax
    lea eax, [ebp - 8]
    push eax
    lea eax, [ebp - 4]
    push eax
    lea eax, [ebp - 12]
    push eax
    call 0x038ae3cc
    add esp, 12
    movzx eax, byte ptr [ebp - 9]     ; day
    movzx edx, byte ptr [ebp - 10]    ; month
    push ebx
    push edx
    push eax
    push esi
    push {fmt_on}
    push 256
    push {buffer}
    call dword ptr [0x047d75cc]       ; sprintf_s
    add esp, 32                       ; four numbers, two texts
    jmp formatted
invalid:
    push esi
    push {fmt_error}
    jmp format_simple
off:
    push esi
    push {fmt_off}
format_simple:
    push 256
    push {buffer}
    call dword ptr [0x047d75cc]
    add esp, 20                       ; two numbers, two texts
formatted:
    test eax, eax
    js original
    mov esi, {buffer}
original:
    push esi
    mov ecx, edi
    call 0x033cdaf7
    pop edi
    pop esi
    pop ebx
    mov esp, ebp
    pop ebp
    ret 4
'''

# Reached only through the day-loop's past-date branch. Calendar selections are
# one-shot; dates supplied by the existing Lua/text settings stay persistent.
ARRIVED_SOURCE = '''
    cmp byte ptr [{owner}], 1
    jne switches
    mov dword ptr [{date}], 0
    mov byte ptr [{owner}], 0
switches:
    cmp byte ptr [esi + 0xdcb61c], 2
    jne normal
    mov byte ptr [esi + 0xdcb6a0], 0
    mov byte ptr [esi + 0xdcb61c], 0
normal:
    mov eax, dword ptr [0x026503e0]
    ret
'''


def build():
    values = dict(keyfunc=KEYFUNC, user32=USER32, keyname=KEYNAME, latch=LATCH,
                  select=SELECT, date=DATE, owner=OWNER, error=ERROR, ready=READY,
                  news=NEWS, last_news=LAST_NEWS, news_on=NEWS_ON, news_off=NEWS_OFF,
                  last_date=LAST_DATE, last_error=LAST_ERROR, fmt_off=FMT_OFF, fmt_on=FMT_ON, fmt_error=FMT_ERROR, buffer=BUFFER)
    # Mark even unused padding so a later mod cannot mistake our reserved cave for free space.
    result = bytearray([0xcc]) * SIZE
    occupied = set()

    def put(at, data, limit):
        assert at >= CAVE and at + len(data) <= limit <= CAVE + SIZE, (hex(at), len(data), hex(limit))
        for offset in range(at - CAVE, at - CAVE + len(data)):
            assert offset not in occupied, hex(CAVE + offset)
            occupied.add(offset)
        result[at - CAVE:at - CAVE + len(data)] = data

    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    for at, limit, source in ((POLL, SELECT, POLL_SOURCE), (SELECT, TITLE, SELECT_SOURCE),
                              (TITLE, ARRIVED, TITLE_SOURCE), (ARRIVED, USER32, ARRIVED_SOURCE)):
        text = '\n'.join(line.split(';')[0] for line in source.splitlines()).format(**values)
        code, _ = ks.asm(text, at)
        put(at, bytes(code), limit)
    for at, limit, text in ((USER32, KEYNAME, b'user32.dll\0'),
                            (KEYNAME, FMT_OFF, b'GetAsyncKeyState\0'),
                            (FMT_OFF, FMT_ON, b'%.64s | SIM OFF | F8 SET | %s\0'),
                            (FMT_ON, FMT_ERROR, b'%.64s | SIM %02u.%02u.%04u | F9 OFF | %s\0'),
                            (FMT_ERROR, NEWS_ON, b'%.64s | FUTURE DATE ONLY | SIM OFF | %s\0'),
                            (NEWS_ON, NEWS_OFF, b'NEWS ON\0'),
                            (NEWS_OFF, CAVE + SIZE, b'NEWS OFF\0')):
        put(at, text, limit)
    return bytes(result)


def lua_block():
    image = build()
    parts, previous = [], 0

    def hex_parts(data):
        h = data.hex()
        parts.extend('unhex("' + h[i:i + 96] + '")' for i in range(0, len(h), 96))

    for run in re.finditer(b'\xcc{16,}', image):
        hex_parts(image[previous:run.start()])
        parts.append('string.rep(string.char(0xcc), %d)' % (run.end() - run.start()))
        previous = run.end()
    hex_parts(image[previous:])
    return 'local CALENDAR = table.concat({\n    ' + ',\n    '.join(parts) + '\n})'


if __name__ == '__main__':
    if sys.argv[1:] != ['--lua']:
        sys.exit(__doc__)
    print(lua_block())
