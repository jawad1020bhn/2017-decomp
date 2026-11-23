"""What MLGrowth.lua puts into PES2017.exe, and the same arithmetic as Python.

    python3 growth_cave.py            print the layout and the code bytes
    python3 growth_cave.py build      assemble the code again (needs: pip install
                                      keystone-engine) and compare it with the bytes
                                      kept here
    python3 growth_cave.py lua        print the generated block for MLGrowth.lua
                                      (test_growth.py checks that MLGrowth.lua
                                      matches this)
    python3 growth_cave.py calibrate <PES2017.exe> <save>
                                      replay six seasons of the season walk on
                                      every player of the save and print the
                                      OVR bands (growth_twin.py is the fuller
                                      check, on the edit file it can load)

MLGrowth.lua (version 8) is a factor model for every Master League player (PES 2017,
sha256 44b0caaa...).  It replaces the hand-set youth multipliers of version 6 with a
table-driven season, solved against career outcomes by growth_twin.py:

    points = BASE(age, archetype) x TRAJ(form) x PLAY(role) x HEAD(ceiling, talent)

on the attributes the player's position is actually rated by, plus five decline families.
The tracked squad's exp award keeps the version-6 shape (age curve x potential x
playtime) with an eased youth curve, so the two models do not outpace each other.
The vanilla game:

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

The module adds four patches and changes no game byte anywhere else:

  A. fcn_038b2fc4 (the exp award, 0x038b2fc4): the exp argument is multiplied
     by the age curve, by the potential scale and, for a player with a growth
     record, by his playtime before the function runs -- except kind 2, the
     training awards the game already scales by minutes played (they leave
     fcn_0362288c as 0.3 x regime x minutes): those get the curve and the
     scale but no playtime factor, which would count the minutes twice.
     Negative exp (the game's decline awards) is multiplied by DECLINE_TECH
     (0.25), or left at 1.0 for the physical fields at DECLINE_START (31) and
     above.  Everything else of the function -- guards, carry, levels, news,
     growth report -- runs as it is.
  B. fcn_036236a2 (the season walk, hook after its setter call at
     0x0362373a): every player WITHOUT a growth record -- the frozen 19,871
     -- now gets a season of the factor model below: points on up to twelve
     attributes of his position (the game's own weight rows, SIX), and one
     point off each of five decline families from its own age.  Players with
     a record are left to hook A.
  C. The two `call fcn_036216e9` sites of the after-match training path
     (0x036226a7 in fcn_036225f8, individual focus, and 0x036227e5 in
     fcn_0362274d, team focus).  The vanilla game sets the trained value
     with no regard of age; the cave now multiplies the exp by the same age
     curve and potential scale before the exp-to-levels function runs.  The
     player (edi) and the growth record (ecx) the two call sites hold are
     passed on untouched.  fcn_036216e9 keeps its own exp array in the
     growth record (int16 at +0x16, selector-indexed, 1000 cap), which is
     where the scaled exp lands.

The arithmetic (Python below, machine code above):

  hook A (the tracked fifty), the same arithmetic as version 6:
  base mult     15-17: 1.50  18-21: 1.25  22-24: 1.00  25-27: 0.75
                28-29: 0.50  30+:   0.25
  scale         min(1, (99 - rating [+4 if rating >= 75 and age <= 21]) /
                margin(age)),   margin: 15: 25  18: 19  21: 12  24: 5  27+: 1
                (age 53+: 0 -- no more growth)
  playtime      PLAYTIME_WEIGHT + (1 - PLAYTIME_WEIGHT) * min(1,
                appearances / PLAYTIME_FULL)  for players with a record,
                and not at all for kind-2 training awards
  decline       negative exp: x DECLINE_TECH, but x 1.0 on speed, explosive
                power, body control, physical contact, jump and stamina from
                DECLINE_START on

  hook B (everyone else), one season = (BASE x TRAJ x PLAY x HEAD) >> 1, and a
  draw r = (hashb(pid, age) + 0x25 k) & 0xff per attribute k of SIX:
      BASE  PHASE[arch][age - 15], a 16th of a point (no season from 33 on)
      TRAJ  TRAJ[form >> 5], eighths of a season; form = (128u2 + 77u1 + 51u0) >> 8
            (AR(2) shape, a pure function of pid and age -- no state); a breakout
            (u >= 224) is followed by three quarters, two slumps before 20 cost
            three ceiling points
      PLAY  PLAYT[hashb >> 5], eighths of a season (the role: starter..fringe)
      HEAD  min(8, ((99 - value) x talent) >> 4), 0 at the personal ceiling and,
            above 86/89, for most draws (the scarcity gates)
      step  +2 if r < threshold >> 1, else +1 if r < threshold (no 255 cap: a
            threshold above it means every draw passes)
      decline  one point off the family attribute whose start age this is
               (face 27, stamina 29, strength 32, technique 33, cognitive 34,
               shifted -1 for the attacking positions, +3 for a GK), down to 45

The code lives in eight blocks in gaps the other modules leave free (each is
checked for zeros before anything is written): the .reloc gap 0x047d5b8c (the
curve), the .link gaps 0x047d6377 (the award hook), 0x047d6e50 (the award
arithmetic) and 0x047d6efe (the training scale), and the .trace page behind the
day step at 0x02e8b198 (the hash chain, the season walk and its tables, 0x600 +
0x200 bytes).  The hook-A tables and floats sit in the zero tail of the .text
page at 0x0298c200, which is writable but not executable -- data only, as
MLSimToDate.lua uses that page for its state as well.
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
B2 = 0x047d6e50                           # .link gap, 174 bytes before FOCUS (v7's E1 slot)
B1 = 0x047d6377                           # .link gap, 137 bytes
FOCUS = 0x047d6efe                        # .link gap behind B2, 98 bytes
LEVELS = 0x036216e9                       # ecx = growth record, (selector, exp) -> levels, ret 8
FOCUS_CALLS = (0x036226a7, 0x036227e5)    # the two `call LEVELS` sites of the training paths

# attribute selectors of fcn_038278b0 / fcn_038281b0 (table 0x2164500 of
# fcn_0383899a; confirmed in the emulator on a crafted record)
SEL = {'atk': 0x0e, 'def': 0x0f, 'gk': 0x10, 'drib': 0x11, 'finish': 0x13,
       'ball_ctrl': 0x12, 'lowpass': 0x14, 'loftpass': 0x15, 'header': 0x16,
       'ball_win': 0x17, 'place_kick': 0x18, 'swerve': 0x19, 'reflex': 0x1a,
       'catching': 0x1b, 'clearing': 0x1c, 'cover': 0x1d, 'kick_pwr': 0x22,
       'speed': 0x1f, 'exp_pwr': 0x23, 'body_ctrl': 0x20, 'phys': 0x21,
       'jump': 0x24, 'stamina': 0x25, 'age': 0x2b}
PHYSICAL = ('speed', 'exp_pwr', 'body_ctrl', 'phys', 'jump', 'stamina')
# position 0 CF .. 12 GK (record dword +0, bits 28-31) -> the primary ability that grows
POSITION_FIELD = {'CF': 'finish', 'SS': 'finish', 'LWF': 'drib', 'RWF': 'drib',
                  'AMF': 'drib', 'DMF': 'def', 'CMF': 'drib', 'LMF': 'drib',
                  'RMF': 'drib', 'CB': 'def', 'LB': 'def', 'RB': 'def', 'GK': 'gk'}
# secondary ability for balanced multi-attribute development (alternating by age)
POSITION_FIELD2 = {'CF': 'drib', 'SS': 'drib', 'LWF': 'lowpass', 'RWF': 'lowpass',
                   'AMF': 'lowpass', 'DMF': 'ball_win', 'CMF': 'lowpass', 'LMF': 'lowpass',
                   'RMF': 'lowpass', 'CB': 'ball_win', 'LB': 'speed', 'RB': 'speed', 'GK': 'reflex'}

# POSTBL: primary position abilities (0..12), index 13 = speed for senior even-age decline, 14..15 fallback
POSTBL = [SEL[POSITION_FIELD[p]] for p in
          ('CF', 'SS', 'LWF', 'RWF', 'AMF', 'DMF', 'CMF', 'LMF', 'RMF',
           'CB', 'LB', 'RB', 'GK')] + [SEL['speed'], SEL['drib'], SEL['drib']]

# POSTBL2: secondary position abilities (0..12), index 13 = stamina for senior odd-age decline, 14..15 fallback
POSTBL2 = [SEL[POSITION_FIELD2[p]] for p in
           ('CF', 'SS', 'LWF', 'RWF', 'AMF', 'DMF', 'CMF', 'LMF', 'RMF',
            'CB', 'LB', 'RB', 'GK')] + [SEL['stamina'], SEL['lowpass'], SEL['lowpass']]

# ---------------- settings (MLGrowth.lua holds the same) ----------------
# Version 8 replaces the hand-set youth multipliers of v6/v7 with a factor model whose
# shape is solved against career outcomes (growth_twin.py):
#
#     points = BASE(age, ARCH) x TRAJ(form) x PLAY(role) x HEAD(ceiling, talent)
#     decline: five families, each with its own start age, shifted by the position
#
# v6 multiplied the game's own exp award by 1.75/1.50/1.00/..., which made 15-17 *faster*
# than vanilla: the shape was right, the anchor was not.  Here BASE is a table of chances
# solved for the target career gains (elite +18-25, regular +10-15, squad +5-8, limited
# +2-4), and the tracked squad's exp curve (hook A) is read back out of that shape.
#
# One point of an ability is the smallest step the game carries, so a seasonal growth of
# e.g. 0.6 points becomes a threshold on the season's draw.  The draw is not i.i.d.:
# TRAJ turns the per-player-per-season hash into an AR(2)-shaped form, so good seasons
# follow good ones and two bad ones before 20 derail the career.  No state is stored: the
# form of a season is a pure function of (player id, age), so a reload changes nothing.
ARCH = ('early', 'normal', 'late', 'limited')     # ~12 / 62 / 12 / 14 per cent
# The first hash byte picks the archetype and the intake band together: bits 0-2 pick one
# of the eight nibbles (0 early, 1 normal, 2 late, 3 limited), bits 3-5 the band.
ARCH_NIBBLES = (0, 1, 1, 2, 3, 1, 1, 2, 1, 3, 1, 1, 2, 1, 3, 1)
INBAND = (0, 1, 2, 3, 0, 1, 2, 3)                 # bits 3-5 -> the intake band
# HEAD: the personal ceiling of an ability, archetype x intake band, and the talent that
# says how fast a player climbs towards it (eighths of a season at full headroom).
CEIL = ((72, 78, 86, 91),                          # early: peak 23-25, fades by 28
        (70, 76, 84, 92),                          # normal: peak 26-28
        (72, 78, 88, 92),                          # late: peak 29-31
        (62, 66, 70, 74))                          # limited: plateau by 21
TALENT = ((6, 7, 8, 8), (5, 6, 7, 8), (5, 6, 8, 8), (3, 3, 4, 4))
GATE86, GATE89 = 128, 210                          # the universal scarcity gates (hash)
# BASE: the chance of a point a season, in 16ths, by archetype and age 15..  These numbers
# are outputs of growth_twin.py, not hand-set multipliers.
PHASE = (
    (16, 15, 14, 12, 10, 7, 4, 2, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0),
    (13, 14, 15, 14, 13, 11, 9, 7, 5, 4, 3, 2, 1, 0, 0, 0, 0, 0),
    (5, 6, 7, 9, 11, 12, 13, 14, 14, 13, 12, 10, 7, 4, 1, 0, 0, 0),
    (18, 16, 14, 11, 8, 5, 3, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
)  # 0 early, 1 normal, 2 late, 3 limited (the limited one stops at 18)
# TRAJ: form (0..255) >> 5 -> eighths of a season.  A breakout draws 16, a slump 0.
TRAJ = (0, 4, 6, 8, 8, 10, 10, 12, 16)
FORM_HI, FORM_LO = 224, 96                         # breakout draw, slump draw
CONSOLIDATE = 224                                  # after a breakout: three quarters
DERAIL_AGE, DERAIL_CEIL = 20, 3                    # two slumps before 20: ceiling -3
# PLAY: AI minutes are not readable, so the season's role comes from the same hash byte
# (a starter, a rotation player, a fringe player), in eighths of a season.
PLAYT = (3, 3, 4, 4, 4, 4, 4, 2)
# PRE: how far a season reaches into the position's twelve attributes (12 = the top six)
PRE = (12, 12, 11, 10, 9, 8, 7, 6)
# DECLINE: the five families, their attributes, and the age each starts for a neutral
# position.  Wings and forwards feel pace first; a GK a year later than everyone.
FAMILIES = (('pace', (SEL['speed'], SEL['exp_pwr'], SEL['drib']), 27),
            ('stamina', (SEL['stamina'],), 29),
            ('strength', (SEL['phys'], SEL['body_ctrl'], SEL['jump']), 32),
            ('technique', (SEL['ball_ctrl'], SEL['lowpass'], SEL['loftpass'],
                           SEL['place_kick'], SEL['kick_pwr']), 33),
            ('cognitive', (SEL['def'], SEL['ball_win'], SEL['atk'], SEL['header'],
                           SEL['swerve']), 34))
POS_SHIFT = (('CF', -1), ('SS', -1), ('LWF', -1), ('RWF', -1), ('AMF', -1),
             ('DMF', 0), ('CMF', 0), ('LMF', 0), ('RMF', 0), ('CB', 1),
             ('LB', 0), ('RB', 0), ('GK', 3))          # the cave's table is POSH
DECLINE_FLOOR = 45
POS_NAMES = ('CF', 'SS', 'LWF', 'RWF', 'AMF', 'DMF', 'CMF', 'LMF', 'RMF', 'CB', 'LB', 'RB', 'GK')
# SIX: the twelve attributes of a position, in the game's own weight order (the rows of
# fcn_04067af3), so a season grows what the overall rating actually reads.
SIX = {
    'CF': (0x13, 0x0e, 0x12, 0x11, 0x1f, 0x23, 0x20, 0x21, 0x16, 0x22, 0x24, 0x0f),
    'SS': (0x23, 0x11, 0x12, 0x0e, 0x13, 0x14, 0x15, 0x1f, 0x22, 0x25, 0x20, 0x21),
    'LWF': (0x11, 0x12, 0x0e, 0x1f, 0x23, 0x13, 0x15, 0x25, 0x14, 0x22, 0x20, 0x21),
    'RWF': (0x11, 0x12, 0x0e, 0x1f, 0x23, 0x13, 0x15, 0x25, 0x14, 0x22, 0x20, 0x21),
    'AMF': (0x11, 0x12, 0x14, 0x13, 0x0e, 0x15, 0x23, 0x1f, 0x25, 0x20, 0x21, 0x0f),
    'DMF': (0x15, 0x12, 0x14, 0x11, 0x25, 0x19, 0x0f, 0x0e, 0x20, 0x21, 0x24, 0x17),
    'CMF': (0x11, 0x12, 0x14, 0x15, 0x25, 0x23, 0x0e, 0x1f, 0x0f, 0x20, 0x21, 0x10),
    'LMF': (0x11, 0x1f, 0x23, 0x12, 0x25, 0x15, 0x0e, 0x14, 0x19, 0x0f, 0x10, 0x13),
    'RMF': (0x11, 0x1f, 0x23, 0x12, 0x25, 0x15, 0x0e, 0x14, 0x19, 0x0f, 0x10, 0x13),
    'CB': (0x0f, 0x17, 0x16, 0x24, 0x1f, 0x20, 0x21, 0x25, 0x0e, 0x10, 0x11, 0x12),
    'LB': (0x1f, 0x0f, 0x11, 0x15, 0x23, 0x25, 0x17, 0x24, 0x12, 0x0e, 0x20, 0x21),
    'RB': (0x1f, 0x0f, 0x11, 0x15, 0x23, 0x25, 0x17, 0x24, 0x12, 0x0e, 0x20, 0x21),
    'GK': (0x10, 0x1d, 0x1a, 0x1b, 0x1c, 0x24, 0x20, 0x21, 0x0e, 0x0f, 0x11, 0x12),
}

# hook A (the ~50 tracked players of the user's squad) keeps v6's arithmetic: its exp is
# multiplied by a quarter-step age curve and the potential scale.  The youth steps are
# eased from v6's (1.75 at 15), since the AI model above no longer outpaces them.
AGE_MULT_A = ((15, 1.50), (18, 1.25), (22, 1.00), (25, 0.75), (28, 0.50), (30, 0.25))
RATE_SCALE = 1.00
MARGIN = ((15, 25), (18, 19), (21, 12), (24, 5), (27, 1))     # age 53+: 0
DECLINE_START, DECLINE_TECH = 31, 0.25
PLAYTIME_WEIGHT, PLAYTIME_FULL = 0.20, 20

# ---------------- the same arithmetic in Python ----------------
def _banded(bands, age):
    for start, value in reversed(bands):
        if age >= start:
            return value
    return bands[0][1]


def mult(age):
    """The age-curve multiplier hook A applies, in quarter steps."""
    return round(_banded(AGE_MULT_A, age) * RATE_SCALE * 4) / 4


def margin(age):
    """The potential margin at an age (an int); 0 below 15 and from 53 on."""
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


def award_exp(exp, age, rating, count=PLAYTIME_FULL, kind=0):
    """What hook A leaves in a positive exp argument.  Kind 2 is a training award the
    game already scales by minutes played: no playtime factor, or they count twice."""
    return exp * mult(age) * scale(age, rating) * (1.0 if kind == 2 else playtime(count))


def decline_exp(exp, age, field):
    """Negative exp: the physical fields decline in full from DECLINE_START on."""
    if age >= DECLINE_START and field in PHYSICAL:
        return exp
    return exp * DECLINE_TECH


# ---- the hash chain: one 32-bit word does three jobs -----------------------
def hashb(pid, age):
    """The cave's hashb(pid, age): three multiply-mixes -> one byte.  Ranges: 0..255."""
    t = (age * 0x85ebca6b + pid) & 0xffffffff
    t = (t * 0xc2b2ae35) & 0xffffffff
    t ^= t >> 15
    t = (t * 0x27d4eb2d) & 0xffffffff
    t ^= t >> 16
    return t & 0xff


