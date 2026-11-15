# Sider Lua modules for Master League

Modules for the Sider that ships in `pes.7z` (`sider.dll` of 20 February 2022, Lua
enabled in `sider.ini`). They work on the running game; `PES2017.exe` is not edited.

| file | what it does |
|---|---|
| `MLCheck.lua` | **read-only test.** Reads the overall window of computer clubs by level (section 9.4 of `../MASTER_LEAGUE.md`) and four numbers of the transfer fee formula (section 6.2) from the running game and writes them to `sider.log`. It writes nothing to the game |
| `test_module.py <PES2017.exe>` | runs `MLCheck.lua` outside the game against the bytes of the exe file (needs `pip install lupa`) |
| `MLMoney.lua` | **changes the game.** Player values by rating, age, talent, position and popularity, salaries, the transfer budget of a new career, the yearly income of the club, cup and league prizes, from tables at the top of the file. Checks the game's code first and writes nothing if it differs. Version 2 ran in the game and version 5 was played by hand (no log); versions 3, 4, 6 and 7 have run in the emulator only |
| `MLTransfers.lua` | **changes the game.** The transfers between computer clubs. Version 1 held the price ceiling, which was a part of `MLMoney.lua` up to its version 6; version 2 adds the selling side, club personas and scouting. Needs `MLMoney.lua` (version 7) in the line above its own in `sider.ini`. Has run in the emulator only |
| `MLYear.lua` | **changes the game.** The year in which a new career starts: 2026 (season 2026/27) instead of the 2024 of this exe. Needs no other module. Has run in the emulator only |
| `test_year.py <PES2017.exe>` | runs `MLYear.lua` on the exe in the emulator, then runs the eight changed instructions of the game (needs `pip install lupa unicorn`) |
| `MLSimMatch.lua` | **changes the game.** Simulated matches (Skip Match and AI-vs-AI): smooth Davidson win/draw/loss probabilities with home advantage, realistic Poisson-derived scorelines, and Skip Match CPU substitutions for the user's team. Needs no other module. Has run in the emulator only |
| `sim_cave.py` | the tables and four x86 routines `MLSimMatch.lua` writes to `.xcode` (`0x047d3a50..0x047d3de3`, 915 bytes) and their Python reference model |
| `test_sim.py <PES2017.exe>` | runs `MLSimMatch.lua` and `PES2017.exe`'s match-simulation machine code (`0x03707a1f`, `0x03705feb`, `0x03708de9`, `0x03708230`) in Unicorn and verifies coexistence with `MLMoney.lua`, `MLTransfers.lua`, and `MLYear.lua` |
| `club_ids.tsv` | the 499 clubs of the club ranking of the career `MLTransfers.lua` was set against: id (for `CLUBS`), place, persona, rating of the first eleven |
| `money_cave.py` | what the two modules write (13 small routines, with their source) and the same arithmetic as Python |
| `test_money.py <PES2017.exe>` | runs `MLMoney.lua` and then `MLTransfers.lua` on the exe in the emulator, then runs the game's salary, fee, budget, prize and income code with the changes in and compares it with `money_cave.py` (needs `pip install lupa unicorn`) |

## Install and run `MLCheck.lua`

1. Copy `MLCheck.lua` into the `modules` folder next to `sider.exe`.
2. Add this line to `sider.ini`, below the other `lua.module` lines:
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
  not need them.
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

## `MLTransfers.lua`, version 2: the selling side, club personas, scouting, rivals

Emulator only: this version has not run in the game yet. It needs `MLMoney.lua`
version 7 as before. The price ceiling of version 1 is still there and is described in
the next section; this section says what is new.

### Why

One transfer window of a career played with version 1 was read from two save files
(1 July and 15 September 2024, 498 computer clubs):

| | |
|---|---|
| signings by computer clubs | 511 |
| of them players without a contract | 506 |
| of them from another club | 5 |
| players on the lists of their clubs before / after | 816 / 1,547 |
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
| price ceiling | `CEILING` | as in version 1 (next section). `CEILING_FREE` is now 100: a player without a contract counts at his full value. With 50, a player worth twice a small club's ceiling was within its reach |
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
   from club, player and date, so it changes from window to window).
