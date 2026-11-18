# Sider Lua safety audit and fixes — 17 November 2026

**What this repo does:** The eight Master League Lua modules change PES 2017's running memory. The audit and fixes assume one 32-bit game process using the bundled executable and Sider 3.6.0.

**Status:** The reproducible issues in the available sources have been repaired, and all **12 test suites passed**. PlayerDump, GrowthBridge and Stadiums are unchanged, as requested. The original unexpected close is **not diagnosed** by these tests or the initialization log.

## Changes applied

| Original finding | Current status |
| --- | --- |
| 1. Logged Transfers settings refuse installation | The repository already has valid numeric `Galactico.wealth = 150`. This default installs successfully; added regressions reject an oversized or string-valued first-persona wealth before any transfer patch is applied. Replace/correct the different installed copy; validation was not bypassed. |
| 2. PlayerDump/GrowthBridge use unavailable APIs/events | **Excluded by request.** No source, configuration or DLL changes were made for them. |
| 3. Stadiums cannot open its required map | **Excluded by request.** No map, content or configuration changes were made for it. |
| 4. Growth must follow SimMatch because both write the curve gap | **Fixed in SimMatch v9.** Its ET checks and writes now skip Growth's entire 84-byte reservation. The current pair installs in either order with no cross-module write intersection. |
| 5. Team Spirit decodes already-decoded Sider IDs | **Fixed in Spirit v3.** Callback IDs are used directly. Packed game-memory IDs are decoded once, with the same 16-bit mask as Sider; the invalid user-club sentinel is ignored. |
| 6. Team Spirit reads the day/year with incorrect widths | **Fixed in Spirit v3.** One four-byte read supplies the two u16 fields. Future results do not enter pre-match form, and future-season fixtures do not reset the current league calculation. |
| 7. Team Spirit walks past the last match record | **Fixed in Spirit v3.** The last batch is bounded for matches, clubs and competitions, for both read size and iteration count. |
| 8. Annual Growth award uses the selector as its age margin | **Fixed in Growth v4.** The age margin survives the selector/getter call. Regenerated every affected x86 block, including the season hook's jump into the moved exit sequence. |
| Failed patch writes leave earlier changes installed | Money, Transfers, Year, SimMatch, Growth and Spirit now restore patches already attempted when read-back verification fails, and explicitly report failed restoration. See the host-error limitation below. |
| Stale free-memory notes | Corrected the current reservation map in `README.md` and the generator bounds, including incoming/pressure sizes and Growth's boundary before training-focus code. |

### Team Spirit v3

**Sources:** `MLTeamSpirit.lua:169–174`, `232–277`, `297–335`, `480–545`; `test_spirit.py`.

Before the fix, Sider-style home/away team numbers `7`/`8` were divided by 16,384 a second time. Two losses therefore left the value at **95 rather than 92**. The old tests passed packed career IDs, unlike the real callback. All event fixtures now use decoded team numbers, and the expected form, cup, derby and league bonuses pass at home and away.

The old date reader treated day 305/year 2024 as day **132,645,169**. It now decodes day and year separately and ignores neighboring bytes. Tests cover both 2024 and 2026, a scheduled next-season opening fixture, and a future-dated played result. Current form and the league bonus stay unchanged.

The old final match batch processed 9,024 records instead of 9,000, reading **14,112 bytes past the array**. Tests now put a fake win immediately after that array and prove it is neither read nor included. The last valid match (record 8,999) still works. Club and competition walkers also stop exactly at their counts, including partial final batches.

**Compatibility:** `RIVALS` still accepts packed career club IDs. The log labels a copyable `RIVALS id` separately from the decoded Sider team number. Existing packed rival settings remain effective.

### Growth v4

**Sources:** `growth_cave.py:258–315`, `359–382`, `530–543`; generated blocks in `MLGrowth.lua`; `test_growth.py`.

The annual award previously loaded an age margin into EDX, replaced it with an ability selector, and later used that selector for its headroom comparison/division. The margin is now saved across the getter call. The regenerated award is **147 bytes**, within its **153-byte** reservation; the dependent season-hook branch has also been regenerated.

The original failures are now corrected: CF finishing 80, turning 17, becomes **81**, not 82; finishing 84, turning 23, becomes **85**, not 84. The test compares native annual awards with `season_levels` across **1,456 age/position/ability cases**, including limited headroom and invalid-position fallback. It also assembles every Growth block and compares the resulting bytes with the literal and embedded Lua data.

