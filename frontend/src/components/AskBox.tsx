"use client";

import { useState } from "react";
import { type AskResponse, ApiError, askQuestion } from "@/lib/api";

interface ChatTurn {
  question: string;
  response: AskResponse;
}

export function AskBox() {
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || pending) return;

    setPending(true);
    setError(null);
    try {
      const response = await askQuestion(trimmed);
      setTurns((prev) => [...prev, { question: trimmed, response }]);
      setQuestion("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the API.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section>
      <h2 className="mb-3 text-sm font-medium text-zinc-700 dark:text-zinc-300">Ask your documents</h2>

      <div className="space-y-4 rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
        {turns.length === 0 && (
          <p className="text-sm text-zinc-500">
            Ask about a specific document (cited by page) - it searches everything you&apos;ve uploaded so far.
          </p>
        )}

        {turns.map((turn, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm font-medium">{turn.question}</p>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">{turn.response.answer}</p>
            {turn.response.citations.length > 0 && (
              <ul className="space-y-1">
                {turn.response.citations.map((citation, j) => (
                  <li key={j} className="text-xs text-zinc-500">
                    <span className="font-medium">
                      {citation.filename}
                      {citation.page_number != null ? `, page ${citation.page_number}` : ""}
                    </span>
                    <span className="block truncate text-zinc-400">{citation.snippet}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}

        {error && <p className="text-sm text-red-600">{error}</p>}

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="e.g. What's the total on the Bluefin invoice?"
            disabled={pending}
            className="flex-1 rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-500 disabled:opacity-50 dark:border-zinc-700"
          />
          <button
            type="submit"
            disabled={pending || !question.trim()}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
          >
            {pending ? "Asking…" : "Ask"}
          </button>
        </form>
      </div>
    </section>
  );
}
