# Runtime layout and verified formulas

[Master League guide](../MASTER_LEAGUE.md) · Section numbers are the original research citations. Paths in the notes are relative to `pes database/exe` unless a command changes directory.

## 1 What is proven

From `pes database/exe/tools`:

```
python3 check_findings.py ~/pes-work/game/PES2017.exe "../../EDIT00000000 (pes 2017 updated)"
7 ok: the game's salary code (fcn_038ac66e) and money.salary give the same amount for 3000 random players (awards and title bonuses not run)
8 ok: the game's transfer fee code (fcn_038ab832) and money.fee give the same amount for 3000 random cases, with and without the random change
9 ok: the game's year-plan code (fcn_038b0b21) and yearplan.events put the same events on each day (8928 days: four modes, both season kinds, flags on and off)
10 ok: the game's league fixture code (fcn_03774725, fcn_037741b4) and fixtures.plan build the same table for leagues of 2 to 24 teams with two legs, also with the sides changed
11 ok: the game's overall window of a computer club (fcn_0365d12d, fcn_0365d08d) is clubai.LEVEL_MIN / LEVEL_MAX for the levels 0 to 9
```

- **Salary formula** (section 6.1), `tools/money.py`.
- **Transfer fee formula** (section 6.2), `tools/money.py`.
- **Year plan**: which event falls on which day, for Master League, Become a Legend,
  League mode and the other modes, for both kinds of season (section 4),
  `tools/yearplan.py`.
- **League fixtures**: which teams of the list meet in which round of a home-and-away
  league (section 5.3), `tools/fixtures.py`.
- **Overall window of a computer club** by its level (section 9.4),
  `tools/clubai.py`.

How the proof works: `emu.py` runs the function's machine code. The functions it would
call to fetch a player, a ranking place or a random number are answered with chosen
values (`Game.replace`), so the arithmetic that runs is the game's. What this does
**not** prove: that the inputs I name (rating, ranking place, …) are what the game feeds
in during a career. That part is read, not run. Each check was also tried
against a wrong formula (one event dropped, one fee rule dropped, one salary off by
1, the seventh-round rule of the fixtures dropped, one level limit off by 1) and
failed as it should.

## 2 The frame: mode data, records, random numbers

Level: **read**.

### 2.1 Where the mode lives

| what | where | note |
|---|---|---|
| mode object | pointer at `0x026503e0` (`mode_object`, `fcn_0381c0e5`, 3,003 callers) | `+0x30` = pointer to the **mode data**, one block of more than 15 MB |
| menu / mode selector | pointer at `0x0264f3e8` (`fcn_03808865`) | `+0x20` = number of the running mode, 0 to 69 |
| mode kind | `mode_kind` (`fcn_038093f1`): table `0x0251d408[mode number]` | **11 = League, 12 = Master League, 13 = Become a Legend**; the other values are the other modes |

Mode numbers 19 and 40 give kind 12; 18 and 39 give 11; 20 and 41 give 13. That 12 is
Master League is concluded from the code: the kind-12 branches are the ones that run
negotiations, scouts and club accounts, and kind 13 reads one player id at
`+0xe4a528` (the Become a Legend player).

### 2.2 The mode data (offsets from the pointer at `+0x30`)

| offset | size | what |
|---|---|---|
| `0x552e80` | 300 × `0x224` | competition records; count at `0x5fece8`; empty record at `0x5fe840` |
| `0x5fe320` | | empty team record (returned when a team id is not found) |
| `0x6f154c` | 9,000 × `0x24c` | match records (every fixture of the season) |
| `0xbfd52c` | 365 × `0x214` | **calendar**: one record per day of the year (section 4) |
| `0xc2cbb0` | u16 | today, as day number of the year, 0 to 364 |
| `0xc2cbb2` | u16 | the year (the first one comes from the set-up, section 2.5) |
| `0xcc84cc` | | club ranking: rows of `0x10` bytes, count at `+0x28a0`; `fcn_03138333(club)` returns the number stored for the club (taken to be its place) |
| `0xccb80c` | 851 × `0x118` | squad plan of each club (section 9); count at `0xd06434` |
| `0xd06438` | 70 × `0x1dc` | **deal records** of the user's club (section 7) |
| `0xd0f154` | 3 × `0x1e4` | three search slots with 16 results each; taken to be the scouts (section 8) |
| `0xdcb68c` | date | the first day of the career, written by the set-up (section 2.5); compared with today in many steps (what for ?) |
| `0xddce6d` | byte | when set, most Master League steps of the day are skipped (meaning ?) |
| `0xddcf02` | u16 | **seed of the mode's random numbers** |
| `0xddcf04` | u32 | when not 0, the transfer and report steps are skipped (meaning ?) |
| `0xdddef0` … `0xddf74c` | | club accounts; `0xddf74c` low 24 bits = a money figure set each day from `fcn_03878855` |
| `0xe4a528` | id | the Become a Legend player |
| `0xed3620` | | empty player record |

