-- MLTransfers.lua, version 9: the transfers between the computer clubs in the PES 2017
-- Master League (Sider Lua module). Made for PES2017.exe sha256 44b0caaa... and for
-- MLMoney.lua version 7, whose player values it uses.
--
-- What it changes, in the running game only (no file is touched). Each part has its own
-- switch in the settings below:
--   * price ceiling (CEILING): a computer club looks at the price. Up to the ceiling of
--     its place in the club ranking it signs as before, above it less and less often, and
--     far above it never. The game looks at the rating only.
--   * selling side (SELL_SIDE): a player whose club will not let him go no longer takes
--     one of the three places on a buyer's list. In the game he does, and the buyer then
--     often ends with nobody or with a player without a contract.
--   * club personas (PERSONA): every club gets a character: where it looks for players
--     (without a contract, on the lists of other clubs, in other clubs' squads) and in
--     which order, which ages it wants, how well it judges a player, how far it goes for
--     him, how good a player must be for it, how good a player still comes to it, and how
--     many of its own players it keeps. The big clubs are named one by one (CLUBS); the
--     others draw a character that fits their place in the ranking. Two clubs of one
--     character still differ a little (PERSONA_SPREAD, AGE_SHIFT). A club holds on to
--     its first team, except against a clearly bigger club (KEEP_BEST). A club with
--     too many players for a part of the pitch lets them go more easily
--     (SQUAD_PRESSURE, new in version 9).
--   * scouting (SCOUTING): a club knows only a part of the players (how many is a number
--     of its persona). Players a club has put on its list are known to all, and so are
--     the good ones (KNOWN_FROM) and the famous ones (KNOWN_FAME).
--   * rivals (RIVALS): two clubs that are rivals do not buy each other's players.
--   * position need (NEED): a club looks for a better player for the weakest place of
--     its eleven, the goalkeeper included. In the game a club looks for a player only
--     when a place of its eleven is empty or when it has fewer than 25 players.
--   * the mood of a deal (DEAL_MOOD): a club does not answer the same way on every day of
--     a career, and the club that sells has a leaning of its own (a seller, a trader, a
--     builder or a hoarder, drawn from its id). The same two clubs and the same player are
--     still answered the same way on the same day, so a reload changes nothing.
--   * offers for your own players (INCOMING): the game picks the club that makes an offer
--     for one of your players by a slot of the competition in hand. The module answers that
--     look-up itself, with the club of the nearest slot among those that would really take
--     him, by the rules the computer clubs choose their players by: no rival of yours, a
--     character that wants him (age band, ambition, prestige), a club that knows him, one
--     that is looking where he is, a place for his position in its plan (or its position
--     need asking for it), and money enough for his value (the ceiling of its level, with
--     the wealth, premium, fame and panic of its character). Every draw has the day of the
--     career in it. The same offers come; when no club passes, the game's answer stands.
-- With every switch off but CEILING, and RIVALS empty, the module works as its version 1
-- did.
--
-- What it cannot do: no money is booked for a computer club, there are no offers, wages
-- or loans between computer clubs, and no club remembers anything. For one player a club
-- is looking at, the module answers: may he go on its list or not. NEED adds one more
-- position a club looks for; it does not choose the player.
--
-- It first checks that MLMoney.lua is installed, that the game holds the expected code
-- and that the memory it needs is empty. If anything differs it writes nothing and says
-- so in sider.log. MLMoney.lua is not touched by it and works with or without it.
--
-- Install: copy this file and MLMoney.lua into the "modules" folder next to sider.exe
-- and add, in this order,
--     lua.module = "MLMoney.lua"
--     lua.module = "MLTransfers.lua"
-- to sider.ini. Sider starts the modules in the order of these lines, and this one needs
-- the other to be in before it. Remove the second line to have the computer clubs choose
-- as in the game again.
--
-- It needs no new career: it works from the next time the computer clubs choose players
-- (the first day of a season, 1 September, 1 February).
--
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, tonumber, type.

local m = {}

-- ============================ settings ============================

-- false: check and report only, write nothing.
local WRITE = true

-- Price ceiling of the computer clubs. In the game a computer club has no money. It
-- chooses the players it signs by rating, age and position, never by price, and when it
-- finds nobody for a position in the rating range of its size it looks again among all
-- players, from the best down.
-- With this setting a computer club compares a player's value (the value MLMoney.lua
-- computes, before the game's random change) with the ceiling of its place in the
-- game's club ranking. Up to the ceiling it takes the player as the game does. Above it,
-- see CEILING_STRETCH and the settings after it. A player it passes over is skipped and
-- the next best is looked at. The ceilings, in the ten groups the game itself uses for
-- the rating range: millions for the clubs at place
--     1-10, 11-20, 21-50, 51-80, 81-120, 121-170, 171-220, 221-260, 261-300, all others.
-- 0.01 to 9999 each, or 0 for a group without a ceiling. false: no club looks at a price.
-- Your own club is not touched: what you can buy is a matter of your budget, and offers
-- for your players go another way. No money is booked by this setting; a computer club
-- still has no account, and between two computer clubs the game has no offer and no
-- price: the setting decides only whether the player is within reach.
-- These numbers: about the value of the most valuable player of the middle club of each
-- group in the squads this module was set against, with more room for the first twenty
-- clubs (README.md has the table; ceiling_survey.py prints it for your edit file).
-- If you change VALUE in MLMoney.lua much, change these with it.
-- A persona moves the ceiling of its club up or down (wealth).
local CEILING = { 200, 100, 50, 28, 18, 12, 8, 6, 4.5, 3 }

-- How far a club goes above its ceiling, in percent of the ceiling. At the ceiling a
-- player is sure to be within reach; from there the chance falls evenly and is gone at
-- this much above it. With 50: a player 10 percent above the ceiling is within reach of
-- 4 clubs in 5 of that group, 25 percent above of every second club, 50 percent above of
-- none. Which club goes how far for which player is fixed by the two of them (no dice
-- are thrown), so the same club answers the same way while the player's value stays.
-- 0 to 300. 0: a hard ceiling, nothing above it. A persona changes it for its club
-- (premium).
local CEILING_STRETCH = 50

-- Need. The ceiling of a club is this many percent higher
--   * in its second search, when it found nobody for the position in its own rating
--     range (it then looks at the dearer players of that range again before it goes
--     further down),
--   * when it looks for a key player, which the ten or twenty best clubs do for one
--     position on the last day of a window, and
--   * with PERSONA on, while its squad is smaller than SQUAD_NEED.
-- CEILING_STRETCH comes on top: with 30 and 50 a club in need never goes beyond 1.95
-- times its ceiling. 0 to 300. 0: need changes nothing. A persona changes it for its
-- club (panic).
local CEILING_NEED = 30

-- A seller who wants to sell. For a player his club has put on its list of players to
-- let go, this many percent of his value count against the ceiling. 0 to 100; 100: he
-- counts like any other.
local CEILING_LISTED = 70

-- The same for a player the game signs without a transfer (as far as the code was read:
-- the players without a contract). 0 to 100; 100: he counts like any other.
-- Version 1 had 50 here. In a career played with it, 506 of 511 signings of one window
-- were players without a contract, and the small clubs took the best of them: with the
-- discount a player worth twice a club's ceiling was within its reach. 100 takes the
-- discount away (versions 2 to 4). 75 since version 5: by now `prestige` of the personas
-- keeps a good player away from a small club, whatever he costs.
local CEILING_FREE = 75

-- The second search. A computer club looks for a player in a rating range that goes by
-- its place in the ranking (the smallest clubs 47 to 74, the ten best 83 to 99). When it
-- finds nobody for a position there, the game lets it look again among all players,
-- from rating 99 down. It leaves out the stars of other clubs who are not for sale, but
-- not the players without a club and not those who have outgrown their club: a small
-- club can come away with one of the best of them.
-- true: in that second search a club takes nobody rated above the top of its own
-- range (74, 75, 76, 77, 78, 79, 80, 83, 86 from the smallest clubs up; the ten best
-- clubs have no limit), so it looks further down, not further up. Without this, the
-- ceiling alone still lets a small club sign a great player of 38 whose value has fallen
-- below it. false: the second search goes from 99 down as in the game.
-- CEILING_STRETCH and CEILING_NEED do not move this limit. Used only while CEILING is on.
-- A persona can switch it off for itself with `rating = false` (see ARCHETYPES): with it,
-- only Galactico and Retirement team look further up in that second search.
local CEILING_RATING = true

-- The selling side. The game lists the first three players who fit a position and only
-- then asks whether their club lets them go. It does for a listed player, and for another
-- player only if his club counts more than 23 players and
--   * he is one of those who have outgrown their club, or
--   * his status band is below 7 and his club is not one of the first twenty, or
--   * the buyer is one of the first ten or twenty and looks for a key player.
-- If none of the three may go, the club signs nobody for that position, although more
-- players stood further down the list.
-- true: the same question is asked before a player takes one of the three places, so
-- the list holds only players who can really move. false: as in the game.
local SELL_SIDE = true

-- Club personas. true: every computer club has a character (ARCHETYPES, PERSONA_GROUPS,
-- CLUBS below). false: all clubs behave alike, as in version 1, and the settings from
-- here to the end of the settings are not used.
local PERSONA = true

-- Scouting. true: a club knows only a part of the players without a contract and of the
-- players of other clubs (the number `knows` of its persona); which ones is fixed by
-- club and player. A player his club has listed is known to every club. false: every
-- club knows every player. Needs PERSONA.
local SCOUTING = true

-- A player of this rating or more is known to every club: nobody overlooks a star.
-- Below it SCOUTING counts as above. 0 to 100; 100: no player is known to all (version 2).
-- 70 since this setting: a club no longer overlooks a player rated 70 or more, so the
-- scouting draw is left to the ones below that (80 before, 80 in version 2).
local KNOWN_FROM = 70

-- A player of this popularity or more is known to every club as well: a famous name is
-- not overlooked, whatever his rating. The game keeps a popularity for every player; in
-- the career the module was set against the highest is 1,110, a player rated 80 to 84 has
-- about 660, and 400 or more have a third of the world known by name; 600 or more, the
-- number of version 5, have 942 of 19,921, and 700 (version 4) have 395.
-- 0 to 4096; 4096: off, no player is known for his name (version 3). Needs SCOUTING.
local KNOWN_FAME = 400

-- A player without a contract costs no fee, so a club is less strict about his age: for
-- him `strict` of the persona (below) counts only this many percent. With 35 a club that
-- refuses 60 of 100 players outside its ages refuses 21 of 100 such players without a
-- contract. 0 to 100; 100: off, as for every other player (version 3); 50: version 4; 0:
-- his age is never a reason. Needs PERSONA.
local STRICT_FREE = 35

-- A club holds on to its first team. Three numbers:
--   1. a player counts as first team if his rating is at most this many points below
--      the rating of his club's first eleven (STRENGTH below), or better. 0 to 99.
--   2. for each point he stands above that line, this many percent are added to `keeps`
--      of his club's persona. With { 4, 12, 2 }: a reserve five points below the eleven
--      goes as `keeps` says; a player as good as the eleven stays 48 percent more often;
--      one four points better than the eleven nearly always stays. 0 to 100; 0: off, all
--      players of a club go alike (version 2).
--   3. none of this holds against a buyer whose first eleven is at least this many
--      points better than the eleven of the player's club: a club cannot hold a player
--      against a clearly bigger one. 0 to 99; 99: it holds against every buyer.
-- Players a club has listed are not kept. Needs PERSONA.
local KEEP_BEST = { 4, 12, 2 }

-- A club with too many players for a part of the pitch keeps them less often. If it has
-- more players of a group than `positions` says, `keeps` of its persona (with what
-- KEEP_BEST adds) counts `keeps_drop` lower for every player of that group, not below 0.
-- The groups, by the position a player is registered for: GK; DF = CB, LB, RB;
-- MF = DMF, CMF, LMF, RMF, AMF; FW = LWF, RWF, SS, CF. A player who is in a deal already
-- is not counted.
-- With the numbers below a club with 7 forwards lets a spare forward go as if its
-- `keeps` were 0 or nearly 0 (the personas have a `keeps` of 5 to 40). A forward of its
-- first team is still held by KEEP_BEST, only less firmly. When a forward has left and
-- it has 6 again, it keeps them as before.
-- positions: 0 to 99 each. keeps_drop: 0 to 100. false, or keeps_drop = 0: off (as up
-- to version 8). Needs PERSONA. The other rules stay: with SELL_SIDE a club that counts 23 players
-- or fewer still sells nobody.
local SQUAD_PRESSURE = { positions = { GK = 3, DF = 8, MF = 9, FW = 6 }, keeps_drop = 40 }

-- The mood of a deal. `keeps` of the selling club (its persona, KEEP_BEST and SQUAD_PRESSURE)
-- is moved by two things drawn from the deal itself: the buying club, the selling club, the
-- player and the day of the career. Nothing is stored, so the same deal on the same day is
-- answered the same way after a reload, and the same player is not answered the same way
-- twice in a career. (In the game a club answers the same way on every day of the window.)
--   * mood: the most the day moves `keeps`, in percent, down or up. 0 to 30. 0: off.
--   * style: for each of the four styles of a club -- seller, trader, builder, hoarder -- how
--     many percent the style adds to or takes from `keeps`. A club that CLUBS names keeps the
--     character its archetype gives it; the style is a lean on that character, so the four
--     numbers below sit where the archetypes of those names are. -15 to 15 each.
-- With mood = 0 and every style 0 the module answers as version 9 did. Needs PERSONA.
local DEAL_MOOD = { mood = 8, style = { seller = -12, trader = -3, builder = 5, hoarder = 12 } }

-- Two clubs of one persona are not the same: each number of a persona (but not the
-- order of the places; for the ages see AGE_SHIFT) is, for each club, up to this many
-- percent lower or higher. Fixed by the club, so a club keeps its character for the
-- whole career. 0 to 50. 0: all clubs of a persona are alike.
local PERSONA_SPREAD = 20

-- The ages of a persona are moved for each club by up to this many years, down or up
-- (both ages by the same number, fixed by the club): with 2, clubs of a persona with
-- ages 24 to 28 want 22 to 26, 23 to 27, ... or 26 to 30. 0 to 5; 0: off (version 2).
local AGE_SHIFT = 2

-- How good a club's first eleven is taken to be: rating = first number x the club's
-- points in the game's club ranking + second number, kept inside the rating range of the
-- club's group. `ambition` and `prestige` of a persona are measured from it. These two
-- numbers fit the mean rating of the best eleven of the 499 clubs of the career the
-- module was set against (PSG 1,464 points: 87; the last club 984 points: 62).
-- First 0 to 0.5, second 0 to 99.
local STRENGTH = { 0.0533, 9.45 }

-- The month of the day on which the clubs choose the players they sign in the winter
-- window (the game: 1 September, the day after the summer window closes). On that day a
-- club buys for a position only as often as `winter` of its persona says. 1 to 12, or 0:
-- winter is like summer.
local WINTER_MONTH = 9

-- A club that counts fewer players than this is in need: it buys for every position, in
-- winter too, at any age and below its usual level, so that no squad runs empty. It
-- still looks in the places of its persona. (A slot of a top club that asks for a key
-- player looks everywhere.) 0 to 32. The game itself aims at 23 to 25 players; 26 is
-- one player above that, so a club that has not been buying looks for everybody.
local SQUAD_NEED = 26

-- Position need. In the game a club looks for a player when a place of its eleven has
-- nobody, or when it counts fewer than 25 players, and then its list of weak positions
-- leaves the goalkeeper out. An eleven rated 85 with a goalkeeper rated 75 looks for
-- nobody. With NEED on, a club also looks for a player for the weakest place of its
-- eleven, the goalkeeper included, when the player there stands NEED_GAP rating points or
-- more below the mean of the other ten. For that position it takes only a player rated
-- NEED_BETTER points or more above the one it has, inside the rating range of its group.
-- Everything else still counts: the price, the persona, the selling club. One such
-- position per club each time the clubs plan. A club with 32 players signs nobody, as in
-- the game; it has to lose a player first. false: as in the game.
local NEED = true
-- 1 to 30. A lower number makes more clubs look: counted on the best eleven of each of
-- the 498 computer clubs of one career, 3 gives about 180 clubs, 4 about 70, 5 about 40,
-- 6 about 20. With 4, six in ten of them look for a goalkeeper.
local NEED_GAP = 4
-- 1 to 20.
local NEED_BETTER = 1

-- Sporting projects / rebuilds (SPORTING_PROJECTS).
-- Independent sporting projects / rebuilds for top European AI clubs (like PSG / Man City),
-- preserving their existing personas. Five distinct qualifying clubs are chosen per Master
-- League career from the global top 15 clubs that belong to the top five first-division
-- leagues (England 17, Italy 18, Spain 19, France 20, Germany 50). The selection is drawn
-- once per career and remains strictly identical across save reloads, without mutating
-- personas, corrupting save files, or consuming match RNG.
-- For their priority squad need positions (their weakest positions), project clubs receive
-- rebuild recruitment assistance (up to 20% recruitment ceiling expansion), allowing them
-- to sign high-caliber targets for their squad gaps while preserving scouting, age bands,
-- rivalries, and seller protection.
-- false: off.
local SPORTING_PROJECTS = true
local PROJECT_COUNT = 5          -- number of project clubs per career (5)
local PROJECT_CEILING_BOOST = 20 -- up to 20% additional recruitment ceiling for priority need positions
local PROJECT_RANK_MAX = 15      -- global rank 1 to 15
local TOP_FIVE_LEAGUES = { 17, 18, 19, 20, 50 } -- Premier League, Serie A, La Liga, Ligue 1, Bundesliga

-- The personas. Each has a name and these numbers:
--   free, listed, clubs   where it looks first, in percent of the positions it buys for:
--                         players without a contract / players another club has listed
--                         / other players of other clubs. What is left to 100 is "does
--                         not buy for this position this time" (the stand-in for a club
--                         that fills the place from its own academy).
--   second                the second search (when the first found nobody): the first of
--                         these two places that the first search did not look in.
--   winter                percent of the positions it still buys for in the winter window
--   age, strict           the ages it wants (first, last), and how many percent of the
--                         players outside them it refuses (of players without a contract:
--                         STRICT_FREE percent of that)
--   knows                 percent of the players it knows (SCOUTING)
--   fog                   how far its judgement of a rating is off: up to this many
--                         points too low or too high, fixed by club and player. 0 to 10
--   wealth                its ceiling in percent of the CEILING of its group. 10 to 250
--   premium               its CEILING_STRETCH in percent of that setting. 0 to 250
--   panic                 its CEILING_NEED in percent of that setting. 0 to 250
--   fame                  percent by which its limit rises for 1,000 points of a player's
--                         popularity: what a famous name is worth to it. 0 to 250
--   ambition              how many rating points below its first eleven a player may be
--   prestige              how many rating points above its first eleven a player may be
--                         and still join (he, too, has a say; players without a contract
--                         included)
--   keeps                 percent of its own players, not listed, that it never lets go
--   rating                whether the rating limit of `CEILING_RATING` applies to it: not
--                         given (or true), it does; false, in its second search the club
--                         may take a player rated above the top of its own rating range
--                         (Galactico and Retirement team, who pay for the best and the
--                         famous whatever their club's level: set it that way below)
-- At most 15 personas. Numbers without a range given: 0 to 100 (knows: 1 to 100; ambition
-- and prestige: 0 to 99; ages 0 to 63).
local ARCHETYPES = {
    { "Galactico", free = 5, listed = 10, clubs = 85, second = { "clubs", "free" }, winter = 45,
      age = { 21, 31 }, strict = 70, knows = 85, fog = 2, wealth = 150, premium = 150, panic = 100, fame = 40,
      ambition = 7, prestige = 12, keeps = 30, rating = false },
    { "State-backed", free = 25, listed = 15, clubs = 60, second = { "clubs", "listed" }, winter = 50,
      age = { 21, 30 }, strict = 70, knows = 85, fog = 1, wealth = 160, premium = 150, panic = 150, fame = 25,
      ambition = 7, prestige = 10, keeps = 20 },
    { "Moneyball", free = 15, listed = 25, clubs = 60, second = { "clubs", "listed" }, winter = 35,
      age = { 19, 29 }, strict = 75, knows = 90, fog = 0, wealth = 90, premium = 40, panic = 50, fame = 0,
      ambition = 8, prestige = 6, keeps = 15 },
    { "Elite trader", free = 15, listed = 20, clubs = 55, second = { "clubs", "listed" }, winter = 35,
      age = { 18, 25 }, strict = 45, knows = 85, fog = 1, wealth = 100, premium = 60, panic = 60, fame = 0,
      ambition = 9, prestige = 6, keeps = 15 },
    { "Academy purist", free = 15, listed = 15, clubs = 40, second = { "clubs", "free" }, winter = 25,
      age = { 17, 25 }, strict = 40, knows = 60, fog = 1, wealth = 70, premium = 50, panic = 50, fame = 0,
      ambition = 12, prestige = 4, keeps = 25 },
    { "Old-money", free = 30, listed = 20, clubs = 50, second = { "clubs", "free" }, winter = 50,
      age = { 23, 32 }, strict = 50, knows = 75, fog = 2, wealth = 110, premium = 100, panic = 120, fame = 30,
      ambition = 7, prestige = 8, keeps = 20 },
    { "Mid-table", free = 25, listed = 30, clubs = 40, second = { "listed", "clubs" }, winter = 50,
      age = { 23, 30 }, strict = 40, knows = 70, fog = 0, wealth = 100, premium = 100, panic = 100, fame = 5,
      ambition = 8, prestige = 4, keeps = 15 },
    { "Survival churner", free = 40, listed = 35, clubs = 25, second = { "free", "listed" }, winter = 80,
      age = { 27, 36 }, strict = 40, knows = 60, fog = 3, wealth = 90, premium = 80, panic = 200, fame = 5,
      ambition = 9, prestige = 4, keeps = 15 },
    { "Crisis", free = 60, listed = 30, clubs = 10, second = { "free", "listed" }, winter = 70,
      age = { 17, 38 }, strict = 20, knows = 50, fog = 3, wealth = 50, premium = 30, panic = 100, fame = 0,
      ambition = 12, prestige = 2, keeps = 10 },
    { "New-money", free = 35, listed = 10, clubs = 55, second = { "clubs", "free" }, winter = 60,
      age = { 24, 31 }, strict = 60, knows = 65, fog = 1, wealth = 250, premium = 200, panic = 150, fame = 30,
      ambition = 7, prestige = 8, keeps = 40 },
    { "Selling farm", free = 20, listed = 25, clubs = 40, second = { "listed", "free" }, winter = 40,
      age = { 17, 26 }, strict = 60, knows = 70, fog = 2, wealth = 60, premium = 40, panic = 50, fame = 0,
      ambition = 12, prestige = 4, keeps = 5 },
    { "Youth elite", free = 10, listed = 15, clubs = 65, second = { "clubs", "listed" }, winter = 30,
      age = { 18, 25 }, strict = 45, knows = 85, fog = 1, wealth = 140, premium = 120, panic = 80, fame = 15,
      ambition = 8, prestige = 8, keeps = 30 },
    { "Retirement team", free = 0, listed = 30, clubs = 65, second = { "listed", "clubs" }, winter = 70,
      age = { 32, 40 }, strict = 95, knows = 80, fog = 0, wealth = 250, premium = 250, panic = 150, fame = 250,
      ambition = 4, prestige = 22, keeps = 5, rating = false },
}

-- The personas a club without an entry in CLUBS draws from, by its place in the game's
-- club ranking (the ten groups of CEILING). 1 to 8 names per group; a name written twice
-- is drawn twice as often, and with fewer than 8 names the list is read again from its
-- start until 8 are filled. Which one a club draws is fixed by the club.
local PERSONA_GROUPS = {
    { "Galactico", "Old-money", "State-backed", "Elite trader" },                                       -- 1-10
    { "Old-money", "Elite trader", "Moneyball", "Youth elite", "Old-money", "Academy purist" },         -- 11-20
    { "Mid-table", "Moneyball", "Elite trader", "Old-money", "Elite trader", "Academy purist",
      "Mid-table", "Selling farm" },                                                                    -- 21-50
    { "Mid-table", "Mid-table", "Moneyball", "Academy purist", "Selling farm", "Survival churner",
      "Old-money", "New-money" },                                                                       -- 51-80
    { "Mid-table", "Mid-table", "Survival churner", "Selling farm", "Academy purist", "Moneyball",
      "Mid-table", "Survival churner" },                                                                -- 81-120
    { "Mid-table", "Survival churner", "Survival churner", "Selling farm", "Academy purist", "Crisis",
      "Mid-table", "Moneyball" },                                                                       -- 121-170
    { "Mid-table", "Survival churner", "Selling farm", "Academy purist", "Mid-table", "Survival churner",
      "Moneyball", "Survival churner" },                                                                -- 171-220
    { "Survival churner", "Mid-table", "Selling farm", "Academy purist", "Crisis", "Survival churner",
      "Mid-table", "Mid-table" },                                                                       -- 221-260
    { "Survival churner", "Mid-table", "Selling farm", "Academy purist", "Mid-table", "Survival churner",
      "Survival churner", "Selling farm" },                                                             -- 261-300
    { "Survival churner", "Mid-table", "Selling farm", "Academy purist", "Crisis", "Survival churner",
      "Survival churner", "Mid-table" },                                                                -- others
}

-- The clubs with a persona of their own: the game's id of the club, the persona. At most
-- 192. The ids are those of the career the module was set against (the name behind each is
-- what that career calls the club); a club your data does not have is simply never found.
-- If an id stands twice, the last entry counts. { } : no club is named.
-- How each was chosen: from what the real club does on the market (README.md).
-- First the biggest clubs, then the rest of the five big leagues (as they stand in
-- 2025/26, which is what the data looks like), then other clubs. For a small or newly
-- promoted club the choice is a weak one: change any line you see differently.
local CLUBS = {
    { 0x001c804a, "State-backed" },      -- Paris Saint-Germain
    { 0x001b4036, "Galactico" },         -- Real Madrid CF
    { 0x001b002b, "Old-money" },         -- FC Barcelona
    { 0x00194000, "Galactico" },         -- Arsenal FC
    { 0x001fc074, "Old-money" },         -- FC Bayern München
    { 0x002b400c, "State-backed" },      -- Manchester City FC
    { 0x0019c00b, "Moneyball" },         -- Liverpool FC
    { 0x002b002a, "Old-money" },         -- Club Atlético de Madrid
    { 0x001dc01c, "Old-money" },         -- Internazionale Milano
    { 0x0019000d, "Crisis" },             -- Manchester United
    { 0x00198006, "New-money" },         -- Chelsea FC
    { 0x002cc011, "Moneyball" },         -- Tottenham Hotspur FC
    { 0x0051c021, "Old-money" },         -- SSC Napoli
    { 0x001f8075, "Elite trader" },      -- Borussia Dortmund
    { 0x001e001d, "Old-money" },         -- Juventus FC
    { 0x001f4024, "Old-money" },         -- AS Roma
    { 0x001e4020, "Moneyball" },         -- AC Milan
    { 0x001ac001, "New-money" },         -- Aston Villa FC
    { 0x00408029, "Academy purist" },    -- Athletic Club de Bilbao (the game makes no plan for the club you play)
    { 0x0020817f, "Retirement team" },   -- Galatasaray SK
    { 0x001a800e, "New-money" },         -- Newcastle United FC
    { 0x0031417e, "Old-money" },         -- Fenerbahçe SK
    { 0x00308035, "Old-money" },         -- Real Betis Balompié
    { 0x005e4004, "Moneyball" },         -- Brighton & Hove Albion FC
    { 0x00200073, "Elite trader" },      -- Bayer 04 Leverkusen
    { 0x003a8014, "Elite trader" },      -- Atalanta BC
    { 0x03f9c002, "Moneyball" },         -- AFC Bournemouth
    { 0x0030006c, "Elite trader" },      -- FC Porto
    { 0x002fc063, "Elite trader" },      -- SL Benfica
    { 0x00630010, "Moneyball" },         -- Sunderland AFC
    { 0x04e4807e, "Elite trader" },      -- RB Leipzig
    { 0x04150003, "Moneyball" },         -- Brentford FC
    { 0x0138008c, "Old-money" },         -- CR Flamengo
    { 0x041ec017, "New-money" },         -- Como 1907
    { 0x00310038, "Academy purist" },    -- Real Sociedad de Fútbol
    { 0x017441c3, "Retirement team" },   -- Al Hilal SFC
    { 0x001d004e, "Selling farm" },      -- Ajax
    { 0x001c0046, "Elite trader" },      -- AS Monaco
    { 0x001d805a, "Elite trader" },      -- PSV
    { 0x0039c07f, "Moneyball" },         -- VfB Stuttgart
    { 0x005c8034, "Survival churner" },  -- Rayo Vallecano de Madrid
    { 0x0030406f, "Selling farm" },      -- Sporting CP
    { 0x0030c02c, "Academy purist" },    -- RC Celta de Vigo
    { 0x001b803a, "Crisis" },            -- Valencia CF
    { 0x0041c033, "Academy purist" },    -- CA Osasuna
    { 0x002d4043, "Crisis" },            -- Olympique Lyonnais
    { 0x0044417a, "Old-money" },         -- Beşiktaş JK
    { 0x0036804b, "Elite trader" },      -- Stade Rennais FC
    { 0x002d8040, "Moneyball" },         -- RC Lens
    { 0x028441d3, "Retirement team" },   -- Al Nassr FC
    { 0x002280ae, "Old-money" },         -- CA River Plate
    { 0x0022c09e, "Old-money" },         -- CA Boca Juniors
    { 0x005a802f, "Survival churner" },  -- Getafe CF
    { 0x00354041, "Elite trader" },      -- LOSC Lille
    { 0x00224091, "Elite trader" },      -- SE Palmeiras
    { 0x00388077, "Elite trader" },      -- Eintracht Frankfurt
    { 0x0038c079, "Academy purist" },    -- SC Freiburg
    { 0x001c4044, "Old-money" },         -- Olympique de Marseille
    { 0x00424039, "Crisis" },            -- Sevilla FC
    { 0x001d4051, "Selling farm" },      -- Feyenoord
    { 0x01ed8064, "Selling farm" },      -- Sporting Braga
    { 0x0020c161, "Elite trader" },      -- Celtic FC
    { 0x0222c10d, "Moneyball" },         -- Girona FC
    { 0x059a80cc, "Retirement team" },   -- Inter Miami CF
    { 0x015141ca, "New-money" },         -- Al Ahli Saudi FC
    { 0x00434148, "Elite trader" },      -- Club Brugge KV
    { 0x015181cf, "Retirement team" },   -- Al Ittihad Club
    { 0x002b8144, "Selling farm" },      -- RSC Anderlecht
    { 0x003c804f, "Selling farm" },      -- AZ
    { 0x012cc191, "Selling farm" },      -- GNK Dinamo Zagreb
    { 0x012ac14a, "Selling farm" },      -- KRC Genk
    { 0x018c8193, "Selling farm" },      -- FC Salzburg
    { 0x012e0159, "Selling farm" },      -- FC Nordsjælland
    -- England, Premier League
    { 0x0061400f, "New-money" },         -- Nottingham Forest FC
    { 0x005f8007, "Moneyball" },         -- Crystal Palace FC
    { 0x002c4008, "Mid-table" },         -- Everton FC
    { 0x001a000a, "Mid-table" },         -- Leeds United FC
    { 0x002c8009, "Mid-table" },         -- Fulham FC
    { 0x001a40f2, "Old-money" },         -- West Ham United FC
    { 0x003400f3, "Elite trader" },      -- Wolverhampton Wanderers FC
    { 0x005e80f0, "Survival churner" },  -- Burnley FC
    -- Spain, La Liga
    { 0x0042c03b, "Moneyball" },         -- Villarreal CF
    { 0x0040c02e, "Survival churner" },  -- RCD Espanyol
    { 0x040c4028, "Survival churner" },  -- Deportivo Alavés
    { 0x005b8031, "Survival churner" },  -- Levante UD
    { 0x00414115, "Mid-table" },         -- RCD Mallorca
    { 0x005a402d, "Survival churner" },  -- Elche CF
    { 0x04290113, "Survival churner" },  -- Real Oviedo
    -- Italy, Serie A
    { 0x001e801e, "Mid-table" },         -- S.S. Lazio
    { 0x002e8015, "Moneyball" },         -- Bologna FC 1909
    { 0x001f0019, "Old-money" },         -- ACF Fiorentina
    { 0x00534026, "Mid-table" },         -- Torino FC
    { 0x01dfc025, "Elite trader" },      -- US Sassuolo Calcio
    { 0x002f8027, "Elite trader" },      -- Udinese Calcio
    { 0x0050c01a, "Elite trader" },      -- Genoa CFC
    { 0x00500016, "Survival churner" },  -- Cagliari Calcio
    { 0x001ec022, "Elite trader" },      -- Parma Calcio 1913
    { 0x0423401f, "Moneyball" },         -- US Lecce
    { 0x00540136, "Elite trader" },      -- Hellas Verona FC
    { 0x041f0018, "Survival churner" },  -- US Cremonese
    { 0x0424413a, "Survival churner" },  -- Pisa Sporting Club
    -- Germany, Bundesliga
    { 0x04078080, "Elite trader" },      -- TSG 1899 Hoffenheim
    { 0x006d007d, "Moneyball" },         -- 1. FSV Mainz 05
    { 0x04070072, "Mid-table" },         -- FC Augsburg
    { 0x00384076, "Mid-table" },         -- VfL Borussia M’gladbach
    { 0x040b0081, "Survival churner" },  -- 1. FC Union Berlin
    { 0x0020407a, "Mid-table" },         -- Hamburger SV
    { 0x040a407c, "Mid-table" },         -- 1. FC Köln
    { 0x002e4082, "Mid-table" },         -- SV Werder Bremen
    { 0x003a0083, "Elite trader" },      -- VfL Wolfsburg
    { 0x040ac078, "Mid-table" },         -- FC St. Pauli
    { 0x04e4407b, "Moneyball" },         -- 1. FC Heidenheim
    -- France, Ligue 1
    { 0x00364048, "Mid-table" },         -- OGC Nice
    { 0x041cc049, "New-money" },         -- Paris FC
    { 0x041d404c, "Elite trader" },      -- RC Strasbourg Alsace
    { 0x014c403e, "Survival churner" },  -- Stade Brestois 29
    { 0x0037404d, "Moneyball" },         -- Toulouse FC
    { 0x002d003d, "Academy purist" },    -- AJ Auxerre
    { 0x0064c03c, "Survival churner" },  -- Angers SCO
    { 0x00678042, "Selling farm" },      -- FC Lorient
    { 0x0067403f, "Academy purist" },    -- Havre AC
    { 0x00360123, "Crisis" },            -- FC Nantes
    { 0x0406c12b, "Selling farm" },      -- FC Metz
    -- clubs of the second divisions that were in those leagues lately, or are big
    { 0x00608013, "Mid-table" },         -- Ipswich Town FC
    { 0x0033c0fe, "Elite trader" },      -- Southampton FC
    { 0x003300f4, "Crisis" },            -- Leicester City FC
    { 0x042c0112, "Survival churner" },  -- CD Leganés
    { 0x005b0111, "Academy purist" },    -- UD Las Palmas
    { 0x00428118, "Survival churner" },  -- Real Valladolid CF
    { 0x001bc030, "Mid-table" },         -- Deportivo La Coruña
    { 0x00594105, "New-money" },         -- UD Almería
    { 0x00410037, "Academy purist" },    -- Málaga CF
    { 0x005ac117, "Academy purist" },    -- Real Sporting de Gijón
    { 0x04214142, "Selling farm" },      -- Venezia FC
    { 0x04cc8023, "Crisis" },            -- AC Monza
    { 0x003ac135, "Selling farm" },      -- Empoli FC
    { 0x003c013f, "Crisis" },            -- UC Sampdoria
    { 0x003b813c, "Mid-table" },         -- Palermo FC
    { 0x014c8128, "Elite trader" },      -- Stade de Reims
    { 0x0068812a, "Moneyball" },         -- AS Saint-Étienne
    { 0x0035c124, "Crisis" },            -- Montpellier Hérault SC
    { 0x05ed4103, "New-money" },         -- Wrexham AFC
    { 0x003240ec, "New-money" },         -- Birmingham City FC
    { 0x00638101, "Elite trader" },      -- Watford FC
    { 0x006280fd, "Crisis" },            -- Sheffield Wednesday FC
    -- other clubs with a known way of buying
    { 0x0021418c, "Old-money" },         -- Olympiacos FC
    { 0x01e64189, "Old-money" },         -- Trabzonspor
    { 0x0021016a, "Old-money" },         -- Rangers FC
    { 0x0511418f, "Elite trader" },      -- SK Slavia Praha
    { 0x05190151, "Moneyball" },         -- R. Union Saint-Gilloise
    { 0x02054158, "Moneyball" },         -- FC Midtjylland
    { 0x0521418a, "Moneyball" },         -- FK Bodø/Glimt
    { 0x012dc157, "Old-money" },         -- F.C. København
    { 0x01e78176, "Elite trader" },      -- BSC Young Boys
    { 0x0131c190, "Elite trader" },      -- FK Crvena zvezda
    { 0x01aa816c, "Selling farm" },      -- FC Basel 1893
    { 0x02084194, "Elite trader" },      -- SK Sturm Graz
    { 0x01ca0155, "Selling farm" },      -- Brøndby IF
    { 0x0138408d, "Retirement team" },   -- Fluminense FC
    { 0x00220096, "Retirement team" },   -- CR Vasco da Gama
    { 0x0139c095, "Crisis" },            -- São Paulo F.C.
    { 0x01398094, "Selling farm" },      -- Santos FC
    { 0x0044808b, "New-money" },         -- Cruzeiro EC
    { 0x01374085, "Old-money" },         -- Atlético Mineiro
    { 0x01378087, "Elite trader" },      -- Botafogo FR
    { 0x0137c089, "Crisis" },            -- SC Corinthians Paulista
    { 0x02654086, "New-money" },         -- EC Bahia
    { 0x0266c092, "Elite trader" },      -- Red Bull Bragantino
    { 0x01e28084, "Elite trader" },      -- Athletico Paranaense
    { 0x013540ad, "Old-money" },         -- Racing Club Avellaneda
    { 0x013600a7, "Crisis" },            -- CA Independiente
    { 0x013700b5, "Selling farm" },      -- CA Vélez Sarsfield
    { 0x01e240aa, "Selling farm" },      -- CA Lanús
    { 0x01350099, "Selling farm" },      -- Argentinos Juniors
    { 0x04ed80b2, "Elite trader" },      -- CA Talleres de Córdoba
    { 0x059b40ce, "Retirement team" },   -- Los Angeles FC
    { 0x040ec0cd, "Retirement team" },   -- Los Angeles Galaxy
    { 0x041141b3, "Retirement team" },   -- Toronto FC
    { 0x040d00c8, "Retirement team" },   -- Chicago Fire FC
    { 0x059a01aa, "New-money" },         -- Atlanta United FC
    { 0x040fc0d4, "Selling farm" },      -- Philadelphia Union
    { 0x040f80d2, "Elite trader" },      -- New York Red Bulls
    { 0x041341ce, "Retirement team" },   -- Al Sadd SC
}

-- Rivals do not trade: the two clubs of a pair never take each other's player onto a
-- list, as long as he has a contract (a player on his club's list too). A player whose
-- contract has run out goes where he likes, to the rival as well. It works by itself,
-- whatever the switches above say. Each line is one pair of club ids, the same ids as in
-- CLUBS (club_ids.tsv next to this file lists all of them); for three clubs that are all
-- rivals write three pairs. At most 64 pairs. { } : no rivals.
-- The pairs are my choice of well-known rivalries: delete or add as you see them. The
-- club you play is in it like any other (if the game lets a computer club go for your
-- players, a rival will not). What you yourself buy is never touched by this module.
local RIVALS = {
    -- England
    { 0x0019000d, 0x0019c00b },  -- Manchester United, Liverpool FC
    { 0x0019000d, 0x002b400c },  -- Manchester United, Manchester City FC
    { 0x0019000d, 0x001a000a },  -- Manchester United, Leeds United FC
    { 0x00194000, 0x002cc011 },  -- Arsenal FC, Tottenham Hotspur FC
    { 0x0019c00b, 0x002c4008 },  -- Liverpool FC, Everton FC
    { 0x001a800e, 0x00630010 },  -- Newcastle United FC, Sunderland AFC
    { 0x001ac001, 0x003240ec },  -- Aston Villa FC, Birmingham City FC
    { 0x005f8007, 0x005e4004 },  -- Crystal Palace FC, Brighton & Hove Albion FC
    { 0x001a40f2, 0x0060c0f6 },  -- West Ham United FC, Millwall FC
    { 0x0061400f, 0x005fc0f1 },  -- Nottingham Forest FC, Derby County FC
    { 0x0033c0fe, 0x044340f9 },  -- Southampton FC, Portsmouth FC
    { 0x041880fc, 0x006280fd },  -- Sheffield United FC, Sheffield Wednesday FC
    { 0x00608013, 0x006100f7 },  -- Ipswich Town FC, Norwich City FC
    -- Spain
    { 0x001b4036, 0x001b002b },  -- Real Madrid CF, FC Barcelona
    { 0x001b4036, 0x002b002a },  -- Real Madrid CF, Club Atlético de Madrid
    { 0x001b002b, 0x0040c02e },  -- FC Barcelona, RCD Espanyol
    { 0x00424039, 0x00308035 },  -- Sevilla FC, Real Betis Balompié
    { 0x00408029, 0x00310038 },  -- Athletic Club de Bilbao, Real Sociedad de Fútbol
    { 0x001b803a, 0x005b8031 },  -- Valencia CF, Levante UD
    { 0x0030c02c, 0x001bc030 },  -- RC Celta de Vigo, Deportivo La Coruña
    { 0x04290113, 0x005ac117 },  -- Real Oviedo, Real Sporting de Gijón
    -- Italy
    { 0x001dc01c, 0x001e4020 },  -- Internazionale Milano, AC Milan
    { 0x001dc01c, 0x001e001d },  -- Internazionale Milano, Juventus FC
    { 0x001f4024, 0x001e801e },  -- AS Roma, S.S. Lazio
    { 0x001e001d, 0x00534026 },  -- Juventus FC, Torino FC
    { 0x0050c01a, 0x003c013f },  -- Genoa CFC, UC Sampdoria
    -- Germany
    { 0x0020407a, 0x002e4082 },  -- Hamburger SV, SV Werder Bremen
    { 0x0020407a, 0x040ac078 },  -- Hamburger SV, FC St. Pauli
    { 0x040a407c, 0x00384076 },  -- 1. FC Köln, VfL Borussia M’gladbach
    { 0x040a407c, 0x00200073 },  -- 1. FC Köln, Bayer 04 Leverkusen
    -- France
    { 0x001c804a, 0x001c4044 },  -- Paris Saint-Germain, Olympique de Marseille
    { 0x002d4043, 0x0068812a },  -- Olympique Lyonnais, AS Saint-Étienne
    { 0x002d8040, 0x00354041 },  -- RC Lens, LOSC Lille
    { 0x00360123, 0x0036804b },  -- FC Nantes, Stade Rennais FC
    -- Portugal
    { 0x002fc063, 0x0030006c },  -- SL Benfica, FC Porto
    { 0x002fc063, 0x0030406f },  -- SL Benfica, Sporting CP
    { 0x0030006c, 0x0030406f },  -- FC Porto, Sporting CP
    -- Netherlands
    { 0x001d004e, 0x001d4051 },  -- Ajax, Feyenoord
    { 0x001d004e, 0x001d805a },  -- Ajax, PSV
    -- Scotland
    { 0x0020c161, 0x0021016a },  -- Celtic FC, Rangers FC
    -- Turkey
    { 0x0020817f, 0x0031417e },  -- Galatasaray SK, Fenerbahçe SK
    { 0x0020817f, 0x0044417a },  -- Galatasaray SK, Beşiktaş JK
    { 0x0031417e, 0x0044417a },  -- Fenerbahçe SK, Beşiktaş JK
    { 0x0031417e, 0x01e64189 },  -- Fenerbahçe SK, Trabzonspor
    -- Belgium
    { 0x002b8144, 0x00434148 },  -- RSC Anderlecht, Club Brugge KV
    { 0x002b8144, 0x012b4150 },  -- RSC Anderlecht, Royal Standard de Liège
    -- Denmark
    { 0x012dc157, 0x01ca0155 },  -- F.C. København, Brøndby IF
    -- Argentina
    { 0x0022c09e, 0x002280ae },  -- CA Boca Juniors, CA River Plate
    { 0x013540ad, 0x013600a7 },  -- Racing Club Avellaneda, CA Independiente
    { 0x013680af, 0x013640ab },  -- CA Rosario Central, CA Newell's Old Boys
    { 0x013580a2, 0x0135c0a4 },  -- Club Estudiantes LP, Gimnasia y Esgrima LP
    { 0x0136c0b0, 0x01e080a6 },  -- CA San Lorenzo Almagro, CA Huracán
    -- Brazil
    { 0x0138008c, 0x0138408d },  -- CR Flamengo, Fluminense FC
    { 0x0138008c, 0x00220096 },  -- CR Flamengo, CR Vasco da Gama
    { 0x0137c089, 0x00224091 },  -- SC Corinthians Paulista, SE Palmeiras
    { 0x0138808e, 0x0139008f },  -- Grêmio FBPA, SC Internacional
    { 0x01374085, 0x0044808b },  -- Atlético Mineiro, Cruzeiro EC
    { 0x02654086, 0x01e44097 },  -- EC Bahia, EC Vitória
    -- Saudi Arabia
    { 0x017441c3, 0x028441d3 },  -- Al Hilal SFC, Al Nassr FC
    { 0x015181cf, 0x015141ca },  -- Al Ittihad Club, Al Ahli Saudi FC
    -- United States
    { 0x040ec0cd, 0x059b40ce },  -- Los Angeles Galaxy, Los Angeles FC
}

-- Offers for your own players. The game decides which club makes an offer for a player of
-- yours by a slot of the competition in hand: a club look-up answers the club that sits at
-- that slot, and the routine that creates the offer asks it. The module answers that look-up
-- itself, with the club whose slot is nearest to the game's own among those that would
-- really take him, by the same rules the computer clubs choose their players by, narrowed
-- to what a club that is not choosing a player for its own plan can be asked:
--   * not a rival of yours (RIVALS), and not the club the game itself skips;
--   * its character wants him (PERSONA): he is in its age band, he is not too good for it
--     (prestige) nor too poor for it (ambition, as it judges him), and for a player
--     without a contract only a part of `strict` counts (STRICT_FREE);
--   * it knows him (SCOUTING): a listed player, one rated KNOWN_FROM or more and a famous
--     one are known to every club, every other one only to `knows` percent of them;
--   * it is looking where he is: for this position and this time its character looks
--     either among the players without a contract, the listed players or those of other
--     clubs (free, listed, clubs), and it takes him only from the place it looks in;
--   * it buys for his position at all (NEED): a free place of its plan asks for that
--     position, or the position need marked it. A marked position is a club in want of
--     him: it does not mind his age or the rating it makes of him, and it goes further
--     for him (panic);
--   * it can afford him (CEILING): his value after the discount for a player without a
--     contract or one on the list does not exceed the ceiling of its level, raised by its
--     wealth, by a part of its stretch (CEILING_STRETCH, premium), by its fame and by its
--     panic when it is in want of him. Above the ceiling it takes him less and less often,
--     as in the transfers between the computer clubs, and never past the stretch.
-- Every draw of these rules has the day of the career in it, so that the club that bids is
-- not the same club on every day of the window.
-- A club with a full squad is answered too: the room test of the routine that creates the
-- offer is the game's own and decides whether the offer is made.
-- An offer that was already sensible is left alone, and when no club passes, the game's own
-- answer stands: nothing is added.
-- false: as in the game.
local INCOMING = true

-- ========================= end of settings ===========================

local CAVE = 0x047d4200         -- unused end of a page of the game's code: the tables and the routine
local CAVE_SIZE = 0xe00
-- a second piece of unused memory, for NEED: its two numbers (NEED_GAP, NEED_BETTER - 1)
-- and its two routines
local NEED_CAVE = 0x047d6400
local NEED_CAVE_SIZE = 0x150
-- a fourth piece, in the same unused page right after that one (MLSimToDate.lua's day-loop
-- hook starts at 0x047d6f60; its calendar block moved to .trace at 0x03fc8000 in version 4):
-- the chooser of the club that makes an offer for one of your players
local INCOMING_CAVE = 0x047d6550
local INCOMING_CAVE_SIZE = 0x7f0
local INCOMING_ROUTINE = "9c608b44242c3d660a1002752f8b44241885c074270fb60d660a10028b542408515250e8ea05000083c40c85c0740d8b"
      .. "542428890289d0619dc20c00619d5589e583ec14e9587d04ff55535783ec2089e58b5d308b4534e8e4a6fdff89f883c4"
      .. "205f5b5dc356578b44240c8b4c2410c7010d0000006a025150e874d507ff83c40c0fb6c05f5ec38b4424048b5424088b"
      .. "4c240c5250e84bc204ffc35589e583ec1c8945ec8955e8894de48b45ecf765e83b55e47305f775e4eb05b8ffffffff89"
      .. "45fc8b45fcc9c35589e5575689c65381ec8c0000008b028b155cf85102894d94b940000000894590a1c8477d0439c80f"
      .. "47c18d3cc5cc477d04b8cc477d0439c70f844f0100008b188b4804395d90750839ca0f843601000083c00839da75df39"
      .. "4d9075dae92501000083ff020f85240400000fb61139d0b8010000000f45d88b4dac694580656b54e68bb57cffffff8d"
      .. "1409c1e8184281c680501f010fafd08b458429c8c1ea0801c283ff020f845e0400008b45c08b4d8c01d039c80f834e04"
      .. "00008b0cb500000000b802000000bb01000000410f847004000050508b459452ff30e8a2feffff83c4108945908b4594"
      .. "8b401c83f8020f85240400008b04b5000000008b55b0b964000000e8cbfeffff89c683ff0275198b55b8a138427d04e8"
      .. "b7feffff8d506489f0e8adfeffff89c6a134427d048b55b4b964000000e899feffff6955806bcaeb85b900640000c1ea"
      .. "180fafd089f0e880feffffb9a086010001c6b8ffffffff0f42f08b45948b50180faf55bc89f0e860feffff01c60f82c4"
      .. "0300008b459039c60f83b903000031c0e9b50300008b96a0280000b88a0200008d9ecc84cc0039c20f46c231c9894588"
      .. "89d8394d8874128d50108b3889558c397d9074074189d0ebe989d80fb778080fb6400ebac000000089857cffffffa160"
      .. "427d0439d00f47c289c283e80172158b0c85c8447d04394d9075ed0fb68207447d04eb26b80900000039857cffffff0f"
      .. "46857cffffff695590b179379ec1ea1d8d84c278427d040fb6006bc01431db05c8427d04894588694590b179379e8945"
      .. "80a144427d048b0d48427d0469d39301000189458c8b458801d88a008845848b458031c28b458c69d26bcaeb85c1ea18"
      .. "0fafd1b9e8030000c1ea0801c20fb64584e855fdffff89449d984383fb1475b18b0d4c427d04b80900000039857cffff"
      .. "ff0f46857cffffff8b1550427d040faff901d70fb69064427d04c1ef10897d8c39d7730a0fb6b864427d04897d8c0fb6"
      .. "906e427d048b7d8c39fa730a0fb6806e427d0489458c8b45948b40088945848b7d848b458c0345c439f80f828efeffff"
      .. "0fb796b2cbc2008b7d94b953030000668b86b0cbc2008b5f04c1e01009d08b5580899d74ffffff69c09301000131da31"
      .. "d08b963464d0008945808b459439ca0f47d18b400c69d218010000898578ffffff8d860cb8cc0001c239c274778b188d"
      .. "8818010000395d90740489c8ebeb85c074628d50108d9810010000be810000008b0af7c100c03f00741c89cfc1ef0783"
      .. "e77f39bd78ffffff750cc1e91689f7d3ef83e701754183c21039d375d38bb578ffffff0fb690090100008d4e0139ca75"
      .. "130fb6800a0100008b7584bf0200000039f072138b5d8c8b45840345c039d80f93c00fb6c089c78b459431db8b401c83"
      .. "f80174348b15f84f7d0439558473298b15e44f7d048b7594c1ea143956187318695580b167561631dbc1ea186bd264c1"
      .. "ea083b55a80f93c38b75888a56108d4e10fec27453699578ffffff35aeb2c28bb574ffffff31f28b758031f28b759869"
      .. "d26bcaeb85c1ea186bd264c1ea0839f2730485c0eb1a03759c39f2730583f801eb0e0375a039f20f83ecfbffff83f802"
      .. "ba010000000f45da85ff740a83ff02750ae9e9fbffffbb010000008b75948b15fc4f7d048b0dfc4f7d04034e14697590"
      .. "41a11ddf01d242c1ee180fafd68b7588c1ea0829d10fb6560e39d1720c0fb6560f39ca0f83a6fbffff8b55ccb9640000"
      .. "0085c075068b0de84f7d046945809335871b0fafd1c1e8186bc064c1e8086bc06439d0b8010000000f42d8e96ffbffff"
      .. "8b04b500000000400f85bcfbffffeb2785c075088b153c427d04eb068b1540427d048b4590b964000000e89cfaffff89"
      .. "4590e9b5fbffff8d43018d65f45b5e5f5dc35589e557565383ec4c837d0800750731f6e9b7010000a15cf851028945c4"
      .. "4883f8fd77eb8b450c8b780885ff74e18b378b5f0450ff75085356e837faffff83c4108d50ff8945c883fafd77c3668b"
      .. "482c0fb7d66639f175b769db9301000131d3895dcc8b5004c1ea1c8955d48d55d851515250e8dbf9ffff8b55c883c410"
      .. "31c98945d08b421cc1e80783e03f8945dc8b82b4000000c1e80b25ff0f00008945e08b82b400000083e00f4883f80176"
      .. "128b82b80000002500000060f7d819c983c1028b4508894de48bb0e0ec5f008d46ff3dff0300000f8734ffffff8b4508"
      .. "31c98d98e01b480089da8b0285c074393945c474348b821e03000083e0074874288b8214030000c1e8070fb6c03b4510"
      .. "75178b45088d4dc8e89af9ffff8945c0480f84eafeffffeb104181c22005000039ce75b631d28955c069f620050000c7"
      .. "45b8000100008d041e31f68945b48b038945bc85c074493945c474448b831e03000083e0074874388b45088d4dc889da"
      .. "e842f9ffff4875288b83140300008b5510c1e8070fb6c029c23b451072052b451089c28b45b839c273068955b88b75bc"
      .. "81c320050000395db475a385f6740e8b450c8b400c85c074168930eb12837dc0020f844afeffff31c08b75c48947048d"
      .. "65f489f05b5e5f5dc3"
local INCOMING_SITE = { "incoming", 0x0381e2eb, "5589e583ec14", "e96082fb0090" }
-- a fifth piece, right after the fourth (MLGrowth.lua starts at 0x047d6e50), for
-- SQUAD_PRESSURE: its numbers and its routine, which the routine of the first piece calls
-- (so it is always written with it)
local PRESSURE_CAVE = 0x047d6d40
local PRESSURE_CAVE_SIZE = 0x110
-- a sixth piece, in the run of zeros of .trace that MLSimToDate.lua leaves free between its
-- calendar block (0x03fc8000-0x03fc88ff) and the budget keys of MLMoney.lua
-- (0x03fc9300-0x03fc943f): the numbers and the routine of DEAL_MOOD, which the routine of the
-- first piece calls
local MOOD_CAVE = 0x03fc8900
local MOOD_CAVE_SIZE = 0xa00
-- the styles of DEAL_MOOD in the order of the memory, with the lowest and highest of each
local MOOD_STYLES = { { "seller", -15, 15 }, { "trader", -15, 15 }, { "builder", -15, 15 }, { "hoarder", -15, 15 } }
-- the groups of SQUAD_PRESSURE in the order of the memory, and the group (0 to 3) of each
-- of the 13 positions, GK to CF
local PRESSURE_GROUPS = { "GK", "DF", "MF", "FW" }
local GROUP_OF = "00010101020202020203030303"
local MONEY_MARK = 0x047b065c   -- where MLMoney.lua leaves its mark, "MLM" and the number of its version
-- the rating range a computer club searches first, smallest clubs first (the game's numbers)
local RANGE_LOW = { 47, 51, 55, 59, 63, 67, 70, 73, 76, 83 }
local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 86, 99 }
-- offsets in that memory: the twelve numbers, the two ranges, the personas by group, the
-- personas, the personas of the named clubs, their ids, the number of pairs of rivals and
-- the pairs (money_cave.py has the list)
local NUMBERS_AT, RANGES_AT, GROUPS_AT, PERSONAS_AT, CLUB_TYPES_AT, CLUB_IDS_AT = 0x34, 0x64, 0x78, 0xc8, 0x208, 0x2c8
local RIVALS_AT = 0x5c8
-- the last seven numbers of that memory: KNOWN_FAME (times 1 << 20, as the routine
-- compares it; 4096 is the largest number), STRICT_FREE, KEEP_BEST (three), KNOWN_FROM,
-- AGE_SHIFT
local LAST_AT = 0xde4
local MOST_PERSONAS, MOST_CLUBS, PER_GROUP, MOST_RIVALS = 15, 192, 8, 64
-- the numbers of a persona in the order of the memory, with the lowest and highest of each
local GENES = { { "free", 0, 100 }, { "listed", 0, 100 }, { "clubs", 0, 100 }, { "winter", 0, 100 },
                { "knows", 1, 100 }, { "fog", 0, 10 }, { "wealth", 10, 250 }, { "premium", 0, 250 },
                { "panic", 0, 250 }, { "fame", 0, 250 }, { "ambition", 0, 99 }, { "prestige", 0, 99 },
                { "keeps", 0, 100 }, { "strict", 0, 100 } }
local PLACE = { free = 0, listed = 1, clubs = 2 }
-- persona 0: a club as in version 1 (what every club is with PERSONA = false)
local NEUTRAL = "64000064ff0064646400ffff0000003fffff0100"
-- the routine: offset in that memory, machine code (source: money_cave.py)
local ROUTINE = { 0x7cc, "53575589e581ec900000008b45008945c88b58d88b480481f9580d660374"
      .. "0c81f9b90d66030f85d4040000894dc08b48dc894dac8b48188b51048955bc8b09894de88b50308b128955b8"
      .. "8b5014691235aeb2c28955b48b000fb6481b894df08b401c8b0083f8090f87920400008945e031c98b93b400"
      .. "000083e20f4a83fa01760e41f783b800000000000060750141894dd00fb74b2c6953309301000131d1894dd8"
      .. "6955e8b179379e31d1894dd43155b48b4dac81e1ffffff0069c993010001314db4894dac8b45e8e8d6040000"
      .. "8945ec8955b031c9518b45ec8b55e8e88e0400005989848d70ffffff4183f90e72e6c745f80d0000006a028d"
      .. "45f85053e873f007ff83c40c0fb6c08945dc8b55b0e81f0400008945cc837dd0000f84450100008365f8008d"
      .. "45f8508d45c45089d9e8876505ff8b45c43b0534eb4f020f84230100008b55e88b0dc8477d0449782e3904cd"
      .. "cc477d04750d3914cdd0477d040f84aa0300003914cdcc477d0475de3904cdd0477d040f8494030000ebcf83"
      .. "7dd0020f85df000000e8180400005052e8a00300008945a85a833d5c427d040074588b4dc88b49f48b45c425"
      .. "ff3f00003d8d0200000f83a700000083bc81ac070000170f8699000000817dc0b90d660375285253e86bf407"
      .. "ff83c4045a8b4de083f9087315837dbc04750439c1770b83f807736e807a0e087368586a0c598b55c4e86c03"
      .. "00008b55cc2b55a83b15f44f7d047d178b55dc0315ec4f7d042b55a87e090faf15f04f7d0401d0694dc4b179"
      .. "379e334dd8334dac69c92febd427c1e9186bc964c1e908833d0889fc03007405e8f13c7fffe8342100000f82"
      .. "b1020000eb0658e9a9020000837dd00174358b45dc3b05f84f7d04732a8b83b4000000c1e0093b05e44f7d04"
      .. "7319694dd4b1675616c1e9186bc964c1e9083b4d800f836e0200008b45cc03459c3945dc0f875f0200008b55"
      .. "b88b4dc88b49f48b45e825ff3f00003d8d02000073128b8481ac0700003b0558427d04730383ca018955e483"
      .. "7db8000f850c0100008b55ec807a10ff0f8494000000694db46bcaeb85c1e9186bc964c1e90831c08b9570ff"
      .. "ffff39d1722740039574ffffff39d1721c40039578ffffff39d17211837de4000f84df0100008b55ec0fb642"
      .. "10837de400752b8b4dc80fb649de3b0d54427d04751c694db4512d9eccc1e9186bc964c1e9083b8d7cffffff"
      .. "0f83a7010000837df00074118b55ec0fb64a1039c175040fb64a1189c83b45d00f8587010000837de4007565"
      .. "6945e8b179379e69c091f44525c1e8188b15fc4f7d048d4c12010fafc1c1e80829d08b4b1cc1e90783e13f29"
      .. "c18b55ec3a4a0e7c053a4a0f7e2b694dd49335871bc1e9186bc964c1e9088b45a4837dd000750a0faf05e84f"
      .. "7d046bc96439c10f821c0100008b45848d0c45010000006955d4656b54e6c1ea180fafcac1e90829c1014ddc"
      .. "837de400750f8b45cc2b45983945dc0f8ce80000008b55f08b4dec2251128b4de074128b45dc0fb69128427d"
      .. "0439d00f8fc80000008b048d00427d0483f8ff0f84a80000006a645f8b4d88e8ba0000008945fc8b45e40b45"
      .. "f0741ba138427d048b4d90e8a20000008d0c388b45fce8970000008945fca134427d048b4d8ce88700000069"
      .. "4dd46bcaeb85c1e9180fafc88b45fcbf00640000e86d000000e8750000008b8bb4000000c1e90b81e1ff0f00"
      .. "000faf4d948b45fcbfa0860100e848000000e8500000008b45dce8e3bdfdff8b4dd083f902741189f8f7248d"
      .. "3c427d04f73554067b0489c73b7dfc771089ec5d5f5b588b4d245650e9e54495ff89ec5d5f5b83c404e940ac"
      .. "e8fef7e139fa7303f7f7c383c8ffc30145fc7304834dfcffc30fb64a0e83f9097605b9090000000fb742080f"
      .. "af054c427d04030550427d04c1e8100fb69164427d0439d0730289d00fb6916e427d0439d0760289d0c30fb6"
      .. "040869c99301000169d2b179379e31d169c96bcaeb85c1e9180faf0d48427d04c1e908030d44427d04f7e1f7"
      .. "3558067b04c38b55c88b52f881c2cc84cc00528b8aa028000081f98a020000770c4978093902740883c210eb"
      .. "f48b142483c4048b0d60427d0449781239048dc8447d0475f40fb68108447d04eb1f0fb64a0e83f9097605b9"
      .. "0900000069c0b179379ec1e81d0fb684c878427d046bc01405c8427d04c3" }

-- The place that is changed: name, address, bytes there now, bytes to write.
local SITE = { "transfers", 0x0365fb0d, "8b4d2456e8aa98ac00", "e8ba4e170190909090" }

-- Native transfer candidate filter sites: bypass unlisted 85+ OVR freeze
local STAR_SITES = {
    { "star band", 0x0365f8ec, "83ff06", "83ff08" },
    { "star pick", 0x0366106b, "83f807", "83f808" },
    { "star level", 0x03661094, "83f808", "83f80a" },
}

-- Native squad trim & mutual contract termination sites: unlock 32-player squad deadlock
local TRIM_SITES = {
    { "trim plan", 0x03660b85, "83f919", "83f91e" },
    { "trim fill", 0x038895f6, "83f820", "83f821" },
    { "trim close", 0x0365d3f4, "833a20", "833a21" },
    { "trim evict", 0x03892145, "83f80d0f8523020000", "83f80c0f8223020000" },
}

-- The position need: the two routines (offset in the third piece of memory, machine code)
-- and the two places that are changed for it.
local NEED_ROUTINES = {
    { 0x010, "608b75b469f6180100000375b081c60cb8cc0066c786090100000000837e04010f87d8000000"
      .. "8b7da08b45a429f83db00000000f82c50000008d8fb000000031db5353ba800000008b47043b0508eb4f0275"
      .. "1085c07421668b07663b0504eb4f0274158b470883e07f01c3ff44240439d0730589c2893c2483c71039cf72"
      .. "c95f59497e7a29d389d0030500647d040fafc139c37269031504647d0483fa637605ba630000008b47082580"
      .. "3f00005231ff8d4e108d9e100100008b1181e2803f000039c2743881fa80060000750685ff750289cf83c110"
      .. "39d972df5a85ff741f8b0f81e17fc0ffff09c1890fc1e8074088860901000088960a010000eb015a618b45b8"
      .. "c3" },
    { 0x120, "8b45188b1051538b4d100fb68109010000488b5d0c3b03750d0fb6810a01000039c2730289c2"
      .. "5b59c3" },
}
local NEED_SITES = {
    { "need plan", 0x03660b93, "8b85b8ffffff", "e87858170190" },
    { "need pick", 0x03660c83, "8b45188b10", "e898581701" },
}

-- SQUAD_PRESSURE: its routine (offset in the fifth piece of memory, machine code)
local PRESSURE_ROUTINE = { 0x18, "39c10f83a90000002b05406d7d0439c10f8c9a0000008b4304"
      .. "c1e81c83f80c0f878b00000056570fb680486d7d04506a008b4dc88b49f8ff75c4e8d2bb04ff8bb828030000"
      .. "c1ef0983e77f8db0f80000008d3cfe39fe73496804eb4f0289f1e8026d40fe84c075348b4dc88b49f8ff7604"
      .. "ff36e865ba04fff680b400000030751b8b4004c1e81c83f80c77100fb680486d7d043b4424047503ff042483"
      .. "c608ebb3585a0fb692446d7d045f5e39c2f5c3f9c3" }

-- DEAL_MOOD: its routine (offset in the sixth piece of memory, machine code)
local MOOD_ROUTINE = { 0x10, "51535657837dd00074678b75d88b7dc469f69301000169ff2d"
      .. "ebd42731f78b75d469f66bcaeb8531f78b5dac69dbb179379e31df69ff6bcaeb85c1ef188b350089fc0385f6"
      .. "740c89fb0fafdec1eb0629f301d889fb83e3030fbe9b0489fc0301d885c0790231c083f8607605b860000000"
      .. "5f5e5b59c3" }

-- What MLMoney.lua must have put into its memory: name, address, bytes.
local MONEY = {
    { "value routine", 0x047b0c90,
      "83f8637605b86300000089c78b048500027b048b4b1cc1e90783e13f0fb69180067b0429d77f0231ff0faf3d"
      .. "800d7b043b3d840d7b0476068b3d840d7b040fb70c4d20057b04f7e1f73554067b0450f7e7f73554067b043b"
      .. "05880d7b047605a1880d7b045901c88b4b04c1e91c0fb70c4d20067b04f7e1f73554067b040fb74b2c695330"
      .. "9301000131d169c9b179379ec1e9180faf0d48067b04c1e908030d44067b04f7e1f73558067b043d9ce0f505"
      .. "7605b89ce0f50589c78b8bb4000000c1e90b81e1ff0f00000faf0d40067b04f7e1b9a0860100f7f101c7c745"
      .. "f400000000c3" },
    { "numbers", 0x047b0654,
      "64000000e8030000" },
    { "value hook", 0x038ab8db,
      "e8b053f000909090909090909090909090" },
}

-- The code of the game the place and the routine rely on: name, address, bytes.
local CONTEXT = {
    { "choose", 0x0365f5c2,
      "5589e583ec64535689cb31f657899df4ffffff89b5fcffffffe805cb1b008b40308d8ddcffffff518985f8ff"
      .. "ffff89b5e8ffffffe856ee24008b45108b550c83c404bf630000002b388d8dccffffff518b4d18be63000000"
      .. "2b3289bdd0ffffffe84b6d01008b108b8df8ffffff52e834331c0089f28985d4ffffff8995e4ffffff39fe0f"
      .. "832405000083c63cc1e60401de89b5e0ffffff8b45088b0883f9010f8ff004000083fa3c0f83e704000083f9"
      .. "0175078b46042b06eb0c8b8644fcffff2b8640fcffffc1f80485c00f84c404000083f90175078b0e894d10eb"
      .. "098b9640fcffff8955108b4d108b45088b0083f8017e058b4304eb0d75058b4604eb068b8644fcffff39c10f"
      .. "84790400008b51048b018b8df8ffffff5250e8822f1c0089c689b5d8ffffff85f60f843d040000f786b80000"
      .. "00000000100f852d0400008b83a00700008b0d34eb4f0289c231caf7c2ff3f0000750931c8a900c0ffff744d"
      .. "838dfcffffff018d450c508d8dc8ffffff5189f1c7450c00000000e845b91c008b008b8ba007000089c231ca"
      .. "f7c2ff3f0000751331c8a900c0ffff750a8b0d34eb4f02b001eb088b0d34eb4f0230c0f685fcffffff017407"
      .. "83a5fcfffffffe84c00f85a50300008b83a407000089c231caf7c2ff3f0000750931c8a900c0ffff7441838d"
      .. "fcffffff028d450c508d8dc4ffffff5189f1c7450c00000000e8c3b81c008b008b8ba407000089c231caf7c2"
      .. "ff3f0000750d31c8a900c0ffff7504b001eb0230c0f685fcffffff02740783a5fcfffffffd84c00f852f0300"
      .. "008d450c508d8dc0ffffff5189f1c7450c00000000e86fb81c008b4d188d95bcffffff5289c7e8496b01008b"
      .. "088b0789c231caf7c2ff3f0000750d31c8a900c0ffff0f84e8020000f686b4000000300f85db0200008d450c"
      .. "50bf140000006a2b89f1897d0ce848801c000fb64d0c8b55283b0a0f82b70200008d450c506a2b89f1897d0c"
      .. "e829801c000fb64d0c8b552c3b0a0f87980200008b4508833801745d56e86a471f008b5d3089c78b0383c404"
      .. "39c70f8272020000f686b40000000f753683f80772178d8ddcffffff5189f1e825d1feff83f8020f824d0200"
      .. "00833b007515f786b800000000000060750983ff060f83330200008b9df4ffffff8b7d14833f0d741d8b5520"
      .. "528d450f50575689d9c6450f00e87bd9ffff84c00f840e020000833f000f852e0100008d4d0c518d95f0ffff"
      .. "ff5289f1c7450c00000000e845b71c006834eb4f028d8df0ffffffe8d5d861ff84c00f84fd0000008b85f0ff"
      .. "ffff8b8df8ffffff31f65089b5ecffffffe8f52f1c00f7802803000000fe00000f86aa010000c7450cf80000"
      .. "00908b8df0ffffff518b8df8ffffffe8cb2f1c008b90280300008b3d04eb4f028b1d08eb4f02c1ea0983e27f"
      .. "89bdacffffff899db0ffffff39d673168b4d0c8b3c018b5c010489bdacffffff899db0ffffff6804eb4f028d"
      .. "8dacffffffe8d2e057ff84c075298b8df8ffffff5357e8382e1c0089c789f9e80983abff85c0750ff687b400"
      .. "0000307506ff85ecffffff8b85f0ffffff8b8df8ffffff83450c085046e8392f1c008b8828030000c1e90983"
      .. "e17f39ce0f8248ffffff83bdecffffff020f86d70000008bb5d8ffffff8b7d18c6450f0083c708bb10000000"
      .. "85ff74288b4d108b178b4704518d8da4ffffff8995a4ffffff8985a8ffffffe834e057ff84c07404c6450f01"
      .. "83c7104b75ce385d0f0f85870000008b7d1880bf080100000175388b562c8b46308d8db8ffffff518b8dd4ff"
      .. "ffff89959cffffff8985a0ffffffe8a1680100508d959cffffff52e805c2220083c40884c074438b7510568d"
      .. "85b4ffffff5089f9e87b68010050e80af6220083c40884c07509c6870801000001eb1b8b4d2456e8aa98ac00"
      .. "8b85e8ffffff408985e8ffffff83f80373478b9df4ffffff8b4d108bb5e0ffffff8bbdd0ffffff83c110894d"
      .. "10e963fbffff83bde8ffffff03731e8b95e4ffffff4283c6108995e4ffffff89b5e0ffffff39fa0f82eafaff"
      .. "ff5f5e5b89ec5dc22c00" },
    { "pick", 0x03660c52,
      "5589e56aff680c64540464a1000000005083ec30535657a1501a520231e8508d85f4ffffff64a30000000089"
      .. "8decffffff8b45188b108b451c508995e0ffffffe8f6c3ffff8985e4ffffffc6451b0085d27511b863000000"
      .. "c6451b018985e4ffffffeb0583fa28730ac785e0ffffff2800000083f863760ac785e4ffffff6300000031f6"
      .. "31ff89bdc4ffffff89b5c8ffffff89b5ccffffff89b5fcffffffe8f0b31b008b48308b5d108b4304898de8ff"
      .. "ffff83f801745b83f80474568b55288b45248b4d205250518b4d148d95c4ffffff528b550c8d451b50515352"
      .. "8d85e0ffffff508d8de4ffffff518b8decffffff8d95d8ffffff52c785d8ffffff01000000e86ae8ffff8bb5"
      .. "c8ffffff8bbdc4ffffffc685f3ffffff0039f775588b45288b4d248b55205051528b55148d85c4ffffff508b"
      .. "450c8d4d1b515253508d8de0ffffff518b8decffffff8d95e4ffffff528d85d8ffffff50c785d8ffffff0000"
      .. "0000e809e8ffff8bb5c8ffffff8bbdc4ffffffeb07c685f3ffffff01e8f5be1f0039f70f84da0200006a0056"
      .. "57e84ac4feff29fe89f3c1fb0383c40cc745240000000085db743489fe903b5d2476418b4e048b16518b8de8"
      .. "ffffff52e8221a1c00f780b8000000000000608b4524751c4083c60889452439d872cf31f685db0f849f0000"
      .. "0089f8894524eb6939c3770b68fc93f001ff1538747d048b8decffffff8d34c756e871c3ffff8b5d088b068b"
      .. "4e048903894b04c785fcffffffffffffff85ff7411578d550852c7450802000000e8124d56ff89d88b8df4ff"
      .. "ffff64890d00000000595f5e5b89ec5dc224008d24248b452439f376978b48048b10518b8de8ffffff52e878"
      .. "191c008b80b4000000240f3c020f8434020000834524084639de72ce31c089452485db746989fe39c30f8659"
      .. "ffffff56e84ec0220083c4043c0175448b4e048b16518b8de8ffffff52e82d191c00f780b800000000000020"
      .. "0f854c0200008b46048b0e50518b8de8ffffffe80b191c00f780b8000000000000400f852a0200008b452440"
      .. "83c60889452439c377a1c745240000000085db743d89fe3b5d240f86e4feffff8b56048b068b8de8ffffff52"
      .. "50e8c5181c008b88b40000008b452480e10f80f9010f84e20100004083c60889452439d872c5c74524000000"
      .. "0085db0f841601000089fe3b5d240f8698feffff8b56048b068b8de8ffffff5250e879181c008d4d145189c7"
      .. "8d55205289f9c7451400000000e8b3a01c008b0d34eb4f028b452089ca25ff3f000081e2ff3f000039d0750b"
      .. "334d20f7c100c0ffff74148b8decffffff83bc81ac070000170f869000000057e8fb2f1f008b168b4e0483c4"
      .. "0480bdf3ffffff008995d4ffffff898dd8ffffff0f85960100008b551c8b1283fa09720c8b4d288339000f87"
      .. "920100008b4d108b490483f901750983fa080f837501000083f904750839c20f875f01000083f807732d8b57"
      .. "2c8b47308d8ddcffffff518b8decffffff8995dcffffff8985e0ffffffe8e1c6ffff83f8080f823f0100008b"
      .. "45244083c60889452439d80f82f2feffff8bbdc4ffffff8b75088b1508eb4f028b0d04eb4f02c785fcffffff"
      .. "ffffffff895604890e85ff7411578d450850c7450802000000e8b24a56ff89f08b8df4ffffff64890d000000"
      .. "00595f5e5b89ec5dc2240039f3770b68fc93f001ff1538747d048b8decffffff8d34f756e8aec0ffff8b5d08"
      .. "8b0e8b5604890b895304c785fcffffffffffffff85ff7411578d450850c7450802000000e84f4a56ff89d88b"
      .. "8df4ffffff64890d00000000595f5e5b89ec5dc224008b452439c3770b68fc93f001ff1538747d048b8decff"
      .. "ffff8d34c756e848c0ffff8b5d088b168b46048913894304c785fcffffffffffffff85ff7411578d4d0851c7"
      .. "450802000000e8e94956ff89d88b8df4ffffff64890d00000000595f5e5b89ec5dc224008d95d4ffffff52eb"
      .. "108d8dd4ffffff51eb078d85d4ffffff508b8decffffffe8dfbfffff8b75088b85c4ffffff8b8dd4ffffff8b"
      .. "95d8ffffff890e895604c785fcffffffffffffff85c00f84cefeffff50e9b8" },
    { "range", 0x0365d08d,
      "5589e58b45088b0083f8097758ff2485fdd06503b84b0000005dc20400b84c0000005dc20400b84d0000005d"
      .. "c20400b84e0000005dc20400b84f0000005dc20400b8500000005dc20400b8530000005dc20400b856000000"
      .. "5dc20400b8630000005dc20400b84a0000005dc2040089fff2d06503a1d06503aad06503b3d06503bcd06503"
      .. "c5d06503ced06503d7d06503e0d06503e9d06503" },
    { "range low", 0x0365d12d,
      "5589e58b45088b0083f8097758ff24859dd16503b8330000005dc20400b8370000005dc20400b83b0000005d"
      .. "c20400b83f0000005dc20400b8430000005dc20400b8460000005dc20400b8490000005dc20400b84c000000"
      .. "5dc20400b8530000005dc20400b82f0000005dc2040089ff92d1650341d165034ad1650353d165035cd16503"
      .. "65d165036ed1650377d1650380d1650389d16503" },
    { "club", 0x0382b087,
      "5589e58b450c8b0083f8027c0f8b45088b0dc0fe510289085dc208008b9481a80000008b450889105dc20800" },
    { "band", 0x0385400e,
      "5589e583ec28a1501a520231e88985fcffffff8b0d480f5202578b7d088b572c8b473085c9751d85c00f94d0"
      .. "84c0742131c05f8b8dfcffffff31e9e8fa2b090089ec5dc3663b15440f5202750439c874df568d85d8ffffff"
      .. "506a2e89f9c785d8ffffff00000000e83638fdff0fb6b5d8ffffff83fe077605be070000006a028d8dd8ffff"
      .. "ff5157c785d8ffffff0d000000e8f648feff83c40c0fb6d0c785dcffffff00000000c785e0ffffff32000000"
      .. "c785e4ffffff37000000c785e8ffffff3c000000c785ecffffff46000000c785f0ffffff50000000c785f4ff"
      .. "ffff55000000c785f8ffffff5800000089f083fe05761531c93b948ddcffffff72084183f90872f1eb0289c8"
      .. "83fe047239770a83fa507205b80400000083fe05770a83fa557205b80500000083fe06770a83fa587205b806"
      .. "00000083fe07770a83fa5a7205b8070000008b8dfcffffff5e31e95fe8e52a090089ec5dc3" },
    { "club level", 0x0365d775,
      "5589e551535657e864e91b008b70308b45088b48048b10515289f131dbe89e501c0089c78d4508508d8dfcff"
      .. "ffff5189f9895d08e8d9d81c008b87b400000083e00f8d8ecc84cc0083f802750c5f5e8d43015b89ec5dc204"
      .. "0083f801750e5f5eb8050000005b89ec5dc20400a134eb4f028b95fcffffff89c631d6f7c6ff3f0000750931"
      .. "d0a900c0ffff74198d95fcffffff52e82744b5ff0fb6400e5f5e5b89ec5dc204005f5e89d85b89ec5dc20400" },
    { "ranking", 0x031b1c34,
      "5589e583ec0c5389c88b88a0280000565731ff8985fcffffff898df8ffffff85c9744a8b4d088b19895d0881"
      .. "e3ff3f000089c68d098d95f4ffffff5289f1e8fb464c008b0089c181e1ff3f000039d9750a334508a900c0ff"
      .. "ff741b4783c6103bbdf8ffffff72ce8b85fcffffff5f5e5b89ec5dc2040089f85fc1e0040385fcffffff5e5b"
      .. "89ec5dc20400" },
    { "rating", 0x03853b42,
      "5589e55de94f4efeff" },
    { "take", 0x041293c0,
      "5589e55689ce8b4604578b7d0839c773388b0e39f9773229cfc1ff033b460875096a0189f1e8eafaffff8b4e"
      .. "0485c974378b068b14f889118b44f804894104834604085f5e5dc204003b460875096a0189f1e8bdfaffff8b"
      .. "460485c0740a8b0f89088b5704895004834604085f5e5dc20400" },
    { "plan", 0x036602e5,
      "5589e56aff68008c4c0464a1000000005081ec84000000535657a1501a520231e8508d85f4ffffff64a30000"
      .. "0000898d94ffffff31f6c685daffffff00c685ebffffff00c685eaffffff00e8b0bd1b008b78308d85c8ffff"
      .. "ff5089bdb0ffffff8d9f0cb8cc00e801e124008d8dc8ffffff518d95d0ffffff52c785d0ffffff1e000000e8"
      .. "5de4240083c40c3c0175068885ebffffff8d85c8ffffff50e8cf96220083c4043c0175068885eaffffff89b5"
      .. "9cffffff89b5b4ffffff39b328ac030077208b8df4ffffff64890d00000000595f5e5b89ec5dc3eb038d2424"
      .. "8bb5b4ffffffb81f85eb51f7e6c1ea056bd26489f129d17525e8f11df7ff85c0741ce8e81df7ff80b8bc5901"
      .. "0000750ee8da1df7ff80b8bd5901000074a883bd9cffffff04779f81fe530300000f83fe0700008bb5b4ffff"
      .. "ff69f61801000001de89b5e0ffffff0f84e40700008d957cffffff5289f1e8365f01008b008b0d34eb4f0289"
      .. "c231caf7c2ff3f0000750d31c8a900c0ffff0f84b507000083be0c010000000f87a80700008d85c8ffffff50"
      .. "e8df95220083c40484c0740d83be14010000070f8288070000ff859cffffff8d8df3ffffff5189f1c685f3ff"
      .. "ffff01e8c8c7ffff8d9574ffffff5289f1e8bf5e01008b005089f9e806221c0089c3899dd4ffffff85db0f84"
      .. "450700008b8328030000c1e80931f683e07f764f8dbbf8000000eb038d24248b0d04eb4f028b1508eb4f0239"
      .. "c673058b0f8b570452518b8db0ffffffe859211c0085c0740a81a0b8000000ffffff9f8b8328030000c1e809"
      .. "4683e07f83c70839c672bc31ff89bda0ffffff89bda4ffffff89bda8ffffff8d8ddaffffff518d95ebffffff"
      .. "528d85a0ffffff508d8d78ffffff518b8dd4ffffff89bdfcffffffe8055e010050e8973e230031c031db83c4"
      .. "1031c98985b8ffffff899dbcffffff898dc0ffffffc685fcffffff0189bdecffffffeb0aeb028d098b8dc0ff"
      .. "ffff8b95a4ffffff8bb5a0ffffff29f2c1fa043b95ecffffff0f868206000001fef74608803f0000746e39de"
      .. "732a39f0772629c639cb75196a018d8db8ffffffe88faab9008b9dbcffffff8b85b8ffffff83e6f001c6eb1d"
      .. "39cb75196a018d8db8ffffffe86baab9008b9dbcffffff8b85b8ffffff85db74168b0e890b8b56048953048b"
      .. "4e08894b088b560c89530c83c310899dbcffffffff85ecffffff83c71081ffb00000000f824fffffff8bbdd4"
      .. "ffffff8d8570ffffff5089f9e80c5d010050e8328722008d88e9ffffff31f683c404898dd0ffffff89b5ccff"
      .. "ffff39f10f8ed10100008b8728030000c1e80983e07f89b5ecffffff0f86b901000081c7f800000089bde4ff"
      .. "ffffeb088d1b8b8dd0ffffff398dccffffff0f8d970100008b0d04eb4f028b1508eb4f0239c673058b0f8b57"
      .. "0452518b8db0ffffffe87c1f1c0089c689b598ffffff85f60f842f01000056e811391f008b8da0ffffff8985"
      .. "dcffffff8b85a4ffffff29c8c1f80483c40431ffc685f3ffffff0085c074508b562c89958cffffff8b563089"
      .. "9590ffffff39f80f860805000083bd90ffffff008b318b51040f85a800000085d20f94d284d27407c685f3ff"
      .. "ffff014783c11039f877d68bb598ffffff8b9dbcffffff80bdeaffffff01bf06000000752e8d85f2ffffff50"
      .. "8d8d98ffffff51c685f2ffffff00c78598ffffff05000000e8f2511f0083c40885c075038d780880bdf3ffff"
      .. "ff00756d39bddcffffff73658d95f2ffffff528d85dcffffff50c685f2ffffff00c785dcffffff05000000e8"
      .. "b3511f0083c40885c0752a818eb800000000000040eb28663bb58cffffff0f855bffffff3b9590ffffff0f84"
      .. "48ffffffe94affffff818eb800000000000020ff85ccffffff8b8dd4ffffff8b81280300008bb5ecffffff8b"
      .. "bde4ffffffc1e8094683c70883e07f89b5ecffffff89bde4ffffff39c60f8257feffff8b85a4ffffff8b95a0"
      .. "ffffff29d031c9c1f804898de4ffffff898decffffff39c80f86de00000031ff39c80f86b90300008b3508eb"
      .. "4f028b0c3a8b443a0485f6753f85c00f94d084c00f848d0000008b443a088bb5e0ffffffc1e807ba10000000"
      .. "83e07f31c901d68b1e81e3803f000081fb8006000074184101d639d172e9eb2d663b0d04eb4f02755239f074"
      .. "c1eb4c8bb5e0ffffff89ca01d28d54d608c1e00733420825803f000031420889caff85e4ffffff83fa10741d"
      .. "8b85e0ffffff83780403751101d289c18d44d108ba170000006689500e8b9dbcffffff8b85a4ffffff8b95a0"
      .. "ffffff8b8decffffff29d041c1f80483c710898decffffff39c80f872cffffff8b85b8ffffff89dec68580ff"
      .. "ffff008b8d80ffffff29c651c1fe0456535089b5dcffffffe82eebffff8b9de0ffffff31ff83c410837b0401"
      .. "89bdecffffff89bdd0ffffff750bbf0100000089bdd0ffffff8b8dd4ffffff8d9584ffffff52c685f3ffffff"
      .. "00e8a75901008b008b8d94ffffff25ff3f00008b9481ac0700002b95ccffffff01fa0395e4ffffff83fa190f"
      .. "92d084c00f84980100008b85b8ffffff83c0088985e0ffffffeb068bb5dcffffff3bb5ecffffff0f82750100"
      .. "000f86220200008b8de0ffffff8b01c1e80783e07fbe1000000031c98d5310eb038d24248b3a81e7803f0000"
      .. "81ff8006000074094101f239f172e9eb1989ca01d2c1e0073344d3108d54d30825803f000031420889ce8385"
      .. "e0ffffff10bf0100000001bde4ffffff01bdecffffff83fe100f84b80000008b430429f8747c29f8746729f8"
      .. "74528d85c8ffffff50e8a68f220083c40484c00f849200000083bb14010000080f82850000008d8ddbffffff"
      .. "518d9588ffffff52c685dbffffff00c78588ffffff64000000e8ad4e1f0083c40883f8647c37eb5701f68d74"
      .. "f308b8170000006689460eeb4601f68d74f308b91400000066894e0eeb358d95c8ffffff52e8328f220083c4"
      .. "0484c0742280bdf3ffffff00751901f68d74f308b806000000897b046689460cc685f3ffffff018d8d84ffff"
      .. "ff518b8dd4ffffffe8145801008b108b8594ffffff81e2ff3f00008b8c90ac0700002b8dccffffff038dd0ff"
      .. "ffff038de4ffffff83f9190f92d084c00f8579feffff8b85b8ffffff31f6c685fcffffff0039f07417508d95"
      .. "dcffffff52c785dcffffff02000000e8dd4f56ff8b85a0ffffff89b5b8ffffff89b5bcffffff89b5c0ffffff"
      .. "c785fcffffffffffffff39f07417508d85dcffffff50c785dcffffff02000000e8a04f56ff8bbdb0ffffff89"
      .. "b5a0ffffff89b5a4ffffff89b5a8ffffff8b85b4ffffff408d9f0cb8cc008985b4ffffff3b8328ac03000f82"
      .. "90f7ffff8b8df4ffffff64890d00000000595f5e5b89ec5dc3" },
    { "fill", 0x03661b15,
      "5589e583ec60568d85d4ffffff575089cee826c9240083c404e8b2a51b008b783031c089bddcffffff8985f0"
      .. "ffffff8985d8ffffff39873464d0000f8603040000538d9f10b8cc00899df4ffffff9083bdf0ffffff040f87"
      .. "e70300003d530300000f83b70300008d8bfcffffff85c90f84a903000083bb08010000000f879c03000080bb"
      .. "0c010000000f848f0300008d95d4ffffff52e8a57e220083c40484c0740d83bb10010000070f826f030000ff"
      .. "85f0ffffff8d85f8ffffff8d8bfcffffff50c6830c01000000c6830401000000e888470100a134eb4f028b8d"
      .. "f8ffffff89c231caf7c2ff3f0000750d31c8a900c0ffff0f84250300008d85e0ffffff508d8de4ffffff518d"
      .. "95f8ffffff52c785e0ffffff00000000c785e4ffffff06000000e8ce3e200083c40c8d85f8ffffff508d8fcc"
      .. "84cc00e8e3ffb4ff0fb6480e898decffffff8d95ecffffff5289f1e8c4b4ffff8b8df8ffffff8985c4ffffff"
      .. "8d85c0ffffff505189f9e8e50c1c0089c1e82f5db5ff8b103396a00700008b8df8ffffff81e2ff3f00003196"
      .. "a00700008b103396a007000081e2ff3f000033108d85bcffffff505189f98996a0070000e89f0c1c0089c1e8"
      .. "b55ef8ff8b103396a40700008d8db8ffffff81e2ff3f00003196a40700008b103396a407000031ff81e2ff3f"
      .. "000033108d85e0ffffff50518d8bfcffffff8996a407000089bde0ffffffe85646010050e8e280210089bde0"
      .. "ffffff83c4088d7b0c908d83fcffffff50e8c777220083c40484c00f84e70100008b1fc1eb0783e37f83fb0d"
      .. "0f84b70100008b97f8ffffff8b87fcffffff6804eb4f028d8da8ffffff8995a8ffffff8985acffffffe87fbd"
      .. "57ff84c00f85870100000fb74f060fb75704899de4ffffff8b9df4ffffff833b00c785c8ffffff0000000089"
      .. "8dccffffff8995e8ffffff74318885fdffffff8d85fdffffff508d8dd0ffffff51c785d0ffffff64000000e8"
      .. "bf3b1f0083c40883f8327d06c703040000008d95e8ffffff528d85ccffffff508d8dc8ffffff518d95ecffff"
      .. "ff528d85c4ffffff508d8dfcffffff5183c3fc538d95e4ffffff528d85b0ffffff5089f1e828eeffff6804eb"
      .. "4f028d8db0ffffffe884bc57ff84c0747731c03985e8ffffff756d8d8dc8ffffff518985c8ffffff8985d0ff"
      .. "ffff8985e8ffffff8d95ccffffff528d85d0ffffff508d8decffffff518d95e8ffffff528d85fcffffff5053"
      .. "8d8de4ffffff518d95a0ffffff5289f1c785ccffffff63000000e8aeedffff8b088b5004898db0ffffff8995"
      .. "b4ffffff8b85f4ffffff8338047506c700000000006804eb4f028d8db0ffffffe8e8bb57ff84c075348b85b0"
      .. "ffffff8b8db4ffffff8987f8ffffff898ffcffffff8b1781e2ffff7ff881ca0000400089d025ff7fc0ff0d00"
      .. "40000089078b85e0ffffff8b9df4ffffff4083c7108985e0ffffff83f8100f8202feffff8bbddcffffff8b85"
      .. "d8ffffff4081c3180100008985d8ffffff899df4ffffff3b873464d0000f820cfcffff5b5f5e89ec5dc3" },
    { "lineup", 0x03894bcf,
      "8b07890c308b8d44f8ffff894c30048b078b570429c2c1fa0439da0f8647fbffff8b4430086a028d8d2cf8ff"
      .. "ffc1e807518d9540f8ffff83e07f5289852cf8ffffe83deffbff0fb6c88b078b54300831ca83e27f31543008"
      .. "8b47042b0743c1f80483c40c83c61039c30f8227ffffff" },
    { "team", 0x03822969,
      "5589e55689ce8b4d0889c8c1e80e85c0744f8b155cf85102c1ea0e39d074423df0ff030072073dfeff030076"
      .. "3489c825ff3f00003dfd3f000074313dfe3f0000742a83be0814ec00025189f1750ae86cbaffff5e5dc20400"
      .. "e86dfaffff85c075068d8620e35f005e5dc20400e80b97ffff8b40348d4d08518d88b8370500e8b38d00005e"
      .. "5dc20400" },
    { "player", 0x03822835,
      "5589e55689ce8b4d0c3b0d30f8510274378b4508bafdff00006639d07435bafeff00006639d0742b83be0814"
      .. "ec0002515089f1750ae889bbffff5e5dc20800e8e5faffff85c075228d862036ed005e5dc20800e85898ffff"
      .. "8b40348d4d08518d88b8370500e8429100005e5dc20800" },
    { "no player", 0x02bddabe,
      "5589e58b55088b420485c0750a3941040f94d05dc2040056668b31663b325e750e3941047509b8010000005d"
      .. "c2040031c05dc20400" },
    { "no player id", 0x024feb04,
      "ffff000000000000" },
    { "trim fill", 0x038895f6,
      "83f820" },
    { "trim close", 0x0365d3f4,
      "833a20" },
    { "trim evict", 0x03892145,
      "83f80d0f8523020000" },
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

local function u32(v)
    return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256,
        math.floor(v / 16777216) % 256)
end

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

local function round(v)
    return math.floor(v + 0.5)
end

-- 1234567 -> "1,234,567"
local function commas(v)
    local s = string.format("%.0f", v)
    local out = ""
    while #s > 3 do
        out = "," .. string.sub(s, -3) .. out
        s = string.sub(s, 1, -4)
    end
    return s .. out
end

-- millions on the screen -> the game's stored amount (the screen shows 100 times it),
-- rounded to 10
local function amount(millions)
    return math.floor(millions * 1000 + 0.5) * 10
end

local function is_number(v, lo, hi)
    return type(v) == "number" and v >= lo and v <= hi
end

-- nil, or what is wrong with the settings of the ceiling
local function ceiling_fault()
    if CEILING == false then return nil end
    if type(CEILING_RATING) ~= "boolean" then return "CEILING_RATING is not true or false" end
    for _, c in ipairs({ { CEILING_STRETCH, "CEILING_STRETCH", 300 }, { CEILING_NEED, "CEILING_NEED", 300 },
                         { CEILING_LISTED, "CEILING_LISTED", 100 }, { CEILING_FREE, "CEILING_FREE", 100 } }) do
        if not is_number(c[1], 0, c[3]) then
            return c[2] .. " is not a number from 0 to " .. c[3]
        end
    end
    if type(CEILING) ~= "table" or #CEILING ~= 10 then
        return "CEILING is not a list of 10 numbers or false"
    end
    for i = 1, 10 do
        local v = CEILING[i]
        if type(v) ~= "number" or (v ~= 0 and (v < 0.01 or v > 9999)) then
            return "CEILING: entry " .. i .. " is not 0 or a number from 0.01 to 9999"
        end
    end
    return nil
end

-- the number of a persona by its name -> index 1 to 15, or nil
local function persona_number(name)
    for i, a in ipairs(ARCHETYPES) do
        if a[1] == name then return i end
    end
    return nil
end

-- nil, or what is wrong with the settings of the personas
local function persona_fault()
    if PERSONA == false then return nil end
    if type(SCOUTING) ~= "boolean" then return "SCOUTING is not true or false" end
    if not is_number(PERSONA_SPREAD, 0, 50) then return "PERSONA_SPREAD is not a number from 0 to 50" end
    if type(STRENGTH) ~= "table" or #STRENGTH ~= 2 or not is_number(STRENGTH[1], 0, 0.5)
        or not is_number(STRENGTH[2], 0, 99) then
        return "STRENGTH is not { 0 to 0.5, 0 to 99 }"
    end
    if not is_number(WINTER_MONTH, 0, 12) or WINTER_MONTH ~= math.floor(WINTER_MONTH) then
        return "WINTER_MONTH is not a whole number from 0 to 12"
    end
    if not is_number(SQUAD_NEED, 0, 32) then return "SQUAD_NEED is not a number from 0 to 32" end
    if not is_number(KNOWN_FROM, 0, 100) then return "KNOWN_FROM is not a number from 0 to 100" end
    if not is_number(AGE_SHIFT, 0, 5) then return "AGE_SHIFT is not a number from 0 to 5" end
    if not is_number(KNOWN_FAME, 0, 4096) then return "KNOWN_FAME is not a number from 0 to 4096" end
    if not is_number(STRICT_FREE, 0, 100) then return "STRICT_FREE is not a number from 0 to 100" end
    if type(KEEP_BEST) ~= "table" or #KEEP_BEST ~= 3 or not is_number(KEEP_BEST[1], 0, 99)
        or not is_number(KEEP_BEST[2], 0, 100) or not is_number(KEEP_BEST[3], 0, 99) then
        return "KEEP_BEST is not { 0 to 99, 0 to 100, 0 to 99 }"
    end
    if SQUAD_PRESSURE ~= false then
        local p = SQUAD_PRESSURE
        local fault = "SQUAD_PRESSURE is not false or { positions = { GK, DF, MF, FW: 0 to 99 }, keeps_drop = 0 to 100 }"
        if type(p) ~= "table" or type(p.positions) ~= "table" or not is_number(p.keeps_drop, 0, 100) then
            return fault
        end
        for _, name in ipairs(PRESSURE_GROUPS) do
            if not is_number(p.positions[name], 0, 99) then return fault end
        end
    end
    if DEAL_MOOD ~= false then
        local m = DEAL_MOOD
        local fault = "DEAL_MOOD is not false or { mood = 0 to 30, style = { seller, trader, builder, hoarder: -15 to 15 } }"
        if type(m) ~= "table" or not is_number(m.mood, 0, 30) or type(m.style) ~= "table" then return fault end
        for _, st in ipairs(MOOD_STYLES) do
            if not is_number(m.style[st[1]], st[2], st[3]) then return fault end
        end
    end
    if type(ARCHETYPES) ~= "table" or #ARCHETYPES < 1 or #ARCHETYPES > MOST_PERSONAS then
        return "ARCHETYPES is not a list of 1 to " .. MOST_PERSONAS .. " personas"
    end
    for i, a in ipairs(ARCHETYPES) do
        local where = "ARCHETYPES: entry " .. i
        if type(a) ~= "table" or type(a[1]) ~= "string" or a[1] == "" then return where .. " has no name" end
        where = where .. " (" .. a[1] .. ")"
        if persona_number(a[1]) ~= i then return where .. ": the name stands twice" end
        for _, g in ipairs(GENES) do
            if not is_number(a[g[1]], g[2], g[3]) then
                return where .. ": " .. g[1] .. " is not a number from " .. g[2] .. " to " .. g[3]
            end
        end
        if a.free + a.listed + a.clubs > 100 then return where .. ": free + listed + clubs is above 100" end
        if a.rating ~= nil and type(a.rating) ~= "boolean" then return where .. ": rating is not true or false" end
        if type(a.age) ~= "table" or #a.age ~= 2 or not is_number(a.age[1], 0, 63)
            or not is_number(a.age[2], a.age[1], 63) then
            return where .. ": age is not { first, last } with 0 to 63 each"
        end
        if type(a.second) ~= "table" or #a.second ~= 2 or PLACE[a.second[1]] == nil
            or PLACE[a.second[2]] == nil or a.second[1] == a.second[2] then
            return where .. ": second is not two different places of \"free\", \"listed\", \"clubs\""
        end
    end
    if type(PERSONA_GROUPS) ~= "table" or #PERSONA_GROUPS ~= 10 then
        return "PERSONA_GROUPS is not a list of 10 lists"
    end
    for i, group in ipairs(PERSONA_GROUPS) do
        if type(group) ~= "table" or #group < 1 or #group > PER_GROUP then
            return "PERSONA_GROUPS: entry " .. i .. " is not a list of 1 to " .. PER_GROUP .. " names"
        end
        for _, name in ipairs(group) do
            if persona_number(name) == nil then
                return "PERSONA_GROUPS: entry " .. i .. " names a persona ARCHETYPES does not have"
            end
        end
    end
    if type(CLUBS) ~= "table" or #CLUBS > MOST_CLUBS then
        return "CLUBS is not a list of at most " .. MOST_CLUBS .. " clubs"
    end
    for i, c in ipairs(CLUBS) do
        if type(c) ~= "table" or not is_number(c[1], 0, 4294967295) or c[1] ~= math.floor(c[1]) then
            return "CLUBS: entry " .. i .. " does not start with a club id"
        end
        if persona_number(c[2]) == nil then
            return "CLUBS: entry " .. i .. " names a persona ARCHETYPES does not have"
        end
    end
    return nil
end

local function is_club_id(v)
    return is_number(v, 0, 4294967295) and v == math.floor(v)
end

-- nil, or what is wrong with RIVALS
local function rivals_fault()
    if type(RIVALS) ~= "table" or #RIVALS > MOST_RIVALS then
        return "RIVALS is not a list of at most " .. MOST_RIVALS .. " pairs"
    end
    for i, pair in ipairs(RIVALS) do
        if type(pair) ~= "table" or #pair ~= 2 or not is_club_id(pair[1]) or not is_club_id(pair[2])
            or pair[1] == pair[2] then
            return "RIVALS: entry " .. i .. " is not a pair of two different club ids"
        end
    end
    return nil
end

-- nil, or what is wrong with the settings
local function projects_fault()
    if type(SPORTING_PROJECTS) ~= "boolean" then return "SPORTING_PROJECTS is not true or false" end
    if not is_number(PROJECT_COUNT, 1, 15) then return "PROJECT_COUNT is not a number from 1 to 15" end
    if not is_number(PROJECT_CEILING_BOOST, 0, 100) then return "PROJECT_CEILING_BOOST is not a number from 0 to 100" end
    if not is_number(PROJECT_RANK_MAX, 1, 50) then return "PROJECT_RANK_MAX is not a number from 1 to 50" end
    if type(TOP_FIVE_LEAGUES) ~= "table" or #TOP_FIVE_LEAGUES < 1 then
        return "TOP_FIVE_LEAGUES is not a list of league ids"
    end
    for i, lid in ipairs(TOP_FIVE_LEAGUES) do
        if not is_number(lid, 1, 65535) or lid ~= math.floor(lid) then
            return "TOP_FIVE_LEAGUES: entry " .. i .. " is not a valid league id"
        end
    end
    return nil
end

local function settings_fault()
    if type(WRITE) ~= "boolean" then return "WRITE is not true or false" end
    if type(INCOMING) ~= "boolean" then return "INCOMING is not true or false" end
    if type(SELL_SIDE) ~= "boolean" then return "SELL_SIDE is not true or false" end
    if type(PERSONA) ~= "boolean" then return "PERSONA is not true or false" end
    if type(NEED) ~= "boolean" then return "NEED is not true or false" end
    if not is_number(NEED_GAP, 1, 30) then return "NEED_GAP is not a number from 1 to 30" end
    if not is_number(NEED_BETTER, 1, 20) then return "NEED_BETTER is not a number from 1 to 20" end
    return ceiling_fault() or persona_fault() or rivals_fault() or projects_fault()
end

-- the highest value by club level 0 to 9 (CEILING starts with the best clubs, level 9;
-- 0xffffffff: no ceiling)
local function values()
    local out = {}
    for level = 0, 9 do
        local v = CEILING and CEILING[10 - level] or 0
        out[level + 1] = (v == 0) and 0xffffffff or clamp(amount(v), 100, 99990000)
    end
    return out
end

-- the 20 bytes of a persona
local function persona_bytes(a)
    local t = {}
    for i, g in ipairs(GENES) do
        t[i] = string.char(clamp(round(a[g[1]]), g[2], g[3]))
    end
    if not SCOUTING then t[5] = string.char(255) end
    return table.concat(t) .. string.char(round(a.age[1]), round(a.age[2]), PLACE[a.second[1]], PLACE[a.second[2]],
        (a.rating == false) and 0 or 1, 0)
end

-- the part of the memory after the ceilings: twelve numbers, the two rating ranges, the
-- personas by club level, the personas, the named clubs, the rivals
local function persona_image()
    local ceiling = (CEILING ~= false)
    local numbers = { ceiling and round(CEILING_STRETCH) or 0, ceiling and round(CEILING_NEED) or 0,
                      ceiling and round(CEILING_FREE) or 100, ceiling and round(CEILING_LISTED) or 100,
                      1000, 0, 0, 0, 0, 0, SELL_SIDE and 1 or 0, 0 }
    local groups, personas, types, ids = {}, { unhex(NEUTRAL) }, {}, {}
    if PERSONA then
        local spread = round(PERSONA_SPREAD)
        numbers[5], numbers[6] = 1000 - 10 * spread, 20 * spread
        numbers[7], numbers[8] = round(STRENGTH[1] * 65536), round(STRENGTH[2] * 65536) + 32768
        numbers[9], numbers[10], numbers[12] = WINTER_MONTH, round(SQUAD_NEED), #CLUBS
        for _, a in ipairs(ARCHETYPES) do personas[#personas + 1] = persona_bytes(a) end
        for level = 0, 9 do
            local group = PERSONA_GROUPS[10 - level]
            for k = 0, PER_GROUP - 1 do
                groups[#groups + 1] = string.char(persona_number(group[k % #group + 1]))
            end
        end
        for i, c in ipairs(CLUBS) do
            types[i] = string.char(persona_number(c[2]))
            ids[i] = u32(c[1])
        end
    end
    local out = ""
    for _, v in ipairs(numbers) do out = out .. u32(v) end
    for level = 1, 10 do out = out .. string.char(RANGE_LOW[level]) end
    for level = 1, 10 do out = out .. string.char(RANGE_TOP[level]) end
    out = out .. table.concat(groups)
    out = out .. string.rep("\0", PERSONAS_AT - NUMBERS_AT - #out) .. table.concat(personas)
    out = out .. string.rep("\0", CLUB_TYPES_AT - NUMBERS_AT - #out) .. table.concat(types)
    out = out .. string.rep("\0", CLUB_IDS_AT - NUMBERS_AT - #out) .. table.concat(ids)
    out = out .. string.rep("\0", RIVALS_AT - NUMBERS_AT - #out) .. u32(#RIVALS)
    for _, pair in ipairs(RIVALS) do out = out .. u32(pair[1]) .. u32(pair[2]) end
    return out
end

-- what goes into the memory: the ceilings, the highest rating of the second search by
-- club level (255: none), the tables of persona_image, the routine, the last seven
-- numbers (0 without PERSONA). nil: the module file is damaged
local function image()
    local parts = {}
    for _, v in ipairs(values()) do parts[#parts + 1] = u32(v) end
    for level = 0, 9 do
        parts[#parts + 1] = string.char((CEILING and CEILING_RATING) and RANGE_TOP[level + 1] or 255)
    end
    local out = table.concat(parts)
    out = out .. string.rep("\0", NUMBERS_AT - #out) .. persona_image()
    if #out > ROUTINE[1] or #unhex(NEUTRAL) ~= 20 or ROUTINE[1] + #ROUTINE[2] / 2 > LAST_AT then
        return nil
    end
    out = out .. string.rep("\0", ROUTINE[1] - #out) .. unhex(ROUTINE[2])
    out = out .. string.rep("\0", LAST_AT - #out)
    local fame = round(KNOWN_FAME)
    local last = PERSONA and { fame < 4096 and fame * 0x100000 or 0xffffffff, round(STRICT_FREE),
                               round(KEEP_BEST[1]), round(KEEP_BEST[2]), round(KEEP_BEST[3]), round(KNOWN_FROM),
                               round(AGE_SHIFT) } or { 0, 0, 0, 0, 0, 0, 0 }
    for _, v in ipairs(last) do out = out .. u32(v) end
    if #out ~= CAVE_SIZE then return nil end
    return out
end

-- what goes into the memory of NEED. nil: the module file is damaged
local function need_image()
    local out = u32(round(NEED_GAP)) .. u32(round(NEED_BETTER) - 1)
    for _, r in ipairs(NEED_ROUTINES) do
        if #out > r[1] then return nil end
        out = out .. string.rep("\0", r[1] - #out) .. unhex(r[2])
    end
    if #out > NEED_CAVE_SIZE then return nil end
    return out .. string.rep("\0", NEED_CAVE_SIZE - #out)
end

-- what goes into the memory of SQUAD_PRESSURE: the drop (0: off, and without PERSONA),
-- the four limits, the group of each position, the routine. nil: the module file is damaged
local function pressure_image()
    local on = PERSONA and SQUAD_PRESSURE
    local out = u32(on and round(on.keeps_drop) or 0)
    for _, name in ipairs(PRESSURE_GROUPS) do
        out = out .. string.char(on and round(on.positions[name]) or 0)
    end
    out = out .. unhex(GROUP_OF)
    if #out > PRESSURE_ROUTINE[1] then return nil end
    out = out .. string.rep("\0", PRESSURE_ROUTINE[1] - #out) .. unhex(PRESSURE_ROUTINE[2])
    if #out > PRESSURE_CAVE_SIZE then return nil end
    return out .. string.rep("\0", PRESSURE_CAVE_SIZE - #out)
end

-- what goes into the memory of DEAL_MOOD: the mood (0: off, and without PERSONA), the four
-- styles, the routine. nil: the module file is damaged
local function mood_image()
    local on = PERSONA and DEAL_MOOD
    if not on then return string.rep("\0", MOOD_CAVE_SIZE) end   -- no window, no routine: MOOD_ON stays 0
    local out = u32(round(on.mood))
    for _, st in ipairs(MOOD_STYLES) do
        local v = round(on.style[st[1]])
        out = out .. string.char(v >= 0 and v or 256 + v)
    end
    out = out .. u32(1)                 -- MOOD_ON: the ceiling routine calls the routine below
    if #out > MOOD_ROUTINE[1] then return nil end
    out = out .. string.rep("\0", MOOD_ROUTINE[1] - #out) .. unhex(MOOD_ROUTINE[2])
    if #out > MOOD_CAVE_SIZE then return nil end
    return out .. string.rep("\0", MOOD_CAVE_SIZE - #out)
end

-- what goes into the memory of INCOMING. nil: the module file is damaged
local function incoming_image()
    local code = unhex(INCOMING_ROUTINE)
    -- the routine reads the pairs of RIVALS out of the tables of the memory above: if that
    -- memory moved, the bytes would have to be built again (python3 money_cave.py build)
    if code == nil or #code > INCOMING_CAVE_SIZE or not string.find(code, u32(CAVE + RIVALS_AT), 1, true) then
        return nil
    end
    return code .. string.rep("\0", INCOMING_CAVE_SIZE - #code)
end

-- one line of the log for a piece of memory that is compared: -> is it as expected?
local function same(name, at, expected)
    local got = memory.read(at, #expected / 2)
    local good = (got ~= nil and hex(got) == expected)
    log(string.format("check: %-13s at %08x  %s", name, at, good and "as expected" or "DIFFERENT"))
    return good
end

local function report_ceiling()
    log("price ceiling of the computer clubs: the value on the screen up to which a club signs for sure, by its "
        .. "place in the club ranking:")
    local groups = { "1-10", "11-20", "21-50", "51-80", "81-120", "121-170", "171-220", "221-260", "261-300",
                     "others" }
    local amounts = values()
    local line = " "
    for i = 1, 10 do
        local c = amounts[11 - i]
        line = line .. " " .. groups[i] .. ": " .. (c == 0xffffffff and "none" or commas(c * 100))
            .. (i < 10 and ";" or "")
        if i == 5 or i == 10 then
            log(line)
            line = " "
        end
    end
    log(string.format("  above the ceiling: the chance falls to none at %d percent above it; a club in need "
        .. "counts its ceiling %d percent higher; a listed player counts at %d percent of his value, a player "
        .. "without a contract at %d percent", round(CEILING_STRETCH), round(CEILING_NEED),
        round(CEILING_LISTED), round(CEILING_FREE)))
    if CEILING_RATING then
        local free = {}
        for _, a in ipairs(ARCHETYPES) do
            if a.rating == false then free[#free + 1] = a[1] end
        end
        log("  second search: no player rated above the top of the club's own rating range"
            .. (#free > 0 and (", except for " .. table.concat(free, ", ")) or ""))
    else
        log("  second search: from rating 99 down, as in the game")
    end
end

local function report_persona()
    log(string.format("club personas: %d personas, %d clubs named, the others by their place in the club "
        .. "ranking; each number up to %d percent lower or higher from club to club", #ARCHETYPES, #CLUBS,
        round(PERSONA_SPREAD)))
    local seen, twice = {}, 0
    for _, c in ipairs(CLUBS) do
        if seen[c[1]] then twice = twice + 1 end
        seen[c[1]] = true
    end
    if twice > 0 then
        log(string.format("  note: %d entries of CLUBS name a club that a later entry names again; the last entry of "
            .. "a club counts", twice))
    end
    if round(KEEP_BEST[2]) > 0 then
        log(string.format("  a club keeps its first team: for each rating point a player stands above its eleven "
            .. "minus %d, %d percent more often; not against a buyer whose eleven is %d or more points better",
            round(KEEP_BEST[1]), round(KEEP_BEST[2]), round(KEEP_BEST[3])))
    else
        log("  a club keeps its first team no more often than its other players (KEEP_BEST is off)")
    end
    if SQUAD_PRESSURE and round(SQUAD_PRESSURE.keeps_drop) > 0 then
        local p = SQUAD_PRESSURE.positions
        log(string.format("  squad pressure: a club with more than %d goalkeepers, %d defenders, %d midfielders or %d "
            .. "forwards counts `keeps` %d lower for a player of that group", round(p.GK), round(p.DF), round(p.MF),
            round(p.FW), round(SQUAD_PRESSURE.keeps_drop)))
    else
        log("  squad pressure: off; a club keeps a player the same however many it has for his position")
    end
    log(string.format("  players rated %d or more are known to every club; the ages of a persona are moved by up "
        .. "to %d years from club to club", round(KNOWN_FROM), round(AGE_SHIFT)))
    log(string.format("  players of a popularity of %d or more are known to every club; for a player without a "
        .. "contract %d percent of `strict` count", round(KNOWN_FAME), round(STRICT_FREE)))
    for _, a in ipairs(ARCHETYPES) do
        log(string.format("  %-17s looks first: free %d, listed %d, clubs %d percent, second search %s, %s; winter %d; ages "
            .. "%d-%d (%d); knows %s; fog %d; wealth %d, premium %d, panic %d, fame %d; ambition %d, prestige %d; "
            .. "keeps %d", a[1], round(a.free), round(a.listed), round(a.clubs), a.second[1], a.second[2],
            round(a.winter), round(a.age[1]), round(a.age[2]), round(a.strict),
            SCOUTING and string.format("%d", round(a.knows)) or "all", round(a.fog), round(a.wealth), round(a.premium),
            round(a.panic), round(a.fame), round(a.ambition), round(a.prestige), round(a.keeps)))
    end
end

function m.init(ctx)
    log("MLTransfers 9: the transfers of the computer clubs from the settings in MLTransfers.lua")

    local fault = settings_fault()
    if fault then
        log("RESULT: nothing written. Settings: " .. fault)
        return
    end
    if CEILING == false and not SELL_SIDE and not PERSONA and not NEED and not INCOMING and #RIVALS == 0 then
        log("RESULT: nothing written. CEILING, SELL_SIDE, PERSONA, NEED and INCOMING are off and RIVALS is "
            .. "empty: the computer clubs choose as in the game.")
        return
    end
    local memory_image = image()
    local need_memory = need_image()
    local incoming_memory = incoming_image()
    local pressure_memory = pressure_image()
    local mood_memory = PERSONA and mood_image() or string.rep("\0", MOOD_CAVE_SIZE)
    local sites = { SITE }
    for _, site in ipairs(STAR_SITES) do sites[#sites + 1] = site end
    for _, site in ipairs(TRIM_SITES) do sites[#sites + 1] = site end
    if NEED then
        for _, site in ipairs(NEED_SITES) do sites[#sites + 1] = site end
    end
    if INCOMING then sites[#sites + 1] = INCOMING_SITE end
    if memory_image == nil or need_memory == nil or (PERSONA and mood_memory == nil)
        or pressure_memory == nil or (INCOMING and incoming_memory == nil) then
        log("RESULT: nothing written. The module file is damaged (routine).")
        return
    end

    -- 1. is MLMoney.lua in, with the value routine this module calls?
    local mark = memory.read(MONEY_MARK, 4)
    local found = (mark ~= nil and string.sub(mark, 1, 3) == "MLM")
    log(string.format("check: %-13s at %08x  %s", "MLMoney.lua", MONEY_MARK,
        found and ("installed, version " .. string.sub(mark, 4, 4)) or "NOT FOUND"))
    local money = found
    if found then
        for _, c in ipairs(MONEY) do
            if not same(c[1], c[2], c[3]) then money = false end
        end
    end

    -- 2. is this the game the module was made for?
    local good = true
    for _, c in ipairs(CONTEXT) do
        if not same(c[1], c[2], c[3]) then good = false end
    end
    local room = memory.read(CAVE, CAVE_SIZE)
    local empty = (room ~= nil and room == string.rep("\0", CAVE_SIZE))
    log(string.format("check: %-13s at %08x  %s", "free memory", CAVE, empty and "empty" or "NOT EMPTY"))
    if NEED then
        room = memory.read(NEED_CAVE, NEED_CAVE_SIZE)
        local free = (room ~= nil and room == string.rep("\0", NEED_CAVE_SIZE))
        log(string.format("check: %-13s at %08x  %s", "free memory", NEED_CAVE, free and "empty" or "NOT EMPTY"))
        empty = empty and free
    end
    if INCOMING then
        room = memory.read(INCOMING_CAVE, INCOMING_CAVE_SIZE)
        local free = (room ~= nil and room == string.rep("\0", INCOMING_CAVE_SIZE))
        log(string.format("check: %-13s at %08x  %s", "free memory", INCOMING_CAVE, free and "empty" or "NOT EMPTY"))
        empty = empty and free
    end
    room = memory.read(PRESSURE_CAVE, PRESSURE_CAVE_SIZE)
    local spare = (room ~= nil and room == string.rep("\0", PRESSURE_CAVE_SIZE))
    log(string.format("check: %-13s at %08x  %s", "free memory", PRESSURE_CAVE, spare and "empty" or "NOT EMPTY"))
    empty = empty and spare
    if PERSONA then
        room = memory.read(MOOD_CAVE, MOOD_CAVE_SIZE)
        local free = (room ~= nil and room == string.rep("\0", MOOD_CAVE_SIZE))
        log(string.format("check: %-13s at %08x  %s", "free memory", MOOD_CAVE, free and "empty" or "NOT EMPTY"))
        empty = empty and free
    end
    if not found then
        log("RESULT: nothing written. MLMoney.lua is not installed, and this module needs its player values. "
            .. "In sider.ini the line for MLMoney.lua must stand above the line for MLTransfers.lua, and "
            .. "the RESULT line of MLMoney.lua must say \"installed\".")
        return
    end
    if not money then
        log("RESULT: nothing written. The MLMoney.lua that is installed is not the version this module was "
            .. "made for. Use the two files that came together.")
        return
    end
    for _, site in ipairs(sites) do
        local there = memory.read(site[2], #site[3] / 2)
        if there ~= nil and string.sub(hex(there), 1, 2) == "e8" and hex(there) ~= site[3] then
            log("RESULT: nothing written. The game's choosing code is changed already: by an MLMoney.lua of "
                .. "version 6 with CEILING on (replace it with version 7), by an older version of this module, or "
                .. "this module stands twice in sider.ini.")
            return
        end
    end
    if not (good and empty) then
        log("RESULT: nothing written. This game does not hold what the module expects; "
            .. "send this log.")
        return
    end
    if not WRITE then
        log("RESULT: nothing written (WRITE = false). All checks passed.")
        return
    end

    -- 3. the tables and the routines first; nothing in the game points to them yet
    memory.write(CAVE, memory_image)
    local written = (memory.read(CAVE, CAVE_SIZE) == memory_image)
    if written and NEED then
        memory.write(NEED_CAVE, need_memory)
        written = (memory.read(NEED_CAVE, NEED_CAVE_SIZE) == need_memory)
    end
    if written and INCOMING then
        memory.write(INCOMING_CAVE, incoming_memory)
        written = (memory.read(INCOMING_CAVE, INCOMING_CAVE_SIZE) == incoming_memory)
    end
    if written then
        memory.write(PRESSURE_CAVE, pressure_memory)
        written = (memory.read(PRESSURE_CAVE, PRESSURE_CAVE_SIZE) == pressure_memory)
    end
    if written and PERSONA then
        memory.write(MOOD_CAVE, mood_memory)
        written = (memory.read(MOOD_CAVE, MOOD_CAVE_SIZE) == mood_memory)
    end
    if not written then
        log("RESULT: the table could not be written; the game's code is unchanged. "
            .. "Send this log.")
        return
    end

    -- 4. the places in the game's code
    for i, site in ipairs(sites) do
        local new = unhex(site[4])
        memory.write(site[2], new)
        local stuck = (memory.read(site[2], #new) == new)
        log(string.format("written: %-9s at %08x  %s", site[1], site[2], stuck and "ok" or "FAILED"))
        if not stuck then
            local restored = true
            for j = i, 1, -1 do
                local site = sites[j]
                local old = unhex(site[3])
                memory.write(site[2], old)
                if memory.read(site[2], #old) ~= old then restored = false end
            end
            log("RESULT: a change did not go in. " .. (restored and "Hooks restored. " or "Hook restore failed. ")
                .. "Quit the game, remove the module, send this log.")
            return
        end
    end

    local changed = {}
    if CEILING ~= false then
        report_ceiling()
        changed[#changed + 1] = "price ceiling of the computer clubs"
    end
    if SELL_SIDE then
        log("selling side: a player whose club does not let him go takes no place on a buyer's list")
        changed[#changed + 1] = "selling side"
    end
    if PERSONA then
        report_persona()
        changed[#changed + 1] = "club personas"
        if SCOUTING then changed[#changed + 1] = "scouting" end
    end
    if #RIVALS > 0 then
        log(string.format("rivals: %d pairs of clubs do not buy each other's players who have a contract", #RIVALS))
        changed[#changed + 1] = "rivals"
    end
    if NEED then
        log(string.format("position need: a club looks for a player for the weakest place of its eleven, the "
            .. "goalkeeper included, when he stands %d or more rating points below the mean of the others; it "
            .. "takes only a player rated %d or more above him", round(NEED_GAP), round(NEED_BETTER)))
        changed[#changed + 1] = "position need"
    end
    if PERSONA and DEAL_MOOD then
        local styles = {}
        for _, st in ipairs(MOOD_STYLES) do
            styles[#styles + 1] = string.format("%s %+d", st[1], round(DEAL_MOOD.style[st[1]]))
        end
        log(string.format("mood of a deal: `keeps` of the club that sells moves by up to %d percent with the day of "
            .. "the career, and its style adds %s (percent of `keeps`); a club that CLUBS names keeps the character "
            .. "its archetype gives it, and the style leans on it", round(DEAL_MOOD.mood), table.concat(styles, ", ")))
        changed[#changed + 1] = "mood of a deal"
    end
    if INCOMING then
        log("offers for your players: the club that makes one is the one of the nearest slot that would take "
            .. "him (no rival, its character wants him, a place in its plan, its ceiling), so none is lost")
        changed[#changed + 1] = "offers for your players"
    end
    if SPORTING_PROJECTS then
        log(string.format("sporting projects: %d qualifying AI clubs from global top %d of the top five leagues receive up to %d%% recruitment ceiling assistance for priority squad need positions",
            round(PROJECT_COUNT), round(PROJECT_RANK_MAX), round(PROJECT_CEILING_BOOST)))
    end
    log("squad trimming: AI squad cap raised to 32 with mutual contract terminations enabled")
    log("RESULT: installed. Changed: " .. table.concat(changed, ", ") .. ".")
end

return m
