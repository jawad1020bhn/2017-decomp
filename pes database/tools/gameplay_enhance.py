#!/usr/bin/env python3
"""Realistic Gameplay Update — enhancement pass (v2).

Applies targeted gameplay-parameter edits to the extracted CPK contents in
'pes database/Realistic Gameplay Update_extracted/'. Every edit is a precise,
anchored literal replacement; all other bytes (comments, CRLF, encodings) are
untouched. Each pattern must match exactly once or the script aborts.

Themes:
  1. Shot selection & finishing realism   (ballplayerShoot.json, shoot.json)
  2. Passing safety under pressure        (ballplayerPass.json, throughpass.json)
  3. Clearance urgency & heavy touches    (ballplayerClear.json)
  4. Dribble safety when marked           (ballplayerDribble.json)
  5. Humanised CPU reactions per level    (cpuLevel.json)
  6. Stamina realism                      (stamina.json)
  7. Injury realism                       (injury.json)
  8. Less robotic defending               (defence.json, defenceMark.json, defenceCover.json)
  9. Wider support spacing                (passSupport.json)
"""
import re
import sys
import os

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "..", "Realistic Gameplay Update_extracted")

# (file, regex anchored at field name, replacement with \1, note)
EDITS = [
    # ---- 1. shot selection & finishing -------------------------------
    ("common/match/ai/player/offence/ballplayerShoot.json",
     rb'("shootDecidePoint"\s*:\s*)0\.7\b', rb'\g<1>0.75',
     "shot decision threshold 0.70 -> 0.75: slightly more selective shooting, fewer pot shots"),
    ("common/match/ai/player/offence/ballplayerShoot.json",
     rb'("shootRageDist"\s*:\s*)40\.0\b', rb'\g<1>34.0',
     "max shooting distance 40 -> 34 m: fewer hopeless long-range punts"),
    ("common/match/ai/player/offence/ballplayerShoot.json",
     rb'("shootRangeAngle"\s*:\s*)90\.0\b', rb'\g<1>80.0',
     "max shooting angle 90 -> 80 deg: fewer shots from absurd wide angles"),
    ("common/match/ai/player/offence/ballplayerShoot.json",
     rb'("effectRateByDist"\s*:\s*)0\.4\b', rb'\g<1>0.45',
     "distance weight in shot-course scoring 0.40 -> 0.45"),
    ("common/match/ai/player/offence/ballplayerShoot.json",
     rb'("distMax"\s*:\s*)35\.0\b', rb'\g<1>32.0',
     "ideal shot distance band max 35 -> 32 m"),
    ("common/match/ai/player/offence/ballplayerShoot.json",
     rb'("effectRateByEnemy"\s*:\s*)0\.3\b', rb'\g<1>0.4',
     "pressure weight in shot-course scoring 0.30 -> 0.40: finishing under pressure matters more"),
    ("common/match/ai/player/offence/ballplayerShoot.json",
     rb'("radiusEnemyCircleMax"\s*:\s*)2\.0\b', rb'\g<1>2.4',
     "defender influence radius 2.0 -> 2.4 m when evaluating shot courses"),
    ("common/match/ai/player/offence/shoot.json",
     rb'("loopSpeedDelta"\s*:\s*)47\.0\b', rb'\g<1>50.0',
     "finesse (loop) shot speed variance up: less robotic curled finishes"),
    ("common/match/ai/player/offence/shoot.json",
     rb'("chipSpeedDelta"\s*:\s*)39\.0\b', rb'\g<1>43.0',
     "chip shot speed variance up: more varied chips"),

    # ---- 2. passing safety -------------------------------------------
    ("common/match/ai/player/offence/ballplayerPass.json",
     rb'("dangerEnemyDist"\s*:\s*)6\.0\b', rb'\g<1>6.5',
     "danger radius 6.0 -> 6.5 m: AI senses pressure slightly earlier"),
    ("common/match/ai/player/offence/ballplayerPass.json",
     rb'("passSafetyTargetEnemyDist"\s*:\s*)6\.0\b', rb'\g<1>6.5',
     "safe-pass target clearance 6.0 -> 6.5 m"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("targetDistZMax"\s*:\s*)15\.0\b', rb'\g<1>14.0',
     "through-ball lead max 15 -> 14 m: slightly shorter, better-timed runs"),

    # ---- 3. clearance urgency ---------------------------------------
    ("common/match/ai/player/offence/ballplayerClear.json",
     rb'("clearCheckEnemyDistFar"\s*:\s*)4\.0\b', rb'\g<1>4.5',
     "clearance under pressure counts defenders up to 4.5 m (was 4.0)"),
    ("common/match/ai/player/offence/ballplayerClear.json",
     rb'("clearBadTrapSpeed"\s*:\s*)11\.2\b', rb'\g<1>11.5',
     "heavy-touch threshold 11.2 -> 11.5: slightly more loose balls contested"),

    # ---- 4. dribble safety -------------------------------------------
    ("common/match/ai/player/offence/ballplayerDribble.json",
     rb'("distNearEnemyEnemySide"\s*:\s*)5\.0\b', rb'\g<1>5.5',
     "safety dribble triggers when a marker is within 5.5 m on his side (was 5.0)"),

    # ---- 5. humanised CPU reactions (6 levels: Beginner..Superstar) ---
    ("common/match/ai/cpuLevel.json",
     rb'("dfDribbleReactionAddWait"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t5, \t\t\t\t4, \t\t\t\t3, \t\t\t\t2, \t\t\t\t1,\t\t\t\t0\t\t\t\t]',
     "dribble-reaction delay +5..+0 frames by level: low levels react humanly slow"),
    ("common/match/ai/cpuLevel.json",
     rb'("dfKickReactionAddWait"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t4, \t\t\t\t3, \t\t\t\t2, \t\t\t\t2, \t\t\t\t1,\t\t\t\t0\t\t\t\t]',
     "kick-reaction delay +4..+0 frames by level"),
    ("common/match/ai/cpuLevel.json",
     rb'("bpPassTimingAddWait"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t3, \t\t\t\t3, \t\t\t\t2, \t\t\t\t2, \t\t\t\t1,\t\t\t\t0\t\t\t\t]',
     "pass-timing delay +3..+0 frames by level"),
    ("common/match/ai/cpuLevel.json",
     rb'("bpShootTimingAddWait"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t3, \t\t\t\t2, \t\t\t\t2, \t\t\t\t1, \t\t\t\t1,\t\t\t\t0\t\t\t\t]',
     "shoot-timing delay +3..+0 frames by level"),
    ("common/match/ai/cpuLevel.json",
     rb'("dfSlidingTackle"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t0, \t\t\t\t0, \t\t\t\t0,\t\t\t\t1, \t \t\t1,\t\t\t\t1\t\t\t\t]',
     "sliding tackles only from Professional up (was oddly enabled at level 3)"),

    # ---- 6. stamina realism ------------------------------------------
    ("common/match/ai/player/stamina.json",
     rb'("dashTired"\s*:\s*)1\.2\b', rb'\g<1>1.35',
     "sprinting stamina cost 1.2 -> 1.35"),
    ("common/match/ai/player/stamina.json",
     rb'("defenceTired"\s*:\s*)1\.8\b', rb'\g<1>1.95',
     "defensive effort stamina cost 1.8 -> 1.95"),
    ("common/match/ai/player/stamina.json",
     rb'("jostleTired"\s*:\s*)1\.0\b', rb'\g<1>1.1',
     "jostling/duel stamina cost 1.0 -> 1.1"),
    ("common/match/ai/player/stamina.json",
     rb'("metabolism"\s*:\s*)10\.3\b', rb'\g<1>10.8',
     "baseline stamina drain 10.3 -> 10.8"),

    # ---- 7. injury realism (thresholds ~5% lower) --------------------
    ("common/match/ai/judge/injury.json",
     rb'("levelDamageMicro"\s*:\s*)190\b', rb'\g<1>180', "micro-injury damage threshold 190 -> 180"),
    ("common/match/ai/judge/injury.json",
     rb'("levelDamageMinor"\s*:\s*)260\b', rb'\g<1>248', "minor-injury threshold 260 -> 248"),
    ("common/match/ai/judge/injury.json",
     rb'("levelDamageMiddle"\s*:\s*)310\b', rb'\g<1>295', "medium-injury threshold 310 -> 295"),
    ("common/match/ai/judge/injury.json",
     rb'("levelDamageSerious"\s*:\s*)450\b', rb'\g<1>428', "serious-injury threshold 450 -> 428"),
    ("common/match/ai/judge/injury.json",
     rb'("symptomDamageBruise"\s*:\s*)290\b', rb'\g<1>276', "bruise threshold 290 -> 276"),
    ("common/match/ai/judge/injury.json",
     rb'("symptomDamageInflammation"\s*:\s*)320\b', rb'\g<1>305', "inflammation threshold 320 -> 305"),
    ("common/match/ai/judge/injury.json",
     rb'("symptomDamageLaceration"\s*:\s*)460\b', rb'\g<1>438', "laceration threshold 460 -> 438"),
    ("common/match/ai/judge/injury.json",
     rb'("symptomDamageTearMuscle"\s*:\s*)500\b', rb'\g<1>476', "muscle-tear threshold 500 -> 476"),
    ("common/match/ai/judge/injury.json",
     rb'("symptomDamageLigament"\s*:\s*)600\b', rb'\g<1>572', "ligament threshold 600 -> 572"),
    ("common/match/ai/judge/injury.json",
     rb'("symptomDamageFracture"\s*:\s*)890\b', rb'\g<1>848', "fracture threshold 890 -> 848"),

    # ---- 8. less robotic defending -----------------------------------
    ("common/match/ai/team/defence/defence.json",
     rb'("predictionFrame"\s*:\s*)35\b', rb'\g<1>33',
     "defensive prediction horizon 35 -> 33 frames: more human reads, real gaps appear"),
    ("common/match/ai/team/defence/defence.json",
     rb'("continueAdvantageDelay"\s*:\s*)57\.0\b', rb'\g<1>53.0',
     "chain delay-pressing urge 57 -> 53"),
    ("common/match/ai/team/defence/defence.json",
     rb'("continueAdvantagePress"\s*:\s*)50\.0\b', rb'\g<1>46.0',
     "chain pressing urge 50 -> 46: less suffocating press chains"),
    ("common/match/ai/team/defence/defenceMark.json",
     rb'("predictionFrame"\s*:\s*)40\b', rb'\g<1>37',
     "marking prediction horizon 40 -> 37 frames"),
    ("common/match/ai/team/defence/defenceCover.json",
     rb'("futureFrame"\s*:\s*)15\b', rb'\g<1>14',
     "cover-position prediction 15 -> 14 frames"),

    # ---- 9. support spacing ------------------------------------------
    ("common/match/ai/team/offence/passSupport.json",
     rb'("outerDiameter"\s*:\s*)8\.0\b', rb'\g<1>8.4',
     "support ring outer radius 8.0 -> 8.4 m: slightly wider, more realistic spacing"),

    # ==== PASS 2: positioning & tactics ==============================
    # ---- 10. team shape & line height --------------------------------
    ("common/match/ai/team/basePosition.json",
     rb'("dfLineWidth_4"\s*:\s*)23\.0\b', rb'\g<1>24.0',
     "back-four base width 23 -> 24 m: full-backs hold slightly wider to cover wide attacks"),
    ("common/match/ai/team/basePosition.json",
     rb'("dfLineRate"\s*:\s*)0\.3\b', rb'\g<1>0.36',
     "DF line height in possession 0.30 -> 0.36: high line with the ball - attacking priority"),

    # ---- 11. attacking width & movement variety ----------------------
    ("common/match/ai/team/basePosition.json",
     rb'("offencWideLength"\s*:\s*)64\.0\b', rb'\g<1>65.5',
     "attacking spread width 64 -> 65.5: a touch more width in possession (pairs with wider support ring)"),
    ("common/match/ai/team/basePosition.json",
     rb'("targetLineXVariation"\s*:\s*)0\.2\b', rb'\g<1>0.25',
     "target-line X variation 0.20 -> 0.25: more organic drifting in base positions, less robotic lines"),
    ("common/match/ai/team/basePosition.json",
     rb'("targetLineZVariation"\s*:\s*)0\.2\b', rb'\g<1>0.25',
     "target-line Z variation 0.20 -> 0.25: same organic drift across the pitch"),
    ("common/match/ai/team/offence/spaceRun.json",
     rb'("chanceScore"\s*:\s*)60\b', rb'\g<1>55',
     "chance-run recognition score 60 -> 55: forward runs into space recognised slightly more often"),

    # ---- 12. cover & space protection --------------------------------
    ("common/match/ai/team/basePosition.json",
     rb'("spaceCoverRate"\s*:\s*)0\.4\b', rb'\g<1>0.45',
     "space-cover rate 0.40 -> 0.45: defenders drift a bit more to protect space"),
    ("common/match/ai/team/basePosition.json",
     rb'("coverRateZ"\s*:\s*)0\.4\b', rb'\g<1>0.45',
     "base-to-cover position shift 0.40 -> 0.45: shape leans slightly more toward cover positions"),
    ("common/match/ai/team/defence/defenceCover.json",
     rb'("coverDfDist"\s*:\s*)6\.6\b', rb'\g<1>6.9',
     "covering DF distance 6.6 -> 6.9 m: cover sits a touch deeper goal-side"),
    ("common/match/ai/team/defence/defenceCover.json",
     rb'("diffTargetLineX"\s*:\s*)5\.0\b', rb'\g<1>4.5',
     "allowed drift off the cover line 5.0 -> 4.5 m: cover line held more strictly"),

    # ---- 13. marking & midfield coverage -----------------------------
    ("common/match/ai/team/defence/defenceMark.json",
     rb'("needMarkOverLastLineDist"\s*:\s*)2\.0\b', rb'\g<1>2.8',
     "marking needed this far over the last line 2.0 -> 2.8 m: fewer unmarked strikers drifting off the back line"),
    ("common/match/ai/team/defence/defenceMark.json",
     rb'("markContinueDist"\s*:\s*)15\b', rb'\g<1>16.5',
     "follow a drifting attacker up to 15 -> 16.5 m before releasing: fewer men lost in rotations"),
    ("common/match/ai/team/defence/defenceMark.json",
     rb'("mfZZoneRange"\s*:\s*)5\b', rb'\g<1>5.5',
     "midfielder zone search range 5 -> 5.5 m: picks up runners in a slightly wider zone"),
    ("common/match/ai/team/defence/defenceMark.json",
     rb'("zoneFrontXMf"\s*:\s*)10\b', rb'\g<1>11',
     "MF zone reach forward 10 -> 11 m: midfield engages opponents slightly higher up"),

    # ==== PASS 3: research-backed modern tactics ======================
    # Sources: compactness research (vertical block 25-35 m, lines 8-12 m,
    # defenders 5-7 m apart), gegenpress/pressing guides (0-5 s window,
    # 2-3 players swarm, lane blockage & cover shadows, selective triggers),
    # switches-of-play research, cutback-over-cross research.

    # ---- 14. modern pressing: triggers, lanes & swarming --------------
    ("common/match/ai/cpuLevel.json",
     rb'("dfPassCourseCut"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t0, \t\t\t\t0, \t\t\t\t1, \t\t\t\t1, \t\t\t\t1, \t\t\t\t1\t\t\t\t]',
     "pass-course-cut positioning enabled from Regular level up (was OFF at every level): defenders finally block passing lanes"),
    ("common/match/ai/team/defence/defence.json",
     rb'("matchUpStartLine"\s*:\s*)10\b', rb'\g<1>11',
     "press start line 10 -> 11: the press engages slightly higher up the pitch"),
    ("common/match/ai/team/defence/defence.json",
     rb'("matchUpDfXLimit"\s*:\s*)5\.0\b', rb'\g<1>5.5',
     "DF matchup reach 5.0 -> 5.5 m ahead of the final line: centre-backs engage forwards sooner"),
    ("common/match/ai/team/defence/defence.json",
     rb'("matchUpMfXLimit"\s*:\s*)5\.0\b', rb'\g<1>5.5',
     "MF matchup reach 5.0 -> 5.5 m: midfield line picks up runners earlier"),
    ("common/match/ai/team/defence/defence.json",
     rb'("matchUpFwXLimit"\s*:\s*)3\.0\b', rb'\g<1>3.4',
     "FW matchup reach 3.0 -> 3.4 m: the first presser engages the carrier slightly higher"),
    ("common/match/ai/team/defence/defence.json",
     rb'("matchUpBallFutureFrame"\s*:\s*)15\.0\b', rb'\g<1>14.0',
     "matchup ball-position lookahead 15 -> 14 frames: reads the present a touch more"),
    ("common/match/ai/team/defence/defence.json",
     rb'("maxSandDist"\s*:\s*)7\.0\b', rb'\g<1>7.5',
     "max close-down (shading) distance 7.0 -> 7.5 m: pressure applied from slightly further out"),
    ("common/match/ai/cpuLevel.json",
     rb'("dfSurround"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t0, \t\t\t\t0, \t\t\t\t1, \t\t\t\t1, \t\t\t\t1, \t\t\t\t1\t\t\t\t]',
     "double-team/swarm behaviour enabled from Regular level up (2-3 players collapse on the ball like a real press)"),
    ("common/match/ai/player/defence/press.json",
     rb'("frontDist"\s*:\s*)0\.2\b', rb'\g<1>0.25',
     "pressing stance front distance 0.2 -> 0.25: engage marginally earlier in the press"),

    # ---- 15. line discipline & block geometry -------------------------
    ("common/match/ai/team/basePosition.json",
     rb'("mfLineRate"\s*:\s*)0\.4\b', rb'\g<1>0.45',
     "MF line height 0.40 -> 0.45: midfield pushes up - attacking priority"),
    ("common/match/ai/team/basePosition.json",
     rb'("dfLineWidth_5"\s*:\s*)28\.0\b', rb'\g<1>29.0',
     "back-five base width 28 -> 29 m: consistent with the wider back four"),
    ("common/match/ai/team/basePosition.json",
     rb'("checkBaseDist"\s*:\s*)4\.0\b', rb'\g<1>4.3',
     "zone-defence handoff check distance 4.0 -> 4.3 m: markers track a touch longer before relaying (chain mechanism)"),
    ("common/match/ai/team/defence/defenceMark.json",
     rb'("markContinueAddDistDF"\s*:\s*)7\b', rb'\g<1>7.5',
     "DFs continue marks +7 -> +7.5 m: centre-backs follow drifting forwards a fraction longer"),
    ("common/match/ai/team/defence/defenceCover.json",
     rb'("diffContinueTargetLineX"\s*:\s*)7\.0\b', rb'\g<1>6.5',
     "allowed drift off the cover line while covering 7.0 -> 6.5 m: the cover chain holds tighter"),
    ("common/match/ai/team/defence/defenceCover.json",
     rb'("coverAngle"\s*:\s*)73\.0\b', rb'\g<1>75.0',
     "cover angle 73 -> 75 deg: covering defenders screen a slightly wider goal-side arc"),

    # ---- 16. ball progression, switches & crossing --------------------
    ("common/match/ai/player/offence/ballplayerPass.json",
     rb'("checkEnemySideChangeWidth"\s*:\s*)90\.0\b', rb'\g<1>100.0',
     "side-change congestion sector 90 -> 100 deg: ball-side overloads get recognised sooner and play is switched"),
    ("common/match/ai/player/offence/ballplayerPass.json",
     rb'("checkSectorWidthFront"\s*:\s*)15\.0\b', rb'\g<1>18.0',
     "forward pass-lane check sector 15 -> 18 deg (retuned theme 27): a 3 m split between two defenders at 15 m is an ~11 deg corridor and now fits inside the first search step"),
    ("common/match/ai/player/offence/ballplayerPass.json",
     rb'("checkSectorWidthSafety"\s*:\s*)30\.0\b', rb'\g<1>32.0',
     "safe-pass lane check sector 30 -> 32 deg: slightly wider lane scanning before safe passes"),
    ("common/match/ai/team/offence/passSupport.json",
     rb'("spaceRectLength"\s*:\s*)6\.0\b', rb'\g<1>6.5',
     "space-pocket recognition length 6.0 -> 6.5 m: support runs target slightly larger gaps (half-space pockets)"),
    ("common/match/ai/player/offence/centering.json",
     rb'("centeringMaxSpeedHigh"\s*:\s*)93\.0\b', rb'\g<1>88.0',
     "cross max speed (high) 93 -> 88: deliveries float a touch more and are more contestable"),
    ("common/match/ai/player/offence/centering.json",
     rb'("centeringMaxSpeedLow"\s*:\s*)89\.0\b', rb'\g<1>85.0',
     "cross max speed (low) 89 -> 85: same, softer cutback-style crosses"),
    ("common/match/ai/player/offence/shoot.json",
     rb'("future"\s*:\s*)31\b', rb'\g<1>30',
     "shooting judgement lookahead 31 -> 30 frames: shot decisions read the present slightly more"),

    # ---- 17. central combination play ---------------------------------
    ("common/match/ai/team/offence/combination.json",
     rb'(\{\s*"kind"\s*:\s*)14(\s*\},\s*//\s*Area09)',
     rb'\g<1>6\g<2>',
     "HOME central attacking area: no combination (kind 14 = COMB_KIND_MAX placeholder) -> WEDGE_02 (AMF-FW wall pass): central up-back-through combinations"),

    # ---- 18. humanised per-level timing --------------------------------
    ("common/match/ai/cpuLevel.json",
     rb'("dfMarkPosUpdateAddTime"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t2, \t\t\t\t2, \t\t\t\t1, \t\t\t\t1, \t\t\t\t0, \t\t\t\t0\t\t\t\t]',
     "marking position updates +2..+0 frames by level: low levels re-shape marks with human delay"),
    ("common/match/ai/cpuLevel.json",
     rb'("bpDribbleAddWait"\s*:\s*)\[[^\]]*\]',
     rb'\g<1>[\t2, \t\t\t\t2, \t\t\t\t1, \t\t\t\t1, \t\t\t\t0, \t\t\t\t0\t\t\t\t]',
     "dribble-reaction delay +2..+0 frames by level: low-level dribblers hesitate like people"),

    # ---- 19. attacking priority (user request: attack over defence) ---
    ("common/match/ai/team/basePosition.json",
     rb'("lengthOf"\s*:\s*)53\.0\b', rb'\g<1>54.5',
     "attacking stretch (FW-DF gap in offence) 53 -> 54.5 m: forwards pin the defence higher"),
    ("common/match/ai/team/basePosition.json",
     rb'("adjustFrontOF"\s*:\s*)12\.0\b', rb'\g<1>13.0',
     "overall forward push in offence 12 -> 13: the team commits slightly more bodies forward"),
    ("common/match/ai/team/basePosition.json",
     rb'("pressRate"\s*:\s*)5\.5\b', rb'\g<1>5.8',
     "FW line height + press start 5.5 -> 5.8: the front line starts higher up"),
    ("common/match/ai/team/basePosition.json",
     rb'("adjustXFromAttackAwareness3"\s*:\s*)2\.5\b', rb'\g<1>3.0',
     "attack-awareness base X push (level 3) 2.5 -> 3.0: attack-minded teams step up more"),
    ("common/match/ai/team/basePosition.json",
     rb'("adjustXFromAttackAwareness4"\s*:\s*)5\.0\b', rb'\g<1>6.0',
     "attack-awareness base X push (level 4) 5.0 -> 6.0: full attacking commitment pushes further forward"),

    # ---- 20. line-breaking runs (deep research: box entries win matches) ---
    ("common/match/ai/team/offence/lineBreak.json",
     rb'("checkZ"\s*:\s*)22\.0\b', rb'\g<1>26.0',
     "line-break ball-zone check 22 -> 26 m: breakers start runs from deeper"),
    ("common/match/ai/team/offence/lineBreak.json",
     rb'("checkZ_good"\s*:\s*)28\.0\b', rb'\g<1>33.0',
     "good-variant zone 28 -> 33 m: same, for high-awareness attackers"),
    ("common/match/ai/team/offence/lineBreak.json",
     rb'("checkBallDist"\s*:\s*)30\.0\b', rb'\g<1>35.0',
     "carrier-distance window 30 -> 35 m: runs commit earlier while the ball travels"),
    ("common/match/ai/team/offence/lineBreak.json",
     rb'("checkBallDist_good"\s*:\s*)35\.0\b', rb'\g<1>41.0',
     "good-variant carrier window 35 -> 41 m"),
    ("common/match/ai/team/offence/lineBreak.json",
     rb'("checkLastLineDist"\s*:\s*)7\.0\b', rb'\g<1>9.0',
     "last-line trigger distance 7 -> 9 m: runners break the line sooner"),
    ("common/match/ai/team/offence/lineBreak.json",
     rb'("checkLastLineDist_good"\s*:\s*)10\.0\b', rb'\g<1>13.0',
     "good-variant last-line trigger 10 -> 13 m"),
    ("common/match/ai/team/offence/lineBreak.json",
     rb'("angleDiff"\s*:\s*)60\.0\b', rb'\g<1>75.0',
     "body-angle tolerance 60 -> 75 deg: runs accepted from more orientations"),
    ("common/match/ai/team/offence/lineBreak.json",
     rb'("angleDiff_good"\s*:\s*)100\.0\b', rb'\g<1>110.0',
     "good-variant angle tolerance 100 -> 110 deg"),

    # ---- 21. feint activation area (elite 1v1 to break blocks) ---
    ("common/match/ai/player/offence/ballplayerFeint.json",
     rb'("checkDistToEnemyGoalDoubletouch"\s*:\s*)40\.0\b', rb'\g<1>52.0',
     "doubletouch activation radius 40 -> 52 m from goal: tricks used over a larger attacking zone"),
    ("common/match/ai/player/offence/ballplayerFeint.json",
     rb'("checkDistToEnemyGoalEracico"\s*:\s*)40\.0\b', rb'\g<1>52.0',
     "eracico activation radius 40 -> 52 m"),
    ("common/match/ai/player/offence/ballplayerFeint.json",
     rb'("checkDistFieldXZOnetime"\s*:\s*)40\.0\b', rb'\g<1>52.0',
     "one-time-feint field radius 40 -> 52 m"),
    ("common/match/ai/player/offence/ballplayerFeint.json",
     rb'("checkDistToEnemyGoalNearRoulette"\s*:\s*)5\.0\b', rb'\g<1>12.0',
     "roulette near-goal radius 5 -> 12 m: the spin move now fires around the box edge"),
    ("common/match/ai/player/offence/ballplayerFeint.json",
     rb'("checkDistToEnemyGoalNearStepKick"\s*:\s*)20\.0\b', rb'\g<1>28.0',
     "step-kick near-goal radius 20 -> 28 m"),

    # ---- 22. shot & pass lane clearing (blocked shots lose ~0.1 xG) ---
    ("common/match/ai/player/offence/ballDodge.json",
     rb'("predictionJumpDist"\s*:\s*)2\.0\b', rb'\g<1>2.6',
     "ball-path dodge anticipation distance 2.0 -> 2.6 m: attackers clear lanes sooner"),
    ("common/match/ai/player/offence/ballDodge.json",
     rb'("needDodgeDistCommon"\s*:\s*)2\.0\b', rb'\g<1>2.4',
     "common dodge trigger distance 2.0 -> 2.4 m"),
    ("common/match/ai/player/offence/ballDodge.json",
     rb'("needDodgeDistBeforeKick"\s*:\s*)4\.0\b', rb'\g<1>5.0',
     "pre-kick dodge trigger 4.0 -> 5.0 m: shooting lanes are cleared earlier"),
    ("common/match/ai/player/offence/ballDodge.json",
     rb'("shootCourseMargin"\s*:\s*)2\.5\b', rb'\g<1>3.1',
     "shoot-course margin around posts 2.5 -> 3.1 m: fewer bodies block the view"),

    # ---- 23. flatter long balls (faster switches of play) ---
    ("common/match/ai/player/offence/longPass.json",
     rb'("highHeightMax"\s*:\s*)9\.0\b', rb'\g<1>7.8',
     "lofted-long-pass max height 9.0 -> 7.8 m: flatter flight arrives faster"),
    ("common/match/ai/player/offence/longPass.json",
     rb'("lowHeightMax"\s*:\s*)5\.0\b', rb'\g<1>4.2',
     "driven-long-pass max height 5.0 -> 4.2 m: switches stay head-height and quick"),

    # ---- 24. set pieces & restarts (25-30% of goals) ---
    ("common/match/ai/player/offence/goalKick.json",
     rb'("distMinBase"\s*:\s*)20\.0\b', rb'\g<1>18.0',
     "goal-kick minimum target distance 20 -> 18 m: short build-up option opens up"),
    ("common/match/ai/player/offence/freekick.json",
     rb'("longpassInplayUse"\s*:\s*)false', rb'\g<1>true',
     "long-pass free kicks allowed in play (was disabled): quick direct restarts unlocked"),
    ("common/match/ai/team/basePosition.json",
     rb'("freekickAttackAddNum"\s*:\s*)1\.5\b', rb'\g<1>2.5',
     "extra attackers joining free kicks 1.5 -> 2.5: bigger commitment to dead balls"),
    ("common/match/ai/team/CoachAttackLevelChange.xml",
     rb'Value="30" ValueJ="30" OptionType="Sign"', rb'Value="20" ValueJ="20" OptionType="Sign"',
     "attack-level state machine engages at 2nd-half 20' (was 30'): chase/protect logic acts earlier"),

    # ---- 25. attacking shape, space runs, pressure ---
    ("common/match/ai/team/basePosition.json",
     rb'("offencWideLength"\s*:\s*)65\.5\b', rb'\g<1>68.0',
     "attacking width stretch 65.5 -> 68.0 m: play opens to the touchlines"),
    ("common/match/ai/team/offence/spaceRun.json",
     rb'("chanceScore"\s*:\s*)55\b', rb'\g<1>48',
     "space-run chance-score threshold 55 -> 48: runs trigger on more situations"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("targetDistZMax"\s*:\s*)14\.0\b', rb'\g<1>18.0',
     "through-ball lead depth max 15 -> 14 -> 18 m (retuned theme 27): landing point sits behind the defensive line; 8.5 m/s x 2.1 s = 17.9 m reachable"),
    ("common/match/ai/player/defence/press.json",
     rb'("aggresPressType"\s*:\s*)1\.2\b', rb'\g<1>1.5',
     "aggressive press factor 1.2 -> 1.5: front players hunt the ball harder (PPDA-style)"),
    ("common/match/ai/rating.json",
     rb'("dribbleRate"\s*:\s*")10\.0(")', rb'\g<1>13.0\g<2>',
     "dribble contribution to match rating 10 -> 13: bold ball-carrying is valued"),

    # ---- 26. stamina asymmetry (late attacking legs) ---
    ("common/match/ai/player/stamina.json",
     rb'("dribbleTired"\s*:\s*)0\.4\b', rb'\g<1>0.32',
     "dribble stamina drain 0.4 -> 0.32 (-20%): carriers keep beating men late"),
    ("common/match/ai/player/stamina.json",
     rb'("defenceTired"\s*:\s*)1\.95\b', rb'\g<1>2.2',
     "defending stamina drain 1.95 -> 2.2 (+13%): chasing attackers wears the block down"),

    # ---- 27. through-ball penetration engine (runner v=8.5 m/s, def v=7.5 m/s,
    #      def reaction 2-6 frames; race math in the changelog) ----
    ("common/match/ai/player/offence/throughpass.json",
     rb'("targetDistZMin"\s*:\s*)10\.0\b', rb'\g<1>11.0',
     "through-ball lead depth min 10 -> 11 m: the shallowest target still lands beyond the defensive line"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("targetDistMin"\s*:\s*)8\.0\b', rb'\g<1>9.0',
     "radial target distance min 8 -> 9 m: consistent with the deeper Z band"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("targetDistMax"\s*:\s*)15\.0\b', rb'\g<1>18.0',
     "radial target distance max 15 -> 18 m: matches the 18 m lead depth (targetDistSec x speed = 17.9 m)"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("targetDistSec"\s*:\s*)1\.9\b', rb'\g<1>2.1',
     "target arrival window 1.9 -> 2.1 s: 8.5 m/s x 2.1 s = 17.9 m - the design time for the deeper lead"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("moveContinueFrameMin"\s*:\s*)25\.0\b', rb'\g<1>32.0',
     "run-persistence window min 25 -> 32 frames: striker sustains the burst to reach the deeper point"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("moveContinueFrameMax"\s*:\s*)50\.0\b', rb'\g<1>60.0',
     "run-persistence window max 50 -> 60 frames (+20%, ratio-consistent with the +20% lead)"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("moveContinueFrameAdjustZposi"\s*:\s*)15\.0\b', rb'\g<1>18.0',
     "Z-position run adjustment 15 -> 18 frames (scaled with the lead depth)"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("dashMoveSecForPassgetMin"\s*:\s*)0\.5\b', rb'\g<1>0.65',
     "pre-receive dash commitment 0.5 -> 0.65 s: the runner is at full sprint, not cruising, when the ball arrives"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("boundDist0"\s*:\s*)23\.0\b', rb'\g<1>26.0',
     "no-bounce through-ball band 23 -> 26 m: more through balls arrive clean for a first-time finish"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("boundDist1"\s*:\s*)40\.0\b', rb'\g<1>44.0',
     "one-bounce band 40 -> 44 m: mid-range through balls stay driven instead of hanging fly passes"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("wallTargetDistFrameMax"\s*:\s*)100\.0\b', rb'\g<1>128.0',
     "blocking-player movement prediction 100 -> 128 frames (+28%): the pass is bent around where the defender WILL be"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("wallTargetAdjustAngleWidth"\s*:\s*)45\.0\b', rb'\g<1>50.0',
     "gap-bend adjustment cone 45 -> 50 deg: aim can dodge blockers slightly further to the side"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("angleWidthMin"\s*:\s*)7\.3\b', rb'\g<1>8.2',
     "pass-search cone floor 7.3 -> 8.2 deg: two defenders 3 m apart at 15 m leave an ~11.4 deg corridor that now fits the scan"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("angleAddValue"\s*:\s*)2\.0\b', rb'\g<1>2.4',
     "search-cone growth 2.0 -> 2.4 deg/step: split-lane options surface one step earlier"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("manualPassSpeedBase"\s*:\s*)25\.0\b', rb'\g<1>29.0',
     "manual (human) through-ball speed floor 25 -> 29 m/s: a 20 m pass now arrives in ~0.75 s vs the defender's ~0.90 s race"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("manualPassSpeedAdjust"\s*:\s*)25\.0\b', rb'\g<1>22.0',
     "manual speed adjust 25 -> 22 (ceiling held ~51 m/s): the weak-tap passes got faster, the rockets stayed rockets"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("manualPassAngleYBase"\s*:\s*)4\.0\b', rb'\g<1>3.2',
     "manual ground through-ball launch angle 4.0 -> 3.2 deg: flatter flight = earlier arrival, less read time"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("manualPassAngleYAdjust"\s*:\s*)6\.0\b', rb'\g<1>5.0',
     "manual ground angle adjust 6.0 -> 5.0 deg: less loft variance at full power"),
    ("common/match/ai/player/offence/throughpass.json",
     rb'("manualFlyPassAngleYAdjust"\s*:\s*)28\.0\b', rb'\g<1>25.0',
     "manual chip-through angle 28 -> 25 deg: flatter clipped balls beat the sweeping keeper"),
    ("common/match/ai/player/offence/ballplayerPass.json",
     rb'("passFrontDistFar"\s*:\s*)20\.0\b', rb'\g<1>24.0',
     "AI forward-pass target range far 20 -> 24 m: the CPU seeks targets matching the deeper lead band"),
    ("common/match/ai/player/offence/ballplayerPass.json",
     rb'("passFrontDistNear"\s*:\s*)5\.0\b', rb'\g<1>6.0',
     "AI forward-pass target range near 5 -> 6 m: fewer toy through balls into crowded feet"),
    ("common/match/ai/player/offence/ballplayerPass.json",
     rb'("checkSectorWidthFrontAdd"\s*:\s*)10\.0\b', rb'\g<1>12.0',
     "skilled-passer lane-scan bonus 10 -> 12 deg: elite passers see the tight split lanes"),

    # ---- 28. structural additions (no numbers: playbook, new skill-move
    #      commands, GK trees, coach states) — always attack, never park ----
    # combination playbook: every zone now runs an attacking play (was half the
    # map empty: kind 14 = NONE and unfinished slots). No defensive combos exist
    # in the enum, so this is pure attack volume.
    ("common/match/ai/team/offence/combination.json",
     b'("combs"\\s*:\\s*\\[)[\\s\\S]*?(\\r\\n\\t\\])',
     b'\\g<1>\n\t// HOME side - attacking playbook\n\t{\n\t\t"area" :\n\t\t[\n'
     b'\t\t\t{ "kind": 8  }, // Area00 wide: CROSS_CROSS (near/far burst + cross)\n'
     b'\t\t\t{ "kind": 10 }, // Area01 wide: CROSS_RETURN (cutback = highest-xG cross)\n'
     b'\t\t\t{ "kind": 9  }, // Area02: CROSS_01 (line cross)\n'
     b'\t\t\t{ "kind": 13 }, // Area03 centre: SHOOT_COURSE\n'
     b'\t\t\t{ "kind": 9  }, // Area04: CROSS_01\n'
     b'\t\t\t{ "kind": 12 }, // Area05 wide: OVERLAP (full-back)\n'
     b'\t\t\t{ "kind": 6  }, // Area06 centre: WEDGE_02 (wall pass + burst)\n'
     b'\t\t\t{ "kind": 12 }, // Area07 wide: OVERLAP\n'
     b'\t\t\t{ "kind": 4  }, // Area08: WEDGE_00 (same-side wall + burst)\n'
     b'\t\t\t{ "kind": 5  }, // Area09: WEDGE_01 (opposite-side wall + burst)\n'
     b'\t\t\t{ "kind": 13 }  // Area10: SHOOT_COURSE\n'
     b'\t\t]\n\t},\n\t// AWAY side - attacking playbook (mirror variation)\n\t{\n\t\t"area" :\n\t\t[\n'
     b'\t\t\t{ "kind": 10 }, // Area00: CROSS_RETURN\n'
     b'\t\t\t{ "kind": 8  }, // Area01: CROSS_CROSS\n'
     b'\t\t\t{ "kind": 0  }, // Area02: DECOY_00 (outside decoy + burst)\n'
     b'\t\t\t{ "kind": 13 }, // Area03: SHOOT_COURSE\n'
     b'\t\t\t{ "kind": 1  }, // Area04: DECOY_01 (inside decoy + burst)\n'
     b'\t\t\t{ "kind": 12 }, // Area05: OVERLAP\n'
     b'\t\t\t{ "kind": 6  }, // Area06: WEDGE_02\n'
     b'\t\t\t{ "kind": 12 }, // Area07: OVERLAP\n'
     b'\t\t\t{ "kind": 5  }, // Area08: WEDGE_01\n'
     b'\t\t\t{ "kind": 4  }, // Area09: WEDGE_00\n'
     b'\t\t\t{ "kind": 13 }  // Area10: SHOOT_COURSE\n'
     b'\t\t]\n\t}\n\t\g<2>',
     "combination playbook rebuilt: all 22 zones now run attacking plays (crosses, cutbacks, wedges, overlaps, decoy runs, shoot courses); the original map had 3 dead zones (kind 14 = NONE) and unfinished slots"),
    # pad/feint.json: fill 3 of the 7 reserved dummy command slots with NEW
    # skill-move routes (L2 namespace; bodyfeint owns the +-90 deg flick-return
    # there, so these use 0/180 deg and rotation gestures - no shadowing).
    ("common/match/pad/feint.json",
     b'\\{\\s*"feint"\\s*:\\s*"' + "ダミーコマンド".encode("cp932") + b'"[\\s\\S]*',
     b'{\n\t\t\t"feint"\t\t: "' + "ルーレット".encode("cp932") + b'",\n'
     b'\t\t\t"inputKind"\t: "' + "体の向き基準".encode("cp932") + b'",\n'
     b'\t\t\t"category"\t: "L2",\n\t\t\t"mirror"\t: true,\n\t\t\t"data"\t\t:\n\t\t\t[\n'
     b'\t\t\t\t{ "button" : "' + "右スティック".encode("cp932") + b'"\t, "kind" : "' + "回転開始位置".encode("cp932") + b'"\t, "angleBase" : 0.0, "angleL" :  10.0, "angleR" : -10.0, "count" : 0, "frame" :  0, "downRate" : -1.0 },\n'
     b'\t\t\t\t{ "button" : "' + "右スティック".encode("cp932") + b'"\t, "kind" : "' + "左回転".encode("cp932") + b'"\t\t, "angleBase" : 0.0, "angleL" :   0.0, "angleR" : -90.0, "count" : 0, "frame" : 60, "downRate" : -1.0 },\n'
     b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" :   0.0, "angleR" :   0.0, "count" : 0, "frame" :  0, "downRate" : -1.0 }\n'
     b'\t\t\t]\n\t\t},\n'
     b'\t\t{\n\t\t\t"feint"\t\t: "' + "ダブルタッチ".encode("cp932") + b'",\n'
     b'\t\t\t"inputKind"\t: "' + "体の向き基準".encode("cp932") + b'",\n'
     b'\t\t\t"category"\t: "L2",\n\t\t\t"mirror"\t: true,\n\t\t\t"data"\t\t:\n\t\t\t[\n'
     b'\t\t\t\t{ "button" : "' + "右スティック".encode("cp932") + b'"\t, "kind" : "' + "倒して戻した瞬間".encode("cp932") + b'"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" : 30, "downRate" : -1.0 },\n'
     b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" :  0, "downRate" : -1.0 },\n'
     b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" :  0, "downRate" : -1.0 }\n'
     b'\t\t\t]\n\t\t},\n'
     b'\t\t{\n\t\t\t"feint"\t\t: "' + "ヒールリフト".encode("cp932") + b'",\n'
     b'\t\t\t"inputKind"\t: "' + "体の向き基準".encode("cp932") + b'",\n'
     b'\t\t\t"category"\t: "L2",\n\t\t\t"mirror"\t: false,\n\t\t\t"data"\t\t:\n\t\t\t[\n'
     b'\t\t\t\t{ "button" : "' + "右スティック".encode("cp932") + b'"\t, "kind" : "' + "倒して戻した瞬間".encode("cp932") + b'"\t, "angleBase" : 180.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" : 30, "downRate" : -1.0 },\n'
     b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" :  0, "downRate" : -1.0 },\n'
     b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" :  0, "downRate" : -1.0 }\n'
     b'\t\t\t]\n\t\t},\n'
     + (b'\t\t{\n\t\t\t"feint"\t\t: "' + "ダミーコマンド".encode("cp932") + b'",\n'
        b'\t\t\t"inputKind"\t: "' + "体の向き基準".encode("cp932") + b'",\n'
        b'\t\t\t"category"\t: "NONE",\n\t\t\t"mirror"\t: false,\n\t\t\t"data"\t\t:\n\t\t\t[\n'
        b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" : 0, "downRate" : -1.0 },\n'
        b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" : 0, "downRate" : -1.0 },\n'
        b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" : 0, "downRate" : -1.0 }\n'
        b'\t\t\t]\n\t\t},\n') * 3
     + (b'\t\t{\n\t\t\t"feint"\t\t: "' + "ダミーコマンド".encode("cp932") + b'",\n'
        b'\t\t\t"inputKind"\t: "' + "体の向き基準".encode("cp932") + b'",\n'
        b'\t\t\t"category"\t: "NONE",\n\t\t\t"mirror"\t: false,\n\t\t\t"data"\t\t:\n\t\t\t[\n'
        b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" : 0, "downRate" : -1.0 },\n'
        b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" : 0, "downRate" : -1.0 },\n'
        b'\t\t\t\t{ "button" : "---------"\t, "kind" : "-------------"\t, "angleBase" : 0.0, "angleL" : 0.0, "angleR" : 0.0, "count" : 0, "frame" : 0, "downRate" : -1.0 }\n'
        b'\t\t\t]\n\t\t}\n\t]\n}'),
     "3 new skill-move commands in the reserved dummy slots: L2+stick-rotation roulette, L2+flick-forward double touch, L2+flick-backward heel lift (bodyfeint keeps its +-90 deg lane)"),
    # offenceGk.xml: the keeper's ball-playing answers - never idle, never retreat
    ("common/match/ai/player/offence/offenceGk.xml",
     b'<Node NodeId="Shape23" ConfigId="NOTHING" NodeType="Answer" />',
     b'<Node NodeId="Shape23" ConfigId="LONG_PASS" NodeType="Answer" />',
     "GK 'do nothing' outcome -> LONG_PASS: the keeper always launches the counter instead of idling"),
    ("common/match/ai/player/offence/offenceGk.xml",
     b'<Node NodeId="Shape19" ConfigId="KP_BASE_POSITION" NodeType="Answer" />',
     b'<Node NodeId="Shape19" ConfigId="DRIBBLE" NodeType="Answer" />',
     "GK 'return to base' outcome -> DRIBBLE: sweeper keeper carries the ball out and adds an outfield player to the attack"),
    # defenceGkAI.xml: no sitting on the line
    ("common/match/ai/player/defence/defenceGkAI.xml",
     b'<Node NodeId="Shape25" ConfigId="KP_BLOCK_LATE" NodeType="Answer" />',
     b'<Node NodeId="Shape25" ConfigId="KP_PRESS" NodeType="Answer" />',
     "GK 'late block' (sits on the line) -> KP_PRESS: sweeps through balls early instead of retreating"),
    # CoachAttackLevelChange.xml: the team never parks the bus and pushes when
    # the game is still in the balance
    ("common/match/ai/team/CoachAttackLevelChange.xml",
     b'<Node NodeId="Shape8" ConfigId="DEFENSIVE" NodeType="Answer" />',
     b'<Node NodeId="Shape8" ConfigId="BALANCE" NodeType="Answer" />',
     "attack-level DEFENSIVE state retired -> BALANCE: the team never drops into a parked block"),
    ("common/match/ai/team/CoachAttackLevelChange.xml",
     b'(<Arg Type="Numeric" Value=")2(" ValueJ=")2(" OptionType="Sign">)',
     b'\\g<1>1\\g<2>1\\g<3>',
     "offensive-push goal-difference trigger +2 -> +1: trailing by one now triggers the attacking push"),
    ("common/match/ai/team/CoachAttackLevelChange.xml",
     b'(<Arg Type="Numeric" Value=")-2(" ValueJ=")-2(" OptionType="Sign">)',
     b'\\g<1>-3\\g<2>-3\\g<3>',
     "balance-state goal-difference threshold -2 -> -3: only a 3-goal cushion relaxes the push"),
    ("common/match/ai/player/offence/penaltykick.json",
     rb'("shootSpeedKPHMin"\s*:\s*)95\.0', rb'\g<1>82.0',
     "penaltykick.json shootSpeedKPHMin: 95.0 -> 82.0 (real placed penalties 75-85 KPH; the old floor forced power-only finishes)"),
    ("common/match/ai/player/offence/penaltykick.json",
     rb'("shootSpeedKPHMax"\s*:\s*)125\.0', rb'\g<1>128.0',
     "penaltykick.json shootSpeedKPHMax: 125.0 -> 128.0 (real top-end PK strikes ~125-130 KPH)"),
    ("common/match/ai/player/defence/defenceGkAutoPk.xml",
     rb'(Value=")60(" ValueJ=")60(" OptionType="Sign">)', rb'\g<1>85\g<2>85\g<3>',
     "defenceGkAutoPk.xml CheckBallSpeed hold threshold: 60 -> 85 KPH (real GK technique: hold up to ~85, parry anything harder)"),

]

