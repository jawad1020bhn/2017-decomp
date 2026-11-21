# Day processing, calendar and fixtures

[Master League guide](../MASTER_LEAGUE.md) · Section numbers are the original research citations. Paths in the notes are relative to `pes database/exe` unless a command changes directory.

## 3 How a day is processed

Level: **read** for the frame; the steps themselves are **located** or **inferred**.

Four task classes (names from the exe's own type records) drive the career day:

| class | worker | body |
|---|---|---|
| `process::CmnUpdateDayBegin` | `process::UpdateDayBeginThread` | `day_begin` `fcn_0360a350` (531 lines) |
| `process::CmnUpdateDayEnd` | `process::UpdateDayEndThread` | `day_loop` `fcn_0360dbf0` → `day_end` `fcn_0360bf0c` (1,032 lines) |
| `process::CmnUpdatePreMatch` | | `fcn_03611910` → `fcn_03611277` (the matches of the day), then "skip" or "proceed" |
| `process::CmnUpdatePostMatch` | `process::UpdatePostMatchThread` | `fcn_03611162` → `fcn_036101d9` |
| `process::CmnUpdateSeasonEnd` | | `fcn_035feb08` (not read) |

The day-end worker also advances the days on which the user has nothing to do:

```
day_end()
while not day_loop_stop():        # fcn_0360b713: stops when day_state() == 2
    day_begin()                   # the next day
    after_matches_1()             # fcn_03611277
    after_matches_2()             # fcn_036101d9
    day_end()
```

`day_state` (`fcn_03877938`, 525 lines, 17 callers) is asked by almost every step. The
value 2 stops the loop, so it means "the user has to act today"; 0 and 1 are in
section 3.1. What makes a day a 2 is read in part only (a switch over 49 kinds of entry
of the day; in Master League also the state of the 70 squad players and four kinds of
news).

Each step is an object that is created, run once and freed. The steps that run only in
Master League (kind 12), in the order of the code:

**Day begin** (`fcn_0360a350`):

1. Each of the 70 deal records whose state is not 3 or 4 gets a new number from 1
   to 100 (`+0x1d4`); taken to be the record's chance number for the day.
2. On event 48 a byte (`+0xddce81`) is cleared. On event 1 (first day of the
   season): the year plan is written (`fcn_035d8b2e`, section 4) and `fcn_036336b0`
   runs.
3. `fcn_03640d19` (1,280 lines): the money step. It asks for events 3, 23, 25 and 49
   and uses the wage bill and team strength (not read). Then, for all modes,
   `fcn_0387585e(1)` when the test at `0x03671c55` says so (section 5).
4. On events 3 and 6 (a window opens): `fcn_0382e072`.
5. `fcn_03664a3d`; `negotiation_day_begin` (`fcn_0365c89a`) which on events 3 and 6
   runs the negotiation step once for all records; `fcn_03661f6b`; `fcn_036e20d2`;
   `fcn_036dfd10`; `fcn_03656fa5` (449 lines, uses random numbers, rating, salary,
   team strength); `fcn_0364b81c` (event 11).
6. On events 31 and 45: `fcn_03676016`.
7. `mode data + 0xddf74c` is set from `fcn_03878855`; `fcn_0362579a`; `fcn_036523fb`.

**Day end** (`fcn_0360bf0c`):

1. On events 5 and 8 (a window closes) a mark is set for the screens.
2. `fcn_036696e1` and `fcn_0362eb70` (events 41 to 44; they belong to the
   `process::SpecialTitle…` classes). Not read.
3. `fcn_03664d29` (event 9) → `fcn_0366365b` (769 lines; section 9.8).
4. `fcn_0365692c`, only when `day_state` is 2: for each deal record with state 2, 3
   or 12 that is not of kind `0x20`, thirteen numbers (26 to 38) are tried. Each has
   a chance in thousandths from `fcn_0365293e`, lowered by 150 (by 300 in April and
   October, by 1,000 in March and September); it passes if `rand(1000)` is not above
   the rest. What passes is collected and handed on (`fcn_03655628`, 203 lines, uses
   random numbers). What the 13 numbers stand for: not read.
5. `negotiation_day_end` (`fcn_0365cbbc`): on event 9 (a window day) the negotiation
   step runs (section 7). Then `fcn_036e2d84` (event 9) → `fcn_036e2557`.
6. `fcn_0365df66`, `fcn_036e1568`, `fcn_036e067a`, `fcn_0364c065`, `fcn_0366f4bb`.
7. `fcn_0366d620`, `fcn_03640686`, `scout_step` (`fcn_03652198`, section 8).
8. On event 8 (second window closes): `fcn_0385e248` builds a list for team **4971**
   and `move_players` (`fcn_0389734b`) runs on it. Team 4971 is the empty slot
   "The Old Boys" of the edit file. What is moved is not read.
9. `fcn_0363beba` (event 48, report), `fcn_03634561`.
10. On event 23 (last day of the season): the byte `+0xdd064d` is set and the
    season-end block follows (about 400 lines of the same function, not read; near
    its end the year plan is written again and `fcn_0387585e(1)` is called).

Appendix A lists every step with its size, the events it asks for and what it uses.

### 3.1 The two switches: "keep advancing" and "Skip Match"

Level: **read**. Nothing of this was seen in the game. `sider/MLSimToDate.lua` is built on it.

**The day end moves more than one day.** `day_end` asks `fcn_03879434` how many days to
go on: it walks the coming days and stops at the first whose `day_state` is not 0. So
0 = "nothing on this day" (the day is jumped over), 1 = "something to work off, no stop",
2 = "the user has to act". Then it sets the date (day number at `+0xc2cbb0`, 0 = 1 January;
the year at `+0xc2cbb2` goes up after day 364), and `fcn_038d5920` writes the user's match
of the new day into the match object (`[0x026503e0] + 0x34`, then `+0x537b8`: match id,
`0xffff` = none; competition at `+2`).

**The byte at mode data `+0xdcb6a0`: keep advancing.** Set to 1 in the main menu of
Master League (`fcn_031a502c`) and of Become a Legend (`fcn_03137118`) for menu item
`0xd`, which neither menu builder creates: the game's own way in is not there. 28
functions read it. While it is set:

- `day_loop_stop` (`fcn_0360b713`) answers with `fcn_0387a831` instead of `day_state`;
- `day_end` calls `fcn_0387a831` itself at its end, so the byte is normally 0 again
  before `day_loop_stop` asks, and that day goes the normal way;
- `fcn_0387a831` clears the byte and answers 1: on a day without a match of the user
  (or one of competition `0x38`) if event 23, 6, 3, 5 or 8 is on the day (last day of the
  season, a transfer window opens or closes); on a match day for certain kinds of
  competition (`fcn_0345e2ea` gives 0, 6, `0x1d`, `0x22`, `0x35`; a list at `0x0216adf8`
  and ids 7 and 14), for one of the three rival clubs (`fcn_03857dfb`), in some
  competitions if the user's team strength is not more than 5 above the opponent's
  (`fcn_03865b0a`), and by a table of club pairs (`fcn_0381e9c2`). Taken to be "an
  important match"; not worked out further;
- the pre-match step (`fcn_03611910`) and `CmnMatchInit` (`fcn_035fe39e`) answer "skip",
  the day-begin task opens a loading screen (`fcn_033f027e`) and about 19 report checks
  leave out their screen.

**The byte at `+0xdcb61c`: Skip Match.** `CmnUpdateSkipMatch` (`fcn_035fe56d`) sets it
to 1; the step before the main menu (`fcn_03612ef7`) clears it when it answers
"mainmenu" (it answers "userskip", the next day without the menu, when `day_state` is
not 2). `fcn_03611277` first calls `fcn_03708fd5`, which simulates every match of the
day that is not played, **except a match of the user while this byte is 0**. A match
goes through `fcn_03708de9`, or through `fcn_037064f5` when `fcn_0385cd11` says that a
side cannot field seven players. So the first switch alone would pass a match of the
user unplayed; with both set the match goes the Skip Match way. Nine functions read the
byte and all but one only ask whether it is 0 (`fcn_03623a38` asks for 1, and only while
the first switch is off).

A day of the task chain and a day inside the loop of the day-end worker call the same
four functions in the same order: `day_begin`, `fcn_03611277`, `fcn_036101d9`, `day_end`.
The tasks add screens and, after a played match, `fcn_0360fcbc` (two bytes at
`+0xe4c1da`).

`after_matches_2` (`fcn_036101d9`) leaves out the bookkeeping of a played match when
either switch is set and, in Master League with a match of the user, raises event `0x10`
(Skip Match set), `0xf` and `0xe` (`fcn_038551f2`).

## 4 The year plan (calendar)

Level: **proven** for the dates; the meaning of each event is **read** or **inferred**
as marked.

### 4.1 The calendar record

`mode data + 0xbfd52c` holds 365 records of `0x214` bytes, one per day:

| offset | what |
|---|---|
| `+0x000` | up to 200 match numbers (i16) played that day; `-1` = empty |
| `+0x190` | number of matches (u16) |
| `+0x194` | 16 event slots of 8 bytes: event number (u16), a mark (i16), a date; at most 9 are written per day |

`event_on_date` (`fcn_038ae7ca(&event, &date)`, 66 callers) and `event_on_day`
(`fcn_038558cc(&event, &day number)`, 31 callers) answer "is this event on that day".
All timed rules of the mode hang on these two questions.

### 4.2 Where the events come from

One table in the exe, `0x0216bc20`, 169 rows of `0x14` bytes:

| offset | what |
|---|---|
| `+0x00` | month (u8) |
| `+0x02` | day (u16) |
| `+0x04` | event number |
| `+0x08` | 1 = only in the career modes (Master League, Become a Legend) |
| `+0x09` | 1 = not in Become a Legend |
| `+0x0c` | a number written with the event (meaning ?) |
| `+0x10` | kind of season: 0 = season from 1 July, 1 = season from 1 January, 3 = both |

On the first day of a season (event 1) `year_plan_write` (`fcn_035d8b2e`) walks from
today to day 364 and on from day 0, and for each day calls
`year_plan_day` (`fcn_038b0b21`), which picks the rows of that date:

- the row's season kind is 3 or equals the season kind of the user's league;
- Master League takes every row; Become a Legend takes rows with `+0x09` = 0; all
  other modes take rows with `+0x08` = 0;
- event 29 only if the byte at mode data `+0xdcb686` is set;
- events 32 to 39 (draws) not if mode data `+0xdc9d78` is `0x56` (and, outside the career
  modes, not if the byte at `+0xdc9cbc` is 2 or more);
- events 19 and 20 not in May and June of a year with `year mod 4 = 1`;
- event 48 not in February and September if the byte at `+0xddce71` is set.

The season kind comes from `season_kind` (`fcn_0385adf6`): a table of 92 league ids at
`0x021687d0` (appendix D). Kind 0 = the season runs from 1 July to 30 June; any other
kind = from 1 January to 31 December. Outside the three career modes the January
season is always used.

`python3 yearplan.py <exe> july` (or `january`) prints the year.

### 4.3 The Master League year, season from 1 July

Event 9 is on every day of July, August and January.

| date | event | what |
|---|---|---|
| 1.7. | 1 | first day of the season: the year plan is written |
| 1.7. | 3 | first transfer window opens |
| 26.7. | 45 | asked by fcn_03676016 (not read) |
| 4.8. | 10 | asked by fcn_0364c065 and the staff report (not read) |
| 20.8. | 19 | taken to be a national team day (six a year) |
| 21.8. | 20 | the day after event 19 |
| 26.8. | 42 | title step of fcn_0362eb70 (process::SpecialTitleSetUEFA, not read) |
| 27.8. | 32 | draw day (process::ProcessCmnLotCheck) |
| 27.8. | 27 | asked by fcn_0366f4bb and news functions (not read) |
| 30.8. | 4 | day before the first window closes (the daily scout step is left out) |
| 31.8. | 5 | first transfer window closes |
| 1.9. | 30 | day after a window closes: computer clubs plan their squads (fcn_036602e5) |
| 21.9. | 19 | taken to be a national team day (six a year) |
| 22.9. | 20 | the day after event 19 |
| 25.9. | 48 | report step fcn_0363beba (writes a staff report; not read) |
| 26.10. | 19 | taken to be a national team day (six a year) |
| 27.10. | 20 | the day after event 19 |
| 7.11. | 11 | asked by fcn_0364b81c (not read) |
| 10.12. | 33 | draw day (process::ProcessCmnLotCheck) |
| 10.12. | 34 | draw day (process::ProcessCmnLotCheck) |
| 12.12. | 11 | asked by fcn_0364b81c (not read) |
| 28.12. | 44 | title step of fcn_0362eb70, fcn_036696e1 (not read) |
| 29.12. | 43 | title step of fcn_0362eb70, fcn_036696e1 (not read) |
| 29.12. | 31 | asked by fcn_03676016 (not read) |
| 29.12. | 11 | asked by fcn_0364b81c (not read) |
| 30.12. | 28 | asked by fcn_0366f4bb and news functions (not read) |
| 31.12. | 12 | half-year step of fcn_036e1665 (not read) |
| 31.12. | 24 | asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts) |
| 31.12. | 15 | half-year step of fcn_036e067a, fcn_036e1568 (not read) |
| 31.12. | 22 | asked by fcn_0314910f only (not read) |
| 1.1. | 25 | money step fcn_03640d19; asked by process::ProcessCmnFinanceReportCheck |
| 1.1. | 6 | second transfer window opens |
| 8.1. | 41 | title step of fcn_0362eb70, fcn_036696e1 (process::SpecialTitle, not read) |
| 11.1. | 26 | asked by fcn_0366f4bb and news functions (not read) |
| 30.1. | 7 | day before the second window closes (the daily scout step is left out) |
| 31.1. | 8 | second transfer window closes |
| 1.2. | 30 | day after a window closes: computer clubs plan their squads (fcn_036602e5) |
| 6.3. | 17 | asked by fcn_036f5728 (not read) |
| 7.3. | 16 | asked by the staff report and a transfer news function (not read) |
| 15.3. | 19 | taken to be a national team day (six a year) |
| 16.3. | 20 | the day after event 19 |
| 19.3. | 35 | draw day (process::ProcessCmnLotCheck) |
| 19.3. | 36 | draw day (process::ProcessCmnLotCheck) |
| 16.4. | 37 | draw day (process::ProcessCmnLotCheck) |
| 16.4. | 38 | draw day (process::ProcessCmnLotCheck) |
| 9.5. | 11 | asked by fcn_0364b81c (not read) |
| 25.5. | 19 | taken to be a national team day (six a year) |
| 26.5. | 20 | the day after event 19 |
| 28.5. | 39 | draw day (process::ProcessCmnLotCheck) |
| 13.6. | 11 | asked by fcn_0364b81c (not read) |
| 22.6. | 19 | taken to be a national team day (six a year) |
| 23.6. | 20 | the day after event 19 |
| 25.6. | 48 | report step fcn_0363beba (writes a staff report; not read) |
| 28.6. | 11 | asked by fcn_0364b81c (not read) |
| 28.6. | 31 | asked by fcn_03676016 (not read) |
| 28.6. | 49 | money step fcn_03640d19 |
| 30.6. | 14 | half-year step of fcn_036e1665 (not read) |
| 30.6. | 24 | asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts) |
| 30.6. | 13 | half-year step of fcn_036e067a, fcn_036e1568 (not read) |
| 30.6. | 23 | last day of the season: season-end processing |

