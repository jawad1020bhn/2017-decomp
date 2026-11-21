# Build checks, career year and Team Spirit

[Sider developer guide](../README.md) · These are versioned implementation notes and test observations. For current settings and deployment, use the guide and shipped Lua files. Paths and commands assume the `sider` directory unless noted.

## Install and run `MLCheck.lua`

1. Copy `MLCheck.lua` into the `modules` folder next to `sider.exe`.
2. Add this line to `sider.ini`, above `MLMoney.lua` and other memory-patching modules:
   `lua.module = "MLCheck.lua"`
3. Start the game with Sider as usual, wait for the title screen, quit.
4. Open `sider.log` (next to `sider.exe`) and look for the lines with `MLCheck`.

Expected, on the exe of this repository:

```
MLCheck 1: read-only test, nothing is written to the game
club level       0  1  2  3  4  5  6  7  8  9
lowest overall  47 51 55 59 63 67 70 73 76 83   as expected
highest overall 74 75 76 77 78 79 80 83 86 99   as expected
fee: rating step 68             at 038ab8db = 83f844   as expected
fee: 9,000 per rating point     at 038ab8e6 = 69ff28230000   as expected
fee: factor 0.00027             at 0216ba48 = 00000020d9b1313f   as expected
fee: factor 2.2                 at 01f0f2b8 = 000000a099990140   as expected
RESULT: 6 of 6 as expected. The running game has the code the notes describe, at the same addresses.
```

To remove it, delete the line from `sider.ini`.

What the result means:

- **6 of 6**: the running game holds the same code at the same addresses as the exe
  file that was analysed. A module that changes these numbers can be tried next.
- **`DIFFERENT` or `??`**: the game that runs is not this exe, or its code is changed
  in memory. No tuning module made from these notes should be used.
- **No `MLCheck` line at all**: look for `MLCheck.lua` in `sider.log`. Sider writes
  there why it skipped the module (file not found, error in `init`).

## Result in the game (14 November 2026)

`MLCheck.lua` ran on the user's PC under Sider 3.6.0: **6 of 6 as expected**, with the
same nine lines as above. So the running game holds the analysed code at the analysed
addresses, and a Sider module reads it without trouble.

What else the same `sider.log` shows:

- `luajit.ext.enabled = 0`: modules have no `ffi`, `bit` or `require`. Modules here must
  work without them, including the F6/F7 money controls.
- Sider itself uses `0x026503E0` (`_tid_addr1`), the pointer `MASTER_LEAGUE.md` calls the
  mode object, and `0x04062701`, the competition id table function. Two addresses of the
  notes confirmed from another side.
- Sider changes code at 31 places of the running game (hooks and small patches). None of
  them lies in one of the 133 functions that `../names.tsv` named when this was checked,
  so the salary, fee, fixture and computer-club code runs as analysed. The eight names
  added later (prize money, account lines) were not checked against the 31 places, and
  the 31 addresses are not kept here. `MLMoney.lua` settles it at run time: it compares
  every piece of code it relies on with the exe file before it writes, so a place Sider
  had changed would show as `DIFFERENT` and nothing would be written.
- Sider's gameplay settings point at the constants `0x01F0F2A8` and `0x01F0F2C0`, the
  neighbours of the shared 2.2 at `0x01f0f2b8`. One more reason not to change that
  constant in place.
- Three other modules of that install are not active, for reasons of their own:
  `Script_Stadiums.lua` (file `map_teams.txt` missing), `PlayerDump.lua` (calls
  `memory.search_process`, which this Sider does not have) and `GrowthBridge.lua` (asks
  for events this Sider does not know: `key_down`, `overlay_on`, `set_teams`,
  `gamepad_input`).

## `MLYear.lua`, version 1: a new career starts in 2026/27

Emulator only: it has not run in the game yet.

### What it changes

This exe starts every new career on 1 July 2024. The year is a constant in the game's
set-up of a new career, at eight places (`../MASTER_LEAGUE.md`, section 2.5): the year of
the first day, the first day itself for both kinds of season, and the start and end of
every player's contract. The module writes `START_YEAR` into the eight, in the running
game only. With `START_YEAR = 2026`:

