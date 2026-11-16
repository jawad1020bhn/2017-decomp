"""What MLGrowth.lua puts into PES2017.exe, and the same arithmetic as Python.

    python3 growth_cave.py            print the layout and the code bytes
    python3 growth_cave.py build      assemble the code again (needs: pip install
                                      keystone-engine) and compare it with the bytes
                                      kept here
    python3 growth_cave.py lua        print the generated block for MLGrowth.lua
                                      (test_growth.py checks that MLGrowth.lua
                                      matches this)
    python3 growth_cave.py calibrate <PES2017.exe> <save>
                                      replay six seasons of the model on every
                                      player of the save and print the OVR bands

MLGrowth.lua (version 1) gives Master League players an age curve (PES 2017,
sha256 44b0caaa...).  The vanilla game:

  1. keeps growth records (exp/carry int16[98] at +0x16/+0xda, match counters
     at +0x1a0/+0x1a4, pending events at +0x19e) for about fifty players only
     -- the user's squad and the youth team.  fcn_0313b4b5 (a 50-entry table
     at mode data +0xd10140 +0x493ec, stride 0x204) says who has one;
     fcn_031207c6 returns the record, or a dummy at the table base when the
     player has none.
  2. awards growth exp only through fcn_038b2fc4(player, &field, &exp, kind,
     news).  For a player without a growth record the exp goes to the dummy:
     nothing happens.  Every other player of the game (19,871 of 19,921 in the
     test save) is frozen for his whole career.
  3. drives the records it does keep with pending events: after a match,
     fcn_03626f8d counts an appearance (+0x1a0, +0x1a4) and, when +0x19e is
     not empty, calls the distributor fcn_03625c10 once and takes one event
     off; the day step fcn_0362752f rolls the age table 0x20fe140 (22 rows of
     age, flag, rate) and fills +0x19e with ten events when the roll succeeds,
     with a staff report.  The distributor then awards 1000-exp to the top exp
     fields and tier amounts (140..250) to the weakest fields.
  4. raises the age of every player once a season in fcn_036236a2, which walks
     the player array (mode data +0, stride 0xe0, count at mode data
     +0x5fecdc; a dummy record follows at +0xed3620) and calls the
     attribute setter with selector 0x2b (age, bits 7-12 of the record dword
     at +0x1c) for each.

The module adds two hooks and changes no game byte anywhere else:

  A. fcn_038b2fc4 (the exp award, 0x038b2fc4): the exp argument is multiplied
     by the age curve, by the potential scale and, for a player with a growth
     record, by his playtime before the function runs.  Negative exp (the
     game's decline awards) is multiplied by DECLINE_TECH (0.25), or left at
     1.0 for the physical fields at DECLINE_START (31) and above.  Everything
     else of the function -- guards, carry, levels, news, growth report --
     runs as it is.
  B. fcn_036236a2 (the season walk, hook after its setter call at
     0x0362373a): every player WITHOUT a growth record -- the frozen 19,871
     -- now also gets floor(curve) points on the ability of his position
     (CF/SS finishing, DMF and the defenders defending, the GK goalkeeping,
     the rest dribbling).  Players with a record are left to hook A.

The arithmetic (Python below, machine code above):

  mult(age)     15-17: 3.0   18-21: 2.5   22-24: 1.5   25-27: 1.0
                28-29: 0.5   30+:   0.25
  scale         min(1, (99 - rating [+4 if rating >= 75 and age <= 21]) /
                margin(age)),   margin: 15: 25  18: 19  21: 12  24: 5  27+: 1
                (age 53+: 0 -- no more growth)
  playtime      PLAYTIME_WEIGHT + (1 - PLAYTIME_WEIGHT) * min(1,
                appearances / PLAYTIME_FULL)  for players with a record
  decline       negative exp: x DECLINE_TECH, but x 1.0 on speed, explosive
                power, body control, physical contact, jump and stamina from
                DECLINE_START on

The code lives in four gaps the other modules leave free (each is checked for
zeros before anything is written): the .reloc gap 0x047d5b8c (the curve), the
.xcode gap 0x047d3f07 (the season award), and the .link gaps 0x047d6377 (the
award hook) and 0x047d6e50 (the season hook and the award arithmetic).  The
tables and floats sit in the zero tail of the .text page at 0x0298c200, which
is writable but not executable -- data only, as MLSimToDate.lua uses that page
for its state as well.
"""
import os
import struct
import sys

