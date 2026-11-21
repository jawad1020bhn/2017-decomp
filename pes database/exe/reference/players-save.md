# Team strength, development and saves

[Master League guide](../MASTER_LEAGUE.md) · Section numbers are the original research citations. Paths in the notes are relative to `pes database/exe` unless a command changes directory.

## 10 Team strength

Level: **read**.

`team_strength_of` (`fcn_03865b0a(&club, &kind, …)`, 34 callers) collects one value
per player of the squad (up to 32) and hands them to `team_strength`
(`fcn_04067cfa`):

```
sort the values, highest first
s = sum of the first 11
kind 6 (overall):  s / 11, limited to 40 … 99
other kinds:       s / 11 (rounded up in one mode), limited to 1 … 9, times 10
```

For kind 6 the value of a player is his overall rating at his best position with the
condition arrow (`fcn_03838c18`, the rating code of `NOTES.md`); for the other kinds
`fcn_03865a43(player, kind) / 10`. So a club's strength is the **mean rating of its
eleven best players**, whatever their positions.

## 11 Team roles

Level: **read** in part.

The role of a player is the byte at `+0xc4` (1 to 22; 0 and 23 = none) with a level 1
to 3 in `+0xb8`. Table `0x0216f85c` has one row of `0x14` bytes per role: three effect
numbers (10 = none) and a kind (appendix E). `role_effects` (`fcn_038ba942`) lists the
effects of a role.

`role_multiplier` (`fcn_038bb0f0(club)`) returns a factor for a club, starting at 1.0.
For one player of the squad (the index is the byte `+0x271` of a second club
record, taken to be the captain) the effects of his role count:

- effect 3: × (1 + 0.05 × level) → 1.05, 1.10, 1.15;
- effect 4: × 1.3; effect 5: × 1.4;
- and for every player whose role has kind 6 (role 16) and who has an entry in a second table
  (`fcn_0329d8e5`): a 7-bit value below 51 → × 0.7; 56 to 60 → × 1.1; 61 to 65 → × 1.2;
  66 and up → × 1.3.

What the factor is applied to (one caller, `fcn_038b4368`) is not read. Roles also raise the salary (section 6.1).
`menu::ModeMLTeamRoleList` is the screen; `fcn_038bbe67` (222 lines) and
`fcn_038b9378` (191 lines, a table of dates at `0x0216f518`) assign roles. Not read.

## 12 Growth, team spirit, youth, retirement

Level: the growth system **read and run in the emulator** (November 2026, section
12.2); whether the game keeps a potential for a player **read** (below).

**No potential was found.** The player record of the edit file has no such field
(`output/edit_fields.tsv`); field `0x2e` of the mode's record is a status band. Age is
field `0x2b`; `fcn_036236a2` raises it once a year. Abilities are raised by
`fcn_03625c10` and `fcn_038b2fc4` in fixed amounts; the one byte argument of
`fcn_03625c10` that could have been a rate is a constant of its caller (`0x3c`). So
what a player becomes is a matter of his age and of what he plays, not of a stored
number, and a module cannot read "potential" from the game. `sider/MLMoney.lua` uses
the rating a player has at his age in its place (6.6). Of the functions named in the
table below, `fcn_038b805c`, `fcn_038679a9`, `fcn_0360e02f` and `fcn_0360f0fc` were
read far enough to see that they are not the growth arithmetic (nor is
`fcn_0360f928`); `fcn_038b9827` belongs to the match day and sets field `0x60`.

