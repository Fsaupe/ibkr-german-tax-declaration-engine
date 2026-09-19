# § 22 Nr. 3 EStG -- Einkuenfte aus Leistungen

## Scope of this file

The residual income type reached when a payment is neither one of the six Einkunftsarten of
§ 2 Abs. 1 Satz 1 Nr. 1 bis 6 nor one of the other Nummern of § 22. It is where the order of
enquiry in [GT-ESTG20-049] ends, and it decides the treatment of a benefit a bank or broker grants
for placing capital with it.

**Claim ID area.** The area table in the knowledge store defines no `GT-ESTG22`, and the boundary
against § 22 Nr. 3 is already carried under `GT-ESTG20` at [GT-ESTG20-049]. The claims below
therefore continue the `GT-ESTG20` sequence. Introducing a dedicated area would be a change to the
area table itself and is left to a `ks-maint`.

## Sources

- **Tier 1 -- § 22 Nr. 3 EStG**, retrieved 2026-08-13 from
  [gesetze-im-internet.de/estg/__22.html](https://www.gesetze-im-internet.de/estg/__22.html)
- **Tier 1 -- § 11 Abs. 1 EStG**, retrieved 2026-08-13 from
  [gesetze-im-internet.de/estg/__11.html](https://www.gesetze-im-internet.de/estg/__11.html)
- **Tier 1 -- § 8 Abs. 1, Abs. 2 EStG**, retrieved 2026-08-13 from
  [gesetze-im-internet.de/estg/__8.html](https://www.gesetze-im-internet.de/estg/__8.html)
- **Tier 1 -- § 20 Abs. 1 Nr. 7 EStG**, retrieved 2026-09-20 from
  [gesetze-im-internet.de/estg/__20.html](https://www.gesetze-im-internet.de/estg/__20.html);
  the verbatim text is held at [GT-ESTG20-003]. Cited for the charging element that the boundary
  against § 22 Nr. 3 turns on.
- **Tier 2 -- BMF-Schreiben vom 14.05.2025 (Einzelfragen zur Abgeltungsteuer), Rz. 129b**, retrieved
  2026-09-20; index and retrieval record in `../bmf-guidance/abgeltungsteuer-einzelfragen.md`. The
  decisive administrative authority on a bank/broker premium for moving or retaining capital.
- **Tier 4 -- BFH v. 30.06.2011 -- VI R 37/09**, retrieved 2026-08-13 from
  [bundesfinanzhof.de](https://www.bundesfinanzhof.de/en/entscheidungen/entscheidungen-online/decision-detail/STRE201110231/).
  Cited for the Zufluss test only, alongside § 11 Abs. 1 Satz 1, never alone --
  Validation Protocol item 1.

Applicable tax years: unrestricted within the Abgeltungsteuer regime. None of the three provisions
carries a first year of application relevant here, and the 256-Euro figure in Nr. 3 Satz 2 is not
year-parameterised.

---

## [GT-ESTG20-062] Nr. 3 Satz 1 -- the subsidiarity gate, and Satz 2 to 4

**Satz 1**, verbatim:

> *"Einkuenfte aus Leistungen, soweit sie weder zu anderen Einkunftsarten (§ 2 Absatz 1 Satz 1
> Nummer 1 bis 6) noch zu den Einkuenften im Sinne der Nummern 1, 1a, 2 oder 4 gehoeren, z. B.
> Einkuenfte aus gelegentlichen Vermittlungen und aus der Vermietung beweglicher Gegenstaende."*

The clause is **subsidiary by its own wording**: it is reached only once the six Einkunftsarten and
the other Nummern of § 22 are exhausted, never alongside them. The two named examples are
illustrative (*"z. B."*), not exhaustive -- a *Leistung* is any conduct, including a Dulden or
Unterlassen, done for consideration.

**Satz 2**, verbatim:

> *"Solche Einkuenfte sind nicht einkommensteuerpflichtig, wenn sie weniger als 256 Euro im
> Kalenderjahr betragen haben."*

A **Freigrenze, not a Freibetrag**: below 256 Euro the income is not taxable at all; at 256 Euro or
above the whole amount is taxable, not merely the excess. It is measured **per Kalenderjahr and
across all Leistungen of that year taken together**, not per single receipt.

**What the cited unit also contains.** Satz 3 bars a loss from Leistungen from being offset against
other income or carried under § 10d. Satz 4 lets such a loss reduce Leistungen income of the
immediately preceding and the following assessment periods, § 10d Abs. 4 applying accordingly.
Neither is reached by a benefit received, which cannot be negative.

---

## [GT-ESTG20-063] A benefit granted for placing capital is a Leistung, not Kapitalertrag

Where a bank or broker grants a benefit **in return for the customer transferring or leaving funds
with it**, the order of enquiry fixed by [GT-ESTG20-049] and [GT-ESTG20-050] runs as follows.

**Step 1 -- § 20 Abs. 3 fails.** Abs. 3 requires the benefit to be granted *neben* or *an deren
Stelle* of Einnahmen under Abs. 1 or Abs. 2. A benefit owed for the act of transferring funds is
owed **whether or not the funds go on to yield anything**, so there is no Einnahme of a particular
Kapitalanlage for it to stand alongside or replace. That is precisely the test [GT-ESTG20-050]
states, and the reason it gives -- both worked Randziffern of the administration combine Abs. 3
with a Nummer of Abs. 1 -- applies unchanged.

**Step 2 -- § 20 Abs. 1 Nr. 7 fails.** A credit balance is a Kapitalforderung, so the gate that
stopped the Wertpapierdarlehen fee (a Sachforderung, [GT-ESTG20-046]) is passed here; the exclusion
turns on the charging element instead. Nr. 7 Satz 1 taxes *"Ertraege aus sonstigen Kapital-
forderungen jeder Art, **wenn die Rueckzahlung des Kapitalvermoegens oder ein Entgelt fuer die
Ueberlassung des Kapitalvermoegens zur Nutzung** zugesagt oder geleistet worden ist, auch wenn die
Hoehe ... von einem ungewissen Ereignis abhaengt"* ([GT-ESTG20-003], verbatim there). The taxable
receipt must be an **Entgelt fuer die Ueberlassung des Kapitalvermoegens zur Nutzung** -- the
consideration for the capital being made available for the bank's use. Because Satz 1 covers such an
Entgelt *even where its amount depends on an uncertain event*, the exclusion **cannot** rest on the
benefit not being "measured by amount and time"; that reading is contrary to the statutory text.

**The administration has drawn the line, and it is not Nr. 7.** BMF-Schreiben vom 14.05.2025
(Einzelfragen zur Abgeltungsteuer) **Rz. 129b**, under the heading *Einkuenfte aus sonstigen
Leistungen (§ 22 Nummer 3 EStG)*, treats a **Geldpraemie a receiving Kreditinstitut pays for the
transfer of a Wertpapierdepot** as *"Einkuenfte aus sonstigen Leistungen im Sinne des § 22 Nummer 3
EStG ..., sofern sie nicht einer anderen Einkunftsart (§§ 13, 15, 18 oder 21 EStG) zugeordnet werden
kann"* (¶1). The premium for moving capital to the bank is consideration for the customer's
*Leistung*, not an Entgelt for the use of a Kapitalforderung, so it falls outside Nr. 7 and into
§ 22 Nr. 3. The administration reserves a **different** treatment for one narrow case only: where the
premium is paid *"unter der Bedingung ..., dass Wertpapiere ... erworben werden"*, Rz. 129b ¶2
directs it to **reduce the Anschaffungskosten** of those securities rather than be income at all --
which is not this benefit (see the fact pattern below).

**Step 3 -- § 22 Nr. 3 applies.** Its subsidiarity clause is satisfied once § 20 is exhausted. The
customer's conduct -- transferring funds and leaving them in place -- is a *Leistung*, and the
benefit is its consideration.

**The supported fact pattern.** The subsumption above is for a benefit granted **for the deposit or
retention of the customer's own capital and not conditioned on the acquisition of securities**. Two
boundaries fix its edges. Where the benefit is a security rather than a cash amount, only its
**valuation** differs -- it is a benefit in kind, brought to tax at the ueblicher Endpreis on the
day of Zufluss (§ 8 Abs. 2 Satz 1, [GT-ESTG20-064]); the income category is unchanged, because
Rz. 129b ¶1 turns on what the benefit is paid *for*, not on the form it takes. Where the benefit is
instead paid *on the condition that the customer acquires securities*, it is the Rz. 129b ¶2 case --
a reduction of the Anschaffungskosten of those securities, not income under Nr. 3 -- and is outside
this claim.

**This is the same three-step result the store already reached for the Wertpapierdarlehen fee**
(open-legal-questions.md Q14, retired 2026-08-09, at [GT-ESTG20-049]); the fee failed Step 2 on the
gate, this benefit fails it on the element. Both land in Nr. 3.

**Consequence for Kapitalertragsteuer.** § 22 Nr. 3 income is not Kapitalertrag, so no domestic
Kapitalertragsteuer arises on it and it does not enter the Sparer-Pauschbetrag or the § 20 Abs. 6
loss pots. It is declared on Anlage SO, not Anlage KAP.

---

## [GT-ESTG20-064] Valuation and Zufluss of a benefit granted in kind

**Valuation -- § 8 Abs. 1 Satz 1 and Abs. 2 Satz 1 EStG.**

> *"Einnahmen sind alle Gueter, die in Geld oder Geldeswert bestehen und dem Steuerpflichtigen im
> Rahmen einer der Einkunftsarten des § 2 Absatz 1 Satz 1 Nummer 4 bis 7 zufliessen."*

> *"Einnahmen, die nicht in Geld bestehen (Wohnung, Kost, Waren, Dienstleistungen und sonstige
> Sachbezuege), sind mit den um uebliche Preisnachlaesse geminderten ueblichen Endpreisen am
> Abgabeort anzusetzen."*

§ 22 Nr. 3 income falls under § 2 Abs. 1 Satz 1 Nr. 7, so § 8 reaches it. A benefit granted in
securities rather than money is a *sonstiger Sachbezug* and is valued at the **ueblicher Endpreis
am Abgabeort** -- for an exchange-traded share, its market price.

**Zufluss -- § 11 Abs. 1 Satz 1 EStG.**

> *"Einnahmen sind innerhalb des Kalenderjahres bezogen, in dem sie dem Steuerpflichtigen
> zugeflossen sind."*

Satz 1 fixes the year by Zufluss and does not define it. **The test is wirtschaftliche
Verfuegungsmacht, and BFH VI R 37/09 states both halves of it.**

Leitsatz 1, verbatim:

> *"Dem Arbeitnehmer fliesst der geldwerte Vorteil in Form verbilligter Aktien in dem Zeitpunkt
> zu, in dem er die wirtschaftliche Verfuegungsmacht ueber die Aktien erlangt."*

Leitsatz 2, verbatim:

> *"Ein solcher Zufluss liegt nicht vor, solange dem Arbeitnehmer eine Verfuegung ueber die
> Aktien rechtlich unmoeglich ist."*

And the point that decides a restricted benefit, Rn. 12 (restated on the facts at Rn. 23):

> *"Einem solchen Zufluss im vorgenannten Sinne steht nicht entgegen, dass der Arbeitnehmer
> aufgrund einer Sperr- bzw. Haltefrist die Aktien fuer eine bestimmte Zeit nicht veraeussern
> kann."*

**So the line is not restricted versus unrestricted, but obligatorisch versus dinglich.** A
contractual restraint -- a holding period, a promise to give the shares back on some future
event -- does **not** postpone Zufluss. What postpones it is the disposal being *rechtlich
unmoeglich*: Rn. 15, *"Aktien sind daher nicht zugeflossen, solange dem Arbeitnehmer eine
Verfuegung darueber rechtlich unmoeglich ist."*

**Applied to a benefit in shares booked into the recipient's account:** Zufluss falls on the
booking, and a condition under which the grantor may later reclaim the shares does not defer it,
**unless the recipient is legally unable to dispose of them until the condition lapses**, which
is Leitsatz 2's case.

**What the cited unit also contains, and the limit of the citation.** VI R 37/09 is decided
under § 19 Abs. 1 Satz 1 Nr. 1 in Verbindung mit § 8 Abs. 1 and § 11 Abs. 1 Satz 1 EStG -- an
employee receiving shares from an employer. § 11's Zufluss concept is general and is what is
borrowed here; **no located source applies the test to a benefit granted by a broker under
§ 22 Nr. 3**, and that step is recorded as the residual uncertainty in
`../research/open-legal-questions.md` under Q17. The decision itself did not settle its own facts:
Rn. 17 and Rn. 20 remand to the Finanzgericht to establish whether, under the foreign law governing
the shares, a disposal was rechtlich moeglich in the year in dispute -- so whether Zufluss had
occurred was left open on the facts. Rn. numbering verified 2026-09-20 against the full text at
urteile-gesetze.de/rechtsprechung/vi-r-37-09, which carries the court's own Randnummern.

**What the cited unit also contains.** § 11 Abs. 1 has five sentences: Satz 2 on regularly
recurring income falling either side of the year end, Satz 3 on spreading income from a
Nutzungsueberlassung over the advance period, Satz 4 cross-referring provisions for
non-employment income, and Satz 5 preserving the profit-determination rules. None is reached by a
one-off benefit in kind.

---

## [GT-ESTG20-065] The amount taxed on receipt becomes the Anschaffungskosten

Where the benefit consists of securities, the value brought to tax under [GT-ESTG20-064] is the
recipient's **Anschaffungskosten** for those securities on a later disposal under § 20 Abs. 2
Satz 1 Nr. 1 EStG. Taxing the receipt and then taxing the whole disposal proceeds again would tax
the same accretion twice; the acquisition is entgeltlich to the extent it has been taxed, and
§ 20 Abs. 4 Satz 1 measures the gain against the Anschaffungskosten.

**This claim does not depend on the benefit having actually been declared.** The Anschaffungskosten
follow from the value that fell to be taxed under § 11 and § 8, not from what appeared on a return.

**Where the sources run out.** Whether a receipt left untaxed by the Freigrenze of Nr. 3 Satz 2
nonetheless supplies Anschaffungskosten at its full value is **not settled** by any Tier 1 or
Tier 2 source located. Recorded in `../research/open-legal-questions.md`.

## [GT-ESTG20-066] The order of a same-day award reversal and a disposal is not fixed by law

An award reversal removes the awarded lot ([GT-ESTG20-064]); a disposal of the same security
consumes lots in the FIFO order § 20 Abs. 4 Satz 7 fixes ([GT-ESTG20-012]), the earliest-acquired
first, with lot selection by instruction disregarded. **Satz 7 fixes which lot a disposal consumes;
it does not fix the sequence of two distinct events -- a reversal and a disposal -- that fall on the
same day.** Where both touch one security on one day, which is applied first decides whether the
disposal is measured before or after the awarded lot has been removed, and so which lot's
Anschaffungskosten the gain is measured against.

**No Tier 1 or Tier 2 source located settles that sequence.** Satz 7 speaks to the consumption
order within a disposal, not to the ordering of a disposal against a same-day event that is not
itself a disposal; and § 11's Zufluss/Abfluss concept fixes the year an item falls in, not the
intra-day order of two events already in the same year. The two readings, and what the choice
between them moves, are recorded in `../research/open-legal-questions.md` as Q18.

This has to be decided for a figure only where an award reversal and a disposal of the same
security fall on one day and the awarded lot is within the disposal's FIFO reach. The reading
chosen, and the evidence that each grey-area condition is met, are recorded against this claim ID
in `docs/legal-implementation-map.md` -- not here, where only the law belongs.
