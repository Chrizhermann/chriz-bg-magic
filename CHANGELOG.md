# Changelog

## Unreleased

- Selected spells now use Morale, Favor, Luck, Dodge, Deflection and Curse bonus types.
  EEex compares each statistic separately: a type contributes its strongest bonus and
  strongest penalty, while different types and untyped effects combine. Weaker effects
  resume when stronger ones expire. Spell and scroll descriptions identify typed values.
- Typed spells refresh themselves on recast, including their linked payloads. Shared
  external effects are isolated before patching. Optional IWD spells are found by symbol
  and skipped with an informational line when absent.
- Transformation and Regeneration spells form separate exclusive families: higher spell
  level wins; a new casting replaces an equal-level member. These rules work without EEex.
- With EEex installed, Pierce Magic reduces current Magic Resistance by half, rounded down
  and limited to 10-40 percentage points, for 5 rounds. Its other effects stay unchanged.
  Without EEex at installation, its existing resistance effect is retained.
- Added offline installer and LuaJIT/Lua 5.3 tests, plus the disposable-lab `bonus` group.
  Live acceptance remains pending. HP and extra-attack type comparisons remain deferred.
- Healing: Cure Light, Moderate (IWD), Medium, Serious and Critical Wounds now use the
  decided dice rolls and casting times; Mass Cure casts in 4. Cause Wounds uses the matching
  rolls and heals undead instead of damaging them while preserving direct and touch-charge
  delivery. Optional IWD Mass Cause Light Wounds also heals undead; Harm casts in 7 and
  heals undead completely. Changed spell and scroll descriptions match the new behavior.
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
- Find Familiar, Wish, Minor Sequencer, Contingency, Spell Sequencer, Spell Trigger and
  Chain Contingency: school set to Universal (no specialist mage exclusions on spells or
  scrolls).
- Cloudkill, Death Fog, Stinking Cloud, Web and Incendiary Cloud: school set to Conjuration
  (Diviner exclusion on spells and scrolls).
- Grease: save vs. breath (+2 bonus kept); flying, incorporeal and dragon creatures are
  immune.
- Stinking Cloud: undead, golems, elementals and slimes are immune.
- Power Word: Sleep: school set to Enchantment (Invoker exclusion on spell and scrolls);
  elves and half-elves resist (90% / 30%); undead, dragons and elementals are immune.
- Spook and Horror: undead are immune, and creatures with True Seeing are immune to Spook.
- Mirror Image and Reflected Image no longer stack with each other or themselves.
- Area-of-effect damage from area projectiles bypasses Mirror Image.
- Dispel/Remove Magic checks magically created weapons by the same caster-level roll as
  other effects.
- Magic Resistance adds to existing magic resistance instead of setting it, and refreshes
  itself on recast.
- Strength of One no longer lowers a party member's Strength if already 18/75 or higher.
- Blindness: duration scaled to 1 round per 2 caster levels (2 to 5 rounds).
- Finger of Death (wizard and priest): save vs. death without penalty on the slay effect.
- Disintegrate destroys Mordenkainen's Sword without a save.
- Entangle: save vs. breath (+3 bonus kept); flying, incorporeal, elemental, giant and
  dragon creatures are immune.
- Flame Blade: restricted to druids and rangers, and its blade counts as a +1 magical
  weapon.
- Conjure Fire, Air and Earth Elemental (wizard and priest): 12/16/24 HD probabilities
  scale with caster level.
- Barkskin, Animal Summoning I-III and Conjure Animals: restricted to druids and rangers.
- Faster casting times on Bless, Flame Strike, Heal, Blade Barrier, Bolt of Glory, Magic
  Resistance, Righteous Magic, True Seeing, True Sight, Glyph of Warding, Invisibility
  Purge, Strength and Fire Seeds.
- Arcane kept/decided changes: Invisibility (8 hours), Luck (15 rounds, self-refreshing),
  Clairvoyance (indoor/outdoor backstab immunity for 3-10 rounds), Invisibility Sphere
  (renamed from Invisibility, 10' Radius, casting time 1, 1 turn, ally-only radius 110 via
  `ADD_PROJECTILE`), Confusion (4/5/6 rounds at levels 1/15/20), Universal school for
  Minor Sequencer, Contingency, Spell Sequencer, Spell Trigger and Chain Contingency,
  Teleport Field (range 30 ft., Save vs. Spell at -4), Oracle (dispels illusions up to level
  9 in a 30-ft radius-450 enemy-only area via `ADD_PROJECTILE`), and Sphere of Chaos
  (5-outcome 1-round table with Save vs. Spell at -4).