| topic | where to start |
|---|---|
| growth | `process::CmnGrowthCheck` (`fcn_0360f02d`, `fcn_0360f0fc`), `process::CmnSeasonGrowthCheck` (`fcn_0360df60`, `fcn_0360e02f`), `process::InfoNewsGrowth`; `menu::MenuModeGrowthReport`; `fcn_038b805c` (15 callers), `fcn_038679a9` (16 callers). Large bodies next to the role code, purpose not established: `fcn_038b9827` (736 lines; called from the day-end step `fcn_036365e6`; constants 0.5, 2, 3, 16; random numbers; tables `0x0216f510`, `0x0216f518`) and `fcn_038b765b` (156 lines; constants 0.7, 3.1, 100) |
| report day | event 48: `fcn_0363beba` |
| team spirit | read: section 12.1 |
| youth | strings `PlayerList::CreateObjectYouth` (`0x01f69540`), `ML/MLYouthMemberList` (`0x01f69560`); no class of its own in the type records; the rule that makes youth players is not found |
| retirement, new players | string `RETIREMENT_PLAYER` (`0x01f21500`); on the first day of a season the Become a Legend branch of the day begin sets a mark on the user's player from age 37 (from 36 with a condition); the Master League rule is not found |
| contracts | events 12 to 15 on 30 June and 31 December: `fcn_036e1665` (405 lines), `fcn_036e20d2`, `fcn_036e067a`, `fcn_036e1568`; string `PlayerList::CreateObjectUpdateContract`; years of a deal: `fcn_0388a1be` (96 lines, 9 callers) |
| draws, titles, awards | draws, events 32 to 39: `process::ProcessCmnLotCheck` (`fcn_035e6c9a`), `fcn_036cdb49`; titles, events 41 to 44: `fcn_0362eb70`, `fcn_036696e1`, `process::SpecialTitle…`; award holders: `fcn_0318c209` (12 callers) |
| news, staff reports | `process::InfoNews…`, `process::InfoStaffReportML`, `process::InfoEventML`; `fcn_038551f2(&kind, &value)` posts a news item, `fcn_031538bf(…)` a staff report |

### 12.1 Team spirit

Level: **read** (November 2026, C and disassembly); the value function and the match
set-up were run in the emulator on a made-up player (`sider/test_spirit.py`). Nothing was
seen in the game. `sider/MLTeamSpirit.lua` switches it off for Master League.

**Where it counts.** `fcn_038ddff7` is the gate: the mode number is `0x13` (Master
League) or `0x34` to `0x3d` (kind 21, taken to be myClub: its branch uses the strings
`teamSpirit_full`, `teamSpirit_decrease` of the myClub screens). Outside it every value is 99.

**The value of a player**, `fcn_038df4c9(player, his 14 bytes, the club's tactic flags,
position, flag, formation, team, list)` -> 1 to 99:

- `fcn_038ddcd2`: the player has two bytes for each of the club's seven tactic settings,
  one per option; the byte of the option the club uses counts. In the emulator seven
  equal bytes `n` give `n`.
- `fcn_038dddae`: plus 10 for each setting where player field `0x3a` (taken to be the
  playing style) has a mark in table `0x02171450`.
- `fcn_038ddee8`: times 1.0, 0.8 or 0.5 for a position he plays at A, B or C.
- Master League (`mode_kind` 12) only: `fcn_038defb9` adds a list of numbers from the
  match object (`+0x4ec4` count, `+0x4ec8`) and one more number, each times a factor of
  1 to 5 that is larger for a low value; cap 97, or 98 / 99 when that last number is 5 or
  10 (`fcn_038b6e0d(8)`, `(9)`: taken to be role effects 8 and 9 of appendix E). What
  fills the list is not read. A flag byte per team (match object `+0x4dbc`, set by
  `fcn_038df8fe`) cuts the value to a tenth first; what it stands for is not read.
- Master League with a career loaded: **only a player of the user's club gets this
  value** (`fcn_03854677`: he is in the squad of the user's club, and the club in his
  match record, `+0xa8`, is that club); every other player gets 99. That branch starts at
  `0x038df6c1` (`mov eax, [ebp + 0x24]`, the first of the seven arguments of
  `fcn_038df383`), and it is reached from three places: from the test of the two flags at
  `0x038df6ab` and twice from the way of a mode without a career (`0x038df789`,
  `0x038df7b1`), which looks for the player among the two teams of the match. Version 2
  of `sider/MLTeamSpirit.lua` writes twelve bytes there: `mov al, <value>`, the three pops
  the branch owes (`pop ebx`, `pop edi`, and the `pop esi` at `0x038df7a5`, followed by
  `mov esp, ebp`, `pop ebp`, `ret`), and a jump to that `pop esi`. Version 1 jumped five
  bytes at `0x038df528`, before the flags are worked out, to the `return 99` at
  `0x038df7a1`.

