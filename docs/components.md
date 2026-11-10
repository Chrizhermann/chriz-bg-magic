# Components

What each part of Chriz BG Magic changes, in engine-neutral terms, so the same rules can
move to the Chriz script engine later. Values not named here stay as in the base game.

## Layout

One component for now, `0` (label `chriz-bg-magic-main`). The user-facing layout is
Christopher's decision.

The mod overwrites. Every spell, item and effect it changes is defined whole in `defs/` and
copied over what stands in the game, whatever that is. `tools/build_resources.py` builds the
files, the install code and the strings from `defs/`; only what depends on the install stays
open until then: strings, table rows, spell states, projectiles and the slots of new spells.
So nothing in the install reads old content, and a spell someone edited by hand ends up like
any other. A definition comes from the reference game, EET with EE Fixpack; plain BG2:EE gets
the same files. So a definition names only what the base game or this mod has: the helper spells
of EE Fixpack it calls are in the mod under names of its own (`CBH*`).

The same holds for numbers. Spell states, SPLPROT rows, secondary types, projectiles and record
icons that the base game does not have are named by symbol in `defs/` and get their number at
install; a plain number always lies inside the base game's tables (a test checks every
definition). The reference game's numbers had leaked into five places and are gone: the
immunity states EE Fixpack numbers 119 and 127 to 142 (447 effects), Grease's areas, the record
icon of Unholy Blight (now the game's own "Cursed", icon 35), the icon of the form weapons'
proficiency helper `CBHWSTY1` (dropped: its row and image belong to EE Fixpack) and the secondary
type of the mind flayer form's drain `CBMSFLH` (none now).

Still patched at install, because we do not ship their files: IWDification's spells and the two
it replaces, Emotion: Hopelessness and Chant (`lib/cbmagic_iwd.tpa`, `lib/cbmagic_healing.tpa`,
`lib/cbmagic_bonus.tpa`). This goes when the IWD spells become our own.

The function names in the headings below name where a change was first built; the result now
lives in `defs/`.

The target is BG2:EE and EET 2.7.3.0. Comparing typed bonuses and the new Pierce Magic
resistance rule need EEex v1.3.1. The remaining changes work without EEex. The bonus batch
has offline coverage; its in-game acceptance checks are still pending.

## Spell bonus types (`cbmagic_bonus`)

This pass runs last in component 0, using each spell's final values after the other
changes. For each statistic and type, the largest positive modifier and the most
negative modifier contribute together. Different types combine. Suppressed modifiers
remain on the creature, so they can contribute again when the stronger effect ends.
The same rules apply to party members and enemies. Equipment and untyped effects keep
their existing stacking behavior.

| Type | Spells | Affected values |
| --- | --- | --- |
| Morale | Emotion: Courage, Emotion: Hope, Righteous Wrath of the Faithful, Blood Rage, Animal Rage | THAC0, damage and saving throws |
| Favor | Bless, Prayer, Recitation; Chant's saving throws | THAC0, damage and saving throws where supplied by the spell; includes penalties |
| Luck | Luck; Chant's Luck modifier | Luck and Luck's saving throws; includes penalties |
| Dodge | Blur, Defensive Harmony | Positive AC modifiers and saving throws |
| Deflection | Entropy Shield, Aura of Flaming Death; Spirit Armor and Barkskin | Positive AC modifiers and saving throws; Spirit Armor and Barkskin contribute only their saves |
| Curse | Doom, Curse, Unholy Blight | Negative THAC0, damage, saving throw and Luck modifiers |

Base AC still uses the game's existing best-value rule. AC penalties, attributes,
resistances, spell failure, Greater Malison and Slow are outside this system. Temporary
HP still accumulates between Courage and Righteous Wrath.

Righteous Wrath of the Faithful, Haste and Improved Haste no longer end or block one another.
While more than one runs, only one extra attack counts: Haste before the others, otherwise the
strongest. When the counted one ends, the other works again. This needs EEex; without it the
extra attacks add up.

Every typed spell refreshes its own effects on recast. Bless, Chant and Luck retain their
existing amounts and durations when their built-in nonstacking effects are decomposed;
Bless also retains its +5 morale modifier. Bad Chant retains its Luck penalty. Existing
save and skill modifiers remain separate. The Champion's Strength effect is retained.

Each typed value is listed with its type in the English spell and scroll descriptions.
An appended list covers varying caster-level values and conditional payloads without
replacing unrelated description text. New strings are allocated; shared old strings are
preserved. Missing descriptions and unsupported languages are reported in the log.
Optional IWD spells are located by their installed symbols; absence is informational.
Changed linked payloads use private copies, preserving other users of the original data.

The EEex listener verifies a per-rebuild marker before changing statistics and stops
after ten errors. Without EEex, correction is inactive and different spells accumulate
normally; self-refresh still works. This batch has synthetic installer and Lua runtime
coverage, not completed live acceptance.

External effects need an additional runtime step: the game keeps their delivery wrapper
on the creature and executes the payload internally. The listener reads the payload only
after the wrapper reports successful execution, retaining the game's eligibility checks.
The wrapper also determines the payload's effective lifetime. This path was checked
against the 2.7.3.0 executable and independent mocks; its live acceptance is pending.
It reads the installed payload amounts: a separate EEex mutator that changes only the
transient decoded child's amount is outside this path's verified compatibility.

## Exclusive spell families (`cbmagic_family`)

Within each family, a higher-level spell replaces and temporarily excludes lower-level
members. At equal level, the new casting replaces the old one. Levels come from the
installed spells, and recasting a member refreshes it. Removing an old family member
removes its whole spell effect, including linked payloads.

- **Transformation:** Tenser's Transformation, Divine Power, Righteous Magic,
  Champion's Strength, Blood Rage and Animal Rage.
- **Champion's Strength and Draw Upon Divine Might:** Champion's Strength removes an active
  Draw Upon Divine Might from its recipient and prevents a new one for its own duration. As the
  higher-level spell, Champion's Strength wins this pair; Draw Upon Divine Might otherwise remains
  outside the Transformation family and can coexist with its other members.
- **Regeneration:** Regenerate, Mass Regenerate and Trollish Fortitude. Both this mod's
  Mass Regenerate and an optional installed spell with that symbol participate.

These exclusions last as long as the main buff and retain its dispellability. All
removals run before the new protections and buff. These families work without EEex.

## Pierce Magic

The resistance reduction is half the target's current Magic Resistance, rounded down,
with a minimum of 10 and maximum of 40 percentage points, lasting 5 rounds. For example,
10, 20, 50 and 100 MR produce reductions of 10, 10, 25 and 40 points. The spell's other
effects, targeting and protection interactions are preserved.

The installer selects this behavior when the EEex bootstrap resource `M___EEex.lua`
exists. Without it, Pierce Magic keeps its existing resistance effect and text, and the
installer logs that choice. Adding or removing EEex requires reinstalling the component.
The selected implementation uses EEex to read current resistance at impact and applies
one timed reduction; it does not recalculate the reduction during its duration.

## Bonus acceptance checks

`tests/test_bonus.py` covers the installer with fabricated data shaped like the supported
spells, including alternate symbol assignments, effect layouts and shared external
payloads. `tests/bonus_runtime.lua` runs under both LuaJIT and Lua 5.3 through `lupa`.
The disposable-lab runner `tests/lab/run_batches.py --only bonus` adds installed-spell
checks using the runner's normal path arguments. It has not been run for this batch.

The report keeps save/reload, rest, area transitions, an actual equipped item, normal
spellbook casting/projectiles, a character-sheet screenshot and a separate installation
without EEex as explicit manual checks. Direct spell application and an untyped synthetic
modifier do not establish those cases. No game or reference installation is modified by
the offline tests.

## Healing (`cbmagic_healing.tpa`)

- Cure Light Wounds is `1d8 + 5` at casting time 4; optional IWD Cure Moderate Wounds is
  `2d8 + 4` and one casting-time unit faster; Cure Medium, Serious and Critical Wounds are
  `2d8 + 7` at 4, `3d8 + 7` at 6, and `4d8 + 12` at 7. Mass Cure keeps its effect and has
  casting time 4.
- Cause Light, Moderate, Medium, Serious and Critical Wounds use the matching Cure roll
  and their decided faster casting times. Their ordinary targets keep the original direct
  spell or touch-charge delivery, saving throw and unrelated effects. The optional IWD
  Mass Cause Light Wounds keeps its native roll, casting time and save rule.
- Cause Wounds, IWD Mass Cause Light Wounds and Harm heal undead instead of damaging them.
  The source damage is blocked for undead before it can run (opcode 324, `GENERAL =
  UNDEAD`); a private healing payload is then cast only for undead through the complementary
  opcode-318 guard. For touch spells this happens in the created charge item, not in the
  parent spell. A charge item shared by another spell is privately cloned and only this
  spell's creation effect is retargeted. Harm retains its effect on non-undead, has casting
  time 7, and heals undead completely.
- Optional IWD symbols absent from `SPELL.IDS` log a normal skip. Every changed English
  spell description and every actual scroll description must match the expected base text;
  a mismatch stops the install rather than leaving a false description.

## Spell Revisions installed

Chriz BG Magic replaces Spell Revisions and the two do not go together (Christopher,
2026-11-06). The installer says so plainly in a warning and carries on; no work goes into
making them fit.

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
- Only the waking. The other changes decided on these rows (immunities, schools) come
  later. Trap and monster copies of these spells stay as they are.

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

## Schools (`cbmagic_vanilla_find_familiar_universal`, `cbmagic_vanilla_wish_universal`, `cbmagic_vanilla_minor_sequencer_universal`, `cbmagic_vanilla_contingency_universal`, `cbmagic_vanilla_spell_sequencer_universal`, `cbmagic_vanilla_spell_trigger_universal`, `cbmagic_vanilla_chain_contingency_universal`, `cbmagic_vanilla_cloudkill_school`, `cbmagic_vanilla_death_fog_school`, `cbmagic_vanilla_web_school`, `cbmagic_vanilla_incendiary_cloud_school`)

- Find Familiar, Wish, Minor Sequencer, Contingency, Spell Sequencer, Spell Trigger and
  Chain Contingency belong to the Universal school (`0`) with no specialist mage
  exclusions on the spells or their scrolls (clearing specialist kit usability bits on
  ITM `0x2d` / `0x2f` while preserving unrelated usability bits), so every specialist can
  learn and cast them. Their descriptions and scrolls say `(Universal)`.
- Cloudkill, Death Fog, Stinking Cloud, Web and Incendiary Cloud belong to Conjuration (`2`,
  Diviner exclusion on the spells and ITM `0x2d` bit `0x01` on their scrolls). Their
  descriptions and scrolls say `(Conjuration/Summoning)`.
- Power Word: Sleep belongs to Enchantment (`4`, Invoker exclusion on the spell and ITM
  `0x2d` bit `0x08` on its scrolls), and its description and scroll say `(Enchantment/Charm)`.


Find Familiar is the one spell of these written field by field: each game keeps its own way of
calling the familiar. EET picks the familiar by chapter, so it has the Hit Points of its campaign;
BG2:EE has only Shadows of Amn and Throne of Bhaal. The description names all three campaigns.

## Grease (`cbmagic_vanilla_grease`)

- Save vs. breath instead of vs. spell, keeping the base game's +2 bonus on the grease
  effect (opcode 158) and every effect that shares its roll. Its description and scroll
  say so.
- Flying, incorporeal and dragon creatures are immune by race (`WYVERN`, `BEHOLDER`,
  `MEPHIT`, `SPECTRE`, `WRAITH`, `SHADOW`, `MIST`, `DRAGON`).
- It lasts as its description says, 3 rounds + 1 round a level: one area per caster level
  (`cbmgr01.pro` to `cbmgr20.pro` via `ADD_PROJECTILE`, the game's `GREASE.PRO` with 4 to 23
  triggers). The base game's Grease lasts 10 rounds at every level.

## Stinking Cloud (`cbmagic_vanilla_stinking_cloud`)

- School set to Conjuration (`2`, Diviner exclusion); description and scroll updated.
- Creatures that do not breathe are immune: undead (`GENERAL = UNDEAD`, SPLPROT row 1) and
  races `GOLEM`, `ELEMENTAL` and `SLIME`.

## Character Record entries (`cbmagic_record_base_game`)

The Character Record reflects the conditions actually applied by base-game spells. This
pass changes only portrait-icon entries and their `STATDESC` labels; it does not alter the
underlying gameplay effect, target, saving throw, duration, or a condition's cure.

- Mislabelled entries are corrected for Wraithform, Wild-surge Minor Globe, Protection
  From Good, Shadow Form, Defensive Stance, Mimic Web, and Spell Deflection. Stinking
  Cloud uses the sleep effect's native entry rather than a separately timed icon, including
  private payloads belonging to the spell.
- Missing entries are added beside the existing effects for Blur, Physical Mirror, Divine
  Favor, lowered fire/electrical resistance, Symbol, Pain, Selune's Blessing, the listed
  Wish outcomes, Jester/False Dawn confusion where it targets an enemy, and Nahal's
  Wildmagic. New named entries use private copies of the matching state icon.
- Death Ward, Enhanced Bard Song, Conjure Fire Elemental, and Dolorous Decay use the
  lifetime or dispellability of their own status effect. Salt Crystals relies on its native
  stun entry instead of a duplicate icon.
- Exaltation, poison cures, Heal, Remove Paralysis, Greater Restoration and the named Wish
  outcomes remove separately added Record rows when they cure the corresponding condition.
  Cure markers follow self-only abilities but otherwise target the recipient.
- The base Record labels for rows 55, 8 and 112 use new strings, `Stunned`, `Blinded`, and
  `Deafened`; shared dialog strings are never changed. Missing spells are silently skipped.

Every match is by opcode and parameter within an ability. Unrelated effects, additional
abilities, and other users of a native icon stay intact. A second install recognizes
matching entries and does not add another one.

## Record entries that follow a state (`cbmagic_record_live`, `lua/M_CBMREC.lua`)

A fixed entry would stay after a state ends early, so these follow the state at runtime. No spell
changes; EEex is required, without it they are left out.

- Invisible, Improved Invisibility, Sanctuary, Mirror Image and Reflected Image are listed while the
  state lasts, from any source, also items.
- Shield of the Archons, Minor Spell Deflection and Minor Spell Turning show their own name in place
  of the big spell's row, until the last level is spent. With the big spell active at the same time,
  the big spell's row stays.
- Only party members: nobody else has a record.

## Power Word: Sleep (`cbmagic_vanilla_power_word_sleep`)

- School set to Enchantment (`4`, Invoker exclusion); description and scroll updated.
- Elves and half-elves resist with the same probability windows as Sleep (`SPWI116`):
  SPLPROT row 15 (`RACE = ELF`) at 0-90 and row 19 (`RACE = HALF_ELF`) at 0-30.
- Undead (`GENERAL = UNDEAD`, row 1), dragons (`DRAGON`) and elementals (`ELEMENTAL`) are
  immune. The existing 20 HP gate and wake-on-damage stay in place.

## Spook and Horror (`cbmagic_vanilla_spook`, `cbmagic_vanilla_horror`)

- Undead (`GENERAL = UNDEAD`, SPLPROT row 1) are immune to both Spook and Horror.
- Creatures protected by True Seeing (`stat 118 TRUE_SIGHT > 0`) are also immune to Spook.

## Mirror Image and Reflected Image (`cbmagic_vanilla_mirror_reflected_image`)

Mirror Image and Reflected Image no longer stack with each other or with themselves:

- Reflected Image (`SPWI120`, level 1) refreshes itself on recast via leading opcode 321.
- Mirror Image (`SPWI212` and Contingency `SPWI298`, level 2) refreshes both `SPWI212` and
  `SPWI298`, removes any active Reflected Image (`SPWI120`) via leading opcode 321, and
  blocks `SPWI120` for its duration via opcode 206.

## Area damage ignores Mirror Images (`cbmagic_vanilla_aoe_bypass_mirror_image`)

Damage effects (opcode 12) on spells and items whose ability uses an area-of-effect
projectile (`.PRO` type 3) get the "bypass Mirror Image" save flag (bit 24). Single-target
projectiles and melee abilities stay untouched.

## Dispel Magic vs. magically created weapons (`cbmagic_vanilla_dispel_magic_items`)

Level-checked Dispel/Remove Magic spells (`WIZARD_REMOVE_MAGIC`, `WIZARD_TRUE_DISPEL_MAGIC`,
`CLERIC_DISPEL_MAGIC`, `INQUIS_DISPEL_MAGIC`) set the high word of opcode 58's second
parameter to `2` when a caster-level check is used, so magically created weapons are
dispelled by the same level check as other effects rather than unconditionally.

## Magic Resistance (`cbmagic_vanilla_magic_resistance`)

Priest Magic Resistance (`SPPR509`) adds its resistance bonus to the target's existing
Magic Resistance (opcode 166 parameter 2 = 0) instead of setting it (parameter 2 = 1), so
it never lowers a higher value. Because it now adds, a leading self-refresh (opcode 321)
replaces any previous casting of `SPPR509` on the same target. Its description is updated.

## Polymorph Self (`SPWI416` and the `CBMP*` files)

SCS's six forms with SCS's real values, built from this mod's own files; nothing of SCS is named.
The spell lasts 1 turn + 3 rounds a level (one ability a level, 1 to 20). On casting it gives the
natural form and the six forms as special abilities for the duration and opens a menu of the
forms (`CBMPOLY.2DA`). Taking a form first removes the powers of the last form (`CBMFREM`), then
puts the form's weapon in the magic weapon slot, gives the form again so it can be taken once
more, and gives the form's power (`CBMP*G`). The weapon holds the body: the look (opcode 135,
appearance only, from `CBMP*C` or the game's creature), Strength, exceptional Strength and
Dexterity, attacks, base Armor Class, resistances and, except for the ogre mage, the blocked
spell, item and talk buttons. The natural form (`CBMPNAT`) clears the weapon slot and the powers
and stays for the duration; one second after the forms end, `CBMPEND` does the same.

| Form | Strength / Dexterity | Base AC | Attacks | Weapon | Power |
| --- | --- | --- | --- | --- | --- |
| Hill Giant (`CBMPHG`) | 19 / 10 | 3 | 1 | 2d8 piercing, +1 | Barbarian Rage, once each time the form is taken |
| Ogre Mage (`CBMPOM`) | 18/00 / 12 | 4 | 1 | 1d10 slashing, +1 | can cast spells and use items |
| Spider (`SPWI495`) | 15 / 17 | 4 | 2 | 1d4+1 piercing, +1, poison | Web Tangle, once each time the form is taken |
| Mustard Jelly (`SPWI496`) | 14 / 9 | own | 1, 15 ft. | 5d4 crushing, +3, slow and poison | Magic Resistance 125%, resistances, immunities |
| Hell Hound (`CBMPHH`) | 18 / 15 | 4 | 1 | 1d10 piercing + 1d6 fire, +1 | Fiery Breath, 3d6, every 3 rounds; immune to fire |
| Rat (`CBMPRT`) | 10 / 20 | 4 | 1 | 1d2 piercing, +1 | Hide, at once again |

- The hill giant wears Icewind Dale's verbeeg look (animation `0xE293`, `E293.INI`, the 24
  `MGVE*.BAM` and 8 `VERBEE*.WAV`, taken from Icewind Dale: Enhanced Edition): BG2:EE has no hill
  giant art.
