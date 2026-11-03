# Install checks, 2026-11-04

The five fixes of branch `claude/first-five-fixes`, installed in two disposable labs built
from clean game copies. These are install-time checks of the data; nothing was tried in
play (no game was launched).

## Labs

| Lab | Game | Mods before Chriz BG Magic |
|---|---|---|
| A | BG2:EE 2.7.3.0 (clean copy) | EEex v1.3.1 (components 0, 1, 8) |
| B | EET: BG:EE 2.7.3.0 with Siege of Dragonspear merged (DlcMerger 2.1) and BG2:EE 2.7.3.0 | EE Fixpack Beta 2 (0, 2) on both games, EET 14.0 core, EEex v1.3.1 (0, 1, 8); no EET_end |

Lab B is the variation test: EE Fixpack already changes several of these spells (it
adds an undead/golem immunity to Stinking Cloud, removes Web's extra hold effect, gives
Glyph of Warding more level steps), and those changes had to survive.

Each lab: install (WeiDU 249, `--force-install-list 0`), run `tests/check_install.py`,
uninstall and compare every override file byte for byte with the state before, install
again and check again.

## Results

- Both labs: `SUCCESSFULLY INSTALLED`, no warnings, after the first and after the second
  install; the checks passed both times (40 of 40), and 49 of 49 with the final checker,
  which also checks every changed description.
- Uninstall restored the override folder byte for byte: lab A 25 files, lab B 19,328
  files.
- Offline tests (`tests/run_tests.py`, WeiDU 249, made-up games): 11 of 11 passed.

WeiDU.log, lab A:

```
~EEEX/EEEX.TP2~ #0 #0 // Quick Menu Core: v1.3.1
~EEEX/EEEX.TP2~ #0 #1 // EEex: v1.3.1
~EEEX/EEEX.TP2~ #0 #8 // Experimental - Use LuaJIT: Can help stuttering | WARNING: May cause crashes when combined with certain mods: v1.3.1
~SETUP-CHRIZ-BG-MAGIC.TP2~ #0 #0 // Chriz BG Magic: v0.1.0-dev
```

WeiDU.log, lab B:

```
~EEFIXPACK/SETUP-EEFIXPACK.TP2~ #0 #0 // Core Fixes: Beta 2
~EEFIXPACK/SETUP-EEFIXPACK.TP2~ #0 #2 // Game Text Update: Beta 2
~EET/EET.TP2~ #0 #0 // EET core (resource importation): v14.0
~EEEX/EEEX.TP2~ #0 #0 // Quick Menu Core: v1.3.1
~EEEX/EEEX.TP2~ #0 #1 // EEex: v1.3.1
~EEEX/EEEX.TP2~ #0 #8 // Experimental - Use LuaJIT: Can help stuttering | WARNING: May cause crashes when combined with certain mods: v1.3.1
~SETUP-CHRIZ-BG-MAGIC.TP2~ #0 #0 // Chriz BG Magic: v0.1.0-dev
```

Install log, lab B (lab A prints the same, except Web: 4 effects of the same roll,
because EE Fixpack removed one, and Glyph of Warding: 14 damage effects):

