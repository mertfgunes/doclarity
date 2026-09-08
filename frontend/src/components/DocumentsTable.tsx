"use client";

import { Fragment, useEffect, useState } from "react";
import { type Document, type DocumentExtraction, getDocumentExtractions } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";

function formatDate(iso: string) {
  return new Date(iso).toLocaleString();
}

function ExtractionRow({ extraction }: { extraction: DocumentExtraction }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-3 text-sm dark:border-zinc-800">
      <div className="flex flex-wrap items-center gap-2">
        <span className="font-medium capitalize">{extraction.document_type}</span>
        <StatusBadge status={extraction.status} />
      </div>
      <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-zinc-600 sm:grid-cols-3 dark:text-zinc-400">
        {extraction.vendor_name && (
          <div>
            <dt className="text-xs text-zinc-400">Vendor</dt>
            <dd>{extraction.vendor_name}</dd>
          </div>
        )}
        {extraction.invoice_number && (
          <div>
            <dt className="text-xs text-zinc-400">Invoice #</dt>
            <dd>{extraction.invoice_number}</dd>
          </div>
        )}
        {extraction.total_amount && (
          <div>
            <dt className="text-xs text-zinc-400">Total</dt>
            <dd>
              {extraction.currency} {extraction.total_amount}
            </dd>
          </div>
        )}
        {extraction.invoice_date && (
          <div>
            <dt className="text-xs text-zinc-400">Invoice date</dt>
            <dd>{extraction.invoice_date}</dd>
          </div>
        )}
        {extraction.due_date && (
          <div>
            <dt className="text-xs text-zinc-400">Due date</dt>
            <dd>{extraction.due_date}</dd>
          </div>
        )}
      </dl>
      {extraction.confidence_flags.length > 0 && (
        <ul className="mt-2 space-y-0.5 text-xs text-amber-700 dark:text-amber-400">
          {extraction.confidence_flags.map((flag) => (
            <li key={flag}>⚠ {flag}</li>
          ))}
        </ul>
      )}
      {extraction.error_message && (
        <p className="mt-2 text-xs text-red-600 dark:text-red-400">{extraction.error_message}</p>
      )}
    </div>
  );
}

function ExtractionsPanel({ documentId }: { documentId: string }) {
  const [state, setState] = useState<
    { kind: "loading" } | { kind: "error" } | { kind: "loaded"; extractions: DocumentExtraction[] }
  >({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    getDocumentExtractions(documentId)
      .then((extractions) => {
        if (!cancelled) setState({ kind: "loaded", extractions });
      })
      .catch(() => {
        if (!cancelled) setState({ kind: "error" });
      });
    return () => {
      cancelled = true;
    };
  }, [documentId]);

  if (state.kind === "loading") {
    return <p className="px-4 py-3 text-sm text-zinc-500">Loading extractions…</p>;
  }
  if (state.kind === "error") {
    return <p className="px-4 py-3 text-sm text-red-600">Couldn&apos;t load extractions.</p>;
  }
  if (state.extractions.length === 0) {
    return <p className="px-4 py-3 text-sm text-zinc-500">No extraction rows yet.</p>;
  }
  return (
    <div className="space-y-2 px-4 py-3">
      {state.extractions.map((extraction) => (
        <ExtractionRow key={extraction.id} extraction={extraction} />
      ))}
    </div>
  );
}

export function DocumentsTable({ documents }: { documents: Document[] }) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (documents.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-zinc-300 px-4 py-8 text-center text-sm text-zinc-500 dark:border-zinc-700">
        No documents uploaded yet.
      </p>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-left text-sm">
        <thead className="bg-zinc-50 text-xs uppercase text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
          <tr>
            <th className="px-4 py-2 font-medium">Filename</th>
            <th className="px-4 py-2 font-medium">Type</th>
            <th className="px-4 py-2 font-medium">Status</th>
            <th className="px-4 py-2 font-medium">Uploaded</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
          {documents.map((doc) => {
            const isExpanded = expandedId === doc.id;
            return (
              <Fragment key={doc.id}>
                <tr
                  onClick={() => setExpandedId(isExpanded ? null : doc.id)}
                  className="cursor-pointer hover:bg-zinc-50 dark:hover:bg-zinc-900"
                >
                  <td className="px-4 py-3 font-medium">{doc.filename}</td>
                  <td className="px-4 py-3 text-zinc-500">{doc.content_type}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={doc.status} />
                  </td>
                  <td className="px-4 py-3 text-zinc-500">{formatDate(doc.uploaded_at)}</td>
                </tr>
                {isExpanded && (
                  <tr>
                    <td colSpan={4} className="bg-zinc-50/50 dark:bg-zinc-900/50">
                      <ExtractionsPanel documentId={doc.id} />
                    </td>
                  </tr>
                )}
              </Fragment>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
