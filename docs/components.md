# Components

What each part of Chriz BG Magic changes, in engine-neutral terms, so the same rules can
move to the Chriz script engine later. Values not named here stay as in the base game.

## Layout

One component for now, `0` (label `chriz-bg-magic-main`). It calls one function per
decided change (`chriz-bg-magic/lib/cbmagic_fixes.tpa`); any of them can move to a
component of its own without changes. The user-facing layout is Christopher's decision.

None of the changes below needs EEex. They work on BG2:EE and EET (built and checked on
2.7.3.0).

## Spell Revisions installed

Chriz BG Magic replaces Spell Revisions and the two do not go together (Christopher,
2026-11-06). The installer says so plainly in a warning and carries on; no work goes into
making them fit. The setting is `cbmagic_sr_policy` in `lib/cbmagic_shared.tpa`, so a hard
refusal is one word away if the two get declared incompatible outright.

## Spirit Armor (`cbmagic_fix_spirit_armor`)

Casting Spirit Armor on a creature that already has it replaces the earlier casting. The
base game stacks it with itself, although its text rules that out: every casting added
another +3 to saves vs. spell and another expiry damage (2d4 when it runs out).

- How: every ability of the spell starts with "remove this spell's effects" (opcode 321
  naming the spell, instant, bypasses magic resistance), the form the base game's own
  refreshing spells use. The earlier casting's waiting expiry damage goes with it; the
  new casting brings its own.
- Mage Armor and Ghost Armor need nothing: all three set the base AC and the best counts.
- Already refreshing abilities are left alone. Text unchanged (it already says so).

## Minor Spell Deflection (`cbmagic_fix_minor_spell_deflection`)

Stops only spells of levels 1-4. The base game's version stopped levels 1-7 (still four
levels in total), so a level-3 spell also absorbed Breach and priest spells up to level 7.
The rest of the Spell Deflection and Spell Turning line stays as it is.

- How: the level deflections for levels 5-9 (opcode 201 with power level above 4) are
  removed from every ability; the spell cast when the deflection runs out stays attached.
- The description's "up to 7th-level spells" becomes "up to 4th-level spells", also on
  its scroll.
- A version that deflects only levels above 4 would lose its whole function; it is left
  as it is with a warning.

## Save vs. Breath for dodgeable explosions and area damage (`cbmagic_fix_breath_saves`)

The damage of Fireball, Delayed Blast Fireball, Sunfire, Cone of Cold, Flame Strike,
Skull Trap, Glyph of Warding, Incendiary Cloud and Lightning Bolt allows a save vs.
breath instead of vs. spell. No extra penalties; damage, half damage and everything else
stay. Chain Lightning, mind and transmutation spells keep their save vs. spell.

- How: in every ability, the damage effects (opcode 12) that roll vs. spell, and the
  effects that share their roll (same save, same bonus), switch to vs. breath. Only the
  save type bit changes; other flags (e.g. bypassing Mirror Image) stay.
- Sunfire's damage sits in its own payload (SPWI523D), which is changed with it. Spells a
  spell casts that are not its own payloads are named in the log and left alone.
- Scrolls, wands and other items that cast these spells use the changed spells.
  Descriptions that named the save ("Saving Throw vs. Spell", "Save vs. Spell") now say
  "vs. Breath", on the spells and their scrolls. Fireball, Sunfire and Cone of Cold texts
  name no save type and stay.
- Not part of it: Meteor Swarm and Fire Storm. The base game gives them no save at all,
  and they stay that way for now; a save is on the list of possible later changes.
- Trap and monster copies of these spells keep their save vs. spell.

## Damage wakes sleepers (`cbmagic_fix_wake_on_damage`)

The magical sleep of Sleep, Color Spray, Stinking Cloud, Power Word: Sleep, Command,
Greater Command and Emotion: Hopelessness ends when the sleeper takes damage.

- How: their sleep effects (opcode 39) get "wake on damage" (parameter 2 = 0; the base
  game uses 1, no waking). Power Word: Sleep (opcode 217) passes its setting on and has
  it on in the base game already, so nothing changes there.