- a new Master League starts on **1 July 2026**, season 2026/27;
- every contract starts on 1 July 2026 and ends on 31 August of 2026 plus the years the
  game gives the player (it was 2024 plus the years);
- Become a Legend and League mode start in 2026 as well: they use the same set-up.

**It needs a new career.** The year and all dates of a career are in its save, so the
career of the saves in `../ML saves` stays in 2024, with or without the module.

### What it does not change

- **The players.** An age is a number in the player's record, there is no year of birth.
  The players are as old as the edit file says, in 2024 and in 2026.
- **The calendar.** The year plan is made of fixed days of fixed months, and the date of
  a day comes from a table of months without a leap day. Whether the game shows a
  weekday anywhere was not looked for.
- **The places where the exe still says 2016.** The game as it came here was moved to
  2024 at the same eight places only. Some thirty other places in fifteen functions
  still hold 2016 or 2017:
  questions "is this the year 2016" (taken to be the exceptions of the first season),
  a date taken to be the end of the loans the set-up makes (2017), a date in 72 records
  of the mode data.
  The module leaves all of them alone, so a career that starts in 2026 behaves like one
  that starts in 2024. The list is in section 2.5.
- One thing does move: a part of the staff report runs in July only when the year minus
  2017 is a multiple of four (2017, 2021, 2025, 2029). From 2024 that is the second
  summer, from 2026 the fourth. What the part does is not read.

### Install

1. Copy `MLYear.lua` into the `modules` folder next to `sider.exe`.
2. Add one line to `sider.ini`, above or below the other `lua.module` lines:
   ```
   lua.module = "MLYear.lua"
   ```
3. Start the game and look at `sider.log`:
   ```
   MLYear 1: the year in which a new career starts, from the setting in MLYear.lua
   check: year of the first day               at 035f44b4  as expected
   ... (eight check lines)
   RESULT: installed. A new career starts in 2026 (season 2026/27). A saved career keeps its year.
   ```
4. Start a **new** Master League. The first day must read 1 July 2026, and a player's
   contract must end in 2027 or later.

`RESULT: nothing written. ...` with a `DIFFERENT` line: the game does not hold the
expected code at that place; send the log. To undo, remove the line from `sider.ini`: the
next new career starts in 2024 again. A career started in 2026 stays in 2026.

For another year change `START_YEAR` at the top of the file (2000 to 2100).

### What the test shows

`python3 test_year.py <PES2017.exe>` (one second):

```
ok 1: with START_YEAR 2026, 2016, 2031 and 2100 the module writes the eight places and nothing else; only the bytes of the year differ
ok 2: the game's own code then gives that year: the year of the first day, the stored first day of both season kinds, the date of a day number, and the start and end of a contract (32 contract runs a year; without the module the same code gives 2024)
ok 3: seven faulty settings are refused before anything is read; with START_YEAR = 2024 nothing is written
ok 4: with one byte of a place changed (63 cases, a game that starts in 2026 already among them) nothing is written and the place is named; a write that does not go in is reported
ok 5: with MLMoney.lua and MLTransfers.lua in the same game, above or below them, all three are installed and the year is 2026
```

Sixteen faults were planted in the module one at a time (a wrong address, a wrong year
at one place, the bytes of the year in the wrong order, a check taken out, and so on);
the test failed on each of the sixteen.

Not shown: the set-up of a career as a whole was not run, only its eight instructions,
so a ninth place that takes the year in another way would not be seen. The search for
2024 and 2025 in the code found no other. Nothing ran in the game.

## `MLTeamSpirit.lua`, version 6: Team Spirit follows the form of your club

Emulator only: it has not run in the game yet. (Version 1 answered 99 for every player,
which switched the effect off; it is described at the end of this section.)

### What the game does

Read in the exe (`../MASTER_LEAGUE.md`, section 12.1), not seen in the game:

