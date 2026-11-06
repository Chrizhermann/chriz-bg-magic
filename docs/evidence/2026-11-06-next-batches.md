# Bonus types, more spells, healing and the character record: checks, 2026-11-06

What was checked for the branch that merges the bonus types, the further spells and the first
healing version, and for the display fixes on top, and what was not.

## Install checks

- Offline tests (`tests/run_tests.py`, WeiDU 249, made-up games): 46 of 46 passed.
- Real installs with WeiDU on real data, in two disposable labs: BG2:EE 2.7.3.0 + EEex v1.3.1, and
  EET with EE Fixpack: `SUCCESSFULLY INSTALLED`, no warnings in either.

## In-game checks

`tests/lab/run_batches.py` drove a hidden, muted lab game (same lab, test party and arena as the
earlier rounds). 117 checks passed; the guards stayed clean; nothing was saved. Two of them first
tested Exaltation on an enemy, which the spell turns away, so they said nothing about the fix.
The test now uses a party member, the mod did not change, and that group ran again on its own,
34 of 34.

| Group | Checks | What it shows |
|---|---|---|
| Haste, Slow, Improved Haste | 6 | They cancel each other as decided; Improved Haste ends Slow and keeps it out |
| Earlier spell groups | 30 | Curse, control, Strength of One, Magic Resistance, images, Mordenkainen's Sword, new spells, Breathless, insects, nature, fiends |
| Bonus types | 21 | Stacking by type and family, also through wrapped effects; Pierce Magic runs once |
| Sequencer | 4 | Dispelling Screen in the Spell Trigger list: once, with its own icon and description; it can be chosen and fires |
| Record | 34 | See below |
| Live | 21 | Entries that follow a state, see below |
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

Errors of the base game, fixed in the same round:

- Names, measured: Wraithform, Spell Deflection, Stinking Cloud; rows 55, 8 and 112 now say Stunned,
  Blinded, Deafened. Offline only: Protection From Good, Shadow Form, Defensive Stance, wild Minor
  Globe, Mimic Web.
- Missing entries, measured: Blur, Physical Mirror. Offline only: Divine Favor, lowered resistances,
  Symbol: Pain, Selune's Blessing, Wish outcomes, confusion from Jester and False Dawn.
- Lifetimes, offline only: Death Ward, Enhanced Bard Song, Conjure Fire Elemental, Salt Crystals,
  Dolorous Decay.
- Cures, measured: Exaltation, Slow Poison, Neutralize Poison, Heal and Remove Paralysis clear what
  they cure.

Entries that follow a state (`lua/M_CBMREC.lua`, a deferred EEex listener, no spell changes):

- Invisible, Improved Invisibility, Sanctuary, Mirror Image, Reflected Image: listed while the state
  lasts, also from effects that are no spell, gone when it ends.
- Shield of the Archons, Minor Spell Deflection, Minor Spell Turning: the entry takes the spell's own
  name. Opcode 169 does not keep a native row off, so the listener renames the list entry, on every
  pass, as the engine brings its row back whenever it rebuilds the list. The Record itself was read
  for Shield of the Archons: right text, right icon.

## Not checked

- Invisibility and Sanctuary broken by an attack: attacks do not land in the arena. The state ending
  was measured through removal and a reveal effect.
- A deflection spell's own name beside the big spell at the same time: the big spell's row stays then.
- Touch delivery of Cause Wounds and Harm in the game.
- Fiends in a fight, party-wide delivery of area buffs, Nahal's Reckless Dweomer's changed target.
- The Contingency and Spell Sequencer screens after the fix: they share Spell Trigger's list, and
  Contingency was opened before it.
- IWDification spells under the bonus types, and interplay with Rebalance's True Time Stop.
- Nothing was launched in EET, and nothing ran together with Spell Revisions.