- The mustard jelly's slow is the one this mod gives every slow, so Haste and the slow cancel
  each other as everywhere else.
- In another form the Strength floors do not apply: the form keeps its values.

## Shapechange (`SPWI916` and the `CBMS*` files)

Built the same way as Polymorph Self from SCS's six forms and SCS's real values, with the same
remover and empty weapon. The spell lasts 6 turns (one ability), with its own natural form
(`CBMSNAT`), end (`CBMSEND`) and menu (`CBMSHAP.2DA`). The forms keep the game's resources where
the game has them (`SPIN152`-`SPIN154`, `CDMINDFL.ITM`, `CDGOLIRO.ITM`, `TROLLALL.ITM`, the
creatures `SHMIND`, `SHIRON`, `SHTROLL`, `STALKE`), written whole by this mod.

| Form | Strength / Dexterity | Base AC / THAC0 | Attacks | Weapon | Powers and protections |
| --- | --- | --- | --- | --- | --- |
| Mind Flayer (`SPIN152`) | 10 / 10 | 3 / 11 | 4 | 1d2 crushing, +2, Intelligence -5 for 30 s | MR 90%, 50% physical; Psionic Blast (stun 60 s, save vs. Spell), again at once; can cast |
| Iron Golem (`SPIN153`) | 24 / 9 | 3 / 3 | 1 | 4d10 crushing, +4 | MR 100%, fire 125%, cold, electricity and acid 100%, 20% physical, weapons below +3 cannot hurt it, no backstabs; Gas Cloud every 3 rounds |
| Giant Troll (`SPIN154`) | 22 / 18 | 4 / 8 | 3 | 2d6 piercing, +2 | regenerates 5 HP every few seconds (about 2 a second), faster, immune to hold, paralysis, sleep, stun; can cast |
| Marilith (`CBMSMA`) | 19 / 18 | -6 / 8 | 5 | 1d8 slashing, +4, random elemental damage and poison | MR 85%, immune to fire and electricity, 50% cold, immune to charm, fear, poison, disease; Teleport, again at once; can cast |
| Greater Basilisk (`CBMSBA`) | 18 / 10 | 2 / 11 | 3 | 1d8+2 piercing, +2, poison for 20 s (3 at a time) | Petrifying Gaze (save vs. Polymorph at -6), again at once |
| Invisible Stalker (`CBMSIS`) | 18/10 / 17 | -3 / 11 | 1 | 2d8 crushing, +2 | improved invisibility every round, 80% missiles, 30% elements; can cast |