- **Played match.** Every player of **your** club has a Team Spirit value of 1 to 99;
  the number on the game plan screen is their average. In the match 22 of his abilities
  are multiplied by a factor that goes from 0.70 (value 10 or less) over 0.90 (value 50)
  to 1.00 (value 99). A player of a computer club always has 99.
- **Skipped match.** The simulation does not read Team Spirit; it works from team
  strength. `MLSimMatch.lua` does not read it either.

So Team Spirit only ever makes your own team worse, and only when you play.

### What the module changes

Twelve bytes in the function that gives a player his value (`fcn_038df4c9`), in the running
game only: the head of the branch that only a player of your club goes into now answers
"the value is this number" and takes the function's own way out (the same three pops the
branch owed). One byte of that, the value itself, is written again before every match,
worked out from the match records of the career (section 5 of `../MASTER_LEAGUE.md`):

| rule | effect |
|---|---|
| the last five matches, most recent first with the weights 3, 2, 2, 1, 1 | a win raises the value, a loss lowers it, a draw does neither; nine form points are four value points |
| two losses one after the other | at most 92 |
| three wins one after the other or more | at least 98 |
| the last round of a cup | 99 |
| the round below it | +2 |
| a club your club record names as a rival | +2 |
| a league match of two of the best four, or two of the worst three | +2 |
| the base value, when nothing is known | 95 |
| never below 90, never above 99 | 90 to 99 is a factor of 0.981 to 1.00 |

Every rule is a setting at the top of the file, and every one that fires is named in
`sider.log` with the value it led to. Nothing is stored in the game: no cave, no new
memory, no code of our own. The value itself is not saved; after restarting PES
without the module the game computes Team Spirit as before.

### Install

1. Copy `MLTeamSpirit.lua` into the `modules` folder next to `sider.exe`.
2. Add one line to `sider.ini`, above or below the other `lua.module` lines:
   ```
   lua.module = "MLTeamSpirit.lua"
   ```
3. Start the game and look at `sider.log`:
   ```
   MLTeamSpirit 6: Team Spirit follows the form of your club
        base 95, kept inside 90 to 99; two losses -> 92, 3 wins -> 98, a cup final -> 99
   check: the value of a player of your club at 038df6c1  as expected
   RESULT: installed. In a Master League match the Team Spirit of every player of your club is worked out from the club's form before the match and kept inside 90 to 99; it is 95 until the first match.
   ```
4. Play a match. One line is written for it, and the game plan screen of your club reads
   the same number:
   ```
   MLTeamSpirit 6: your club is 114838 (Sider team 7). RIVALS uses packed club ids; copy the RIVALS id shown for the opponent.
   MLTeamSpirit 6: at home against club 8 (RIVALS id 131072), competition 29 round 4, form D D D D D -> 97  [big match (+2)]
   MLTeamSpirit 6: at home against club 8 (RIVALS id 131072), competition 30 round 53, form none -> 99  [final (99)]
   ```

`RESULT: nothing written. ...` with a `DIFFERENT` line: the game does not hold the
expected code at that place; send the log. To undo, remove the line from `sider.ini`.

### How to see it working in a career

V5's indexed-table fix is emulator-tested, not live-verified. **Recalculation runs at
match setup** (`set_conditions` / `after_set_conditions`), not on a post-match home
screen. Set up the next played match before judging a change after a win. A single
win in an otherwise empty history gives 96, but a full weighted history can balance
to 95; no rule promises a visible increase after every win. Start with the log:

1. **The value moves.** Play three or four matches of a career and read the lines: the
   form string (`W W D L W`, newest first) is the last matches of your club, and the
   number after `->` is the value. Lose two in a row: 92. Win three in a row: 98 or 99.
2. **The screen agrees.** Open the game plan of your club before a match: Team Spirit
   reads the number of the last line of the log (the screen asks the same function).
