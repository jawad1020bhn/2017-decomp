"""What MLMoney.lua and MLTransfers.lua put into the game, and the same arithmetic as Python.

    python3 money_cave.py            print the layout and the code bytes
    python3 money_cave.py build      assemble the code again (needs: pip install keystone-engine)
                                     and compare it with the bytes kept in this file
    python3 money_cave.py lua <PES2017.exe>
                                     print the part of MLMoney.lua that is made from this file and
                                     the exe: ROUTINES, SITES and CONTEXT (test_money.py checks that
                                     MLMoney.lua holds exactly this text)
    python3 money_cave.py lua <PES2017.exe> transfers
                                     the same for MLTransfers.lua: ROUTINE, SITE, NEED_ROUTINES,
                                     NEED_SITES, MONEY and CONTEXT

MLMoney.lua changes up to 25 places of PES2017.exe (sha256 44b0caaa...) and fills a
piece of unused memory with 13 small routines and their tables. MLTransfers.lua changes
one place more and fills a second piece (the transfers of the computer clubs; its price
ceiling was part of MLMoney.lua in its versions 5 and 6). Its routine calls FEE_CODE and
divides by the 100 and the 1000 at HUNDRED_AT, all in the memory of MLMoney.lua, so it
writes nothing unless it finds them there (MONEY_NEEDED). Since its version 6 it can
change two places more and fill a third piece with two routines (the position need:
NEED_PLAN_SOURCE, NEED_PICK_SOURCE; in Python need_slot and need_lowest; test_need.py).

Fee, fcn_038ab832 (MASTER_LEAGUE.md 6.2). The 17 bytes at 0x038ab8db hold the rating part
of the formula, `9000 * max(0, rating - 68)`, left in edi. They become a call to FEE_CODE:

    v           = VALUE[rating] * AGE[age] / 100
    p           = min(max(0, rating - TALENT[age]) * TALENT_STEP, TALENT_MAX)
    v           = v + min(v * p / 100, TALENT_CAP)       the talent bonus; TALENT[age] = 255: none
    v           = v * POSITION[registered position] / 100
    v           = v * (SPREAD_LOW + (hash * SPREAD_RANGE >> 8)) / 1000, at most 99,999,900
    edi         = v + v * (popularity * FAME) / 100000
    [ebp - 0xc] = 0.0        the factor of the salary part; the game goes on to compute
                             trunc(salary * factor) + edi, which is now edi

All divisions drop the remainder. rating is in eax there (0 to 255; above 99 counts as
99) and the player record in ebx. Of the record (what the game's getter fcn_038278b0
gives for fields 0x2b and 0x00): age = 6 bits at +0x1c, bits 7-12; registered position =
4 bits at +0x04, bits 28-31, in the edit file's order (0 GK ... 12 CF). popularity is the
12-bit number at +0xb4, bits 11-22. hash is one byte made from the player's id (the word
at +0x2c and the dword at +0x30), so it is the same for a player at every call.
Everything after that in the function is as before: a handed-in figure taken as it is,
the random change, the limit.

Salary, fcn_038ac66e (6.1). The 98 bytes from 0x038ac875 compute A = 30 * rating - 500
into [ebp - 0x38] and B (the three steps at 65, 75, 85) into [ebp - 0x34]. The first 7
bytes become a call to SALARY_CODE and a jump over the rest:

    [ebp - 0x38] = SALARY[rating] * SALARY_AGE[age] / 100
    [ebp - 0x34] = 0

so `salary = trunc((role bonus + popularity part + that) * club factor) + ...`.

Budgets, fcn_038ad9c4 (6.4). `add esi, esi; mov eax, [eax + 0x30]` at 0x038adc47 (the
mean value of the 16 best players, doubled) becomes a call to BUDGET_T_CODE:
`esi = esi * BUDGET_T / 100`, the same mov, and the zero flag the next jump reads.
`lea esi, [ecx + eax*2]; call 0x0381c0e5` at 0x038add08 (wage bill + twice the mean
salary of the 16 best paid) becomes a call to BUDGET_S_CODE and three nops:
`esi = ecx + eax * BUDGET_S / 100`, then a jump to 0x0381c0e5, which returns to the nops.

Prize money (6.7). cup_prize (fcn_038aa307) searches the 73 rows (competition, stage,
amount) at 0x0216b178. The three instructions that hold the table's address get the
address of a copy with other amounts (CUP_TAB); the game's table is not written.
league_prize (fcn_038a9ebb) reads the amount for a place from a list on its stack:
`mov eax, [ebp + eax*4 - 0x17c]` at 0x038aa2dd (first list, index 0 to 22) and
`mov eax, [ebp + eax*4 - 0x120]` at 0x038aa2c6 (second list, index 0 to 24). The second
becomes `mov eax, [eax*4 + LEAGUE2_TAB]`, the same length. The first becomes a call to
LEAGUE_CODE: the number of the club's league is in edi there (16 bits, from fcn_03879e04);
if it is one of the LEAGUE_COUNT numbers at LEAGUE_IDS, the amount is that league's row of
LEAGUE_ROWS_TAB (words, in units of 100 stored), else `[eax*4 + LEAGUE1_TAB]`. The routine
uses ecx and edx, which the game loads anew right after.
A cup without a row in the table gets one of six amounts by stage, the immediates of six
`mov edi` (NATIONAL_SITES); the module writes other numbers there.
prize_step (fcn_03640686) hands every prize to balance_add (fcn_038aadb7), at 0x03640ac5
(league) and 0x03640b78 (cup). Both calls go to PRIZE_CODE instead: it calls balance_add
with the same argument and then, in game mode 0x13 (Master League), transfer_budget_add
(fcn_038aac87) with `amount * SHARE / 100`.

Salary once more. `fmul qword [0x01f2fe88]` at 0x038aca19 multiplies (251 - rank) by 0.004;
its address operand (0x038aca1b) is pointed to RANK_STEP, a number of the module, so the
shared constant stays as it is. `add esi, [ebp - 0x50]` at 0x038aca2b (esi = the role
bonus R) becomes a call to BONUS_R_CODE: `esi = esi * BONUS / 100`, then that add.
`mov eax, [ebp - 0x34]; add eax, [ebp - 0x50]` at 0x038acd96 (award bonuses + band bonus
T) becomes a call to BONUS_END_CODE: `eax = (awards + T) * BONUS / 100`.

Contract years (7.3). `mov eax, 3` at 0x03887fc1 in fcn_03887f5d is the limit for players
of 23 and younger; its number is replaced.

Yearly income (6.4). season_income (fcn_038ade76) calls the wage bill function and then
overwrites its result: `call wage_bill; mov eax, [ebp + 8]; push eax; call club_popularity`.
The nine bytes after the first call become a call to WAGES_KEEP_CODE, which stores eax in
the function's local [ebp - 4] (a flag byte for the wage bill function, not read again),
pushes the argument under its own return address and jumps to club_popularity, so that
function returns to the nops after the call as if the game had called it. The last step
of the amount, `lea eax, [esi - 3451330]` at 0x038adeee, becomes a call to INCOME_N_CODE:

    eax = esi - 3451330
    eax = eax * INCOME / 100            only if eax > 0 (INCOME_SCALE_CODE)
    eax = eax + [ebp - 4] * INCOME_WAGES / 100

and the game's `test eax, eax` and its floor of 1,000 follow as before. With INCOME_WAGES
off the percent is 0 and the first place is not changed. `imul eax, eax, 5000` at
0x038a9e9c (the amount by rank, fcn_038a9e6b) and `add esi, 15000` at 0x038ae025 (the
starting amount in club_money_setup) become calls that do the same and apply INCOME.

The yearly budget step (6.7) is not changed. june_grants() below is its arithmetic, and
test_money.py runs the game's code for both days against it.

Transfers of the computer clubs (9.6, 9.10; MLTransfers.lua). ai_candidates (fcn_0365f5c2)
lists up to three players a computer club may sign for a position: it walks lists of
players by overall from the top of the club's rating range down and adds every player who
passes its tests with `mov ecx, [ebp + 0x24]; push esi; call 0x041293c0` at 0x0365fb0d.
None of the tests reads a price, and none asks the player's club. Those nine bytes become
a call to CEILING_CODE, which decides whether the player is added. If not, it drops its
return address and jumps to 0x0365fb28, where the game's own failed tests go: the next
player. What it reads of the game: from the frame of ai_candidates the player record, the
date, the pool object, the mode data, the position and the status band asked for and the
plan record (buying club, kind); through the saved ebp, from ai_pick_candidate
(fcn_03660c52), the only caller, the club level and the "second search" byte; and the
return address of ai_candidates, which says which of the two calls of ai_pick_candidate
this is. Only if that address is one of the two, and the level is 0 to 9, it decides at
all; otherwise the player is added as in the game.

MLTransfers.lua from version 2 on (version 1: only step 7, with wealth, premium and panic 100
and fame 0). A club has a persona: 14 numbers (GENE_NAMES), two ages and two places for
its second search, 20 bytes at GENES_TAB. Which persona: the one CLUBS names for the club
id (HAND_IDS, HAND_TYPES), else one of the 8 at BY_LEVEL_TAB for the level of the club's
record in the game's club ranking (mode data + 0xcc84cc, records of 16 bytes: club id,
place, points at +8, level at +0xe; the game's own search fcn_031b1c34 gives the first
record for a club that is not there, and so does the routine), drawn by the club id. Each
of the 14 numbers is, for a club, the persona's number x (PERSONA_LOW + (h x PERSONA_RANGE
>> 8)) / 1000, h being a byte drawn from club id and the number's place. Persona 0
(NEUTRAL) is what every club is with PERSONA off: it never refuses in steps 2 to 6.
A player is "free" if his status (+0xb4, bits 0-3) is 1 or 2, else "listed" if he has mark
29 or 30 of +0xb8, else "clubs". In order (accepts() below is the same in Python):

 0. Rivals (for "listed" and "clubs", if the player has a club): refused if the buyer's
    id and his club's id are a pair of RIVAL_PAIRS, in either order.
 1. The selling club (only for "clubs", and if the player has a club). With SELL_SIDE: the
    pool object counts more than 23 players for it (dword at +0x7ac + 4 x the low 14 bits
    of its id, as the game's own pool function asks), and, in the second call of
    ai_pick_candidate, the rule by which that function lets a player with a contract go
    after it has listed him: the buyer's level is 9 and the slot asks for a band, or the
    plan's kind is 1 and the level at least 8, or the kind is 4 and the level above the
    player's status band, or his band is below 7 and his club's level below 8. Then
    `keeps` of the selling club's persona: refused if a draw from club, player and date
    is below it. Unless the buyer's eleven (step 3) is KEEP_BIGGER points or more above
    the eleven of his club, `keeps` is KEEP_STEP higher for each point of
    rating + KEEP_FROM - eleven of his club above 0.
    SQUAD_PRESSURE (version 9, PRESSURE_CODE in a fifth piece of memory, CAVE_5; the
    routine above calls it for the comparison): if his club has more players of his
    group (GROUP_OF his registered position, bits 28-31 of +4: goalkeeper, defender,
    midfielder, forward) than PRESSURE_LIMITS of that group, `keeps` is the drop at
    PRESSURE_DROP_AT lower, not below 0. Counted: the entries of the club record's
    squad (the game's function at TEAM_RECORD; id pairs at +0xf8, count in bits 9-15
    of +0x328) that are not the game's "no player" and not in a deal (+0xb4, bits 4
    and 5), as the game's own count of goalkeepers in ai_candidates (0x0365f920) does.
    The squad is walked only for a draw from `keeps` minus the drop to `keeps` minus 1.
 2. Scouting (not for "listed", not for a rating of KNOWN or more, not for a popularity
    of FAME_KNOWN or more: the 12 bits from bit 11 of +0xb4): refused if a draw from
    player and buyer is not below `knows`.
 3. The player: refused if his rating is above eleven + `prestige`, eleven = (ranking
    points of the buyer x STRENGTH_A + STRENGTH_B) >> 16, kept inside the rating range of
    the level of its ranking record (WINDOW_LOW, WINDOW_TOP).
 4. Need: the slot asks for a status band, or the pool counts fewer than SQUAD players for
    the buyer. Unless the slot asks for a band: a draw from position, buyer and date
    picks, by `free`, `listed`, `clubs`, the place the club looks in for this position on
    this day, or none (refused; in need it takes the first of the persona's two places
    for the second search instead). If the month is WINTER, a second such draw must be below `winter`
    (not in need). In the second search the place is the first of the persona's two that
    the first search did not use. The player must be of that place. Then the ages (not
    in need), moved for the club by a draw from its id, -AGE_SHIFT to AGE_SHIFT years
    (age_shift() below): outside them he is refused if a draw from player and buyer is
    below `strict`; for a "free" player, if 100 x the draw is below `strict` x STRICT_FREE.
 5. The rating as this club sees it: rating - fog + (h x (2 fog + 1) >> 8). Refused if
    below eleven - `ambition` (not in need).
 6. In the second search: refused if that rating is above CEILING_TOP[level], unless the persona
   of the club has that limit switched off (byte KEEP_TOP_AT of it).
 7. The price, unless CEILING_TAB[level] is "none" (all divisions drop the remainder, and
    a product that does not fit 32 bits counts as the largest number):

    limit = CEILING_TAB[level] * wealth / 100
    limit = limit * (100 + NEED * panic / 100) / 100     in need, or in the second search
    limit = limit + limit * (h * (STRETCH * premium / 100)) / 25600
    limit = limit + limit * (popularity * fame) / 100000
    price = value * FREE / 100                   a "free" player
          = value * LISTED / 100                 a "listed" player
          = value                                else
    refused if price > limit

value is what FEE_CODE gives for the rating of step 5. h is one byte made from the
player's id and the id of the buying club, so one club goes further for a player than
another, and the same club decides the same way about the same player: h = ((word at
+0x2c) ^ (dword at +0x30) * 0x01000193 ^ club id * 0x9e3779b1) * 0x85ebca6b >> 24. The
other draws use the same two keys and the factors HASH_*. test_money.py runs the whole of
ai_candidates, and ai_pick_candidate up to the end of its two calls, against accepts()
and candidates().

The memory used is the end of the section .trace: the section's content ends at
0x047b005d, its declared size at 0x047b0123, and its last page runs to 0x047b0fff. The
section is readable, writable and executable. No call or jump of the exe goes there.
The tables and the routine of MLTransfers.lua are in a second piece (CAVE_2): the page of
the section .data1, which follows .trace and .xcode in memory. That section holds 0x170
bytes (0x047d4000-0x047d416f, code the game runs); the file's bytes for it end at
0x047d41ff and are zeros from 0x047d4170 on, and the rest of its page, to 0x047d4fff, is
not in the file: the loader fills it with zeros. The section is readable, writable and
executable. In the whole file 23 dwords have a value from 0x047d4170 to 0x047d4fff, at
places without a pattern (fewer than chance gives for a file of this size): no stored
address points there. (Version 1 used 0x047d3c40-0x047d3dbf, the end of .xcode's last
page; the routine of version 2 does not fit there, and that range is unused again.
Version 5 of MLMoney.lua kept the ceiling at 0x047b0130-0x047b01fb.)
"""
import struct
import sys

CAP = 99999900
UNIT = 100                      # the screens show 100 times the stored amount
CAVE = 0x047b0200
VALUE_TAB = CAVE                # 100 dwords, by rating 0-99
SALARY_TAB = CAVE + 0x190       # 100 dwords, by rating 0-99
AGE_TAB = CAVE + 0x320          # 64 words, percent, by age 0-63
SALARY_AGE_TAB = CAVE + 0x3a0   # 64 words, percent, by age 0-63
POSITION_TAB = CAVE + 0x420     # 16 words, percent, by registered position
FAME_AT = CAVE + 0x440          # dword: percent of value per 1000 popularity points
SPREAD_LOW_AT = CAVE + 0x444    # dword: lowest factor of the spread, in thousandths
SPREAD_RANGE_AT = CAVE + 0x448  # dword: width of the spread, in thousandths
BUDGET_T_AT = CAVE + 0x44c      # dword: transfer budget, percent of the mean value of the best 16
BUDGET_S_AT = CAVE + 0x450      # dword: salary budget, percent of the mean salary of the best 16
HUNDRED_AT = CAVE + 0x454       # dword 100
THOUSAND_AT = CAVE + 0x458      # dword 1000
MARK_AT = CAVE + 0x45c          # 4 bytes: MARK
MARK = b'MLM7'                  # MLTransfers.lua looks for its first three bytes
TALENT_TAB = CAVE + 0x480       # 64 bytes, by age 0-63: the rating above which a young player gets the
                                # talent bonus (255: no bonus at this age)
INCOME_N_CODE = CAVE + 0x460     # (0x4c0 to 0x4cb are not used)
INCOME_M_CODE = CAVE + 0x4cc
INCOME_SCALE_CODE = CAVE + 0x4d8
INCOME_S_CODE = CAVE + 0x4ec
LEAGUE_CODE = CAVE + 0x500
WAGES_KEEP_CODE = CAVE + 0x532
SALARY_CODE = CAVE + 0x540
BUDGET_T_CODE = CAVE + 0x580
BUDGET_S_CODE = CAVE + 0x5a0
LEAGUE1_TAB = CAVE + 0x5c0      # 23 dwords: league prize by place, first list (index 0 is not a place)
LEAGUE2_TAB = CAVE + 0x620      # 25 dwords: league prize by place, second list
RANK_STEP_AT = CAVE + 0x688     # double: rise of the club factor per place of the ranking
SHARE_AT = CAVE + 0x690         # dword: percent of a prize that goes to the transfer budget
BONUS_AT = CAVE + 0x694         # dword: percent of the game's role, band and award bonuses
PRIZE_CODE = CAVE + 0x6a0
BONUS_R_CODE = CAVE + 0x6e0
BONUS_END_CODE = CAVE + 0x700
CUP_TAB = CAVE + 0x720          # 73 rows of 12 bytes: competition, stage, amount
FEE_CODE = CAVE + 0xa90         # (0x480 in version 3)
TALENT_STEP_AT = CAVE + 0xb80   # dword: percent of value per rating point above TALENT_TAB
TALENT_MAX_AT = CAVE + 0xb84    # dword: the most percent
TALENT_CAP_AT = CAVE + 0xb88    # dword: the most the bonus can be, as an amount
INCOME_AT = CAVE + 0xb8c        # dword: percent of the game's two yearly incomes
LEAGUE_IDS_AT = CAVE + 0xb90    # 12 words: leagues with a prize list of their own
LEAGUE_COUNT_AT = CAVE + 0xba8  # dword: how many of them are used
INCOME_WAGES_AT = CAVE + 0xbac  # dword: percent of the wage bill that is added to the yearly income
LEAGUE_ROWS_TAB = CAVE + 0xbb0  # 12 rows of 24 words: prize by place in units of LEAGUE_UNIT, index 0 unused
LEAGUE_ROWS, LEAGUE_ROW_WORDS, LEAGUE_UNIT = 12, 24, 100
CAVE_SIZE = 0xdf0
CAVE_LIMIT = 0x047b1000
# a second piece, the unused rest of the page of the section .data1 (it follows .xcode in
# memory): the tables and the routine of MLTransfers.lua (only written when a part of it is on)
CAVE_2 = 0x047d4200
CAVE_2_SIZE = 0xe00              # to the end of the page
CAVE_2_LIMIT = 0x047d5000
CEILING_TAB = CAVE_2            # 10 dwords, by club level 0-9: the value a club of that level takes for sure
CEILING_TOP = CAVE_2 + 0x28     # 10 bytes, by club level: the highest rating it takes in the second, wide search
STRETCH_AT = CAVE_2 + 0x34      # dword: percent above the ceiling at which the chance to take a player reaches none
NEED_AT = CAVE_2 + 0x38         # dword: the percent by which need raises the ceiling
FREE_AT = CAVE_2 + 0x3c         # dword: percent of his value that counts for a player signed without a transfer (status 1 or 2)
LISTED_AT = CAVE_2 + 0x40       # dword: the same for a player listed by his club
PERSONA_LOW_AT = CAVE_2 + 0x44  # dword: 1000 - 10 x PERSONA_SPREAD
PERSONA_RANGE_AT = CAVE_2 + 0x48  # dword: 20 x PERSONA_SPREAD
STRENGTH_A_AT = CAVE_2 + 0x4c   # dword: rating points per ranking point, times 65536
STRENGTH_B_AT = CAVE_2 + 0x50   # dword: the rating at 0 ranking points, times 65536, plus 32768
WINTER_AT = CAVE_2 + 0x54       # dword: the month of the planning day whose deals close in the winter window (0: none)
SQUAD_AT = CAVE_2 + 0x58        # dword: a club that counts fewer players than this is in need
SELL_AT = CAVE_2 + 0x5c         # dword: 1 = the selling club's side is asked before a player takes a place
HAND_COUNT_AT = CAVE_2 + 0x60   # dword: how many clubs are named in CLUBS
RANGE_LOW_TAB = CAVE_2 + 0x64   # 10 bytes, by club level: the lowest and (next 10 bytes) the highest rating a
RANGE_TOP_TAB = CAVE_2 + 0x6e   # first eleven is taken to have (the game's rating range of the level)
BY_LEVEL_TAB = CAVE_2 + 0x78    # 10 rows of 8 bytes, by club level: the personas a club without a name draws from
GENES_TAB = CAVE_2 + 0xc8       # 16 personas of 20 bytes (GENE_NAMES, then first age, last age, two channels)
HAND_TYPES = CAVE_2 + 0x208     # 192 bytes: the persona of each named club
HAND_IDS = CAVE_2 + 0x2c8       # 192 dwords: the ids of the named clubs
RIVAL_COUNT_AT = CAVE_2 + 0x5c8  # dword: how many pairs RIVALS has
RIVAL_PAIRS = CAVE_2 + 0x5cc    # 64 pairs of dwords: the ids of two clubs that do not trade
CEILING_CODE = CAVE_2 + 0x7cc
FAME_KNOWN_AT = CAVE_2 + 0xde4  # dword: a player of this popularity or more is known to every club, times 1 << 20
STRICT_FREE_AT = CAVE_2 + 0xde8  # dword: percent of `strict` that counts for a player without a contract
KEEP_FROM_AT = CAVE_2 + 0xdec   # dword: a player this many rating points below his club's eleven, or better, is first team
KEEP_STEP_AT = CAVE_2 + 0xdf0   # dword: percent added to `keeps` of his club for each point he stands above that
KEEP_BIGGER_AT = CAVE_2 + 0xdf4  # dword: not against a buyer whose eleven is this many points better than his club's
KNOWN_AT = CAVE_2 + 0xdf8       # dword: a player of this rating or more is known to every club
AGE_SHIFT_AT = CAVE_2 + 0xdfc   # dword: the ages of a persona are moved by up to this many years, by club
# a third piece, in the unused rest of the page of the section .link (MLSimMatch.lua ends at
# 0x047d6376, MLSimToDate.lua starts at 0x047d6f60): the position need of MLTransfers.lua
# (written only when NEED is on). The page cannot be written while the game runs: it holds
# code and two numbers that never change.
CAVE_3 = 0x047d6400
CAVE_3_SIZE = 0x150
NEED_GAP_AT = CAVE_3            # dword: the weakest of the eleven is in need this many rating points below the mean of the others
NEED_MORE_AT = CAVE_3 + 4       # dword: NEED_BETTER - 1: the search looks above his rating plus this
NEED_PLAN_CODE = CAVE_3 + 0x10
NEED_PICK_CODE = CAVE_3 + 0x120
# a fourth piece, in the same unused page right after the need piece: the chooser of the
# club that makes an offer for one of the user's players (MLTransfers.lua, INCOMING). It
# is entered at fcn_0381e2eb, the look-up that answers which club sits at slot n of the
# competition in hand; the routine of fcn_03652df0 that creates an offer asks it for the
# buying club, so answering another club there redirects the offer with everything the
# game does afterwards (the room test, the salary, the news) staying consistent.
INCOMING_CODE = CAVE_3 + 0x150
INCOMING_CAVE_SIZE = 0x7f0         # what MLTransfers.lua keeps for it (0x7f0 ends where CAVE_5 starts)
INCOMING_SITE = 0x0381e2eb
INCOMING_SITE_OLD = bytes.fromhex('5589e583ec14')
INCOMING_BACK = INCOMING_SITE + len(INCOMING_SITE_OLD)
INCOMING_SITE_NEW = b'\xe9' + struct.pack('<i', INCOMING_CODE - (INCOMING_SITE + 5)) + b'\x90'
MODE_OBJECT_AT = 0x026503e0   # dword: the mode object; its +0x30 is the mode data
CURRENT_CLUB_AT = 0x0251f85c  # dword: the club of the player being handled
INCOMING_KEY = 0x02100a66     # byte: the slot the look-up resolves
CLUB_TABLE, CLUB_TABLE_COUNT, CLUB_STRIDE = 0x481be0, 0x5fece0, 0x520
# a fifth piece, in the same page right after the 0x7f0 bytes kept for the fourth (which
# end at 0x047d6d3f; MLGrowth.lua starts at 0x047d6e50): SQUAD_PRESSURE of MLTransfers.lua
# 9. The second piece is full, and its routine calls this one, so it is written with it.
CAVE_5 = INCOMING_CODE + INCOMING_CAVE_SIZE
CAVE_5_SIZE = 0x110
PRESSURE_DROP_AT = CAVE_5       # dword: `keeps` of a club is this much lower for a player of a group it has too many of (0: off)
PRESSURE_LIMITS = CAVE_5 + 4    # 4 bytes, by group (GROUPS): the most players of the group a club has without that
PRESSURE_GROUPS = CAVE_5 + 8    # 13 bytes, by registered position: its group (GROUP_OF)
PRESSURE_CODE = CAVE_5 + 0x18
NO_CEILING = 0xffffffff         # in CEILING_TAB: this level takes any value
NO_TOP = 0xff                   # in CEILING_TOP: this level takes any rating
LEVELS = 10
PERSONAS, PERSONA_BYTES, BY_LEVEL, HAND, RIVALS = 16, 20, 8, 192, 64
# the numbers of a persona that are changed a little from club to club (bytes 0 to 13 of its 20)
GENE_NAMES = ('free', 'listed', 'clubs', 'winter', 'knows', 'fog', 'wealth', 'premium', 'panic', 'fame', 'ambition',
              'prestige', 'keeps', 'strict')
