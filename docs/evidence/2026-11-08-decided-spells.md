# Decided spells, first two blocks: checks, 2026-11-08

Command, Chaos, Sphere of Chaos, druid Conjure Air Elemental, Icelance, Champion's Strength against
Draw Upon Divine Might, IWD Hopelessness, and the control contest of the eight wizard elementals.

## Checks

- Offline tests (`tests/run_tests.py`, WeiDU 249, made-up games): 39 of 39.
- Clean installs in three labs, without warnings: BG2:EE, EET with EE Fixpack, BG2:EE with
  IWDification's spell packs.
- In-game, group `decided` in `tests/lab/run_batches.py`, 15 of 15 in BG2:EE and in BG2:EE with
  IWDification. Measured: Chaos confuses for 30.3 seconds at caster level 18; Icelance took 11 to
  23 Hit Points, stunned only on a failed save, and stun immunity kept the damage.
- In-game, group `iwdbatch`, BG2:EE with IWDification, 19 of 19: Hopelessness stuns through its own
  area, a hit ends it with its icon, a stun from elsewhere stays. All eight wizard elementals arrive
  on the party's side and end the contest as ally or hostile; one of eight turned hostile in that
  run. Symbol: Hopelessness has the same row and was read back, not cast.
- In-game, plain BG2:EE: every earlier group passed again, 117 of 117; 160 changed spells cast once;
  7 of 7 in the waking checks, Emotion: Hopelessness among them.

- First run on the rest of the stack, commit 52d8558 (before Hopelessness and the elementals): the
  Chriz Easy BG install on EET with SCS and EEex 1.3.1, without Spell Revisions, the script engine on
  top. The install took 30 seconds, without warnings about game data. Ten fights in a hidden EET game,
  five BG1 encounters with engine and SCS at Insane, ran without errors.

## Celestials

- Offline tests: 41 of 41, among them a check that every table of every creature file lies inside
  the file and agrees with the others.
- Clean installs in BG2:EE, in BG2:EE with IWDification and in EET; in all three the game's own
  summon effects now call the mod's creatures.
- In-game, group `celestials` in `tests/lab/run_batches.py`, BG2:EE:
  - All four creatures arrive on the party's side with the numbers of their descriptions: 136 or
    152 Hit Points, AC -5 or -7, 2 or 3 attacks, level 14 or 18, the attributes, saving throws,
    resistances and spell lists given there, gender BOTH.
  - Limit: a second deva leaves and the first stays; a fallen deva and the paladin's Summon Fallen
    Deva leave beside a deva; a planetar comes beside the deva; a dark planetar leaves beside a
    planetar; once the first is gone another comes; with the party AI button off the second still
    leaves; a second deva leaves while the first stands out of sight.
  - Enemy casters are not limited: two devas of an enemy caster stay beside the party's deva.
  - An enemy's devas carry the game's `DEVAGOOD` in the class slot, the party's deva none.
  - A deva casts Bless from its book on order; a planetar regenerated 4 Hit Points in 12 seconds.
- In-game, group `celweapons`, BG2:EE, hits on a foe that cannot die: deva 11 to 20 (1d10+10),
  planetar 13 to 21 (2d6+10), fallen deva 13 to 26 plus its bleeding in single Hit Points.
- Both groups again in BG2:EE with IWDification: 39 of 39.

## Lesser Restoration

- Offline: without EEex the game's spell stays; with EEex it calls `CBMLRES`, and Blood Rage's file
  is named in the module.
- In-game, group `restoration`, BG2:EE with IWDification: on one character Ray of Enfeeblement,
  a mind flayer's hit, Energy Drain, a disease and Blood Rage's weakness, then Lesser Restoration:
  Strength 5 to 10, Intelligence 13 to 18, Dexterity 8 to 10 and Constitution back but for the
  disease's 2; Ray of Enfeeblement's icon went with it; Energy Drain's save penalty and icon, the
  disease and Blood Rage's weakness stayed. The same in plain BG2:EE, without Blood Rage.
- The drains were put on as the spell or weapon leaves them, from a hostile creature; a real Ray
  of Enfeeblement or mind flayer fight was not run.

## Simulacrum

- Offline: the clone helper calls `CBMSIMU`, quick-slot items are blocked, special abilities open;
  without EEex the game's Simulacrum text stays.
- In-game, group `simulacrum`, BG2:EE: a spawned Korgan at level 12 (Berserker) with Berserker
  Rage three times, as his levels give it, plus one ability of a quest and two of an item. His
  copy came out at level 8 with Berserker Rage twice, as levels 1 and 5 give it, and without the
  quest and item abilities; Korgan kept everything. After two rages Korgan had two uses left and
  his copy one.
- Not run: high-level abilities, multi-class and dual-class casters, a party member as caster.

