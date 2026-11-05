# Second round of checks, 2026-11-06

Christopher answered the open questions on 2026-11-06. Changed since
[the first round](2026-11-04-install-checks.md):

- With Spell Revisions installed the installer warns that the two do not go together, and
  carries on (it refused before). The README says so too.
- Damage now also wakes sleepers of Command, Greater Command and Emotion: Hopelessness.
- Web also spares the very obvious flying, incorporeal and very large creatures, by race:
  WYVERN, BEHOLDER, MEPHIT; SPECTRE, WRAITH, SHADOW, MIST; DRAGON, GIANT, ETTIN.
- Meteor Swarm and Fire Storm stay without a save, and Web keeps its -2, for now.

Same two labs as before (BG2:EE 2.7.3.0 + EEex v1.3.1; EET 14 with EE Fixpack), same steps:
uninstall the old version, install, check, uninstall and compare, install, check.

## Results

- Offline tests (`tests/run_tests.py`, WeiDU 249, made-up games): 12 of 12 passed.
- Both labs: `SUCCESSFULLY INSTALLED`, no warnings, after both installs.
- Uninstall restored the override folder byte for byte: lab A 25 files, lab B 19,328 files.
- `tests/check_install.py`: 50 of 50 in both labs. In lab B it first reported 49 of 50: EE
  Fixpack moves Emotion: Hopelessness' sleep into a spell of its own, `SPWI411B`. The
  installer had followed it and changed all 14 sleep effects there; the checker had not
  looked. It follows such spells now, and an offline test covers this layout.

## In-game checks (lab A)

Driven as before (`tests/lab/run_probe.py`, hidden and muted lab game, EEex Remote Console
v0.2.0, the BuffBot lab's test party and arena, staged for the run and removed afterwards).
Two game runs of the final code: all groups but Fireball, then Fireball alone. All 13 checks
passed; the guards stayed clean (no sound, no pointer capture, nothing left running).

| Check | Result |
|---|---|
| Spirit Armor cast twice on the cleric | save vs. spell 9 → 6 → 6; one save bonus and one waiting expiry cast |
| Minor Spell Deflection, then Flame Strike (level 5) at the mage | gets through: hit points 112 → 86, pool unchanged (4) |
| Minor Spell Deflection, then Melf's Acid Arrow (level 2) | absorbed: hit points 112 → 112, pool 4 → 2 |
| Sleep, Power Word: Sleep, Command, Greater Command, Emotion: Hopelessness cast at a held huge spider, then a 1-point hit | each: asleep (state 0x21), awake after the hit (0x20); the sleep effect has wake-on-damage on |
| Color Spray and Stinking Cloud applied to the spider, then a 1-point hit | the same (why they are applied: see the first round) |
| Web cast at a green slime, a gauth, a greater wraith and a fire giant, all with the worst saves (20) | none caught: the effect log shows the spell reaching each of them, the race immunities first, and no Web effect stays |
| The same Web at a tasloi (spell save 1, breath save 20) | caught, all three Web effects with save type 2 (Breath) |
| The same Web at a giant spider (worst saves) | not caught, but that is the base game's `ANTIWEB` |
| Web applied to the giant spider without its projectile | not caught: the spell arrives, the race immunities first, and no Web effect stays |
| Fireball by the level-18 mage at a party member | breath save 1, spell save 20: 15 and 15 damage; breath save 20, spell save 1: 28 and 33 (full); save type 0x1000002 (Breath, bypass Mirror Image) |

After waking from Emotion: Hopelessness only the sleep is gone; the spell's portrait icon,
its special state and its delayed sound stay until they run out, as in the base game.

The creatures in the Web check are ones nothing else protects: no item or effect of theirs
stops Web. How much the race immunities add, by BG2:EE's creature files (immune before =
an item with an immunity to Web's effect, its spell or its projectile):

| Race | Creature files | Immune before |
|---|---|---|
| DRAGON | 25 | 24 |
| WYVERN | 16 | 10 |
| BEHOLDER | 34 | 13 |
| MIST | 18 | 2 |
| SPECTRE | 26 | 1 |
| MEPHIT | 39 | 0 |
| WRAITH | 15 | 0 |
| SHADOW | 31 | 0 |
| GIANT | 17 | 0 |
| ETTIN | 5 | 0 |

## Not covered

- In play: everything the first round names, and the other races of the Web list (the
  mechanism and the row are the same; the checker confirms each race on every ability).
- Emotion: Hopelessness with EE Fixpack in play (lab B was install-checked only).
- A real Spell Revisions install: the warning is tested on made-up games with its marker
  file. By decision no work goes into that combination.
- Trap and monster copies of the changed spells keep the old behaviour.