2. **Scouting.** The club knows `knows` percent of the players. Which ones is drawn
   from club and player and stays the same for the whole career. A listed player is
   known to every club.
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
   time.
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

**A club in need** is one that counts fewer than `SQUAD_NEED` (23) players. It always
buys, in winter too, at any age and below its usual level, and its ceiling counts
higher; it still looks in the places of its persona. A slot of a top club that asks for
a key player (the game does this for one slot of the first ten or twenty clubs on the
last day of a window) looks everywhere.

Every number of a persona is, for each club, up to `PERSONA_SPREAD` (20) percent lower
or higher, fixed by the club. No dice are thrown during play: every draw is worked out
from the ids of club and player, the position and the date, so the same club answers
the same way on the same day.

### The personas

`ARCHETYPES` in the file; at most 15, every number can be changed.

| persona | looks first: free / listed / clubs / does not buy | second search | winter | ages (strict) | knows | fog | wealth | premium | panic | fame | ambition | prestige | keeps |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Galactico | 20 / 5 / 75 / 0 | clubs, free | 30 | 24-30 (80) | 70 | 1 | 150 | 150 | 100 | 40 | 4 | 12 | 70 |
| State-backed | 20 / 15 / 65 / 0 | clubs, listed | 40 | 22-29 (80) | 75 | 2 | 200 | 200 | 150 | 25 | 4 | 10 | 70 |
| Moneyball | 15 / 25 / 60 / 0 | clubs, listed | 30 | 20-24 (85) | 90 | 0 | 90 | 40 | 50 | 0 | 8 | 6 | 30 |
| Elite trader | 15 / 20 / 55 / 10 | clubs, listed | 30 | 19-23 (85) | 85 | 1 | 100 | 60 | 60 | 0 | 9 | 6 | 15 |
| Academy purist | 10 / 10 / 30 / 50 | clubs, free | 15 | 18-23 (90) | 40 | 2 | 70 | 50 | 50 | 0 | 12 | 4 | 50 |
| Old-money | 30 / 20 / 50 / 0 | clubs, free | 40 | 25-30 (75) | 60 | 2 | 110 | 100 | 120 | 30 | 5 | 8 | 60 |
| Mid-table | 20 / 25 / 45 / 10 | listed, clubs | 40 | 24-28 (50) | 50 | 2 | 100 | 100 | 100 | 5 | 8 | 4 | 40 |
| Survival churner | 40 / 35 / 25 / 0 | free, listed | 80 | 28-34 (70) | 40 | 3 | 90 | 120 | 200 | 5 | 9 | 4 | 30 |
| Crisis | 60 / 35 / 5 / 0 | free, listed | 70 | 17-36 (20) | 30 | 3 | 50 | 30 | 100 | 0 | 12 | 2 | 0 |
| New-money | 45 / 0 / 55 / 0 | clubs, free | 60 | 25-32 (60) | 50 | 3 | 180 | 200 | 150 | 30 | 5 | 3 | 60 |
| Selling farm | 20 / 20 / 30 / 30 | listed, free | 30 | 18-22 (85) | 60 | 2 | 60 | 40 | 50 | 0 | 12 | 4 | 0 |

"Does not buy" stands for a club that fills a place from its own academy: the module
cannot make a youth player, it can only keep the club from buying.

**Which club has which persona.** 180 clubs are named in `CLUBS` (the game's id of the
club and the name of a persona; at most 192). The choice is mine, from what the real
clubs are known for on the market; no source was looked up for it, and each line can be
changed. It is surest for the big clubs and gets weaker further down: for a small or
newly promoted club "Mid-table" or "Survival churner" is often all that can be said.
In brackets the place in the game's club ranking of the career above.

The 73 named first (the biggest clubs of the data):

- Galactico: Real Madrid (2), Arsenal (4), Manchester United (10)
- State-backed: Paris Saint-Germain (1), Manchester City (6)
- Old-money: Barcelona (3), Bayern (5), Atlético (8), Inter (9), Napoli (13), Juventus
  (15), Roma (16), Galatasaray (20), Fenerbahçe (22), Betis (25), Flamengo (37),
  Beşiktaş (55), River Plate (62), Boca Juniors (63), Marseille (72)
