"use client";

import Link from "next/link";
import { useCallback, useEffect, useState, useTransition } from "react";
import {
  type AnomalyResponse,
  type CurrencyOption,
  type DashboardSummary,
  type RevenuePoint,
  type StatusDistributionRow,
  type VendorBreakdownRow,
  getAnomalies,
  getDashboardCurrencies,
  getDashboardSummary,
  getRevenueOverTime,
  getStatusDistribution,
  getVendorBreakdown,
} from "@/lib/api";
import { StatTile } from "@/components/dashboard/StatTile";
import { CurrencyFilter } from "@/components/dashboard/CurrencyFilter";
import { RevenueLineChart } from "@/components/dashboard/RevenueLineChart";
import { VendorBarChart } from "@/components/dashboard/VendorBarChart";
import { StatusDistributionBar } from "@/components/dashboard/StatusDistributionBar";
import { AnomalyList } from "@/components/dashboard/AnomalyList";
import { EmptyState } from "@/components/dashboard/EmptyState";

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <h2 className="mb-3 text-sm font-medium text-zinc-700 dark:text-zinc-300">{title}</h2>
      {children}
    </section>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [currencies, setCurrencies] = useState<CurrencyOption[]>([]);
  const [currency, setCurrency] = useState<string | null>(null);
  const [statusRows, setStatusRows] = useState<StatusDistributionRow[]>([]);

  const [revenue, setRevenue] = useState<RevenuePoint[]>([]);
  const [vendors, setVendors] = useState<VendorBreakdownRow[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyResponse | null>(null);
  const [currencyDataPending, startCurrencyTransition] = useTransition();
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    Promise.all([getDashboardSummary(), getDashboardCurrencies(), getStatusDistribution()])
      .then(([summaryData, currencyData, statusData]) => {
        setSummary(summaryData);
        setCurrencies(currencyData);
        setStatusRows(statusData);
        setCurrency((prev) => prev ?? currencyData[0]?.currency ?? null);
      })
      .catch(() => setLoadError(true));
  }, []);

  const loadCurrencyData = useCallback((selected: string) => {
    startCurrencyTransition(async () => {
      try {
        const [revenueData, vendorData, anomalyData] = await Promise.all([
          getRevenueOverTime(selected),
          getVendorBreakdown(selected),
          getAnomalies(selected),
        ]);
        setRevenue(revenueData);
        setVendors(vendorData);
        setAnomalies(anomalyData);
        setLoadError(false);
      } catch {
        setLoadError(true);
      }
    });
  }, []);

  useEffect(() => {
    if (currency) loadCurrencyData(currency);
  }, [currency, loadCurrencyData]);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-12">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Aggregate view across everything uploaded so far.
          </p>
        </div>
        <Link href="/" className="text-sm text-zinc-500 underline hover:text-zinc-700 dark:hover:text-zinc-300">
          ← Back to documents
        </Link>
      </header>

      {loadError && <p className="text-sm text-red-600">Can&apos;t reach the API.</p>}

      {summary && (
        <div className="grid grid-cols-3 gap-4">
          <StatTile label="Documents uploaded" value={String(summary.total_documents)} />
          <StatTile label="Extraction rows" value={String(summary.total_extractions)} />
          <StatTile label="Needs review" value={String(summary.needs_review_count)} />
        </div>
      )}

      <ChartCard title="Extraction status distribution">
        <StatusDistributionBar rows={statusRows} />
      </ChartCard>

      {currencies.length === 0 ? (
        <ChartCard title="Revenue">
          <EmptyState message="No completed invoices yet - upload one to see revenue and vendor charts here." />
        </ChartCard>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Revenue &amp; vendors</h2>
            {currency && <CurrencyFilter options={currencies} value={currency} onChange={setCurrency} />}
          </div>

          <div className={`grid gap-6 transition-opacity ${currencyDataPending ? "opacity-60" : "opacity-100"}`}>
            <ChartCard title={`Revenue over time (${currency})`}>
              <RevenueLineChart points={revenue} currency={currency ?? ""} />
            </ChartCard>

            <ChartCard title={`Top vendors by amount (${currency})`}>
              <VendorBarChart rows={vendors} currency={currency ?? ""} />
            </ChartCard>

            <ChartCard title={`Anomalies (${currency})`}>
              {anomalies && <AnomalyList anomalies={anomalies.anomalies} explanation={anomalies.explanation} currency={currency ?? ""} />}
            </ChartCard>
          </div>
        </>
      )}
    </div>
  );
}
