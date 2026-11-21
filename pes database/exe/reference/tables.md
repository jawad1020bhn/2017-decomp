# Lookup tables and worked schedules

[Master League guide](../MASTER_LEAGUE.md) · Section numbers are the original research citations. Paths in the notes are relative to `pes database/exe` unless a command changes directory.

## Appendix A: steps of a day

Steps called from the four bodies of section 3 (60 C lines and more), in the order of
the code. "events asked" = the event numbers the function itself tests.

| function | called from | C lines | events asked | uses |
|---|---|---|---|---|
| `fcn_035d8b2e` | day begin | 181 | - | - |
| `fcn_03640d19` | day begin | 1280 | 3, 23, 25, 49 | random, wage bill, team strength |
| `fcn_03664a3d` | day begin | 111 | 1, 3, 6 | - |
| `fcn_0365c89a` | day begin | 177 | 3, 6 | day state, negotiation step |
| `fcn_03661f6b` | day begin | 144 | 1, 3, 6, 30 | day state |
| `fcn_036e20d2` | day begin | 114 | 1, 3, 6, 12, 14 | - |
| `fcn_03656fa5` | day begin | 449 | - | random, rating, salary, team strength, day state |
| `fcn_0364b81c` | day begin | 302 | 11 | random, staff report |
| `fcn_03676016` | day begin | 115 | 31, 45 | staff report |
| `fcn_0362579a` | day begin | 174 | 3, 6 | rating |
| `fcn_03632aa8` | day begin | 89 | - | - |
| `fcn_0363e8bb` | day begin | 930 | - | - |
| `fcn_035f51fe` | day end | 81 | - | - |
| `fcn_036fc11a` | day end | 240 | - | - |
| `fcn_03701dd5` | day end | 306 | - | - |
| `fcn_036696e1` | day end | 233 | 41, 43, 44 | - |
| `fcn_0362eb70` | day end | 139 | 41, 42, 43, 44 | - |
| `fcn_03664d29` | day end | 77 | 9 | day state |
| `fcn_0365692c` | day end | 266 | - | random, rating, team strength, day state |
| `fcn_0365cbbc` | day end | 86 | 9 | day state, negotiation step |
| `fcn_036e067a` | day end | 232 | 5, 13, 15 | complete transfer, staff report, news |
| `fcn_036fbe88` | day end | 115 | - | - |
| `fcn_0366f4bb` | day end | 60 | 6, 19, 23, 26, 27, 28, 29 | - |
| `fcn_0366d620` | day end | 228 | 23 | - |
| `fcn_03640686` | day end | 276 | 23 | - |
| `fcn_03652198` | day end | 111 | 4, 7 | random, scout search |
| `fcn_0363beba` | day end | 77 | 48 | staff report |
| `fcn_03634561` | day end | 85 | - | - |
| `fcn_03633690` | day end | 372 | - | - |
| `fcn_036f9395` | day end | 566 | - | - |
| `fcn_036f5728` | day end | 145 | 17 | - |
| `fcn_03621fab` | day end | 66 | - | - |
| `fcn_0360b189` | day end | 107 | - | - |
| `fcn_036e469b` | day end | 218 | - | - |
| `fcn_036365e6` | day end | 379 | - | staff report |
| `fcn_03708fd5` | after matches 1 | 128 | - | - |
| `fcn_03705515` | after matches 2 | 339 | - | random, staff report |
| `fcn_03637230` | after matches 2 | 167 | - | team strength |
| `fcn_0363c32e` | after matches 2 | 1400 | - | - |
| `fcn_036e3f46` | after matches 2 | 258 | - | - |
| `fcn_0370403e` | after matches 2 | 156 | - | - |
| `fcn_036793c1` | after matches 2 | 73 | - | - |
| `fcn_0364418c` | after matches 2 | 206 | - | - |
| `fcn_0362af8a` | after matches 2 | 284 | - | team strength |
| `fcn_03633f22` | after matches 2 | 222 | - | - |
| `fcn_03631f2d` | after matches 2 | 313 | - | - |
| `fcn_03627f98` | after matches 2 | 385 | - | rating |

Large functions (250 C lines and more) called by these steps:

| function | called by | C lines | events asked | uses |
|---|---|---|---|---|
| `fcn_03623a38` | `fcn_03627f98` | 489 | - | random |
| `fcn_0362636e` | `fcn_03627f98` | 583 | - | random |
| `fcn_0362e2bd` | `fcn_0362eb70` | 359 | - | rating |
| `fcn_03634e91` | `fcn_036365e6` | 270 | - | random, staff report |
| `fcn_03635675` | `fcn_036365e6` | 548 | - | - |
| `fcn_03638a08` | `fcn_0363beba` | 657 | - | - |
| `fcn_036435a7` | `fcn_0364418c` | 374 | - | wage bill |
| `fcn_0364692a` | `fcn_0364b81c` | 1202 | - | random |
| `fcn_03651767` | `fcn_03652198` | 416 | - | - |
| `fcn_0364f2ca` | `fcn_03652198` | 1381 | - | random, rating, fee, team strength, squad needs, staff report |
| `fcn_03653d49` | `fcn_0365692c` | 426 | - | - |
| `fcn_03654736` | `fcn_03656fa5` | 539 | - | random, rating |
| `fcn_03655c6b` | `fcn_03656fa5` | 334 | - | - |
| `fcn_03659b50` | `fcn_0365c89a` | 1621 | - | random, salary, fee, staff report |
| `fcn_03661380` | `fcn_03661f6b` | 304 | - | rating |
| `fcn_036602e5` | `fcn_03661f6b` | 392 | 30 | random, squad needs |
| `fcn_0366365b` | `fcn_03664d29` | 769 | 5, 8 | random, salary, complete transfer, staff report |
| `fcn_03668ee8` | `fcn_036696e1` | 310 | - | random |
| `fcn_0366e79f` | `fcn_0366f4bb` | 455 | - | - |
| `fcn_03672359` | `fcn_03676016` | 261 | - | - |
| `fcn_036dfd95` | `fcn_036e067a` | 366 | - | staff report |
| `fcn_036e1665` | `fcn_036e20d2` | 405 | 12, 14 | random, rating, staff report, news |
| `fcn_036fb5de` | `fcn_036fbe88` | 445 | - | - |
| `fcn_037010dc` | `fcn_03701dd5` | 517 | - | - |
| `fcn_0362c6ad` | `fcn_03705515` | 1125 | - | random |

