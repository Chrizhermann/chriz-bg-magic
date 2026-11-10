# Changelog

## Unreleased

- Texts: 23 spells whose rules changed now describe those rules (among them Haste and Slow,
  Mirror Image and Reflected Image, Fireball, Cone of Cold, Sleep, Dispel Magic, Remove Magic,
  Breach, Tenser's Transformation), and eight older texts name who is immune, what wakes a
  sleeper and which spells replace each other.
- Numbers of the reference game removed from the definitions, so every install gets the same
  result: Grease lasts 3 rounds + 1 round a level through areas of its own (on a game without
  EE Fixpack it had pointed at wrong or missing areas), immunities against sleep, hold, slow and
  the like are tested by name, Unholy Blight shows the game's "Cursed" icon, and the form
  weapons' helper no longer shows an icon.
- Texts: a scroll now shows the description of its spell wherever this mod writes that
  description (nine of the game's scrolls had kept the old text). The summoned elementals are
  named by size, the same for every element: Lesser, plain, Greater, Elder.
- The main character as a statue or imprisoned (needs EEex): petrification and imprisonment no longer end the game. He becomes a tough statue or
  vanishes into a prison, the party takes him along when it travels, and only Stone to Flesh, or
  Freedom where he vanished, bring him back. The game ends when nobody else in the party can act.
  Petrified or imprisoned companions leave the party as before, but once cured they rejoin with
  their party AI script. Resting stays possible; dreams wait until he is free. Where the party
  cannot leave and carries no cure (Hell, Spellhold's maze, the Throne of Bhaal and the like), the
  game ends after 30 seconds without combat.
- Polymorph Self: the six forms of SCS with their real values, built from this mod's own files:
  hill giant, ogre mage, spider, mustard jelly, hell hound and rat. The spell's text lists each
  form and what it can do. The hill giant looks like Icewind Dale's verbeeg; BG2 has no hill
  giant art, so the mod brings these files and sounds from Icewind Dale: Enhanced Edition.
- Shapechange: SCS's six forms in the same way: mind flayer, iron golem, giant troll, marilith,
  greater basilisk and invisible stalker, for 6 turns. Only weapons of +3 or better hurt the iron
  golem (SCS's data would have shut out every weapon).

- Strength, Strength of One, Divine Power, Champion's Strength and IWDification's Animal Rage no
  longer lower a higher Strength, and bonuses and penalties from other sources, such as Draw Upon
  Divine Might or an item's +1, count on top of them, whichever came first. A creature in another
  form keeps the Strength of its form. Needs EEex; without it these spells set Strength as before.

- Simulacrum: the copy keeps the special abilities of its class and kit that its own level gives,
  no more uses than the caster had left; abilities from items and quests are lost. It cannot use
  quick-slot items. Needs EEex.

- Lesser Restoration also ends temporary attribute drain, such as Ray of Enfeeblement or a mind
  flayer's hit. Disease, permanent loss and the weakness after Blood Rage stay. Needs EEex.

- Summon Deva, Summon Fallen Deva, Summon Planetar and Summon Dark Planetar call new creatures:
  their numbers, weapons, spell lists and look are in each spell's description. The party can
  have one deva or fallen deva and one planetar or dark planetar at the same time; a second of
  the same kind leaves as soon as it arrives. Enemy casters are not limited, and their celestials
  cast with the game's own celestial scripts. The paladin's two summons call the same creatures.

- The mod now overwrites: every spell, item and effect it changes is written whole, whatever
  stood there. A spell another mod or a player changed no longer stops or skews the install,
  and an install takes seconds. Spells of IWDification are still patched, without any check.
- IWD Emotion: Hopelessness and Symbol: Hopelessness now end their own incapacitation when the
  target takes damage, without curing unrelated stuns or restoring Hope.
- Wizard Fire, Air, Earth and Water Elemental summons, including all Lesser forms, now use a
  three-round control contest with a 15% hostile result. Druid elementals remain uncontested.
- Righteous Wrath of the Faithful, Haste and Improved Haste no longer end or block one another;
  while more than one runs, only one extra attack counts. This needs EEex.
- Bonus types: a condition on a delivered sub-spell stays attached to it, so Righteous Wrath's
  alignment rule and similar ones hold.
- Recitation's description no longer says it adds to Prayer.
- Remove Paralysis and the matching cure clear "Webbed" in EET too; Mimic Web's record entry is
  right there.
- Spell Revisions gets a warning and nothing else; there is no refusing mode any more.
- Selected spells now use Morale, Favor, Luck, Dodge, Deflection and Curse bonus types.
  EEex compares each statistic separately: a type contributes its strongest bonus and
  strongest penalty, while different types and untyped effects combine. Weaker effects
  resume when stronger ones expire. Spell and scroll descriptions identify typed values.
- Typed spells refresh themselves on recast, including their linked payloads. Shared
  external effects are isolated before patching. Optional IWD spells are found by symbol
  and skipped with an informational line when absent.
- The mod brings the helper spells its changes call, so they work on plain BG2:EE and on EET,
  with or without EE Fixpack. Find Familiar keeps each game's own way of calling the familiar and
  names the Hit Points of all three campaigns.
- Transformation and Regeneration spells form separate exclusive families: higher spell
  level wins; a new casting replaces an equal-level member. These rules work without EEex.
- Champion's Strength now removes and blocks Draw Upon Divine Might for its duration, while
  Draw Upon Divine Might remains outside the wider Transformation family. Champion's native
  caster concentration behavior is unchanged.
- Command now has its decided one-round, damage-waking sleep with a Save vs. Spell penalty that
  scales from 0 at level 1 to -4 at level 9.
- Chaos now lasts 4/5/6 rounds at caster levels 1/15/20, retaining its distinct automatic and
  saving-throw branches. Sphere of Chaos has equal five-way outcomes, and priest Confusion
  (level 7) becomes the same spell with the wizard spell's field.
- Added a level-6 druid Conjure Air Elemental with the decided 12/16/24-Hit-Dice progression and
  no control contest, plus level-3 druid Icelance: automatic 5d6 cold damage and a separately
  saveable three-round stun. Icelance also reaches shamans and rangers through the existing druid
  spell category; no priest scroll was added.
- With EEex installed, Pierce Magic reduces current Magic Resistance by half, rounded down
  and limited to 10-40 percentage points, for 5 rounds. Its other effects stay unchanged.
  Without EEex at installation, its existing resistance effect is retained.
- Added offline installer and LuaJIT/Lua 5.3 tests, plus the disposable-lab `bonus` group.
  HP type comparisons remain deferred.
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
