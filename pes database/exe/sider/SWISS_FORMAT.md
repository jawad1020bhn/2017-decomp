# UEFA 36-Team Swiss Format Native In-Game UI Integration

## 1. Overview

The UEFA Champions League 36-team single league phase ("Swiss system") is integrated directly into PES 2017's native Master League user interface. When the user navigates to **Competition Info -> Standings -> UEFA Champions League** or advances through post-match standings checks (`process::CmnStandingsCheck`), the game engine displays all 36 European clubs in a single, unified, scrollable league table with live points, wins, draws, losses, goals for, goals against, goal difference, and official UEFA qualification zones.

---

## 2. Reverse-Engineered Executable Architecture

Tracing the decompiled executable source (`031.c.xz`, `032.c.xz`, `038.c.xz`) revealed the complete internal standings rendering pipeline:

```
[Standings Menu Navigation]
         │
         ▼
 fcn_0323a66c (Common/CmnStandingsMenu, rankingTeam.bin)
         │
         ├──► Resolves active competition ID (ModeData + 0xdc9d7c)
         │
         ▼
 fcn_031209ba (UI Layout Selector)
         │
         ├──► Reads Jump Table Index at 0x03120b2d:
         │      Vanilla UCL (comp 2): index 0x00 -> Case 0 (push 2: 8 groups of 4)
         │      PATCHED UCL (comp 2): index 0x07 -> Case 7 (push 0: Unified League Table)
         │
         ▼
 fcn_0323a885 (Choice Row Generator)
         │
         ├──► Reads competition record from ModeData + 0xc2cbb8 via fcn_0381e21b
         ├──► Reads total teams at rec + 0x844 (36 clubs)
         ├──► Loops uVar9 = 0 .. 35:
         │      Creates UI element "choice_<uVar9>"
         │      Calls fcn_0323a1e1 (Qualification cutoff zone highlights)
         │      Calls fcn_03239e2f (Rank movement arrows: up/down/dash)
         │      Calls fcn_0323a336 (Bit-unpacks points, record, goals)
         │
         ▼
[Native Game Screen Renders 36-Team Swiss Table]
```

### Key Executable Locations

| Virtual Address | File Offset | Vanilla Instruction / Bytes | Patched Instruction / Bytes | Description |
|:---|:---|:---|:---|:---|
| `0x03120b2d` | `0x02d1c92d` | `0x00` | `0x07` | UCL layout index in `fcn_031209ba`: routes to Case 7 (`0x03120a79`, `push 0` = League Table view) |
| `0x0323a3af` | `0x02e361af` | `cmp eax, 0x20` (`83 f8 20`) | `cmp eax, 0x40` (`83 f8 40`) | `fcn_0323a336`: raises team clamp from 32 to 64 so stats unpack for all 36 teams |
| `0x0323abc3` | `0x02e369c3` | `cmp edi, 0x20` (`83 ff 20`) | `cmp edi, 0x40` (`83 ff 40`) | `fcn_0323a885`: raises loop clamp from 32 to 64 so choice rows are created for all 36 teams |
| `0x03239e9c` | `0x02e35c9c` | `cmp eax, 0x20` (`83 f8 20`) | `cmp eax, 0x40` (`83 f8 40`) | `fcn_03239e2f`: raises team entry clamp for rank arrow calculation |
| `0x03239edd` | `0x02e35cdd` | `cmp edi, 0x20` (`83 ff 20`) | `cmp edi, 0x40` (`83 ff 40`) | `fcn_03239e2f`: raises previous table clamp for rank arrow calculation |
| `0x03239f31` | `0x02e35d31` | `cmp edi, 0x20` (`83 ff 20`) | `cmp edi, 0x40` (`83 ff 40`) | `fcn_03239e2f`: raises previous table loop match clamp |

---

## 3. In-Game Standings Memory Structure (`ModeData + 0xc2cbb8`)