### SimMatch v9 and shared memory

**Sources:** `MLSimMatch.lua:993–1029`; `sim_cave.py:93–116`, `2389`, `3157–3178`; `test_sim.py`, `test_safety.py`.

The simulator's logical ET image is still 4,030 bytes for code/table generation. Installation now checks and writes only:

- code reservation: `0x047d5040–0x047d5b8b`;
- score tables: `0x047d5be0–0x047d5ffd`.

It does not check or overwrite `0x047d5b8c–0x047d5bdf`, where Growth places its curve. Both Growth-first and simulator-first installations pass. Native-code/table tamper checks outside the gap remain active. Generator limits prevent future simulator code from growing into adjacent Growth allocations.

The integration test installs all eight modules in **22 orders**: two explicit opposite Growth/SimMatch orders and 20 deterministic sampled orders, respecting Check-before-Money and Money-before-Transfers. It captures every write, rejects cross-module intersections, and checks that later modules preserve every previously installed byte.

**Upgrade both files together.** With an older SimMatch v8, SimMatch must still load before Growth. The supplied log used that working order; this dependency was not proof of why that run closed.

### Failed-write recovery

**Sources:** `MLMoney.lua:932–954`, `MLTransfers.lua:1581–1599`, `MLYear.lua:98–114`, `MLSimMatch.lua:1035–1052`, `MLGrowth.lua:169–187`, `MLTeamSpirit.lua:632–642`; `test_safety.py`.

On a read-back mismatch, the patchers restore the failed patch and earlier attempted patches in reverse order. Other modules' changes are left alone. Cave data can remain occupied, but no successfully restored native hook points to it. A full process restart is still required after a failed install.

Transfers additionally checks Money's actual native fee hook. A stale Money cave/marker after rollback is no longer accepted as a completed prerequisite; the regression verifies that Transfers writes nothing after each recoverable Money failure.

Tests inject **102 refused/damaged patch writes** across the six patchers and verify that all original patch bytes are restored. Separate cases refuse restoration itself and verify that each patcher reports `restore failed` rather than falsely claiming recovery. Existing SimToDate tests cover its rollback and READY gate.

**Host-error limitation:** Sider 3.6.0's Lua environment does not expose `pcall`. If `memory.write`/`memory.read` raises a host error, init can stop before Lua performs rollback. The fixes cover verification failures, not an exception-safe transaction or atomic writes across threads. No Sider DLL was modified. Quit PES on any init/write/restore failure; do not keep playing or save.

## Validation

All 12 suites exited **0**, sequentially against the bundled executable:

| Suite | Seconds |
| --- | ---: |
| `test_module.py` | 0.3 |
| `test_safety.py` | 1.3 |
| `test_growth.py` | 3.8 |
| `test_spirit.py` | 3.9 |
| `test_year.py` | 0.8 |
| `test_need.py` | 6.6 |
| `test_offer.py` | 0.5 |
| `test_sim.py` | 57.0 |
| `test_simdate.py` | 19.0 |
| `test_simdate_calendar.py` | 1.5 |
| `test_transfers.py` | 7.4 |
| `test_money.py` | 206.5 |

Before changing production code, the corrected Spirit fixtures and new Growth cases failed against the original code. The new failed-write regression also failed before recovery was implemented, and the chained Money-failure/Transfers regression failed before the prerequisite hook check was added. The final sequential run passed all suites; running multiple large emulator suites concurrently can exceed the sandbox's memory budget, so the release check used one suite at a time.

Run from this folder with Python packages `lupa`, `unicorn`, `capstone`, and `keystone-engine`:

```
python test_safety.py "path/to/PES2017.exe"
python test_spirit.py "path/to/PES2017.exe"
python test_growth.py "path/to/PES2017.exe"
```

The executable and saves are only read by the harness. Executable SHA-256:

```
44b0caaac6703459f1a674ab7defc98d39613008b9254646f2543431fa9d954f
```

## Current memory reservations

Inclusive endpoints; this table lists large injected regions, not the small native patch sites:

| Owner | Range | Bytes |
| --- | --- | ---: |
| Simulator cards | `047b0060–047b01f4` | 405 |
| Money tables/code | `047b0200–047b0fef` | 3,568 |
| Simulator main | `047d3a50–047d3f06` | 1,207 |
| Growth annual award | `047d3f07–047d3f99` | 147 |
| Simulator secondary data | `047d3fa0–047d3fff` | 96 |
| Simulator data | `047d4170–047d41ff` | 144 |
| Transfers main | `047d4200–047d4fff` | 3,584 |
| Simulator ET code reservation | `047d5040–047d5b8b` | 2,892 |
| Growth curve | `047d5b8c–047d5bde` | 83 |
| Simulator score tables | `047d5be0–047d5ffd` | 1,054 |
| Simulator PK/fatigue/injury | `047d6030–047d6376` | 839 |
| Growth experience hook | `047d6377–047d63fa` | 132 |
| Transfers position need | `047d6400–047d654f` | 336 |
| Transfers incoming offers | `047d6550–047d6d3f` | 2,032 |
| Transfers squad pressure | `047d6d40–047d6e4f` | 272 |
| Growth season walk/arithmetic | `047d6e50–047d6efd` | 174 |
| Growth training | `047d6efe–047d6f4b` | 78 |
| Sim-to-Date day loop | `047d6f60–047d6fec` | 141 |
| Sim-to-Date calendar | `03fc8000–03fc88ff` | 2,304 |
| Sim-to-Date state | `0298c0e0–0298c1ff` | 288 |
| Growth tables | `0298c200–0298c2eb` | 236 |

In particular, `047d6d60–047d6e4f` is **not free**; it belongs to transfer squad-pressure code. No unbounded Lua collection or per-frame allocation loop was found in the eight modules. Their injected footprint is fixed, roughly 20 KB, but this is not a Windows memory/leak profile.

## Deployment and remaining uncertainty

1. Back up the actual installed modules, `sider.ini`, and saves. Copy the updated Lua files from this folder into Sider's `modules` folder. Do not copy Python generators/tests there.
2. Keep Check before Money and Money before Transfers. The matching SimMatch v9/Growth v4 work in either order. Keep just one line per module; the recommended eight-ML-line order is in `README.md`.
3. The deployed Transfers settings were invalid in the log, while this copy has `wealth = 150`. Replace the different copy or correct that setting without weakening validation. Back up custom settings before replacing a module.
4. Fully exit and relaunch PES after each change. Removing a Lua line does not undo a running patch. Growth/money changes already persisted by the game are not reversed by disabling the module. SimToDate's default "off" still installs hooks; excluding those requires removing its module line and restarting.
5. PlayerDump, GrowthBridge and Stadiums remain untouched. No `sider.ini`, third-party package, Sider DLL, executable or save was edited by this fix.
6. **Switcher2 remains unrepairable from this checkout:** its source is absent. The logged `Pattern not found. Unknown game version` cannot safely be fixed by inventing an address or bypassing the version check. Its source and the actual installed configuration are needed.
7. If the close continues, record the exact triggering action and collect the matching Windows Application Error entry (faulting module, exception code and offset), preferably with a crash dump. Compare the same action with Lua disabled and, where possible, without Sider, using a disposable save.

Twelve logged sources are absent: `Script_CustomCup.lua`, `Script_Entrance.lua`, `Script_NoCrowd.lua`, `Script_Pitch.lua`, `Script_Scorex.lua`, `Script_Stadiums.lua`, `Script_Switcher.lua`, `Script_Switcher1.lua`, `Script_Switcher2.lua`, `Script_Weather.lua`, `PlayerDump.lua`, and `GrowthBridge.lua`. Unknown writes/content in these files cannot be included in the compatibility result.

The original log's `DLL detaching / Unmapping from PES` is a generic detach message, not a fault address. Speed `20833.333 (0.000)` is neutral speed, not a large speed multiplier. These interpretations and Sider's decoded team-ID contract were checked against upstream Sider 3.6.0 source at commit [`45096559ec742f650d828b6e967135f35aad75a4`](https://github.com/pes-modding/sider3/tree/45096559ec742f650d828b6e967135f35aad75a4); exact equivalence to the user's DLL was not established.

**Verdict:** Available-source defects are repaired and regression-tested; deploy the updated files together and test on a backup. The reported game closure still has no proven cause.

**Not checked:** live Windows/Sider/PES behavior, a crash dump, missing third-party sources/assets, drivers, other injected DLLs, or every native instruction/path. **Risk:** emulator success does not guarantee crash-free play or undo changes already saved by the game.
