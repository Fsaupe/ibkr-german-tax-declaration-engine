"""Shared factual and legal text for the selected short-sale position.

Authority and limits: reference/tax-law/estg-20-leerverkaeufe.md,
GT-ESTG20-071–074. The implementation map records the maintainer's choice.
"""
from src.domain.enums import AssetCategory
from src.reporting.reporting_utils import _q, _q_qty, format_date_german


TITLE = "Abweichende Rechtsauffassung: jahresübergreifende Wertpapier-Leerverkäufe"
NOTICE = "Hinweis: Die Zahlen enthalten die abweichende Leerverkaufs-Position; Anlage am Ende mit einreichen."


def disclosure_paragraphs(tax_year):
    return [
        f"Die erste Tabelle legt die am 31.12.{tax_year} noch offenen Wertpapier-Leerverkäufe "
        "je Depot und Eröffnungslos offen. Für diese offenen Mengen wird ein Beitrag von "
        "0,00 EUR (0 % Ansatz, keine Steuerbefreiung) in den erklärten Einkünften angesetzt. "
        "Die vereinnahmten Netto-Verkaufserlöse werden vollständig daneben ausgewiesen. "
        "Bereits eingedeckte Teilmengen sind hiervon getrennt; ihr tatsächlicher Gewinn oder "
        "Verlust ist im Jahr der Eindeckung enthalten. Die zweite Tabelle zeigt solche "
        "Eindeckungen, soweit sie zu einem offenen Bestand oder zu einem Vorjahres-Leerverkauf gehören.",
        "Beantragt wird, den tatsächlichen Saldo aus Verkaufserlösen und zugehörigen "
        "Eindeckungskosten erst bei Eindeckung anzusetzen. Dafür wird angeführt, dass "
        "§ 20 Abs. 4 Satz 1 EStG den tatsächlichen Unterschiedsbetrag bestimmt und "
        "§ 43a Abs. 2 Satz 7 EStG die Ersatzbemessungsgrundlage von 30 % der "
        "Veräußerungseinnahmen für den Steuerabzug regelt. Eine unmittelbare Pflicht, "
        "diesen Ersatzwert bei einem ausländischen Broker ohne deutschen Steuerabzug "
        "in der Veranlagung anzusetzen, wird daraus nicht abgeleitet.",
        "Diese beantragte zeitliche Zuordnung ist keine gesicherte Rechtslage. Dagegen "
        "sprechen § 11 Abs. 1 Satz 1 und § 32d Abs. 3 Satz 1 EStG sowie BMF vom "
        "14.05.2025, Rn. 196: sofortige Behandlung des Verkaufs als Veräußerung und "
        "nachträgliche Zuordnung der Eindeckungskosten zum vorangehenden Verkauf, auch "
        "bei jahresübergreifender Eindeckung. Die fehlende unmittelbare Anwendung der "
        "Ersatzbemessungsgrundlage begründet für sich allein keinen Anspruch auf einen Nullansatz. "
        "Das Finanzamt wird um ausdrückliche Prüfung und gegebenenfalls abweichende "
        "Festsetzung gebeten. Eine unveränderte Steuerlast über mehrere Jahre wird nicht behauptet.",
        "Die Sachverhalte und die Abweichung werden gemäß § 90 Abs. 1 Satz 2 und "
        "§ 150 Abs. 2, Abs. 7 Satz 1 AO offengelegt. BGH vom 10.11.1999, 5 StR 221/99, "
        "Rn. 22-25 unterscheidet vollständige Tatsachenangaben von einer unzutreffenden "
        "Rechtsauffassung; die Entscheidung bestätigt nicht die beantragte steuerliche "
        "Behandlung von Leerverkäufen. Diese Anlage ist mit der Erklärung einzureichen "
        "und im Feld 'Ergänzende Angaben' als abweichende Rechtsauffassung zu benennen.",
        f"Datenstand dieser Jahresaufstellung: 31.12.{tax_year}. Die Eröffnungsdaten sind "
        "Handelstage, keine gesondert festgestellten Zuflussdaten. Spätere, bei Abgabe "
        "bekannte Eindeckungen oder sonstige Änderungen sind ergänzend offenzulegen; "
        "die erste Tabelle behauptet nicht, dass diese Positionen bei Abgabe noch offen sind. "
        "Bereits erfolgte abweichende Festsetzungen sind vor Verwendung der Zahlen zu "
        "berücksichtigen. Eine spätere Änderung nach § 175 AO wird nicht als automatisch "
        "zulässig vorausgesetzt.",
        "Beträge in EUR: Nettoerlöse nach den zugeordneten Verkaufskosten und gegebenenfalls "
        "Optionsprämienanpassungen; Eindeckungskosten einschließlich zugeordneter Kaufkosten. "
        "Teilmengen verwenden die tatsächliche FIFO-Zuordnung. Währungsumrechnungen folgen "
        "den jeweiligen Handelstagen. Mengen sind positive Beträge der Short-Verpflichtung "
        "zum angegebenen Zeitpunkt; Kapitalmaßnahmen können die Stückzahl verändert haben. "
        "Aktien: KAP Z19 und Z20/Z23; andere Kapitalforderungen: KAP Z19/Z22; "
        "Investmentfonds: KAP-INV mit der jeweiligen Teilfreistellung. "
        "Optionen, Futures, CFDs und Währungssalden sind nicht Gegenstand dieser Anlage.",
    ]