def form(pid, age):
    """TRAJ: 0.5 U(age-2) + 0.3 U(age-1) + 0.2 U(age) in 0..255 -- an AR(2)-shaped
    process that is a pure function of (player, age): no state, reload-safe."""
    return (128 * hashb(pid, age - 2) + 77 * hashb(pid, age - 1) + 51 * hashb(pid, age)) >> 8


def arch(pid):
    """ARCH: one of the four archetypes, fixed for the whole career."""
    return ARCH_NIBBLES[hashb(pid, 0) & 15]


def intake_band(pid):
    """HEAD: the intake band (0..3), fixed with the archetype."""
    return INBAND[(hashb(pid, 0) >> 3) & 7]


def ceiling(pid):
    """HEAD: the personal ceiling of an ability, in OVR points."""
    return CEIL[arch(pid)][intake_band(pid)]


def talent(pid):
    """HEAD: how fast the player climbs towards it."""
    return TALENT[arch(pid)][intake_band(pid)]


def phase(a, age):
    """BASE: the chance of a point at an age, in 16ths."""
    return PHASE[a][age - 15] if 15 <= age <= 32 else 0


def trajectory(pid, age):
    """TRAJ: eighths of a season, and the consolidation after a breakout season."""
    q = TRAJ[form(pid, age) >> 5]
    if q and hashb(pid, age - 1) >= CONSOLIDATE:
        q = q * 3 >> 2
    return q