For a league with a January season the two halves change places: the first window is
1 to 31 January, the second 1 July to 31 August, the season ends on 31 December
(`yearplan.py <exe> january`).

### 4.4 What the dates say

- **Two transfer windows**: 1 July to 31 August and 1 to 31 January (events 3-5 and
  6-8), with the daily step (event 9) on every day inside them.
- **1 September and 1 February** (event 30), and the first day of the season
  (event 1): the computer clubs plan their squads and choose players (section 9.2).
  The deals close on window days.
- **30 June and 31 December** (events 12 to 15, 24): half-year steps. Contract ends,
  loan returns and the closing of the accounts are expected here; the functions are
  located, not read.
- **Six dates with a day after** (events 19, 20), dropped in May and June every
  fourth year: taken to be the national team days.
- **Eight draw days** (events 32 to 39, asked by `process::ProcessCmnLotCheck`) and
  four title days (41 to 44).
- **25 June and 25 September** (event 48): a report step.

Appendix F lists, for each event, the functions that ask for it. That table is the
map from a date to the code that acts on it.

## 5 Fixtures and match days

Level: the pairing table of a league is **proven** (check 10); the rest is **read**
or **located** as marked. `tools/fixtures.py` holds the rule.

### 5.1 The records

| record | where (mode data) | size, count | fields seen |
|---|---|---|---|
| competition | `+0x552e80`, count at `+0x5fece8` | `0x224` bytes, up to 300 | `+0x00` id; `+0x5c` kind (1 league, 3 and 4 other creators, 2 and 5 nothing to create); `+0x60` list of its match days (up to 58 numbers); `+0x148` team list, 4 bytes per team; `+0x214` bits 19-24 number of match days; `+0x218` bit 8 "fixtures are to be made"; `+0x21c` bits 16-22 number of teams, bits 30-31 number of legs |
| match day | `+0x632e6c` | `0x208` bytes, up to 1,500 | `+0x204` bits 26-31: number of the round inside its competition |
| match | `+0x6f154c` | `0x24c` bytes, up to 9,000 | `+0x00` own number (`0xffff` = free); `+0x04` competition id; `+0x06` bits 0-11 round, bit 13 set, **bit 14 "has been played"**; `+0x08` the date (a date, section 2.2); `+0x0c` first team; `+0x10` second team; **`+0x14` goals of the first team, `+0x17` goals of the second** (`+0x15`, `+0x16`, `+0x18`, `+0x19` are 0 but for a few matches: extra time or penalties ?) |

