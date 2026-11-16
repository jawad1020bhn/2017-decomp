-- MLSimToDate.lua, version 2: Sim to Date for PES 2017 Master League (Sider).
-- NOT YET RUN IN THE GAME. Back up your save before trying it; see sider/README.md.
--
-- In Master League, open Schedule, highlight a future day and press F8. The calendar
-- headline shows the selected target. Press F9 there to cancel. Go back and advance:
-- matches before the target use Skip Match. The target automatically switches off when
-- reached. The game can stop for news or at transfer windows; advance again to continue.
-- Today is not skipped. The run ends on the first natural stop on or after the target.
-- An unfinished target may affect another loaded career: cancel it before switching saves.
--
-- Only this exe is supported: sha256 44b0caaa...; checks precede all game-code writes.
-- Install in modules/ and add lua.module = "MLSimToDate.lua" to sider.ini. Keyboard
-- shortcuts work in the game's Schedule screen, without newer Sider overlay events.
--
-- Optional legacy controls: set the date below, or put MLSimToDate.txt next to sider.exe
-- with 2025-03-15, 15.3.2025, or off. File changes are read on Sider's file-load events
-- only if the file existed on startup; see the README. These dates remain in force
-- across careers until switched off, unlike a one-shot selection in the calendar.

local m = {}

-- ============================ settings ============================

-- Optional starting date; 0 starts off, ready to select a date in Schedule.
-- A text file, if present, overrides these three settings.
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
local ROUTINE_SIZE = 138
-- Mutable state is in the writable, otherwise unused .text stub, not the RX code page.
local DATA_AT, DATA_SIZE = 0x0298c0e0, 0x120
local DATE_AT = DATA_AT
-- the call that is changed, in the game's test "does the calendar stop today?"
local SITE = 0x0360b786
-- the text file with the date, next to sider.exe
local FILE_NAME = "MLSimToDate.txt"
local SITE_OLD = "e85a092100"
local CALENDAR_AT, CALENDAR_SIZE = 0x047d6550, 0x900
local POLL_SITE, TITLE_SITE = 0x03231ec5, 0x03230d54
local POLL_AT, TITLE_AT = CALENDAR_AT, 0x047d6950
local READY = DATA_AT + 7

-- The day-loop routine (source in test_simdate.py). At the call: esi = the career's
-- data, bl = the game's stop decision. Skip Match value 2 marks our own setting.
local PARTS = {
    "803de7c0980201757ba1e8f3640285c07472837820137406837820287566a1e0c09802"
        .. "3986b0cbc2007354c686a0b6dc0001c6861cb6dc0002a1e00365028b40346683b8b8370500ff740ab0",
    "84c0751330dbeb25b0",
    "20d87409c686a0b6dc0000eb0fb831a88703ffd084c0750430dbeb07c6861cb6dc0000"
        .. "83042413c3e96cfbffffa1e0036502c3",
}

