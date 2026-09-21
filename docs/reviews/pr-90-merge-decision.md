# PR #90 — award-date acceptance decision

2026-09-21. Category: `fix-func`. The maintainer explicitly requested acceptance
and merge of the existing award-date version, with the decision and reasoning
documented. This supersedes the 2026-09-20 vesting instruction; it does not
relabel that earlier instruction as approval of award-date treatment.

## Decision and implementation

Use award-date receipt/acquisition for the supported IBKR Refer-A-Friend
programme. The maintainer reports actual shares booked into the account, rather
than RSUs or future-delivery claims, and ordinary dividends received rather
than payments in lieu. Those facts support the booking rule and the grounds
at GT-ESTG20-064. The recorded research has not established a sufficiently
strong programme-specific case requiring vesting-date receipt. Lower complexity
supports the selected model but does not substitute for legal reasoning.

The knowledge store retains the German rule, both applications and their
limits. BMF 01.06.2024 Rn. 25–26 and BFH VI R 37/09 Rn. 12, 15, 17, 20
distinguish an obligatory holding restriction from legal impossibility of
disposal. The contract's “void” wording is a counterargument; its proprietary
effect was not conclusively established. Ordinary dividends corroborate
ownership but are not conclusive alone. No claim of a programme-specific
German ruling or absence of negligence is made. Q17 remains open as a legal
application question; the selected position and approval live in the
GT-ESTG20-064 implementation-map row, in accordance with the store's purity rule.

Fsaupe's `121a176fa136c8dc51ca5c7845ee46b119b6c745` supplies the existing
implementation and its tests: award-date value/FX and basis, inert vesting,
and returns at original value in the return year. The correction is additive
on live head `4998842bb9ccd2a0dd8923fa2da201312c8775fd`, preserving history.
Reference commit `8755b1d` precedes the restored behavior. The only new runtime
behavior beyond `121a176` is a single position disclosure for imported grant
history, rendered in console and PDF, including historical awards. Attribution
and input-contract prose are corrected. Receipt and return amounts remain
explicit manual Anlage SO entries pending issue #76.

The former vesting-specific missing-release and price-date findings do not
apply to an implementation that does not use vesting to determine receipt or
basis. They are not disguised as fixes to the vesting implementation.

## Verification

- Full suite in the isolated candidate, template configuration and no private
  data/cache: **1,432 passed, 1 skipped**. Dependencies unchanged from the
  previously verified candidate; reused the same Python environment.
- Then copied maintainer exports: **10 raw-model/schema tests passed**.
- Original saved acceptance probes: **5 failed on `4998842`, 5 passed on the
  restored award-date candidate**. Three distinguish missing award/return
  receipts; two distinguish positive award-price validation from the vesting
  model's later disposal refusal. All use invented figures.
- New current/historical position-disclosure tests: **2 failed before the
  disclosure, 2 passed afterward**, checking both console and actual PDF text.
  The rendered affected PDF page was visually inspected: legible, no clipping.
- Fresh VZ **2023, 2024, 2025**: all complete; console reports and PDFs with
  volatile metadata stripped are byte-identical to the accepted-main tree
  (`3312971`, merged as `7d27755`) captured on the same date. Fresh same-tree
  controls are identical. Yesterday's PDFs differed only in the printed report
  date; fresh baselines resolve that comparison artifact.
- Original exports are byte-identical to the retained input seed. The maintainer
  has no Grants or Transfers files, so these runs establish compatibility;
  synthetic scenarios establish award, return, FX, basis and historical behavior.
- No new deferred work is accepted or closed by this decision. The existing
  issue #76 manual-entry limitation and prior unrelated follow-up remain.
- Restored award-lot and scenario tests are byte-identical to `121a176`.
  Searches across source, tests, README, input specification, reference and map
  for the former approved-vesting/2026-09-20 award-approval assertions found
  **zero remaining hits**. `git diff --check` passes. Added lines since
  `4998842` checked against private export account IDs and monetary values
  of magnitude at least 1,000: **zero matches**.

## Knowledge-store validation

All nine protocol items were applied to the changed timing/application text:

1. Tier 1: § 11 Abs. 1 Satz 1 and § 8 Abs. 1 Satz 1/Abs. 2 Satz 1 EStG;
   Tier 2: BMF Rn. 25–26. BFH supports interpretation, not the sole authority.
2. Exact sentences/Randnummern and the additional scope of the cited units
   remain recorded at GT-ESTG20-064.
3. No new year rule; the existing § 19a amendment and its limited a-contrario
   use remain identified.
4. No form-line mapping changed or new line asserted.
5. Source provenance and retrieval dates are retained; no new rate or threshold.
6. Applicable years and the programme-version limits are explicit.
7. Q17 preserves both applications; the map records the authorized choice and
   factual reasons, not a claimed resolution by a court.
8. Reference/index/coverage, affected map rows, code, tests and user-facing
   documentation were converted together; historical validation entries remain
   labeled as history.
9. `reference/` contains the legal analysis; approval and implementation state
   are in the map and this record. Reference-purity tests pass.

The existing source record and passages were read; no fresh claim of live legal
source retrieval is made. The 2026-09-21 factual clarification and acceptance
instruction supply the decision, not an invented missing transaction value.
