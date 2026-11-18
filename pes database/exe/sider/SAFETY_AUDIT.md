# Sider Lua safety audit and fixes — 17 November 2026

**What this repo does:** Nine Master League Lua modules are covered here. MLCheck only reads memory; MLNews patches native presentation while observing sporting state; the other seven patch gameplay or controls. The audit assumes one 32-bit game process using the bundled executable and Sider 3.6.0.

**Status:** The earlier reproducible defects remain repaired, and all **13 test suites passed** one at a time on the current News v4 code. The new factual world-result ticker is **emulator-tested only, not live-game verified**; its first real in-game display remains outstanding. PlayerDump, GrowthBridge and Stadiums are unchanged, as requested. The original unexpected close is **not diagnosed** by these tests or the initialization log.

## News v4: expand content without bypassing the missing-display investigation

The user reports original-only News after progression, but has supplied no latest v3
runtime snapshot to distinguish rejection from a copied-but-invisible string. Spirit
is user-confirmed fixed and is unchanged. V4 expands ticker content at the user's
request; it does **not** establish the missing-display cause or a rendering fix.

V4 ranks up to **four completed AI-v-AI league/cup results**, **0–14 game days old**,
by date, goal margin and physical record order. Every existing displayed native item
uses its ordinal modulo the pool size; fewer results repeat. The native cap is nine
items; a one-item feed still displays only one result and an empty feed stays empty.
Every original ticker string and all large photo/title cards remain untouched.

**Competition evidence:** native `038566ec` returns competition `+5c` as a dword;
`0385662c` resolves the `+4e` parent. `038a9115` handles kind 3 knockout rounds and
kind 1 group positions, while `03879719` distinguishes standalone leagues by a missing
parent. The supplied named save has kind 3 FA Cup/Copa del Rey/DFB-Pokal records,
kind 1 Champions League groups under kind 2 parents, and kind 4 Arabic-named friendly/
training fixtures. **Kind 4 is not a cup** and is excluded. Selection accepts kind 1
standalone leagues, kind 3 knockout cups, and kind 1 groups only if their parent is a
known, bounded kind 2 record; those groups are labelled CUP, not LEAGUE. Containers,
friendlies, unsupported kinds and missing/self/non-container group parents are skipped.
Both metadata getters now have exact installation fingerprints.

The hook, 2,560-byte cave and 48-byte diagnostic block keep their existing addresses
and ownership safeguards. Four 16-byte story slots live only on the stack, initialized
on every call; no history/cache, career write or sports RNG is added. Each native item
rescans the same bounded 9,000-record table. Bounds, clock, completed-state, controlled-
club, name and ET/shoot-out guards remain. Live menu performance is not yet measured.
Only `MLNews.lua`, its generator/tests and these documents change; PlayerDump,
GrowthBridge, Stadiums, Team Spirit, the other ML modules and configuration do not.

**Regressions:** the expanded test first failed against unchanged News v3's old single,
unlabelled result. A separate red test caught the provisional kind-4 filter before
correction. Passing cases now include pool sizes 1/2/3/4, a fifth result displacing the
fourth, exact physical-order ties, ordinals 0–11, all existing native items in both UI
paths, preserved Arabic UTF-8 source text, 14/15-day and New Year boundaries, factual
league/knockout/cup-group labels and guarded exclusions/parents. Hooked/unhooked native
shuffle arguments, seed, stored news strings, career bytes and temporary ownership
still match. Two real-save table replays each exercise four factual results across
nine native items; expanded fixtures also execute with all nine ML modules installed.
These are emulator checks with CRT/final-widget stand-ins, not live rendering proof.

## Runtime follow-up: normal indexed careers were incorrectly rejected

**Reported evidence:** after progressing to **03/10/2026**, News v2 logged rising
native `copies` / `attempts`, `copied=0`, and `last=alternate table layout; mode=19`.
The hook and native items were present; it refused at the lookup-mode guard before
reading clock/count/result fields. Their zeros were diagnostic resets, not evidence
of a zero game date. Spirit v4 had the same unconditional rejection of value 2.