Two slips in SCS's data are corrected: the stalker's base Armor Class -3, which SCS writes as
65533, and one of the iron golem's three weapon immunities, whose two values SCS swaps (opcode 120
type 1, "magical", which with "non-magical" would leave no weapon able to hurt it); the golem now
has the game's own iron golem immunity (non-magical, +1 and +2). Copied monster weapons protect
creatures that are immune to their poison through the weapon itself.

## Strength floors (`cbmagic_strength_floor`, `lua/M_CBMSTR.lua`)

A spell of this mod that gives a fixed Strength never lowers a higher one, and bonuses and
penalties from other sources count on top of it, in whatever order they came:

| Spell | Strength at least | Notes |
| --- | --- | --- |
| Strength (`SPWI214`, scroll `SCRL98`) | 18 | plus its own +50 exceptional Strength, as before |
| Strength of One (`SPPR312`) | 18/75 | written whole, without the sub-spell |
| Divine Power (`SPPR412`) | 18/00 | |
| Champion's Strength (`SPPR507`) | 18/00 | |
| Animal Rage (IWDification, `CLERIC_ANIMAL_RAGE`) | 19 | given its floor at install, in its own slot |

- How: the spell carries a marker instead of setting Strength: opcode 44 by 0 with the resource
  `CBTSTRF` and Strength × 1000 + exceptional Strength in its special field, beside a private
  spell state (`CBM_STR_FLOOR`). After each pass of a creature's effects, the EEex listener takes
  the highest marker and adds every Strength bonus and penalty on the creature: opcode 44 by a
  value, opcode 97 by a value, and the oldest Draw Upon Divine Might (opcode 132), also inside
  EFF files (opcode 177). Effects still waiting to start do not count. When that gives more than
  the game worked out without the floor, the Strength (and exceptional Strength at 18) becomes
  that; otherwise the game's value stays. Strength stays between 1 and 25.
