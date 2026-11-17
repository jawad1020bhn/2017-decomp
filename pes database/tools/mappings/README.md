# constant_team.bin field mappings

Vendored from `the4chancup/pes-gameplay-editor` (`pes_ai/mappings/18/team/*.txt`,
GPL-3.0, commit 4a7df9d / b5a4546) and cross-checked against the implyingrigged
wiki (`User:Aoba/PES2021_dt18`, `User:MarcoZ/dt18_Files_Breakdown`,
`User:Aoba/PES2021_Engine_Research`).

Format: `byte_offset field_name` per line (`padding` = unmapped filler).
Encoding: `u32` ints when the value fits 0..10000, `f32` otherwise
(`utils.conv_from_bytes`); one-byte bools marked in the editor's `one_byte_bools`
list (eyeOff, lastLine, lastLineEnemy, pullAway, ...).

NOTE: these mappings target the PES 2021 dt18 bins. PES 2017 entries are
smaller; offsets used in gameplay_enhance.BIN_EDITS were re-validated against
our constant_team.bin payload (contiguous 0x500..0xeb0, sizes x16, 7-field
lineBreak.o == Aoba's overlap.o table verbatim).

Module semantics (wiki):
- diagonalRun.o  -- dummy/decoy runs that displace the defence; Dummy Runner
  playing style gets 4 special values (distXBpMax 8->15, fanAngle 20->40,
  fanFar 5->8, fanAngleHalfMargin 5).
- lineBreak.o (our name; = Aoba's overlap.o table) -- overlap-run triggers:
  addCount/addCount_adverse (extra runners), checkMiddleLineX/checkTopLineX
  (+_adverse = deeper when under pressure), style.
- pullAway.o -- breaking away from markers (Goal Poacher system, dispatch 47).
- selectorVision.o -- offerNum_<runType>1..5: dispatch thresholds for how many
  runs of each type (diagonalRun/lineBreak/pullAway/spaceRunChance/Counter/
  SecondLine) are offered; lower bar = offered in more situations.
- subConcept.o -- named attacking/possession concept toggles (EarlyCross,
  PenetrateInsideOneTwo, CreateSpaceOneTwo, PassAndGoTriangle...); the
  defensive concepts (ForeCheck*/Retreat*/NetDefence*/SealOff*/DoublePress)
  only exist in later games' enum tail -- PES 2017 holds the 21-entry
  attacking prefix, all shipped disabled.
- support.o / spaceRun.o / centreingGet.o -- support-run positioning
  (angleMax 45/90, supportDist 6, distMax 20...), chance-creation runs
  (chanceScore threshold 85/100 for _good styles), cross arrivals.