3. **The rules of a career are read, not guessed.** The line names the competition and
   the round of the match: both come from the record of the match in the career's own
   match records, the one Sider's `match_id` is the number of (the same number the game
   asks a record by, `match_record` of section 5.1). The kind of that competition — a
   league or a cup — is read from the competition record that carries its number, the way
   the game's own look-up does; Sider's `tournament_id` is not it, that is a number of the
   game's own. If the record does not hold the two clubs of the match, the round is not
   known, the cup rules cannot fire, and the log says so once; the other rules are not
   affected.
4. **A derby.** The three rivals of your club record (`+0x514`) are read. In the two
   saves of `../ML saves/` every club record names no rival at all, so a derby may never
   fire; copy the opponent's labelled `RIVALS id` from a match line into the setting
   `RIVALS` to make it a derby whatever the game says. This remains a packed career id,
   not Sider's decoded team number.
5. **A big match.** The places in the league are counted from the matches of the season
   in the records, so they are the league table of the game's own results.

### What the test shows

`python3 test_spirit.py <PES2017.exe>` (historical first-ten-check output below):

```
ok 1: without the module the game gives the made-up player a value below 99 in every mode (48 cases: he knows the tactics at 3, 30, 60, 90, plays a position rated A, B or C), lower out of position, and the match set-up stores it for 3 formations x 13 positions
ok 2: the module writes the 12 bytes of the one place and nothing else, and the byte in them is the base value 95
ok 3: with the module the same code gives 95 in Master League (mode numbers 19 and 40), whatever the player knows and wherever he plays, and the match reads it for all 3 formations x 13 positions; in League mode and mode kind 21 the values are as without the module. It gives back ebx, esi and edi as it was given them and leaves the stack where the game leaves it
ok 4: the form of the club is the last five matches (7 careers written out: nothing played, one loss, two losses, three wins, five wins, five losses, a draw and a win), and every rule that fires is named in the log
ok 5: the last round of a cup, the round before it, a rival the club record names and a league match of two clubs at the top raise the value; an early round, a club that is no rival and a match against a club in the middle do not
ok 6: a match of two other clubs and a mode that is not a career leave the value where it is
ok 7: every value the byte holds, 93 here, is what the game gives a player of your club in Master League and what the match reads for 3 formations x 13 positions; the other modes keep the value the game works out
ok 8: with one byte of the place changed (12 cases) or the change in already nothing is written and the place is named; a write that does not go in is reported
ok 9: with MLMoney.lua and MLTransfers.lua in the same game, above or below them, all three are installed and the value is 95
ok 10: the kind of a competition is the one of the record that carries its number, not the one of the record that sits at that number's place in the table (a league was put in the cup's place and the cup rules still fired); a competition the table does not hold is no cup
```

`ok 4` to `ok 7` fill a mode data block of the emulator with match records, competition
records, club records with rivals and a day of the year, and then call the function the
module registers for the conditions of a match with a Sider `ctx` — the same call Sider
makes, using decoded `ctx.home_team`/`ctx.away_team` numbers, not packed career ids.
The original v2 tests used packed callback ids and did not expose the double decoding.
`ok 11`–`ok 13` also cover away matches, packed RIVALS compatibility, u16 date widths,
future seasons, and the final table batches. V5 also tests modes 0/1/2, bounds and
real-save club-table replays; sparse indexed primary/rival/competition tails produce
96/98/99 for one-win/derby/final setups without changing career bytes, alone and with
all eight modules installed. `ok 2` also checks the five bytes of version 1's place are still the game's own:
with version 1's jump in them no player reaches the branch, and the log says so.

Not shown: the code that multiplies the abilities (`fcn_02f903a7`) and the screen were
not run, and no match was played. Nothing ran in the game.

### Version 1: Team Spirit has no effect in a match

Version 1 put one jump, five bytes at `0x038df528`, at the start of the same branch, to
the function's own "return 99" — the answer a player of another club gets. With it the
match set-up stored 99 for every player, formation and position, the game plan screen
showed 99, the other modes with Team Spirit (mode kind 21, taken to be myClub) went
another way through the function and were untouched, and nothing was saved. It had no
settings. Version 2 does the same thing with a number of the club's own; the two must not
be installed together, and version 2 says so in the log if version 1's bytes are there.
