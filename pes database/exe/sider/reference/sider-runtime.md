# Sider API and patch memory reservations

[Sider developer guide](../README.md) · These are versioned implementation notes and test observations. For current settings and deployment, use the guide and shipped Lua files. Paths and commands assume the `sider` directory unless noted.

## What was looked at in `sider.dll`

Read from the DLL's code and strings, not run:

- A module must return a table with an `init(ctx)` function. It gets these names:
  `log`, `memory` (`read`, `write`, `search`, `pack`, `unpack`), `string`, `table`,
  `math`, `pairs`, `ipairs`, `tostring`, `tonumber`, `type`, `unpack`, `assert`,
  `error`, `os` (`time`, `clock`, `date`), `audio`; with `luajit.ext.enabled` also
  `ffi`, `bit`, `require`. There is **no `pcall`**: an error in `init` makes Sider skip
  the module and log the error.
- **`io` is among them** (`0x10003610`: thirteen names are copied from Lua's own globals
  into what a module sees, `io` is the last; `os` is a new table with three functions).
  So a module can read and write files. `ctx.sider_dir` (the folder of `sider.exe`, made
  from a wide string into UTF-8) and `ctx.register(event, function)` are put into `ctx`
  at `0x10003590`.
- `ctx.register` (`0x10002c70`) knows 21 events, all about files, a match, the edit mode
  or the replay gallery. **None for a key, the pad or a menu.**