- A set Strength from elsewhere, such as a potion of giant strength or Ray of Enfeeblement, is
  part of what the game works out: the higher of the two wins.
- A creature in another form keeps the values of its form: polymorphed, or with any opcode 135 on
  it, as Polymorph Self's forms, which change only the look.
- In a fight the written Strength counts like the game's own: measured in the lab with fists.
- Without EEex the four spells of defs/ come in their versions from `defs/without-eeex/`, which
  set Strength as the game does (Strength of One there keeps its sub-spell and guards), and
  Animal Rage stays as IWDification wrote it. The log names each such file.

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

The three probability windows (`[0, c12-1]`, `[c12, c12+c16-1]`, `[c12+c16, 100]` for 12,
16 and 24 Hit Dice elementals) scale per ability level while keeping each spell's other
effects (including mental combat on the wizard spells):

- Wizard Conjure Fire, Air and Earth Elemental: 64%/35%/1% at level 12, shifting 1% per
  level from 12 HD to 24 HD (60%/35%/5% at level 16, 56%/35%/9% at level 20+).
- Druid Conjure Fire and Earth Elemental: 64%/35%/1% at level 11, 61%/37%/2% at level 12,
  52%/42%/6% at level 15, and 37%/51%/12% at level 20+ (interpolated evenly across levels
  11-20 with sums at 100%).

## IWD Hopelessness (`cbmagic_iwd_hopelessness`)

IWDification's Emotion: Hopelessness and Symbol: Hopelessness stay as they are, with their own
area and icons. A last native TookDamage condition on each invokes a private helper that removes
only that spell's own effects, including its stun, icon and delayed effects. Actual damage
therefore ends its hopelessness without curing an unrelated stun or restoring Hope. Both get a
complete description. A game without the IWD version keeps the base game's spell, whose sleep
wakes on damage.

## Wizard elemental contests (`cbmagic_iwd_wizard_elementals`)

All wizard Conjure Fire, Air, Earth and Water Elemental spells, and their four Lesser forms, have
the base game's three-round contest: 15% of the elementals turn hostile. IWDification removes the
contest from the shared creatures, so the mod ships its own copies of them, with the game's own
contest scripts. A successful enemy casting stays hostile to the party, as in the base game. Fire,
Air, Earth and Water use the 64%/35%/1% 12/16/24-Hit-Dice distribution at level 12, moving one
point per level from the 12-HD tier to the 24-HD tier and reaching 56%/35%/9% at level 20. Each
Lesser form summons an 8-HD elemental. The two water spells exist only with IWDification; they
keep its name and icons. Druid elementals have no contest.

## Druid-only priest spells (`cbmagic_vanilla_barkskin_druid`, `cbmagic_vanilla_animal_summoning_1_druid`, `cbmagic_vanilla_animal_summoning_2_druid`, `cbmagic_vanilla_animal_summoning_3_druid`, `cbmagic_vanilla_conjure_animals_druid`)

Barkskin, Flame Blade, Animal Summoning I-III and Conjure Animals are restricted to druids
and rangers (cleric/paladin exclusion bit set in the priest class word at SPL offset
`0x20`, preserving alignment bits).

## New druid spells

- **Conjure Air Elemental:** a new level-6 druid spell, using the same druid/ranger class
  setting as the other druid elementals. It targets a point within 35 feet, lasts one turn per
  caster level (up to 20 turns), and summons a 12-, 16-, or 24-Hit-Dice air elemental. The
  chances progress from 64%/35%/1% at level 11 to 37%/51%/12% at level 20, with the decided
  interpolated values at the intervening levels. The elemental has no control contest.
- **Icelance:** a new level-3 spell in the druid spell category, therefore available to druids,
  shamans and rangers without a separate ranger grant. It automatically deals 5d6 cold damage to
  one creature within 100 feet. A Save vs. Spell negates only the three-round stun; it never
  negates the damage. There is no priest scroll.
  It ships with native icons and missile; where IWDification brought the wizard spell's art, it
  uses that.

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
- Invisibility Purge (`cbmagic_vanilla_invisibility_purge_ct`): 8 to 3.
- Strength (`cbmagic_vanilla_strength_ct`): 9 to 5.
- Fire Seeds (`cbmagic_vanilla_fire_seeds_ct`): 9 to 6.
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
- **Invisibility Sphere (`cbmagic_kept_invisibility_sphere`)**: renames Invisibility, 10'
  Radius to Invisibility Sphere in spell and scroll names and descriptions, sets casting
  time to 1 (from 9), duration to 1 turn (60 seconds, from 24 hours), and uses an
  ally-only radius-110 area (`cbminv10.pro` via `ADD_PROJECTILE`).
- **Confusion (`cbmagic_kept_confusion`)**: lasts 4 rounds at levels 1-14, 5 rounds at
  levels 15-19, and 6 rounds at level 20+, preserving existing ability breakpoints. Save
  vs. Spell at -2 and all other properties stay as in the base game.
