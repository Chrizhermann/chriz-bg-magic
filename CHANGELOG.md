# Changelog

## Unreleased

- Spirit Armor: a new casting replaces the old one, so its save bonus and its expiry
  damage no longer stack with themselves.
- Minor Spell Deflection stops only spells up to level 4 (was 7).
- Fireball, Delayed Blast Fireball, Sunfire, Cone of Cold, Flame Strike, Skull Trap, Glyph
  of Warding, Incendiary Cloud and Lightning Bolt: save vs. breath instead of vs. spell,
  without extra penalties.
- Damage wakes creatures put to sleep by Sleep, Color Spray, Stinking Cloud, Command,
  Greater Command and Emotion: Hopelessness (Power Word: Sleep does so already).
- Web: save vs. breath instead of vs. spell (the -2 stays); spiders, amorphous creatures,
  dragons and the very obvious flying and incorporeal creatures are immune.
- Arcane kept/decided changes: Invisibility (8 hours), Luck (15 rounds, self-refreshing),
  Clairvoyance (indoor/outdoor backstab immunity for 3-10 rounds), Invisibility 10' Radius
  (casting time 1, 1 turn), Confusion (4/5/6 rounds at levels 1/15/20), Universal school for
  Minor Sequencer, Contingency, Spell Sequencer, Spell Trigger and Chain Contingency,
  Teleport Field (Save vs. Spell at -4), Oracle (dispels illusions up to level 9 in a 30-ft
  radius), and Sphere of Chaos (5-outcome 1-round table with Save vs. Spell at -4).
- Divine kept/decided changes: Bless (casting time 5), Shillelagh (druid-only), Doom
  (casting time 1, -2 damage, Save vs. Spell scaling 0 to -4), Faerie Fire (new level-1
  druid spell via `ADD_SPELL`), Silence 15' Radius (enemies only), Free Action (usable by
  druids, 1 turn/level, Stun protection, allows Haste), Neutralize Poison (cures poison +
  1 turn/level poison immunity), Holy Power (casting time 4, fighter APR for non-fighter
  clerics), Iron Skins (renamed Stoneskin, casting time 1), Mass Regenerate (new level-5
  druid spell via `ADD_SPELL`), and Regenerate (druid-only, 2 HP/s for 1 round/level,
  self-refreshing).
- Descriptions that named the old behaviour are updated (English).
- Installer frame for BG2:EE and EET, shared library, and the exported list of decided
  changes (`docs/build-list.json`) with its generator. With Spell Revisions installed the
  installer warns that the two do not go together.
