# The move to overwriting: checks, 2026-11-07

What was checked when the mod stopped patching at install and started writing its resources whole.

## How the definitions were made

The old patch version was installed twice in the EET lab (EET with EE Fixpack, EEex v1.3.1): once
as it is, once after a helper mod had moved every number an install assigns. Comparing the two
runs showed which fields depend on the install: strings, SPLPROT rows, record rows, sectypes and
spell states. No byte in 595 files stayed unexplained. The result became `defs/`.

## Checks

- Offline tests (`tests/run_tests.py`, WeiDU 249, made-up games), including: the build is in sync
  with `defs/`; reading and writing round-trips; a spell edited by hand, with other text, with
  other effect counts, of garbage bytes, or missing ends up exactly as defined; install numbers
  follow the game's tables; other languages keep their descriptions.
- Real installs in three labs: BG2:EE, EET with EE Fixpack, BG2:EE with IWDification's spell
  packs. About 8 seconds each, no warnings.
- EET: every file of the old patch run compared by content with the new install. All equal, apart
  from the numbers of the four projectiles, which an install assigns.
- In-game, hidden lab game, plain BG2:EE with the new install: 118 of 118 checks, including 148
  changed spells cast once.
- In-game, BG2:EE with IWDification: 43 of 43 in the groups `attacks` and `bonus`, the first run of
  the bonus types on real IWD spells. Extra attack, measured: Righteous Wrath alone gives 2 attacks;
  with Haste its bonus goes to 0 and only Haste counts; it comes back when Haste ends; beside
  Improved Haste one of the two counts.
- After the first run: the definitions came from EET with EE Fixpack and named their files, which
  plain BG2:EE lacks. Spells then lost their cures, Chromatic Orb its effects, and Find Familiar
  summoned nothing. The in-game run could not show Find Familiar: it is left out of the cast-once
  list. Now the mod brings 28 helpers of its own (`CBH*`), Find Familiar is written field by field,
  and four strings with EET-only numbers are text. Every spell and EFF a definition delivers was
  checked against plain BG2:EE's files; none is missing. Then again 118 of 118 in plain BG2:EE,
  155 changed spells cast once, and clean installs in all three labs.
- The old patches compared between plain BG2:EE and EET: three changes had silently failed in EET
  because EE Fixpack builds those spells differently (Remove Paralysis, its cure sub-spell, Mimic
  Web). They are in `defs/` now.

## Not covered

- Spell Revisions, SCS and the rest of the Chriz Easy BG stack on top of the new install.
- Nothing was launched in EET.
- IWDification's Blood Rage does not land on the lab party, so its place in the Transformation
  family is covered offline only. The cause was not found: the spell carries two conditions of
  its own, and it is unchanged by this mod apart from its bonus types and family rows.
- See `docs/evidence/2026-11-06-next-batches.md` for what was already open.
