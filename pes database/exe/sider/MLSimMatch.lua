-- MLSimMatch.lua, version 6: realistic simulated matches (Skip Match and AI-vs-AI)
-- in PES 2017 (Sider Lua module). Made for PES2017.exe sha256 44b0caaa...
--
-- What it changes, in the running game only (no file is touched):
--   1. Match outcomes (fcn_03707a1f): replaces the game's linear rating-diff cliff
--      (where diff >= 12 gives 100% win / 0% draw / 0% upset) with a smooth Davidson
--      win/draw/loss curve featuring home advantage, realistic draw rates, scaled
--      Master League captain role bonuses, and guaranteed non-zero W/L tails so
--      knockout and two-leg replay loops always terminate.
--   2. Scorelines (fcn_03705feb): replaces the game's flat uniform `rand() % max`
--      scorelines with weighted Poisson-derived distributions across 7 strength-gap
--      bands (1-0, 2-0, 2-1, 3-0, ... up to 6-5) plus weighted draw scorelines
--      (0-0, 1-1, 2-2, 3-3, 4-4).
--   3. Skip Match substitutions, GK protection & smart CPU subs (fcn_03707e71):
--      restores the user team's 3 CPU substitutions during Skip Match (instead of
--      forcing sub1 = sub2 = sub3 = 11), prevents slot 0 (GK) from ever being
--      subbed off for an outfielder, and ranks bench candidates by effective OVR
--      (condition arrow & fatigue) + small jitter instead of pure random order.
--   4. Dynamic match ratings (fcn_03708cc4): replaces the fixed 11-slot rating tables
--      with ratings driven by match result, goal difference, clean-sheet / heavy-
--      conceded positional adjustments, scaled goals + assists counts, yellow/red
--      card deductions, and per-player variance.
--   5. Realistic goal scorers & assists (fcn_03706ef6): replaces the top-5 cutoff
--      and hardcoded 20/15/10/5/50 assist split with exponential attribute weighting
--      across all 10 outfield players, configurable unassisted goals, and zero
--      self-assists.
--   6. Fair penalty shootouts & realistic extra time (fcn_037062ca & fcn_037063bb):
--      fixes the vanilla `rand(1)` bug where home wins 100% of simulated penalty
--      shootouts, replaces uniform `rand(3)` extra-time goals with strength-scaled
--      30-min extra time, and generates authentic shootout scorelines (3-1..7-6).
--   7. Yellow & red cards + suspensions (fcn_03708de9): issues position-weighted
--      yellow cards (0..4 per team), second-yellow red cards, and straight red cards
--      into stat_rec +0x0c, feeding directly into fcn_0370403e's competition card
--      tallies and suspensions.
--   8. Squad condition, lineup strength, fatigue & injury simulation effects
--      (eff_strength, fcn_038556f1, and post-match injury roll in fcn_03708de9):
--      evaluates each club's actual Starting XI from tactics (replacing unavailable
--      starters from the bench), excludes injured/suspended players, and adjusts
--      simulated match strength by condition arrow & fitness; scales match fatigue
--      by Stamina (with +30 min extra-time drain and optional AI team fatigue); and
--      rolls rare post-match injuries weighted by Injury Resistance and fatigue
--      (skipping GKs and preserving >= 8 healthy players).
--
-- It first checks that the game holds the expected code at every place and that the
-- unused memory caves are empty. If anything differs, it writes nothing and logs why
-- in sider.log.
--
-- Install: copy this file into the "modules" folder next to sider.exe and add
--     lua.module = "MLSimMatch.lua"
-- to sider.ini (in any order relative to MLMoney.lua, MLTransfers.lua, MLYear.lua).
--
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, pairs,
-- tonumber, type, tostring.

local m = {}

-- ============================ settings ============================

-- Set to false to run all safety checks and log without writing anything to memory.
local WRITE = true

-- Which simulated matches use the enhanced outcome + scoreline model:
--   "all"       : all simulated matches (Skip Match AND AI-vs-AI league/cup games)
--   "skip_only" : only the user's own match when skipped via Skip Match
--   false       : leave outcomes and scorelines as in the vanilla game
local SCOPE = "all"

-- Effective team OVR boost for the home side (0.0 to 15.0).
-- 2.4 gives ~46% home win / ~26% draw / ~28% away win between equal teams.
local HOME_ADVANTAGE = 2.4

-- OVR points per e-fold of odds ratio (2.0 to 30.0).
-- Smaller = stronger favorites; larger = more upsets. 6.2 respects OVR gaps realistically.
local ELO_SCALE = 6.2

-- Draw probability when effective home and away strengths are equal (0.05 to 0.55).
local BASE_DRAW = 0.27

-- Scales the game's Master League captain role bonus (+-10 / +-20) into OVR points
-- (0.0 to 1.0). At 0.2, +-10 becomes +-2 OVR and +-20 becomes +-4 OVR. 0.0 disables.
local CAPTAIN_WEIGHT = 0.2

-- Multiplier for expected goals in decisive wins (0.50 to 2.00).
-- 1.0 averages ~2.56 total goals per match across a league; lower for tighter games.
local GOAL_SCALE = 1.0

-- Relative weights for draw scorelines: { 0-0, 1-1, 2-2, 3-3, 4-4 }.
local DRAW_WEIGHTS = { 28.0, 46.0, 21.0, 4.5, 0.5 }

-- Let the user's team make its 3 CPU substitutions during Skip Match (true / false).
local SKIP_SUBS = true

-- Never sub off the starting goalkeeper (slot 0) for an outfielder (true / false).
local GK_PROTECT = true

-- Rank bench substitutes by effective OVR (arrow & fatigue) + small rotation jitter
-- instead of pure random order (true / false).
local SMART_SUBS = true

-- ---- Feature 1: Dynamic match ratings (fcn_03708cc4) ----

-- Enable dynamic match ratings for simulated matches (true / false).
local RATINGS = true

-- Base rating for { win, draw, loss } on the PES 0.0-10.0 scale (4.0 to 8.5 each).
local RATING_BASE = { 6.4, 6.1, 5.7 }

-- Rating tenths added/subtracted per goal of margin, capped at +-4 GD (0.0 to 3.0).
-- At 1.5 (default): +3 GD adds +0.4, -3 GD subtracts -0.4.
local RATING_GD = 1.5

-- Clean sheet bonus (0 goals conceded) for { GK/CB/FB/DMF, CMF and above } (0.0 to 2.0).
local RATING_CLEAN_SHEET = { 0.3, 0.1 }

-- Rating bonus per goal scored (0.0 to 2.0) and per assist (0.0 to 2.0).
local RATING_GOAL = 0.7
local RATING_ASSIST = 0.4

-- Rating deduction per yellow card (0.0 to 2.0) and for a red card (0.0 to 3.0).
local RATING_YELLOW = 0.3
local RATING_RED = 1.0

-- Random per-player match-day variance (+- this amount, 0.0 to 1.5).
local RATING_VARIANCE = 0.4

