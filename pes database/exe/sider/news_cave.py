"""Build MLNews.lua's presentation-only Master League ticker hook.

    python news_cave.py --lua

Only the first temporary headline copy in MainMenuInfoFL is prefixed. The native
news list, its shuffle/RNG calls and all career records stay untouched. Only diagnostic counters
survive a draw, never story-selection state. PES owns and frees the temporary string.
"""
import re
import sys

from keystone import Ks, KS_ARCH_X86, KS_MODE_32

# The checked zero run also houses SimToDate at 03fc8000..03fc88ff.
# .trace is RWX; buffers/locals live on the stack, never in this code block.
CAVE, SIZE = 0x03fc8900, 0xa00
STATE, STATE_SIZE = 0x0298c2f0, 48  # writable diagnostic counters, after Growth tables; never story input
COPY, BUILD, DATE, NAME, LEAGUE = CAVE, CAVE + 0x100, CAVE + 0x700, CAVE + 0x800, CAVE + 0x880
FORMAT, MONTHS = CAVE + 0x900, CAVE + 0x980
SITE, ORIGINAL, READER = 0x032a2dd1, 0x041b2870, 0x032a2b93
FMT = b'WORLD RESULT %02u/%02u/%04u: %s %u-%u %s | \0'
BEFORE = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)
DAYS = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)

COPY_SOURCE = '''
    pushfd
    inc dword ptr [{state}]
    popfd
    test edi, edi                     ; ordinal of the displayed headline, NOT its shuffled index
    jnz original
    push ebp
    mov ebp, esp
    sub esp, 0x100
    push ebx
    push esi
    push edi
    mov ebx, ecx                     ; native source string, still owned by PES
    lea ecx, [ebp - 0x100]
    call {build}
    test eax, eax
    jz fallback
    mov esi, dword ptr [ebp + 8]      ; the caller's unconstructed temporary string
    lea eax, [ebp - 0x100]
    push eax
    mov ecx, esi
    call 0x03807ee4                   ; construct/copy the prefix into game-owned storage
    push -1
    push 0
    push ebx
    mov ecx, esi
    call 0x02bcbfb9                   ; append the original headline, without editing its record
    mov eax, esi
    inc dword ptr [{state} + 8]
    mov dword ptr [{state} + 12], 12  ; string copied, NOT proof of final rendering
    jmp done
fallback:
    push dword ptr [ebp + 8]
    mov ecx, ebx
    call {original}
done:
    pop edi
    pop esi
    pop ebx
    mov esp, ebp
    pop ebp
    ret 4
original:
    jmp {original}
'''