- Moneyball: Liverpool (7), Tottenham (12), Milan (17), Brighton (26), Bournemouth (30),
  Sunderland (33), Brentford (36), Stuttgart (48), Lens (58), Girona (99)
- Elite trader: Chelsea (11), Dortmund (14), Leverkusen (27), Atalanta (28), Porto (31),
  Benfica (32), RB Leipzig (35), Monaco (43), PSV (44), Rennes (57), Lille (66),
  Palmeiras (67), Eintracht Frankfurt (69), Celtic (91), Club Brugge (111)
- New-money: Aston Villa (18), Newcastle (21), Como (38), Al Hilal (41), Al Nassr (60),
  Inter Miami (104), Al Ahli (106), Al Ittihad (114)
- Academy purist: Athletic Club (19), Real Sociedad (39), Celta (51), Osasuna (53),
  Freiburg (70)
- Survival churner: Rayo Vallecano (49), Getafe (64)
- Crisis: Valencia (52), Lyon (54), Sevilla (76)
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
São Paulo (82), Corinthians (113), Independiente (163). New-money: Cruzeiro (84), Al
Sadd (90), Bahia (124), Los Angeles FC (152), Los Angeles Galaxy (179), Atlanta (240).

Every other club draws one of up to eight personas of its group in the club ranking
(`PERSONA_GROUPS`, the ten groups of `CEILING`); which one is fixed by the club's id.
Naming the 107 clubs changed the persona of 90 of them; 17 had drawn the same one.
With the file as it is, the 499 clubs of that career come out as: Survival churner 140,
Mid-table 90, Crisis 60, Academy purist 52, Selling farm 49, Elite trader 36, Old-money
24, Moneyball 24, New-money 19, Galactico 3, State-backed 2. `club_ids.tsv` lists
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

### Settings new in version 2

| setting | as shipped; meaning |
|---|---|
| `CEILING_FREE` | 100 (was 50) |
| `SELL_SIDE` | `true`; `false`: the game's order (list three, then ask the club) |
| `PERSONA` | `true`; `false`: all clubs alike, and the settings below are not used |
| `SCOUTING` | `true`; `false`: every club knows every player |
| `PERSONA_SPREAD` (0 to 50) | 20: each number of a persona up to 20 percent lower or higher from club to club |
| `STRENGTH` | `{ 0.0533, 9.45 }`: rating of the first eleven = 0.0533 x ranking points + 9.45, kept inside the club's rating range. Fits the mean of the best eleven of the 499 clubs of the career above (1,464 points: 87; 984 points: 62) |
| `WINTER_MONTH` (0 to 12) | 9: the clubs choose their winter signings on 1 September; 0: winter is like summer |
| `SQUAD_NEED` (0 to 32) | 23: with fewer players a club is in need |
| `ARCHETYPES` | the eleven personas above |
| `PERSONA_GROUPS` | ten lists of 1 to 8 persona names, best clubs first |
| `CLUBS` | the 180 named clubs (at most 192); `{ }` names none |
| `RIVALS` | the 61 pairs above (at most 64); `{ }`: no rivals |

A faulty setting is named in `sider.log` and nothing is written, as before.

### What the log says

```
MLTransfers 2: the transfers of the computer clubs from the settings in MLTransfers.lua
check: MLMoney.lua   at 047b065c  installed, version 7
check: value routine at 047b0c90  as expected
check: numbers       at 047b0654  as expected
check: choose        at 0365f5c2  as expected
check: pick          at 03660c52  as expected
check: range         at 0365d08d  as expected
check: range low     at 0365d12d  as expected
check: club          at 0382b087  as expected
check: band          at 0385400e  as expected
check: club level    at 0365d775  as expected
check: ranking       at 031b1c34  as expected
check: rating        at 03853b42  as expected
check: take          at 041293c0  as expected
check: free memory   at 047d4200  empty
written: transfers at 0365fb0d  ok
```

