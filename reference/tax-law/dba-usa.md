# DBA Deutschland -- USA: dividends and the credit for US tax

The double-taxation treaty between Germany and the United States, for the two questions a foreign
withholding on a US dividend (or a payment in lieu of one) raises: at what rate the United States
may tax the dividend as source state, and how the US tax is credited against the German tax. It is
the treaty that § 32d Abs. 5 Satz 2 EStG folds into the unilateral credit mechanism ([GT-CREDIT-004],
[GT-CREDIT-026]).

## Source

- **Treaty:** Abkommen zwischen der Bundesrepublik Deutschland und den Vereinigten Staaten von
  Amerika zur Vermeidung der Doppelbesteuerung ... vom 29.08.1989 (BGBl. 1991 II S. 354), in der
  Fassung des Protokolls vom 01.06.2006 (BGBl. 2006 II S. 1184). **Neufassung bekannt gemacht am
  04.06.2008, BGBl. 2008 II Nr. 15 S. 611.** Retrieved 2026-09-22 as the BMF Bekanntmachung PDF
  (41 pages, two-column German/English, authentic in both languages; read with `pdftotext -layout`):
  https://www.bundesfinanzministerium.de/Content/DE/Standardartikel/Themen/Steuern/Internationales_Steuerrecht/Staatenbezogene_Informationen/Laender_A_Z/Verein_Staaten/2008-06-23-USA-Abkommen-DBA-Bekanntmachung.pdf?__blob=publicationFile&v=3
  Tier 1 (primary law: a ratified treaty is federal law via the Zustimmungsgesetz).
- **Creditable-rate table:** BZSt, "Anrechenbarkeit der Quellensteuer auf Dividenden und Zinsen ...",
  Stand 1. Januar 2026. Retrieved 2026-09-22:
  https://www.bzst.de/SharedDocs/Downloads/DE/EU_OECD/anrechenbare_ausl_quellensteuer_2026.pdf?__blob=publicationFile&v=2
  Tier 2 (administrative guidance binding the paying agent).

**Applicable tax years.** The 2006 Protokoll is in force for every assessment year in scope (regime
floor VZ 2023). No later protocol has changed the
Article 10 rates or the Article 23 credit method for a privately held portfolio as of the retrieval
date. The rates are not year-parameterised within the window.

---

## [GT-CREDIT-027] Art. 10 -- who may tax a US dividend, and the 15 % ceiling

**Art. 10 Abs. 1:** *"Dividenden, die eine in einem Vertragsstaat ansaessige Gesellschaft an eine im
anderen Vertragsstaat ansaessige Person zahlt, koennen im anderen Staat besteuert werden."*

**Art. 10 Abs. 2:** *"Diese Dividenden koennen jedoch auch in dem Vertragsstaat, in dem die die
Dividenden zahlende Gesellschaft ansaessig ist, nach dem Recht dieses Staates besteuert werden; die
Steuer darf aber, wenn die Dividenden von einer im anderen Vertragsstaat ansaessigen Person als
Nutzungsberechtigtem bezogen werden, nicht uebersteigen: a) 5 vom Hundert des Bruttobetrags der
Dividenden, wenn der Nutzungsberechtigte eine Gesellschaft ist, der unmittelbar mindestens 10 vom
Hundert der stimmberechtigten Anteile der die Dividenden zahlenden Gesellschaft gehoeren; b) 15 vom
Hundert des Bruttobetrags der Dividenden in allen anderen Faellen."*

**The rate for a German private investor is Abs. 2 Buchst. b: 15 % of the gross.** Buchst. a (5 %)
needs a corporate holder with a 10 % voting stake and cannot be reached by a natural person.

**Art. 10 Abs. 4 Saetze 1 und 2:** *"Absatz 2 Buchstabe a und Absatz 3 Buchstabe a sind nicht bei
Dividenden anzuwenden, die von einer Person der Vereinigten Staaten, bei der es sich um eine
Regulated Investment Company (RIC) der Vereinigten Staaten oder einen Real Estate Investment Trust
(REIT) der Vereinigten Staaten handelt, oder von einem deutschen Investmentfonds oder einer
deutschen Investmentaktiengesellschaft ... gezahlt werden. Im Fall von Dividenden, die von einer RIC
oder einem Investmentvermoegen gezahlt werden, sind Absatz 2 Buchstabe b und Absatz 3 Buchstabe b
anzuwenden."* So a dividend from a US RIC is expressly put on the 15 % rate of Abs. 2 b; the RIC
status of the payer neither raises nor lowers the rate for a private investor.

