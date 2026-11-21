# Negotiations, scouting and AI recruitment

[Master League guide](../MASTER_LEAGUE.md) · Section numbers are the original research citations. Paths in the notes are relative to `pes database/exe` unless a command changes directory.

## 7 Negotiations of the user's club

Level: **read** in part; arithmetic on fractions is lost in the C at several places,
so the numbers below are what could be followed. Not run.

### 7.1 The deal record

70 records of `0x1dc` bytes at `mode data + 0xd06438`. One record is one player the
user's club is dealing with. Dwords of the record:

| dword | what |
|---|---|
| 0, 1 | player id |
| 5, bits 0-3 | **state**, 0 to 13 |
| 5, bits 4-7 | kind of deal; `0x20` is treated apart (taken to be a loan) |
| 5, bits 8-11 | a small number from `fcn_0388a1be` (taken to be contract years) |
| 10, 11 | the two money figures of the club's answer |
| 14, 15, 16 | three extra figures, each made by `fcn_038a9dc5` from figure 11 |
| 18-21 | two more player ids (players offered in exchange) |
| 25 | date on which the other side answers |
| 28 | the `kind` handed to the fee formula |
| `+0xf8` | five entries of `0x20` bytes: other clubs in the same deal, each with a day counter |
| `+0x1d4` | the day's chance number, 1 to 100 |

### 7.2 The step

`negotiation_step` (`fcn_03659b50`, 1,621 lines) walks the 70 records. It runs at the
day end of every window day (event 9) and at the day begin of the days a window opens
(events 3, 6). On the daily run the day counters of the five other clubs go down by 1.
Then a switch on the state (13 cases). For state 2, when the answer date is reached:

1. The deal ends at once (state → 8) if the player's record has bit 31 of `+0xb4`
   set, if his status is 4, or if his age is 45 or more.
2. The salary formula is run for the player at the user's club, the fee formula for
   the fee, and `fcn_0388a1be` for the years.
3. `n` = how many of the five other-club entries are in use; a factor
   `0.9 + 0.1 * n` enters one of the figures. More clubs after the player, higher
   price.
4. If the player is in one of the 3 × 16 result lists at `+0xd0f154` (section 8), the
   first figure is cut to **70 %**.
5. Two scores from 0 to 100 are computed (`fcn_0389b3f8`, 352 lines, and
   `fcn_0389bd94`, 276 lines; both use rating, the squad and `fcn_0389a28a`); the
   lower one counts. Below 100 it raises the first figure by
   `(100 - score) / 100` of something (operands lost).
6. Unless the player's status is 2: three draws of `rand(100)` against
   `fcn_03896290`, `fcn_03896c26` and `fcn_0389675b` (three functions of 169 lines
   each; not read) decide whether the three extra figures are asked.
7. Two more draws of `rand(100)`. The first is compared with the score; if the score
   is 40 or less and the second draw is below 10, the marks `2` or `4` are set in
   dword `0x76` and a figure is raised. On the paths the C shows, the state becomes 5
   and the figures are stored. **What a draw above the score leads to cannot be told
   from the C** (the decompiler drops branches here); the disassembly was not read.
8. The figures are stored in dwords 10 and 11 after `money_clamp`
   (`fcn_038a9d95`), the years in dword 5.

States seen being set: 5 (with a "new" mark at `+0x1ce`, as for 6 and 11) and 8
(the mark is cleared). So 5 is taken to be "answer received" and 8 "ended". The other
cases of the switch are not read. In case 0, `fcn_03658eda` (422 lines) is called; it
tests events 5 and 8, reads the club plan records and uses the salary and fee
formulas. Case 3 follows the pattern of case 2 with `fcn_03657dcd` and
`fcn_03658371`. `fcn_03658821` (225 lines, event 9) calls `complete_transfer`.

The screens: `menu::MenuModeMLNegociationMenu`, `…List`, `…Detail`, `…Adjust`,
`…CountDown`, `…Dialog` (appendix B). `MenuModeMLNegociationDialog` calls
`fcn_0388d7fb` (633 lines) and `fcn_03898af6` (720 lines; uses salary, fee and
`complete_transfer`). `complete_transfer` (`fcn_0389840a`, 11 callers) →
`fcn_038913b5` (745 lines). Not read.

### 7.3 Years of a contract: `deal_years` = `fcn_0388a1be(&player, club, &flag)`

Level: **read** (disassembly of the first part; not run). 12 call sites.

```
n     = 7 bits of the player record at +0xb4, bit 23 (0 to 127; meaning ?)
years = 1 if age >= 35, else 1, 2, 3, 4, 5 for n below 30, 50, 70, 90, and above
years = years - 1 + (age + word at mode data +0xc2cbb0) mod 3
years = at most the limit by age (fcn_03887f5d): 1 from 35, 2 from 32, 3 below 24, else 5
years = at least 1; at most 2 from age 32
```

If the flag byte is 0, more follows (for game mode 13 the years are cut so that the
contract ends within 5 years of a date in the record; in some months 1 year becomes
2); that part is read from the decompile only. The limit of 3 years below age 24 is
one immediate in `years_limit` (`fcn_03887f5d(&player)`, 16 call sites, **run in the
emulator** for every age): `mov eax, 3` at `0x03887fc1`. `sider/MLMoney.lua` changes
that number (6.6).

### 7.4 The offers for the user's players

Level: **read** (disassembly of `fcn_03649f1f`, `fcn_0364c065`, `fcn_036497b5`,
`fcn_03658821`, `fcn_0315e472`, `fcn_036524ac`, `fcn_036582ac`, `fcn_03655628`,
`fcn_03652df0`, `fcn_0381e2eb`), and `fcn_03652df0` **run** in `tools/emu.py` on
made-up frames. This is the path a module would have to change to make the offers a club
receives for its own players realistic; it is written down here because it is not the
path of section 9.

**The list.** 70 records of `0x14` bytes at `mode data + 0xd0e660` (the gap between the
deal records and the scout slots). Only `fcn_03649f1f` and its two helpers read it in
Master League:

| offset | what |
|---|---|
| `+0` | first dword of an id pair; `fcn_0314a909` and `fcn_03649f1f` copy it with `fcn_03676372` and compare it with the user's club, so in Master League it holds a club |
| `+4` | the second dword of that pair (0 when there is none: `0x024fea2c`/`0x024fea30`) |
| `+8` | state, 1 to 7 (`fcn_03652df0` writes a club id here in the deal record, a different structure) |
| `+0xc` | a date in Master League: the day the approach arrived |
| `+0x10` | flags: bit `0x100000` is tested by `fcn_0314b223`; in Become a Legend the low part is the years (`fcn_036e2557` case 1) |

