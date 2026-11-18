-- MLTeamSpirit.lua, version 4: Team Spirit follows your club's form
-- (Sider Lua module). Made for PES2017.exe sha256 44b0caaa...
--
-- What the game does (MASTER_LEAGUE.md, section 12): in a played match every player of
-- YOUR club has a Team Spirit value of 1 to 99, and 22 of his abilities are multiplied by
-- 0.70 (value 10 or less) to 1.00 (value 99). A player of a computer club always has 99.
-- A skipped match does not read Team Spirit at all. So the value only ever makes your own
-- team worse, and only when you play. Version 1 of this module answered 99 for your players
-- too, which switches the effect off. Version 2 answers a value of the club's own, 90 to 99:
-- the effect is there, but it never bites, and it moves with what the club is doing.
-- Version 3 fixes Sider team IDs, date widths and the final table batches.
-- Version 4 finds the primary controlled club in the career, not the invalid-ID placeholder.
--
-- Where the number comes from: the match records of the career (mode data +0x6f154c,
-- 9,000 records of 0x24c bytes, section 5). Every match your club has played is in there
-- with its date, its competition, its round and its score, so the last five results, the
-- stage of the cup and the places in the league are all read, not guessed. Nothing is
-- stored in the game: the walk over the records runs once when a match is set up.
--
-- The rules (all of them are settings below, and every one that fires is written to
-- sider.log with the value it led to):
--
--   the last five matches, most recent first with the weights 3, 2, 2, 1, 1:
--       a win raises the value, a loss lowers it, a draw does neither;
--   two losses one after the other: at most 92;
--   three wins one after the other or more: at least 98;
--   the last round of a cup: 99; the round before it: +2;
--   a rival of your club (the three the club record names at +0x514): +2;
--   a league match between two of the best four, or two of the worst three: +2;
--   never below 90, never above 99.
--
-- What it changes, in the running game only (no file is touched): twelve bytes of the
-- function that gives a player his value, fcn_038df4c9, at the head of the branch only a
-- player of your club goes into (0x038df6c1; version 1 jumped a little earlier, at
-- 0x038df528). In their place: "the value is this byte", then the function's own way out,
-- the same three pops the branch would have done. One byte of that, the value itself, is
-- written again before every match. No new memory is used, no cave, no code of our own in
-- the game: the number is the only thing that moves.
--
-- Every other player, every other mode and every skipped match are exactly as the game
-- makes them: the branch we change is the one the game reaches only in Master League for a
-- player it has found to be one of yours.
--
-- It first checks that the game holds the expected code at the place. If it differs it
-- writes nothing and says so in sider.log.
--
-- Install: copy this file into the "modules" folder next to sider.exe and add
--     lua.module = "MLTeamSpirit.lua"
-- to sider.ini, above or below the other lines. Remove the line to get Team Spirit back.
-- It needs no other module, and no other module needs it.
--
-- How to see it working in a career (section "Verification" of sider/README.md):
--   1. after a match is set up, sider.log has one line for it: the two clubs, the
--      competition and round, the last results, which rules fired, and the value;
--   2. on the game plan screen of your club, Team Spirit reads that value. Lose two in a
--      row: it should read 92. Reach a cup final: 99.
--
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, tonumber, type,
-- tostring.

local m = {}

-- ============================ settings ============================
-- The rules the value comes from. Nothing else has to be changed to tune it.

local BASE = 95             -- the value when nothing about the club is known
local FLOOR = 90            -- never below this
local CEILING = 99          -- never above this

local FORM_MATCHES = 5      -- how many of the club's last matches are looked at
local FORM_WEIGHTS = { 3, 2, 2, 1, 1 }   -- most recent first; a draw counts for nothing
local FORM_SCALE = 0.4      -- nine form points (five wins) raise the value by four

local TWO_LOSS_CAP = 92     -- two losses one after the other: no more than this
local WIN_RUN = 3           -- this many wins one after the other ...
local WIN_RUN_VALUE = 98    -- ... give at least this