def play(pid, age):
    """PLAY: eighths of a season by the season's role (AI minutes are not readable)."""
    return PLAYT[hashb(pid, age) >> 5]


def derailed(pid, age):
    """TRAJ: two bad draws in a row before DERAIL_AGE cost the career three OVR points.
    (The draws, not the smoothed form: a derailment is an event, not a slow burn.)"""
    return (age <= DERAIL_AGE and hashb(pid, age - 1) < FORM_LO
            and hashb(pid, age - 2) < FORM_LO)


def head(pid, value, age):
    """HEAD: eighths of the season this ability may still use, now at `value`."""
    top = ceiling(pid) - (DERAIL_CEIL if derailed(pid, age) else 0)
    if value >= top:
        return 0
    hb = hashb(pid, age)
    if value >= 89 and hb < GATE89:
        return 0
    if value >= 86 and hb < GATE86:
        return 0
    return min(8, ((99 - value) * talent(pid)) >> 4)


def six(pos):
    """SIX: the twelve attributes of a position, in the game's weight order."""
    return SIX[POS_NAMES[pos] if pos < 13 else 'CF']


def pre(pid, age):
    """PRE: how far the season reaches into those twelve (6 at best, 2 at worst)."""
    return PRE[hashb(pid, age) >> 5]


def season_points(pid, age, values, pos):
    """The whole season for one player: which of the position's attributes gain a point,
    and the step (1 or 2).  `values` is a dict selector -> value."""
    out = []
    p = phase(arch(pid), age)
    if p == 0:
        return out
    q = trajectory(pid, age) * play(pid, age)
    if q == 0:
        return out
    hb = hashb(pid, age)
    for k, sel in enumerate(six(pos)[:pre(pid, age)]):
        head_q = head(pid, values.get(sel, 0), age)
        if head_q == 0:
            continue
        # no clamp at 255: x above it means every draw passes (that is how a top
        # archetype's peak seasons read), and min() there cost the elite band 3 points
        x = (p * q * head_q) >> 1
        r = (hb + 0x25 * k) & 0xff
        if r < x:
            out.append((sel, 2 if r < x >> 1 else 1))
    return out


