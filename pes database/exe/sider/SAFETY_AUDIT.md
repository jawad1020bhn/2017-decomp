# Sider Lua safety audit and fixes — 17 November 2026

Eight modules are covered: MLCheck reads memory; the others patch gameplay or controls. These checks exercise the bundled 32-bit executable under emulation, not a full Windows career.

## Earlier startup-log follow-up

- **Growth 4 → 5:** the untracked positive-award branch jumped into the playtime
  fragment without loading exp/curve onto x87 or restoring `&exp` in EDX after the
  lookup. A real native 50-slot miss leaves EDX=`32` hex: the hook attempted
  `fstp [00000032]`. The emulator maps the null page for Windows SEH, so the added
  low-address write guard was necessary to catch this. V5 skips only the optional
  appearance lookup, restores `&exp`, and runs full arithmetic. B1 shrinks from 132
  to 128 bytes; rates/settings/events/other hooks are unchanged. This is a crash risk,
  **not proof it occurred in the user's session**.
- **Spirit 3 → 4:** `yours 4294967295` in the log means the callback skipped dynamic
  form. V3 treated `024fea5c` as the user ID; native callers use it as an invalid-ID
  placeholder. V4 resolves the primary controlled club from the current bounded
  table (`+314`, bits 7–14), requires exactly one slot-0 club and compares its decoded
  ID with Sider's teams. Added read-only layout checks avoid Transfers' hooked entry.
  Missing/ambiguous ownership, alternate layout and unsupported counts fail closed.

Old Growth fixtures mocked tracked lookups; old Spirit fixtures fabricated a valid
ID at the wrong global. Corrected fixtures fail against Growth 4 / Spirit 3 before
the fixes. Coverage now includes 36 real first/last/missing growth-record cases with
low-address/x87 guards and four real-save **club-table** ownership replays with the
invalid-ID global unchanged. The latter use synthetic two-loss form, not full career
loads.

## Earlier changes applied

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

**Sources:** `MLTeamSpirit.lua`, `test_spirit.py`. Version 6 retains bounded indexed-table reads and checks ownership against the current match participants.

Before the fix, Sider-style home/away team numbers `7`/`8` were divided by 16,384 a second time. Two losses therefore left the value at **95 rather than 92**. The old tests passed packed career IDs, unlike the real callback. All event fixtures now use decoded team numbers, and the expected form, cup, derby and league bonuses pass at home and away.

The old date reader treated day 305/year 2024 as day **132,645,169**. It now decodes day and year separately and ignores neighboring bytes. Tests cover both 2024 and 2026, a scheduled next-season opening fixture, and a future-dated played result. Current form and the league bonus stay unchanged.

The old final match batch processed 9,024 records instead of 9,000, reading **14,112 bytes past the array**. Tests now put a fake win immediately after that array and prove it is neither read nor included. The last valid match (record 8,999) still works. Club and competition walkers also stop at the proper scan extent (populated counts in modes 0/1, bounded slots in mode 2), including partial final batches.

**Compatibility:** `RIVALS` still accepts packed career club IDs. The log labels a copyable `RIVALS id` separately from the decoded Sider team number. Existing packed rival settings remain effective.

### Growth v4

**Sources:** `growth_cave.py`, generated blocks in `MLGrowth.lua`, `test_growth.py`. Earlier annual-margin fix retained in v5; the lookup-miss fix is described above.

The annual award previously loaded an age margin into EDX, replaced it with an ability selector, and later used that selector for its headroom comparison/division. The margin is now saved across the getter call. The regenerated award is **147 bytes**, within its **153-byte** reservation; the dependent season-hook branch has also been regenerated.

The original failures are now corrected: CF finishing 80, turning 17, becomes **81**, not 82; finishing 84, turning 23, becomes **85**, not 84. The test compares native annual awards with `season_levels` across **1,456 age/position/ability cases**, including limited headroom and invalid-position fallback. It also assembles every Growth block and compares the resulting bytes with the literal and embedded Lua data.

### SimMatch v9 and shared memory

**Sources:** `MLSimMatch.lua:993–1029`; `sim_cave.py:93–116`, `2389`, `3157–3178`; `test_sim.py`, `test_safety.py`.

The simulator's logical ET image is still 4,030 bytes for code/table generation. Installation now checks and writes only:

- code reservation: `0x047d5040–0x047d5b8b`;
- score tables: `0x047d5be0–0x047d5ffd`.

It does not check or overwrite `0x047d5b8c–0x047d5bdf`, where Growth places its curve. Both Growth-first and simulator-first installations pass. Native-code/table tamper checks outside the gap remain active. Generator limits prevent future simulator code from growing into adjacent Growth allocations.