def amount(value):
    return "nicht rekonstruiert" if value is None else str(_q(value)).replace(".", ",")


def quantity(value):
    # Keep fractional units without turning integers into wrapped ten-digit
    # decimal strings in the narrow PDF column.
    text = format(_q_qty(value), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text.replace(".", ",")


def identity(row, assets):
    asset = assets[row.asset_internal_id]
    category = {AssetCategory.STOCK: "Aktien", AssetCategory.BOND: "Anleihen",
                AssetCategory.SONSTIGE_KAPITALFORDERUNG: "Kapitalforderungen",
                AssetCategory.INVESTMENT_FUND: "Investmentfonds"}[asset.asset_category]
    return " / ".join(str(v) for v in (asset.ibkr_symbol, asset.ibkr_isin or asset.ibkr_conid,
                                       category) if v)


def open_table(rows, assets):
    table = [["Depot / Wertpapier", "Eröffnung / Beleg", "Offene Menge",
              "Nettoerlös EUR", "Ansatz EUR"]]
    for row in rows:
        if row.cover_date is not None:
            continue
        table.append([f"{row.account_id}\n{identity(row, assets)}",
                      f"{format_date_german(row.opening_date) if row.opening_date else 'nicht rekonstruiert'}\n{row.source_transaction_id}",
                      quantity(row.quantity), amount(row.net_proceeds_eur), amount(row.declared_gain_eur)])
    return table


def cover_table(rows, assets):
    table = [["Depot / Wertpapier", "Eröffnung / Beleg", "Eindeckung / Beleg",
              "Menge", "Nettoerlös EUR", "Kosten EUR", "Saldo EUR"]]
    for row in rows:
        if row.cover_date is None:
            continue
        table.append([f"{row.account_id}\n{identity(row, assets)}",
                      f"{format_date_german(row.opening_date)}\n{row.source_transaction_id}",
                      f"{format_date_german(row.cover_date)}\n{row.cover_transaction_id or 'ohne Belegnummer'}",
                      quantity(row.quantity), amount(row.net_proceeds_eur), amount(row.cover_cost_eur),
                      amount(row.declared_gain_eur)])
    return table


def print_short_sale_disclosure(rows, assets, tax_year):
    if not rows:
        return
    print(f"\n--- {TITLE} ---")
    for text in disclosure_paragraphs(tax_year):
        print(text)
    for heading, table in ((f"Offene Positionen am 31.12.{tax_year}", open_table(rows, assets)),
                           (f"Eindeckungen im Jahr {tax_year}", cover_table(rows, assets))):
        print(heading)
        if len(table) == 1:
            print("Keine.")
        else:
            for line in table:
                print(" | ".join(cell.replace("\n", "; ") for cell in line))