- A sleep effect with a permanent timing cannot wake whatever the setting says; such an
  effect is left as it is with a warning.
- Emotion: Hopelessness: only its sleep ends, wherever it sits (EE Fixpack moves it into
  a spell of its own). Its other effects, the portrait icon among them, run out as before
  and its text stays; the IWD version replaces this spell later.
- Only the waking. The other changes decided on these rows (immunities, schools) come
  later. The IWD spells that put creatures to sleep or knock them out get the same when
  they are built. Trap and monster copies of these spells stay as they are.

## Web (`cbmagic_fix_web`)

- Save vs. breath instead of vs. spell: the web effect (opcode 157) and every effect that
  shares its roll switch; the base game's -2 stays. Its description and scroll say so.
- Spiders (race SPIDER) and amorphous creatures (race SLIME: slimes, jellies, oozes,
  puddings) are immune: every ability starts with "immune to this spell, with the
  game's message" for those races (opcode 324 with the SPLPROT.2DA row `RACE = value`;
  the row is appended when a game lacks it). The base game's spiders already resist the
  cast Web: they carry the item `ANTIWEB`, an immunity to the projectile that brings
  Web's effects (all 38 spiders of BG2:EE, 58 of 62 in EET). The race immunity adds Web
  without that projectile (applied directly, e.g. by script or another mod) and spiders
  without the item; in EET those are Siege of Dragonspear's three driders and Centeol.
- Dragons and flying and incorporeal creatures: the game has no flag for the last two, so
  this goes by race too, and for now only the very obvious ones (Christopher, 2026-11-06):
  - DRAGON;
  - flying: WYVERN (wyverns, fairy and pseudo dragons), BEHOLDER (the whole family, gauths
    and spectators too), MEPHIT;
  - incorporeal: SPECTRE (ghosts, apparitions, specters), WRAITH (wraiths, banshees),
    SHADOW (shadows, shade wolves), MIST (gaseous forms, mists, nishruus).

  Almost all dragons, true wyverns and true beholders were immune before through items of
  their own; for mephits, wraiths, spectres, shadows and most mists this is new. Giants and
  ettins stay catchable.
- Left out for now, on the list of possible later changes: imps and quasits, genies, devas
  and planetars, bats, birds and will-o'-wisps (no race of their own), golems and big
  elementals. Fire elementals burn, so a web holding them makes little sense. Web's -2
  stays for now, although Web may be too strong in the base game. An idea on the same list,
  far off: webs that can catch fire.
- Radius and school come later.

## SCS-style spell changes (`chriz-bg-magic/lib/cbmagic_scs.tpa`)

Every decided SCS-style spell change is implemented in our own library (`cbmagic_scs.tpa`), resolved through `SPELL.IDS`, and checks whether the target behaviour is already present so it works with or without SCS installed:

- **Chromatic Orb (`cbmagic_scs_chromatic_orb`):** uses the IWD/SCS level progression without the +6 saving throw bonus:
  - Level 1: 1d4 magic damage + blind for 1 round (save vs. spell negates the secondary effect).
  - Level 2: 1d6 fire damage + pain (-1 AC and THAC0) for 1 round.
  - Level 3: 1d8 magic damage + 1d3 fire damage.
  - Level 4: 1d10 magic damage + blind for 4 rounds.
  - Level 5: 1d12 magic damage + stun for 3 rounds.
  - Level 7+: 2d8 magic damage + hold for 13 rounds (Free Action protects).