def decline_sel(pid, age, pos):
    """DECLINE: the family attribute that loses a point this season, or None.  One point
    a season per family from its start age, walking the family so it falls together."""
    shift = POS_SHIFT[pos][1] if pos < 13 else 0
    for name, sels, start in FAMILIES:
        if age == start + shift:
            return sels[(age >> 1) % len(sels)]
    return None


def ci(sel):
    """DECI: the index of a selector in its family's attribute list (0 if none)."""
    for name, sels, start in FAMILIES:
        if sel in sels:
            return sels.index(sel)
    return 0


# ---------------- the tables of the cave ----------------
# DATA (0x0298c200, 236 bytes): what hook A and the curve read; v6's layout, unchanged.
MULTQ, MARGIN_TBL = DATA + 16, DATA + 88
PHYS_TBL, POSTBL_TBL = DATA + 144, DATA + 200
POSTBL2_TBL = DATA + 184
F_INV4, F_FULL, F_INV1PW, F_PW, F_DTECH = (DATA + 216 + 4 * i for i in range(5))
# WALK (0x02e8b198, 0x600 bytes, the .trace gap) is the season walk's code; the tables
# follow it at SEASON (0x02e8b798, 0x200 bytes).
#   +0x000 PHASE   4 x 18 bytes, archetype x age 15..
#   +0x048 SIX     16 x 12, by position (13..15: CF's)
#   +0x108 TRAJ    9 bytes   +0x111 PLAYT   8   +0x119 PRE     8
#   +0x121 HEADT   4 x 4 (talent)              +0x131 CEILT   4 x 4 (ceiling)
#   +0x141 MINUS3  +0x142 FLOOR
#   +0x150 DECL    5 x 8: start age, shift, family mask, count, the attributes (4)
#   +0x1a0 DECI    0x23 bytes: selector - 0x0e -> index in DECL's list
#   +0x1c4 ARCHN   16 nibbles               +0x1d4 INBAND  8
#   +0x1dc FORM_LO, DERAIL_AGE, GATE86, GATE89, CONSOLIDATE, DERAIL_CEIL
#   +0x1e4 POSH    16 signed position shifts
#   +0x1f0 the record of the season being walked: key (id lo, id hi, age), cursor
WALK, TBL, TBL_SIZE = 0x02e8b198, 0x02e8b798, 0x200
WALK_SIZE = 0x600                                 # the code (the tables follow it)
HB = WALK                                         # hashb, the walk's first block
WALK_CODE = 0x02e8b1d0                            # the walk itself, behind HB
F_W12 = TBL + 0x1e8                               # form weights, age .. age-2
T_PHASE, T_SIX, T_TRAJ = TBL, TBL + 0x48, TBL + 0x108
T_PLAYT, T_PRE, T_HEADT, T_CEILT = TBL + 0x111, TBL + 0x119, TBL + 0x121, TBL + 0x131
T_MINUS3, T_FLOOR, T_DECL, T_DECI = TBL + 0x141, TBL + 0x142, TBL + 0x150, TBL + 0x1a0
T_ARCHN, T_INBAND, T_FORM_LO = TBL + 0x1c4, TBL + 0x1d4, TBL + 0x1dc
T_DAGE, T_GATE86, T_GATE89 = TBL + 0x1dd, TBL + 0x1de, TBL + 0x1df
T_CONSOL, T_POSH = TBL + 0x1e0, TBL + 0x1e4
T_REC = TBL + 0x1f0

# the bytes each code block may take; build() stops when one outgrows its gap
ROOM = {'curve': 84, 'B1': 137, 'focus': 98, 'B2': FOCUS - B2,
        'HB': WALK_CODE - HB, 'walk': WALK_SIZE - (WALK_CODE - HB)}


