-- MLYear.lua, version 1: the year in which a new career starts in PES 2017 (Sider Lua
-- module). Made for PES2017.exe sha256 44b0caaa..., whose new careers start in 2024.
--
-- What it changes, in the running game only (no file is touched): the eight numbers in
-- the game's set-up of a new career that hold the year. With START_YEAR = 2026 a new
-- Master League starts on 1 July 2026 (season 2026/27), and every contract starts and
-- ends two years later than without the module.
--
-- It works for a NEW career only. The year and every date of a career are in its save,
-- so a career that was started in 2024 stays in 2024. Become a Legend and League mode
-- use the same set-up and start in the same year.
--
-- What it does not change: the players. Their ages are the ages of the edit file, in
-- any year. And the places where the game still asks "is this 2016?" (its own first
-- season): they do not answer yes in 2024 and do not in 2026 (sider/README.md).
--
-- It first checks that the game holds the expected code at all eight places. If one
-- differs it writes nothing and says so in sider.log.
--
-- Install: copy this file into the "modules" folder next to sider.exe and add
--     lua.module = "MLYear.lua"
-- to sider.ini, above or below the other lines. Remove the line to start in 2024 again.
-- It needs neither MLMoney.lua nor MLTransfers.lua, and they do not need it.
--
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, tonumber, type.

local m = {}

-- ============================ settings ============================

-- The year of the first day of a new career. 2026 gives the season 2026/27.
local START_YEAR = 2026

-- ========================= end of settings =========================

-- the year the game holds at the places below
local GAME_YEAR = 2024

-- The year in the set-up of a new career (MASTER_LEAGUE.md, section 2.5): address of the
-- instruction, its bytes before the year, years added to the start year, its bytes after
-- the year, what it is.
local PLACES = {
    { 0x035f44b4, "b8",           0, "0000", "year of the first day" },
    { 0x035f452e, "c7868cb6dc00", 0, "0101", "first day, season from January" },
    { 0x035f458f, "c7868cb6dc00", 0, "0701", "first day, season from July" },
    { 0x036653b3, "8d8b",         0, "0000", "contract end, season from July" },
    { 0x036653bf, "c787d8000000", 0, "0701", "contract start, season from July" },
    { 0x036653f2, "8d8b",         1, "0000", "contract end, season from January" },
    { 0x036653fa, "8d8b",         0, "0000", "contract end, season from January" },
    { 0x0366540c, "c787d8000000", 0, "0101", "contract start, season from January" },
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

-- the instruction of a place with the given start year, as hex text
local function instruction(place, year)
    local y = year + place[3]
    return place[2] .. string.format("%02x%02x", y % 256, math.floor(y / 256)) .. place[4]
end

function m.init(ctx)
    log("MLYear 1: the year in which a new career starts, from the setting in MLYear.lua")

    if type(START_YEAR) ~= "number" or START_YEAR ~= math.floor(START_YEAR)
        or START_YEAR < 2000 or START_YEAR > 2100 then
        log("RESULT: nothing written. Settings: START_YEAR is not a whole year from 2000 to 2100")
        return
    end

    local good = true
    for _, place in ipairs(PLACES) do
        local expected = instruction(place, GAME_YEAR)
        local got = memory.read(place[1], #expected / 2)
        local same = (got ~= nil and hex(got) == expected)
        if not same then good = false end
        log(string.format("check: %-35s at %08x  %s", place[5], place[1],
            same and "as expected" or ("DIFFERENT: " .. (got and hex(got) or "not readable"))))
    end
    if not good then
        log("RESULT: nothing written. This game does not hold what the module expects; "
            .. "send this log.")
        return
    end
    if START_YEAR == GAME_YEAR then
        log("RESULT: nothing written. The game starts a new career in " .. GAME_YEAR .. " by itself.")
        return
    end

    for i, place in ipairs(PLACES) do
        local new = unhex(instruction(place, START_YEAR))
        memory.write(place[1], new)
        if memory.read(place[1], #new) ~= new then
            local restored = true
            for j = i, 1, -1 do
                local old = unhex(instruction(PLACES[j], GAME_YEAR))
                memory.write(PLACES[j][1], old)
                if memory.read(PLACES[j][1], #old) ~= old then restored = false end
            end
            log("RESULT: a change did not go in. " .. (restored and "Changes restored. " or "Change restore failed. ")
                .. "Quit the game, remove the module, send this log.")
            return
        end
    end
    log(string.format("RESULT: installed. A new career starts in %d (season %d/%02d). "
        .. "A saved career keeps its year.", START_YEAR, START_YEAR, (START_YEAR + 1) % 100))
end

return m
