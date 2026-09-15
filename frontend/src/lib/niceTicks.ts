// Classic "nice numbers" tick algorithm: picks a round step (1/2/5 * 10^n)
// so axis gridlines land on clean values instead of raw data fractions.
export function niceTicks(maxValue: number, targetCount = 4): { step: number; niceMax: number; ticks: number[] } {
  if (maxValue <= 0) return { step: 1, niceMax: 1, ticks: [0, 1] };

  const roughStep = maxValue / targetCount;
  const magnitude = Math.pow(10, Math.floor(Math.log10(roughStep)));
  const normalized = roughStep / magnitude;

  let step: number;
  if (normalized < 1.5) step = 1;
  else if (normalized < 3) step = 2;
  else if (normalized < 7) step = 5;
  else step = 10;
  step *= magnitude;

  const niceMax = Math.ceil(maxValue / step) * step;
  const ticks: number[] = [];
  for (let v = 0; v <= niceMax + step / 2; v += step) ticks.push(Math.round(v * 100) / 100);
  return { step, niceMax, ticks };
}
