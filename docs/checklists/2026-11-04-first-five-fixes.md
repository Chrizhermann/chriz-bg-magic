# Testliste: die ersten fünf Fixes (4. November)

Ein Test-Lab: BG2:EE 2.7.3.0 mit EEex v1.3.1 und Chriz BG Magic, Debug Mode an (im
Baldur.lua des Profils: `SetPrivateProfileString('Program Options','Debug Mode','1')`).

**Einmal vorab:** `InfinityLoader.exe` im Lab-Ordner starten, neues Spiel, als
Protagonist einen Mage bauen. Im Verlies von Irenicus pausieren. Konsole: Ctrl+Space,
jede Zeile einzeln, Enter.

Ein Gnoll als Zauberer und Ziel (Stufe 2, feindlich; erscheint am Mauszeiger, also den
Zeiger vorher ein paar Schritte vom Mage weg halten):

```
C:CreateCreature("AEGNOLL")
```

## 1. Spirit Armor stapelt nicht mehr mit sich selbst

1. Im Charakterbogen den Wert „Spell“ bei den Saving Throws merken.
2. Zweimal, mit ein paar Sekunden Abstand:
   ```
   C:Eval('ReallyForceSpellRES("SPWI414",Player1)')
   ```
3. **Erwartet:** Der Save vs. Spell ist nur **3** besser als vorher (Vanilla: 6), und am
   Porträt hängt nur ein Spirit-Armor-Symbol.

## 2. Minor Spell Deflection hält nur noch Stufe 1 bis 4 auf

1. ```
   C:Eval('ReallyForceSpellRES("SPWI318",Player1)')
   ```
2. Der Gnoll wirkt Flame Strike (Stufe 5) auf dich:
   ```
   C:Eval('ActionOverride("aegnoll",ReallyForceSpellRES("SPPR503",Player1))')
   ```
   **Erwartet:** Der Flame Strike trifft (Vanilla: abgefangen).
3. Der Gnoll wirkt Magic Missile (Stufe 1):
   ```
   C:Eval('ActionOverride("aegnoll",ReallyForceSpellRES("SPWI112",Player1))')
   ```
   **Erwartet:** abgefangen, wie in Vanilla.
4. Text: Spell im Zauberbuch ansehen, oder die Schriftrolle `C:CreateItem("SCRL6G")`.
   **Erwartet:** „up to 4th-level spells“.

## 3. Save vs. Breath bei Explosionen und Flächenschaden

1. Dein Save vs. Breath gelingt immer, dein Save vs. Spell fast nie (20 ist der
   schlechteste Wert, nur eine gewürfelte 20 rettet):
   ```
   C:Eval('ChangeStat(Player1,SAVEVSBREATH,1,SET)')
   C:Eval('ChangeStat(Player1,SAVEVSSPELL,20,SET)')
   ```
2. Den Gnoll auf Stufe 10 heben, damit der Schaden deutlich ist, und ihn einen Fireball
   auf dich werfen lassen (vorher mit Ctrl+R heilen, falls nötig):
   ```
   C:Eval('ChangeStat("aegnoll",LEVEL,10,SET)')
   C:Eval('ActionOverride("aegnoll",ReallyForceSpellRES("SPWI304",Player1))')
   ```
3. **Erwartet:** Im Log nur halber Schaden (rund 17 statt rund 35), weil der Save vs.
   Breath gelingt. In Vanilla wäre es voller Schaden.
4. Text: `C:CreateItem("SCRL1K")` (Lightning Bolt). **Erwartet:** „Saving Throw vs.
   Breath“.

## 4. Schaden weckt Schlafende

1. Schriftrollen holen und zwei Gnolle dazu:
   ```
   C:CreateItem("SCRL81",3)
   C:CreateItem("SCRL70",3)
   C:CreateItem("SCRL97",3)
   C:CreateCreature("AEGNOLL")
   ```
2. Sleep (SCRL81) auf die Gnolle lesen. Wenn einer schläft, mit der Waffe zuschlagen.
   **Erwartet:** Er wacht beim ersten Treffer auf (Vanilla: schläft weiter).
3. Dasselbe mit Color Spray (SCRL70) und Stinking Cloud (SCRL97).
4. Command, Greater Command und Emotion: Hopelessness, je einzeln auf einen Gnoll, danach
   wieder zuschlagen:
   ```
   C:Eval('ActionOverride(Player1,ReallyForceSpellRES("SPPR102","aegnoll"))')
   C:Eval('ActionOverride(Player1,ReallyForceSpellRES("SPPR512","aegnoll"))')
   C:Eval('ActionOverride(Player1,ReallyForceSpellRES("SPWI411","aegnoll"))')
   ```
   **Erwartet:** Er wacht beim ersten Treffer auf (Vanilla: schläft weiter). Bei
   Hopelessness endet nur der Schlaf; die übrigen Effekte laufen wie gehabt aus.

## 5. Web

1. Eine Riesenspinne, ein Green Slime und ein Gnoll, nah beieinander (Mauszeiger):
   ```
   C:CreateCreature("SPIDGI01")
   C:CreateCreature("JELGRE01")
   C:CreateCreature("AEGNOLL")
   C:CreateItem("SCRL99",3)
   ```
2. Web (SCRL99) auf die Gruppe lesen.
   **Erwartet:** Spinne und Slime bleiben frei, der Gnoll klebt (wenn er seinen Save
   vs. Breath mit -2 nicht schafft). Beim Slime ist das der Fix. Die Spinne war schon im
   Grundspiel frei: alle Spinnen tragen das Item `ANTIWEB`, das vor dem Web-Projektil
   schützt.
3. Unser Spinnen-Schutz, ohne Projektil: Web direkt auf die Spinne legen:
   ```
   C:Eval('ActionOverride(Player1,ApplySpellRES("SPWI215","spidgi01"))')
   ```
   **Erwartet:** Die Spinne bleibt frei (im Grundspiel klebt sie jetzt).
4. Je ein Wesen aus den neuen Gruppen (fliegend, körperlos) und ein Riese, nah beieinander:
   ```
   C:CreateCreature("BEHGAU01")
   C:CreateCreature("FIRWRA01")
   C:CreateCreature("GIANTF01")
   ```
   Web (SCRL99) auf die Gruppe lesen. **Erwartet:** Gauth und Greater Wraith bleiben frei,
   auch wenn sie ihren Save nicht schaffen. Der Fire Giant klebt, wenn er seinen Save nicht
   schafft: Riesen sind nicht immun.
5. Text der Schriftrolle: **Erwartet:** „Saving Throw vs. Breath with a -2 penalty“.
