# Research leads and reproduction commands

[Master League guide](../MASTER_LEAGUE.md) · Section numbers are the original research citations. Paths in the notes are relative to `pes database/exe` unless a command changes directory.

## 14 Not found, not read

- Fixtures: where the match days get their dates; the creators of kind 3 and 4
  (knock-out rounds, `fcn_0377661c`, `fcn_03775815`); leagues with one or three
  legs in Python; which competitions carry the ids with a fixed table; the order of
  a competition's team list (section 5).
- Computer clubs: what a deal moves in money (`fcn_03889e24`, `fcn_03888c69`) and
  whether a budget limits a club; the years of the contract (`fcn_0388a1be`); the
  two tests `fcn_0388bce3` and `fcn_0388f107`; what tells mark 29 from mark 30;
  where a slot gets "loan" and the state 9; how often the choosing step is repeated
  on its days; the rest of `user_deal_step`, `fcn_036e2557`, `fcn_036e067a`
  (section 9).
- Growth, youth, retirement, new players, contracts (section 12); of team spirit the
  Master League bonuses and the six places of the match AI (12.1).
- What the screens call each amount of the account (sections 6.4, 6.7); the grade of
  28 June and the two sums taken off the yearly transfer money (6.7); `fcn_03649f1f`
  (event 24); where the screens multiply amounts by 100.
- What moves `x` during a career (section 6.5); the meaning of field `0x2e`, of the fee
  formula's `kind`, of the 13 deal states and of `day_state`.
- The other twelve cases of the negotiation step, and the lost fraction arithmetic in
  the one that was read.
- Season end (`fcn_035feb08` and the event-23 block).
- Calls through tables of function pointers are not resolved in `calls.tsv.xz`.
  `output/classes.tsv.xz` (9,814 tables of 6,932 classes) gives the class and
  the slot of each such function, which is enough to follow a call by hand.

## 15 How to go on

```
cd "pes database/exe/tools"
python3 find.py show salary                  # C of a named function
python3 find.py callers 0x038ac66e           # who calls it
python3 x86dis.py <exe> 038ac66e 1940        # disassembly, for the fractions the C drops
python3 rtti.py <exe>                        # class names and their function tables
python3 yearplan.py <exe> july               # the year
python3 fixtures.py 20                       # rounds of a league of 20 teams
python3 -c "import money; print(money.salary(90, 2000, rank=1), money.fee(77400, 90, 2000))"
```

The pattern that worked for the two formulas: read the C, take the arithmetic from
the disassembly, write it in Python, then run the game's code in `emu.py` with the
look-up functions answered (`Game.replace`) and compare. The next candidates, in the
order of what they would explain: `fcn_0385400e` (band), `fcn_038ab5ea`,
`fcn_0388a1be` (years), `fcn_0389b3f8` / `fcn_0389bd94` (willingness),
`fcn_03896290` (fit to the squad), `fcn_0389440a` (squad needs), `fcn_03889e24`
(money of a deal), `fcn_0377661c` (knock-out fixtures), `fcn_038b9827` (growth).

Use the before/after career snapshots in `ML saves/` to compare candidate fields with known players. To confirm a screen label, obtain the matching in-game observation as well.
