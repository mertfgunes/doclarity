from datetime import date
from decimal import Decimal, InvalidOperation

# ISO 4217 currency codes. Not exhaustive of every historical/regional code,
# but covers what a normal invoice extraction should ever produce.
ISO_4217_CODES = {
    "AED", "AFN", "ALL", "AMD", "ANG", "AOA", "ARS", "AUD", "AWG", "AZN",
    "BAM", "BBD", "BDT", "BGN", "BHD", "BIF", "BMD", "BND", "BOB", "BRL",
    "BSD", "BTN", "BWP", "BYN", "BZD", "CAD", "CDF", "CHF", "CLP", "CNY",
    "COP", "CRC", "CUP", "CVE", "CZK", "DJF", "DKK", "DOP", "DZD", "EGP",
    "ERN", "ETB", "EUR", "FJD", "FKP", "GBP", "GEL", "GHS", "GIP", "GMD",
    "GNF", "GTQ", "GYD", "HKD", "HNL", "HRK", "HTG", "HUF", "IDR", "ILS",
    "INR", "IQD", "IRR", "ISK", "JMD", "JOD", "JPY", "KES", "KGS", "KHR",
    "KMF", "KPW", "KRW", "KWD", "KYD", "KZT", "LAK", "LBP", "LKR", "LRD",
    "LSL", "LYD", "MAD", "MDL", "MGA", "MKD", "MMK", "MNT", "MOP", "MRU",
    "MUR", "MVR", "MWK", "MXN", "MYR", "MZN", "NAD", "NGN", "NIO", "NOK",
    "NPR", "NZD", "OMR", "PAB", "PEN", "PGK", "PHP", "PKR", "PLN", "PYG",
    "QAR", "RON", "RSD", "RUB", "RWF", "SAR", "SBD", "SCR", "SDG", "SEK",
    "SGD", "SHP", "SLE", "SOS", "SRD", "SSP", "STN", "SYP", "SZL", "THB",
    "TJS", "TMT", "TND", "TOP", "TRY", "TTD", "TWD", "TZS", "UAH", "UGX",
    "USD", "UYU", "UZS", "VES", "VND", "VUV", "WST", "XAF", "XCD", "XOF",
    "XPF", "YER", "ZAR", "ZMW", "ZWL",
}

LINE_ITEMS_TOTAL_TOLERANCE = Decimal("0.02")


def validate_extraction(
    total_amount: Decimal | None,
    currency: str | None,
    invoice_date: date | None,
    due_date: date | None,
    line_items: list[dict] | None,
    document_type: str = "invoice",
) -> list[str]:
    """Sanity-check an LLM extraction. Returns a list of human-readable flags;
    an empty list means nothing looked suspicious.

    The canonical columns (total_amount, currency, ...) are invoice-shaped,
    so a missing total_amount is only suspicious for document_type="invoice" -
    contracts and unknown documents don't have one to extract.
    """
    flags: list[str] = []

    if currency and currency.upper() not in ISO_4217_CODES:
        flags.append(f"Unrecognized currency code: {currency!r}")

    if invoice_date and due_date and due_date < invoice_date:
        flags.append("Due date is before invoice date")

    if total_amount is not None and total_amount < 0:
        flags.append("Total amount is negative")

    if line_items:
        line_items_sum = Decimal("0")
        has_amounts = False
        for item in line_items:
            amount = item.get("amount")
            if amount is None:
                continue
            try:
                line_items_sum += Decimal(str(amount))
                has_amounts = True
            except InvalidOperation:
                flags.append(f"Line item has a non-numeric amount: {amount!r}")

        if has_amounts and total_amount is not None:
            if abs(line_items_sum - total_amount) > LINE_ITEMS_TOTAL_TOLERANCE * max(total_amount, Decimal("1")):
                flags.append(
                    f"Line items sum to {line_items_sum} but total_amount is {total_amount}"
                )

    if total_amount is None and document_type == "invoice":
        flags.append("No total_amount extracted")

    return flags