# ---------------- addresses (PES2017.exe sha256 44b0caaa...) ----------------
GETTER, SETTER = 0x038278b0, 0x038281b0   # (ecx = player, selector, &out / value), ret 8
PLAYER_OVR = 0x03838c18                   # cdecl(&id, &pos, arrow) -> overall in al
TRACKED = 0x0313b4b5                      # ecx = growth table, (id lo, id hi) -> bool, ret 8
GROWTH_REC = 0x031207c6                   # the same -> record or dummy, ret 8
MODE_OBJECT = 0x026503e0                  # -> mode data at +0x30, growth table at +0xd10140
AWARD = 0x038b2fc4                        # the exp award (hook A)
AWARD_NEXT = 0x038b2fcd                   # its first byte after push ebp; mov ebp,esp; sub esp,0x23c
SEASON = 0x036236a2                       # the season age++ walk (hook B inside)
SEASON_CALL = 0x0362373a                  # its setter call site: mov edx, [0x24fe518]
SEASON_NEXT = 0x03623740                  # the loop continues here
RECORD_STRIDE = 0xe0                      # the player array the season walk uses

# the caves (see the module docstring)
DATA = 0x0298c200                         # tables and floats, .text page tail
CURVE = 0x047d5b8c                        # .reloc gap, 84 bytes
E2 = 0x047d3f07                           # .xcode gap, 153 bytes
E1 = 0x047d6e50                           # .link gap, 176 bytes: E1, then B2
B1 = 0x047d6377                           # .link gap, 137 bytes

# attribute selectors of fcn_038278b0 / fcn_038281b0 (table 0x2164500 of
# fcn_0383899a; confirmed in the emulator on a crafted record)
SEL = {'atk': 0x0e, 'def': 0x0f, 'gk': 0x10, 'drib': 0x11, 'finish': 0x13,
       'ball_ctrl': 0x12, 'lowpass': 0x14, 'loftpass': 0x15, 'header': 0x16,
       'ball_win': 0x17, 'place_kick': 0x18, 'swerve': 0x19, 'reflex': 0x1a,
       'catching': 0x1b, 'clearing': 0x1c, 'cover': 0x1d, 'kick_pwr': 0x22,
       'speed': 0x1f, 'exp_pwr': 0x23, 'body_ctrl': 0x20, 'phys': 0x21,
       'jump': 0x24, 'stamina': 0x25, 'age': 0x2b}
PHYSICAL = ('speed', 'exp_pwr', 'body_ctrl', 'phys', 'jump', 'stamina')
# position 0 CF .. 12 GK (record dword +0, bits 28-31) -> the ability that grows
POSITION_FIELD = {'CF': 'finish', 'SS': 'finish', 'LWF': 'drib', 'RWF': 'drib',
                  'AMF': 'drib', 'DMF': 'def', 'CMF': 'drib', 'LMF': 'drib',
                  'RMF': 'drib', 'CB': 'def', 'LB': 'def', 'RB': 'def', 'GK': 'gk'}
POSTBL = [SEL[POSITION_FIELD[p]] for p in
          ('CF', 'SS', 'LWF', 'RWF', 'AMF', 'DMF', 'CMF', 'LMF', 'RMF',
           'CB', 'LB', 'RB', 'GK')] + [SEL['drib']] * 3

# ---------------- settings (MLGrowth.lua holds the same) ----------------
AGE_MULT = ((15, 3.0), (18, 2.5), (22, 1.5), (25, 1.0), (28, 0.5), (30, 0.25))
MARGIN = ((15, 25), (18, 19), (21, 12), (24, 5), (27, 1))     # age 53+: 0
DECLINE_START, DECLINE_TECH = 31, 0.25
PLAYTIME_WEIGHT, PLAYTIME_FULL = 0.5, 20
RATE_SCALE = 1.0