-- Output rating clamp { min, max } (within 1.0 to 10.0).
local RATING_RANGE = { 4.5, 9.5 }

-- ---- Feature 2: Realistic goal scorers & assists (fcn_03706ef6) ----

-- Enable exponential attribute-weighted goal scorer selection across all 10 outfielders.
local SCORERS = true

-- Enable exponential attribute-weighted assist selection across all 10 outfielders.
local ASSISTS = true

-- Attribute decay sharpness for goals (0.01 to 0.50). Higher concentrates goals on top
-- attackers; 0.11 gives ~26% CF / ~38% wingers / ~14% AMF / ~16% CMF-DMF / ~6% defenders.
local SCORER_SHARPNESS = 0.11

-- Attribute decay sharpness for assists (0.01 to 0.50).
local ASSIST_SHARPNESS = 0.045

-- Percentage of goals with no assist (set pieces, rebounds, solo runs; 0 to 100).
local UNASSISTED_PCT = 28

-- ---- Feature 3: Fair penalty shootouts & realistic extra time ----

-- Enable strength-scaled 30-min Extra Time and fair OVR-weighted Penalty Shootouts.
-- Fixes the vanilla `rand(1)` bug where home always wins simulated penalty shootouts.
local EXTRA_TIME_PK = true

-- Multiplier for extra-time goal rate (0.25 to 2.00; 1.0 = ~0.52 total goals in 30 min).
local ET_GOAL_SCALE = 1.0

-- Home shootout bias in percentage points (-25 to +25; 0 = 50/50 for equal teams).
local PK_HOME_BIAS = 0

-- Shootout win-chance shift in percentage points per 1 OVR difference (0.0 to 2.0).
local PK_OVR_WEIGHT = 0.5

-- ---- Feature 4: Yellow & red cards + competition suspensions ----

-- Issue position-weighted yellow cards (0..4 per team), 2nd-yellow reds, and
-- straight red cards during simulated matches (feeds into competition suspensions).
local CARDS = true

-- Average yellow cards per team per match (0.0 to 4.0; 1.7 matches top-flight average).
local YELLOW_AVG = 1.7

-- Percentage chance per team per match of a straight red card (0 to 30).
local RED_PCT = 4

-- ---- Feature 5: Squad condition, fatigue & injury simulation effects ----

-- Weight simulated team OVR by available players' condition arrow and fitness (true / false).
-- Excludes injured (attr 0x5e) and suspended players when evaluating simulated strength.
local CONDITION_STRENGTH = true

-- Evaluate each team's actual Starting XI from tactics (replacing injured/suspended
-- starters from the bench) instead of raw squad top-11 OVR (true / false).
local LINEUP_STRENGTH = true

-- OVR shift per condition arrow { red-down, orange-down, flat, green-up, blue-up } (-10 to +10).
local CONDITION_OVR = { -3, -1, 0, 1, 3 }

-- Fitness level below which player OVR begins dropping (40 to 100; 72 = full above 72%).
local FATIGUE_THRESHOLD = 72

-- Maximum OVR penalty at 0% fitness (0 to 20).
local FATIGUE_PENALTY = 5

-- Scale match fatigue drain by player Stamina (attr 0x25) and add +30 min for Extra Time.
local STAMINA_FATIGUE = true

-- How strongly Stamina (75 baseline) scales fitness drain (0.0 to 2.0; 1.0 = 0.5x..1.5x).
local STAMINA_WEIGHT = 1.0

-- Also apply stamina-scaled fitness drain to AI teams (true / false).
local AI_FATIGUE = true

-- Percentage chance per team per simulated match of a match injury (0 to 20; 0 disables).
local INJURY_PCT = 3

-- Injury duration range in days { min, max } (1 <= min <= max <= 60).
local INJURY_DAYS = { 7, 28 }

-- ========================= end of settings =========================

-- Generated by sim_cave.py (do not edit by hand; test_sim.py checks this block)
local CAVE = 0x047d3a50
local CAVE_SIZE = 1334
local CAVE_D = 0x047d4170
local CAVE_D_SIZE = 144
local CAVE_D2 = 0x047d4f60
local CAVE_D2_SIZE = 40
local CAVE_ET = 0x047d5040
local CAVE_ET_SIZE = 1457
local CAVE_C = 0x047b0060
local CAVE_C_SIZE = 405
local CAVE_PK = 0x047d6030
local CAVE_PK_SIZE = 839
local CODE_OFF = 0x018c
local DIFF_MIN = -25
local DIFF_MAX = 25
local PAIRS_COUNT = 21

local ROUTINES = {
    { 0x018c, "535689ce89d30fb7460483f83c740583f83d7514b865888003ffd08b402083f827745183f828744c833d503a7d0400744880bb1cb6dc0000743aff760c89d9b869298203ffd085c0740d8b8014030000c1e8073cff7522ff761089d9b869298203ffd085c0740d8b8014030000c1e8073cff750531c05e5bc3b8010000005e5bc3" },
    { 0x0210, "6a00518d4424048d0c245051b898598503ffd083c410c3" },
    { 0x0228, "89d98b5030b8dc3b7d04ffd084c0750c8b45088b00b971607003ffe18b45088b1083fa020f84a4000000a1604f7d040b05844f7d04741a5289d98b530ce88613000089c689d98b5310e87a13000089c75a5289f00305543a7d0429f885d27402f7d831f683f8fa7e1f4683f8ff7e194683f8037e134683f8077e0d4683f80b7e074683f80f7e01466bf61581c6463b7d04b9ff000000b8603c7d04ffd031c90fb6140e39d072064183f91472f20fb681313b7d0488c1c0e904240f5a85d27407ba59617003ffe2ba10617003ffe2b9ff000000b8603c7d04ffd031c90fb6912c3b7d0439d072064183f90472ef88c8ba10617003ffe2" },
    { 0x0320, "5053b8e5c08103ffd08b50308b4d10b8dc3b7d04ffd084c0750d5b588b4d0883f902e9a84ff3febb70417d048b7424048b55100fb642140fb64a17837d0c0074019189c229ca83fafc7d05bafcffffff83fa047e05ba040000000faf530c89d09929d0d1f8518b4d0883f902740a3b4d0c740a034308eb07034304eb020303598b560cc1ea0e83e20f85c9750f83fa037605034314eb1c034310eb1783f903721283fa02770d83e9023b4b2c76038b4b2c29c80fb64e080faf4b1801c80fb64e090faf4b1c01c8e8e4220000508b4b208d0c4d01000000b8603c7d04ffd05a2b432001c23b53247d038b53243b53287e038b532888d189f05b83c404e9024ff3fe" },
    { 0x0424, "89ca8b4d0cb8dc3b7d04ffd084c0740f807d08007413833da0417d0400752c31c9894de4e9a030f3fe833da4417d040074edb964000000b8603c7d04ffd03b05a8417d047305e92634f3fe8b45108b308b400439c67205e91534f3fe0fb65608525083ec1831db31ff89f13b4c2418736483fb0b735f0fb6410884c07449807d080075168b5514668b12663b11750b8b55148b52043b5104742d8b54241c29c2790231d28d05ac417d04d1ea807d08007505d1ea83c01883fa177605ba170000000fb60410eb0231c001c766893c5c4383c10ceb9685ff750883c420e99033f3fe89f9b8603c7d04ffd031c90fb7144c39d072064139d972f3496bc90c01ce8b7e048b368975d8897ddc83c420e9be32f3fe" },
}