**Art. 10 Abs. 5** (Dividendenbegriff): *"Der in diesem Artikel verwendete Ausdruck ,Dividenden'
bedeutet Einkuenfte aus Aktien ... sowie aus sonstigen Rechten stammende andere Einkuenfte, die nach
dem Recht des Vertragsstaats, in dem die ausschuettende Gesellschaft ansaessig ist, den Einkuenften
aus Aktien steuerlich gleichgestellt sind. ..."* English text: *"... as well as other income from
other rights that is subjected to the same taxation treatment as income from shares by the laws of
the Contracting State of which the company making the distribution is a resident."* The definition
therefore **defers to the source state's law** for whether a payment other than an ordinary share
dividend is a dividend for the treaty.

**What the cited unit also contains** (Validation Protocol item 2): Abs. 3 (0 % for qualifying
corporate holders and pension funds); Abs. 4 Saetze 3 ff. (REIT conditions); Abs. 6 (contingent
interest re-characterised as interest); Abs. 7 ff. (permanent establishment, branch tax). None
reaches a directly held private portfolio and none is relied on here.

### The source-state-law fact Abs. 5 points at (foreign law, cited for a fact only)

Abs. 5 makes the dividend character of a substitute payment turn on *"dem Recht des Vertragsstaats,
in dem die ausschuettende Gesellschaft ansaessig ist"* -- here, US law. This fact is **not German
ground truth and is not law of this store**; it is quoted only because a German provision expressly
sends the reader to it, and because the Ermaessigungsanspruch of [GT-CREDIT-026] is measured by the
source state's law. Retrieved 2026-09-22 via law.cornell.edu (eCFR mirror):

- **26 CFR § 1.871-7(b)(2):** a substitute dividend payment received by a foreign person under a
  securities-lending or sale-repurchase transaction *"shall have the same character as a
  distribution received with respect to the transferred security"*.
- **26 CFR § 1.894-1(c)(1):** the treaty provisions on dividends *"include substitute ... dividend
  payments that have the same character as ... dividends under § 1.864-5(b)(2)(ii), 1.871-7(b)(2) or
  1.881-2(b)(2)."*

Under US law a payment in lieu on a US share or RIC unit is therefore taxed as the dividend it
replaces: the US applies Art. 10 to it, withholds 15 % on a valid W-8BEN, and grants no refund below
15 %.

**Independent confirmation of the 15 % result (Tier 2).** BZSt table, Stand 1.1.2026, row
*Vereinigte Staaten*, Dividenden: national 0/30, nach DBA hoechstens 15, Ergebnis anrechenbar **15**,
*"falls keine Befreiung"*; Hinweis column verbatim *"Dividenden: Steuerbefreiung fuer bestimmte
Dividenden von regulierten Kapitalanlagegesellschaften"*. An exempt RIC dividend carries no tax and
produces no withholding, so the qualification changes nothing that reaches a withholding figure.
Zinsen: anrechenbar 0.

---

## [GT-CREDIT-028] Art. 23 and Art. 21 -- the credit for US tax, and the character of a substitute payment

**Art. 23 Abs. 3 Buchst. b, Doppelbuchst. aa:** *"Auf die deutsche Steuer vom Einkommen wird unter
Beachtung der Vorschriften des deutschen Steuerrechts ueber die Anrechnung auslaendischer Steuern die
Steuer der Vereinigten Staaten angerechnet, die nach dem Recht der Vereinigten Staaten und in
Uebereinstimmung mit diesem Abkommen von den nachstehenden Einkuenften gezahlt wurde: aa) Einkuenfte
aus Dividenden im Sinne des Artikels 10 ..., auf die Buchstabe a nicht anzuwenden ist; ..."*

**Art. 21 Abs. 1** (Andere Einkuenfte): *"Einkuenfte einer in einem Vertragsstaat ansaessigen Person,
die in den vorstehenden Artikeln nicht behandelt wurden, koennen ohne Ruecksicht auf ihre Herkunft
nur in diesem Staat besteuert werden."*

**What the cited units also contain:** Art. 23 Abs. 3 Buchst. a is the Freistellung for corporate
Schachteldividenden and excludes RIC and REIT dividends; Art. 21 Abs. 2 is the permanent-establishment
exception. Neither reaches a directly held private portfolio.

