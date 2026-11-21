# Simulated matches: outcomes and tuning

[Sider developer guide](../README.md) · These are versioned implementation notes and test observations. For current settings and deployment, use the guide and shipped Lua files. Paths and commands assume the `sider` directory unless noted.

## `MLSimMatch.lua`, version 9: simulated matches, Attack/Defense split, attribute scorers/assists, subs, fatigue & injuries

Emulator only: it has not run in the game yet. Needs no other module and coexists cleanly
with `MLMoney.lua`, `MLTransfers.lua`, and `MLYear.lua` in any load order.

### What it changes

1. **Match outcome (`0x03707a1f`):** replaces vanilla's harsh `diff >= 4` / `diff >= 2`
   step function with a smooth Davidson win/draw/loss table plus `HOME_ADVANTAGE`
   (`2.5` OVR since the post-audit retune below; `ELO_SCALE = 4.0`, `BASE_DRAW = 0.28`)
   and ML captain role bonus via
   `CAPTAIN_WEIGHT` (`0.125`: +-10 gives +-1 OVR, +-20 gives +-2).
   **Version 8** changed these four defaults (version 7: `2.4`, `6.2`, `0.27`, `0.2`),
   because the tables of version 7 were too flat. Model of the module's own tables on
   the 20, 18 and 20 clubs of England, Germany and Spain in `ML saves/ML00000013
   (before)` (best eleven of each club, all fit; home and away against every other
   club; 2,000 seasons):

   | | version 7 | version 8 | real football (about) |
   |---|---|---|---|
   | points of the champion, England / Germany / Spain | 76 / 73 / 83 | 83 / 81 / 92 | 90 / 80 / 88 |
   | points of the last club | 29 / 25 / 30 | 23 / 20 / 25 | 21 / 22 / 24 |
   | best club: matches won | 53% / 63% / 63% | 60% / 73% / 72% | 70 to 75% |
   | best club: goals for a match | 1.50 / 1.79 / 1.76 | 1.71 / 2.03 / 1.98 | 2.3 to 2.6 |
   | home wins / draws / away wins, England | 44 / 26 / 31% | 44 / 25 / 31% | 45 / 24 / 31% |
   | goals a match | 2.36 / 2.49 / 2.46 | 2.51 / 2.65 / 2.62 | 2.8 / 3.0 / 2.6 |

   The lineups of such a league are only about 11 OVR points apart, which is why 6.2 points
   per e-fold made the best club win barely more than half its matches. The draws were
   already right (one match in four), so `BASE_DRAW` moved only to keep them there.
   `test_sim.py` (test 24) holds the defaults to this.
   **After the suggestion audit** the home advantage was raised again, from `1.6` to `2.5`
   (just above version 7's `2.4`): between equal teams home/draw/away becomes 48/27/25%,
   and in test 24's model of the twenty best clubs home wins rise from 43% to 47% while
   draws stay at 26% and the champion's points move by less than one (74 -> 73). Home
   wins now sit a touch above the ~45% of real football, accepted deliberately; test 24's
   bound for them was widened to 50% for this.
2. **Scorelines, Attack/Defense split & GK modifier (`0x03705feb`, `ATTACK_DEFENSE_SPLIT`, `GK_SCORE_MOD`):**
   moves `score_hook` to `CAVE_ET` and replaces vanilla's narrow goal tables with a
   7x7 2D conditional Poisson table (`WIN_CDF_2D`, 1,029 B) indexed by
   `(Winner_ATK - Loser_DEF - Loser_GK_delta)` and `(Winner_DEF - Loser_ATK + Winner_GK_delta)`,
   a clean-sheet (`gl = 0`) boost when `Winner_GK_eff >= 82` (`min(25, (GK_eff - 79) * 2)%`),
   and a 5-band match-tempo draw CDF (`DRAW_CDF_BANDS`, 25 B) indexed by
   `(ATK_H - DEF_A) + (ATK_A - DEF_H) - GK_H_delta - GK_A_delta`, damping `>= 4` GD
   blowouts (`GOAL_SCALE`). `GK_eff` uses `GK_CONDITION_OVR = { -6, -3, 0, 3, 6 }` (1.5x
   arrow swing) minus fatigue, with `GK_delta = clamp((GK_eff - 82) / 3, -4, 5)` and
   `pos == 0` excluded from `def_ovr` to avoid double-counting. When `ATTACK_DEFENSE_SPLIT = false`,
   both ATK and DEF collapse to overall effective OVR.
   **Version 8** moves the neutral goalkeeper of `GK_delta` from 76 to 82 (`GK_BASELINE`
   in `sim_cave.py`; four bytes of the code, nothing else). Model of the tables on the
   499 clubs of `ML saves/ML00000013 (before)`, matches inside each group, goals per
   match and clean sheets per team: first 20 clubs (goalkeepers 84 on average) 2.33 and
   32% with 76, 2.47 and 30% with 82; places 21-60 (80) 2.45 and 30%, then 2.60 and 27%;
   places 101-140 (75) 2.61 and 27%, then 2.80 and 24%; places 301-340 (69) 2.83 and
   24%, then 3.01 and 21%. With `GK_SCORE_MOD = false` every group gives about 2.56 and
   28%. So 82 suits the best clubs and adds goals below them; the clean-sheet boost
   (from 82) is as it was.
3. **Skip Match substitutions, GK protection & smart CPU subs (`fcn_03707e71`):**
   - `SKIP_SUBS` (`0x03708230`): removes the hardcoded `sub = 11` overwrite when `SCOPE`
     includes Skip Match so simulated Skip Match fixtures behave like AI-vs-AI simulations.
   - `GK_PROTECT` (`0x0370818d`, version 6): replaces `xor edi, edi` (`31 ff` -> `90 90`)
     so slot `0` (starting GK) is never randomly selected as `sub1` for an outfielder.
   - `SMART_SUBS` (`0x037080d9`, version 6): replaces pure `rand(100)` bench sort keys
     with `player_eff_ovr(pos=13) + rand(4)` (clamped `<= 255`), so descending sort
     (`fcn_03705ef2`) brings on stronger, in-form, fresh substitutes first (respecting
     `SCOPE`).
4. **Dynamic player ratings (`0x03708cc4`):** computes end-of-match ratings from team
   result (`W/D/L`), goal difference, clean sheet bonus, goals (`RATING_GOAL`), assists
   (`RATING_ASSIST`), and disciplinary card penalties (`CARDS` adjustment), replacing
   vanilla's flat base ratings.
5. **Attribute-weighted goal scorers & assists (`0x037085b5` + `0x03706ef6`, enhanced in version 7):**
   - `sim_vec_hook` (`0x0370875c` inside `fcn_037085b5`): replaces vanilla's raw
     Finishing-only scorer stat (`-10` CB / `-5` FB) with `(2*Finishing + 2*Attacking Prowess + Header + 2) / 5`
     plus a 13-position modifier (`SCORER_POS_ADJ`), and adds a 13-position assist
     modifier (`ASSIST_POS_ADJ`) onto `Low Pass + Lofted Pass`, plus `2 * (cond_ovr - fatigue_pen)`
     when `CONDITION_STRENGTH = true` (clamped to `[1, 255]`, `GK = 0`).
   - `scorer_hook` (`0x03706ef6`): distributes goals across all 10 outfield
     players using exponential weights (`SCORER_SHARPNESS`, zero for GKs) and assigns
     assists across the remaining outfielders (`UNASSISTED_PCT`, `ASSIST_SHARPNESS`).
   - **Version 8** spreads the goals: position table `(0, -22, -24, -24, -18, -4, 6, 6,
     8, 10, 10, 12, 12)` (GK, CB, LB, RB, DMF, CMF, LMF, RMF, AMF, LWF, RWF, SS, CF;
     wingers were raised from `8` to `10` and CF lowered from `14` to `12` after the
     suggestion audit, so elite wingers sit nearer the CFs in the scoring charts),
     `SCORER_SHARPNESS = 0.05`, and the weight table is read with `gap >> 2` for goals
     too (version 7: `gap >> 1`, so every gap above 46 counted alike and no table could
     keep defenders low without a steep curve). Measured on the best eleven of the 499
     clubs of `ML saves/ML00000013 (before)`:

     | | version 7 | version 8 | after the audit |
     |---|---|---|---|
     | goals by CF | 50% | 32% | 30% |
     | SS, wingers, AMF | 37% | 41% | 44% |
     | CMF, DMF | 7% | 14% | 14% |
     | defenders | 6% | 12% | 12% |
     | best scorer's share of his club's goals: median / 90th / most | 47 / 66 / 88% | 30 / 38 / 57% | 28 / 35 / 55% |
     | Haaland / Kane / Mbappé | 83 / 68 / 40% | 48 / 37 / 25% | 45 / 34 / 22% |

     (The "~26% CF" that the settings comment of version 7 gave was not what real
     squads produced.) Assists are unchanged.
6. **Extra Time & Penalty Shootouts (`0x037062ca`, `0x037063bb`):** adds strength-scaled
   Extra Time goal chances (`ET_GOAL_SCALE`) and replaces vanilla's broken
   100%-home-win Penalty Shootout table with a symmetric OVR-weighted shootout
   (`PK_HOME_BIAS`, `PK_OVR_WEIGHT`).
7. **Disciplinary cards (`0x03708f45`):** awards position-weighted yellow and red cards
   (`CARDS`, `YELLOW_AVG`, `RED_PCT`) and feeds competition suspension tracking.
8. **Starting XI lineup, Attack/Defense split & condition/fatigue team strength (`LINEUP_STRENGTH`, `CONDITION_STRENGTH`, `ATTACK_DEFENSE_SPLIT`):**
   intercepts team strength lookups inside `outcome`, `score`, `et`, and `pk` (`CAVE_ET`
   `eff_strength`), looks up the team's active tactics (`fcn_03117d98` + `fcn_03822a29`)
   when `LINEUP_STRENGTH = true`, validates non-sentinel distinct indices in
   `tactics_rec + 0x248[0..10]` (falling back to the squad top-11 loop when invalid),
   evaluates each starter's positional OVR (`tactics_rec + 0x68[0..10]`, defaulting
   `> 12` or `slot > 0 and pos == 0` to `13`), replaces injured/suspended starters
   (`fcn_0385b771`) with the best eligible non-starters from the bench (a natural GK
   only ever fills a missing slot while the XI has no keeper, mirroring the game's
   own sub picker `fcn_03706d2e`, which never fields a GK in an outfield slot), and (when
   `CONDITION_STRENGTH = true`) adjusts each player's OVR via `player_eff_ovr` by
   condition arrow (`CONDITION_OVR = { -3, -1, 0, 1, 3 }`) and pre-match fatigue
   below `FATIGUE_THRESHOLD` (`72`, up to `FATIGUE_PENALTY = 5`). In version 7,
   `eff_strength` also accumulates positional Attack (`pos >= 6` weight 2, `CMF/unknown`
   weight 1) and outfield Defense (`pos 1..4` weight 2, `CMF/unknown` weight 1, excluding GK)
   averages plus starting `GK_eff` (using `GK_CONDITION_OVR`), returning `eax = overall_ovr` and
   `edx = (gk_eff << 16) | (def_ovr << 8) | atk_ovr` (other callers discard `edx`).
