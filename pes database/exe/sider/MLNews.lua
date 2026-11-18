-- MLNews.lua, version 4: factual world-result ticker proof (Sider 3.6.0).
-- For PES2017.exe SHA256 44b0caaa... only. Emulator-tested, NOT live-game verified.
--
-- Rotates up to four dated AI-v-AI league/cup results across the native ML ticker.
-- Results are at most fourteen game days old, ranked by newest date then goal margin.
-- Every native ticker item keeps its original headline after its factual prefix.
-- No stored article, popup, extra stop, RNG draw, gameplay write or history file.
-- Version 2 adds bounded runtime diagnostics: a copy/rejection stage, not a rendering claim.
-- Version 3 accepts the normal indexed career tables (lookup mode 2), including sparse slots.
-- Version 4 expands to four stories, normal-time cup results and a fourteen-day window.
-- The native ticker must already have an item; no recent eligible result means no change.
-- shortcut: four normal-time league/cup scores, English labels; expand after live display proof.
--
-- Built from the current career on each ticker rebuild: reloads, earlier saves and
-- another career cannot inherit a Lua cache. A redraw gets one prefix, not another entry.
-- The native string constructor copies the stack text; PES owns and frees its copy.
-- Match, club, competition and date fields are observed, never changed.
--
-- Copy into Sider's modules folder, add lua.module = "MLNews.lua", fully restart PES.
-- Test on a backed-up save first; remove that line and restart to undo the UI hook.
-- See README.md for the live acceptance check. Python is for development only.

local m = {}
local CAVE, SIZE = 0x03fc8900, 0xa00
local STATE, STATE_SIZE = 0x0298c2f0, 48
local SITE = 0x032a2dd1
local OLD, CALL = "e89afaf000", "e82a5bd200"

local function unhex(h)
    local t = {}
    for i = 1, #h, 2 do t[#t + 1] = string.char(tonumber(string.sub(h, i, i + 1), 16)) end
    return table.concat(t)
end