local FINAL_VALUE = 99      -- the last round of a cup
local CUP_NEAR_BONUS = 2    -- the round before the last one of a cup
local DERBY_BONUS = 2       -- one of the three clubs your club record names as rivals
local BIG_MATCH_BONUS = 2   -- a league match of two of the best four or the worst three
local BIG_TOP = 4           -- how many places are "the top" of a league
local BIG_BOTTOM = 3        -- how many are "the bottom"

local RIVALS = {}           -- packed career club ids, for a derby the game does not name.
                            -- Copy the opponent's "RIVALS id" from sider.log, not its Sider team number.

local SEASON = 372          -- date-key stride above day 364, not an elapsed-day counter

-- ============================ the game ============================
-- Addresses of MASTER_LEAGUE.md; the exe is not relocated, so they hold in the game.

local MODE_OBJECT_AT = 0x026503e0   -- pointer to the mode object; its +0x30 is the mode data
local SELECTOR_AT = 0x0264f3e8      -- pointer to the menu; its +0x20 is the number of the mode
local MODE_KIND_TAB = 0x0251d408    -- kind of a mode number: 12 is Master League
local MASTER_LEAGUE = 12

local MATCHES_AT = 0x6f154c         -- 9,000 match records of 0x24c bytes
local MATCH_STRIDE = 0x24c
local MATCH_COUNT = 9000
local M_FREE = 0x00                 -- u16, 0xffff is a free place
local M_COMP = 0x04                 -- u16, the competition
local M_FLAGS = 0x06                -- u16: bits 0-11 the round, bit 14 "has been played"
local M_HOME = 0x0c                 -- u32, the first club
local M_AWAY = 0x10                 -- u32, the second club
local M_DATE = 0x08                 -- u16 year, then month, then day (a date, section 2.2)
local M_GOAL1 = 0x14                -- u8, goals of the club at +0x0c
local M_GOAL2 = 0x17                -- u8, goals of the club at +0x10

local COMPETITIONS_AT = 0x552e80    -- 300 competition records of 0x224 bytes
local COMP_STRIDE = 0x224
local COMP_COUNT_AT = 0x5fece8      -- how many of them are in use
local C_KIND = 0x5c                 -- 1 a league, 3 and 4 the cups

local CLUBS_AT = 0x481be0           -- the club records, 0x520 bytes each; count at +0x5fece0
local CLUB_STRIDE = 0x520
local CLUB_COUNT_AT = 0x5fece0
local CLUB_LIMIT = 651              -- shortcut: saved-career slots; fail closed beyond these
local CLUB_CONTROL = 0x314           -- (dword >> 7) & 255: primary user 0, AI 255
local CLUB_RIVALS = 0x514           -- three club ids, the rivals (fcn_035f5c69)

local TODAY_AT = 0xc2cbb0           -- u16, the day of the year, 0 to 364
local YEAR_AT = 0xc2cbb2            -- u16, the year

-- The place that is changed. Twelve bytes at the head of the Master League branch:
--   mov eax, [ebp + 0x24] / fld dword [ebp - 0x10] / mov ecx, [ebp + 0x20]
-- become
--   mov eax, <value> / pop ebx / pop edi / jmp 0x038df7a5
-- and 0x038df7a5 is the tail of the function's own way out (pop esi, mov esp, ebp,
-- pop ebp, ret), which is what every other way to the end of the function runs through.
-- The branch pushed ebx at 0x038df527 and the prologue pushed esi and edi, so the three
-- pops are the ones the branch owed, in its order. The value goes into the whole of eax,
-- not only into al, because a caller may take more than the low byte of it.
local PLACE = 0x038df6c1
local OLD = "8b4524d985f0ffffff8b4d20"
local VALUE_AT = 0x038df6c2         -- the one byte that changes from match to match
-- The place version 1 changed, five bytes above the branch. It has to be left alone:
-- with the jump of version 1 in it, no player ever reaches the branch.
local OLD_PLACE, OLD_VANILLA = 0x038df528, "e8b8cbf3ff"
local LAYOUT_CHECKS = {
    { 0x0381e39c, "8b9614030000c1ea073a550f" }, -- field read beyond Transfers' hooked entry
    { 0x03822433, "5589e583ec085689ce8b86e0ec5f0069c020050000578b7d08578d8c30e01b4800" },
}