local ET_IMAGE = "5589e583ec68535657c745fc060000008955f80fb7018945f46a008d45fc508d45f850e8a20a09ff83c40c0fb6d8a1604f7d040b05844f7d040f84e7020000e8617004ff8b40308945f0ff75f889c1e8d5d804ff85c00f84ca0200008b9028030000c1ea0983e27f0f84b802000083fa207605ba200000008955ec8945dc05f80000008945d8895dd4833d844f7d04000f84bc01000083fa0b0f82b30100008d45e0508b4ddce8ad2c94feff75e4ff75e08b4df0e830d904ff85c00f84910100008b55f081c264ea5f0039d00f848001000031d231c90fb6bc08480200003b7dec0f836b0100000fa3fa0f82620100000fabfa4183f90b72dd8945d08955cc31c08945e88945c88945c431f68b45d00fb68c30480200008b45d88d04c88b088b5004894de08955e452518b4df0e8f1d404ff85c0744289c78d45f4508d45e050e8ec6508ff83c40884c0742c8b45d00fb644306883f80c770885f6740985c07505b80d00000089f98d55e0e8c00100000145c8ff45e8eb03ff45c44683fe0b728b837dc4000f849b0000008d7d9831c08b4dc4f3ab31f63b75ec73720fa375cc72698b45d88d04f08b088b5004894de08955e452518b4df0e866d404ff85c0744a89c78d45f4508d45e050e8616508ff83c40884c0743489f98d55e0b80d000000e84a01000089c331c931ff8b5598413b4dc4730e8b448d9839d07df289c289cfebec39d37e04895cbd9846eb8931c93b4dc473118b448d9885c074060145c8ff45e841ebea8b55e885d275088b45d4e9f30000008b45c883fa0b0f83c3000000b90b00000029d16bc92801c8e9b20000008d7d9831c0b90b000000f3ab8945e88b75d831db3b5dec736e8b0e8b560483c608894de08955e452518b4df0e8a0d304ff85c0744f89c78d45f4508d45e050e89b6408ff83c40884c0743989f98d55e0b80d000000e8840000005389c331c931ff8b55984183f90b730e8b448d9839d07df289c289cfebec39d37e04895cbd985bff45e843eb8d8b55e885d275058b45d4eb4331c031c903448d984183f90b72f683fa0b730cb90b00000029d16bc92801c883c00531d2b90b000000f7f183f8287d05b82800000083f8637e09b863000000eb0289d85f5e5b89ec5dc3005356575089ce89e06a025052e8973806ff83c40c0fb6d8833d604f7d040074418b461c89c1c1e91583e10783f90477090fbe91784f7d0401d383e07f8b0d644f7d0485c9741b39c8731789ca29c20faf15684f7d0489c8d1e801d031d2f7f129c383fb1e7d05bb1e00000083fb6d7e05bb6d00000089d883c4045f5e5bc30000833d804f7d0400745a8b4d088b95a0feffffe8d5e7ffff84c074488b8db4feffff8d955cfeffffb80d000000e84fffffff50c785b4feffff040000008d85bbfeffff508d85b4feffff50e8590508ff83c4085901c83dff0000007616b8ff000000eb0fc785b4feffff64000000e8360508ffe9812cf3fe00e8786c04ff8b50308b4d0ce864e7ffff84c0750abb03000000e96c0ef3fe8b450c89c18b500ce8adfbffff89c38b450c89c18b5010e89efbffff29c3031d543a7d0483fbec7d05bbecffffff83fb147e05bb1400000031f66bc30305e60000000faf05e4417d0499b964000000f7f983f83c7d05b83c0000003de00100007e05b8e001000050b9e8030000e868e7ffff5989cac1ea0339d0720839c819c0f7d8eb05b8020000008944b5ec880783c703f7db4683fe0272a08b5dec8b75f0e9fe0df3fe0089f189fab8dc3b7d04ffd084c0750b0fb67df3b85d7d7003ffe0a1604f7d040b05844f7d04741a89f18b560ce8e3faffff89c389f18b5610e8d7faffff29c3eb0e0fb645f3837de8007402f7d889c38b45ec837de8007402f7d88b0d583a7d0485c9740599f7f901c383fbe77d05bbe7ffffff83fb197e05bb1900000083c3190fb7349d603a7d040fb73c9d623a7d04b9e8030000b8603c7d04ffd039f0730931c0b9107e7003ffe139f8730cb802000000b9107e7003ffe1b801000000b9107e7003ffe1"
local CARDS_CODE = "565753e87dc006ff8b503089f1e86a3b020084c07437803d774f7d040074158d45d450e8300000008d45e450e82700000083c408803d744f7d040074108d55d4e8a36102008d55e4e89b6102005b5f5e8d55d4e9938ef5fe5589e553565783ec488b45088b388b400439c70f830601000031db31c939c7734483fb0b733f50515789f1e8db34f5fe5989449c1c85c0741c8b500cc1ea0e83e20f83fa097605ba090000000fb682f6417d04eb0231c001c166894c5c04584383c70cebb8895c244485c90f84ae00000051b9ff000000e82c3b020031ff3a87f1417d0472064783ff0472f25b31f639fe735f89d9e80e3b0200e8880000008b4c841885c974488b510c89d0c1e81383e00383f802733885c0742551b964000000e8e23a02005983f81473238b510c81e2ffffe3ff81ca0000140089510ceb0f81e2ffffe7ff81ca0000080089510c46eb9db964000000e8ac3a02003a05f0417d04731b89d9e89d3a0200e8170000008b4c841885c9740781490c0000040083c4485f5e5b5dc331c98b542448663b444c0472064139d172f44989c8c3"
local PK_IMAGE = "5589e55356e8ab6004ff8b50308b4d0ce897dbffff84c0750e5e5b5d5589e583ec08e96a03f3fe8b450c89c18b500ce8dcefffff89c38b450c89c18b5010e8cdefffff29c383fbec7d05bbecffffff83fb147e05bb1400000089d80faf05ec417d0499b90a000000f7f90305e8417d0483f80f7d05b80f00000083f8557e05b85500000089c3b964000000e8a0dbffff39d80f93c20fb6d28b75088916b964000000e889dbffff31c93a8140617d0472064183f90772f20fb68148617d0488c1c0e904240f8b550c833e007508884a16884219eb06884a198842165e5b5dc208000000000000000000000000000000008b4e0cf7c10000040074042b4370c3c1e91383e1030faf4b6c29c8c300000000182c3e4a545a60ff5443425365314176833d6c4f7d040075088d4df8e981f607ff8b450c8b1885db0f8ed200000083fb5a77348b45100fb7003dffff000074275089f1e8b7c904ff85c0741b8d8e4c156f0039c874118a50150a50180a50160a5019740383c31e8b4718c1e80783e07f7505b84b00000083f8287d05b82800000083f8637e05b863000000b94b00000029c10faf0d704f7d0489c899b90a000000f7f983c06483f8327d05b8320000003d960000007e05b8960000006bdb030fafc305f401000031d2b9e8030000f7f18b4f04c1e91c85c9751085c0740c6bc00931d2b90a000000f7f18b4f1c83e17f29c1790231c9516a5f89f9e8701f05ffe975f607ff000000803d744f7d04000f84210100008b023b42040f83160100005356575589e583ec508b328b7a04b964000000e8e8d9ffff3a05744f7d040f83ec000000e85c5e04ff8b583031c9894dfc894df839fe0f838400000083f90b737f51ff7604ff3689d9e8b5c304ff5989448dcc31d285c0745380780200754dff45fc8b5004c1ea1c74420fb6502383e20383fa027605ba02000000b80300000029d08b548dcc8b521c83e27f83fa647605ba6400000050b86400000029d031d251b919000000f7f1595a01c20155f88b45f86689444db44183c60ce974ffffff894db0837dfc0776478b4df885c97440e82bd9ffff31c98b55b04a39d1730a663b444db4720341ebf28b5c8dcc85db741f0fb60d764f7d04e803d9ffff0fb60d754f7d0401c8506a5e89d9e8401e05ff89ec5d5f5e5bc3"

