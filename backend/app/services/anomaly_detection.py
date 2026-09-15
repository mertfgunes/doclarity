from typing import NamedTuple


class VendorBaseline(NamedTuple):
    mean: float
    stddev: float
    invoice_count: int


def detect_anomalies(
    invoices: list[dict],
    baselines: dict[str, VendorBaseline],
    z_threshold: float,
) -> list[dict]:
    """Flag invoices whose total_amount deviates from their own vendor's mean
    by at least `z_threshold` standard deviations, sorted most-anomalous first.

    Each `invoices` dict is passed through unchanged, plus the vendor's
    mean/stddev/invoice_count and the computed z_score/ratio. A vendor with a
    zero stddev (every invoice on file is identical) is skipped entirely -
    z-score is undefined with no variance to divide by, and a single
    repeated amount isn't an outlier by definition.
    """
    anomalies = []
    for invoice in invoices:
        baseline = baselines.get(invoice["vendor_name"])
        if baseline is None or baseline.stddev == 0:
            continue

        amount = float(invoice["total_amount"])
        z_score = (amount - baseline.mean) / baseline.stddev
        if abs(z_score) < z_threshold:
            continue

        ratio = amount / baseline.mean if baseline.mean else float("inf")
        anomalies.append(
            {
                **invoice,
                "vendor_mean": baseline.mean,
                "vendor_stddev": baseline.stddev,
                "vendor_invoice_count": baseline.invoice_count,
                "z_score": z_score,
                "ratio": ratio,
            }
        )

    anomalies.sort(key=lambda row: abs(row["z_score"]), reverse=True)
    return anomalies