GENES = len(GENE_NAMES)
AGE_FROM, AGE_TO, THEN_1, THEN_2 = 14, 15, 16, 17      # the bytes after them
CHANNELS = ('free', 'listed', 'clubs')                 # where a player is: 0 no contract, 1 listed by his club, 2 any other
NO_CHANNELS = 0xff              # in THEN_1: this persona takes players from anywhere
KEEP_TOP_AT = 18                # byte 18 of a persona: 1 = the rating limit of the wide search
                                # (CEILING_TOP) applies to it, 0 = it does not (NEUTRAL has 1)
# persona 0: a club that behaves as in version 1 (what every club is with PERSONA = false)
NEUTRAL = bytes([100, 0, 0, 100, 255, 0, 100, 100, 100, 0, 255, 255, 0, 0, 0, 63, NO_CHANNELS, NO_CHANNELS, 1, 0])
# the highest overall of the rating range of a club, by level 0 to 9 (fcn_0365d08d)
WINDOW_TOP = (74, 75, 76, 77, 78, 79, 80, 83, 86, 99)
# the club ranking places of each level, 9 down to 0 (fcn_036720d7 and fcn_03672359; the last has no end)
LEVEL_PLACES = ((1, 10), (11, 20), (21, 50), (51, 80), (81, 120), (121, 170), (171, 220), (221, 260), (261, 300),
                (301, None))

# Sporting Projects (independent rebuilds of top AI clubs, preserving personas)
PROJECT_COUNT = 5
PROJECT_CEILING_BOOST = 20
PROJECT_RANK_MAX = 15
TOP_FIVE_LEAGUES = { 17, 18, 19, 20, 50 }

FEE_SITE = 0x038ab8db
FEE_SITE_OLD = bytes.fromhex('83f844760c8db8bcffffff69ff28230000')
SALARY_SITE = 0x038ac875
SALARY_SITE_OLD = bytes.fromhex('89c1c1e10429c1')
SALARY_BLOCK_END = 0x038ac8d7
BUDGET_T_SITE = 0x038adc47
BUDGET_T_SITE_OLD = bytes.fromhex('01f68b4030')
BUDGET_S_SITE = 0x038add08
BUDGET_S_SITE_OLD = bytes.fromhex('8d3441e8d5e3f6ff')
MODE_OBJECT_GETTER = 0x0381c0e5
MENU_GETTER = 0x03808865          # -> object whose +0x20 is the game mode number
MASTER_LEAGUE = 0x13
BALANCE_ADD = 0x038aadb7
TRANSFER_BUDGET_ADD = 0x038aac87
CUP_TABLE, CUP_ROWS = 0x0216b178, 73    # the game's own table
LEAGUE1_SITE, LEAGUE1_SITE_OLD = 0x038aa2dd, bytes.fromhex('8b848584feffff')
LEAGUE2_SITE, LEAGUE2_SITE_OLD = 0x038aa2c6, bytes.fromhex('8b8485e0feffff')
LEAGUE1_PLACES, LEAGUE2_PLACES = 22, 24
PRIZE_SITE_1, PRIZE_SITE_1_OLD = 0x03640ac5, bytes.fromhex('e8eda22600')
PRIZE_SITE_2, PRIZE_SITE_2_OLD = 0x03640b78, bytes.fromhex('e83aa22600')
RANK_SITE, RANK_SITE_OLD = 0x038aca1b, bytes.fromhex('88fef201')
RANK_STEP_OLD = 0.004000000189989805
BONUS_R_SITE, BONUS_R_SITE_OLD = 0x038aca2b, bytes.fromhex('03b5b0ffffff')
BONUS_END_SITE, BONUS_END_SITE_OLD = 0x038acd96, bytes.fromhex('8b85ccffffff0385b0ffffff')
YEARS_SITE, YEARS_SITE_OLD = 0x03887fc1, bytes.fromhex('b803000000')
# yearly income: season_income (fcn_038ade76), the amount by rank (fcn_038a9e6b), and the
# same amount by club level when a career is set up (fcn_038adf0c)
INCOME_N_SITE, INCOME_N_SITE_OLD = 0x038adeee, bytes.fromhex('8d863e56cbff')   # lea eax, [esi - 0x34a9c2]
INCOME_M_SITE, INCOME_M_SITE_OLD = 0x038a9e9c, bytes.fromhex('69c088130000')   # imul eax, eax, 5000
INCOME_S_SITE, INCOME_S_SITE_OLD = 0x038ae025, bytes.fromhex('81c6983a0000')   # add esi, 15000
# season_income calls the wage bill function and throws the result away; right after that call:
# mov eax, [ebp + 8]; push eax; call club_popularity
INCOME_W_SITE, INCOME_W_SITE_OLD = 0x038adeaa, bytes.fromhex('8b450850e8a2a9fcff')
CLUB_POPULARITY = 0x03878855
# ai_candidates (fcn_0365f5c2): a player who passed every test is put on the list of candidates:
# mov ecx, [ebp + 0x24]; push esi; call take
CEILING_SITE, CEILING_SITE_OLD = 0x0365fb0d, bytes.fromhex('8b4d2456e8aa98ac00')
AI_CANDIDATES, AI_PICK, AI_MAX_OVERALL = 0x0365f5c2, 0x03660c52, 0x0365d08d
AI_MIN_OVERALL = 0x0365d12d
# the lowest overall of the rating range of a club, by level 0 to 9 (fcn_0365d12d)
WINDOW_LOW = (47, 51, 55, 59, 63, 67, 70, 73, 76, 83)
PLAYER_CLUB = 0x0382b087                        # thiscall (player record; -> club id, -> index 0): the club he plays for
PLAYER_BAND = 0x0385400e                        # (player record) -> his status band 0 to 7
NO_CLUB = 0xffffffff                            # that id, in the game's file
NO_CLUB_AT = 0x024feb34                         # dword: the club id that stands for "no club"
RANK_TABLE, RANK_COUNT, RANK_MOST = 0xcc84cc, 0x28a0, 650    # mode data: the club ranking, records of 16 bytes
# (club id, place, word +8 ranking points, byte +0xe level); the count is a dword at this offset from its start
POOL_COUNTS = 0x7ac                             # the pool object: dwords by the low 14 bits of a club id, its counted players
POOL_CLUBS = 0x28d                              # the pool object counts the players of this many clubs
POOL_KEEPS = 23                                 # a club lets a player go only while it counts more than this
AI_NEXT_PLAYER = 0x0365fb28                     # where ai_candidates goes on when a player fails a test
AI_TAKEN = 0x0365fb16                           # the instruction after the replaced ones
AI_PICK_RETURNS = (0x03660d58, 0x03660db9)      # where ai_candidates returns to: its two calls in ai_pick_candidate
STAR_BAND_SITE, STAR_BAND_SITE_OLD = 0x0365f8ec, bytes.fromhex('83ff06')
STAR_BAND_SITE_NEW = bytes.fromhex('83ff08')
STAR_PICK_BAND_SITE, STAR_PICK_BAND_SITE_OLD = 0x0366106b, bytes.fromhex('83f807')
STAR_PICK_BAND_SITE_NEW = bytes.fromhex('83f808')
STAR_PICK_LEVEL_SITE, STAR_PICK_LEVEL_SITE_OLD = 0x03661094, bytes.fromhex('83f808')
STAR_PICK_LEVEL_SITE_NEW = bytes.fromhex('83f80a')
TRIM_PLAN_SITE, TRIM_PLAN_SITE_OLD = 0x03660b85, bytes.fromhex('83f919')
TRIM_PLAN_SITE_NEW = bytes.fromhex('83f91e')
TRIM_FILL_SITE, TRIM_FILL_SITE_OLD = 0x038895f6, bytes.fromhex('83f820')
TRIM_FILL_SITE_NEW = bytes.fromhex('83f821')
TRIM_CLOSE_SITE, TRIM_CLOSE_SITE_OLD = 0x0365d3f4, bytes.fromhex('833a20')
TRIM_CLOSE_SITE_NEW = bytes.fromhex('833a21')
TRIM_EVICT_SITE, TRIM_EVICT_SITE_OLD = 0x03892145, bytes.fromhex('83f80d0f8523020000')
TRIM_EVICT_SITE_NEW = bytes.fromhex('83f80c0f8223020000')
TRIM_SITES = (
    ('trim plan', TRIM_PLAN_SITE, TRIM_PLAN_SITE_OLD, TRIM_PLAN_SITE_NEW),
    ('trim fill', TRIM_FILL_SITE, TRIM_FILL_SITE_OLD, TRIM_FILL_SITE_NEW),
    ('trim close', TRIM_CLOSE_SITE, TRIM_CLOSE_SITE_OLD, TRIM_CLOSE_SITE_NEW),
    ('trim evict', TRIM_EVICT_SITE, TRIM_EVICT_SITE_OLD, TRIM_EVICT_SITE_NEW),
)
TAKE = 0x041293c0                               # adds an id pair to a list (thiscall, one argument)
RATING = 0x03853b42                             # (player record, -> position or 13, kind) -> rating in al
FIND_PLAYER = 0x03822835                        # (player id low, id high), ecx = mode data -> the player record
# club_squad_plan (fcn_036602e5), the end of its work on one club: mov eax, [ebp - 0x48]
SQUAD_PLAN = 0x036602e5
NEED_PLAN_SITE, NEED_PLAN_SITE_OLD = 0x03660b93, bytes.fromhex('8b85b8ffffff')
# ai_pick_candidate, the lowest overall its caller hands in: mov eax, [ebp + 0x18]; mov edx, [eax]
NEED_PICK_SITE, NEED_PICK_SITE_OLD = 0x03660c83, bytes.fromhex('8b45188b10')
AI_FILL_SLOTS = 0x03661b15                      # the only caller of ai_pick_candidate
LINEUP_RATINGS = 0x03894bcf                     # squad_needs: the loop that puts player and rating into each entry
PLAN_RECORDS, PLAN_SIZE, PLAN_SLOTS = 0xccb80c, 0x118, 16    # mode data: one record per computer club; slots from +8
PLAN_COUNT = 0xd06434                            # mode data: how many plan records there are (up to 851)
NO_POSITION = 13                                # in a slot: it looks for nobody
# two bytes of a plan record that the game leaves alone (they follow the byte +0x108 and are 0 in
# every record of every save looked at): the position of the need slot + 1 (0: the club has none)
# and the rating its search starts above
PLAN_NEED_AT = 0x109
# what ai_candidates itself walks a squad with (0x0365f95a, its count of the goalkeepers of the selling club):
# the record of a club (thiscall on the mode data, club id), the record of a player (the same, id pair),
# "are two id pairs the same" (thiscall on one pair, -> the other)
TEAM_RECORD, PLAYER_RECORD, SAME_ID = 0x03822969, 0x03822835, 0x02bddabe
TEAM_SQUAD, TEAM_COUNT = 0xf8, 0x328            # a club record: the id pairs of its players; their number in bits 9-15
NO_PLAYER_AT = 0x024feb04                       # two dwords: the id pair that stands for "no player"
ELEVEN = 11                                     # the first entries of the lineup list
# cup_prize: the amounts for a cup that has no row in the table, by stage (immediates of six mov edi)
NATIONAL_SITES = ((0x038aa43a, 20000), (0x038aa446, 10000), (0x038aa452, 5000), (0x038aa45e, 1000),
                  (0x038aa46a, 500), (0x038aa476, 300))
NATIONAL_STAGES = ((0,), (1,), (2, 3), (4,), (5,), (6,))        # the stages each of the six serves
# the game's cup table: (competition, stage, amount)
GAME_CUP_ROWS = struct.iter_unpack('<3I', bytes.fromhex(
    '0200000000000000803801000200000001000000409c00000200000003000000307500000200000004000000204e0000'
    '0200000007000000102700000200000009000000881300000300000000000000307500000300000001000000204e0000'
    '0300000003000000983a00000300000004000000102700000300000005000000881300000300000007000000b80b0000'
    '0300000009000000e80300000400000000000000b8880000040000000100000010270000050000000000000080380100'
    '0500000001000000409c00000500000003000000307500000500000004000000204e0000050000000700000010270000'
    '0500000009000000881300003000000000000000803801003000000001000000409c0000300000000300000030750000'
    '3000000004000000204e0000300000000700000010270000300000000900000088130000060000000000000030750000'
    '0600000001000000204e00000600000003000000983a0000060000000400000010270000060000000700000088130000'
    '0600000009000000b80b0000060000000a000000e80300005b00000000000000307500005b00000001000000204e0000'
    '5b00000003000000983a00005b00000004000000102700005b00000007000000881300005b00000009000000b80b0000'
    '5b0000000a000000e80300000700000000000000b8880000070000000100000010270000080000000000000080380100'
    '0800000001000000409c00000800000003000000307500000800000004000000204e0000080000000700000010270000'
    '0800000009000000881300000100000000000000409c00000100000001000000204e0000010000000200000010270000'
    '0100000003000000881300004900000000000000881300004900000001000000b80b00004a0000000000000088130000'
    '4a00000001000000b80b00004b00000000000000881300004b00000001000000b80b00004c0000000000000088130000'
    '4c00000001000000b80b00004d00000000000000881300004d00000001000000b80b00004e0000000000000088130000'
    '4e00000001000000b80b00004f00000000000000881300004f00000001000000b80b0000520000000000000088130000'
    '5200000001000000b80b00005300000000000000881300005300000001000000b80b0000540000000000000088130000'
    '5400000001000000b80b0000'))
GAME_CUP_ROWS = tuple(GAME_CUP_ROWS)
assert len(GAME_CUP_ROWS) == CUP_ROWS
# what cup_prize gives for a cup without a row, by stage (switch at 0x038aa42b)
CUP_FALLBACK = {0: 20000, 1: 10000, 2: 5000, 3: 5000, 4: 1000, 5: 500, 6: 300}
CUP_NONE = (0x2d, 0x2e, 0x2f, 0x36, 0x37, 0x46, 0x47, 0x48)
# league_prize's four lists, index 0 to the last place
GAME_LEAGUE = {
    'first': (0, 150000, 130000, 100000, 80000, 60000, 50000, 45000, 40000, 35000, 30000, 27000, 24000, 21000,
              18000, 15000, 12000, 9000, 7000, 5000, 3000, 3000, 3000),
    'second': (0, 20000, 15000, 12000, 10000, 9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000, 1500, 1000, 900,
               800, 700, 600, 500, 450, 400, 350, 300, 250),
    60: (0, 20000, 10000, 8000, 6000, 4000, 2000, 1000) + (0,) * 15,
    61: (0, 2000, 1000, 500) + (0,) * 19,
}

POSITIONS = ('GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF')
# SQUAD_PRESSURE: the four groups of positions and the group of each position
GROUPS = ('GK', 'DF', 'MF', 'FW')
GROUP_OF = (0, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3)
HASH_A, HASH_B = 0x01000193, 0x9e3779b1
HASH_C = 0x85ebca6b             # the last step of the hash of the ceiling (player and buying club)
# the last steps of the other draws of MLTransfers.lua, and the factor of the position asked for
HASH_POSITION, HASH_KEEPS, HASH_KNOWS, HASH_WINTER, HASH_AGE, HASH_FOG = (
    0xc2b2ae35, 0x27d4eb2f, 0x165667b1, 0xcc9e2d51, 0x1b873593, 0xe6546b65)
HASH_SHIFT = 0x2545f491         # the last step of the draw that moves the ages of a club