then the ceilings, `selling side: ...`, `club personas: 11 personas, 180 clubs named,
...` with one line per persona, `rivals: 61 pairs of clubs do not buy each other's
players who have a contract`, and `RESULT: installed. Changed: price ceiling of the
computer clubs, selling side, club personas, scouting, rivals.`

**The line that matters most is `free memory at 047d4200`.** Version 2 needs 3,424
bytes and version 1's place (`0x047d3c40`, 384 bytes) is too small, so it uses another
piece of memory that has never been used in the running game: the rest of the page of
the small code section `.data1`. In the file that page holds 368 bytes of code and
zeros after them, and nothing in the file points behind the code. Whether the running
game leaves it alone can only be seen in the game. If the line says `NOT EMPTY`, the
module writes nothing; send the log.

### What to look at in the game

1. The log lines above.
2. Play to the end of the first transfer window and look at the transfer news, or send
   the save files of before and after as last time. The save of 1 July used last time
   can be played again: in it no club has chosen yet (all 7,968 slots of the 498 plan
   records are empty), so version 2 decides the whole window and the two results can be
   compared. What should differ from the 506 of
   511: moves between computer clubs, listed players who find a club, and no player of
   85 at a club of the lower half.
3. If the computer clubs sign almost nobody: set `SCOUTING = false` first, then
   `PERSONA = false`; each takes away one set of refusals. `SELL_SIDE = false` gives
   the game's order back.

### What is not known

- The module has never run in the game. In the emulator the game's own choosing code
  runs with it; the days of a season do not.
- How many signings the settings give was not worked out. The earlier analysis of the
  two saves was not repeated for version 2, so the mix per persona in the table is
  what the settings ask for, not what was seen.
- The number the game keeps per club and tests against 23 is taken to be the size of
  the squad without the players already promised away (read, not proven).
- `ambition` and `prestige` lean on the club ranking. If a club's points drift far over
  many seasons, its eleven is taken to be better or worse than it is.
- 1 September as the day of the winter signings is read from the game's calendar, not
  seen in play.

## `MLMoney.lua`, version 7, and the price ceiling of `MLTransfers.lua`: values, salaries, budgets, income, prize money, and what a computer club can afford

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
  rating range: it looks further down, not further up.

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
| `CEILING_FREE` (0 to 100) | 100 (version 1: 50): the same for a player without a contract |
| `SELL_SIDE`, `PERSONA`, `SCOUTING` and the persona settings | new in version 2: see the section on version 2 above |
| `CEILING_RATING` | `true`: in its second search a computer club takes nobody rated above the top of its own rating range; `false`: from 99 down, as in the game. Used only with `CEILING` |

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

### Install

1. Copy `MLMoney.lua` and `MLTransfers.lua` into the `modules` folder next to
   `sider.exe`. `MLMoney.lua` goes over the older version; an `MLMoney.lua` of version 5
   or 6 must not stay, because it holds a ceiling of its own.
2. `sider.ini` needs these two lines, once and in this order:

   ```
   lua.module = "MLMoney.lua"
   lua.module = "MLTransfers.lua"
   ```
3. Start the game. `sider.log` must show, from `MLMoney.lua`: "MLMoney 7: ...", twenty
   `check:` lines "as expected", the line "free memory ... empty", twenty-one
   `written:` lines "ok", the tables, and `RESULT: installed. Changed: values, salaries,
   transfer budget, cup prizes, league prizes, prizes into the transfer budget, pay gap,
   salary bonuses, contract years, yearly income, national cup prizes.`
4. Below it, from `MLTransfers.lua`: the lines shown in the section on version 2
   above, from `MLTransfers 2: ...` to `RESULT: installed. Changed: price ceiling of the
   computer clubs, selling side, club personas, scouting.` Among them the ceilings with
   the line "above the ceiling: the chance falls to none at 50 percent above it; a club
   in need counts its ceiling 30 percent higher; a listed player counts at 70 percent
   of his value, a player without a contract at 100 percent".

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
| `0x047d4200`, 3,424 bytes (version 1: `0x047d3c40`, 384 bytes) | zero | ten ceilings, ten highest ratings for the second search, twelve single numbers, the two rating ranges by level, the personas by level (10 x 8), 16 personas of 20 bytes, 192 named clubs (persona and id), 64 pairs of rivals, the routine of 1345 bytes | the same |

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

