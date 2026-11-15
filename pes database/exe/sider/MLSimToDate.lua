-- MLSimToDate.lua, version 1: "Sim to Date" for the Master League of PES 2017 (Sider Lua
-- module). Made for PES2017.exe sha256 44b0caaa...
--
-- NOT YET RUN IN THE GAME. It was tested in an emulator on small pieces of the game's
-- code only. Copy your save before the first try (sider/README.md says how to try it).
--
-- What it does: you set a date below. In a Master League whose date is before it, you
-- press the normal "advance" once, and the game goes on, day after day, up to that date.
-- Your own matches on the way are simulated the way "Skip Match" simulates them (so with
-- MLSimMatch.lua, if it is installed), without a stop at each one.
--
-- It ends on the first day, on or after the date, on which the game stops by itself. The
-- match of that day is not played: it is yours. So for "sim to a fixture", set the date
-- of that fixture.
--
-- How: the game has its own "keep advancing" switch and its own "this match is skipped"
-- switch. The module changes one call in the game's "does the calendar stop today?"
-- test into a call of a small routine (140 bytes, written into free memory) that turns
-- both switches on while the date is before yours, and off when the date is reached.
--
-- It works in Master League only. In every other mode the routine does nothing.
-- The date stays in force for every Master League you load, a new one too: set
-- SIM_YEAR = 0 when you are done.
-- A match of today is not skipped for you: play or skip it, the run starts after it.
--
-- It first checks that the game holds the expected code at five places and that the
-- free memory is empty. If one differs it writes nothing and says so in sider.log.
--
-- Install: copy this file into the "modules" folder next to sider.exe and add
--     lua.module = "MLSimToDate.lua"
-- to sider.ini, above or below the other lines. The date is read when the game starts:
-- for another date change it here and start the game again.
--
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, tonumber, type.

local m = {}

-- ============================ settings ============================

-- The date to simulate to, as the game shows it. SIM_YEAR = 0 switches the module off.
local SIM_YEAR = 0
local SIM_MONTH = 1
local SIM_DAY = 1

-- true: on a day without a match of yours, stop where the game normally stops (a transfer
-- offer, an injury, a report: whatever stops a normal "advance"). Press "advance" again
-- and the run goes on. false: do not stop for these; their screens are not shown.
local STOP_FOR_NEWS = true

