# Club accounts and player prices

[Master League guide](../MASTER_LEAGUE.md) · Section numbers are the original research citations. Paths in the notes are relative to `pes database/exe` unless a command changes directory.

## 6 Money: salary, fee, wage bill

Amounts are whole numbers; the largest is **99,999,900** (`0x5f5e09c`).
`money_text` (`fcn_03869870`) prints a 64-bit amount with thousands separators and no
scaling.

**The screens show 100 times the stored amount.** Not found in the code; taken from one
player of the user's career (Manchester United, Bruno Fernandes, rating 89): the screens
show a salary of 7,259,700 and a value of 36,743,200. With the salary 72,597 the fee
formula of 6.2 gives 367,432 for `x` = 955, and for no other rating from 60 to 99 is
there an `x` that gives it (`sider/test_money.py`, ok 5). So the value on the screen is
the fee of 6.2 without the random change, times 100. All four amounts the user read
(the two above, a transfer budget of 48,013,700 and a salary budget of 12,373,500) end
in 00. One player; the formula has no age term, and a player of 31 or 32 showed none.

### 6.1 Salary: `salary` = `fcn_038ac66e(player, club, …)`

Level: **proven** (check 7) for the formula below; the award and title bonuses are
**read**.

```
o  = overall rating of the player (best position, with condition)
x  = the 12-bit number of the player record (+0xb4, bits 11-22): popularity, see 6.5

A  = 30*o - 500
B  = 300*max(0, o-65) + 500*max(0, o-75) + 700*max(0, o-85)
X  = x
     + 2*(5*x - 4000)   if x > 800
     + 4*(5*x - 9000)   if x > 1800
R  = role bonus (below)
f  = 1 + 0.004*(251 - rank)   if rank <= 250, else 1
T  = (0, 0, 0, 1000, 3000, 5000, 10000, 15000)[band];  if T > 0: T += 20 * field 0x20
salary = trunc((R + X + B + A) * f) + T + awards        limited to 1 … 99,999,900
```

- `rank` is the place of the club in the mode's club ranking (`fcn_03138333`); 300 if
  the club is not in it. So the first club of the ranking pays twice what a club
  below place 250 pays for the same player.
- `R`, by the role byte (`+0xc4`) and the role level (1 to 3): roles 5, 6, 8 →
  1,000 / 2,000 / 3,000; roles 7, 9, 14 → 5,000 / 7,500 / 10,000; role 18 → 3,000;
  role 19 → 15,000; other roles → 0.
- `band` comes from `fcn_0385400e` (29 callers): field `0x2e` of the player, at most
  7; when that is 6 or 7 the band is counted from the rating against the steps 50,
  55, 60, 70, 80, 85, 88. Read; the exact count is not settled. In the proof the band
  was a free input from 0 to 7.
- `awards` (skipped for status 6): +10,000, +5,000, +5,000, +5,000 if the player holds
  one of four awards (`fcn_0318c209(0 … 3)` gives the holder's record, the ids are
  compared by `fcn_02bddabe`); this part **runs in the emulator** in
  `sider/test_money.py` with made-up holders. And +2,000 for each entry of his in the
  lists of finished competitions (`fcn_035e5fa7`): read, not run.
- Clubs whose league number (`fcn_03879e04`) is 60, 61 or 62, and in mode number 40
  players with status 3 (or status 2 and a certain mark) who have an entry number at
  `+0xbc`, use another formula, `fcn_038ab5ea`:
  `700*(o-70)` above rating 71,
  `(x-150) * club factor` above x = 500 (factor from `fcn_038aaad2`, table
  `0x0216b8f8` of 42 clubs with a tier 1 to 5), `10*o`, a ranking factor
  `1 + 0.01*(101 - rank)` up to place 100, and a band bonus
  (0, 0, 1,000, 2,000, 3,000, 5,000, 10,000, 20,000). Read, not run.

Worked example (rank 1, no role, band 0): rating 80, x = 0 →
`A = 1900`, `B = 4500 + 2500 = 7000`, `f = 2.0` → **17,800**. Rating 90, x = 2,000 →
`A = 2200`, `B = 7500 + 7500 + 3500 = 18,500`, `X = 2000 + 12,000 + 4,000 = 18,000`,
→ `38,700 * 2` = **77,400**.

### 6.2 Transfer fee: `transfer_fee` = `fcn_038ab832(player, &figure, &kind, &random, &flag)`

Level: **proven** (check 8).

