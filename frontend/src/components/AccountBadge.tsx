"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { clearToken, getRole, getToken, type Role } from "@/lib/auth";

// Redirects to /login if there's no token, and shows "logged in as
// {role} · Log out" once there is one. Used on every page that requires
// auth - the redirect check lives here so each page doesn't repeat it.
export function AccountBadge() {
  const router = useRouter();
  const [role] = useState<Role | null>(() => getRole());

  useEffect(() => {
    if (!getToken()) router.replace("/login");
  }, [router]);

  if (!role) return null;

  return (
    <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
      <span>
        Logged in as <span className="font-medium">{role}</span>
      </span>
      <button
        type="button"
        onClick={() => {
          clearToken();
          router.replace("/login");
        }}
        className="underline hover:text-zinc-700 dark:hover:text-zinc-300"
      >
        Log out
      </button>
    </div>
  );
}