FEE_SOURCE = f'''
    cmp eax, 99
    jbe f1
    mov eax, 99
f1: mov edi, eax
    mov eax, dword ptr [eax*4 + {VALUE_TAB}]
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    movzx edx, byte ptr [ecx + {TALENT_TAB}]
    sub edi, edx
    jg t1
    xor edi, edi
t1: imul edi, dword ptr [{TALENT_STEP_AT}]
    cmp edi, dword ptr [{TALENT_MAX_AT}]
    jbe t2
    mov edi, dword ptr [{TALENT_MAX_AT}]
t2: movzx ecx, word ptr [ecx*2 + {AGE_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    push eax
    mul edi
    div dword ptr [{HUNDRED_AT}]
    cmp eax, dword ptr [{TALENT_CAP_AT}]
    jbe t3
    mov eax, dword ptr [{TALENT_CAP_AT}]
t3: pop ecx
    add eax, ecx
    mov ecx, dword ptr [ebx + 4]
    shr ecx, 28
    movzx ecx, word ptr [ecx*2 + {POSITION_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    movzx ecx, word ptr [ebx + 0x2c]
    imul edx, dword ptr [ebx + 0x30], {HASH_A}
    xor ecx, edx
    imul ecx, ecx, {HASH_B}
    shr ecx, 24
    imul ecx, dword ptr [{SPREAD_RANGE_AT}]
    shr ecx, 8
    add ecx, dword ptr [{SPREAD_LOW_AT}]
    mul ecx
    div dword ptr [{THOUSAND_AT}]
    cmp eax, {CAP}
    jbe f2
    mov eax, {CAP}
f2: mov edi, eax
    mov ecx, dword ptr [ebx + 0xb4]
    shr ecx, 11
    and ecx, 0xfff
    imul ecx, dword ptr [{FAME_AT}]
    mul ecx
    mov ecx, 100000
    div ecx
    add edi, eax
    mov dword ptr [ebp - 0xc], 0
    ret
'''
SALARY_SOURCE = f'''
    cmp eax, 99
    jbe s1
    mov eax, 99
s1: mov eax, dword ptr [eax*4 + {SALARY_TAB}]
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    movzx ecx, word ptr [ecx*2 + {SALARY_AGE_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    mov dword ptr [ebp - 0x38], eax
    mov dword ptr [ebp - 0x34], 0
    ret
'''
BUDGET_T_SOURCE = f'''
    mov eax, dword ptr [eax + 0x30]
    push eax
    push edx
    mov eax, esi
    mul dword ptr [{BUDGET_T_AT}]
    div dword ptr [{HUNDRED_AT}]
    mov esi, eax
    pop edx
    pop eax
    test esi, esi
    ret
'''
BUDGET_S_SOURCE = f'''
    push edx
    mul dword ptr [{BUDGET_S_AT}]
    div dword ptr [{HUNDRED_AT}]
    pop edx
    lea esi, [ecx + eax]
    jmp {MODE_OBJECT_GETTER}
'''
PRIZE_SOURCE = f'''
    mov eax, dword ptr [esp + 4]
    push eax
    call {BALANCE_ADD}
    add esp, 4
    call {MENU_GETTER}
    cmp dword ptr [eax + 0x20], {MASTER_LEAGUE}
    jne p1
    mov eax, dword ptr [esp + 4]
    mov eax, dword ptr [eax]
    imul dword ptr [{SHARE_AT}]
    idiv dword ptr [{HUNDRED_AT}]
    push eax
    push esp
    call {TRANSFER_BUDGET_ADD}
    add esp, 8
p1: ret
'''
BONUS_R_SOURCE = f'''
    push eax
    push edx
    mov eax, esi
    mul dword ptr [{BONUS_AT}]
    div dword ptr [{HUNDRED_AT}]
    mov esi, eax
    pop edx
    pop eax
    add esi, dword ptr [ebp - 0x50]
    ret
'''
BONUS_END_SOURCE = f'''
    push edx
    mov eax, dword ptr [ebp - 0x34]
    add eax, dword ptr [ebp - 0x50]
    mul dword ptr [{BONUS_AT}]
    div dword ptr [{HUNDRED_AT}]
    pop edx
    ret
'''
INCOME_N_SOURCE = f'''
    lea eax, [esi - 0x34a9c2]
    call {INCOME_SCALE_CODE}
    mov ecx, eax
    mov eax, dword ptr [ebp - 4]
    mul dword ptr [{INCOME_WAGES_AT}]
    div dword ptr [{HUNDRED_AT}]
    add eax, ecx
    ret
'''
# [ebp - 4] of season_income holds a flag byte for the wage bill function, which nothing
# reads after that call. The routine keeps the wage bill there and goes on to
# club_popularity with the argument the replaced instructions pushed. With the percent at
# INCOME_WAGES_AT 0 this routine is not used and whatever [ebp - 4] holds is multiplied by 0.
WAGES_KEEP_SOURCE = f'''
    mov dword ptr [ebp - 4], eax
    pop eax
    push dword ptr [ebp + 8]
    push eax
    jmp {CLUB_POPULARITY}
'''
INCOME_M_SOURCE = f'''
    imul eax, eax, 0x1388
    jmp {INCOME_SCALE_CODE}
'''
INCOME_SCALE_SOURCE = f'''
    test eax, eax
    jle i1
    push edx
    mul dword ptr [{INCOME_AT}]
    div dword ptr [{HUNDRED_AT}]
    pop edx
i1: ret
'''
INCOME_S_SOURCE = f'''
    add esi, 0x3a98
    push eax
    mov eax, esi
    call {INCOME_SCALE_CODE}
    mov esi, eax
    pop eax
    ret
'''
LEAGUE_SOURCE = f'''
    xor ecx, ecx
    jmp l3
l1: movzx edx, word ptr [ecx*2 + {LEAGUE_IDS_AT}]
    cmp edx, edi
    je l2
    inc ecx
l3: cmp ecx, dword ptr [{LEAGUE_COUNT_AT}]
    jb l1
    mov eax, dword ptr [eax*4 + {LEAGUE1_TAB}]
    ret
l2: imul ecx, ecx, {LEAGUE_ROW_WORDS}
    add ecx, eax
    movzx eax, word ptr [ecx*2 + {LEAGUE_ROWS_TAB}]
    imul eax, eax, {LEAGUE_UNIT}
    ret
'''
# The routine of MLTransfers.lua. Entered by a call from ai_candidates (ebp = its frame) in
# the place of `mov ecx, [ebp + 0x24]; push esi; call take`: the player has passed every test
# of the game and is about to be put on the list of (at most three) candidates. From the
# frame of ai_candidates: [ebp - 0x28] the player record, [ebp - 0x24] today (word year, byte
# month, byte day), [ebp - 0xc] the pool object, [ebp - 8] the mode data, [ebp + 0x14] ->
# the position asked for, [ebp + 0x18] the plan record of the buying club (club id, kind),
# [ebp + 0x30] -> the status band the slot asks for. The club level is not handed to
# ai_candidates; it is an argument of its only caller, ai_pick_candidate ([its ebp + 0x1c]
# -> level), whose frame is the saved ebp; the byte [its ebp + 0x1b] is 1 in the second,
# wide search. If ai_candidates was not called from one of the two known places, or the
# level is not 0 to 9, the player is taken as in the game. Otherwise the steps of
# accepts() below, in its order. Refused: the return address is dropped and the game's
# "next player" follows.
# Locals: [ebp - 4] limit, [ebp - 8] a number handed to the game by address, [ebp - 0xc]
# scratch of FEE_CODE, [ebp - 0x10] wide search, [ebp - 0x14] persona of the buying club,
# [ebp - 0x18] buying club, [ebp - 0x1c] need, [ebp - 0x20] level, [ebp - 0x24] rating (as
# the club sees it, once the fog is on it), [ebp - 0x28] key of the player, [ebp - 0x2c]
# key of player and buying club, [ebp - 0x30] where the player is (CHANNELS), [ebp - 0x34]
# the eleven of the buying club, [ebp - 0x38] frame of ai_candidates, [ebp - 0x3c] his
# club, [ebp - 0x40] the return address of ai_candidates, [ebp - 0x44] kind of the plan,
# [ebp - 0x48] band asked for, [ebp - 0x4c] key of club, date and position, [ebp - 0x50]
# ranking record of the buying club, [ebp - 0x54] date part of the keys, [ebp - 0x58] the
# eleven of the selling club, [ebp - 0x90] to
# [ebp - 0x5c] the 14 numbers of the buying club's persona (GENE_NAMES).
def G(name):
    return 'dword ptr [ebp - 0x%x]' % (0x90 - 4 * GENE_NAMES.index(name))


def PERCENT(register):
    """the high byte of the register -> 0 to 99"""
    return f'''shr {register}, 24
    imul {register}, {register}, 100
    shr {register}, 8'''


CEILING_SOURCE = f'''
    push ebx
    push edi
    push ebp
    mov ebp, esp
    sub esp, 0x90
    mov eax, dword ptr [ebp]
    mov dword ptr [ebp - 0x38], eax
    mov ebx, dword ptr [eax - 0x28]
    mov ecx, dword ptr [eax + 4]
    cmp ecx, {AI_PICK_RETURNS[0]}
    je c1
    cmp ecx, {AI_PICK_RETURNS[1]}
    jne take
c1: mov dword ptr [ebp - 0x40], ecx
    mov ecx, dword ptr [eax - 0x24]
    mov dword ptr [ebp - 0x54], ecx
    mov ecx, dword ptr [eax + 0x18]
    mov edx, dword ptr [ecx + 4]
    mov dword ptr [ebp - 0x44], edx
    mov ecx, dword ptr [ecx]
    mov dword ptr [ebp - 0x18], ecx
    mov edx, dword ptr [eax + 0x30]
    mov edx, dword ptr [edx]
    mov dword ptr [ebp - 0x48], edx
    mov edx, dword ptr [eax + 0x14]
    imul edx, dword ptr [edx], {HASH_POSITION}
    mov dword ptr [ebp - 0x4c], edx
    mov eax, dword ptr [eax]
    movzx ecx, byte ptr [eax + 0x1b]
    mov dword ptr [ebp - 0x10], ecx
    mov eax, dword ptr [eax + 0x1c]
    mov eax, dword ptr [eax]
    cmp eax, {LEVELS - 1}
    ja take
    mov dword ptr [ebp - 0x20], eax
    xor ecx, ecx
    mov edx, dword ptr [ebx + 0xb4]
    and edx, 0xf
    dec edx
    cmp edx, 1
    jbe c2
    inc ecx
    test dword ptr [ebx + 0xb8], 0x60000000
    jnz c2
    inc ecx
c2: mov dword ptr [ebp - 0x30], ecx
    movzx ecx, word ptr [ebx + 0x2c]
    imul edx, dword ptr [ebx + 0x30], {HASH_A}
    xor ecx, edx
    mov dword ptr [ebp - 0x28], ecx
    imul edx, dword ptr [ebp - 0x18], {HASH_B}
    xor ecx, edx
    mov dword ptr [ebp - 0x2c], ecx
    xor dword ptr [ebp - 0x4c], edx
    mov ecx, dword ptr [ebp - 0x54]
    and ecx, 0xffffff
    imul ecx, ecx, {HASH_A}
    xor dword ptr [ebp - 0x4c], ecx
    mov dword ptr [ebp - 0x54], ecx
    mov eax, dword ptr [ebp - 0x18]
    call persona
    mov dword ptr [ebp - 0x14], eax
    mov dword ptr [ebp - 0x50], edx
    xor ecx, ecx
c3: push ecx
    mov eax, dword ptr [ebp - 0x14]
    mov edx, dword ptr [ebp - 0x18]
    call gene
    pop ecx
    mov dword ptr [ebp + ecx*4 - 0x90], eax
    inc ecx
    cmp ecx, {GENES}
    jb c3
    mov dword ptr [ebp - 8], 0xd
    push 2
    lea eax, [ebp - 8]
    push eax
    push ebx
    call {RATING}
    add esp, 12
    movzx eax, al
    mov dword ptr [ebp - 0x24], eax
    mov edx, dword ptr [ebp - 0x50]
    call eleven
    mov dword ptr [ebp - 0x34], eax
    cmp dword ptr [ebp - 0x30], 0
    je s9
    and dword ptr [ebp - 8], 0
    lea eax, [ebp - 8]
    push eax
    lea eax, [ebp - 0x3c]
    push eax
    mov ecx, ebx
    call {PLAYER_CLUB}
    mov eax, dword ptr [ebp - 0x3c]
    cmp eax, dword ptr [{NO_CLUB_AT}]
    je s9
    mov edx, dword ptr [ebp - 0x18]
    mov ecx, dword ptr [{RIVAL_COUNT_AT}]
v1: dec ecx
    js v3
    cmp dword ptr [ecx*8 + {RIVAL_PAIRS}], eax
    jne v2
    cmp dword ptr [ecx*8 + {RIVAL_PAIRS + 4}], edx
    je refuse
v2: cmp dword ptr [ecx*8 + {RIVAL_PAIRS}], edx
    jne v1
    cmp dword ptr [ecx*8 + {RIVAL_PAIRS + 4}], eax
    je refuse
    jmp v1
v3: cmp dword ptr [ebp - 0x30], 2
    jne s9
    call persona
    push eax
    push edx
    call eleven
    mov dword ptr [ebp - 0x58], eax
    pop edx
    cmp dword ptr [{SELL_AT}], 0
    je s5
    mov ecx, dword ptr [ebp - 0x38]
    mov ecx, dword ptr [ecx - 0xc]
    mov eax, dword ptr [ebp - 0x3c]
    and eax, 0x3fff
    cmp eax, {POOL_CLUBS}
    jae s8
    cmp dword ptr [ecx + eax*4 + {POOL_COUNTS}], {POOL_KEEPS}
    jbe s8
    cmp dword ptr [ebp - 0x40], {AI_PICK_RETURNS[1]}
    jne s5
    push edx
    push ebx
    call {PLAYER_BAND}
    add esp, 4
    pop edx
    mov ecx, dword ptr [ebp - 0x20]
    cmp ecx, 8
    jae s5
    cmp dword ptr [ebp - 0x44], 4
    jne s3
    cmp ecx, eax
    ja s5
s3: cmp eax, 7
    jae s8
    cmp byte ptr [edx + 0xe], 8
    jae s8
s5: pop eax
    push {GENE_NAMES.index('keeps')}
    pop ecx
    mov edx, dword ptr [ebp - 0x3c]
    call gene
    mov edx, dword ptr [ebp - 0x34]
    sub edx, dword ptr [ebp - 0x58]
    cmp edx, dword ptr [{KEEP_BIGGER_AT}]
    jge s6
    mov edx, dword ptr [ebp - 0x24]
    add edx, dword ptr [{KEEP_FROM_AT}]
    sub edx, dword ptr [ebp - 0x58]
    jle s6
    imul edx, dword ptr [{KEEP_STEP_AT}]
    add eax, edx
s6: imul ecx, dword ptr [ebp - 0x3c], {HASH_B}
    xor ecx, dword ptr [ebp - 0x28]
    xor ecx, dword ptr [ebp - 0x54]
    imul ecx, ecx, {HASH_KEEPS}
    {PERCENT('ecx')}
    call {PRESSURE_CODE}
    jb refuse
    jmp s9
s8: pop eax
    jmp refuse
s9: cmp dword ptr [ebp - 0x30], 1
    je k9
    mov eax, dword ptr [ebp - 0x24]
    cmp eax, dword ptr [{KNOWN_AT}]
    jae k9
    mov eax, dword ptr [ebx + 0xb4]
    shl eax, 9
    cmp eax, dword ptr [{FAME_KNOWN_AT}]
    jae k9
    imul ecx, dword ptr [ebp - 0x2c], {HASH_KNOWS}
    {PERCENT('ecx')}
    cmp ecx, {G('knows')}
    jae refuse
k9: mov eax, dword ptr [ebp - 0x34]
    add eax, {G('prestige')}
    cmp dword ptr [ebp - 0x24], eax
    ja refuse
    mov edx, dword ptr [ebp - 0x48]
    mov ecx, dword ptr [ebp - 0x38]
    mov ecx, dword ptr [ecx - 0xc]
    mov eax, dword ptr [ebp - 0x18]
    and eax, 0x3fff
    cmp eax, {POOL_CLUBS}
    jae n1
    mov eax, dword ptr [ecx + eax*4 + {POOL_COUNTS}]
    cmp eax, dword ptr [{SQUAD_AT}]
    jae n1
    or edx, 1
n1: mov dword ptr [ebp - 0x1c], edx
    cmp dword ptr [ebp - 0x48], 0
    jnz f1
    mov edx, dword ptr [ebp - 0x14]
    cmp byte ptr [edx + {THEN_1}], {NO_CHANNELS}
    je a0
    imul ecx, dword ptr [ebp - 0x4c], {HASH_C}
    {PERCENT('ecx')}
    xor eax, eax
    mov edx, {G('free')}
    cmp ecx, edx
    jb w1
    inc eax
    add edx, {G('listed')}
    cmp ecx, edx
    jb w1
    inc eax
    add edx, {G('clubs')}
    cmp ecx, edx
    jb w1
    cmp dword ptr [ebp - 0x1c], 0
    je refuse
    mov edx, dword ptr [ebp - 0x14]
    movzx eax, byte ptr [edx + {THEN_1}]
w1: cmp dword ptr [ebp - 0x1c], 0
    jnz w2
    mov ecx, dword ptr [ebp - 0x38]
    movzx ecx, byte ptr [ecx - 0x22]
    cmp ecx, dword ptr [{WINTER_AT}]
    jne w2
    imul ecx, dword ptr [ebp - 0x4c], {HASH_WINTER}
    {PERCENT('ecx')}
    cmp ecx, {G('winter')}
    jae refuse
w2: cmp dword ptr [ebp - 0x10], 0
    je w4
    mov edx, dword ptr [ebp - 0x14]
    movzx ecx, byte ptr [edx + {THEN_1}]
    cmp ecx, eax
    jne w3
    movzx ecx, byte ptr [edx + {THEN_2}]
w3: mov eax, ecx
w4: cmp eax, dword ptr [ebp - 0x30]
    jne refuse
a0: cmp dword ptr [ebp - 0x1c], 0
    jnz f1
    imul eax, dword ptr [ebp - 0x18], {HASH_B}
    imul eax, eax, {HASH_SHIFT}
    shr eax, 24
    mov edx, dword ptr [{AGE_SHIFT_AT}]
    lea ecx, [edx + edx + 1]
    imul eax, ecx
    shr eax, 8
    sub eax, edx
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    sub ecx, eax
    mov edx, dword ptr [ebp - 0x14]
    cmp cl, byte ptr [edx + {AGE_FROM}]
    jl a1
    cmp cl, byte ptr [edx + {AGE_TO}]
    jle f1
a1: imul ecx, dword ptr [ebp - 0x2c], {HASH_AGE}
    {PERCENT('ecx')}
    mov eax, {G('strict')}
    cmp dword ptr [ebp - 0x30], 0
    jne a2
    imul eax, dword ptr [{STRICT_FREE_AT}]
    imul ecx, ecx, 100
a2: cmp ecx, eax
    jb refuse
f1: mov eax, {G('fog')}
    lea ecx, [eax*2 + 1]
    imul edx, dword ptr [ebp - 0x2c], {HASH_FOG}
    shr edx, 24
    imul ecx, edx
    shr ecx, 8
    sub ecx, eax
    add dword ptr [ebp - 0x24], ecx
    cmp dword ptr [ebp - 0x1c], 0
    jnz p0
    mov eax, dword ptr [ebp - 0x34]
    sub eax, {G('ambition')}
    cmp dword ptr [ebp - 0x24], eax
    jl refuse
p0: mov edx, dword ptr [ebp - 0x10]
    mov ecx, dword ptr [ebp - 0x14]
    and dl, byte ptr [ecx + {KEEP_TOP_AT}]
    mov ecx, dword ptr [ebp - 0x20]
    jz p1
    mov eax, dword ptr [ebp - 0x24]
    movzx edx, byte ptr [ecx + {CEILING_TOP}]
    cmp eax, edx
    jg refuse
p1: mov eax, dword ptr [ecx*4 + {CEILING_TAB}]
    cmp eax, -1
    je take
    push 100
    pop edi
    mov ecx, {G('wealth')}
    call muldiv
    mov dword ptr [ebp - 4], eax
    mov eax, dword ptr [ebp - 0x1c]
    or eax, dword ptr [ebp - 0x10]
    jz p2
    mov eax, dword ptr [{NEED_AT}]
    mov ecx, {G('panic')}
    call muldiv
    lea ecx, [eax + edi]
    mov eax, dword ptr [ebp - 4]
    call muldiv
    mov dword ptr [ebp - 4], eax
p2: mov eax, dword ptr [{STRETCH_AT}]
    mov ecx, {G('premium')}
    call muldiv
    imul ecx, dword ptr [ebp - 0x2c], {HASH_C}
    shr ecx, 24
    imul ecx, eax
    mov eax, dword ptr [ebp - 4]
    mov edi, 25600
    call muldiv
    call more
    mov ecx, dword ptr [ebx + 0xb4]
    shr ecx, 11
    and ecx, 0xfff
    imul ecx, {G('fame')}
    mov eax, dword ptr [ebp - 4]
    mov edi, 100000
    call muldiv
    call more
    mov eax, dword ptr [ebp - 0x24]
    call {FEE_CODE}
    mov ecx, dword ptr [ebp - 0x30]
    cmp ecx, 2
    je p3
    mov eax, edi
    mul dword ptr [ecx*4 + {FREE_AT}]
    div dword ptr [{HUNDRED_AT}]
    mov edi, eax
p3: cmp edi, dword ptr [ebp - 4]
    ja refuse
take:
    mov esp, ebp
    pop ebp
    pop edi
    pop ebx
    pop eax
    mov ecx, dword ptr [ebp + 0x24]
    push esi
    push eax
    jmp {TAKE}
refuse:
    mov esp, ebp
    pop ebp
    pop edi
    pop ebx
    add esp, 4
    jmp {AI_NEXT_PLAYER}
muldiv:
    mul ecx
    cmp edx, edi
    jae m1
    div edi
    ret
m1: or eax, -1
    ret
more:
    add dword ptr [ebp - 4], eax
    jnc m2
    or dword ptr [ebp - 4], -1
m2: ret
eleven:
    movzx ecx, byte ptr [edx + 0xe]
    cmp ecx, {LEVELS - 1}
    jbe e1
    mov ecx, {LEVELS - 1}
e1: movzx eax, word ptr [edx + 8]
    imul eax, dword ptr [{STRENGTH_A_AT}]
    add eax, dword ptr [{STRENGTH_B_AT}]
    shr eax, 16
    movzx edx, byte ptr [ecx + {RANGE_LOW_TAB}]
    cmp eax, edx
    jae e2
    mov eax, edx
e2: movzx edx, byte ptr [ecx + {RANGE_TOP_TAB}]
    cmp eax, edx
    jbe e3
    mov eax, edx
e3: ret
gene:
    movzx eax, byte ptr [eax + ecx]
    imul ecx, ecx, {HASH_A}
    imul edx, edx, {HASH_B}
    xor ecx, edx
    imul ecx, ecx, {HASH_C}
    shr ecx, 24
    imul ecx, dword ptr [{PERSONA_RANGE_AT}]
    shr ecx, 8
    add ecx, dword ptr [{PERSONA_LOW_AT}]
    mul ecx
    div dword ptr [{THOUSAND_AT}]
    ret
persona:
    mov edx, dword ptr [ebp - 0x38]
    mov edx, dword ptr [edx - 8]
    add edx, {RANK_TABLE}
    push edx
    mov ecx, dword ptr [edx + {RANK_COUNT}]
    cmp ecx, {RANK_MOST}
    ja r2
r1: dec ecx
    js r2
    cmp dword ptr [edx], eax
    je r3
    add edx, 16
    jmp r1
r2: mov edx, dword ptr [esp]
r3: add esp, 4
    mov ecx, dword ptr [{HAND_COUNT_AT}]
r4: dec ecx
    js r5
    cmp dword ptr [ecx*4 + {HAND_IDS}], eax
    jne r4
    movzx eax, byte ptr [ecx + {HAND_TYPES}]
    jmp r7
r5: movzx ecx, byte ptr [edx + 0xe]
    cmp ecx, {LEVELS - 1}
    jbe r6
    mov ecx, {LEVELS - 1}
r6: imul eax, eax, {HASH_B}
    shr eax, 29
    movzx eax, byte ptr [ecx*8 + eax + {BY_LEVEL_TAB}]
r7: imul eax, eax, {PERSONA_BYTES}
    add eax, {GENES_TAB}
    ret
'''
# the assembled routines (python3 money_cave.py build checks them against the source above)
FEE_BYTES = bytes.fromhex(
    '83f8637605b86300000089c78b048500027b048b4b1cc1e90783e13f0fb69180067b0429d77f0231ff0faf3d800d7b043b3d840d7b0476'
    '068b3d840d7b040fb70c4d20057b04f7e1f73554067b0450f7e7f73554067b043b05880d7b047605a1880d7b045901c88b4b04c1e91c0f'
    'b70c4d20067b04f7e1f73554067b040fb74b2c6953309301000131d169c9b179379ec1e9180faf0d48067b04c1e908030d44067b04f7e1'
    'f73558067b043d9ce0f5057605b89ce0f50589c78b8bb4000000c1e90b81e1ff0f00000faf0d40067b04f7e1b9a0860100f7f101c7c745'
    'f400000000c3')
