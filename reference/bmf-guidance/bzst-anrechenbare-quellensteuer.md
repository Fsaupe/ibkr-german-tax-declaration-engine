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

**Applicable tax years.** Each edition gives *"die Rechtslage zum 1. Januar"* of its year (2025
edition, Erlaeuterungen, page 1). The rows quoted below carry the same values in all four
editions, so they hold for VZ 2023, VZ 2024 and VZ 2025 without a change inside the window. The
Erlaeuterungen add that paying agents need not apply a change against the previous year's edition
before 1 July (Rn. 208a of the BMF-Schreiben vom 14.05.2025); that is a Nichtbeanstandung for the
Steuerabzug, not for the Veranlagung, and no quoted value changed in any case.

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

**The rows** (dividends; column A a) national rate, A b) DBA ceiling, C creditable). Identical in
the 2023, 2024, 2025 and 2026 editions; page numbers 2023 / 2024 / 2025 / 2026:

| Source state | A a) national | A b) DBA | **C anrechenbar** | Pages |
|---|---|---|---|---|
| Frankreich | 12,8 | 15 | **12,8** | 8 / 8 / 7 / 8 |
| Japan | 15 / 20 | 15 | **15** | 10 / 10 / 10 / 11 |
| Kanada | 25 | 15 | **15** | 10 / 10 / 10 / 11 |
| Korea, Republik | 20 | 15 | **15** | 12 / 12 / 11 / 13 |
| Niederlande | 15 | 15 | **15** | 16 / 16 / 15 / 18 |
| Taiwan | 21 | 10 | **10** | 22 / 22 / 21 / 25 |
| Vereinigte Staaten | 0 / 30 | 15 | **15** *falls keine Befreiung* | quoted at [GT-CREDIT-027] |

Where the national rate is below the DBA ceiling (Frankreich), the national rate is what is
creditable: the source state's own law already grants the reduction down to it. Where it is above
(the others), the DBA ceiling is; the difference is claimed back in the source state.

**What the cited unit also contains** (Validation Protocol item 2), none of it relied on here:

- Column D, the creditable **interest** rate for each state, and column B. Which state levied a
  given interest withholding is a fact the table cannot supply.
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
