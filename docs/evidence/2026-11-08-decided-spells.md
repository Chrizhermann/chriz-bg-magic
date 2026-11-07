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

## Not covered

- Whether druids and shamans find the new spells in their books: that follows from the spell's
  class setting, and no druid or shaman was in the lab party.
- Rangers get Icelance too: they share the class setting with druids.
- The stack run covers BG1's early levels only, and not the later commit.
- The 15 % of the contest comes from the game's own script and was seen once, not measured.
- The celestials' look was not seen: a lab game runs hidden and draws no picture. Animation,
  colors and items are in the files and were read back, not looked at.