**The step.** `fcn_0364c065` runs at the day end and, in Master League only
(`fcn_038093f1` = 0xc), calls `fcn_03649f1f`. On the 10th of a month it also calls
`fcn_0364b1b6`, which makes the news for these records. `fcn_0364b81c` (day begin,
event 11) calls `fcn_036497b5`, which sends the messages of states 1, 3, 4, 5 and 7.

For a record in state 1 `fcn_03649f1f` does, in this order:

1. event `0x18` on this day → state 2 and message `0x3a`;
2. the date at `+0xc` must be 10 to 45 days old, else the record is left alone;
3. the club at `+0` and the user's club (key `0x02100846`) are looked up in the club
   ranking (`fcn_03138333`). If the user's club is worse placed, state 4 and message
   `0x39`; otherwise a chance of `100 + place(buyer) - place(user)` (at least 10) is
   drawn against `rand(100)`: state 4 and `0x39`, or state 2 and `0x3a`.

**No price, squad need, persona or rivalry is read.** The only thing that decides is
the two places in the ranking and one draw.

**The close.** `fcn_03658821` (called from `negotiation_step`, 0x03659b50) is handed a
deal record and calls `complete_transfer` (`fcn_0389840a`). The fee of such a move is
the one `do_transfer` computes (6.2), so it follows the value of `MLMoney.lua`; no
figure of the offer is used for it.

**The five suitors of a deal record.** The 70 deal records of 7.1 carry five entries of
`0x20` bytes at `+0xf0` (the `+0xf8` of 7.1 is the day counter inside an entry). The
accessor `fcn_0315e472(deal, out, i)` copies entry `i` (entry 0 when `i` is 5 or more);
`fcn_036582ac(deal, entry)` checks the club and calls `fcn_036524ac`, which looks the
club up among the five by its low 14 bits and, when it is not there, writes it into the
first empty entry; the routine then sends event `0x3d`. Inside `fcn_03658eda` the
attach call is at `0x03659325` (the accepted suitors) and `0x03659467` (the second
list), and again at `0x03659759` and `0x0365980b` once a figure has been computed.
Entry `i` is read before that, at `0x0365915e`-`0x036592f4`, so the routine works on
**the five entries the deal already holds**: it copies them out, tests them
(`fcn_02c7d227` is true when the club id is not the empty one at `0x024feac8`) and
attaches the ones that pass again.

**Where an offer is born.** The five entries are written by `fcn_03652df0`, whose only
caller is `fcn_03655628` (1603 bytes; the three call sites of that one are the message
pump). `fcn_03655628(player id pair, message)` is the handler of the messages a club
sends when it wants a player of the user's club:

* `*ecx` is a level. It becomes the window of club levels that may bid:
  `low = level - 2` (0 when `level < 3`), `high = level + 2` (9 when `level >= 7`);
  message codes `0x18` and `0x19` open it to `0..9`;
* `[message + 0x10]` is how many clubs are tried;
* it walks the per-club candidate lists (8-byte entries at `container + 8 + n*0x10`),
  drops the clubs already counted — `fcn_0388ba8a(&player, &club, &buf, &flag,
  message + 0x18)` returns the running count and the club is skipped when
  `[message + 0x18]` is already below it. **`[message + 0x18]` is the cap on the
  offers for a player.** It also drops the user's club (`0x024fea5c`) and, for code
  `0x1b`, clubs of another federation (`[+0x310]`);
* for message codes 1, `0x18` and `0x19` it then calls
  `fcn_03652df0(player, deal proto, &club)`.

`fcn_03652df0(player, proto, &club)` is the one that materialises an offer:

1. the room test on the **buying** club: `([buyer + 0x328] >> 9 & 0x7f) -
   fcn_03889077()` must be **more than 16**, unless `[player + 0x1c] == 1` (the direction
   is from the emulator run below, not from the reading);
2. `[proto + 8] = club`, the id pair into `+0`/`+4` and `+0xc`;
3. bits 4-7 of `[proto + 0x14]` = the role (`fcn_03652d7a`), bits 8-11 = a chance from
   `fcn_03855998(&age)` cut down to 1 when it is 0 or when a flag is set;
4. `fcn_036524ac(proto)` appends the club to the five entries of `proto`;
5. the salary is computed into the player at `+0x28`/`+0x2c`
   (`fcn_038ac66e`/`fcn_038ab832`, then `fcn_038a9d95`), and the news message `0x21`
   (roles 4 and 0xa) or `0x2c` is posted with `fcn_031538bf`.

**There is no transfer fee in this path.** The only figure is the salary
(`fcn_038a9d95`). The fee of an outgoing move is computed at the transfer itself
(`do_transfer`, 6.2), so it follows the value of the player, not an offer.

**What this means for a module.** The number of offers a player gets is
`min(cap in [message+0x18], clubs in the level window)`, and the clubs are then
checked one by one. Filtering there can only subtract. To *add* sensible offers, the
module has to call `fcn_03652df0` itself with a club it picked — the three arguments
are known, the room test, the salary and the news come with it — or widen the level
window / raise the cap, which adds the wrong clubs (a window is a range of levels, not
a judgement of need).

**Not read:** `fcn_036527f2`, which builds the `proto` that `fcn_03652df0` writes into
(the object is temporary: `fcn_03653bf9(&proto)` destroys it after the call, so the
persistent record is written inside one of them); what `fcn_0388ba8a` counts and what
it does with `message + 0x18`; which of the three callers of `fcn_03655628` runs in
Master League and with which level; the other states of `fcn_03649f1f`.

**Run, not just read: what `fcn_03652df0` writes.** `tools/emu.py` runs it with every
look-up it calls answered with a chosen value (`fcn_0381c0e5` → a block whose `+0x30`
points at mode data; `fcn_0381e2eb` writes `0x333` and zero; `fcn_03822835` → a club
record; `fcn_03822969` → a club record whose `+0x328` is the squad count; `fcn_03652d7a`
→ a block whose `+4` is the role; the six formula and news calls → numbers). The offer
writer `fcn_036524ac` and the routine itself are the game's own code. Two runs, with the
third argument pointing at `0x111`, the look-up answering `0x333`, and the third
argument of the *caller's* kind in the last field:

| written | value | where it comes from |
|---|---|---|
| `+8` | `0x333` | the routine's own look-up (`0x02100a66`), **not** an argument |
| `+0xc` | `0x111` | the second argument (low 14 bits) |
| `+0x14` | `0x0170` | bits 4-7 role `7`, bits 8-11 the chance `1` |
| `+0x28`, `+0x2c` | the figure | `fcn_038a9d95` |
| `+0x64` | `0x21` | the news code |
| `+0x70` | the third argument | written straight through |

and **the room test is `squad > 16`, not "at most 16 below the target"**: with a squad
count of 0 it wrote nothing but `+0x70` and returned; with 40 it wrote the rest.
`fcn_036524ac` left no readable id behind in the five slots at `+0xf0` in either run —
the ids are stored scrambled, so the emulator cannot show which slot took the club.