# ---------------- the same arithmetic in Python ----------------
def _banded(bands, age):
    for start, value in reversed(bands):
        if age >= start:
            return value
    return bands[0][1]


def mult(age):
    """The age curve multiplier (a float)."""
    return _banded(AGE_MULT, age)


def margin(age):
    """The potential margin at an age (an int); 0 below 15 and from 53 on,
    exactly what the padded table of the cave answers."""
    return _banded(MARGIN, age) if 15 <= age < 53 else 0


def scale(age, rating):
    """min(1, headroom / margin): how much of the curve a player may still use."""
    m = margin(age)
    if m == 0:
        return 0.0
    head = 99 - rating + (4 if rating >= 75 and age <= 21 else 0)
    return min(1.0, head / m)


def playtime(count):
    """The playtime factor of a player with a growth record (count appearances)."""
    return PLAYTIME_WEIGHT + (1 - PLAYTIME_WEIGHT) * min(1.0, max(0, count) / PLAYTIME_FULL)


def award_exp(exp, age, rating, count=PLAYTIME_FULL):
    """What hook A leaves in a positive exp argument (count = appearances of
    this growth cycle; negative exp goes through decline_exp below)."""
    return exp * mult(age) * scale(age, rating) * playtime(count)


def decline_exp(exp, age, field):
    """Negative exp: the physical fields decline in full from DECLINE_START on."""
    if age >= DECLINE_START and field in PHYSICAL:
        return exp
    return exp * DECLINE_TECH


def season_levels(age, value):
    """Hook B: the points a player without a growth record gets on his position
    ability that now has `value`.  Integer, as the machine code computes it."""
    m = margin(age)
    if m == 0:
        return 0
    q = round(mult(age) * RATE_SCALE * 4)          # the quarter multiplier of the table
    head = 99 - value
    if head >= m:
        return q >> 2
    return head * q // (4 * m)


# ---------------- the tables and floats of the cave ----------------
def tables():
    """The data image at DATA: quarter multipliers, margins, physical marks,
    position fields, floats.  Index of the first two is age - 15, padded with
    16 rows below (age 0..14) and 17 above (age 54..70), so the code needs no
    range check: below the margin is 0, above it is 0 as well."""
    multq = []
    for age in range(15, 54):
        multq.append(round(mult(age) * RATE_SCALE * 4))
    marg = [margin(age) for age in range(15, 54)]
    phys_sel = {SEL[p] for p in PHYSICAL}
    phys = [1 if f in phys_sel else 0 for f in range(0x27)]
    f = lambda x: struct.pack('<f', x)
    return (b'\x0c' * 16 + bytes(multq) + b'\x01' * 17 +          # MULTQ (age<15: 12, 54+: 1)
            b'\x00' * 16 + bytes(marg) + b'\x00' * 17 +           # MARGIN (age<15 and 54+: 0)
            bytes(phys) + b'\x00' * (56 - len(phys)) +            # PHYS
            bytes(POSTBL) + b'\x00' * (16 - len(POSTBL)) +        # POSTBL
            f(0.25) + f(float(PLAYTIME_FULL)) + f(1 - PLAYTIME_WEIGHT) +
            f(PLAYTIME_WEIGHT) + f(DECLINE_TECH))                 # F_INV4 F_FULL F_INV1PW F_PW F_DTECH


MULTQ, MARGIN_TBL = DATA + 16, DATA + 88      # first real row; 16 zero rows before, 17 after
PHYS_TBL, POSTBL_TBL = DATA + 144, DATA + 200
F_INV4, F_FULL, F_INV1PW, F_PW, F_DTECH = (DATA + 216 + 4 * i for i in range(5))

# ---------------- the machine code ----------------
CODE_PARTS = {}                      # name -> (address, hex); filled by _emit()


def _asm(ks, src, base):
    enc, _ = ks.asm(src, base)
    assert enc is not None, 'keystone refused:\n' + src
    return bytes(enc)


def _find(blob, hex_pattern):
    """The offset of a byte pattern in an assembled block."""
    return blob.index(bytes.fromhex(hex_pattern))


