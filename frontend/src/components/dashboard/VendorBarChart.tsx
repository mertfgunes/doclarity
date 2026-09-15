"use client";

import { useState } from "react";
import type { VendorBreakdownRow } from "@/lib/api";
import { formatAmount } from "@/lib/format";
import { horizontalBarPath } from "@/lib/barPath";
import { EmptyState } from "./EmptyState";

const WIDTH = 640;
const ROW_HEIGHT = 44;
const BAR_HEIGHT = 18;

export function VendorBarChart({ rows, currency }: { rows: VendorBreakdownRow[]; currency: string }) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (rows.length === 0) {
    return <EmptyState message="No completed invoices in this currency yet." />;
  }

  const maxValue = Math.max(...rows.map((r) => parseFloat(r.total_amount)));
  const height = rows.length * ROW_HEIGHT;

  return (
    <svg viewBox={`0 0 ${WIDTH} ${height}`} className="w-full" role="img" aria-label={`Top vendors by amount in ${currency}`}>
      {rows.map((row, i) => {
        const value = parseFloat(row.total_amount);
        const barWidth = maxValue === 0 ? 0 : Math.max(3, (value / maxValue) * WIDTH);
        const y = i * ROW_HEIGHT;
        const isHovered = i === hoverIndex;

        return (
          <g key={row.vendor_name} onPointerEnter={() => setHoverIndex(i)} onPointerLeave={() => setHoverIndex(null)}>
            <text x={0} y={y + 12} className="fill-zinc-700 dark:fill-zinc-300 text-[12px] font-medium">
              {row.vendor_name}
            </text>
            <text x={WIDTH} y={y + 12} textAnchor="end" className="fill-zinc-500 dark:fill-zinc-400 text-[11px]">
              {formatAmount(row.total_amount, currency)} · {row.invoice_count} invoice{row.invoice_count === 1 ? "" : "s"}
            </text>
            <rect x={0} y={y + 20} width={WIDTH} height={BAR_HEIGHT} className="fill-zinc-100 dark:fill-zinc-900" />
            <path
              transform={`translate(0, ${y + 20})`}
              d={horizontalBarPath(barWidth, BAR_HEIGHT)}
              className={isHovered ? "fill-blue-600 dark:fill-blue-300" : "fill-blue-500 dark:fill-blue-400"}
            />
            {/* full-row transparent hit area, bigger than the painted bar */}
            <rect x={0} y={y} width={WIDTH} height={ROW_HEIGHT} fill="transparent" />
          </g>
        );
      })}
    </svg>
  );
}