**The team value** on the game plan screen (`fcn_0431a07c`, strings `gmPlanTeamSpirit`,
`gmPlanTeamSpiritValue`; arrows by `fcn_04319974`): `fcn_042f18d5` -> `fcn_042f1263`, the
mean of the values of the eleven lineup places (of three formations when
`fcn_042f8fd7(team)` says so). After a played match `fcn_0360fcbc` keeps it in the bytes
`+0xe4c1da` / `+0xe4c1db` (and team strength in `+0xe4c1dc` / `+0xe4c1dd`); the menu
(`fcn_0329dbd9`, `fcn_0329dd72`) reads them only to show a change. `fcn_0368ac2a`, a
news text builder, tests the value against 66; not read further.

**Played match.** The match set-up `fcn_04177a65` (callers `fcn_0417e90f`,
`fcn_0417f2fa`, `fcn_04192ea0`) stores the value for 3 formations x 13 positions at
team block `+0x56 + formation x 13 + position` (`fcn_02f7d861`; read by `fcn_02f7d891`).
`fcn_02f903a7` runs per player during the match: with value `v`,

```
t = 0.65 x clamp((v - 10) / 40, 0, 1) + 0.35 x clamp((v - 50) / 49, 0, 1)
factor = 0.70 + 0.30 x t          v <= 10: 0.70    50: 0.895    80: 0.96    99: 1.00
```

and 22 ability bytes of the match (indices 20 to 35, 37 to 42 of table `0x01f41a50`) are
multiplied by it and by five other factors, then kept inside 40 to 99
(`fcn_02f7e623`). By the tables `0x0256f6d8`, `0x021629f0`, `0x02164500` and the names of
`tools/overall.py` these are attack, defence, goalkeeping, dribbling, ball control,
finishing, low pass, lofted pass, header, ball winning, place kicking, swerve, reflexes,
catching, clearing, coverage, speed, body control, physical contact, kicking power,
explosive power and jump; stamina (index 43) is not among them. One player picked by
`fcn_0308ccf4` is spared; who that is, is not read. `fcn_0308d992` gives the mean value
of two players to six places of the match AI (limits 50 and 80); what they decide is not
read.

**Skipped match.** None of the simulation functions (`fcn_03708fd5`, `fcn_03708de9`,
`fcn_03707a1f`, `fcn_03705feb` and what they call) reaches a team spirit function; they
use `team_strength_of` (section 10).

**`sider/MLTeamSpirit.lua` version 2** answers a value of the club's own, 90 to 99, in the
place of the value of the branch: it walks the match records (section 5.1) for the last
five matches of the user's club, the highest round of its cup and the places in its
league, and sets the byte at `0x038df6c2` before every match from the rules at the top of
the module. Over 90 to 99 the factor is 0.981 to 1.00, so the effect is there and does not
bite. Which match it is, it is told by Sider: `ctx.match_id` is the number of the match
record (the same word the game gives `match_record`), so the record answers the
competition and the round of the match; the kind of that competition — a league or a cup —
is then read from the competition record that carries its number, as `fcn_03822ab9` does.
Sider's `ctx.tournament_id` is not used for it: that number is one of the game's own
(`fcn_04062701`, section 5.1) and the records do not carry it.

### 12.2 The growth system

Level: **read and run in the emulator** (November 2026, disassembly + `sider/growth_cave.py`,
`sider/test_growth.py`).

**Who grows.** The mode keeps a growth record for about fifty players only: the user
squad and the youth team. The records live in a 50-entry container at mode data
`+0xd10140` (entry stride `0x204` at `+0x493ec`). `fcn_0313b4b5(id_lo, id_hi)` with
`ecx` = the container answers whether a player has one; `fcn_031207c6` (same arguments)
returns it, or the dummy entry at the table base when he has none — it never returns 0,
so the test is `fcn_0313b4b5`. Every other player of the game (19,871 of 19,921 in the
test save) is frozen: he is never awarded anything.

**The record.** `exp int16[98]` at `+0x16` and `carry int16[98]` at `+0xda`, both
indexed by the field selector; pending growth events at `+0x19e` (a counter, filled
with 10); appearances of the current cycle at `+0x1a0`; cumulative appearances at
`+0x1a4`.

