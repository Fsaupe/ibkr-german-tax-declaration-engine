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
- Column F, DBA special rules: for Frankreich, *"volles Besteuerungsrecht des Quellenstaats auf
  Einkuenfte aus Rechten oder Anteilen mit Gewinnbeteiligung, wenn diese bei der Ermittlung des
  Gewinns des Schuldners abzugsfaehig sind (Art. 9 Abs. 9 DBA)"*; for Taiwan, under *"Zinsen:"*, a
  15 % rate on distributions of a Real Estate Investment Trust or Real Estate Asset Trust
  (Art. 11 Abs. 4 DBA). Japan, Kanada, Korea and Niederlande carry none. Neither note reaches an
  ordinary share dividend. (In the text extraction, column-F text printed next to Niederlande and
  after Taiwan belongs to Nordmazedonien and Thailand, the neighbouring rows.)
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