def _emit():
    """Assemble the five blocks.  Order: E2, curve, E1, B2, B1 -- each block
    that jumps into a later one is assembled once to learn the address it
    needs, then again with that address in the source."""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    parts = {}

    # ---- E2: the season award (in: edi = player, ebx = new age, frame of E1) ----
    e2_src = f"""
        lea eax, [ebx - 15]
        movzx edx, byte ptr [eax + {MARGIN_TBL:#x}]
        test edx, edx
        jz e_out
        mov eax, [edi + 4]
        shr eax, 28
        movzx edx, byte ptr [eax + {POSTBL_TBL:#x}]
        mov [ebp - 4], edx
        lea eax, [ebp - 8]
        push eax
        push edx
        mov ecx, edi
        call {GETTER:#x}
        mov edx, [ebp - 4]
        mov eax, [ebp - 8]
        cmp eax, 99
        jae e_out
        mov esi, eax
        mov ecx, 99
        sub ecx, eax
        cmp ecx, edx
        jae e_full
        lea eax, [ebx - 15]
        movzx eax, byte ptr [eax + {MULTQ:#x}]
        imul ecx, eax
        shl edx, 2
        mov eax, ecx
        mov ecx, edx
        cdq
        idiv ecx
        jmp e_lev
    e_full:
        lea eax, [ebx - 15]
        movzx eax, byte ptr [eax + {MULTQ:#x}]
        shr eax, 2
    e_lev:
        test eax, eax
        jle e_out
        add eax, esi
        cmp eax, 99
        jbe e_set
        mov eax, 99
    e_set:
        push eax
        push dword ptr [ebp - 4]
        mov ecx, edi
        call {SETTER:#x}
    e_out:
        mov esp, ebp
        pop ebp
        pop edi
        pop esi
        pop ebx
        mov edx, dword ptr [0x24fe518]
        jmp {SEASON_NEXT:#x}
    """
    parts['E2'] = _asm(ks, e2_src, E2)

    # ---- curve: (ebx = age, esi = rating) -> st0 = mult x scale ----
    curve_src = f"""
        lea eax, [ebx - 15]
        movzx eax, byte ptr [eax + {MULTQ:#x}]
        push eax
        fild dword ptr [esp]
        fmul dword ptr [{F_INV4:#x}]
        pop eax
        lea eax, [ebx - 15]
        movzx ecx, byte ptr [eax + {MARGIN_TBL:#x}]
        test ecx, ecx
        jz c_zero
        lea eax, [esi - 99]
        neg eax
        cmp esi, 75
        jl c_1
        cmp ebx, 21
        jg c_1
        add eax, 4
    c_1:
        push eax
        fild dword ptr [esp]
        pop eax
        push ecx
        fild dword ptr [esp]
        pop eax
        fdivp
        fld1
        fcomi st(0), st(1)
        fcmovnb st(0), st(1)
        fxch st(1)
        fstp st(0)
        fmulp
        ret
    c_zero:
        fstp st(0)
        fldz
        ret
    """
    parts['curve'] = _asm(ks, curve_src, CURVE)

    e_out = E2 + _find(parts['E2'], '89ec5d5f5e5b')               # mov esp,ebp; pop ebp; pop edi; pop esi; pop ebx

    # ---- E1: the season hook (in: esi = player of the walk) ----
    e1_src = f"""
        push ebx
        push esi
        push edi
        push ebp
        mov ebp, esp
        sub esp, 16
        mov edi, esi
        mov eax, dword ptr [{MODE_OBJECT:#x}]
        mov eax, [eax + 0x30]
        lea ecx, [eax + 0xd10140]
        push dword ptr [edi + 0x30]
        push dword ptr [edi + 0x2c]
        call {TRACKED:#x}
        test al, al
        jnz {e_out:#x}
        mov ebx, [edi + 0x1c]
        shr ebx, 7
        and ebx, 0x3f
        jmp {E2:#x}
    """
    parts['E1'] = _asm(ks, e1_src, E1)

    # ---- B2: the award arithmetic (in: edx = &exp, ebx = age, esi = rating,
    #      edi = player, [ebp-8] = appearances, frame of B1) ----
    b2 = E1 + len(parts['E1'])
    b2_src = f"""
    b_pos:
        fld dword ptr [edx]
        call {CURVE:#x}
        fmulp
        fild dword ptr [ebp - 8]
        fdiv dword ptr [{F_FULL:#x}]
        fld1
        fcomi st(0), st(1)
        fcmovnb st(0), st(1)
        fmul dword ptr [{F_INV1PW:#x}]
        fadd dword ptr [{F_PW:#x}]
        fxch st(1)
        fstp st(0)
        fmulp
        fstp dword ptr [edx]
        jmp b_out
    b_neg:
        fld dword ptr [edx]
        mov eax, [ebp + 0x18]
        mov eax, [eax]
        xor ecx, ecx
        cmp eax, 0x26
        ja b_n1
        movzx ecx, byte ptr [eax + {PHYS_TBL:#x}]
    b_n1:
        fld dword ptr [{F_DTECH:#x}]
        cmp ebx, {DECLINE_START}
        jl b_n2
        test ecx, ecx
        jz b_n2
        fstp st(0)
        fld1
    b_n2:
        fmulp
        fstp dword ptr [edx]
    b_out:
        mov esp, ebp
        pop ebp
        pop edi
        pop esi
        pop ebx
        push ebp
        mov ebp, esp
        sub esp, 0x23c
        jmp {AWARD_NEXT:#x}
    """
    parts['B2'] = _asm(ks, b2_src, b2)
    b_neg = b2 + _find(parts['B2'], 'd9028b4518')                 # fld [edx]; mov eax, [ebp+0x18] = b_neg
    skip = b2 + _find(parts['B2'], 'db45f8')                      # fild [ebp-8]: the playtime part

    # ---- B1: the award hook (the entry of fcn_038b2fc4) ----
    b1_src = f"""
        push ebx
        push esi
        push edi
        push ebp
        mov ebp, esp
        sub esp, 16
        mov edi, [ebp + 0x14]
        mov ebx, [edi + 0x1c]
        shr ebx, 7
        and ebx, 0x3f
        lea eax, [ebp - 4]
        push 0
        push eax
        lea eax, [edi + 0x2c]
        push eax
        call {PLAYER_OVR:#x}
        add esp, 12
        movzx esi, al
        mov edx, [ebp + 0x1c]
        test byte ptr [edx + 3], 0x80
        jnz {b_neg:#x}
        mov dword ptr [ebp - 8], {int(PLAYTIME_FULL)}
        mov eax, dword ptr [{MODE_OBJECT:#x}]
        mov eax, [eax + 0x30]
        lea eax, [eax + 0xd10140]
        mov [ebp - 12], eax
        mov ecx, [ebp - 12]
        push dword ptr [edi + 0x30]
        push dword ptr [edi + 0x2c]
        call {TRACKED:#x}
        test al, al
        jz {skip:#x}
        mov ecx, [ebp - 12]
        push dword ptr [edi + 0x30]
        push dword ptr [edi + 0x2c]
        call {GROWTH_REC:#x}
        mov edx, [eax + 0x1a0]
        mov [ebp - 8], edx
        mov edx, [ebp + 0x1c]
        jmp {b2:#x}
    """
    parts['B1'] = _asm(ks, b1_src, B1)
    return parts


