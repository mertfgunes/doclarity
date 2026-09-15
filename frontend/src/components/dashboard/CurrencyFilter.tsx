import type { CurrencyOption } from "@/lib/api";

export function CurrencyFilter({
  options,
  value,
  onChange,
}: {
  options: CurrencyOption[];
  value: string;
  onChange: (currency: string) => void;
}) {
  return (
    <label className="flex items-center gap-2 text-sm text-zinc-600 dark:text-zinc-400">
      Currency
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-zinc-300 bg-transparent px-2 py-1 text-sm text-zinc-900 outline-none focus:border-zinc-500 dark:border-zinc-700 dark:text-zinc-50"
      >
        {options.map((opt) => (
          <option key={opt.currency} value={opt.currency}>
            {opt.currency} ({opt.invoice_count})
          </option>
        ))}
      </select>
    </label>
  );
}
