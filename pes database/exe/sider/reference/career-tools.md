# Transfer reports and Schedule controls

[Sider developer guide](../README.md) · These are versioned implementation notes and test observations. For current settings and deployment, use the guide and shipped Lua files. Paths and commands assume the `sider` directory unless noted.

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