local SITES = {
    outcome    = { "outcome probability", 0x03707d56, "0fb6bdf3ffffff", "e9d1d70c019090" },
    score      = { "scoreline model",     0x0370606c, "8b45088b00", "e907dc0c01" },
    smart_subs = { "smart CPU subs",      0x037080d9, "c785b4feffff64000000e8b0d81400", "e912d30c0190909090909090909090" },
    gk_protect = { "GK sub protection",   0x0370818d, "31ff", "9090" },
    skip_subs  = { "skip-match subs",     0x03708230, "7417", "eb17" },
    ratings    = { "match ratings",       0x03708d39, "8b4d0883f902", "e932b00c0190" },
    scorer     = { "scorers & assists",   0x03706f35, "31c9898de4ffffff", "e93acf0c01909090" },
    et         = { "extra time",          0x037062ed, "bb03000000", "e976f10c01" },
    pk         = { "penalty shootout",    0x037063bb, "5589e583ec08", "e970fc0c0190" },
    cards      = { "cards & injuries",    0x03708f45, "8d95d4ffffff", "e916710a0190" },
    fatigue    = { "stamina fatigue",     0x038557dc, "8d8df8ffffff", "e96f09f80090" },
    ai_fatigue = { "AI team fatigue",     0x038557d6, "0f84de000000", "909090909090" },
}

local CONTEXT = {
    { "outcome entry",    0x03707a1f, "5589e56aff68edf2" },
    { "outcome fallback", 0x03707d5d, "8d5cbf2383fb64" },
    { "outcome return",   0x03707e10, "8b8df4ffffff64890d00000000595f5e" },
    { "score entry",      0x03705feb, "5589e583ec0c" },
    { "score fallback",   0x03706071, "31c985c00f85a4000000" },
    { "score done H",     0x03706110, "5f5e884b148843175b89ec5dc2" },
    { "score done A",     0x03706159, "5f5e884b178843145b89ec5dc2" },
    { "sub candidate",    0x037080ac, "8b85b4feffff8b502c" },
    { "sub return",       0x037080e8, "888564feffff83c408" },
    { "gk sub check",     0x03708189, "85c07502" },
    { "ratings entry",    0x03708cc4, "5589e551535657" },
    { "ratings fallback", 0x03708d3f, "75098a0cbd98" },
    { "ratings done",     0x03708d73, "8b3560ff4f02884d14" },
    { "scorer entry",     0x03706ef6, "5589e583ec38" },
    { "scorer fallback",  0x03706f3d, "384d080f84cc" },
    { "scorer picked",    0x03707244, "8b8dccffffff5756" },
    { "scorer none",      0x037072e5, "8b8dfcffffff5f5e" },
    { "et entry",         0x037062ca, "5589e583ec14" },
    { "et done",          0x03706329, "8b9decffffff8bb5" },
    { "pk fallback",      0x037063c1, "568d85ffffffff" },
    { "cards fallback",   0x03708f4b, "52566a005389f9" },
    { "fatigue entry",    0x038556f1, "5589e583ec18535657" },
    { "fatigue branch",   0x038557d0, "3cff750884db" },
    { "fatigue fallback", 0x038557e2, "5131db6a5f89f989" },
    { "fatigue exit",     0x038558ba, "5f5e5b89ec5dc3" },
    { "mode obj",         0x0381c0e5, "a1e0036502c3" },
    { "menu status",      0x03808865, "a1e8f36402c3" },
    { "team record",      0x03822969, "5589e55689ce" },
    { "team tactics",     0x03117d98, "5589e58b91f8010000" },
    { "tactics rec",      0x03822a29, "5589e58b45085689" },
    { "player rec",       0x03822663, "5589e58b4508" },
    { "fix rec",          0x03822b3f, "5589e58b4508" },
    { "player set",       0x038281b0, "5589e58b4508" },
    { "player ovr",       0x03838c18, "5589e5e8c534" },
    { "player elig",      0x0385b771, "5589e551a148" },
    { "team strength",    0x03865b0a, "5589e581ec18" },
    { "mode random",      0x03855998, "5589e551578b" },
    { "stat rec lookup",  0x037035c3, "5589e583ec08" },
}

local function hex(s)
    local t = {}
    for i = 1, #s do t[i] = string.format("%02x", string.byte(s, i)) end
    return table.concat(t)
end

local function unhex(h)
    local t = {}
    for i = 1, #h, 2 do t[#t + 1] = string.char(tonumber(string.sub(h, i, i + 1), 16)) end
    return table.concat(t)
end

local function round(x)
    if x >= 0 then return math.floor(x + 0.5) end
    return math.ceil(x - 0.5)
end

local function clamp(x, lo, hi)
    if x < lo then return lo end
    if x > hi then return hi end
    return x
end

local function u16_bytes(v)
    v = v % 65536
    return string.char(v % 256, math.floor(v / 256))
end

local function u32_bytes(v)
    v = v % 4294967296
    local b0 = v % 256
    local b1 = math.floor(v / 256) % 256
    local b2 = math.floor(v / 65536) % 256
    local b3 = math.floor(v / 16777216) % 256
    return string.char(b0, b1, b2, b3)
end

local function is_num(v)
    return type(v) == "number" and v == v and v ~= math.huge and v ~= -math.huge
end