### The character of a payment in lieu (substitute dividend) under the treaty

No located Tier 1 or Tier 2 source names the treaty character of a Dividendenersatzleistung received
by a German private lender; a BFH search on the point returned only the § 39 AO attribution line
(I R 88/13, I R 40/17, I R 22/20), nothing on treaty qualification. Two readings exist, and which
applies follows the § 39 AO attribution decided at [GT-INVSTG-059] / [GT-ESTG20-042] ff.:

- **Reading A (Art. 10), on branch A** -- attribution stayed with the lender. What the lender
  receives is, for German tax, the company's dividend reaching its Nutzungsberechtigten
  ([GT-ESTG20-045], Rz. 12). Art. 10 Abs. 1's condition -- a payment by a company of one state to a
  resident of the other -- is met; and Art. 10 Abs. 5 independently brings in *"andere Einkuenfte,
  die nach dem Recht des [Quellenstaats] den Einkuenften aus Aktien steuerlich gleichgestellt sind"*,
  which US law does in terms (above). The administration's own framework for the mirror-image case
  (Germany as source state) makes Art. 10 turn on exactly that condition: BMF-Antwort vom 06.10.2025
  an den Wissenschaftlichen Beirat, GZ I A 1 - Vw 3160/00134/002/001, quoted with page references by
  the Wissenschaftliche Dienste des Deutschen Bundestages, WD 4 - 3000 - 062/25, "Cum/Cum-
  Steuergestaltungen" (Abschluss 04.02.2026), pages 22-23,
  https://www.bundestag.de/resource/blob/1151946/WD-4-062-25.pdf (second-hand, and marked so; the
  quoting document is an official Bundestag publication): *"... besitzt Deutschland ... als
  Quellenstaat nur dann einen Besteuerungsanspruch hinsichtlich der Wertpapierleihgebuehren und
  sonstigen Dividendenersatzleistungen, wenn diese Leistungen unter den Dividendenbegriff des
  jeweiligen DBA fallen. Andernfalls handelt es sich um ,andere Einkuenfte', fuer die das
  Besteuerungsrecht nach Art. 21 Abs. 1 OECD-MA ... ausschliesslich bei dem Staat [liegt], in dem der
  Leistungsempfaenger ansaessig ist."*
- **Reading B (Art. 21), on branch B** -- attribution passed to the borrower. The payer is the
  borrower, not *"die ausschuettende Gesellschaft"*, so Art. 10 Abs. 1 fails and the Abs. 5 residual
  clause does not cure it; Art. 21 Abs. 1 gives Germany the exclusive right and the US tax is then not
  paid *"in Uebereinstimmung mit diesem Abkommen"* for Art. 23 Abs. 3 b.

**Why the creditable amount is 15 % under either reading, and this is therefore not an open
question.** The German credit is § 32d Abs. 5 Satz 1, a unilateral credit reduced only by an
*entstandenen Ermaessigungsanspruch* ([GT-CREDIT-026]); Satz 2 applies Satz 1 *entsprechend* in
treaty cases rather than substituting a treaty-conformity test, and § 32d Abs. 5 has **no counterpart
to § 34c Abs. 6 Satz 3**, the sentence that would remove treaty-nonconforming tax from the credit
base ([GT-CREDIT-026]). The Ermaessigungsanspruch is measured by the source state's law, and the US
refunds nothing below 15 %. So on both readings, and on both attribution branches, the creditable
amount is 15 % of the gross. The readings would diverge only if a Finanzamt constructed an abstract,
German-side treaty entitlement as the Ermaessigungsanspruch and referred the taxpayer to a
Verstaendigungsverfahren under Art. 25; no located source does that for § 32d Abs. 5. Because no
declared figure depends on the choice, it is recorded here with both readings rather than as a point
in `open-legal-questions.md` (Validation Protocol item 7: a point that must be answered either way is
an open question; this one need not be answered to produce the figure).

**Residual risk, stated.** The invariance argument rests on an argument from silence in § 32d Abs. 5
and on the administration measuring the Ermaessigungsanspruch by the source state's law (Rn. 207a,
[GT-CREDIT-026]), not on a source naming this case. If a Finanzamt takes the abstract view, the 15 %
on a branch-B payment could be denied. That is a position the Finanzamt can assess differently, which
is the normal working of the process; it is not the "lean to the taxpayer" case, because no Tier 1 or
Tier 2 source stands against the 15 %.
