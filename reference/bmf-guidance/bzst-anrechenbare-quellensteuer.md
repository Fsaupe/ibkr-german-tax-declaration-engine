# BZSt -- creditable foreign withholding on dividends, by source state

The Bundeszentralamt fuer Steuern's annual table of how much foreign withholding tax on dividends
and interest is creditable under § 32d Abs. 5 EStG, per source state with which Germany has a DBA.
It is the administrative statement of the Ermaessigungsanspruch of [GT-CREDIT-026] for each state:
the rate in column C is what remains once the reduction the source state's own law or the DBA
grants has been taken off.

## Source

Tier 2 (administrative guidance). One edition per year, each stating the law at 1 January of that
year. All four were retrieved 2026-09-23 and read with `pdftotext -layout`:

| Edition | URL | Pages |
|---|---|---|
| Stand 1. Januar 2023 | https://www.bzst.de/SharedDocs/Downloads/DE/EU_OECD/anrechenbare_ausl_quellensteuer_2023.pdf?__blob=publicationFile&v=1 | 26 |
| Stand 1. Januar 2024 | https://www.bzst.de/SharedDocs/Downloads/DE/EU_OECD/anrechenbare_ausl_quellensteuer_2024.pdf?__blob=publicationFile&v=1 | 26 |
| Stand 1. Januar 2025 | https://www.bzst.de/SharedDocs/Downloads/DE/EU_OECD/anrechenbare_ausl_quellensteuer_2025.pdf?__blob=publicationFile&v=1 | 25 |
| Stand 1. Januar 2026 | https://www.bzst.de/SharedDocs/Downloads/DE/EU_OECD/anrechenbare_ausl_quellensteuer_2026.pdf?__blob=publicationFile&v=1 | 29 |

The 2026 edition is the one [GT-CREDIT-026] and [GT-CREDIT-027] already quote (there as `v=2`).

**Applicable tax years: one edition per assessment year, never carried.** Each edition gives
*"die Rechtslage zum 1. Januar"* of its year (2025 edition, Erlaeuterungen, page 1). A rate
stated here holds for the assessment year of the edition it was read from, and for no other
year: a year whose edition has not been read has no rate in this store, even where the
neighbouring editions agree. Editions read: **2023, 2024, 2025, 2026**.

A change taking effect during a year shows only in the next year's edition. For VZ 2023, 2024
and 2025 the following edition has been read too and shows the same value for every row below,
so no such change occurred. For VZ 2026 no later edition exists yet (as of 2026-09-23).

The Erlaeuterungen add that paying agents need not apply a change against the previous year's
edition before 1 July (Rn. 208a of the BMF-Schreiben vom 14.05.2025); that is a
Nichtbeanstandung for the Steuerabzug, not for the Veranlagung.

---

## [GT-CREDIT-029] Column C -- the creditable dividend rate per source state

**What the columns mean** (Erlaeuterungen, 2025 edition, pages 1-2). Columns A (dividends) and B
(interest): *"unter Buchstabe a) ... ob der Quellenstaat nach seinem nationalen Recht eine Steuer
auf Dividenden und/oder Zinsen erhebt"*; *"Unter Buchstabe b) ist der Prozentsatz angegeben, den
die Quellensteuer nach dem zwischen Quellenstaat und Deutschland abgeschlossenen DBA nicht
uebersteigen darf. Wurde im Quellenstaat eine hoehere Steuer erhoben, kann die steuerpflichtige
Person im Quellenstaat einen Entlastungsanspruch geltend machen"*. Columns C and D give *"das
Ergebnis, d. h. der massgebende Wert, in Prozent"* -- what is *anrechenbar*. The table covers
*"unbeschraenkt steuerpflichtige Personen, die aufgrund ihres Wohnsitzes oder dauernden Aufenthalts
in Deutschland der Einkommensteuer unterliegen"* (page 1).

**What "Dividenden" means here** (same page): *"Dividenden = Gewinnausschuettungen von
Kapitalgesellschaften an ihre Anteilseigner"*. A distribution by an investment fund is not within
that definition as the table uses it; for a US fund, the treaty itself puts RIC dividends on the
dividend rate ([GT-CREDIT-027], Art. 10 Abs. 4 Satz 2).

