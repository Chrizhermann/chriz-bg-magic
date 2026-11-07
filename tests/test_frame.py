"""Tests of the installer frame: games, the Spell Revisions policy, spell lookup, the SPLPROT rows,
and Emotion: Hopelessness, the one base-game spell still patched at install."""
import fakegame as fg
import fixtures as fx
import ie
from harness import check, probe, test


@test
def installs_and_uninstalls_on_bg2ee_and_eet(work, weidu):
    """The main component installs on BG2:EE and EET and its uninstall leaves the game as it was."""
    for game in ("bg2ee", "eet"):
        g = fg.FakeGame(work / game[:2], weidu, game=game, tlk=fx.tlk(), biff=fx.game())
        before = g.tree()
        out = g.install()
        check("SUCCESSFULLY INSTALLED" in out, f"{game}: install failed:\n{out}")
        out = g.uninstall()
        check("SUCCESSFULLY REMOVED" in out or "REMOVED" in out, f"{game}: uninstall:\n{out}")
        check(g.tree() == before, f"{game}: uninstall left changes")


@test
def refuses_bgee(work, weidu):
    g = fg.FakeGame(work, weidu, game="bgee")
    out = g.install()
    check(not fg.installed_ok(out), f"installed on BG:EE:\n{out}")
    check("Enhanced Edition Trilogy" in out, "no reason given")


@test
def spell_revisions_warns_and_goes_on(work, weidu):
    """Spell Revisions' marker gives a warning; the install goes through all the same."""
    g = fg.FakeGame(work / "warn", weidu, tlk=fx.tlk(), biff=fx.game(), override={"DVIMHERE.MRK": b"x"})
    out = g.install()
    check(fg.with_warnings(out) and "Do not use Chriz BG Magic together with Spell Revisions" in out, out)
    g = fg.FakeGame(work / "none", weidu, tlk=fx.tlk(), biff=fx.game())
    check("SUCCESSFULLY INSTALLED" in g.install(), "no SR: should install without warnings")


@test
def spell_resref_from_symbol(work, weidu):
    body = r"""
ACTION_FOR_EACH s IN WIZARD_SPIRIT_ARMOR CLERIC_COMMAND TRAP_FIREBALL WIZARD_FIREBALL NO_SUCH_SPELL BEGIN
  LAF cbmagic_spell_resref STR_VAR symbol = EVAL ~%s%~ RET r = resref f = found END
  PRINT ~RESULT %s% %r% %f%~
END
"""
    ids = ie.make_ids([(1102, "CLERIC_COMMAND"), (2414, "WIZARD_SPIRIT_ARMOR"), (2001, "TRAP_FIREBALL"),
                       (2304, "WIZARD_FIREBALL")])
    spl = ie.make_spl(level=1, abilities=[{"effects": []}])
    _, out, res = probe(work, weidu, body, biff={"SPELL.IDS": ids, "SPWI414.SPL": spl, "SPPR102.SPL": spl,
                                                  "SPWI001.SPL": spl})
    check(res == ["WIZARD_SPIRIT_ARMOR SPWI414 1", "CLERIC_COMMAND SPPR102 1", "TRAP_FIREBALL SPWI001 1",
                  "WIZARD_FIREBALL SPWI304 0", "NO_SUCH_SPELL  0"], f"got {res}\n{out}")


@test
def splprot_row_is_found_or_appended(work, weidu):
    """A row the table has is used, also when one side writes hex; a row with stars never matches;
    a missing row goes behind the others and is found the next time."""
    body = r"""
LAF cbmagic_splprot_row INT_VAR stat = 0x10b value = 4 relation = 1 RET a = row END
LAF cbmagic_splprot_row INT_VAR stat = 267 value = 4 relation = 1 RET b = row END
LAF cbmagic_splprot_row INT_VAR stat = 131 value = 1 relation = 4 RET c = row END
LAF cbmagic_splprot_row INT_VAR stat = 131 value = 1 relation = 4 RET d = row END
PRINT ~RESULT %a% %b% %c% %d%~
"""
    g, out, res = probe(work, weidu, body, biff=fx.game())
    check(res == [f"1 1 {len(fx.SPLPROT_ROWS)} {len(fx.SPLPROT_ROWS)}"], f"got {res}\n{out}")
    table = g.file("override/SPLPROT.2DA").decode("ascii").split()
    check(table[-4:] == [f"{len(fx.SPLPROT_ROWS)}_CBMAGIC", "131", "1", "4"], f"appended row: {table[-4:]}")