**Native trace:** `035fbac3` sets `[career + ec1408] = 2` after the normal `03787e30`
career load. Progression `036101d9` also writes 2. This selects indexed access, not
relocated arrays: `03822969 → 0381e428` returns `career + 481be0 + (id & 3fff)*520`,
and `03822ab9 → 0381e458` scans all 300 competition slots at `career + 552e80`.
`0381e624` counts populated records separately; sparse tables must not truncate at
that count. The two indexed getters now have exact installation fingerprints.

**News v3 / Spirit v5:** accept only known lookup values 0/1/2. Preserve existing
positive/bounded count checks. Modes 0/1 scan the populated prefix; mode 2 scans the
bounded slot extent (651 saved-club slots / 300 competition slots), skipping invalid
records. The native array's two additional club slots remain unsupported, not silently
included. Spirit shares this selection for primary-club, rivals and competition-kind
walks. Missing/ambiguous ownership and invalid pointers/dates/results remain guarded.
No career/sporting records, growth settings, other modules or allocation sizes change.

News's diagnostic +44 word now records the observed lookup value (initially unread),
replacing the unused `MLN2` marker. The state stays 48 bytes at the same address;
selection branches on a separate stack local, never diagnostic metadata. `lookup=2`
is normal; unknown values still yield stage 4. Native copy is still not rendering proof.

**Regressions:** before production edits, valid indexed fixtures failed against News
v2 at stage 4 and Spirit v4 at 95 rather than 96 after one win. Most career fixtures
now default to the indexed mode actually used in load/progression. Tests explicitly
retain 0/1 support, compare real native getters, place the primary club at slot 600,
AI clubs at 649/650 and a competition at 299 with populated counts only 3/1, and poison
the immediately following slots to enforce bounded reads. At an explicit test clock
03/10/2026 (day 275), News prefixes the known 02/10 result, while Spirit's one-win,
derby and cup-final setups give 96/98/99. Both sparse paths also run with all nine
modules installed; career record bytes and the native ticker RNG behavior stay unchanged.
These are synthetic worlds and read-only save-table replays, **not the user's save**.

Spirit still computes before the **next match setup**; no post-match/home-menu refresh
was added. A weighted real history can legitimately give 95 even after a win. The user
has since confirmed Spirit fixed. News still needs `MLNews 4 runtime:` plus a factual
visible prefix/result cross-check; the present expansion does not change Spirit.

## Earlier startup-log follow-up

All nine ML modules installed, but two further defects were reproduced **before**
fixing them. Initialization and the previous green suites were not enough evidence.

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
loads. Growth awards/season/training, Spirit callbacks/native value reads and ticker
execution also each run with all nine ML modules installed.

**News 1 → 2:** the supplied v1 log has no runtime/selection evidence. Its invisible
display remains **undiagnosed**, not “fixed by installation.” V2 adds zero-checked
48-byte diagnostics at `0298c2f0–0298c31f`, after Growth data. Native code records the
last rejection/copy stage, counters and bounded metadata; none is selection input.
Supported resource/match observers only read it, return nil and throttle changed
snapshot logs. `copied` means **a native string was built**, not that a headline
rendered. Empty feed/unvisited UI, data/result rejection and copy stages are now
observable; the real UI milestone is still open. See `README.md`.

The latest log also shows Stadiums **not activated** (missing map), Switcher2's failed
pattern lookup despite “initialized,” and SimToDate intentionally off. Third-party
initialization is not gameplay verification. Missing sources cannot be independently
audited; excluded modules/configuration remain untouched.

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

### MLNews v4: expanded native ticker, not a completed news system

**Sources:** `MLNews.lua`, `news_cave.py`, `test_news.py`.

The only native patch is the five-byte string-copy call at `032a2dd1`, within the fully
fingerprinted reader `032a2b93–032a33bf`. The wrapper prefixes **every displayed**
item using its displayed ordinal, not its shuffled source index, cycling through up to
four dated actual AI-v-AI league/cup results. Newest date ranks first, then largest
margin, then first stored record. Results must be completed, 0–14 game days old, have
valid bounded dates/names/clubs/competition and no extra-time/shoot-out words. Exactly
one primary controller-slot-0 club must exist; all controlled clubs are excluded from
the story. Other mode selectors, unknown lookup modes and
invalid counts are skipped. Normal indexed mode 2 is supported as described above;
other controller layouts are not live-verified.