def tables():
    """(DATA image, SEASON image): the tables of hook A and of the season walk."""
    multq = [round(mult(age) * 4) for age in range(15, 54)]
    marg = [margin(age) for age in range(15, 54)]
    phys_sel = {SEL[p] for p in PHYSICAL}
    phys = [1 if f in phys_sel else 0 for f in range(0x27)]
    f = lambda x: struct.pack('<f', x)
    a = (b'\x0c' * 16 + bytes(multq) + b'\x01' * 17 +          # MULTQ (age<15: 12, 54+: 1)
         b'\x00' * 16 + bytes(marg) + b'\x00' * 17 +           # MARGIN (age<15 and 54+: 0)
         bytes(phys) + b'\x00' * (40 - len(phys)) +            # PHYS (40 bytes: 0x27 + 1 pad)
         bytes(POSTBL2) +                                      # POSTBL2 (16 bytes)
         bytes(POSTBL) +                                       # POSTBL (16 bytes)
         f(0.25) + f(float(PLAYTIME_FULL)) + f(1 - PLAYTIME_WEIGHT) +
         f(PLAYTIME_WEIGHT) + f(DECLINE_TECH))                 # F_INV4 F_FULL F_INV1PW F_PW F_DTECH
    assert len(a) == 236, len(a)
    t = bytearray(TBL_SIZE)

    def put(addr, data):
        t[addr - TBL:addr - TBL + len(data)] = data
    for a_i in range(4):
        put(T_PHASE + 18 * a_i, bytes(PHASE[a_i]))
    for pos in range(16):
        put(T_SIX + 12 * pos, bytes(six(pos)))
    put(T_TRAJ, bytes(TRAJ))
    put(T_PLAYT, bytes(PLAYT))
    put(T_PRE, bytes(PRE))
    for a_i in range(4):
        for band in range(4):
            t[T_HEADT - TBL + 4 * a_i + band] = TALENT[a_i][band]
            t[T_CEILT - TBL + 4 * a_i + band] = CEIL[a_i][band]
    t[T_MINUS3 - TBL] = DERAIL_CEIL
    t[T_FLOOR - TBL] = DECLINE_FLOOR
    shift = POS_SHIFT[6][1]                        # the neutral position (CMF)
    for fi, (name, sels, start) in enumerate(FAMILIES):
        o = T_DECL - TBL + 8 * fi
        t[o] = start + shift
        t[o + 1] = 0                               # the position shift (DECL's second table)
        t[o + 2] = fi                              # the family mask byte
        t[o + 3] = len(sels)
        t[o + 4:o + 8] = bytes(sels[:4])
    for sel in range(0x0e, 0x25):
        t[T_DECI - TBL + sel - 0x0e] = ci(sel)
    t[T_ARCHN - TBL:T_ARCHN - TBL + 16] = bytes(ARCH_NIBBLES)
    t[T_INBAND - TBL:T_INBAND - TBL + 8] = bytes(INBAND)
    t[T_FORM_LO - TBL] = FORM_LO
    t[T_DAGE - TBL] = DERAIL_AGE
    t[T_GATE86 - TBL] = GATE86
    t[T_GATE89 - TBL] = GATE89
    t[T_CONSOL - TBL] = CONSOLIDATE
    put(T_POSH, bytes((s_[1] & 0xff) for s_ in POS_SHIFT) + b'\0\0\0')
    # the form weights in the order w_form reads them: hashb(age), hashb(age-1),
    # hashb(age-2) -> 51, 77, 128 (growth_cave.form weights age-2 the most)
    put(F_W12, b'\x33\x4d\x80')
    return a, bytes(t)



# ---------------- the machine code ----------------


def _asm(ks, src, base):
    enc, _ = ks.asm(src, base)
    assert enc is not None, 'keystone refused:\n' + src
    return bytes(enc)


def _find(blob, hex_pattern):
    """The offset of a byte pattern in an assembled block."""
    return blob.index(bytes.fromhex(hex_pattern))