**The award.** `fcn_038b2fc4(rec, &field, &exp_f32, kind, news)`, cdecl. `exp` is a
float; guards: selectors `0x1e`/`0x2a` are special, the ability must be under 99, the
exp under 40 after scaling. The exp goes to `carry[field]`; `fcn_036216e9` turns carry
into levels (1000 exp = 1 level, the remainder stays in `exp[field]`); the ability is
set with `fcn_038281b0(field, value)` (`ecx` = record); `news` asks for an entry at
mode `+0xd5f9f4`. Run in the emulator: exp 1000, kind 0, news 1 → one level. Negative
exp is the game's decline award and removes levels the same way.

**The driver.** After a match `fcn_03626f8d` counts an appearance (`+0x1a0`,
`+0x1a4`) and, when `+0x19e` is not empty, calls the distributor `fcn_03625c10` once
and takes one event off. The distributor sorts the club's players by rating into
quartiles (band from `fcn_0329d810(&id)` age getter: `([age] / 0x3c) or 0`): a player
with a record gets tier exp through `fcn_038b2fc4` (under 0x38: 140/100/70/40; under
0x41: 210/140/100/70; else 250/210/140/100 by band), the user's second pass gives
`1000 - exp` to the top exp fields; a player without a record gets the direct setter
`+{2, 1, 1, 0}` by band, cap 99. The day step `fcn_0362752f` rolls the training table
`0x20fe140` (22 rows: age, gk flag, rate; gate selector `0x5e`) and fills `+0x19e`
with ten events, with a staff report: at 9 left the report is posted (news `0x31`), at
5 the setter gets `0x13`, at 0 the setters `0x12` and `0x13` run and `+0x1a0` is
cleared.

**The after-match training step.** For every player of a played match (event 13 of
the day, `fcn_03627f02`'s branch) the game runs, in order: `fcn_03879434` computes a
minutes factor; `fcn_038b4368` accumulates match data; then the three training
awards -- `fcn_036225f8` (individual focus, the setting at mode data `+0xd62a8c`,
a menu code 1-13 that `fcn_038547ee` maps to a training category), `fcn_0362274d`
(team focus, the coach setting at `+0xd62a88`, one of 0x42-0x5d) and `fcn_0362288c`
(the two regime meters, selectors `0x1e`/`0x2a`, capped 0-3) -- and finally
`fcn_03626f8d`, the appearance counter.  The focus paths scale their exp by the
player's position versatility (table `0x0216da18`, 13x13 rows of rate/10, factor
1.0-6.0, `fcn_038b12a2`) and by the coach level (byte at `+0xd62a83`, table
`0x0216dcf4`, `fcn_038b1393`), and turn it into levels with `fcn_036216e9`
directly -- the exp award is not involved.  `fcn_0362288c` awards
`0.3 x regime x minutes` to the meters through `fcn_038b2fc4` with kind 2 (no
news).  The exp award's own guards: selectors `0x1e`/`0x2a` accept values 0-3 only,
and a negative exp that would take an ability below 41 does not run at all -- the
vanilla decline never breaks the 41 floor.

**The season walk.** `fcn_036236a2` raises the age of every player once a season: it
walks the player array at mode data `+0` (stride `0xe0`, count at `+0x5fecdc`, a dummy
record follows at `+0xed3620`), skips records with id high word 0 (when
`[0x24fe518]` is 0), the two global club ids (`[0x24fe514]`, `[0x24fe518]`) and types
5 and 6 (`[+0xb4]` bits 0-3), and calls the setter with selector `0x2b` for each. The
`mov edx, [0x24fe518]` at `0x0362373a` is the last instruction of the loop body before
the branch back — the hook site of the module below (`esi` = the record).

**The player record of the mode** (the case handlers of the getter `fcn_038278b0`,
jump table `0x0382801c`; the setter `fcn_038281b0` writes the same slots, `ecx` =
record): 7-bit abilities packed four to a dword — `rec+0` bits 24-30 atk, bit 31
registered; `rec+4` top nibble position (0 CF … 12 GK), then def, gk, drib,
ball_ctrl; `rec+8` finish, lowpass, loftpass, header; `rec+0xc` ball_win, place_kick,
swerve, reflex; `rec+0x10` catching, clearing, cover, speed; `rec+0x14` body_ctrl,
phys, kick_pwr, exp_pwr; `rec+0x18` jump, stamina; `rec+0x1c` bits 7-12 age, bits 0-6
fitness; `rec+0x2c` the id (low, high). The overall rating of a record:
`fcn_03838c18(&id, &slot, 0)`, cdecl, result in `al`.