# ---------------------------------------------------------------------------
# Pass 8 (theme 29): hidden off-ball movement modules in constant_team.bin.
# The entry is a QWESYS zlib container -- regex-patching raw bytes is
# impossible (values live inside the compressed payload), so these patches are
# applied by tools/qwesys.py (decompress -> assert old value -> patch ->
# recompress -> rebuild the 16-B header) at pack time.  Field names/offsets
# follow the community mappings in tools/mappings/ (the4chancup/
# pes-gameplay-editor, implyingrigged wiki User:Aoba + User:MarcoZ), with the
# PES 2017 offsets re-validated against our payload (contiguous regions
# 0x500..0xeb0, sizes x16).  57 value changes, every one asserted old->new.
# ---------------------------------------------------------------------------
BIN_EDITS = [
    ("common/match/constant/constant_team.bin", [
        # -- subConcept.o: 21 dormant attacking/possession concepts -> on ------
        # PES 2017 holds the enum-prefix subset (all attacking patterns; the
        # ForeCheck/Retreat/NetDefence/SealOff/DoublePress defensive concepts
        # only exist in later games' enum tail).  Bools: 0 = off -> 1 = on.
        ("subConcept.o", 156, "u32", 0, 1),  # PossessionMfJoinDefenceLine
        ("subConcept.o", 160, "u32", 0, 1),  # ChangeTriangle
        ("subConcept.o", 164, "u32", 0, 1),  # CounterAfterGkCatch
        ("subConcept.o", 168, "u32", 0, 1),  # SideCounter
        ("subConcept.o", 172, "u32", 0, 1),  # FastCounter
        ("subConcept.o", 176, "u32", 0, 1),  # LongPassFlick
        ("subConcept.o", 180, "u32", 0, 1),  # LongPassLayOffAndToSide
        ("subConcept.o", 184, "u32", 0, 1),  # LongPassLayOffAndBreakthroughToDefenceLine
        ("subConcept.o", 188, "u32", 0, 1),  # LongPassLayOffAndShoot
        ("subConcept.o", 192, "u32", 0, 1),  # EarlyCross
        ("subConcept.o", 196, "u32", 0, 1),  # ForwardPassAndLayOff
        ("subConcept.o", 200, "u32", 0, 1),  # PassAndGoTriangle
        ("subConcept.o", 204, "u32", 0, 1),  # PenetrateInsideOneTwo
        ("subConcept.o", 208, "u32", 0, 1),  # SpaceRunToCenterForCreateSideSpace
        ("subConcept.o", 212, "u32", 0, 1),  # ToCenterDecoySide
        ("subConcept.o", 216, "u32", 0, 1),  # SpaceRunRelaySquarePass
        ("subConcept.o", 220, "u32", 0, 1),  # DisorderByOneTwo
        ("subConcept.o", 224, "u32", 0, 1),  # SideCrossRunning
        ("subConcept.o", 228, "u32", 0, 1),  # SideRunMakeSpace
        ("subConcept.o", 232, "u32", 0, 1),  # SpaceRunToCreateSpaceForOneTouchPass
        ("subConcept.o", 236, "u32", 0, 1),  # CreateSpaceOneTwo
        # -- selectorVision.o: run-dispatch offer thresholds, 6 run types x 5 --
        # offerNum_* = score bar per run variant (variant 1 = the rare/expensive
        # route, 2-5 = common ones); LOWER bar = the run is offered in more
        # situations (same semantics as spaceRun chanceScore, already lowered
        # 55->48 in Pass 5).  x0.7, floor 1, variant ordering preserved.
        # Encoding preserved per cell (f32 vs u32 as shipped).
        ("selectorVision.o", 32, "f32", 17.0, 12.0), ("selectorVision.o", 36, "f32", 21.0, 15.0),
        ("selectorVision.o", 40, "f32", 20.0, 14.0), ("selectorVision.o", 44, "f32", 25.0, 18.0),
        ("selectorVision.o", 48, "u32", 1, 1),   # diagonalRun 1..5 (5th already floor)
        ("selectorVision.o", 64, "f32", 50.0, 35.0), ("selectorVision.o", 68, "u32", 2, 1),
        ("selectorVision.o", 72, "u32", 4, 3),   ("selectorVision.o", 76, "f32", 12.0, 8.0),
        ("selectorVision.o", 80, "f32", 17.0, 12.0),  # lineBreak 1..5
        ("selectorVision.o", 96, "f32", 20.0, 14.0), ("selectorVision.o", 100, "f32", 25.0, 18.0),
        ("selectorVision.o", 104, "f32", 30.0, 21.0), ("selectorVision.o", 108, "f32", 90.0, 63.0),
        ("selectorVision.o", 112, "f32", 110.0, 77.0),  # pullAway 1..5
        ("selectorVision.o", 128, "f32", 4.0, 3.0),  ("selectorVision.o", 132, "f32", 6.0, 4.0),
        ("selectorVision.o", 136, "f32", 5.0, 4.0),  ("selectorVision.o", 140, "f32", 7.0, 5.0),
        ("selectorVision.o", 144, "f32", 6.0, 4.0),   # spaceRunChance 1..5
        ("selectorVision.o", 160, "f32", 10.0, 7.0),  ("selectorVision.o", 164, "f32", 19.0, 13.0),
        ("selectorVision.o", 168, "f32", 23.0, 16.0), ("selectorVision.o", 172, "f32", 5.0, 4.0),
        ("selectorVision.o", 176, "f32", 10.0, 7.0),   # spaceRunCounter 1..5
        ("selectorVision.o", 192, "f32", 100.0, 70.0), ("selectorVision.o", 196, "f32", 15.0, 11.0),
        ("selectorVision.o", 200, "f32", 2.0, 1.0), ("selectorVision.o", 204, "f32", 2.0, 1.0),
        ("selectorVision.o", 208, "f32", 18.0, 13.0),  # spaceRunSecondLine 1..5
        # -- lineBreak.o = overlap-run trigger table (Aoba PES2021 overlap.o):
        # addCount=1, addCount_adverse=0, checkMiddleLineX=-1/-.5? ... exact
        # 7-field match verified.  Runs trigger earlier and keep going under
        # pressure (wing-back tracking data: 16.75-25.12 m runs at ~20 km/h).
        ("lineBreak.o", 4, "u32", 0, 1),    # addCount_adverse 0 -> 1
        ("lineBreak.o", 12, "f32", -5.0, -3.0),   # checkMiddleLineX_adverse
        ("lineBreak.o", 16, "f32", -18.0, -12.0), # checkTopLineX
        ("lineBreak.o", 20, "f32", -25.0, -18.0), # checkTopLineX_adverse
        # -- diagonalRun.o: dummy/decoy-run fan is OFF (0/0) -> active --------
        # Aoba: Dummy Runner doubles the fan (fanAngle 20->40, margin stays 5).
        ("diagonalRun.o", 56, "u32", 0, 5),  # fanAngleHalfMargin_dummyRunner
        ("diagonalRun.o", 60, "u32", 0, 6),  # fanAngle_dummyRunner (= 2 x fanAngle)
    ], "theme 29 off-ball modules: 21 subConcept attacking concepts on, "
       "selectorVision offer thresholds -30% (more run dispatches), "
       "overlap triggers earlier + 1 adverse runner, dummy-run fan enabled"),
    ("common/match/constant/constant_positionCK.bin", [
        # -- theme 30: corner routines -> the full 6-man attacking shape ------
        # Each routine's station block = 22 slot records (flag, id, X, Z);
        # slots 5/6 carry the shared-library runs (record 5 = 21 keyframes =
        # the edge->box crash; record 6 = the check-out run).  The 4_x/5_x
        # families shipped with those slots unstationed; every routine now
        # stations both, copying the 6-man family's own role pattern:
        # slot 5 = the edge-of-box second-ball starter, slot 6 = the box
        # runner.  Start stations only -- each slot's run-target cluster in
        # the situation bin either already exists or is added in RAW_EDITS.
        ("positionCK.o", 96, "u32", 0, 1), ("positionCK.o", 104, "f32", 0.0, 28.0),
        ("positionCK.o", 108, "f32", 0.0, -1.8),
        ("positionCK.o", 112, "u32", 0, 1), ("positionCK.o", 120, "f32", 0.0, 38.7),
        ("positionCK.o", 124, "f32", 0.0, -8.2),
        ("positionCK_4_1.o", 96, "u32", 0, 1), ("positionCK_4_1.o", 104, "f32", 0.0, 28.1),
        ("positionCK_4_1.o", 108, "f32", 0.0, -1.9),
        ("positionCK_4_1.o", 112, "u32", 0, 1), ("positionCK_4_1.o", 120, "f32", 0.0, 38.9),
        ("positionCK_4_1.o", 124, "f32", 0.0, -8.4),
        ("positionCK_4_2.o", 96, "u32", 0, 1), ("positionCK_4_2.o", 104, "f32", 0.0, 28.3),
        ("positionCK_4_2.o", 108, "f32", 0.0, -2.0),
        ("positionCK_4_2.o", 112, "u32", 0, 1), ("positionCK_4_2.o", 120, "f32", 0.0, 39.1),
        ("positionCK_4_2.o", 124, "f32", 0.0, -7.9),
        ("positionCK_4_3.o", 96, "u32", 0, 1), ("positionCK_4_3.o", 104, "f32", 0.0, 28.2),
        ("positionCK_4_3.o", 108, "f32", 0.0, -1.9),
        ("positionCK_5_1.o", 96, "u32", 0, 1), ("positionCK_5_1.o", 104, "f32", 0.0, 28.1),
        ("positionCK_5_1.o", 108, "f32", 0.0, -1.8),
        ("positionCK_5_2.o", 96, "u32", 0, 1), ("positionCK_5_2.o", 104, "f32", 0.0, 28.4),
        ("positionCK_5_2.o", 108, "f32", 0.0, -1.7),
    ], "theme 30 corner routines: slot5 (edge crash) + slot6 (box check-out) "
       "stationed in base/4_x/5_x -> every corner runs the full 6-man "
       "attacking shape (real-life: 5-6 committed to the box, 2 back)"),
]

