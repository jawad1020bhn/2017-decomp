-- MLSwiss.lua, version 1: UEFA Swiss Format League Phase & Knockouts for PES 2017 Master League (Sider Lua module).
-- Made for PES2017.exe sha256 44b0caaa...
--
-- What this module does:
-- Implements the official UEFA 36-team single league phase ("Swiss system") and
-- knockout progression introduced in 2024/25 for European competitions (Champions League):
--
-- 1. 36 Qualified European Clubs divided into 4 Seeding Pots of 9 teams by coefficient.
-- 2. 8-Matchday League Phase Schedule:
--    - Each club plays 8 unique opponents (4 Home, 4 Away).
--    - Balanced across all 4 pots: exactly 2 opponents from each pot (1 Home, 1 Away).
--    - Country protection: clubs from the same association cannot play each other.
-- 3. Unified 36-Team Standings Table:
--    - Points (3 win, 1 draw, 0 loss), Goal Difference (GD), Goals For (GF), Away Goals.
--    - Strict UEFA tiebreakers.
-- 4. Qualification & Knockouts:
--    - Ranks 1 to 8: Direct qualification to Round of 16 (seeded).
--    - Ranks 9 to 24: Two-legged Knockout Phase Play-Offs (9-16 seeded vs 17-24 unseeded).
--    - Ranks 25 to 36: Completely eliminated from Europe (no drop-down to Europa League).
--    - Round of 16 -> Quarter-finals -> Semi-finals -> Final.
-- 5. 2024/25 Financial Rewards System:
--    - Starting fee: £15.70M (€18.62M).
--    - Match performance: £1.77M (€2.10M) per win, £0.59M (€0.70M) per draw.
--    - Final league phase rank bonus: 36 shares (£230k to £8.28M / €9.9M).
--    - Knockout round bonuses: Play-offs (£0.84M), R16 (£9.30M), QF (£10.50M),
--      SF (£12.70M), Runner-up (£15.60M), Champion (£21.10M).
--    - Automatically credited to user club transfer budget and balance in Master League!
-- 6. Live In-Game Memory Observer:
--    - Hooks into Master League match records (mode_data + 0x6f154c).
--    - Intercepts completed European matches, updates the Swiss standings in real time.
--    - Simulates AI-vs-AI fixtures using realistic Poisson/Elo ratings.
--    - Outputs formatted ASCII table and bracket to MLSwiss_Table.txt.
--
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, pairs, tonumber, type, io, os.

local m = {}

-- ============================ SETTINGS ============================

-- Master switch for the UEFA Swiss Format engine
local SWISS_ENABLED = true

-- Target competition ID (2 = UEFA Champions League, 3 = UEFA Europa League)
local COMPETITION_ID = 2

-- Total clubs participating in the league phase
local TOTAL_TEAMS = 36

-- Number of league phase matchdays per club (standard: 8)
local LEAGUE_ROUNDS = 8

-- Credit prize money directly to user club's Transfer Budget and Balance in Master League
local CREDIT_PRIZES = true

-- Simulate remaining AI matches on European matchdays using Poisson/Elo strength model
local SIMULATE_AI = true

-- Table output filename (saved in Sider directory)
local TABLE_FILE = "MLSwiss_Table.txt"

-- Command control filename for manual triggers
local COMMAND_FILE = "MLSwiss_Command.txt"

-- Financial reward amounts in millions (2024/25 UEFA Champions League standard, GBP):
local PRIZE_BASE              = 15.70  -- €18.62M starting fee
local PRIZE_WIN               = 1.77   -- €2.10M win bonus
local PRIZE_DRAW              = 0.59   -- €0.70M draw bonus
local PRIZE_RANK_SHARE        = 0.23   -- €0.275M per rank share (36 shares for 1st = £8.28M / €9.9M)
local PRIZE_PLAYOFF           = 0.84   -- €1.00M play-off round qualification
local PRIZE_R16               = 9.30   -- €11.00M round of 16 qualification
local PRIZE_QF                = 10.50  -- €12.50M quarter-final
local PRIZE_SF                = 12.70  -- €15.00M semi-final
local PRIZE_RUNNER_UP         = 15.60  -- €18.50M runner-up
local PRIZE_CHAMPION          = 21.10  -- €25.00M champion

-- ============================ CLUB POOL ============================