local function settings_fault()
    if type(WRITE) ~= "boolean" then return "WRITE must be true or false" end
    if SCOPE ~= false and SCOPE ~= "all" and SCOPE ~= "skip_only" then
        return 'SCOPE must be "all", "skip_only", or false'
    end
    if not is_num(HOME_ADVANTAGE) or HOME_ADVANTAGE < 0 or HOME_ADVANTAGE > 15 then
        return "HOME_ADVANTAGE must be a number from 0 to 15"
    end
    if not is_num(ELO_SCALE) or ELO_SCALE < 2 or ELO_SCALE > 30 then
        return "ELO_SCALE must be a number from 2 to 30"
    end
    if not is_num(BASE_DRAW) or BASE_DRAW < 0.05 or BASE_DRAW > 0.55 then
        return "BASE_DRAW must be a number from 0.05 to 0.55"
    end
    if not is_num(CAPTAIN_WEIGHT) or CAPTAIN_WEIGHT < 0 or CAPTAIN_WEIGHT > 1 then
        return "CAPTAIN_WEIGHT must be a number from 0 to 1"
    end
    if CAPTAIN_WEIGHT > 0 and round(1 / CAPTAIN_WEIGHT) < 1 then
        return "CAPTAIN_WEIGHT is too large"
    end
    if not is_num(GOAL_SCALE) or GOAL_SCALE < 0.5 or GOAL_SCALE > 2.0 then
        return "GOAL_SCALE must be a number from 0.5 to 2.0"
    end
    if type(DRAW_WEIGHTS) ~= "table" or #DRAW_WEIGHTS ~= 5 then
        return "DRAW_WEIGHTS must be a table of 5 numbers (for 0-0 .. 4-4)"
    end
    local dsum = 0
    for i = 1, 5 do
        if not is_num(DRAW_WEIGHTS[i]) or DRAW_WEIGHTS[i] < 0 then
            return "DRAW_WEIGHTS entries must be non-negative numbers"
        end
        dsum = dsum + DRAW_WEIGHTS[i]
    end
    if dsum <= 0 then return "DRAW_WEIGHTS must have a positive sum" end
    if type(SKIP_SUBS) ~= "boolean" then return "SKIP_SUBS must be true or false" end
    if type(GK_PROTECT) ~= "boolean" then return "GK_PROTECT must be true or false" end
    if type(SMART_SUBS) ~= "boolean" then return "SMART_SUBS must be true or false" end

    if type(RATINGS) ~= "boolean" then return "RATINGS must be true or false" end
    if type(RATING_BASE) ~= "table" or #RATING_BASE ~= 3 then
        return "RATING_BASE must be { win, draw, loss }"
    end
    for i = 1, 3 do
        if not is_num(RATING_BASE[i]) or RATING_BASE[i] < 4.0 or RATING_BASE[i] > 8.5 then
            return "RATING_BASE entries must be numbers from 4.0 to 8.5"
        end
    end
    if not is_num(RATING_GD) or RATING_GD < 0 or RATING_GD > 3.0 then
        return "RATING_GD must be a number from 0 to 3.0"
    end
    if type(RATING_CLEAN_SHEET) ~= "table" or #RATING_CLEAN_SHEET ~= 2 then
        return "RATING_CLEAN_SHEET must be { def, att }"
    end
    for i = 1, 2 do
        if not is_num(RATING_CLEAN_SHEET[i]) or RATING_CLEAN_SHEET[i] < 0 or RATING_CLEAN_SHEET[i] > 2.0 then
            return "RATING_CLEAN_SHEET entries must be numbers from 0 to 2.0"
        end
    end
    if not is_num(RATING_GOAL) or RATING_GOAL < 0 or RATING_GOAL > 2.0 then
        return "RATING_GOAL must be a number from 0 to 2.0"
    end
    if not is_num(RATING_ASSIST) or RATING_ASSIST < 0 or RATING_ASSIST > 2.0 then
        return "RATING_ASSIST must be a number from 0 to 2.0"
    end
    if not is_num(RATING_YELLOW) or RATING_YELLOW < 0 or RATING_YELLOW > 2.0 then
        return "RATING_YELLOW must be a number from 0 to 2.0"
    end
    if not is_num(RATING_RED) or RATING_RED < 0 or RATING_RED > 3.0 then
        return "RATING_RED must be a number from 0 to 3.0"
    end
    if not is_num(RATING_VARIANCE) or RATING_VARIANCE < 0 or RATING_VARIANCE > 1.5 then
        return "RATING_VARIANCE must be a number from 0 to 1.5"
    end
    if type(RATING_RANGE) ~= "table" or #RATING_RANGE ~= 2 then
        return "RATING_RANGE must be { min, max }"
    end
    if not is_num(RATING_RANGE[1]) or not is_num(RATING_RANGE[2])
        or RATING_RANGE[1] < 1.0 or RATING_RANGE[2] > 10.0 or RATING_RANGE[1] > RATING_RANGE[2] then
        return "RATING_RANGE must satisfy 1.0 <= min <= max <= 10.0"
    end

    if type(SCORERS) ~= "boolean" then return "SCORERS must be true or false" end
    if type(ASSISTS) ~= "boolean" then return "ASSISTS must be true or false" end
    if not is_num(SCORER_SHARPNESS) or SCORER_SHARPNESS < 0.01 or SCORER_SHARPNESS > 0.50 then
        return "SCORER_SHARPNESS must be a number from 0.01 to 0.50"
    end
    if not is_num(ASSIST_SHARPNESS) or ASSIST_SHARPNESS < 0.01 or ASSIST_SHARPNESS > 0.50 then
        return "ASSIST_SHARPNESS must be a number from 0.01 to 0.50"
    end
    if not is_num(UNASSISTED_PCT) or UNASSISTED_PCT < 0 or UNASSISTED_PCT > 100 then
        return "UNASSISTED_PCT must be a number from 0 to 100"
    end

    if type(EXTRA_TIME_PK) ~= "boolean" then return "EXTRA_TIME_PK must be true or false" end
    if not is_num(ET_GOAL_SCALE) or ET_GOAL_SCALE < 0.25 or ET_GOAL_SCALE > 2.0 then
        return "ET_GOAL_SCALE must be a number from 0.25 to 2.0"
    end
    if not is_num(PK_HOME_BIAS) or PK_HOME_BIAS < -25 or PK_HOME_BIAS > 25 then
        return "PK_HOME_BIAS must be a number from -25 to 25"
    end
    if not is_num(PK_OVR_WEIGHT) or PK_OVR_WEIGHT < 0 or PK_OVR_WEIGHT > 2.0 then
        return "PK_OVR_WEIGHT must be a number from 0 to 2.0"
    end

    if type(CARDS) ~= "boolean" then return "CARDS must be true or false" end
    if not is_num(YELLOW_AVG) or YELLOW_AVG < 0 or YELLOW_AVG > 4.0 then
        return "YELLOW_AVG must be a number from 0 to 4.0"
    end
    if not is_num(RED_PCT) or RED_PCT < 0 or RED_PCT > 30 then
        return "RED_PCT must be a number from 0 to 30"
    end

    if type(CONDITION_STRENGTH) ~= "boolean" then return "CONDITION_STRENGTH must be true or false" end
    if type(LINEUP_STRENGTH) ~= "boolean" then return "LINEUP_STRENGTH must be true or false" end
    if type(CONDITION_OVR) ~= "table" or #CONDITION_OVR ~= 5 then
        return "CONDITION_OVR must be a table of 5 numbers (for arrows 0..4)"
    end
    for i = 1, 5 do
        if not is_num(CONDITION_OVR[i]) or CONDITION_OVR[i] < -10 or CONDITION_OVR[i] > 10 then
            return "CONDITION_OVR entries must be numbers from -10 to 10"
        end
    end
    if not is_num(FATIGUE_THRESHOLD) or FATIGUE_THRESHOLD < 40 or FATIGUE_THRESHOLD > 100 then
        return "FATIGUE_THRESHOLD must be a number from 40 to 100"
    end
    if not is_num(FATIGUE_PENALTY) or FATIGUE_PENALTY < 0 or FATIGUE_PENALTY > 20 then
        return "FATIGUE_PENALTY must be a number from 0 to 20"
    end
    if type(STAMINA_FATIGUE) ~= "boolean" then return "STAMINA_FATIGUE must be true or false" end
    if not is_num(STAMINA_WEIGHT) or STAMINA_WEIGHT < 0 or STAMINA_WEIGHT > 2.0 then
        return "STAMINA_WEIGHT must be a number from 0 to 2.0"
    end
    if type(AI_FATIGUE) ~= "boolean" then return "AI_FATIGUE must be true or false" end
    if not is_num(INJURY_PCT) or INJURY_PCT < 0 or INJURY_PCT > 20 then
        return "INJURY_PCT must be a number from 0 to 20"
    end
    if type(INJURY_DAYS) ~= "table" or #INJURY_DAYS ~= 2 then
        return "INJURY_DAYS must be { min, max }"
    end
    if not is_num(INJURY_DAYS[1]) or not is_num(INJURY_DAYS[2])
        or INJURY_DAYS[1] < 1 or INJURY_DAYS[2] > 60 or INJURY_DAYS[1] > INJURY_DAYS[2] then
        return "INJURY_DAYS must satisfy 1 <= min <= max <= 60"
    end
    return nil