The integration test now installs all eight modules in **22 orders**: two explicit opposite Growth/SimMatch orders and 20 deterministic sampled orders, respecting Check-before-Money and Money-before-Transfers. It captures every write, rejects cross-module intersections, and checks that later modules preserve every previously installed byte.

**Upgrade both files together.** With an older SimMatch v8, SimMatch must still load before Growth. The supplied log used that working order; this dependency was not proof of why that run closed.

### Failed-write recovery

**Sources:** `MLMoney.lua:932–954`, `MLTransfers.lua:1581–1599`, `MLYear.lua:98–114`, `MLSimMatch.lua:1035–1052`, `MLGrowth.lua:169–187`, `MLTeamSpirit.lua:632–642`; `test_safety.py`.

On a read-back mismatch, the patchers restore the failed patch and earlier attempted patches in reverse order. Other modules' changes are left alone. Cave data can remain occupied, but no successfully restored native hook points to it. A full process restart is still required after a failed install.

Transfers additionally checks Money's actual native fee hook. A stale Money cave/marker after rollback is no longer accepted as a completed prerequisite; the regression verifies that Transfers writes nothing after each recoverable Money failure.

The failed-write tests verify restoration of original patch bytes and explicit reporting when restoration fails. SimToDate separately tests its rollback and READY gate.

**Host-error limitation:** Sider 3.6.0's Lua environment does not expose `pcall`. If `memory.write`/`memory.read` raises a host error, init can stop before Lua performs rollback. The fixes cover verification failures, not an exception-safe transaction or atomic writes across threads. No Sider DLL was modified. Quit PES on any init/write/restore failure; do not keep playing or save.

## Validation

Run from this folder with Python packages `lupa`, `unicorn`, `capstone`, and `keystone-engine`:

```
python test_safety.py "path/to/PES2017.exe"
python test_spirit.py "path/to/PES2017.exe"
python test_growth.py "path/to/PES2017.exe"
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
| Growth experience hook | `047d6377–047d63f6` | 128 |
| Transfers position need | `047d6400–047d654f` | 336 |
| Transfers incoming offers | `047d6550–047d6d3f` | 2,032 |
| Transfers squad pressure | `047d6d40–047d6e4f` | 272 |
| Growth season walk/arithmetic | `047d6e50–047d6efd` | 174 |
| Growth training | `047d6efe–047d6f4b` | 78 |
| Sim-to-Date day loop | `047d6f60–047d6fec` | 141 |
| Sim-to-Date calendar | `03fc8000–03fc88ff` | 2,304 |
| Money budget keys | `03fc9300–03fc943f` | 320 |
| Sim-to-Date state | `0298c0e0–0298c1ff` | 288 |
| Growth tables | `0298c200–0298c2eb` | 236 |

## Deployment and remaining uncertainty

1. Back up the actual installed modules, `sider.ini`, and saves. Copy the updated Lua files from this folder into Sider's `modules` folder. Do not copy Python generators/tests there.
2. Use the module order in `README.md`.
3. Fully exit and relaunch PES after each change. Removing a Lua line does not undo a running patch. Growth/money changes already persisted by the game are not reversed by disabling the module. SimToDate's default "off" still installs hooks; excluding those requires removing its module line and restarting.
4. PlayerDump, GrowthBridge and Stadiums remain untouched. No `sider.ini`, third-party package, Sider DLL, executable or save was edited by this fix.
5. **Switcher2 remains unrepairable from this checkout:** its source is absent. The logged `Pattern not found. Unknown game version` cannot safely be fixed by inventing an address or bypassing the version check. Its source and the actual installed configuration are needed.
6. If the close continues, record the exact triggering action and collect the matching Windows Application Error entry (faulting module, exception code and offset), preferably with a crash dump. Compare the same action with Lua disabled and, where possible, without Sider, using a disposable save.

Twelve logged sources are absent: `Script_CustomCup.lua`, `Script_Entrance.lua`, `Script_NoCrowd.lua`, `Script_Pitch.lua`, `Script_Scorex.lua`, `Script_Stadiums.lua`, `Script_Switcher.lua`, `Script_Switcher1.lua`, `Script_Switcher2.lua`, `Script_Weather.lua`, `PlayerDump.lua`, and `GrowthBridge.lua`. Unknown writes/content in these files cannot be included in the compatibility result.

The original log's `DLL detaching / Unmapping from PES` is a generic detach message, not a fault address. Speed `20833.333 (0.000)` is neutral speed, not a large speed multiplier. These interpretations and Sider's decoded team-ID contract were checked against upstream Sider 3.6.0 source at commit [`45096559ec742f650d828b6e967135f35aad75a4`](https://github.com/pes-modding/sider3/tree/45096559ec742f650d828b6e967135f35aad75a4); exact equivalence to the user's DLL was not established.