### 12.3 A Sider module that gives every player an age curve

`sider/MLGrowth.lua` (version 3) changes four places in the running game; what it
writes and why is in `sider/growth_cave.py` (its Python is the reference the test
compares the machine code with), `sider/test_growth.py` runs the game's own award,
training and season-walk code with the changes in the emulator.

- **Hook A, the exp award** (`fcn_038b2fc4` entry, `0x038b2fc4`): before the function
  runs, the exp argument is multiplied by the moderated age curve (x2.5 at 15-17,
  x2.0 at 18-21, x1.25 at 22-24, x0.75 at 25-27, x0.5 at 28-29, x0.25 from 30), by
  the potential scale `min(1, (99 - rating [+4 when rating >= 75 and age <= 21]) /
  margin(age))` with
  margins 25/19/12/5/1 from 15/18/21/24/27 on (0 below 15 and from 53 on: no growth),
  and, for a player with a growth record, by his playtime of the cycle
  (`0.5 + 0.5 x min(1, appearances / 20)`, 20 for a player without one). The rating
  is the game's own (`fcn_03838c18`). Version 3 applies a 0.80 pace setting before
  the quarter-step table is made. It therefore reduces the 15-27 rates but keeps the
  x0.5/x0.25 late-career tail; potential headroom and playtime still determine whether
  a player receives the reduced rate. Negative exp (decline) is multiplied by 0.25,
  except the physical fields — speed, body balance, physical contact, explosive
  power, jumping, stamina — from 31 on, which decline in full. Guards, carry, levels,
  news and reports run as before.
- **Hook E, the season walk** (after the age setter call, `0x0362373a`): every player
  without a growth record — the frozen 19,871 — now also gets
  `season_levels(age, value)` points on the ability of his position (CF and SS
  finishing, DMF and the defenders defending, the GK goalkeeping, the rest dribbling;
  a position number above 12 falls back to dribbling), where `season_levels` is
  `floor(curve)` at full headroom and `headroom x curve / margin` (integer division)
  below it, capped so the ability stays under 99. Players with a record are left to
  hook A.
- **Version 2, hook A fix**: kind-2 awards (the regime meters of the after-match
  step, which the game already scales by minutes played) no longer get the playtime
  factor on top -- the minutes were counted twice.
- **Version 2, hook C, the training focus** (the two `call fcn_036216e9` sites of
  the after-match step, `0x036226a7` in `fcn_036225f8` and `0x036227e5` in
  `fcn_0362274d`): the exp of the individual and the team focus is multiplied by
  the same age curve and potential scale before the game turns it into levels --
  vanilla training improved a 33-year-old as fast as a 17-year-old.  The cave holds
  the player (edi) and the growth record (ecx) of the call sites and passes them
  on; the scaled exp lands in `fcn_036216e9`'s own exp array of the growth record.

A six-season replay of **version 3** hook E on all 19,921 players of the test save
(`python3 sider/growth_cave.py calibrate <exe> <save>`) moves the mean rating from
67.81 to 67.92. The 15-20-year-olds gain 0.49 on average (the biggest riser is +17),
the 21-24-year-olds 0.12, and from 25 on nothing moves. The ~50 players with growth
records follow hook A instead, which hangs on matches played and cannot be replayed
from a save.

The module uses the free gaps `0x047d3f07`-`0x047d3f9a` (season award),
`0x047d5b8c`-`0x047d5bde` (the curve routine), `0x047d6377`-`0x047d63fa` (the exp
award), `0x047d6e50`-`0x047d6ef7` (the season walk) and the `.text` page tail
`0x0298c200`-`0x0298c2eb` (236 bytes of tables), all zero-checked first; see the
memory map in `sider/README.md`.

## 13 The Master League save file

Level: the table **read**; the content **seen in two saves of one career** (see below).