def hopelessness(*extra):
    """A sleep with a target icon, and the caster's icon that has to stay."""
    return ie.make_spl(1, 4, [{"target": 4, "min_level": level, "effects": [
        fx.fx(opcode=142, target=2, power=4, p2=44, duration=54),
        fx.fx(opcode=39, target=2, power=4, p2=1, duration=54),
        fx.fx(opcode=142, target=1, power=4, p2=44, duration=54),
        fx.fx(opcode=174, target=2, power=4, timing=4, duration=54),
        *extra]} for level in (1, 8)])


def wake_on_damage(work, weidu, **spells):
    g, out, _ = probe(work, weidu, "LAF cbmagic_fix_wake_on_damage END", biff=fx.game(**spells))
    check("SUCCESSFULLY INSTALLED" in out and not fg.with_warnings(out), out)
    return g, out


def check_sleep(g, resref):
    effects = [e for a in g.spl(resref)["abilities"] for e in a["effects"]]
    sleep = [e for e in effects if e["opcode"] == 39]
    check(len(sleep) == 2 and all(e["p2"] == 0 and e["special"] == 44 for e in sleep), f"sleep: {effects}")
    check(not any(e["opcode"] == 142 and e["target"] == 2 for e in effects), f"target icon: {effects}")
    check(sum(e["opcode"] == 142 and e["target"] == 1 and e["p2"] == 44 for e in effects) == 2, f"caster icon: {effects}")
    check(sum(e["opcode"] == 174 for e in effects) == 2, f"unrelated effect: {effects}")


@test
def hopelessness_wakes_on_damage_in_every_shape(work, weidu):
    """The sleep wakes on damage and has its own icon, in the spell or in a spell of its own."""
    g, _ = wake_on_damage(work / "own", weidu, SPWI411_SPL=hopelessness())
    check_sleep(g, "SPWI411")
    caster = ie.make_spl(1, 4, [{"target": 4, "min_level": level, "effects": [
        fx.fx(opcode=142, power=4, p2=37, duration=54),
        fx.fx(opcode=146, power=4, p2=2, timing=1, save=ie.SAVE_SPELL, resource="SPWI411B")]} for level in (1, 8)])
    g, _ = wake_on_damage(work / "split", weidu, SPWI411_SPL=caster, SPWI411B_SPL=hopelessness())
    check_sleep(g, "SPWI411B")
    check(g.file("override/SPWI411.SPL") is None, "the spell that only casts the sleep changed")
    # A permanent sleep never wakes, whatever parameter 2 says; on the caster it needs no icon.
    lasting = ie.make_spl(1, 4, [{"effects": [fx.fx(opcode=39, target=1, p2=1, timing=1, duration=54)]}])
    g, _ = wake_on_damage(work / "lasting", weidu, SPWI411_SPL=lasting)
    check(g.file("override/SPWI411.SPL") is None, "a sleep on the caster changed")


@test
def hopelessness_of_other_shapes_never_stops_the_install(work, weidu):
    """IWDification's version without a sleep, spells that are not its own, broken files and no spell
    at all: the rest of the install goes on, and the log says what was left."""
    hold = ie.make_spl(1, 4, [{"effects": [fx.fx(opcode=185, power=4, duration=54)]}])
    g, _ = wake_on_damage(work / "hold", weidu, SPWI411_SPL=hold)
    check(g.file("override/SPWI411.SPL") is None, "a version without sleep changed")
    foreign = ie.make_spl(1, 4, [{"effects": [fx.fx(opcode=146, power=4, p2=2, resource="SPWI999")]}])
    g, out = wake_on_damage(work / "foreign", weidu, SPWI411_SPL=foreign, SPWI999_SPL=hopelessness())
    check("also casts [SPWI999]" in out and g.file("override/SPWI999.SPL") is None, f"another spell changed:\n{out}")
    casts = ie.make_spl(1, 4, [{"effects": [fx.fx(opcode=146, power=4, p2=2, resource="SPWI411B")]}])
    _, out = wake_on_damage(work / "gone", weidu, SPWI411_SPL=casts)
    check("SPWI411B.spl, which SPWI411 casts, does not exist; left out" in out, out)
    _, out = wake_on_damage(work / "cut", weidu, SPWI411_SPL=b"SPL V1  " + bytes(30))
    check("Emotion: Hopelessness (SPWI411) left as it is: shorter than an SPL header" in out, out)
    _, out = wake_on_damage(work / "broken", weidu, SPWI411_SPL=casts, SPWI411B_SPL=b"garbage" * 40)
    check("Emotion: Hopelessness (SPWI411B) left as it is: not an SPL V1 file" in out, out)
    wake_on_damage(work / "none", weidu)