# ecx = 256-byte output buffer; eax = length, or zero (leave the native copy alone).
# Select the newest eligible AI-v-AI league result, then largest margin, then first
# physical record. Dates, clubs and competitions are checked before using a result.
BUILD_SOURCE = '''
    push ebp
    mov ebp, esp
    sub esp, 0x34
    push ebx
    push esi
    push edi
    mov dword ptr [ebp - 4], ecx
    inc dword ptr [{state} + 4]
    mov dword ptr [{state} + 12], 1
    mov dword ptr [{state} + 16], 0
    mov dword ptr [{state} + 20], 0
    mov dword ptr [{state} + 24], 0
    mov dword ptr [{state} + 28], 0
    mov dword ptr [{state} + 32], 0
    mov dword ptr [{state} + 36], -1
    mov dword ptr [{state} + 40], 0
    mov eax, dword ptr [0x0264f3e8]
    cmp eax, 0x10000
    jb unavailable
    cmp eax, 0x7fff0000
    ja unavailable
    mov dword ptr [{state} + 12], 2
    mov edx, dword ptr [eax + 0x20]
    mov dword ptr [{state} + 40], edx
    cmp edx, 0x13                    ; shortcut: this exe's two ML modes; re-trace for other builds
    je master_league
    cmp edx, 0x28
    jne unavailable
master_league:
    mov dword ptr [{state} + 12], 3
    mov eax, dword ptr [0x026503e0]
    cmp eax, 0x10000
    jb unavailable
    cmp eax, 0x7fff0000
    ja unavailable
    mov esi, dword ptr [eax + 0x30]
    cmp esi, 0x10000
    jb unavailable
    cmp esi, 0x7f000000                ; every accessed offset must remain below 2 GB
    ja unavailable
    mov dword ptr [{state} + 12], 4
    cmp dword ptr [esi + 0xec1408], 2  ; the alternate table layout is not supported
    je unavailable
    mov dword ptr [{state} + 12], 5
    movzx eax, word ptr [esi + 0xc2cbb2]
    mov dword ptr [{state} + 16], eax
    cmp eax, 2000
    jb unavailable
    cmp eax, 2200
    ja unavailable
    imul eax, eax, 365
    movzx edx, word ptr [esi + 0xc2cbb0]
    mov dword ptr [{state} + 20], edx
    cmp edx, 364
    ja unavailable
    add eax, edx
    mov dword ptr [ebp - 8], eax
    mov dword ptr [{state} + 12], 6
    mov eax, dword ptr [esi + 0x5fece0]
    mov dword ptr [{state} + 24], eax
    test eax, eax
    jz unavailable
    cmp eax, 651
    ja unavailable
    mov dword ptr [ebp - 0xc], eax
    mov dword ptr [{state} + 12], 7
    mov eax, dword ptr [esi + 0x5fece8]
    mov dword ptr [{state} + 28], eax
    test eax, eax
    jz unavailable
    cmp eax, 300
    ja unavailable
    mov dword ptr [ebp - 0x10], eax
    mov dword ptr [{state} + 12], 8
    mov dword ptr [ebp - 0x14], 0
    lea edi, [esi + 0x481be0]
    mov ebx, dword ptr [ebp - 0xc]
user_loop:
    cmp dword ptr [edi], -1
    je next_user
    mov eax, dword ptr [edi + 0x314]   ; same control byte as native 0381e2eb (primary user = 0)
    shr eax, 7
    test al, al
    jnz next_user
    inc dword ptr [{state} + 32]
    cmp dword ptr [ebp - 0x14], 0
    jne unavailable                   ; ambiguous ownership: do not claim an AI-only result
    mov eax, dword ptr [edi]
    shr eax, 14
    and eax, 0xffff
    test eax, eax
    jz unavailable
    cmp eax, 0xffff
    je unavailable
    mov dword ptr [ebp - 0x14], eax
next_user:
    add edi, 0x520
    dec ebx
    jnz user_loop
    cmp dword ptr [ebp - 0x14], 0
    je unavailable
    mov dword ptr [{state} + 12], 9
    mov dword ptr [ebp - 0x18], 0     ; best record
    mov dword ptr [ebp - 0x1c], 0     ; best date*128 + margin
    lea edi, [esi + 0x6f154c]
    lea ebx, [esi + 0xbfd52c]         ; exactly 9000 * 0x24c, not a read into the calendar
match_loop:
    cmp word ptr [edi], 9000
    jae next_match
    test byte ptr [edi + 7], 0x40     ; completed; cups' future rounds are already allocated
    jz next_match
    cmp word ptr [edi + 0x15], 0      ; do not interpret extra-time/shoot-out fields
    jne next_match
    cmp word ptr [edi + 0x18], 0
    jne next_match
    mov eax, dword ptr [edi + 0xc]
    shr eax, 14
    and eax, 0xffff
    cmp eax, dword ptr [ebp - 0x14]
    je next_match
    mov edx, dword ptr [edi + 0x10]
    shr edx, 14
    and edx, 0xffff
    cmp edx, dword ptr [ebp - 0x14]
    je next_match
    cmp eax, edx
    je next_match
    mov edx, dword ptr [edi + 8]
    call {date}
    test eax, eax
    jz next_match
    mov ecx, dword ptr [ebp - 8]
    sub ecx, eax
    jb next_match                     ; future, even if the played flag is wrong
    cmp ecx, 7
    ja next_match                     ; explicitly dated, at most seven game days old
    shl eax, 7
    movzx ecx, byte ptr [edi + 0x14]
    cmp ecx, 99
    ja next_match
    movzx edx, byte ptr [edi + 0x17]
    cmp edx, 99
    ja next_match
    sub ecx, edx
    jns margin
    neg ecx
margin:
    add eax, ecx
    cmp eax, dword ptr [ebp - 0x1c]
    jbe next_match
    mov dword ptr [ebp - 0x20], eax
    movzx eax, word ptr [edi + 4]
    mov ecx, dword ptr [ebp - 0x10]
    call {league}
    test eax, eax
    jz next_match
    mov eax, dword ptr [edi + 0xc]
    mov ecx, dword ptr [ebp - 0xc]
    call {name}
    test eax, eax
    jz next_match
    mov dword ptr [ebp - 0x24], eax
    mov eax, dword ptr [edi + 0x10]
    mov ecx, dword ptr [ebp - 0xc]
    call {name}
    test eax, eax
    jz next_match
    mov dword ptr [ebp - 0x30], eax
    mov eax, dword ptr [ebp - 0x24]
    mov dword ptr [ebp - 0x2c], eax
    mov eax, dword ptr [ebp - 0x20]
    mov dword ptr [ebp - 0x1c], eax
    mov dword ptr [ebp - 0x18], edi
next_match:
    add edi, 0x24c
    cmp edi, ebx
    jb match_loop
    mov edi, dword ptr [ebp - 0x18]
    test edi, edi
    jz unavailable
    movzx eax, word ptr [edi]
    mov dword ptr [{state} + 36], eax
    mov dword ptr [{state} + 12], 10
    push dword ptr [ebp - 0x30]
    movzx eax, byte ptr [edi + 0x17]
    push eax
    movzx eax, byte ptr [edi + 0x14]
    push eax
    push dword ptr [ebp - 0x2c]
    movzx eax, word ptr [edi + 8]
    push eax
    movzx eax, byte ptr [edi + 0xa]
    push eax
    movzx eax, byte ptr [edi + 0xb]
    push eax
    push {format}
    push 256
    push dword ptr [ebp - 4]
    call dword ptr [0x047d75cc]        ; sprintf_s; both names are NUL-terminated within 70 bytes
    add esp, 40
    cmp eax, 1
    jb unavailable
    cmp eax, 255
    ja unavailable
    mov dword ptr [{state} + 12], 11
    jmp done
unavailable:
    xor eax, eax
done:
    pop edi
    pop esi
    pop ebx
    mov esp, ebp
    pop ebp
    ret
'''