SALARY_BYTES = bytes.fromhex('83f8637605b8630000008b048590037b048b4b1cc1e90783e13f0fb70c4da0057b04f7e1f73554067b048945c8c745cc00000000c3')
BUDGET_T_BYTES = bytes.fromhex('8b4030505289f0f7254c067b04f73554067b0489c65a5885f6c3')
BUDGET_S_BYTES = bytes.fromhex('52f72550067b04f73554067b045a8d3401e92fb906ff')
PRIZE_BYTES = bytes.fromhex('8b44240450e80da50fff83c404e8b37f05ff83782013751c8b4424048b00f72d90087b04f73d54067b045054e8b6a30fff83c408c3')
BONUS_R_BYTES = bytes.fromhex('505289f0f72594087b04f73554067b0489c65a580375b0c3')
BONUS_END_BYTES = bytes.fromhex('528b45cc0345b0f72594087b04f73554067b045ac3')
# The position need of MLTransfers.lua, two routines.
#
# NEED_PLAN_SOURCE. Entered by a call from club_squad_plan (ebp = its frame) in the place of
# `mov eax, [ebp - 0x48]`, where its work on one club ends: the club's plan record has been
# emptied and the game has written its own slots (a place of the lineup without a player;
# for a club that counts under 25, its weakest outfield positions). From that frame:
# [ebp - 0x50] the mode data, [ebp - 0x4c] the number of the club's plan record, [ebp - 0x60]
# and [ebp - 0x5c] begin and end of the lineup list squad_needs made: entries of 16 bytes,
# the player's id pair at +0, at +8 a dword with his rating at that position in bits 0-6
# (the game's rating function, kind 2) and the position in bits 7-13 (0 is the goalkeeper;
# the game's own list of weak positions leaves him out). The first eleven entries are the
# eleven. The steps of need_slot() below: the two bytes at PLAN_NEED_AT are cleared; a
# plan of kind 2 or 3 is left alone (the game puts an age on its slots); the weakest of
# the eleven (the first of equals) must stand NEED_GAP points or more below the mean of
# the others; if no slot looks for his position yet, the first empty slot gets it, and
# the two bytes get position + 1 and his rating + NEED_BETTER - 1 (at most 99). Every
# register is left as it was, eax as the replaced instruction leaves it.
#
# NEED_PICK_SOURCE. Entered by a call from ai_pick_candidate (ebp = its frame) in the place
# of `mov eax, [ebp + 0x18]; mov edx, [eax]`: edx is the overall above which the club
# looks. [ebp + 0x10] is the plan record and [ebp + 0xc] -> the position of the slot (the
# arguments ai_fill_slots, its only caller, hands in). For the position of the need slot
# edx is raised to the second byte, so that both searches of ai_pick_candidate look only
# above the player the club has, and the second one, which the game makes from 99 down
# when 0 is handed in, stays in the rating range of the club's level like the first.
NEED_PLAN_SOURCE = f'''
    pushad
    mov esi, dword ptr [ebp - 0x4c]
    imul esi, esi, {PLAN_SIZE}
    add esi, dword ptr [ebp - 0x50]
    add esi, {PLAN_RECORDS}
    mov word ptr [esi + {PLAN_NEED_AT}], 0
    cmp dword ptr [esi + 4], 1
    ja out
    mov edi, dword ptr [ebp - 0x60]
    mov eax, dword ptr [ebp - 0x5c]
    sub eax, edi
    cmp eax, {16 * ELEVEN}
    jb out
    lea ecx, [edi + {16 * ELEVEN}]
    xor ebx, ebx
    push ebx
    push ebx
    mov edx, 0x80
next:
    mov eax, dword ptr [edi + 4]
    cmp eax, dword ptr [{NO_PLAYER_AT + 4}]
    jne has
    test eax, eax
    je skip
    mov ax, word ptr [edi]
    cmp ax, word ptr [{NO_PLAYER_AT}]
    je skip
has:
    mov eax, dword ptr [edi + 8]
    and eax, 0x7f
    add ebx, eax
    inc dword ptr [esp + 4]
    cmp eax, edx
    jae skip
    mov edx, eax
    mov dword ptr [esp], edi
skip:
    add edi, 0x10
    cmp edi, ecx
    jb next
    pop edi
    pop ecx
    dec ecx
    jle out
    sub ebx, edx
    mov eax, edx
    add eax, dword ptr [{NEED_GAP_AT}]
    imul eax, ecx
    cmp ebx, eax
    jb out
    add edx, dword ptr [{NEED_MORE_AT}]
    cmp edx, 99
    jbe capped
    mov edx, 99
capped:
    mov eax, dword ptr [edi + 8]
    and eax, 0x3f80
    push edx
    xor edi, edi
    lea ecx, [esi + 0x10]
    lea ebx, [esi + {0x10 + 16 * PLAN_SLOTS}]
scan:
    mov edx, dword ptr [ecx]
    and edx, 0x3f80
    cmp edx, eax
    je same
    cmp edx, {NO_POSITION << 7}
    jne taken
    test edi, edi
    jne taken
    mov edi, ecx
taken:
    add ecx, 0x10
    cmp ecx, ebx
    jb scan
    pop edx
    test edi, edi
    je out
    mov ecx, dword ptr [edi]
    and ecx, 0xffffc07f
    or ecx, eax
    mov dword ptr [edi], ecx
    shr eax, 7
    inc eax
    mov byte ptr [esi + {PLAN_NEED_AT}], al
    mov byte ptr [esi + {PLAN_NEED_AT + 1}], dl
    jmp out
same:
    pop edx
out:
    popad
    mov eax, dword ptr [ebp - 0x48]
    ret
'''
NEED_PICK_SOURCE = f'''
    mov eax, dword ptr [ebp + 0x18]
    mov edx, dword ptr [eax]
    push ecx
    push ebx
    mov ecx, dword ptr [ebp + 0x10]
    movzx eax, byte ptr [ecx + {PLAN_NEED_AT}]
    dec eax
    mov ebx, dword ptr [ebp + 0xc]
    cmp eax, dword ptr [ebx]
    jne done
    movzx eax, byte ptr [ecx + {PLAN_NEED_AT + 1}]
    cmp edx, eax
    jae done
    mov edx, eax
done:
    pop ebx
    pop ecx
    ret
'''
# SQUAD_PRESSURE of MLTransfers.lua, one routine.
#
# PRESSURE_SOURCE. Called by CEILING_SOURCE in step 1 in the place of `cmp ecx, eax`, with
# its frame: ecx is the draw (0 to 99), eax `keeps` of the selling club with what KEEP_BEST
# adds, ebx the player. It returns with the carry flag set if the club keeps him. A draw of
# `keeps` or more: he goes, as before. A draw below `keeps` minus the drop (the drop is 0
# with the setting off): he is kept. Only for a draw between the two the squad is counted,
# the way ai_candidates counts the goalkeepers of a selling club (0x0365f95a-0x0365fa3e:
# the club record, its id pairs, "no player" skipped, a player in a deal, bits 4-5 of
# +0xb4, not counted): the players whose registered position is of the group of his. More
# than the limit of the group: he goes.
PRESSURE_SOURCE = f'''
    cmp ecx, eax
    jae p9
    sub eax, dword ptr [{PRESSURE_DROP_AT}]
    cmp ecx, eax
    jl p8
    mov eax, dword ptr [ebx + 4]
    shr eax, 28
    cmp eax, {len(POSITIONS) - 1}
    ja p8
    push esi
    push edi
    movzx eax, byte ptr [eax + {PRESSURE_GROUPS}]
    push eax
    push 0
    mov ecx, dword ptr [ebp - 0x38]
    mov ecx, dword ptr [ecx - 8]
    push dword ptr [ebp - 0x3c]
    call {TEAM_RECORD}
    mov edi, dword ptr [eax + {TEAM_COUNT}]
    shr edi, 9
    and edi, 0x7f
    lea esi, [eax + {TEAM_SQUAD}]
    lea edi, [esi + edi*8]
p1: cmp esi, edi
    jae p4
    push {NO_PLAYER_AT}
    mov ecx, esi
    call {SAME_ID}
    test al, al
    jne p3
    mov ecx, dword ptr [ebp - 0x38]
    mov ecx, dword ptr [ecx - 8]
    push dword ptr [esi + 4]
    push dword ptr [esi]
    call {PLAYER_RECORD}
    test byte ptr [eax + 0xb4], 0x30
    jne p3
    mov eax, dword ptr [eax + 4]
    shr eax, 28
    cmp eax, {len(POSITIONS) - 1}
    ja p3
    movzx eax, byte ptr [eax + {PRESSURE_GROUPS}]
    cmp eax, dword ptr [esp + 4]
    jne p3
    inc dword ptr [esp]
p3: add esi, 8
    jmp p1
p4: pop eax
    pop edx
    movzx edx, byte ptr [edx + {PRESSURE_LIMITS}]
    pop edi
    pop esi
    cmp edx, eax
    cmc
    ret
p8: stc
p9: ret
'''
INCOME_N_BYTES = bytes.fromhex('8d863e56cbffe86d00000089c18b45fcf725ac0d7b04f73554067b0401c8c3')
WAGES_KEEP_BYTES = bytes.fromhex('8945fc58ff750850e916810cff')
INCOME_M_BYTES = bytes.fromhex('69c088130000eb04')
INCOME_SCALE_BYTES = bytes.fromhex('85c07e0e52f7258c0d7b04f73554067b045ac3')
INCOME_S_BYTES = bytes.fromhex('81c6983a00005089f0e8deffffff89c658c3')
LEAGUE_BYTES = bytes.fromhex('31c9eb0d0fb7144d900d7b0439fa7411413b0da80d7b0472eb8b0485c0077b04c36bc91801c10fb7044db00d7b046bc064c3')
CEILING_BYTES = bytes.fromhex(
    '53575589e581ec900000008b45008945c88b58d88b480481f9580d6603740c81f9b90d66030f85c6'
    '040000894dc08b48dc894dac8b48188b51048955bc8b09894de88b50308b128955b88b5014691235'
    'aeb2c28955b48b000fb6481b894df08b401c8b0083f8090f87840400008945e031c98b93b4000000'
    '83e20f4a83fa01760e41f783b800000000000060750141894dd00fb74b2c6953309301000131d189'
    '4dd86955e8b179379e31d1894dd43155b48b4dac81e1ffffff0069c993010001314db4894dac8b45'
    'e8e8c80400008945ec8955b031c9518b45ec8b55e8e8800400005989848d70ffffff4183f90e72e6'
    'c745f80d0000006a028d45f85053e873f007ff83c40c0fb6c08945dc8b55b0e8110400008945cc83'
    '7dd0000f84370100008365f8008d45f8508d45c45089d9e8876505ff8b45c43b0534eb4f020f8415'
    '0100008b55e88b0dc8477d0449782e3904cdcc477d04750d3914cdd0477d040f849c0300003914cd'
    'cc477d0475de3904cdd0477d040f8486030000ebcf837dd0020f85d1000000e80a0400005052e892'
    '0300008945a85a833d5c427d040074588b4dc88b49f48b45c425ff3f00003d8d0200000f83990000'
    '0083bc81ac070000170f868b000000817dc0b90d660375285253e86bf407ff83c4045a8b4de083f9'
    '087315837dbc04750439c1770b83f8077360807a0e08735a586a0c598b55c4e85e0300008b55cc2b'
    '55a83b15f44f7d047d178b55dc0315ec4f7d042b55a87e090faf15f04f7d0401d0694dc4b179379e'
    '334dd8334dac69c92febd427c1e9186bc964c1e908e8422100000f82b1020000eb0658e9a9020000'
    '837dd00174358b45dc3b05f84f7d04732a8b83b4000000c1e0093b05e44f7d047319694dd4b16756'
    '16c1e9186bc964c1e9083b4d800f836e0200008b45cc03459c3945dc0f875f0200008b55b88b4dc8'
    '8b49f48b45e825ff3f00003d8d02000073128b8481ac0700003b0558427d04730383ca018955e483'
    '7db8000f850c0100008b55ec807a10ff0f8494000000694db46bcaeb85c1e9186bc964c1e90831c0'
    '8b9570ffffff39d1722740039574ffffff39d1721c40039578ffffff39d17211837de4000f84df01'
    '00008b55ec0fb64210837de400752b8b4dc80fb649de3b0d54427d04751c694db4512d9eccc1e918'
    '6bc964c1e9083b8d7cffffff0f83a7010000837df00074118b55ec0fb64a1039c175040fb64a1189'
    'c83b45d00f8587010000837de40075656945e8b179379e69c091f44525c1e8188b15fc4f7d048d4c'
    '12010fafc1c1e80829d08b4b1cc1e90783e13f29c18b55ec3a4a0e7c053a4a0f7e2b694dd4933587'
    '1bc1e9186bc964c1e9088b45a4837dd000750a0faf05e84f7d046bc96439c10f821c0100008b4584'
    '8d0c45010000006955d4656b54e6c1ea180fafcac1e90829c1014ddc837de400750f8b45cc2b4598'
    '3945dc0f8ce80000008b55f08b4dec2251128b4de074128b45dc0fb69128427d0439d00f8fc80000'
    '008b048d00427d0483f8ff0f84a80000006a645f8b4d88e8ba0000008945fc8b45e40b45f0741ba1'
    '38427d048b4d90e8a20000008d0c388b45fce8970000008945fca134427d048b4d8ce88700000069'
    '4dd46bcaeb85c1e9180fafc88b45fcbf00640000e86d000000e8750000008b8bb4000000c1e90b81'
    'e1ff0f00000faf4d948b45fcbfa0860100e848000000e8500000008b45dce8f1bdfdff8b4dd083f9'
    '02741189f8f7248d3c427d04f73554067b0489c73b7dfc771089ec5d5f5b588b4d245650e9f34495'
    'ff89ec5d5f5b83c404e94eace8fef7e139fa7303f7f7c383c8ffc30145fc7304834dfcffc30fb64a'
    '0e83f9097605b9090000000fb742080faf054c427d04030550427d04c1e8100fb69164427d0439d0'
    '730289d00fb6916e427d0439d0760289d0c30fb6040869c99301000169d2b179379e31d169c96bca'
    'eb85c1e9180faf0d48427d04c1e908030d44427d04f7e1f73558067b04c38b55c88b52f881c2cc84'
    'cc00528b8aa028000081f98a020000770c4978093902740883c210ebf48b142483c4048b0d60427d'
    '0449781239048dc8447d0475f40fb68108447d04eb1f0fb64a0e83f9097605b90900000069c0b179'
    '379ec1e81d0fb684c878427d046bc01405c8427d04c3')
assert CEILING_CODE + len(CEILING_BYTES) <= FAME_KNOWN_AT and CAVE_2 + CAVE_2_SIZE <= CAVE_2_LIMIT
NEED_PLAN_BYTES = bytes.fromhex(
    '608b75b469f6180100000375b081c60cb8cc0066c786090100000000837e04010f87d80000008b7da08b45a429f83db00000000f82c500'
    '00008d8fb000000031db5353ba800000008b47043b0508eb4f02751085c07421668b07663b0504eb4f0274158b470883e07f01c3ff4424'
    '0439d0730589c2893c2483c71039cf72c95f59497e7a29d389d0030500647d040fafc139c37269031504647d0483fa637605ba63000000'
    '8b470825803f00005231ff8d4e108d9e100100008b1181e2803f000039c2743881fa80060000750685ff750289cf83c11039d972df5a85'
    'ff741f8b0f81e17fc0ffff09c1890fc1e8074088860901000088960a010000eb015a618b45b8c3')
NEED_PICK_BYTES = bytes.fromhex('8b45188b1051538b4d100fb68109010000488b5d0c3b03750d0fb6810a01000039c2730289c25b59c3')
PRESSURE_BYTES = bytes.fromhex(
    '39c10f83a90000002b05406d7d0439c10f8c9a0000008b4304c1e81c83f80c0f878b00000056'
    '570fb680486d7d04506a008b4dc88b49f8ff75c4e8d2bb04ff8bb828030000c1ef0983e77f8db0f80000008d'
    '3cfe39fe73496804eb4f0289f1e8026d40fe84c075348b4dc88b49f8ff7604ff36e865ba04fff680b4000000'
    '30751b8b4004c1e81c83f80c77100fb680486d7d043b4424047503ff042483c608ebb3585a0fb692446d7d04'
    '5f5e39c2f5c3f9c3')
assert PRESSURE_CODE + len(PRESSURE_BYTES) <= CAVE_5 + CAVE_5_SIZE


ROUTINES = ((FEE_CODE, FEE_SOURCE, 'FEE_BYTES'), (SALARY_CODE, SALARY_SOURCE, 'SALARY_BYTES'),
            (BUDGET_T_CODE, BUDGET_T_SOURCE, 'BUDGET_T_BYTES'), (BUDGET_S_CODE, BUDGET_S_SOURCE, 'BUDGET_S_BYTES'),
            (PRIZE_CODE, PRIZE_SOURCE, 'PRIZE_BYTES'), (BONUS_R_CODE, BONUS_R_SOURCE, 'BONUS_R_BYTES'),
            (BONUS_END_CODE, BONUS_END_SOURCE, 'BONUS_END_BYTES'),
            (INCOME_N_CODE, INCOME_N_SOURCE, 'INCOME_N_BYTES'), (INCOME_M_CODE, INCOME_M_SOURCE, 'INCOME_M_BYTES'),
            (INCOME_SCALE_CODE, INCOME_SCALE_SOURCE, 'INCOME_SCALE_BYTES'),
            (INCOME_S_CODE, INCOME_S_SOURCE, 'INCOME_S_BYTES'), (LEAGUE_CODE, LEAGUE_SOURCE, 'LEAGUE_BYTES'),
            (WAGES_KEEP_CODE, WAGES_KEEP_SOURCE, 'WAGES_KEEP_BYTES'))

# limits the module keeps, so that no step of the routines can overflow 32 bits
MAX_AGE_PERCENT = 300
MAX_POSITION_PERCENT = 200
MAX_SPREAD = 30
MAX_FAME = 100
MAX_SALARY = 40000000
MAX_SALARY_AGE_PERCENT = 200
MIN_BUDGET, MAX_BUDGET = 0.1, 10.0
MIN_PRIZE, MAX_PRIZE = 0.001, 2000      # millions on the screen
MAX_SHARE = 100
MIN_GAP, MAX_GAP = 1.0, 10.0
MAX_BONUS = 1000
MIN_YEARS, MAX_YEARS = 1, 5
MAX_TALENT_STEP, MAX_TALENT_PERCENT = 50, 200
MIN_INCOME, MAX_INCOME = 10, 1000
MAX_INCOME_WAGES = 100                  # percent: the wage bill times this still fits the division
MAX_LEAGUE_ROW = 650                    # millions: a place of a list by league is kept in 16 bits
MIN_CEILING, MAX_CEILING = 0.01, 9999   # millions; 0 in the list: no ceiling for that group of clubs
MAX_STRETCH, MAX_NEED = 300, 300        # percent
MAX_PERSONA_SPREAD = 50                 # percent
MAX_SLOPE, MAX_BASE = 0.5, 99           # STRENGTH: rating points per ranking point, rating at 0 points
MAX_SQUAD = 32
MAX_KEEP_FROM, MAX_KEEP_STEP, MAX_KEEP_BIGGER = 99, 100, 99      # KEEP_BEST
MAX_KNOWN, MAX_AGE_SHIFT = 100, 5       # KNOWN_FROM, AGE_SHIFT
MAX_KNOWN_FAME = 4096                   # KNOWN_FAME: the popularity of a player is 0 to 4095, so 4096 is "no player"
MAX_STRICT_FREE = 100                   # STRICT_FREE, percent
MAX_NEED_GAP, MAX_NEED_BETTER = 30, 20  # NEED_GAP, NEED_BETTER: rating points, from 1
MAX_PRESSURE_LIMIT, MAX_PRESSURE_DROP = 99, 100     # SQUAD_PRESSURE: players of a group, percent
# a persona: the lowest and the highest number each entry takes (GENE_NAMES, then the two ages)
GENE_LIMITS = {'free': (0, 100), 'listed': (0, 100), 'clubs': (0, 100), 'winter': (0, 100), 'knows': (1, 100),
               'fog': (0, 10), 'wealth': (10, 250), 'premium': (0, 250), 'panic': (0, 250), 'fame': (0, 250),
               'ambition': (0, 99), 'prestige': (0, 99), 'keeps': (0, 100), 'strict': (0, 100)}
AGE_LIMITS = (0, 63)
NO_TALENT = 255

# the code the routines rely on: name, address, byte count (MLMoney.lua compares these
# bytes of the running game with the bytes of the exe file before it writes anything)
CONTEXT = (
    ('fee code', 0x038ab832, 228),          # start of the fee function to the end of the changed part and its use
    ('salary code', 0x038ac6f8, 15),        # the player record goes into ebx
    ('salary code 2', 0x038ac86f, 110),     # the rating part and what follows
    ('salary roles', 0x038ac937, 244),      # role bonus and club factor, up to the sum
    ('salary sum', 0x038aca2b, 49),         # where the two numbers are added
    ('salary end', 0x038aca5c, 870),        # band bonus, award bonuses, the last sum and its limits
    ('budget code', 0x038adc0b, 346),       # both budget sums to the place they are stored
    ('position', 0x03827961, 17),           # getter of the registered position
    ('age', 0x03827ba9, 20),                # getter of the age
    ('cup prize', 0x038aa307, 383),         # the whole function
    ('cup table', CUP_TABLE, 876),          # the game's 73 rows
    ('league prize', 0x038a9ebb, 1100),     # the whole function
    ('prize step', 0x03640abe, 200),        # both places where a prize is paid
    ('balance add', BALANCE_ADD, 98),       # the whole function
    ('budget add', TRANSFER_BUDGET_ADD, 98),  # the whole function
    ('mode number', MENU_GETTER, 6),        # the whole function
    ('years limit', 0x03887f5d, 109),       # the whole function
    ('income', 0x038ade76, 141),            # season_income, the whole function
    ('rank income', 0x038a9e6b, 66),        # the whole function
    ('career money', 0x038adfb6, 144),      # club_money_setup: the amount by club level
)


# the same for MLTransfers.lua; compared only when one of its parts is on
CONTEXT_CEILING = (
    ('choose', AI_CANDIDATES, 1462),        # ai_candidates, the whole function
    ('pick', AI_PICK, 1483),                # ai_pick_candidate, the whole function: its two calls of ai_candidates
                                            # and the rule by which it takes one of the three (the selling side)
    ('range', AI_MAX_OVERALL, 152),         # the highest overall of a club's rating range, by level (WINDOW_TOP)
    ('range low', AI_MIN_OVERALL, 152),     # the lowest (WINDOW_LOW)
    ('club', PLAYER_CLUB, 44),              # the club a player plays for, the whole function
    ('band', PLAYER_BAND, 345),             # the status band of a player, the whole function
    ('club level', 0x0365d775, 176),        # what ai_pick_candidate asks about the selling club: its level, from the ranking
    ('ranking', 0x031b1c34, 138),           # the look-up of a club in the ranking that function uses
    ('rating', RATING, 9),                  # the rating call of the fee function
    ('take', TAKE, 114),                    # the function that adds a player to the candidates, both its returns
    ('plan', SQUAD_PLAN, 2401),             # club_squad_plan, the whole function: the frame the need routine reads
    ('fill', AI_FILL_SLOTS, 1098),          # ai_fill_slots, the whole function: what it hands to ai_pick_candidate
    ('lineup', LINEUP_RATINGS, 111),        # squad_needs: player, position and rating of an entry of the lineup list
    ('team', TEAM_RECORD, 136),             # the record of a club, the whole function (SQUAD_PRESSURE walks its squad)
    ('player', PLAYER_RECORD, 111),         # the record of a player, the whole function
    ('no player', SAME_ID, 53),             # "are two id pairs the same", the whole function
    ('no player id', NO_PLAYER_AT, 8),      # the id pair of an empty squad entry it is asked with
    ('trim fill', TRIM_FILL_SITE, 3),       # squad trim room test: cmp eax, 0x20
    ('trim close', TRIM_CLOSE_SITE, 3),     # deal closing squad cap check: cmp dword ptr [edx], 0x20
    ('trim evict', TRIM_EVICT_SITE, 9),     # squad eviction mode gate: cmp eax, 0xd; jne ...
)