- **Chaos:** lasts 4 rounds at level 1, 5 rounds at level 15, and 6 rounds at level 20. Its
  automatic low-Hit-Dice branch and its Save vs. Spell at -4 branch remain separate.
- **Sequencers and Contingencies (`cbmagic_kept_minor_sequencer`,
  `cbmagic_kept_contingency`, `cbmagic_kept_spell_sequencer`,
  `cbmagic_kept_spell_trigger`, `cbmagic_kept_chain_contingency`)**: Minor Sequencer,
  Contingency, Spell Sequencer, Spell Trigger, and Chain Contingency belong to the
  Universal school and clear specialist exclusion flags on the spells and their scrolls, so
  all specialist mages (including Diviners) can learn and cast them.
- **Teleport Field (`cbmagic_kept_teleport_field`)**: range is 30 ft. (from 40 ft.) and
  enemies in the field get a Save vs. Spell at -4 to avoid being teleported (base game: no
  save).
- **Oracle (`cbmagic_kept_oracle`)**: dispels illusion spells up to 9th level (from 5th)
  in a 30-ft (radius 450) enemy-only area around the caster (`cbmoracl.pro` via
  `ADD_PROJECTILE`, range 1) and updates the affected-spell list in the description.
- **Sphere of Chaos (`cbmagic_kept_sphere_of_chaos`)**: the wizard spell keeps its name,
  level 7, point targeting within range 40 ft., and 10-round enemy-only field. Priest
  Confusion (level 7) becomes the same spell, with the same range and field. Each round, enemies in the area save
  vs. Spell at -4 or suffer one of 5 equally likely effects for 1 round (6 seconds): feeblemind,
  confusion, panic, sleep waking on damage, or hold.

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
- **Command:** one creature within 30 feet falls asleep for one round unless it makes a Save
  vs. Spell. Damage wakes the target. The saving-throw penalty is -1 for each two caster levels
  after 1st, to a maximum of -4 at 9th level.
- **Faerie Fire (`cbmagic_kept_faerie_fire`)**: new level-1 druid-only spell added via
  `ADD_SPELL` (`CLERIC_CBMAGIC_FAERIE_FIRE`), using ability location 2 and base-game
  Invisibility Purge icons (`SPPR309C` / `SPPR309B`). In a hostile 5-ft (radius 75)
  enemy-only area (`cbmffir.pro` via `ADD_PROJECTILE`, range 20, casting time 1), targets
  that fail a Save vs. Spell suffer a -2 AC penalty, lose and cannot gain invisibility,
  and glow violet for 4 rounds.
- **Aid (`cbmagic_kept_aid`)**: replaces the base game's combined Bless/HP effect (opcode
  129) with a hit-point-only bonus of `1d8 + min(L, 10)` where `L = max(ability level, 3)`,
  lasting 1 turn per level, refreshing on recast, and displaying its own portrait icon
  (appended to `STATDESC.2DA` using `SPPR150D`).
- **Silence 15' Radius (`cbmagic_kept_silence`)**: affects enemies only instead of all
  creatures in the area.
- **Free Action (`cbmagic_kept_free_action`)**: usable by druids and rangers as well as
  clerics, lasts 1 turn per level (scaling all timed protections and companion state, stat,
  and visual effects), protects against Stun, and no longer blocks Haste or movement rate
  bonuses.
- **Neutralize Poison (`cbmagic_kept_neutralize_poison`)**: cures poison and grants
  immunity to poison for 1 turn per level (levels 7-20); no longer heals 10 Hit Points or
  cures disease, paralysis, blindness, or deafness (removing non-self opcode 321 disease and
  paralysis resource removals).
- **Divine Power (`cbmagic_kept_divine_power`)**: renames Holy Power to Divine Power in
  name and description, sets casting time to 4 (from 6), and grants non-fighter clerics
  (single-class Cleric, Cleric/Thief, Cleric/Mage) dispellable fighter bonus attacks per
  round (+1/2 APR at levels 7-12, +1 APR at level 13+).
- **Negative Plane Protection (`cbmagic_kept_negative_plane_protection`)**: lasts 1 turn
  per level (levels 7-20, 420-1200 seconds) for both clerics and druids; all other
  properties stay as in the base game.
- **Iron Skins / Stoneskin (`cbmagic_kept_iron_skins`)**: renamed Stoneskin, with casting
  time 1 (from 9); skin progression and duration stay as in the base game.
- **Mass Regenerate (`cbmagic_kept_mass_regenerate`)**: new level-5 druid-only spell added
  via `ADD_SPELL` (`CLERIC_CBMAGIC_MASS_REGENERATE`), using ability location 2 and
  base-game Regeneration icons (`SPPR711C` / `SPPR711B`). In a sight-range party-only area
  around the caster (`cbmmreg.pro` via `ADD_PROJECTILE`, radius 452, casting time 5), party
  members within sight regenerate 2 Hit Points per round (1 HP every 3 seconds) for 1 turn +
  2 rounds per level (up to 30 rounds at level 10); a new casting replaces the previous one.
- **Regenerate (`cbmagic_kept_regeneration`)**: restricted to druids, stays level 7, heals
  2 Hit Points per second (from 3) for 1 round per level (from 1 round per 2 levels), and
  replaces an earlier casting on the same target.
- **Greater Restoration (`cbmagic_kept_greater_restoration`)**: keeps the base game's
  cures, casting time (3), and caster fatigue drawback, and additionally cures Hold, Stun,
  Sleep, Petrification (removed before the full heal), Polymorph, curses, Blindness, and
  Deafness.
## SCS-style spell changes (`chriz-bg-magic/lib/cbmagic_scs.tpa`)

Every decided SCS-style spell change is implemented in our own library (`cbmagic_scs.tpa`), resolved through `SPELL.IDS`, and checks whether the target behaviour is already present so it works with or without SCS installed:

- **Chromatic Orb (`cbmagic_scs_chromatic_orb`):** uses the IWD/SCS level progression without the +6 saving throw bonus, sets range to 50 ft., clears the misplaced Conjurer exclusion bit (`0x0080`), and preserves per-ability foreign effects:
  - Level 1: 1d4 magic damage + blind for 1 round (save vs. spell negates the secondary effect).
  - Level 2: 1d6 fire damage + pain (-1 AC and THAC0) for 1 round.
  - Level 3: 1d8 magic damage + 1d3 fire damage (no save).
  - Level 4: 1d10 magic damage + blind for 4 rounds.
  - Level 5: 1d12 magic damage + stun for 3 rounds (Free Action protects against the stun).
  - Level 7+: 2d8 magic damage + hold for 13 rounds (Free Action protects).