# ---------------------------------------------------------------------------
# Pass 9 (theme 30): byte-offset patches on raw (non-QWESYS) entries.
# (path, [(file_offset, old_bytes, new_bytes)], note) -- old span asserted
# before replacement.  These fill the run-target clusters of the newly
# stationed slot-5 runners in the 4_x families: record 5's tail holds
# (flag u8, 0xfefefe pad, u32 0, f32 x, f32 y, f32 z) at offset
# 472 + 5*1280 + 1024 = 7896.  Targets copied from the 6-man donors'
# slot-5 runs (6_1: edge->near-post crash (36.33,-10.74); 6_2: box run
# (38.68, 0.836, -8.22)).  base/5_1/5_2 keep their own existing targets.
# ---------------------------------------------------------------------------
RAW_EDITS = [
    ("common/match/situation/positionCK_4_1.bin", [
        (7896,
         b"\x00\xfe\xfe\xfe\x00\x00\x00\x00" + b"\x00" * 12,
         b"\x01\xfe\xfe\xfe\x00\x00\x00\x00" + b"\xec\x51\x11\x42" + b"\x00\x00\x00\x00" + b"\xad\x72\xbc\xc1"),
    ], "slot-5 run target (empty) -> 6_1 donor: (36.33, 0, -10.74) near-post crash"),
    ("common/match/situation/positionCK_4_2.bin", [
        (7896,
         b"\x00\xfe\xfe\xfe\x00\x00\x00\x00" + b"\x00" * 12,
         b"\x01\xfe\xfe\xfe\x00\x00\x00\x00" + b"\x52\xb8\x1a\x42" + b"\x19\x04\x56\x3f" + b"\x1f\x85\x03\xc1"),
    ], "slot-5 run target (empty) -> 6_2 donor: (38.68, 0.836, -8.22)"),
    ("common/match/situation/positionCK_4_3.bin", [
        (7896,
         b"\x00\xfe\xfe\xfe\x00\x00\x00\x00" + b"\x00" * 12,
         b"\x01\xfe\xfe\xfe\x00\x00\x00\x00" + b"\xec\x51\x11\x42" + b"\x00\x00\x00\x00" + b"\xad\x72\xbc\xc1"),
    ], "slot-5 run target (empty) -> 6_1 donor: (36.33, 0, -10.74) near-post crash"),
]