The 2,560-byte code/constant image is at `03fc8900–03fc92ff`, directly after SimToDate's
separate `03fc8000–03fc88ff`. It is zero-checked and read back **before** the hook is
written/read back. A failed hook write attempts to restore the original call and
reports refused restoration. The code cave can remain occupied after failure; restart
is mandatory. Runtime text uses a bounded 256-byte stack buffer, then the game's own
string constructor/append/cleanup. It never adopts a stack/cave pointer as string-owned
memory. This is a **presentation-memory patch**, not a zero-write module.

The native list and stored strings are untouched: no news-vector insertion, extra RNG
call, popup, forced stop or sporting-state update. An empty native feed stays empty.
There is no story history/cache/file to contaminate a reload or another career, and prefixes
do not accumulate across redraws. The same eligible result **can recur** on later
redraws until replaced/expired; consumed-story deduplication is outside this proof.
Long feeds cycle the fixed pool; photo/title cards are unchanged.
No invented finances, transfers, upsets, sackings or player emotions are generated.

`test_news.py` executes the real reader, string/vector ownership paths and shuffle/mode
RNG, comparing hooked/unhooked RNG arguments and the resulting seed. Career memory is
read-protected except for the native seed page, with a write guard allowing only that
existing u16 seed write; all other career bytes and stored news strings are checked
unchanged. Temporary ownership is balanced on the tested paths, with the code cave
read/execute-only. Tests include 30 seeded fixture worlds, 2,772 date-parser cases,
last-record bounds, malformed/ambiguous data, unreadable install checks, 63 sampled
fingerprint/cave/state mismatches, write refusal/damage/recovery, empty feeds, format failure,
redraws and earlier/changed same-address career data. Native ticker tests also run
with all nine modules installed. This is **not** a whole-match or Windows leak profile.

Two real-save **table replays** reached the final UI stand-in with factual prefixes:

```text
WORLD RESULT 29/08/2024 [LEAGUE]: Botafogo FR 0-4 Clube do Remo |
WORLD RESULT 12/09/2024 [LEAGUE]: Clube do Remo 4-0 SC Corinthians Paulista |
```

These copy observed club/competition/result tables and explicitly set the replay clock
to the latest completed-match date. They are not full career loads, do not establish
the saved-clock mapping and are **not** PES screenshots. CRT allocation/formatting/
random APIs and final widgets are stand-ins. Actual rendering, fonts, scrolling/clipping,
menu lifetime/transitions and live stability need the disposable-save procedure in
`README.md`; only a visible, result-cross-checked Master League headline passes it.

Static cave review found no verified native direct target or plain-data pointer into
`[03fc8900,03fc9300)`. An overlapping-dword scan found nine live-code matches (instruction
bytes/relative displacements or `+3fc` member offsets, not pointers) and 20 in encrypted
`.data`. Fourteen raw near-call/jump/conditional candidates in live code were all inside
other instructions, not instruction-boundary targets, when decoded from their recorded
function starts. The preceding thunks jump over the zero run to `03fc9da0`; News is far
from the padding NOP that straddles its start. This corrects the older blanket “no dword
points into the run” wording; it is not proof against computed or third-party references.
Runtime zero/fingerprint checks and nine-module overlap tests remain required.

The diagnostic block fits inside the loader-zeroed tail of the read/write, non-executable
`.text` page; the next section starts at `0298d000`. An overlapping-dword scan of the
entire executable found **no value in `0298c2f0–0298c31f`**. Scanning its whole page
found 38 raw matches, including real TLS metadata: the active PE TLS directory at
`047d4008` declares raw TLS bytes only at `0298c000–0298c043`, with no additional
zero-fill. The original header copy at `022c5170` has the same raw extent. Diagnostics
are outside that extent and after Growth's last byte `0298c2eb`. This is not proof
against computed references, broad page operations, protected startup behavior or
unknown third-party modules; zero/read-back checks and the disposable-save live test
are still necessary. The diagnostic values are never story-selection input.

### Team Spirit v3