What this settles: the club that buys is the one the routine **looks up itself**, and
the second argument is a different club (it only reaches the low 14 bits of `+0xc`).
Redirecting the buyer therefore means changing what the look-up answers, that is the
global behind `0x02100a66` that the posting code filled, and not the argument of
`fcn_03652df0`. That global, and `fcn_036527f2` which runs just before the call, are
the places left to read.

**The byte the buyer comes from.** The key pushed at `0x03652e08` is `0x02100a66`
(the decompiler printed it a digit short), and `fcn_0381e2eb(ecx = mode data, &out,
key, &out2)` reads **one byte** there and answers a club id (`ret 0xc`):

* it walks the club table at `mode data + 0x481be0`, stride `0x520`, count
  `[mode data + 0x5fece0]` (up to 0x28d);
* it skips the club equal to `[0x0251f85c]` (the club of the player being handled) and,
  when `[[out2]] == 1`, the clubs whose `[+0x31e] & 7 == 1`;
* it takes the first club whose `[+0x314] >> 7` equals that byte and writes its id to
  `*out`; when none matches, `*out` gets `[0x0251f85c]`;
* the byte is only ever **pushed** (8 sites: `0x03652e08`, `0x036541c8`, `0x036547d2`,
  `0x03655cf5`, `0x03656a36`, `0x03656a76`, `0x036570ac`, `0x036570ec`) and never stored
  through a literal address, so what fills it does so indirectly, most likely the screen
  that opens the negotiation.

So the buying club is "the club at slot `n` of the competition in hand", `n` being that
byte, and the club record packs `n << 7` into `+0x314`. There are two ways to redirect
it: write a different `n`, or repoint that one `push` to a byte of the module's own and
fill it. The second is the clean one — `68 66 0a 10 02` is five bytes, so it can be
replaced on its own and the other seven readers of the byte stay untouched.

**What is done about it.** `sider/MLTransfers.lua` (version 8, `INCOMING`; version 9
gives it the rest of the rules) answers that
look-up itself, in the place of its prologue, for that one key. Version 7 only refused a
rival; version 8 keeps the club of the game's slot when it passes and otherwise answers the
club whose slot is **nearest** to the game's own among those that pass all four rules: no
rival of the player's club, a persona that wants him (the age band with `AGE_SHIFT`, the
ambition, the prestige, the strictness — the genes and the tables of the selling side, so
it is the same arithmetic as `ai_candidates`), a place in the buyer's own plan record
(`+0xccb80c`, `0x118` bytes, ranking order, count `+0xd06434`: a slot with `kind` whose
position is his and whose state is 0 or 7, or the position need written at `+0x109`), and
a price it can afford (the value `MLMoney.lua` gives the player, less `CEILING_FREE` or
`CEILING_LISTED`, at most `CEILING[level] x wealth x (1 + premium + panic)`, the club
passing when its level has no ceiling). The rule of version 7 that guessed the room of the
substitute from the squad count is gone: `fcn_03652df0` runs its own room test on the
answered club, and if it refuses, that is the game's decision. Nothing is written to the
mode data, so the slot space does not have to be known: the answer is a club id, not an
index. The fee is untouched (`MLMoney.lua` computes it at the transfer), and the module
answers the game's own club when no club passes, so it neither adds nor removes an offer by
its own choice.

**Version 9** adds what version 8 left out, so that the rules are those of `ai_candidates`
themselves (`money_cave.accepts`): scouting (`knows`, with `KNOWN_FROM` and `KNOWN_FAME`);
the place the club buys from (`free`, `listed`, `clubs`, with `THEN_1` for a club in want of
the position); the stretch of the ceiling above it (`CEILING_STRETCH`, `premium`, `fame`) in
place of the hard cut; and the day of the career in every draw (the word at
`mode data + 0xc2cbb0`, the year behind it), which is what keeps the same club from bidding
again and again. A club the position need marked for his position is a club in want of him:
it does not mind his age or the rating it makes of him, and it goes further for him.

