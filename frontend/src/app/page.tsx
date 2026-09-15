"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { type Document, listDocuments } from "@/lib/api";
import { UploadDropzone } from "@/components/UploadDropzone";
import { DocumentsTable } from "@/components/DocumentsTable";
import { AskBox } from "@/components/AskBox";
import { AccountBadge } from "@/components/AccountBadge";

const POLL_INTERVAL_MS = 3000;

export default function Home() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loadError, setLoadError] = useState(false);

  const refresh = useCallback(() => {
    listDocuments()
      .then((docs) => {
        setDocuments(docs);
        setLoadError(false);
      })
      .catch(() => setLoadError(true));
  }, []);

  useEffect(() => {
    refresh();
    const interval = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [refresh]);

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-8 px-6 py-12">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Doclarity</h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Upload an invoice, contract, or transaction file to see it parsed and structured.
          </p>
        </div>
        <div className="flex items-center gap-4">
          <AccountBadge />
          <Link href="/dashboard" className="text-sm text-zinc-500 underline hover:text-zinc-700 dark:hover:text-zinc-300">
            Dashboard →
          </Link>
        </div>
      </header>

      <UploadDropzone onUploaded={refresh} />

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-medium text-zinc-700 dark:text-zinc-300">Documents</h2>
          {loadError && <span className="text-xs text-red-600">Can&apos;t reach the API.</span>}
        </div>
        <DocumentsTable documents={documents} />
      </section>

      <AskBox />
    </div>
  );
}