**Sources:** `MLTeamSpirit.lua`, `test_spirit.py`. Earlier fixes retained in v5; the user-club locator and indexed-mode fixes are described above.

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

The integration test now installs all nine modules in **22 orders**: two explicit opposite Growth/SimMatch orders and 20 deterministic sampled orders, respecting Check-before-Money and Money-before-Transfers. It captures every write, rejects cross-module intersections, and checks that later modules preserve every previously installed byte.

**Upgrade both files together.** With an older SimMatch v8, SimMatch must still load before Growth. The supplied log used that working order; this dependency was not proof of why that run closed.

### Failed-write recovery

**Sources:** `MLMoney.lua:932–954`, `MLTransfers.lua:1581–1599`, `MLYear.lua:98–114`, `MLSimMatch.lua:1035–1052`, `MLGrowth.lua:169–187`, `MLTeamSpirit.lua:632–642`; `test_safety.py`.

On a read-back mismatch, the patchers restore the failed patch and earlier attempted patches in reverse order. Other modules' changes are left alone. Cave data can remain occupied, but no successfully restored native hook points to it. A full process restart is still required after a failed install.

Transfers additionally checks Money's actual native fee hook. A stale Money cave/marker after rollback is no longer accepted as a completed prerequisite; the regression verifies that Transfers writes nothing after each recoverable Money failure.

Tests now inject **104 refused/damaged patch writes** across seven patchers (including News) and verify that all original patch bytes are restored. Separate cases refuse restoration itself and verify that each patcher reports `restore failed` rather than falsely claiming recovery. Existing SimToDate tests cover its rollback and READY gate. News additionally exercises failed/damaged cave writes with its native hook left untouched.

**Host-error limitation:** Sider 3.6.0's Lua environment does not expose `pcall`. If `memory.write`/`memory.read` raises a host error, init can stop before Lua performs rollback. The fixes cover verification failures, not an exception-safe transaction or atomic writes across threads. No Sider DLL was modified. Quit PES on any init/write/restore failure; do not keep playing or save.

## Validation