-- What the routine relies on: address, bytes, what it is.
local PLACES = {
    { SITE, "e85a0921008b503080baa0b6dc00007407e895f0260088c35e88d85b89ec5dc3",
      "end of the stop test" },
    { 0x0387a831, "5589e583ec2c5356e8a718faff8b4030", "the game's own stop test" },
    { 0x035fe5aa, "c6861cb6dc0001", "Skip Match sets its switch" },
    { 0x038ae460, "0fb788b0cbc200", "where today's date is" },
    { 0x0387a865, "81c6b8370500", "where today's match is" },
    { 0x038093f1, "8b412083f846720231c08b048508d45102c3", "mode lookup" },
    { 0x0251d454, "0c000000", "Master League mode 19" },
    { 0x0251d4a8, "0c000000", "Master League mode 40" },
    { 0x03231df4, "5589e583ec08565789cee8e959180089", "schedule input context" },
    { 0x03231a90, "e850a65e008b40300fb788b0cbc200898ea8000000", "schedule initial day" },
    { 0x03231c9e, "5589e583ec0c5689ce8b86a80000003b46680f848600000085c0750ac786a80000006d",
      "schedule previous day" },
    { 0x03231d41, "5589e583ec0c5689ce8b86a80000003b466c0f848a000000408986a80000003d6d010000750ac786",
      "schedule next day" },
    { 0x033680c6, "83c40439d88d476875118d5f6cc700b5000000c703b4000000eb0b89188d5f6cc7036c010000",
      "schedule season bounds" },
    { 0x038ae33c, "5589e553e8a0ddf6ff8b40308a9890b6dc00e892ddf6ff8b48308b450c8a5002",
      "season start month" },
    { 0x03231ea0, "683433fe0189f1e8265e180089c1e8dd60190084c0743d684033fe0189f1e80f5e180089c1",
      "schedule readiness checks" },
    { 0x033b7cd2, "8b41588b407cc3", "schedule control lookup" },
    { POLL_SITE, "e8c660190084c07426b0013885ffffff", "schedule input" },
    { TITLE_SITE, "e89ecd1900889dfcffffff39b5ccffff", "schedule headline" },
    { 0x03230bb2, "5589e56aff6839aa480464a100000000", "headline refresh" },
    { 0x033c7f90, "5589e56aff68754d4a0464a100000000", "schedule readiness" },
    { 0x033cdaf7, "5589e56aff68c2114a0464a100000000", "headline text" },
    { 0x038ae3cc, "5589e5515356e80eddf6ff8b75108b16", "date conversion" },
    { 0x0216bb60, "01000000000000001e000000020000001f0000003a000000"
        .. "030000003b00000059000000040000005a00000077000000"
        .. "0500000078000000960000000600000097000000b4000000"
        .. "07000000b5000000d300000008000000d4000000f2000000"
        .. "09000000f3000000100100000a000000110100002f010000"
        .. "0b000000300100004d0100000c0000004e0100006c010000", "month table" },
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

-- Generated by simdate_calendar.py; its source and checks are in the adjacent tests.
local CALENDAR = table.concat({
    unhex("ff742404e8371abffe9c6084c00f8447010000803de7c09802010f853a010000a1e8f3640285c00f8426010000837820"),
    unhex("13740a837820280f8516010000a1e003650285c00f8409010000837830000f84ff000000ff1548797d0485c00f84f100"),
    unhex("00006a0089e25250ff1574797d045b85c00f84dc000000ff1570717d0439d80f85ce0000008b1de8c0980285db752668"),
    unhex("e06b7d04ff15e4717d0485c0747c68f06b7d0450ff15ec717d0485c0746c89c3a3e8c098026a77ffd366a90080750980"),
    unhex("25e6c09802feeb17f605e6c0980201750e800de6c098020189f1e8210100006a78ffd366a9008075098025e6c09802fd"),
    unhex("eb28f605e6c0980202751f800de6c0980202c705e0c0980200000000c605e4c0980200c605e5c0980200a1e0c098023b"),
    unhex("05ecc09802750da0e5c098023a05f0c098027426a1e0c09802a3ecc09802a0e5c09802a2f0c098026a0089f1e811a5a5"),
    unhex("feeb07c605e6c0980203619dc20400"),
    string.rep(string.char(0xcc), 161),
    unhex("5589e553565789cea1e003650285c00f84da0000008b783085ff0f84cf0000008b8ea800000081f96c0100000f879e00"),
    unhex("00008b87b0cbc2000fb7d881fb6c0100000f8789000000c1e8103dd0070000727f3d9808000077780fb69790b6dc0083"),
    unhex("fa01726c83fa0c77674a6bd20c8b9264bb160281fa6c010000775539566875505285d27505ba6d0100004a39566c5a75"),
    unhex("3f39d373014839d17301403dd0070000722e3d980800007727c1e01009c83b87b0cbc200761aa3e0c09802c605e4c098"),
    unhex("0201c605e5c0980200b801000000eb21c705e0c0980200000000c605e4c0980200c605e5c0980201b801000000eb0231"),
    unhex("c05f5e5b89ec5dc3"),
    string.rep(string.char(0xcc), 264),
    unhex("5589e583ec0c53565789cf8b7508803de7c09802010f85b6000000a1e8f3640285c00f84a900000083782013740a8378"),
    unhex("20280f8599000000803de5c09802007566a1e0c0980289c3c1eb1081fbd0070000725c81fb98080000775425ffff0000"),
    unhex("3d6c0100007748895dfc8945f88d45f8508d45fc508d45f450e8fe790dff83c40c0fb645f70fb655f65352505668606c"),
    unhex("7d0468000100006800c19802ff15cc757d0483c41ceb215668c06c7d04eb065668106c7d0468000100006800c19802ff"),
    unhex("15cc757d0483c41085c07805be00c198025689f9e8ce70bffe5f5e5b89ec5dc20400"),
    string.rep(string.char(0xcc), 286),
    unhex("803de4c09802017511c705e0c0980200000000c605e4c098020080be1cb6dc0002750ec686a0b6dc0000c6861cb6dc00"),
    unhex("00a1e0036502c3"),
    string.rep(string.char(0xcc), 89),
    unhex("7573657233322e646c6c00cccccccccc4765744173796e634b6579537461746500cccccccccccccccccccccccccccccc"),
    unhex("252e363473207c2053494d204f4646207c2046382053455400"),
    string.rep(string.char(0xcc), 55),
    unhex("252e363473207c2053494d20253032752e253032752e25303475207c204639204f464600"),
    string.rep(string.char(0xcc), 60),
    unhex("252e363473207c204655545552452044415445204f4e4c59207c2053494d204f464600"),
    string.rep(string.char(0xcc), 365)
})

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

-- The game's date as one number: the year, then the day of the year (1 January = 0).
-- nil if it is not a date from 2000 to 2200.
local function date_number(year, month, day)
    if not whole(year, 2000, 2200) or not whole(month, 1, 12)
        or not whole(day, 1, DAYS[month]) then
        return nil
    end
    return year * 65536 + BEFORE[month] + day - 1
end

-- that number as text, the way the game shows a date
local function shown(number)
    local year, day = math.floor(number / 65536), number % 65536
    local month = 12
    while BEFORE[month] > day do month = month - 1 end
    return string.format("%d.%d.%d", day - BEFORE[month] + 1, month, year)
end

-- The text of the file -> the date as a number, 0 for "off" (or an empty file), nil if
-- it is neither. Year first (2025-03-15) or year last (15.3.2025).
local function from_text(text)
    text = string.gsub(text, "^\239\187\191", "")         -- the mark some editors put first
    local a, b, c = string.match(text, "^%s*(%d+)%D+(%d+)%D+(%d+)%s*$")
    if a == nil then
        if string.match(string.lower(text), "^%s*off%s*$") or string.match(text, "^%s*0?%s*$") then
            return 0
        end
        return nil
    end
    a, b, c = tonumber(a), tonumber(b), tonumber(c)
    if a >= 1000 then return date_number(a, b, c) end
    return date_number(c, b, a)
end

function m.init(ctx)
    log("MLSimToDate 2: choose a date in Schedule (F8), cancel with F9; " .. FILE_NAME .. " is optional")

    -- the text file, if this Sider lets a module read files and hear of the game's loading
    local path, text
    if type(io) == "table" and type(os) == "table" and type(ctx) == "table"
        and type(ctx.register) == "function" and type(ctx.sider_dir) == "string" then
        path = ctx.sider_dir
        local last = string.sub(path, -1)
        if last ~= "\\" and last ~= "/" then path = path .. "\\" end
        path = path .. FILE_NAME
        local file = io.open(path, "r")
        if file then
            text = file:read(64) or ""
            file:close()
        end
        log("date file: " .. path .. (text and "  found" or "  not there, the date in MLSimToDate.lua is used"))
    end

    local target
    if text == nil then
        target = SIM_YEAR == 0 and 0 or date_number(SIM_YEAR, SIM_MONTH, SIM_DAY)
        if target == nil then
            log("RESULT: nothing written. Settings: SIM_YEAR, SIM_MONTH, SIM_DAY are not a date "
                .. "from 2000 to 2200 (the game has no 29 February)")
            return
        end
    else
        target = from_text(text)
        if target == nil then
            log("date file: invalid date; starting switched off. Correct the file or use Schedule.")
            target = 0
        end
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
    local data_room = memory.read(DATA_AT, DATA_SIZE)
    local data_empty = (data_room ~= nil and data_room == string.rep("\0", DATA_SIZE))
    if not data_empty then good = false end
    log(string.format("check: %-28s at %08x  %s", "calendar state", DATA_AT,
        data_empty and "empty" or "NOT EMPTY"))
    local space = memory.read(CALENDAR_AT, CALENDAR_SIZE)
    local calendar_empty = (space ~= nil and space == string.rep("\0", CALENDAR_SIZE))
    if not calendar_empty then good = false end
    log(string.format("check: %-28s at %08x  %s", "calendar free memory", CALENDAR_AT,
        calendar_empty and "empty" or "NOT EMPTY"))
    if not good then
        log("RESULT: nothing written. This game does not hold what the module expects; "
            .. "send this log.")
        return
    end

    local routine = unhex(PARTS[1] .. (STOP_AT_BIG_MATCHES and "01" or "00")
        .. PARTS[2] .. (STOP_FOR_NEWS and "01" or "00") .. PARTS[3])
    if #routine ~= ROUTINE_SIZE or #CALENDAR ~= CALENDAR_SIZE then
        log("RESULT: nothing written. A routine in the file is damaged.")
        return
    end

    -- Install state and code before exposing them; mark the reserved text buffer as occupied.
    local data = unhex(le32(target)) .. string.rep("\0", 0x1c) .. string.rep(string.char(0xcc), 0x100)
    memory.write(DATA_AT, data)
    if memory.read(DATA_AT, DATA_SIZE) ~= data then
        log("RESULT: a change did not go in (calendar state). The game's code is untouched; restart and send this log.")
        return
    end
    memory.write(CALENDAR_AT, CALENDAR)
    if memory.read(CALENDAR_AT, CALENDAR_SIZE) ~= CALENDAR then
        log("RESULT: a change did not go in (calendar). The game's code is untouched; restart and send this log.")
        return
    end
    memory.write(ROUTINE, routine)
    if memory.read(ROUTINE, ROUTINE_SIZE) ~= routine then
        log("RESULT: a change did not go in (the routine). The game's code is untouched; restart and send this log.")
        return
    end
    local hooks = {
        { TITLE_SITE, "e89ecd1900", TITLE_AT },
        { POLL_SITE, "e8c6601900", POLL_AT },
        { SITE, SITE_OLD, ROUTINE },
    }
    for i, hook in ipairs(hooks) do
        local call = unhex("e8" .. le32(hook[3] - (hook[1] + 5)))
        memory.write(hook[1], call)
        if memory.read(hook[1], 5) ~= call then
            local restored = true
            for j = i, 1, -1 do
                local old = unhex(hooks[j][2])
                memory.write(hooks[j][1], old)
                if memory.read(hooks[j][1], 5) ~= old then restored = false end
            end
            log("RESULT: a change did not go in. " .. (restored and "Hooks restored. " or "Hook restore failed. ")
                .. "Quit the game, remove the module, send this log.")
            return
        end
    end

    -- the text file from now on: looked at when the game loads a file, once a second at most
    local live = ""
    if text ~= nil then
        local looked = os.time()
        ctx.register("livecpk_make_key", function()
            local now = os.time()
            if now == looked then return end
            looked = now
            if memory.read(READY, 1) ~= "\1" then return end
            local file = io.open(path, "r")
            if not file then return end
            local new = file:read(64) or ""
            file:close()
            if new == text then return end
            local number = from_text(new)
            if number == nil then
                text = new
                log("MLSimToDate: " .. FILE_NAME .. " holds neither a date nor the word off; "
                    .. "the date stays as it was")
                return
            end
            -- Write the date and its source/error together so a file change replaces a calendar choice.
            local state = unhex(le32(number)) .. "\0\0"
            if memory.read(DATE_AT, 6) == state then
                text = new
                return
            end
            memory.write(DATE_AT, state)
            if memory.read(DATE_AT, 6) ~= state then
                log("MLSimToDate: the new date did not go in; send this log")
                return
            end
            text = new
            log("MLSimToDate: " .. (number == 0 and "switched off" or ("the date is now " .. shown(number)))
                .. " (from " .. FILE_NAME .. ")")
        end)
        live = " The date is read from " .. FILE_NAME .. " while the game runs."
    end

    -- Sider has no pcall. All hooks stay inert if a write throws before this point.
    memory.write(READY, "\1")
    if memory.read(READY, 1) ~= "\1" then
        memory.write(READY, "\0")
        log("RESULT: the module could not be enabled. Quit the game, remove the module, send this log.")
        return
    end

    local settings = (STOP_FOR_NEWS and " It stops for news." or "")
        .. (STOP_AT_BIG_MATCHES and " It stops at big matches." or "") .. live
    if target == 0 then
        log("RESULT: installed, switched off. In Master League Schedule, highlight a future day and press F8."
            .. settings)
        return
    end
    log("RESULT: installed. A Master League before " .. shown(target) .. " runs on to that date "
        .. "when you advance; your matches on the way are simulated." .. settings)
end

return m