The four fields in bold were read from two saves of `ML saves/` (the same career before
and after 76 days of it): of the 1,931 records with bit 14 set every one has goals of 0
to 5 (1-0 404 times, 0-1 341, 0-0 251) and a goal or an event list after `+0x1c`, and of
the records without it not one has a goal. **Every round of a cup is in the records from
the day the cup is made**, both teams in it: in the earlier save a cup of 77 matches has
all six of its rounds (16, 32, 16, 8, 4 and 1 match) and none of them played.

#### A number is not a place

The number in `+0x00` of a match record is the one the game asks a record by
(`match_record`, `fcn_03822b3f(number)`, 183 callers): it goes to
`mode + 0x6f154c + number * 0x24c` and takes that record when the number in its own
`+0x00` is the one it was given, and only when it is not does it go looking in a second
table at `+0xbfd52c` (`fcn_038225a7`, the same function without the fall-back of
answering record 0). In the later of the two saves all 7,211 records that are in use hold
their own place in `+0x00`, so in a career the number of a record is its place.

A competition is answered the other way about: `fcn_03822ab9(id)` walks the competition
table and compares the id in `+0x00` of every record (and answers `+0x5fe840`, a dummy,
when it finds none), because **the place of a competition record is not its id**. The ids
are the numbers of the game's own list of competitions — 2, 3, 5, 8, 9, 11, 12, 15, 16,
23, 52, 59, 400 to 404, 600 to 607, 1000 to 1011, 1600 to 1605, 1800 to 1807, 3000 to
3007, 6800 to 6807, 7200 to 7207, 20000 to 20215 and so on — and a match record names the
competition it belongs to with one of those ids in `+0x04`, not with a place.