```
python3 test_money.py ~/pes-work/game/PES2017.exe
ok 0: without the module the emulated game gives the amounts of ../tools/money.py (salary with role, age band and award bonuses at every place of the club ranking; fee); its budget function adds twice the mean of the 16 highest fees and the wage bill plus twice the mean of the 16 highest salaries; cup_prize and league_prize give the game's lists (2626 and 6720 cases); a prize goes to the balance only; the contract limit is 3 years up to age 23; the three amounts of yearly income are 25 x popularity - 670 x the club's number - 3,451,330 (whatever the wage bill), (403 - rank) x 5,000 and 15,000 + 165,000 x club level; on 28 and on 30 June the yearly budget step gives the two grants of money_cave.june_grants for 2,000 cases each (to within 2); ai_candidates, the code that lists the players a computer club may sign, run whole through its two calls in ai_pick_candidate and, for three cases in eight, with ai_pick_candidate itself run from its first instruction to the end of its two searches, lists the first three players of the lists from the highest overall down who pass its tests (in a deal, on loan, the status band a slot asks for), whatever their value; ai_pick_candidate searches the first set of lists and then the second, a plan of kind 1 or 4 the second only, in the rating range of the club level, or from 99 down to 41 when the lowest overall handed in is 0
ok 1: MLMoney.lua and then MLTransfers.lua pass their checks, write only their own memory and the places they report, and what they wrote is what money_cave.py builds from the same settings
ok 2: with the changes in, the game's code gives the amounts of money_cave.py: salary and fee for 3000 + 3000 random players (ratings 40 to 255, ages 0 to 63, every position, with and without awards and the random change) and for every place of the club ranking; the budgets of 150 squads of 0 to 40 players; cup_prize for 2626 cases (competitions 0 to 100, stages 0 to 12, two game modes; mode 0x28 keeps its own table); league_prize for 11648 cases (every list, place and half); the two places that pay a prize, in Master League and four other modes: balance, transfer budget, account line, registers and stack; the two bonus routines leave every other register as it was; the contract limit for every age; the three amounts of yearly income for 600 cases each, with wage bills from 0 to the largest number; ai_candidates run whole for 750 random sets of lists (club levels 0 to 9 and six numbers that are no level, both searches, both sets of lists, plans of every kind, any day, slots that ask for a status band; players without a contract, listed, in a deal and on loan, of any status band, of clubs with 0 to 40 counted players and of no club; buying and selling clubs anywhere in a made-up club ranking, named in CLUBS or not, some missing from the ranking, which the game's own search of the ranking answers as the routine does; the ceiling put where one player is just within the club's limit for him and 1 below that; three cases in eight with ai_pick_candidate itself run up to the end of its two searches, so that level, range, the mark of the second search and the place each search returns to are where the game puts them): it lists the players of money_cave.candidates (rivals, selling side, scouting, the persona of the buying club and of the selling club, the price), passes over the others and goes on, leaves stack, registers, player records and plan as the game does, and entered from anywhere else it lists as the game
ok 3: with every optional part switched off only the fee place is written and salary, prizes and contract limit are the game's own; each of the 20 optional parts switched on alone changes its own places and nothing else; BUDGET_SALARY changes the salary budget; with spread, position and salary age switched off the value is VALUE x AGE plus popularity; PAY_GAP = 1, 1.5, 2, 2.75, 7.3, 10 give the club factor of money_cave.py at every place of the ranking; with every setting at its limit the code and money_cave.py still agree; the ceiling without the rating rule, with groups without a ceiling, with none at all (the rating rule alone) and with the lowest amount everywhere; the hard ceiling of version 5 (CEILING_STRETCH = 0, CEILING_NEED = 0, CEILING_LISTED = CEILING_FREE = 100), each of the four alone, and all four at their limits; the rivals alone and with each other part, 1 to 64 pairs among 2 to 128 clubs; MLTransfers.lua with the personas alone, with the selling side, with the ceiling, with and without scouting, PERSONA_SPREAD 0 to 50, STRENGTH, WINTER_MONTH and SQUAD_NEED at their limits; 1, 7 and 15 personas with numbers anywhere inside their limits, groups of 1 to 8 names, 0, 1, 40 (each id twice) and 192 named clubs: 500 to 700 sets of lists each
ok 4: WRITE = false, one changed byte at 60 places of the checked code and data, memory not empty, 57 kinds of faulty settings: MLMoney.lua writes nothing, and MLTransfers.lua after it writes nothing either; a write to its memory that does not stick: the code is not touched. MLTransfers.lua: WRITE = false, one changed byte at 30 places of the transfer code, its memory not empty, 51 kinds of faulty settings, a write that does not stick: it writes no place of the code and MLMoney.lua is installed as without it; run without MLMoney.lua, before it, with a mark that is not MLMoney.lua's, with a changed byte at 6 places of the value routine and the two numbers it uses, or a second time: it writes nothing; with another version number in the mark and the same value routine it installs; with CEILING, SELL_SIDE and PERSONA off and RIVALS empty it does not look at the game at all
ok 5: Bruno Fernandes as the user saw him without a module (rating 89, salary 7,259,700, value 36,743,200): the game's formula gives exactly that value from that salary with popularity 955, and with no other rating from 60 to 99
      as the user saw him with version 2 and SPREAD = 0 in a new career (age 32, value 52,973,200): the module's formula gives exactly that for an AMF of rating 89 with popularity 910, and with no other popularity
```