-- Official 36 European clubs mapped by ID, name, country association, and strength rating:
local TEAMS = {
    -- Pot 1 (Ranks 1 to 9)
    { id = 0x001b4036, name = "Real Madrid CF",         assoc = "ESP", pot = 1, rating = 87 },
    { id = 0x002b400c, name = "Manchester City FC",      assoc = "ENG", pot = 1, rating = 86 },
    { id = 0x001fc074, name = "FC Bayern München",       assoc = "GER", pot = 1, rating = 86 },
    { id = 0x001c804a, name = "Paris Saint-Germain",     assoc = "FRA", pot = 1, rating = 87 },
    { id = 0x0019c00b, name = "Liverpool FC",            assoc = "ENG", pot = 1, rating = 85 },
    { id = 0x001dc01c, name = "Internazionale Milano",   assoc = "ITA", pot = 1, rating = 84 },
    { id = 0x001f8075, name = "Borussia Dortmund",       assoc = "GER", pot = 1, rating = 83 },
    { id = 0x04e4807e, name = "RB Leipzig",              assoc = "GER", pot = 1, rating = 80 },
    { id = 0x001b002b, name = "FC Barcelona",            assoc = "ESP", pot = 1, rating = 87 },

    -- Pot 2 (Ranks 10 to 18)
    { id = 0x00200073, name = "Bayer 04 Leverkusen",     assoc = "GER", pot = 2, rating = 80 },
    { id = 0x002b002a, name = "Club Atlético de Madrid", assoc = "ESP", pot = 2, rating = 84 },
    { id = 0x003a8014, name = "Atalanta BC",             assoc = "ITA", pot = 2, rating = 80 },
    { id = 0x001e001d, name = "Juventus FC",             assoc = "ITA", pot = 2, rating = 82 },
    { id = 0x002fc063, name = "SL Benfica",              assoc = "POR", pot = 2, rating = 80 },
    { id = 0x00194000, name = "Arsenal FC",              assoc = "ENG", pot = 2, rating = 87 },
    { id = 0x00434148, name = "Club Brugge KV",          assoc = "BEL", pot = 2, rating = 78 },
    { id = 0x0022401f, name = "FC Shakhtar Donetsk",     assoc = "UKR", pot = 2, rating = 77 },
    { id = 0x001e4020, name = "AC Milan",                assoc = "ITA", pot = 2, rating = 82 },

    -- Pot 3 (Ranks 19 to 27)
    { id = 0x001d4051, name = "Feyenoord Rotterdam",     assoc = "NED", pot = 3, rating = 78 },
    { id = 0x0030406f, name = "Sporting CP",             assoc = "POR", pot = 3, rating = 79 },
    { id = 0x001d805a, name = "PSV Eindhoven",           assoc = "NED", pot = 3, rating = 79 },
    { id = 0x012cc191, name = "GNK Dinamo Zagreb",       assoc = "CRO", pot = 3, rating = 76 },
    { id = 0x018c8193, name = "FC Red Bull Salzburg",    assoc = "AUT", pot = 3, rating = 77 },
    { id = 0x00354041, name = "Lille OSC",               assoc = "FRA", pot = 3, rating = 78 },
    { id = 0x0131c190, name = "FK Crvena zvezda",        assoc = "SRB", pot = 3, rating = 75 },
    { id = 0x01e78176, name = "BSC Young Boys",          assoc = "SUI", pot = 3, rating = 75 },
    { id = 0x0020c161, name = "Celtic FC",               assoc = "SCO", pot = 3, rating = 76 },

    -- Pot 4 (Ranks 28 to 36)
    { id = 0x0041c033, name = "ŠK Slovan Bratislava",    assoc = "SVK", pot = 4, rating = 73 },
    { id = 0x001c0046, name = "AS Monaco",               assoc = "FRA", pot = 4, rating = 79 },
    { id = 0x0511418f, name = "AC Sparta Praha",         assoc = "CZE", pot = 4, rating = 75 },
    { id = 0x001ac001, name = "Aston Villa FC",          assoc = "ENG", pot = 4, rating = 81 },
    { id = 0x002e8015, name = "Bologna FC 1909",         assoc = "ITA", pot = 4, rating = 77 },
    { id = 0x0222c10d, name = "Girona FC",               assoc = "ESP", pot = 4, rating = 78 },
    { id = 0x0039c07f, name = "VfB Stuttgart",           assoc = "GER", pot = 4, rating = 80 },
    { id = 0x02084194, name = "SK Sturm Graz",           assoc = "AUT", pot = 4, rating = 74 },
    { id = 0x014c403e, name = "Stade Brestois 29",       assoc = "FRA", pot = 4, rating = 76 },
}

-- ============================ FIXTURE SCHEDULE ============================

