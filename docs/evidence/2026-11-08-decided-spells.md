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

## Not covered

- Whether druids and shamans find the new spells in their books: that follows from the spell's
  class setting, and no druid or shaman was in the lab party.
- Rangers get Icelance too: they share the class setting with druids.
- The stack run covers BG1's early levels only, and not the later commit.
- The 15 % of the contest comes from the game's own script and was seen once, not measured.