**The rows, per edition.** Column C (creditable dividend rate, in %), read from each edition
separately; the edition's year is the assessment year it governs. Column A a) (national rate)
and A b) (DBA ceiling) are the same in all four editions and are given once.

| Source state | Code | A a) national | A b) DBA | C 2023 | C 2024 | C 2025 | C 2026 | Pages 2023 / 2024 / 2025 / 2026 |
|---|---|---|---|---|---|---|---|---|
| Frankreich | FR | 12,8 | 15 | 12,8 | 12,8 | 12,8 | 12,8 | 8 / 8 / 7 / 8 |
| Japan | JP | 15 / 20 | 15 | 15 | 15 | 15 | 15 | 10 / 10 / 10 / 11 |
| Kanada | CA | 25 | 15 | 15 | 15 | 15 | 15 | 10 / 10 / 10 / 11 |
| Korea, Republik | KR | 20 | 15 | 15 | 15 | 15 | 15 | 12 / 12 / 11 / 13 |
| Niederlande | NL | 15 | 15 | 15 | 15 | 15 | 15 | 16 / 16 / 15 / 18 |
| Taiwan | TW | 21 | 10 | 10 | 10 | 10 | 10 | 22 / 22 / 21 / 25 |
| Vereinigte Staaten | US | 0 / 30 | 15 | 15 | 15 | 15 | 15 | 25 / 25 / 24 / 29 |

For the Vereinigte Staaten every edition prints C as *"15, falls keine Befreiung"*, with column E
*"Dividenden: Steuerbefreiung fuer bestimmte Dividenden von regulierten
Kapitalanlagegesellschaften"*; the treaty basis, and the exemption's consequence, are
[GT-CREDIT-027]. The US row applies to a US fund's distribution as well as a share dividend,
because the treaty itself puts RIC dividends on the dividend rate (Art. 10 Abs. 4 Satz 2); for
the other rows only share dividends are within the table's *Dividenden*.

**How column C is derived** (Erlaeuterungen, page 2 in each of the four editions, re-read
2026-09-23): *"Die Ermittlung erfolgte nach folgendem Pruefschema: 1. Wird eine Quellensteuer nach
nationalem Recht erhoben, wenn ja, mit welchem Steuersatz? 2. Wird die Hoehe des unter Nr. 1
ermittelten Quellensteuersatzes durch das DBA begrenzt/abgesenkt? 3. Enthaelt ein DBA eine
Vorschrift ueber die Anrechnung fiktiver Steuern, die ueber dem nach Nr. 2 ermittelten Satz liegt?"*
Step 3 does not arise for the states above (no *fiktive* Quellensteuer). So where the national rate
is below the DBA ceiling (Frankreich), the national rate is what is creditable: the DBA does not
lower it. Where it is above (the others), the DBA ceiling is; the difference is claimed back in the
source state.

**Two national rates in A a)** (Japan *15 / 20*, Vereinigte Staaten *0 / 30*): *"Einige Staaten
kennen Steuerbefreiungen oder verschiedene Steuersaetze"* (Erlaeuterungen, page 2); column E says
which income the lower rate is for -- Japan's 15 for *"qualifizierte Dividenden aus boersennotierten
Gesellschaften"*, the US 0 for the exempt RIC dividends. The comparison with the DBA ceiling is made
with the rate that applies to the dividend in question: for a US dividend that is not exempt, 30
against 15, so 15.

**What the cited unit also contains** (Validation Protocol item 2), none of it relied on here:

- Column D, the creditable **interest** rate, and column B: for Irland at [GT-CREDIT-030] below;
  for every other state not relied on. Which state levied a given interest withholding is a fact
  the table cannot supply.
- Column E, national special rules. For the states above: Japan, *"15 % auf qualifizierte
  Dividenden aus boersennotierten Gesellschaften"* (the 15 of A a)); Kanada and Korea, interest
  exemptions only.