## Strength floors

- Before building, a probe in the BG2:EE lab: Korgan without his gear punched for 1 or 2 with
  Strength 14; with 18/00 written into his derived stats by a listener, for 7 or 8. A Strength
  written that way counts in a fight. An opcode 44 with the resource `CBTSTRF` kept its tag and
  special field on the effect list.
- Offline: the four floor spells carry the marker and the spell state and set no Strength; their
  versions without EEex set it and are otherwise the same spells; installs without and with EEex,
  IWDification's Animal Rage in its own slot, a second install that changes nothing; the listener
  under Lua 5.3 and LuaJIT with mocked engines (37 checks each: floors, bonuses in both orders,
  Draw Upon Divine Might once, caps, forms, waiting effects, EFF wrappers, passes, errors).
- In-game, groups `strength` and `floor`, BG2:EE 13 of 13 and BG2:EE with IWDification 15 of 15:
  Strength of One 10 to 18/75, 19 and 18/90 kept; Divine Power 10 to 18/00, 19 kept; Champion's
  Strength 12 to 18/00, 20 kept; Strength 10 to 18/50, 18/30 to 18/80, 19 kept; Animal Rage 10
  to 19, 22 kept; after the spells end the game's own value returns; Draw Upon Divine Might on
  top of Divine Power gave the same Strength in both orders; in a fight Korgan under Divine
  Power hit for 7 or 8, and for 11 or 12 while his own Barbarian Rage (+4) ran: 22 on top of the
  floor.
- Seen on the way: a Strength bonus that stands before a set Strength on the effect list still
  counts on top of it (+4, then a set to 10: 14).
- Not run: a creature in another form (only mocked), Ray of Enfeeblement in a fight, the
  versions without EEex in a game (offline only), EET.

## Polymorph Self

- Source of the values: a disposable lab, BG2:EE 2.7.3.0 with EEex and only SCS 35.21's spell
  tweaks, read file by file; an EET lab with more mods had other mods' changes in SCS's forms, so
  it was not used. Strings below 103599 are the game's own (the unmodded game's string table).
- One slip in SCS's data: the spider's -4 against missiles was written as 65532 (the game also
  takes it as -4), so -4 is written.
- Offline: the spell's 20 abilities (forms for 60 + 18 per level seconds, the natural form one
  second longer), the menu, every form's weapon, look, Strength, Dexterity, attacks and base Armor
  Class, the powers and the remover, the breath's 3 rounds; nothing of SCS is named.
- In-game, group `polymorph`, BG2:EE 13 of 13, a spawned Korgan without gear or scripts: the spell
  gives the natural form and six forms; each form had its look, Strength, Dexterity, weapon and
  only its own power; the mustard jelly had Magic Resistance 125, the hell hound fire 100 and cold
  -50; Fiery Breath came back after 3 rounds; the natural form gave back his look and body and
  removed the powers; the rat kept Strength 10 under Divine Power; when the spell ran out he was
  in his natural form without forms or powers. Appearance-only forms do not set the game's
  polymorph flag: the Strength floor looks for opcode 135 instead.
- Not run: the form menu with a party member, the look on screen, Barbarian Rage, Web Tangle,
  Hide and the jelly's slow in a fight, the spider's Armor Class against missiles (its stat read
  0), EET.
- Hill giant look, later the same day: SCS gives the form Icewind Dale's verbeeg art under the
  animation slot `0xE293`, art the base game lacks. This mod now ships that art itself, taken from
  Icewind Dale: Enhanced Edition (`E293.INI`, 24 `MGVE*.BAM`, the 8 `VERBEE*.WAV` it names), with the
  selection circle and walk sound of SCS's form. Offline 48 of 48; in-game group `polymorph` again
  13 of 13 in BG2:EE, the hill giant form showing animation `0xE293`.

## Shapechange

- Same source as Polymorph Self. Two slips in SCS's data: the stalker's base Armor Class -3 was
  written as 65533, so -3 is written; one of the iron golem's three weapon immunities has its two
  values swapped against the game's own `IMMUNE3.ITM` (opcode 120 type 1, "magical", beside type 2,
  "non-magical"), so the golem gets the game's iron golem immunity: non-magical, +1 and +2.
- Offline: one ability of 6 turns, the natural form one second longer, the menu, every form's
  weapon, look, Strength, Dexterity, attacks, base Armor Class and THAC0, the powers in the shared
  remover, the stalker's invisibility removed with the form, the golem's three immunities.