-- true: let the game stop at a match it calls important (a final, a rival, a strong
-- opponent in a cup: the game's own list, not fully read). false: simulate every match.
local STOP_AT_BIG_MATCHES = false

-- ========================= end of settings =========================

-- the free memory the routine goes to (the end of the page of .link) and its length
local ROUTINE = 0x047d6f60
local ROUTINE_SIZE = 140
-- the call that is changed, in the game's test "does the calendar stop today?"
local SITE = 0x0360b786
local SITE_OLD = "e85a092100"

-- The routine (its source is in test_simdate.py). At the call: esi = the career's data,
-- bl = 1 if the game would stop today. Three numbers are put in: the date,
-- STOP_AT_BIG_MATCHES, STOP_FOR_NEWS. It sets the Skip Match switch to 2 where the game
-- sets 1, to know its own setting from yours; the game only asks "is it 0".
local PARTS = {
    "a1e8f3640285c0747d8378200c757781beb0cbc200",       -- Master League? today before the date?
    "7354c686a0b6dc0001c6861cb6dc0002a1e00365028b40346683b8b8370500ff740ab0",
    "84c0751330dbeb25b0",
    "20d87409c686a0b6dc0000eb0fb831a88703ffd084c0750430dbeb07c6861cb6dc0000"
        .. "83042413c380be1cb6dc0002750ec686a0b6dc0000c6861cb6dc0000a1e0036502c3",
}

-- What the routine relies on: address, bytes, what it is.
local PLACES = {
    { SITE, "e85a0921008b503080baa0b6dc00007407e895f0260088c35e88d85b89ec5dc3",
      "end of the stop test" },
    { 0x0387a831, "5589e583ec2c5356e8a718faff8b4030", "the game's own stop test" },
    { 0x035fe5aa, "c6861cb6dc0001", "Skip Match sets its switch" },
    { 0x038ae460, "0fb788b0cbc200", "where today's date is" },
    { 0x0387a865, "81c6b8370500", "where today's match is" },
}

-- days before the first of each month (the game's year has no 29 February)
local BEFORE = { 0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334 }
local DAYS = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 }

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

-- a number as four bytes, lowest first, as hex text
local function le32(v)
    local t = {}
    for i = 1, 4 do
        t[i] = string.format("%02x", v % 256)
        v = math.floor(v / 256)
    end
    return table.concat(t)
end

local function whole(v, low, high)
    return type(v) == "number" and v == math.floor(v) and v >= low and v <= high
end

function m.init(ctx)
    log("MLSimToDate 1: simulate a Master League to the date set in MLSimToDate.lua")

    if SIM_YEAR == 0 then
        log("RESULT: nothing written. SIM_YEAR is 0: the module is switched off.")
        return
    end
    if not whole(SIM_YEAR, 2000, 2200) or not whole(SIM_MONTH, 1, 12)
        or not whole(SIM_DAY, 1, DAYS[SIM_MONTH]) then
        log("RESULT: nothing written. Settings: SIM_YEAR, SIM_MONTH, SIM_DAY are not a date "
            .. "from 2000 to 2200 (the game has no 29 February)")
        return
    end
    if type(STOP_FOR_NEWS) ~= "boolean" or type(STOP_AT_BIG_MATCHES) ~= "boolean" then
        log("RESULT: nothing written. Settings: STOP_FOR_NEWS and STOP_AT_BIG_MATCHES "
            .. "must be true or false")
        return
    end

    local good = true
    for _, place in ipairs(PLACES) do
        local got = memory.read(place[1], #place[2] / 2)
        local same = (got ~= nil and hex(got) == place[2])
        if not same then good = false end
        log(string.format("check: %-28s at %08x  %s", place[3], place[1],
            same and "as expected" or ("DIFFERENT: " .. (got and hex(got) or "not readable"))))
    end
    local room = memory.read(ROUTINE, ROUTINE_SIZE)
    local empty = (room ~= nil and room == string.rep("\0", ROUTINE_SIZE))
    if not empty then good = false end
    log(string.format("check: %-28s at %08x  %s", "free memory", ROUTINE,
        empty and "empty" or "NOT EMPTY"))
    if not good then
        log("RESULT: nothing written. This game does not hold what the module expects; "
            .. "send this log.")
        return
    end

    -- the game's date as one number: the year, then the day of the year (1 January = 0)
    local target = SIM_YEAR * 65536 + BEFORE[SIM_MONTH] + SIM_DAY - 1
    local routine = unhex(PARTS[1] .. le32(target) .. PARTS[2]
        .. (STOP_AT_BIG_MATCHES and "01" or "00") .. PARTS[3]
        .. (STOP_FOR_NEWS and "01" or "00") .. PARTS[4])
    if #routine ~= ROUTINE_SIZE then
        log("RESULT: nothing written. The routine in the file is damaged.")
        return
    end

    -- the routine first; the call is changed only when the routine is in
    memory.write(ROUTINE, routine)
    if memory.read(ROUTINE, ROUTINE_SIZE) ~= routine then
        log("RESULT: a change did not go in (the routine). The game's code is untouched; "
            .. "send this log.")
        return
    end
    local call = unhex("e8" .. le32(ROUTINE - (SITE + 5)))
    memory.write(SITE, call)
    if memory.read(SITE, 5) ~= call then
        log("RESULT: a change did not go in. Quit the game, remove the module, send this log.")
        return
    end
    log(string.format("RESULT: installed. A Master League before %d.%d.%d runs on to that date "
        .. "when you advance; your matches on the way are simulated.%s%s",
        SIM_DAY, SIM_MONTH, SIM_YEAR,
        STOP_FOR_NEWS and " It stops for news." or "",
        STOP_AT_BIG_MATCHES and " It stops at big matches." or ""))
end

return m
