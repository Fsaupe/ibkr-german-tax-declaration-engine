# Issue #79 — annual Anlage SO allocation lines

**Completed 2026-09-23:** the maintainer accepted the reported result and
instructed merge and issue closure. Merged and pushed as **`8686b05`**;
GitHub confirmed that main's tree exactly matches accepted candidate `4e5e736`
(`d929c47547784c3648aa4a1e1d595e68a612375c`). Issue #79 is
**CLOSED/COMPLETED**, confirmed at **11:00:42 UTC**. No implementation
question or new deferred work remains for this issue.

Implementation prepared on 2026-09-23. Category: **fix-func**.
Branch: `fix-func-79-so-form-lines`, based on refreshed GitHub main
`282ac4f`. Implementation: **`fbd0def`**. Store-first commits:
`6ddd72d` and `5722770`. The verification below preceded the authorized merge.

The isolated checkout is `/private/tmp/issue79.Jq6X4e/work`.
The original issue #76 workspace and its unrelated edits are preserved.

## Requirement and result

[GT-FORM-020](../../reference/tax-forms/anlage-so-zeilen.md) now records
independent readings of the official FMS sheets for VZ 2023/2024/2025,
including all requested private-sale sub-lines. Contrary to the old unsourced
table, both dates share a line. The individual disposal result is Z53/Z53/Z57;
the taxpayer allocation destination is **Z54/Z54/Z58**. The additional-disposal
schedule remains a separate Z55/Z55/Z59. This fix preserves the existing
allocation convention and changes its annual label; it does not redistribute
disposals between the calculation and additional-schedule fields.

The engine emits `ANLAGE_SO_NET_GV`. Console, PDF summary and PDF detail subtotal
resolve its destination through the year-specific registry. All three display
Z58 in VZ 2025. Existing report tests also call VZ 2021/2022, so their official
two-page forms were independently checked: Z48 in both years. No real-data
assessment before VZ 2023 was run. Pre-2021 mappings are refused; an unverified
future carry is identified in log, console and PDF.

The maintainer explicitly approved updating affected tests alongside code.
Existing fixture keys, their schema and documentation were renamed without
altering expected monetary values.

## Legal validation protocol

1. Tier 1 basis: §22 Nr.2, §23 Abs.1 Satz1 Nr.2 Satz1 and Abs.3 Satz1 EStG;
   Tier 3 official forms establish the annual layout.
2. Exact labels, transfer destinations and sheet identifiers are transcribed;
   neighbouring calculation and additional-schedule lines are distinguished.
3. This is an annual form-layout change, not a statutory amendment.
4. Each annual sheet was read separately; no backward projection.
5. Each annual mapping identifies its individual FMS URL and print identifier.
6. Allocation-source floor VZ 2021; real-data validation floor remains VZ 2023.
7. No new disputed legal position or taxpayer election.
8. GT-FORM-020 and GT-ESTG23-012 map rows, reference index, coverage matrix,
   active specifications and fixtures are aligned.
9. Reference text contains legal requirements, not implementation state;
   all 33 reference-purity checks pass.

## Verification

- New regression file against the old implementation: **30 failed, 4 passed**,
  after correcting an initial fixture enum typo. Failures establish the stale
  key/label behavior and missing annual lookup. Fixed result: **34 passed**.
- Focused engine/report/year compatibility tests: **133 passed**.
- Full suite in the fresh isolated worktree, template `config.py`, no private
  input/cache state: **1,633 passed, 1 skipped**. The skip requires exports.
  The tested application/test source is exactly `fbd0def`.
- Real-data baseline and candidate each ran twice for **VZ 2023, 2024, 2025**,
  with copied inputs/configuration/caches. Same-tree console/log/PDF-text
  controls pass. Original input/configuration/cache hashes remain unchanged.
- **VZ 2023/2024:** normalized console byte identity and metadata-stripped
  PDF byte identity.
- **VZ 2025:** exactly one console label and two PDF labels change 54 → 58.
  PDF text is otherwise identical, including order. Every declaration amount
  and all captured realization/trade records match in all three years.
- Actual VZ 2025 PDF summary (page 2) and detail subtotal (page 147) visually
  inspected: updated labels are readable without clipping or overlap.
- The figure still depends on the existing taxable §23 flag and EUR gains;
  arithmetic and input handling are unchanged. Captured private-sale gain
  records contain **0 missing gains out of 23 / 424 / 465 records** for
  VZ 2023/2024/2025. The new mapping input is the explicitly supplied tax year;
  all twelve real-data invocations supply it. No missing-input substitution
  was introduced.
- Old production key and old fixture field: **0 remaining uses**. The one
  remaining old-key literal is a regression assertion requiring its absence.
  Year-qualified Z54 statements remain valid; the old legal-validation report
  is already explicitly marked historical and superseded.
- Added lines were checked against account identifiers and monetary columns
  in the original exports: **0 account identifiers, 0 new monetary-token
  collisions**. Numerically unchanged fixture-renaming lines retain their
  pre-existing invented expectations. Whitespace checks pass.

Private captures remain outside the repository, under
`/private/tmp/ibkr-issue85-20260922/private/issue79-base` and
`issue79-candidate`; comparison and visual-check scripts are under
`/private/tmp/issue79.Jq6X4e`. Public records contain no account amounts.