```
chriz-bg-magic: Spirit Armor (SPWI414): a new casting replaces the old one in 1 abilities; 0 did so already.
chriz-bg-magic: Minor Spell Deflection (SPWI318): stops spell levels 1-4 only; 48 higher-level deflection effects removed, 64 kept.
chriz-bg-magic: Minor Spell Deflection (SPWI318): description 1, scrolls updated 1 of [SCRL6G].
chriz-bg-magic: Save vs. Breath: WIZARD_FIREBALL (SPWI304): 6 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: WIZARD_FIREBALL (SPWI304): description 0, scrolls updated 0 of [SCRL1G SCRL5Z].
chriz-bg-magic: Save vs. Breath: WIZARD_DELAYED_BLAST_FIREBALL (SPWI712): 1 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: WIZARD_DELAYED_BLAST_FIREBALL (SPWI712): description 1, scrolls updated 1 of [SCRL8N].
chriz-bg-magic: Save vs. Breath: WIZARD_SUN_FIRE (SPWI523): 7 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: WIZARD_SUN_FIRE (SPWI523): description 0, scrolls updated 0 of [SCRLAL SCRLAR].
chriz-bg-magic: Save vs. Breath: WIZARD_CONE_OF_COLD (SPWI503): 12 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: WIZARD_CONE_OF_COLD (SPWI503): description 0, scrolls updated 0 of [SCRL2F].
chriz-bg-magic: Save vs. Breath: CLERIC_FLAME_STRIKE (SPPR503): 12 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: CLERIC_FLAME_STRIKE (SPPR503): description 1, scrolls updated 1 of [SCRL62].
chriz-bg-magic: Save vs. Breath: WIZARD_SKULL_TRAP (SPWI313): 16 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: WIZARD_SKULL_TRAP (SPWI313): description 1, scrolls updated 1 of [SCRL1P].
chriz-bg-magic: Save vs. Breath: CLERIC_GLYPH_OF_WARDING (SPPR304): 16 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: CLERIC_GLYPH_OF_WARDING (SPPR304): description 1, scrolls updated 0 of [].
chriz-bg-magic: Save vs. Breath: WIZARD_INCENDIARY_CLOUD (SPWI810): 5 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: WIZARD_INCENDIARY_CLOUD (SPWI810): description 1, scrolls updated 1 of [SCRL9E].
chriz-bg-magic: Save vs. Breath: WIZARD_LIGHTNING_BOLT (SPWI308): 6 damage effects now save vs. breath (0 effects of the same roll with them).
chriz-bg-magic: WIZARD_LIGHTNING_BOLT (SPWI308): description 1, scrolls updated 1 of [SCRL1K].
chriz-bg-magic: Damage wakes sleepers: WIZARD_SLEEP (SPWI116): 20 sleep effects now end on damage; 0 did already.
chriz-bg-magic: Damage wakes sleepers: WIZARD_COLOR_SPRAY (SPWI105): 1 sleep effects now end on damage; 0 did already.
chriz-bg-magic: Damage wakes sleepers: WIZARD_STINKING_CLOUD (SPWI213): 1 sleep effects now end on damage; 0 did already.
chriz-bg-magic: Damage wakes sleepers: WIZARD_POWER_WORD_SLEEP (SPWI220): its 1 sleep effects end on damage already.
chriz-bg-magic: Web (SPWI215): 1 web effects now save vs. breath (3 effects of the same roll with them); 0 did already.
chriz-bg-magic: Web (SPWI215): race SPIDER (116) immune in 1 abilities; 0 were already.
chriz-bg-magic: Web (SPWI215): race SLIME (119) immune in 1 abilities; 0 were already.
chriz-bg-magic: Web (SPWI215): description 1, scrolls updated 1 of [SCRL99].
```

Check report, lab B (lab A gives the same lines, with its own effect counts):

```
ok   WeiDU.log lists chriz-bg-magic #0
ok   Spirit Armor SPWI414: refresh first, rest unchanged (11 effects)
ok   Minor Spell Deflection SPWI318 ability 0 (min level 1): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 1 (min level 6): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 2 (min level 7): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 3 (min level 8): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 4 (min level 9): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 5 (min level 10): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 6 (min level 11): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 7 (min level 12): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 8 (min level 13): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 9 (min level 14): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 10 (min level 15): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 11 (min level 16): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 12 (min level 17): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 13 (min level 18): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 14 (min level 19): levels [1, 2, 3, 4]
ok   Minor Spell Deflection SPWI318 ability 15 (min level 20): levels [1, 2, 3, 4]
ok   Minor Spell Deflection text says up to 4th-level spells
ok   WIZARD_FIREBALL: damage effects saving vs. breath (SPWI304 6), nothing else changed
ok   WIZARD_FIREBALL text: names no save type, no vs. Spell left
ok   WIZARD_DELAYED_BLAST_FIREBALL: damage effects saving vs. breath (SPWI712 1), nothing else changed
ok   WIZARD_DELAYED_BLAST_FIREBALL text: names vs. Breath, no vs. Spell left
ok   WIZARD_SUN_FIRE: damage effects saving vs. breath (SPWI523 0, SPWI523D 7), nothing else changed
ok   WIZARD_SUN_FIRE text: names no save type, no vs. Spell left
ok   WIZARD_CONE_OF_COLD: damage effects saving vs. breath (SPWI503 12), nothing else changed
ok   WIZARD_CONE_OF_COLD text: names no save type, no vs. Spell left
ok   CLERIC_FLAME_STRIKE: damage effects saving vs. breath (SPPR503 12), nothing else changed
ok   CLERIC_FLAME_STRIKE text: names vs. Breath, no vs. Spell left
ok   WIZARD_SKULL_TRAP: damage effects saving vs. breath (SPWI313 16), nothing else changed
ok   WIZARD_SKULL_TRAP text: names vs. Breath, no vs. Spell left
ok   CLERIC_GLYPH_OF_WARDING: damage effects saving vs. breath (SPPR304 16), nothing else changed
ok   CLERIC_GLYPH_OF_WARDING text: names vs. Breath, no vs. Spell left
ok   WIZARD_INCENDIARY_CLOUD: damage effects saving vs. breath (SPWI810 5), nothing else changed
ok   WIZARD_INCENDIARY_CLOUD text: names vs. Breath, no vs. Spell left
ok   WIZARD_LIGHTNING_BOLT: damage effects saving vs. breath (SPWI308 6), nothing else changed
ok   WIZARD_LIGHTNING_BOLT text: names vs. Breath, no vs. Spell left
ok   WIZARD_CHAIN_LIGHTNING SPWI615: unchanged
ok   WIZARD_METEOR_SWARM SPWI911: unchanged
ok   CLERIC_FIRE_STORM SPPR705: unchanged
ok   WIZARD_SLEEP SPWI116: 20 sleep effects wake on damage, nothing else changed
ok   WIZARD_COLOR_SPRAY SPWI105: 1 sleep effects wake on damage, nothing else changed
ok   WIZARD_STINKING_CLOUD SPWI213: 1 sleep effects wake on damage, nothing else changed
ok   WIZARD_POWER_WORD_SLEEP SPWI220: 1 sleep effects wake on damage, nothing else changed
ok   CLERIC_COMMAND SPPR102: unchanged (waits for Christopher)
ok   CLERIC_GREATER_COMMAND SPPR512: unchanged (waits for Christopher)
ok   Web SPWI215 ability 0: spiders and slimes immune (SPLPROT row 104)
ok   Web SPWI215 ability 0: the web's roll saves vs. breath (bonus [-2]), nothing else changed
ok   Web text says vs. Breath with a -2 penalty
49 checks passed, 0 failed
```