About 4½ minutes. The prize, budget, salary and income code of the game runs as machine
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
personas whose numbers are drawn anywhere inside their limits. Each run of the game's
code is stopped after 100,000 instructions, which no sound case reaches.

The test was tried against planted faults. Version 2: ten in the routines and the
changed places (wrong shift for the position, wrong mask for the age, the id read with
its unused upper half, wrong table for the salary age, wrong step of the spread, wrong
divisor of the popularity bonus, wrong number slot or wrong sum in the budget routines,
a call one byte off). Nine made it fail. The tenth, leaving out the `test esi, esi` at
the end of the transfer budget routine, cannot be seen in the emulator: the jump after
it reads the zero flag, which a real processor leaves undefined after a division and
the emulator does not. The instruction is there for the real processor.

Version 3: twenty more (the prize routine without the mode test, with the stack off by
4, with an unsigned division, without the call to `balance_add`; the bonus routines
without the popularity part, without the awards, with a register not restored; the two
league lists swapped; a cup operand pointing to the stage column; the pay gap operand
one byte off; the contract limit written to the wrong instruction; two faults in
`money_cave.py`'s own arithmetic; six in the Lua: a cup amount in the wrong row, a
wrongly built floating-point number, league places shifted, the contract years setting
ignored, a place written although switched off, one piece of code not compared). All
twenty made it fail; two of them (a register not restored in a bonus routine) only
after a check of the routines' registers was added, because the game does not use
those registers afterwards.

Version 4: thirty-two more, run together with the twenty of version 3 (52 runs). In the
routines: the talent bonus without its zero below the ordinary rating, without the
limit in money, replacing the value instead of adding to it, with the percent limit
one step late; income scaled below zero, without the 5,000 per place, with the 15,000
added after the percent, with two places swapped; the wage bill kept in the slot of a
saved register, `club_popularity` reached without its argument or with the wrong one,
the wage share not added or added before the percent, the place one byte late; the
league routine with rows of the wrong width, without the unit of 100, comparing unused
slots; two national cup amounts swapped. In `money_cave.py`'s arithmetic: a wrong
stage for the national cups, the talent bonus after the position, the constant of 30
June used on 28 June, the wage share added after the floor of 1,000. In the Lua: the
talent table one year late, the television money of one cup given to every cup, the
national amounts in reverse, the income percent or the wage percent not written, a
short league list filled with zeros, the count of leagues one short, three places
written although switched off or not written although needed. All 52 made the test
fail. Two of the new ones (the argument of `club_popularity`, the saved register) are
seen only by a check of `season_income`'s argument and registers that was written for
them: the result of the function is right with either fault. One planted
fault was dropped as no fault at all: comparing the league number in 16 bits, which is
all the game keeps of it. The wage share added after the floor of 1,000 is seen only
with a wage bill near the largest number, because the game's amount never reaches
that floor.