```
base   = the figure handed in, or the player's salary (+0xcc) if it is 0
factor = 2.2 + 0.00027 * x
fee    = trunc(base * factor) + 9000 * max(0, o - 68)
if kind != 0 and the player's "own" bit is clear:  fee = base
if random:
    kind 1:  p = -rand(50)          # down by up to 49 %
    kind 2:  p = +rand(50)          # up by up to 49 %
    else:    p = +rand(20) or -rand(20), sign from rand(2)
    if p == 0: p = 1
    fee += trunc(fee * p / 100)
limited to 1 … 99,999,900
```

So the fee is the **salary times 2.2 to 3.3** (by `x`) plus **9,000 for every rating
point above 68**. With the two examples above: 17,800 → `39,160 + 108,000` =
**147,160**; 77,400 with x = 2,000 → `77,400 * 2.74 + 198,000` = **410,076**.
What `kind` stands for (values 0 to 3) is not established.

### 6.3 Wage bill: `wage_bill` = `fcn_038ad7a8(club, recompute)`

Level: **read**. Sum of the salaries (`+0xcc`) of the squad, leaving out players with
the "own" bit. For one club (the id comes from a setting; taken to be the user's
club) the players of deal records in state 13 are added.
With `recompute` the salary formula is run for each player instead of the stored
figure. 8 callers, among them the money step and the closing of the accounts.

### 6.4 Club money

Level: `budgets_from_squad` **run in the emulator** (`sider/test_money.py`, ok 0: 40
squads of 0 to 40 players); `season_income`, the amount by rank and the piece of
`club_money_setup` that makes `M` **run in the emulator** (the same test, with the
popularity, the ranking record and the wage bill made up); the rest of the three
functions below **read** (C and disassembly, not run). The names of the amounts are inferred. The rest **located**: `fcn_03640d19` (money step, events 3,
23, 25, 49; 1,280 lines), `fcn_03649f1f` (616 lines, event 24),
`process::ProcessCmnFinanceReportCheck` (`fcn_035e69ce`, event 25) and about twenty
small functions at `0x038aa000`-`0x038ab400` that add and read account lines. The
account of the user's club is at mode data `+0xdddfc4`. Prize money and the yearly
budget step are in 6.7; what the screens call each amount is **not read**.

- `club_money_setup` (`fcn_038adf0c(club, &with budgets)`), one caller chain, from
  `fcn_035f445b` in Master League (taken to be the set-up of a new career): balance
  (`+0xdddfe4`) = `M + N/2 + wage bill`, with
  `M = (15,000 + 165,000 * level) * (1 + p/100)`, `p` a random whole number from -10
  to +10, `level` the club's level 0 to 9 (byte `+0xe` of its record in the table at
  `+0xcc84cc`), and `N = season_income`. `M` is also stored at `+0xdddfec`, `N` at
  `+0xdddff0`.
- `season_income` (`fcn_038ade76(club)`) =
  `25 * max(150,000, V) - 670 * min(400, club field +4) - 3,451,330`, or 1,000 if that
  is below 1. `V = club_popularity` (`fcn_03878855`): 10,000 to 140,000 by the club's
  level (10, 15, 20, 25, 35, 50, 65, 80, 110, 140 thousand) plus twice the sum of the
  16 highest `x` of the squad. With `V` at least 150,000 and the field at most 400 the
  amount is never below 30,670, so the 1,000 is not reached. The function also calls
  `wage_bill` for the club, before `club_popularity` (`0x038adea5`), and does not use
  the result. `sider/MLMoney.lua` keeps that result and adds a share of it (6.6).
- `budgets_from_squad` (`fcn_038ad9c4(club)`), called by the set-up and in event 24 at
  what is taken to be a change of club: the fee of 6.2 (no random change) is computed
  for every player of the squad. **Transfer budget** (`+0xdddfc4`) += 2 x (sum of the
  16 highest fees / 16); **salary budget** (`+0xdddfdc`) += wage bill + 2 x (sum of the
  16 highest salaries / 16). So both budgets follow the values and salaries of the
  squad: a change of the fee or salary formula scales them in a new career.
  The two factors are in the code, not in data: `add esi, esi` at `0x038adc47` for the
  transfer budget and `lea esi, [ecx + eax*2]` at `0x038add08` for the salary budget
  (`ecx` = wage bill). A sum of 0 counts as 10,000; each amount added is kept within
  -99,999,999 to 99,999,999. The squad is the list of 8-byte player ids at `+0xf8` of
  the club record, its length the 7 bits at `+0x328`, bit 9. Worked from the squads of
  the edit file in this repository, with club part 300 for every club, on the screen's
  scale: Manchester United about 39 million transfer budget with the game's formulas,
  Real Madrid about 52, Burnley about 19. With the default tables of
  `sider/MLMoney.lua` (factor 3): about 107, 232 and 19 million. The user saw 70 million
  for Manchester United in a new career; whether a module was running then is not
  known.
