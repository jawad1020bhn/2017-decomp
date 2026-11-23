# Master League modules for Sider 3.6.0

These Lua modules change the running game, not `PES2017.exe` on disk. For the unmodified game's structures and algorithms, use the [Master League guide](../MASTER_LEAGUE.md). For patch ranges, load-order tests and rollback limits, use the [safety audit](SAFETY_AUDIT.md).

**Jump to:** [Install](#install-and-verify) · [Modules and tests](#find-the-implementation-and-the-test) · [Developer workflow](#developer-workflow) · [Sider API](#what-was-looked-at-in-siderdll) · [Patch reservations](#notes-for-the-next-module)

## Install and verify

1. Back up the saves, installed modules and `sider.ini`. The supported EXE has SHA-256 `44b0caaac6703459f1a674ab7defc98d39613008b9254646f2543431fa9d954f`. Don't bypass a fingerprint or occupied-memory check to support another build.
2. Copy the desired `.lua` files into `modules` next to `sider.exe`. Keep other Sider settings. Use each enabled line **once**; run Check before any patcher, and **Money before Transfers**. Python scripts are development tools, not Sider modules.

```ini
lua.enabled = 1
lua.module = "MLCheck.lua"
lua.module = "MLMoney.lua"
lua.module = "MLYear.lua"
lua.module = "MLTransfers.lua"
lua.module = "MLSimMatch.lua"
lua.module = "MLTeamSpirit.lua"
lua.module = "MLSimToDate.lua"
lua.module = "MLGrowth.lua"
```

3. Fully restart PES and Sider. In `sider.log`, expect `RESULT: 6 of 6 as expected` for Check and `RESULT: installed` for each enabled patcher. **Installation is not a gameplay test.** On a write or restore failure, exit without saving. To uninstall, remove the module line and restart; this does not undo changes already saved in a career.

## Find the implementation and the test

Defaults and validation live in the linked Lua files. The references below retain the earlier behavior, settings explanations, test evidence and limits; old version numbers in test transcripts describe those runs, not today's defaults.

| Module | What changes / first useful check | Detailed reference or tests |
|---|---|---|
| [MLCheck](MLCheck.lua) | Read-only check of the AI rating window and transfer-fee code. Six matches confirm those locations, not the whole executable. | [Build checks and live observations](#result-in-the-game-14-november-2026); `test_module.py` |
| [MLMoney](MLMoney.lua) | Player values, salaries, contract years, budgets, income and prizes. With sufficient funds, tap **F6** in a focused ML game to move 4M of transfer funds into 1M of salary room; **F7** reverses it. Reopen Finance to refresh. | [Formulas, settings and verification](#mlmoney-values-wages-and-budgets); `money_cave.py`, `money_keys.py`, `test_money.py` |
| [MLYear](MLYear.lua) | A **new** career starts in 2026/27 by default. An existing career keeps its year. | [Year and contract boundaries](#mlyearlua-version-1-a-new-career-starts-in-202627); `test_year.py` |
| [MLTransfers](MLTransfers.lua) | AI recruitment: price ceilings, personas, rivals, squad needs, offers, sporting projects and trimming. Requires the installed Money v7 valuation hook. To assess results, compare saves across a transfer window. | [Recruitment rules and observed windows](#mltransfers-ai-recruitment); `test_transfers.py`, `test_need.py`, `test_offer.py`, `test_projects.py`, `test_trim.py` |
| [MLSimMatch](MLSimMatch.lua) | Skip Match and AI simulation: strength-based results, substitutions, ratings, scorers, extra time, penalties, cards, fatigue and injury. Not the played-match Team Spirit calculation. | [Simulation and tuning](#mlsimmatch-simulated-matches); `sim_cave.py`, `test_sim.py` |
| [MLTeamSpirit](MLTeamSpirit.lua) | **v6:** updates form at **played match setup** when exactly one controller-slot-0 record matches either participant. An unrelated marked club no longer blocks it. If ownership is unclear, it keeps the previous value. Check the matchup, form and final 90–99 value in the log. | [Rules, examples and native reader](#mlteamspiritlua-version-6-team-spirit-follows-the-form-of-your-club); `test_spirit.py` |
| [MLSimToDate](MLSimToDate.lua) | Off by default. In **Schedule**, highlight a future day, press **F8**, check the heading, then advance normally. **F9** cancels; **F10** toggles stopping for news. “Switched off” does not mean the hooks were uninstalled. | [Controls, early stops and optional date file](#install-and-use-the-in-game-control); `test_simdate.py`, `test_simdate_calendar.py` |
| [MLGrowth](MLGrowth.lua) | **v8:** the tracked squad's exp and training follow an age curve x potential x playtime; every other player gets a hash-driven season on the attributes his position is rated by, with personal ceilings and five decline families. Nothing is stored, so a reload changes nothing. Check a season transition, not just startup OVR. | [Growth mechanics, §12](../MASTER_LEAGUE.md#122-the-growth-system); `growth_cave.py`, `test_growth.py`, `growth_twin.py` |

## Developer workflow

Run from `pes database/exe/sider` with the matching executable. These checks use Lua and CPU emulation; they don't launch PES on Windows.

```sh
python3 -m pip install lupa unicorn capstone keystone-engine
python3 test_spirit.py /path/to/PES2017.exe    # match callbacks and native reader
python3 test_safety.py /path/to/PES2017.exe    # load orders, write overlap and rollback
```

- **Changing a hook:** check the [Sider API and reserved ranges](#what-was-looked-at-in-siderdll), keep generator output and embedded Lua bytes in sync, run the feature test and then the safety suite. A host API error can interrupt rollback: Sider's sandbox has no `pcall`.
- **Comparing a real window:** [window_transfers.py](window_transfers.py) reads a save and writes a CSV. A `paid` entry uses the user club's recorded payment; a `formula` entry is an estimate, not the actual AI transfer price. See [report instructions and limitations](#window_transferspy-the-transfers-of-the-current-window-the-most-expensive-first).
- **Current test boundary:** Spirit v6 passed the match regressions, four club-table replays and the eight-module safety run; the affected Windows career wasn't tested. A separate `test_growth.py` season-growth assertion also failed with the pre-change test. Don't report the whole suite as green or change growth rates to make an unexplained assertion pass.
- **Tracing an earlier result:** the [tool inventory and safety-fix history](#earlier-safety-fixes--17-november-2026) and the module sections preserve the original test descriptions, observations and version-specific behavior.


## Install and run `MLCheck.lua`

Install Check first as in [Install and verify](#install-and-verify). At the title screen, inspect `sider.log`.

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

### Verify the career year

Set `START_YEAR` (2000–2100). With the default and a July season, a **new** career should start on 1 July 2026 with contracts ending in 2027 or later. Removing the module restores the stock start for new careers, not for an existing save.

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

### Verify the match callback

Play a match. One line is written for it, and the game plan screen of your club reads
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

## `window_transfers.py`: the transfers of the current window, the most expensive first

It reads a save file. It does not touch the game or the save.

```
pip install lupa unicorn
python3 window_transfers.py <PES2017.exe> <save>
```

1. In the game, save the career **while the window is open**. Its last day (31 August,
   31 January) is fine.
2. Run the line above on the save file (`ML00000013` or the like, in the `save` folder
   of the game). The exe is only read: the game's own rating code runs on each player.
3. It writes `<save>.transfers.csv` next to the save (or to a third argument) and
   prints the 20 most expensive. The file opens in Excel or LibreOffice.

`../ML saves/2nd test/ML00000013 (after).transfers.csv` is the file for the save of that
folder (31 August 2024, 438 transfers). Its first lines:

```
price,how,player,age,position,rating,from,to,date
55263500,paid,Endrick,20,CF,80,Real Madrid CF,SSC Napoli,2024-07-20
52344600,formula,Donyell Malen,27,CF,83,AS Roma,FC Bayern München,2024-07-19
41722000,formula,Angelo Stiller,25,DMF,83,VfB Stuttgart,TSG 1899 Hoffenheim,2024-08-01
32752800,paid,David Neres,29,RWF,81,SSC Napoli,CR Flamengo,2024-07-17
```

**The price, and what `how` says.** The game keeps a price only for the deals of your
own club. A computer club has no money: the game works a fee out and drops it
(`../MASTER_LEAGUE.md`, 9.7).

| `how` | the price is |
|---|---|
| `paid` | a deal of your club: the amount of its line in your accounts. Exact |
| `free` | the player had no club: 0 |
| `formula` | worked out again the way the game did, with the settings of the `MLMoney.lua` **in this folder**. The game then moved it up or down by up to 19 percent at random; that part is lost. Rating, age and popularity are those of the save, not of the day of the move |

For the six deals of the save above in which your club bought from or sold to a club,
what was paid is 0.97 to 1.21 times what the formula gives. So `formula` is the right
size, not the exact number. If you changed settings in your copy of `MLMoney.lua`, put
your copy into this folder first. A career played without `MLMoney.lua` has other
prices; that case is not built.

**Where it comes from in the save** (all seen in the four saves of `../ML saves/`, see
`../MASTER_LEAGUE.md`, 13): a transfer is a player with a club whose contract began
inside the window (1 July to 31 August, or January) that holds the date of the save.
The club he left stands in his record while the window is open.

**After the window has closed** the game clears the club left for nearly all players
(in the save of 15 September it is still there for 5 of 511). The script then says
`CLOSED`, writes `?` as the club left and gives every signing a price by the formula,
because a free signing can no longer be told from a bought one. Save before the window
closes.

`python3 test_transfers.py <PES2017.exe>` (8 seconds):

```
ok 1: the save of 31 August alone gives the 438 moves that the saves of 1 July and 31 August show together, each with the club left and the club joined; 254 have a price by the formula, 176 were without a club and cost nothing, 8 are deals of SSC Napoli with the amounts of its account lines; the most expensive is first (Endrick, 55,263,500)
ok 2: the save of 15 September, after the window: the same 511 players as its two saves show, each with the club joined; the club left is still in the save for 5 of them and is "?" for the others, and none is called free
ok 3: a save of the first day of a new career lists nothing (the 19,921 contracts dated that day are not signings); the window is January up to 30 June and July to August after; the file has the nine columns and the 438 rows, the most expensive first
```

18 faults were planted in the script one at a time (cheapest first, a wrong place in
the save, the sign of an amount kept, free signings priced, your deals by the formula,
the first day of a career counted, and so on). The test failed on 16. The two it cannot
notice are two guards that no save here needs: "a player without a club is not a
signing" and "not after the last day of the window".

Not shown: a January window, a second season (whether a renewed contract gets a new
start day and so looks like a signing is not known), a loan, a save from a career
without `MLMoney.lua`, and Windows (it ran on Linux only).

## `MLSimToDate.lua`, version 4: "Sim to Date"

**Experimental: tested in a CPU emulator only, not in Windows, Sider or the running
game.** The Schedule controls, status text, real matches and save effects still need
to be verified. Back up your Master League save before trying it, and do not overwrite
the only copy until you have checked the results.

### Install and use the in-game control

1. Make a copy of your Master League save (`ML00000013` or similar).
2. Copy `MLSimToDate.lua` into the `modules` folder next to `sider.exe`. Add this line
   to `sider.ini`, with `lua.enabled = 1`:
   ```
   lua.module = "MLSimToDate.lua"
   ```
   This is made for the repository's `PES2017.exe` (SHA-256
   `44b0caaac6703459f1a674ab7defc98d39613008b9254646f2543431fa9d954f`). The module
   checks the code and free memory at startup and refuses a mismatch. No additional
   module, text file or Sider overlay is needed for the in-game control.
3. Start the game through Sider and check `sider.log` for `RESULT: installed`. With
   the default settings and no date file it starts **off**. An existing
   `MLSimToDate.txt` or a nonzero `SIM_YEAR` can instead start it with a target; see
   "Optional file controls" below.
4. Load the copied career. Open **Schedule** and use the game's normal calendar controls
   to highlight a future day in the current season. With the game in focus, press **F8**
   on the keyboard (on some laptops, Fn+F8). The calendar heading is intended to show
   `SIM DD.MM.YYYY | F9 OFF | NEWS ON`; confirm that it shows the date you selected
   before proceeding. Press F8 on another future day to replace the target. Selecting
   today or an earlier day cancels the target and shows
   `FUTURE DATE ONLY | SIM OFF | NEWS ON`.
5. Return to the Master League menu and use the normal **advance** action. Matches
   before the target are simulated as Skip Match; the match on the arrival day is left
   for you. The game may stop early for news, a big match (if enabled), or its own
   events such as a transfer window; handle the event and advance again. It finishes
   on the first natural stop **on or after** the selected date.
6. To cancel while at a menu, open Schedule and press **F9**. Check for
   `SIM OFF | F8 SET | NEWS ON` (or `NEWS OFF`) before advancing. A date selected in
   Schedule also switches off automatically when the target is reached. There is no
   controller shortcut: F8/F9/F10 require a keyboard; you can still navigate the
   calendar with the game's controls.
7. **F10** in Schedule switches stopping for news on and off while the game runs: the
   heading shows `NEWS ON` or `NEWS OFF`, and the next day advanced follows it. This
   lasts until the game is restarted; the `STOP_FOR_NEWS` setting only decides its
   state at startup.

**Important:** an unfinished target is held in game memory, not tied to a specific
save. Cancel it before loading another Master League in the same session or it may
apply there too. A match on the day you start is not skipped for you; play or skip it
normally first. The game's calendar has no 29 February. The calendar control only
selects within the displayed season; choose another target after a season change for a
longer run.

If F8/F9/F10 or the confirmation text do not work, **do not advance on the assumption
that a target was set**. Check that the game window is focused, the Schedule screen is
ready, and `sider.log` contains `RESULT: installed`. If a clearly future date shows
`FUTURE DATE ONLY`, the calendar's season bounds may not match this module; do not
proceed. A `DIFFERENT` or `NOT EMPTY` check means this exe or another mod does not
match; the module writes nothing. For any failed write, restart the game and remove
the module until the problem is understood.

### Behavior and optional settings

- `STOP_FOR_NEWS = true` by default: on days without your match it stops for the same
  news a normal advance would. Set it to `false` in the Lua file to skip those stops,
  or switch it in Schedule with **F10**; the skipped screens are not shown and nobody
  answers an offer. The F10 switch is held in game memory until the game restarts.
- `STOP_AT_BIG_MATCHES = false` by default: all matches before the target are simulated.
  `true` asks the game's own test to stop at important matches; its full list is not
  known. Save changes to these settings before starting the game.
- Master League only. This revision also fixes the older v2 mode check: the game's raw
  mode numbers are 19 and 40, whereas 12 is the derived mode *kind*.
- If `MLSimMatch.lua` is installed, its simulated-match rules apply as with Skip Match.

### Optional file controls (existing v2 behavior)

You can still set `SIM_YEAR`, `SIM_MONTH`, `SIM_DAY` in the Lua file before launch, or
put `MLSimToDate.txt` **next to `sider.exe`** containing a date such as `2025-03-15`
or `15.3.2025`, or `off`. If that file exists at startup, it overrides the Lua date.
Unlike a calendar selection, a Lua/file target remains in force after it is reached and
can affect other careers in that session. F9 cancels it in memory, but does **not** edit
the file or Lua settings: the configured date returns on the next launch. Write `off`
to the file if one exists, or set `SIM_YEAR = 0` when there is no file, to start off again.

If the file existed when Sider started, changing it while the game runs is checked on
the next Sider `livecpk_make_key` file-load callback, at most once a second; the latest
valid file change replaces any calendar target. An invalid file at startup starts off;
an invalid or missing file during play leaves the current target unchanged. `sider.log`
reports changes. File updates require `livecpk.enabled = 1` and may be delayed by
`address-cache.enabled = 1`; setting that cache to 0 allows more callbacks but can slow
other modules. If the file did not exist at startup it is not monitored until restart.
A non-English Sider folder path may prevent the file being found. Change the file at a
menu, not during an advance; reopen Schedule and verify the displayed target after a
file change. None of these callback/cache requirements apply to F8/F9/F10.

### How and what was checked

The existing day-loop hook at `0x0360b786` uses the game's keep-advancing and Skip Match
switches (`../MASTER_LEAGUE.md`, section 3.1). Two additional checked call sites in
Schedule poll `GetAsyncKeyState` only after the game reports the screen ready and only
while a Master League window belonging to the game has focus. The game's selected day,
season bounds and date conversion provide the target and heading. Mutable state is kept
in a checked, empty writable `.text` stub; the calendar block (the Schedule hooks and the
strings they print) uses a checked, empty run of zeros in `.trace` at
`0x03fc8000`-`0x03fc88ff`, and the day-loop routine uses checked, empty space in `.link`
at `0x047d6f60`-`0x047d6fe9`. All three hooks remain inert until installation and event registration complete;
a failed hook write attempts to restore earlier hooks. The module does not patch the exe
on disk. Reserved code padding and the initial text buffer are marked occupied to help
other mods detect them; this still assumes no other mod later overwrites those regions.

From this directory, with `pip install lupa unicorn keystone-engine capstone`:

```
python3 test_simdate.py <PES2017.exe>
python3 test_simdate_calendar.py <PES2017.exe>
```

The tests run the real game's stop test, day loop, Schedule input handler and date
conversion in an emulator with stand-ins for days, Windows, controller input and UI.
They cover 288 synthetic multi-day runs, 15,330 calendar choices across year/season
boundaries, both Master League mode numbers, cancel/invalid/focus cases, the F10
stop-for-news switch through the real input handler and the byte the day loop reads,
startup and write failures, file overrides, and coexistence with the other four
modules. In the calendar test the `.link` page (`0x047d6000`, the day-loop routine) is
marked read/execute and the `.text` stub read/write, so runtime state writes must work
without a writable code page; the calendar block itself sits in `.trace`, which the
executable already marks read/write/execute. These tests do **not** establish that the interface is
visible or responsive in the real game, that a simulated match is booked correctly in a
real save, or that Sider's file callbacks arrive at a particular time.

## MLTransfers: AI recruitment

Version 2 ran in the game: one transfer window played with it was read from two save
files (see "What the second window showed" below). **Versions 3 to 9 have run in the
emulator only.** It needs `MLMoney.lua` version 7 as before. The price ceiling of
version 1 is still there and is described in the next section.

### New in version 9: squad pressure

**What the game does.** A computer club that is asked for a player does not look at how
many players it has for his position. The one exception is the goalkeeper: when a club
looks for a goalkeeper, the game skips a goalkeeper whose club has two or fewer who are
not in a deal (`ai_candidates`, `0x0365f920`; `MASTER_LEAGUE.md` 9.6). Up to version 8
the module was the same: a club's `keeps` (how often it refuses to let a player go) did
not depend on the squad.

**What `SQUAD_PRESSURE` adds.** The module counts the squad of the selling club by
group: goalkeepers, defenders (CB, LB, RB), midfielders (DMF, CMF, LMF, RMF, AMF) and
forwards (LWF, RWF, SS, CF), by the position a player is registered for. If the club
has more players of the asked player's group than the limit, its `keeps` counts
`keeps_drop` lower for him, not below 0.

    local SQUAD_PRESSURE = { positions = { GK = 3, DF = 8, MF = 9, FW = 6 }, keeps_drop = 40 }

1. The drop is for **every** player of a group that is above its limit, not only for
   the last ones: the routine does not know which of seven forwards is the seventh.
   What protects the best ones is `KEEP_BEST`: the drop comes after what `KEEP_BEST`
   adds. With `KEEP_BEST = { 4, 12, 2 }` a forward rated as high as his club's eleven,
   at a club with `keeps` 30, stands at 30 + 4 x 12 = 78 and falls to 38; a reserve
   stands at 30 and falls to 0.
2. With the numbers above the drop (40) is as large as the highest `keeps` of the
   personas (5 to 40; `PERSONA_SPREAD` can lift a 40 to 48 for one club). So a club
   above a limit refuses a player of that group who is not first team never or
   almost never. A smaller `keeps_drop` makes it softer.
3. Players in a deal (bought or sold, not yet moved) are not counted, as in the
   game's own goalkeeper rule. A player on the transfer list or without a contract
   never reaches `keeps`, so nothing changes for him.
4. It only lets players go. The rule of `SELL_SIDE` that a club with 23 or fewer
   players sells nobody stays, and so do the price ceiling, the persona of the buyer,
   scouting and the rivals.
5. It needs `PERSONA = true`: without personas `keeps` is 0 for every club and there
   is nothing to lower.

| setting | as shipped; meaning |
|---|---|
| `SQUAD_PRESSURE` | the line above; `false`, or `keeps_drop = 0`: off, as up to version 8 |
| `positions`: `GK`, `DF`, `MF`, `FW` (0 to 99 each) | 3, 8, 9, 6: the most players of the group a club can have without the drop. All four must be there |
| `keeps_drop` (0 to 100) | 40: how much lower `keeps` counts, in points of 100 |

**New memory.** The routine of version 8 fills its memory to the last byte, so the
count is a routine of its own: 178 bytes in a fifth piece of unused memory,
`0x047d6d40`-`0x047d6e4f` (272 bytes: the drop, the four limits, the group of each of
the 13 positions, the routine), right behind the 0x7f0 bytes kept for the offers for
your players and before `MLGrowth.lua` (`0x047d6e50`). No new place of the game's code
is changed; the routine of version 8 calls it where it compared the draw with `keeps`
(two other instructions of that routine were written shorter to make room for the
call). It walks the squad only
when the answer depends on it (a draw from `keeps` minus the drop to `keeps` minus 1).
The memory is written with every setting, also with `SQUAD_PRESSURE = false` (drop 0),
because the main routine always calls it. The module checks three more functions of
the game and one of its constants before it writes (`team`, `player`, `no player`,
`no player id` in the log).

**What the test shows** (`test_money.py`, parts of `ok 3` and `ok 4`): the routine
alone gives the answer of `money_cave.pressed_keeps` in 3,000 made-up cases for each of
six settings (off, drop 0, limits no squad is above, limits every squad is above, a
small drop, numbers that are rounded), looks at the squad only when it must, asks for
each counted player once and keeps the registers of the choosing code; the choosing
code with it lists the players the model lists; in the model a club with one player
too many of a group lets go about 155 of 1,500 players of that group that it keeps
otherwise, and no player of another group. Seven faulty settings are refused.
`python3 planted_faults.py <exe> pressure` flips every bit of the routine: see
`planted_faults.py` for the count. **Not shown:** how many more players move in a real
window, and whether squads thin out too far over seasons; no window was played with it.

To go back to version 8: `git show 3a63fde:"pes database/exe/sider/MLTransfers.lua"`.

### New in version 9: the mood of a deal

**What the game does.** `keeps` — how often a club refuses to let a player go — is the same
number every day of a career and for every buyer. A club's answer to the same player is
fixed from the first day of the window to the last, and the same club refuses him against
any club that asks.

**What `DEAL_MOOD` adds** (no place of the game's code is changed: it is one routine that the
ceiling routine calls, 118 bytes in a sixth piece of memory):

    local DEAL_MOOD = { mood = 8, style = { seller = -12, trader = -3, builder = 5, hoarder = 12 } }

1. **the mood of the deal** — from the player, the two clubs and the date of the keys of the
   module (the year and month of the search) one byte from 0 to 99 is drawn, and it moves
   `keeps` by `mood x (byte/window)` between `-mood` and `+mood` percent, 0 in the middle.
   The same player and the same two clubs are not answered the same way by two dates, so a
   club that refuses him in August may let him go in January, and the day of the career in
   the key makes it deterministic: nothing is stored, a reload gives the same deal;
2. **the style of the seller** — the low two bits of that same byte name one of four styles,
   and its percent is added to `keeps` for that club: a club whose style is `hoarder` asks
   for more, one whose style is `seller` asks for less. It is not a second personality: it
   leans on the `keeps` its persona already has.

The amount is clamped to 0 to 96 and 0 to 96 percent, and it is added **before**
`SQUAD_PRESSURE` and before the price ceiling, so all the other rules keep their meanings.
A player without a club has no mood (there is no club to have one), and with
`DEAL_MOOD = false` the sixth piece of memory is left as zeros: its first dword
`MOOD_ON` is 0 and the ceiling routine does not call the routine at all.

| setting | as shipped; meaning |
|---|---|
| `DEAL_MOOD` | the line above; `false`: off, as up to version 9 |
| `mood` (0 to 96) | 8: the most the mood of a deal moves `keeps`, in percent |
| `style`: `seller`, `trader`, `builder`, `hoarder` (-96 to 96) | -12, -3, 5, 12: what each style adds to `keeps` |

**Where it lives.** The routine sits at `0x03fc8910` (118 bytes) in the sixth piece of
memory, `0x03fc8900`-`0x03fc92ff` (0xa00 bytes), in the run of zeros of `.trace` between
`MLSimToDate.lua`'s `0x03fc8000`-`0x03fc88ff` and the next block; the dwords at
`0x03fc8900` (`MOOD_ON`), `0x03fc8904` (window) and `0x03fc8908` (the four styles) are the
numbers, and the write is checked before it happens as every other piece of memory is. No
place of the game's code is changed for it.

**What the test shows** (`test_money.py`, `ok 6`): the routine alone, entered with a frame
laid out as the ceiling routine's, gives the answer of `money_cave.mood` in 1,200 made-up
cases (any window 0 to 96, any four styles, any two clubs, any player and date, keeps 0 to
96, the clamps at 0 and 96, a player without a club and `MOOD_ON` 0). `ok 3` runs the
choosing code with every optional part alone, this one included.

### New in version 8: the whole rules for the club that makes an offer

Version 7 only kept a rival of yours from making an offer. Version 8 makes the chooser
apply the rules the selling side already had, on the **buying** club: with `INCOMING = true`
the club that makes an offer for one of your players is the club nearest the game's own
slot (in `[club + 0x314] >> 7`) among those that pass all four:

1. **no rival** — the pair is not in `RIVALS` (as in version 7);
2. **its persona wants him** — the age band moved by `AGE_SHIFT` for that club, the
   ambition and the prestige of the club, and the strictness of its persona about a player
   without a contract or one listed by his club: the same genes, the same draw and the same
   tables as the selling side, so a club that would never look at such a player in
   `ai_candidates` does not offer for him either;
3. **a place in its plan** — the buyer's own plan record (`mode data + 0xccb80c`, `0x118`
   bytes each, in the club ranking order, count at `+0xd06434`) has a free slot
   (`state` 0 or 7, with a `kind`) for the player's position, or the byte `+0x109` carries
   the position need the module wrote in version 6; a club that plans nothing for that
   position and whose eleven is not in need of it does not offer;
4. **it can afford him** — the value `MLMoney.lua` gives the player, less the `CEILING_FREE`
   or `CEILING_LISTED` discount, is at most `CEILING[level] x wealth x (1 + premium + panic)`,
   the amount that club's price ceiling allows: a second-division club does not bid for a
   player it could never sign, and a club with no ceiling (`CEILING[level]` = `0xffffffff`)
   passes whatever his price.

**The "more than 16 players" test is gone.** Version 7 guessed it from the squad count.
Version 8 leaves the room of the substitute to the game: the look-up answers a club id,
the routine that creates the offer (`fcn_03652df0`) runs its own room test on it, and if
that club cannot take another player the offer is not made: the club the look-up answered
is the club the game judges, so the count is never second-guessed by the module. The club nearest
the game's slot with a place in its plan for the player's position is almost always a club
with room; nothing in the module assumes it.

**What does not change.** Not one offer is added and the number of offers is the game's:
the module answers the same look-up, once, and returns the game's own club when no club
passes (so where nothing would take the player, the offer the game would have made is the
one that is made).
Nothing is written to the mode data, so no slot number has to be known. **The fee is not
touched** — `MLMoney.lua` computes it from the value of the player exactly as on any
transfer (§ "the fee"), and neither salary nor premium is written on this path.

**Where it lives.** The look-up `fcn_0381e2eb` is entered at its prologue: the module's
code sits at `0x047d6550`-`0x047d6d3f` (the 0x7f0 bytes after the position need;
`0x047d6d06` is its last used byte, 0x39 free) and `0x0381e2eb` starts with `e9 rel32`
and one `nop`. That place holds zeros in the file, and it is clear of `MLGrowth.lua`'s
`0x047d6e50`-`0x047d6ec3` and `0x047d6efe`-`0x047d6f4b`, and of `MLSimToDate.lua`'s
day-loop hook at
`0x047d6f60`-`0x047d6fe9`. **`MLSimToDate.lua` version 3 had its Schedule hooks here**
(`0x047d6550`-`0x047d6e4f`), and the two modules then refused each other — the one that
came second found the memory not empty and wrote nothing; version 4 moved that calendar
block to the `.trace` run at `0x03fc8000`-`0x03fc88ff`, so the two install together now.
With `INCOMING = false` this piece is not touched at all. The entry keeps every register and flag, answers the game's own
code for any other key, and falls back to the game's own prologue when the game's club can afford him. When redirected,
both the look-up result and the caller's buyer argument (`[ebp + 0xc]`) are updated to the chosen club; when no club
passes and the game's club cannot afford him, the deal is cleanly aborted so insolvent clubs cannot bid.
The source is `sider/incoming.c` (gcc `-m32`, `offer_source.py` cleans the asm for
keystone); `money_cave.py build` assembles it and checks the bytes the module ships.

**What the tests show.** `sider/test_offer.py` runs the real look-up at that place on a
made-up mode data (club table, plan records, club ranking, personas, rivals, the player's
record) for 200 cases of 32 clubs and compares the club the game answers with
`money_cave.offer_pick` (the same rules in Python): the game's own club is kept in 153 of
them, another club answers in 25, and in 22 the game's slot holds no club at all and the
game's own answer stands. One case is asked again on twelve days of the career, and the
club answered changes with the day, as the rules say. Not run in the game: the club table
of a real career, `[0x0251f85c]` at the moment of the offer and the result of
`fcn_03889077` (the count the room test uses) are read from the disassembly, not from a
running career.

### New in version 9: the same rules as the transfers of the computer clubs

Version 8 chose the club by four rules of its own. Version 9 makes them the rules of
`ai_candidates` themselves (`money_cave.accepts`), so that a club makes an offer for one
of your players on the same grounds on which it signs one from another computer club:

* **scouting** — a club knows only `knows` percent of the players; a listed player, one
  rated `KNOWN_FROM` or more and one of a popularity of `KNOWN_FAME` or more are known to
  every club (`SCOUTING`, `KNOWN_FROM`, `KNOWN_FAME`);
* **the place it buys from** — for a position and a time its persona looks either among
  the players without a contract, the listed players or those of other clubs (`free`,
  `listed`, `clubs`), and it offers only where it is looking. A club whose plan has a free
  place or whose eleven is in need of that position looks in the place its persona names
  second when the draw falls outside all three (`THEN_1`, the second search of its
  persona), as in `ai_candidates`;
* **the day of the career** — every draw of the rules (scouting, the place it buys from,
  the age, the rating it makes of him, the stretch of the ceiling) takes the day into it,
  the word at `mode data + 0xc2cbb0` with the year behind it, so the club that bids for a
  player is not the same club on every day of the window. Before, the key of a draw was
  the player and the club only, which is why the same club came back again and again;
* **the stretch above the ceiling** — above the ceiling a club takes him less and less
  often (`CEILING_STRETCH` with `premium`) instead of never, and its `fame`, its `panic`
  and `CEILING_NEED` are in the amount as they are in the transfers of the computer clubs;
* **a club in want of him** — a club whose position need marked his position is a club in
  want of him: it does not mind his age or the rating it makes of him, and it goes
  further for him. In `ai_candidates` that is what a club with too small a squad does.

The four pieces of memory are grown to make room: the offers keep `0x047d6550`-`0x047d6d3f`
(0x7f0 bytes, was 0x700) and the squad pressure moved to `0x047d6d40`-`0x047d6e4f`, so
that the two still end where `MLGrowth.lua` begins. Moving it changes one byte of the
routine of version 8 (the address of the call to the squad pressure) and the addresses in
the 178 bytes of that routine, and nothing else.

### New in version 7: offers for your players

**What the game does.** Which computer club makes an offer for a player of yours is
decided by a slot number: a club look-up (`fcn_0381e2eb`) answers the club that sits at
that slot of the competition in hand, and the routine that creates the offer
(`fcn_03652df0`) asks it for the buying club. Nothing in that path looks at a price, a
squad need, a persona or a rivalry, and the offer carries no fee: the fee of the move is
computed later, from the value `MLMoney.lua` gives the player (section "the fee").

**What `INCOMING = true` adds** (one new place in the game's code): the module answers
that look-up itself, for that one key. Version 7 only refused a rival of yours and, when
the game's club was one, answered the club of the nearest slot that was no rival, was not
the club whose player it is and counted more than 16 players. **Version 8 replaced that
rule by the whole rules of the selling side** — persona, plan and affordability, with the
room test left to the game: see "New in version 8" above. Nothing is added to the offers
and the fee is not touched.

### New in version 6: position need

**What the game does.** A computer club looks for a player in two cases only: a place
of its eleven has nobody, or it counts fewer than 25 players. In the second case it
takes positions from a list of its weakest outfield players; the goalkeeper is not in
that list. So an eleven rated 85 with a goalkeeper rated 75 looks for nobody, and a
club with 28 players never looks for a better right back.

**What `NEED = true` adds** (two new places in the game's code, 300 bytes of new code):

1. Each time a club plans (the first day of the season, 1 September, 1 February, when
   it is the club's turn), the module looks at the eleven the game has just picked for
   it. If the weakest player of the eleven, the goalkeeper included, stands `NEED_GAP`
   rating points or more below the mean of the others, the club gets one more position
   to look for: his.
2. This does not depend on the size of the squad. The game's own limit stays: a club
   that counts 32 players (with the players it has already chosen) signs nobody.
3. For that position the club takes only a player rated `NEED_BETTER` or more above the
   starter it has. The rating is the same one in both cases (the game's rating function
   for a player at a position).

Everything else still counts for such a signing: the price ceiling, the persona, the
selling club, scouting, rivals. The module only adds the position and raises the
lowest rating of the search; it cannot make a club sign.

| setting | as shipped; meaning |
|---|---|
| `NEED` | `true`; `false`: as in the game, and the two places and the new memory are not touched |
| `NEED_GAP` (1 to 30) | 4: the weakest of the eleven must stand 4 points or more below the mean of the others |
| `NEED_BETTER` (1 to 20) | 1: the new player must be rated 1 or more above him |

Details:

- One position per club and planning day. If two players are equally weak, the first
  in the game's lineup list counts.
- Nothing is added when the club already looks for that position (a deal that is under
  way), when all 16 slots of its plan are taken, when a place of the eleven is empty
  (the game looks for that one itself), or for the few clubs whose plan is of kind 2 or
  3 (seven or eight of 498 in the saves; the game puts an age on their slots).
- A player a club has put on its list stands 7 points lower in the game's search
  lists. Such a player must be 7 points better than otherwise to be found for a need
  position. So the rule errs to the safe side: never a worse player.
- A club of the first group looks at ratings from 83 up anyway. For it the new part is
  the position, not the rating.
- The mark is kept in two bytes of the club's plan record (`+0x109`, `+0x10a`) that
  are 0 in all 1,992 plan records of the four saves here and that no code read so far
  uses. They go into the save file with the record. Without the module nobody reads
  them.

**How many clubs.** Counted on the save of 1 July 2024 of `ML saves/2nd test`, 498
computer clubs, with the best goalkeeper and the ten best outfield players of each
club taken as its eleven (**an estimate: the game picks the eleven by the club's
formation**):

| `NEED_GAP` | 3 | 4 | 5 | 6 |
|---|---|---|---|---|
| clubs with a need position | 179 | 71 | 41 | 21 |

With 4: goalkeeper 43, CMF 7, CF 6, CB 4, RB 4, DMF 3, LB 2, LWF 1, RWF 1. Ten of the
71 have 32 players and sign nobody until one leaves. Of the first ten clubs: Paris
Saint-Germain (goalkeeper 83, the others 88.2), FC Bayern München (goalkeeper 81,
86.2), Liverpool FC (right back 81, 85.3). How many of these searches end in a signing
is not known; see "What is not known".

**What the test shows** (`python3 test_need.py <PES2017.exe>`, 6 seconds; the install
side is in `test_money.py`):

```
ok 0: without a module: the game's own loop of club_squad_plan, run on 2,000 made-up frames, takes the places without a player from the lineup list and writes their positions into the first empty slots (2463 slots), so list, "no player" and slots are laid out as this test makes them; the place that will be changed changes no plan record; ai_pick_candidate hands its two searches the range of the club level, or 99 down to 41 when 0 is handed in (300 cases each); the two bytes of the plan record that the position need uses are 0 in all 1992 records of the four saves
ok 1: with MLTransfers.lua in (NEED_GAP 4, NEED_BETTER 1), 6,000 made-up clubs at the end of club_squad_plan (lineups of 0 to 20 entries, places without a player in the three forms of "no player", the weakest at, just under and just over the gap, plans of every kind, slots empty and taken): the plan record comes out as money_cave.need_slot says (663 clubs got a slot, 148 of them for a goalkeeper), the two bytes are cleared for the others, and frame, lineup, the records next to it, stack and registers are as the game leaves them; ai_pick_candidate run 3,000 times to the end of its searches hands them the range of money_cave.need_lowest (937 times raised), for the position of the need slot only
ok 2: the same with NEED_GAP and NEED_BETTER at 1 and 1, 30 and 20, 6 and 3, 3.4 and 1.6 (1,500 clubs each); with NEED = false the two places are not changed and plan and searches are the game's
```

Planted faults (`planted_faults.py`, numbers 137 to 152, and the six older ones whose
text changed): all 22 are noticed, by `test_need.py` or by `test_money.py`. The other 131 of the list were not run on version 6.
In the routines themselves four changed instructions were tried by hand: three are
noticed, the fourth (`jae` for `ja` where the two ratings are equal) does the same thing.

The two changed places: `0x03660b93` (6 bytes, where `club_squad_plan` is done with a
club and frees its two lists) and `0x03660c83` (5 bytes, where `ai_pick_candidate`
reads the lowest rating it was handed). Each becomes a call to a routine in the new
memory that first does the work of the bytes it replaced. A scan of the exe found no
call or jump into the inside of either place and no stored address of them.

**What the test does not show.** `club_squad_plan` was not run whole; it needs a career
in memory. That the lineup list, the club's number and the career data are where the
routine reads them when the changed place is reached is read from the disassembly
(`MASTER_LEAGUE.md` 9.3), and the game's own loop over that list was run on the same
made-up frame. That the game does not use the two bytes of the plan record is taken
from the saves and from the 34 functions that handle the records; if it did, a club
would look for a need position without the "better than the starter" rule, no more.
**No window has been played with it.**

### New in version 5

Settings only; the routine is the one of version 4, byte for byte. From a third list by
the user, after a window of a second season (237 signings by computer clubs, 2 of them by
the first twenty clubs, no player without a contract rated 80 or more signed).

| | version 4 | version 5 |
|---|---|---|
| `CEILING_FREE` | 100 | 75 |
| `KNOWN_FAME` | 700 (395 players) | 600 (942 players, 509 of them rated under 80) |
| `STRICT_FREE` | 50 | 35 |
| `knows` | 30 to 90 | 50 to 90: Crisis 50 (30), Academy purist and Survival churner 60 (40), Mid-table 70 (50), New-money 65 (50), Old-money 75 (60), Galactico and State-backed 85 (70, 75), Selling farm and Retirement team 70 (60) |
| `keeps` | 10 to 60 | 10 to 35: Galactico and State-backed 30 (50), Old-money, Academy purist, New-money, Youth elite and Retirement team 35 (50 or 60), Mid-table 30 (40), Moneyball and Survival churner 25 (30) |
| ages | | wider by one to three years for ten personas (Galactico 22-32, Old-money 24-32, Mid-table 23-30, Survival churner 26-34, ...), and `strict` of the same ten 5 to 10 lower |
| `ambition` | Galactico, State-backed 4; Old-money, New-money 5; Youth elite, Retirement team 6 | 7, 7, 7, 7, 8, 7: a big club takes a player a little further below its eleven |
| where a club looks, `winter` | | a few points moved (the table of the personas below); `winter` 5 to 15 higher for ten personas |

To go back to version 4: `git show 339dd67:"pes database/exe/sider/MLTransfers.lua"`.

**Not taken from the list**, with the numbers of the model below:

- `prestige` raised for Mid-table (4 to 8), Survival churner (4 to 7), Crisis, Selling
  farm and Academy purist: 385 of the 499 clubs. A player without a contract rated 75
  to 79 would then be 5 or more points above the eleven of 13 percent of the clubs that
  can sign him (now 2 percent), one rated 70 to 74 above that of 9 percent (now none),
  a player with a contract rated 75 to 79 above that of 10 percent (now 1). That is a
  step back towards version 1, where the signed players stood 3.9 points above the
  eleven of their new club.
- `KEEP_BEST = { 3, 6, 5 }`: with it and the lower `keeps` the first twenty clubs let 53
  percent of their best eleven go (version 4: 17, version 5: 27). The third number, 5
  for 2, also makes it harder for a bigger club to take a player, which the list did not
  want.
- `CEILING_NEED = 50`: one to three percent more clubs can pay. Left at 30.

**What it should give, worked out and not played.** The save of 1 July 2024 of
`ML saves/2nd test`, 498 computer clubs. For each player, the number of clubs that could
sign him: his club lets him go, he is not rated above the top of the club's rating range
(`CEILING_RATING`), he would join, he is good enough, the club knows him, his age fits,
it can pay, and it has fewer than 32 players. Left out: the place the club looks in on
that day, the other tests of the game and its rule about the players of the first fifty
clubs. So these are not numbers of signings, and they are another count than the tables
of versions 3 and 4 below.

| players | how many | version 4 | version 5 | 5 or more above the club's eleven, 4 / 5 |
|---|---|---|---|---|
| no contract, rated 83 or more | 4 | 5.5 | 6.5 | 0 / 0 percent |
| no contract, rated 80 to 82 | 15 | 17.1 | 22.7 | 0 / 0 percent |
| no contract, rated 75 to 79 | 428 | 49.5 | 74.8 | 2 / 2 percent |
| no contract, rated 70 to 74 | 1,951 | 93.9 | 152.2 | 0 / 0 percent |
| with a contract, not listed, rated 85 or more | 88 | 0.5 | 0.8 | 0 / 0 percent |
| with a contract, not listed, rated 80 to 84 | 403 | 3.2 | 5.5 | 0 / 0 percent |
| with a contract, not listed, rated 75 to 79 | 1,363 | 12.8 | 22.8 | 1 / 1 percent |

Players with a contract whom no club can buy: 70, 183 and 468 in version 4; 63, 118 and
317 in version 5.

**The best players without a contract** stay hard to place: 6.5 and 22.7 clubs, most of
them full or looking elsewhere on the day. The one setting that opens more clubs to them
is `CEILING_RATING = false` (a fourth list by the user asked for it): 22.8 and 47.7
clubs for the two groups, 76.1 for those of 75 to 79. The price: 52 and 31 percent of
those clubs have an eleven 5 or more points below the player (with the rule: none); it is
`prestige` that then says how far down he goes, not the ceiling. Not switched: it is one
word to try in a window.

The share of its players (not listed) a club lets go to a buyer that is not clearly
bigger (best eleven / places 12 to 18 / the rest):

| clubs | version 4 | version 5 |
|---|---|---|
| Galactico | 18 / 53 / 57 percent | 32 / 70 / 74 percent |
| State-backed | 9 / 48 / 51 percent | 20 / 67 / 70 percent |
| Old-money | 14 / 46 / 49 percent | 26 / 61 / 64 percent |
| New-money | 7 / 33 / 41 percent | 21 / 57 / 65 percent |
| Mid-table | 18 / 52 / 60 percent | 26 / 62 / 70 percent |
| the first twenty clubs | 17 / 52 / 55 percent | 27 / 66 / 69 percent |
| all 498 | 26 / 61 / 69 percent | 31 / 68 / 76 percent |

**What it does not change.** A club with 32 players cannot sign, and 15 of the first
nineteen clubs of that save have 32. The module can only refuse a player; it cannot make
room. More selling by the big clubs gives room for the next day on which the clubs
choose, not for the same one. Whether that is what holds the big clubs back in a second
season is not known: no save of one was read, only the list of that window's transfers.

**In the game, look at:** the first log line (`MLTransfers 5`); how many players the
first twenty clubs sign and sell; whether players of 75 to 79 without a contract find a
club; whether too many starters of big clubs leave (then put `keeps` of Galactico,
State-backed and Old-money back to 50).

### New in version 4

From a second list of suggestions by the user (five points). Three were taken, two were
not; the reasons are below, with numbers from the model on the save from before the
window played with version 2 (`ML saves/2nd test`, 19,921 players, 498 computer clubs).

| | in version 4 | what it does |
|---|---|---|
| `KNOWN_FAME` (new) | 700 | a player whose popularity is this or more is known to every club (no scouting draw), whatever his rating. 4096: off |
| `STRICT_FREE` (new) | 50 | for a player without a contract, `strict` of the buying club's persona counts only this many percent: he costs no fee, so his age matters less. 100: off |
| `keeps` of three personas | Galactico 50 (was 70), State-backed 50 (was 70), Old-money 50 (was 60) | the biggest clubs let more of their players go |

With `KNOWN_FAME = 4096`, `STRICT_FREE = 100` and the three `keeps` put back, the
routine does what version 3 did.

**Famous players.** The popularity the game keeps runs from 0 to 1,110 in that career
(half of all players have 250 or less; a player rated 80 to 84 has about 660). 395
players have 700 or more, and 109 of them are rated under 80, so version 3 let most
clubs overlook them: Andrew Robertson, Mateo Kovačić, Luke Shaw, Mason Mount, Jordan
Henderson. All 109 have a club. Of the players without a contract and rated under 80
none reaches 700 (the highest has 610); the one free player above it, Riyad Mahrez with
710, is rated 84 and is known already through his rating. So in that save the number
changes nothing for free players and opens only sales between clubs.

**The age of a player without a contract.** A club that wants players of 24 to 28 and
refuses half of the others now refuses a quarter of the others who have no contract.

**What it should give, worked out and not played.** The number of the 498 computer clubs
that could sign a player: they know him, he would join, his age and rating fit, and the
price is within the club's limit. (The place the club looks in on that day, and the
selling club, are left out; this is another count than the 19.7 in the table of
version 3 below, so compare the two columns here with each other only.)

| players | how many | version 3 | version 4 |
|---|---|---|---|
| no contract, rated 80 or more | 19 | 31.6 | 55.3 |
| no contract, rated 70 or more, up to 30 years old | 1,559 | 75.3 | 107.6 |
| no contract, rated 70 or more, 31 or older | 837 | 66.3 | 114.5 |
| no contract, rated 75 to 79, 34 or older | 97 | 32.5 | 72.1 |
| with a contract, popularity 700 or more, rated under 80 | 107 | 34.0 | 60.8 |
| with a contract, all others rated 70 or more | 4,873 | 64.9 | 64.9 |

So a player without a contract is open to about half as many clubs again when he is
young and to nearly twice as many when he is over 30. A club still signs only one
player for a place, and how often it looks among the players without a contract is
`free` of its persona, which did not change: the number of such signings should stay
about the same, but **they will be older**. If the news shows too many old players
signed, raise `STRICT_FREE` (75, then 100).

The share of its players (not listed) a club lets go to a buyer that is not clearly
bigger, by the place of the player in its squad (best eleven / places 12 to 18 / the
rest):

| persona (clubs) | version 3 | version 4 |
|---|---|---|
| Galactico (3) | 8 / 36 / 40 percent | 19 / 53 / 57 percent |
| State-backed (2) | 2 / 27 / 31 percent | 10 / 48 / 51 percent |
| Old-money (23) | 8 / 36 / 39 percent | 14 / 46 / 49 percent |

Over all 498 clubs version 3 gave 25 / 60 / 68 percent, so these 28 clubs still hold
their players better than the average club does. `KEEP_BEST` is unchanged.

**Not taken: prestige + 4 for Galactico and State-backed** (12 to 16, 10 to 14). It
changes nothing. The five clubs of these two personas (Real Madrid, Arsenal,
Manchester United, Paris Saint-Germain, Manchester City) have an eleven of 83 to 87
and already take a player up to 94 to 101; the best player of the career is rated 91.
No player is refused by them for this reason, with 12 or with 16.

**Not taken: prestige minus 1 for each year over 30.** `prestige` is how far *above* a
club's eleven a player may be and still join. Taking a point off for each year over 30
makes an older player refuse *more* clubs, which is the opposite of the reason given for
it ("an ageing player accepts a weaker club") and works against `STRICT_FREE`. In the
model, the players without a contract rated 80 or more and 34 or older could be signed
by 25 clubs in version 3 and by 9 with this rule; players with a contract of that kind
by 24 and by 8. The other way round (one point *more* per year over 30) gives 76 and
67. That would be a rule of its own and was not asked for; it also does not fit: with
the two new pieces of code one byte of the routine's page is left.

**In the game, look at:** the new log line (below); whether well-known players of 75
to 79 now move; how old the players are that clubs sign without a transfer; whether
the five biggest clubs lose too many of their best eleven (then put their `keeps` back
to 70).

### New in version 3

The window played with version 2 showed three things that are not like football:

- A club sold its best players as easily as its reserves: 131 of the 254 players sold
  were among the best eleven of their club.
- Good players without a contract stayed without a club (2 of the 19 rated 80 or more
  were signed), partly because few clubs "knew" them.
- All clubs of a persona wanted the same ages.

What version 3 does about them (three settings, each can be switched off):

| setting | as shipped | what it does |
|---|---|---|
| `KEEP_BEST` | `{ 4, 12, 2 }` | a club holds on to its first team. A player counts as first team if his rating is at most 4 points below the rating of his club's eleven. For each point above that line, 12 percent are added to `keeps` of his club. Not against a buyer whose eleven is 2 or more points better: a club cannot hold a player against a clearly bigger one. Listed players are not kept. Second number 0: off |
| `KNOWN_FROM` | 70 | a player of this rating or more is known to every club (no scouting draw). 100: off |
| `AGE_SHIFT` | 2 | the ages of a persona are moved by up to 2 years down or up, fixed by the club: clubs with ages 24-28 want 22-26, 23-27, ... or 26-30. 0: off |

With `KEEP_BEST = { 4, 0, 2 }`, `KNOWN_FROM = 100` and `AGE_SHIFT = 0` the routine does
what version 2 did.

Changed numbers of the personas (from a list of suggestions by the user; the table
further down has the new numbers): Galactico ages 22-30 and strict 70; State-backed
wealth 160 and premium 150; Survival churner premium 80; Crisis and Selling farm keeps
10 (was 0); New-money wealth 250 and prestige 8 (was 180 and 3). Two new personas:
**Youth elite** (pays well for players of 19 to 24 from other clubs) and **Retirement
team** (players of 32 to 40, the famous ones above all: `fame` 250 and `prestige` 22, so
it takes a player far above its eleven if his name is worth it). Chelsea is now Youth elite; Al Nassr,
Inter Miami, Al Ittihad and Al Sadd are Retirement team. In `PERSONA_GROUPS` Crisis is
drawn less often (46 clubs instead of 60), New-money less often among the first fifty,
and the last three groups are no longer the same list.

**What it should give, worked out and not played.** The model of the routine was run on
the save from before the window played with version 2 (`ML saves/2nd test`):

| | version 2 | version 3 |
|---|---|---|
| share of its players a club lets go to a buyer that is not clearly bigger: best eleven / places 12-18 / the rest | 71 / 71 / 71 percent | 25 / 60 / 68 percent |
| players of a squad that count as first team | - | 14 of 28 (median) |
| of the 214 players that moved between clubs without being listed: the seller would refuse | 0 | 64 (55 of the 121 from a best eleven, 9 of the 93 others) |
| clubs that could sign a player without a contract rated 80 or more (mean of the 19) | 7.4 | 19.7 |
| the same for the three rated 84 | 7, 4, 4 | 13, 8, 12 |

A buyer whose first choice is refused takes the next player who fits, so this does not
say there will be 64 signings fewer; it says they will more often be reserves. Only 28
of the 214 buyers were "clearly bigger" than the seller. How a real window comes out
is not known until one is played.

**In the game, look at:** the log lines (below); whether clubs still lose players of
their best eleven to clubs of the same size; whether the best players without a
contract find a club in the first window; what Al Nassr, Inter Miami, Al Ittihad and
Al Sadd sign. If too few players move: lower the second number of `KEEP_BEST` (12)
first.

### Why

One transfer window of a career played with version 1 was read from two save files
(1 July and 15 September 2024, 498 computer clubs):

| | |
|---|---|
| signings by computer clubs | 511 |
| of them players without a contract | 506 |
| of them from another club | 5 |
| players on the lists of their clubs before / after | 816 / 1,548 |
| listed players who were sold | 0 |

The ceiling was not what stood in the way of a move between two clubs. Two things in
the game's code were:

1. A club first looks among the players without a contract and those who have
   outgrown their club. Only if that search gives nobody does it look at the players
   of other clubs. After the contracts of a season have run out there is always
   somebody without a contract.
2. The search lists the first three players who fit and only afterwards asks whether
   their club lets them go. It lets a player go only if it counts more than 23 players
   and he is not one of its better players (status band below 7, club not among the
   first twenty), with exceptions for buyers among the first twenty clubs and for one
   kind of slot. If none of the three may go the club signs nobody, although more
   players stood further down.

### What it changes

Five parts, each with a switch. With all but `CEILING` off the module does what
version 1 did.

| part | switch | what it does |
|---|---|---|
| price ceiling | `CEILING` | as in version 1 (next section). `CEILING_FREE` was 100 in versions 2 to 4 (a player without a contract counts at his full value; with the 50 of version 1 a player worth twice a small club's ceiling was within its reach) and is 75 in version 5 |
| selling side | `SELL_SIDE` | the question of point 2 above is asked before a player takes one of the three places, so the list holds only players who can move |
| club personas | `PERSONA` | every club has a character: where it looks and in which order, which ages it wants, how well it judges, how far it goes, how good a player must be for it, how good a player still joins it, how many of its players it keeps |
| scouting | `SCOUTING` | a club knows only a part of the players (not those another club has listed: they are known to all) |
| rivals | `RIVALS` (a list; `{ }` is off) | two clubs that are rivals do not take each other's players who have a contract |

What it cannot do, as before: no money is booked for a computer club, there are no
offers and no wages between computer clubs, no loans, no club remembers what it did. The
module answers one question for one player a club is looking at: may he go on its list.
The game then chooses among the three as it always did.

### How a club decides about a player

The game's own tests come first (position, age range of the slot, not on loan, not in
a deal, not of the same club, the foreign-player and squad rules). For a player who
passed them, in this order; "refused" means the club looks at the next player:

0. **Rivals.** For a player with a contract, on his club's list or not: refused if his
   club and the buying club are a pair of `RIVALS`. A player whose contract has run out
   is not asked: he goes where he likes.
1. **His club.** For a player with a contract who is not on his club's list. With
   `SELL_SIDE`: his club must count more than 23 players, and in the search among the
   players of other clubs the rule of point 2 above must let him go. Then the persona
   of his club: `keeps` percent of its players it never lets go (which ones is drawn
   from club, player and date, so it changes from window to window). For a player of
   its first team `keeps` is higher (`KEEP_BEST`, version 3), unless the buyer is
   clearly the bigger club.
2. **Scouting.** The club knows `knows` percent of the players. Which ones is drawn
   from club and player and stays the same for the whole career. A listed player is
   known to every club, and so is a player rated `KNOWN_FROM` (80) or more (version 3)
   or of a popularity of `KNOWN_FAME` (600) or more (version 4).
3. **The player.** He does not join a club whose first eleven is more than `prestige`
   rating points below him. The eleven's rating is worked out from the club's points in
   the game's club ranking (`STRENGTH`).
4. **Where the club looks.** For each position, on each of the three days of a year on
   which the clubs choose, a club looks in one place: players without a contract
   (`free`), players on the lists of other clubs (`listed`), other players of other
   clubs (`clubs`). The three percentages say how often; what is left to 100 is "does
   not buy for this position this time". On the day the winter signings are chosen it
   buys only `winter` percent of the time. If the first search gives nobody, the
   second search (among all ratings) looks in the next place the persona names
   (`second`). Then the ages: a player outside `age` is refused `strict` percent of the
   time; a player without a contract only `STRICT_FREE` (35) percent of that
   (version 4). The two ages are moved by up to `AGE_SHIFT` years from club to club
   (version 3).
5. **The rating as the club sees it.** Up to `fog` points too low or too high (drawn
   from club and player). A player seen more than `ambition` points below the first
   eleven is refused.
6. **Second search:** nobody seen above the top of the club's rating range
   (`CEILING_RATING`, as in version 1).
7. **The price** (as in version 1), with the persona's numbers: the ceiling is `wealth`
   percent of the group's, `CEILING_STRETCH` counts `premium` percent, `CEILING_NEED`
   counts `panic` percent, and for every 1,000 points of the player's popularity the
   limit is `fame` percent higher. The value is that of the rating of step 5: a club
   with fog misjudges the price too.

**A club in need** is one that counts fewer than `SQUAD_NEED` (26) players. It always
buys, in winter too, at any age and below its usual level, and its ceiling counts
higher; it still looks in the places of its persona. A slot of a top club that asks for
a key player (the game does this for one slot of the first ten or twenty clubs on the
last day of a window) looks everywhere.

Every number of a persona but its ages is, for each club, up to `PERSONA_SPREAD` (20)
percent lower or higher, fixed by the club. No dice are thrown during play: every draw is worked out
from the ids of club and player, the position and the date, so the same club answers
the same way on the same day.

### The personas

`ARCHETYPES` in the file; at most 15, every number can be changed.

| persona | looks first: free / listed / clubs / does not buy | second search | winter | ages (strict) | knows | fog | wealth | premium | panic | fame | ambition | prestige | keeps | `rating` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Galactico | 5 / 10 / 85 / 0 | clubs, free | 45 | 21-31 (70) | 85 | 0 | 150 | 150 | 100 | 40 | 7 | 12 | 30 | off |
| State-backed | 25 / 15 / 60 / 0 | clubs, listed | 50 | 21-30 (70) | 85 | 1 | 160 | 150 | 150 | 25 | 7 | 10 | 20 | on |
| Moneyball | 15 / 25 / 60 / 0 | clubs, listed | 35 | 19-29 (75) | 90 | 0 | 90 | 40 | 50 | 0 | 8 | 6 | 15 | on |
| Elite trader | 15 / 20 / 55 / 10 | clubs, listed | 35 | 18-25 (45) | 85 | 1 | 100 | 60 | 60 | 0 | 9 | 6 | 15 | on |
| Academy purist | 15 / 15 / 40 / 30 | clubs, free | 25 | 17-25 (40) | 60 | 2 | 70 | 50 | 50 | 0 | 12 | 4 | 25 | on |
| Old-money | 30 / 20 / 50 / 0 | clubs, free | 50 | 23-32 (50) | 75 | 2 | 110 | 100 | 120 | 30 | 7 | 8 | 20 | on |
| Mid-table | 25 / 30 / 40 / 5 | listed, clubs | 50 | 23-30 (40) | 70 | 2 | 100 | 100 | 100 | 5 | 8 | 4 | 15 | on |
| Survival churner | 40 / 35 / 25 / 0 | free, listed | 80 | 27-36 (40) | 60 | 3 | 90 | 80 | 200 | 5 | 9 | 4 | 15 | on |
| Crisis | 60 / 30 / 10 / 0 | free, listed | 70 | 17-38 (20) | 50 | 3 | 50 | 30 | 100 | 0 | 12 | 2 | 10 | on |
| New-money | 35 / 10 / 55 / 0 | clubs, free | 60 | 24-31 (60) | 65 | 3 | 250 | 200 | 150 | 30 | 7 | 8 | 40 | on |
| Selling farm | 20 / 25 / 40 / 15 | listed, free | 40 | 17-26 (60) | 70 | 2 | 60 | 40 | 50 | 0 | 12 | 4 | 5 | on |
| Youth elite | 10 / 15 / 65 / 10 | clubs, listed | 30 | 18-25 (45) | 85 | 1 | 140 | 120 | 80 | 15 | 8 | 8 | 30 | on |
| Retirement team | 0 / 30 / 65 / 5 | listed, clubs | 70 | 32-40 (95) | 80 | 0 | 250 | 250 | 150 | 250 | 4 | 22 | 5 | off |

"Does not buy" stands for a club that fills a place from its own academy: the module
cannot make a youth player, it can only keep the club from buying. `rating` is the
`CEILING_RATING` rule: `off` (Galactico and Retirement team) means that in its second
search the club may also take a player rated above the top of its own rating range; `on`
every other persona keeps that limit.

**Which club has which persona.** 183 clubs are named in `CLUBS` (the game's id of the
club and the name of a persona; at most 192). The choice is mine, from what the real
clubs are known for on the market; no source was looked up for it, and each line can be
changed. It is surest for the big clubs and gets weaker further down: for a small or
newly promoted club "Mid-table" or "Survival churner" is often all that can be said.
In brackets the place in the game's club ranking of the career above.

The 73 named first (the biggest clubs of the data):

- Galactico: Real Madrid (2), Arsenal (4)
- State-backed: Paris Saint-Germain (1), Manchester City (6)
- Old-money: Barcelona (3), Bayern (5), Atlético (8), Inter (9), Napoli (13), Juventus
  (15), Roma (16), Fenerbahçe (22), Betis (25), Flamengo (37), Beşiktaş (55),
  River Plate (62), Boca Juniors (63), Marseille (72)
- Moneyball: Liverpool (7), Tottenham (12), Milan (17), Brighton (26), Bournemouth (30),
  Sunderland (33), Brentford (36), Stuttgart (48), Lens (58), Girona (99)
- Elite trader: Dortmund (14), Leverkusen (27), Atalanta (28), Porto (31),
  Benfica (32), RB Leipzig (35), Monaco (43), PSV (44), Rennes (57), Lille (66),
  Palmeiras (67), Eintracht Frankfurt (69), Celtic (91), Club Brugge (111)
- New-money: Chelsea (11), Aston Villa (18), Newcastle (21), Como (38), Al Ahli (106)
- Retirement team: Galatasaray (20), Al Hilal (41), Al Nassr (60), Fluminense (81),
  Al Sadd (90), Inter Miami (104), CR Vasco da Gama (112), Al Ittihad (114),
  Los Angeles FC (152), Los Angeles Galaxy (179), Chicago Fire (186), Toronto FC (209)
- Academy purist: Athletic Club (19), Real Sociedad (39), Celta (51), Osasuna (53),
  Freiburg (70)
- Survival churner: Rayo Vallecano (49), Getafe (64)
- Crisis: Manchester United (10), Valencia (52), Lyon (54), Sevilla (76)
- Selling farm: Ajax (42), Sporting CP (50), Feyenoord (86), Braga (89), Anderlecht
  (142), AZ (143), Dinamo Zagreb (145), Genk (150), Salzburg (208), Nordsjælland (272)

The rest of the five big leagues (50 clubs; the leagues as they stand in 2025/26, which
is what the data looks like: Sunderland, Leeds, Burnley, Paris FC, Hamburg, Köln, Pisa
and Oviedo are in it as top-flight clubs by their ranking. The league of a club was
not read from the data):

| league | personas |
|---|---|
| England | New-money: Nottingham Forest (23). Moneyball: Crystal Palace (24). Mid-table: Everton (34), Leeds (40), Fulham (45). Old-money: West Ham (65). Elite trader: Wolverhampton (78). Survival churner: Burnley (93) |
| Spain | Moneyball: Villarreal (29). Mid-table: Mallorca (119). Survival churner: Espanyol (75), Alavés (101), Levante (118), Elche (120), Oviedo (165) |
| Italy | Mid-table: Lazio (46), Torino (71). Moneyball: Bologna (56), Lecce (157). Old-money: Fiorentina (61). Elite trader: Sassuolo (88), Udinese (97), Genoa (108), Parma (128), Verona (174). Survival churner: Cagliari (127), Cremonese (185), Pisa (221) |
| Germany | Elite trader: Hoffenheim (47), Wolfsburg (110). Moneyball: Mainz (74), Heidenheim (227). Mid-table: Augsburg (85), Mönchengladbach (87), Hamburg (98), Köln (100), Werder Bremen (102), St. Pauli (222). Survival churner: Union Berlin (94) |
| France | Mid-table: Nice (79). New-money: Paris FC (80). Elite trader: Strasbourg (105). Moneyball: Toulouse (141). Survival churner: Brest (135), Angers (160). Academy purist: Auxerre (159), Le Havre (171). Selling farm: Lorient (162), Metz (282). Crisis: Nantes (183) |

22 clubs of the second divisions that were in those leagues lately, or are big:
Mid-table: Ipswich (73), Deportivo La Coruña (77), Palermo (121). Elite trader:
Southampton (115), Watford (172), Reims (321). Crisis: Monza (125), Sampdoria (137),
Leicester (254), Sheffield Wednesday (274), Montpellier (365). Survival churner:
Leganés (192), Valladolid (319). Academy purist: Las Palmas (164), Málaga (169),
Sporting Gijón (236). New-money: Almería (131), Wrexham (146), Birmingham (147).
Selling farm: Venezia (116), Empoli (333). Moneyball: Saint-Étienne (216).

35 other clubs with a known way of buying: Old-money: Olympiacos (59), Trabzonspor
(68), Fluminense (81), Atlético Mineiro (92), Rangers (123), Racing Club (132),
København (168). Elite trader: Botafogo (107), Slavia Praha (109), Bragantino (156),
Young Boys (161), Talleres (167), Crvena zvezda (170), Athletico Paranaense (193), Sturm
Graz (307), New York Red Bulls (369). Moneyball: Midtjylland (148), Union
Saint-Gilloise (149), Bodø/Glimt (151). Selling farm: Santos (83), Lanús (136), Vélez
(154), Argentinos Juniors (217), Basel (285), Philadelphia (288), Brøndby (299). Crisis:
São Paulo (82), Corinthians (113), Independiente (163). New-money: Cruzeiro (84), Bahia (124), Atlanta (240).

Every other club draws one of up to eight personas of its group in the club ranking
(`PERSONA_GROUPS`, the ten groups of `CEILING`); which one is fixed by the club's id.
Naming the 107 clubs changed the persona of 90 of them; 17 had drawn the same one.
With the file as it is, the 499 clubs of that career come out as: Survival churner 133,
Mid-table 95, Selling farm 58, Academy purist 50, Crisis 47, Elite trader 35, Moneyball
30, Old-money 22, New-money 13, Retirement team 12, Galactico 2, State-backed 2 (Youth
elite: none, drawn only by the clubs of its groups) (version 2: 140, 90, 49, 52, 60, 36, 24, 24, 19, -, 3, 2, -). `club_ids.tsv` lists
every one of them with its id, place, persona and the rating its first eleven is taken
to have. The ids are those of the data that career was played with; with other data a
club that is not found simply has no entry of its own. Your own club is never asked:
the module acts only where a computer club chooses.

### Rivals

`RIVALS` in the file: 61 pairs of club ids (at most 64), the ids of `CLUBS` and
`club_ids.tsv`. Three clubs that are all rivals are three pairs. The part works by
itself, with every other switch on or off. The choice of pairs is mine, without a source,
and it is strict where the real clubs are not always (Real Madrid and Atlético, Inter and
Milan, Juventus and Torino have traded): delete a line to let a pair trade.

| country | pairs |
|---|---|
| England | Manchester United - Liverpool; Manchester United - Manchester City; Manchester United - Leeds; Arsenal - Tottenham; Liverpool - Everton; Newcastle - Sunderland; Aston Villa - Birmingham; Crystal Palace - Brighton; West Ham - Millwall; Nottingham Forest - Derby; Southampton - Portsmouth; Sheffield United - Sheffield Wednesday; Ipswich - Norwich |
| Spain | Real Madrid - Barcelona; Real Madrid - Atlético; Barcelona - Espanyol; Sevilla - Betis; Athletic Club - Real Sociedad; Valencia - Levante; Celta - Deportivo; Oviedo - Sporting Gijón |
| Italy | Inter - Milan; Inter - Juventus; Roma - Lazio; Juventus - Torino; Genoa - Sampdoria |
| Germany | Hamburg - Werder Bremen; Hamburg - St. Pauli; Köln - Mönchengladbach; Köln - Leverkusen |
| France | Paris Saint-Germain - Marseille; Lyon - Saint-Étienne; Lens - Lille; Nantes - Rennes |
| Portugal | Benfica - Porto; Benfica - Sporting CP; Porto - Sporting CP |
| Netherlands | Ajax - Feyenoord; Ajax - PSV |
| Scotland | Celtic - Rangers |
| Turkey | Galatasaray - Fenerbahçe; Galatasaray - Beşiktaş; Fenerbahçe - Beşiktaş; Fenerbahçe - Trabzonspor |
| Belgium | Anderlecht - Club Brugge; Anderlecht - Standard |
| Denmark | København - Brøndby |
| Argentina | Boca Juniors - River Plate; Racing Club - Independiente; Rosario Central - Newell's; Estudiantes - Gimnasia La Plata; San Lorenzo - Huracán |
| Brazil | Flamengo - Fluminense; Flamengo - Vasco; Corinthians - Palmeiras; Grêmio - Internacional; Atlético Mineiro - Cruzeiro; Bahia - Vitória |
| Saudi Arabia | Al Hilal - Al Nassr; Al Ittihad - Al Ahli |
| United States | LA Galaxy - Los Angeles FC |

What it does not do: it does not stop a player who is free from joining the rival, and
it knows nothing of a move by way of a third club. Whether the game lets a computer
club go for a player of the club you play was not looked at; if it does, the pair of
your club (Athletic Club - Real Sociedad) counts there too. What you buy yourself is
not touched.

### Settings new in versions 2 to 6

| setting | as shipped; meaning |
|---|---|
| `CEILING_FREE` | 75 (version 1: 50; versions 2 to 4: 100) |
| `SELL_SIDE` | `true`; `false`: the game's order (list three, then ask the club) |
| `PERSONA` | `true`; `false`: all clubs alike, and the settings below are not used |
| `SCOUTING` | `true`; `false`: every club knows every player |
| `PERSONA_SPREAD` (0 to 50) | 20: each number of a persona up to 20 percent lower or higher from club to club |
| `STRENGTH` | `{ 0.0533, 9.45 }`: rating of the first eleven = 0.0533 x ranking points + 9.45, kept inside the club's rating range. Fits the mean of the best eleven of the 499 clubs of the career above (1,464 points: 87; 984 points: 62) |
| `WINTER_MONTH` (0 to 12) | 9: the clubs choose their winter signings on 1 September; 0: winter is like summer |
| `SQUAD_NEED` (0 to 32) | 26: with fewer players a club is in need |
| `KEEP_BEST` (0 to 99, 0 to 100, 0 to 99) | `{ 4, 12, 2 }`, version 3: see "New in version 3" |
| `KNOWN_FROM` (0 to 100) | 80, version 3 |
| `AGE_SHIFT` (0 to 5) | 2, version 3 |
| `KNOWN_FAME` (0 to 4096) | 400 (version 5: 600, version 4: 700): see "New in version 4" |
| `STRICT_FREE` (0 to 100) | 35 (version 4: 50) |
| `ARCHETYPES` | the thirteen personas above (at most 15) |
| `PERSONA_GROUPS` | ten lists of 1 to 8 persona names, best clubs first |
| `CLUBS` | the 180 named clubs (at most 192); `{ }` names none |
| `RIVALS` | the 61 pairs above (at most 64); `{ }`: no rivals |
| `NEED`, `NEED_GAP` (1 to 30), `NEED_BETTER` (1 to 20) | `true`, 4, 1, version 6: see "New in version 6" |
| `INCOMING` | `true`; `false`: as in the game, and the fourth piece of memory and its place are not touched. Uses `RIVALS` with the four rules of the selling side: see "New in version 8" |
| `SQUAD_PRESSURE` | `{ positions = { GK = 3, DF = 8, MF = 9, FW = 6 }, keeps_drop = 40 }`, version 9: see "New in version 9" |
| `DEAL_MOOD` | `{ mood = 8, style = { seller = -12, trader = -3, builder = 5, hoarder = 12 } }`, version 9: see "New in version 9: the mood of a deal" |

A faulty setting is named in `sider.log` and nothing is written, as before.

### What the log says

Read the checks in order: Money v7 installed, valuation code unchanged, required game bytes matched, reserved memory empty, writes verified, then `RESULT: installed`. The printed ceilings and persona settings reflect the loaded file. A duplicate club in `CLUBS` is reported; the last entry wins.

Do not ignore `NOT EMPTY`. The Transfers main block moved from `0x047d3c40` (384 bytes, v1) to `0x047d4200` (3,424 bytes in v2; 3,584 from v3). One observed window ran through 30 August; that does not prove compatibility with other mods. The optional `NEED` block at `0x047d6400` takes 336 bytes. Disabling `NEED` or `INCOMING` omits the corresponding hook and its checks; it does not make occupied memory safe. See [patch reservations](#notes-for-the-next-module) for the current layout.

### What to look at in the game

1. The log lines above.
2. The transfer news of a window. `window_report.py` reads a window from the save
   files of before and after.
3. For more signings: set `SCOUTING = false` first, then `PERSONA = false`; each takes
   away one set of refusals. `SELL_SIDE = false` gives the game's order back.

### What the second window showed

A new career (SSC Napoli) was played from 1 July to the end of the window with the
settings of the file, and the two saves were read with

    python3 window_report.py <PES2017.exe> <save before> <save after> [MLTransfers.lua]

(the last argument is the `MLTransfers.lua` the window was played with, if it is not the
one in this folder; for this pair, version 2: `git show
d6f4a02:"pes database/exe/sider/MLTransfers.lua"`). Computer clubs only (what they bought from the user's club is left out: 2 and 4
players).

| | version 1 | version 2 |
|---|---|---|
| signings by the 498 computer clubs | 509 | 430 |
| players without a contract | 506 | 176 |
| players on the list of their club | 0 | 40 |
| other players of clubs | 3 | 214 |
| clubs that signed / clubs that sold | 230 / 3 | 221 / 172 |
| players on the lists before / after | 816 / 1,548 | 816 / 1,288 |
| mean age of the signed players | 30.1 | 27.3 |
| their rating against the buyer's first eleven | 3.9 above | 0.3 above |
| signed players of 80 and more | 17 | 8 |
| best player signed by a club of the lower half | 76 | 74 |
| clubs under 23 players before / after | 49 / 25 | 49 / 26 |

The module's rules are seen in who was signed. A club with `knows = 50` knows half of
the players; of the 176 signed players without a contract all 176 were known to their
buyer (75 would be by chance; in the first window 241 of 506, as chance says). All 430
pass `prestige` (first window: 195 of 509), 428 the price. 16 signings (4 %) do not
fit scouting or `keeps`; the saves do not say why (most likely the player was put on
his club's list during the window, and a listed player skips both).

By persona (signings; no contract / listed / other; clubs that signed):

| persona | signings | from | clubs |
|---|---|---|---|
| Survival churner | 127 | 76 / 16 / 35 | 61 of 140 |
| Mid-table | 90 | 19 / 9 / 62 | 41 of 90 |
| Crisis | 54 | 39 / 7 / 8 | 27 of 60 |
| Academy purist | 39 | 7 / 2 / 30 | 20 of 52 |
| Elite trader | 35 | 5 / 1 / 29 | 21 of 36 |
| Selling farm | 29 | 8 / 4 / 17 | 19 of 49 |
| New-money | 26 | 16 / 0 / 10 | 12 of 19 |
| Moneyball | 21 | 3 / 1 / 17 | 11 of 24 |
| Old-money | 9 | 3 / 0 / 6 | 9 of 23 |
| State-backed | 0 | | 0 of 2 |
| Galactico | 0 | | 0 of 3 |

Three weak points, none of them a fault of the code:

1. **The biggest clubs buy almost nothing** (first twenty: 5 signings; version 1: 8).
   15 of the 19 start with 32 players, the most a club can hold, and so do 99 of the
   498 clubs. A full club cannot sign. Version 2 makes them sell (those 99 clubs lost
   88 players and signed 4), so there is room from the winter on. This comes from the
   database: squads filled to 32.
2. **No star moves.** No player of 85 or more moved in either window. Nearly all of
   them (111 of the 130 players of 84 and more) are at one of the first twenty clubs,
   and the game lets those clubs sell only in a few cases. The module can refuse a
   player; it cannot make the game offer one.
3. **The best players without a contract stay without a club**: of the 19 of 80 and
   more, computer clubs signed 2 (version 1: 14, most of them at clubs far below
   them). For a player of 84 only 49 clubs are good enough (`prestige`), 35 of them
   can pay, 24 of those know him, 12 of those have room, 7 of those want his age.
   To change it: raise `prestige` of the personas (each point lets him join a club one
   rating point weaker), or set `SCOUTING = false` (24 becomes 35). Not tried in the
   game. Version 3 takes the scouting step away for players of 80 and more
   (`KNOWN_FROM`); `prestige` is as it was but for New-money.

The lists are used little (40 of 816) because the listed players are weak: none above
74, 658 below 65.

### What is not known

- Versions 3 to 6 have not run in the game. Their numbers above come from the model.
- Position need (version 6): how many of the need positions end in a signing. The
  search still has to find a player who is better than the starter, who would come,
  whom his club lets go and whom the club can pay. For a goalkeeper of a club of the
  first group that is a short list. `window_transfers.py` on a save after the window
  shows it: look for goalkeepers among the signings.
- What `STRICT_FREE` does to the ages of the players signed is an estimate from how
  many clubs could sign a player, not from a played window.
- The winter window, a second season and the fees paid were not looked at.
- The mix per persona in the table of the settings is what the settings ask for; the
  table above is what one window gave.
- The number the game keeps per club and tests against 23 is taken to be the size of
  the squad without the players already promised away (read, not proven).
- `ambition` and `prestige` lean on the club ranking. If a club's points drift far over
  many seasons, its eleven is taken to be better or worse than it is.
- 1 September as the day of the winter signings is read from the game's calendar, not
  seen in play.

## MLMoney: values, wages and budgets

**Two files since version 7.** `MLMoney.lua` holds the money: values, salaries,
budgets, income, prizes. `MLTransfers.lua` holds the transfers between computer clubs:
today the price ceiling (every setting whose name starts with `CEILING`), moved out of
`MLMoney.lua` without a change. The bytes written to the game and their addresses are
those of version 6, except for the four letters of the mark (`MLM7`). The reasons for
the second file: the money settings are finished and are not touched by the coming
transfer work, a fault in one file does not stop the other, and the transfers can be
switched off by taking one line out of `sider.ini`. Both run once, when the game
starts, and cost nothing during play.

`MLTransfers.lua` needs `MLMoney.lua`: its routine calls the value routine of
`MLMoney.lua` to price a player. Sider runs the modules in the order of their
`lua.module` lines, so the line of `MLMoney.lua` must stand above. `MLTransfers.lua`
looks for the mark of `MLMoney.lua` in the memory and compares the value routine
(226 bytes) and the numbers 100 and 1000 it uses with what version 7 writes; if they are not
there, or differ, it writes nothing and says so. `MLMoney.lua` alone works as before.
A setting `WRITE` stands in both files; each rules its own file.

### What the game does without it

`../MASTER_LEAGUE.md` section 6. The value of a player is
`salary x (2.2 to 3.3) + 9,000 x (rating - 68)`, and the screens show 100 times the
stored amount. There is no age and no position in it, and it rises in a straight line
with the rating. From the formula, for a club high in the ranking: rating 80 about 16
million, 85 about 23 million, 94 about 40 million. The one player measured in the user's
career, Bruno Fernandes (rating 89, captain's bonus in his salary), showed 36,743,200.

When a career starts, the transfer budget of the user's club is twice the mean value of
its 16 best players, and the salary budget is the wage bill plus twice the mean salary
of its 16 best paid players (section 6.4).

A cup pays once, when the club is out or has won: 8 million for winning the Champions
League, half a million for going out in its group stage. A first division pays 15
million for place 1 down to 0.3 million. The money goes to the club's balance; neither
budget gets any of it (section 6.7). The first club of the game's club ranking pays twice
the salary of a club outside the first 250. A player of 23 or younger signs for 3 years
at most (section 7.3).

On the first day of a season the club gets two amounts: one by its place in the club
ranking (201 million for the first club, 76.5 million at place 250, almost nothing
at place 400) and one by the popularity of the club and its players (30 to 85 million
for the squads of the edit file). Neither depends on what the club pays its players. On 28 and on 30 June the two budgets get a grant; both
grants are fractions of the wage bill and of the fees of the ten most valuable players
(section 6.7).

The game keeps no number for a player's potential. Players grow by age and by playing
time with fixed steps (section 12), and nothing of that enters the value.

### What the module does

- **Value** = `VALUE[rating] x AGE[age]`, plus the talent bonus, times
  `POSITION[registered position]`, times the player's own fixed factor (`SPREAD`), plus
  `FAME` percent of that for every 1,000 popularity points of the player (section 6.5).
  The salary no longer enters the value.
  The rest of the game's fee function is untouched: figures handed in by a deal, the
  random change of up to 20 or 49 percent, the limit.
- **The player's own factor**: without it, two players of the same rating, age and
  position cost exactly the same. Each player gets one of 256 steps between
  `100 - SPREAD` and `100 + SPREAD` percent, chosen by his id, so it is the same every
  time the game asks.
- **Salary**: the rating part (`30 x rating - 500` plus the steps at 65, 75, 85) becomes
  `SALARY[rating] x SALARY_AGE[age]`. The popularity part is the game's own.
- **Transfer budget** at the start of a career: `BUDGET_TRANSFER` times the mean value
  of the 16 best players, in place of 2 times. `BUDGET_SALARY` does the same for the
  salary budget and is off by default.
- **Budget slider & rebalancing** (`BUDGET_SLIDER`, `BUDGET_SLIDER_RATIO`, `BUDGET_SLIDER_STEP`):
  interactively move money between transfer budget and salary budget in Master League.
  Moving money uses multi-year contract amortization: because salaries are annual commitments,
  transfer lump-sums convert to annual wages at `BUDGET_SLIDER_RATIO` (default 4.0x, representing
  a standard 4-year contract). For example, reallocating £10M transfer budget adds £2.5M to the
  salary budget; freeing £2.5M of annual salary adds £10M to the transfer budget.
  Use F6 for transfer → salary or F7 for salary → transfer.

New in version 3, each with its own switch:

- **Cup prizes** (`CUP`): the amounts of the game's cup table are replaced for the
  competitions and stages named in the setting. The game's table is not written; the
  three instructions that read it are pointed to a copy.
- **League prizes** (`LEAGUE`, `LEAGUE_2`): the game's two main lists by place, for
  first and second divisions. Leagues played in two halves still get half per half.
- **Prizes into the transfer budget** (`PRIZE_TO_BUDGET`): on the day a prize is paid,
  that percent of it is added to the transfer budget as well. The balance gets the whole
  prize as before. Only in Master League (game mode `0x13`).
- **Pay gap** (`PAY_GAP`): the first club of the ranking pays this many times the
  salary of a club outside the first 250, in place of 2 times. `SALARY` is what the
  first club pays, so a higher gap lowers the salaries at small clubs.
- **Salary bonuses** (`BONUS`): the game's bonuses for the team role, the age band and
  the awards are multiplied by this percent. They are fixed amounts (1,000 to 15,000 a
  year stored, 100,000 to 1.5 million on the screen) that the larger salaries of the
  module would otherwise dwarf.
- **Contract years** (`YOUNG_YEARS`): the limit of 3 years for a player of 23 or
  younger becomes this number. The game still picks the years itself below the limit
  (section 7.3), so not every young player is offered the full length.

New in version 4, each with its own switch:

- **Talent** (`TALENT`, `TALENT_STEP`, `TALENT_MAX`, `TALENT_CAP`): a young player who
  is already good for his age costs more. Because the game has no potential to read,
  the rating a player has at his age stands for it: `TALENT` gives the rating that is
  ordinary at each age up to 23, and every point above it adds `TALENT_STEP` percent
  to the value, up to `TALENT_MAX` percent and `TALENT_CAP` millions. This is a
  stand-in. It cannot tell a late developer from a finished player, and it gives a
  17-year-old of rating 60 nothing even if he would grow fast.
- **Yearly income** (`INCOME_WAGES`): `INCOME_WAGES` percent of the club's wage bill is
  added to the popularity amount of every 1 July. The game's own code already works
  out the wage bill at that point and throws it away; the module keeps it. With 60 the
  income less the wages comes out close to what the game alone gives, for strong and
  for weak squads (table below). `INCOME` is a second, blunt tool, off by default: it
  multiplies both of the game's amounts, and the first of them at the start of a
  career, by a percent.
- **Prize lists by league** (`LEAGUE_BY_ID`): up to 12 first divisions get a list of
  their own, or a percent of `LEAGUE`. The routine looks at the league number the
  game's function already holds.
- **National cups** (`CUP_NATIONAL`): the six amounts the game pays for every cup that
  has no row in its cup table.
- **Television money of the big cups** (`CUP_TV`): an amount per competition that is
  added to every amount of `CUP` for it.

New in version 5, changed in version 6, in `MLTransfers.lua` since version 7:

- **Price ceiling of the computer clubs** (`CEILING`, `CEILING_RATING`). This is the
  first part that changes the transfers between computer clubs.

  *The game.* A computer club has no money (section 9 of `MASTER_LEAGUE.md`). For each
  open position it goes through lists of players sorted by overall, from the top of a
  rating range down, and notes the first three who pass its tests; one of them is
  signed. The range goes by the club's place in the club ranking, in ten groups: the
  clubs outside the first 300 look from 74 down to 47, the first ten from 99 down to
  83. No test looks at a price. If nobody fits, the club looks a second time among
  all players from 99 down to 40, whatever its size. In that second search the game
  leaves out the stars of other clubs (players of the highest status bands who are not
  listed for sale), but not the players it sorted into its first set of lists: those
  without a club and those who are more than 3 points above the range of the club
  they play for.

  *The module.* One more test at the point where a player has passed all the others:
  his value (the value this module computes, with his own factor and popularity,
  before the game's random change) is compared with the ceiling of the club's group.
  A player the club cannot reach is passed over and the search goes on with the next
  one, so the three players it notes are the best three it can afford.
  With `CEILING_RATING` the second search also stops at the top of the club's own
  rating range: it looks further down, not further up. A persona with `rating = false`
  is exempt: Galactico and Retirement team look past that top (a famous player above
  their eleven is what the one buys and the other is famous for), and every other
  persona keeps the limit.

  What it does not do: no money is booked. A computer club still has no account, the
  ceiling is the same for a club every time, and a club that sold a player for 100
  million can spend no more than before. Your own club is not touched: your players
  are not in these lists (offers for them go another way), and what you can buy is a
  matter of your budget.

  *Version 6: the ceiling gives way.* Version 5 refused every player above the
  ceiling. Played by hand it gave fewer transfers than the game alone. Between two
  computer clubs the game has no offer and no price, so a club cannot "bid less" or
  "bid more"; what the module can decide is how far above its ceiling a club still
  reaches. Four settings:

  - `CEILING_STRETCH` (50): above the ceiling the chance falls evenly, to none at 50
    percent above it. A player 10 percent above is within reach of four clubs in five
    of the group, 25 percent above of every second one. No dice: which club reaches
    how far for which player comes from the player's id and the club's id, so the
    same club gives the same answer every day and two clubs of one group differ.
  - `CEILING_NEED` (30): a club in need counts its ceiling 30 percent higher. In need
    is a club in its second search (it found nobody for the position) and a club that
    asks for a player of a certain standing, which is how the game's plan marks the
    key player a club wants on the last day of a window. The stretch comes on top:
    1.3 x 1.5, so never beyond 1.95 times the ceiling.
  - `CEILING_LISTED` (70): of a player his club has listed for sale, 70 percent of
    the value count.
  - `CEILING_FREE` (50): of a player without a contract, 50 percent. No fee is due
    for him; what is left stands for his wages.

  With 0, 0, 100, 100 the module chooses exactly as version 5 did.

The **yearly budget step** of 28 and 30 June is not changed, and needs no change: its
two grants are fractions of the wage bill and of the fees of the ten most valuable
players, so they grow with the module's salaries and values by themselves. The test
runs that code for both days and compares it with `money_cave.june_grants`.

### In-Game Budget Rebalancing Slider (Approach A)

In PES 2017 Master League, the game strictly isolates the Transfer Budget (`mode_data + 0xdddfc4`)
and the Salary Budget (`mode_data + 0xdddfdc`). Often managers have ample transfer funds but cannot
finalize free agent signings or vital player contract renewals due to small salary budget shortfalls.

The **Budget Slider** allows flexible in-game reallocation of funds between the Transfer Budget
and Salary Budget using realistic financial math:
- **Contract Amortization Math**: Transfer fees are one-time capital expenditures, whereas player
  salaries are recurring annual operating obligations. Simply converting transfer money 1:1 to salary
  would distort the multi-year economy (a £10M annual salary over a 4-year contract commits £40M in cash).
  With `BUDGET_SLIDER_RATIO = 4.0` (matching the standard 3-5 year prime contract duration in PES 2017):
  $$\Delta \text{Salary Budget} = \frac{\Delta \text{Transfer Budget}}{4.0}$$
  $$\Delta \text{Transfer Budget} = \Delta \text{Salary Budget} \times 4.0$$
  - Reallocating £10M transfer budget adds £2.5M to the annual salary budget.
  - Freeing £2.5M from the annual salary budget adds £10M to the transfer budget.
- **In-Game Control**:
  - After replacing `modules/MLMoney.lua`, fully restart Sider and PES. Check for `Budget keys active:`
    in `sider.log`. No LuaJIT extensions, LiveCPK polling, or command file is needed.
  - With a loaded Master League career and the game window focused, **tap F6** to move £4M
    from transfer funds into £1M of annual salary room. **Tap F7** to move it back.
    If the current finance screen still shows its old values, leave and reopen it.
  - The main Windows message pump handles initial F6/F7 keydowns (not auto-repeats) and
    forwards the original message to PES. This is checked in emulation, not on Windows.
- **Safety**:
  All transactions include floor protection and bounds checking ($[0, 99999999]$ in stored units, up to £9.99B),
  preventing budget deficits or integer overflows.

Not changed: the second salary formula (`fcn_038ab5ea`, used for clubs of the league
numbers 60 to 62 and for some players in one mode), the lists of the league numbers 60
and 61, the list for second divisions unless `LEAGUE_2` is set, the cup table of game
mode `0x28`, the growth of players, the rest of the way computer clubs choose players
(positions, ages, the three candidates and the pick among them, section 9).

### Settings (top of the file; amounts in millions as on the screen)

| setting | default |
|---|---|
| `VALUE` | rating 60: 0.3, 65: 0.8, 70: 2.5, 75: 8, 80: 25, 85: 65, 88: 110, 90: 150, 92: 185, 94: 215, 99: 260 |
| `AGE` (percent) | up to 19: 130, falling to 100 at 25 and 26, then 27: 97, 28: 90, 29: 80, 30: 65, 31: 50, 32: 36, 33: 26, 34: 18, 35: 12, 36: 8, 37: 6, from 38: 5 |
| `POSITION` (percent) | GK 45, CB 85, LB and RB 75, DMF 95, CMF 100, LMF and RMF 95, AMF 105, LWF and RWF 110, SS 105, CF 110 |
| `SPREAD` | 12 percent up and down; 0 switches it off |
| `FAME` | 10 percent per 1,000 points |
| `TALENT` (age, ordinary rating) | 16: 62, 18: 66, 20: 70, 22: 74, 23: 76; no bonus from 24 on; `false` = no talent bonus |
| `TALENT_STEP`, `TALENT_MAX`, `TALENT_CAP` | 6 percent per rating point above the ordinary rating, at most 60 percent and 40 million (before position, spread and popularity) |
| `SALARY` (first club of the ranking; a club outside the first 250 pays this divided by `PAY_GAP`) | rating 60: 0.2, 65: 0.5, 70: 1.2, 75: 2.6, 80: 5.5, 85: 10, 88: 15, 90: 20, 92: 25, 94: 30, 99: 36; `false` leaves salaries alone |
| `SALARY_AGE` (percent) | 16: 45, 18: 50, 20: 62, 22: 76, 24: 90, 26 to 31: 100, 33: 92, 35: 80, 37: 65, 39: 50 |
| `BUDGET_TRANSFER` | 3 (the game: 2); `false` leaves the game's code |
| `BUDGET_SALARY` | `false` = the game's own 2 |
| `BUDGET_SLIDER` | `true`: in-game budget rebalancing slider enabled; `false` = disabled |
| `BUDGET_SLIDER_RATIO` | 4.0 (range 1.0 to 10.0): contract amortization ratio (e.g. 10M transfer <-> 2.5M salary/yr) |
| `BUDGET_SLIDER_STEP` | 4.0: step size in millions (e.g. £4M transfer <-> £1M salary per step) |
| `INCOME_WAGES` | 60 percent of the wage bill added to the yearly income; `false` = nothing added |
| `INCOME` | `false`; a number is the percent of the game's two yearly amounts (10 to 1000) |
| `CUP` (competition, stage, millions) | Champions League (2): winner 82.12, runner-up 75.62, semi-final 57.12, quarter-final 42.12, first knock-out round 29.62, group stage 18.62. Europa League (3): 26.06, 20.06, 13.06, 8.86, round of 16 6.36, first knock-out round 4.61, group 4.31. UEFA Super Cup (4): 5 and 4. Libertadores (5): 32.25, 15.25, 8.25, 5.95, 4.25, 3. Sudamericana (6): 9.5, 5, 3, 2.2, 1.5, 0.9. AFC Champions League (8): 12, 6, 2, 1.4, 1, 0.8. Club World Cup (1): 5 and 4. `false` leaves the game's amounts |
| `LEAGUE` (place 1 to 22) | 53.1, 50.4, 47.7, 45.0, 42.4, 39.8, 37.1, 34.5, 31.9, 29.1, 26.5, 23.8, 21.2, 18.6, 15.9, 13.3, 10.7, 7.9, 5.3, 2.6, 2.6, 2.6; `false` leaves the game's list |
| `CUP_TV` (competition, millions) | Champions League (2): 23.7; Europa League (3): 5.5; `false` = nothing added |
| `CUP_NATIONAL` | winner 3.91, runner-up 2.91, semi-final 1.41, quarter-final 0.46, round of 16 0.235, round before 0.115 (the game: 2, 1, 0.5, 0.1, 0.05, 0.03); `false` leaves the game's amounts |
| `LEAGUE_BY_ID` (league number, list or percent of `LEAGUE`) | 19 Spain: 58.4 down to 0.9. 50 Germany: 71.1 down to 6.6. 18 Italy: 74.2 down to 3.0. 21 Netherlands: 14.73 down to 3.37. 29 Brazil: 8.0 down to 2.7, places 17 to 20 nothing. 20 France: 9 percent. 22 Portugal, 30 Argentina, 51, 52, 67 Chile: 5 percent. Every other first division: `LEAGUE`. `false` = `LEAGUE` for all |
| `LEAGUE_2` (place 1 to 24) | `false` = the game's list (2 million down to 25,000) |
| `PRIZE_TO_BUDGET` | 75 percent; `false` = prizes go to the balance only |
| `PAY_GAP` | 3 (the game: 2); `false` leaves the game's code |
| `BONUS` | 300 percent; `false` leaves the game's code |
| `YOUNG_YEARS` | 5 (the game: 3); `false` leaves the game's code |
| `WRITE` | `true`; `false` = check and report only |
| **in `MLTransfers.lua`:** | |
| `WRITE` | the same, for this file |
| `CEILING` (ranking places 1-10, 11-20, 21-50, 51-80, 81-120, 121-170, 171-220, 221-260, 261-300, others) | 200, 100, 50, 28, 18, 12, 8, 6, 4.5, 3: the highest value a computer club of that group signs; 0 in a place = no ceiling for the group; `false` = computer clubs choose as in the game |
| `CEILING_STRETCH` (0 to 300) | 50: a club reaches a player up to 50 percent above its ceiling, the further above the less often; 0 = nothing above the ceiling, as in version 5 |
| `CEILING_NEED` (0 to 300) | 30: the ceiling of a club in need (second search, or a slot that asks for a player of a certain standing) counts 30 percent higher; 0 = need changes nothing |
| `CEILING_LISTED` (0 to 100) | 70: percent of the value that counts for a player listed for sale; 100 = he counts like any other |
| `CEILING_FREE` (0 to 100) | 75 (version 1: 50; versions 2 to 4: 100): the same for a player without a contract |
| `SELL_SIDE`, `PERSONA`, `SCOUTING` and the persona settings | new in version 2: see the section on version 2 above |
| `CEILING_RATING` | `true`: in its second search a computer club takes nobody rated above the top of its own rating range; `false`: from 99 down, as in the game. Used only with `CEILING`. A persona can switch it off for itself with `rating = false`: Galactico and Retirement team have it that way |

Where the prize defaults come from. Cups: the fixed payments per stage of 2025/26
(Champions League, Europa League, UEFA Super Cup), of 2025 (Libertadores, Sudamericana,
Intercontinental Cup for the Club World Cup) and of 2024/25 (AFC Champions League), as
published in the press, added up to the stage where the run ends, because the game pays
a cup once. The payments per win and the television shares are not in them; with those
a Champions League winner got about 140 million in 2024/25, so the defaults are on the
low side for the big cups. Euros and dollars are taken as the same. League: the Premier
League's payments by place of 2024/25 (pounds); the equal share every club gets is not
in it.

Version 4 adds, from press figures as well: `CUP_TV` is UEFA's "value" share of 2024/25
divided evenly by the 36 clubs; a real club gets between a few million and about 45.
`CUP_NATIONAL` is the FA Cup of 2024/25 from the third round on, added up. One list
serves every country, so the Copa del Rey, the Coppa Italia and the others pay FA Cup
money. `LEAGUE_BY_ID` holds figures of different kinds, because the leagues publish
different things:

| league | what the numbers are |
|---|---|
| 19 Spain | the part of LaLiga's television money that is shared by place, 2023/24 |
| 50 (Germany in the usual patches) | a club's television money of 2024/25 less about 26 million, roughly what every club gets. It is shared by the results of several years, not by this year's place |
| 18 Italy | the same for 2023/24 less the equal share of 26.8 million. Ten amounts are published figures; places 11 to 20 are filled in evenly |
| 21 Netherlands | all of a club's media money of 2026/27, also by the results of several years |
| 29 Brazil | the prize by place of 2024 at 6 reais to the euro |
| 20 France | 9 percent of `LEAGUE`, the size of the television deal of 2025/26 |
| 22, 30, 51, 52, 67 | 5 percent of `LEAGUE`. **An estimate**; no published list is behind it |

Not found, and so not in the defaults: Portugal, Argentina and Chile by place, every
second division (the Championship pays about 10 million to every club whatever its
place), the Copa del Rey, the Coppa Italia, the Coupe de France. The league numbers
are the game's own (`../MASTER_LEAGUE.md`, appendix D); a list applies to a league
only if the game hands that number to its prize function, which was run in the
emulator with made-up numbers and not seen in a career.

The competition numbers 1 and 5 match names of the edit file. The numbers 2, 3, 4, 6
and 8 are **inferred** from the shape of the game's table (which stages have a prize),
and so are the stage names. If one of them is another competition, that one gets the
amounts meant for the first. `python3 ../tools/prize.py <exe>` prints the game's table.

The defaults were set by hand against published figures of 2026: the most valuable
players at 200 to 220 million, the 25th at 100 million; Bruno Fernandes at about 42
million and 300,000 pounds a week; Manchester United's summer of 145 million pounds
spent and 99 million net. They are a starting point, not a fit to a data set.

What the defaults give for the players and squads of the edit file in this repository
(worked with `money_cave.py`, `SPREAD` left out, every club taken with club part 300 of
the popularity; not read from a career):

| | with the talent bonus (version 4) | without (`TALENT = false`, as in version 3) |
|---|---|---|
| most valuable | Lamine Yamal 287 million, Jude Bellingham 239, Erling Haaland 204, João Neves 185, Michael Olise 183, Kylian Mbappé 183, Pedri 175, Vitinha 167 | Lamine Yamal 238, Erling Haaland 204, Jude Bellingham 193, Michael Olise 183, Kylian Mbappé 183, Pedri 175, Vitinha 167 |
| 25th, 50th, 100th, 200th player | 111, 79, 53, 35 million | 93, 70, 51, 33 million |
| transfer budget of a new career | Manchester United 120 million, Manchester City 228, Real Madrid 265, Paris Saint-Germain 282, Liverpool 159, Juventus 96, Brentford 61, Sevilla 29, Burnley 19 | Manchester United 107 (72 with the factor 2, 39 with the game's own formulas), Manchester City 208, Real Madrid 232, Paris Saint-Germain 254, Liverpool 147, Juventus 88, Brentford 59, Sevilla 29, Burnley 19 |

398 of the 13,760 club players get a talent bonus. The largest: Lamine Yamal (rating
90, age 19) 238 to 287 million, Arda Güler (85, 21) 94 to 142, Désiré Doué (86, 21)
112 to 160, Jude Bellingham (90, 23) 193 to 239, Florian Wirtz (86, 23) 98 to 143,
Jamal Musiala (87, 23) 116 to 162, João Neves (88, 22) 141 to 185. These are above
the published values of 2026 for some of them; lower `TALENT_STEP` or `TALENT_CAP`
if they look too high in the game.

Income and wages of one season, in millions, before prizes and transfers. Squads from
the edit file; **the ranking places are guesses**, so the columns show the size of the
effect and not what a career will read:

| club | place taken | wages, game | wages, module | income, game | income with `INCOME_WAGES = 60` | income less wages: game | module, no income setting | with `INCOME_WAGES = 60` | with `INCOME = 150` instead |
|---|---|---|---|---|---|---|---|---|---|
| Real Madrid | 1 | 93 | 235 | 278 | 419 | 185 | 43 | 184 | 182 |
| Paris Saint-Germain | 2 | 89 | 222 | 282 | 415 | 193 | 60 | 193 | 201 |
| Manchester City | 3 | 78 | 193 | 275 | 391 | 197 | 83 | 198 | 220 |
| Bayern München | 4 | 80 | 195 | 277 | 394 | 197 | 82 | 199 | 220 |
| Manchester United | 12 | 65 | 143 | 266 | 352 | 201 | 123 | 209 | 256 |
| Juventus | 20 | 59 | 128 | 221 | 298 | 162 | 93 | 170 | 203 |
| Porto | 35 | 49 | 92 | 214 | 269 | 165 | 122 | 177 | 228 |
| Ajax | 40 | 39 | 68 | 211 | 252 | 172 | 144 | 184 | 249 |
| Sevilla | 60 | 33 | 54 | 201 | 233 | 168 | 148 | 180 | 248 |
| Brentford | 90 | 39 | 69 | 186 | 227 | 147 | 117 | 159 | 210 |
| Leeds United | 110 | 36 | 65 | 176 | 215 | 141 | 111 | 150 | 199 |
| Burnley | 120 | 29 | 39 | 171 | 195 | 142 | 132 | 155 | 218 |
| Blackburn Rovers | 200 | 13 | 12 | 131 | 138 | 118 | 119 | 126 | 185 |

The module's salaries cost the strongest squads about 140 million a year more than the
game's and a weak squad nothing more. A share of the wage bill follows that; one
percent for every club does not, which is why `INCOME` is off. The side effect of
`INCOME_WAGES`: of every salary the club adds, 60 percent comes back on 1 July, so a
large wage bill hurts the balance less than its size says. The salary budget still
limits it.

`CEILING` and the club ranking. The ten amounts are for the ten groups of ranking
places the game uses. `python3 ceiling_survey.py <exe> <edit file>` prints what they
mean for the squads of the edit file, with the default settings and `SPREAD` off, in
millions:

| places | rating range | `CEILING` | middle club: most valuable player | third most valuable | players in the range above the ceiling | mean age at the top of the range: all / under the ceiling |
|---|---|---|---|---|---|---|
| 1-10 | 83-99 | 200 | 158.3 | 93.3 | 1.0 % | 27.8 / 28.5 |
| 11-20 | 76-86 | 100 | 59.4 | 40.2 | 0.6 % | 27.9 / 28.5 |
| 21-50 | 73-83 | 50 | 46.4 | 27.1 | 0.7 % | 28.8 / 29.3 |
| 51-80 | 70-80 | 28 | 22.5 | 13.9 | 1.1 % | 27.9 / 28.5 |
| 81-120 | 67-79 | 18 | 14.4 | 9.9 | 1.8 % | 27.8 / 28.9 |
| 121-170 | 63-78 | 12 | 10.1 | 5.7 | 3.1 % | 27.7 / 29.8 |
| 171-220 | 59-77 | 8 | 7.1 | 4.3 | 4.2 % | 27.8 / 30.4 |
| 221-260 | 55-76 | 6 | 5.5 | 3.4 | 5.6 % | 27.8 / 31.1 |
| 261-300 | 51-75 | 4.5 | 4.7 | 2.4 | 7.5 % | 27.8 / 31.4 |
| others | 47-74 | 3 | 2.2 | 1.4 | 11.4 % | 27.9 / 32.1 |

A club looks from the top of its range down, so what counts is the top. The same
survey for the three highest rating points of each range (players with a contract who
are not listed):

| places | above the ceiling: passed over by version 5 | version 6, passed over in the usual search | version 6, club in need | version 6, out of reach of every club of the group |
|---|---|---|---|---|
| 1-10 | 10.0 % | 5.4 % | 0.6 % | 0.0 % |
| 11-20 | 8.2 % | 4.7 % | 0.7 % | 0.0 % |
| 21-50 | 6.8 % | 3.4 % | 1.1 % | 0.0 % |
| 51-80 | 9.6 % | 4.2 % | 1.6 % | 0.4 % |
| 81-120 | 19.1 % | 9.5 % | 2.8 % | 0.6 % |
| 121-170 | 37.1 % | 20.2 % | 7.8 % | 2.7 % |
| 171-220 | 48.1 % | 30.6 % | 13.2 % | 4.2 % |
| 221-260 | 53.7 % | 35.1 % | 15.8 % | 5.4 % |
| 261-300 | 57.9 % | 41.2 % | 19.8 % | 8.1 % |
| others | 63.5 % | 50.4 % | 30.7 % | 15.9 % |

"Passed over" in the two middle columns is the mean over the clubs of the group: each
club reaches a different part of the players above the ceiling.

Two things in this table are guessed, because the edit file does not hold them: the
club ranking (the clubs are ranked by the mean rating of their best eleven; the game
has its own table) and each player's popularity (which moves a value by a few
percent).

So a ceiling is about what the middle club of a group has in its most valuable
player, with more room at the top. Over the whole rating range it turns away few
players. At the top of the range, where the search begins, version 5 turned away more
than half at the small clubs: the young ones, so the best players a small club could
still sign were a few years older (last column of the first table). Version 6 leaves
about a third of that for a club in need. In the second search the range is gone and
the ceiling, with `CEILING_RATING`, is what keeps a small club from the best players. A stricter set (15, 8,
4.5, 2.5, 1.5, 1 for the six lower groups) turned away 42 percent of the range at the
smallest clubs and left them players of 35 at its top; it was dropped. If you change
`VALUE` much, change `CEILING` with it. `0` in a place of the list means no ceiling
for that group.

### Money and Transfers installation diagnostics

Use [the install order above](#install-and-verify). Replace, rather than stack, older Money v5/v6 files: they implement their own price ceiling. Check Money’s `RESULT` first, then Transfers’.

What `MLTransfers.lua` says when it writes nothing:

| line in `sider.log` | cause | what to do |
|---|---|---|
| `RESULT: nothing written. MLMoney.lua is not installed ...` | no line for `MLMoney.lua` in `sider.ini`, or it stands below, or `MLMoney.lua` itself wrote nothing | put its line above; read the `RESULT` line of `MLMoney.lua` |
| `... The MLMoney.lua that is installed is not the version this module was made for` | another version of `MLMoney.lua` | take both files from the same folder of this repository |
| `... The game's choosing code is changed already` | an `MLMoney.lua` of version 6 is still in use, or version 1 of `MLTransfers.lua` beside version 2, or `MLTransfers.lua` stands twice in `sider.ini` | replace the old file; one line only |
| `... This game does not hold what the module expects` | one of the ten `check:` lines of the transfer code says `DIFFERENT`, or "free memory" says `NOT EMPTY` | send the log |
| `... CEILING, SELL_SIDE and PERSONA are off` | the settings | |

In each of these cases the money part stays in. The "free memory" line of
`MLTransfers.lua` is a place new in its version 2 (`0x047d4200`): the file of the game
holds zeros there, but whether the running game leaves it alone has not been seen yet,
which is why this line of the log matters. (The place of version 6 and of version 1,
`0x047d3c40`, was empty in the running game: version 6 was played through a window.)

To undo: remove the two lines from `sider.ini` (the line of `MLTransfers.lua` alone: the
transfers of the game come back and the money stays). No file of the game is changed.

**A running career.** Salaries are stored in the contracts and the budgets were made
from the old numbers. With the module on, values change at once, salaries only at a new
contract, and the budgets stay as they are. Prizes, the share for the transfer budget,
the yearly income and the contract limit work in a running career from the day the
module is on. For a running career set `SALARY = false`, `PAY_GAP = false`,
`BONUS = false` and `INCOME_WAGES = false` (its 60 percent is sized for the module's
salaries), or start a new career. The price ceiling needs no new career: it works from
the next time the computer clubs choose players. Deals they have already chosen are
kept.

### Version 2 in the game (November 2026)

The user ran version 2 with `SPREAD = 0`: all checks "as expected", three places
written, `RESULT: installed. Changed: values, salaries, transfer budget.` In a new
career with Manchester United:

- Bruno Fernandes (rating 89, AMF, age 32) showed a value of **52,973,200**. The
  module's formula gives exactly that for popularity 910, and for no other popularity
  from 0 to 3,000 (`test_money.py`, ok 5). In the older career his popularity was 955,
  which would give 53,191,700; a new career starts him lower.
- The transfer budget was **106,925,700**. The estimate made from the edit file, with
  every player's popularity guessed, was 107 million.

So the value routine runs in the game and reads rating, age, position and popularity
from the right places, the budget routine runs, and the budget field is the one the
screen shows. Not seen yet: salaries of new contracts, `SPREAD` above 0, a season.

### What to look at with versions 3, 4 and 5

Nothing of the parts added since version 2 has run in the game. In the order of effort:

1. `sider.log` as under Install. If a `check:` line says `DIFFERENT`, nothing is written;
   send the log.
2. A new career with Manchester United and the same edit file started with a transfer
   budget of 106,925,700 under version 2. With `TALENT = false` it must be the same
   again, which shows that the larger module did not disturb the old part. With the
   talent bonus on it is higher; the estimate is 120 million.
3. The value of a young player before and after: one of 21 or younger with a rating
   of 80 or more must read higher than with `TALENT = false`, a player of 24 or older
   the same.
4. Note the salary of two players in the new career, with their rating, age and team
   role: one star and one captain or leader. From these the pay gap and the bonus can
   be checked against `money_cave.py`.
5. Offer a new contract to a player of 23 or younger. Lengths of 4 or 5 years must now
   be possible; the game never offered more than 3 before.
6. Note the transfer budget on the day before and the day after your club goes out of
   a cup or wins one, and at the end of the league. It must rise by 75 percent of the
   prize. Premier League (league 17), place 1: 53,100,000, so 39,825,000 more budget.
   Spain (19), place 1: 58,400,000. A national cup: winner 3,910,000, so 2,932,500
   more budget. If a league pays the amounts of `LEAGUE` although `LEAGUE_BY_ID`
   names it, the league number in the setting is not the one the game uses.
7. The balance on 30 June and on 2 July. The rise is the two yearly amounts, each
   changed by up to 10 percent by the game; with `INCOME_WAGES = 60` the second one
   holds 60 percent of the wage bill.
8. The price ceiling can only be seen in the transfer news. Play through the first
   transfer window of a new career and note three or four signings of computer clubs:
   player, his value on the screen, the buying club. A club outside the first 300 of
   the ranking must not sign a player valued above 3,000,000, one of the places 51 to
   80 none above 28,000,000. The value on a screen can differ from the one the test
   uses by the game's random change of up to 20 percent, so a signing a little above
   a ceiling is no fault, and with version 6 a signing up to 1.5 times the ceiling
   (1.95 times for a club in need) is as intended.
9. The number of signings. Version 5 gave fewer than the game alone, by a test played
   by hand. Count the signings of computer clubs in one window with version 6 and, if
   you can, in the same window of the same save with `CEILING = false`. If version 6
   is still clearly lower, set `CEILING_RATING = false` and count once more: that
   tells whether the price or the rating limit of the second search holds the clubs
   back. Why version 5 lost transfers was not found out; see "Not shown by the test".

### How it works

Up to 26 places of the game's code are changed and two pieces of unused memory are
filled (`money_cave.py` has the layout and the source of the 14 routines):

| where | before | after | setting |
|---|---|---|---|
| `0x038ab8db`, 17 bytes, fee function | `9,000 x max(0, rating - 68)` into `edi` | call to the value routine; it also sets the factor of the salary part to 0 | always |
| `0x038ac875`, 7 bytes, salary function | start of the 98 bytes that compute the rating part | call to the salary routine, jump over the rest | `SALARY` |
| `0x038adc47`, 5 bytes, budget function | the mean value of the best 16, doubled | call to a routine that multiplies by `BUDGET_TRANSFER` | `BUDGET_TRANSFER` |
| `0x038add08`, 8 bytes, budget function | wage bill + twice the mean salary of the best 16 | call to a routine that uses `BUDGET_SALARY` in place of the 2 | `BUDGET_SALARY` |
| `0x038aa400`, `0x038aa408`, `0x038aa423`, 4 bytes each, `cup_prize` | address of the game's cup table (`0x0216b178`) in three instructions | address of the module's copy of the table | `CUP` |
| `0x038aa2dd`, 7 bytes, `league_prize` | `mov eax, [ebp + eax*4 - 0x17c]`: the first list, built on the stack | call to a routine: if the league number in `edi` is one of `LEAGUE_BY_ID`, the amount of its list, else of the module's first list | `LEAGUE` (and `LEAGUE_BY_ID`) |
| `0x038aa2c6`, 7 bytes, `league_prize` | the same for the second list | the same | `LEAGUE_2` |
| `0x03640ac5` and `0x03640b78`, 5 bytes each, `prize_step` | `call balance_add` for a league and for a cup prize | call to a routine that calls `balance_add` and then, in Master League, `transfer_budget_add` with the share | `PRIZE_TO_BUDGET` |
| `0x038aca1b`, 4 bytes, salary function | address of the shared 0.004 in `fmul qword [0x01f2fe88]` | address of a number of the module, `(PAY_GAP - 1) / 250` | `PAY_GAP` |
| `0x038aca2b`, 6 bytes, salary function | `add esi, [ebp - 0x50]`: role bonus + popularity part | call to a routine that first multiplies the role bonus by `BONUS` | `BONUS` |
| `0x038acd96`, 12 bytes, salary function | award bonuses + band bonus into `eax` | call to a routine that multiplies their sum by `BONUS` | `BONUS` |
| `0x03887fc1`, 5 bytes, contract limit | `mov eax, 3` | `mov eax, YOUNG_YEARS` | `YOUNG_YEARS` |
| `0x038adeaa`, 9 bytes, `season_income` | `mov eax, [ebp + 8]; push eax; call club_popularity`, right after the call that works out the wage bill | call to a routine that keeps the wage bill in the function's own local and goes on to `club_popularity` with the same argument | `INCOME_WAGES` |
| `0x038adeee`, 6 bytes, `season_income` | `lea eax, [esi - 3451330]`: the last step of the amount | call to a routine that does the same, applies `INCOME` and adds the share of the wage bill | `INCOME_WAGES` or `INCOME` |
| `0x038a9e9c`, 6 bytes, amount by rank | `imul eax, eax, 5000` | call to a routine that does the same and applies `INCOME` | `INCOME` |
| `0x038ae025`, 6 bytes, `club_money_setup` | `add esi, 15000` | call to a routine that does the same and applies `INCOME` | `INCOME` |
| `0x038aa43a`, `...446`, `...452`, `...45e`, `...46a`, `...476`, 4 bytes each, `cup_prize` | the six amounts for a cup without a row: 20000, 10000, 5000, 1000, 500, 300 (the numbers in six `mov edi`) | the six amounts of `CUP_NATIONAL` | `CUP_NATIONAL` |
| `0x047b0200`, 3,568 bytes | zero | the tables (value, salary, two by age, position, talent), the cup table, two league lists, 12 lists by league, the single numbers, 13 routines of 226, 53, 26, 22, 53, 24, 21, 31, 8, 19, 18, 50 and 13 bytes | always |
| `0x0365fb0d`, 9 bytes, `ai_candidates` | `mov ecx, [ebp + 0x24]; push esi; call 0x041293c0`: the player who passed every test is added to the list of candidates | call to the routine of `MLTransfers.lua`, which goes on to that function or to the game's "next player" at `0x0365fb28` | `CEILING`, `SELL_SIDE` or `PERSONA` |
| `0x047d4200`, 3,584 bytes (version 2: 3,424; version 1: `0x047d3c40`, 384 bytes) | zero | ten ceilings, ten highest ratings for the second search, twelve single numbers, the two rating ranges by level, the personas by level (10 x 8), 16 personas of 20 bytes, 192 named clubs (persona and id), 64 pairs of rivals, the routine of 1,555 bytes (version 3: 1,520), the seven numbers of `KNOWN_FAME`, `STRICT_FREE`, `KEEP_BEST`, `KNOWN_FROM` and `AGE_SHIFT` (version 3: the last five) | the same |

**The routine of `MLTransfers.lua`** (this part: as in version 1; the steps of version 2 and all it reads are written out at the top of `money_cave.py`). `ai_candidates` is not handed the club's level. Its only
caller, `ai_pick_candidate`, has it as an argument, so the routine reads it from that
function's stack frame (the saved `ebp`), and the byte there that says "second
search". The buying club is the first number of the plan record and the standing the
slot asks for is behind the last argument, both among `ai_candidates`' own arguments
(`[ebp + 0x18]`, `[ebp + 0x30]`). It does so only if `ai_candidates` is about to return to one of its two calls
in `ai_pick_candidate` (`0x03660d58`, `0x03660db9`; a scan of the exe found no other
call) and the level is 0 to 9. In every other case the player is taken as in the game:
when something is not as expected the routine changes nothing. The rating is fetched
with the same call the fee function uses, the value with the module's own value
routine. A refused player leaves the routine by a jump to the place the game's own
failed tests jump to. `ebx`, `edi`, `esi` and `ebp` come back as they were.

The limit, in whole numbers (each division drops the remainder):

```
limit = ceiling of the level
in need (second search, or the slot asks for a standing):  limit = limit * (100 + CEILING_NEED) / 100
h     = ((player id, 16 bits) ^ (player id, 32 bits) * 0x01000193 ^ club id * 0x9e3779b1) * 0x85ebca6b >> 24      0 to 255
limit = limit + limit * (h * CEILING_STRETCH) / 25600
price = value * CEILING_FREE / 100      status 1 or 2 (+0xb4, bits 0-3)
        value * CEILING_LISTED / 100    else, with bit 29 or 30 of +0xb8
        value                           else
refused if price > limit
```

The rating limit of the second search comes before this and is not moved by it.

The memory is the end of the code section `.trace`: its content ends at `0x047b005d` and
its last page runs to `0x047b0fff`; the file holds zeros from `0x047b005e` on. That page
is full (version 5 had its ceiling routine below the tables, at `0x047b0130`; version 6
leaves that piece unused). The second piece is the end of the next section, `.xcode`:
its content ends at `0x047d3a42`, the file holds zeros up to `0x047d3dff`, the next
section begins at `0x047d4000`, and a scan found no call, jump or stored address into
`0x047d3000`-`0x047d3fff`. Both sections are readable, writable and executable in
the exe's header, so the routines can run there whatever Sider does with the page
protection. No call or jump of the exe goes into that range. For the changed places a
scan of the exe found no call or jump into the inside of any of them; for the three
address operands in `cup_prize` this was read from the listing of the function, not
scanned.

No shared constant is changed: the 0.004 of the club factor has five other users in the
exe, so the salary function is given a number of its own.

After each changed place the game's code was read for what it still needs. The league
routine uses `ecx` and `edx`; the game loads both anew before it reads them. The income
routines change the flags; a `test eax, eax` follows two of them and the third is
followed by code that reads no flag. `[ebp - 4]` of `season_income`, where the wage
bill is kept, holds a flag byte for the wage bill function that nothing reads after
that call.

What the routines read of a player record: the age (6 bits at `+0x1c`, bit 7) and the
registered position (4 bits at `+0x04`, bit 28), which is where the game's own getter
`fcn_038278b0` reads fields `0x2b` and `0x00`; the popularity (`+0xb4`, bit 11) as the
fee function itself does; the id (`+0x2c`, `+0x30`) as the rating function does.

Order of the module's work: check the settings; build the tables; compare 5,120 bytes
of the game, in twenty pieces, with what the exe file has (the code around every
changed place, whole functions where they are short: `cup_prize`, `league_prize`,
`balance_add`, `transfer_budget_add`, the contract limit, `season_income`, the amount
by rank; the game's cup table), and in `MLTransfers.lua` 4,075 bytes more in ten pieces
(`ai_candidates` whole, `ai_pick_candidate` whole, the two functions with the rating
ranges, the functions that give a player's club, his status band and his club's level,
the search of the club ranking, the rating call, the function that adds a candidate); see
that the memory is all zero; write tables and routines; read them back; only then
change the places one by one and read each back. If a comparison fails, nothing more is
written. `MLTransfers.lua` works in the same order on its own piece of memory and its
one place, after it has found `MLMoney.lua`. The part of each file that holds the
routines, the places and the compared bytes is made by `python3 money_cave.py lua <exe>`
(`MLMoney.lua`) and `python3 money_cave.py lua <exe> transfers` (`MLTransfers.lua`);
the test fails if a file differs from it.

### What the test shows

Run `python3 test_money.py /path/to/PES2017.exe` from `sider/`. The native tests compare unmodified code with `tools/money.py`, patched code with `money_cave.py`, and installed bytes with the generator. The recorded run covered 3,000 salary and 3,000 fee cases, 150 squads, 2,626 cup and 11,648 patched league prize cases. Switches are tested alone, off and at their limits; mismatched bytes, invalid settings, failed writes and a missing Money prerequisite must not expose an active hook.

Live cross-check (Bruno Fernandes, rating 89): stock salary 7,259,700 and value 36,743,200 match the formula at popularity 955. With Money v2, spread off, age 32 and AMF, value 52,973,200 matches popularity 910. These are fits to the displayed amounts, not direct reads of popularity.

The prize, budget, salary and income code of the game runs as machine
code in the emulator, with the module's changes in it. For the two places that pay a
prize the piece of `prize_step` around each call is run on its own, with a made-up
stack frame; `prize_step` as a whole (the walk over the competitions of the club) was
not run. The same holds for the yearly budget step: the piece of the money step from
the grade to the transfer grant is run for 28 June and for 30 June, not the whole
step, and for the piece of `club_money_setup` that makes the starting amount.
`season_income` and the amount by rank run as whole functions; the test also sees that
`season_income` hands the club to `club_popularity` and gives back `ebx`, `esi` and
`edi` as it got them.

The price ceiling: `ai_candidates` runs as a whole function with made-up lists of 1 to
14 players. Of eight cases, four start it at one of its two call instructions in
`ai_pick_candidate` with a made-up frame of that function (level, "second search"
byte); three run `ai_pick_candidate` itself from its first instruction to the end of
its two searches (`0x03660dce`), so that the level, the range, the search byte and the
order of the two sets are the game's; one calls it from somewhere else. The players
have a contract or none, a quarter are listed, the slot asks for a standing or for
none, the buying club is any number. Five things it asks are
answered by the test: the record of a player, his club, the date, and the two tests
taken to be the foreign-player and squad rules (always "yes"); the rating is a number
kept in the made-up record. Everything else is the game's code, with the changed place
and the routine in it. The list it returns is compared with `money_cave.candidates`:
without the module (the first three who pass, whatever they cost), with it, with the
ceiling of the level put where one player is exactly at the club's limit for him and 1
below it, with players the game's own tests refuse mixed in, with a number that is no
level, and entered from somewhere else (then it must list as the game does). After
each run the stack pointer, `ebp`, `ebx`, `esi`, `edi`, the player records and the
plan record must be as the game leaves them. The four numbers of version 6 are also
set to 0, 0, 100, 100 (the list must be version 5's), each alone, and to their
limits. The second half of `ai_pick_candidate` (which of the three is taken),
`ai_fill_slots` and the steps above them were not run.

Version 2 of `MLTransfers.lua` is tested the same way, with more made up around
`ai_candidates`: a club ranking in the mode data with the buying and the selling clubs
at random places (some named in `CLUBS`, some missing from the ranking, a ranking with a
count that cannot be), the pool's number of players per club (also for a club index
beyond the pool's table), players listed, in a deal, on loan, of no club, with any
status band, plans of every kind, any day of the year. Seven things the game's code
asks are answered by the test instead of the game: the record of a player, the date,
the foreign-player and squad rules, the status band of a player, and the two
functions that give a club's ranking record and level where `ai_pick_candidate` itself
asks them; the routine's own search of the ranking and its call for a player's club run
as machine code. The rating call is answered by the test too, which checks that the
routine asks as the fee function does and hands back a number with rubbish above its
lowest byte, as the game may. The list is compared with `money_cave.candidates` (in it, `accepts`)
for 750 cases with the file's settings (the module changes the list in about three of
four) and for 400 to 700 with each of the settings named under `ok 3`, among them
personas whose numbers are drawn anywhere inside their limits. One player in four is
put on a limit that chance meets too seldom (new with version 3): an id whose draw for
the age or for scouting is the buying club's number or one less (for a player without a
contract: the first draw at which `STRICT_FREE` lets him pass, or one less), a rating at the line
of his club's first team with a draw at one end of what the club keeps there, or an age
at one end of the ages the club wants; and in the winter month, every other case is
dated to a year in which the club's winter draw is at its limit. Of eight players two
get the popularity `KNOWN_FAME` or one less and three a lower one (the field holds 0 to
4,095, the game's numbers end near 1,100, so chance alone would make nearly every
player famous). One player in sixteen stands on `KNOWN_FAME` itself with a contract, not
listed, and with a scouting draw at which the club does not know him, so that only his
name lets him through. 600 cases use personas
that refuse for the age and nothing else; in them `strict` is 95 and `STRICT_FREE` 79,
numbers at which a multiplication by 101 or 102 instead of 100 gives another answer. Each run of the game's code is stopped after
100,000 instructions, which no sound case reaches.

#### What fault injection caught — and missed

The counts below are historical mutation tests, **not** current gameplay pass rates. `python3 planted_faults.py <exe> files` alters source/model inputs; `routine` flips emitted instruction bits. The per-flip records are in `bitflips_v2.tsv`, `bitflips_v3.tsv` and `bitflips_v4.tsv`.

| Version tested | Result and regression to keep |
|---|---|
| Money v2 | 9/10 injected faults detected. Omitting the final `test esi,esi` escaped: after division a real CPU leaves the zero flag undefined. Keep the explicit test. |
| Money v3 / v4 | 20/20, then 52/52 (32 new). Correct output alone missed clobbered registers and a wrong `club_popularity` argument; check the ABI too. The wage-share rounding fault needed a near-limit wage bill. |
| Transfers v1 | All 37 file faults and 2,497/2,504 routine flips detected (earlier ceiling: 1,169/1,176). Six pushed the wrong register before the caller reloaded it; one destroyed the stack pointer but passed because the emulator mapped address zero. |
| Transfers v2 | 92/92 file faults before rivals; after rivals, 22/22 selected, not all 106 rerun. One bit per byte, initially 1,800 cases per flip: 1,354/1,413 detected after retrying survivors. Of 59 misses, 34 were equivalent, 7 on the 32-bit overflow path (one unsafe `ret`), 18 unresolved. Earlier code without rivals: 1,283/1,345 detected. |
| Transfers v3 | 22/24 selected file faults initially detected. One mutation was equivalent; an age draw exactly at `strict` needed a boundary case. After correcting the mutation and strengthening the test, both faults and five other boundary cases were detected; 100 older faults were not rerun. Routine sample: 1,456/1,520 detected. Of 64 misses: 43 equivalent, 6 overflow-path, 3 emulator-only crash blind spots, 2 real age/winter errors, 10 unresolved. |
| Transfers v4 | 20/20 selected file faults; 117 not rerun. Added explicit cases for popularity exactly at `KNOWN_FAME` and the `STRICT_FREE` draw at its threshold. Only the two new code regions were bit-tested; the other 1,517 bytes were not. |

After adding boundary inputs, every bit of the v3 age comparison/shift (443/464 detected) and winter draw (215/224) was tested; the remaining changes were equivalent on reachable inputs. The analogous v4 results were 129/136 for fame and 162/168 for `STRICT_FREE`, with 13 equivalent survivors. These targeted reruns are stronger evidence for the boundaries than random cases, but don't establish correctness of the untested paths or Windows stack/memory behavior.

Not shown by the test: for the price ceiling, anything above the two searches of
`ai_pick_candidate` (how the game calls it in a transfer window, how often the first
search finds nobody, whether squads stay full over seasons), and that the club level
the routine reads is the one the club's rating range was made from in a running game
(read in the disassembly, not run). That the status 1 and 2 of `CEILING_FREE` are the
players without a contract is taken from how the game closes their deals
(`MASTER_LEAGUE.md` 9.7), not seen in a game. **Why version 5 gave fewer transfers is
not known**, so it is not known either how much of them version 6 brings back. What
the code says (`MASTER_LEAGUE.md` 9.6): the game notes only the first three players
who pass and then takes one of them only if his club lets him go; if none of the three
can go, the position stays open and, unless the slot asks for a standing, the club
searches a second time. Without the module that second search starts at rating 99 and
finds other players. With `CEILING_RATING` it starts at the top of the club's own
range again, so it can meet the same three and fail again; version 6 changes that
only as far as the need raise lets dearer players in ahead of them. How often this
happens was not measured. The setting to try if signings stay low is therefore
`CEILING_RATING = false`. Sider's `memory.write` on the real game, the memory being empty
in the running game (the module checks it), that the game's cup table and code are in
the running game as in the exe file (the module checks it), which competition each
number of the cup table is, which league number the game hands to `league_prize` for
each league of a career (the lists by league rest on the numbers of appendix D), when
and how often the game calls the prize and income code in a season, what the screens
show of a prize, and the play of a season with the new numbers. The 30 June budget step
grades the year's result against the year before (section 6.7); larger prizes and the
wage share enter that result, and what this does over several seasons is not known.
The table of income and wages above is worked from the edit file with guessed ranking
places; no season was played. The emulator computes the club factor with 80-bit
floating point; if the game runs with a lower precision setting, a salary can differ by
1 (100 on the screen).

## MLSimMatch: simulated matches

Emulator only: it has not run in the game yet. Needs no other module and coexists cleanly
with `MLMoney.lua`, `MLTransfers.lua`, and `MLYear.lua` in any load order.

### What it changes

1. **Match outcome (`0x03707a1f`):** replaces vanilla's harsh `diff >= 4` / `diff >= 2`
   step function with a smooth Davidson win/draw/loss table plus `HOME_ADVANTAGE`
   (`2.5` OVR since the post-audit retune below; `ELO_SCALE = 4.0`, `BASE_DRAW = 0.28`)
   and ML captain role bonus via
   `CAPTAIN_WEIGHT` (`0.125`: +-10 gives +-1 OVR, +-20 gives +-2).
   **Version 8** changed these four defaults (version 7: `2.4`, `6.2`, `0.27`, `0.2`),
   because the tables of version 7 were too flat. Model of the module's own tables on
   the 20, 18 and 20 clubs of England, Germany and Spain in `ML saves/ML00000013
   (before)` (best eleven of each club, all fit; home and away against every other
   club; 2,000 seasons):

   | | version 7 | version 8 | real football (about) |
   |---|---|---|---|
   | points of the champion, England / Germany / Spain | 76 / 73 / 83 | 83 / 81 / 92 | 90 / 80 / 88 |
   | points of the last club | 29 / 25 / 30 | 23 / 20 / 25 | 21 / 22 / 24 |
   | best club: matches won | 53% / 63% / 63% | 60% / 73% / 72% | 70 to 75% |
   | best club: goals for a match | 1.50 / 1.79 / 1.76 | 1.71 / 2.03 / 1.98 | 2.3 to 2.6 |
   | home wins / draws / away wins, England | 44 / 26 / 31% | 44 / 25 / 31% | 45 / 24 / 31% |
   | goals a match | 2.36 / 2.49 / 2.46 | 2.51 / 2.65 / 2.62 | 2.8 / 3.0 / 2.6 |

   The lineups of such a league are only about 11 OVR points apart, which is why 6.2 points
   per e-fold made the best club win barely more than half its matches. The draws were
   already right (one match in four), so `BASE_DRAW` moved only to keep them there.
   `test_sim.py` (test 24) holds the defaults to this.
   **After the suggestion audit** the home advantage was raised again, from `1.6` to `2.5`
   (just above version 7's `2.4`): between equal teams home/draw/away becomes 48/27/25%,
   and in test 24's model of the twenty best clubs home wins rise from 43% to 47% while
   draws stay at 26% and the champion's points move by less than one (74 -> 73). Home
   wins now sit a touch above the ~45% of real football, accepted deliberately; test 24's
   bound for them was widened to 50% for this.
2. **Scorelines, Attack/Defense split & GK modifier (`0x03705feb`, `ATTACK_DEFENSE_SPLIT`, `GK_SCORE_MOD`):**
   moves `score_hook` to `CAVE_ET` and replaces vanilla's narrow goal tables with a
   7x7 2D conditional Poisson table (`WIN_CDF_2D`, 1,029 B) indexed by
   `(Winner_ATK - Loser_DEF - Loser_GK_delta)` and `(Winner_DEF - Loser_ATK + Winner_GK_delta)`,
   a clean-sheet (`gl = 0`) boost when `Winner_GK_eff >= 82` (`min(25, (GK_eff - 79) * 2)%`),
   and a 5-band match-tempo draw CDF (`DRAW_CDF_BANDS`, 25 B) indexed by
   `(ATK_H - DEF_A) + (ATK_A - DEF_H) - GK_H_delta - GK_A_delta`, damping `>= 4` GD
   blowouts (`GOAL_SCALE`). `GK_eff` uses `GK_CONDITION_OVR = { -6, -3, 0, 3, 6 }` (1.5x
   arrow swing) minus fatigue, with `GK_delta = clamp((GK_eff - 82) / 3, -4, 5)` and
   `pos == 0` excluded from `def_ovr` to avoid double-counting. When `ATTACK_DEFENSE_SPLIT = false`,
   both ATK and DEF collapse to overall effective OVR.
   **Version 8** moves the neutral goalkeeper of `GK_delta` from 76 to 82 (`GK_BASELINE`
   in `sim_cave.py`; four bytes of the code, nothing else). Model of the tables on the
   499 clubs of `ML saves/ML00000013 (before)`, matches inside each group, goals per
   match and clean sheets per team: first 20 clubs (goalkeepers 84 on average) 2.33 and
   32% with 76, 2.47 and 30% with 82; places 21-60 (80) 2.45 and 30%, then 2.60 and 27%;
   places 101-140 (75) 2.61 and 27%, then 2.80 and 24%; places 301-340 (69) 2.83 and
   24%, then 3.01 and 21%. With `GK_SCORE_MOD = false` every group gives about 2.56 and
   28%. So 82 suits the best clubs and adds goals below them; the clean-sheet boost
   (from 82) is as it was.
3. **Skip Match substitutions, GK protection & smart CPU subs (`fcn_03707e71`):**
   - `SKIP_SUBS` (`0x03708230`): removes the hardcoded `sub = 11` overwrite when `SCOPE`
     includes Skip Match so simulated Skip Match fixtures behave like AI-vs-AI simulations.
   - `GK_PROTECT` (`0x0370818d`, version 6): replaces `xor edi, edi` (`31 ff` -> `90 90`)
     so slot `0` (starting GK) is never randomly selected as `sub1` for an outfielder.
   - `SMART_SUBS` (`0x037080d9`, version 6): replaces pure `rand(100)` bench sort keys
     with `player_eff_ovr(pos=13) + rand(4)` (clamped `<= 255`), so descending sort
     (`fcn_03705ef2`) brings on stronger, in-form, fresh substitutes first (respecting
     `SCOPE`).
4. **Dynamic player ratings (`0x03708cc4`):** computes end-of-match ratings from team
   result (`W/D/L`), goal difference, clean sheet bonus, goals (`RATING_GOAL`), assists
   (`RATING_ASSIST`), and disciplinary card penalties (`CARDS` adjustment), replacing
   vanilla's flat base ratings.
5. **Attribute-weighted goal scorers & assists (`0x037085b5` + `0x03706ef6`, enhanced in version 7):**
   - `sim_vec_hook` (`0x0370875c` inside `fcn_037085b5`): replaces vanilla's raw
     Finishing-only scorer stat (`-10` CB / `-5` FB) with `(2*Finishing + 2*Attacking Prowess + Header + 2) / 5`
     plus a 13-position modifier (`SCORER_POS_ADJ`), and adds a 13-position assist
     modifier (`ASSIST_POS_ADJ`) onto `Low Pass + Lofted Pass`, plus `2 * (cond_ovr - fatigue_pen)`
     when `CONDITION_STRENGTH = true` (clamped to `[1, 255]`, `GK = 0`).
   - `scorer_hook` (`0x03706ef6`): distributes goals across all 10 outfield
     players using exponential weights (`SCORER_SHARPNESS`, zero for GKs) and assigns
     assists across the remaining outfielders (`UNASSISTED_PCT`, `ASSIST_SHARPNESS`).
   - **Version 8** spreads the goals: position table `(0, -22, -24, -24, -18, -4, 6, 6,
     8, 10, 10, 12, 12)` (GK, CB, LB, RB, DMF, CMF, LMF, RMF, AMF, LWF, RWF, SS, CF;
     wingers were raised from `8` to `10` and CF lowered from `14` to `12` after the
     suggestion audit, so elite wingers sit nearer the CFs in the scoring charts),
     `SCORER_SHARPNESS = 0.05`, and the weight table is read with `gap >> 2` for goals
     too (version 7: `gap >> 1`, so every gap above 46 counted alike and no table could
     keep defenders low without a steep curve). Measured on the best eleven of the 499
     clubs of `ML saves/ML00000013 (before)`:

     | | version 7 | version 8 | after the audit |
     |---|---|---|---|
     | goals by CF | 50% | 32% | 30% |
     | SS, wingers, AMF | 37% | 41% | 44% |
     | CMF, DMF | 7% | 14% | 14% |
     | defenders | 6% | 12% | 12% |
     | best scorer's share of his club's goals: median / 90th / most | 47 / 66 / 88% | 30 / 38 / 57% | 28 / 35 / 55% |
     | Haaland / Kane / Mbappé | 83 / 68 / 40% | 48 / 37 / 25% | 45 / 34 / 22% |

     (The "~26% CF" that the settings comment of version 7 gave was not what real
     squads produced.) Assists are unchanged.
6. **Extra Time & Penalty Shootouts (`0x037062ca`, `0x037063bb`):** adds strength-scaled
   Extra Time goal chances (`ET_GOAL_SCALE`) and replaces vanilla's broken
   100%-home-win Penalty Shootout table with a symmetric OVR-weighted shootout
   (`PK_HOME_BIAS`, `PK_OVR_WEIGHT`).
7. **Disciplinary cards (`0x03708f45`):** awards position-weighted yellow and red cards
   (`CARDS`, `YELLOW_AVG`, `RED_PCT`) and feeds competition suspension tracking.
8. **Starting XI lineup, Attack/Defense split & condition/fatigue team strength (`LINEUP_STRENGTH`, `CONDITION_STRENGTH`, `ATTACK_DEFENSE_SPLIT`):**
   intercepts team strength lookups inside `outcome`, `score`, `et`, and `pk` (`CAVE_ET`
   `eff_strength`), looks up the team's active tactics (`fcn_03117d98` + `fcn_03822a29`)
   when `LINEUP_STRENGTH = true`, validates non-sentinel distinct indices in
   `tactics_rec + 0x248[0..10]` (falling back to the squad top-11 loop when invalid),
   evaluates each starter's positional OVR (`tactics_rec + 0x68[0..10]`, defaulting
   `> 12` or `slot > 0 and pos == 0` to `13`), replaces injured/suspended starters
   (`fcn_0385b771`) with the best eligible non-starters from the bench (a natural GK
   only ever fills a missing slot while the XI has no keeper, mirroring the game's
   own sub picker `fcn_03706d2e`, which never fields a GK in an outfield slot), and (when
   `CONDITION_STRENGTH = true`) adjusts each player's OVR via `player_eff_ovr` by
   condition arrow (`CONDITION_OVR = { -3, -1, 0, 1, 3 }`) and pre-match fatigue
   below `FATIGUE_THRESHOLD` (`72`, up to `FATIGUE_PENALTY = 5`). In version 7,
   `eff_strength` also accumulates positional Attack (`pos >= 6` weight 2, `CMF/unknown`
   weight 1) and outfield Defense (`pos 1..4` weight 2, `CMF/unknown` weight 1, excluding GK)
   averages plus starting `GK_eff` (using `GK_CONDITION_OVR`), returning `eax = overall_ovr` and
   `edx = (gk_eff << 16) | (def_ovr << 8) | atk_ovr` (other callers discard `edx`).
9. **Stamina-scaled fatigue (`STAMINA_FATIGUE`, `AI_FATIGUE`, version 5):** hooks
   `fcn_038556f1` (`0x038557dc` & `0x038557d6`) so simulated AI teams also accumulate
   match fatigue when `AI_FATIGUE = true`, scales drain by player stamina around 75
   (`STAMINA_WEIGHT`), keeps vanilla's `0.9x` GK factor, and adds `+30` minutes when
   a simulated fixture went to Extra Time (without double-counting played 120-minute
   fixtures).
10. **Simulated match injuries (`INJURY_PCT`, `INJURY_DAYS`, version 5):** extends
    `CARDS_HOOK` so each simulated match rolls `INJURY_PCT` (`3%` default) per team
    (when more than 7 outfield-capable healthy players are available), picks a random
    healthy outfield player weighted by low injury resistance and low post-match
    fitness, and sets injury duration in `[INJURY_DAYS[1], INJURY_DAYS[2]]` (`7..28`
    days default). Works even when `CARDS = false`.

### Settings & verification

All toggles and tuning parameters live at the top of `MLSimMatch.lua` and are validated
by `settings_fault()` before any byte is written. `python3 test_sim.py <PES2017.exe>`
runs 24 tests (all passing): generated block & Keystone byte-for-byte equivalence across
all 16 routines and 6 caves, 76 invalid-setting rejections, 9 partial-mode installs,
tamper detection across all 13 patch sites and 6 caves, real `PES2017.exe` execution for
all match-sim hooks (`ok 6`–`ok 19`, `ok 21`–`ok 23`), and coexistence with `MLMoney.lua`,
`MLTransfers.lua`, and `MLYear.lua` in any order (`ok 20`).

## Earlier safety fixes — 17 November 2026

- **`MLTeamSpirit.lua` v3:** uses Sider's already-decoded team numbers, reads the
  career day/year as u16 fields, ignores future results when calculating form, and
  bounds the final match/club/competition reads. Existing packed `RIVALS` settings
  still work; copy the labelled **`RIVALS id`**, not the Sider team number, from the log.
- **`MLGrowth.lua` v8:** the AI season is a table-driven factor model (archetype x
  form x role x ceiling) solved by `growth_twin.py`, and the season walk moved out of
  `.link` to the `.trace` page behind the day step, so no gap is shared with another
  module. The assembly, preassembled bytes and embedded Lua block are synchronized.
- **`MLSimMatch.lua` v9:** neither checks nor writes the 84-byte gap reserved for
  Growth's curve. The matching SimMatch/Growth files now work in either load order.
  With an older SimMatch v8, SimMatch must still load first. Upgrade both files.
- **Failed writes:** Money, Transfers, Year, SimMatch, Growth and Spirit now attempt
  to restore all patches already attempted if a write fails its read-back check.
  Failed restoration is reported. This is not exception-safe transaction support:
  Sider 3.6.0's Lua sandbox provides no `pcall`, so a host memory-API error can still
  stop init before rollback. Fully exit PES on any write/init failure; do not save.
- **Transfers setup:** the checked default is numeric `wealth = 150` for Galactico.
  A log saying that persona's wealth is invalid means the installed file differs.
  Back it up and replace it with this copy, or keep your custom value numeric and
  within **10–250**. The validator remains enabled; unsafe settings are not clamped
  or accepted silently.
  Transfers also verifies Money's actual installed fee hook, not just its marker and
  cave contents, so it cannot activate after Money has rolled back a failed install.

### Tools not covered by the module index

- `growth_cave.py calibrate <exe> <save>` projects annual AI-player changes (it needs a save `window_report.py` can unpack; `growth_twin.py <exe> <edit> 20` is the fuller check and is the spec of the tables). Growth v8 gives every AI player a hash-driven season on the attributes his position is rated by, and one decline point a season from each of five families (pace 27, stamina 29, strength 32, technique 33, cognitive 34, shifted by position, down to 45).
- `club_ids.tsv` maps 499 ranked clubs to packed IDs, places, personas and eleven strength. Sporting projects select up to five eligible AI clubs from the top 15 in the top five leagues: no user club, no backfilling, no match RNG. The need-position ceiling boost is at most 20%; it does not change personas.
- `window_report.py <exe> <before> <after>` compares a window by club, level and persona. `window_transfers.py` instead exports one save’s signings. `test_transfers.py` checks against the four repository saves.
- `simdate_calendar.py`, `sim_cave.py` and `money_cave.py` generate native hook code. Use the [module/test index](#find-the-implementation-and-the-test) for the corresponding emulator tests; the [reservation map](#notes-for-the-next-module) documents shared-memory boundaries.

## What was looked at in `sider.dll`

Read from the DLL's code and strings, not run:

- A module must return a table with an `init(ctx)` function. It gets these names:
  `log`, `memory` (`read`, `write`, `search`, `pack`, `unpack`), `string`, `table`,
  `math`, `pairs`, `ipairs`, `tostring`, `tonumber`, `type`, `unpack`, `assert`,
  `error`, `os` (`time`, `clock`, `date`), `audio`; with `luajit.ext.enabled` also
  `ffi`, `bit`, `require`. There is **no `pcall`**: an error in `init` makes Sider skip
  the module and log the error.
- **`io` is among them** (`0x10003610`: thirteen names are copied from Lua's own globals
  into what a module sees, `io` is the last; `os` is a new table with three functions).
  So a module can read and write files. `ctx.sider_dir` (the folder of `sider.exe`, made
  from a wide string into UTF-8) and `ctx.register(event, function)` are put into `ctx`
  at `0x10003590`.
- `ctx.register` (`0x10002c70`) knows 21 events, all about files, a match, the edit mode
  or the replay gallery. **None for a key, the pad or a menu.**
- `livecpk_make_key` (used by `MLSimToDate.lua` 2 as a clock tick): the three places
  where Sider is called when the game looks for a file (`0x10007f20`, `0x10008130`,
  `0x100082c0`; installed only with `livecpk.enabled = 1` and when Sider finds the
  game's code for it) first ask a list of earlier lookups, by the address and the name
  of the file (`0x10010cb0`; only with `address-cache.enabled = 1`). A lookup that is in
  the list does not reach Lua. Any other, with `lua.enabled = 1`, goes through every
  module that registered `livecpk_make_key` or `livecpk_get_filepath` (`0x10007ca0`) and
  calls its `livecpk_make_key` function with `ctx` and the file name (`0x100078c0`), in a
  protected call: an error there is logged (`lua ERROR`) and does not stop the game. A
  function that returns nothing gives an empty key; with no `livecpk_get_filepath`
  function the module then names no file and Sider goes on to the next module.
- `memory.read(address, count)` makes the pages readable and writable
  (`VirtualProtect`), copies the bytes, and asks for the old protection back with a
  call that Windows refuses (no place for the old value is passed). So **a read leaves
  the touched pages marked writable**. No byte changes. Every Sider module that reads
  memory does the same.
- `memory.write(address, bytes)` does the same and copies the other way, so it can
  change code. That is the route for the tuning modules. It gives the pages the
  protection "read, write, execute" (`0x40`) before the copy; if Windows refuses that,
  the module stops with an error and Sider skips it.

## Notes for the next module

- The exe has a fixed load address (no relocation table, no dynamic base), so the
  addresses of `MASTER_LEAGUE.md` are valid in the running game. `MLCheck.lua` tests
  exactly this.
- The level values are single bytes inside `mov eax, value` instructions; 68 and 9,000
  of the fee formula are numbers inside two instructions; 0.00027 is a constant with
  one user. All four can be changed in place.
- **The 2.2 of the fee formula is a shared constant** (`0x01f0f2b8`, 16 references in
  the exe). It must not be changed in place; the fee function has to be pointed to a
  constant of its own. (`MLMoney.lua` does not need it: its routine sets the factor of
  the salary part to 0 in the function's own stack frame.)
- Free memory for code and tables: `0x047b0200`-`0x047b0fff`, the end of `.trace`
  (3,584 bytes; `MLMoney.lua` uses the first 3,568), and below it `0x047b0060`-`0x047b01fd`
  (`MLSimMatch.lua` version 9 uses `0x047b0060`-`0x047b01f4`, 405 bytes, for cards + injury call;
  `0x047b0124`-`0x047b01fe` was used by version 5 of `MLMoney.lua` only). The end of `.xcode`,
  `0x047d3a43`-`0x047d3fff` (`MLSimMatch.lua` version 9 uses `0x047d3a50`-`0x047d3f06`,
  1,207 bytes, for code and `0x047d3fa0`-`0x047d3fff`, 96 bytes, for its v5–v7 config & positional/GK tables;
  previously used by version 6 of `MLMoney.lua` and version 1 of `MLTransfers.lua` at
  `0x047d3c40`-`0x047d3dbc`). The page of `.data1` behind its code,
  `0x047d4170`-`0x047d4fff`: `MLSimMatch.lua` version 9 uses `0x047d4170`-`0x047d41ff`
  (144 bytes) for v1–v3 config/tables; `MLTransfers.lua` versions 3 and 4 use all of
  `0x047d4200`-`0x047d4fff` (version 2: up to `0x047d4f5f`; one window was played with
  it and that part was left alone. The last 160 bytes are zero in the file and were not
  yet used in the game). The v5 config of `MLSimMatch.lua` was first put at
  `0x047d4f60`-`0x047d4f7f`, inside what `MLTransfers.lua` version 3 uses; the two could
  not be installed together, so it was moved to the end of the `.xcode` page (`0x047d3fa0`-`0x047d3fff`, 96 bytes for v7).
  `.reloc` and `.link` RX page tails hold `MLSimMatch.lua` version 9's
  `eff_strength` + `player_eff_ovr`/`gk_eff_ovr` + ET + outcome + score + `sim_vec`
  code reservation (`0x047d5040`-`0x047d5b8b`, 2,892 bytes) and separate 2D
  scoreline/draw CDF tables (`0x047d5be0`-`0x047d5ffd`, 1,054 bytes). It checks and
  writes these separately: **`0x047d5b8c`-`0x047d5bdf` belongs to Growth**, not the
  simulator. PK + `card_adj` + fatigue + injury use `0x047d6030`-`0x047d6376`
  (839 bytes). The generators enforce these bounds, including the adjacent Growth code.
  `MLTransfers.lua` uses `0x047d6400`-`0x047d654f` (336 bytes, position need),
  `0x047d6550`-`0x047d6d3f` (2,032 bytes, incoming offers), and
  `0x047d6d40`-`0x047d6e4f` (272 bytes, squad pressure).
  `MLSimToDate.lua` uses `0x047d6f60`-`0x047d6fec` (141 bytes) for its day-loop hook.
  With Growth below, the ranges still free after the transfer code are
  `0x047d6ec4`-`0x047d6efd` (58 bytes), `0x047d6f4c`-`0x047d6f5f` (20 bytes) and
  `0x047d6fed`-`0x047d6fff` (19 bytes).
  **`0x047d6d60`-`0x047d6e4f` is not free**; old allocation notes understated the
  current incoming/pressure sizes.
  `MLSimToDate.lua` version 3 had its calendar block (`0x900` bytes: the Schedule poll,
  the selection, the heading and their strings) at `0x047d6550`-`0x047d6e4f`, which is why
  the two modules could not be installed together; version 4 moved it to an unused run of
  8,196 zeros in `.trace`, `[0x03fc7d9c, 0x03fc9da0)` (exclusive end; the first four
  zeros finish a padding NOP, and the next function starts at `0x03fc9da0`), where it
  takes `0x03fc8000`-`0x03fc88ff`. `MLTransfers.lua` version 9 takes
  `0x03fc8900`-`0x03fc92ff` (0xa00 bytes: `MOOD_ON`, the window, the four styles and the
  routine of `DEAL_MOOD` at `0x03fc8910`). `MLMoney.lua` uses `0x03fc9300`–`0x03fc943f` for budget keys.
  `MLGrowth.lua` version 8 uses what is left of the `.link` gaps:
  `0x047d5b8c`-`0x047d5bde` (the age curve, 83 of the 84 bytes between
  `MLSimMatch.lua`'s hook code and its scoreline tables), `0x047d6377`-`0x047d63f6`
  (the exp award, 128 bytes, up to `MLTransfers.lua` version 6),
  `0x047d6e50`-`0x047d6ec3` (the award arithmetic, 116 of the 174 bytes; version 7's
  season walk was here), and `0x047d6efe`-`0x047d6f4b` (the training scale, 78 bytes,
  still 20 short of `MLSimToDate.lua`'s hook).  Its season walk and tables moved out of
  `.link` entirely: they sit in the `.trace` page behind the day step
  `0x02e8b198`-`0x02e8b9b8` (the hash chain, 0x600 bytes of code, then 0x200 bytes
  of tables), where no other module of the set lives.  The old `.xcode` gap
  `0x047d3f07`-`0x047d3f9c` (the version-3 season award) is free again.
  `MLSimToDate.lua` also
  checks and uses `0x0298c0e0`-`0x0298c1ff` in the writable, zero-filled `.text` stub
  for its state, and `MLGrowth.lua` checks and uses the page tail behind it,
  `0x0298c200`-`0x0298c2eb` (236 bytes of tables; `.text` holds `0x200` bytes at
  `0x0298c000`, the rest of its last page is zero-filled by the loader). A module must
  see zeros in its ranges before it writes.
- A plan record (`MASTER_LEAGUE.md` 9.1) has spare bytes at `+0x109`-`+0x10b`; `MLTransfers.lua`
  version 6 uses the first two. Do not store anything in the low 7 bits of a slot word: the
  game uses them.
- A routine that is called from inside a game function can read the arguments of that
  function's caller through the saved `ebp`, if it first checks the return address.
  The routine of `MLTransfers.lua` does this to get the club level without changing a
  call, and reads the locals of the function it is called from (date, pool, player) the
  same way.