def call(site, target):
    return b'\xe8' + struct.pack('<i', target - (site + 5))


assert THOUSAND_AT == HUNDRED_AT + 4


FEE_SITE_NEW = call(FEE_SITE, FEE_CODE) + b'\x90' * 12
# MLTransfers checks the cave and installed hook: a stale mark after rollback is not ready.
MONEY_NEEDED = (('value routine', FEE_CODE, FEE_BYTES),
                ('numbers', HUNDRED_AT, struct.pack('<II', 100, 1000)),
                ('value hook', FEE_SITE, FEE_SITE_NEW))
SALARY_SITE_NEW = call(SALARY_SITE, SALARY_CODE) + b'\xeb' + bytes([SALARY_BLOCK_END - (SALARY_SITE + 7)])
BUDGET_T_SITE_NEW = call(BUDGET_T_SITE, BUDGET_T_CODE)
BUDGET_S_SITE_NEW = call(BUDGET_S_SITE, BUDGET_S_CODE) + b'\x90' * 3
#        name, address, bytes of the game, bytes of the module
# ('years': the number in its last four bytes is a setting, and so are the amounts of the six
# 'nat' places; Tables.sites() gives them as written)
SITES = (('fee', FEE_SITE, FEE_SITE_OLD, FEE_SITE_NEW), ('salary', SALARY_SITE, SALARY_SITE_OLD, SALARY_SITE_NEW),
         ('budget 1', BUDGET_T_SITE, BUDGET_T_SITE_OLD, BUDGET_T_SITE_NEW),
         ('budget 2', BUDGET_S_SITE, BUDGET_S_SITE_OLD, BUDGET_S_SITE_NEW),
         ('cup 1', 0x038aa400, struct.pack('<I', CUP_TABLE), struct.pack('<I', CUP_TAB)),
         ('cup 2', 0x038aa408, struct.pack('<I', CUP_TABLE + 4), struct.pack('<I', CUP_TAB + 4)),
         ('cup 3', 0x038aa423, struct.pack('<I', CUP_TABLE + 8), struct.pack('<I', CUP_TAB + 8)),
         ('league 1', LEAGUE1_SITE, LEAGUE1_SITE_OLD, call(LEAGUE1_SITE, LEAGUE_CODE) + b'\x90' * 2),
         ('league 2', LEAGUE2_SITE, LEAGUE2_SITE_OLD, b'\x8b\x04\x85' + struct.pack('<I', LEAGUE2_TAB)),
         ('prize 1', PRIZE_SITE_1, PRIZE_SITE_1_OLD, call(PRIZE_SITE_1, PRIZE_CODE)),
         ('prize 2', PRIZE_SITE_2, PRIZE_SITE_2_OLD, call(PRIZE_SITE_2, PRIZE_CODE)),
         ('pay gap', RANK_SITE, RANK_SITE_OLD, struct.pack('<I', RANK_STEP_AT)),
         ('bonus 1', BONUS_R_SITE, BONUS_R_SITE_OLD, call(BONUS_R_SITE, BONUS_R_CODE) + b'\x90'),
         ('bonus 2', BONUS_END_SITE, BONUS_END_SITE_OLD, call(BONUS_END_SITE, BONUS_END_CODE) + b'\x90' * 7),
         ('years', YEARS_SITE, YEARS_SITE_OLD, b'\xb8\x05\x00\x00\x00'),
         ('income 1', INCOME_N_SITE, INCOME_N_SITE_OLD, call(INCOME_N_SITE, INCOME_N_CODE) + b'\x90'),
         ('income 2', INCOME_M_SITE, INCOME_M_SITE_OLD, call(INCOME_M_SITE, INCOME_M_CODE) + b'\x90'),
         ('income 3', INCOME_S_SITE, INCOME_S_SITE_OLD, call(INCOME_S_SITE, INCOME_S_CODE) + b'\x90'),
         ('income 4', INCOME_W_SITE, INCOME_W_SITE_OLD, call(INCOME_W_SITE, WAGES_KEEP_CODE) + b'\x90' * 4),
         ) + tuple(('nat %d' % i, at, struct.pack('<I', old), struct.pack('<I', old))
                   for i, (at, old) in enumerate(NATIONAL_SITES)) + (
         ('transfers', CEILING_SITE, CEILING_SITE_OLD, call(CEILING_SITE, CEILING_CODE) + b'\x90' * 4),
         ('star band', STAR_BAND_SITE, STAR_BAND_SITE_OLD, STAR_BAND_SITE_NEW),
         ('star pick', STAR_PICK_BAND_SITE, STAR_PICK_BAND_SITE_OLD, STAR_PICK_BAND_SITE_NEW),
         ('star level', STAR_PICK_LEVEL_SITE, STAR_PICK_LEVEL_SITE_OLD, STAR_PICK_LEVEL_SITE_NEW),
         ('trim plan', TRIM_PLAN_SITE, TRIM_PLAN_SITE_OLD, TRIM_PLAN_SITE_NEW),
         ('trim fill', TRIM_FILL_SITE, TRIM_FILL_SITE_OLD, TRIM_FILL_SITE_NEW),
         ('trim close', TRIM_CLOSE_SITE, TRIM_CLOSE_SITE_OLD, TRIM_CLOSE_SITE_NEW),
         ('trim evict', TRIM_EVICT_SITE, TRIM_EVICT_SITE_OLD, TRIM_EVICT_SITE_NEW),
         ('need plan', NEED_PLAN_SITE, NEED_PLAN_SITE_OLD, call(NEED_PLAN_SITE, NEED_PLAN_CODE) + b'\x90'),
         ('need pick', NEED_PICK_SITE, NEED_PICK_SITE_OLD, call(NEED_PICK_SITE, NEED_PICK_CODE)))
TRANSFER_SITES = ('transfers', 'star band', 'star pick', 'star level',
                  'trim plan', 'trim fill', 'trim close', 'trim evict',
                  'need plan', 'need pick')     # the places of MLTransfers.lua
assert all(len(old) == len(new) for _, _, old, new in SITES)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def curve(knots, lo, hi, geometric):
    """Value for every whole number lo..hi from a list of (x, y) knots: straight lines
    between the knots (or, geometric, straight lines of the logarithm), the end values
    outside them."""
    out = []
    for x in range(lo, hi + 1):
        if x <= knots[0][0]:
            y = knots[0][1]
        elif x >= knots[-1][0]:
            y = knots[-1][1]
        else:
            for (x1, y1), (x2, y2) in zip(knots, knots[1:]):
                if x1 <= x <= x2:
                    t = (x - x1) / (x2 - x1)
                    y = y1 * (y2 / y1) ** t if geometric else y1 + (y2 - y1) * t
                    break
        out.append(y)
    return out