-- Frozen machine code from news_cave.py --lua; no assembler or unsupported Lua callbacks.
local CODE = table.concat({
    unhex("9cff05f0c298029d5589e581ec0001000053565789cb89fa8d8d00ffffffe8dd00000085c074318b75088d8500ffffff"),
    unhex("5089f1e8acf583ff6aff6a005389f1e87536c0fe89f0ff05f8c29802c705fcc298020c000000eb0aff750889d9e80e9f"),
    unhex("1e005f5e5b89ec5dc20400"),
    string.rep(string.char(0xcc), 149),
    unhex("5589e583ec78535657894dfc8955c88d7d8831c0b910000000f3abff05f4c29802c705fcc2980201000000c70500c398"),
    unhex("0200000000c70504c3980200000000c70508c3980200000000c7050cc3980200000000c70510c3980200000000c70514"),
    unhex("c39802ffffffffc70518c3980200000000c7051cc39802ffffffffa1e8f364023d000001000f82ba0300003d0000ff7f"),
    unhex("0f87af030000c705fcc29802020000008b5020891518c3980283fa13740983fa280f858e030000c705fcc29802030000"),
    unhex("00a1e00365023d000001000f82740300003d0000ff7f0f87690300008b703081fe000001000f825a03000081fe000000"),
    unhex("7f0f874e030000c705fcc29802040000008b860814ec008945cca31cc3980283f8020f872d030000c705fcc298020500"),
    unhex("00000fb786b2cbc200a300c398023dd00700000f820c0300003d980800000f870103000069c06d0100000fb796b0cbc2"),
    unhex("00891504c3980281fa6c0100000f87e202000001d08945f8c705fcc29802060000008b86e0ec5f00a308c3980285c00f"),
    unhex("84c00200003d8b0200000f87b5020000837dcc027505b88b0200008945f4c705fcc29802070000008b86e8ec5f00a30c"),
    unhex("c3980285c00f848a0200003d2c0100000f877f020000837dcc027505b82c0100008945f0c705fcc2980208000000c745"),
    unhex("ec000000008dbee01b48008b5df4833fff743d8b8714030000c1e80784c07530ff0510c39802837dec000f8535020000"),
    unhex("8b07c1e80e25ffff000085c00f84230200003dffff00000f84180200008945ec81c7200500004b75b5837dec000f8402"),
    unhex("020000c705fcc29802090000008dbe4c156f008d9e2cd5bf0066813f28230f831c010000f64707400f84120100006683"),
    unhex("7f15000f850701000066837f18000f85fc0000008b470cc1e80e25ffff00003b45ec0f84e80000008b5710c1ea0e81e2"),
    unhex("ffff00003b55ec0f84d300000039d00f84cb0000008b5708e84303000085c00f84bb0000008b4df829c10f82b0000000"),
    unhex("83f90e0f87a7000000c1e0070fb64f1483f9630f87970000000fb6571783fa630f878a00000029d17902f7d901c83b45"),
    unhex("b8767d8945e00fb747048b4df0e86e04000085c0746a8b470c8b4df4e8df03000085c0745b8945dc8b47108b4df4e8cd"),
    unhex("03000085c074498945d08b45e08d55883b02770583c210ebf78d4db839d1761c8b41f089018b41f48941048b41f88941"),
    unhex("088b41fc89410c83e910ebe08b45e08902897a048b45dc8942088b45d089420c81c74c02000039df0f82cbfeffff31c9"),
    unhex("8d558c833a0074094183c21083f90472f285c90f849c0000008b45c831d2f7f1c1e2048d5415888b7a048b42088945d4"),
    unhex("8b420c8945d00fb747048b4df0e8ae03000085c0746fba5092fc0383f8017405ba5892fc030fb707a314c39802c705fc"),
    unhex("c298020a000000ff75d00fb64717500fb6471450ff75d4520fb74708500fb6470a500fb6470b50680092fc0368000100"),
    unhex("00ff75fcff15cc757d0483c42c83f80172133dff000000770cc705fcc298020b000000eb0231c05f5e5b89ec5dc3"),
    string.rep(string.char(0xcc), 434),
    unhex("0fb7c23dd007000072353d98080000772e69c06d01000089d1c1e91081e1ff0000004983f90b7717c1ea184a3b14cd84"),
    unhex("92fc03730a0304cd8092fc0301d0c331c0c3"),
    string.rep(string.char(0xcc), 190),
    unhex("83f8ff74138d96e01b48003b02740c81c2200500004975f331c0c38b8a14030000c1e90780f9ff75ef538d5a0489d8b9"),
    unhex("460000000fb61084d2741c80fa20721380fa7f740e80fa3c740980fa3e7404404975e131c05bc339d874f889d85bc3"),
    string.rep(string.char(0xcc), 33),
    unhex("516683f8ff74148d96802e5500663b02740d81c2240200004975f231c0eb3c8b425c83f803743483f80175ef66837a4e"),
    unhex("ff74280fb7424e8b0c248d96802e5500663b02740b81c2240200004975f2ebcb837a5c0275c5b80300000059c3"),
    string.rep(string.char(0xcc), 35),
    unhex("574f524c4420524553554c5420253032752f253032752f25303475205b25735d3a2025732025752d2575202573207c20"),
    unhex("00"),
    string.rep(string.char(0xcc), 31),
    unhex("4c454147554500cc43555000"),
    string.rep(string.char(0xcc), 36),
    unhex("000000001f0000001f0000001c0000003b0000001f0000005a0000001e000000780000001f000000970000001e000000"),
    unhex("b50000001f000000d40000001f000000f30000001e000000110100001f000000300100001e0000004e0100001f000000"),
    string.rep(string.char(0xcc), 32)
})-- Check the whole reader: the ordinal in EDI, temporary lifetime and both UI paths matter.
local PLACES = {
    { 0x032a2b93, "5589e56aff68610c490464a1000000005081eca0000000a1501a520231e88985f0ffffff535657508d85f4ffffff64a3"
        .. "000000008b450831f6898d6cffffff898594ffffff39f00f84bc070000e89827330089c1898568ffffffe84410330089"
        .. "c789bd90ffffff39f70f849a07000089b554ffffff89b558ffffff89b55cffffff578d8d54ffffff89b5fcffffffe8c5"
        .. "03a20089b598ffffff39f70f868a000000eb028d098d858bffffff508d8d84ffffff4651c6858bffffff0089b584ffff"
        .. "ffe83f2d5b008b8d54ffffff8d3c8183c40829cf8d9598ffffff528d8d54ffffffc1ff02e8994d16008b9d58ffffff8b"
        .. "8d54ffffff8d83fcffffff8d0cb939c1741339d8740f6a006a00535051e8d9d2ea0083c41489b598ffffff3bb590ffff"
        .. "ff72828bbd90ffffffeb068b9d58ffffff31f689b570ffffff89b574ffffff89b578ffffff5668630000028d8db8ffff"
        .. "ffc685fcffffff01c785ccffffff0f00000089b5c8ffffffc685b8ffffff00e8b29592ffc685fcffffff0289bd8cffff"
        .. "ff83ff09720ac7858cffffff0900000031ff39b58cffffff0f86fb0100008b8554ffffff29c3c1fb02899d84ffffff89"
        .. "8590ffffffb3036a00686d0000028d8dd4ffffffc785e8ffffff0f000000c785e4ffffff00000000c685d4ffffff00e8"
        .. "429592ff889dfcffffff39bd84ffffff0f86360200008b9590ffffff8b8d68ffffff52e8bb0e330089c685f6752783bd"
        .. "e8ffffff10c685fcffffff020f82610100008b85d4ffffff508d8d98ffffff51e93f0100008d959cffffff5289f1e89a"
        .. "faf0006aff6a00508d8dd4ffffffc685fcffffff04e8cc9192ff83bdb0ffffff10889dfcffffff721d8b859cffffff50"
        .. "8d8d98ffffff51c78598ffffff02000000e8812d92ff837e2c0076636a0168201000028d8dd4ffffffe8789292ff8d95"
        .. "9cffffff5289f1e8ebb8ffff6aff6a00508d8dd4ffffffc685fcffffff05e8639192ff83bdb0ffffff10889dfcffffff"
        .. "721d8b859cffffff508d8d98ffffff51c78598ffffff02000000e8182d92ff83bd8cffffff0176366a0268241000028d"
        .. "8dd4ffffffe80c9292ff6a1468281000028d8dd4ffffffe8fa9192ff6a0268401000028d8dd4ffffffe8e89192ff8d95"
        .. "d4ffffff528d8d70ffffffe8bcc218016aff6a008d85d4ffffff508d8db8ffffffe8d09092ff83bde8ffffff10c685fc"
        .. "ffffff02721d8b8dd4ffffff518d9598ffffff52c78598ffffff02000000e8842c92ff838590ffffff04473bbd8cffff"
        .. "ff0f8220feffff31f68bbd94ffffff83c764566a1289f989bd98ffffffe8426b120089c339f3747f56568d85b8ffffff"
        .. "5089d9e8f436120089d9e8a12c120084c075646a0489d9e8642912006a006a008d8db8ffffff5189d9e8ce36120089d9"
        .. "e8ab29120031f6566a1289f9e8f36a120085c00f840f03000039d8740b6a026a0089c1e86044120046566a1289f9e8d1"
        .. "6a120085c075e2e9ec02000068fc93f001ff1538747d048b8d74ffffff2b8d70ffffffb893244992f7e901ca8b8d98ff"
        .. "ffffc1fa0489d7c1ef1f01d75601ff6a1289b590ffffff89bd84ffffffe8826a120089c3899d8cffffff39f30f845401"
        .. "0000eb028d0939bd90ffffff0f830e0100008bb56cffffff8b86100600008d958cffffff39c20f83880000008b960c06"
        .. "00008d8d8cffffff39ca777889cb8b8e1406000029d3c1fb0239c8754729d0c1f8023dfeffff3f0f87b401000029d140"
        .. "c1f90239c8762d89cad1eabfffffff3f29d739cf730431c9eb0201d139c1730289c1518d8e0c060000e84affa1008bbd"
        .. "84ffffff8b86100600008b960c0600008d1c9a85c074048b0b890883861006000004eb778b8e1406000039c8754d8b96"
        .. "0c06000029d0c1f8023dfeffff3f0f873d01000029d140c1f90239c8762d89cad1eabfffffff3f29d739cf730431c9eb"
        .. "0201d139c1730289c1518d8e0c060000e8d3fea1008bbd84ffffff8b861006000085c07402891883861006000004eb0b"
        .. "6a026a0089d9e8cd4212008b8590ffffff8b8d98ffffff40506a12898590ffffffe82e69120089c3899d8cffffff85db"
        .. "0f85b0feffff8bb56cffffff8b86100600002b860c06000081c60c060000c1f80239c7762e8b8d74ffffffd1e88d14c5"
        .. "0000000029c28b8570ffffff518d0490508d9594ffffff528d8d70ffffffe812d9fb008b8570ffffff3b8574ffffff0f"
        .. "84e30000008b0e3b4e040f84d8000000d9ee8b8d98ffffffd99564ffffff6a00d99568ffffff6a01d99580ffffffd99d"
        .. "84ffffffe88b68120089c385db742d8b138b52588d8564ffffff5089d9ffd28b038b50688d8d80ffffff5189d9ffd2eb"
        .. "4168087eee01ff1568737d048b068b088b118b52588d8564ffffff50ffd2e81f5656008b4018898594ffffffdb8594ff"
        .. "ffff85c07906d805b46dee01d99d80ffffffd98564ffffff8b856cffffffd9901c06000083ec08d9c08d8d70ffffffd8"
        .. "8580ffffffd99d94ffffffd98594ffffffd99020060000d95c2404d91c245156e845ea120083c41083bdccffffff10c6"
        .. "85fcffffff01721d8b95b8ffffff528d8594ffffff50c78594ffffff02000000e8c22892ff8bb570ffffff31ffc785cc"
        .. "ffffff0f00000089bdc8ffffffc685b8ffffff00c685fcffffff0039fe745d8b9d74ffffff39de74368d2424837e1410"
        .. "72198b06508d8d94ffffff51c78594ffffff02000000e86c2892ffc746140f000000897e10c6060083c61c39de75cd8b"
        .. "9570ffffff528d8594ffffff50c78594ffffff02000000e83b2892ff8b8554ffffff89bd70ffffff89bd74ffffff89bd"
        .. "78ffffffc785fcffffffffffffff39f87417508d8d94ffffff51c78594ffffff02000000e8fe2792ff8b8df4ffffff64"
        .. "890d00000000595f5e5b8b8df0ffffff31e9e88e38640089ec5dc20400", "native main-menu news reader" },
    { 0x041b2870, "5589e551568b750831c06aff5051c746140f00000089461089f18985fcffffff8806e83299a1fe89f05e89ec5dc20400", "native headline copy" },
    { 0x03807ee4, "5589e58b55085689ce89d057c746140f000000c7461000000000c606008d78018a084084c975f929f8505289f1e8a343"
        .. "3cff5f89f05e5dc20400", "native text constructor" },
    { 0x02bcbfb9, "5589e58b55088b4210535689ce8b4d0c39c8730b68f46eee01ff1538747d048b5d1029c839d8730289c38b461083c9ff"
        .. "29c139d9770b68e46eee01ff1568737d0485db0f849e000000578d3c1883fffe760b68e46eee01ff1568737d048b4e14"
        .. "39f9731e505789f1e830fdffff8b550885ff7472b810000000394214722a8b0aeb2885ff75ee897e1083f910720e8b06"
        .. "5fc6000089f05e5b5dc20c005f89f05ec600005b5dc20c0089d139461472048b06eb0289f0034d0c53518b4e1001c151"
        .. "e8f1acd10083c40c837e1410897e10720f8b06c60438005f89f05e5b5dc20c0089f0c60438005f89f05e5b5dc20c00", "native string append" },
    { 0x02bcc1c9, "5589e5538b5d0c5689ce8b4d08578b791039df730b68f46eee01ff1538747d048b451029df39f8730289c739ce751f6a"
        .. "ff01df5789f1e872a6e3ff536a0089f1e868a6e3ff5f89f05e5b5dc20c0083fffe760b68e46eee01ff1568737d048b46"
        .. "1439f873288b4610505789f1e81cfbffff8b4d0885ff7468b81000000039411472028b09394614722a8b06eb2885ff75"
        .. "e7897e1083f810720e8b065fc6000089f05e5b5dc20c005f89f05ec600005b5dc20c0089f05701d95150e8e7aad10083"
        .. "c40c837e1410897e10720f8b06c60438005f89f05e5b5dc20c0089f0c60438005f89f05e5b5dc20c00", "native string copy" },
    { 0x02bcc2b9, "5589e5538b5d085689ce85db74598b4e1483f91072048b06eb0289f039c3724783f91072048b06eb0289f08b561001c2"
        .. "39da763383f91072178b068b4d0c5129c3535689f1e8c6feffff5e5b5dc208008b4d0c89f05129c3535689f1e8affeff"
        .. "ff5e5b5dc20800578b7d0c83fffe760b68e46eee01ff1568737d048b461439f8731a8b5610525789f1e80ffaffff85ff"
        .. "745b837e1410722a8b06eb2885ff75f2897e1083f810720e8b065fc6000089f05e5b5dc208005f89f05ec600005b5dc2"
        .. "080089f0575350e8eaa9d10083c40c837e1410897e10720f8b06c60438005f89f05e5b5dc2080089f0c60438005f89f0"
        .. "5e5b5dc20800", "native text assign" },
    { 0x02bcbd56, "5589e56aff68d44b460464a1000000005083ec10535657a1501a520231e8508d85f4ffffff64a30000000089a5f0ffff"
        .. "ff89cf89bdecffffff8b450889c683ce0f83fefe760489c6eb278b5f14b8abaaaaaaf7e689d9d1e9d1ea39d17613b8fe"
        .. "ffffff29c88d341939c37605befeffffff6a018d4601508d8de8ffffff51c785fcffffff00000000c785e8ffffff0200"
        .. "0000e8d1a0ffff894508c785fcffffffffffffffeb4f8b450889a5f0ffffff8985e8ffffff6a0140508d95e4ffffff52"
        .. "c685fcffffff02c785e4ffffff02000000e892a0ffff894508c785fcffffff01000000b83fbebc02c38bbdecffffff8b"
        .. "b5e8ffffff8b5d0c85db741a837f141072048b07eb0289f853508b450850e806", "native string allocation" },
    -- Observe the field read, not the entry MLTransfers hooks. MLNews never calls that function.
    { 0x0381e39c, "8b9614030000c1ea073a550f", "primary-user control field" },
    { 0x0381e428, "5589e58b450825ff3f00003d8d020000771169c0200500008d8408e01b480085c075068d8120e35f005dc20400", "indexed club slots" },
    { 0x0381e458, "5589e556668b750831c08d91802e550066393274194081c2240200003d2c01000072ed8d8140e85f005e5dc2040069c0240200008d8408802e55005e5dc20400", "indexed competition scan" },
    { 0x038225a7, "5589e583ec0853668b5d08b828230000898df8ffffff6639c3731e0fb7d369d24c02000066399c0a4c156f008d840a4c"
        .. "156f00750485c0757356578db12cd5bf008db94c156f006a00c64508008b4d08518d95fcffffff520fb7c356578985fc"
        .. "ffffffe883efffff83c41439f07405663918743631c031c989fa66391a74184181c24c02000081f92823000072ec5f5e"
        .. "5b89ec5dc204008b85f8ffffff69c94c0200008d84014c156f005f5e5b89ec5dc20400", "match table layout" },
    { 0x03822433, "5589e583ec085689ce8b86e0ec5f0069c020050000578b7d08578d8c30e01b4800518d96e01b480052e884feffff83c4"
        .. "0c8985fcffffff85c0754c5381e7ff3f000081c6402455008d58028d85f8ffffff5089f1e8e63ee5ff8b0089c181e1ff"
        .. "3f000039f97510334508a900c0ffff750689b5fcffffff81c6200500004b75cb8b85fcffffff5b5f5e89ec5dc20400", "club table layout" },
    { 0x03822ab9, "5589e551538b5d08b8ffff00005689ce6639c3745f83be0814ec0002750e53e87bb9ffff5e5b89ec5dc204008b96e8ec"
        .. "5f0069d224020000570fb7cb6a00c64508008b450850898dfcffffff8d8dfcffffff8dbc32802e5500518d96802e5500"
        .. "5752e806eaffff83c41439f85f740566391874068d8640e85f005e5b89ec5dc20400", "competition table layout" },
    { 0x038566ec, "5589e55657e8ef59fcff8b48308bb1e8ec5f0031c085f6741c8b55080fb73a8d91802e550066393a74144081c2240200"
        .. "0039f072f05fb8060000005e5dc357e889c3fcff8b405c5f5e5dc3", "competition format kind" },
    { 0x0385662c, "5589e5535657e8ae5afcff8b48308bb1e8ec5f008b5d0831c085f674190fb73b8d91802e550066393a74134081c22402"
        .. "000039f072f0668b035f5e5b5dc357e849c4fcff89c10fb7414ebaffff00006639d075030fb7015f5e5b5dc3", "competition parent link" },
    { 0x038ae451, "5589e583ec0856e888dcf6ff8b40300fb788b0cbc2000fb790b2cbc2008b75088d85fcffffff898dfcffffff508d8df8"
        .. "ffffff51568995f8ffffffe83bffffff83c40c89f05e89ec5dc3", "career date layout" },
    { 0x0251d454, "0c000000", "Master League mode 19" },
    { 0x0251d4a8, "0c000000", "Master League mode 40" },
}

