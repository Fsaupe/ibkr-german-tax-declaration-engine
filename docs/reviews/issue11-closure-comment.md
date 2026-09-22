The researched, explicitly selected approach is now implemented and merged. We retain recognition of the actual net result on covering, and replace the generic disclaimer with a conditional, detailed annex in both console and PDF tax reports.

### Why we do not automatically use a 30% base

[§ 43a Abs. 2 Satz 7 EStG](https://www.gesetze-im-internet.de/estg/__43a.html) specifies **30% of disposal receipts as the withholding base** when acquisition data are not demonstrated: “bemisst sich der Steuerabzug nach 30 Prozent der Einnahmen”. It is neither a 30% tax rate nor 30% of the year-end market value.

[§ 44 Abs. 1 Satz 3 and Satz 4 Nr. 1 Buchst. a EStG](https://www.gesetze-im-internet.de/estg/__44.html) assigns the relevant securities-sale withholding to the domestic paying institution. Our research established the substitute for this withholding procedure, including domestic bank/broker handling under BMF Rn. 196. It **did not establish a direct requirement to apply the same substitute in an individual taxpayer's assessment of foreign-broker transactions that bore no German withholding**.

This is a distinction between withholding and assessment, not a personal exemption: § 44 Abs. 1 Satz 1 still makes the investor the tax debtor. The relevant domestic establishment matters, not the broker's brand. [§ 32d Abs. 3 Satz 1 EStG](https://www.gesetze-im-internet.de/estg/__32d.html) requires declaration of income without withholding but does not import the substitute formula. Abs. 4 addresses review of income that did bear withholding.

### The implemented treatment and disclosure

- Open securities-short quantities contribute **€0 until covering**, without adding a 30% substitute to Z19 and related KAP fields. Fund units retain their separate KAP-INV routing. Zero is the requested contribution to taxable income, **not a statement that no proceeds were received**.
- The annex lists all year-end open lots by account and instrument, with opening dates/source references, quantities, allocated net sale proceeds and the zero contribution. Relevant covers show their dates, quantities, costs and actual results. Partial covers and unchanged holdings carried from previous years are included.
- It appears only for relevant cross-year positions: still open at the current year-end or opened in a previous year and covered in the current year. Ordinary same-year round trips alone do not trigger it. Options, futures, CFDs and currency-short exposure are outside this securities annex.
- The report states the deviating view, asks the Finanzamt to examine it, and instructs the filer to submit the annex and flag **Ergänzende Angaben**. Its inventory is expressly dated at year-end: later covers known when filing must be added, and any different treatment already assessed must be reconciled.

### Legal argument and limits

The argument for the requested treatment is the **actual-gain calculation under § 20 Abs. 4 Satz 1 EStG**, together with the absence of an established direct requirement to import the withholding substitute into this assessment. This does not establish an entitlement to zero or to deferral. The report also presents the contrary argument: **§ 11 Abs. 1 Satz 1 and § 32d Abs. 3 Satz 1 EStG**, and **BMF 14.05.2025, Rn. 196's immediate disposal treatment and subsequent attribution of covering costs to the preceding sale**, including cross-year covers. Original-year attribution remains the stronger reading found in the research.

The basis for transparently presenting the disagreement is §§ 90 Abs. 1 Satz 2 and 150 Abs. 2/Abs. 7 Satz 1 AO, alongside [BGH 10.11.1999, 5 StR 221/99, Rn. 22–25](https://www.hrr-strafrecht.de/5/99/5-221-99.php). It distinguishes an incorrect legal interpretation from incorrect or incomplete factual information under § 370 Abs. 1 Nr. 1 AO, where complete facts enable correct assessment under another interpretation. It does not decide short-sale timing or guarantee acceptance of the zero contribution.

We no longer claim that moving income between years necessarily leaves total tax unchanged, or that later amendment under § 175 AO is automatic. **Q22 remains an unresolved legal amount question.** Closing #11 records the implemented, fully disclosed project policy; it does not claim that the originally requested original-year attribution has been implemented or that the Finanzamt must accept our position.

Verification: **1,572 tests passed, 1 skipped**, with 14 focused disclosure checks. VZ 2023–2025 declared figures remain unchanged; all year-end short quantities match the broker snapshots. The added PDF annexes were rendered and visually checked.

[Implementation and verification](https://github.com/uebber/ibkr-german-tax-declaration-engine/blob/main/docs/reviews/issue11-disclosed-position.md) · [Authorities and scope](https://github.com/uebber/ibkr-german-tax-declaration-engine/blob/main/reference/tax-law/estg-20-leerverkaeufe.md).