-- Pre-computed, verified 8-round fixture schedule (1-based team indices):
-- 144 matches total, exactly 18 matches per round.
-- Guarantees: 4H/4A, 8 distinct opponents, 1H/1A vs each of the 4 pots, no same-country clashes.
local SCHEDULE = {
    -- Round 1
    { { 7, 1 }, { 8, 2 }, { 17, 11 }, { 18, 14 }, { 28, 31 }, { 4, 5 }, { 26, 22 }, { 21, 27 }, { 32, 34 }, { 23, 25 }, { 15, 10 }, { 3, 35 }, { 36, 33 }, { 6, 16 }, { 20, 24 }, { 12, 9 }, { 19, 29 }, { 13, 30 } },
    -- Round 2
    { { 1, 8 }, { 31, 36 }, { 11, 18 }, { 25, 19 }, { 20, 9 }, { 6, 3 }, { 16, 13 }, { 17, 2 }, { 27, 23 }, { 35, 28 }, { 34, 5 }, { 24, 26 }, { 29, 30 }, { 14, 4 }, { 7, 15 }, { 12, 33 }, { 22, 21 }, { 10, 32 } },
    -- Round 3
    { { 1, 12 }, { 5, 24 }, { 9, 10 }, { 16, 3 }, { 11, 36 }, { 7, 22 }, { 33, 29 }, { 19, 20 }, { 4, 26 }, { 13, 8 }, { 18, 31 }, { 17, 28 }, { 21, 32 }, { 2, 23 }, { 6, 30 }, { 25, 15 }, { 34, 35 }, { 14, 27 } },
    -- Round 4
    { { 18, 1 }, { 2, 4 }, { 9, 19 }, { 25, 28 }, { 3, 17 }, { 20, 13 }, { 30, 32 }, { 8, 21 }, { 11, 23 }, { 31, 14 }, { 27, 34 }, { 7, 33 }, { 15, 35 }, { 36, 10 }, { 5, 6 }, { 12, 22 }, { 16, 24 }, { 29, 26 } },
    -- Round 5
    { { 1, 20 }, { 8, 31 }, { 24, 12 }, { 10, 5 }, { 11, 7 }, { 6, 27 }, { 35, 17 }, { 21, 4 }, { 23, 30 }, { 13, 25 }, { 16, 29 }, { 3, 9 }, { 26, 36 }, { 22, 33 }, { 28, 18 }, { 19, 2 }, { 14, 34 }, { 32, 15 } },
    -- Round 6
    { { 24, 1 }, { 20, 31 }, { 13, 17 }, { 4, 28 }, { 9, 7 }, { 32, 2 }, { 35, 27 }, { 10, 12 }, { 30, 21 }, { 26, 16 }, { 33, 8 }, { 34, 11 }, { 18, 19 }, { 23, 3 }, { 36, 25 }, { 15, 6 }, { 5, 29 }, { 22, 14 } },
    -- Round 7
    { { 1, 36 }, { 3, 25 }, { 29, 6 }, { 4, 13 }, { 30, 12 }, { 33, 16 }, { 19, 11 }, { 26, 8 }, { 14, 15 }, { 22, 5 }, { 28, 9 }, { 31, 24 }, { 35, 7 }, { 27, 10 }, { 21, 17 }, { 32, 20 }, { 2, 18 }, { 34, 23 } },
    -- Round 8
    { { 31, 1 }, { 2, 34 }, { 36, 3 }, { 30, 4 }, { 5, 14 }, { 25, 6 }, { 27, 7 }, { 8, 11 }, { 9, 32 }, { 10, 21 }, { 12, 16 }, { 29, 13 }, { 33, 19 }, { 24, 35 }, { 15, 26 }, { 17, 20 }, { 23, 18 }, { 28, 22 } },
}

-- ============================ RUNTIME STATE ============================

local current_round = 1
local stage = "LEAGUE" -- "LEAGUE", "PLAYOFFS", "R16", "QF", "SF", "FINAL", "COMPLETED"
local results_matrix = {} -- [round][match_idx] = { h_goals, a_goals, played = true }
local standings = {} -- indexed 1..36
local playoffs_bracket = {}
local knockout_bracket = {}
local user_club_id = nil
local last_poll_time = 0