- `livecpk_make_key` (used by `MLSimToDate.lua` 2 as a clock tick): the three places
  where Sider is called when the game looks for a file (`0x10007f20`, `0x10008130`,
  `0x100082c0`; installed only with `livecpk.enabled = 1` and when Sider finds the
  game's code for it) first ask a list of earlier lookups, by the address and the name
  of the file (`0x10010cb0`; only with `address-cache.enabled = 1`). A lookup that is in
  the list does not reach Lua. Any other, with `lua.enabled = 1`, goes through every
  module that registered `livecpk_make_key` or `livecpk_get_filepath` (`0x10007ca0`) and
  calls its `livecpk_make_key` function with `ctx` and the file name (`0x100078c0`), in a
  protected call: an error there is logged (`lua ERROR`) and does not stop the game. A
  function that returns nothing gives an empty key; with no `livecpk_get_filepath`
  function the module then names no file and Sider goes on to the next module.
- `memory.read(address, count)` makes the pages readable and writable
  (`VirtualProtect`), copies the bytes, and asks for the old protection back with a
  call that Windows refuses (no place for the old value is passed). So **a read leaves
  the touched pages marked writable**. No byte changes. Every Sider module that reads
  memory does the same.
- `memory.write(address, bytes)` does the same and copies the other way, so it can
  change code. That is the route for the tuning modules. It gives the pages the
  protection "read, write, execute" (`0x40`) before the copy; if Windows refuses that,
  the module stops with an error and Sider skips it.

## Notes for the next module

- The exe has a fixed load address (no relocation table, no dynamic base), so the
  addresses of `MASTER_LEAGUE.md` are valid in the running game. `MLCheck.lua` tests
  exactly this.
- The level values are single bytes inside `mov eax, value` instructions; 68 and 9,000
  of the fee formula are numbers inside two instructions; 0.00027 is a constant with
  one user. All four can be changed in place.
- **The 2.2 of the fee formula is a shared constant** (`0x01f0f2b8`, 16 references in
  the exe). It must not be changed in place; the fee function has to be pointed to a
  constant of its own. (`MLMoney.lua` does not need it: its routine sets the factor of
  the salary part to 0 in the function's own stack frame.)
- Free memory for code and tables: `0x047b0200`-`0x047b0fff`, the end of `.trace`
  (3,584 bytes; `MLMoney.lua` uses the first 3,568), and below it `0x047b0060`-`0x047b01fd`
  (`MLSimMatch.lua` version 9 uses `0x047b0060`-`0x047b01f4`, 405 bytes, for cards + injury call;
  `0x047b0124`-`0x047b01fe` was used by version 5 of `MLMoney.lua` only). The end of `.xcode`,
  `0x047d3a43`-`0x047d3fff` (`MLSimMatch.lua` version 9 uses `0x047d3a50`-`0x047d3f06`,
  1,207 bytes, for code and `0x047d3fa0`-`0x047d3fff`, 96 bytes, for its v5–v7 config & positional/GK tables;
  previously used by version 6 of `MLMoney.lua` and version 1 of `MLTransfers.lua` at
  `0x047d3c40`-`0x047d3dbc`). The page of `.data1` behind its code,
  `0x047d4170`-`0x047d4fff`: `MLSimMatch.lua` version 9 uses `0x047d4170`-`0x047d41ff`
  (144 bytes) for v1–v3 config/tables; `MLTransfers.lua` versions 3 and 4 use all of
  `0x047d4200`-`0x047d4fff` (version 2: up to `0x047d4f5f`; one window was played with
  it and that part was left alone. The last 160 bytes are zero in the file and were not
  yet used in the game). The v5 config of `MLSimMatch.lua` was first put at
  `0x047d4f60`-`0x047d4f7f`, inside what `MLTransfers.lua` version 3 uses; the two could
  not be installed together, so it was moved to the end of the `.xcode` page (`0x047d3fa0`-`0x047d3fff`, 96 bytes for v7).
  `.reloc` and `.link` RX page tails hold `MLSimMatch.lua` version 9's
  `eff_strength` + `player_eff_ovr`/`gk_eff_ovr` + ET + outcome + score + `sim_vec`
  code reservation (`0x047d5040`-`0x047d5b8b`, 2,892 bytes) and separate 2D
  scoreline/draw CDF tables (`0x047d5be0`-`0x047d5ffd`, 1,054 bytes). It checks and
  writes these separately: **`0x047d5b8c`-`0x047d5bdf` belongs to Growth**, not the
  simulator. PK + `card_adj` + fatigue + injury use `0x047d6030`-`0x047d6376`
  (839 bytes). The generators enforce these bounds, including the adjacent Growth code.
  `MLTransfers.lua` uses `0x047d6400`-`0x047d654f` (336 bytes, position need),
  `0x047d6550`-`0x047d6d3f` (2,032 bytes, incoming offers), and
  `0x047d6d40`-`0x047d6e4f` (272 bytes, squad pressure).
  `MLSimToDate.lua` uses `0x047d6f60`-`0x047d6fec` (141 bytes) for its day-loop hook.
  With Growth below, the ranges still free after the transfer code are
  `0x047d6f4c`-`0x047d6f5f` (20 bytes) and `0x047d6fed`-`0x047d6fff` (19 bytes).
  **`0x047d6d60`-`0x047d6e4f` is not free**; old allocation notes understated the
  current incoming/pressure sizes.
  `MLSimToDate.lua` version 3 had its calendar block (`0x900` bytes: the Schedule poll,
  the selection, the heading and their strings) at `0x047d6550`-`0x047d6e4f`, which is why
  the two modules could not be installed together; version 4 moved it to an unused run of
  8,196 zeros in `.trace`, `[0x03fc7d9c, 0x03fc9da0)` (exclusive end; the first four
  zeros finish a padding NOP, and the next function starts at `0x03fc9da0`), where it
  takes `0x03fc8000`-`0x03fc88ff`. `MLMoney.lua` uses `0x03fc9300`–`0x03fc943f` for budget keys.
  `MLGrowth.lua` uses what is left: `0x047d3f07`-`0x047d3f9c` (the season award, 150
  bytes, three bytes short of `MLSimMatch.lua`'s v7 tables), `0x047d5b8c`-`0x047d5bde`
  (the age curve, 83 of the 84 bytes between `MLSimMatch.lua`'s hook code and its
  scoreline tables), `0x047d6377`-`0x047d63f6` (the v5 exp award, 128 bytes, up to
  `MLTransfers.lua` version 6), `0x047d6e50`-`0x047d6efd` (the season walk and the
  award arithmetic, all 174 bytes before the training-focus code),
  and `0x047d6efe`-`0x047d6f4b` (the training scale, 78 bytes, still 20 short of
  `MLSimToDate.lua`'s hook).
  `MLSimToDate.lua` also
  checks and uses `0x0298c0e0`-`0x0298c1ff` in the writable, zero-filled `.text` stub
  for its state, and `MLGrowth.lua` checks and uses the page tail behind it,
  `0x0298c200`-`0x0298c2eb` (236 bytes of tables; `.text` holds `0x200` bytes at
  `0x0298c000`, the rest of its last page is zero-filled by the loader). A module must
  see zeros in its ranges before it writes.
- A plan record (`MASTER_LEAGUE.md` 9.1) has spare bytes at `+0x109`-`+0x10b`; `MLTransfers.lua`
  version 6 uses the first two. Do not store anything in the low 7 bits of a slot word: the
  game uses them.
- A routine that is called from inside a game function can read the arguments of that
  function's caller through the saved `ebp`, if it first checks the return address.
  The routine of `MLTransfers.lua` does this to get the club level without changing a
  call, and reads the locals of the function it is called from (date, pool, player) the
  same way.