end

local function build_image()
    local buf = {}
    for i = 1, CAVE_SIZE do buf[i] = "\0" end

    local function put(off, s)
        for i = 1, #s do
            buf[off + i] = string.sub(s, i, i)
        end
    end

    -- 1. CFG (16 bytes at +0x000)
    local scope_int = (SCOPE == "skip_only") and 1 or 0
    local home_adv_int = round(HOME_ADVANTAGE)
    local cap_div = (CAPTAIN_WEIGHT > 0) and round(1.0 / CAPTAIN_WEIGHT) or 0
    put(0x000, u32_bytes(scope_int) .. u32_bytes(home_adv_int) .. u32_bytes(cap_div) .. u32_bytes(0x4d4c5335))

    -- 2. OUTCOME_TABLE (51 x 4 bytes at +0x010)
    local nu = 2.0 * BASE_DRAW / (1.0 - BASE_DRAW)
    local ot_off = 0x010
    for diff = DIFF_MIN, DIFF_MAX do
        local eff = diff + HOME_ADVANTAGE
        local a = math.exp(eff / ELO_SCALE)
        local d = nu * math.sqrt(a)
        local z = a + 1.0 + d
        local ph = clamp(round(1000.0 * (a / z)), 1, 998)
        local pd = clamp(round(1000.0 * (d / z)), 1, 999 - ph)
        put(ot_off, u16_bytes(ph) .. u16_bytes(ph + pd))
        ot_off = ot_off + 4
    end

    -- 3. DRAW_CDF (5 bytes at +0x0dc)
    local dsum = 0.0
    for i = 1, 5 do dsum = dsum + DRAW_WEIGHTS[i] end
    local d_acc = 0.0
    local d_prev = 0
    local d_bytes = {}
    for i = 1, 5 do
        d_acc = d_acc + DRAW_WEIGHTS[i] / dsum
        local val = (i == 5) and 255 or clamp(round(d_acc * 255.0), d_prev, 255)
        d_prev = val
        d_bytes[i] = string.char(val)
    end
    put(0x0dc, table.concat(d_bytes))

    -- 4. PAIR_SCORES (21 bytes at +0x0e1)
    local pairs_list = {}
    local p_bytes = {}
    for gw = 1, 6 do
        for gl = 0, gw - 1 do
            local idx = #pairs_list + 1
            pairs_list[idx] = { gw, gl }
            p_bytes[idx] = string.char(gw * 16 + gl)
        end
    end
    if #pairs_list ~= PAIRS_COUNT then return nil end
    put(0x0e1, table.concat(p_bytes))

    -- 5. WIN_CDF (7 x 21 bytes at +0x0f6)
    local fact = { [0] = 1, 1, 2, 6, 24, 120, 720 }
    local function poisson(lam, k)
        return (lam ^ k) * math.exp(-lam) / fact[k]
    end
    local band_lambdas = {
        { 0.76, 1.58 }, -- Band 0 (d <= -6, Big Upset)
        { 1.02, 1.32 }, -- Band 1 (d -5..-1, Slight Upset)
        { 1.35, 1.00 }, -- Band 2 (d  0..3, Equal)
        { 1.55, 0.85 }, -- Band 3 (d  4..7, Slight Fav)
        { 1.76, 0.72 }, -- Band 4 (d  8..11, Clear Fav)
        { 1.98, 0.60 }, -- Band 5 (d 12..15, Strong Fav)
        { 2.22, 0.50 }, -- Band 6 (d >= 16, Huge Fav)
    }
    local wc_off = 0x0f6
    for bi, b in ipairs(band_lambdas) do
        local lam_w = b[1] * GOAL_SCALE
        local lam_l = b[2] * GOAL_SCALE
        local damp = math.max(0.20, 0.58 - 0.065 * (bi - 1))
        local weights = {}
        local wsum = 0.0
        for i, p in ipairs(pairs_list) do
            local gw, gl = p[1], p[2]
            local w = poisson(lam_w, gw) * poisson(lam_l, gl)
            if gw - gl >= 4 then
                w = w * math.exp(-damp * (gw - gl - 3))
            end
            weights[i] = w
            wsum = wsum + w
        end
        local w_acc = 0.0
        local w_prev = 0
        local w_bytes = {}
        for i = 1, PAIRS_COUNT do
            w_acc = w_acc + weights[i] / wsum
            local val = (i == PAIRS_COUNT) and 255 or clamp(round(w_acc * 255.0), w_prev, 255)
            w_prev = val
            w_bytes[i] = string.char(val)
        end
        put(wc_off, table.concat(w_bytes))
        wc_off = wc_off + PAIRS_COUNT
    end

    -- 6. ROUTINES
    for _, r in ipairs(ROUTINES) do
        local bytes = unhex(r[2])
        if r[1] + #bytes > CAVE_SIZE then return nil end
        put(r[1], bytes)
    end

    local out = table.concat(buf)
    if #out ~= CAVE_SIZE then return nil end
    return out