`sider/test_offer.py` runs the real look-up at that place on a made-up mode data (club
table, plan records, club ranking, personas, rivals, the player's record) for 200 cases
against `money_cave.offer_pick`, the same rules in Python: 142 keep the game's club, 19
answer another club, 39 have no club at the game's slot. The source is `sider/incoming.c`,
assembled by `offer_source.py` into the 1,661 bytes at `0x047d6550` that the module ships.
`MLSimToDate.lua` version 3 used the same page, so the two could not be installed together;
version 4 moved its calendar block to `0x03fc8000`-`0x03fc88ff` in the unused `.trace` run
at `0x03fc7d9c`-`0x03fc9da0`, and the two install together now.

**Not read still.** `fcn_036527f2` (the object `fcn_03652df0` writes into, destroyed right
after), what `fcn_0388ba8a` counts, which of the three callers of `fcn_03655628` runs in
Master League with which level, what `+0x314` holds below bit 7, and the other states of
`fcn_03649f1f`.

**What blocks a patch here.** Three things, in the order they were found:

1. no fee. Settled: the fee of an outgoing move is computed at the transfer from the
   value of the player, so `MLMoney.lua` already owns it and an offer has no amount to
   write;
2. `[record + 8]` does not come from the third argument. `fcn_03652df0` fills it from its
   own look-up (`fcn_0381e2eb(&var_8, 0x02100a66, &var_10)` at `0x03652e08`), and that
   same value is what `fcn_03822969` turns into the buying club's squad count. The third
   argument (`[ebp + 0xc]`) only feeds the low 14 bits of `[record + 0xc]` and
   `fcn_03652d7a`. Swapping the club in the argument alone therefore leaves the room
   test, `[record + 8]` and the news on the club the game chose;
3. no free memory. The cave at `0x047d4200` is used to its last byte (`LAST_AT` is
   `0xde4` and holds seven numbers) and `NEED_CAVE` has 0x13 bytes left. Version 8 took the
   0x700 bytes after the need block, `0x047d6550`-`0x047d6c4f` (1,661 used), which hold
   zeros in the file; the module's own emptiness check is what keeps a wrong guess
   harmless. `MLSimToDate.lua` version 3 used `0x047d6550`-`0x047d6e4f` and the two modules
   refused each other; version 4 moved that block to `0x03fc8000` (an unused run of zeros
   in `.trace`, `0x03fc7d9c`-`0x03fc9da0`), so they no longer do.

## 8 Scouts

Level: **inferred** that these are the scouts; the step is **read**.

`mode data + 0xd0f154` holds three records of `0x1e4` bytes: a player id pair, a byte
"in use" at `+0x1c`, 16 results of `0x1c` bytes from `+0x20`, and a date at `+0x1e0`.
Three slots with a list of 16 players each, a search that takes days, and the 30 %
cut in the negotiation fit the scouts of the menu (`menu::ModeMLScoutMenu`,
`ModeMLScoutingSettings`).

`scout_step` (`fcn_03652198`) runs at each day end when the byte `+0xdd0655` is set
and today is not the date at `+0xdcb68c`, except on the day before a window closes
(events 4, 7):

```
n = number of slots in use (1 to 3)
for each slot in use:
    if rand(1000) < 30 / n:          # 3 %, 1.5 % or 1 % a day
        scout_search(slot)           # fcn_0364f2ca
    else if 14 days or more have passed since the slot's date:
        (a second branch; what it does was not followed)
```

`scout_search` (`fcn_0364f2ca`, 1,381 lines) uses ratings, player fields, team
strength, the fee formula, `squad_needs` and random numbers, and writes a staff
report. Its selection rule is not read.

## 9 Transfers of the computer clubs

Level: **read** (C and disassembly), the two tables of 9.4 **proven** (check 11).
Meanings marked "taken to be" are **inferred**. The chain is now followed from the
plan to the closed deal; what a deal moves in money is still not read.

### 9.1 The plan record

`mode data + 0xccb80c`: up to 851 records of `0x118` bytes, one per club (count at
`+0xd06434`). The records are made when the career data is created
(`plan_setup`, `fcn_0365fb7d`, called by `process::ModeDataCreationThread`), for every
club that is not the user's and passes three tests on the team record, sorted
(`fcn_0365cd59` compares; order not read).

| offset | what |
|---|---|
| `+0x000` | club id |
| `+0x004` | kind 0 to 4. Set-up gives 1, 2 or 3 by the high part of the club id (1 for `0x72`, `0x78`, `0x7f`, `0xad`; 2 for 100 to 102, 108, 109; 3 for `0x10a9`; the rest of the switch is lost in the C). The kinds 1 and 4 change the search (9.5) |
| `+0x008` | 16 slots of `0x10` bytes, see below |
| `+0x108` | a byte: set to 0 when the slots are emptied (9.3), tested and set to 1 at `0x0365faa4` / `0x0365fb04` in `ai_candidates`. Meaning not read |
| `+0x109` | three spare bytes (9.3) |
| `+0x10c` | wait counter. Set-up: the running number of the club among the clubs of its level, divided by 10 |
| `+0x110` | "ready" byte |
| `+0x114` | **club level 0 to 9**: byte `+0xe` of the record `fcn_031b1c34(club)` returns. The number of clubs of each level is kept at `+0xd10118 + 4 × level` |

A slot: the player id pair at `+0`, a word at `+8`, a word at `+0xc`
(`0x630000` when empty).

| bits of the word at `+8` | what |
|---|---|
| 7-13 | position looked for; 13 = none |
| 14-21 | 1 = buy, 2 = **taken to be a loan** (it leads to deal type 2, which sets the player's loan mark) |
| 22-26 | state of the slot: 0 empty, 1 player chosen, 9 → 10 (a second way in, set outside the code read), 7 given up |

Set-up also marks players: in every club with more than 27 players that are not on
loan, up to three players of the sorted squad whose position field is not 0 (taken
to be: not goalkeepers) get a mark of `+0xb8`: mark 29 if a draw out of 13 is below
6, else mark 30.

### 9.2 When the steps run

`ai_transfer_step` (`fcn_03661f6b`, day begin, called by `fcn_0360a350`):

- **Planning and choosing** run on the stored date `+0xdcb68c`, on event 1 (first
  day of the season) and on event 30 (1 September, 1 February), if the byte
  `+0xdcb698` is set. In order: the wait counters (below), `ai_squad_counts`,
  `club_squad_plan`, `ai_pool`, `ai_fill_slots`.
- **Closing** runs on events 3 and 6 (the first day of each window) through
  `ai_close_slots(1)`, and from the day end (`fcn_0365df66`) on every day on which
  `day_state` is 2 or event 9 is on (window days) through `ai_close_slots(0)`.

Wait counters: every record is set ready. A club whose counter is 0 gets a new one
(the number of clubs of its level minus the count of such clubs so far); every other
counter goes down by one. `ai_fill_slots` serves only clubs whose counter is 0, and
**at most five clubs per call**. So the clubs of one level take turns. How often the
step is called again on such a day is not established, so the number of clubs that
shop per day is open.

### 9.3 Squad counts and the plan

`ai_squad_counts` (`fcn_0365cda9`) keeps one number per club: squad size minus the
players already promised away. `club_squad_plan` (`fcn_036602e5`, 392 lines) then
handles, per club:

1. The marks 29 and 30 of `+0xb8` are cleared for every player of the squad.
2. `squad_needs` (`fcn_0389440a`, 647 lines, read in part) copies the team and its
   tactics, takes out the players that carry a mark and have been at the club for
   more than 364 days and those with bit 31 of `+0xb4`, and returns entries of
   `0x10` bytes for the eleven positions of the formation (tactics record `+0x68`)
   and beyond: a player id and a position. Entries without a player are the
   positions the club lacks.
3. Surplus = squad size (`fcn_03888d9e`) − 23. While there is a surplus, players who
   are not in the list of step 2 and whose band (`fcn_0385400e`) is below 6 (below 8
   with a chance of 1 in 5 on the last day of a window) are marked: with a chance of
   1 in 5 mark 30, else mark 29. **Taken to be the club's list of players it lets
   go**; what tells the two marks apart is not established.
4. The positions without a player are written into empty slots of the plan record.
   Then, while squad size − marked players + new slots stays under 25, more
   positions from the list are added.

So a computer club aims at a squad of 23 to 25, keeps the players its plan names and
those of the top bands, and marks the rest.

More of the same function, from the disassembly (read for `MLTransfers.lua` version 6,
not run whole):

- It handles a club only if its wait counter (`+0x10c`) is 0, and at most five clubs
  per call, as `ai_fill_slots` does after it: the same clubs are planned and served.
- Before anything else `fcn_0365cc6d(plan, &1)` empties every slot whose state is not
  7, 9 or 10: no player, position 13, ages 0 to 99. It also sets the byte `+0x108` to
  0. So the slots of a club are made anew at every planning; a slot in state 1 from
  the time before is dropped.
- The list of step 2 is a vector at `[ebp-0x60]` (begin) and `[ebp-0x5c]` (end) of
  16-byte entries: player id pair at `+0`, a dword at `+8` with the **rating at the
  position in bits 0-6** and the **position in bits 7-13** (0 goalkeeper to 12 centre
  forward, the order of the edit file). The rating is put there by the loop at
  `0x03894bcf` with `fcn_03853b52(&id, &position, 2)`, the function `ai_pool` (9.5)
  calls with position 13 ("his own"): the same scale as the search lists. The first
  eleven entries are the eleven. An entry without a player holds the pair at
  `0x024feb04`.
- `0x036605a1`-`0x0366064c` copies the eleven without the goalkeeper to a second
  vector (`[ebp-0x48]`); `fcn_0365f4b8` at `0x03660985` sorts that copy by rating,
  lowest first. It is the list step 4 takes "more positions" from. **So the goalkeeper
  is never one of them**, and a club with 25 players or more gets no position at all
  unless a place of its eleven is empty.
- `0x0366085c`-`0x03660961`: the loop that writes the positions without a player into
  the first empty slots (run in the emulator on made-up frames, `sider/test_need.py`).
  A plan of kind 3 gets age 23 as the highest age of such a slot.
- Frame: `[ebp-0x50]` career data, `[ebp-0x4c]` the number of the club's plan record,
  `[ebp-0x20]` the record (reused as a pointer into the copy after `0x03660a04`). Both
  vectors are freed from `0x03660b93` on; `MLTransfers.lua` version 6 puts its call
  there.
- Spare bytes of the plan record: `+0x109` to `+0x10b` are 0 in all records of the
  four saves of `ML saves/`, and none of the 34 functions that use `0xccb80c` or
  `0xccb810` touches them (`plan_setup` and `ai_fill_slots` work on record `+ 4`, so
  their `+0x108` is the wait counter). `MLTransfers.lua` version 6 keeps a position
  + 1 and a rating in the first two.

### 9.4 The overall window by club level (proven)

| level | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| lowest overall looked for (`ai_min_overall`, `fcn_0365d12d`) | 47 | 51 | 55 | 59 | 63 | 67 | 70 | 73 | 76 | 83 |
| highest overall looked for (`ai_max_overall`, `fcn_0365d08d`) | 74 | 75 | 76 | 77 | 78 | 79 | 80 | 83 | 86 | 99 |

`tools/clubai.py`. The overall is the game's rating for the player's own position
(`overall`, kind 2). That the byte is a club level and where it comes from is read,
not proven.

### 9.5 The pool of players (`ai_pool`, `fcn_03661380`)

All players of the career are sorted into two sets of 60 lists, one list per
overall from 99 down to 40. A player enters only if

- he is not older than 36 (field `0x2b`; the test is made only for players whose id
  matches the pair at `+0xe4a528`, which is not understood further), and his status
  (`+0xb4` bits 0-3) is not 6;
- `fcn_03888145` allows him: status 0, 1 or 2; bit 31 of `+0xb4` clear; not on loan
  (bit 28 of `+0xb8`); his club keeps more than 16 players without the bit-31 ones;
  he is in none of the 70 deal records of the user (`+0xd06438`); he is in no other
  deal (bits 4-5 of `+0xb4`);
- **he does not play for the club fetched with `fcn_0381e2eb(…, 0x2100cc4)`, taken
  to be the user's club**: computer clubs do not pick the user's players on this
  way (offers for them go through the deal records of section 7);
- he has no club, or **his club's wait counter is 0 and it counts more than 23
  players** (disassembly at `0x0366176f`).

The overall used for sorting is lowered by 7 for a player who carries mark 29 or 30
(a listed player comes within reach of weaker clubs) and kept inside 40 to 99.

- **Set B**: players with status 1 or 2 (**taken to be players without a contract**;
  see the deal types in 9.7), and players whose overall is above the highest overall
  of their own club's level + 3 (never the case at a club of level 9).
- **Set A**: all the others.

Set B is searched first (9.6), so players who are too good for their club and
players of status 1 or 2 are offered before the rest.

### 9.6 Choosing (`ai_fill_slots`, `ai_candidates`, `ai_pick_candidate`)

`ai_fill_slots` (`fcn_03661b15`) goes through the slots of a club while squad +
open slots (states 1, 9, 10) is below **32** (`fcn_03889502`). For an empty slot
with a position it asks `ai_pick_candidate` (`fcn_03660c52`) with the window of 9.4
for the club's level; **if nobody is found and the slot asks for no status band**
(the low half of the slot word `+0xc` is 0), it asks again with the lowest overall 0
(the search then goes from 99 down to 41), ages 0 to 99 and no band. A slot that asks
for a band and finds nobody stays empty: there is no second search for it. A found
player is written into the slot with state 1 and "buy". (Corrected: an earlier text
said "no age limit was set"; the test at the second call is on the band.)

What asks for a band, from the plan function (`fcn_036602e5`, read, not run): a slot
of kind 1 gets band 6 on the last day of a window (31 January, 31 August), once per
club; a slot of another kind on that day becomes kind 1 with band 6 if the record's
`+0x114` is above 7 and a random test passes. Kind 2 sets the highest age 20, kind 3
sets 23. For the search a kind other than 0 is 4 with a chance of 50 in 100.

`ai_candidates` (`fcn_0365f5c2`) walks the lists from the highest allowed overall
down and takes **the first three** players who pass: not on loan, not of the two
clubs shut out for this search, not of the buying club, not in a deal, age inside
the two limits, position fits the slot (`fcn_0365d293`: the player's registered
position, or a position he can play), not already in a slot, and the two tests
`fcn_0388bce3` (by the leagues of the two clubs and the player's nationality:
taken to be the foreign-player rules; not read through) and `fcn_0388f107`. Set B
is searched first, then set A; clubs of kind 1 or 4 search only set A.

Four details, from the disassembly:

- The walk goes from the list of the highest overall down to the list **one above
  the lowest**; the list of the lowest overall itself is not searched (loop from
  `99 - highest` while below `99 - lowest`, `0x0365f643` and `0x0365fb69`). A level-0
  club so looks at 74 down to 48, and the second search at 99 down to 41. **Run in the
  emulator**: the whole function, entered through its two calls in
  `ai_pick_candidate`, with made-up lists (`sider/test_money.py`).
- In set A only (`0x0365f89e`-`0x0365f8ef`), with the status band of the player from
  `fcn_0385400e`: the band must not be below the number the slot asks for; if the
  slot asks for 7 or more, a player with a club must show 2 or more in `fcn_0364c9f7`
  (taken to be his years at the club); and **if the slot asks for nothing (0), a player with a
  club who has band 6 or more is left out unless he carries mark 29 or 30**. The
  second search always asks for 0, so it does not take the stars of other clubs from
  set A. Set B has none of these tests: players without a club, and players more
  than 3 points above their club's window, can be taken by any club in the second
  search.
- Goalkeepers only (`0x0365f920`-`0x0365fa4b`): if the slot's position is 0 and the
  player has a club, the function walks that club's squad (the club record from
  `fcn_03822969`; id pairs at `+0xf8`, count in bits 9-15 of `+0x328`) and counts the
  players whose registered position (`fcn_03117d0f`) is 0 and who are not in a deal
  (`+0xb4`, bits 4 and 5 clear). The player is skipped unless the count is **3 or
  more**: a club never gives up one of its last two goalkeepers. It is the only test
  that looks at the size of the selling club's squad by position; there is none for
  outfield players. (`sider/MLTransfers.lua` version 9 adds one for all four groups,
  `SQUAD_PRESSURE`.) Read from the disassembly, not run alone.
- No test reads a fee, a salary or a budget.

`ai_pick_candidate` puts the up to three candidates into a random order
(`fcn_0364d22e`, a shuffle with `rand`) and takes, in this order:

1. a player with mark 29 or 30;
2. a player with status 2;
3. a player with a mark for whom `fcn_0388cf3d` is true (never reached: 1 takes every
   marked player);
4. a player with status 1;
5. any other who has no club or whose club still has more than 23 counted players
   (the pool's count at `+0x7ac`, lowered with every player chosen), if
   - the list came from set B, or
   - the buying club is of level 9 and the slot asks for a band, or
   - the slot is of kind 1 and the buying club of level 8 or 9, or
   - the slot is of kind 4 and the player's band is below the buying club's level, or
   - the player's band is below 7 and the level of his club is below 8
     (`fcn_0365d775`: the level of his club; 0 without a club; 1 for status 2, 5 for
     status 1).

**If none of the three passes, nobody is taken** (the "no player" id of `0x24feb04`),
even when the lists hold more players further down: `ai_candidates` stopped at three.
So an ordinary player of a club of the first 20 (level 8 or 9) leaves on this way only
if he is listed, or to a slot of kind 1 or 4. Read in the decompiled code, not run.

The chosen player gets bit 5 of `+0xb4` ("in a deal", `fcn_0365d1cd`) and his club's
count goes down by one.

### 9.7 Closing (`ai_close_slots`, `ai_close_deal`)

`ai_close_slots` (`fcn_0365d9ca`) is skipped on the stored date `+0xdcb68c`. Called
with 0 (ordinary window days) it handles only the clubs whose wait counter is 0;
called with 1 (first day of a window) all clubs, but only the states 1 and 10. Per
slot, by its state:

| state | what happens |
|---|---|
| 1, 10 | `fcn_0365d3a3` gives the slot up (state 7) if the player's status became 3 or 4, if the squad would pass 31, or if the player is now in one of the user's deals (`fcn_03662383`, `fcn_03120625`). Otherwise the deal is closed if `fcn_0385a08a` is true (**taken to be: a transfer window is open**) |
| 9 | becomes 10; then as above, and closed at once on the last day of a window (31 January, 31 August; `fcn_0388c35c`) |
| 7 | the slot is emptied and the player's "in a deal" bits are cleared |

`ai_close_deal` (`fcn_0365d4a9`) sets the deal type and calls `complete_transfer`
(`fcn_0389840a(player, new club, &type)`):

| type | when | meaning |
|---|---|---|
| 2 | slot says 2 | loan (inferred) |
| 5 | player status 2 | signing of a player without a club (inferred) |
| 6 | player status 1 | the same for status 1 (inferred) |
| 11 | player status 4 | ? |
| 1 | else | transfer. The marks 29 and 30 of all players of the **selling** club are cleared if the player himself carried none |

Then the slot is emptied.

`complete_transfer` sends the news and messages when the user's club or one of the
user's deal records is touched, and hands the move to one of five functions; a move
between two computer clubs goes to `do_transfer` (`fcn_038913b5`, 745 lines, read in
part):

- **Fee, salary and years** come from the user's deal record if one exists for the
  player (`+0x28`, `+0x2c`, `+0x14` bits 8-11). Otherwise fee = `transfer_fee`
  (section 6.2, with its random change), salary = `salary` for the new club
  (section 6.1), years = `fcn_0388a1be` (section 7.3), at least 1.
- The player's years at the club (`+0xb4` bits 6-10) and his marks are cleared and
  the day is stored at `+0xdc`.
- By the kind of move (four cases): 1 transfer: out of the old squad
  (`fcn_03889d7e`), into the new one (`fcn_03889b6b`), team id `+0xd0`, salary
  `+0xcc`; 2 loan: the same and **bit 28 of `+0xb8` is set**; 4: bit 28 is cleared
  (return from a loan); 3: the player goes to the club id at `0x2521194` (taken to
  be "no club").
- `fcn_03889e24` is called around the move with the two clubs and the amounts. Read
  from the decompiled C: it books money only when the buying or the selling club is
  the club that `fcn_0381e2eb` returns for a fixed key (**taken to be the user's
  club**). Then `fcn_038aab52` writes one line (player id, amount with the sign of the
  side, kind) into a list of 100 lines of `0x28` bytes through `fcn_038a9c7a`. For a
  move between two computer clubs nothing is booked. No account, budget or balance of
  a computer club has turned up in any of the code read so far (the mode data was not
  searched for one): the one account known is the user's (`+0xdddfc4`, 6.4). `fcn_03888c69` works on a dated record of the player and was
  not read further.
- So, as far as read, **a computer club has no money**. Nothing in the choosing code of 9.5 and 9.6
  looks at a price: the choice goes by overall, level, age, position and squad size
  only, and the fee computed in `do_transfer` is paid by nobody and received by
  nobody unless the user's club is one of the two.

### 9.8 Other steps that end in `complete_transfer`

- `user_deal_step` (`fcn_0366365b`, 769 lines, day end, window days; 70 records of
  `0x1dc` bytes at `+0xd06438`, 11 states): read up to line 230. It sends messages
  to the user, so it is taken to work the user's deal list (offers for the user's
  players included). At the deadline of a deal: fail with 4 in 5 if the player's
  value at `+0xb4` bits 23-29 is below 30; fail if `fcn_0388cca1` < a draw from 0
  to 99; else success if a draw from 0 to 99 is below
  `{10, 30, 100}[class] + (5 − years at the club) × 10` (class from
  `fcn_038b1433`). On success the salary is the larger of the `salary` formula and
  the record's figure. The rest is not read.
- `fcn_036e2d84` → `fcn_036e2557` (320 lines; event 8; salary, `complete_transfer`)
  and `fcn_036e067a` (232 lines; events 5, 13, 15): not read.
- `move_players` (`fcn_0389734b`, 466 lines) is the only function found that writes
  the squad count of a team record together with the squad list. It has two callers:
  the day end (event 8, team 4971) and `fcn_0387585e`.

### 9.9 What this means in play

- A computer club has no account that was found (9.7). It shops by **level**, not by money: a level-9 club looks at overall
  83 to 99, a level-0 club at 47 to 74 (9.4). `sider/MLTransfers.lua` adds a
  highest value per level, which gives way for a club in need (9.10).
- It takes **the best three that fit** and prefers listed players and players
  without a club among them (9.6). In one window read from two saves 506 of 511
  signings were players without a contract (9.11).
- A player leaves a computer club on this way only if that club counts more than 23
  players; those more than 3 points above the top of their club's window are looked
  at first (9.5).
- Deals are chosen at the start of the season and on the day after each window, and
  close when the next window is open (9.2, 9.7). Squads end between 23 and 32.

### 9.10 A price ceiling by a module (`sider/MLTransfers.lua`; in `sider/MLMoney.lua` in versions 5 and 6)

The ceiling was written by `MLMoney.lua` in its versions 5 and 6. Since version 7 of
`MLMoney.lua` it is written by `MLTransfers.lua` (version 1), with the same bytes at the
same addresses as version 6; "version 6" below is that state. `MLTransfers.lua` runs
after `MLMoney.lua` and uses its value routine.

The module adds one test to `ai_candidates`, at `0x0365fb0d`, where a player who
passed everything is added to the list (`mov ecx, [ebp + 0x24]; push esi; call
0x041293c0`; only the jump at `0x0365fb02` leads there). The nine bytes become a call
to a routine in unused memory (version 6: `0x047d3c84`, at the end of section
`.xcode`; version 5: `0x047b0162`), which

1. takes the player record from the function's local `[ebp - 0x28]` (written at
   `0x0365f6e3`, read again at `0x0365fa51`);