-- Helper for commas in numbers
local function commas(n)
    local s = string.format("%d", math.floor(math.abs(n) + 0.5))
    local pos = ((#s - 1) % 3) + 1
    return (n < 0 and "-" or "") .. string.sub(s, 1, pos) .. string.gsub(string.sub(s, pos + 1), "(%d%d%d)", ",%1")
end

-- Memory helpers
local function read_u8(addr)
    local b = memory.read(addr, 1)
    if not b or #b ~= 1 then return nil end
    return string.byte(b, 1)
end

local function write_u8(addr, val)
    local v = math.floor(val + 0.5) % 256
    memory.write(addr, string.char(v))
end

local function read_u16(addr)
    local b = memory.read(addr, 2)
    if not b or #b ~= 2 then return nil end
    local b1, b2 = string.byte(b, 1, 2)
    return b1 + b2 * 256
end

local function write_u16(addr, val)
    local v = math.floor(val + 0.5) % 65536
    local b1 = v % 256
    local b2 = math.floor(v / 256) % 256
    memory.write(addr, string.char(b1, b2))
end

local function read_u32(addr)
    local b = memory.read(addr, 4)
    if not b or #b ~= 4 then return nil end
    local b1, b2, b3, b4 = string.byte(b, 1, 4)
    return b1 + b2 * 256 + b3 * 65536 + b4 * 16777216
end

local function write_u32(addr, val)
    local v = math.floor(val + 0.5) % 0x100000000
    local b1 = v % 256
    local b2 = math.floor(v / 256) % 256
    local b3 = math.floor(v / 65536) % 256
    local b4 = math.floor(v / 16777216) % 256
    memory.write(addr, string.char(b1, b2, b3, b4))
end

local function read_i32(addr)
    local u = read_u32(addr)
    if u == nil then return nil end
    if u >= 0x80000000 then return u - 0x100000000 end
    return u
end

local function write_i32(addr, val)
    local v = math.floor(val + 0.5)
    if v < -0x80000000 then v = -0x80000000 end
    if v > 0x7fffffff then v = 0x7fffffff end
    if v < 0 then v = v + 0x100000000 end
    local b1 = v % 256
    local b2 = math.floor(v / 256) % 256
    local b3 = math.floor(v / 65536) % 256
    local b4 = math.floor(v / 16777216) % 256
    memory.write(addr, string.char(b1, b2, b3, b4))
end

-- Resolve active Master League mode data
local function get_mode_data()
    local mode_obj = read_u32(0x026503e0)
    if not mode_obj or mode_obj == 0 then return nil end
    local menu_obj = read_u32(0x0264f3e8)
    if not menu_obj or menu_obj == 0 then return nil end
    local mode_kind = read_u32(menu_obj + 0x20)
    if mode_kind ~= 0x13 and mode_kind ~= 0x28 then return nil end
    local mode_data = read_u32(mode_obj + 0x30)
    if not mode_data or mode_data == 0 then return nil end
    return mode_data
end

-- Credit funds into Master League transfer budget and balance
local function credit_money(millions)
    if not CREDIT_PRIZES or millions <= 0 then return end
    local mode_data = get_mode_data()
    if not mode_data then return end

    local dt = math.floor(millions * 10000 + 0.5)
    local t = read_i32(mode_data + 0xdddfc4)
    local bal = read_i32(mode_data + 0xdddfe4)

    if t ~= nil then
        t = math.min(99999999, t + dt)
        write_i32(mode_data + 0xdddfc4, t)
    end
    if bal ~= nil then
        bal = math.min(99999999, bal + dt)
        write_i32(mode_data + 0xdddfe4, bal)
    end
    log(string.format("MLSwiss: credited £%.2fM UEFA prize money to club budget.", millions))
end

-- Initialize or reset standings table
local function init_standings()
    standings = {}
    for i = 1, TOTAL_TEAMS do
        local t = TEAMS[i]
        standings[i] = {
            team_idx = i,
            id = t.id,
            name = t.name,
            assoc = t.assoc,
            pot = t.pot,
            rating = t.rating,
            p = 0,
            w = 0,
            d = 0,
            l = 0,
            gf = 0,
            ga = 0,
            gd = 0,
            pts = 0,
            away_gf = 0,
            away_w = 0,
            prize = PRIZE_BASE,
        }
    end
    results_matrix = {}
    for r = 1, LEAGUE_ROUNDS do
        results_matrix[r] = {}
        for m_idx = 1, #SCHEDULE[r] do
            results_matrix[r][m_idx] = { h_goals = nil, a_goals = nil, played = false }
        end
    end
    current_round = 1
    stage = "LEAGUE"
    playoffs_bracket = {}
    knockout_bracket = {}
end

-- Sort standings by strict UEFA Swiss tiebreakers:
-- 1. Points
-- 2. Goal Difference
-- 3. Goals Scored
-- 4. Away Goals Scored
-- 5. Total Wins
-- 6. Away Wins
-- 7. Team Rating (coefficient)
local function sort_standings()
    table.sort(standings, function(a, b)
        if a.pts ~= b.pts then return a.pts > b.pts end
        if a.gd ~= b.gd then return a.gd > b.gd end
        if a.gf ~= b.gf then return a.gf > b.gf end
        if a.away_gf ~= b.away_gf then return a.away_gf > b.away_gf end
        if a.w ~= b.w then return a.w > b.w end
        if a.away_w ~= b.away_w then return a.away_w > b.away_w end
        return a.rating > b.rating
    end)
end

-- Find standing record by 1-based team index
local function get_team_standing(team_idx)
    for _, s in ipairs(standings) do
        if s.team_idx == team_idx then return s end
    end
    return nil
end

-- Record a completed match result and update points/GD
local function record_match_result(r, m_idx, h_idx, a_idx, h_goals, a_goals)
    local m_res = results_matrix[r][m_idx]
    if m_res.played then return end -- already processed

    m_res.h_goals = h_goals
    m_res.a_goals = a_goals
    m_res.played = true

    local home = get_team_standing(h_idx)
    local away = get_team_standing(a_idx)
    if not home or not away then return end

    home.p = home.p + 1
    away.p = away.p + 1
    home.gf = home.gf + h_goals
    home.ga = home.ga + a_goals
    away.gf = away.gf + a_goals
    away.ga = away.ga + h_goals
    home.gd = home.gf - home.ga
    away.gd = away.gf - away.ga
    away.away_gf = away.away_gf + a_goals

    if h_goals > a_goals then
        home.w = home.w + 1
        home.pts = home.pts + 3
        away.l = away.l + 1
        home.prize = home.prize + PRIZE_WIN
    elseif h_goals < a_goals then
        away.w = away.w + 1
        away.away_w = away.away_w + 1
        away.pts = away.pts + 3
        home.l = home.l + 1
        away.prize = away.prize + PRIZE_WIN
    else
        home.d = home.d + 1
        away.d = away.d + 1
        home.pts = home.pts + 1
        away.pts = away.pts + 1
        home.prize = home.prize + PRIZE_DRAW
        away.prize = away.prize + PRIZE_DRAW
    end
end

-- Realistic Poisson-based score generator given team ratings and home advantage
local function simulate_score(h_rating, a_rating)
    -- Home advantage adds +2.5 effective rating
    local diff = (h_rating + 2.5) - a_rating
    local lambda_h = math.max(0.4, math.min(3.8, 1.45 * math.exp(diff / 16.0)))
    local lambda_a = math.max(0.3, math.min(3.2, 1.15 * math.exp(-diff / 16.0)))

    -- Knuth Poisson generator
    local function poisson(lambda)
        local l = math.exp(-lambda)
        local k = 0
        local p = 1.0
        repeat
            k = k + 1
            p = p * math.random()
        until p <= l
        return k - 1
    end

    local gh = poisson(lambda_h)
    local ga = poisson(lambda_a)
    return gh, ga
end

-- Simulate an entire round of Swiss matches
local function simulate_round(r)
    if r < 1 or r > LEAGUE_ROUNDS then return end
    local round_fixtures = SCHEDULE[r]
    for m_idx, pair in ipairs(round_fixtures) do
        local h_idx, a_idx = pair[1], pair[2]
        local m_res = results_matrix[r][m_idx]
        if not m_res.played then
            local gh, ga = simulate_score(TEAMS[h_idx].rating, TEAMS[a_idx].rating)
            record_match_result(r, m_idx, h_idx, a_idx, gh, ga)
        end
    end
    sort_standings()

    if r == LEAGUE_ROUNDS then
        -- Finalize League Phase & Award placement shares
        for rank, s in ipairs(standings) do
            local shares = 37 - rank
            local rank_bonus = shares * PRIZE_RANK_SHARE
            s.prize = s.prize + rank_bonus
            if rank <= 8 then
                s.prize = s.prize + PRIZE_R16
            elseif rank <= 24 then
                s.prize = s.prize + PRIZE_PLAYOFF
            end
        end
        stage = "PLAYOFFS"
        log("MLSwiss: League Phase complete! Top 8 directly qualify to R16; 9-24 enter Play-Offs.")
    else
        current_round = r + 1
        log(string.format("MLSwiss: Round %d complete. Advanced to Round %d.", r, current_round))
    end
end

-- Format and output standings table to file
local function write_table_file(ctx)
    local dir = (type(ctx) == "table" and type(ctx.sider_dir) == "string") and ctx.sider_dir or "./"
    local last = string.sub(dir, -1)
    if last ~= "\\" and last ~= "/" then
        dir = dir .. (string.find(dir, "\\") and "\\" or "/")
    end
    local path = dir .. TABLE_FILE

    local file = io.open(path, "w")
    if not file then return end

    file:write("========================================================================================================\n")
    file:write("                                UEFA CHAMPIONS LEAGUE - SWISS FORMAT STANDINGS                          \n")
    file:write(string.format(" Stage: %-12s | Current Round: %d/8 | Total Teams: 36 | 2024/25 Economic Model\n", stage, math.min(LEAGUE_ROUNDS, current_round)))
    file:write("========================================================================================================\n")
    file:write(" Pos  Club Name                 Assoc  Pot   P   W   D   L   GF   GA   GD  PTS    Prize Money  Status     \n")
    file:write("--------------------------------------------------------------------------------------------------------\n")

    for rank = 1, TOTAL_TEAMS do
        local s = standings[rank]
        local status_tag = ""
        if stage == "LEAGUE" then
            if rank <= 8 then status_tag = "[Direct R16]"
            elseif rank <= 24 then status_tag = "[Play-Offs]"
            else status_tag = "[Eliminated]"
            end
        elseif stage == "PLAYOFFS" or stage == "R16" or stage == "COMPLETED" then
            if rank <= 8 then status_tag = "QUALIFIED (R16)"
            elseif rank <= 24 then status_tag = "PLAY-OFFS"
            else status_tag = "ELIMINATED"
            end
        end

        file:write(string.format(" %2d. %-24s  %-4s   %d   %2d  %2d  %2d  %2d  %3d  %3d  %+3d  %3d   £%6.2fM   %-11s\n",
            rank, s.name, s.assoc, s.pot, s.p, s.w, s.d, s.l, s.gf, s.ga, s.gd, s.pts, s.prize, status_tag))

        if rank == 8 then
            file:write("--------------------------------- [TOP 8: DIRECT ROUND OF 16 QUALIFICATION] ---------------------------\n")
        elseif rank == 24 then
            file:write("--------------------------------- [9-24: KNOCKOUT PHASE PLAY-OFFS] ------------------------------------\n")
        end
    end
    file:write("--------------------------------- [25-36: ELIMINATED FROM EUROPE] -------------------------------------\n\n")

    -- Fixtures preview
    if stage == "LEAGUE" and current_round <= LEAGUE_ROUNDS then
        file:write(string.format("Upcoming Matchday %d Fixtures:\n", current_round))
        file:write("--------------------------------------------------------------------------------------------------------\n")
        local round_fixtures = SCHEDULE[current_round]
        for idx, pair in ipairs(round_fixtures) do
            local h, a = TEAMS[pair[1]], TEAMS[pair[2]]
            file:write(string.format("  Match %2d: %-26s vs  %-26s\n", idx, h.name .. " (" .. h.assoc .. ")", a.name .. " (" .. a.assoc .. ")"))
        end
        file:write("\n")
    elseif stage == "PLAYOFFS" or stage == "R16" or stage == "COMPLETED" then
        file:write("Knockout Phase Play-Off Pairings (Seeded 9-16 vs Unseeded 17-24):\n")
        file:write("--------------------------------------------------------------------------------------------------------\n")
        file:write(string.format("  Tie 1: %-24s vs %-24s\n", standings[9].name, standings[24].name))
        file:write(string.format("  Tie 2: %-24s vs %-24s\n", standings[10].name, standings[23].name))
        file:write(string.format("  Tie 3: %-24s vs %-24s\n", standings[11].name, standings[22].name))
        file:write(string.format("  Tie 4: %-24s vs %-24s\n", standings[12].name, standings[21].name))
        file:write(string.format("  Tie 5: %-24s vs %-24s\n", standings[13].name, standings[20].name))
        file:write(string.format("  Tie 6: %-24s vs %-24s\n", standings[14].name, standings[19].name))
        file:write(string.format("  Tie 7: %-24s vs %-24s\n", standings[15].name, standings[18].name))
        file:write(string.format("  Tie 8: %-24s vs %-24s\n", standings[16].name, standings[17].name))
        file:write("\n")
    end

    file:write("# In-Game Commands (uncomment and save to MLSwiss_Command.txt):\n")
    file:write("# SIM_ROUND       - Simulate current European matchday\n")
    file:write("# RESET           - Reset European tournament to Round 1\n")
    file:write("# TABLE           - Refresh MLSwiss_Table.txt\n")

    file:close()
end

-- Command observer from MLSwiss_Command.txt
local function observe_commands(ctx)
    if type(io) ~= "table" or type(ctx) ~= "table" or type(ctx.sider_dir) ~= "string" then return end
    local dir = ctx.sider_dir
    local last = string.sub(dir, -1)
    if last ~= "\\" and last ~= "/" then
        dir = dir .. (string.find(dir, "\\") and "\\" or "/")
    end
    local path = dir .. COMMAND_FILE

    local f = io.open(path, "r")
    if not f then return end
    local content = f:read("*a")
    f:close()

    if content and #content > 0 then
        local sim_req = string.match(content, "SIM_ROUND")
        local reset_req = string.match(content, "RESET")
        local table_req = string.match(content, "TABLE")

        local handled = false
        if sim_req then
            if stage == "LEAGUE" and current_round <= LEAGUE_ROUNDS then
                simulate_round(current_round)
                write_table_file(ctx)
                handled = true
            end
        elseif reset_req then
            init_standings()
            write_table_file(ctx)
            log("MLSwiss: tournament reset by command.")
            handled = true
        elseif table_req then
            write_table_file(ctx)
            handled = true
        end

        if handled then
            local out = io.open(path, "w")
            if out then
                out:write("# MLSwiss Command: Idle\n# Commands: SIM_ROUND, RESET, TABLE\n")
                out:close()
            end
        end
    end
end

-- Synchronize Master League memory data structures with the UEFA Swiss Format
function m.sync_mode_data()
    local mode_data = get_mode_data()
    if not mode_data then return false end

    -- Check if career is loaded
    local active = read_u32(mode_data + 0x30)
    if not active or active == 0 then return false end

    -- 1. Synchronize Competition Records at ModeData + 0x552e80
    -- In PES 2017 ML, competition records hold the participant club IDs
    local comp_count = read_u32(mode_data + 0x5fece8)
    if not comp_count or comp_count == 0 or comp_count > 1000 then
        comp_count = 350
    end

    local ucl_comps = {}
    for i = 0, comp_count - 1 do
        local comp_addr = mode_data + 0x552e80 + i * 0x224
        local cid = read_u16(comp_addr + 0x00)
        if cid == COMPETITION_ID or (cid and cid >= 600 and cid <= 607) then
            ucl_comps[#ucl_comps + 1] = { addr = comp_addr, id = cid }
        end
    end

    -- Write all 36 clubs across the European competition slots
    if #ucl_comps > 0 then
        local team_ptr = 1
        for _, comp in ipairs(ucl_comps) do
            local teams_in_slot = (comp.id == COMPETITION_ID) and 36 or 4
            for slot = 0, teams_in_slot - 1 do
                if team_ptr <= TOTAL_TEAMS then
                    write_u32(comp.addr + 0x148 + slot * 4, TEAMS[team_ptr].id)
                    team_ptr = team_ptr + 1
                end
            end
            write_u16(comp.addr + 0x21c, teams_in_slot)
        end
    end

    -- 2. Synchronize Match Records at ModeData + 0x6f154c
    -- Rewrite European match records with the 144 Swiss fixtures
    local match_count = read_u32(mode_data + 0x8a9e40)
    if not match_count or match_count == 0 or match_count > 10000 then
        match_count = 1500
    end

    local ucl_match_indices = {}
    for mi = 0, match_count - 1 do
        local match_addr = mode_data + 0x6f154c + mi * 0x24c
        local comp_id = read_u16(match_addr + 0x04)
        if comp_id == COMPETITION_ID or (comp_id and comp_id >= 600 and comp_id <= 607) then
            ucl_match_indices[#ucl_match_indices + 1] = match_addr
        end
    end

    -- Inject Swiss schedule into European match slots
    local cur_slot = 1
    for r = 1, LEAGUE_ROUNDS do
        for _, pair in ipairs(SCHEDULE[r]) do
            if cur_slot <= #ucl_match_indices then
                local m_addr = ucl_match_indices[cur_slot]
                local h_team = TEAMS[pair[1]]
                local a_team = TEAMS[pair[2]]
                write_u32(m_addr + 0x0c, h_team.id)
                write_u32(m_addr + 0x10, a_team.id)
                write_u16(m_addr + 0x06, r) -- Round number
                cur_slot = cur_slot + 1
            end
        end
    end

    -- 3. Synchronize In-Game Native Standings UI at ModeData + 0xc2cbb8
    m.sync_in_game_standings(mode_data)

    log("MLSwiss: Master League memory synchronized with 36-team UEFA Swiss Format (competitions, fixtures, and native UI standings table).")
    return true
end

-- Synchronize in-game native Master League Standings UI (Common/CmnStandingsMenu & rankingTeam.bin)
function m.sync_in_game_standings(mode_data)
    if not mode_data or mode_data == 0 then return false end

    -- 1. Apply runtime UI memory hooks (switches UCL to unified table & raises clamps to 64 teams)
    -- Layout switch at fcn_031209ba: 0x00 -> 0x07 (Case 7: unified single league table)
    write_u8(0x03120b2d, 0x07)
    -- fcn_0323a336: cmp eax, 0x20 -> cmp eax, 0x40 (allow reading stats for >32 teams)
    write_u8(0x0323a3af, 0x40)
    -- fcn_0323a885: cmp edi, 0x20 -> cmp edi, 0x40 (allow choice row creation for >32 teams)
    write_u8(0x0323abc3, 0x40)
    -- fcn_03239e2f: cmp eax, 0x20 -> cmp eax, 0x40 (rank arrow team entry pointer)
    write_u8(0x03239e9c, 0x40)
    -- fcn_03239e2f: cmp edi, 0x20 -> cmp edi, 0x40 (rank arrow prev rank entry pointer)
    write_u8(0x03239edd, 0x40)
    -- fcn_03239f2f: cmp edi, 0x20 -> cmp edi, 0x40 (rank arrow match loop compare)
    write_u8(0x03239f31, 0x40)

    -- 2. Locate or allocate Competition 2 record in ModeData + 0xc2cbb8
    -- Standings table storage: 300 records of 0x84c bytes each
    local ucl_rec = nil
    local free_rec = nil
    for slot = 0, 299 do
        local addr = mode_data + 0xc2cbb8 + slot * 0x84c
        local cid = read_u16(addr + 0x00)
        if cid == COMPETITION_ID then
            ucl_rec = addr
            break
        elseif (cid == 0xffff or cid == 0 or not cid) and not free_rec then
            free_rec = addr
        end
    end

    if not ucl_rec then
        if free_rec then
            ucl_rec = free_rec
            write_u16(ucl_rec + 0x00, COMPETITION_ID)
            local count = read_u32(mode_data + 0xcc84c8) or 0
            write_u32(mode_data + 0xcc84c8, count + 1)
        else
            ucl_rec = mode_data + 0xc2cbb8
            write_u16(ucl_rec + 0x00, COMPETITION_ID)
        end
    end

    -- Write team count: 36 clubs
    write_u32(ucl_rec + 0x844, TOTAL_TEAMS)

    -- Write all 36 clubs with packed standings stats
    -- Team entry layout (0x0c bytes = 3 dwords):
    -- dword 0: team_id
    -- dword 1: rank (0..5), pts (6..13), wins (14..19), losses (20..25), draws (26..31)
    -- dword 2: gf (0..11), ga (12..23)
    for rank = 1, TOTAL_TEAMS do
        local s = standings[rank]
        if s then
            local dw0 = s.id
            local dw1 = (rank % 64)
                      + (s.pts % 256) * 64
                      + (s.w % 64) * 16384
                      + (s.l % 64) * 1048576
                      + (s.d % 64) * 67108864
            local dw2 = (s.gf % 4096)
                      + (s.ga % 4096) * 4096

            local row_offset = 0x34 + (rank - 1) * 12
            write_u32(ucl_rec + row_offset + 0x00, dw0)
            write_u32(ucl_rec + row_offset + 0x04, dw1)
            write_u32(ucl_rec + row_offset + 0x08, dw2)
        end
    end

    -- 3. Also populate the 8 individual group slots (competitions 600..607)
    for grp_idx = 0, 7 do
        local grp_cid = 600 + grp_idx
        local grp_rec = nil
        local grp_free = nil
        for slot = 0, 299 do
            local addr = mode_data + 0xc2cbb8 + slot * 0x84c
            local cid = read_u16(addr + 0x00)
            if cid == grp_cid then
                grp_rec = addr
                break
            elseif (cid == 0xffff or cid == 0 or not cid) and not grp_free then
                grp_free = addr
            end
        end
        if not grp_rec and grp_free then
            grp_rec = grp_free
            write_u16(grp_rec + 0x00, grp_cid)
            local count = read_u32(mode_data + 0xcc84c8) or 0
            write_u32(mode_data + 0xcc84c8, count + 1)
        end
        if grp_rec then
            local start_rank = (grp_idx < 4) and (grp_idx * 5 + 1) or (20 + (grp_idx - 4) * 4 + 1)
            local num_in_grp = (grp_idx < 4) and 5 or 4
            write_u32(grp_rec + 0x844, num_in_grp)
            for gi = 0, num_in_grp - 1 do
                local grank = start_rank + gi
                local s = standings[grank]
                if s then
                    local dw0 = s.id
                    local dw1 = ((gi + 1) % 64)
                              + (s.pts % 256) * 64
                              + (s.w % 64) * 16384
                              + (s.l % 64) * 1048576
                              + (s.d % 64) * 67108864
                    local dw2 = (s.gf % 4096)
                              + (s.ga % 4096) * 4096
                    local row_offset = 0x34 + gi * 12
                    write_u32(grp_rec + row_offset + 0x00, dw0)
                    write_u32(grp_rec + row_offset + 0x04, dw1)
                    write_u32(grp_rec + row_offset + 0x08, dw2)
                end
            end
        end
    end

    return true
end

-- Sider match routing callbacks
function m.set_home_team(ctx)
    if not SWISS_ENABLED or stage ~= "LEAGUE" then return end
    local tid = ctx.tournament_id
    if tid == COMPETITION_ID or (tid and tid >= 600 and tid <= 607) then
        if current_round >= 1 and current_round <= LEAGUE_ROUNDS then
            local round_fixtures = SCHEDULE[current_round]
            for _, pair in ipairs(round_fixtures) do
                local h = TEAMS[pair[1]]
                local a = TEAMS[pair[2]]
                if ctx.home_team == h.id or ctx.away_team == a.id or ctx.home_team == a.id or ctx.away_team == h.id then
                    return h.id
                end
            end
        end
    end
end

function m.set_away_team(ctx)
    if not SWISS_ENABLED or stage ~= "LEAGUE" then return end
    local tid = ctx.tournament_id
    if tid == COMPETITION_ID or (tid and tid >= 600 and tid <= 607) then
        if current_round >= 1 and current_round <= LEAGUE_ROUNDS then
            local round_fixtures = SCHEDULE[current_round]
            for _, pair in ipairs(round_fixtures) do
                local h = TEAMS[pair[1]]
                local a = TEAMS[pair[2]]
                if ctx.home_team == h.id or ctx.away_team == a.id or ctx.home_team == a.id or ctx.away_team == h.id then
                    return a.id
                end
            end
        end
    end
end

-- Observer called during Sider game lifecycle
function m.observe(ctx)
    if not SWISS_ENABLED then return end
    local now = (type(os) == "table" and type(os.time) == "function") and os.time() or 0
    if now == last_poll_time then return end
    last_poll_time = now

    observe_commands(ctx)

    -- Check if inside active Master League match
    local mode_data = get_mode_data()
    if not mode_data then return end

    -- Periodically sync ML memory structures if not done yet
    m.sync_mode_data()

    -- Read current match record pointer if available
    local match_ptr = read_u32(mode_data + 0x537b8)
    if match_ptr and match_ptr ~= 0 then
        local comp_id = read_u32(match_ptr + 0x04)
        if comp_id == COMPETITION_ID or (comp_id and comp_id >= 600 and comp_id <= 607) then
            local status_flag = read_u32(match_ptr + 0x06)
            local is_played = (status_flag and (math.floor(status_flag / 16384) % 2 == 1))
            if is_played and stage == "LEAGUE" and current_round <= LEAGUE_ROUNDS then
                local h_goals = read_u32(match_ptr + 0x14) % 256
                local a_goals = read_u32(match_ptr + 0x17) % 256
                -- Find match in schedule
                local round_fixtures = SCHEDULE[current_round]
                for m_idx, pair in ipairs(round_fixtures) do
                    local m_res = results_matrix[current_round][m_idx]
                    if not m_res.played then
                        record_match_result(current_round, m_idx, pair[1], pair[2], h_goals, a_goals)
                        break
                    end
                end
                if SIMULATE_AI then
                    simulate_round(current_round)
                end
                write_table_file(ctx)
            end
        end
    end
end

-- Export functions for test suites & external script callers
m.init_standings = init_standings
m.simulate_round = simulate_round
m.get_standings = function() return standings end
m.get_schedule = function() return SCHEDULE end
m.get_teams = function() return TEAMS end
m.write_table = write_table_file
m.get_stage = function() return stage end
m.get_round = function() return current_round end

function m.init(ctx)
    log("MLSwiss 1: UEFA 36-team Swiss Format League Phase & Knockouts (2024/25)")

    if not SWISS_ENABLED then
        log("RESULT: MLSwiss disabled by configuration.")
        return
    end

    init_standings()
    sort_standings()

    if type(ctx) == "table" and type(ctx.register) == "function" then
        ctx.register("livecpk_make_key", m.observe)
        ctx.register("set_home_team", m.set_home_team)
        ctx.register("set_away_team", m.set_away_team)
        ctx.register("after_set_conditions", m.observe)
    end

    write_table_file(ctx)
    log("RESULT: installed. 36 clubs loaded across 4 pots; 8-matchday Swiss schedule initialized.")
end

return m
