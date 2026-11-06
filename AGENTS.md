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
  it. Follow the `bg-modding` skill and its compatibility policy: patch the intended
  behaviour by meaning, preserve unrelated data and other mods' changes, keep only checks
  with a concrete reason, and say plainly when something is skipped or unclear.
- Code layout: `chriz-bg-magic/lib/cbmagic_shared.tpa` holds the shared helpers, and every
  decided change is one action function, so the component layout can change without
  touching the fixes. Resolve spells through `SPELL.IDS` symbols, not hard-coded resrefs.
- Describe every change in `docs/components.md`, in engine-neutral terms.
- When a change makes a description false, fix the owned sentence (append a new string and
  repoint the resource; never overwrite a shared strref) and log where it could not.
- Test in made-up game folders (`tests/run_tests.py`) and in disposable labs only, never in
  Christopher's game or a reference install. Game launches go through the quiet lab runner
  and need his OK. No Docker.
- Scripts take paths as arguments. Before every push: no home paths, no private data.
- Merges, tags, releases and any Chriz Easy BG pin need Christopher's OK.
