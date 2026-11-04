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

Chriz BG Magic replaces Spell Revisions. What the installer does when Spell Revisions is
installed (refuse, warn, or install anyway) is Christopher's call; until he has decided,
it refuses (`cbmagic_sr_policy` in `lib/cbmagic_shared.tpa`).

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
- Not yet: Meteor Swarm and Fire Storm. The base game gives them no save at all, so the
  rule would add one; that waits for Christopher's answer.

## Damage wakes sleepers (`cbmagic_fix_wake_on_damage`)

The magical sleep of Sleep, Color Spray, Stinking Cloud and Power Word: Sleep ends when
the sleeper takes damage.

- How: their sleep effects (opcode 39) get "wake on damage" (parameter 2 = 0; the base
  game uses 1, no waking). Power Word: Sleep (opcode 217) passes its setting on and has
  it on in the base game already, so nothing changes there.
- A sleep effect with a permanent timing cannot wake whatever the setting says; such an
  effect is left as it is with a warning.
- Only the waking. The other changes decided on these rows (immunities, schools) come
  later. Command, Greater Command and the IWD spells wait for Christopher's answer.

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
- Not yet: flying, incorporeal and very large creatures. The game data has no flag for
  them, so which creatures count waits for Christopher's answer. Radius and school come
  later.

## Descriptions

Changed texts are added as new strings and the spell (and its scrolls) point to them; the
old strings, which other resources may share, stay. The text patterns exist only in
English so far: on a game in another language the installer warns that those
descriptions still describe the old behaviour.