Version 2 of `MLTransfers.lua` (`python3 planted_faults.py <exe> files` and `routine`).

*Faults in the files:* 106, each with a whole run of the test. In the Lua: those of
version 1 (ceilings or ratings in the wrong order, the place not written, checks left
out, wrong limits, the memory not written or not read back, a wrong size or address),
the selling side never switched on, half the spread, the strength without its rounding,
two numbers or two places of a persona swapped, the groups in the wrong order, a short
group filled wrongly, scouting always on, the persona of a named club one too low, a
faulty setting let through, `MLMoney.lua` not looked for or looked for at the wrong
place, a place that is changed already not seen, a write with `WRITE = false`. In
`money_cave.py`, the model the routine is compared with: the price rules of version 1
each a step off; for the selling side, 23 players being enough, band 7 allowed to go, a
club of level 8 letting go, each of the three exceptions a step off, the rule also in
the first search, `keeps` one percent off; scouting, the player's say, need, the place
a club looks in, winter, the ages, the fog and `ambition`, each a step off or with a
part left out; the numbers of a persona left out of the limit; the spread from club to
club left out; the first instead of the last entry for a club; the strength of the
eleven not kept inside the range. For the rivals, in the Lua: the part alone
writing nothing, the last pair left out, the table four bytes too high, a 65th pair, a
club as its own rival, three clubs in a pair or a faulty id let through, the part not
named in the RESULT line; in the model: listed players left out, players without a
contract taken in, one direction only, the buyer never compared, the part alone not
counted as on. **The 92 older faults all made the test fail before the rivals were
added. After it, 22 were run: the 14 new ones and eight older ones that touch the
memory, the named clubs and the line that switches the module off. All 22 made the test
fail. The other 84 were not run again.**

*Flipped bits in the routine:* the routine has 1,413 bytes; one bit of each byte was
flipped in turn (bit 0 of the first byte, bit 1 of the second and so on: 1,413 of
11,304 possible flips, not all of them as for version 1, which would take about a day).
After each flip 1,800 cases ran, 500 with the settings of the file and 1,300 with five
other sets (two of them with 64 pairs of rivals, among 12 and among 128 clubs; one with
none). 1,346 flips were noticed. The 67 others were run again with twice the cases,
which noticed 8 more: **1,354 of 1,413 are noticed, 59 are not**. `bitflips_v2.tsv`
lists the 59 and how each was sorted. Read one by one:

- 34 do the same thing on a real processor for every value that can occur: a shift
  count above 31 (the processor uses its low five bits), `cmp x, 0` turned into
  `sub x, 0`, a jump condition that cannot differ after that compare, a byte compared,
  added or moved instead of four where the number is below 256, an arithmetic shift of
  a number that is never negative, another way to write the same instruction, a larger
  stack frame, the two saved registers the game loads anew, mask bits that are never
  set, a compare turned around before a "not equal" jump, and a jump in the rivals'
  loop that lands on another jump to the same place.
- 7 are on the path for an amount that does not fit 32 bits, where the routine puts
  the largest number. Six give another huge number, which refuses the same players. One
  turns the `ret` there into a `ret` that drops 46 KB of stack: that would crash the
  game, and the test has no case that takes this path with it.