local BEFORE_MONTH = { 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334 }

-- ============================ small helpers ============================

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

local function byte(s, i)
    return string.byte(s, i) or 0
end

local function u16(s, i)
    local a, b = string.byte(s, i, i + 1)
    return (a or 0) + (b or 0) * 256
end

local function u32(s, i)
    local a, b, c, d = string.byte(s, i, i + 3)
    return (a or 0) + (b or 0) * 256 + (c or 0) * 65536 + (d or 0) * 16777216
end

-- Decode packed game/RIVALS ids to the 16-bit team numbers Sider publishes.
local function key_of(id)
    if type(id) ~= "number" or id == 0xffffffff then return nil end
    return math.floor(id / 16384) % 65536
end

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

-- A dword at a fixed address, or nil when Sider cannot read it. Reads of the game's own
-- data are checked first: an address that is not a good one is not read.
local function dword_at(addr)
    local s = memory.read(addr, 4)
    if type(s) ~= "string" or #s < 4 then return nil end
    return u32(s, 1)
end

local function pointer_at(addr)
    local v = dword_at(addr)
    if v == nil or v < 0x10000 or v > 0x7fff0000 then return nil end
    return v
end

-- The mode data, the block every offset of the career is inside, or nil.
local function mode_data()
    local object = pointer_at(MODE_OBJECT_AT)
    if object == nil then return nil end
    return pointer_at(object + 0x30)
end

-- Resolve afresh on both callbacks; an unknown/ambiguous controller must never become an AI club.
local function primary_club(base)
    local layout = dword_at(base + 0xec1408)
    if layout == nil or layout == 2 then return nil end
    local count = dword_at(base + CLUB_COUNT_AT)
    if count == nil or count < 1 or count > CLUB_LIMIT then return nil end
    local found = nil
    for first = 0, count - 1, 8 do
        local n = math.min(8, count - first)
        local blob = memory.read(base + CLUBS_AT + first * CLUB_STRIDE, n * CLUB_STRIDE)
        if type(blob) ~= "string" or #blob ~= n * CLUB_STRIDE then return nil end
        for i = 0, n - 1 do
            local at = i * CLUB_STRIDE + 1
            local id = u32(blob, at)
            if id ~= 0xffffffff and math.floor(u32(blob, at + CLUB_CONTROL) / 128) % 256 == 0 then
                local key = key_of(id)
                if found ~= nil or key == nil or key == 0 or key == 65535 then return nil end
                found = id
            end
        end
    end
    return found
end

-- The kind of the mode that is running: 12 is Master League (section 2.1).
local function mode_kind()
    local selector = pointer_at(SELECTOR_AT)
    if selector == nil then return nil end
    local number = dword_at(selector + 0x20)
    if number == nil or number > 69 then return nil end
    return dword_at(MODE_KIND_TAB + number * 4)
end

-- The day of the career as one number: year * 372 + day of the year.
local function day_key(year, month, day)
    if type(year) ~= "number" or type(month) ~= "number" or type(day) ~= "number" then return nil end
    if month < 1 or month > 12 or day < 1 or day > 31 then return nil end
    return year * SEASON + BEFORE_MONTH[month] + day - 1
end

-- ============================ the walk over the match records ============================