- Divine kept/decided changes: Bless (casting time 5, 30s + 1 round/level across levels
  1-20), Shillelagh (druid-only), Doom (casting time 1, -2 damage, Save vs. Spell scaling 0
  to -4), Faerie Fire (new level-1 druid spell via `ADD_SPELL`), Aid (hit-point-only bonus
  `1d8 + min(L,10)`, 1 turn/level, self-refreshing, own portrait icon via `STATDESC.2DA`),
  Silence 15' Radius (enemies only), Free Action (usable by druids, 1 turn/level on all
  protections and companions, Stun protection, allows Haste), Neutralize Poison (cures
  poison + 1 turn/level poison immunity, without disease/paralysis cures), Divine Power
  (Holy Power renamed Divine Power, casting time 4, fighter APR for non-fighter clerics),
  Negative Plane Protection (1 turn/level for both clerics and druids), Iron Skins (renamed
  Stoneskin, casting time 1), Mass Regenerate (new level-5 druid spell via `ADD_SPELL`,
  sight-range party-only projectile via `ADD_PROJECTILE`), Regenerate (druid-only, 2 HP/s
  for 1 round/level, self-refreshing), and Greater Restoration (adds cures for Hold, Stun,
  Sleep, Petrification, Polymorph, curses, Blindness, and Deafness).
- SCS-style arcane changes: Chromatic Orb (IWD progression without +6 save bonus, range 50,
  Free Action immunity on level 5 stun), Melf's Minute Meteors (+2 enchantment), Skull Trap
  (12d6 cap across all abilities), Lower Resistance (30% + 1%/level, power 5), Power Word
  Silence/Stun/Blind/Kill (school Enchantment with Invoker exclusion on spells and scrolls;
  Stun blocked by Free Action; Blind single-target), Mantle/Improved Mantle/Absolute
  Immunity (+3/+4/+6 weapon protection), Project Image and Simulacrum slot restrictions,
  Abi-Dalzim's Horrid Wilting immunities (undead, golems, animated swords, air/earth/fire
  elementals), party-friendly Enchantment-school Wizard Symbols (with Free Action immunity
  on Symbol, Stun), and alignment-based fiend summoning with species scripts (guarded
  hostility transition, 6-second area fear aura, and on Balor 30-second Stoneskin renewal
  and innate fiend Domination) for Cacofiend, Summon Fiend, and Gate.
- SCS-style divine changes: Blade Barrier (casting time 6, enemy-only, save for half),
  Globe of Blades (enemy-only, save for half), Call Lightning (1 round/level up to 11
  bolts), Defensive Harmony (cleric-only, +4 AC), Glyph of Warding (casting time 5, save
  for half), Magical Stone (3d4 crushing, 6d4 vs. undead), Priest Gate (alignment-based
  fiends), party-friendly Enchantment-school Priest Symbols (with Free Action immunity on
  Symbol, Stun), Summon Insects/Insect Plague/Creeping Doom (all damage and secondary
  effects delivered via subspells, per-round breath save vs. spell failure, countered by
  Fire Shields, Stoneskin, normal-weapon immunity items/spells, and Death Spell, undead
  immune), and Nature's Beauty (schoolless area subspell carrying both humanoid slay and
  blindness: permanent blindness and humanoid death on failed save, 3 rounds blind on
  successful save).
- Descriptions that named the old behaviour are updated (English).
- Additional decided spell changes (`cbmagic_more.tpa`): new priest spells Protection From
  Cold (level 3, `CLERIC_CBMAGIC_PROTECTION_FROM_COLD`, built like Priest level 3
  Protection From Fire) and Protection From Acid (level 4,
  `CLERIC_CBMAGIC_PROTECTION_FROM_ACID`, built like Priest level 4 Protection From
  Lightning) for clerics and druids via `ADD_SPELL`; Dispelling Screen replacing Spell
  Immunity (`SPWI510`, `SCRL6S`, and redirecting `SPWI590`..`SPWI597`, lasting 5 turns in a
  15-ft party area to absorb one Dispel Magic or one Breach, removed by Pierce Shield and
  Spellstrike); Nahal's Reckless Dweomer (`SPWI124`) without Aura Cleansing (ability
  target 7 -> 5 so it respects the round aura timer); Improved Haste (`SPWI613`, `SCRL7Q`)
  rebuilt as a 1-turn party buff in a 15-ft radius without `opcode 16` (+6 movement rate, +1
  APR, +2 THAC0/AC/Save vs. Breath, dispellable, cures and grants immunity to Slow); and
  SCS-style mutual cancellation between Haste and Slow across spells and items while keeping
  vanilla Haste's bonus, duration, and fatigue untouched.
- Installer frame for BG2:EE and EET, shared library, and the exported list of decided
  changes (`docs/build-list.json`) with its generator. With Spell Revisions installed the
  installer warns that the two do not go together.