def _emit():
    """Assemble the six code blocks.  HB and WALK first: the walk is the only caller of
    HB, and B1 and B2 are two halves of one flow, so B2 is assembled first to learn the
    address B1 must jump to."""
    from keystone import Ks, KS_ARCH_X86, KS_MODE_32
    ks = Ks(KS_ARCH_X86, KS_MODE_32)
    parts = {}

    # ---- HB: hashb(pid, age), cdecl (age, pidLo) -> the low byte in eax.  One small
    #      routine so the walk calls the chain the way the Python twin does.
    hb_src = f"""
        push ebx
        mov eax, [esp + 8]
        imul eax, eax, 0x85ebca6b
        add eax, [esp + 12]
        imul eax, eax, 0xc2b2ae35
        mov ebx, eax
        shr ebx, 15
        xor eax, ebx
        imul eax, eax, 0x27d4eb2d
        mov ebx, eax
        shr ebx, 16
        xor eax, ebx
        pop ebx
        ret
    """
    parts['HB'] = _asm(ks, hb_src, HB)

    # ---- WALK: the season hook, in the .trace gap behind the day step fcn_0362752f.
    #      In: esi = the player of the game's age walk (his age is already raised), the
    #      game's registers live.  Out: every register as it was and the game's loop
    #      resumed.  A player without a growth record gets two things a season: the points
    #      on the position's attributes (BASE x TRAJ x PLAY x HEAD, the
    #      arithmetic of growth_cave.season_points) and one point off each family from its
    #      own age (growth_cave.decline_sel).
    walk_src = f"""
        cld
        pushad
        pushfd
        mov ebp, esp
        sub esp, 0x48
        mov edi, esi
        cmp dword ptr [edi + 0xa8], 0xffffffff          // a free agent does not grow
        je w_out

        // a player with a growth record is hook A's (the tracked squad): the season
        // walk only drives the players the game itself leaves alone
        mov eax, dword ptr [{MODE_OBJECT:#x}]
        mov eax, [eax + 0x30]
        lea eax, [eax + 0xd10140]
        mov ecx, eax
        push dword ptr [edi + 0x30]
        push dword ptr [edi + 0x2c]
        call {TRACKED:#x}
        test al, al
        jnz w_out

        // the first hash byte: the archetype (bits 0-2) and the intake band (bits 3-5)
        push dword ptr [edi + 0x2c]
        push 0
        call {HB:#x}
        add esp, 8
        movzx ecx, al
        movzx edx, al
        and ecx, 15
        shr edx, 3
        and edx, 7
        movzx edx, byte ptr [edx + {T_INBAND:#x}]
        mov byte ptr [ebp - 12], dl
        movzx ecx, byte ptr [ecx + {T_ARCHN:#x}]        // 0 early 1 normal 2 late 3 limited
        mov byte ptr [ebp - 11], cl
        movzx eax, byte ptr [edx + ecx * 4 + {T_HEADT:#x}]
        mov byte ptr [ebp - 10], al                     // talent
        movzx eax, byte ptr [edx + ecx * 4 + {T_CEILT:#x}]
        mov [ebp - 8], eax                              // ceiling

        // the age
        mov eax, [edi + 0x1c]
        shr eax, 7
        and eax, 0x3f
        mov [ebp - 4], eax
        cmp eax, 15
        jb w_out
        cmp eax, 60
        jae w_out

        // this age's hash byte (the dither and both gates read it)
        push dword ptr [edi + 0x2c]
        push dword ptr [ebp - 4]
        call {HB:#x}
        add esp, 8
        mov [ebp - 44], al

        // two bad draws in a row before 20 derail a career: talent -1, ceiling -3
        movzx ecx, byte ptr [ebp - 10]
        cmp dword ptr [ebp - 4], {DERAIL_AGE}
        ja w_consol
        mov eax, [ebp - 4]
        dec eax
        mov [ebp - 20], eax
        push dword ptr [edi + 0x2c]
        push eax
        call {HB:#x}
        add esp, 8
        cmp al, {FORM_LO}
        jae w_consol
        dec dword ptr [ebp - 20]
        push dword ptr [edi + 0x2c]
        push dword ptr [ebp - 20]
        call {HB:#x}
        add esp, 8
        cmp al, {FORM_LO}
        jae w_consol
        dec ecx
        mov eax, [ebp - 8]
        sub eax, {DERAIL_CEIL}
        mov [ebp - 8], eax
    w_consol:
        // a breakout last season is followed by three quarters (consolidation)
        mov [ebp - 20], ecx
        mov eax, [ebp - 4]
        dec eax
        push dword ptr [edi + 0x2c]
        push eax
        call {HB:#x}
        add esp, 8
        mov ecx, [ebp - 20]
        cmp al, {CONSOLIDATE}
        jb w_talent
        lea ecx, [ecx + ecx * 2]
        shr ecx, 2
    w_talent:
        mov byte ptr [ebp - 10], cl

        // BASE: the archetype's row of PHASE, the age's byte (a 16th of a point).
        // A row is 18 bytes (ages 15..32), so an older player must not index it.
        mov eax, [ebp - 4]
        sub eax, 15
        cmp eax, 17
        ja w_decline
        movzx ecx, byte ptr [ebp - 11]
        lea ecx, [ecx + ecx * 8]
        lea ecx, [ecx * 2 + {T_PHASE:#x}]
        movzx ecx, byte ptr [eax + ecx]
        mov [ebp - 16], ecx
        test ecx, ecx
        jz w_decline

        // TRAJ: (128 u2 + 77 u1 + 51 u0) >> 8 through the trajectory table
        mov dword ptr [ebp - 24], 0
        xor ecx, ecx
    w_form:
        mov eax, [ebp - 4]
        sub eax, ecx
        push ecx
        push dword ptr [edi + 0x2c]
        push eax
        call {HB:#x}
        add esp, 8
        pop ecx
        movzx eax, al
        movzx edx, byte ptr [ecx + {F_W12:#x}]
        imul eax, edx
        add [ebp - 24], eax
        inc ecx
        cmp ecx, 3
        jb w_form
        mov eax, [ebp - 24]
        shr eax, 8
        cmp eax, 255
        jbe w_f2
        mov eax, 255
    w_f2:
        shr eax, 5
        movzx eax, byte ptr [eax + {T_TRAJ:#x}]
        movzx edx, byte ptr [ebp - 44]
        shr edx, 5
        movzx edx, byte ptr [edx + {T_PLAYT:#x}]
        imul eax, edx
        mov [ebp - 28], eax                             // q, eighths x eighths
        test eax, eax
        jz w_decline

        // the position's twelve attributes, and how far this season reaches
        mov ecx, [edi + 4]
        shr ecx, 28
        and ecx, 15
        cmp ecx, 16
        jb w_pos
        xor ecx, ecx
    w_pos:
        lea ecx, [ecx + ecx * 2]
        shl ecx, 2
        add ecx, {T_SIX:#x}
        mov [ebp - 32], ecx
        movzx edx, byte ptr [ebp - 44]
        shr edx, 5
        movzx edx, byte ptr [edx + {T_PRE:#x}]
        mov [ebp - 36], edx
        mov dword ptr [ebp - 40], 0
    w_attr:
        mov edx, [ebp - 40]
        cmp edx, [ebp - 36]
        jae w_decline
        mov eax, [ebp - 32]
        movzx esi, byte ptr [eax + edx]
        mov [ebp - 48], esi                             // the selector
        lea eax, [ebp - 52]
        push eax
        push esi
        mov ecx, edi
        call {GETTER:#x}
        mov esi, [ebp - 52]                             // its value
        cmp esi, [ebp - 8]
        jae w_next                                      // at the personal ceiling
        movzx ecx, byte ptr [ebp - 10]
        mov edx, 99
        sub edx, esi
        imul edx, ecx
        shr edx, 4
        cmp edx, 8
        jbe w_head2
        mov edx, 8
    w_head2:
        mov [ebp - 56], edx
        movzx ecx, byte ptr [ebp - 44]
        cmp esi, 89
        jb w_gate86
        cmp ecx, {GATE89}
        jb w_next
    w_gate86:
        cmp esi, 86
        jb w_count
        cmp ecx, {GATE86}
        jb w_next
    w_count:
        mov ecx, [ebp - 16]
        imul ecx, [ebp - 28]
        imul ecx, [ebp - 56]
        shr ecx, 1
        mov [ebp - 60], ecx                             // the threshold (no 255 cap)
        movzx eax, byte ptr [ebp - 44]
        mov edx, [ebp - 40]
        imul edx, 0x25
        add eax, edx
        and eax, 0xff
        mov [ebp - 64], eax                             // this attribute's draw
        cmp eax, [ebp - 60]
        jae w_next
        mov ecx, [ebp - 60]
        shr ecx, 1
        mov edx, 1
        cmp eax, ecx
        jae w_step1
        mov edx, 2                                      // a strong draw: two points
    w_step1:
        add edx, esi
        cmp edx, 99
        jbe w_set
        mov edx, 99
    w_set:
        push edx
        push dword ptr [ebp - 48]
        mov ecx, edi
        call {SETTER:#x}
    w_next:
        inc dword ptr [ebp - 40]
        jmp w_attr

        // DECLINE: from each family's own age (shifted by the position) one point off it,
        // walking the family's attributes so they fall together
    w_decline:
        mov ecx, [edi + 4]
        shr ecx, 28
        and ecx, 15
        movsx ebx, byte ptr [ecx + {T_POSH:#x}]
        xor esi, esi
    w_fam:
        lea eax, [esi * 8 + {T_DECL:#x}]
        movzx ecx, byte ptr [eax]
        add ecx, ebx
        cmp ecx, [ebp - 4]
        jne w_fnext
        movzx ecx, byte ptr [eax + 3]
        test ecx, ecx
        jz w_fnext
        mov [ebp - 32], eax
        mov eax, [ebp - 4]
        shr eax, 1
        xor edx, edx
        div ecx
        mov ecx, [ebp - 32]
        movzx edx, byte ptr [ecx + edx + 4]
        mov [ebp - 48], edx
        lea eax, [ebp - 52]
        push eax
        push edx
        mov ecx, edi
        call {GETTER:#x}
        mov ecx, [ebp - 52]
        cmp ecx, {DECLINE_FLOOR}
        jbe w_fnext
        dec ecx
        push ecx
        push dword ptr [ebp - 48]
        mov ecx, edi
        call {SETTER:#x}
    w_fnext:
        inc esi
        cmp esi, 5
        jb w_fam
    w_out:
        mov esp, ebp
        popfd
        popad
        mov edx, dword ptr [0x24fe518]
        jmp {SEASON_NEXT:#x}
    """
    parts['WALK'] = _asm(ks, walk_src, WALK_CODE)

    # ---- curve: (ebx = age, esi = rating) -> st0 = mult x scale.  Hook A's age curve,
    #      in the .reloc gap the module has always used for it.
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

    # ---- B2: the award arithmetic (in: edx = &exp, ebx = age, esi = rating,
    #      edi = player, [ebp-8] = appearances, frame of B1) ----
    b2 = B2
    b2_src = f"""
    b_pos:
        fld dword ptr [edx]
        call {CURVE:#x}
        fmulp
        cmp dword ptr [ebp + 0x20], 2
        jz b_k2
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
    b_k2:
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

    # ---- B1: restore &exp after either lookup outcome; both paths must start B2 with its fld ----
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
        jz b_untracked
        mov ecx, [ebp - 12]
        push dword ptr [edi + 0x30]
        push dword ptr [edi + 0x2c]
        call {GROWTH_REC:#x}
        mov edx, [eax + 0x1a0]
        mov [ebp - 8], edx
    b_untracked:
        mov edx, [ebp + 0x1c]
        jmp {b2:#x}
    """
    parts['B1'] = _asm(ks, b1_src, B1)

    # ---- FOCUS: in place of `call fcn_036216e9` in the two training functions
    #      (in: edi = player, ecx = growth record, [esp+4] = selector,
    #       [esp+8] = exp; the caller cleans nothing: ret 8) ----
    focus_src = f"""
        push ebx
        push esi
        push edi
        push ebp
        mov ebp, esp
        sub esp, 16
        mov [ebp - 8], ecx
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
        call {CURVE:#x}
        fild dword ptr [ebp + 0x18]
        fmulp
        sub esp, 4
        fistp dword ptr [esp]
        push dword ptr [ebp + 0x14]
        mov ecx, [ebp - 8]
        call {LEVELS:#x}
        mov esp, ebp
        pop ebp
        pop edi
        pop esi
        pop ebx
        ret 8
    """
    parts['focus'] = _asm(ks, focus_src, FOCUS)
    return parts


