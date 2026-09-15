"use client";

import { useMemo, useState } from "react";
import type { RevenuePoint } from "@/lib/api";
import { formatAmount, formatCompactNumber, formatMonthLabel } from "@/lib/format";
import { niceTicks } from "@/lib/niceTicks";
import { EmptyState } from "./EmptyState";

const WIDTH = 640;
const HEIGHT = 240;
const MARGIN = { top: 16, right: 16, bottom: 28, left: 56 };
const PLOT_WIDTH = WIDTH - MARGIN.left - MARGIN.right;
const PLOT_HEIGHT = HEIGHT - MARGIN.top - MARGIN.bottom;

export function RevenueLineChart({ points, currency }: { points: RevenuePoint[]; currency: string }) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const values = useMemo(() => points.map((p) => parseFloat(p.total_amount)), [points]);
  const maxValue = Math.max(0, ...values);
  const { niceMax, ticks } = useMemo(() => niceTicks(maxValue), [maxValue]);

  if (points.length === 0) {
    return <EmptyState message="No completed invoices in this currency yet." />;
  }

  const xFor = (i: number) => (points.length <= 1 ? PLOT_WIDTH / 2 : (i / (points.length - 1)) * PLOT_WIDTH);
  const yFor = (v: number) => PLOT_HEIGHT - (niceMax === 0 ? 0 : (v / niceMax) * PLOT_HEIGHT);

  const linePath = points.map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i)} ${yFor(values[i])}`).join(" ");
  const areaPath = `${linePath} L ${xFor(points.length - 1)} ${PLOT_HEIGHT} L ${xFor(0)} ${PLOT_HEIGHT} Z`;
  const hovered = hoverIndex != null ? points[hoverIndex] : null;
  const lastIndex = points.length - 1;

  function handlePointerMove(e: React.PointerEvent<SVGRectElement>) {
    const rect = e.currentTarget.getBoundingClientRect();
    const relX = ((e.clientX - rect.left) / rect.width) * PLOT_WIDTH;
    let nearest = 0;
    let nearestDist = Infinity;
    points.forEach((_, i) => {
      const dist = Math.abs(xFor(i) - relX);
      if (dist < nearestDist) {
        nearestDist = dist;
        nearest = i;
      }
    });
    setHoverIndex(nearest);
  }

  return (
    <div>
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full"
        role="img"
        aria-label={`Revenue over time in ${currency}`}
      >
        <g transform={`translate(${MARGIN.left}, ${MARGIN.top})`}>
          {ticks.map((t) => (
            <g key={t}>
              <line
                x1={0}
                x2={PLOT_WIDTH}
                y1={yFor(t)}
                y2={yFor(t)}
                strokeWidth={1}
                className="stroke-zinc-200 dark:stroke-zinc-800"
              />
              <text x={-8} y={yFor(t)} textAnchor="end" dominantBaseline="middle" className="fill-zinc-400 text-[10px]">
                {formatCompactNumber(t)}
              </text>
            </g>
          ))}

          <path d={areaPath} className="fill-blue-500/10" />
          <path
            d={linePath}
            fill="none"
            strokeWidth={2}
            strokeLinejoin="round"
            strokeLinecap="round"
            className="stroke-blue-500 dark:stroke-blue-400"
          />

          {points.map((p, i) => (
            <circle
              key={p.period}
              cx={xFor(i)}
              cy={yFor(values[i])}
              r={i === hoverIndex || i === lastIndex ? 4 : 3}
              strokeWidth={2}
              className="fill-blue-500 stroke-white dark:fill-blue-400 dark:stroke-zinc-950"
            />
          ))}

          <text
            x={xFor(lastIndex)}
            y={Math.max(10, yFor(values[lastIndex]) - 10)}
            textAnchor="end"
            className="fill-zinc-700 dark:fill-zinc-300 text-[11px] font-medium"
          >
            {formatAmount(points[lastIndex].total_amount, currency)}
          </text>

          {points.map((p, i) => (
            <text key={p.period} x={xFor(i)} y={PLOT_HEIGHT + 18} textAnchor="middle" className="fill-zinc-400 text-[10px]">
              {formatMonthLabel(p.period)}
            </text>
          ))}

          {hovered && hoverIndex != null && (
            <line
              x1={xFor(hoverIndex)}
              x2={xFor(hoverIndex)}
              y1={0}
              y2={PLOT_HEIGHT}
              strokeWidth={1}
              className="stroke-zinc-300 dark:stroke-zinc-700"
            />
          )}

          <rect
            x={0}
            y={0}
            width={PLOT_WIDTH}
            height={PLOT_HEIGHT}
            fill="transparent"
            onPointerMove={handlePointerMove}
            onPointerLeave={() => setHoverIndex(null)}
          />
        </g>
      </svg>

      <div className="mt-1 h-4 text-xs text-zinc-600 dark:text-zinc-400">
        {hovered && (
          <>
            <span className="font-medium text-zinc-900 dark:text-zinc-50">{formatAmount(hovered.total_amount, currency)}</span>
            {" · "}
            {formatMonthLabel(hovered.period)} · {hovered.invoice_count} invoice{hovered.invoice_count === 1 ? "" : "s"}
          </>
        )}
      </div>
    </div>
  );
}
