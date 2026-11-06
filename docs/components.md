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

## Kept and adjusted Spell Revisions changes (`chriz-bg-magic/lib/cbmagic_sr.tpa`)

### Arcane spells

- **Invisibility (`cbmagic_kept_invisibility`)**: lasts 8 hours (2400 seconds) instead of
  24 hours.
- **Luck (`cbmagic_kept_luck`)**: keeps the base game's +1 bonus to luck and skill checks,
  lasts 15 rounds (90 seconds) instead of 3 rounds, and replaces an earlier casting on the
  same target.
- **Clairvoyance (`cbmagic_kept_clairvoyance`)**: works indoors as well as outdoors and
  grants the caster dispellable immunity to backstab for 3 rounds at level 5 plus 1 round
  per 2 caster levels (up to 10 rounds at level 19) instead of revealing the outdoor map.
- **Invisibility 10' Radius (`cbmagic_kept_invisibility_sphere`)**: casting time 1 (from
  9) and duration 1 turn (60 seconds, from 24 hours).
- **Confusion (`cbmagic_kept_confusion`)**: lasts 4 rounds at levels 1-14, 5 rounds at
  levels 15-19, and 6 rounds at level 20+. Save vs. Spell at -2 and all other properties
  stay as in the base game.
- **Sequencers and Contingencies (`cbmagic_kept_minor_sequencer`,
  `cbmagic_kept_contingency`, `cbmagic_kept_spell_sequencer`,
  `cbmagic_kept_spell_trigger`, `cbmagic_kept_chain_contingency`)**: Minor Sequencer,
  Contingency, Spell Sequencer, Spell Trigger, and Chain Contingency belong to the
  Universal school and clear specialist exclusion flags on the spells and their scrolls, so
  all specialist mages (including Diviners) can learn and cast them.
- **Teleport Field (`cbmagic_kept_teleport_field`)**: enemies in the field get a Save vs.
  Spell at -4 to avoid being teleported (base game: no save).
- **Oracle (`cbmagic_kept_oracle`)**: dispels illusion spells up to 9th level (from 5th)
  in a 30-ft enemy-only area around the caster (range 1).
- **Sphere of Chaos (`cbmagic_kept_sphere_of_chaos`)**: keeps its name, level 7, and
  10-round enemy-only aura around the caster. Each round, enemies in the area save vs.
  Spell at -4 or suffer one of 5 random effects for 1 round (6 seconds): feeblemind
  (20%), confusion (20%), panic (20%), sleep waking on damage (20%), or hold (20%).

### Divine spells

- **Bless (`cbmagic_kept_bless`)**: casting time 5 (from 9) and duration 30 seconds + 1
  round per caster level across 20 abilities (levels 1-20, 36-150 seconds), usable by
  clerics and druids as in the base game.
- **Shillelagh (`cbmagic_kept_shillelagh`)**: keeps the base game's mechanics and is
  restricted to druids.
- **Doom (`cbmagic_kept_doom`)**: casting time 1 (from 9), imposes -2 to THAC0, damage
  rolls, and all saving throws (without an AC penalty), and allows a Save vs. Spell to
  negate, scaling from no penalty at level 1 to -4 at level 9 (steps at levels 1, 3, 5, 7,
  and 9).
- **Faerie Fire (`cbmagic_kept_faerie_fire`)**: new level-1 druid-only spell added via
  `ADD_SPELL` (`CLERIC_CBMAGIC_FAERIE_FIRE`). In a 5-ft enemy-only area (range 20, casting
  time 1), targets that fail a Save vs. Spell suffer a -2 AC penalty, lose and cannot
  gain invisibility, and glow violet for 4 rounds.
- **Aid (`cbmagic_kept_aid`)**: replaces the base game's combined Bless/HP effect (opcode
  129) with a hit-point-only bonus of `1d8 + min(L, 10)` where `L = max(ability level, 3)`,
  lasting 1 turn per level, refreshing on recast, and displaying its own portrait icon
  (appended to `STATDESC.2DA` using `SPPR150D`).
- **Silence 15' Radius (`cbmagic_kept_silence`)**: affects enemies only instead of all
  creatures in the area.
- **Free Action (`cbmagic_kept_free_action`)**: usable by druids and rangers as well as
  clerics, lasts 1 turn per level, protects against Stun, and no longer blocks Haste or
  movement rate bonuses.
- **Neutralize Poison (`cbmagic_kept_neutralize_poison`)**: cures poison and grants
  immunity to poison for 1 turn per level (levels 7-20); no longer heals 10 Hit Points or
  cures disease, blindness, or deafness.
- **Divine Power (`cbmagic_kept_divine_power`)**: renames Holy Power to Divine Power in
  name and description, sets casting time to 4 (from 6), and grants non-fighter clerics
  (single-class Cleric, Cleric/Thief, Cleric/Mage) fighter bonus attacks per round (+1/2
  APR at levels 7-12, +1 APR at level 13+).
- **Negative Plane Protection (`cbmagic_kept_negative_plane_protection`)**: lasts 1 turn
  per level (levels 7-20, 420-1200 seconds) for both clerics and druids; all other
  properties stay as in the base game.
- **Iron Skins / Stoneskin (`cbmagic_kept_iron_skins`)**: renamed Stoneskin, with casting
  time 1 (from 9); skin progression and duration stay as in the base game.
- **Mass Regenerate (`cbmagic_kept_mass_regenerate`)**: new level-5 druid-only spell added
  via `ADD_SPELL` (`CLERIC_CBMAGIC_MASS_REGENERATE`). In a sight-range party-only area
  around the caster (`cbmmreg.pro` via `ADD_PROJECTILE`, radius 452, casting time 5), party
  members within sight regenerate 2 Hit Points per round (1 HP every 3 seconds) for 1 turn +
  2 rounds per level (up to 30 rounds at level 10); a new casting replaces the previous one.
- **Regenerate (`cbmagic_kept_regeneration`)**: restricted to druids, stays level 7, heals
  2 Hit Points per second (from 3) for 1 round per level (from 1 round per 2 levels), and
  replaces an earlier casting on the same target.
- **Greater Restoration (`cbmagic_kept_greater_restoration`)**: keeps the base game's
  cures, casting time (3), and caster fatigue drawback, and additionally cures Hold, Stun,
  Sleep, Petrification, Polymorph, curses, Blindness, and Deafness.

## Descriptions

Changed texts are added as new strings and the spell (and its scrolls) point to them; the
old strings, which other resources may share, stay. The text patterns exist only in
English so far: on a game in another language the installer warns that those
descriptions still describe the old behaviour.