-- One walk over the 9,000 records, reading them in blocks of 32.
--   base  = the mode data
--   club  = the key of our club (nil when it is not known)
--   comp  = the competition of the match about to be played (nil when it is not known)
--   now   = the day of the career, or nil
-- Answers:
--   ours       every played match of our club, as { date, gf, ga, comp, round, opp }
--   theirs     every record of `comp`, as { date, round, home, away, g1, g2, played }
--   top_round  the highest round `comp` has, and the one below it (a cup's are the same
--               every season: the whole cup is written into the records when it is made)
--   rivals     the three clubs our club record names, as keys (nil when it does not)
local function walk(base, club, comp, now)
    local ours, theirs, top_round, near_round = {}, {}, nil, nil
    local addr, stride, per = base + MATCHES_AT, MATCH_STRIDE, 32
    for first = 0, MATCH_COUNT - 1, per do
        local count = math.min(per, MATCH_COUNT - first)
        local blob = memory.read(addr + first * stride, count * stride)
        if type(blob) ~= "string" or #blob < count * stride then break end
        for i = 0, count - 1 do
            local at = i * stride + 1                       -- 1-based, as Lua wants it
            if u16(blob, at + M_FREE) ~= 0xffff then        -- a match, not a free place
                local home, away = u32(blob, at + M_HOME), u32(blob, at + M_AWAY)
                local flags = u16(blob, at + M_FLAGS)
                local round = flags % 0x1000                 -- bits 0 to 11
                local played = (math.floor(flags / 0x4000) % 2) == 1     -- bit 14
                local this = u16(blob, at + M_COMP)
                local date = day_key(u16(blob, at + M_DATE), byte(blob, at + M_DATE + 2),
                                     byte(blob, at + M_DATE + 3))
                if this == comp then
                    theirs[#theirs + 1] = {
                        date = date,
                        round = round,
                        home = key_of(home), away = key_of(away),
                        g1 = byte(blob, at + M_GOAL1), g2 = byte(blob, at + M_GOAL2),
                        played = played,
                    }
                    if top_round == nil or round > top_round then
                        near_round, top_round = top_round, round
                    elseif round < top_round and (near_round == nil or round > near_round) then
                        near_round = round          -- the rounds of a cup are not all neighbours
                    end
                end
                if played and club ~= nil and date ~= nil and (now == nil or date <= now) then
                    local one, two = key_of(home), key_of(away)
                    local gf, ga, opp
                    if one == club then gf, ga, opp = byte(blob, at + M_GOAL1), byte(blob, at + M_GOAL2), two
                    elseif two == club then gf, ga, opp = byte(blob, at + M_GOAL2), byte(blob, at + M_GOAL1), one
                    end
                    if gf ~= nil then
                        ours[#ours + 1] = {
                            date = date,
                            gf = gf, ga = ga, comp = this, round = round, opp = opp,
                        }
                    end
                end
            end
        end
    end
    table.sort(ours, function(a, b) return a.date > b.date end)
    return ours, theirs, top_round, near_round
end

-- The three clubs our club record names as rivals, as a set of keys. The club table is
-- walked by id, which is what the game's own look-up does in the end; a club that is not
-- in it, or a record that names no rival, leaves the set empty, and a derby then is a
-- club of RIVALS at most.
local function rivals_of(base, club)
    local set = {}
    for _, id in ipairs(RIVALS) do
        local k = key_of(id)
        if k ~= nil then set[k] = true end
    end
    if club == nil then return set end
    local count = dword_at(base + CLUB_COUNT_AT)
    if count == nil or count < 1 or count > CLUB_LIMIT then return set end
    local addr, stride, per = base + CLUBS_AT, CLUB_STRIDE, 8
    for first = 0, count - 1, per do
        local n = math.min(per, count - first)
        local blob = memory.read(addr + first * stride, n * stride)
        if type(blob) ~= "string" or #blob < n * stride then break end
        for i = 0, n - 1 do
            if key_of(u32(blob, i * stride + 1)) == club then
                for r = 0, 2 do
                    local id = u32(blob, i * stride + 1 + CLUB_RIVALS + r * 4)
                    if id ~= 0xffffffff then
                        local k = key_of(id)
                        if k ~= nil then set[k] = true end
                    end
                end
                return set
            end
        end
    end
    return set