#### The match that is being played (mode data `+0x537b8`)

| field | what the game keeps there |
|---|---|
| `+0x00` word | the number of the match record (`match_record` is called with it) |
| `+0x02` word | the id of its competition (`fcn_03822ab9` is called with it) |
| `+0x04` byte | the leg less one (Sider's `ctx.match_leg` is this plus one) |
| `+0x08` byte | a match info; `0x37` for none (Sider's `ctx.match_info`) |

The getters and setters of `+0x00` and `+0x02` stand next to each other in the game
(`fcn_0382b2a8` and `fcn_0382b2b8`, `fcn_0382b2c8` and `fcn_0382b2d8`), and Sider reads
the same four fields for its `ctx`: `sider.dll` at `0x8770` takes the word at `+0x00` as
`ctx.match_id`, the byte at `+0x04` plus one as `ctx.match_leg` and the byte at `+0x08`
as `ctx.match_info` (**proven** for `match_id`: the same word the game gives to
`match_record`). What it names `ctx.tournament_id` is another number again: it is
`fcn_04062701(id of the competition)`, a function that holds a table of 282 competition
numbers and answers one number of its own for a whole group of them — 11 for 2 and for
400 to 404, 12 for 3 and for 600 to 607, 19 for 5 and for 1000 to 1011, 23 for 8 and for
1600 to 1605, 24 for 9 and for 1800 to 1807, 27 for 11 and for 2200 to 2215, 28 for 12
and for 2400 to 2415, 84 for 23, 77 for 52, 95 for 59, 122 for 7200 to 7207 — and 159
for a competition that is not in its table (run in the emulator). So `ctx.tournament_id`
is a number of its own, 11 to 159, and not one the match records carry.

### 5.2 Who makes the fixtures

`make_fixtures` (`fcn_0377111e(competition id)`) is reached from the day end
(`day_end` → `fcn_036f5728`, and `day_end` → `fcn_036f9395` → `fcn_036f928d`; both
go on to `fcn_036f5f90`) and from `fcn_03670351`. It does nothing unless bit 8 of `+0x218`
is set, then picks by the kind at `+0x5c`:

| kind | creator | level |
|---|---|---|
| 1 | `league_fixtures` (`fcn_03774725`, class `process::LeagueCreation`) | **proven** for two legs |
| 3 | `fcn_0377661c` (154 lines) | located; taken to be the knock-out rounds |
| 4 | `fcn_03775815` (101 lines) | located |
| 2, 5 | none | read |

For the competition ids 60, 61, 12600 and 12601, when the word at `+0xc2cbb2` is 0
(meaning ?), `fcn_03770d07` is tried first (not read). `fcn_036f5728` asks for event 17
(6 March in a July season) before it makes fixtures; why is not read.

### 5.3 The league table of rounds (proven)

`league_fixtures` builds one square table per pair of legs. Cell `[a][b]` holds the
round in which team `a` is the first team against team `b`; `a` and `b` are places
in the competition's team list (`+0x148`), so **the order of that list decides who
meets whom in which round**. The table is made in two steps:

1. **Circle method.** The teams stand in two rows: the first half of the list on
   top, the second half below. Each round pairs the teams standing above each
   other, top team first. Then every place but the first of the top row moves one
   step round the ring. With an odd number of teams the first place of the top row
   is empty and the team below it rests. The second half of the season repeats the
   first with the sides changed: round `r` comes back as round `r + R`, where `R`
   is the number of rounds of one half (`n − 1`, or `n` when `n` is odd).
2. **Change of sides** (`league_creation_pick`, `fcn_037741b4`, the class's second
   function, → `fcn_03774035`). After step 1 the team in the fixed place would be
   first team in every round of the first half. So **every third and every seventh
   round** (rounds 3, 6, 7, 9, 12, 14, 15, 18, 21, … counted from 1) changes place
   with its return match (`fcn_03773b11` swaps two round numbers in the whole
   table).

Exceptions:

- **Four teams**: step 2 is replaced by a fixed table (`fcn_03773791`). Rounds, with
  the teams numbered 1 to 4: 2-1 3-4, 1-3 4-2, 1-4 2-3, 4-1 3-2, 1-2 4-3, 3-1 2-4.
- Competition ids 600-607, 1000-1011 and 3000-3007 use that fixed table; ids
  1800-1807 and 15400-15407 use a second fixed table (`fcn_037738c1`); ids 6800-6807 use `fcn_037739f1` (one leg, three rounds) or
  the first table, by the number of legs. Which competitions carry these ids is not
  established (no competition table was read).
- **One leg, or three**: the last table is used for one half only and is balanced
  by another function (`fcn_03773cf6`). Read, not put into Python; the emulator
  gives the table (see below).
- If `fcn_038a7b83(competition)` says so (not read), the whole table is turned
  round: first and second team change in every match (`fcn_03773ec7`). Check 10
  covers this.

Then the matches are written: for each round, each cell with that round takes a free
match record and gets the competition id, the round, the first and the second team;
the match is hooked to the match day of the competition that carries the same round
number (`fcn_038e09f3`). That the first team is the home side is **inferred** (it is
stored first, and `fcn_03773ec7` exists to turn the sides); it was not seen in the
game.

```
python3 fixtures.py 20        # the 38 rounds of a league of 20 teams (appendix G)
```

What the proof covers: `check_findings.py` runs the game's `league_fixtures` on a
made-up competition of 2 to 24 teams with two legs and compares the whole table with
`fixtures.plan`, with and without the turn. It does not cover one and three legs,
the other creators, or the order of the team list.

### 5.4 Dates of the rounds

Level: **located**. The creator does not choose dates. A round is put on the match
day record that already carries its number, and the match day belongs to a day of
the calendar (section 4.1). Where the match days of a competition get their dates
was not found; no creator writes them, so they are taken to come with the
competition data when the career is created (`process::ModeDataCreationThread`).

### 5.5 Other things near the fixtures

- `process::CmnScheduleProcessCheck` (`fcn_03607db9`, `fcn_03607e8c`) and
  `process::CmnMonthlyScheduleCheck` belong to the schedule screens (not read).
- `fcn_0387585e` (1,085 lines, 9 callers, uses random numbers and `move_players`,
  called from the day begin, from the season end and from the creation of the
  career data) is not read. What it does is open.
- `fcn_038a7cf9(competition)` (37 callers) is asked before most competition steps;
  it walks the parent competitions (meaning ?).