- First day of a season (money step, event 3): `+0xdddfec` =
  `(403 - club rank) * 5,000`, at least 1,000, changed by -10 to +10 percent; `+0xdddff0`
  = `season_income`, changed the same way; three amounts of another record are added to
  the balance. For the first club of the ranking the first figure is about 2,000,000
  (200 million on the screen). The amount by rank is a function of its own
  (`fcn_038a9e6b`), the multiplication by 5,000 at `0x038a9e9c`.
  Neither amount looks at what the club pays. Worked from the squads of the edit file
  with guessed ranking places (`sider/README.md` has the table): the two amounts
  together are about 280 million for the strongest squads and 130 million for a second
  division club, against wage bills of 90 and 13 million with the game's salary
  formula.

The user's two budget figures (480,137 and 123,735 stored) are odd numbers, so they are
not the fresh results of `budgets_from_squad`; they are of the size it gives (twice
the mean fee, twice the mean salary of the best 16).

### 6.5 Popularity: the number `x`

Level: **read** (disassembly); the name is **inferred**.

`x` (player record `+0xb4`, bits 11-22) is kept between 0 and 3,000. It enters the
salary (6.1), the fee (6.2) and the club's popularity (6.4). It is set by
`popularity_start` (`fcn_0385a329`), which has three callers: `fcn_0366dc05`, a loop
over all players called from `fcn_035f445b` (taken to be the set-up of a new career: it
also sets the club's popularity and calls `club_money_setup`); `fcn_035f7c46`, which
also sets the band and the salary of one player; and `fcn_035e2b9d`.

```
x = club part + max(band part, 10 * (max(o, 50) - 50))
band part = (0, 110, 210, 310, 410, 510, 610, 810)[band]        band: section 6.1
club part = (0, 20, 40, 60, 80, 100, 150, 200, 250, 300)[k]
    k = the club's level 0 to 9 for status 0; 2 for status 2 and 6; 5 for status 1; else 0
```

During the career `fcn_0385944c(player, change)` adds to it (11 callers at
`0x0366dce3`-`0x0366f31e`, not read) and `fcn_035e241f` sets it. Bruno Fernandes had
955 in the user's career.

Age: the player record holds it in 6 bits at `+0x1c`, bits 7-12 (field `0x2b` of the
getter `fcn_038278b0`; the next field is the 5-bit playing style, as in the edit file,
where age is the only 6-bit field). The code tests it against 36, 37 and 45, the getter
is called with `0x2b` at 94 places (the byte pattern of `push 0x2b` followed by the
call), and at `0x038b585f` the setter `fcn_038281b0` writes 16 into it (taken to be a
new youth player).

Other fields of the player record used by `sider/MLMoney.lua`: the registered position,
4 bits at `+0x04`, bits 28-31 (field `0x00` of the same getter; the rating function
`fcn_0383899a` reads it this way and turns the edit file's order, 0 GK to 12 CF, into
the game's with `fcn_0383890b`); the player's id, a word at `+0x2c` and a dword at
`+0x30` (`fcn_0383899a` compares the two with a "no player" id before anything else;
in a list of ids the code compares the word and the dword the same way). The 98
fields of the getter were mapped by running it on records with one bit set.

### 6.6 A Sider module that changes values, salaries, budgets and prize money

Version 5 of the module adds a price ceiling to the transfers of the computer clubs
and version 6 lets it give way; since version 7 that part is a file of its own,
`sider/MLTransfers.lua`. It is described in 9.10.

`sider/MLMoney.lua` (version 7) replaces the rating part of the fee by `VALUE[rating] x
AGE[age] x POSITION[registered position] x (the player's own fixed factor) x (1 +
popularity bonus)`, the rating part of the salary by `SALARY[rating] x SALARY_AGE[age]`,
and the 2 of the two budget sums of 6.4 by settings. Version 3 adds: other amounts in
the cup table and in the two main league lists of 6.7, a share of every prize for the
transfer budget, a setting for the 0.004 of the club factor of 6.1, a factor on the
role, band and award bonuses of 6.1, and the contract limit of 7.3. What it writes and
why is in `sider/money_cave.py`. `sider/test_money.py` runs the game's salary, fee,
budget, prize and contract-limit code with the changes in the emulator and compares it
with the Python of `money_cave.py`, also with every setting at its limit.

Version 4 adds five things. A **talent bonus** on the value: the game keeps no
potential (section 12), so the rating a player has at his age stands for it; a table
gives the ordinary rating by age up to 23 and every point above it adds a percent.
A share of the **wage bill** in the yearly income: `season_income` already calls
`wage_bill`; the module keeps the result in the function's local at `[ebp - 4]`
(changed place `0x038adeaa`) and adds a percent of it at the end (`0x038adeee`). A
percent on the game's yearly amounts (`0x038adeee`, `0x038a9e9c`, and `0x038ae025` in
`club_money_setup`), off by default. **Prize lists by league**: the instruction at
`0x038aa2dd` becomes a call to a routine that compares the league number in `edi`
with up to 12 numbers and takes the amount from that league's list. The six amounts
for **cups without a row** (the immediates of six `mov edi` from `0x038aa43a`), and
television money added to the rows of a cup. The yearly budget step of 6.7 is left
alone: it follows the wage bill and the fees.

Seen in the game (version 2, the user's PC, a new career with Manchester United,
`SPREAD = 0`): Bruno Fernandes, rating 89, AMF, age 32, value 52,973,200, which is the
module's formula at popularity 910 exactly; transfer budget 106,925,700. This also
confirms that `+0xdddfc4` is the transfer budget of the screen. The parts added in
versions 3 and 4 have not run in the game.

### 6.7 Prize money and the yearly budget step

Level: the cup table and `cup_prize` **run in the emulator** (`tools/prize.py <exe>
check`: 330 pairs, none differs; `sider/test_money.py`: competitions 0 to 100, stages
0 to 12); `league_prize` **run in the emulator** for every list, place and half;
`balance_add`, `transfer_budget_add` and the two pieces of `prize_step` that pay a
prize **run in the emulator** on a made-up stack frame (`sider/test_money.py`); the
two pieces of the money step that turn a grade into the grants of 28 and 30 June **run
in the emulator** the same way (2,000 cases each against `money_cave.june_grants`);
the rest of this section **read** (disassembly, not run). Stage names and the names of the
competitions 2 to 8 are **inferred**. Nothing here was seen in a game.

**Who pays.** `prize_step` (`fcn_03640686`, in the day end, section 3) walks the
competitions of the user's club. For a league, on the day the club's place is final,
it calls `league_prize`; for a cup, when `cup_stage` (`fcn_038a9115`) says the club is
out or has won, it calls `cup_prize`. The amount goes to two places: the **balance**
(`+0xdddfe4`, through `fcn_038aadb7`; calls at `0x03640ac5` for leagues and
`0x03640b78` for cups) and one of ten 24-byte competition lines at `+0xdde000`
(competition, stage or place, amount, a "paid" byte at `+0x14`). Neither budget is
touched.

**Cups.** `cup_prize` (`fcn_038aa307(&competition, &stage, &club)`) searches a table
of 12-byte rows (competition, stage, amount) at `0x0216b178`, 73 rows, plain data:

| competition | amounts by stage (stored; the screens show 100 times as much) |
|---|---|
| 2 Champions League, 5 Libertadores, 8, 48 | winner 80,000; runner-up 40,000; semi-final 30,000; quarter-final 20,000; stage 7 10,000; stage 9 5,000 |
| 3 Europa League | 30,000; 20,000; 15,000; 10,000; stage 5 5,000; stage 7 3,000; stage 9 1,000 |
| 6, 91 | 30,000; 20,000; 15,000; 10,000; stage 7 5,000; stage 9 3,000; stage 10 1,000 |
| 4, 7 (super cups of the continents) | winner 35,000; loser 10,000 |
| 1 (Club World Cup) | 40,000; 20,000; 10,000; 5,000 for stages 0 to 3 |
| 73 to 79, 82, 83, 84 (national super cups) | winner 5,000; loser 3,000 |

A cup that is not in the table (the national cups) gets, by stage 0 to 6: 20,000,
10,000, 5,000, 5,000, 1,000, 500, 300 (switch at `0x038aa42b`; the six amounts are the
immediates at `0x038aa43a`, `...446`, `...452`, `...45e`, `...46a`, `...476`, stages 2
and 3 sharing one). Competitions 45, 46,
47, 54, 55, 70, 71, 72, leagues, and stage 11 get nothing. Game mode `0x28` uses a
second table (`0x0216b4e8`, 26 rows). Stages as `cup_stage` gives them: 0 winner, 1
runner-up, 2 third, 3 and 4 the semi-final and quarter-final, 5 and 6 the rounds
before (6 only with more than 32 clubs), 7 the first knock-out round, 8 and 9 the
group stage (9 = not gone on), 10 a league part, 11 still in, 12 not taking part.
So a Champions League win is 8 million on the screen and a group stage exit half a
million.

**Leagues.** `league_prize` (`fcn_038a9ebb(&club, &place, &half)`) writes four lists
to its stack (immediates in the code, not data) and picks one: competition 60, 61,
or by the two top bits of the league record's `+0x218` (2 or 3 = the short list,
taken to be a second division). First list, place 1 to 22: 150,000, 130,000,
100,000, 80,000, 60,000, 50,000, 45,000, 40,000, 35,000, 30,000, 27,000, 24,000,
21,000, 18,000, 15,000, 12,000, 9,000, 7,000, 5,000, 3,000, 3,000, 3,000. Second
list, place 1 to 24: 20,000 down to 250. The third argument is the half: 0 = a whole
season, the full amount; 1 = first half, paid only to the leagues `0x3458` and
`0x27d8`; 2 = second half, only to `0x3459` and `0x27d9`; a half pays half the amount,
any other league gets nothing for a half. The amount is in `eax` at `0x038aa2e4`,
before the halving. The league number comes from `fcn_03879e04(club)` and is kept in
16 bits (`movzx edi, ax` at `0x038aa206`); it is still in `edi` where the list is
read, which is what lets a module pay by league. After `0x038aa2e4` the function
loads `edx` and `ecx` anew before it uses them. `sider/MLMoney.lua` replaces the two instructions that read the
first and the second list (`0x038aa2dd`, `0x038aa2c6`), the three address operands of
the cup table in `cup_prize`, and the two calls of `balance_add` in `prize_step`
(6.6).