def build():
    """name -> (address, bytes) of every block, assembled again."""
    parts = _emit()
    out = {k: (a, parts[k]) for k, a in
           (('curve', CURVE), ('E2', E2), ('E1', E1), ('B1', B1))}
    out['data'] = (DATA, tables())
    out['B2'] = (E1 + len(parts['E1']), parts['B2'])
    room = {'curve': 84, 'E2': 153, 'B1': 137}
    for k, (a, b) in out.items():
        if k in ('data', 'B2'):
            continue                                    # B2 shares E1's fragment
        limit = 176 - len(out['B2'][1]) if k == 'E1' else room[k]
        assert len(b) <= limit, f'{k} overflows its fragment: {len(b)} > {limit}'
    return out


def patches(parts=None):
    """(address, old bytes, new bytes) of the two hook sites."""
    if parts is None:
        parts = {k: v for k, v in build().items()}
    b1 = parts['B1'][1]
    e1 = parts['E1'][1]
    jmp = lambda site, to: b'\xe9' + struct.pack('<i', to - site - 5)
    return (
        (AWARD, bytes.fromhex('5589e581ec'), jmp(AWARD, B1)),
        (SEASON_CALL, bytes.fromhex('8b1518e54f02'), jmp(SEASON_CALL, E1) + b'\x90'),
    )