- **Melf's Minute Meteors (`cbmagic_scs_melfs_minute_meteors`):** the created meteor weapon (`MELFMET.ITM`) strikes as a +2 weapon instead of +5.
- **Skull Trap (`cbmagic_scs_skull_trap`):** damage is capped at 12d6 (abilities above caster level 12 are removed; level 12 deals 12d6).
- **Lower Resistance (`cbmagic_scs_lower_resistance`):** lowers magic resistance by 30% + 1% per caster level (was 10% + 1% per level) and sets power level to 5 on its resistance-lowering effects so spell protections block it normally.
- **Power Word: Silence, Stun, Blind, Kill (`cbmagic_scs_power_word_silence`, `cbmagic_scs_power_word_stun`, `cbmagic_scs_power_word_blind`, `cbmagic_scs_power_word_kill`):** moved from Conjuration to Enchantment (Invoker exclusion instead of Diviner) on the spells and their scrolls. Power Word: Stun is blocked by Free Action; Power Word: Blind targets a single creature instead of an area.
- **Mantle, Improved Mantle, Absolute Immunity (`cbmagic_scs_mantle`, `cbmagic_scs_improved_mantle`, `cbmagic_scs_absolute_immunity`):** protect against weapons up to +3, +4, and +6 enchantment respectively (up from +2, +3, and +5).
- **Project Image and Simulacrum (`cbmagic_scs_project_image`, `cbmagic_scs_simulacrum`):** `PROJIMAG.SPL` disables quick-slot items (buttons 9, 11, 12) and innate abilities (button 13); `SIMULACR.SPL` disables quick-slot items (buttons 9, 11, 12) while keeping innate abilities enabled (level-based innate filtering requires EEex and is tracked for later).
- **Abi-Dalzim's Horrid Wilting (`cbmagic_scs_abi_dalzim`):** undead, golems, animated swords, and air/earth/fire elementals are immune.
- **Wizard and Priest Symbols (`cbmagic_scs_wizard_symbol_death`, `cbmagic_scs_wizard_symbol_stun`, `cbmagic_scs_wizard_symbol_fear`, `cbmagic_scs_cleric_symbol_death`, `cbmagic_scs_cleric_symbol_stun`, `cbmagic_scs_cleric_symbol_fear`):** use the party-friendly symbol explosion projectile so they affect only enemies; Symbol, Stun is also blocked by Free Action.
- **Cacofiend, Summon Fiend, Wizard Gate, Priest Gate (`cbmagic_scs_cacofiend`, `cbmagic_scs_summon_fiend`, `cbmagic_scs_wizard_gate`, `cbmagic_scs_cleric_gate`):** summon a fiend matching the caster's law/chaos alignment (Bone Fiend / Cornugon / Pit Fiend for lawful casters; Nabassu / Glabrezu / Balor for chaotic casters; 50/50 for neutral casters).
- **Blade Barrier and Globe of Blades (`cbmagic_scs_blade_barrier`, `cbmagic_scs_globe_of_blades`):** payload spells affect only hostile creatures, and a successful save vs. spell halves the damage instead of negating it. Blade Barrier's casting time is reduced from 9 to 6.
- **Call Lightning (`cbmagic_scs_call_lightning`):** lasts 1 round per caster level up to 11 rounds/bolts (projectiles 85..91).
- **Defensive Harmony (`cbmagic_scs_defensive_harmony`):** restricted to clerics/paladins (`0x20 = 0x8000`) and grants +4 AC (was +2).
- **Glyph of Warding (`cbmagic_scs_glyph_of_warding`):** casting time reduced from 9 to 5, and a successful save halves the damage instead of negating it.
- **Magical Stone (`cbmagic_scs_magical_stone`):** deals 3d4 crushing damage (6d4 against undead) instead of 1d4.
- **Summon Insects, Insect Plague, Creeping Doom (`cbmagic_scs_insect_plague`):** spell failure allows a per-round save vs. breath (at 0, -2, and -2); Fire Shields (Red, Blue, Aura of Flaming Death) remove active swarms and block them; Stoneskin holds off the secondary effects while skins remain (each damage tick strips a skin); immunity to normal weapons protects; undead are immune; magic resistance and Dispel Magic do not help.
- **Nature's Beauty (`cbmagic_scs_natures_beauty`):** blindness is moved to schoolless subspells (so True Sight does not dispel it via school removal) and depends on the save vs. spell (+3): on a failed save, humanoids die and targets suffer permanent blindness; on a successful save, targets are blinded for 3 rounds.

## Descriptions

Changed texts are added as new strings and the spell (and its scrolls) point to them; the
old strings, which other resources may share, stay. The text patterns exist only in
English so far: on a game in another language the installer warns that those
descriptions still describe the old behaviour.