## Effect changes

Every spell file the install wrote, before and after, dumped with the design chat's
`iedump.py`; the full dumps are in the lab folder (`_logs/dumps`). Lines that changed:

```
## bg2ee SPWI414: 1 lines out, 2 lines in
## bg2ee SPWI318: 64 lines out, 16 lines in
## bg2ee SPWI304: 6 lines out, 6 lines in
## bg2ee SPWI712: 1 lines out, 1 lines in
## bg2ee SPWI523D: 7 lines out, 7 lines in
## bg2ee SPWI503: 12 lines out, 12 lines in
## bg2ee SPPR503: 12 lines out, 12 lines in
## bg2ee SPWI313: 16 lines out, 16 lines in
## bg2ee SPPR304: 14 lines out, 14 lines in
## bg2ee SPWI810: 5 lines out, 5 lines in
## bg2ee SPWI308: 6 lines out, 6 lines in
## bg2ee SPWI116: 20 lines out, 20 lines in
## bg2ee SPWI105: 1 lines out, 1 lines in
## bg2ee SPWI213: 1 lines out, 1 lines in
## bg2ee SPWI215: 6 lines out, 8 lines in
## eet SPWI414: 1 lines out, 2 lines in
## eet SPWI318: 64 lines out, 16 lines in
## eet SPWI304: 6 lines out, 6 lines in
## eet SPWI712: 1 lines out, 1 lines in
## eet SPWI523D: 7 lines out, 7 lines in
## eet SPWI503: 12 lines out, 12 lines in
## eet SPPR503: 12 lines out, 12 lines in
## eet SPWI313: 16 lines out, 16 lines in
## eet SPPR304: 16 lines out, 16 lines in
## eet SPWI810: 5 lines out, 5 lines in
## eet SPWI308: 6 lines out, 6 lines in
## eet SPWI116: 20 lines out, 20 lines in
## eet SPWI105: 1 lines out, 1 lines in
## eet SPWI213: 1 lines out, 1 lines in
## eet SPWI215: 5 lines out, 7 lines in
```

Example, Spirit Armor (lab A):

```
- -- ability 0: minlvl=1 target=1 tcount=0 range=1 cast=3 projectile=1 form=1 nfx=11
+ -- ability 0: minlvl=1 target=1 tcount=0 range=1 cast=3 projectile=1 form=1 nfx=12
+    op321 remove effects by resource   t=2 pw=4 p1=0 p2=0 tm=1 dur=0 res=SPWI414 disp=3
```

## Not covered

- Play: whether the engine does what the data says (a second Spirit Armor really clears
  the first one's expiry damage, sleepers wake on a hit, spiders walk through Web, the
  rolled save is vs. breath). That needs a game launch: Christopher's checklist
  `docs/checklists/2026-11-04-first-five-fixes.md`, or a quiet lab run with his OK.
- Spell Revisions installs: the installer refuses for now (his decision pending).
- Other mods than EE Fixpack (SCS, Tweaks Anthology, ...), and BG2:EE 2.6.6.0.
- Description updates in other languages than English.