The game maintains up to 300 competition standings records at `ModeData + 0xc2cbb8`. Each record is `0x84c` (2,124) bytes:

- `+0x00`: `int16_t` Competition ID (`2` for UEFA Champions League)
- `+0x34`: Array of team rows (12 bytes per team = 3 dwords)
- `+0x844`: `int32_t` Active team count (`36`)

### Bit-Packing Specification per Team Row (`0x0c` bytes)

Each team row contains 3 32-bit little-endian integers directly decoded by `fcn_0323a336`:

```c
// Dword 0 (offset +0x00): Club Team ID
uint32_t team_id = dw0;

// Dword 1 (offset +0x04): Ranks and Match Record
uint32_t rank   = dw1 & 0x3f;           // bits 0..5:   1-based table position (1..36)
uint32_t pts    = (dw1 >> 6)  & 0xff;   // bits 6..13:  Points (0..255)
uint32_t wins   = (dw1 >> 14) & 0x3f;   // bits 14..19: Won matches (0..63)
uint32_t losses = (dw1 >> 20) & 0x3f;   // bits 20..25: Lost matches (0..63)
uint32_t draws  = (dw1 >> 26) & 0x3f;   // bits 26..31: Drawn matches (0..63)

// Dword 2 (offset +0x08): Goals Scored & Conceded
uint32_t gf     = dw2 & 0xfff;          // bits 0..11:  Goals For (0..4095)
uint32_t ga     = (dw2 >> 12) & 0xfff;  // bits 12..23: Goals Against (0..4095)
int32_t  gd     = gf - ga;              // In-game UI computes: num_Goals - num_GoalsConceded
```

---

## 4. UEFA Qualification Zones in Native UI

The UI engine highlights rows according to promotion cutoffs via `fcn_0323a1e1`:
- **Ranks 1 to 8**: Direct qualification to the UEFA Round of 16 (seeded status, green highlight bar).
- **Ranks 9 to 24**: Two-legged Knockout Phase Play-Offs (ranks 9-16 seeded vs 17-24 unseeded, blue highlight bar).
- **Ranks 25 to 36**: Completely eliminated from European competition (no drop-down to Europa League).

---

## 5. Dual Execution: Permanent Exe Patcher & Sider Lua Module

1. **Permanent Executable Patch (`pes database/exe/tools/patch_swiss_ui.py`)**:
   Applies the 6 binary patches directly to `PES2017.exe`, permanently routing competition ID 2 to the unified scrollable league layout and expanding table clamps to 64 teams.

2. **Dynamic Sider Module (`pes database/exe/sider/MLSwiss.lua`)**:
   - Hooks into `m.observe(ctx)` during live Master League gameplay.
   - Synchronizes `ModeData + 0x552e80` (competition participant slots).
   - Synchronizes `ModeData + 0x6f154c` (144 match schedule fixtures).
   - Synchronizes `ModeData + 0xc2cbb8` (`m.sync_in_game_standings`): keeps all 36 clubs, points, records, and goals live in game memory.
   - Populates group records 600..607 for seamless group-view tab compatibility.
   - Dynamically writes runtime memory hooks so the UI functions even if the unpatched binary is launched.

---

## 6. Verification and Testing

All components are covered by test suites:
- `python3 "pes database/exe/tools/patch_swiss_ui.py"`: verifies binary disk byte integrity.
- `python3 "pes database/exe/sider/test_swiss_ui.py"`: validates the full decompiled UI decoding pipeline for all 36 clubs.
- `python3 "pes database/exe/sider/test_swiss.py"`: validates 8-round Swiss schedule, pot balancing, country protection, and `ModeData` synchronization.
- `python3 "pes database/exe/sider/test_money.py"`: verifies Master League budget mechanics and ASM caves.
- `python3 "pes database/exe/sider/test_transfers.py" PES2017.exe`: verifies savefile transfer integrity across 4 ML career saves.
