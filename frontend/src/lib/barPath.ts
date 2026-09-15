// A horizontal bar rounded only at its data-end (right edge), square at the
// baseline (left edge) - per the mark spec, never a uniform pill shape.
export function horizontalBarPath(width: number, height: number, radius = 4): string {
  const r = Math.max(0, Math.min(radius, width / 2, height / 2));
  if (width <= 0) return "";
  return [
    `M 0,0`,
    `L ${width - r},0`,
    `Q ${width},0 ${width},${r}`,
    `L ${width},${height - r}`,
    `Q ${width},${height} ${width - r},${height}`,
    `L 0,${height}`,
    `Z`,
  ].join(" ");
}
