-- MLTeamSpirit.lua, version 1: Team Spirit has no effect in a Master League match
-- (Sider Lua module). Made for PES2017.exe sha256 44b0caaa...
--
-- What the game does (MASTER_LEAGUE.md, section 12): in a played match every player of
-- YOUR club has a Team Spirit value of 1 to 99, and 22 of his abilities are multiplied by
-- 0.70 (value 10 or less) to 1.00 (value 99). A player of a computer club always has 99.
-- A skipped match does not read Team Spirit at all.
--
-- What the module changes, in the running game only (no file is touched): one jump in the
-- function that gives a player his value. In Master League it now answers 99 for your
-- players too, so no ability is lowered. The other modes are untouched.
--
-- It first checks that the game holds the expected code at the place. If it differs it
-- writes nothing and says so in sider.log.
--
-- Install: copy this file into the "modules" folder next to sider.exe and add
--     lua.module = "MLTeamSpirit.lua"
-- to sider.ini, above or below the other lines. Remove the line to get Team Spirit back.
-- It needs no other module, and no other module needs it.
--
-- Uses only: log, memory.read, memory.write, string, table, tonumber.

local m = {}

-- The Master League branch of the value function fcn_038df4c9: "call mode_object", the
-- first step of the test "is this a player of the user's club". New: jump to the
-- function's own "return 99" at 0x038df7a1, which is where a player of another club goes.
local PLACE = 0x038df528
local OLD = "e8b8cbf3ff"
local NEW = "e974020000"

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

function m.init(ctx)
    log("MLTeamSpirit 1: Team Spirit has no effect in a Master League match")

    local got = memory.read(PLACE, #OLD / 2)
    local same = (got ~= nil and hex(got) == OLD)
    log(string.format("check: value of a Master League player at %08x  %s", PLACE,
        same and "as expected" or ("DIFFERENT: " .. (got and hex(got) or "not readable"))))
    if not same then
        log("RESULT: nothing written. This game does not hold what the module expects; "
            .. "send this log.")
        return
    end

    local new = unhex(NEW)
    memory.write(PLACE, new)
    if memory.read(PLACE, #new) ~= new then
        log("RESULT: the change did not go in. Quit the game, remove the module, send this log.")
        return
    end
    log("RESULT: installed. In Master League the Team Spirit of every player is 99: "
        .. "no ability is lowered in a match.")
end

return m
