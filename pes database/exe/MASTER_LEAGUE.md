# PES 2017 Master League: developer guide

Use this guide to find **what the stock game does**. For **what the mods change**, their settings and install order, start with the [Sider guide](sider/README.md). Addresses refer to the repository's 32-bit `PES2017.exe`, not to every PES 2017 build.

## Find a subsystem

The section numbers used in code comments and older notes are unchanged. Open the chapter containing the number you need; each retains the function addresses, record fields, worked examples and evidence behind the findings.

| Sections | Reference | Use it for |
|---|---|---|
| 1–2 | [Runtime and verification](reference/runtime.md) | Mode selector, record layouts, RNG, career start and checks 7–11 |
| 3–5 | [Day, calendar and fixtures](reference/season.md) | Day loop vs Skip Match, event dates, match-day links, scores and league pairing algorithm |
| 6 | [Finance](reference/finance.md) | Salary, transfer fee, popularity, wage bill, prize tables and yearly budget step |
| 7–9 | [Recruitment](reference/recruitment.md) | User negotiations and contract years, scouts, AI squad plans, candidate filters, offers and deal completion |
| 10–13 | [Players, teams and save data](reference/players-save.md) | Team strength and roles, Team Spirit (§12.1), growth (§12.2), save container and packed players (§13) |
| 14–15 | [Open questions and investigation commands](reference/research.md) | Unresolved meanings, candidate routines and how to follow a call |
| A–G | [Lookup tables](reference/tables.md) | Day steps, career classes, January calendar, season kinds, roles, event callers and a full 20-team schedule |

## What to verify before using an offset

- **Check the mode.** `0x026503e0` points to the mode object; its `+0x30` points to mode data. The selector is separate: mode numbers 19 and 40 map to kind 12 (Master League). A valid pointer alone does not identify a career.
- **Distinguish IDs from slots.** A match lookup checks the record's own number (`0xffff` marks a free slot). A competition ID is **not** its array position. Look up clubs using the appropriate table mode; indexed tables can contain holes. Sider's home/away team numbers are already decoded, unlike packed career club IDs.
- **Use the right date and score fields.** In memory `+0xc2cbb0` is a **u16 day index** and `+0xc2cbb2` a **u16 year**. A fixture stores year/month/day; check bit 14 of its flags before treating the score as a result. An unplayed fixture is not a 0–0 draw.
- **Keep disk and memory layouts separate.** The ranking block has a known offset relationship; it is not a file-wide conversion. Player records in the four [sample saves](ML%20saves/) are compressed in chunks. Work on copies and check container hashes.

## What “proven” means here

The [reference checks](reference/runtime.md) compare native machine code under emulation with independent Python implementations: salary (3,000 cases, excluding awards/title bonuses), transfer fee (3,000), calendar events (8,928 day cases), two-leg league pairings (2–24 teams), and the AI rating window (club levels 0–9). Matching these outputs does **not** establish which inputs a live career supplies. The notes distinguish **read** (C/disassembly inspected), **inferred** (purpose deduced) and **located** (routine identified only) from tested behavior. The live evidence is narrower: MLCheck matched six checks at the expected addresses, and [one player’s displayed fee matched the formula](reference/finance.md). Neither establishes a whole-career result.

From `pes database/exe/tools`, with `unicorn` and `capstone` installed:

```sh
python3 check_findings.py /path/to/PES2017.exe '../../EDIT00000000 (pes 2017 updated)'
python3 find.py show salary
python3 find.py callers 0x038ac66e
```

Start with the [function index and decompiler limits](README.md) before interpreting guessed C types or missing virtual calls. For a new finding, record the build, address, assumptions, and a case that distinguishes the proposed rule from the old one.