- Column F, DBA special rules. Read per edition by the column's page coordinates, not from the
  flowed text (re-read 2026-09-23; a cell spans several printed lines and the flowed text puts
  parts of it beside the neighbouring rows):
  - Frankreich, all four editions: *"volles Besteuerungsrecht des Quellenstaats auf Einkuenfte aus
    Rechten oder Anteilen mit Gewinnbeteiligung, wenn diese bei der Ermittlung des Gewinns des
    Schuldners abzugsfaehig sind (Art. 9 Abs. 9 DBA)"*.
  - Kanada, all four editions: *"volles Besteuerungsrecht des Quellenstaats auf Einkuenfte aus
    Rechten oder Forderungen mit Gewinnbeteiligung, wenn diese bei der Ermittlung des Gewinns des
    Schuldners abzugsfaehig sind (Protokoll zum DBA, Ziff. 3 zu Artikel 10)"*.
  - Korea, all four editions: *"Besteuerungsrecht des Quellenstaats auf Einkuenfte aus Rechten
    oder Forderungen mit Gewinnbeteiligung bis maximal 25 % des Bruttobetrags der Einkuenfte, wenn
    diese bei der Ermittlung des Gewinns des Schuldners abzugsfaehig sind (Art. 10 Abs. 4 DBA)"*.
  - Niederlande, 2026 edition only: *"volles Besteuerungsrecht des Quellenstaats auf Einkuenfte
    aus Rechten oder Forderungen mit Gewinnbeteiligung, wenn diese bei der Ermittlung der Gewinne
    des Schuldners der Einkuenfte abzugsfaehig sind (Protokoll zum DBA, Ziff. IX zu den Artikeln
    10 und 11)"*. The 2023 to 2025 editions carry none for Niederlande; the text printed beside it
    there belongs to Neuseeland (*"Ziff. 4b"*) and Nordmazedonien.
  - Taiwan, all four editions: the same profit-participation rule (*"Protokoll zum DBA, Ziff. 3
    zu den Artikeln 10 und 11"*), and under *"Zinsen:"* a 15 % rate on distributions of a Real
    Estate Investment Trust or Real Estate Asset Trust (Art. 11 Abs. 4 DBA).
  - Japan: none, in any edition.

  **Scope of these notes.** Each profit-participation note (FR, CA, KR, NL 2026, TW) concerns
  income from rights, shares or claims carrying a profit participation *whose payment the payer
  deducts in computing its profit*. A dividend on an ordinary share of a Kapitalgesellschaft is a
  distribution of profit, not deductible by the company, so it is outside every one of them, and
  column C applies to it. Income within a note is not on the column-C rate: the source state keeps
  its full national tax (FR, CA, NL, TW) or up to 25 % (KR), and this table states no creditable
  rate for it. The TW REIT/REAT rule is likewise outside column C: it applies to a trust's
  distribution, not to a share dividend. Whether a given payment falls under a note is a fact
  about the instrument, not something the table decides.
- The *fiktive* Quellensteuer of columns A/B c): none for the states above.
- Every other source state in the table.

---

## [GT-CREDIT-030] Column D -- the creditable interest rate, Irland

Column B gives, for interest, the source state's national rate (a) and the DBA ceiling (b);
column D the creditable rate (the meaning of the columns is quoted at [GT-CREDIT-029]). Per
edition, as for dividends: a rate holds for the assessment year of its edition only.

| Source state | Code | B a) national | B b) DBA | D 2023 | D 2024 | D 2025 | D 2026 | Pages 2023 / 2024 / 2025 / 2026 |
|---|---|---|---|---|---|---|---|---|
| Irland | IE | 0 / 20 | 0 | 0 | 0 | 0 | 0 | 9 / 9 / 9 / 10 |

Ireland's national law levies up to 20 % on interest (B a)); the DBA leaves it no tax on interest
paid to a German resident (B b) 0). Whatever Ireland withheld is therefore wholly subject to an
Ermaessigungsanspruch and **none of it is creditable** ([GT-CREDIT-026]); it is claimed back in
Ireland. The same values are printed in all four editions, each read separately; for VZ 2023,
2024 and 2025 the following edition shows no change.

**What the row also contains:** column E for Irland concerns dividends only (*"keine
Quellensteuer fuer EU-Buerger und fuer Ansaessige in DBA-Staaten"*, from the 2024 edition on with
*"auf Antrag Vorabbefreiung oder nachtraegliche Erstattung der einbehaltenen Quellensteuer"*);
column F, *"volles Besteuerungsrecht des Quellenstaats auf Dividenden und Zinsen aus Rechten oder
Forderungen mit Gewinnbeteiligung, wenn diese bei der Ermittlung der Gewinne des Schuldners der
Dividenden oder Zinsen abzugsfaehig sind (Protokoll zum DBA, Ziff. 3 zu den Artikeln 10 und 11)"*,
which does not reach interest on a cash balance.

