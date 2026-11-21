# AI transfers: selection rules and observed windows

[Sider developer guide](../README.md) · These are versioned implementation notes and test observations. For current settings and deployment, use the guide and shipped Lua files. Paths and commands assume the `sider` directory unless noted.

## `MLTransfers.lua`, version 9: the selling side, club personas, scouting, rivals, position need, offers for your players, squad pressure

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
`0x047d6e50`-`0x047d6efd` and of `MLSimToDate.lua`'s day-loop hook at
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

A faulty setting is named in `sider.log` and nothing is written, as before.

### What the log says

```
MLTransfers 9: the transfers of the computer clubs from the settings in MLTransfers.lua
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
check: plan          at 036602e5  as expected
check: fill          at 03661b15  as expected
check: lineup        at 03894bcf  as expected
check: team          at 03822969  as expected
check: player        at 03822835  as expected
check: no player     at 02bddabe  as expected
check: no player id  at 024feb04  as expected
check: free memory   at 047d4200  empty
check: free memory   at 047d6400  empty
check: free memory   at 047d6550  empty
check: free memory   at 047d6c50  empty
written: transfers at 0365fb0d  ok
written: need plan at 03660b93  ok
written: need pick at 03660c83  ok
written: incoming  at 0381e2eb  ok
```

then the ceilings, `selling side: ...`, `club personas: 13 personas, 180 clubs named,
...`, the two lines of version 3 (`a club keeps its first team: for each rating point a
player stands above its eleven minus 4, 12 percent more often; not against a buyer
whose eleven is 2 or more points better` and `players rated 80 or more are known to
every club; the ages of a persona are moved by up to 2 years from club to club`; between
them the line of version 9, ``squad pressure: a club with more than 3 goalkeepers, 8
defenders, 9 midfielders or 6 forwards counts `keeps` 40 lower for a player of that
group``), the
line of version 4 (``players of a popularity of 600 or more are known to every club; for
a player without a contract 35 percent of `strict` count``), one
line per persona, `rivals: 61 pairs of clubs do not buy each other's
players who have a contract`, the line of version 6 (`position need: a club looks for a
player for the weakest place of its eleven, the goalkeeper included, when he stands 4
or more rating points below the mean of the others; it takes only a player rated 1 or
more above him`), the line of version 8 (`offers for your players: the club that makes
one is the one of the nearest slot that would take him (no rival, its character wants him,
a place in its plan, its ceiling), so none is lost`), and `RESULT: installed. Changed: price ceiling of the
computer clubs, selling side, club personas, scouting, rivals, position need, offers for
your players.`
With `NEED = false` the three `check` lines, the second `free memory` line, the two
`written: need` lines and the words `position need` are missing. With `INCOMING = false`
the third `free memory` line, the `written: incoming` line and the `offers for your
players` line are missing. The four `check` lines `team` to `no player id` and the last
`free memory` line (version 9, squad pressure) are always there.

If two entries of `CLUBS` name the same club, the last one counts and a line `note: N
entries of CLUBS name a club that a later entry names again` says so (new in version 3;
the file as shipped has none).

**The line that matters most is `free memory at 047d4200`.** Versions 3 and 4 need 3,584
bytes (version 2: 3,424; the 160 more are the rest of the same page, which no version
has used in the game yet: the module looks for zeros there as everywhere) and version 1's place (`0x047d3c40`, 384 bytes) is too small, so it uses another
piece of memory that has never been used in the running game: the rest of the page of
the small code section `.data1`. In the file that page holds 368 bytes of code and
zeros after them, and nothing in the file points behind the code. In the one window
that was played with it the game left it alone: the signings follow the rules up to the
last one, on 30 August. If the line says `NOT EMPTY`, the module writes nothing; send
the log.

**New in version 6: `free memory at 047d6400`**, 336 bytes for the position need, in
the page of the section `.link` that `MLSimMatch.lua` (up to `0x047d6376`), this module's
offers for your players (from `0x047d6550`) and `MLGrowth.lua` (`0x047d6e50`) also use.
It holds zeros in the file. This piece
has not been used in the running game yet. If it says `NOT EMPTY`, set `NEED = false`
and send the log.

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
