# EStG 32d -- Gesonderter Steuertarif fuer Einkuenfte aus Kapitalvermoegen

## Source

- **Primary:** [gesetze-im-internet.de -- 32d EStG](https://www.gesetze-im-internet.de/estg/__32d.html)
- **With annotations:** [dejure.org -- 32d EStG](https://dejure.org/gesetze/EStG/32d.html)

## Scope

The flat tax rate (Abgeltungsteuer), the Veranlagungspflicht that makes a declaration necessary
at all, the foreign tax credit, and the Guenstigerpruefung option. Applying the rate is the
Finanzamt's step, not the taxpayer's: the declaration carries gross figures.

---

## [GT-CREDIT-001] Abs. 1 -- Flat Tax Rate

The income tax on capital income that does not fall under 20 Abs. 8 EStG is **25 percent** (Abgeltungsteuer).

Plus Solidaritaetszuschlag (5.5% of tax = effective 1.375%) and optional Kirchensteuer.

**Effective rates:**
- Without Kirchensteuer: 26.375%
- With Kirchensteuer (8%): 27.819%
- With Kirchensteuer (9%): 27.995%

## [GT-CREDIT-002] Abs. 3 -- Veranlagungspflicht (why a declaration is required at all)

Capital income **not subject to inlaendischer Steuerabzug** must be declared in the
Einkommensteuererklaerung; it is then assessed at the Abs. 1 rate. Income received through a
foreign broker is exactly that case: no inlaendische Zahlstelle, no Steuerabzug, no
Steuerbescheinigung. This is also why Abs. 5 is reachable at all -- Abs. 5 Satz 1 opens
*"In den Faellen der Absaetze 3 und 4"*.

## [GT-CREDIT-003] Abs. 4 -- Antrag auf Ueberpruefung des Steuereinbehalts

*Not* the Guenstigerpruefung. Abs. 4 lets a taxpayer whose income **has** borne
Kapitalertragsteuer request an assessment under Abs. 3 Satz 2 -- e.g. to use an unexhausted
Sparer-Pauschbetrag, a loss not yet taken into account under 43a Abs. 3, a Verlustvortrag under
20 Abs. 6, or foreign taxes not yet credited. On Anlage KAP this is the **Zeile 5** request --
*"Ueberpruefung des Steuereinbehalts dem Grunde und der Hoehe nach"* -- not the Zeile 4 one
(`reference/Anltg_KAP_24.md`, Zeile 5; identical in the 2025 Anleitung; read 2026-08-03).

Foreign-broker income cannot reach Abs. 4 on its own: there is no Steuereinbehalt to review. It
matters only for a taxpayer who also holds a German depot.

## [GT-CREDIT-004] Abs. 5 -- Foreign Tax Credit

*"[...] die auf auslaendische Kapitalertraege festgesetzte und gezahlte und um einen entstandenen
Ermaessigungsanspruch gekuerzte auslaendische Steuer, jedoch hoechstens 25 Prozent auslaendische
Steuer auf den einzelnen steuerpflichtigen Kapitalertrag, auf die deutsche Steuer anzurechnen"*
(Satz 1).

This is a **self-standing** credit mechanism, not an application of 34c Abs. 1 -- 34c Abs. 1
Satz 1 *zweiter Halbsatz* expressly excludes income to which 32d Abs. 1 und 3 bis 6 applies
(see `estg-34d-auslaendische-einkuenfte.md` for the verbatim carve-out). Two ceilings, both
often missed:

### [GT-CREDIT-005] Satz 1 -- the per-Kapitalertrag ceiling

At most 25 % foreign tax per *individual* Kapitalertrag. No per-country Anrechnungshoechstbetrag
applies.

### [GT-CREDIT-006] Satz 3 -- the per-VZ ceiling

*"Die auslaendischen Steuern sind nur bis zur Hoehe der auf die im jeweiligen
Veranlagungszeitraum bezogenen Kapitalertraege im Sinne des Satzes 1 entfallenden deutschen Steuer
anzurechnen."* Across the Veranlagungszeitraum, the credit is limited to the German tax falling on
that year's foreign Kapitalertraege.

**Satz 2**, between the two ceilings and previously unstated (Validation Protocol item 2), extends
Satz 1 to treaty credits: *"Soweit in einem Abkommen zur Vermeidung der Doppelbesteuerung die
Anrechnung einer auslaendischen Steuer einschliesslich einer als gezahlt geltenden Steuer auf die
deutsche Steuer vorgesehen ist, gilt Satz 1 entsprechend."* This is the route by which a **fiktive
Quellensteuer** under a DBA is credited -- the figure the form takes on Zeile 42, separately from
the Zeile 41 amount. Retrieved 2026-08-03.

### [GT-CREDIT-026] Satz 1 -- the Ermaessigungsanspruch

Satz 1 credits the foreign tax *"um einen entstandenen Ermaessigungsanspruch gekuerzte"*. Where the
source state withheld more than it may keep, the excess is an Ermaessigungsanspruch and is **not
creditable in Germany**; only the tax for which no reduction can be claimed is. Two things fix how
far this bites, and both were previously unstated here.

**What grounds an Ermaessigungsanspruch: the source state's law, or a DBA.** BMF-Schreiben vom 14.05.2025,
Rn. 207a (retrieved 2026-09-22, page reference in `../bmf-guidance/abgeltungsteuer-einzelfragen.md`):
*"Die auszahlende Stelle hat keine Anrechnung der auslaendischen Quellensteuer vorzunehmen, wenn im
betreffenden auslaendischen Staat nach dem Recht dieses Staates ein Anspruch auf teilweise oder
vollstaendige Erstattung der auslaendischen Steuer besteht. Besteht lediglich der Anspruch auf eine
teilweise Erstattung, kann der Steuerpflichtige die Anrechnung im Wege der Veranlagung gemaess § 32d
Absatz 4 EStG beantragen. In diesen Faellen hat er dem zustaendigen Finanzamt die Hoehe der
moeglichen Erstattung im auslaendischen Staat nachzuweisen ..."* Rn. 207a names a refund claim
*"nach dem Recht dieses [Quellen-]Staates"*. The BZSt, for the Veranlagung
(`../bmf-guidance/abgeltungsteuer-einzelfragen.md` pointer; BZSt Erlaeuterungen 2026), names **two**
grounds: *"Es ist nur die auslaendische Steuer anrechenbar, die festgesetzt und gezahlt worden ist
und fuer die im Quellenstaat -- nach dessen nationalem Recht oder aufgrund eines DBA -- kein
Ermaessigungsanspruch geltend gemacht werden kann (§ 43a Abs. 3 Satz 1 in Verbindung mit § 32d
Abs. 5 EStG)."* An Ermaessigungsanspruch therefore exists where either the source state's own law
**or a DBA** grants a reduction. Where both point to the same rate -- a dividend within DBA Art. 10,
which the source state applies -- the creditable amount is the withheld tax capped at that treaty
rate; for a US dividend, including a payment in lieu on lent units whose attribution stays with the
lender, that rate is 15 % ([GT-CREDIT-027], [GT-CREDIT-028]). Where the two grounds diverge -- a DBA
that would deny the source state any tax, applied by a source state that refunds only to a treaty
rate -- the extent of the Ermaessigungsanspruch is not settled by any located Tier 1 or Tier 2 source:
`../research/open-legal-questions.md` Q22.

**§ 34c Abs. 6 Satz 2 names two limits; § 32d Abs. 5 Satz 1 names one.** For treaty cases outside
the Abgeltungsteuer, § 34c Abs. 6 Satz 2 applies the credit *"auf die nach dem Abkommen anzurechnende
und um einen entstandenen Ermaessigungsanspruch gekuerzte auslaendische Steuer"* -- treaty conformity
and the Ermaessigungsanspruch as two separate conditions -- and its second Halbsatz withdraws itself
from Abgeltungsteuer income: *"das gilt nicht fuer Einkuenfte, auf die § 32d Absatz 1 und 3 bis 6
anzuwenden ist"* (quoted with Satz 3 at [GT-CREDIT-012]). § 32d Abs. 5 Satz 1 names only the
Ermaessigungsanspruch, and its Satz 2 applies Satz 1 *entsprechend* in treaty cases. This is the
textual ground for the reading that § 32d Abs. 5 knows no separate treaty-conformity limit; whether
the BZSt's *"aufgrund eines DBA"* brings one in through the Ermaessigungsanspruch itself is Q22.
§ 34c Abs. 1 is in any case carved out for this income by its own Satz 1 zweiter Halbsatz
([GT-CREDIT-012]).

**The ceiling and the treaty cap are two different reductions.** The Ermaessigungsanspruch reduction
here (down to the treaty rate) is distinct from the Satz 1 25 %-per-Kapitalertrag ceiling
([GT-CREDIT-005]) and the Satz 3 per-VZ ceiling ([GT-CREDIT-006]); the ceilings can bite below the
treaty rate on a fund item after Teilfreistellung. BMF-Schreiben vom 14.05.2025, Rn. 148 (retrieved
2026-09-22): *"Nach § 32d Absatz 5 Satz 1 EStG sind hoechstens 25 % auslaendische Steuer auf den
einzelnen Kapitalertrag anzurechnen. Bei auslaendischen Investmentertraegen ist fuer die Berechnung
des anrechenbaren Hoechstbetrages der nach Beruecksichtigung der Teilfreistellung nach § 20 InvStG
verbleibende steuerpflichtige Investmentertrag massgebend."* For an Aktienfonds the ceiling is
25 % x 70 % = 17.5 % of gross, above the 15 % treaty rate, so it does not bite; for the two
real-estate fund types (Teilfreistellung 60 % / 80 %) it does. The Rn. 148 worked examples (an
Auslands-Immobilienfonds where the ceiling binds below the treaty rate, and an Aktienfonds where it
does not) are indexed in `../bmf-guidance/abgeltungsteuer-einzelfragen.md`.

**Substantiation.** The taxpayer must be able to prove the withheld tax, the treaty rate, and any
refund available abroad. The Tier 1 ground is § 90 Abs. 2 AO (foreign-fact cooperation duty),
gesetze-im-internet.de/ao_1977/__90.html, retrieved 2026-09-22: *"... so haben die Beteiligten diesen
Sachverhalt aufzuklaeren und die erforderlichen Beweismittel zu beschaffen. Sie haben dabei alle fuer
sie bestehenden rechtlichen und tatsaechlichen Moeglichkeiten auszuschoepfen. ..."*; Rn. 207a states
the administration's matching expectation.

**Applicable tax years:** all years in scope (regime floor is the Abgeltungsteuer). BMF 14.05.2025
applies to all open cases (Rn. 324). The DBA rate is 2006-Protokoll and unchanged in the window
([GT-CREDIT-027]).

The form takes the figure on **Zeile 41**, *"noch nicht angerechnete auslaendische Steuer"*
(verified identical in the 2024 and 2025 Anleitung). The amount entered is the tax to be credited:
the withheld tax reduced by the Ermaessigungsanspruch of Satz 1 (this claim). That follows from
Satz 1 itself; the Anleitung's heading *"anzurechnende Steuern"* for Zeilen 37 to 42 is consistent
with it but does not decide it ([GT-FORM-006]). The per-Kapitalertrag
ceiling of Satz 1 ([GT-CREDIT-005]) and the per-VZ ceiling of Satz 3 ([GT-CREDIT-006]) are applied
in the assessment.

## [GT-CREDIT-007] Abs. 6 -- Guenstigerpruefung (assessment at the individual rate)

*"Auf Antrag des Steuerpflichtigen werden anstelle der Anwendung der Absaetze 1, 3 und 4 die
nach § 20 ermittelten Kapitaleinkuenfte den Einkuenften im Sinne des § 2 hinzugerechnet und der
tariflichen Einkommensteuer unterworfen, wenn dies zu einer niedrigeren Einkommensteuer
einschliesslich Zuschlagsteuern fuehrt (Guenstigerpruefung)."* (Satz 1)

Satz 2 keeps the foreign tax credit under **Abs. 5** even when the Guenstigerpruefung is
elected, so electing it never triggers 34c's per-country Anrechnungshoechstbetrag. Satz 3-4: the
application is only possible uniformly for all Kapitalertraege of the VZ, and for both spouses
jointly. On Anlage KAP this is the **Zeile 4** request -- *"Wenn Sie die Guenstigerpruefung
beantragen moechten, tragen Sie in Zeile 4 eine ,1' ein"* (`reference/Anltg_KAP_24.md`, Zeile 4;
identical in the 2025 Anleitung; read 2026-08-03).

> **Correction, 2026-08-03.** This file previously labelled **Abs. 4** the Guenstigerpruefung.
> It is Abs. 6; Abs. 4 is the Ueberpruefung des Steuereinbehalts. It also stated the Abs. 5
> credit runs *"per 34c Abs. 1 EStG"*, which inverts the relationship. Both were contradicted by
> this library's own `research/inlaendisch-auslaendisch-relevance.md`, which cites Abs. 6 and
> Abs. 6 Satz 2 correctly. Statutory text retrieved 2026-08-03 from
> gesetze-im-internet.de/estg/__32d.html. Validation Protocol items 2 and 8.

---

## What the declaration does not contain

The Abgeltungsteuer amount itself is not a figure the taxpayer enters. It follows from the
declared gross income together with circumstances the declaration does not carry --
Guenstigerpruefung, Sparer-Pauschbetrag, Kirchensteuer -- and is computed by the Finanzamt.