The save-kind table at `0x0213d1a8` (see `NOTES.md`) has Master League in **row 10**:
name `ML`, folder key `ml` (row 11 is `BL`, row 9 `LG`). The
container is the one `savefile.py` reads: same header, same cipher, same hashes. What
is inside was looked at in the two files of `ML saves/` (the same career on 1 July
and on 15 September of its first season). `python3 tools/savefile.py unpack <save>
<folder>` gives a `data.dat` of 13,253,312 bytes. Found in it, each by its content:

| file offset | what | how it was recognised |
|---|---|---|
| `0x50` | 626 team records of `0x520` bytes; the low 14 bits of a club id are the index in this table | names and ids |
| `0x92262c` | the club ranking: 499 records of 16 bytes: club id, place, points (twice, 16 bits each), 0, level (16 bits) | places 1 to 499 in order, levels as in 9.4 |
| `0x92596c` | 498 plan records of `0x118` bytes (9.1) | club ids in ranking order |

The ranking stands at mode data `+0xcc84cc` in the code, so for this part of the file
`file offset = mode-data offset - 0x3a5ea0`. That rule does **not** hold for the
whole file: **the player records are stored packed, as the last part of the data**
(seen in four saves; in all of them the numbers below start at `0xb24664` and the
block ends with the data). All numbers of the block are big-endian:

| | |
|---|---|
| `0x0047e3e0` | size of the records: 21,033 x `0xe0` |
| one dword | differs per save, close to the packed size; not used |
| per chunk: `0x00040000` | its size unpacked (the last chunk: the rest) |
| per chunk: one dword | its size packed |
| per chunk: one dword | a running offset; not used |
| per chunk | a zlib stream (`78 da`) |

18 chunks. `player_block` in `sider/window_report.py` unpacks it. This is why a search
of the data for player names or club ids finds nothing. The order and the offsets of
a record are those of the running game (`+0x2c` is the number of the record, `+0x30`
and `+0x34` the player id, the name from `+0x38`), so the game's own rating function
can be run on a record of a save (`Rater` in the same file).

Fields of a player record, **from the saves, not from the code**: club id at `+0xa8`
(`0xffffffff`: none); `+0xb4`: status in bits 0-3 (1 or 2: no contract), deal in bits
4-5 (3 after a signing in the window), popularity in bits 11-22; `+0xb8`: marks 29 and
30 (9.3), bit 28 loan (set in no record of the four saves); `+0xd8` the day the
contract began (the day of the signing), `+0xb0` its end. Age (`+0x1c`, bits 7-12)
and position (`+0x04`, bits 28-31) as in the code.

Three more places, again **from the saves** (`sider/window_transfers.py` reads them):

| where | what | how it was recognised |
|---|---|---|
| player record `+0xd0` | the club the player left, while the window is open; `0xffffffff` otherwise | in the save of 31 August it is the club of the save of 1 July for all 260 players who moved from a club, and empty for the 178 who had none and for every player who did not move. `do_transfer` writes a club id there in three of its cases. In the save of 15 September only 5 of 511 still carry it; what clears it was not found |
| file `0x75bea8` | today: day of the year (16 bits, 0 = 1 January), year (16 bits) | 181 / 2024 in both saves of 1 July, 242 in the save of 31 August, 257 in that of 15 September; the only place with those four values |
| file `0x868144` | the user's deals: 100 lines of `0x28` bytes: player id (8 bytes), amount at `+0x20` (minus: paid), kind at `+0x24` (1 bought, 5 sold) | the list of `fcn_038a9c7a` (9.7): eight lines for the eight deals of the user's club in that window, zero for the two players signed without a club. A line is written into the first empty place; when all 100 are used nothing is written. What empties the list was not found |

The deal bits of `+0xb4` are 3 for all 438 signings in the save of 31 August and 0 for
all 511 in the save of 15 September: the mark lasts as long as the window.

`do_transfer` also hands the fee to `fcn_038e5185` when the user's club is one of the
two: it puts player id, day, fee and a kind (1 transfer, 3 loan) on top of a list of
ten (`fcn_0382e61b`, object `+0xb74`, 20 bytes each, the oldest drops out). For a move
between two computer clubs the fee goes nowhere.

One consequence of section 2: a career keeps its own player and team records in the
mode data. That is read from the look-up functions (they search tables inside the mode
data), not checked with a save. It means a change of the edit file reaches a running
career only where the mode reads the database again; where that happens is not found.