end

local function build_data_d()
    local t = {
        u32_bytes(round(RATING_BASE[1] * 10)),
        u32_bytes(round(RATING_BASE[2] * 10)),
        u32_bytes(round(RATING_BASE[3] * 10)),
        u32_bytes(round(RATING_GD * 2)),
        u32_bytes(round(RATING_CLEAN_SHEET[1] * 10)),
        u32_bytes(round(RATING_CLEAN_SHEET[2] * 10)),
        u32_bytes(round(RATING_GOAL * 10)),
        u32_bytes(round(RATING_ASSIST * 10)),
        u32_bytes(round(RATING_VARIANCE * 10)),
        u32_bytes(round(RATING_RANGE[1] * 10)),
        u32_bytes(round(RATING_RANGE[2] * 10)),
        u32_bytes(3), -- max clean-sheet-opposite conceded penalty (tenths)
        u32_bytes(SCORERS and 1 or 0),
        u32_bytes(ASSISTS and 1 or 0),
        u32_bytes(round(UNASSISTED_PCT)),
    }
    for i = 0, 23 do
        t[#t + 1] = string.char(clamp(round(120.0 * math.exp(-SCORER_SHARPNESS * (2 * i))), 1, 255))
    end
    for i = 0, 23 do
        t[#t + 1] = string.char(clamp(round(120.0 * math.exp(-ASSIST_SHARPNESS * (4 * i))), 1, 255))
    end
    t[#t + 1] = u32_bytes(round(RATING_YELLOW * 10))
    t[#t + 1] = u32_bytes(round(RATING_RED * 10))
    t[#t + 1] = u32_bytes(round(ET_GOAL_SCALE * 100))
    t[#t + 1] = u32_bytes(round(50 + PK_HOME_BIAS))
    t[#t + 1] = u32_bytes(round(PK_OVR_WEIGHT * 10))
    t[#t + 1] = string.char(round(RED_PCT))

    local fact = { [0] = 1, 1, 2, 6, 24 }
    if YELLOW_AVG <= 0 then
        for _ = 0, 4 do t[#t + 1] = string.char(255) end
    else
        local w = {}
        local wsum = 0.0
        for k = 0, 4 do
            w[k] = (YELLOW_AVG ^ k) * math.exp(-YELLOW_AVG) / fact[k]
            wsum = wsum + w[k]
        end
        local acc = 0.0
        local prev = 0
        for k = 0, 4 do
            acc = acc + w[k] / wsum
            local val = (k == 4) and 255 or clamp(round(acc * 255.0), prev, 255)
            prev = val
            t[#t + 1] = string.char(val)
        end
    end

    local pos_w = { 2, 18, 16, 20, 14, 10, 8, 7, 7, 8 }
    for i = 1, 10 do
        t[#t + 1] = string.char(pos_w[i])
    end

    local out = table.concat(t)
    if #out ~= CAVE_D_SIZE then return nil end
    return out
end

local function build_data_d2()
    local inj_min = round(INJURY_DAYS[1])
    local inj_max = round(INJURY_DAYS[2])
    local t = {
        u32_bytes(CONDITION_STRENGTH and 1 or 0),
        u32_bytes(round(FATIGUE_THRESHOLD)),
        u32_bytes(round(FATIGUE_PENALTY)),
        u32_bytes(STAMINA_FATIGUE and 1 or 0),
        u32_bytes(round(STAMINA_WEIGHT * 10)),
        string.char(round(INJURY_PCT)),
        string.char(inj_min),
        string.char(inj_max - inj_min + 1),
        string.char(CARDS and 1 or 0),
    }
    for i = 1, 5 do
        local v = round(CONDITION_OVR[i])
        t[#t + 1] = string.char((v < 0) and (v + 256) or v)
    end
    t[#t + 1] = "\0\0\0"
    t[#t + 1] = u32_bytes(SMART_SUBS and 1 or 0)
    t[#t + 1] = u32_bytes(LINEUP_STRENGTH and 1 or 0)
    local out = table.concat(t)
    if #out ~= CAVE_D2_SIZE then return nil end
    return out
end

local function check_bytes(name, addr, expected_hex)
    local got = memory.read(addr, #expected_hex / 2)
    local same = (got ~= nil and hex(got) == expected_hex)
    log(string.format("check: %-18s at %08x  %s", name, addr,
        same and "as expected" or ("DIFFERENT: " .. (got and hex(got) or "not readable"))))
    return same, got
end

function m.init(ctx)
    log("MLSimMatch 6: realistic simulated matches, smart/GK-safe subs, lineup & condition strength, ratings, scorers, ET/PK, cards, fatigue & injuries")

    local fault = settings_fault()
    if fault then
        log("RESULT: nothing written. Settings: " .. fault)
        return
    end
    local need_outcome = (SCOPE ~= false)
    local need_scorers = (SCORERS or ASSISTS)
    local need_et_pk = EXTRA_TIME_PK
    local need_fatigue = STAMINA_FATIGUE
    local need_ai_fatigue = (STAMINA_FATIGUE and AI_FATIGUE)
    local need_injury = (round(INJURY_PCT) > 0)
    local need_cards_hook = (CARDS or need_injury)
    local need_et_cave = (need_outcome or need_et_pk or SMART_SUBS)
    local need_pk_cave = (RATINGS or need_et_pk or need_fatigue or need_injury)
    local need_data_d = (RATINGS or need_scorers or need_et_pk or CARDS)
    local need_data_d2 = (need_et_cave or need_fatigue or need_cards_hook)
    local need_cave = (need_outcome or RATINGS or need_scorers or need_et_pk or need_cards_hook or SMART_SUBS)

    if not need_cave and not need_pk_cave and not SKIP_SUBS and not GK_PROTECT then
        log("RESULT: nothing written. All features are off: simulated matches run as in the game.")
        return
    end

    local cave_image = nil
    if need_cave then
        cave_image = build_image()
        if cave_image == nil then
            log("RESULT: nothing written. The module file is damaged (cave size).")
            return
        end
    end

    local data_d_image = nil
    if need_data_d then
        data_d_image = build_data_d()
        if data_d_image == nil then
            log("RESULT: nothing written. The module file is damaged (data cave size).")
            return
        end
    end

    local data_d2_image = nil
    if need_data_d2 then
        data_d2_image = build_data_d2()
        if data_d2_image == nil then
            log("RESULT: nothing written. The module file is damaged (data2 cave size).")
            return
        end
    end

    local et_image = need_et_cave and unhex(ET_IMAGE) or nil
    if et_image and #et_image ~= CAVE_ET_SIZE then
        log("RESULT: nothing written. The module file is damaged (ET cave size).")
        return
    end

    local pk_image = need_pk_cave and unhex(PK_IMAGE) or nil
    if pk_image and #pk_image ~= CAVE_PK_SIZE then
        log("RESULT: nothing written. The module file is damaged (PK cave size).")
        return
    end

    local cards_image = need_cards_hook and unhex(CARDS_CODE) or nil
    if cards_image and #cards_image ~= CAVE_C_SIZE then
        log("RESULT: nothing written. The module file is damaged (cards cave size).")
        return
    end

    -- 1. Check all context instructions
    local good = true
    for _, c in ipairs(CONTEXT) do
        if not check_bytes(c[1], c[2], c[3]) then good = false end
    end

    -- 2. Check target sites + caves
    local active_sites = {}
    if need_outcome then
        active_sites[#active_sites + 1] = "outcome"
        active_sites[#active_sites + 1] = "score"
    end
    if SKIP_SUBS then
        active_sites[#active_sites + 1] = "skip_subs"
    end
    if GK_PROTECT then
        active_sites[#active_sites + 1] = "gk_protect"
    end
    if SMART_SUBS then
        active_sites[#active_sites + 1] = "smart_subs"
    end
    if RATINGS then
        active_sites[#active_sites + 1] = "ratings"
    end
    if need_scorers then
        active_sites[#active_sites + 1] = "scorer"
    end
    if need_et_pk then
        active_sites[#active_sites + 1] = "et"
        active_sites[#active_sites + 1] = "pk"
    end
    if need_cards_hook then
        active_sites[#active_sites + 1] = "cards"
    end
    if need_fatigue then
        active_sites[#active_sites + 1] = "fatigue"
    end
    if need_ai_fatigue then
        active_sites[#active_sites + 1] = "ai_fatigue"
    end

    for _, key in ipairs(active_sites) do
        local s = SITES[key]
        local ok, got = check_bytes(s[1], s[2], s[3])
        if not ok then
            if got ~= nil and string.sub(hex(got), 1, 2) == "e9" then
                log("RESULT: nothing written. Simulated match hooks are already modified "
                    .. "(another module or MLSimMatch.lua listed twice in sider.ini).")
                return
            end
            good = false
        end
    end

    local function check_empty(label, addr, sz)
        local room = memory.read(addr, sz)
        local empty = (room ~= nil and room == string.rep("\0", sz))
        log(string.format("check: %-18s at %08x  %s", label, addr, empty and "empty" or "NOT EMPTY"))
        if not empty then good = false end
    end

    if need_cave then check_empty("free memory", CAVE, CAVE_SIZE) end
    if need_data_d then check_empty("free data memory", CAVE_D, CAVE_D_SIZE) end
    if need_data_d2 then check_empty("free data2 memory", CAVE_D2, CAVE_D2_SIZE) end
    if need_et_cave then check_empty("free ET memory", CAVE_ET, CAVE_ET_SIZE) end
    if need_pk_cave then check_empty("free PK memory", CAVE_PK, CAVE_PK_SIZE) end
    if need_cards_hook then check_empty("free card memory", CAVE_C, CAVE_C_SIZE) end

    if not good then
        log("RESULT: nothing written. This game does not hold what the module expects; send this log.")
        return
    end

    if not WRITE then
        log("RESULT: nothing written (WRITE = false). All checks passed.")
        return
    end

    -- 3. Write caves first (nothing jumps to them yet)
    local function write_cave(label, addr, img)
        memory.write(addr, img)
        if memory.read(addr, #img) ~= img then
            log("RESULT: the " .. label .. " could not be written; the game's code is unchanged. Send this log.")
            return false
        end
        return true
    end

    if need_cave and not write_cave("cave", CAVE, cave_image) then return end
    if need_data_d and not write_cave("data cave", CAVE_D, data_d_image) then return end
    if need_data_d2 and not write_cave("data2 cave", CAVE_D2, data_d2_image) then return end
    if need_et_cave and not write_cave("ET cave", CAVE_ET, et_image) then return end
    if need_pk_cave and not write_cave("PK cave", CAVE_PK, pk_image) then return end
    if need_cards_hook and not write_cave("cards cave", CAVE_C, cards_image) then return end

    -- 4. Patch active hook sites
    for _, key in ipairs(active_sites) do
        local s = SITES[key]
        local new = unhex(s[4])
        memory.write(s[2], new)
        local stuck = (memory.read(s[2], #new) == new)
        log(string.format("written: %-16s at %08x  %s", s[1], s[2], stuck and "ok" or "FAILED"))
        if not stuck then
            log("RESULT: a change did not go in. Quit the game, remove the module, send this log.")
            return
        end
    end

    local parts = {}
    if need_outcome then
        parts[#parts + 1] = string.format(
            "outcomes + scorelines (%s, home +%.1f OVR, scale %.1f, draw %.0f%%, goals %.2fx)",
            SCOPE, HOME_ADVANTAGE, ELO_SCALE, BASE_DRAW * 100, GOAL_SCALE)
    end
    if SKIP_SUBS then
        parts[#parts + 1] = "Skip Match CPU substitutions"
    end
    if GK_PROTECT then
        parts[#parts + 1] = "GK sub protection"
    end
    if SMART_SUBS then
        parts[#parts + 1] = "smart CPU subs"
    end
    if RATINGS then
        parts[#parts + 1] = string.format(
            "dynamic ratings (base %.1f/%.1f/%.1f, range %.1f-%.1f)",
            RATING_BASE[1], RATING_BASE[2], RATING_BASE[3], RATING_RANGE[1], RATING_RANGE[2])
    end
    if need_scorers then
        parts[#parts + 1] = string.format(
            "%s (unassisted %d%%)",
            (SCORERS and ASSISTS) and "scorers & assists" or (SCORERS and "scorers" or "assists"),
            round(UNASSISTED_PCT))
    end
    if need_et_pk then
        parts[#parts + 1] = string.format(
            "ET/PK (ET %.2fx, PK bias %+d%%, OVR %.1f)",
            ET_GOAL_SCALE, PK_HOME_BIAS, PK_OVR_WEIGHT)
    end
    if CARDS then
        parts[#parts + 1] = string.format(
            "cards (avg %.1f Y, %d%% straight R)",
            YELLOW_AVG, round(RED_PCT))
    end
    if (CONDITION_STRENGTH or LINEUP_STRENGTH) and (need_outcome or need_et_pk) then
        local sp = {}
        if LINEUP_STRENGTH then sp[#sp + 1] = "lineup XI" end
        if CONDITION_STRENGTH then
            sp[#sp + 1] = string.format("condition (fatigue <%d%% -%d)",
                round(FATIGUE_THRESHOLD), round(FATIGUE_PENALTY))
        end
        parts[#parts + 1] = "strength: " .. table.concat(sp, " + ")
    end
    if need_fatigue then
        parts[#parts + 1] = string.format(
            "stamina fatigue (weight %.1fx%s)",
            STAMINA_WEIGHT, AI_FATIGUE and ", AI on" or ", user only")
    end
    if need_injury then
        parts[#parts + 1] = string.format(
            "injuries (%d%%, %d-%dd)",
            round(INJURY_PCT), round(INJURY_DAYS[1]), round(INJURY_DAYS[2]))
    end
    log("RESULT: installed. Active: " .. table.concat(parts, "; ") .. ".")
end

return m
