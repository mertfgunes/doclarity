import type { AnomalyRow } from "@/lib/api";
import { formatAmount } from "@/lib/format";
import { EmptyState } from "./EmptyState";

export function AnomalyList({ anomalies, explanation, currency }: { anomalies: AnomalyRow[]; explanation: string; currency: string }) {
  if (anomalies.length === 0) {
    return <EmptyState message="No outliers - every vendor's invoices fall within their own normal range." />;
  }

  return (
    <div className="flex flex-col gap-4">
      <ul className="flex flex-col divide-y divide-zinc-200 dark:divide-zinc-800">
        {anomalies.map((row) => (
          <li key={row.extraction_id} className="flex items-center justify-between gap-4 py-3">
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-zinc-900 dark:text-zinc-50">{row.vendor_name}</p>
              <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">
                {row.invoice_number ?? "No invoice #"} · usual avg {formatAmount(row.vendor_mean, currency)} across{" "}
                {row.vendor_invoice_count} invoices
              </p>
            </div>
            <div className="flex shrink-0 flex-col items-end">
              <span className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">{formatAmount(row.total_amount, currency)}</span>
              <span className="mt-0.5 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-950 dark:text-red-300">
                {row.ratio.toFixed(1)}x average
              </span>
            </div>
          </li>
        ))}
      </ul>

      {explanation && (
        <p className="whitespace-pre-line rounded-md bg-zinc-50 p-3 text-sm text-zinc-700 dark:bg-zinc-900 dark:text-zinc-300">
          {explanation}
        </p>
      )}
    </div>
  );
}