## Appendix B: classes of the career modes

From the exe's type records (`rtti.py`, `output/classes.tsv.xz`). "Functions of its
own" = entries of the class's function table that no other class has; the first is
usually the destructor.

| class | table | functions of its own |
|---|---|---|
| `menu::AccountingPayment` | `0x01fb3fcc` | `0x03199488` `0x0319ac5b` `0x031985fd` `0x03197cdc` |
| `menu::MainMenuML` | `0x01fb604c` | `0x031a25cc` `0x031a4b83` `0x031a2204` `0x031a502c` `0x031a4ee7` `0x031a269b` … (7 in all) |
| `menu::MatchFromSchedule` | `0x020370ac` | `0x0335e134` `0x0335dde7` `0x0335e164` `0x0335f1e8` `0x0335e249` |
| `menu::MenuModeGrowthReport` | `0x01fb1d94` | `0x03183faa` `0x0318c016` `0x031827a6` `0x03182557` |
| `menu::MenuModeMLCoachEdit` | `0x01fb5424` | `0x0319fba9` `0x0319fbd9` `0x0319fe1d` `0x031a0876` `0x031a0916` `0x0319fd15` … (8 in all) |
| `menu::MenuModeMLCoachHallOfFame` | `0x01faf924` | `0x03176a83` `0x03179283` `0x03171d39` `0x03179018` `0x03177b0d` `0x03175a97` … (9 in all) |
| `menu::MenuModeMLCoachMenu` | `0x01fb01ec` | `0x0317c519` `0x0317c5d5` `0x0317c12a` `0x0317bec1` `0x0317bd68` |
| `menu::MenuModeMLCoachSeasonResult` | `0x01fafd6c` | `0x0317a692` `0x0317bcb2` `0x0317adb2` `0x0317bc06` `0x0317bc5c` |
| `menu::MenuModeMLCoachTitleCollection` | `0x01fae9e4` | `0x0316d746` `0x0316e695` `0x0316c99e` `0x0316d38b` `0x0316f3a5` `0x0316db23` … (8 in all) |
| `menu::MenuModeMLMoneyReport` | `0x01fb4fc4` | `0x0319eb57` `0x0319ec13` |
| `menu::MenuModeMLNegociationAdjust` | `0x01fab85c` | `0x03158ce5` `0x031592fc` `0x03154b6f` `0x03155957` `0x03154799` `0x031591cc` |
| `menu::MenuModeMLNegociationCountDown` | `0x01fae024` | `0x0316a843` `0x0316aeaf` `0x0316a206` `0x03169e47` `0x03169e17` |
| `menu::MenuModeMLNegociationDetail` | `0x01fac2dc` | `0x0315d3fe` `0x0315ce0a` `0x031597df` `0x0315c98a` `0x0315cb2f` `0x0315d65a` … (9 in all) |
| `menu::MenuModeMLNegociationDialog` | `0x02004264` | `0x032ab2d7` `0x032ab39c` `0x032ad02a` `0x032abdee` |
| `menu::MenuModeMLNegociationList` | `0x01fad60c` | `0x031646b0` `0x03167916` `0x0315e4c2` `0x031667be` `0x0316714e` `0x0315ef13` … (14 in all) |
| `menu::MenuModeMLNegociationMenu` | `0x01fadacc` | `0x031694f8` `0x03169528` `0x03168ce0` `0x031685c7` `0x031684bc` |
| `menu::MenuModeMLNickName` | `0x01fb0a3c` | `0x0317e805` `0x0317e95c` `0x0317e626` `0x0317e686` |
| `menu::MenuModeMLPlayerManagement` | `0x01fab21c` | `0x03153dcd` `0x03153f17` `0x03154371` `0x03153b5c` `0x031539af` `0x03153c22` |
| `menu::MenuModeMLPlayerSearchConcept` | `0x01faa0cc` | `0x0315099d` `0x031506d9` `0x031507ad` `0x0315089d` `0x031508fd` |
| `menu::MenuModeMLPlayerSearchRole` | `0x01fa9bc4` | `0x0315051e` `0x031502b8` `0x03150398` `0x0315048e` `0x031504de` |
| `menu::MenuModeMLTrainingSelect` | `0x01fb3c24` | `0x03196da1` `0x03197786` `0x03197a86` `0x031975c8` `0x031973ec` `0x03197558` |
| `menu::MenuModeMLTrainingSkill` | `0x01fb3474` | `0x031949e6` `0x03194b5b` `0x03196b65` `0x03195773` `0x031955d0` `0x03196cb5` … (7 in all) |
| `menu::MenuModeMonthlySchedule` | `0x01fe08b4` | `0x03223e65` `0x032251f3` `0x032238a1` `0x032235be` |
| `menu::MenuModeNationalSchedule` | `0x01fb061c` | `0x0317e447` `0x0317e52a` `0x0317d296` `0x0317cd9d` |
| `menu::MenuModeOfferList` | `0x01fb287c` | `0x0318f369` `0x0318f129` `0x0318e40a` `0x0318f0f9` |
| `menu::MenuModeTeamRoleDialog` | `0x020025bc` | `0x032a78d4` `0x032a7db2` `0x032a762a` |
| `menu::ModeMLAccountingClubBS` | `0x01fb44ec` | `0x0319af7e` `0x0319b259` `0x0319b106` |
| `menu::ModeMLDivisionExchange` | `0x01fb0ecc` | `0x0317f12e` `0x0317fac0` `0x0317f05e` |
| `menu::ModeMLGeneralSettings` | `0x01fb58dc` | `0x031a15e0` `0x031a1768` `0x031a13d4` `0x031a15c0` |
| `menu::ModeMLInputMoney` | `0x0203e524` | `0x03379553` `0x03379e4a` `0x03379e9a` `0x03379eca` `0x033793d6` `0x03379396` |
| `menu::ModeMLPhilosophy` | `0x01fae454` | `0x0316bac2` `0x0316b851` `0x0316bb77` `0x0316b227` |
| `menu::ModeMLPlayerGameData` | `0x01fa9264` | `0x0314bf0a` `0x0314d0ae` `0x0314c688` `0x0314d27f` `0x0314d2bf` |
| `menu::ModeMLRangeSetDialogMoney` | `0x02004a34` | `0x032aec5a` `0x032af58a` `0x032af7f9` `0x032aece9` `0x032aeb93` |
| `menu::ModeMLScoutMenu` | `0x01faadd4` | `0x03152e83` `0x031526cf` `0x0315259f` `0x03153690` `0x03152f12` `0x0315264f` |
| `menu::ModeMLScoutingSettings` | `0x01faa824` | `0x0315164c` `0x031522cf` `0x03150a6c` `0x0315137d` `0x03151f32` |
| `menu::ModeMLSeasonRecord` | `0x01fa6a2c` | `0x031387b8` `0x0313b17e` |
| `menu::ModeMLTeamRoleList` | `0x01fb2dfc` | `0x0318fb2a` `0x03194621` `0x03192c2d` `0x03191045` `0x031945f1` `0x0318fa08` … (8 in all) |
| `menu::ModeOfferAccept` | `0x01fa84c4` | `0x03149286` `0x031488da` `0x03146838` `0x03148fff` `0x03148a2a` `0x03148aec` … (7 in all) |
| `menu::Schedule` | `0x01fe367c` | `0x0322fc09` `0x03231f09` `0x03231b45` `0x03231bf6` `0x0322ff8a` `0x03231a59` … (7 in all) |
| `menu::ScheduleBase` | `0x0203931c` | `0x03367fa2` |
| `menu::ScheduleProgress` | `0x01fe3bcc` | `0x032321fb` `0x03231f19` `0x03234067` `0x03233c6b` |
| `menu::SquadNumberSet_ML` | `0x01f9f014` | `0x031191c1` `0x03117e08` |
| `menu::SquadNumberSet_ML_National` | `0x01f9f154` | `0x031191f1` `0x03117e4e` |
| `menu::SquadNumberSettingSel_ML` | `0x01f9f754` | `0x03119e3a` `0x03119e6a` |
| `menu::TeamSelectDefaultTeamML` | `0x020036c4` | `0x032aa340` `0x032aa28b` |
| `menu::TeamSelectRequestML` | `0x02003de4` | `0x032aaa96` `0x032aaac6` `0x032aadc0` |
| `process::CmnAchievementCheck` | `0x020e0524` | `0x035e5e39` `0x035e5f1e` `0x035e6107` |
| `process::CmnAutoSaveCheck` | `0x020e5f84` | `0x036083b1` `0x03608480` |
| `process::CmnAutoSaveCheckFlow` | `0x020e4cdc` | `0x035ff620` `0x035ff6ef` |
| `process::CmnAutoSaveIdleFlow` | `0x020e4b34` | `0x035ff089` `0x035fefd4` `0x035ff2d8` `0x035fef05` |
| `process::CmnAutoSaveSettingIdle` | `0x020e1134` | `0x035e7417` |
| `process::CmnAutoSystemSaveIdleFlow` | `0x020e161c` | `0x035e7a7a` `0x035e78ed` `0x035e78ad` |
| `process::CmnCheckCompeIndex` | `0x020e8934` | `0x03611ae8` `0x03611c86` |
| `process::CmnCheckCompeRegulation` | `0x020e8c1c` | `0x03611f05` `0x03611fd4` |
| `process::CmnCheckJoinCompe` | `0x020e89ac` | `0x03611b18` `0x03611dc6` |
| `process::CmnCoopSettingsCheck` | `0x020dffd4` | `0x035e5670` `0x035e580e` |
| `process::CmnEyeCatchCheck` | `0x020e657c` | `0x036092d3` `0x03609303` |
| `process::CmnGrowthCheck` | `0x020e7e94` | `0x0360f02d` `0x0360f0fc` |
| `process::CmnHallPlayerCheck` | `0x020e7cec` | `0x0360edda` `0x0360eea9` |
| `process::CmnInfoAccumulation` | `0x020e1d04` | `0x035f5515` `0x035f55e4` |
| `process::CmnLeagueRankingSel` | `0x020e0384` | `0x035e5bea` `0x035e5cb9` |
| `process::CmnLoadIdle` | `0x020e219c` | `0x035f88ed` `0x035f9aa2` `0x035fa42c` `0x035f9b22` `0x035fa45c` |
| `process::CmnLoadTeamDataIdle` | `0x020deb24` | `0x035e24af` `0x035e26c3` `0x035e2693` `0x035e2733` `0x035e2b9d` |
| `process::CmnMatchInit` | `0x020e40ec` | `0x035fe2cf` `0x035fe39e` |
| `process::CmnMatchOnlyDataCopy` | `0x020e34b4` | `0x035fd5af` `0x035fd67e` |
| `process::CmnMatchReportMenuReturn` | `0x020e6734` | `0x03609529` `0x036095f8` |
| `process::CmnMatchResultCheck` | `0x020e746c` | `0x0360dc3c` `0x0360dd0b` |
| `process::CmnModeClubGamePlanCreation` | `0x020e371c` | `0x035fd7fe` `0x035fd8cd` |
| `process::CmnModeInit` | `0x020e91b4` | `0x0361251d` `0x036125ec` |
| `process::CmnModeLiveDataAttach` | `0x020dfe14` | `0x035e536d` `0x035e4598` `0x035e5492` |
| `process::CmnModeMainMenuGamePlanCreation` | `0x020e3bfc` | `0x035fdd83` `0x035fde52` |
| `process::CmnModeMainMenuGamePlanRelease` | `0x020e3e6c` | `0x035fe113` `0x035fe1e2` |
| `process::CmnModeNationalGamePlanCreation` | `0x020e398c` | `0x035fda7e` `0x035fdb4d` |
| `process::CmnMonthlyBestElevenCheck` | `0x020e79a4` | `0x0360e645` `0x0360e714` |
| `process::CmnMonthlyCheck` | `0x020e7b54` | `0x0360ea9e` `0x0360eb6d` |
| `process::CmnMonthlyScheduleCheck` | `0x020e77cc` | `0x0360e261` `0x0360e330` |
| `process::CmnMyDataCheck` | `0x020e4e8c` | `0x035ff85e` `0x03606652` |
| `process::CmnOffModeGate` | `0x020df9bc` | `0x035e411b` `0x035e430f` |
| `process::CmnOfferListGamePlanCreation` | `0x020e30ac` | `0x035fd211` `0x035fd2e0` |
| `process::CmnOfferListGamePlanRelease` | `0x020e331c` | `0x035fd3f3` `0x035fd4c2` |
| `process::CmnOfferTeamInfoReturn` | `0x020e27c4` | `0x035fc8d8` `0x035fc9a7` |
| `process::CmnOpCheck` | `0x020e8ebc` | `0x0361234e` `0x0361241d` |
| `process::CmnPostCompeMenuReturn` | `0x020e46f4` | `0x035fe8d9` `0x035fe9a8` |
| `process::CmnPostCompeSelReturn` | `0x020e4534` | `0x035fe696` `0x035fe765` |
| `process::CmnPostLoadModeCheck` | `0x020e6c7c` | `0x03609b23` `0x03609bf2` |
| `process::CmnPostMatchUserCheck` | `0x020e81f4` | `0x0360f859` `0x0360f928` |
| `process::CmnPostMenuReturn` | `0x020e68ec` | `0x03609728` `0x036097f7` |
| `process::CmnPostSaveModeCheck` | `0x020e6ab4` | `0x03609927` `0x036099f6` |
| `process::CmnPromoDemoCheck` | `0x020e62bc` | `0x03608719` `0x036087e8` |
| `process::CmnReportEventCheck` | `0x020e579c` | `0x0360732e` `0x036073da` |
| `process::CmnReportEventFadeWaiting` | `0x020e5514` | `0x03606ef9` `0x03606fde` `0x0360702e` |
| `process::CmnRequestTeamInfoReturn` | `0x020e2954` | `0x035fcae9` `0x035fcbb8` |
| `process::CmnResetInit` | `0x020dda4c` | `0x035e1811` `0x035e1841` `0x035e1a7b` |
| `process::CmnReturnCoopSettingsCheck` | `0x020e004c` | `0x035e56a0` `0x035e592b` |
| `process::CmnReturnMemberList` | `0x020e06b4` | `0x035e61d4` `0x035e62a3` |
| `process::CmnRoleReportCheck` | `0x020e529c` | `0x03606c2e` `0x03606cfd` |
| `process::CmnSaveDataSaveCancel` | `0x020e5964` | `0x03607bae` `0x03607c7d` |
| `process::CmnSaveIdle` | `0x020e10bc` | `0x035fc2e9` |
| `process::CmnScheduleProcessCheck` | `0x020e5c64` | `0x03607db9` `0x03607e8c` |
| `process::CmnSeasonGrowthCheck` | `0x020e7614` | `0x0360df60` `0x0360e02f` |
| `process::CmnSetBGSave` | `0x020ea91c` | `0x036149ca` `0x03614a99` |
| `process::CmnStaffReportCheck` | `0x020e5104` | `0x036068f8` `0x03606ae2` |
| `process::CmnStandingsCheck` | `0x020e8054` | `0x0360f475` `0x0360f544` |
| `process::CmnStorageCheckOP` | `0x020e5df4` | `0x03608215` `0x036082e4` |
| `process::CmnSystemSaveIdle` | `0x020e13a4` | `0x035e781d` `0x035e76a0` `0x035e7680` |
| `process::CmnTeamDataSaveIdle` | `0x020e2624` | `0x035fc838` `0x035fc6bb` `0x035fc5f3` `0x035fc69b` |
| `process::CmnTeamInfoGamePlanCreation` | `0x020e2bbc` | `0x035fcca5` `0x035fcd74` |
| `process::CmnTeamInfoGamePlanRelease` | `0x020e2e44` | `0x035fcf1e` `0x035fd00d` |
| `process::CmnTeamSelCancel` | `0x020e0f2c` | `0x035e722b` `0x035e72fa` |
| `process::CmnUpdateAutoSaveSetting` | `0x020e6114` | `0x0360856d` `0x0360863c` |
| `process::CmnUpdateDayBegin` | `0x020e6f24` | `0x03609e57` `0x03609d22` `0x03609ec7` |
| `process::CmnUpdateDayEnd` | `0x020e71bc` | `0x0360b7af` `0x0360b08e` `0x0360b8ca` |
| `process::CmnUpdatePostAutoSave` | `0x020e1e94` | `0x035f5a7d` `0x035f5b4c` |
| `process::CmnUpdatePostMatch` | `0x020e847c` | `0x0360feac` `0x0360fa6e` `0x0360ff0c` |
| `process::CmnUpdatePreMatch` | `0x020e872c` | `0x03611182` `0x03611910` |
| `process::CmnUpdateSeasonEnd` | `0x020e48ac` | `0x035feb08` `0x035febd7` |
| `process::CmnUpdateSkipMatch` | `0x020e435c` | `0x035fe49e` `0x035fe56d` |
| `process::CompePDSelCancel` | `0x020ea0cc` | `0x03613f0b` `0x03613fda` |
| `process::CompePostUsersCheck` | `0x020ea3f4` | `0x03614329` `0x036143f8` |
| `process::CompePreUsersCheck` | `0x020ea264` | `0x036140d7` `0x036141a6` |
| `process::CompeTeamSelCancel` | `0x020e9f34` | `0x03613d5f` `0x03613e2e` |
| `process::InfoEvent` | `0x021022dc` | `0x0367bb17` |
| `process::InfoEventBL` | `0x021041c8` | `0x036d9543` `0x036daecb` |
| `process::InfoEventLeague` | `0x021022e8` | `0x0367bb47` `0x0367ba4c` |
| `process::InfoEventML` | `0x021027bc` | `0x036832fd` `0x03685083` |
| `process::InfoNews` | `0x02102a24` | - |
| `process::InfoNewsAfterMatch` | `0x02103588` | `0x036c221d` |
| `process::InfoNewsAfterMatchDetail` | `0x02103384` | `0x036b9f94` `0x036ba046` |
| `process::InfoNewsBeforeMatch` | `0x021039a4` | `0x036cd7f4` |
| `process::InfoNewsCompe` | `0x0210315c` | `0x036b6a3a` |
| `process::InfoNewsGeneral` | `0x02102a30` | `0x0368e696` |
| `process::InfoNewsGrowth` | `0x02102c30` | `0x036933f4` |
| `process::InfoNewsTransfer` | `0x02102e78` | `0x036a7949` |
| `process::InfoStaffReport` | `0x021025a8` | `0x03682b67` |
| `process::InfoStaffReportBL` | `0x02103db0` | `0x036d9061` `0x036d9140` |
| `process::InfoStaffReportML` | `0x021025b4` | `0x03682b97` `0x03682f42` |
| `process::KnockOutCreation` | `0x02138bf0` | `0x0376ee12` |
| `process::LeagueCreation` | `0x02138c00` | `0x0376f475` `0x037741b4` |
| `process::LeaguePreUsersCheck` | `0x020df5bc` | `0x035e3c6c` `0x035e3dad` |
| `process::LeagueTeamInfoUserNumCheck` | `0x020df74c` | `0x035e3f7f` `0x035e404e` |
| `process::MLProcessCoachEdit` | `0x020dee0c` | `0x035e3129` `0x035e31f8` |
| `process::ModeDataCreation` | `0x020e1a94` | `0x035e8ba8` `0x035ef91e` `0x035e90eb` `0x035e95c3` |
| `process::ModeDataCreationThread` | `0x020e191c` | `0x035e8b48` `0x035f4b87` |
| `process::OfflineNegociateReturn` | `0x020df0bc` | `0x035e3350` `0x035e341f` |
| `process::PlayerSearch` | `0x020d99c0` | `0x035d7f9c` |
| `process::PracticeCompeCreation` | `0x02138bf8` | `0x0376efdd` |
| `process::ProcessCmnFinanceReportCheck` | `0x020e0bac` | `0x035e68ff` `0x035e69ce` |
| `process::ProcessCmnLotCheck` | `0x020e0d74` | `0x035e6bcb` `0x035e6c9a` |
| `process::ProcessCmnMainMenuSelector` | `0x020e9454` | `0x036129d3` `0x03612a88` |
| `process::ProcessCmnModeTmpWork` | `0x020d9630` | `0x035d4e01` |
| `process::ProcessCmnModeTmpWork::NewsTexture` | `0x020d9628` | `0x035d3dfb` |
| `process::ProcessCmnNationalResultCheck` | `0x020e085c` | `0x035e6370` `0x035e643f` |
| `process::ProcessCmnPreMainCheck` | `0x020e9754` | `0x03612c40` `0x03612c80` `0x03612d35` |
| `process::ProcessCmnSeasonResultCheck` | `0x020e09fc` | `0x035e66df` `0x035e67ae` |
| `process::SpecialCoachTitleSet` | `0x02101168` | `0x036662b8` |
| `process::SpecialTitle` | `0x02101080` | `0x036661c8` |
| `process::SpecialTitleSetAFC` | `0x021010f8` | `0x0366c735` `0x0366691d` `0x0366a4ed` `0x0366696d` `0x03666999` `0x036668dd` |
| `process::SpecialTitleSetCONMEBOL` | `0x021010c0` | `0x0366a3d8` `0x0366689d` |
| `process::SpecialTitleSetUEFA` | `0x02101088` | `0x036667f1` `0x0366662d` |
| `process::SpecialTitleSetWorld` | `0x02101130` | `0x0366a602` `0x0366bd92` `0x03666b95` `0x03666a99` `0x03666b55` `0x036661f8` … (7 in all) |
| `process::UpdateDayBeginThread` | `0x020e6f90` | `0x03609e27` `0x0360b06e` |
| `process::UpdateDayEndThread` | `0x020e7228` | `0x0360b6e3` `0x0360dbf0` |
| `process::UpdatePostMatchThread` | `0x020e84e8` | `0x0360fe7c` `0x03611162` |

