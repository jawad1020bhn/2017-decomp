# Realistic Gameplay Update — ENHANCED: change log

Gameplay tuning applied on top of the `Realistic Gameplay Update` mod for PES 2017
(the CPK contains 427 files: match-AI JSON parameters, set-play .bin constants,
kickoff .fox files, and pad/feint XML+JSON tables). The base mod already added
more fouls, physicality and physical duels; this build sharpens the
*decision-making*, *positioning* and *tactics* layers on top of it, with an
**attacking bias**: teams push up, commit forward and trade space for attacking
presence rather than sitting in a tightened block.

**84 parameter edits across 18 files, in four passes:**

- Pass 1 — decision realism: shooting, passing, clearances, dribbling, CPU
  reaction timing, stamina, injuries, defending reads.
- Pass 2 — positioning & tactics: line heights, widths, cover discipline,
  marking zones and off-ball movement.
- Pass 3 — modern football research pass: pressing triggers and passing-lane
  cutting, line discipline, switches of play, central combinations, and
  per-level humanised timing.
- Pass 4 — attacking priority (user request): the defending block is NOT
  tightened; teams hold a high line with the ball, push the midfield up, keep
  forwards pinning the defence, and attack-aware teams commit further forward.

Deliverables:

- `Realistic Gameplay Update ENHANCED.cpk` — drop-in replacement CPK (verified
  byte-level: 409 of 427 entries identical to the original mod, 18 entries hold
  the edits below).
- `Realistic Gameplay Update_extracted/` — the same content as loose files (e.g.
  for Sider `livecpk` loading).

All changes are literal parameter edits inside the existing JSON structure:
comments, CRLF line endings and encodings are preserved, and every edit targets
exactly one occurrence (the build script aborts otherwise).

## Research basis (pass 3)

Pass 3 maps published football-tactics analysis onto the mod's parameters:

- **Compactness research** (kharasportsdaily.com — "Compactness in Football: 2
  Axes"): elite blocks compress vertically to 25-35 m (8-12 m between lines),
  narrow horizontally to 30-35 m on the ball side, defenders 5-7 m apart.
- **Defending-without-the-ball guide** (kharasportsdaily.com): the chain
  mechanism (unit slides together), pressing triggers (bad touch, backward pass).
- **Pressing / gegenpressing guides** (allaboutfootball.net; kharasportsdaily.com
  — "Counter-Pressing: 7 Principles"): the 0-5 s reaction window, 2-3 players
  swarming the ball winner, passing-lane blockage and cover shadows, selective
  triggers, rest defence behind the press.
- **Inverted-fullback / cutback research** (insideworldsoccer.com;
  kharasportsdaily.com): cutbacks preferred over volume crossing, half-space
  occupation, switches of play punish ball-side collapses.
- **Low-block & Total Football breakdowns** (soccerath.com; beefootball.com):
  central penetration triggers compression; the high line moves with the press.

## Changes by theme

### 1. Shot selection & finishing realism

- `common/match/ai/player/offence/ballplayerShoot.json`
  - Shot decision threshold 0.70 -> 0.75: slightly more selective shooting, fewer pot shots.
  - Max shooting distance 40 -> 34 m: fewer hopeless long-range punts.
  - Max shooting angle 90 -> 80 deg: fewer shots from absurd wide angles.
  - Distance weight in shot-course scoring 0.40 -> 0.45.
  - Ideal shot distance band max 35 -> 32 m.
  - Pressure weight in shot-course scoring 0.30 -> 0.40: finishing under pressure matters more.
  - Defender influence radius 2.0 -> 2.4 m when evaluating shot courses.
- `common/match/ai/player/offence/shoot.json`
  - Finesse (loop) shot speed variance up: less robotic curled finishes.
  - Chip shot speed variance up: more varied chips.

### 2. Passing safety under pressure

- `common/match/ai/player/offence/ballplayerPass.json`
  - Danger radius 6.0 -> 6.5 m: AI senses pressure slightly earlier.
  - Safe-pass target clearance 6.0 -> 6.5 m.
- `common/match/ai/player/offence/throughpass.json`
  - Through-ball lead max 15 -> 14 m: slightly shorter, better-timed runs.

### 3. Clearance urgency

- `common/match/ai/player/offence/ballplayerClear.json`
  - Clearance under pressure counts defenders up to 4.5 m (was 4.0).
  - Heavy-touch threshold 11.2 -> 11.5: slightly more loose balls contested.

### 4. Dribble safety when marked

- `common/match/ai/player/offence/ballplayerDribble.json`
  - Safety dribble triggers when a marker is within 5.5 m on his side (was 5.0).

### 5. Humanised CPU reactions per level

- `common/match/ai/cpuLevel.json`
  - Dribble-reaction delay +5..+0 frames by level: low levels react humanly slow.
  - Kick-reaction delay +4..+0 frames by level.
  - Pass-timing delay +3..+0 frames by level.
  - Shoot-timing delay +3..+0 frames by level.
  - Sliding tackles only from Professional up (was oddly enabled at level 3).

### 6. Stamina realism

- `common/match/ai/player/stamina.json`
  - Sprinting stamina cost 1.2 -> 1.35.
  - Defensive effort stamina cost 1.8 -> 1.95.
  - Jostling/duel stamina cost 1.0 -> 1.1.
  - Baseline stamina drain 10.3 -> 10.8.

### 7. Injury realism

- `common/match/ai/judge/injury.json`
  - Micro-injury damage threshold 190 -> 180.
  - Minor-injury threshold 260 -> 248.
  - Medium-injury threshold 310 -> 295.
  - Serious-injury threshold 450 -> 428.
  - Bruise threshold 290 -> 276.
  - Inflammation threshold 320 -> 305.
  - Laceration threshold 460 -> 438.
  - Muscle-tear threshold 500 -> 476.
  - Ligament threshold 600 -> 572.
  - Fracture threshold 890 -> 848.

### 8. Less robotic defending

- `common/match/ai/team/defence/defence.json`
  - Defensive prediction horizon 35 -> 33 frames: more human reads, real gaps appear.
  - Chain delay-pressing urge 57 -> 53.
  - Chain pressing urge 50 -> 46: less suffocating press chains.
- `common/match/ai/team/defence/defenceMark.json`
  - Marking prediction horizon 40 -> 37 frames.

### 9. Support spacing

- `common/match/ai/team/offence/passSupport.json`
  - Support ring outer radius 8.0 -> 8.4 m: slightly wider, more realistic spacing.

### 10. Team shape & line height (attacking)

- `common/match/ai/team/basePosition.json`
  - Back-four base width 23 -> 24 m: full-backs hold slightly wider to cover wide attacks.
  - DF line height in possession 0.30 -> 0.36: high line with the ball - attacking priority.

### 11. Attacking width & movement variety

- `common/match/ai/team/basePosition.json`
  - Attacking spread width 64 -> 65.5: a touch more width in possession (pairs with wider support ring).
  - Target-line X variation 0.20 -> 0.25: more organic drifting in base positions, less robotic lines.
  - Target-line Z variation 0.20 -> 0.25: same organic drift across the pitch.
- `common/match/ai/team/offence/spaceRun.json`
  - Chance-run recognition score 60 -> 55: forward runs into space recognised slightly more often.

### 12. Cover & space protection

- `common/match/ai/team/defence/defenceCover.json`
  - Cover-position prediction 15 -> 14 frames.
- `common/match/ai/team/basePosition.json`
  - Space-cover rate 0.40 -> 0.45: defenders drift a bit more to protect space.
  - Base-to-cover position shift 0.40 -> 0.45: shape leans slightly more toward cover positions.
  - Covering DF distance 6.6 -> 6.9 m: cover sits a touch deeper goal-side.
  - Allowed drift off the cover line 5.0 -> 4.5 m: cover line held more strictly.

### 13. Marking & midfield coverage

- `common/match/ai/team/defence/defenceMark.json`
  - Marking needed this far over the last line 2.0 -> 2.8 m: fewer unmarked strikers drifting off the back line.
  - Follow a drifting attacker up to 15 -> 16.5 m before releasing: fewer men lost in rotations.
  - Midfielder zone search range 5 -> 5.5 m: picks up runners in a slightly wider zone.
  - MF zone reach forward 10 -> 11 m: midfield engages opponents slightly higher up.

### 14. Modern pressing: triggers, lanes & swarming

- `common/match/ai/cpuLevel.json`
  - Pass-course-cut positioning enabled from Regular level up (was OFF at every level): defenders finally block passing lanes.
- `common/match/ai/team/defence/defence.json`
  - Press start line 10 -> 11: the press engages slightly higher up the pitch.
  - DF matchup reach 5.0 -> 5.5 m ahead of the final line: centre-backs engage forwards sooner.
  - MF matchup reach 5.0 -> 5.5 m: midfield line picks up runners earlier.
  - FW matchup reach 3.0 -> 3.4 m: the first presser engages the carrier slightly higher.
  - Matchup ball-position lookahead 15 -> 14 frames: reads the present a touch more.
  - Max close-down (shading) distance 7.0 -> 7.5 m: pressure applied from slightly further out.
  - Double-team/swarm behaviour enabled from Regular level up (2-3 players collapse on the ball like a real press).
- `common/match/ai/player/defence/press.json`
  - Pressing stance front distance 0.2 -> 0.25: engage marginally earlier in the press.

### 15. Line discipline & movement

- `common/match/ai/team/basePosition.json`
  - MF line height 0.40 -> 0.45: midfield pushes up - attacking priority.
  - Back-five base width 28 -> 29 m: consistent with the wider back four.
  - Zone-defence handoff check distance 4.0 -> 4.3 m: markers track a touch longer before relaying (chain mechanism).
- `common/match/ai/team/defence/defenceMark.json`
  - DFs continue marks +7 -> +7.5 m: centre-backs follow drifting forwards a fraction longer.
- `common/match/ai/team/defence/defenceCover.json`
  - Allowed drift off the cover line while covering 7.0 -> 6.5 m: the cover chain holds tighter.
  - Cover angle 73 -> 75 deg: covering defenders screen a slightly wider goal-side arc.

### 16. Ball progression, switches & crossing

- `common/match/ai/player/offence/ballplayerPass.json`
  - Side-change congestion sector 90 -> 100 deg: ball-side overloads get recognised sooner and play is switched.
  - Forward pass-lane check sector 15 -> 16 deg: slightly fewer blind vertical passes into blocks.
  - Safe-pass lane check sector 30 -> 32 deg: slightly wider lane scanning before safe passes.
- `common/match/ai/team/offence/passSupport.json`
  - Space-pocket recognition length 6.0 -> 6.5 m: support runs target slightly larger gaps (half-space pockets).
- `common/match/ai/player/offence/centering.json`
  - Cross max speed (high) 93 -> 88: deliveries float a touch more and are more contestable.
  - Cross max speed (low) 89 -> 85: same, softer cutback-style crosses.
- `common/match/ai/player/offence/shoot.json`
  - Shooting judgement lookahead 31 -> 30 frames: shot decisions read the present slightly more.

### 17. Central combination play

- `common/match/ai/team/offence/combination.json`
  - HOME central attacking area: no combination (kind 14 = COMB_KIND_MAX placeholder) -> WEDGE_02 (AMF-FW wall pass): central up-back-through combinations.

### 18. Humanised per-level timing

- `common/match/ai/cpuLevel.json`
  - Marking position updates +2..+0 frames by level: low levels re-shape marks with human delay.
  - Dribble-reaction delay +2..+0 frames by level: low-level dribblers hesitate like people.

### 19. Attacking priority

- `common/match/ai/team/basePosition.json`
  - Attacking stretch (FW-DF gap in offence) 53 -> 54.5 m: forwards pin the defence higher.
  - Overall forward push in offence 12 -> 13: the team commits slightly more bodies forward.
  - FW line height + press start 5.5 -> 5.8: the front line starts higher up.
  - Attack-awareness base X push (level 3) 2.5 -> 3.0: attack-minded teams step up more.
  - Attack-awareness base X push (level 4) 5.0 -> 6.0: full attacking commitment pushes further forward.

## Intentionally left unchanged

- `ball.json`, `foul.json` — the base mod's physics/contact values and its
  `MoreFouls=true` setting are already doing their job; tuning them further would
  fight the mod's identity.
- The defending block length (`lengthDf`), DF-line drop trigger and penetration
  compression stay at the base mod's values by request — this build prioritises
  attacking over defending.
- `combination.json` — the per-zone combination table got exactly one edit (the
  central attacking zone had NO combination assigned; it now plays WEDGE_02).
  The remaining pattern IDs are left alone: blind reshuffling risks scripted-
  animation mismatches.
- `lineBreak.json`, `avoid.json`, `goalKick.json`, `freekick.json`,
  `penaltykick.json`, `ballplayer.json` — movement utilities or ball-trajectory
  tables with ambiguous semantics; left for targeted experiments after playtesting.
- The 206 set-piece `.bin` constants and 167 kickoff `.fox` files — binary tables
  the game reads as blobs; preserved byte-identical (with their original CRC
  values and CRILAYLA compression).
- GK AI (`defenceGkAI`, `defenceGkAttack`, `offenceGk*`), pattern-selector and pad
  XML tables — scripted sequences rather than moment-to-moment decisions.

## What the tuning should feel like in-game

- Attacking comes first: teams hold a high line with the ball (DF line 0.36,
  midfield 0.45), stretch the pitch vertically, and attack-aware teams commit
  bodies forward instead of protecting a lead.
- CPU attackers pick their shots more carefully and from realistic distances;
  crossing is softer and more contestable; congested flanks trigger switches of
  play; central zones play up-back-through combinations.
- The front line presses higher (press start 5.8, matchup reach extended), cuts
  passing lanes from Regular difficulty up (a behaviour that was disabled at
  every level in the base files), and swarms the ball with 2-3 players.
- Defending stays structural — cover chains, marking relays, wider cover arcs —
  but the block is not tightened; it trades space for attacking presence.
- Lower CPU levels hesitate like people (dribble reactions, mark updates,
  first-touch timing); top levels stay sharp.
- Stamina drains a touch faster at match pace, and knocks turn into injuries a
  little more easily — physicality has consequences.

## Build / verify

```
python3 tools/gameplay_enhance.py        # apply the 84 parameter edits
python3 tools/cpk_pack.py "Realistic Gameplay Update.cpk" \
    -o "Realistic Gameplay Update ENHANCED.cpk"
```

`tools/cpk_pack.py` rebuilds the CPK in one pass from the original: unchanged
entries keep their original compressed blobs (CRILAYLA), edited entries are stored
raw (FileSize == ExtractSize — the same convention the original CPK uses for its
uncompressed entries), and the GTOC/ETOC packets are copied verbatim. All 427
entries were verified after the build (content equality against the original mod
plus the intended edits).

---

## Pass 5 — deep research & mass expansion (run #10: 114 edits, 26 files)

Run #10 adds **30 further edits (themes 20–26)** after a deep research round
(xG/PPDA data, PES AI-architecture analysis, set-piece science, transition
research). Totals: **114 tuned values across 26 files**.

### Deep research findings that shaped this pass

- **Expected-goals data**: penalties convert at 0.79 xG, six-yard-box headers at
  0.55, long shots at 0.03 — every extra metre of box entry is worth more than
  any long shot; blocked shots lose ~0.1 xG each. Themes 20–22 push box entries
  and shot-lane visibility accordingly.
- **PPDA / pressing science**: elite pressing teams allow 7.5–9 opposition
  passes per defensive action vs 15–20 for deep blocks; "pressure" begins at
  ~2 m. Theme 25 raises the aggressive-press factor; earlier passes already
  raised `pressRate`.
- **Set pieces = 25–30% of goals** (31–37% in academic studies); near-post
  inswinging corners carry the highest xG; committing extra bodies to dead
  balls is the strongest lever. Theme 24 commits +1 attacker to free kicks and
  unlocks quick direct free-kick restarts.
- **Transition windows**: the 5–8 seconds after a regain carry the best
  counter-attack chances. Theme 23 flattens long balls (faster switches),
  theme 26 keeps dribbling legs fresh while chasing defenders tire.
- **PES AI architecture** (implyingrigged PES-AI wiki + local decode of
  `common/match/constant/constant_match.bin`): the "QWESYS" container
  (16-byte header + zlib stream) packs 23 compiled modules (`ball.o`,
  `cpuLevel.o`, `setplayGuideCornerKick.o`, …). Local analysis showed these
  entries are **separate compiled constants, not compiled copies of the mod's
  JSONs** (e.g. `cpuLevel.o` holds only 4 scalars vs the JSON's per-level
  arrays), so the JSON parameter layer this mod edits remains the effective
  surface; the set-play guide constants were documented but left untouched
  (no schema).

### Theme 20 — line-breaking runs (`team/offence/lineBreak.json`, 8)

Runs that break the last line start deeper, commit earlier and accept more
body orientations — the highest-value pass in football.

| key | before → after |
|---|---|
| checkZ | 22.0 → 26.0 m (breakers start from deeper) |
| checkZ_good | 28.0 → 33.0 m |
| checkBallDist | 30.0 → 35.0 m (runs commit earlier) |
| checkBallDist_good | 35.0 → 41.0 m |
| checkLastLineDist | 7.0 → 9.0 m (line broken sooner) |
| checkLastLineDist_good | 10.0 → 13.0 m |
| angleDiff | 60.0 → 75.0 deg (wider run acceptance) |
| angleDiff_good | 100.0 → 110.0 deg |

### Theme 21 — feint activation area (`player/offence/ballplayerFeint.json`, 5)

Trick moves now fire over a much larger attacking zone — elite 1v1 dribbling to
break compact blocks.

| key | before → after |
|---|---|
| checkDistToEnemyGoalDoubletouch | 40.0 → 52.0 m |
| checkDistToEnemyGoalEracico | 40.0 → 52.0 m |
| checkDistFieldXZOnetime | 40.0 → 52.0 m |
| checkDistToEnemyGoalNearRoulette | 5.0 → 12.0 m (roulette at the box edge) |
| checkDistToEnemyGoalNearStepKick | 20.0 → 28.0 m |

### Theme 22 — shot & pass lane clearing (`player/offence/ballDodge.json`, 4)

Attackers read the ball path and clear blocking bodies earlier — every cleared
sight-line is worth ~0.1 xG.

| key | before → after |
|---|---|
| predictionJumpDist | 2.0 → 2.6 m |
| needDodgeDistCommon | 2.0 → 2.4 m |
| needDodgeDistBeforeKick | 4.0 → 5.0 m |
| shootCourseMargin | 2.5 → 3.1 m |

### Theme 23 — flatter long balls (`player/offence/longPass.json`, 2)

| key | before → after |
|---|---|
| highHeightMax | 9.0 → 7.8 m (flatter lofted balls arrive faster) |
| lowHeightMax | 5.0 → 4.2 m (driven switches stay head-height) |

### Theme 24 — set pieces & restarts (4)

| file / key | before → after |
|---|---|
| goalKick.json distMinBase | 20.0 → 18.0 m (short build-up option) |
| freekick.json longpassInplayUse | false → true (quick direct restarts) |
| basePosition.json freekickAttackAddNum | 1.5 → 2.5 (extra attacker on free kicks) |
| CoachAttackLevelChange.xml time gate | 2nd-half 30' → 20' (chase/protect logic earlier) |

### Theme 25 — attacking shape, runs & pressure (5)

| file / key | before → after |
|---|---|
| basePosition.json offencWideLength | 65.5 → 68.0 m (wider attack) |
| spaceRun.json chanceScore | 55 → 48 (runs trigger more often) |
| throughpass.json targetDistZMax | 14.0 → 17.0 m (retuned to 18 m in theme 27) |
| press.json aggresPressType | 1.2 → 1.5 (harder ball hunting) |
| rating.json dribbleRate | 10.0 → 13.0 (ball-carrying rewarded) |

### Theme 26 — stamina asymmetry (`player/stamina.json`, 2)

| key | before → after |
|---|---|
| dribbleTired | 0.4 → 0.32 (-20%: carriers keep beating men late) |
| defenceTired | 1.95 → 2.2 (+13%: chasing defenders tire first) |

### Standing design rules (unchanged)

- The defending block stays at the base mod's shape: `lengthDf` 32.3,
  `dfLineBack` 10.0, `dfLineCloseRate` 0.7 (user instruction: attack priority,
  no tighter block). Base-mod identity preserved: ball.json, foul.json
  (MoreFouls) untouched. Injury thresholds stay lowered (= injuries happen
  more easily). Every edit is an anchored, single-occurrence replacement so a
  failed anchor aborts the build.

---

## Pass 6 — through-ball penetration engine (run #11: 136 edits, 26 files)

Retunes the entire through-ball chain — for **both human (manual) and CPU
play** — so through balls actually split and beat the defensive line. 24
parameters (22 new + 2 retuned) in `throughpass.json` (the receive/flight
engine) and `ballplayerPass.json` (the AI's forward-pass decision layer).

### The penetration model (the calculation behind every number)

Design constants: receiver sprint **v_r ≈ 8.5 m/s** (30.6 km/h fast forward),
defender sprint **v_d ≈ 7.5 m/s**, defender reaction **2–6 frames**
(0.033–0.10 s at 60 fps), ball travel measured in m, `targetDistSec` is the
design arrival window where **lead ≈ v_r × targetDistSec**.

1. **Pass vs interception race.** A 20 m through ball at the old speed floor
   (25 m/s, ~90 km/h) arrives in ≈ 0.83 s; a defender 6 m from the landing
   spot needs 0.10 + 6/7.5 ≈ **0.90 s** — only a 0.07 s margin, so well-read
   passes get cut out. Raising the floor to **29 m/s** cuts arrival to
   ≈ 0.75 s: the pass wins the race by ~0.15 s. The ceiling is held in place
   (adjust 25 → 22 ⇒ max ≈ 51 m/s): only the weak taps got faster.
2. **Lead-depth vs reachability.** Landing points moved from 10–15 m to
   **11–18 m**. Consistency check: 8.5 m/s × **2.1 s** = 17.9 m ≈ the new
   18 m max — the arrival window (`targetDistSec` 1.9 → 2.1 s) is exactly the
   time the striker needs to reach the deeper point, and run persistence
   scales +20% (25→32 / 50→60 frames) to carry him there at full sprint
   (pre-receive dash commitment 0.5 → 0.65 s).
3. **Gap detection.** Two defenders standing 3 m apart at 15 m from the ball
   leave an angular corridor of 2·atan(1.5/15) ≈ **11.4°**. The pass-search
   cone floor rises 7.3° → **8.2°** with growth 2.0 → 2.4°/step, so a
   split-lane now fits inside the first or second scan step instead of being
   missed; the AI's forward-lane sector widens 15° → **18°** (skilled-passer
   bonus 10° → 12°).
4. **Bending around blockers ("wall" logic).** The blocker's movement
   prediction horizon extends 100 → **128 frames** (+28%) and the bend cone
   45° → 50°: the pass is aimed at where the defender *will* be, cutting
   through the future gap rather than the present one.
5. **Arrival quality.** The no-bounce band extends 23 → 26 m and the
   one-bounce band 40 → 44 m: more through balls arrive clean for a
   first-time finish instead of hanging as slow fly passes defenders can
   recover against.
6. **Human (manual) pass feel.** Speed floor 25 → 29 m/s (same race math),
   ground launch angle 4.0° → 3.2° (flatter = arrives ~10% sooner, less read
   time for the keeper), chip-through angle 28° → 25° (harder for the keeper
   to sweep).

### Theme 27 — through-ball parameters

`common/match/ai/player/offence/throughpass.json`:

| key | before → after |
|---|---|
| targetDistZMin | 10.0 → 11.0 m (shallowest lead still lands beyond the line) |
| targetDistZMax | 15.0 → 18.0 m (final; via 14 → 17 → 18 retunes) |
| targetDistMin | 8.0 → 9.0 m |
| targetDistMax | 15.0 → 18.0 m (radial band matches the Z depth) |
| targetDistSec | 1.9 → 2.1 s (8.5 × 2.1 = 17.9 ≈ 18 m reachability) |
| moveContinueFrameMin | 25 → 32 frames |
| moveContinueFrameMax | 50 → 60 frames |
| moveContinueFrameAdjustZposi | 15 → 18 frames |
| dashMoveSecForPassgetMin | 0.5 → 0.65 s (sprint, not cruise, at arrival) |
| boundDist0 | 23 → 26 m (no-bounce arrival band) |
| boundDist1 | 40 → 44 m (one-bounce band; fewer fly passes) |
| wallTargetDistFrameMax | 100 → 128 frames (blocker prediction +28%) |
| wallTargetAdjustAngleWidth | 45 → 50° |
| angleWidthMin | 7.3 → 8.2° (11.4° split corridor now inside the scan) |
| angleAddValue | 2.0 → 2.4°/step |
| manualPassSpeedBase | 25 → 29 m/s (race win 0.83 s → 0.75 s) |
| manualPassSpeedAdjust | 25 → 22 (ceiling held ≈ 51 m/s) |
| manualPassAngleYBase | 4.0 → 3.2° |
| manualPassAngleYAdjust | 6.0 → 5.0° |
| manualFlyPassAngleYAdjust | 28 → 25° |

`common/match/ai/player/offence/ballplayerPass.json` (AI decision layer):

| key | before → after |
|---|---|
| passFrontDistFar | 20 → 24 m (targets sought 4 m deeper) |
| passFrontDistNear | 5 → 6 m (fewer toy through balls) |
| checkSectorWidthFront | 15 → 18° (retuned from 16) |
| checkSectorWidthFrontAdd | 10 → 12° (elite passers see tight splits) |

Untouched by design: `passgetMoveLateFrame` stays **-24** (the
don't-trap/offside margin comment), and the defending-block values remain at
base (`lengthDf` 32.3 / `dfLineBack` 10.0 / `dfLineCloseRate` 0.7).

---

## Pass 7 — structural additions, not numbers (run #12: 144 edits, 29 files)

Tier 1+2 from the "real additions" plan: new playbook content, new skill-move
commands, and rewired decision trees. Standing instruction enforced
throughout: **always prioritize attacking; the AI never parks the bus.**

### Theme 28 — structural content

**1. Combination playbook rebuilt** (`ai/team/offence/combination.json`) —
the engine ships 14 named team-play patterns (wedge wall-passes, decoy+burst
runs, near/far cross runs, cutbacks, full-back overlaps, side changes). The
original map left 3 zones dead (`kind 14` = NONE) and used unfinished slots.
All 22 zones (11 per side) now run attacking plays:

| zones | plays |
|---|---|
| wide (Area00/01) | CROSS_CROSS (near/far burst onto crosses) + CROSS_RETURN (cutbacks — the highest-xG cross) |
| half-spaces (02/04) | CROSS_01 (line crosses) / DECOY_00-01 (decoy + burst) |
| wings (05/07) | OVERLAP (full-back overlap) |
| centre (03/06/10) | SHOOT_COURSE + WEDGE_02 |
| zone 08/09 | WEDGE_00/01 (same-side / opposite-side wall pass + burst) |

**2. Three NEW skill-move commands** (`pad/feint.json`) — filled 3 of the 7
reserved "予備バッファ" dummy command slots:

| input (while holding L2) | move |
|---|---|
| right stick full rotation | roulette (new route) |
| right stick flick-and-return forward (0°) | double touch |
| right stick flick-and-return backward (180°) | heel lift |

Collision analysis: the L2 namespace previously held only `ボディフェイント`
(flick-and-return at ±90° ±22.5° support). The new commands use 0°/180° lanes
and a rotation gesture, so no existing input is shadowed; 4 dummy slots remain
for future moves.

**3. GK behaviour trees rewired toward attack**:
- `offenceGk.xml`: the "do nothing" answer → **LONG_PASS** (the keeper always
  launches the counter) and the "return to base" answer → **DRIBBLE**
  (sweeper keeper carries the ball out — an extra outfield player in attack).
- `defenceGkAI.xml`: the "late block" answer (sits on the line) → **KP_PRESS**
  (sweeps through balls early). Shot-blocking (`KP_BLOCK`) untouched.

**4. Coach attack states — the bus is retired** (`CoachAttackLevelChange.xml`):
- the DEFENSIVE answer state → **BALANCE** (the team never drops into a
  parked block),
- offensive-push trigger: goal difference **+2 → +1** (trailing by one now
  triggers the attacking push),
- relaxation threshold: **-2 → -3** (only a 3-goal cushion relaxes the push;
  at 1-2 up the team keeps attacking).

### Documented but not yet edited (RE continues)

- `constant_positionCK.bin` decoded (QWESYS+zlib, 10 entries matching the 10
  `positionCK_*.fox` corner routines) — the entry schema is mapped but the
  routine constants need value-matching before edits are safe.
- `team_action/team_id_*.bin` (22 team presets) — container identified
  ("WESYS" variant header), payload schema undecoded.
- `situation/position*.bin` and the `.fox` choreography files — binary
  routine data, full RE out of scope for this pass.

## Pass 8 — the hidden off-ball movement modules (run #13: 144 regex + 57 binary value edits, 30 files)

`constant_team.bin` holds the game's off-ball movement engine: the dummy/decoy
run system (`diagonalRun.o`), overlap triggers, break-away-from-marking logic
(`pullAway.o`), run-dispatch quotas (`selectorVision.o`) and a named attacking-
pattern switchboard (`subConcept.o`). The base mod ships these untouched and,
crucially, **all 21 attacking concepts in `subConcept.o` disabled (0)**. This
pass decodes the container, grounds every field in documented community
research, and turns the movement engine on.

### Schema sources (vendored in tools/mappings/)

- the4chancup/pes-gameplay-editor `pes_ai/mappings/18/team/*.txt` — byte-exact
  field names/offsets (diagonalRun, overlap, pullAway, selectorVision,
  lineBreak, spaceRun, subConcept).
- implyingrigged wiki `User:Aoba/PES2021_dt18` — value tables: Dummy Runner's
  4 special values in diagonalRun.o (distXBpMax 8->15, fanAngle 20->40,
  fanFar 5->8, fanAngleHalfMargin 5) and the overlap trigger table
  (addCount 1, addCount_adverse 0, checkMiddleLineX -1, checkMiddleLineX_adverse
  -5, checkTopLineX -18, checkTopLineX_adverse -25, style 0) — this table
  matches our 32-byte `lineBreak.o` entry **verbatim, all 7 fields**.
- `User:MarcoZ/dt18_Files_Breakdown` + `User:Aoba/PES2021_Engine_Research`:
  diagonalRun = dummy runs to displace the defence; pullAway = breaking away
  from markers (Goal Poacher, dispatch 47); selectorVision = how much movement
  gets dispatched per run type; lineBreak/spaceRun `_good` variants = Hole
  Player / Goal Poacher / Prolific Winger bonuses; actions 29-47
  (SPACE_RUN_*, LINE_BREAK, DIAGONAL_RUN, OVERLAP_SB/CB, PULL_AWAY...).
- Real-life grounding (tracking data, CL final 2023 wing-back study): overlapping
  runs average **16.75 m (Dumfries) / 25.12 m (Dimarco) at ~19.9 km/h avg,
  29-31 km/h top speed**, made **often and early**; third-man runs score
  distance 50% / vertical gain 30% / speed 20% — coordinated multi-runner
  movement is the modern game.

Container: `constant_team.bin` = 16-B QWESYS header + zlib payload (3,760 B),
16 named entries (contiguous 0x500..0xeb0, sizes x16; teamId.o = external ref
to `team_action/team_id_01090.bin`). Values live inside the zlib stream, so
edits go through the new `tools/qwesys.py`: decompress -> assert old value ->
patch -> recompress -> rebuild header. 57 patches, every one asserted
old->new, type-preserving per cell (u32 vs f32 exactly as shipped).

### The 57 changes

1. **subConcept.o — the dormant attacking repertoire (21 booleans 0 -> 1).**
   PES 2017 holds the enum-prefix subset of the concept table; all 21 are
   attacking/possession patterns (the ForeCheck/Retreat/NetDefence/SealOff/
   DoublePress defensive concepts only exist in later games' enum tail).
   Now enabled: PossessionMfJoinDefenceLine, ChangeTriangle, CounterAfterGkCatch,
   SideCounter, FastCounter, LongPassFlick, LongPassLayOffAndToSide,
   LongPassLayOffAndBreakthroughToDefenceLine, LongPassLayOffAndShoot,
   EarlyCross, ForwardPassAndLayOff, PassAndGoTriangle, PenetrateInsideOneTwo,
   SpaceRunToCenterForCreateSideSpace, ToCenterDecoySide, SpaceRunRelaySquarePass,
   DisorderByOneTwo, SideCrossRunning, SideRunMakeSpace,
   SpaceRunToCreateSpaceForOneTouchPass, CreateSpaceOneTwo. These are situation
   repertoire toggles (selected contextually by the concept engine), not spam
   triggers — the AI now has its full modern movement vocabulary available.

2. **selectorVision.o — run dispatch thresholds -30% (30 values, 6 run types x
   5 variants).** offerNum_<type>1..5 = the score bar each run variant must
   clear to be offered (same semantics as spaceRun chanceScore, already lowered
   55 -> 48 in Pass 5); lower = dispatched in more situations, variant ordering
   preserved so rare/daring variants stay relatively rarer:
   diagonalRun [17,21,20,25,1] -> [12,15,14,18,1]; lineBreak [50,2,4,12,17] ->
   [35,1,3,8,12]; pullAway [20,25,30,90,110] -> [14,18,21,63,77];
   spaceRunChance [4,6,5,7,6] -> [3,4,4,5,4]; spaceRunCounter [10,19,23,5,10] ->
   [7,13,16,4,7]; spaceRunSecondLine [100,15,2,2,18] -> [70,11,1,1,13].

3. **lineBreak.o (the overlap-run trigger table) — runs trigger earlier and one
   runner persists under pressure.** addCount_adverse 0 -> 1 (even when pressed
   one player still overlaps); checkMiddleLineX_adverse -5 -> -3;
   checkTopLineX -18 -> -12; checkTopLineX_adverse -25 -> -18. Matches the
   tracking-data picture: modern wing-backs go early and often (16.75-25.12 m
   average runs), and adverse situations only shift the trigger slightly
   deeper instead of switching the run off.

4. **diagonalRun.o — the dummy/decoy fan was OFF -> active.**
   fanAngleHalfMargin_dummyRunner 0 -> 5 (= the normal margin, per the wiki
   table where margin stays 5); fanAngle_dummyRunner 0 -> 6 (= 2 x the PES 2017
   fanAngle of 3, mirroring the documented Dummy Runner doubling 20 -> 40).
   Dummy Runner style players now make real decoy runs that drag defenders out
   of the line.

### Verification (run #13)

- 144 regex EDITS replayed on the pristine CPK -> byte-exact match of all 29
  rebuilt entries; 57 binary patches verified in the rebuilt entry with only
  60 payload bytes differing, all inside patch targets; 21 concept toggles
  confirmed = 1 in the built CPK.
- Entry index intact (16 names, regions 0x500..0xeb0); TOC rows/order and the
  `?></@#b.txt` dummy entry preserved; GTOC/ETOC byte-identical.
- Guards intact: `passgetMoveLateFrame : -24` (throughpass.json), `lengthDf :
  32.3` / `dfLineBack : 10.0` / `dfLineCloseRate : 0.7` (basePosition.json).

### Intentionally untouched in constant_team.bin

- `pullAway.o` (6 role ladders), `overlap.o` sub-records (208 B), `spaceRun.o`
  flag table and `support.o` pointer record — layouts version-shift vs the
  available mappings; documented in tools/mappings/README.md instead of blind
  edits. The defensive trio (`defence.o`, `defenceCover.o`, `defenceMark.o`)
  is untouched per the standing no-tighter-block rule.

## Pass 9 — set pieces: the corner routines get their full attacking shape (run #14: 144 regex + 84 binary value edits, 34 files)

Set pieces produce 25-30% of all goals (pass 3 research) and the base mod
ships the corner routines at partial commitment: the 4- and 5-man families
leave the slot-5/slot-6 runners unstationed even though the shared movement
library carries full runs for them (slot 5's record holds 21 keyframes — the
most elaborate run in the file). This pass decodes the whole set-piece stack
and stations those runners everywhere.

### Architecture (forensics)

Set pieces run on three data layers, all inside the CPK:

1. **`constant/constant_positionCK.bin`** (QWESYS, 10 entries × 368 B) — the
   station table: 22 slot records of `(flag, id, X, Z)`. The lowest active
   slot in each routine sits at the penalty-arc "D" (~28, -2) = the second-
   ball station; the rest spread through the box (near-post lane ~(38,-8),
   penalty spot, far post). Family `N_v` = N attackers × variant v; variants
   differ in the station mix (variant 3 = the short-corner shape).
2. **`situation/positionCK*.bin`** (28,632 B raw) — the shared run library:
   22 slot records × 1,280 B (35 keyframe groups × 36 B + tail). The tail
   carries two run-target clusters per slot: `(flag, 0xfefefe, 0, x, y, z)` —
   the arrival point of the run. All nine situation bins share the library
   and differ only in these clusters + tiny per-routine tweaks (49-95 bytes).
   Record 5's run = the edge→box crash (6_1's target (36.33,-10.74) =
   the near-post zone); record 6's = the check-out to the edge.
3. **`ai/team/positionCK/*.fox`** — Fox-XML authoring copies of the routine
   setups (A08-A11 = the participants). Proven stale at runtime: 4_1.fox's
   transforms equal the *base* routine's stations and 4_3.fox's equal 4_2's —
   one generation behind the shipped bins. Left untouched (documentation
   only); the bins are the runtime truth.

### The changes (theme 30)

Every routine now stations the full 6-man attacking shape (real-life elite
commitment: 5-6 in the box, 2 back — pass 3 set-piece research):

| routine | was | now |
| --- | --- | --- |
| positionCK (base) | 4 stations | 6 (slot5 + slot6 stationed) |
| positionCK_4_1 / _4_2 | 4 | 6 |
| positionCK_4_3 / _5_1 / _5_2 | 5 | 6 |
| _5_3 / _6_1 / _6_2 | 6 | 6 (unchanged) |

- **9 station activations** in constant_positionCK.bin (27 asserted values):
  slot 5 = the edge-of-box second-ball starter (28.0-28.4, -1.7..-2.0 —
  matching the 6-man families' own slot-5 stations), slot 6 = the box
  runner (38.7-39.1, -7.9..-8.4). Each is a real addition: the run library
  already carries slot 5's 21-keyframe crash and slot 6's check-out for
  every bin.
- **3 run-target clusters** filled where the library had none (slot 5 in the
  4_x bins, byte-offset patches with old-bytes asserts at file offset 7896):
  4_1/4_3 receive 6_1's donor target (36.33, 0, -10.74) — the near-post
  crash arrival; 4_2 receives 6_2's (38.68, 0.836, -8.22). base/5_1/5_2
  already had targets and keep them.
- Resulting shape per corner: edge crash runner + box check-out man + the
  routine's own near-post/penalty-spot/far-post stations = six committed
  attackers, ground coverage for second balls at the box edge (xG research:
  six-yard box 0.55, edge-of-box second balls = the modern standard).

### Verification (run #14)

- 144 regex EDITS replayed on the pristine CPK → byte-exact in 29 files;
  84 binary patches (57 constant_team + 27 constant_positionCK) byte-exact
  with only 136 payload bytes differing, all inside targets; 3 raw cluster
  patches byte-exact with diffs confined to their 20-B spans.
- TOC rows/order (427) and the `?></@#b.txt` dummy preserved; GTOC/ETOC
  byte-identical; guards intact (passgetMoveLateFrame -24; lengthDf 32.3 /
  dfLineBack 10.0 / dfLineCloseRate 0.7).
- New builder capability: `RAW_EDITS` (offset-based patches with old-bytes
  asserts) for non-QWESYS entries alongside the regex and qwesys lanes.

### Intentionally untouched

- `constant_positionPK.bin` / `constant_positionKickOff*.bin` — PK rush and
  kickoff station tables decoded (PK slot 11 = the GK on the line, slots
  12-21 = the encroachment wall; kickoff stations rules-locked to the own
  half) but left as shipped: rare moments, and the marginal gain did not
  justify touching them.
- The `positionCK_6_3.o` external-ref record and the defensive trio in
  constant_team.bin (standing no-tighter-block rule).

## Pass 8 addendum — offerNum: both interpretations (documented before the chosen reading)

The selectorVision `offerNum` cells can be read two ways:

1. **Threshold reading** — the value is a *count threshold*: the engine fires the run-type only when
   that many qualifying options are present. High values = the run is rare (needs a crowd of options);
   low values = it fires often.
2. **Player-count reading** — the value is *how many players* the mechanism offers/pulls: the engine
   recruits N players into the movement (selectorVision's wiki semantics: "amount of players pulled away").
   High values = more bodies committed to the move; low values = a single runner.

**Chosen reading: the threshold reading.** Evidence: the cells sit in per-state rows alongside
distance/rate constants (the same tables whose members are thresholds like `stateCount`, `addCount`,
`checkFrameEnd`), the values span 1–77 with per-run-type profiles that correlate with run frequency
(diagonalRun [12,15,14,18,1] high-throughout-states vs pullAway [14,18,21,63,77] rare-last-states),
and the wiki's "pulled away" phrasing describes the *effect* of the run, not the cell's unit.
Under this reading we scaled every offerNum by x0.7 (floor 1): lower threshold = the attacking
movement library fires more often. The player-count reading would have implied the opposite
direction (fewer bodies), so the direction of the edit follows explicitly from the chosen reading.

---

## Pass 10 — Theme 31: the realism layer (final version)

The last pass brings the two least-realistic surfaces of the sim up to real-life football, plus the
default team-action script that every team inherits.

### Penalty realism (penaltykick.json)
- `shootSpeedKPHMin: 95.0 -> 82.0` — the old floor forced power-only finishes. Real placed penalties
  travel ~75-85 KPH (the modern run-up-and-pass style). 82 keeps the game mix: placement now exists.
- `shootSpeedKPHMax: 125.0 -> 128.0` — real top-end PK strikes (Ronaldo/Bale-style) sit at 125-130 KPH.

### Penalty keeper realism (defenceGkAutoPk.xml)
- `CheckBallSpeed` hold-vs-parry threshold `60 -> 85` KPH. Real GK technique: hold anything up to
  ~85 KPH, parry/block above. With the new 82-128 PK band, softly-placed penalties can be held while
  power finishes are always parried — exactly the real-life split.

### Match rating realism (pesSmart.o @ constant_match.bin +13856, 4 TEXT formulas)
The engine's per-player rating formulas carried two dead terms (weight 0.0):
- `-  0.0  * ( StatsPlayerFoul() - StatsPlayerOffSide() )` -> `-  2.0  * (...)` in all 3 field
  formulas: fouls were literally free. Real player ratings penalise ill-discipline; now every foul
  beyond the offside count costs 2 rating points (the GK formula has its own card terms already).
- Formula 1 only: `+  0.0  * StatsPlayerPassShortSuccess()` -> `+  1.5  * ...` — build-up passing
  was unrewarded in the most-used formula while formulas 2/3 already paid 1.5 per completion.
  Now consistent: short-pass completion = 1.5 pts everywhere.

Full weight profile preserved (goals 80 / assists 40 / pass-accuracy blocks / saves 15 / cards),
including the deliberate PK-goal discount (-18) and the clearance/miss penalties.

### Default team-action script (team_id_01090.bin, referenced by support.o as the default)
- `EnemyLastLine() + DefenceSide() * 5.0` -> `* 2.5`: the default role station sits 2.5 m off the
  opponent's last line instead of 5 m — playing on the shoulder like real forwards (and like the
  engine's own Goal Poacher archetype, which "pushes up to the offside line"). Universal: every team
  without a custom script inherits it.

### Documented deep decodes (mapped, deliberately not blind-tuned)
- **team_action/team_id_*.bin x22**: per-team Esp formula scripts (`RoleN_StateM: QUALIFY/RUN/STRAIGHT`
  trees with positioning formulas like `PlayerBaseX() + DefenceSide()*13.0`, `Sign(PlayerTransZ())*(PenaltyAreaZ()-4.0)`).
  The values are already realistic (wide roles hug `FieldZ()-1.0`, channels sit 4 m outside the box);
  the full constant census (00070 [1,4,13] ... 12541 [2,3,5]) is the team-identity layer — left as-is
  rather than blind-tuned.
- **throwin.o** (112 B): 28 integer cells (frame/distance ladder 450/1000/400/360/30/600/...); no
  public mapping — untouched.
- **teamEmotion.o** (128 B): momentum thresholds (32/25/15/5, 20/10/10/50/35 + 0.5/0.6 strengths);
  no public mapping — untouched.
- **freekick.json**: delivery band (long-pass FK 30-90 KPH, inplayUse on from Pass 5) already realistic.

### Verification (run #15)
147 EDITS + 84 BIN + 3 QRAW + 3 RAW replayed byte-exactly from the pristine CPK; 427 TOC rows with
name/ID/CRC/UserString columns preserved in order; GTOC/ETOC verbatim; all untouched entries
byte-identical; guards (`passgetMoveLateFrame -24`, defensive trio 32.3/10.0/0.7) confirmed.

**Final state: 31 themes, 237 anchored patches across 38 entries (26 AI text, 13 binary layers),
one CPK. This is the final version.**