---

## [GT-CREDIT-031] Column C for China -- 0 / 10, and the BMF-Schreiben it refers to

**Sources.**
- The four BZSt editions above, row *China (Volksrepublik ohne Hongkong und Macau)*, page 6 in
  each; read by the columns' page coordinates, 2026-09-23.
- BMF-Schreiben vom 31.03.2022, IV C 1 - S 2283-c/19/10012 :004, DOK 2022/0342138, BStBl I 2022
  S. 328, *"Anrechnung von Quellensteuer, die auf Ausschuettungen von chinesischen Aktien erhoben
  wird, auf die deutsche Kapitalertragsteuer nach § 43a Absatz 3 EStG"*. Tier 2. The BMF no longer
  serves it; retrieved 2026-09-23 as the BMF's own PDF (4 pages; PDF metadata Author
  *Bundesministerium der Finanzen*, created 31.03.2022) from the Internet Archive snapshot of
  20220817044403 of
  https://www.bundesfinanzministerium.de/Content/DE/Downloads/BMF_Schreiben/Steuerarten/Abgeltungsteuer/20220331-anrechnung-von-quellensteuer-die-auf-ausschuettungen-von-chinesischen-aktien-erhoben-wird-auf-die-deutsche-kapitalertragsteuer.pdf?__blob=publicationFile&v=2
- Abkommen vom 28.03.2014 (DBA China), Gesetz vom 22.12.2015, BGBl. 2015 II Nr. 35; retrieved
  2026-09-23 from
  https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/Themen/Steuern/Internationales_Steuerrecht/Staatenbezogene_Informationen/Laender_A_Z/China/2015-12-29-China-Abkommen-DBA-Gesetz.pdf?__blob=publicationFile&v=3
  Tier 1.

**Applicable tax years.** The BMF-Schreiben vom 07.01.2026 on the *Stand der
Doppelbesteuerungsabkommen* (cited at [GT-CREDIT-027]) lists for *China (ohne Hongkong und Macau)*
the treaty of 28.03.2014, applicable from 01.01.2017, and nothing later in force; it adds that the
treaty is *"in Hongkong nicht anwendbar"*, and the same for Macau. Column C reads *0 / 10* in each of
the 2023, 2024, 2025 and 2026 editions, so the claim below holds per edition for those four
assessment years and no other.

- *China (ohne Hongkong und Macau)*, code CN. A a) national: 0 / 10 / 20. A b) DBA: 10.
- Column C, per edition: 2023 **0 / 10**; 2024 **0 / 10**; 2025 **0 / 10**; 2026 **0 / 10**.

Column E, all four editions: *"Dividenden: Zur Anrechnung von Quellensteuer, die auf Ausschuettungen
von chinesischen Aktien erhoben wird, vgl. BMF-Schreiben vom 31. Maerz 2022 (BStBl I S. 328)"*.
Column F: the profit-participation rule of the Protokoll, Ziff. 4 zu den Artikeln 10 und 11, in the
same terms as for the states at [GT-CREDIT-029] and with the same scope.

**The treaty rate. DBA China Art. 10 Abs. 2:** *"Diese Dividenden koennen jedoch auch in dem
Vertragsstaat, in dem die die Dividenden zahlende Gesellschaft ansaessig ist, nach dem Recht dieses
Staates besteuert werden; die Steuer darf aber, wenn der Nutzungsberechtigte der Dividenden eine in
dem anderen Vertragsstaat ansaessige Person ist, nicht uebersteigen: a) 5 Prozent des
Bruttobetrages der Dividenden, wenn der Nutzungsberechtigte eine Gesellschaft (jedoch keine
Personengesellschaft) ist, die unmittelbar ueber mindestens 25 Prozent des Kapitals der die
Dividenden zahlenden Gesellschaft verfuegt; b) 15 Prozent des Bruttobetrags der Dividenden, sofern
diese Dividenden aus Einkuenften oder Ertraegen gezahlt werden, die unmittelbar oder mittelbar aus
unbeweglichem Vermoegen im Sinne des Artikels 6 von einem Investmentvehikel erzielt werden, das diese
Einkuenfte oder Ertraege groesstenteils jaehrlich ausschuettet und dessen Einkuenfte oder Ertraege
aus dem betreffenden unbeweglichen Vermoegen von der Steuer befreit sind; c) 10 Prozent des
Bruttobetrags der Dividenden in allen anderen Faellen."* For a private investor's share dividend the
ceiling is Buchst. c, 10 %; Buchst. a needs a corporate holder, and Buchst. b applies to an
investment vehicle's distribution out of exempt real-property income, with a 15 % ceiling instead.
Art. 10 Abs. 1 and 2 require a paying company *"in einem Vertragsstaat ansaessig"*, that is resident
in the People's Republic under Art. 4.