## Appendix C: the year for a league with a January season

| date | event | what |
|---|---|---|
| 1.1. | 1 | first day of the season: the year plan is written |
| 1.1. | 3 | first transfer window opens |
| 8.1. | 41 | title step of fcn_0362eb70, fcn_036696e1 (process::SpecialTitle, not read) |
| 11.1. | 26 | asked by fcn_0366f4bb and news functions (not read) |
| 30.1. | 4 | day before the first window closes (the daily scout step is left out) |
| 31.1. | 5 | first transfer window closes |
| 1.2. | 30 | day after a window closes: computer clubs plan their squads (fcn_036602e5) |
| 15.2. | 48 | report step fcn_0363beba (writes a staff report; not read) |
| 15.3. | 19 | taken to be a national team day (six a year) |
| 16.3. | 20 | the day after event 19 |
| 19.3. | 35 | draw day (process::ProcessCmnLotCheck) |
| 19.3. | 36 | draw day (process::ProcessCmnLotCheck) |
| 16.4. | 37 | draw day (process::ProcessCmnLotCheck) |
| 16.4. | 38 | draw day (process::ProcessCmnLotCheck) |
| 9.5. | 11 | asked by fcn_0364b81c (not read) |
| 25.5. | 19 | taken to be a national team day (six a year) |
| 26.5. | 20 | the day after event 19 |
| 28.5. | 39 | draw day (process::ProcessCmnLotCheck) |
| 13.6. | 11 | asked by fcn_0364b81c (not read) |
| 22.6. | 19 | taken to be a national team day (six a year) |
| 23.6. | 20 | the day after event 19 |
| 28.6. | 11 | asked by fcn_0364b81c (not read) |
| 28.6. | 31 | asked by fcn_03676016 (not read) |
| 30.6. | 14 | half-year step of fcn_036e1665 (not read) |
| 30.6. | 24 | asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts) |
| 30.6. | 13 | half-year step of fcn_036e067a, fcn_036e1568 (not read) |
| 30.6. | 22 | asked by fcn_0314910f only (not read) |
| 1.7. | 25 | money step fcn_03640d19; asked by process::ProcessCmnFinanceReportCheck |
| 1.7. | 6 | second transfer window opens |
| 26.7. | 45 | asked by fcn_03676016 (not read) |
| 4.8. | 10 | asked by fcn_0364c065 and the staff report (not read) |
| 20.8. | 19 | taken to be a national team day (six a year) |
| 21.8. | 20 | the day after event 19 |
| 26.8. | 42 | title step of fcn_0362eb70 (process::SpecialTitleSetUEFA, not read) |
| 27.8. | 32 | draw day (process::ProcessCmnLotCheck) |
| 27.8. | 27 | asked by fcn_0366f4bb and news functions (not read) |
| 30.8. | 7 | day before the second window closes (the daily scout step is left out) |
| 31.8. | 8 | second transfer window closes |
| 1.9. | 30 | day after a window closes: computer clubs plan their squads (fcn_036602e5) |
| 18.9. | 17 | asked by fcn_036f5728 (not read) |
| 19.9. | 16 | asked by the staff report and a transfer news function (not read) |
| 21.9. | 19 | taken to be a national team day (six a year) |
| 22.9. | 20 | the day after event 19 |
| 26.10. | 19 | taken to be a national team day (six a year) |
| 27.10. | 20 | the day after event 19 |
| 7.11. | 11 | asked by fcn_0364b81c (not read) |
| 10.12. | 33 | draw day (process::ProcessCmnLotCheck) |
| 10.12. | 34 | draw day (process::ProcessCmnLotCheck) |
| 12.12. | 11 | asked by fcn_0364b81c (not read) |
| 20.12. | 49 | money step fcn_03640d19 |
| 24.12. | 48 | report step fcn_0363beba (writes a staff report; not read) |
| 28.12. | 44 | title step of fcn_0362eb70, fcn_036696e1 (not read) |
| 29.12. | 43 | title step of fcn_0362eb70, fcn_036696e1 (not read) |
| 29.12. | 31 | asked by fcn_03676016 (not read) |
| 29.12. | 11 | asked by fcn_0364b81c (not read) |
| 30.12. | 28 | asked by fcn_0366f4bb and news functions (not read) |
| 31.12. | 12 | half-year step of fcn_036e1665 (not read) |
| 31.12. | 24 | asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts) |
| 31.12. | 15 | half-year step of fcn_036e067a, fcn_036e1568 (not read) |
| 31.12. | 23 | last day of the season: season-end processing |

