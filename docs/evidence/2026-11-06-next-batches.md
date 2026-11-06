# Bonus types, more spells, healing and the character record: checks, 2026-11-06

What was checked for the branch that merges the bonus types, the further spells and the first
healing version, and for the display fixes on top, and what was not.

## Install checks

- Offline tests (`tests/run_tests.py`, WeiDU 249, made-up games): 42 of 42 passed.
- Real installs with WeiDU on real data, in two disposable labs: BG2:EE 2.7.3.0 + EEex v1.3.1, and
  EET with EE Fixpack: `SUCCESSFULLY INSTALLED`, no warnings in either.

## In-game checks

`tests/lab/run_batches.py` drove a hidden, muted lab game (same lab, test party and arena as the
earlier rounds). 82 checks passed; the guards stayed clean; nothing was saved. Three of them first
failed through an error in the test: a negative save value wraps to the worst save. The test
changed, the mod did not, and that group ran again on its own, 20 of 20.

| Group | Checks | What it shows |
|---|---|---|
| Haste, Slow, Improved Haste | 6 | They cancel each other as decided; Improved Haste ends Slow and keeps it out |
| Earlier spell groups | 30 | Curse, control, Strength of One, Magic Resistance, images, Mordenkainen's Sword, new spells, Breathless, insects, nature, fiends |
| Bonus types | 21 | Stacking by type and family, also through wrapped effects; Pierce Magic runs once |
| Sequencer | 4 | Dispelling Screen in the Spell Trigger list: once, with its own icon and description; it can be chosen and fires |
| Record | 20 | See below |
| Smoke | 1 | 148 changed spells cast once, the game kept answering |

## The character record

A full audit of what the record shows for every spell (1,673 spells, all rows of STATDESC.2DA),
by two independent read-only passes. One pass got row numbers wrong, so disputed cases were
measured in the game from the list the record itself uses.

- The Contingency, Spell Sequencer and Spell Trigger lists swap a spell for the rows of the 2DA of
  the same name, whatever the spell does. Dispelling Screen showed eight times. It now has one row,
  itself.
- Fixed, measured in the game: Pierce Magic, Divine Power, Faerie Fire, the insect spells,
  Hopelessness, Strength of One, Greater Restoration.
- Fixed, checked offline only: Sphere of Chaos, Nature's Beauty, Chromatic Orb, Protection From
  Acid, Wild Slow.

Errors of the base game are not touched here and are listed for a decision.

## Not checked

- Touch delivery of Cause Wounds and Harm in the game.
- Fiends in a fight, party-wide delivery of area buffs, Nahal's Reckless Dweomer's changed target.
- The Contingency and Spell Sequencer screens after the fix: they share Spell Trigger's list, and
  Contingency was opened before it.
- IWDification spells under the bonus types, and interplay with Rebalance's True Time Stop.
- Nothing was launched in EET, and nothing ran together with Spell Revisions.