local enabled, last_snapshot, last_second = false, nil, nil
local REASONS = {
    [0] = "waiting for a native ticker copy (empty feed or different UI path)",
    [1] = "menu pointer unavailable", [2] = "not a supported ML mode",
    [3] = "career pointer unavailable", [4] = "unsupported table lookup mode (expected 0/1/2)",
    [5] = "invalid career clock", [6] = "unsupported club count (1-651)",
    [7] = "unsupported competition count (1-300)",
    [8] = "primary controller-slot-0 club missing, invalid or ambiguous",
    [9] = "no eligible recent AI league/cup result (0-14 days; date/club/name/score filters)",
    [10] = "text formatting failed", [11] = "result selected, copy not completed",
    [12] = "prefix copied into native string; final rendering NOT verified",
}

local function u32(s, at)
    local a, b, c, d = string.byte(s, at, at + 3)
    return a + b * 256 + c * 65536 + d * 16777216
end

-- Observe our own diagnostic block only; returning nil must not change a CPK key.
function m.observe(ctx, filename)
    if not enabled then return end
    local now = type(os) == "table" and type(os.time) == "function" and os.time() or nil
    if now ~= nil and now == last_second then return end
    last_second = now
    local s = memory.read(STATE, STATE_SIZE)
    if type(s) ~= "string" or #s ~= STATE_SIZE then
        if last_snapshot ~= "unreadable" then log("MLNews 4 runtime: diagnostic state unreadable; restart and send this log.") end
        last_snapshot = "unreadable"
        return
    end
    if s == last_snapshot then return end
    last_snapshot = s
    local selected, lookup = u32(s, 37), u32(s, 45)
    log(string.format("MLNews 4 runtime: copies=%u attempts=%u copied=%u; last=%s; "
        .. "year=%u day-index=%u clubs=%u comps=%u primary=%u selected=%s mode=%u lookup=%s",
        u32(s, 1), u32(s, 5), u32(s, 9), REASONS[u32(s, 13)] or "unknown stage",
        u32(s, 17), u32(s, 21), u32(s, 25), u32(s, 29), u32(s, 33),
        selected == 4294967295 and "none" or tostring(selected), u32(s, 41),
        lookup == 4294967295 and "unread" or tostring(lookup)))