- In-game, group `shapechange`, BG2:EE 13 of 13, the same Korgan: the spell gives the natural form
  and six forms; each form had its look, Strength, weapon and own power; the mind flayer had Magic
  Resistance 90, the iron golem 100 and fire 125, the marilith 85 and fire 100; the stalker was
  invisible; the natural form gave back his look and ended the invisibility. The giant troll
  healed 5 Hit Points at a time, every 2 to 3 seconds (about 1.9 a second over 24 seconds), not
  every second as the effect says: periodic effects pulse on the creature's own one-second grid,
  which each heal reseeds (`ie-duration.md` in the bg-modding skill). The texts say "about 2 a
  second" and give no rate per second for poison, which was not measured.
- Polymorph Self ran again in the same game: 13 of 13.
- Not run: the form menu with a party member, the look on screen, the powers in a fight (Psionic
  Blast, Gas Cloud, Teleport, Petrifying Gaze), the golem's weapon immunity in a fight, EET.

## The main character as a statue or imprisoned (first part)

- Engine facts from a lab console session (BG2:EE 2.7.3.0, EEex v1.3.1), before the build:
  - EEex's opcode 403 sees an effect before the engine rolls its save and before opcode
    immunity: Flesh to Stone (`SPWI604`, opcode 134, save vs. spell) applied 12 times to a main
    character with spell save 1 reached the screen 12 times; with opcode 101 against 134 on him,
    6 of 6 still did. So the screen blocks the effect and casts the state through opcode 146 with
    the old save; opcode immunity is checked by the screen.
  - Such a cast from inside the screen keeps the save: with spell save 1, 0 of 8 landed; with
    spell save 20, all landed; no error.
  - The two gather-check patterns match once each in `Baldur.exe` 2.7.3.0 of BG2:EE (also EET's)
    and BG:EE, and the bytes at the static addresses read the same in the running game.
- Offline: the five spells (statue, prison, net, cure, release), installs without EEex (nothing
  installed, scripts untouched) and with EEex (module with its four states from `SPLSTATE.IDS`,
  pattern file beside EEex's, the tick on top of each campaign world script from an EET-style
  `CAMPAIGN.2DA` and, for BG2:EE's heading-only table, on `BALDUR` and `BALDUR25`; the dream guard on
  `PLAYER1D` and the companions' dream scripts from `PDIALOG.2DA`; the Solar's `PartyRested()` block
  in `AR4000` with the extra condition), a second install changes nothing; the cure list from a
  made-up game (another mod's spell, a wand and a ring that cast it, a Freedom, a broken item
  file); 91 runtime checks of the Lua under mocks in Lua 5.3 and LuaJIT (screen, saves and immunity,
  the prison read from the effect list, Freedom here and elsewhere, companions' return, the tick's
  game over, cutscene, pull-along, the hooks' bytes, label and cell, cures, dead ends, the clock).
- Installed into the BG2:EE lab folder with WeiDU only (no game started): the world scripts
  `BALDUR` and `BALDUR25` carry the tick, the dream scripts and `AR4000` their guards.
- In-game, 2026-11-10, a console session on the BG2:EE lab (2.7.3.0, EEex v1.3.1), party of
  three, in the BuffBot arena and in `AR0330`/`AR0331` (two rooms without area scripts, joined by
  party-required exits). The exits were used the way a click does it: the engine's action 93 with
  the travel region's object in the action's integer parameter. What the first runs found and what
  changed:
  - An imprisoned creature's spell states read unset (all, also older ones), and a bit written
    into either of its stat blocks was gone 3 seconds later. The prison is now read from the effect
    list, the hooks compare against a cell, scripts read a global.
  - The maze brings a delayed Freedom (opcode 212) of its own when it is applied; the screen takes
    only an undelayed one for a cast Freedom.
  - A Freedom cast in another area freed the prisoner without the opcode reaching his screen: the
    tick now closes the prison again away from the stored place.
  - `ClearActions(Myself)` queued in front of `JumpToPoint` takes the jump with it.
  - A bare `je jmp_success` in the hook assembled to a jump to the next instruction (seen in the
    dumped hook bytes); `#L(jmp_success)` gives the real target.
  - Joining the party again puts `DPLAYER2` into the party AI slot; the companion's own script is
    now put back over it.
- Seen with the final code:
  - Flesh to Stone (spell save made to fail): statue, held, no game over, cell and global set;
    Stone to Flesh: cured, both cleared. With opcode 101 against 134 on him: no statue.
  - Imprisonment: prison with the place stored; a cutscene woke him and the tick imprisoned him
    again once; Freedom there: free, the prison's effects gone, on his spot.
  - Exit `AR0330` to `AR0331` and back with the statue: the whole party arrived, the statue with
    it, still a statue. Counter-test with the tick stopped and the cell emptied: nobody moved.
  - The same exits with the prisoner: he arrived with the party, imprisoned. Freedom in the other
    room: still imprisoned (a fresh maze in his list). Back in the first room: Freedom freed him.
  - A script moved the two others to the other room (`LeaveAreaLUA`): the statue followed.
  - A companion petrified by the game left the party (script slot emptied, `KickedOut` set);
    Stone to Flesh: back in the party with its own script.
  - Both others put into a maze while he was a statue: the tick answered "game over" once; game
    time stopped 43 ticks later and no script ran again.
- Dead ends, same day:
  - The list of dead ends comes from a read of the game's data (areas, scripts, world map) of
    BG2:EE 2.7.3.0 and an EET install: only places with proof are in, 9 situations; 13 more are
    likely but one step is concluded, not read, and are left out.
  - The cure list of the lab install: Stone to Flesh from `SPWI625`, `SPPR713`, `BDREJUVE`, the
    items `SCRLPET`, `SCRL8C`, `RING29`, `STAF16`, `SW1H71`; Freedom from `SPWI917`, `OHBFREE`,
    `SCRL9Z`.
  - In the lab game: no cure with nothing; a Stone to Flesh scroll with a companion counted; a
    Freedom scroll with the main character himself did not; a companion with Stone to Flesh in
    his book counted while the area allowed resting and no longer with the area's no-rest flag.
  - With the arena made a dead end for the test (no rest, statue, no scroll): the stuck flag came
    on, the clock ran to 456 ticks in 58 script passes and the game-over answer came 452 ticks
    after the start.
  - A false trigger in front stops a block before its Lua trigger is evaluated (seen with a
    condition evaluated from the console), which is what keeps the clock still in combat. A real
    fight during the clock was not staged: the creatures spawned did not fight.
  - Not seen: a scroll inside a bag, a real dead end of the game, the clock across a save.
- One lab game crashed on a probe of mine (a string read from a guessed address), not on the mod.
- Not seen yet: the world map and map edges (the other hook), ambushes, the Pocket Plane's exit,
  dreams at a rest, the statue hit in a fight, EET with its other campaigns, a save and reload
  while he is out, the look on screen.

## Touch spells (2026-11-10)

- Open since the healing changes: in the arena an ordered attack with a touch spell had never
  landed. Now a spawned Korgan without gear or scripts casts on himself and strikes a held target
  with Hit Points to spare (group `touch`, BG2:EE lab, 12 of 12):
  - Each spell gave its touch weapon (`CBHT40`, `CRITICAL`, `CBHT70`), and the first hit used it up.
  - A huge spider lost 25 to Cause Serious Wounds (3d8 + 7) and 34 to Cause Critical Wounds
    (4d8 + 12); Harm left it 1 Hit Point.
  - A zombie, hurt first, gained 26 from Cause Serious Wounds and 30 from Cause Critical Wounds;
    Harm healed it completely.
- Not run: a saving throw against the touch, Cause Light, Moderate and Medium Wounds (cast at a
  distance, covered by the earlier batches), IWDification's variants, EET.
- The lab group `floor` had dropped out of `tests/lab/run_batches.py` with the Polymorph Self
  commit (the list still named it); it is back and ran 10 of 10.

## Numbers and texts (2026-11-10)

No game was started for these; files were read after an install into the BG2:EE lab folder
(2.7.3.0, EEex v1.3.1, no EE Fixpack), and the offline suite ran 53 of 53.

- Numbers: every definition was compared with the base game's tables (PROJECTL.IDS, MSECTYPE,
  SPLPROT, STATDESC, SPLSTATE.IDS and the creature id files). Found and fixed: the immunity
  states, Grease's areas, two record icons and one secondary type. After the install each Grease
  level points at its own area (`cbmgr01` to `cbmgr20`) with level + 3 triggers, Unholy Blight
  shows icon 35, and the Sleep spell tests the state the installer numbered for
  `SLEEP_IMMUNITY`.
- Texts: the 23 new descriptions and the eight completed ones are in the game's strings, and the
  game's own scrolls of Fireball, Haste, Breach and Tenser's Transformation point at the same
  string as their spell.
- Left as they are: Dispel Magic and Remove Magic destroy a creature with `SPECIFIC = 25`. Only
  EE Fixpack gives that value to the summoned Nishruu and Hakeashar, so without it the effect
  does nothing. Files of Baldur's Gate and Siege of Dragonspear (`BD*`, some items) are written
  on plain BG2:EE as well, where nothing uses them; their names are EET string numbers.
- Not seen in a game: Grease's duration by level, the icons, the texts on screen.

## Not covered

- Whether druids and shamans find the new spells in their books: that follows from the spell's
  class setting, and no druid or shaman was in the lab party.
- Rangers get Icelance too: they share the class setting with druids.
- The stack run covers BG1's early levels only, and not the later commit.
- The 15 % of the contest comes from the game's own script and was seen once, not measured.
- The celestials' look was not seen: a lab game runs hidden and draws no picture. Animation,
  colors and items are in the files and were read back, not looked at.
