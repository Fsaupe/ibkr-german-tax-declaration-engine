# src/reporting/form_rules.py
"""Compatibility shim: the year-specific Anlage KAP form rules
live in the law-as-data registry. Import from src.tax_law.registry directly
in new code; this module keeps existing import paths working."""
from src.tax_law.registry import (  # noqa: F401
    FormYearRules,
    form_rules_are_carried,
    get_form_rules,
    resolved_form_year,
    unverified_form_rules_source,
)