def amount(millions):
    """Millions on the screen -> stored amount, rounded to 10 (1,000 on the screen)."""
    return int(millions * 1000 + 0.5) * 10


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Tables:
    incoming = False                # version 7 of MLTransfers.lua: the offers for the user's players

    """The settings of MLMoney.lua as the module stores them.

    value, age: lists of (x, y) knots; position: {name: percent}; spread: percent;
    fame: percent per 1,000 points; salary: knots or None (the salary formula stays the
    game's); salary_age: knots; budget_transfer, budget_salary: factor or None (the
    game's own 2); cup: list of (competition, stage, millions) or None; league, league_2:
    millions for place 1 to 22 and 1 to 24, or None; prize_share: percent or None;
    pay_gap: factor of the first club of the ranking or None (the game's own 2); bonus:
    percent or None; young_years: 1 to 5 or None (the game's own 3); talent: knots (age,
    rating) or None, talent_step: percent per rating point, talent_max: percent,
    talent_cap: millions; income: percent or None; league_by_id: list of (league, list of
    millions | percent of `league`) or None; cup_national: six amounts in millions or
    None; cup_tv: list of (competition, millions) or None; income_wages: percent of the
    wage bill added to the yearly income, or None; ceiling: 10 amounts in millions for the
    club ranking places of LEVEL_PLACES (best clubs first; 0: no ceiling), or None;
    ceiling_rating: with a ceiling, the second search of a club stays below the top of its
    rating range; ceiling_stretch: percent above its ceiling at which a club's chance to
    take a player has fallen to none; ceiling_need: percent by which need raises the
    ceiling; ceiling_listed, ceiling_free: percent of his value that counts for a listed
    player and for one signed without a transfer; sell: the selling club's side is asked
    (SELL_SIDE); scouting: the `knows` of the personas counts (SCOUTING); persona: None, or
    a dict with archetypes [(name, {entry: number, 'age': (first, last), 'second': (channel,
    channel)})], groups (10 lists of names, best clubs first), clubs [(club id, name)],
    spread (percent), strength (rating points per ranking point, rating at 0 points),
    winter (month or 0), squad (players); rivals: None, or [(club id, club id)]: the two
    clubs of a pair do not buy each other's players who have a contract (RIVALS)."""

    def __init__(self, value, age, position, spread, fame, salary, salary_age, budget_transfer, budget_salary,
                 cup=None, league=None, league_2=None, prize_share=None, pay_gap=None, bonus=None,
                 young_years=None, talent=None, talent_step=0, talent_max=0, talent_cap=0, income=None,
                 league_by_id=None, cup_national=None, cup_tv=None, income_wages=None, ceiling=None,
                 ceiling_rating=True, ceiling_stretch=0, ceiling_need=0, ceiling_listed=100, ceiling_free=100,
                 sell=False, scouting=False, persona=None, rivals=None, need=None, pressure=None,
                 sporting_projects=True, project_count=5, project_boost=20, project_rank_max=15,
                 top_five_leagues=None, project_clubs=None):
        # need: None, or (gap, better): NEED_GAP and NEED_BETTER of MLTransfers.lua with NEED on
        # pressure: None, or ((GK, DF, MF, FW), drop): SQUAD_PRESSURE of MLTransfers.lua; counts with PERSONA only
        # persona may also hold: keep (from, step, bigger), known, shift (KEEP_BEST, KNOWN_FROM, AGE_SHIFT) and
        # fame, strict_free (KNOWN_FAME, STRICT_FREE)
        self.sporting_projects = bool(sporting_projects)
        self.project_count = clamp(int(project_count + 0.5), 1, 15) if sporting_projects else 0
        self.project_boost = clamp(int(project_boost + 0.5), 0, 100) if sporting_projects else 0
        self.project_rank_max = clamp(int(project_rank_max + 0.5), 1, 50) if sporting_projects else 15
        self.top_five_leagues = set(top_five_leagues or TOP_FIVE_LEAGUES)
        self.project_clubs = set(project_clubs or ())
        self.value = [clamp(amount(m), 1, CAP) for m in curve(value, 0, 99, True)]
        self.age = [clamp(int(p + 0.5), 0, MAX_AGE_PERCENT) for p in curve(age, 0, 63, False)]
        self.position = [clamp(int(position[n] + 0.5), 0, MAX_POSITION_PERCENT) for n in POSITIONS] + [100] * 3
        s = clamp(int(spread + 0.5), 0, MAX_SPREAD)
        self.spread_low, self.spread_range = 1000 - 10 * s, 20 * s
        self.fame = clamp(int(fame + 0.5), 0, MAX_FAME)
        self.has_salary = bool(salary)
        self.has_gap = bool(pay_gap)
        self.gap = clamp(float(pay_gap), MIN_GAP, MAX_GAP) if pay_gap else 2.0
        self.rank_step = (self.gap - 1) / 250 if pay_gap else RANK_STEP_OLD
        self.salary = ([clamp(amount(m / self.gap), 1, MAX_SALARY) for m in curve(salary, 0, 99, True)]
                       if salary else [0] * 100)
        self.salary_age = [clamp(int(p + 0.5), 0, MAX_SALARY_AGE_PERCENT) for p in curve(salary_age, 0, 63, False)]
        self.budget_transfer = None if not budget_transfer else int(budget_transfer * 100 + 0.5)
        self.budget_salary = None if not budget_salary else int(budget_salary * 100 + 0.5)
        self.has_cup = cup is not None
        rows = [list(r) for r in GAME_CUP_ROWS]
        tv = dict((int(c), m) for c, m in cup_tv or ())
        for competition, stage, millions in cup or ():
            hit = [r for r in rows if r[0] == competition and r[1] == stage]
            assert hit, 'the game has no prize row for competition %d, stage %d' % (competition, stage)
            hit[0][2] = prize(millions + tv.get(competition, 0))
        self.cup_rows = [tuple(r) for r in rows]
        self.has_league, self.has_league_2 = league is not None, league_2 is not None
        assert league is None or len(league) == LEAGUE1_PLACES
        assert league_2 is None or len(league_2) == LEAGUE2_PLACES
        self.league = [0] + [prize(m, 0) for m in league] if self.has_league else [0] * (LEAGUE1_PLACES + 1)
        self.league_2 = [0] + [prize(m, 0) for m in league_2] if self.has_league_2 else [0] * (LEAGUE2_PLACES + 1)
        self.prize_share = None if not prize_share else clamp(int(prize_share + 0.5), 0, MAX_SHARE)
        self.bonus = None if bonus is None else clamp(int(bonus + 0.5), 0, MAX_BONUS)
        self.young_years = None if not young_years else clamp(int(young_years + 0.5), MIN_YEARS, MAX_YEARS)
        # talent: the rating above which the bonus starts, by age; ages above the last entry have none
        self.talent = [NO_TALENT] * 64
        if talent:
            last = int(talent[-1][0])
            for a, r in enumerate(curve(talent, 0, 63, False)):
                if a <= last:
                    self.talent[a] = clamp(int(r + 0.5), 0, 254)
        self.talent_step = clamp(int(talent_step + 0.5), 0, MAX_TALENT_STEP) if talent else 0
        self.talent_max = clamp(int(talent_max + 0.5), 0, MAX_TALENT_PERCENT) if talent else 0
        self.talent_cap = clamp(amount(talent_cap), 0, CAP) if talent else 0
        self.income = None if not income else clamp(int(income + 0.5), MIN_INCOME, MAX_INCOME)
        self.income_wages = None if not income_wages else clamp(int(income_wages + 0.5), 1, MAX_INCOME_WAGES)
        # lists by league: only with `league` on. A list shorter than 22 is filled with its last number.
        self.league_rows = []
        for league_id, what in (league_by_id or ()) if self.has_league else ():
            if isinstance(what, (list, tuple)):
                full = [prize(m, 0) for m in what] + [prize(what[-1], 0)] * (LEAGUE1_PLACES - len(what))
            else:
                full = [a * int(what + 0.5) // 100 for a in self.league[1:]]
            words = [0] + [min(a // LEAGUE_UNIT, 0xffff) for a in full[:LEAGUE1_PLACES]] + [0]
            assert len(words) == LEAGUE_ROW_WORDS
            self.league_rows.append((int(league_id), words))
        assert len(self.league_rows) <= LEAGUE_ROWS
        self.national = None if not cup_national else [prize(m) for m in cup_national]
        assert self.national is None or len(self.national) == len(NATIONAL_SITES)
        # by club level 0 to 9 (the list in the settings starts with the best clubs, level 9)
        assert ceiling is None or len(ceiling) == LEVELS
        self.has_ceiling = ceiling is not None
        self.ceiling = [NO_CEILING] * LEVELS if ceiling is None else [
            clamp(amount(m), amount(MIN_CEILING), amount(MAX_CEILING)) if m else NO_CEILING for m in reversed(ceiling)]
        self.ceiling_top = list(WINDOW_TOP) if ceiling_rating and self.has_ceiling else [NO_TOP] * LEVELS
        self.ceiling_stretch = clamp(int(ceiling_stretch + 0.5), 0, MAX_STRETCH) if self.has_ceiling else 0
        self.ceiling_need = clamp(int(ceiling_need + 0.5), 0, MAX_NEED) if self.has_ceiling else 0
        self.ceiling_listed = clamp(int(ceiling_listed + 0.5), 0, 100) if self.has_ceiling else 100
        self.ceiling_free = clamp(int(ceiling_free + 0.5), 0, 100) if self.has_ceiling else 100
        # MLTransfers.lua writes only if one of its parts is on
        self.sell, self.has_persona = bool(sell), persona is not None
        self.scouting = bool(scouting) and self.has_persona
        self.rivals = [(int(a), int(b)) for a, b in rivals or ()]
        assert len(self.rivals) <= RIVALS
        self.need = need is not None
        self.need_gap, self.need_more = (clamp(int(need[0] + 0.5), 1, MAX_NEED_GAP),
                                         clamp(int(need[1] + 0.5), 1, MAX_NEED_BETTER) - 1) if self.need else (0, 0)
        self.transfers = (self.has_ceiling or self.sell or self.has_persona or bool(self.rivals) or self.need
                          or self.incoming)
        # the personas: number 0 is the club of version 1, the others are ARCHETYPES in their order
        self.genes, self.names = [NEUTRAL], ['']
        self.by_level, self.hand = [[0] * BY_LEVEL for _ in range(LEVELS)], []
        self.persona_low, self.persona_range, self.strength_a, self.strength_b, self.winter, self.squad = 1000, 0, 0, 0, 0, 0
        self.keep_from, self.keep_step, self.keep_bigger, self.known, self.age_shift = 0, 0, 0, 0, 0
        self.known_fame, self.strict_free = 0, 0
        if persona is not None:
            for name, numbers in persona['archetypes']:
                record = [clamp(int(numbers[k] + 0.5), *GENE_LIMITS[k]) for k in GENE_NAMES]
                if not scouting:
                    record[GENE_NAMES.index('knows')] = NEUTRAL[GENE_NAMES.index('knows')]
                record += [clamp(int(a + 0.5), *AGE_LIMITS) for a in numbers['age']]
                record += [CHANNELS.index(c) for c in numbers['second']] + [
                    1 if numbers.get('rating', True) else 0, 0]
                self.genes.append(bytes(record))
                self.names.append(name)
            assert len(self.genes) <= PERSONAS and len(persona['groups']) == LEVELS
            for level, group in zip(range(LEVELS - 1, -1, -1), persona['groups']):
                assert 1 <= len(group) <= BY_LEVEL
                self.by_level[level] = [self.names.index(group[k % len(group)]) for k in range(BY_LEVEL)]
            self.hand = [(int(club), self.names.index(name)) for club, name in persona['clubs']]
            assert len(self.hand) <= HAND
            spread = clamp(int(persona['spread'] + 0.5), 0, MAX_PERSONA_SPREAD)
            self.persona_low, self.persona_range = 1000 - 10 * spread, 20 * spread
            slope, base = persona['strength']
            self.strength_a = int(clamp(slope, 0, MAX_SLOPE) * 65536 + 0.5)
            self.strength_b = int(clamp(base, 0, MAX_BASE) * 65536 + 0.5) + 32768
            self.winter = clamp(int(persona['winter'] + 0.5), 0, 12)
            self.squad = clamp(int(persona['squad'] + 0.5), 0, MAX_SQUAD)
            self.keep_from, self.keep_step, self.keep_bigger = (
                clamp(int(x + 0.5), 0, most) for x, most in zip(persona.get('keep', (0, 0, 0)),
                                                                (MAX_KEEP_FROM, MAX_KEEP_STEP, MAX_KEEP_BIGGER)))
            self.known = clamp(int(persona.get('known', MAX_KNOWN) + 0.5), 0, MAX_KNOWN)
            self.age_shift = clamp(int(persona.get('shift', 0) + 0.5), 0, MAX_AGE_SHIFT)
            self.known_fame = clamp(int(persona.get('fame', MAX_KNOWN_FAME) + 0.5), 0, MAX_KNOWN_FAME)
            self.strict_free = clamp(int(persona.get('strict_free', MAX_STRICT_FREE) + 0.5), 0, MAX_STRICT_FREE)
        self.pressure_limits, self.pressure_drop = [0] * len(GROUPS), 0
        if persona is not None and pressure is not None:
            self.pressure_limits = [clamp(int(x + 0.5), 0, MAX_PRESSURE_LIMIT) for x in pressure[0]]
            self.pressure_drop = clamp(int(pressure[1] + 0.5), 0, MAX_PRESSURE_DROP)

    def sites(self):
        """The places the module changes with these settings: (name, address, old, new)."""
        share, bonus, income = self.prize_share is not None, self.bonus is not None, self.income is not None
        wages = self.income_wages is not None
        on = {'fee': True, 'salary': self.has_salary, 'budget 1': self.budget_transfer is not None,
              'budget 2': self.budget_salary is not None, 'cup 1': self.has_cup, 'cup 2': self.has_cup,
              'cup 3': self.has_cup, 'league 1': self.has_league, 'league 2': self.has_league_2,
              'prize 1': share, 'prize 2': share, 'pay gap': self.has_gap, 'bonus 1': bonus, 'bonus 2': bonus,
              'years': self.young_years is not None, 'income 1': income or wages, 'income 2': income, 'income 3': income,
              'income 4': wages, 'transfers': self.transfers, 'star band': self.transfers,
              'star pick': self.transfers, 'star level': self.transfers,
              'trim plan': self.transfers, 'trim fill': self.transfers,
              'trim close': self.transfers, 'trim evict': self.transfers,
              'need plan': self.need, 'need pick': self.need}
        used = []
        for name, at, old, new in SITES:
            if name == 'years' and on[name]:
                new = b'\xb8' + struct.pack('<I', self.young_years)
            if name.startswith('nat '):
                if self.national is None:
                    continue
                new = struct.pack('<I', self.national[int(name[4:])])
            elif not on[name]:
                continue
            used.append((name, at, old, new))
        if self.incoming:
            used.append(('incoming', INCOMING_SITE, INCOMING_SITE_OLD, INCOMING_SITE_NEW))
        return used


def prize(millions, lowest=10):
    """Millions on the screen -> stored prize."""
    return clamp(amount(millions), lowest, amount(MAX_PRIZE))


def image(t):
    d = struct.pack('<100I', *t.value) + struct.pack('<100I', *t.salary) + struct.pack('<64H', *t.age)
    d += struct.pack('<64H', *t.salary_age) + struct.pack('<16H', *t.position)
    assert len(d) == FAME_AT - CAVE
    d += struct.pack('<7I', t.fame, t.spread_low, t.spread_range, t.budget_transfer or 200, t.budget_salary or 200,
                     100, 1000) + MARK
    pieces = [(at, globals()[name]) for at, _, name in ROUTINES]
    pieces += [(LEAGUE1_TAB, struct.pack('<23I', *t.league)), (LEAGUE2_TAB, struct.pack('<25I', *t.league_2)),
               (RANK_STEP_AT, struct.pack('<d', t.rank_step)),
               (SHARE_AT, struct.pack('<2I', t.prize_share or 0, 100 if t.bonus is None else t.bonus)),
               (CUP_TAB, b''.join(struct.pack('<3I', *r) for r in t.cup_rows)),
               (TALENT_TAB, bytes(t.talent)),
               (TALENT_STEP_AT, struct.pack('<4I', t.talent_step, t.talent_max, t.talent_cap, t.income or 100)),
               (LEAGUE_IDS_AT, struct.pack('<%dH' % len(t.league_rows), *[i for i, _ in t.league_rows])),
               (LEAGUE_COUNT_AT, struct.pack('<2I', len(t.league_rows), t.income_wages or 0)),
               (LEAGUE_ROWS_TAB, b''.join(struct.pack('<%dH' % LEAGUE_ROW_WORDS, *w) for _, w in t.league_rows))]
    for at, piece in sorted(pieces):
        assert len(d) <= at - CAVE, hex(at)
        d = d.ljust(at - CAVE, b'\0') + piece
    assert len(d) <= CAVE_SIZE
    return d.ljust(CAVE_SIZE, b'\0')


def image_2(t):
    """The second piece of memory: the tables and the routine of MLTransfers.lua."""
    d = struct.pack('<%dI' % LEVELS, *t.ceiling) + bytes(t.ceiling_top)
    d = d.ljust(STRETCH_AT - CAVE_2, b'\0') + struct.pack(
        '<12I', t.ceiling_stretch, t.ceiling_need, t.ceiling_free, t.ceiling_listed, t.persona_low, t.persona_range,
        t.strength_a, t.strength_b, t.winter, t.squad, int(t.sell), len(t.hand))
    assert CAVE_2 + len(d) == RANGE_LOW_TAB and RANGE_TOP_TAB == RANGE_LOW_TAB + LEVELS
    d = (d + bytes(WINDOW_LOW) + bytes(WINDOW_TOP)).ljust(BY_LEVEL_TAB - CAVE_2, b'\0')
    d += b''.join(bytes(row) for row in t.by_level)
    assert CAVE_2 + len(d) == GENES_TAB
    d = (d + b''.join(t.genes)).ljust(HAND_TYPES - CAVE_2, b'\0')
    d = (d + bytes(index for _, index in t.hand)).ljust(HAND_IDS - CAVE_2, b'\0')
    d = (d + struct.pack('<%dI' % len(t.hand), *[club for club, _ in t.hand])).ljust(RIVAL_COUNT_AT - CAVE_2, b'\0')
    d += struct.pack('<I%dI' % (2 * len(t.rivals)), len(t.rivals), *[club for pair in t.rivals for club in pair])
    assert CAVE_2 + len(d) <= RIVAL_PAIRS + 8 * RIVALS <= CEILING_CODE
    d = d.ljust(CEILING_CODE - CAVE_2, b'\0')
    d += CEILING_BYTES
    assert CAVE_2 + len(d) <= FAME_KNOWN_AT and AGE_SHIFT_AT + 4 == CAVE_2 + CAVE_2_SIZE
    d = d.ljust(FAME_KNOWN_AT - CAVE_2, b'\0')
    # the routine compares the dword at +0xb4 of the player, moved 9 bits up (its popularity then stands in
    # the 12 highest bits), with this number: no such dword reaches 0xffffffff
    return d + struct.pack('<7I', min(t.known_fame << 20, M32), t.strict_free, t.keep_from, t.keep_step,
                           t.keep_bigger, t.known, t.age_shift)


def image_3(t):
    """The third piece of memory: the two numbers and the two routines of the position need."""
    d = struct.pack('<2I', t.need_gap, t.need_more).ljust(NEED_PLAN_CODE - CAVE_3, b'\0') + NEED_PLAN_BYTES
    assert CAVE_3 + len(d) <= NEED_PICK_CODE
    d = d.ljust(NEED_PICK_CODE - CAVE_3, b'\0') + NEED_PICK_BYTES
    assert len(d) <= CAVE_3_SIZE
    return d.ljust(CAVE_3_SIZE, b'\0')


def need_slot(t, eleven, slots, kind=0):
    """The slot a club gets for its weakest position. eleven: the first entries of its lineup
    list, (rating, position) or None for a place without a player; slots: the position each
    of the 16 slots of its plan looks for (NO_POSITION: none); kind: of the plan.
    -> None, or (slot, position, the overall its search starts above)."""
    have = [e for e in eleven[:ELEVEN] if e is not None]
    if t is None or not t.need or kind > 1 or len(eleven) < ELEVEN or len(have) < 2:
        return None
    rating, position = min(have, key=lambda e: e[0])         # the first of equals
    if sum(r for r, _ in have) - rating < (len(have) - 1) * (rating + t.need_gap):
        return None
    if position in slots or NO_POSITION not in slots:
        return None
    return slots.index(NO_POSITION), position, min(rating + t.need_more, 99)


def need_lowest(lowest, position, mark):
    """The overall ai_pick_candidate looks above: `lowest` as handed in, raised for the
    position of the need slot. mark: the two bytes at PLAN_NEED_AT of the club's plan."""
    return max(lowest, mark[1]) if mark[0] == position + 1 else lowest


def spread_hash(id_low, id_high):
    """The byte the fee routine makes from a player's id."""
    x = (id_low & 0xffff) ^ (id_high * HASH_A & 0xffffffff)
    return (x * HASH_B & 0xffffffff) >> 24


def value(t, rating, age, popularity, position=5, player=(0, 0)):
    """What the fee routine leaves in edi: the player's value before a handed-in figure,
    the random change and the game's limit."""
    rating = min(rating, 99)
    x = t.value[rating] * t.age[age] // 100
    percent_more = min(max(0, rating - t.talent[age]) * t.talent_step, t.talent_max)
    x += min(x * percent_more // 100, t.talent_cap)
    x = x * t.position[position] // 100
    x = min(CAP, x * (t.spread_low + (spread_hash(*player) * t.spread_range >> 8)) // 1000)
    return x + x * (popularity * t.fame) // 100000


def level_of_place(place):
    """The club level 0 to 9 the game gives a place of its club ranking."""
    for level, (first, last) in zip(range(LEVELS - 1, -1, -1), LEVEL_PLACES):
        if last is None or place <= last:
            return level


M32 = 0xffffffff


def high_byte(x, factor):
    """One byte from a key: the last step of every draw of MLTransfers.lua."""
    return ((x & M32) * factor & M32) >> 24


def draw(x, factor):
    """The same as a number from 0 to 99."""
    return high_byte(x, factor) * 100 >> 8


def player_key(player):
    return (player[0] & 0xffff) ^ (player[1] * HASH_A & M32)


def club_key(club):
    return club * HASH_B & M32


def stretch_hash(player, club):
    """The byte the routine makes from a player's id and the buying club's id."""
    return high_byte(player_key(player) ^ club_key(club), HASH_C)


def muldiv(a, b, c):
    """a x b / c as the routine works it out: the largest number if it does not fit 32 bits."""
    return min(a * b // c, M32)


def gene(t, record, i, club):
    """Entry i (GENE_NAMES) of a persona as the club with this id has it: the number of the
    persona, up to PERSONA_SPREAD percent lower or higher by a draw from club and entry."""
    h = high_byte((i * HASH_A & M32) ^ club_key(club), HASH_C)
    return record[i] * (t.persona_low + (h * t.persona_range >> 8)) // 1000


def persona_index(t, club, level):
    """Which persona a club has: the one CLUBS names for it (the last entry counts), else
    one of the eight of its level (the level of its record in the club ranking; for a club
    that is not in the ranking the game's own search gives the first record, and so does
    the routine)."""
    named = [index for c, index in t.hand if c == club]
    return named[-1] if named else t.by_level[min(level, LEVELS - 1)][club_key(club) >> 29]


def persona(t, club, level):
    return t.genes[persona_index(t, club, level)]


def eleven(t, points, level):
    """The rating a club's first eleven is taken to have: from its ranking points, kept
    inside the rating range the game gives its level."""
    level = min(level, LEVELS - 1)
    return clamp(((points * t.strength_a + t.strength_b) & M32) >> 16, WINDOW_LOW[level], WINDOW_TOP[level])


def limit(t, level, player=(0, 0), club=0, need=False, numbers=None, popularity=0):
    """The most a computer club of this level counts as affordable for this player.
    need: its second search, a slot that asks for a status band, or too small a squad;
    numbers: the club's persona as it has it (gene() of every entry; None: persona 0)."""
    g = dict(zip(GENE_NAMES, numbers or NEUTRAL))
    x = muldiv(t.ceiling[level], g['wealth'], 100)
    if need:
        x = muldiv(x, (muldiv(t.ceiling_need, g['panic'], 100) + 100) & M32, 100)
        if getattr(t, 'sporting_projects', False) and club in getattr(t, 'project_clubs', ()):
            x = muldiv(x, 100 + getattr(t, 'project_boost', PROJECT_CEILING_BOOST), 100)
    stretch = muldiv(t.ceiling_stretch, g['premium'], 100)
    x = min(x + muldiv(x, stretch_hash(player, club) * stretch & M32, 25600), M32)
    return min(x + muldiv(x, popularity * g['fame'] & M32, 100000), M32)


def career_hash(user_club, ranking, leagues=None):
    """Deterministic 32-bit FNV-1a hash over invariant career state (user club, ranking table).
    Stable across reloads and save-switches; distinct across different careers."""
    seed = 0x811C9DC5
    if user_club:
        seed = ((seed ^ (user_club & 0xffffffff)) * 0x01000193) & 0xffffffff
    if isinstance(ranking, dict):
        rows = sorted(ranking.values(), key=lambda r: r.get('place', 0))
    else:
        rows = ranking
    for r in rows[:15]:
        cid = r.get('id', 0) if isinstance(r, dict) else r[0]
        place = r.get('place', 0) if isinstance(r, dict) else r[1]
        pts = r.get('points', 0) if isinstance(r, dict) else r[2]
        seed = ((seed ^ (cid & 0xffffffff)) * 0x01000193) & 0xffffffff
        seed = ((seed ^ (place & 0xffff)) * 0x01000193) & 0xffffffff
        seed = ((seed ^ (pts & 0xffff)) * 0x01000193) & 0xffffffff
    return seed & 0xffffffff


def qualifying_clubs(ranking, in_top_five, user_club=None, rank_max=PROJECT_RANK_MAX,
                     allowed_leagues=TOP_FIVE_LEAGUES):
    """The AI clubs eligible for Sporting Projects:
    In global loaded-career ranks 1 to rank_max, belonging to top five first divisions,
    excluding the user's own club. Sorted by place."""
    if isinstance(ranking, dict):
        rows = sorted(ranking.values(), key=lambda r: r.get('place', 0))
    else:
        rows = ranking
    allowed = set(allowed_leagues)
    out = []
    for r in rows:
        cid = r.get('id') if isinstance(r, dict) else r[0]
        place = r.get('place') if isinstance(r, dict) else r[1]
        if 1 <= place <= rank_max and cid != user_club:
            if isinstance(in_top_five, (set, list, tuple)):
                if cid in in_top_five:
                    out.append(cid)
            elif isinstance(in_top_five, dict):
                if in_top_five.get(cid) in allowed:
                    out.append(cid)
    return out


def draw_projects(qualifying_clubs, seed, count=PROJECT_COUNT):
    """Deterministically select up to `count` distinct clubs from `qualifying_clubs` using
    a stable career `seed`.
    If fewer than `count` qualify, return all qualifying clubs (never backfill)."""
    if len(qualifying_clubs) <= count:
        return list(qualifying_clubs)
    pool = list(qualifying_clubs)
    chosen = []
    s = seed & 0xffffffff
    for _ in range(count):
        s = (s * 1103515245 + 12345) & 0x7fffffff
        idx = s % len(pool)
        chosen.append(pool.pop(idx))
    return chosen


def project_limit(t, level, player=(0, 0), club=0, need=False, numbers=None, popularity=0):
    """Recruitment ceiling limit with Sporting Project rebuild assistance."""
    return limit(t, level, player, club, need, numbers, popularity)


def age_shift(t, club):
    """By how many years the ages of its persona are moved for this club: -AGE_SHIFT to AGE_SHIFT."""
    return (high_byte(club_key(club), HASH_SHIFT) * (2 * t.age_shift + 1) >> 8) - t.age_shift


def image_5(t):
    """The fifth piece of memory: the numbers and the routine of SQUAD_PRESSURE."""
    d = struct.pack('<I', t.pressure_drop) + bytes(t.pressure_limits) + bytes(GROUP_OF)
    assert CAVE_5 + len(d) <= PRESSURE_CODE and len(t.pressure_limits) == len(GROUPS) and len(GROUP_OF) == len(POSITIONS)
    d = d.ljust(PRESSURE_CODE - CAVE_5, b'\0') + PRESSURE_BYTES
    assert len(d) <= CAVE_5_SIZE
    return d.ljust(CAVE_5_SIZE, b'\0')


def pressed_keeps(t, keeps, position, groups):
    """SQUAD_PRESSURE: `keeps` of a club for one of its players, lower by the drop (not
    below 0) if the club has more players of his group than the limit of that group.
    position: the one he is registered for; groups: how many players of its squad are of
    each group of GROUPS (None: not known, nothing changes)."""
    if t.pressure_drop and groups and position < len(POSITIONS):
        group = GROUP_OF[position]
        if groups[group] > t.pressure_limits[group]:
            return max(0, keeps - t.pressure_drop)
    return keeps


def accepts(t, level, player, buyer=None, search=None, from_pick=True):
    """Does a computer club take the player as a candidate (after all the game's own
    tests)? The routine of MLTransfers.lua, step by step.

    level: of the buying club, as ai_pick_candidate has it (the plan record).
    player: dict with rating, age, popularity, position, id (two parts) and, if not 0 or
    False, status (+0xb4 bits 0-3), listed (mark 29 or 30), band (his status band), club
    (None: the game's "no club"; else a dict with id, level and points of its ranking
    record and count, the players the pool counts for it; for SQUAD_PRESSURE also groups,
    how many players of its squad are of each group of GROUPS, those in a deal left out).
    buyer: dict with id, level and points (its ranking record), count (as above).
    search: dict with wide (the second search, among all players), first (the first of the
    two calls of ai_candidates: the set of players without a contract and of those who
    have outgrown their club), band (the status band the slot asks for), kind (of the
    plan), position (asked for), date (year, month).
    Without a part of MLTransfers.lua on, with a level outside 0 to 9, or when the choosing
    code was not entered from ai_pick_candidate: always."""
    if t is None or not t.transfers or not from_pick or not 0 <= level < LEVELS:
        return True
    buyer = buyer or dict(id=0, level=level, points=0, count=99)
    search = dict(dict(wide=False, first=False, band=0, kind=0, position=13, date=(0, 0)), **(search or {}))
    status, wide = player.get('status', 0), search['wide']
    where = 0 if status in (1, 2) else 1 if player.get('listed') else 2
    key = player_key(player['id'])
    both = key ^ club_key(buyer['id'])
    year, month = search['date']
    date = (year | month << 16) * HASH_A & M32
    turn = (search['position'] * HASH_POSITION & M32) ^ club_key(buyer['id']) ^ date
    mine = persona(t, buyer['id'], buyer['level'])
    numbers = [gene(t, mine, i, buyer['id']) for i in range(GENES)]
    g = dict(zip(GENE_NAMES, numbers))
    own = eleven(t, buyer['points'], buyer['level'])
    # 1. the selling club: the rule by which ai_pick_candidate lets a player with a contract go
    #    (a player it would refuse must not take one of the three places), then what the club keeps
    seller = player.get('club')
    # 0. rivals: a club does not sell to its rival. A player without a contract goes where he likes
    if where != 0 and seller is not None and ((buyer['id'], seller['id']) in t.rivals
                                              or (seller['id'], buyer['id']) in t.rivals):
        return False
    if where == 2 and seller is not None:
        if t.sell:
            if seller['count'] is None or seller['count'] <= POOL_KEEPS:
                return False
            if not search['first']:
                band = player.get('band', 0)
                wanted = level >= 8 or (search['kind'] == 4 and level > band)
                if not wanted and (band >= 7 or seller['level'] >= 8):
                    return False
        keeps = gene(t, persona(t, seller['id'], seller['level']), GENE_NAMES.index('keeps'), seller['id'])
        # its first team it keeps more often, the better the player; not against a clearly bigger club
        his = eleven(t, seller['points'], seller['level'])
        if own - his < t.keep_bigger and player['rating'] + t.keep_from > his:
            keeps += (player['rating'] + t.keep_from - his) * t.keep_step
        keeps = pressed_keeps(t, keeps, player['position'], seller.get('groups'))
        if draw(club_key(seller['id']) ^ key ^ date, HASH_KEEPS) < keeps:
            return False
    # 2. scouting: a club knows a part of the players; a listed player, a good one and a famous one are
    #    known to all
    if (where != 1 and player['rating'] < t.known and player['popularity'] < t.known_fame
            and draw(both, HASH_KNOWS) >= g['knows']):
        return False
    # 3. the player: he does not join a club too far below him
    if player['rating'] > own + g['prestige']:
        return False
    # 4. where the club looks. A slot that asks for a band looks everywhere; a club with a
    #    small squad is in need too: it always buys, in winter as well, at any age
    need = bool(search['band']) or (buyer['count'] is not None and buyer['count'] < t.squad)
    if not search['band'] and mine[THEN_1] != NO_CHANNELS:
        d = draw(turn, HASH_C)
        first = (0 if d < g['free'] else 1 if d < g['free'] + g['listed']
                 else 2 if d < g['free'] + g['listed'] + g['clubs'] else None)
        if first is None:                                    # it does not buy for this position this time
            if not need:
                return False
            first = mine[THEN_1]
        if not need and month == t.winter and draw(turn, HASH_WINTER) >= g['winter']:
            return False
        if wide:                                             # the second search: the next place it looks in
            first = mine[THEN_1] if mine[THEN_1] != first else mine[THEN_2]
        if first != where:
            return False
    # the ages: for a player without a contract `strict` counts in part only
    strict = g['strict'] * (t.strict_free if where == 0 else 100)
    if (not need and not mine[AGE_FROM] <= player['age'] - age_shift(t, buyer['id']) <= mine[AGE_TO]
            and draw(both, HASH_AGE) * 100 < strict):
        return False
    # 5. the rating as this club sees it
    seen = player['rating'] + (high_byte(both, HASH_FOG) * (2 * g['fog'] + 1) >> 8) - g['fog']
    if not need and seen < own - g['ambition']:
        return False
    # 6. the price
    if wide and mine[KEEP_TOP_AT] and seen > t.ceiling_top[level]:
        return False
    if t.ceiling[level] == NO_CEILING:
        return True
    price = value(t, seen & M32, player['age'], player['popularity'], player['position'], player['id'])
    if where != 2:
        price = price * (t.ceiling_free, t.ceiling_listed)[where] // 100
    return price <= limit(t, level, player['id'], buyer['id'], need or wide, numbers, player['popularity'])


def candidates(t, level, lists, lowest, highest, passes=lambda p: True, most=3, buyer=None, search=None):
    """The walk of ai_candidates over one set of lists: from the highest overall asked for
    down to the lowest, each list in its order, the first `most` players who pass the
    game's tests and the routine. lists: {overall: [player, ...]}, a player being a dict
    as accepts() takes it. As the game, the walk leaves out the list of `lowest` itself."""
    out = []
    for overall in range(highest, lowest, -1):
        for p in lists.get(overall, ()):
            if passes(p) and accepts(t, level, p, buyer, search):
                out.append(p)
                if len(out) >= most:
                    return out
    return out


def offer_need(plan, position, rating):
    """Is this club short of the player's position? plan: what the chooser reads of a plan
    record, ([(position, state) of the 16 slots], (the byte +0x109, the byte +0x10a), the
    ranking points of the club, its level) or None. 1: a free slot (state 0) or one the club
    gave up (state 7) looks for his position; 2: the position need of MLTransfers.lua marked
    that position and wants someone above the rating it stands at, so this club is in want of
    him; 0: neither."""
    if not plan:
        return 0
    slots, need = plan[0], plan[1]
    for looks, state, kind in slots:
        if kind and looks == position and state in (0, 7):
            return 1
    return 2 if need[0] == position + 1 and rating > need[1] else 0


def offer_wants(t, player, buyer, plan=None, seller=None, date=(0, 0)):
    """Would this club take this player? (incoming.c wants)
    1: full pass (wants him and affords him);
    0: hard reject (rival, prestige violation, or unaffordable: price > limit);
    2: soft reject (affordable, but failed need, channel, age, ambition or scouting).
    """
    if seller is not None and ((buyer['id'], seller) in t.rivals or (seller, buyer['id']) in t.rivals):
        return 0
    level = buyer['level']
    record = persona(t, buyer['id'], level)
    numbers = [gene(t, record, i, buyer['id']) for i in range(GENES)]
    g = dict(zip(GENE_NAMES, numbers))
    own = eleven(t, buyer['points'], level)
    if player['rating'] > own + g['prestige']:                  # he does not join a club far below him
        return 0
    day, year = date
    stamp = (year | day << 16) * HASH_A & M32
    both = player_key(player['id']) ^ club_key(buyer['id']) ^ stamp
    turn = (player['position'] * HASH_POSITION & M32) ^ both ^ player_key(player['id'])
    soft = False

    need = offer_need(plan, player['position'], player['rating'])
    if not need and player['rating'] + g['ambition'] >= own:
        need = 1
    status = player.get('status', 0) & 0xf
    where = 0 if status in (1, 2) else 1 if player.get('listed') else 2
    # scouting: a listed player, a good one and a famous one are known to every club
    if (where != 1 and player['rating'] < t.known and player['popularity'] < t.known_fame
            and draw(both, HASH_KNOWS) >= g['knows']):
        soft = True
    # where it looks for a player of that position this time
    if record[THEN_1] != NO_CHANNELS:
        d = draw(turn, HASH_C)
        if d < g['free']:
            first = 0
        elif d < g['free'] + g['listed']:
            first = 1
        elif d < g['free'] + g['listed'] + g['clubs']:
            first = 2
        elif need == 2:
            first = record[THEN_1]
        else:
            soft = True
            first = -1
        if first != where:
            soft = True
    if not need:                                                # it buys for that position at all
        soft = True
    age = player['age'] - age_shift(t, buyer['id'])
    if need != 2 and not record[AGE_FROM] <= age <= record[AGE_TO]:
        strict = g['strict'] * (t.strict_free if where == 0 else 100)
        if draw(both, HASH_AGE) * 100 < strict:
            soft = True
    seen = player['rating'] + (high_byte(both, HASH_FOG) * (2 * g['fog'] + 1) >> 8) - g['fog']
    if need != 2 and seen + g['ambition'] < own:                # as this club sees him
        soft = True
    if t.ceiling[min(level, LEVELS - 1)] == NO_CEILING:
        return 2 if soft else 1
    price = value(t, seen & M32, player['age'], player['popularity'], player['position'], player['id'])
    if where != 2:
        price = muldiv(price, (t.ceiling_free, t.ceiling_listed)[where], 100)
    lim = limit(t, min(level, LEVELS - 1), player['id'], buyer['id'], need == 2, numbers,
                player['popularity'])
    if price > lim:
        return 0
    return 2 if soft else 1


def offer_pick(t, key, player, clubs, seller, date=(0, 0)):
    """The club the chooser of the offers for the user's players answers, 0 when the game's
    own answer stands. clubs: [(id, slot, flagged, plan)] in the order of the game's club
    table; slot: [club + 0x314] >> 7 and 0xff; flagged: [club + 0x31e] & 7 == 1, a club the
    game skips; plan: as offer_need() takes it; date: as offer_wants() takes it. The game's
    own answer (the club whose slot is the key) stands when it passes; else the club whose
    slot is nearest among those that pass; else the game's own answer when it can afford him;
    else the user's club (seller) to abort the offer so no insolvent club bids."""
    def buyer(club, plan):
        return dict(id=club, level=plan[3] if plan else 0, points=plan[2] if plan else 0)

    game = 0
    for club, slot, flagged, plan in clubs:
        if not club or club == seller or flagged:
            continue
        if slot == key:
            game = (club, plan)
            break
    game_w = offer_wants(t, player, buyer(game[0], game[1]), game[1], seller, date) if game else 0
    if game_w == 1:
        return 0
    best, best_slot = 0, 0x100
    for club, slot, flagged, plan in clubs:
        if not club or club == seller or flagged:
            continue
        if offer_wants(t, player, buyer(club, plan), plan, seller, date) != 1:
            continue
        if abs(slot - key) < best_slot:
            best, best_slot = club, abs(slot - key)
    if best:
        return best
    if game_w == 2:
        return 0
    return seller


def fee(t, rating, age, popularity, position=5, player=(0, 0), base=0, percent=0, keep=False):
    """The transfer fee with MLMoney.lua in place (stored amount; the screen shows 100 times it).
    position: 0 GK ... 12 CF (the edit file's order); player: the two parts of the player's id;
    base, percent, keep: as in ../tools/money.py fee()."""
    x = value(t, rating, age, popularity, position, player)
    if keep:
        x = base
    if percent:
        x += int(x * f32(percent / 100.0))
    return max(1, min(CAP, x))


def salary(t, rating, age, popularity, role_bonus=0, rank=300, band_bonus=0, awards=0):
    """The yearly salary with MLMoney.lua in place. role_bonus: R of MASTER_LEAGUE.md 6.1;
    band_bonus: T (with its 20 * field 0x20); awards: the sum of the award bonuses."""
    x = popularity
    if popularity > 800:
        x += (5 * popularity - 4000) * 2
    if popularity > 1800:
        x += (5 * popularity - 9000) * 4
    f = f32(1.0) if rank > 250 else f32((251 - rank) * t.rank_step + 1.0)
    if t.has_salary:
        part = t.salary[min(rating, 99)] * t.salary_age[age] // 100
    else:                                           # the game's own A + B
        part = 30 * rating - 500 + 300 * max(0, rating - 65) + 500 * max(0, rating - 75) + 700 * max(0, rating - 85)
    if t.bonus is not None:
        role_bonus = role_bonus * t.bonus // 100
        awards, band_bonus = (awards + band_bonus) * t.bonus // 100, 0
    return max(1, min(CAP, awards + band_bonus + int((role_bonus + x + part) * f)))


def cup_prize(t, competition, stage):
    """What cup_prize (fcn_038aa307) gives in Master League. t = None: the game's own."""
    if competition in CUP_NONE or stage == 11:
        return 0
    for c, s, a in (t.cup_rows if t is not None and t.has_cup else GAME_CUP_ROWS):
        if (c, s) == (competition, stage):
            if a:
                return a
            break
    if t is not None and t.national is not None:
        for amount_, stages in zip(t.national, NATIONAL_STAGES):
            if stage in stages:
                return amount_
    return CUP_FALLBACK.get(stage, 0)


def league_prize(t, league, division, place, half=0):
    """What league_prize (fcn_038a9ebb) gives. league: the number of the club's league
    (60 and 61 have lists of their own); division: the two top bits of the league record's
    +0x218 (0, 1: the first list, 2, 3: the second); place: 1 = first; half: 0, or 1 or 2
    for a league played in two halves. t = None: the game's own."""
    league &= 0xffff                                # the game keeps 16 bits of the number
    if half == 1 and league not in (0x3458, 0x27d8) or half == 2 and league not in (0x3459, 0x27d9):
        return 0
    if league in (60, 61):
        amounts = GAME_LEAGUE[league]
    elif division < 2:
        amounts = t.league if t is not None and t.has_league else GAME_LEAGUE['first']
        for league_id, words in (t.league_rows if t is not None else ()):
            if league_id == league:
                amounts = [w * LEAGUE_UNIT for w in words[:LEAGUE1_PLACES + 1]]
                break
    else:
        amounts = t.league_2 if t is not None and t.has_league_2 else GAME_LEAGUE['second']
    a = amounts[place] if 0 <= place < len(amounts) else 0
    return a // 2 if half else a


def prize_paid(t, amount, mode=MASTER_LEAGUE):
    """What a prize adds to (balance, transfer budget)."""
    limit = lambda v: clamp(v, -99999999, 99999999)
    share = t.prize_share if t is not None and t.prize_share is not None and mode == MASTER_LEAGUE else 0
    part = abs(amount) * share // 100               # the division drops the remainder
    return limit(amount), limit(part if amount >= 0 else -part)


def scaled_income(t, v):
    """An amount of yearly income as the module leaves it (amounts of 0 and below are not scaled)."""
    return v if t is None or t.income is None or v <= 0 else v * t.income // 100


def season_income(t, popularity, field, wage_bill=0):
    """season_income (fcn_038ade76): popularity = club_popularity, field = the dword at +4 of
    the club's record in the ranking, wage_bill = what fcn_038ad7a8 gives for the club (the
    game works it out in this function and does not use it). t = None: the game's own."""
    v = scaled_income(t, 25 * max(150000, popularity) - 670 * min(400, field) - 3451330)
    if t is not None and t.income_wages is not None:
        v = (v + wage_bill * t.income_wages // 100 + 2 ** 31) % 2 ** 32 - 2 ** 31     # 32 bits, as the code adds
    return v if v > 0 else 1000


def rank_income(t, rank):
    """fcn_038a9e6b: the yearly amount by the club's place in the ranking."""
    v = scaled_income(t, (403 - rank) * 5000)
    return v if v > 0 else 1000


def career_income(t, level):
    """club_money_setup: the same kind of amount when a career starts, by club level 0-9,
    before the random change of -10 to +10 percent."""
    return scaled_income(t, 165000 * level + 15000)


JUNE_28, JUNE_30 = 0.6000000238418579, 0.4000000059604645        # the doubles at 0x01f0a0a0 and 0x01f0a780
GRANT_A, GRANT_B = (0.00699999975040555, 0.10000000149011612), (0.00215000007301569, 0.07000000029802322)
GRANT_LOW, GRANT_LOWEST = 0.05000000074505806, 0.019999999552965164


def june_grants(day, grade, rank, wage_bill, top_fees, salary_budget=None, extras=(0.0, 0.0)):
    """What the yearly budget step (fcn_03640d19) works out on its two days:
    (salary budget grant, transfer budget grant). day: 28 or 30 (June); grade: 1 to 6 as
    the step numbers it on that day; rank: the club's place, 1 to 200; top_fees: the sum
    top_fees_sum gives for 10 players. The two days differ in three things. The constant
    (0.6 and 0.4). The grades (30 June has no grant for grades 3 and 4). And the transfer
    grant: on 28 June it is taken from the salary grant and the wage bill; on 30 June the
    salary grant first gets two extras (`extras`, two fractions the step works out
    before; this model takes them as given) and is then set against `salary_budget`, the
    salary budget of the account, not against the wage bill. The game's own numbers; the
    module changes none of this."""
    k = JUNE_28 if day == 28 else JUNE_30
    by_rank = {28: {1: GRANT_A, 3: GRANT_B}, 30: {1: GRANT_A, 2: GRANT_B}}[day]
    flat = {28: {2: GRANT_B[1], 4: GRANT_LOW, 5: GRANT_LOW, 6: GRANT_LOWEST}, 30: {5: GRANT_LOW, 6: GRANT_LOWEST}}[day]
    if grade in by_rank:
        a, b = by_rank[grade]
        s = int((rank * a + b) * wage_bill * k)
    elif grade in flat:
        s = int(wage_bill * flat[grade] * k)
    else:
        s = 0
    against = wage_bill
    if day != 28:
        for extra in extras:
            s += int(s * f32(extra))
        against = wage_bill if salary_budget is None else salary_budget
    t = int(top_fees * f32((s + against) / against) / 5.0 * k)
    return s, t


def young_years(t, age):
    """The limit of contract years by age (fcn_03887f5d)."""
    if age >= 35:
        return 1
    if age >= 32:
        return 2
    if age <= 23:
        return 3 if t is None or t.young_years is None else t.young_years
    return 5


def budgets(t, fees, salaries, wage_bill):
    """What fcn_038ad9c4 adds to the transfer budget and to the salary budget of the
    user's club. fees, salaries: of every player of the squad. t = None: the game's own."""
    def mean(amounts):
        return (sum(sorted(amounts, reverse=True)[:16]) or 10000) // 16
    bt = 200 if t is None or t.budget_transfer is None else t.budget_transfer
    bs = 200 if t is None or t.budget_salary is None else t.budget_salary
    limit = lambda v: clamp(v, -99999999, 99999999)
    return limit(mean(fees) * bt // 100), limit(wage_bill + mean(salaries) * bs // 100)


# INCOMING_SOURCE. Entered at fcn_0381e2eb in the place of its prologue: the look-up the
# offer creator (fcn_03652df0) asks for the buying club, a byte of the mode data turned into
# a club id. Only the key 0x02100a66 is touched; every other call runs the game's own code.
# The entry below hands the mode data, the frame of the caller and the slot to pick(), which
# is the routine of incoming.c (assembled by offer_source.py): it answers 0 when the game's
# own answer stands, else the club to answer with (the club nearest to the game's own slot
# among those that would take the player: no rival, its persona wants him, its plan has a
# place for him, and it can afford him). All registers and flags are left as they were.
INCOMING_STUB_SOURCE = f'''
    pushfd
    pushad
    mov  eax, dword ptr [esp + 0x2c]
    cmp  eax, {INCOMING_KEY:#x}
    jne  original
    mov  eax, dword ptr [esp + 0x18]
    test eax, eax
    jz   original
    movzx ecx, byte ptr [{INCOMING_KEY:#x}]
    mov  edx, dword ptr [esp + 0x08]
    push ecx
    push edx
    push eax
    call pick
    add  esp, 0xc
    test eax, eax
    jz   original
    mov  edx, dword ptr [esp + 0x28]
    mov  dword ptr [edx], eax
    mov  eax, edx
    popad
    popfd
    ret  0xc

original:
    popad
    popfd
    push ebp
    mov  ebp, esp
    sub  esp, 0x14
    jmp  {INCOMING_BACK:#x}

'''
# What gcc makes of incoming.c (offer_source.py), cleaned of its directives: the three
# thunks that enter the game's own routines, muldiv, the tables, the rules and pick().
INCOMING_BODY_SOURCE = '''value_oracle:
    push ebp
    push ebx
    push edi
    sub esp, 0x20
    mov ebp, esp
    mov ebx, [ebp + 0x30]
    mov eax, [ebp + 0x34]
    call 0x047b0c90
    mov eax, edi
    add esp, 0x20
    pop edi
    pop ebx
    pop ebp
    ret
rating_oracle:
    push esi
    push edi
    mov eax, [esp + 0xc]
    mov ecx, [esp + 0x10]
    mov dword ptr [ecx], 13
    push 2
    push ecx
    push eax
    call 0x03853b42
    add esp, 12
    movzx eax, al
    pop edi
    pop esi
    ret
player_oracle:
    mov eax, [esp + 4]
    mov edx, [esp + 8]
    mov ecx, [esp + 0xc]
    push edx
    push eax
    call 0x03822835
    ret
muldiv:
	push	ebp
	mov	ebp, esp
	sub	esp, 28
	mov	DWORD PTR [ebp-20], eax
	mov	DWORD PTR [ebp-24], edx
	mov	DWORD PTR [ebp-28], ecx
	mov eax, DWORD PTR [ebp-20]
	mul DWORD PTR [ebp-24]
	cmp edx, DWORD PTR [ebp-28]
	jae muldiv_over11
	div DWORD PTR [ebp-28]
	jmp muldiv_done11
muldiv_over11:
	mov eax, -1
muldiv_done11:
	mov DWORD PTR [ebp-4], eax
	mov	eax, DWORD PTR [ebp-4]
	leave
	ret
wants:
	push	ebp
	mov	ebp, esp
	push	edi
	push	esi
	mov	esi, eax
	push	ebx
	sub	esp, 140
	mov	eax, DWORD PTR [edx]
	mov	edx, DWORD PTR [38926428]
	mov	DWORD PTR [ebp-108], ecx
	mov	ecx, 64
	mov	DWORD PTR [ebp-112], eax
	mov	eax, DWORD PTR [75319240]
	cmp	eax, ecx
	cmova	eax, ecx
	lea	edi, [75319244+eax*8]
	mov	eax, 75319244
L4:
	cmp	edi, eax
	je	L100
	mov	ebx, DWORD PTR [eax]
	mov	ecx, DWORD PTR [eax+4]
	cmp	DWORD PTR [ebp-112], ebx
	jne	L57
	cmp	edx, ecx
	je	L5
L57:
	add	eax, 8
	cmp	edx, ebx
	jne	L4
	cmp	DWORD PTR [ebp-112], ecx
	jne	L4
	jmp	L5
L30:
	cmp	edi, 2
	jne	L53
	movzx	edx, BYTE PTR [ecx]
	cmp	eax, edx
	mov	eax, 1
	cmovne	ebx, eax
L32:
	mov	ecx, DWORD PTR [ebp-84]
	imul	eax, DWORD PTR [ebp-128], -430675099
	mov	esi, DWORD PTR [ebp-132]
	lea	edx, [ecx+ecx]
	shr	eax, 24
	inc	edx
	add	esi, 18829440
	imul	edx, eax
	mov	eax, DWORD PTR [ebp-124]
	sub	eax, ecx
	shr	edx, 8
	add	edx, eax
	cmp	edi, 2
	je	L35
	mov	eax, DWORD PTR [ebp-64]
	mov	ecx, DWORD PTR [ebp-116]
	add	eax, edx
	cmp	eax, ecx
	jnb	L35
	mov	ecx, DWORD PTR [0+esi*4]
	mov	eax, 2
	mov	ebx, 1
	inc	ecx
	je	L3
L36:
	push	eax
	push	eax
	mov	eax, DWORD PTR [ebp-108]
	push	edx
	push	DWORD PTR [eax]
	call	value_oracle
	add	esp, 16
	mov	DWORD PTR [ebp-112], eax
	mov	eax, DWORD PTR [ebp-108]
	mov	eax, DWORD PTR [eax+28]
	cmp	eax, 2
	jne	L101
L37:
	mov	eax, DWORD PTR [0+esi*4]
	mov	edx, DWORD PTR [ebp-80]
	mov	ecx, 100
	call	muldiv
	mov	esi, eax
	cmp	edi, 2
	jne	L40
	mov	edx, DWORD PTR [ebp-72]
	mov	eax, DWORD PTR [75317816]
	call	muldiv
	lea	edx, [eax+100]
	mov	eax, esi
	call	muldiv
	mov	esi, eax
L40:
	mov	eax, DWORD PTR [75317812]
	mov	edx, DWORD PTR [ebp-76]
	mov	ecx, 100
	call	muldiv
	imul	edx, DWORD PTR [ebp-128], -2048144789
	mov	ecx, 25600
	shr	edx, 24
	imul	edx, eax
	mov	eax, esi
	call	muldiv
	mov	ecx, 100000
	add	esi, eax
	mov	eax, -1
	cmovc	esi, eax
	mov	eax, DWORD PTR [ebp-108]
	mov	edx, DWORD PTR [eax+24]
	imul	edx, DWORD PTR [ebp-68]
	mov	eax, esi
	call	muldiv
	add	esi, eax
	jc	L58
	mov	eax, DWORD PTR [ebp-112]
	cmp	esi, eax
	jnb	L58
L5:
	xor	eax, eax
	jmp	L3
L100:
	mov	edx, DWORD PTR [esi+10400]
	mov	eax, 650
	lea	ebx, [esi+13403340]
	cmp	edx, eax
	cmovbe	eax, edx
	xor	ecx, ecx
	mov	DWORD PTR [ebp-120], eax
	mov	eax, ebx
L47:
	cmp	DWORD PTR [ebp-120], ecx
	je	L102
	lea	edx, [eax+16]
	mov	edi, DWORD PTR [eax]
	mov	DWORD PTR [ebp-116], edx
	cmp	DWORD PTR [ebp-112], edi
	je	L11
	inc	ecx
	mov	eax, edx
	jmp	L47
L102:
	mov	eax, ebx
L11:
	movzx	edi, WORD PTR [eax+8]
	movzx	eax, BYTE PTR [eax+14]
	mov	edx, 192
	mov	DWORD PTR [ebp-132], eax
	mov	eax, DWORD PTR [75317856]
	cmp	eax, edx
	cmova	eax, edx
L13:
	mov	edx, eax
	sub	eax, 1
	jb	L103
	mov	ecx, DWORD PTR [75318472+eax*4]
	cmp	DWORD PTR [ebp-112], ecx
	jne	L13
	movzx	eax, BYTE PTR [edx+75318279]
	jmp	L97
L103:
	mov	eax, 9
	cmp	DWORD PTR [ebp-132], eax
	cmovbe	eax, DWORD PTR [ebp-132]
	imul	edx, DWORD PTR [ebp-112], -1640531535
	shr	edx, 29
	lea	eax, [edx+75317880+eax*8]
	movzx	eax, BYTE PTR [eax]
L97:
	imul	eax, eax, 20
	xor	ebx, ebx
	add	eax, 75317960
	mov	DWORD PTR [ebp-120], eax
	imul	eax, DWORD PTR [ebp-112], -1640531535
	mov	DWORD PTR [ebp-128], eax
L16:
	mov	eax, DWORD PTR [75317828]
	mov	ecx, DWORD PTR [75317832]
	imul	edx, ebx, 16777619
	mov	DWORD PTR [ebp-116], eax
	mov	eax, DWORD PTR [ebp-120]
	add	eax, ebx
	mov	al, BYTE PTR [eax]
	mov	BYTE PTR [ebp-124], al
	mov	eax, DWORD PTR [ebp-128]
	xor	edx, eax
	mov	eax, DWORD PTR [ebp-116]
	imul	edx, edx, -2048144789
	shr	edx, 24
	imul	edx, ecx
	mov	ecx, 1000
	shr	edx, 8
	add	edx, eax
	movzx	eax, BYTE PTR [ebp-124]
	call	muldiv
	mov	DWORD PTR [ebp-104+ebx*4], eax
	inc	ebx
	cmp	ebx, 20
	jne	L16
	mov	ecx, DWORD PTR [75317836]
	mov	eax, 9
	cmp	DWORD PTR [ebp-132], eax
	cmovbe	eax, DWORD PTR [ebp-132]
	mov	edx, DWORD PTR [75317840]
	imul	edi, ecx
	add	edi, edx
	movzx	edx, BYTE PTR [eax+75317860]
	shr	edi, 16
	mov	DWORD PTR [ebp-116], edi
	cmp	edi, edx
	jnb	L17
	movzx	edi, BYTE PTR [eax+75317860]
	mov	DWORD PTR [ebp-116], edi
L17:
	movzx	edx, BYTE PTR [eax+75317870]
	mov	edi, DWORD PTR [ebp-116]
	cmp	edx, edi
	jnb	L18
	movzx	eax, BYTE PTR [eax+75317870]
	mov	DWORD PTR [ebp-116], eax
L18:
	mov	eax, DWORD PTR [ebp-108]
	mov	eax, DWORD PTR [eax+8]
	mov	DWORD PTR [ebp-124], eax
	mov	edi, DWORD PTR [ebp-124]
	mov	eax, DWORD PTR [ebp-116]
	add	eax, DWORD PTR [ebp-60]
	cmp	eax, edi
	jb	L5
	movzx	edx, WORD PTR [esi+12766130]
	mov	edi, DWORD PTR [ebp-108]
	mov	ecx, 851
	mov	ax, WORD PTR [esi+12766128]
	mov	ebx, DWORD PTR [edi+4]
	sal	eax, 16
	or	eax, edx
	mov	edx, DWORD PTR [ebp-128]
	mov	DWORD PTR [ebp-140], ebx
	imul	eax, eax, 16777619
	xor	edx, ebx
	xor	eax, edx
	mov	edx, DWORD PTR [esi+13657140]
	mov	DWORD PTR [ebp-128], eax
	mov	eax, DWORD PTR [ebp-108]
	cmp	edx, ecx
	cmova	edx, ecx
	mov	eax, DWORD PTR [eax+12]
	imul	edx, edx, 280
	mov	DWORD PTR [ebp-136], eax
	lea	eax, [esi+13416460]
	add	edx, eax
L19:
	cmp	edx, eax
	je	L22
	mov	ebx, DWORD PTR [eax]
	lea	ecx, [eax+280]
	cmp	DWORD PTR [ebp-112], ebx
	je	L20
	mov	eax, ecx
	jmp	L19
L20:
	test	eax, eax
	je	L22
	lea	edx, [eax+16]
	lea	ebx, [eax+272]
	mov	esi, 129
L25:
	mov	ecx, DWORD PTR [edx]
	test	ecx, 4177920
	je	L23
	mov	edi, ecx
	shr	edi, 7
	and	edi, 127
	cmp	DWORD PTR [ebp-136], edi
	jne	L23
	shr	ecx, 22
	mov	edi, esi
	shr	edi, cl
	and	edi, 1
	jne	L24
L23:
	add	edx, 16
	cmp	ebx, edx
	jne	L25
	mov	esi, DWORD PTR [ebp-136]
	movzx	edx, BYTE PTR [eax+265]
	lea	ecx, [esi+1]
	cmp	edx, ecx
	jne	L22
	movzx	eax, BYTE PTR [eax+266]
	mov	esi, DWORD PTR [ebp-124]
	mov	edi, 2
	cmp	eax, esi
	jb	L24
L22:
	mov	ebx, DWORD PTR [ebp-116]
	mov	eax, DWORD PTR [ebp-124]
	add	eax, DWORD PTR [ebp-64]
	cmp	eax, ebx
	setnb	al
	movzx	eax, al
	mov	edi, eax
L24:
	mov	eax, DWORD PTR [ebp-108]
	xor	ebx, ebx
	mov	eax, DWORD PTR [eax+28]
	cmp	eax, 1
	je	L26
	mov	edx, DWORD PTR [75321336]
	cmp	DWORD PTR [ebp-124], edx
	jnb	L26
	mov	edx, DWORD PTR [75321316]
	mov	esi, DWORD PTR [ebp-108]
	shr	edx, 20
	cmp	DWORD PTR [esi+24], edx
	jnb	L26
	imul	edx, DWORD PTR [ebp-128], 374761393
	xor	ebx, ebx
	shr	edx, 24
	imul	edx, edx, 100
	shr	edx, 8
	cmp	edx, DWORD PTR [ebp-88]
	setnb	bl
L26:
	mov	esi, DWORD PTR [ebp-120]
	mov	dl, BYTE PTR [esi+16]
	lea	ecx, [esi+16]
	inc	dl
	je	L27
	imul	edx, DWORD PTR [ebp-136], -1028477387
	mov	esi, DWORD PTR [ebp-140]
	xor	edx, esi
	mov	esi, DWORD PTR [ebp-128]
	xor	edx, esi
	mov	esi, DWORD PTR [ebp-104]
	imul	edx, edx, -2048144789
	shr	edx, 24
	imul	edx, edx, 100
	shr	edx, 8
	cmp	edx, esi
	jnb	L28
	test	eax, eax
	jmp	L98
L28:
	add	esi, DWORD PTR [ebp-100]
	cmp	edx, esi
	jnb	L29
	cmp	eax, 1
	jmp	L98
L29:
	add	esi, DWORD PTR [ebp-96]
	cmp	edx, esi
	jnb	L30
	cmp	eax, 2
L98:
	mov	edx, 1
	cmovne	ebx, edx
L27:
	test	edi, edi
	je	L53
	cmp	edi, 2
	jne	L31
	jmp	L32
L53:
	mov	ebx, 1
L31:
	mov	esi, DWORD PTR [ebp-108]
	mov	edx, DWORD PTR [75321340]
	mov	ecx, DWORD PTR [75321340]
	add	ecx, DWORD PTR [esi+20]
	imul	esi, DWORD PTR [ebp-112], -551706303
	add	edx, edx
	inc	edx
	shr	esi, 24
	imul	edx, esi
	mov	esi, DWORD PTR [ebp-120]
	shr	edx, 8
	sub	ecx, edx
	movzx	edx, BYTE PTR [esi+14]
	cmp	ecx, edx
	jb	L33
	movzx	edx, BYTE PTR [esi+15]
	cmp	edx, ecx
	jnb	L32
L33:
	mov	edx, DWORD PTR [ebp-52]
	mov	ecx, 100
	test	eax, eax
	jne	L34
	mov	ecx, DWORD PTR [75321320]
L34:
	imul	eax, DWORD PTR [ebp-128], 461845907
	imul	edx, ecx
	shr	eax, 24
	imul	eax, eax, 100
	shr	eax, 8
	imul	eax, eax, 100
	cmp	eax, edx
	mov	eax, 1
	cmovb	ebx, eax
	jmp	L32
L35:
	mov	eax, DWORD PTR [0+esi*4]
	inc	eax
	jne	L36
	jmp	L58
L101:
	test	eax, eax
	jne	L38
	mov	edx, DWORD PTR [75317820]
	jmp	L39
L38:
	mov	edx, DWORD PTR [75317824]
L39:
	mov	eax, DWORD PTR [ebp-112]
	mov	ecx, 100
	call	muldiv
	mov	DWORD PTR [ebp-112], eax
	jmp	L37
L58:
	lea	eax, [ebx+1]
L3:
	lea	esp, [ebp-12]
	pop	ebx
	pop	esi
	pop	edi
	pop	ebp
	ret
pick:
	push	ebp
	mov	ebp, esp
	push	edi
	push	esi
	push	ebx
	sub	esp, 76
	cmp	DWORD PTR [ebp+8], 0
	jne	L105
L107:
	xor	esi, esi
	jmp	L104
L105:
	mov	eax, DWORD PTR [38926428]
	mov	DWORD PTR [ebp-60], eax
	dec	eax
	cmp	eax, -3
	ja	L107
	mov	eax, DWORD PTR [ebp+12]
	mov	edi, DWORD PTR [eax+8]
	test	edi, edi
	je	L107
	mov	esi, DWORD PTR [edi]
	mov	ebx, DWORD PTR [edi+4]
	push	eax
	push	DWORD PTR [ebp+8]
	push	ebx
	push	esi
	call	player_oracle
	add	esp, 16
	lea	edx, [eax-1]
	mov	DWORD PTR [ebp-56], eax
	cmp	edx, -3
	ja	L107
	mov	cx, WORD PTR [eax+44]
	movzx	edx, si
	cmp	cx, si
	jne	L107
	imul	ebx, ebx, 16777619
	xor	ebx, edx
	mov	DWORD PTR [ebp-52], ebx
	mov	edx, DWORD PTR [eax+4]
	shr	edx, 28
	mov	DWORD PTR [ebp-44], edx
	lea	edx, [ebp-40]
	push	ecx
	push	ecx
	push	edx
	push	eax
	call	rating_oracle
	mov	edx, DWORD PTR [ebp-56]
	add	esp, 16
	xor	ecx, ecx
	mov	DWORD PTR [ebp-48], eax
	mov	eax, DWORD PTR [edx+28]
	shr	eax, 7
	and	eax, 63
	mov	DWORD PTR [ebp-36], eax
	mov	eax, DWORD PTR [edx+180]
	shr	eax, 11
	and	eax, 4095
	mov	DWORD PTR [ebp-32], eax
	mov	eax, DWORD PTR [edx+180]
	and	eax, 15
	dec	eax
	cmp	eax, 1
	jbe	L108
	mov	eax, DWORD PTR [edx+184]
	and	eax, 1610612736
	neg	eax
	sbb	ecx, ecx
	add	ecx, 2
L108:
	mov	eax, DWORD PTR [ebp+8]
	mov	DWORD PTR [ebp-28], ecx
	mov	esi, DWORD PTR [eax+6286560]
	lea	eax, [esi-1]
	cmp	eax, 1023
	ja	L107
	mov	eax, DWORD PTR [ebp+8]
	xor	ecx, ecx
	lea	ebx, [eax+4725728]
	mov	edx, ebx
L111:
	mov	eax, DWORD PTR [edx]
	test	eax, eax
	je	L109
	cmp	DWORD PTR [ebp-60], eax
	je	L109
	mov	eax, DWORD PTR [edx+798]
	and	eax, 7
	dec	eax
	je	L109
	mov	eax, DWORD PTR [edx+788]
	shr	eax, 7
	movzx	eax, al
	cmp	eax, DWORD PTR [ebp+16]
	jne	L109
	mov	eax, DWORD PTR [ebp+8]
	lea	ecx, [ebp-56]
	call	wants
	mov	DWORD PTR [ebp-64], eax
	dec	eax
	je	L107
	jmp	L110
L109:
	inc	ecx
	add	edx, 1312
	cmp	esi, ecx
	jne	L111
	xor	edx, edx
	mov	DWORD PTR [ebp-64], edx
L110:
	imul	esi, esi, 1312
	mov	DWORD PTR [ebp-72], 256
	lea	eax, [esi+ebx]
	xor	esi, esi
	mov	DWORD PTR [ebp-76], eax
L117:
	mov	eax, DWORD PTR [ebx]
	mov	DWORD PTR [ebp-68], eax
	test	eax, eax
	je	L114
	cmp	DWORD PTR [ebp-60], eax
	je	L114
	mov	eax, DWORD PTR [ebx+798]
	and	eax, 7
	dec	eax
	je	L114
	mov	eax, DWORD PTR [ebp+8]
	lea	ecx, [ebp-56]
	mov	edx, ebx
	call	wants
	dec	eax
	jne	L114
	mov	eax, DWORD PTR [ebx+788]
	mov	edx, DWORD PTR [ebp+16]
	shr	eax, 7
	movzx	eax, al
	sub	edx, eax
	cmp	eax, DWORD PTR [ebp+16]
	jb	L116
	sub	eax, DWORD PTR [ebp+16]
	mov	edx, eax
L116:
	mov	eax, DWORD PTR [ebp-72]
	cmp	edx, eax
	jnb	L114
	mov	DWORD PTR [ebp-72], edx
	mov	esi, DWORD PTR [ebp-68]
L114:
	add	ebx, 1312
	cmp	DWORD PTR [ebp-76], ebx
	jne	L117
	test	esi, esi
	je	L118
	mov	eax, DWORD PTR [ebp+12]
	mov	eax, DWORD PTR [eax+12]
	test	eax, eax
	je	L104
	mov	DWORD PTR [eax], esi
	jmp	L104
L118:
	cmp	DWORD PTR [ebp-64], 2
	je	L107
	xor	eax, eax
	mov	esi, DWORD PTR [ebp-60]
	mov	DWORD PTR [edi+4], eax
L104:
	lea	esp, [ebp-12]
	mov	eax, esi
	pop	ebx
	pop	esi
	pop	edi
	pop	ebp
	ret
'''

INCOMING_SOURCE = INCOMING_STUB_SOURCE + INCOMING_BODY_SOURCE


INCOMING_BYTES = bytes.fromhex(
    '9c608b44242c3d660a1002752f8b44241885c074270fb60d660a10028b542408515250e8ea05000083c40c85c0740d8b5424'
    '28890289d0619dc20c00619d5589e583ec14e9587d04ff55535783ec2089e58b5d308b4534e8e4a6fdff89f883c4205f5b5d'
    'c356578b44240c8b4c2410c7010d0000006a025150e874d507ff83c40c0fb6c05f5ec38b4424048b5424088b4c240c5250e8'
    '4bc204ffc35589e583ec1c8945ec8955e8894de48b45ecf765e83b55e47305f775e4eb05b8ffffffff8945fc8b45fcc9c355'
    '89e5575689c65381ec8c0000008b028b155cf85102894d94b940000000894590a1c8477d0439c80f47c18d3cc5cc477d04b8'
    'cc477d0439c70f844f0100008b188b4804395d90750839ca0f843601000083c00839da75df394d9075dae92501000083ff02'
    '0f85240400000fb61139d0b8010000000f45d88b4dac694580656b54e68bb57cffffff8d1409c1e8184281c680501f010faf'
    'd08b458429c8c1ea0801c283ff020f845e0400008b45c08b4d8c01d039c80f834e0400008b0cb500000000b802000000bb01'
    '000000410f847004000050508b459452ff30e8a2feffff83c4108945908b45948b401c83f8020f85240400008b04b5000000'
    '008b55b0b964000000e8cbfeffff89c683ff0275198b55b8a138427d04e8b7feffff8d506489f0e8adfeffff89c6a134427d'
    '048b55b4b964000000e899feffff6955806bcaeb85b900640000c1ea180fafd089f0e880feffffb9a086010001c6b8ffffff'
    'ff0f42f08b45948b50180faf55bc89f0e860feffff01c60f82c40300008b459039c60f83b903000031c0e9b50300008b96a0'
    '280000b88a0200008d9ecc84cc0039c20f46c231c989458889d8394d8874128d50108b3889558c397d9074074189d0ebe989'
    'd80fb778080fb6400ebac000000089857cffffffa160427d0439d00f47c289c283e80172158b0c85c8447d04394d9075ed0f'
    'b68207447d04eb26b80900000039857cffffff0f46857cffffff695590b179379ec1ea1d8d84c278427d040fb6006bc01431'
    'db05c8427d04894588694590b179379e894580a144427d048b0d48427d0469d39301000189458c8b458801d88a008845848b'
    '458031c28b458c69d26bcaeb85c1ea180fafd1b9e8030000c1ea0801c20fb64584e855fdffff89449d984383fb1475b18b0d'
    '4c427d04b80900000039857cffffff0f46857cffffff8b1550427d040faff901d70fb69064427d04c1ef10897d8c39d7730a'
    '0fb6b864427d04897d8c0fb6906e427d048b7d8c39fa730a0fb6806e427d0489458c8b45948b40088945848b7d848b458c03'
    '45c439f80f828efeffff0fb796b2cbc2008b7d94b953030000668b86b0cbc2008b5f04c1e01009d08b5580899d74ffffff69'
    'c09301000131da31d08b963464d0008945808b459439ca0f47d18b400c69d218010000898578ffffff8d860cb8cc0001c239'
    'c274778b188d8818010000395d90740489c8ebeb85c074628d50108d9810010000be810000008b0af7c100c03f00741c89cf'
    'c1ef0783e77f39bd78ffffff750cc1e91689f7d3ef83e701754183c21039d375d38bb578ffffff0fb690090100008d4e0139'
    'ca75130fb6800a0100008b7584bf0200000039f072138b5d8c8b45840345c039d80f93c00fb6c089c78b459431db8b401c83'
    'f80174348b15f84f7d0439558473298b15e44f7d048b7594c1ea143956187318695580b167561631dbc1ea186bd264c1ea08'
    '3b55a80f93c38b75888a56108d4e10fec27453699578ffffff35aeb2c28bb574ffffff31f28b758031f28b759869d26bcaeb'
    '85c1ea186bd264c1ea0839f2730485c0eb1a03759c39f2730583f801eb0e0375a039f20f83ecfbffff83f802ba010000000f'
    '45da85ff740a83ff02750ae9e9fbffffbb010000008b75948b15fc4f7d048b0dfc4f7d04034e1469759041a11ddf01d242c1'
    'ee180fafd68b7588c1ea0829d10fb6560e39d1720c0fb6560f39ca0f83a6fbffff8b55ccb96400000085c075068b0de84f7d'
    '046945809335871b0fafd1c1e8186bc064c1e8086bc06439d0b8010000000f42d8e96ffbffff8b04b500000000400f85bcfb'
    'ffffeb2785c075088b153c427d04eb068b1540427d048b4590b964000000e89cfaffff894590e9b5fbffff8d43018d65f45b'
    '5e5f5dc35589e557565383ec4c837d0800750731f6e9b7010000a15cf851028945c44883f8fd77eb8b450c8b780885ff74e1'
    '8b378b5f0450ff75085356e837faffff83c4108d50ff8945c883fafd77c3668b482c0fb7d66639f175b769db9301000131d3'
    '895dcc8b5004c1ea1c8955d48d55d851515250e8dbf9ffff8b55c883c41031c98945d08b421cc1e80783e03f8945dc8b82b4'
    '000000c1e80b25ff0f00008945e08b82b400000083e00f4883f80176128b82b80000002500000060f7d819c983c1028b4508'
    '894de48bb0e0ec5f008d46ff3dff0300000f8734ffffff8b450831c98d98e01b480089da8b0285c074393945c474348b821e'
    '03000083e0074874288b8214030000c1e8070fb6c03b451075178b45088d4dc8e89af9ffff8945c0480f84eafeffffeb1041'
    '81c22005000039ce75b631d28955c069f620050000c745b8000100008d041e31f68945b48b038945bc85c074493945c47444'
    '8b831e03000083e0074874388b45088d4dc889dae842f9ffff4875288b83140300008b5510c1e8070fb6c029c23b45107205'
    '2b451089c28b45b839c273068955b88b75bc81c320050000395db475a385f6740e8b450c8b400c85c074168930eb12837dc0'
    '020f844afeffff31c08b75c48947048d65f489f05b5e5f5dc3'
)


assert len(INCOMING_BYTES) <= INCOMING_CAVE_SIZE and INCOMING_CODE + INCOMING_CAVE_SIZE == CAVE_5


def build():
    import keystone
    ks = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_32)
    out = {name: bytes(ks.asm(source, at)[0]) for at, source, name in ROUTINES}
    out['CEILING_BYTES'] = bytes(ks.asm(CEILING_SOURCE, CEILING_CODE)[0])
    out['NEED_PLAN_BYTES'] = bytes(ks.asm(NEED_PLAN_SOURCE, NEED_PLAN_CODE)[0])
    out['NEED_PICK_BYTES'] = bytes(ks.asm(NEED_PICK_SOURCE, NEED_PICK_CODE)[0])
    out['INCOMING_BYTES'] = bytes(ks.asm(INCOMING_SOURCE, INCOMING_CODE)[0])
    out['PRESSURE_BYTES'] = bytes(ks.asm(PRESSURE_SOURCE, PRESSURE_CODE)[0])
    return out


def context_lua(exe, name='CONTEXT', pieces=None):
    """The CONTEXT list of MLMoney.lua, from the bytes of the exe file."""
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
    from layout import load, off
    d = load(exe)
    lines = ['local %s = {' % name]
    for name, at, n in CONTEXT if pieces is None else pieces:
        h = d[off(at):off(at) + n].hex()
        parts = [h[i:i + 88] for i in range(0, len(h), 88)]
        lines.append('    { "%s", 0x%08x,' % (name, at))
        lines.append('\n'.join('      %s"%s"' % ('.. ' if i else '', p) for i, p in enumerate(parts)) + ' },')
    lines.append('}')
    return '\n'.join(lines)


def quoted(h, first, width=88):
    parts = [h[:first]] + [h[k:k + width] for k in range(first, len(h), width)]
    return '\n      .. '.join('"%s"' % x for x in parts if x)


def lua_block(exe):
    """The lines of MLMoney.lua from `local ROUTINES` to the end of CONTEXT."""
    out = 'local ROUTINES = {\n'
    for at, _, name in ROUTINES:
        out += '    { 0x%03x, %s },\n' % (at - CAVE, quoted(globals()[name].hex(), 76))
    out += ('}\n\n-- The places that are changed: name, address, bytes there now, bytes to write. (The\n'
            '-- number in "years" is YOUNG_YEARS and the amounts of the six "nat" places are\n'
            '-- CUP_NATIONAL; they are put in below.)\nlocal SITES = {\n')
    for name, at, old, new in SITES:
        if name not in TRANSFER_SITES:                       # those places belong to MLTransfers.lua
            out += '    { "%s", 0x%08x, "%s", "%s" },\n' % (name, at, old.hex(), new.hex())
    return (out + '}\n\n-- The code and data those places and the routines rely on: name, address, bytes.\n'
            + context_lua(exe) + '\n')


def lua_block_transfers(exe):
    """The lines of MLTransfers.lua from `local ROUTINE` to the end of CONTEXT."""
    (name, at, old, new), = [x for x in SITES if x[0] == 'transfers']
    star = ('-- Native transfer candidate filter sites: bypass unlisted 85+ OVR freeze\n'
            'local STAR_SITES = {\n')
    for site in SITES:
        if site[0].startswith('star '):
            star += '    { "%s", 0x%08x, "%s", "%s" },\n' % (site[0], site[1], site[2].hex(), site[3].hex())
    star += '}\n\n'
    trim = ('-- Native squad trim & mutual contract termination sites: unlock 32-player squad deadlock\n'
            'local TRIM_SITES = {\n')
    for site in SITES:
        if site[0].startswith('trim '):
            trim += '    { "%s", 0x%08x, "%s", "%s" },\n' % (site[0], site[1], site[2].hex(), site[3].hex())
    trim += '}\n\n'
    need = ('-- The position need: the two routines (offset in the third piece of memory, machine code)\n'
            '-- and the two places that are changed for it.\nlocal NEED_ROUTINES = {\n')
    for code_at, code in ((NEED_PLAN_CODE, NEED_PLAN_BYTES), (NEED_PICK_CODE, NEED_PICK_BYTES)):
        need += '    { 0x%03x, %s },\n' % (code_at - CAVE_3, quoted(code.hex(), 76))
    need += '}\nlocal NEED_SITES = {\n'
    for site in SITES:
        if site[0].startswith('need '):
            need += '    { "%s", 0x%08x, "%s", "%s" },\n' % (site[0], site[1], site[2].hex(), site[3].hex())
    need += ('}\n\n-- SQUAD_PRESSURE: its routine (offset in the fifth piece of memory, machine code)\n'
             'local PRESSURE_ROUTINE = { 0x%02x, %s }\n\n' % (PRESSURE_CODE - CAVE_5, quoted(PRESSURE_BYTES.hex(), 50)))
    out = ('local ROUTINE = { 0x%02x, %s }\n\n-- The place that is changed: name, address, bytes there now, bytes to write.\n'
           'local SITE = { "%s", 0x%08x, "%s", "%s" }\n\n' % (
               CEILING_CODE - CAVE_2, quoted(CEILING_BYTES.hex(), 60), name, at, old.hex(), new.hex()))
    out += star + trim + need + '-- What MLMoney.lua must have put into its memory: name, address, bytes.\nlocal MONEY = {\n'
    for name, at, data in MONEY_NEEDED:
        out += '    { "%s", 0x%08x,\n      %s },\n' % (name, at, quoted(data.hex(), 88))
    return (out + '}\n\n-- The code of the game the place and the routine rely on: name, address, bytes.\n'
            + context_lua(exe, 'CONTEXT', CONTEXT_CEILING) + '\n')


if __name__ == '__main__':
    if sys.argv[1:2] == ['lua']:
        print((lua_block_transfers if sys.argv[3:] == ['transfers'] else lua_block)(sys.argv[2]), end='')
        sys.exit(0)
    if sys.argv[1:] == ['build']:
        for name, code in build().items():
            assert code == globals()[name], '%s: the bytes kept in this file are not what the source assembles to: %s' % (name, code.hex())
        print('ok: the source assembles to the bytes kept in this file')
    print('memory   %08x - %08x' % (CAVE, CAVE + CAVE_SIZE - 1))
    print('memory 2 %08x - %08x (MLTransfers.lua)' % (CAVE_2, CAVE_2 + CAVE_2_SIZE - 1))
    print('memory 3 %08x - %08x (MLTransfers.lua, NEED)' % (CAVE_3, CAVE_3 + CAVE_3_SIZE - 1))
    print('memory 4 %08x - %08x (MLTransfers.lua, INCOMING)' % (INCOMING_CODE, INCOMING_CODE + len(INCOMING_BYTES) - 1))
    print('memory 5 %08x - %08x (MLTransfers.lua, SQUAD_PRESSURE)' % (CAVE_5, CAVE_5 + CAVE_5_SIZE - 1))
    for name, at, old, new in SITES:
        print('%-9s %08x: %s -> %s' % (name, at, old.hex(), new.hex()))
    for at, _, name in ROUTINES:
        print('%-15s %08x: %s' % (name, at, globals()[name].hex()))
    print('%-15s %08x: %s' % ('CEILING_BYTES', CEILING_CODE, CEILING_BYTES.hex()))
    print('%-15s %08x: %s' % ('NEED_PLAN_BYTES', NEED_PLAN_CODE, NEED_PLAN_BYTES.hex()))
    print('%-15s %08x: %s' % ('NEED_PICK_BYTES', NEED_PICK_CODE, NEED_PICK_BYTES.hex()))
    print('%-15s %08x: %s' % ('PRESSURE_BYTES', PRESSURE_CODE, PRESSURE_BYTES.hex()))