def build():
    """name -> (address, bytes) of every block, assembled again."""
    parts = _emit()
    data, season = tables()
    out = {k: (a, parts[k]) for k, a in
           (('curve', CURVE), ('B1', B1), ('focus', FOCUS))}
    out['HB'] = (HB, parts['HB'])
    out['walk'] = (WALK_CODE, parts['WALK'])
    out['B2'] = (B2, parts['B2'])
    out['data'] = (DATA, data)
    out['season'] = (TBL, season)
    for k, (a, b) in out.items():
        if k in ROOM:
            assert len(b) <= ROOM[k], f'{k} overflows its fragment: {len(b)} > {ROOM[k]}'
    return out


def patches(parts=None):
    """(address, old bytes, new bytes) of the four hook sites."""
    if parts is None:
        parts = {k: v for k, v in build().items()}
    jmp = lambda site, to: b'\xe9' + struct.pack('<i', to - site - 5)
    call = lambda site, to: b'\xe8' + struct.pack('<i', to - site - 5)
    out = (
        (AWARD, bytes.fromhex('5589e581ec'), jmp(AWARD, B1)),
        (SEASON_CALL, bytes.fromhex('8b1518e54f02'), jmp(SEASON_CALL, WALK_CODE) + b'\x90'),
    )
    for site in FOCUS_CALLS:                    # `call LEVELS` -> `call FOCUS`
        out += ((site, call(site, LEVELS), call(site, FOCUS)),)
    return out