CODE_PARTS = {           # name -> (address, hex); growth_cave.py build verifies
    "curve": (
        0x47d5b8c,
        "8d43f10fb68010c2980250db0424d80dd8c29802588d43f10fb68858c2980285",
        "c9742b8d469df7d883fe4b7c0883fb157f0383c00450db04245851db042458de",
        "f9d9e8dbf1dbc1d9c9ddd8dec9c3ddd8d9eec3",
    ),
    "E2": (
        0x47d3f07,
        "8d43f10fb69058c2980285d274758b4704c1e81c0fb690c8c298028955fc8d45",
        "f8505289f9e87f3905ff8b55fc8b45f883f863734e89c6b96300000029c139d1",
        "73198d43f10fb68010c298020fafc8c1e20289c889d199f7f9eb0d8d43f10fb6",
        "8010c29802c1e80285c07e1701f083f8637605b86300000050ff75fc89f9e826",
        "4205ff89ec5d5f5e5b8b1518e54f02e9a5f7e4fe",
    ),
    "E1": (
        0x47d6e50,
        "5356575589e583ec1089f7a1e00365028b40308d884001d100ff7730ff772ce8",
        "414696fe84c00f850ed1ffff8b5f1cc1eb0783e33fe97dd0ffff",
    ),
    "B1": (
        0x47d6377,
        "5356575589e583ec108b7d148b5f1cc1eb0783e33f8d45fc6a00508d472c50e8",
        "7d2806ff83c40c0fb6f08b551cf64203800f850a0b0000c745f814000000a1e0",
        "0365028b40308d804001d1008945f48b4df4ff7730ff772ce8e15096fe84c00f",
        "84b70a00008b4df4ff7730ff772ce8dca394fe8b90a00100008955f88b551ce9",
        "8f0a0000",
    ),
    "data": (
        0x298c200,
        "0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0a0a0a0a060606040404020201",
        "0101010101010101010101010101010101010101010101010101010101010101",
        "0101010101010101000000000000000000000000000000001919191313130c0c",
        "0c05050501010101010101010101010101010101010101010101010101010000",
        "0000000000000000000000000000000000000000000000000000000000000000",
        "0000000000000000000000000000000101010001010100000000000000000000",
        "000000000000000013131111110f1111110f0f0f101111110000803e0000a041",
        "0000003f0000003f0000803e",
    ),
    "B2": (
        0x47d6e8a,
        "d902e8fbecffffdec9db45f8d835dcc29802d9e8dbf1dbc1d80de0c29802d805",
        "e4c29802d9c9ddd8dec9d91aeb2cd9028b45188b0031c983f82677070fb68890",
        "c29802d905e8c2980283fb1f7c0885c97404ddd8d9e8dec9d91a89ec5d5f5e5b",
        "5589e581ec3c020000e9d5c00dff",
    ),
}


def part(name):
    """(address, hex) of a code part of the CODE_PARTS literal."""
    a, *hx = CODE_PARTS[name]
    return a, ''.join(hx)



# what the game must hold where the cave jumps to and calls (see test_growth.py)
CONTEXT = (
    ('award after prologue', 0x038b2fcd, 'a1501a520231e88985fcffff'),   # AWARD_NEXT
    ('season walk next', 0x03623740, '8185fcffffffe0000000'),           # SEASON_NEXT
    ('attribute getter', 0x038278b0, '5589e58b450883f8'),
    ('attribute setter', 0x038281b0, '5589e58b450883f8'),
    ('player overall', 0x03838c18, '5589e5e8c534feff'),
    ('growth record test', 0x0313b4b5, '5589e5a1c44f4b02'),
    ('growth record find', 0x031207c6, '5589e551a1f83d4b'),
    ('season walk entry', 0x036236a2, '5589e583ec085357'),
)