## Appendix D: season kind by league id

Table `0x021687d0` (92 rows). Kind 0 = season from 1 July; every other kind = season
from 1 January. The ids are the game's league ids (`fcn_0385662c` gives the league of
a competition); their names are not looked up.

| kind | league ids |
|---|---|
| 0 | 17, 20, 18, 21, 19, 22, 50, 79, 80, 81, 82, 99, 2, 3, 4, 5, 6, 7, 23, 26, 24, 27, 25, 28, 53, 36, 41, 42, 83, 84, 85, 86, 87, 88, 89, 90, 91, 95 |
| 1 | 29, 30, 67, 13400, 13401, 51, 10200, 10201, 8, 9, 10, 76, 77, 78, 11, 12, 13, 100, 101, 102, 14, 29, 68, 59, 54, 38, 92 |
| 2 | 52, 15, 16, 55, 39, 44, 45, 97 |
| 3 | 60, 61, 62, 63, 64, 65, 66, 75, 74 |
| 4 | 40, 46 |
| 5 | 37, 43 |
| 6 | 1, 35, 34, 47, 48, 56 |

## Appendix E: role table

Table `0x0216f85c`, one row of `0x14` bytes per role, raw: three effect numbers
(10 = none, shown as "-") and the number at `+0x0c` ("kind") that `role_multiplier`
tests for 6. Effects 3, 4 and 5 are the ones `role_multiplier` uses; the others are
not followed. The role names are not looked up.