end

function m.init(ctx)
    log("MLNews 4: up to four league/cup results, 14 days, every native ticker item; emulator only")
    local good = true
    for _, place in ipairs(PLACES) do
        local same = memory.read(place[1], #place[2] / 2) == unhex(place[2])
        log(string.format("check: %-30s at %08x  %s", place[3], place[1],
            same and "as expected" or "DIFFERENT or unreadable"))
        if not same then good = false end
    end
    local empty = memory.read(CAVE, SIZE) == string.rep("\0", SIZE)
    log("check: news cave at 03fc8900  " .. (empty and "empty" or "NOT EMPTY or unreadable"))
    local state_empty = memory.read(STATE, STATE_SIZE) == string.rep("\0", STATE_SIZE)
    log("check: news diagnostics at 0298c2f0  " .. (state_empty and "empty" or "NOT EMPTY or unreadable"))
    if not good or not empty or not state_empty or #CODE ~= SIZE then
        log("RESULT: nothing written. Code/layout or free memory differs; restart and send this log.")
        return
    end
    local data = string.rep("\0", 36) .. string.rep(string.char(0xff), 4) .. string.rep("\0", 4)
        .. string.rep(string.char(0xff), 4)
    memory.write(STATE, data)
    if memory.read(STATE, STATE_SIZE) ~= data then
        log("RESULT: a change did not go in (news diagnostics). The native hook is untouched; restart and send this log.")
        return
    end
    memory.write(CAVE, CODE)
    if memory.read(CAVE, SIZE) ~= CODE then
        log("RESULT: a change did not go in (news cave). The native hook is untouched; restart and send this log.")
        return
    end
    local call = unhex(CALL)
    memory.write(SITE, call)
    if memory.read(SITE, #call) ~= call then
        local old = unhex(OLD)
        memory.write(SITE, old)
        local restored = memory.read(SITE, #old) == old
        log("RESULT: a change did not go in. " .. (restored and "Hook restored. " or "Hook restore failed. ")
            .. "Quit PES without saving, remove the module, send this log.")
        return
    end
    enabled = true
    if type(ctx) == "table" and type(ctx.register) == "function" then
        ctx.register("livecpk_make_key", m.observe)
        ctx.register("after_set_conditions", m.observe)
    else
        log("MLNews 4: no runtime observer registered by this host; native hook is still installed.")
    end
    log("RESULT: installed. Up to four recent AI league/cup results rotate across native ticker items when available. "
        .. "Runtime diagnostics enabled; a copied string is not rendering proof. Verify WORLD RESULT on a backup save.")
end

return m