def lua_block():
    """The generated Lua code block for MLGrowth.lua."""
    lines = [
        '-- Generated by growth_cave.py (do not edit by hand; test_growth.py checks this block)',
        'local DATA = 0x%08x' % DATA,
        'local DATA_SIZE = %d' % len(bytes.fromhex(part('data')[1])),
        'local CAVE_E2 = 0x%08x' % part('E2')[0],
        'local CAVE_E2_SIZE = %d' % len(bytes.fromhex(part('E2')[1])),
        'local CAVE_CURVE = 0x%08x' % part('curve')[0],
        'local CAVE_CURVE_SIZE = %d' % len(bytes.fromhex(part('curve')[1])),
        'local CAVE_B1 = 0x%08x' % part('B1')[0],
        'local CAVE_B1_SIZE = %d' % len(bytes.fromhex(part('B1')[1])),
        'local CAVE_E1 = 0x%08x' % part('E1')[0],
        'local CAVE_E1_SIZE = %d' % (len(bytes.fromhex(part('E1')[1])) +
                                     len(bytes.fromhex(part('B2')[1]))),   # E1 + B2 share the gap
        '',
        'local BLOCKS = {',
        '    { "season award code", CAVE_E2, "%s" },' % part('E2')[1],
        '    { "age curve code", CAVE_CURVE, "%s" },' % part('curve')[1],
        '    { "exp award code", CAVE_B1, "%s" },' % part('B1')[1],
        '    { "season walk code", CAVE_E1, "%s" },' % part('E1')[1],
        '    { "season walk code 2", CAVE_E1 + %d, "%s" },'
        % (len(bytes.fromhex(part('E1')[1])), part('B2')[1]),
        '    { "growth tables", DATA, "%s" },' % part('data')[1],
        '}',
        '',
        'local SITES = {',
    ]
    names = {AWARD: 'exp award entry', SEASON_CALL: 'season age walk'}
    for at, old, new in patches():
        lines.append('    { "%s", 0x%08x, "%s", "%s" },'
                     % (names[at], at, old.hex(), new.hex()))
    lines += [
        '}',
        '',
        'local CONTEXT = {',
    ]
    for name, at, hx in CONTEXT:
        lines.append('    { "%s", 0x%08x, "%s" },' % (name, at, hx))
    lines += ['}', '']
    return '\n'.join(lines)