All 13 suites exited **0** against the bundled executable on News v4. News ran first,
then the other twelve suites ran sequentially on unchanged production/test code; no
large emulator suites overlapped. Combined suite time was approximately **547.6 seconds**
(News's 111.6-second figure is approximate wall time):

| Suite | Seconds |
| --- | ---: |
| `test_news.py` | 111.63 |
| `test_module.py` | 0.23 |
| `test_safety.py` | 1.54 |
| `test_growth.py` | 4.90 |
| `test_spirit.py` | 8.00 |
| `test_year.py` | 0.82 |
| `test_need.py` | 7.73 |
| `test_offer.py` | 0.68 |
| `test_sim.py` | 77.97 |
| `test_simdate.py` | 24.84 |
| `test_simdate_calendar.py` | 1.94 |
| `test_transfers.py` | 7.82 |
| `test_money.py` | 299.48 |

Before changing production code, the corrected Spirit fixtures and new Growth cases failed against the original code. The new failed-write regression also failed before recovery was implemented, and the chained Money-failure/Transfers regression failed before the prerequisite hook check was added. The final sequential run passed all suites; running multiple large emulator suites concurrently can exceed the sandbox's memory budget, so the release check used one suite at a time.

Run from this folder with Python packages `lupa`, `unicorn`, `capstone`, and `keystone-engine`:

```
python test_safety.py "path/to/PES2017.exe"
python test_news.py "path/to/PES2017.exe"
python test_spirit.py "path/to/PES2017.exe"
python test_growth.py "path/to/PES2017.exe"
```

All 30 recorded input files were hash-identical across the tests. Compared with the
pre-edit baseline, only the intended `MLNews.lua`, `news_cave.py` and `test_news.py`
changed; the other **27 input hashes** are unchanged, including the executable, all
four saves, existing transfer CSV and the other eight ML Lua files. Documentation
changes are outside that input manifest. The executable and saves are only read by
the harness. Executable SHA-256:

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
| Growth experience hook | `047d6377–047d63f6` | 128 |
| Transfers position need | `047d6400–047d654f` | 336 |
| Transfers incoming offers | `047d6550–047d6d3f` | 2,032 |
| Transfers squad pressure | `047d6d40–047d6e4f` | 272 |
| Growth season walk/arithmetic | `047d6e50–047d6efd` | 174 |
| Growth training | `047d6efe–047d6f4b` | 78 |
| Sim-to-Date day loop | `047d6f60–047d6fec` | 141 |
| Sim-to-Date calendar | `03fc8000–03fc88ff` | 2,304 |
| News code/constants | `03fc8900–03fc92ff` | 2,560 |
| Sim-to-Date state | `0298c0e0–0298c1ff` | 288 |
| Growth tables | `0298c200–0298c2eb` | 236 |
| News diagnostics (data only) | `0298c2f0–0298c31f` | 48 |

In particular, `047d6d60–047d6e4f` is **not free**; it belongs to transfer squad-pressure code. No unbounded Lua collection was found in the nine checked modules. The listed fixed injected regions total about 22 KiB; News also uses a stack buffer and native-owned temporary strings on ticker rebuilds. This is not a Windows memory/leak profile.

## Deployment and remaining uncertainty

1. Back up the actual installed modules, `sider.ini`, and saves. Copy the updated Lua files from this folder into Sider's `modules` folder. Do not copy Python generators/tests there.
2. Keep Check before Money and Money before Transfers. The matching SimMatch v9/Growth v5 work in either order. Keep just one line per module; the recommended nine-ML-line order (News optional/experimental) is in `README.md`. News can also be tested alone; it has no module dependency.
3. The earlier log refused Transfers settings; the latest supplied log now shows valid Galactico `wealth = 150` and successful installation. No new Transfers settings change is required. For the current expansion, back up custom settings and replace only News v4; the already-working Spirit v5, Growth v5 and all other modules are unchanged.
4. Fully exit and relaunch PES after each change. Removing a Lua line does not undo a running patch. Growth/money changes already persisted by the game are not reversed by disabling the module. SimToDate's default "off" still installs hooks; excluding those requires removing its module line and restarting.
5. PlayerDump, GrowthBridge and Stadiums remain untouched. No `sider.ini`, third-party package, Sider DLL, executable or save was edited by this fix.
6. **Switcher2 remains unrepairable from this checkout:** its source is absent. The logged `Pattern not found. Unknown game version` cannot safely be fixed by inventing an address or bypassing the version check. Its source and the actual installed configuration are needed.
7. If the close continues, record the exact triggering action and collect the matching Windows Application Error entry (faulting module, exception code and offset), preferably with a crash dump. Compare the same action with Lua disabled and, where possible, without Sider, using a disposable save.

Twelve logged sources are absent: `Script_CustomCup.lua`, `Script_Entrance.lua`, `Script_NoCrowd.lua`, `Script_Pitch.lua`, `Script_Scorex.lua`, `Script_Stadiums.lua`, `Script_Switcher.lua`, `Script_Switcher1.lua`, `Script_Switcher2.lua`, `Script_Weather.lua`, `PlayerDump.lua`, and `GrowthBridge.lua`. Unknown writes/content in these files cannot be included in the compatibility result.

The original log's `DLL detaching / Unmapping from PES` is a generic detach message, not a fault address. Speed `20833.333 (0.000)` is neutral speed, not a large speed multiplier. These interpretations and Sider's decoded team-ID contract were checked against upstream Sider 3.6.0 source at commit [`45096559ec742f650d828b6e967135f35aad75a4`](https://github.com/pes-modding/sider3/tree/45096559ec742f650d828b6e967135f35aad75a4); exact equivalence to the user's DLL was not established.

**Verdict:** Earlier fixes are retained; the normal indexed-career guard fix remains
in News v4 / Spirit v5, and Spirit is user-confirmed working. News v4 expands factual
content with all 13 suites passing, but does not diagnose the original-only display.
Initialization, copied-string counters and emulator UI stand-ins are not rendering
proof. Follow the backup-save acceptance procedure in `README.md` before relying on
it. The reported game closure still has no proven cause.

**Not checked:** live Windows/Sider/PES behavior, a crash dump, missing third-party sources/assets, drivers, other injected DLLs, or every native instruction/path. **Risk:** emulator success does not guarantee crash-free play or undo changes already saved by the game.