CODE_PARTS = {           # name -> (address, hex chunks); growth_cave.py build verifies
    "curve": (
        0x047d5b8c,
        "8d43f10fb68010c2980250db0424d80dd8c29802588d43f10fb68858c2980285",
        "c9742b8d469df7d883fe4b7c0883fb157f0383c00450db04245851db042458de",
        "f9d9e8dbf1dbc1d9c9ddd8dec9c3ddd8d9eec3",
    ),
    "B1": (
        0x047d6377,
        "5356575589e583ec108b7d148b5f1cc1eb0783e33f8d45fc6a00508d472c50e8",
        "7d2806ff83c40c0fb6f08b551cf64203800f85d60a0000c745f814000000a1e0",
        "0365028b40308d804001d1008945f48b4df4ff7730ff772ce8e15096fe84c074",
        "178b4df4ff7730ff772ce8e0a394fe8b90a00100008955f88b551ce9590a0000",
    ),
    "focus": (
        0x047d6efe,
        "5356575589e583ec10894df88b5f1cc1eb0783e33f8d45fc6a00508d472c50e8",
        "f61c06ff83c40c0fb6f0e85fecffffdb4518dec983ec04db1c24ff75148b4df8",
        "e8a6a7e4fe89ec5d5f5e5bc20800",
    ),
    "HB": (
        0x02e8b198,
        "538b44240869c06bcaeb850344240c69c035aeb2c289c3c1eb0f31d869c02deb",
        "d42789c3c1eb1031d85bc3",
    ),
    "walk": (
        0x02e8b1d0,
        "fc609c89e583ec4889f783bfa8000000ff0f84f5020000a1e00365028b40308d",
        "804001d10089c1ff7730ff772ce8b3022b0084c00f85d2020000ff772c6a00e8",
        "84ffffff83c4080fb6c80fb6d083e10fc1ea0383e2070fb6926cb9e8028855f4",
        "0fb6895cb9e802884df50fb6848ab9b8e8028845f60fb6848ac9b8e8028945f8",
        "8b471cc1e80783e03f8945fc83f80f0f827702000083f83c0f836e020000ff77",
        "2cff75fce81fffffff83c4088845d40fb64df6837dfc1477368b45fc488945ec",
        "ff772c50e8fffeffff83c4083c60731fff4decff772cff75ece8eafeffff83c4",
        "083c60730a498b45f883e8038945f8894dec8b45fc48ff772c50e8c9feffff83",
        "c4088b4dec3ce072068d0c49c1e902884df68b45fc83e80f83f8110f87830100",
        "000fb64df58d0cc98d0c4d98b7e8020fb60c08894df085c90f8466010000c745",
        "e80000000031c98b45fc29c851ff772c50e872feffff83c408590fb6c00fb691",
        "80b9e8020fafc20145e84183f90372d78b45e8c1e8083dff0000007605b8ff00",
        "0000c1e8050fb680a0b8e8020fb655d4c1ea050fb692a9b8e8020fafc28945e4",
        "85c00f84fc0000008b4f04c1e91c83e10f83f910720231c98d0c49c1e10281c1",
        "e0b7e802894de00fb655d4c1ea050fb692b1b8e8028955dcc745d8000000008b",
        "55d83b55dc0f83b90000008b45e00fb634108975d08d45cc505689f9e8dfc499",
        "008b75cc3b75f80f838f0000000fb64df6ba6300000029f20fafd1c1ea0483fa",
        "087605ba080000008955c80fb64dd483fe59720881f9d2000000726083fe5672",
        "0881f98000000072538b4df00faf4de40faf4dc8d1e9894dc40fb645d48b55d8",
        "6bd22501d025ff0000008945c03b45c4732a8b4dc4d1e9ba0100000039c87305",
        "ba0200000001f283fa637605ba6300000052ff75d089f9e844cd9900ff45d8e9",
        "3bffffff8b4f04c1e91c83e10f0fbe997cb9e80231f68d04f5e8b8e8020fb608",
        "01d93b4dfc753f0fb6480385c974378945e08b45fcd1e831d2f7f18b4de00fb6",
        "5411048955d08d45cc505289f9e8eec399008b4dcc83f92d760c4951ff75d089",
        "f9e8dacc99004683fe0572aa89ec9d618b1518e54f02e955827900",
    ),
    "B2": (
        0x047d6e50,
        "d902e835edffffdec9837d20027421db45f8d835dcc29802d9e8dbf1dbc1d80d",
        "e0c29802d805e4c29802d9c9ddd8dec9d91aeb2cd9028b45188b0031c983f826",
        "77070fb68890c29802d905e8c2980283fb1f7c0885c97404ddd8d9e8dec9d91a",
        "89ec5d5f5e5b5589e581ec3c020000e909c10dff",
    ),
    "data": (
        0x0298c200,
        "0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c0c06060605050505040404030303020201",
        "0101010101010101010101010101010101010101010101010101010101010101",
        "0101010101010101000000000000000000000000000000001919191313130c0c",
        "0c05050501010101010101010101010101010101010101010101010101010000",
        "0000000000000000000000000000000000000000000000000000000000000000",
        "0000000000000000000000000000000101010001010100001111141414171414",
        "14171f1f1a25141413131111110f1111110f0f0f101f11110000803e0000a041",
        "cdcc4c3fcdcc4c3e0000803e",
    ),
    "season": (
        0x02e8b798,
        "100f0e0c0a070402010000000000000000000d0e0f0e0d0b0907050403020100",
        "00000000050607090b0c0d0e0e0d0c0a07040100000012100e0b080503010000",
        "0000000000000000130e12111f2320211622240f2311120e1314151f22252021",
        "11120e1f231315251422202111120e1f2313152514222021111214130e15231f",
        "2520210f1512141125190f0e202124171112141525230e1f0f202110111f2312",
        "25150e14190f1013111f231225150e14190f10130f1716241f2021250e101112",
        "1f0f111523251724120e20211f0f111523251724120e2021101d1a1b1c242021",
        "0e0f1112130e12111f2320211622240f130e12111f2320211622240f130e1211",
        "1f2320211622240f00040608080a0a0c1003030404040404020c0c0b0a090807",
        "0606070808050607080506080803030404484e565b464c545c484e585c3e4246",
        "4a032d000000000000000000000000001b0000031f2311001d00010125000000",
        "20000203212024002100030512141518220004050f170e160000000000000000",
        "0000000000000000000000000000000000000000000000000000000000000000",
        "0200000200000102030103040000000000000100040102000000000000000000",
        "00000000000101020301010201030101020103010001020300010203601480d2",
        "e0000000ffffffff334d8000000100000300000000000000000000",
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
    ('exp to levels', 0x036216e9, '5589e5568b750883fe627c0731'),
)


def lua_block_hex(key):
    """The bytes a block is written with: the code as assembled, the tables padded to
    the room the module reserves for them."""
    hexed = part(key)[1]
    size = {'data': 236, 'season': TBL_SIZE}.get(key)
    if size:
        hexed += '00' * (size - len(bytes.fromhex(hexed)))
    return hexed


def lua_block():
    """The generated Lua code block for MLGrowth.lua."""
    sizes = {'data': 236, 'season': TBL_SIZE}
    lines = [
        '-- Generated by growth_cave.py (do not edit by hand; test_growth.py checks this block)',
    ]
    for name, key in (('CAVE_CURVE', 'curve'), ('CAVE_B1', 'B1'), ('CAVE_FOCUS', 'focus'),
                      ('CAVE_B2', 'B2'), ('CAVE_HB', 'HB'), ('CAVE_WALK', 'walk'),
                      ('CAVE_DATA', 'data'), ('CAVE_SEASON', 'season')):
        at = part(key)[0]
        size = sizes.get(key, len(bytes.fromhex(part(key)[1])))
        lines += ['local %s = 0x%08x' % (name, at), 'local %s_SIZE = %d' % (name, size)]
    lines += ['', 'local BLOCKS = {']
    for label, key in (('age curve code', 'curve'), ('exp award code', 'B1'),
                       ('training scale code', 'focus'), ('exp award code 2', 'B2'),
                       ('hash chain', 'HB'), ('season walk code', 'walk'),
                       ('growth tables', 'data'), ('season tables', 'season')):
        lines.append('    { "%s", CAVE_%s, "%s" },' % (label, key.upper(), lua_block_hex(key)))
    lines += ['}', '', 'local SITES = {']
    names = {AWARD: 'exp award entry', SEASON_CALL: 'season age walk',
             FOCUS_CALLS[0]: 'individual training', FOCUS_CALLS[1]: 'team training'}
    for at, old, new in patches():
        lines.append('    { "%s", 0x%08x, "%s", "%s" },' % (names[at], at, old.hex(), new.hex()))
    lines += ['}', '', 'local CONTEXT = {']
    for name, at, hx in CONTEXT:
        lines.append('    { "%s", 0x%08x, "%s" },' % (name, at, hx))
    lines += ['}', '']
    return '\n'.join(lines)


def calibrate(exe_path, save_path, seasons=6):
    """Replay the model over every player of a save and print how the overall ratings
    move.  growth_twin.py is the fuller check (it also tests the outcome bands); this
    one exists for a save, whose players carry the ids the hash chain needs."""
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
            player_id = struct.unpack_from('<I', r, 0x2c)[0]
            values = {sel: getf(r, sel) for sel in slot}
            gained = 0
            for sel, step in season_points(player_id, age, values, pos):
                setf(r, sel, min(99, getf(r, sel) + step))
                gained += step
            d = decline_sel(player_id, age, pos)
            if d is not None and getf(r, d) > DECLINE_FLOOR:
                setf(r, d, getf(r, d) - 1)
                gained -= 1
            if gained:
                risen[wr.name(bytes(r))] += gained
    after = {k: rater(bytes(r)) for k, r in records.items()}

    bands = [(0, 59), (60, 64), (65, 69), (70, 74), (75, 79), (80, 84), (85, 99)]
    print(f'{len(records)} players, {seasons} seasons of the season walk')
    print(f'{"OVR":>8s} {"before":>8s} {"after":>8s}')
    for lo, hi in bands:
        b = sum(lo <= v <= hi for v in before.values())
        a = sum(lo <= v <= hi for v in after.values())
        print(f'{lo:3d}-{hi:3d} {b:8d} {a:8d}')
    print(f'{"mean":>8s} {sum(before.values()) / len(before):8.2f} '
          f'{sum(after.values()) / len(after):8.2f}')
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
        for k in sorted(CODE_PARTS, key=lambda k: part(k)[0]):
            a, hx = part(k)
            n = len(bytes.fromhex(hx))
            print(f'{k:6s} {a:#010x} +{n:#05x}' + (f' of {ROOM[k]:#x}' if k in ROOM else ''))
        for at, old, new in patches():
            print(f'patch  {at:#010x}: {old.hex()} -> {new.hex()}')