end

-- The kind of a competition: 1 a league, 3 and 4 the cups (section 5.1). `comp` is the
-- number the match records carry in their +0x04, and it is the number in +0x00 of the
-- competition record, not the place of that record in the table: the game answers a
-- competition by walking the table and comparing that number (fcn_03822ab9), so this
-- walks it the same way. A competition the table does not hold, or a kind it does not
-- hold, is answered as nil, and the cup rules then do not fire.
local function kind_of(base, comp)
    if comp == nil then return nil end
    local count = dword_at(base + COMP_COUNT_AT)
    if count == nil or count < 1 or count > 300 then return nil end
    local addr, stride, per = base + COMPETITIONS_AT, COMP_STRIDE, 16
    for first = 0, count - 1, per do
        local n = math.min(per, count - first)
        local blob = memory.read(addr + first * stride, n * stride)
        if type(blob) ~= "string" or #blob < n * stride then break end
        for i = 0, n - 1 do
            if u16(blob, i * stride + 1) == comp then            -- +0x00: its own number
                local kind = byte(blob, i * stride + 1 + C_KIND)
                if kind >= 1 and kind <= 5 then return kind end
                return nil
            end
        end
    end
    return nil
end

-- The places in a league: how many points every club of `theirs` has this season. A
-- season starts with the newest first round in the records, so last season's matches
-- are not counted; a match that has not been played does not count either.
local function places(theirs, now)
    local first = nil
    for _, m in ipairs(theirs) do
        if m.round == 0 and m.date ~= nil and (now == nil or m.date <= now)
           and (first == nil or m.date > first) then
            first = m.date
        end
    end
    local rows = {}
    for _, m in ipairs(theirs) do
        if m.played and m.date ~= nil and (now == nil or m.date <= now)
           and (first == nil or m.date >= first) then
            for side = 1, 2 do
                local k = (side == 1) and m.home or m.away
                if k ~= nil then
                    local row = rows[k]
                    if row == nil then row = { pts = 0, played = 0, gf = 0, ga = 0 } rows[k] = row end
                    local gf, ga = m.g1, m.g2
                    if side == 2 then gf, ga = m.g2, m.g1 end
                    row.played = row.played + 1
                    row.gf, row.ga = row.gf + gf, row.ga + ga
                    if gf > ga then row.pts = row.pts + 3 elseif gf == ga then row.pts = row.pts + 1 end
                end
            end
        end
    end
    local order = {}
    for k, row in pairs(rows) do order[#order + 1] = { key = k, pts = row.pts, gf = row.gf, ga = row.ga } end
    table.sort(order, function(a, b)
        if a.pts ~= b.pts then return a.pts > b.pts end
        if a.gf - a.ga ~= b.gf - b.ga then return a.gf - a.ga > b.gf - b.ga end
        return a.gf > b.gf
    end)
    local place = {}
    for i, row in ipairs(order) do place[row.key] = i end
    return place, #order
end

-- ============================ the rules ============================

-- The value, and the rules that fired. `ours` is newest first.
local function value_of(ours, facts)
    local why, v = {}, BASE

    -- form: the last five matches, most recent first
    local form = 0
    for i = 1, FORM_MATCHES do
        local m, w = ours[i], FORM_WEIGHTS[i]
        if m == nil or w == nil then break end
        if m.gf > m.ga then form = form + w elseif m.gf < m.ga then form = form - w end
    end
    if form ~= 0 then
        local step = clamp(form * FORM_SCALE, -9, 9)
        v = v + step
        why[#why + 1] = string.format("form %+d (%+d)", form, step)
    end

    -- two losses one after the other
    if ours[1] ~= nil and ours[2] ~= nil and ours[1].gf < ours[1].ga and ours[2].gf < ours[2].ga then
        if v > TWO_LOSS_CAP then
            why[#why + 1] = string.format("two losses (%d to %d)", v, TWO_LOSS_CAP)
            v = TWO_LOSS_CAP
        end
    end

    -- a run of wins
    local run = 0
    while ours[run + 1] ~= nil and ours[run + 1].gf > ours[run + 1].ga do run = run + 1 end
    if run >= WIN_RUN and v < WIN_RUN_VALUE then
        why[#why + 1] = string.format("%d wins in a row (%d to %d)", run, v, WIN_RUN_VALUE)
        v = WIN_RUN_VALUE
    end

    -- the stage of a cup
    if facts.cup and facts.round ~= nil and facts.top ~= nil then
        if facts.round >= facts.top then
            why[#why + 1] = string.format("final (%d)", FINAL_VALUE)
            v = FINAL_VALUE
        elseif facts.near ~= nil and facts.round >= facts.near then
            why[#why + 1] = string.format("last but one round (+%d)", CUP_NEAR_BONUS)
            v = v + CUP_NEAR_BONUS
        end
    end

    -- a derby
    if facts.derby then
        why[#why + 1] = string.format("derby (+%d)", DERBY_BONUS)
        v = v + DERBY_BONUS
    end

    -- a league match at the top or at the bottom
    if facts.big then
        why[#why + 1] = string.format("big match (+%d)", BIG_MATCH_BONUS)
        v = v + BIG_MATCH_BONUS
    end

    local was = v
    v = clamp(math.floor(v + 0.5), FLOOR, CEILING)
    if v ~= was then why[#why + 1] = string.format("kept inside %d to %d (%d to %d)", FLOOR, CEILING, was, v) end
    return v, why
end

-- One line about the last matches: "W D L W W".
local function form_text(ours)
    local t = {}
    for i = 1, FORM_MATCHES do
        local m = ours[i]
        if m == nil then break end
        t[i] = (m.gf > m.ga) and "W" or ((m.gf == m.ga) and "D" or "L")
    end
    return #t > 0 and table.concat(t, " ") or "none"
end

-- ============================ one match ============================

local said, last_value, last_line = {}, nil, nil     -- logged once, the value, the last line

local function say_once(what)
    if said[what] then return false end
    said[what] = true
    return true
end

-- The value for the match Sider is telling us about, written to the byte in the patch.
function m.set_conditions(ctx)
    if last_value == nil then return end                     -- nothing was installed
    if mode_kind() ~= MASTER_LEAGUE then
        if say_once("mode") then log("MLTeamSpirit 4: no career of your own in this mode; nothing changed") end
        return
    end
    local base = mode_data()
    if base == nil then
        if say_once("mode data") then log("MLTeamSpirit 4: the mode data cannot be read; the value stays where it is") end
        return
    end

    local home = tonumber(ctx and ctx.home_team)
    local away = tonumber(ctx and ctx.away_team)
    local ours_id = primary_club(base)
    if ours_id == nil then
        if say_once("user club") then log("MLTeamSpirit 4: primary controlled club unavailable or ambiguous; "
            .. "the value stays where it is") end
        return
    end
    local club = key_of(ours_id)
    local opp, home_side = nil, nil
    if club ~= nil then
        if home == club then opp, home_side = away, true
        elseif away == club then opp, home_side = home, false
        end
    end
    if opp == nil then
        -- not a match of your club (or the club is not known): the value stays as it is
        if home ~= nil and away ~= nil and say_once("not ours") then
            log(string.format("MLTeamSpirit 4: no match of your club (yours %s, home %s, away %s); "
                .. "the value stays where it is", tostring(ours_id), tostring(home), tostring(away)))
        end
        return
    end

    -- The competition and the round: from the record of the match, when Sider's match_id
    -- is the number of one (match_record, fcn_03822b3f: the mode data + 0x6f154c + the
    -- number times 0x24c, and the record answers with that number in its own +0x00).
    -- Sider's tournament_id is another thing: the game makes it from the competition of
    -- the match with a table of 282 competition numbers (fcn_04062701), so it is a number
    -- of its own (11 to 159, 159 when the competition is not in the table) and not one
    -- the match records carry. So the number of the competition is taken from the record,
    -- or left unknown, and when it is unknown no cup rule fires.
    local comp, round = nil, nil
    local record = tonumber(ctx and ctx.match_id)
    if record ~= nil and record >= 0 and record < MATCH_COUNT then
        local s = memory.read(base + MATCHES_AT + record * MATCH_STRIDE, 0x18)
        if type(s) == "string" and #s >= 0x18 and u16(s, 1 + M_FREE) ~= 0xffff then
            local one, two = key_of(u32(s, 1 + M_HOME)), key_of(u32(s, 1 + M_AWAY))
            if (one == club and two == opp) or (two == club and one == opp) then
                comp, round = u16(s, 1 + M_COMP), u16(s, 1 + M_FLAGS) % 0x1000
            elseif say_once("match_id") then
                log(string.format("MLTeamSpirit 4: match_id %d is not this match; the round of a cup "
                    .. "is not known, so the cup rules do not fire", record))
            end
        end
    end

    local now = nil
    local date = memory.read(base + TODAY_AT, YEAR_AT - TODAY_AT + 2)
    if type(date) == "string" and #date == 4 then now = u16(date, 3) * SEASON + u16(date, 1) end

    local ours, theirs, top, near = walk(base, club, comp, now)
    local kind = kind_of(base, comp)

    -- a derby: one of the three clubs the club record names, or one of RIVALS
    local rival_set = rivals_of(base, club)
    local derby = rival_set[opp] == true

    -- a big league match: two of the best four, or two of the worst three
    local big = false
    local place, teams = places(theirs, now)
    if kind == 1 and place ~= nil then
        local mine, his = place[club], place[opp]
        if mine ~= nil and his ~= nil then
            big = (mine <= BIG_TOP and his <= BIG_TOP)
                  or (mine > teams - BIG_BOTTOM and his > teams - BIG_BOTTOM)
        end
    end

    local v, why = value_of(ours, {
        cup = (kind ~= nil and kind ~= 1), round = round, top = top, near = near,
        derby = derby, big = big,
    })

    if v ~= last_value then
        memory.write(VALUE_AT, string.char(v))
        if memory.read(VALUE_AT, 1) ~= string.char(v) then
            if say_once("write") then log("MLTeamSpirit 4: the value did not go in. Quit the game, "
                .. "remove the module, send this log.") end
            return
        end
        last_value = v
    end

    if say_once("club") then
        log(string.format("MLTeamSpirit 4: your club is %d (Sider team %d). RIVALS uses packed "
            .. "club ids; copy the RIVALS id shown for the opponent.", ours_id, club))
    end
    -- one line for a match: Sider asks twice about the same one (set_conditions and after it)
    local line = string.format("MLTeamSpirit 4: %s against club %d (RIVALS id %d), competition %s round %s, "
        .. "form %s -> %d  [%s]", home_side and "at home" or "away", opp, opp * 16384, tostring(comp),
        tostring(round), form_text(ours), v, table.concat(why, "; "))
    if line ~= last_line then log(line) end
    last_line = line
end

-- ============================ install ============================

-- The settings, looked at before a single byte is written. -> the fault, or nil
local function settings_fault()
    local function whole(name, v, lo, hi)
        if type(v) ~= "number" or v ~= v or v < lo or v > hi then
            return string.format("%s is not a number from %d to %d", name, lo, hi)
        end
        return nil
    end
    local fault = whole("BASE", BASE, 1, 99) or whole("FLOOR", FLOOR, 1, 99)
                  or whole("CEILING", CEILING, 1, 99) or whole("TWO_LOSS_CAP", TWO_LOSS_CAP, 1, 99)
                  or whole("WIN_RUN_VALUE", WIN_RUN_VALUE, 1, 99) or whole("FINAL_VALUE", FINAL_VALUE, 1, 99)
                  or whole("FORM_SCALE", FORM_SCALE, 0, 20)
    if fault == nil and FLOOR > CEILING then fault = "FLOOR is above CEILING" end
    if fault == nil and (BASE < FLOOR or BASE > CEILING) then fault = "BASE is outside FLOOR to CEILING" end
    if fault == nil then
        fault = whole("FORM_MATCHES", FORM_MATCHES, 1, 10)
                or whole("WIN_RUN", WIN_RUN, 2, 10) or whole("SEASON", SEASON, 366, 400)
                or whole("CUP_NEAR_BONUS", CUP_NEAR_BONUS, 0, 9) or whole("DERBY_BONUS", DERBY_BONUS, 0, 9)
                or whole("BIG_MATCH_BONUS", BIG_MATCH_BONUS, 0, 9) or whole("BIG_TOP", BIG_TOP, 1, 20)
                or whole("BIG_BOTTOM", BIG_BOTTOM, 1, 20)
    end
    if fault == nil then
        if type(FORM_WEIGHTS) ~= "table" or #FORM_WEIGHTS < 1 then fault = "FORM_WEIGHTS is not a list" end
        for i = 1, #FORM_WEIGHTS do
            fault = fault or whole("FORM_WEIGHTS[" .. i .. "]", FORM_WEIGHTS[i], 0, 9)
        end
    end
    if fault == nil and type(RIVALS) ~= "table" then fault = "RIVALS is not a list" end
    return fault
end

function m.init(ctx)
    log("MLTeamSpirit 4: Team Spirit follows the form of your club")

    local fault = settings_fault()
    if fault ~= nil then
        log("RESULT: nothing written. Settings: " .. fault .. ".")
        return
    end
    log(string.format("     base %d, kept inside %d to %d; two losses -> %d, %d wins -> %d, "
        .. "a cup final -> %d", BASE, FLOOR, CEILING, TWO_LOSS_CAP, WIN_RUN, WIN_RUN_VALUE, FINAL_VALUE))

    for _, place in ipairs(LAYOUT_CHECKS) do
        local bytes = memory.read(place[1], #place[2] / 2)
        if bytes ~= unhex(place[2]) then
            log("RESULT: nothing written. This game does not hold the expected controlled-club layout; send this log.")
            return
        end
    end
    local got = memory.read(PLACE, #OLD / 2)
    local same = (type(got) == "string" and hex(got) == OLD)
    log(string.format("check: the value of a player of your club at %08x  %s", PLACE,
        same and "as expected" or ("DIFFERENT: " .. (got and hex(got) or "not readable"))))
    if not same then
        log("RESULT: nothing written. This game does not hold what the module expects; send this log.")
        return
    end

    local above = memory.read(OLD_PLACE, #OLD_VANILLA / 2)
    if type(above) == "string" and hex(above) ~= OLD_VANILLA then
        log(string.format("check: five bytes above the branch at %08x  DIFFERENT: %s. Version 1 of "
            .. "this module (or another) has changed them; while it has, no player reaches the "
            .. "branch, so the value of this module never comes into play.", OLD_PLACE, hex(above)))
    end

    local new = unhex(string.format("b8%02x0000005b5fe9d8000000", BASE))
    memory.write(PLACE, new)
    if memory.read(PLACE, #new) ~= new then
        local old = unhex(OLD)
        memory.write(PLACE, old)
        local restored = (memory.read(PLACE, #old) == old)
        log("RESULT: the change did not go in. " .. (restored and "Hook restored. " or "Hook restore failed. ")
            .. "Quit the game, remove the module, send this log.")
        return
    end
    last_value = BASE
    log("RESULT: installed. In a Master League match the Team Spirit of every player of your club "
        .. "is worked out from the club's form before the match and kept inside "
        .. string.format("%d to %d; it is %d until the first match.", FLOOR, CEILING, BASE))

    if type(ctx) == "table" and ctx.register ~= nil then
        ctx.register("after_set_conditions", m.set_conditions)
        ctx.register("set_conditions", m.set_conditions)
    end
end

return m