9. **Stamina-scaled fatigue (`STAMINA_FATIGUE`, `AI_FATIGUE`, version 5):** hooks
   `fcn_038556f1` (`0x038557dc` & `0x038557d6`) so simulated AI teams also accumulate
   match fatigue when `AI_FATIGUE = true`, scales drain by player stamina around 75
   (`STAMINA_WEIGHT`), keeps vanilla's `0.9x` GK factor, and adds `+30` minutes when
   a simulated fixture went to Extra Time (without double-counting played 120-minute
   fixtures).
10. **Simulated match injuries (`INJURY_PCT`, `INJURY_DAYS`, version 5):** extends
    `CARDS_HOOK` so each simulated match rolls `INJURY_PCT` (`3%` default) per team
    (when more than 7 outfield-capable healthy players are available), picks a random
    healthy outfield player weighted by low injury resistance and low post-match
    fitness, and sets injury duration in `[INJURY_DAYS[1], INJURY_DAYS[2]]` (`7..28`
    days default). Works even when `CARDS = false`.

### Settings & verification

All toggles and tuning parameters live at the top of `MLSimMatch.lua` and are validated
by `settings_fault()` before any byte is written. `python3 test_sim.py <PES2017.exe>`
runs 24 tests (all passing): generated block & Keystone byte-for-byte equivalence across
all 16 routines and 6 caves, 76 invalid-setting rejections, 9 partial-mode installs,
tamper detection across all 13 patch sites and 6 caves, real `PES2017.exe` execution for
all match-sim hooks (`ok 6`–`ok 19`, `ok 21`–`ok 23`), and coexistence with `MLMoney.lua`,
`MLTransfers.lua`, and `MLYear.lua` in any order (`ok 20`).
