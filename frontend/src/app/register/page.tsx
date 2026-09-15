"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ApiError, loginUser, registerUser } from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      await registerUser(email, password);
      const { access_token } = await loginUser(email, password);
      setToken(access_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't reach the API.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-sm flex-1 flex-col justify-center gap-6 px-6 py-12">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Doclarity</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Create an account (read-only viewer access - see README for admin accounts).
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          required
          disabled={pending}
          className="rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-500 disabled:opacity-50 dark:border-zinc-700"
        />
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password (min. 8 characters)"
          minLength={8}
          required
          disabled={pending}
          className="rounded-md border border-zinc-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-zinc-500 disabled:opacity-50 dark:border-zinc-700"
        />
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={pending}
          className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {pending ? "Creating account…" : "Register"}
        </button>
      </form>

      <p className="text-sm text-zinc-500">
        Already have an account?{" "}
        <Link href="/login" className="underline hover:text-zinc-700 dark:hover:text-zinc-300">
          Log in
        </Link>
      </p>
    </div>
  );
}