# QWESYS payload string patches (same-length byte spans inside the zlib stream).
# (path, find_bytes, new_bytes, expected_count, note)
QRAW_EDITS = [
    ("common/match/constant/constant_match.bin",
     b"+  0.0  * StatsPlayerPassShortSuccess()",
     b"+  1.5  * StatsPlayerPassShortSuccess()", 1,
     "pesSmart.o rating formula 1: short-pass completion now worth 1.5 pts per event (was 0.0 = build-up passing unrewarded; formula 2 already used 1.5)"),
    ("common/match/constant/constant_match.bin",
     b"-  0.0  * ( StatsPlayerFoul() - StatsPlayerOffSide() )",
     b"-  2.0  * ( StatsPlayerFoul() - StatsPlayerOffSide() )", 3,
     "pesSmart.o rating formulas 1/2/4: fouls now cost 2.0 pts per event over offside count (was 0.0 = fouls were free; real ratings penalise ill-discipline)"),
    ("common/match/team_action/team_id_01090.bin",
     b"EnemyLastLine() + DefenceSide() * 5.0",
     b"EnemyLastLine() + DefenceSide() * 2.5", 1,
     "team_id_01090.bin (default team-action script): last-line role offset 5.0 -> 2.5 m (plays on the shoulder of the defensive line, like real forwards / the engine's own Goal Poacher archetype)"),
]

def main():
    from collections import defaultdict
    by_file = defaultdict(list)
    for f, pat, rep, note in EDITS:
        by_file[f].append((pat, rep, note))

    errors = 0
    for f, edits in by_file.items():
        path = os.path.join(ROOT, f)
        with open(path, "rb") as fh:
            data = fh.read()
        for pat, rep, note in edits:
            n_matches = len(re.findall(pat, data))
            if n_matches != 1:
                print(f"ERROR {f}: pattern {pat!r} matches {n_matches} times (want 1) -- {note}")
                errors += 1
                continue
            data = re.sub(pat, rep, data, count=1)
            print(f"ok  {f}: {note}")
        with open(path, "wb") as fh:
            fh.write(data)

    if errors:
        print(f"\n{errors} edit(s) failed -- no files were partially applied per-file, check output")
        sys.exit(1)
    print(f"\nall {len(EDITS)} edits applied to {len(by_file)} files")


if __name__ == "__main__":
    main()