2. looks at the return address of `ai_candidates`. Only if it is `0x03660d58` or
   `0x03660db9` (its two calls in `ai_pick_candidate`; no other call was found) it
   reads from that function's frame the club level (`[[ebp + 0x1c]]`, the number
   `ai_fill_slots` took from the club's ranking record, byte `+0xe`) and the byte
   `[ebp + 0x1b]`, which `ai_pick_candidate` sets to 1 when the lowest overall handed
   in is 0: the second search;
3. fetches the rating as the fee function does (`0x03853b42(record, &13, 2)`) and the
   value from the module's value routine;
4. in the second search refuses a rating above the top of the level's window (9.4);
5. refuses a value above the ceiling of the level (version 5), or above the club's
   limit for this player (version 6, below);
6. goes on to `0x041293c0` (taken) or drops its return address and jumps to
   `0x0365fb28`, where the game's own failed tests go (refused).

With a level outside 0 to 9 or another return address the player is taken as in the
game. Settings: `CEILING` (ten amounts by ranking group) and `CEILING_RATING` (step
4). **Run in the emulator**: `ai_candidates` whole, with and without the change,
against `money_cave.candidates`. **Not run**: `ai_pick_candidate`, `ai_fill_slots`
and everything above them, so that the level and the search byte are where step 2
reads them rests on the disassembly of `ai_pick_candidate` (`0x03660c83`-`0x03660caa`,
`0x03660d27`, `0x03660d88`) and on `ai_max_overall` reading the same argument at
`0x03660c88`. Not known: how often the first search finds nobody, and what the
ceiling does to squad sizes over seasons.