- **Melf's Minute Meteors (`cbmagic_scs_melfs_minute_meteors`):** resolved via `WIZARD_MELF_METEOR`; the created meteor weapon (`MELFMET.ITM`) strikes as a +2 weapon instead of +5.
- **Skull Trap (`cbmagic_scs_skull_trap`):** damage is capped at 12d6 in place across all abilities (preserving higher-level abilities and any unrelated effects on them).
- **Lower Resistance (`cbmagic_scs_lower_resistance`):** lowers magic resistance by 30% + 1% per caster level (was 10% + 1% per level) and sets power level to 5 on its resistance-lowering effects so spell protections block it normally.
- **Power Word: Silence, Stun, Blind, Kill (`cbmagic_scs_power_word_silence`, `cbmagic_scs_power_word_stun`, `cbmagic_scs_power_word_blind`, `cbmagic_scs_power_word_kill`):** moved from Conjuration to Enchantment (Invoker exclusion `0x0800` instead of Diviner `0x0100` on the spells; kit usability byte `0x2d` bit `0x08` instead of `0x01` on their scrolls). Power Word: Stun is blocked by Free Action; Power Word: Blind targets a single creature instead of an area.
- **Mantle, Improved Mantle, Absolute Immunity (`cbmagic_scs_mantle`, `cbmagic_scs_improved_mantle`, `cbmagic_scs_absolute_immunity`):** protect against weapons up to +3, +4, and +6 enchantment respectively (up from +2, +3, and +5).
- **Project Image and Simulacrum (`cbmagic_scs_project_image`, `cbmagic_scs_simulacrum`):** `PROJIMAG.SPL` disables quick-slot items (buttons 9, 11, 12) and innate abilities (button 13); `SIMULACR.SPL` disables quick-slot items (buttons 9, 11, 12) and, with EEex, calls `CBMSIMU` (`lua/M_CBMSIM.lua`) on the copy: it keeps the special abilities its class and kit tables (`KITLIST.2DA`, `CLAB*.2DA`, `GA_` entries) give at its own levels, as often as those levels give them; uses beyond that count as spent, and spent ones stay spent. High-level abilities stay only if each of its levels reaches what 3,000,000 experience gives (`XPLEVEL.2DA`, `LUABBR.2DA`). Every other ability (items, quests, scripts) is removed. The game's limits on the copy stay. Without EEex the game's Simulacrum text stays.
- **Abi-Dalzim's Horrid Wilting (`cbmagic_scs_abi_dalzim`):** undead, golems, animated swords, and air/earth/fire elementals are immune.
- **Wizard and Priest Symbols (`cbmagic_scs_wizard_symbol_death`, `cbmagic_scs_wizard_symbol_stun`, `cbmagic_scs_wizard_symbol_fear`, `cbmagic_scs_cleric_symbol_death`, `cbmagic_scs_cleric_symbol_stun`, `cbmagic_scs_cleric_symbol_fear`):** moved from Conjuration to Enchantment (updating spell school, Invoker exclusion on wizard symbols and their scrolls, and descriptions while preserving priest exclusions) and use the party-friendly symbol explosion projectile so they affect only enemies; Symbol, Stun is also blocked by Free Action.
- **Cacofiend, Summon Fiend, Wizard Gate, Priest Gate (`cbmagic_scs_cacofiend`, `cbmagic_scs_summon_fiend`, `cbmagic_scs_wizard_gate`, `cbmagic_scs_cleric_gate`):** summon a fiend matching the caster's law/chaos alignment (Bone Fiend / Cornugon / Pit Fiend for lawful casters; Nabassu / Glabrezu / Balor for neutral and chaotic casters), with dedicated species combat scripts (`CBMGBONF.BCS`, `CBMGCORN.BCS`, `CBMGBALR.BCS`: guarded hostility transition, 6-second area fear aura via `DEMON_FEAR`, and on Balor 30-second Stoneskin renewal and innate fiend Domination `CBMGBDOM.SPL`).
- **Blade Barrier and Globe of Blades (`cbmagic_scs_blade_barrier`, `cbmagic_scs_globe_of_blades`):** aura damage payload spells (`SPPR603D`, `SPPR698D`, `SPPR725D`, traced across abilities through `op177`/`.EFF` and verified to carry `opcode 12` damage) affect only hostile creatures, and a successful save vs. spell halves the damage instead of negating it (with `SPPR698D` also updated to range 6 and 8d8 damage). Blade Barrier's casting time is reduced from 9 to 6.
- **Call Lightning (`cbmagic_scs_call_lightning`):** lasts 1 round per caster level up to 11 rounds/bolts (projectiles 85..91).
- **Defensive Harmony (`cbmagic_scs_defensive_harmony`):** restricted to clerics/paladins (`0x20 = 0x8000`) and grants +4 general AC (was +2).
- **Glyph of Warding (`cbmagic_scs_glyph_of_warding`):** casting time reduced from 9 to 5, and a successful save halves the damage instead of negating it.
- **Magical Stone (`cbmagic_scs_magical_stone`):** deals 3d4 crushing damage (6d4 against undead) instead of 1d4 via non-dispellable `.EFF` files (`0x5c = 0`).
- **Summon Insects, Insect Plague, Creeping Doom (`cbmagic_scs_insect_plague`):** main spells strip their own repeating damage (`opcode 272`) and deliver all damage and effects through their subspells; spell failure allows a per-round save vs. breath (at 0, -2, and -2); Fire Shields (Red, Blue, Aura of Flaming Death) remove active swarms and block them (`op206`); Stoneskin holds off the secondary effects while skins remain (each damage tick strips a skin); items and spells granting immunity to normal weapons (`op120 p2=2`) block and remove them; Death Spell (`SPWI605`) disperses active swarms in its area; undead are immune; magic resistance and Dispel Magic do not help.
- **Nature's Beauty (`cbmagic_scs_natures_beauty`):** both humanoid slay (`opcode 55`, save vs. spell +3) and blindness are moved to a schoolless area subspell (`CBMGNB1.SPL`, `target = 5`, `projectile = 159`, so True Sight does not dispel it via school removal and a single effect list decides both death and blindness): on a failed save, humanoids die and targets suffer permanent blindness; on a successful save, targets are blinded for 3 rounds.
- **Lesser Restoration:** stays cleric-only as in the base game. With EEex it also ends temporary
  attribute drain: its opcode 402 calls `CBMLRES` (`lua/M_CBMRST.lua`), which ends every running
  timed effect on the recipient that lowers Strength, Dexterity, Constitution, Intelligence,
  Wisdom or Charisma (opcodes 6, 10, 15, 19, 44, 49: a lower value, a fixed value below 12, or a
  share below 100 %). Disease is opcode 78 and not touched; permanent loss is no timed effect. Blood
  Rage's own weakness stays: the installer names that spell's file in the module. When a source's
  drain ends and nothing else of that source stays, its icon, sound and visual go too (Ray of
  Enfeeblement); Energy Drain keeps its save penalty and icon. No spell or item that drains is
  rewritten. Without EEex the game's spell stays.

## Additional decided spell changes (`chriz-bg-magic/lib/cbmagic_more.tpa`)

