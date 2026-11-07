# chriz-bg-magic

Christopher's own WeiDU spell mod for BG2:EE and EET, the successor to the frozen Spell
Revisions fork that Chriz Easy BG installs today (`chriz-bg-collection`).

## Design is Christopher's

- Only what he picked changes. Everything else stays vanilla, plus bug and logic fixes
  ("throw out, add back gradually"). Build exactly the decided text: no extra mechanics,
  values, fixes or "improvements". When game data shows a decision cannot work as written,
  show him what you found and ask.
- His decisions live on his private decision page (db collection `entscheidungen`); the
  design chat owns the page. Never write to it. `docs/build-list.json` is the exported list:
  regenerate it with `python -I tools/build_list.py <snapshot folder>`. His raw notes stay
  out of this repo; specs here are English summaries of the decided text.
- Spell Revisions, SCS and IWDification serve only as comparison. Build everything
  ourselves; never copy their code or files.

## Engineering rules

- Target BG2:EE and EET 2.7.3.0. EEex (v1.3.1) is a requirement only for changes that need
  it. Follow the `bg-modding` skill and its modding policy.
- We overwrite. A spell we change becomes what was decided; what stood there before does not
  matter. No checks of old content: not of descriptions, wording, old values, effect counts or
  order. Game data never stops an install, and a decided change is never skipped because the
  old data looks different.
- Code layout: `defs/*.json` define every spell, item and effect the mod changes, whole. To
  change one, edit its definition and run `python tools/build_resources.py`; commit what it
  writes (`chriz-bg-magic/res/`, `lib/cbmagic_resources.tpa`, `languages/english/resources.tra`).
  Fields only the install can know are symbols, see `tools/resformat.py`. `lib/cbmagic_iwd.tpa`
  and what it calls patch IWDification's spells until we build them ourselves.
- Describe every change in `docs/components.md`, in engine-neutral terms.
- We write the complete description of every spell we change (append a new string and repoint
  the resource; never overwrite a shared strref). No search and replace in old sentences.
- Test in made-up game folders (`tests/run_tests.py`) and in disposable labs only, never in
  Christopher's game or a reference install. Game launches go through the quiet lab runner
  and need his OK. No Docker.
- Scripts take paths as arguments. Before every push: no home paths, no private data.
- Merges, tags, releases and any Chriz Easy BG pin need Christopher's OK.