**Version 6.** Version 5, played by hand, gave fewer transfers than the game alone.
The cause was not found. Step 5 now compares a price with a limit, both made in the
routine (whole numbers, each division drops the remainder):

```
limit = ceiling of the level
in need:  limit = limit * (100 + CEILING_NEED) / 100
h     = ((player id, 16 bits) ^ (player id, 32 bits) * 0x01000193 ^ club id * 0x9e3779b1) * 0x85ebca6b >> 24
limit = limit + limit * (h * CEILING_STRETCH) / 25600
price = value * CEILING_FREE / 100      status 1 or 2
        value * CEILING_LISTED / 100    else, with mark 29 or 30
        value                           else
refused if price > limit
```

"In need" is the second search (the byte of step 2) or a slot that asks for a status
band (`[[ebp + 0x30]]` of `ai_candidates`, its last argument). The buying club is the
first number of the plan record (`[[ebp + 0x18]]`). `h` is 0 to 255 and fixed for a
player and a club, so the answer does not change from day to day and differs between
two clubs of one level. Defaults: stretch 50, need 30, listed 70, free 50; with 0, 0,
100, 100 the routine decides as version 5. Step 4 is not moved by any of this.
**Run in the emulator**: `ai_candidates` whole and `ai_pick_candidate` from its first
instruction to the end of its two searches (`0x03660dce`), against
`money_cave.candidates`. **Not run**: the choice among the three (9.6) and everything
above.