A date is four bytes: year (u16), month, day. `today` (`fcn_038ae451`) builds it from
the day number with the month table at `0x0216bb60` (12 rows: month, first day number,
last day number; February has 28 days, there is no leap day).

### 2.3 Records

Look-up functions:

| function | returns |
|---|---|
| `player_record` (`fcn_03822835(id, id2)`, 502 callers) | player record; a player id is two numbers |
| `team_record` (`fcn_03822969(id)`, 500 callers) | team record; a team id has 14 low bits and a high part |
| `competition_record` (`fcn_03822ab9(id)`, 403 callers) | competition record |
| `match_record` (`fcn_03822b3f(number)`, 183 callers) | match record |
| `player_value` (`fcn_038278b0(field, out)`, 302 callers) | one of 98 packed fields of a player |

Fields seen in use (offsets inside the record; "?" = meaning not established):

| record | offset | what |
|---|---|---|
| player | `+0x2c`, `+0x30` | the id pair |
| player | `+0xb4` bits 0-3 | status: 0 for a normal player; 1 and 2 lead to the deal types 6 and 5 (taken to be players without a contract); 3 and 4 stop a deal; 6 is shut out of the pool (section 9) |
| player | `+0xb4` bits 4-5 | "in a deal" (bit 5 is set when a computer club picks the player) |
| player | `+0xb4` bits 6-10 | years at the club (`fcn_0364c9f7`; cleared by a transfer) |
| player | `+0xb4` bits 11-22 | **a number 0 to 4095, called `x` below**: it raises salary and fee. Meaning ? (candidates: fame, popularity) |
| player | `+0xb8` bits 26-27 | level of the team role, 0 to 3 |
| player | `+0xb8` bit 28 | a mark, called "own" bit below: players with it are left out of the wage bill, and it changes the fee (section 6.2). **Taken to be "on loan"**: the loan kind of `do_transfer` sets it, the return clears it, and the pool of section 9.5 leaves such players out |
| player | `+0xb8` bits 29, 30 | marks set by the squad planning of computer clubs: players the club lets go (section 9) |
| player | `+0xd0` | team id |
| player | `+0xdc` | day of the last transfer |
| player | `+0xc4` | team role, one byte (section 11) |
| player | `+0xcc` | **salary** (the wage bill sums it; the fee starts from it) |
| team | `+0x4a` | name |
| team | `+0xf8` | squad: 8 bytes (id pair) per player |
| team | `+0x328` bits 9-15 | number of players in the squad |
| team | `+0x514`, `+0x518`, `+0x51c` | **the three rivals** of the club (`fcn_035f5c69(record, n, &out)`: `n` 0 to 2, `n` 3 and more give `+0x514`; `fcn_03857dfb` asks it for two clubs and compares the ids shifted right 14). `0xffffffff` is "none": in the two saves of `ML saves/` every club record holds three of them |
| competition | `+0x21c` bits 30-31 | number of legs; more fields in section 5.1 |

Player fields used by the money and negotiation code (`player_value`): field `0x2b` =
age (the code tests it against 36, 37 and 45), field `0x20` ?, field `0x2e` ? (0 to 7). The numbering is the game's own, not that of the edit
file, so `output/edit_fields.tsv` does not name them.

### 2.4 Random numbers

`mode_random` (`fcn_03855998(&n)`, 141 callers) returns a number from 0 to n-1:

```
seed = u16 at mode data + 0xddcf02
srand(seed)
r    = (rand() * rand()) mod n            # the result
seed = ((r + 1) * n + seed) mod 65535     # stored back
```

Every chance in the mode goes through this one function and one 16-bit seed that is
part of the mode data. So the same save, continued the same way, draws the same
numbers. (Read; whether the seed is saved with the career is not checked.)

The 141 callers are a map of where chance enters the mode; the large ones are listed
in appendix A.

### 2.5 The year of a new career

The set-up of a new career (`career_setup`, `fcn_035f445b`; the same function for League
mode, Master League and Become a Legend, mode kinds 11, 12, 13) writes the year as a
constant, and the function it calls for the contracts (`career_contracts`,
`fcn_036651d4`) does the same. In this exe the constant is **2024**. Eight
instructions hold it:

| address | instruction | what |
|---|---|---|
| `0x035f44b4` | `mov eax, 2024`, then stored as the year at `+0xc2cbb2` | year of the first day |
| `0x035f452e` | `mov [mode + 0xdcb68c], 1 January 2024` | first day, season from January |
| `0x035f458f` | `mov [mode + 0xdcb68c], 1 July 2024` | first day, season from July |
| `0x036653b3` | `lea ecx, [ebx + 2024]`, then 31 August of it | contract end, season from July (`ebx` = years) |
| `0x036653bf` | `mov [player + 0xd8], 1 July 2024` | contract start, season from July |
| `0x036653f2` | `lea ecx, [ebx + 2025]`, then 31 January of it | contract end, season from January |
| `0x036653fa` | `lea ecx, [ebx + 2024]` | the same, when the flag at `[ebp-0xa4c]` is set |
| `0x0366540c` | `mov [player + 0xd8], 1 January 2024` | contract start, season from January |

`sider/MLYear.lua` writes another year into these eight (`sider/test_year.py` runs the
eight instructions after the change). The eight were found by a search of the whole code
for the number 2024 and 2025 as a value or as the year of a date; every other hit is an
offset into a record or a jump distance.

The exe still holds **2016** (and 2017) at other places, so 2024 is taken to be a change
made to the exe before it came here, and these were left out of it. `MLYear.lua` leaves
them as they are too, so a career behaves as it does now, in another year:

- `0x036655f1`, `0x03665616`: the date 1 January or 1 August 2016, given to
  `fcn_0388b857`, which writes a date at player `+0xdc`: 1 July or 1 January of the
  year after, so 2017. It is taken to be the end of a loan the set-up makes:
  `fcn_036df464` looks for players with the loan mark (bit 28 of `+0xb8`) whose date is
  today. Three more functions give the date to `fcn_03135cea`, taken to be the days
  between two dates (`fcn_0389ec18`, `fcn_038a2b31`, `fcn_03649f1f`). What a date years
  back does to them is not worked out.
- `0x03665455`: contract end 31 August 2017 (31 January 2018) for the Become a Legend
  player.
- `0x03637c9c` (`fcn_03637bf2`, Master League, season from July): 1 July 2016 at `+0x18`
  of the 72 records at `0xd62a90` (meaning ?). The two saves hold 32 and 31 dates in 2016.
- `fcn_036cc580`: gives a date and 1 July 2016, then 1 January 2016, to `fcn_03121acc`
  (not read).
- "Is the year 2016?" in `fcn_035d8f79`, `fcn_0362579a`, `fcn_03629931`, `fcn_0363e8bb`,
  `fcn_036696e1`, `fcn_036960cc`, `fcn_036d0c58`, `fcn_03862262`, `fcn_0386285a`,
  `day_state` (`fcn_03877938`) and `fcn_038af05f`. Taken to be the exceptions of the
  first season; they were not read one by one. In a career that starts in 2024 or later
  none of them answers yes.
- `fcn_03635675` (called by the staff report at day end): in July a part of it runs only
  when the year minus 2017 is a multiple of four, so in 2017, 2021, 2025, 2029. What the
  part does is not read. It is the only place found where the year counts in fours.

What does not hang on the year: the age of a player is a 6-bit number in his record
(section 6.5), there is no year of birth. The date of a day (`date_of_day`,
`fcn_038ae3cc`) is the year and the month table; there is no leap day.
