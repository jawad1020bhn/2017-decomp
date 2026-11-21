# Master League modules for Sider 3.6.0

These Lua modules change the running game, not `PES2017.exe` on disk. For the unmodified game's structures and algorithms, use the [Master League guide](../MASTER_LEAGUE.md). For patch ranges, load-order tests and rollback limits, use the [safety audit](SAFETY_AUDIT.md).

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
| [MLCheck](MLCheck.lua) | Read-only check of the AI rating window and transfer-fee code. Six matches confirm those locations, not the whole executable. | [Build checks and live observations](reference/match-setup.md#result-in-the-game-14-november-2026); `test_module.py` |
| [MLMoney](MLMoney.lua) | Player values, salaries, contract years, budgets, income and prizes. With sufficient funds, tap **F6** in a focused ML game to move 4M of transfer funds into 1M of salary room; **F7** reverses it. Reopen Finance to refresh. | [Formulas, settings and verification](reference/money.md); `money_cave.py`, `money_keys.py`, `test_money.py` |
| [MLYear](MLYear.lua) | A **new** career starts in 2026/27 by default. An existing career keeps its year. | [Year and contract boundaries](reference/match-setup.md#mlyearlua-version-1-a-new-career-starts-in-202627); `test_year.py` |
| [MLTransfers](MLTransfers.lua) | AI recruitment: price ceilings, personas, rivals, squad needs, offers, sporting projects and trimming. Requires the installed Money v7 valuation hook. To assess results, compare saves across a transfer window. | [Recruitment rules and observed windows](reference/transfers.md); `test_transfers.py`, `test_need.py`, `test_offer.py`, `test_projects.py`, `test_trim.py` |
| [MLSimMatch](MLSimMatch.lua) | Skip Match and AI simulation: strength-based results, substitutions, ratings, scorers, extra time, penalties, cards, fatigue and injury. Not the played-match Team Spirit calculation. | [Simulation and tuning](reference/simulation.md); `sim_cave.py`, `test_sim.py` |
| [MLTeamSpirit](MLTeamSpirit.lua) | **v6:** updates form at **played match setup** when exactly one controller-slot-0 record matches either participant. An unrelated marked club no longer blocks it. If ownership is unclear, it keeps the previous value. Check the matchup, form and final 90–99 value in the log. | [Rules, examples and native reader](reference/match-setup.md#mlteamspiritlua-version-6-team-spirit-follows-the-form-of-your-club); `test_spirit.py` |
| [MLSimToDate](MLSimToDate.lua) | Off by default. In **Schedule**, highlight a future day, press **F8**, check the heading, then advance normally. **F9** cancels; **F10** toggles stopping for news. “Switched off” does not mean the hooks were uninstalled. | [Controls, early stops and optional date file](reference/career-tools.md#install-and-use-the-in-game-control); `test_simdate.py`, `test_simdate_calendar.py` |
| [MLGrowth](MLGrowth.lua) | Potential, playtime and age affect development; annual AI changes include position-specific skills and physical decline for contracted veterans. Check a training/award event or season transition, not just startup OVR. | [Original growth mechanics, §12](../reference/players-save.md); `growth_cave.py`, `test_growth.py` |

## Developer workflow

Run from `pes database/exe/sider` with the matching executable. These checks use Lua and CPU emulation; they don't launch PES on Windows.

```sh
python3 -m pip install lupa unicorn capstone keystone-engine
python3 test_spirit.py /path/to/PES2017.exe    # match callbacks and native reader
python3 test_safety.py /path/to/PES2017.exe    # load orders, write overlap and rollback
```

- **Changing a hook:** check the [Sider API and reserved ranges](reference/sider-runtime.md), keep generator output and embedded Lua bytes in sync, run the feature test and then the safety suite. A host API error can interrupt rollback: Sider's sandbox has no `pcall`.
- **Comparing a real window:** [window_transfers.py](window_transfers.py) reads a save and writes a CSV. A `paid` entry uses the user club's recorded payment; a `formula` entry is an estimate, not the actual AI transfer price. See [report instructions and limitations](reference/career-tools.md).
- **Current test boundary:** Spirit v6 passed the match regressions, four club-table replays and the eight-module safety run; the affected Windows career wasn't tested. A separate `test_growth.py` season-growth assertion also failed with the pre-change test. Don't report the whole suite as green or change growth rates to make an unexplained assertion pass.
- **Tracing an earlier result:** the [tool inventory and safety-fix history](reference/setup-history.md) and the module references above preserve the original test descriptions, observations and version-specific behavior.