# edx = packed native date. February has 28 days, including in leap years in PES.
DATE_SOURCE = '''
    movzx eax, dx
    cmp eax, 2000
    jb invalid
    cmp eax, 2200
    ja invalid
    imul eax, eax, 365
    mov ecx, edx
    shr ecx, 16
    and ecx, 0xff
    dec ecx
    cmp ecx, 11
    ja invalid
    shr edx, 24
    dec edx
    cmp edx, dword ptr [ecx*8 + {months} + 4]
    jae invalid
    add eax, dword ptr [ecx*8 + {months}]
    add eax, edx
    ret
invalid:
    xor eax, eax
    ret
'''

# eax = packed team ID, ecx = bounded count, esi = mode. Returns name pointer or 0.
NAME_SOURCE = '''
    cmp eax, -1
    je invalid
    lea edx, [esi + 0x481be0]
club_loop:
    cmp eax, dword ptr [edx]
    je found
    add edx, 0x520
    dec ecx
    jnz club_loop
invalid:
    xor eax, eax
    ret
found:
    mov ecx, dword ptr [edx + 0x314]
    shr ecx, 7
    cmp cl, 0xff                     ; exclude secondary controlled teams too, not just primary user 0
    jne invalid
    push ebx
    lea ebx, [edx + 4]
    mov eax, ebx
    mov ecx, 70
name_loop:
    movzx edx, byte ptr [eax]
    test dl, dl
    jz terminated
    cmp dl, 32
    jb bad_name
    cmp dl, 127
    je bad_name
    cmp dl, 60                       ; do not introduce UI tags via an edited club name
    je bad_name
    cmp dl, 62
    je bad_name
    inc eax
    dec ecx
    jnz name_loop
bad_name:
    xor eax, eax
    pop ebx
    ret
terminated:
    cmp eax, ebx
    je bad_name
    mov eax, ebx
    pop ebx
    ret
'''

# eax = competition ID (not table index), ecx = bounded count, esi = mode.
LEAGUE_SOURCE = '''
    cmp ax, 0xffff
    je invalid
    lea edx, [esi + 0x552e80]
comp_loop:
    cmp ax, word ptr [edx]
    je found
    add edx, 0x224
    dec ecx
    jnz comp_loop
invalid:
    xor eax, eax
    ret
found:
    xor eax, eax
    cmp dword ptr [edx + 0x5c], 1
    sete al
    ret
'''


def assembled(source, address):
    source = '\n'.join(line.split(';')[0] for line in source.splitlines())
    source = source.format(build=BUILD, date=DATE, name=NAME, league=LEAGUE,
                           format=FORMAT, months=MONTHS, original=ORIGINAL, state=STATE)
    return bytes(Ks(KS_ARCH_X86, KS_MODE_32).asm(source, address)[0])


def build():
    import struct
    out = bytearray(b'\xcc' * SIZE)
    for address, end, data in (
            (COPY, BUILD, assembled(COPY_SOURCE, COPY)),
            (BUILD, DATE, assembled(BUILD_SOURCE, BUILD)),
            (DATE, NAME, assembled(DATE_SOURCE, DATE)),
            (NAME, LEAGUE, assembled(NAME_SOURCE, NAME)),
            (LEAGUE, FORMAT, assembled(LEAGUE_SOURCE, LEAGUE)),
            (FORMAT, MONTHS, FMT),
            (MONTHS, CAVE + SIZE, b''.join(struct.pack('<II', a, n) for a, n in zip(BEFORE, DAYS)))):
        assert address + len(data) <= end, (hex(address), len(data), end - address)
        out[address - CAVE:address - CAVE + len(data)] = data
    return bytes(out)


def state():
    return b'\0' * 36 + b'\xff' * 4 + b'\0' * 4 + b'MLN2'


def lua_block():
    image = build()
    parts, previous = [], 0
    for run in list(re.finditer(b'\xcc{16,}', image)) + [None]:
        stop = run.start() if run else len(image)
        h = image[previous:stop].hex()
        parts.extend('unhex("' + h[i:i + 96] + '")' for i in range(0, len(h), 96))
        if run:
            parts.append('string.rep(string.char(0xcc), %d)' % (run.end() - run.start()))
            previous = run.end()
    return 'local CODE = table.concat({\n    ' + ',\n    '.join(parts) + '\n})'


if __name__ == '__main__':
    if sys.argv[1:] != ['--lua']:
        sys.exit(__doc__)
    print(lua_block())
