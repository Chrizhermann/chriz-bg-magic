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
- SCS-style arcane changes: Chromatic Orb (IWD progression without +6 save bonus), Melf's
  Minute Meteors (+2 enchantment), Skull Trap (12d6 cap), Lower Resistance (30% + 1%/level,
  power 5), Power Word Silence/Stun/Blind/Kill (school Enchantment; Stun blocked by Free
  Action; Blind single-target), Mantle/Improved Mantle/Absolute Immunity (+3/+4/+6 weapon
  protection), Project Image and Simulacrum slot restrictions, Abi-Dalzim's Horrid Wilting
  immunities (undead, golems, animated swords, air/earth/fire elementals), party-friendly
  Wizard Symbols (with Free Action immunity on Symbol, Stun), and alignment-based fiend
  summoning for Cacofiend, Summon Fiend, and Gate.
- SCS-style divine changes: Blade Barrier (casting time 6, enemy-only, save for half),
  Globe of Blades (enemy-only, save for half), Call Lightning (1 round/level up to 11
  bolts), Defensive Harmony (cleric-only, +4 AC), Glyph of Warding (casting time 5, save
  for half), Magical Stone (3d4 crushing, 6d4 vs. undead), Priest Gate (alignment-based
  fiends), party-friendly Priest Symbols (with Free Action immunity on Symbol, Stun),
  Summon Insects/Insect Plague/Creeping Doom (per-round breath save vs. spell failure,
  countered by Fire Shields, Stoneskin, and normal-weapon immunity, undead immune), and
  Nature's Beauty (schoolless blindness subspells: permanent on failed save, 3 rounds on
  successful save).
- Descriptions that named the old behaviour are updated (English).
- Installer frame for BG2:EE and EET, shared library, and the exported list of decided
  changes (`docs/build-list.json`) with its generator. With Spell Revisions installed the
  installer warns that the two do not go together.