- 18 are not settled: two limits moved to where the test has nothing (a club index
  with bit 10 lost or up to `0x2cc`: the test's pool counts nothing for other clubs);
  "no ceiling" compared with another number; a divisor of 100,002 instead of 100,000;
  a signed instead of an unsigned product and shift, which differ only for numbers above
  2,147 million; two where the stack pointer is moved before the routine restores it
  from `ebp`; eight where an instruction also changes a register or a local that seems
  not to be read again, or uses a carry that happens to be clear (one of them puts the
  saved `edi` into `esi` on the way out of a refusal); and a frame of 128 KB instead of
  144 bytes, which the emulator cannot show but the real game would.

So the test notices a fault in about 19 of 20 places it was tried, and what it misses
is mostly not a fault. That says how sharp the test is, not that the routine is right
in the game: that is still to be seen.

These numbers are from the routine as it is now, with the rivals in it. Because the new
instructions moved the rest by 68 bytes, the bit that was tried in each later byte is
another one than in the run before (1,283 of 1,345 then; 62 not noticed, of which 23
were not settled). The two runs agree in size; they are two samples of one bit in
eight, and seven bits of every byte are still untried. One flip found between the two
runs, in the distance of the call to the value routine, is of the kind the test cannot
see: the call lands four bytes early on two zero bytes, which a processor reads as "add
the low byte of `eax` to the byte `eax` points at", and then runs into the routine.

The price ceiling of version 1 (`python3 planted_faults.py <exe> routine` and `files`; run again
after the ceiling moved to `MLTransfers.lua`, with the same counts for the routine):
every one of the 2,504 bits of the ceiling routine was flipped in turn. 2,497 flips
made the cases fail (version 5: 1,169 of 1,176). Six of the other seven turn the
`push ebx` or `push edi` at its start into the push of another register, so a wrong
value comes back in `ebx` or `edi`; the game loads both anew right after
(`0x0365fb28`) or returns, so no result changes, and the routine restores them all the
same. The seventh turns `sub esp, 0x1c` into `and esp, 0x1c`; the emulator has memory
at address 0 and the test answers the rating call itself, so the routine still works
there, while the real game would stop. Then 37
faults in the files, each with a whole run of the test: in the Lua the ceilings or the
ratings in reverse order, the place not written, the comparison of the transfer code or
the test for empty memory left out, "no ceiling" written as 0, wrong limits, the rating
rule always on, the second piece of memory not written or not read back, a wrong size
or address of it, a faulty setting let through; in `money_cave.py` a value equal to the
ceiling or a rating equal to the top refused, the rating rule in both searches, the
lowest list searched too, the ceilings in reverse; and for version 6, in the Lua the
need written without its 100, the two discounts swapped, a negative number let
through, in `money_cave.py` need counted in only one of its two cases, a wrong divisor
of the stretch, the club left out of the hash, the discount for only one of the two
statuses, both discounts for a listed player without a contract; and for the two
files, in `MLTransfers.lua` the mark of `MLMoney.lua` not looked at or looked for at a
wrong address, the value routine not compared, a ceiling that is in already not seen,
`WRITE = false` not obeyed. All 37 made the test fail.

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

## What was looked at in `sider.dll`

Read from the DLL's code and strings, not run:

- A module must return a table with an `init(ctx)` function. It gets these names:
  `log`, `memory` (`read`, `write`, `search`, `pack`, `unpack`), `string`, `table`,
  `math`, `pairs`, `ipairs`, `tostring`, `tonumber`, `type`, `unpack`, `assert`,
  `error`, `os` (`time`, `clock`, `date`), `audio`; with `luajit.ext.enabled` also
  `ffi`, `bit`, `require`. There is **no `pcall`**: an error in `init` makes Sider skip
  the module and log the error.
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
  (3,584 bytes; `MLMoney.lua` uses the first 3,568), and below it `0x047b0124`-
  `0x047b01fe` (used by version 5 only; free again). The end of `.xcode`,
  `0x047d3a43`-`0x047d3dff` (`MLSimMatch.lua` uses `0x047d3a50`-`0x047d3de3`, 915 bytes;
  previously used by version 6 of `MLMoney.lua` and version 1 of `MLTransfers.lua`). The page of `.data1`
  behind its code, `0x047d4170`-`0x047d4fff`: `MLTransfers.lua` version 2 uses
  `0x047d4200`-`0x047d4f5f`; 160 bytes above it are free, and whether the running
  game leaves that page alone is not seen yet. A module must see zeros there before it
  writes.
- A routine that is called from inside a game function can read the arguments of that
  function's caller through the saved `ebp`, if it first checks the return address.
  The routine of `MLTransfers.lua` does this to get the club level without changing a
  call, and reads the locals of the function it is called from (date, pool, player) the
  same way.
