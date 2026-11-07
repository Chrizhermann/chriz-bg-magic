# Chriz BG Magic

Christopher Hermann's own spell mod for **Baldur's Gate II: Enhanced Edition** and the
**Enhanced Edition Trilogy (EET)**. The rule is simple: only the changes Christopher picks
are made, everything else stays as in the base game, and real bugs and logic errors get
fixed.

**Status:** early work. Nothing is released yet.

- Target: BG2:EE and EET 2.7.3.0. Where a change needs EEex, it asks for EEex v1.3.1.
- What each change does, in plain terms: [docs/components.md](docs/components.md).
- Every decided change and its build status: [docs/build-list.json](docs/build-list.json).

## Install

There is no release yet. Once there is, extract the release zip into the game folder and
run `setup-chriz-bg-magic` with WeiDU.

**Do not install Chriz BG Magic together with Spell Revisions.** It replaces Spell
Revisions, the two are not compatible, and the installer warns if it finds Spell
Revisions.

## Spell bonus types

Selected spell bonuses have a type: Morale, Favor, Luck, Dodge, Deflection or Curse.
For each statistic, one type contributes its strongest bonus and its strongest penalty.
Different types combine, and untyped equipment and other effects still contribute.
A weaker spell resumes contributing when a stronger one expires. Casting the same spell
again refreshes it. Transformation and Regeneration each allow only one member: a higher
spell level wins, and a newer casting wins a tie.

Comparing bonus types requires EEex v1.3.1. Without EEex, bonuses from different spells
accumulate normally; self-refresh and the two exclusive families still work. Pierce Magic
uses its new resistance reduction only when EEex is present at installation. Reinstall
this component after adding or removing EEex. Hit-point bonuses are not compared by type in
this build. Righteous Wrath of the Faithful, Haste and Improved Haste can all run on one
creature; with EEex only one extra attack counts.

The mod overwrites what it changes: its spells and items replace what stands in the game,
whatever another mod or a player did to them. Install it after anything whose version of these
spells you do not want to keep.

## Tests

`python tests/run_tests.py --weidu <path to weidu.exe>` runs the installer against small
made-up game folders. No game files are needed. The Lua runtime tests require the Python
package `lupa`, including its `lua53` and `luajit21` modules.

## Credits

Some ideas were inspired by [Spell Revisions](https://github.com/Gibberlings3/SpellRevisions)
by Demivrgvs and the Gibberlings Three team. Chriz BG Magic is an independent mod with no
connection to Spell Revisions or its authors: we liked a few of its ideas, and copy nothing
of substance.

## License

MIT, see [LICENSE](LICENSE).
