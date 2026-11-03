# Components

What each part of Chriz BG Magic changes, in engine-neutral terms, so the same rules can
move to the Chriz script engine later. Values not named here stay as in the base game.

## Layout

One component for now, `0` (label `chriz-bg-magic-main`). It calls one function per
decided change; each function lives in `chriz-bg-magic/lib/` and can move to a component
of its own without changes. The user-facing layout is Christopher's decision.

## Spell Revisions installed

Chriz BG Magic replaces Spell Revisions. What the installer does when Spell Revisions is
installed (refuse, warn, or install anyway) is Christopher's call; until he has decided,
it refuses (`cbmagic_sr_policy` in `lib/cbmagic_shared.tpa`).
