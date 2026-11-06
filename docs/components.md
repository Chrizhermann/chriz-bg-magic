# Components

What each part of Chriz BG Magic changes, in engine-neutral terms, so the same rules can
move to the Chriz script engine later. Values not named here stay as in the base game.

## Layout

One component for now, `0` (label `chriz-bg-magic-main`). It calls one function per
decided change (`chriz-bg-magic/lib/cbmagic_fixes.tpa`, `cbmagic_vanilla.tpa`); any of
them can move to a component of its own without changes. The user-facing layout is
Christopher's decision.

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

## Schools (`cbmagic_vanilla_find_familiar_universal`, `cbmagic_vanilla_wish_universal`, `cbmagic_vanilla_cloudkill_school`, `cbmagic_vanilla_death_fog_school`)

- Find Familiar and Wish belong to the Universal school (`0`) with no specialist mage
  exclusions, so every specialist can learn and cast them. Find Familiar's description and
  scroll say `(Universal)`.
- Cloudkill and Death Fog belong to Conjuration (`2`, Diviner exclusion) like the other
  cloud spells. Their descriptions and scrolls say `(Conjuration/Summoning)`.

## Blindness (`cbmagic_vanilla_blindness_duration`)

Blindness lasts 1 round per 2 caster levels, at least 2 rounds and at most 5 rounds (12 s
at levels 1-5, 18 s at 6-7, 24 s at 8-9, 30 s at 10+), instead of the base game's 2 hours.

- How: a single-ability Blindness spell is expanded to four level-gated abilities (levels
  1, 6, 8 and 10), or an already level-scaled spell has its blindness effect durations
  updated in place; instant companion effects (such as the status string) keep their zero
  duration. Its description and scroll state `1 round/2 levels (2 to 5 rounds)`.

## Finger of Death (`cbmagic_vanilla_wizard_finger_of_death_save`, `cbmagic_vanilla_priest_finger_of_death_save`)

Both wizard and priest Finger of Death allow a save vs. death with no penalty on the slay
effect (and effects that share its save roll), instead of the base game's save vs. spell
at -2. The damage on a successful save stays as in the base game; descriptions and the
wizard scroll are updated.

## Disintegrate vs. Mordenkainen's Sword (`cbmagic_vanilla_mordenkainens_sword_disintegrate`)

Disintegrate destroys Mordenkainen's Sword (`RACE = SWORD`) outright without a saving
throw, while keeping its normal save-or-die behaviour against other targets.

- How: before the disintegrate effect in each ability, an external effect (`DESTSELF.EFF`
  targeting `RACE = SWORD`, no save) and a self-immunity block for `RACE = SWORD` are
  inserted so the sword is destroyed cleanly without running the normal disintegrate roll.

## Entangle (`cbmagic_vanilla_entangle`)

- Save vs. breath instead of vs. spell, keeping the base game's +3 bonus on the entangle
  effect and every effect that shares its roll. Its description says so.
- Flying, incorporeal, elemental, giant and dragon creatures are immune by race (`WYVERN`,
  `BEHOLDER`, `MEPHIT`, `SPECTRE`, `WRAITH`, `SHADOW`, `MIST`, `ELEMENTAL`, `GIANT`,
  `ETTIN`, `DRAGON`).

## Flame Blade (`cbmagic_vanilla_flame_blade`)

- Restricted to druids and rangers.
- The created blade (`FBLADE.ITM`) is flagged as a magical weapon with enchantment +1 (if
  unenchanted), so it can hit creatures that require a magical weapon. Existing higher
  enchantments from other mods are preserved. Its description is updated.

## Elemental summoning scaling (`cbmagic_vanilla_conjure_fire_elemental_wiz`, `cbmagic_vanilla_conjure_air_elemental_wiz`, `cbmagic_vanilla_conjure_earth_elemental_wiz`, `cbmagic_vanilla_conjure_fire_elemental_priest`, `cbmagic_vanilla_conjure_earth_elemental_priest`)

The three probability windows (12, 16 and 24 Hit Dice elementals) scale per ability level
while keeping each spell's other effects (including mental combat on the wizard spells):

- Wizard Conjure Fire, Air and Earth Elemental: 64%/35%/1% at level 12, shifting 1% per
  level from 12 HD to 24 HD (60%/35%/5% at level 16, 56%/35%/9% at level 20+).
- Druid Conjure Fire and Earth Elemental: 64%/35%/1% at level 11, 61%/37%/2% at level 12,
  52%/42%/6% at level 15, and 37%/51%/12% at level 20+ (interpolated evenly across levels
  11-20 with sums at 100%).

## Druid-only priest spells (`cbmagic_vanilla_barkskin_druid`, `cbmagic_vanilla_animal_summoning_1_druid`, `cbmagic_vanilla_animal_summoning_2_druid`, `cbmagic_vanilla_animal_summoning_3_druid`, `cbmagic_vanilla_conjure_animals_druid`)

Barkskin, Flame Blade, Animal Summoning I-III and Conjure Animals are restricted to druids
and rangers (cleric/paladin exclusion bit set in the priest class word at SPL offset
`0x20`, preserving alignment bits).

## Per-spell casting times (`cbmagic_vanilla_*_ct`)

Casting times are lowered on abilities that are slower than the target value (faster
abilities from other mods are preserved) and descriptions are updated:

- Bless (`cbmagic_vanilla_bless_ct`): 9 to 5.
- Flame Strike (`cbmagic_vanilla_flame_strike_ct`): 8 to 5.
- Heal (`cbmagic_vanilla_heal_ct`): 9 to 6.
- Blade Barrier (`cbmagic_vanilla_blade_barrier_ct`): 9 to 6.
- Bolt of Glory (`cbmagic_vanilla_bolt_of_glory_ct`): 9 to 6.
- Magic Resistance (`cbmagic_vanilla_magic_resistance_ct`): 9 to 5.
- Righteous Magic (`cbmagic_vanilla_righteous_magic_ct`): 9 to 5.
- True Seeing (`cbmagic_vanilla_true_seeing_priest_ct`) and True Sight
  (`cbmagic_vanilla_true_sight_wizard_ct`): 8 to 6.
- Glyph of Warding (`cbmagic_vanilla_glyph_of_warding_ct`): 9 to 5.
- Invisibility Purge (`cbmagic_vanilla_invisibility_purge_ct`): 8 to 4.
- Strength (`cbmagic_vanilla_strength_ct`): 9 to 5.

## Descriptions

Changed texts are added as new strings and the spell (and its scrolls) point to them; the
old strings, which other resources may share, stay. The text patterns exist only in
English so far: on a game in another language the installer warns that those
descriptions still describe the old behaviour.