**What the budgets get each year** (money step `fcn_03640d19`). The balance and the
prize lines are *not* turned into budget. The step adds to both budgets twice, on
28 June (event 49) and on 30 June (event 23), from the squad and a grade:

```
W = wage bill (fcn_038ad7a8), rank = place of the club in the mode's ranking, kept within 1 to 200

28 June (code from 0x03642bab), k = 0.6
  S = W * g * k                                           added to the salary budget (+0xdddfdc)
  T = (sum of the 10 highest fees) * (W + S) / W / 5 * k   added to the transfer budget (+0xdddfc4)
  g = 0.1 + 0.007 * rank       grade 1
      0.07                     grade 2
      0.07 + 0.00215 * rank    grade 3
      0.05                     grades 4, 5
      0.02                     grade 6

30 June (code from 0x03642011), k = 0.4
  S = W * g * k, then S = S + S * a, then S = S + S * b    (a, b: two fractions, below)
  T = (sum of the 10 highest fees) * (B + S) / B / 5 * k   B = the salary budget before the grant
  g = 0.1 + 0.007 * rank       grade 1
      0.07 + 0.00215 * rank    grade 2
      0                        grades 3, 4
      0.05                     grade 5
      0.02                     grade 6
```

So the two days differ: 28 June sets the transfer grant against the wage bill, 30 June
against the salary budget, and the grades are numbered differently. `(W + S) / W` and
`(B + S) / B` are kept as 32-bit floats; each product is cut to a whole number by
`fcn_038e6c62`, which keeps the low 32 bits if the number is larger. An earlier
version of this section gave one formula for both days, with the salary budget in
both; the disassembly and the emulator run show the above.