- **Priest Protection From Cold (`cbmagic_more_protection_from_cold`) and Protection From Acid (`cbmagic_more_protection_from_acid`):**
  - Two new priest spells for both clerics and druids (`0x20 = 0x0000`) added via `ADD_SPELL`, using ability location `2` (spell book) and base-game graphics.
  - **Protection From Cold** (`CLERIC_CBMAGIC_PROTECTION_FROM_COLD`, Priest level 3): built with the same duration scaling (`3 rounds + 1 round/level`, levels 1-20, 24-138 seconds), casting time (6), touch range (1), school (Abjuration), secondary type (`SpecificProtections`), self-refresh (`opcode 321`), spell state (`BUFF_PRO_EFFECTS` = 65), visuals (`ICrmpari` + RGB fade `61`), and expiry sound (`EFF_E04`) as Priest level 3 Protection From Fire (`SPPR306`), granting +100% normal cold resistance (`opcode 28`) and +80% magical cold resistance (`opcode 85`), with base-game cold icons (`SPWI320C` / `SPWI320B`), portrait icon `25` (`Protection From Cold`), and status string `7565`.
  - **Protection From Acid** (`CLERIC_CBMAGIC_PROTECTION_FROM_ACID`, Priest level 4): built with the same duration scaling (`5 rounds/level`, abilities at level 1 and levels 8-18, 210-540 seconds), casting time (7), touch range (1), school (Abjuration), secondary type (`SpecificProtections`), spell state (`BUFF_PRO_EFFECTS` = 65), visuals (`ICrmpari` + RGB fade `61`), and expiry sound (`EFF_E04`) as Priest level 4 Protection From Lightning (`SPPR407`), setting acid resistance to 100% (`opcode 27`, `parameter2 = 1`, which covers both normal and magical acid since the engine has no separate magical acid stat), with base-game acid icons (`SPWI517C` / `SPWI517B`) and portrait icon `24` (`Protection From Acid`).
- **Dispelling Screen (`cbmagic_more_dispelling_screen`):**
  - Replaces Spell Immunity (`SPWI510`) on Wizard level 5 (and its scroll `SCRL6S.ITM`, adding `2510 WIZARD_DISPELLING_SCREEN` to `SPELL.IDS` alongside `WIZARD_SPELL_IMMUNITY`) with Spell Revisions' Dispelling Screen: lasts 5 turns (300 seconds), affects the caster and allies in a 15-ft party-only area (`projectile = 158`, `INAREAPA`), and protects each recipient against one Dispel/Remove Magic (`opcode 101` against `opcode 58` plus string suppression for `14056`) or one Breach (`opcode 206` against `SPWI513B`).
  - Breach (`SPWI513`, and Wish Breach `SPWISH26` / `SPWISH38` if present) is split into `SPWI513B.SPL` (original Breach payload) + `SPWI513C.SPL` (`opcode 221` removing secondary type `cbm_DispelScreen`), and non-self Dispel/Remove Magic abilities on spells and items receive a trailing `opcode 221` for `cbm_DispelScreen`, so one Breach or one Dispel Magic is absorbed and then strips the screen.
  - Pierce Shield (`SPWI805`) and Spellstrike (`SPWI903`) strip `cbm_DispelScreen` via `opcode 221` without being absorbed, and their descriptions and scrolls (`SCRL9A`, `SCRL9M`) name Dispelling Screen instead of Spell Immunity.
  - Spell Immunity's school-selection menu (`opcode 214` / `SPWI510.2DA`) is removed, and its 8 hidden school subspells (`SPWI590`..`SPWI597`) are redirected to cast `SPWI510` (`opcode 146`), so any creature or AI script that memorised or casts `SPWI510` or `SPWI590`..`SPWI597` casts Dispelling Screen.
- **Nahal's Reckless Dweomer (`cbmagic_more_nahals_reckless_dweomer`):**
  - Stays a very strong spell as in the base game, except it loses Aura Cleansing: ability target is changed from `7` (caster-instant, bypassing `CGameSprite::Spell`'s round aura check) to `5` (caster, normal spell action) across all abilities so casting Nahal's Reckless Dweomer obeys the normal 1-spell-per-round aura timer, and any explicit `opcode 188` (Cleanse Aura) effect is removed while preserving all other effects and ability breakpoints.
- **Improved Haste (`cbmagic_more_improved_haste`) and Haste / Slow mutual cancellation (`cbmagic_more_haste_cancels_slow`):**
  - **Improved Haste (`SPWI613`, scroll `SCRL7Q.ITM`)**: becomes the party buff of Spell Revisions, built cleanly without `opcode 16` so there is no second speed clock. Keeps all 9 ability headers (`min_level` 1, 13..20), uses Area target (`4`), range 30 ft., casting time 6, party-friendly 15-ft radius projectile `158` (`INAREAPA`), and lasts 1 turn (60 seconds), dispellable (`sectype = 13` `NON-COMBAT`, `resist_dispel = 3`). Grants +6 movement rate (`opcode 176`), +1 attack per round (`opcode 1`), +2 THAC0 (`opcode 54`), +2 Armor Class (`opcode 0`), and +2 Saving Throws vs. Breath (`opcode 36`), with portrait icon `110` (`Improved Haste`), status string `14023` (`Hasted`), Alteration visual, RGB fade, and sounds `EFF_M28` / `EFF_M29`. Ends any running Slow (`opcode 221` for `cbm_Slow` + `opcode 240` for icon 41) or normal Haste (`opcode 221` for `cbm_Haste` + `opcode 240` for icon 38), makes recipients immune to Slow for its duration (`opcode 101` against `opcode 40`, `opcode 169` for icon 41, `opcode 267` for Slow strings, `opcode 206` against Slow spells, and `HASTE_IMMUNITY` in `SPLSTATE.IDS` blocking extracted Slow subspells), and prevents cumulative stacking with Haste and itself (`opcode 206` + `HASTE_IMMUNITY`).
  - **Haste and Slow cancel each other (`cbmagic_more_haste_cancels_slow`)**: follows SCS `haste_cancels_slow.tpa` across all spells and items with timed `opcode 16` (Haste) or `opcode 40` (Slow) in their abilities. Haste payloads (including `opcode 93` fatigue and companion icons/strings/sounds) are extracted into `cbm_Haste`-sectype subspells and Slow payloads (including AC/THAC0 penalties and companion icons/strings/sounds) into `cbm_Slow`-sectype subspells. Haste on a slowed target displays `"Slow cancelled by Haste"` (`CBMNEG40.SPL`), blocks the Haste (and its fatigue) from starting, and removes `cbm_Slow`; Slow on a hasted target displays `"Haste cancelled by Slow"` (`CBMNEG16.SPL`), blocks the Slow from starting, and removes `cbm_Haste`. Normal Haste stays vanilla in every other way (bonus, duration, fatigue).

## Descriptions

Changed texts are added as new strings and the spell (and its scrolls) point to them; the
old strings, which other resources may share, stay. The text patterns exist only in
English so far: on a game in another language the installer warns that those
descriptions still describe the old behaviour.

- **Scrolls** (`cbmagic_scroll_texts`, generated, and `cbmagic_text_to_scrolls`): every scroll
  of the game that casts or teaches a spell whose description this mod writes shows that
  description, also a scroll the mod does not ship. Nine of the game's own scrolls had kept the
  old text (Polymorph Self, Shapechange, Simulacrum, Chaos, Champion's Strength, the three
  Conjure Lesser Elementals, the Restoration scroll).
- **Elementals** (`cbmagic_elemental_names`): the elementals this mod summons carry one name per
  size, the same for every element: Lesser (8 Hit Dice), plain (12), Greater (16) and Elder (24).
  The files had the game's names, which called every water elemental "Greater Water Elemental"
  and every earth and fire elemental plainly by its element.

## The main character as a statue or imprisoned (`cbmagic_main_character`, `lua/M_CBMP1.lua`)

Needs EEex; without it nothing here is installed and the game ends as before. Seen working in a
BG2:EE lab game (see the evidence file). Travel into story areas is not blocked while he is out:
that is left out for now, to be judged in play (a block could cut the way to a cure).

- **Petrification no longer ends the game.** On the main character, petrification (opcode 134,
  opcode 13 "stoned") becomes a statue (`CBMP1ST`): held (opcode 185, which Free Action does not
  stop), stone grey, the game's "Petrified" message and the Held icon. The statue is tough, not
  glass: 50% resistance to slashing, piercing, missiles, fire and cold, 25% to crushing, 75% to
  electricity, no poison, disease, level drain or death magic. Destroyed, it is his death.
- **Imprisonment no longer ends the game.** It becomes a prison (`CBMP1IM`): a maze with an
  endless fixed duration (opcode 213, parameter 2 = 1) and the Imprisonment icon.
- **Only the real cures help.** Stone to Flesh (opcode 43) from any source ends the statue
  (`CBMP1CU`). Freedom ends the prison only in the area where he vanished and puts him back on
  that spot (`CBMP1FR`), as the spell's text says. The engine frees every prisoner of an area
  through whoever a Freedom reaches there, past his own screen, so the tick checks the place:
  away from it the prison closes again within a second.
- **How it hooks in.** A screen (EEex opcode 403, `CBMP1NT`, kept through death) sees such effects
  before the engine rolls their save, so it blocks them and casts the state through opcode 146
  with the old effect's save, level and source; opcode immunity (Protection from Petrification) is
  checked by the screen. Other creatures keep the game's own petrification.
- **A prisoner's spell states are not kept up** by the engine: they read unset, and bits written
  into his stats are wiped within seconds. So the module reads the prison from his effect list
  (`P.scan`), and scripts get the global `CBM_P1_OUT` (1 while he is a statue or imprisoned). The
  spell state `CBM_P1_OUT` is reliable for the statue only.
- **Companions** keep the game's petrification and imprisonment: they leave the party as before,
  so the others can fetch help. The game also empties their party AI slot, and joining again puts
  a standard script there. The screen (on every party member) keeps their own script first; when
  Stone to Flesh or Freedom reaches them, they rejoin the party if there is room, and the tick
  gives the script back.
- **The party takes him along.** Two jump hooks in the engine's gather check (`LeaveArea` for map
  edges and the world map, `LeaveAreaName` for exits) let one more member pass like a dead one:
  the one whose address stands in a cell the tick keeps. The engine then moves him with the
  party. The patterns (`eeex/CBMP1.db`, `Baldur.exe` 2.7.3.0) and the bytes are checked at start;
  anything else keeps the hooks off, and then the party cannot leave while he is out.
