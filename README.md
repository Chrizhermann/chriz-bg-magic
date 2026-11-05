# Chriz BG Magic

Christopher Hermann's own spell mod for **Baldur's Gate II: Enhanced Edition** and the
**Enhanced Edition Trilogy (EET)**. The rule is simple: only the changes Christopher picks
are made, everything else stays as in the base game, and real bugs and logic errors get
fixed.

**Status:** early work. The installer frame and the list of decided changes are here; the
first fixes are in review. Nothing is released yet.

- Target: BG2:EE and EET 2.7.3.0. Where a change needs EEex, it asks for EEex v1.3.1.
- What each change does, in plain terms: [docs/components.md](docs/components.md).
- Every decided change and its build status: [docs/build-list.json](docs/build-list.json).

## Install

There is no release yet. Once there is, extract the release zip into the game folder and
run `setup-chriz-bg-magic` with WeiDU.

**Do not install Chriz BG Magic together with Spell Revisions.** It replaces Spell
Revisions, the two are not compatible, and the installer warns if it finds Spell
Revisions.

## Tests

`python tests/run_tests.py --weidu <path to weidu.exe>` runs the installer against small
made-up game folders. No game files are needed.

## Credits

Some ideas were inspired by [Spell Revisions](https://github.com/Gibberlings3/SpellRevisions)
by Demivrgvs and the Gibberlings Three team. Chriz BG Magic is an independent mod with no
connection to Spell Revisions or its authors: we liked a few of its ideas, and copy nothing
of substance.

## License

MIT, see [LICENSE](LICENSE).