One thing the reading of 9.6 says about the lost transfers, not measured: when none
of the three candidates can leave his club, the game's second search starts at 99 and
meets other players; with step 4 it starts at the top of the club's own window again
and can meet the same three. `CEILING_RATING = false` switches step 4 off for every club; a persona with `rating = false` switches it off for itself (Galactico and Retirement team).

The module books no money. A computer club still has no account (9.7).

### 9.11 One window read from two saves, and version 2 of `sider/MLTransfers.lua`

Level: the counts are **read from two save files** of one career (Athletic Club, first
season, 1 July and 15 September 2024, `MLMoney.lua` 7 and `MLTransfers.lua` 1 in use;
`ML saves/`). The player records were compared in the unpacked mode data; the fields
are those of 13.

| | |
|---|---|
| signings by the 498 computer clubs | 511 |
| of them players without a contract | 506 |
| of them from another club | 5 |
| players with mark 29 or 30 before / after | 816 / 1,548 |
| marked players who moved | 0 |

(Two of the 511 and of the 5 were bought from the user's club.)

So nearly every signing is a free agent and the lists of 9.3 grow without being used.
The reading of 9.5 and 9.6 gives two causes; neither is the price ceiling:

- `ai_pick_candidate` searches the set of players without a contract and of players
  who outgrew their club first, and the other set only if the first gave nobody. After
  the end of the contracts the first set is never empty.
- For a player of the other set `ai_pick_candidate` asks after `ai_candidates` has
  listed three whether he may go: the buyer's level is 9 and the slot asks for a band,
  or the plan's kind is 1 and the level at least 8, or the kind is 4 and the level above
  the player's band, or his band is below 7 and his club's level below 8. If none of
  the three may go, nobody is signed for the slot.

Version 2 of `MLTransfers.lua` works at the same place as 9.10 (`0x0365fb0d`) with a
longer routine (1,413 bytes at `0x047d49d0`, tables from `0x047d4200`, in the unused
rest of the page of section `.data1`). Before the ceiling it

1. asks the question above, and the pool's count of more than 23, before the player is
   listed (`SELL_SIDE`), and lets the selling club keep a share of its players;
2. lets the buying club know only a share of the players (`SCOUTING`);
3. gives each club a persona (`PERSONA`): a draw from position, club and date says in
   which of three places it looks for that position on that day (no contract, marked
   29 or 30, other players of clubs) or that it does not buy; the second search looks
   in the next place; ages; a rating seen with an error; a lowest and a highest rating
   against the rating of its first eleven, which is worked out from the points of its
   ranking record (mean of the best eleven of the 499 ranked clubs of the save ≈
   0.0533 x points + 9.45);
4. before all of these, refuses a player with a contract whose club id and the buyer's
   club id are one of up to 64 pairs (`RIVALS`).

The persona is named per club id or drawn by level. All it needs beyond 9.10 is read
from the frame of `ai_candidates` (date `[ebp - 0x24]`, pool `[ebp - 0xc]`, mode data
`[ebp - 8]`, position `[ebp + 0x14]`) and with the game's own functions for a player's
club (`fcn_0382b087`), his band (`fcn_0385400e`) and the ranking record
(`fcn_031b1c34`, which returns the first record for a club that is not ranked). The
steps and every address are written out at the top of `sider/money_cave.py`;
`sider/README.md` has the settings.

**Run in the emulator** as in 9.10, against `money_cave.accepts`, and **in the game**:
a second pair of saves (`ML saves/2nd test/`, a new career with SSC Napoli, 1 July and
after the window, `MLMoney.lua` 7 and `MLTransfers.lua` 2 with the settings of the
file). `python3 sider/window_report.py <exe> <before> <after>` reads a pair; the
numbers below are its output for the two pairs. Computer clubs only; what they took
from the user's club is counted apart (2 and 4 players).

| | version 1 | version 2 |
|---|---|---|
| signings by the 498 computer clubs | 509 | 430 |
| players without a contract | 506 | 176 |
| listed (mark 29 or 30) | 0 | 40 |
| other players of clubs | 3 | 214 |
| clubs that signed / clubs that sold | 230 / 3 | 221 / 172 |
| marked players before / after | 816 / 1,548 | 816 / 1,288 |
| mean age / mean rating of the signed | 30.1 / 75.2 | 27.3 / 71.4 |
| rating minus the rating of the buyer's eleven, mean | +3.9 | +0.3 |
| the 19 or 20 players without a contract of 80 and more: signed by a computer club | 14 | 2 |
| signings by the first twenty clubs | 8 | 5 |
| clubs with fewer than 23 players before / after | 49 / 25 | 49 / 26 |

That the routine decided the second window is seen in the steps that need nothing but
the two clubs and the player. "By chance" is the number a club that does not look
would pass; the first window, played without these steps, is the control.

| step | version 2: passed | by chance | version 1 (control) |
|---|---|---|---|
| scouting, players without a contract | 176 of 176 | 75 | 241 of 506 (chance 248) |
| scouting, other players of clubs | 203 of 214 | 119 | |
| the seller keeps, signed in July | 95 of 98 | 75 | |
| prestige (rating not above eleven + `prestige`) | 430 of 430 | | 195 of 509 |
| price under the ceiling, club in need | 428 of 430 | | 381 of 509 |
| age outside the range | 42, all 42 at clubs under 23 players | | 234, 49 of them |
| a pair of `RIVALS` | 0 of 254 | 0 to 1 | |

16 of the 430 (4 %) fail scouting or the seller's share; all 16 had a contract and were
not marked on 1 July. The saves do not say why. Two readings fit: 724 players were
marked during the window and a marked player skips both steps; or the choosing code was
entered from a caller other than `ai_pick_candidate`, which the routine lets pass.
The last signing is dated 30 August, so the memory at `0x047d4200` held through the
window.

What the second window also shows:

- **Squads of 32.** 99 of the 498 computer clubs, 15 of the 19 among the first twenty,
  start with 32 players, the most a club holds. Such a club signed nobody in the first
  window (0 signings, 2 players lost). In the second these 99 clubs lost 88 players
  and signed 4. This is the database, not the routine.
- **No player of 85 or more moved** in either window. Of the 130 players of 84 and
  more on 1 July, 111 are at clubs of level 8 or 9, which the rule of 9.11 above does
  not let sell, 3 have no contract.
- **The best players without a contract stay without a club.** For a player of 84, 49
  clubs pass `prestige`, 35 of them the price, 24 of those know him, 12 of those have
  fewer than 32 players, 7 of those pass the age step; then come the draw of the place
  and the slots of the plan.
- 185 of the 254 moves between computer clubs go to a club lower in the ranking, 69 to
  a higher one; 25 sellers are of level 8 or 9.
- The 816 players marked on 1 July are weak (none above 74, 658 below 65), so only the
  lowest clubs take them: 31 of the 40 went to clubs of level 0.
- Donyell Malen went from AS Roma to FC Bayern München in both windows.

Not established: the winter signings; what the fees were (the saves were not read for
money); a second season.

**Version 3 of `MLTransfers.lua`** (emulator only, not played). Same place, routine of
1,520 bytes at `0x047d49d0`, five numbers at `0x047d4fec`; it now uses the page up to
`0x047d4fff`. Three additions, made because of the window above:

- Of the 254 players sold, 131 were among the best eleven of their club (42 more among
  places 12 to 18): the selling club kept every player with the same chance. Now
  `keeps` rises by 12 percent for each rating point a player stands above "eleven of
  his club minus 4", unless the buyer's eleven is 2 or more points better
  (`KEEP_BEST`). The rating of both elevens is worked out from the ranking points as
  before. On the save of 1 July the model lets a club part with 25 percent of its best
  eleven instead of 71.
- A player rated 80 or more skips the scouting step (`KNOWN_FROM`): for the 19 best
  players without a contract the clubs that pass every step that does not hang on a
  slot rise from 7.4 to 19.7 on average.
- The two ages of a persona are moved by -2 to +2 years, by a draw from the club's id
  (`AGE_SHIFT`).

Two personas were added and some numbers changed; `sider/README.md` lists them. Whether
a played window comes out as the model says is not known.

**Version 4 of `MLTransfers.lua`** (emulator only, not played). Routine of 1,555 bytes
at `0x047d49d0`, seven numbers at `0x047d4fe4`; one byte of the page is left. Two
additions to the routine:

- A player whose popularity (the 12 bits from bit 11 of `+0xb4`) is 700 or more skips
  the scouting step as well (`KNOWN_FAME`). In the save of 1 July the popularity runs
  from 0 to 1,110, the median is 250, and 395 players have 700 or more; 109 of them are
  rated under 80 and all of those have a club.
- For a player without a contract `strict` of the buyer's persona counts 50 percent
  (`STRICT_FREE`): he is refused for his age if 100 x the draw is below `strict` x 50.

`keeps` of the personas Galactico, State-backed and Old-money is 50 (was 70, 70, 60).
`sider/README.md` has what the model gives for these and why two other suggestions
were not taken.