- **The world tick** (`baf/cbmp1.baf` on top of every campaign's world script from
  `CAMPAIGN.2DA`, or on `BALDUR` and `BALDUR25` where that table names none): it puts the screen
  on every member, keeps the cell and the global, ends the game when nobody else in the party can
  act (alive, not charmed, not imprisoned), imprisons him again after a cutscene woke him, tidies
  up after a Freedom, and pulls him after the party when a script moved everyone else away.
- **Dead ends.** Where the party cannot leave by its own choice and carries no cure for what holds
  him, the game ends after 30 seconds without combat, as it always did (`CBMP1_Stuck`, a second
  block in the world scripts behind `!ActuallyInCombat()`; the clock is the global `CBM_P1_CLOCK`,
  so a fight, a pause or a scene stops it without clearing it). In doubt nothing counts as a dead
  end or as "no cure":
  - Dead ends are only what the game's data proves (no working exit, no way onto the world map,
    the scripts that move the party out wait for the story): the circus tent under Kalah's
    illusion, Spellhold's dungeon, maze and tests, Hell, the start of Throne of Bhaal, the Pocket
    Plane before its exit works, Sendai's chamber while its portals are shut, the Throne of Bhaal,
    and in Siege of Dragonspear Avernus and the last scene. Places one can fight a way out of
    (Irenicus' dungeon, the Sahuagin city, Watcher's Keep) are none. Further places that are
    likely shut for a time (the Planar Sphere away from Athkatla, Spellhold's upper floors, Ust
    Natha with its gate shut, Pocket Plane challenges, Abazigal's chamber, parts of Dragonspear
    castle, the Isle of Balduran, the fights with Sarevok) are not counted yet: there the party
    is stuck without the game ending.
  - Cures are listed at install from every spell and item of the game with Stone to Flesh's
    effect (opcode 43) or Freedom's (opcode 212), also through a spell they cast, whatever mod
    brought them. A cure counts with a companion who is alive and not imprisoned: a spell ready
    to cast, a spell in a book where the area allows resting, or an item carried (bags included,
    whoever could use it). What the main character carries himself does not count. A statue
    inside a prison needs both cures.
- **Dreams wait** while he is out (`baf/cbmp1_dream.baf`, on the global): his own dream script
  (`PLAYER1D`), every companion's dream script from the campaigns' dialog tables (`PDIALOG`,
  `25DIALOG`, `BGDIALOG`, `BDDIALOG`) and the Solar's calls after a rest in Throne of Bhaal
  (`PartyRested()` in `AR4000`). A dream that did not run keeps its variable unset and comes at
  the first rest after he is free.

## Celestial summons (`cbmagic_main`)

- Summon Deva, Summon Fallen Deva, Summon Planetar, Summon Dark Planetar and the paladin's two
  summons take 1 round to cast, reach 30 ft. and last 3 turns (devas) or 2 turns (planetars).
  The game's own effects `SPDEVA`, `SPDEVA2`, `SPPLAN` and `SPPLAN2` now call `cbmdevag`,
  `cbmdevae`, `cbmplang` and `cbmplane`, so every spell that uses them reaches these creatures.
- The creature files in `defs/` hold what the game then adds to: CON 18 gives 36 Hit Points,
  DEX the Armor Class bonus, STR 19 and the +3 weapon the THAC0, and the fighter levels one more
  attack. The numbers in the descriptions are the ones in play.
- No permanent Haste for planetars. The look is an elf cleric (devas) or elf mage (planetars)
  with the game's own wing animation in the helmet slot.
- Gender is BOTH, as on the game's celestials: the gender SUMMONED would let Death Spell destroy
  a creature whose description says it is immune to death magic.
- Combat stays under the game's `BDSUM00`; which spells it casts is the player's choice. An enemy's
  celestial gets the game's own celestial script on arrival (`DEVAGOOD`, `DEVAEVIL`, `PLANGOOD` in
  the class slot), so it casts as the game's celestials do, and as whatever mod changed those
  scripts makes them do.
- The limit is a small override script, `defs/baf/cbmdevac.baf` for devas and
  `defs/baf/cbmplanc.baf` for planetars, compiled to `chriz-bg-magic/files/`. The game's own limit
  in `SUMMLIMT.2DA` does not help: it counts one shared CELESTIAL row by fixed names and animations.
  A newcomer on the party's side asks through a global; one that has arrived answers, in sight or
  not; the newcomer then shows the game's summon limit message and leaves. Without an answer in
  three seconds it stays. Enemy summons neither ask nor answer.