**What the BMF says decides it.** *"Fuer die Anrechenbarkeit der Quellensteuer ist bei deutschen
Anlegern jedoch allein auf das Abkommen ... (DBA China) abzustellen, sofern es sich um Dividenden von
Unternehmen handelt, die nach Artikel 4 DBA China auf dem chinesischen Festland ansaessig sind."*
The source state's national tax then depends on the share:
- **A-Aktien** (mainland exchanges, Renminbi): *"Dividendenzahlungen an nichtansaessige natuerliche
  Personen aus A-Aktien unterliegen einer abgeltenden Quellensteuer von 20 %. Werden A-Aktien
  zwischen einem Monat und einem Jahr gehalten, wird die Bemessungsgrundlage um 50 % reduziert, so
  dass sich effektiv eine Steuer von 10 % ergibt. Keine Quellensteuer wird erhoben, wenn die
  Haltedauer laenger als ein Jahr betraegt. In Deutschland ist im Fall von Streubesitz nach dem DBA
  China auf Dividenden eine Quellensteuer in Hoehe von 10 % anrechenbar (Artikel 10 Absatz 2 Buchst.
  c) DBA China). Aufgrund der vielen Besonderheiten kann eine Anrechnung im
  Kapitalertragsteuerverfahren nicht erfolgen, da die Voraussetzungen im Einzelfall im Rahmen der
  Veranlagung zu pruefen sind."*
- **B-Aktien** (mainland exchanges, foreign currency): *"Dividendenzahlungen an nichtansaessige
  natuerliche Personen aus B-Aktien unterliegen in China keiner Quellensteuer."*
- **H-Aktien** (Hong Kong): *"unterliegen grundsaetzlich einem Quellensteuersatz von 20 %, unter
  bestimmten Voraussetzungen (in China gegruendete Unternehmen auslaendischer Investoren) sind sie
  steuerfrei. In Faellen, in denen ein mit China abgeschlossenes DBA einen niedrigeren Satz
  vorsieht, kommt dieser zum Tragen."* China withholds a uniform 10 % in practice, often labelled
  *"enterprise income tax"*, and the BMF does not object where, *"unabhaengig von der Bezeichnung"*,
  the 10 % of Art. 10 Abs. 2 Buchst. c is credited in the Abzugsverfahren.
- **D-Aktien** (Frankfurt, CEINEX D-Share market): subject to Chinese withholding; the 10 % of
  Art. 10 Abs. 2 Buchst. c is credited in the Abzugsverfahren.

**What column C's two values mean** (read with [GT-CREDIT-026] and the Pruefschema quoted at
[GT-CREDIT-029]). Where China's own law levies nothing on the dividend -- a B-share, an A-share held
more than a year, an exempt foreign-invested enterprise -- the whole of any tax withheld is an
Ermaessigungsanspruch under national law, and **0** is creditable. Otherwise the DBA limits the tax
to 10 % of the gross and **10** is creditable, whatever the tax is called. Three facts about the
individual dividend therefore decide the credit, and none is a property of the tax row: that the
paying company is resident in mainland China (Art. 4); that it is not an Art. 10 Abs. 2 Buchst. b
investment vehicle (15 % ceiling, outside column C); and that China's national law does not exempt
the dividend.

**What the cited units also contain, not relied on:** DBA China Art. 10 Abs. 3 to 5 (definition,
permanent establishment, no tax on undistributed profits), Art. 23 (the credit article; the BMF
cites Abs. 2 Buchst. b (i)); column D (interest, *"10, falls keine Befreiung"*) and column B; the
Abzugsverfahren rules of the BMF-Schreiben as such, which bind the paying agent.