| role | effect 1 | effect 2 | effect 3 | kind |
| --- | --- | --- | --- | --- |
| 0 | - | - | - | - |
| 1 | - | - | - | 0 |
| 2 | - | - | - | 0 |
| 3 | - | - | - | - |
| 4 | 8 | 6 | - | - |
| 5 | - | - | - | - |
| 6 | - | - | - | - |
| 7 | 1 | - | - | - |
| 8 | - | - | - | - |
| 9 | 3 | - | - | - |
| 10 | 1 | - | - | - |
| 11 | 8 | 6 | - | - |
| 12 | 3 | - | - | - |
| 13 | 8 | 7 | - | - |
| 14 | 0 | - | - | 7 |
| 15 | 2 | - | - | 8 |
| 16 | 4 | - | - | 6 |
| 17 | 9 | - | - | 9 |
| 18 | 8 | 7 | 2 | 2 |
| 19 | 8 | 7 | 4 | 1 |
| 20 | - | - | - | 3 |
| 21 | - | - | - | 4 |
| 22 | - | - | - | 5 |

## Appendix F: who asks for each event

For each event number, the functions whose C tests it with `event_on_date` or
`event_on_day` (found by script: the number assigned just before the call). A class
name in brackets = the function is in that class's table.

| event | asked by |
|---|---|
| 1 | `fcn_031a502c` (menu::MainMenuML), `fcn_0360a350`, `fcn_03661f6b`, `fcn_03664a3d`, `fcn_036d7d15`, `fcn_036d9140` (process::InfoStaffReportBL), `fcn_036daecb` (process::InfoEventBL), `fcn_036e20d2` |
| 3 | `fcn_0360a350`, `fcn_0362579a`, `fcn_03640d19`, `fcn_0365c89a`, `fcn_03661f6b`, `fcn_036623d3`, `fcn_03664a3d`, `fcn_036800a9`, `fcn_03682f42` (process::InfoStaffReportML) … (15 in all) |
| 4 | `fcn_03652198` |
| 5 | `fcn_03137118` (menu::MainMenuBL), `fcn_031a502c` (menu::MainMenuML), `fcn_0329c6cf` (menu::MainMenuBL), `fcn_03609ec7` (process::CmnUpdateDayBegin), `fcn_0360bf0c`, `fcn_03658eda`, `fcn_0366365b`, `fcn_03682f42` (process::InfoStaffReportML), `fcn_03695b10` … (13 in all) |
| 6 | `fcn_031a502c` (menu::MainMenuML), `fcn_0360a350`, `fcn_0362579a`, `fcn_0365c89a`, `fcn_03661f6b`, `fcn_03664a3d`, `fcn_0366f4bb`, `fcn_036800a9`, `fcn_03682f42` (process::InfoStaffReportML) … (14 in all) |
| 7 | `fcn_03652198` |
| 8 | `fcn_03137118` (menu::MainMenuBL), `fcn_03156db0`, `fcn_0315916c`, `fcn_0315a7b6`, `fcn_0315f11b`, `fcn_031a502c` (menu::MainMenuML), `fcn_0329c6cf` (menu::MainMenuBL), `fcn_03609ec7` (process::CmnUpdateDayBegin), `fcn_0360bf0c` … (17 in all) |
| 9 | `fcn_03658821`, `fcn_0365cbbc`, `fcn_0365df66`, `fcn_03664d29`, `fcn_036e2d84`, `fcn_0388d1c3` |
| 10 | `fcn_0364c065`, `fcn_03682f42` (process::InfoStaffReportML), `fcn_0385477f` |
| 11 | `fcn_0364b81c`, `fcn_036823b8`, `fcn_036a69e1`, `fcn_038aee47` |
| 12 | `fcn_036e1665`, `fcn_036e20d2` |
| 13 | `fcn_0367affd`, `fcn_036e067a`, `fcn_036e1568` |
| 14 | `fcn_036e1665`, `fcn_036e20d2` |
| 15 | `fcn_0367affd`, `fcn_036e067a`, `fcn_036e1568` |
| 16 | `fcn_03682f42` (process::InfoStaffReportML), `fcn_0369655a`, `fcn_036d9140` (process::InfoStaffReportBL) |
| 17 | `fcn_036f34be`, `fcn_036f5728` |
| 19 | `fcn_031a502c` (menu::MainMenuML), `fcn_0360a350`, `fcn_0366f4bb`, `fcn_0367b994`, `fcn_03681aeb`, `fcn_038703cc` |
| 20 | `fcn_035fde52` (process::CmnModeMainMenuGamePlanCreation), `fcn_0367d797`, `fcn_036893b3`, `fcn_0368bc98`, `fcn_036d68df`, `fcn_036d6b8f`, `fcn_036da4d0`, `fcn_038700b7`, `fcn_038703cc` |
| 22 | `fcn_0314910f` |
| 23 | `fcn_0314910f`, `fcn_0329ae56` (menu::MainMenuBL), `fcn_032b5298` (menu::MainMenuChoiceLeague), `fcn_0360bf0c`, `fcn_03612ef7` (process::PreMainCheckThread), `fcn_03640686`, `fcn_03640d19`, `fcn_0366d620`, `fcn_0366f4bb` … (14 in all) |
| 24 | `fcn_031a502c` (menu::MainMenuML), `fcn_03649f1f`, `fcn_0364c065`, `fcn_03682f42` (process::InfoStaffReportML) |
| 25 | `fcn_035e69ce` (process::ProcessCmnFinanceReportCheck), `fcn_03640d19` |
| 26 | `fcn_03606928`, `fcn_03631bb6`, `fcn_0366f4bb`, `fcn_03683d47`, `fcn_036d0c58`, `fcn_036d9b56` |
| 27 | `fcn_03631bb6`, `fcn_0366f4bb`, `fcn_03683d47`, `fcn_036d0c58`, `fcn_036d9b56` |
| 28 | `fcn_03631bb6`, `fcn_0366f4bb`, `fcn_03683d47`, `fcn_036d0c58`, `fcn_036d9b56` |
| 29 | `fcn_03631bb6`, `fcn_0366f4bb`, `fcn_03683d47`, `fcn_036d0c58`, `fcn_036d9b56` |
| 30 | `fcn_036602e5`, `fcn_03661f6b` |
| 31 | `fcn_0360a350`, `fcn_03676016`, `fcn_03682f42` (process::InfoStaffReportML), `fcn_036d0796` |
| 32 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 33 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 34 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 35 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 36 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 37 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 38 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 39 | `fcn_035e6c9a` (process::ProcessCmnLotCheck), `fcn_036cdb49` |
| 41 | `fcn_0362eb70`, `fcn_036696e1` |
| 42 | `fcn_0362eb70`, `fcn_0366638e`, `fcn_036667f1` (process::SpecialTitleSetUEFA) |
| 43 | `fcn_0362eb70`, `fcn_036696e1` |
| 44 | `fcn_0362eb70`, `fcn_036696e1` |
| 45 | `fcn_0360a350`, `fcn_03676016` |
| 47 | `fcn_036523fb` |
| 48 | `fcn_031a269b` (menu::MainMenuML), `fcn_031a502c` (menu::MainMenuML), `fcn_0329ce18` (menu::MainMenuBL), `fcn_0360a350`, `fcn_0363beba`, `fcn_03682f42` (process::InfoStaffReportML) |
| 49 | `fcn_03640d19` |

