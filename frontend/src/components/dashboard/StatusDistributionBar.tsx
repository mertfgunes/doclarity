"use client";

import { useState } from "react";
import type { ExtractionStatus, StatusDistributionRow } from "@/lib/api";
import { EmptyState } from "./EmptyState";

const WIDTH = 640;
const BAR_HEIGHT = 28;
const GAP = 2;

// Same hue mapping as StatusBadge, at chart-appropriate saturation instead
// of the pastel badge background - one status vocabulary across the app.
const STATUS_ORDER: ExtractionStatus[] = ["completed", "needs_review", "failed"];
const STATUS_FILL: Record<ExtractionStatus, string> = {
  completed: "fill-green-500 dark:fill-green-400",
  needs_review: "fill-amber-500 dark:fill-amber-400",
  failed: "fill-red-500 dark:fill-red-400",
};
const STATUS_DOT: Record<ExtractionStatus, string> = {
  completed: "bg-green-500 dark:bg-green-400",
  needs_review: "bg-amber-500 dark:bg-amber-400",
  failed: "bg-red-500 dark:bg-red-400",
};
const STATUS_LABEL: Record<ExtractionStatus, string> = {
  completed: "Completed",
  needs_review: "Needs review",
  failed: "Failed",
};

export function StatusDistributionBar({ rows }: { rows: StatusDistributionRow[] }) {
  const [hovered, setHovered] = useState<ExtractionStatus | null>(null);

  const countByStatus = new Map(rows.map((r) => [r.status, r.count]));
  const total = rows.reduce((sum, r) => sum + r.count, 0);

  if (total === 0) {
    return <EmptyState message="No extractions yet." />;
  }

  const present = STATUS_ORDER.filter((s) => (countByStatus.get(s) ?? 0) > 0);
  const totalGap = Math.max(0, present.length - 1) * GAP;
  const usableWidth = WIDTH - totalGap;

  const segments = present.reduce<Array<{ status: ExtractionStatus; count: number; x: number; width: number; pct: number }>>(
    (acc, status) => {
      const count = countByStatus.get(status) ?? 0;
      const width = (count / total) * usableWidth;
      const prev = acc[acc.length - 1];
      const x = prev ? prev.x + prev.width + GAP : 0;
      acc.push({ status, count, x, width, pct: (count / total) * 100 });
      return acc;
    },
    [],
  );

  return (
    <div>
      <svg viewBox={`0 0 ${WIDTH} ${BAR_HEIGHT}`} className="w-full" role="img" aria-label="Extraction status distribution">
        <defs>
          <clipPath id="statusBarClip">
            <rect width={WIDTH} height={BAR_HEIGHT} rx={4} />
          </clipPath>
        </defs>
        <g clipPath="url(#statusBarClip)">
          {segments.map((seg) => (
            <rect
              key={seg.status}
              x={seg.x}
              y={0}
              width={seg.width}
              height={BAR_HEIGHT}
              className={`${STATUS_FILL[seg.status]} ${hovered === seg.status ? "opacity-80" : ""}`}
              onPointerEnter={() => setHovered(seg.status)}
              onPointerLeave={() => setHovered(null)}
            />
          ))}
        </g>
      </svg>

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
        {segments.map((seg) => (
          <div
            key={seg.status}
            className="flex items-center gap-1.5 text-xs text-zinc-600 dark:text-zinc-400"
            onPointerEnter={() => setHovered(seg.status)}
            onPointerLeave={() => setHovered(null)}
          >
            <span className={`h-2 w-2 rounded-full ${STATUS_DOT[seg.status]}`} />
            {STATUS_LABEL[seg.status]}
            <span className="font-medium text-zinc-900 dark:text-zinc-50">{seg.count}</span>
            <span className="text-zinc-400">({seg.pct.toFixed(0)}%)</span>
          </div>
        ))}
      </div>
    </div>
  );
}