On 30 June the grade comes from the year's result (the three incomes, the account
lines with the prize money and the transfers, less the costs; stored at `+0xdddfe8`)
against the figure of the year before: 15 percent more or better = grade 1, 5 percent
= 2, down to minus 5 percent = 5, below = 6. On 28 June it comes from a comparison
of two rankings (`fcn_0387cab5`, `fcn_03138333`) and a draw; that part is not read.
The two fractions of 30 June: `a` is (a number of the step - 59) / 100, `b` is 5
percent for each of a count that the step makes before (an earlier reading took it
to be the players with team role 18, at most 4); neither was followed to its data.
After `T`, the 30 June code adds the same two fractions to it and takes two sums
off; those are read as code only. The sum of the 10 highest fees is
`fcn_038acf42(club, 10)`, read from a decompile with gaps and replaced by a made-up
number in the emulator runs.

What follows:

- Prize money counts only through the 30 June grade. Winning the Champions League
  does not put its 8 million into the transfer budget.
- The yearly transfer money follows the fees of the squad, so a module that raises
  the fees (6.6) raises it in the same proportion; the yearly salary money follows
  the wage bill. Nothing in the two grants is a fixed amount of money, which is why
  `sider/MLMoney.lua` does not change this step.
- The factors `0.4`, `0.6`, `5.0` and the grade numbers are shared constants (12 to
  667 references each), except `0.007` and `0.00215` (2 each, this function only).
  A change has to give the instruction its own constant, not change the shared one.