## Appendix G: rounds of a league of 20 teams

`python3 fixtures.py 20`. The numbers are places in the competition's team list
(1 = first team of the list); the first team of each pair is the one stored first
(taken to be the home side). Rounds 20 to 38 are the return matches of rounds 1 to
19, with every third and every seventh round exchanged between the two halves
(section 5.3).

```
round  1: 1-11  2-12  3-13  4-14  5-15  6-16  7-17  8-18  9-19  10-20
round  2: 1-2  3-11  4-12  5-13  6-14  7-15  8-16  9-17  10-18  20-19
round  3: 2-4  3-1  11-5  12-6  13-7  14-8  15-9  16-10  17-20  18-19
round  4: 1-4  5-3  6-2  7-11  8-12  9-13  10-14  18-17  19-16  20-15
round  5: 1-5  6-4  7-3  8-2  9-11  10-12  17-16  18-15  19-14  20-13
round  6: 2-10  3-9  4-8  5-7  6-1  11-20  12-19  13-18  14-17  15-16
round  7: 2-19  3-20  4-10  5-9  6-8  7-1  11-18  12-17  13-16  14-15
round  8: 1-8  9-7  10-6  14-13  15-12  16-11  17-2  18-3  19-4  20-5
round  9: 2-15  3-16  4-17  5-18  6-19  7-20  8-10  9-1  11-14  12-13
round 10: 1-10  12-11  13-2  14-3  15-4  16-5  17-6  18-7  19-8  20-9
round 11: 1-20  11-2  12-3  13-4  14-5  15-6  16-7  17-8  18-9  19-10
round 12: 3-2  4-11  5-12  6-13  7-14  8-15  9-16  10-17  19-1  20-18
round 13: 1-18  2-5  3-4  11-6  12-7  13-8  14-9  15-10  16-20  17-19
round 14: 5-4  6-3  7-2  8-11  9-12  10-13  17-1  18-16  19-15  20-14
round 15: 6-5  7-4  8-3  9-2  10-11  16-1  17-15  18-14  19-13  20-12
round 16: 1-15  2-20  3-10  4-9  5-8  6-7  11-19  12-18  13-17  14-16
round 17: 1-14  2-18  3-19  4-20  5-10  6-9  7-8  11-17  12-16  13-15
round 18: 9-8  10-7  13-1  14-12  15-11  16-2  17-3  18-4  19-5  20-6
round 19: 1-12  2-14  3-15  4-16  5-17  6-18  7-19  8-20  9-10  11-13
round 20: 11-1  12-2  13-3  14-4  15-5  16-6  17-7  18-8  19-9  20-10
round 21: 2-1  11-3  12-4  13-5  14-6  15-7  16-8  17-9  18-10  19-20
round 22: 1-3  4-2  5-11  6-12  7-13  8-14  9-15  10-16  19-18  20-17
round 23: 2-6  3-5  4-1  11-7  12-8  13-9  14-10  15-20  16-19  17-18
round 24: 2-8  3-7  4-6  5-1  11-9  12-10  13-20  14-19  15-18  16-17
round 25: 1-6  7-5  8-4  9-3  10-2  16-15  17-14  18-13  19-12  20-11
round 26: 1-7  8-6  9-5  10-4  15-14  16-13  17-12  18-11  19-2  20-3
round 27: 2-17  3-18  4-19  5-20  6-10  7-9  8-1  11-16  12-15  13-14
round 28: 1-9  10-8  13-12  14-11  15-2  16-3  17-4  18-5  19-6  20-7
round 29: 2-13  3-14  4-15  5-16  6-17  7-18  8-19  9-20  10-1  11-12
round 30: 2-11  3-12  4-13  5-14  6-15  7-16  8-17  9-18  10-19  20-1
round 31: 1-19  2-3  11-4  12-5  13-6  14-7  15-8  16-9  17-10  18-20
round 32: 4-3  5-2  6-11  7-12  8-13  9-14  10-15  18-1  19-17  20-16
round 33: 1-17  2-7  3-6  4-5  11-8  12-9  13-10  14-20  15-19  16-18
round 34: 1-16  2-9  3-8  4-7  5-6  11-10  12-20  13-19  14-18  15-17
round 35: 7-6  8-5  9-4  10-3  15-1  16-14  17-13  18-12  19-11  20-2
round 36: 8-7  9-6  10-5  14-1  15-13  16-12  17-11  18-2  19-3  20-4
round 37: 1-13  2-16  3-17  4-18  5-19  6-20  7-10  8-9  11-15  12-14
round 38: 10-9  12-1  13-11  14-2  15-3  16-4  17-5  18-6  19-7  20-8
```