def calibrate(exe_path, save_path, seasons=6):
    """Replay `seasons` seasons of hook E on every player of the save and print how the
    overall ratings move: the point the model gives an AI player a season is
    season_levels(age, position ability), exactly what the cave computes.  Players with
    a growth record (the user squad, about fifty) are left out: their growth runs
    through hook A and hangs on matches played, which a save cannot tell."""
    import collections

    here = os.path.dirname(os.path.abspath(__file__))
    sys.path[:0] = [here, os.path.join(here, '..', 'tools')]
    import window_report as wr

    save = wr.Save(save_path)
    rater = wr.Rater(exe_path)

    slot = {0x0e: (0, 24), 0x0f: (4, 0), 0x10: (4, 7), 0x11: (4, 14), 0x12: (4, 21),
            0x13: (8, 0), 0x14: (8, 7), 0x15: (8, 14), 0x16: (8, 21),
            0x17: (0xc, 0), 0x18: (0xc, 7), 0x19: (0xc, 14), 0x1a: (0xc, 21),
            0x1b: (0x10, 0), 0x1c: (0x10, 7), 0x1d: (0x10, 14), 0x1f: (0x10, 21),
            0x20: (0x14, 0), 0x21: (0x14, 7), 0x22: (0x14, 14), 0x23: (0x14, 21),
            0x24: (0x18, 0), 0x25: (0x18, 7)}
    postbl = [POSTBL[p] if p < len(POSTBL) else SEL['drib'] for p in range(16)]

    def getf(rec, sel):
        off, shift = slot[sel]
        return (struct.unpack_from('<I', rec, off)[0] >> shift) & 0x7f

    def setf(rec, sel, value):
        off, shift = slot[sel]
        d = struct.unpack_from('<I', rec, off)[0]
        d = (d & ~(0x7f << shift)) | ((value & 0x7f) << shift)
        struct.pack_into('<I', rec, off, d)

    def set_age(rec, age):
        d = struct.unpack_from('<I', rec, 0x1c)[0]
        struct.pack_into('<I', rec, 0x1c, (d & ~0x3f80) | ((age & 0x3f) << 7))

    records = {k: bytearray(r) for k, r in save.players.items()}
    before = {k: rater(bytes(r)) for k, r in records.items()}
    risen = collections.Counter()
    for _ in range(seasons):
        for r in records.values():
            age = wr.age(bytes(r)) + 1                     # the walk raises the age first
            set_age(r, age)
            pos = struct.unpack_from('<I', r, 4)[0] >> 28
            sel = postbl[pos] if pos < 16 else SEL['drib']
            value = getf(r, sel)
            gain = season_levels(age, value)
            if gain:
                risen[wr.name(bytes(r))] += gain
                setf(r, sel, min(99, value + gain))
    after = {k: rater(bytes(r)) for k, r in records.items()}

    bands = [(0, 59), (60, 64), (65, 69), (70, 74), (75, 79), (80, 84), (85, 99)]
    print(f'{len(records)} players, {seasons} seasons of the model '
          f'(hook E only; the ~50 players with growth records follow hook A instead)')
    print(f'{"OVR":>8s} {"before":>8s} {"after":>8s}')
    for lo, hi in bands:
        b = sum(lo <= v <= hi for v in before.values())
        a = sum(lo <= v <= hi for v in after.values())
        print(f'{lo:3d}-{hi:3d} {b:8d} {a:8d}')
    print(f'{"mean":>8s} {sum(before.values()) / len(before):8.2f} '
          f'{sum(after.values()) / len(after):8.2f}')
    age_bands = ((15, 20), (21, 24), (25, 28), (29, 32), (33, 45))
    print('\nby the age the players have now:')
    for lo, hi in age_bands:
        ks = [k for k, r in records.items() if lo <= wr.age(bytes(r)) - seasons <= hi]
        if not ks:
            continue
        mb = sum(before[k] for k in ks) / len(ks)
        ma = sum(after[k] for k in ks) / len(ks)
        print(f'  {lo:2d}-{hi:2d}: {len(ks):6d} players, mean OVR {mb:5.2f} -> {ma:5.2f} '
              f'({ma - mb:+.2f})')
    top = risen.most_common(8)
    print('\nbiggest risers: ' + ', '.join(f'{n} +{g}' for n, g in top))


if __name__ == '__main__':
    here = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, here)
    what = sys.argv[1] if len(sys.argv) > 1 else 'print'
    if what == 'build':
        from keystone import Ks, KS_ARCH_X86, KS_MODE_32       # noqa: F401
        again = build()
        for k in CODE_PARTS:
            a, hx = part(k)
            b = again[k][1]
            print(f'{k:6s} {a:#010x} +{len(b):#05x}  {"same" if b.hex() == hx else "DIFFERENT"}')
    elif what == 'lua':
        print(lua_block())
    elif what == 'calibrate':
        calibrate(sys.argv[2], sys.argv[3])
    else:
        budgets = {'curve': 84, 'E2': 153, 'B1': 137}
        used = {k: len(bytes.fromhex(part(k)[1])) for k in CODE_PARTS}
        used['E1'] += used['B2']                            # they share the 176-byte gap
        for k in sorted(CODE_PARTS, key=lambda k: part(k)[0]):
            a, hx = part(k)
            room = 176 if k == 'E1' else budgets.get(k)
            print(f'{k:6s} {a:#010x} +{used[k]:#05x}' + (f' of {room:#x}' if room else ''))
        for at, old, new in patches():
            print(f'patch  {at:#010x}: {old.hex()} -> {new.hex()}')
