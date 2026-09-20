# src/parsers/grants_parser.py
from typing import List

from src.domain.exceptions import DataIntegrityError

from .csv_reader import parse_records
from .raw_models import RawGrantRecord
from .column_validator import GRANTS_COLUMNS

# **The engine supports exactly one share-award programme: Interactive Brokers'
# "Refer-A-Friend" award.** Everything the engine does with a grant row -- § 22 Nr. 3 as
# the income category, Zufluss on the lapse of the transfer restriction, that day's value
# as the Anschaffungskosten, a return before it as no tax event -- is established in
# reference/tax-law/estg-22-nr3-leistungen.md by applying the law to THAT programme's
# terms ([GT-ESTG20-063] to [GT-ESTG20-067]). Another programme's terms may give another
# result: a premium conditioned on buying securities, for one, is a cost reduction and no
# income at all (BMF 14.05.2025 Rz. 129b para 2).
#
# These are the three activity descriptions that programme writes, matched WHOLE. A row
# that merely contains one of them belongs to something nobody has read the terms of, and
# stops the run.
#
# **The export does not name the programme**, so a different programme that wrote these
# identical strings could not be told apart here. That the rows came under Refer-A-Friend
# is therefore a fact the user states once, as config.STOCK_AWARD_PROGRAMME; with rows
# present and no such confirmation `ParsingOrchestrator` stops the run.
SUPPORTED_STOCK_AWARD_PROGRAMME = "IBKR_REFER_A_FRIEND"

AWARD_ACTIVITY = "Stock Award Grant for Cash Deposit"
REVERSAL_ACTIVITY = "Stock Award Return for Cash Withdrawal"
VESTING_ACTIVITY = "Stock Award Vesting"

KNOWN_ACTIVITIES = (AWARD_ACTIVITY, REVERSAL_ACTIVITY, VESTING_ACTIVITY)


def parse_grants_csv(file_path: str, encoding='utf-8-sig') -> List[RawGrantRecord]:
    """Parse the IBKR Stock Grant Activity export -- shares awarded for placing capital.

    Read strictly, with no `allow_extra`, for the reason `parse_transfers_csv` gives: no
    code path read this export until an award had to reach the ledger, so nothing has yet
    established which shapes of it occur.

    An empty file is ordinary input -- a person whose broker has never awarded them
    shares has no rows -- and absence reads as "nothing was awarded".

    **An unrecognised `ActivityDescription` stops the run.** The alternative is to ignore
    the row, and ignoring is what makes a new activity kind invisible: two of the three
    known kinds move the position and one does not, so a kind nobody has classified is as
    likely to move it as not. A run that silently dropped one would reconcile against the
    broker's snapshot until the year the dropped kind mattered, and then produce a wrong
    cost basis rather than a failure. Every offending row is collected before raising, so
    one run names the whole problem.
    """
    records = parse_records(file_path, RawGrantRecord, GRANTS_COLUMNS,
                            "Grants", encoding=encoding)

    unknown = [
        r for r in records
        if r.activity_description.strip() not in KNOWN_ACTIVITIES
    ]
    if unknown:
        seen = sorted({r.activity_description for r in unknown})
        raise DataIntegrityError(
            f"{len(unknown)} row(s) of the Grants export carry an activity kind this "
            f"engine does not classify: {seen}. The only share-award programme supported "
            f"is Interactive Brokers' Refer-A-Friend award, which writes exactly "
            f"{list(KNOWN_ACTIVITIES)}. Shares granted under any other programme may be "
            f"taxed differently -- category, date of receipt and cost basis all follow "
            f"from the programme's terms -- so they are refused rather than treated "
            f"alike. The supported case and its grounds are in "
            f"reference/tax-law/estg-22-nr3-leistungen.md ([GT-ESTG20-063])."
        )

    return records
