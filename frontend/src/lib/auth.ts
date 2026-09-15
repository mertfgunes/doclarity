const TOKEN_KEY = "doclarity_token";

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string): void {
  try {
    localStorage.setItem(TOKEN_KEY, token);
  } catch {
    // localStorage unavailable (private window, blocked storage) - the
    // user just won't stay logged in across reloads.
  }
}

export function clearToken(): void {
  try {
    localStorage.removeItem(TOKEN_KEY);
  } catch {
    // see setToken
  }
}

export type Role = "admin" | "viewer";

// The JWT payload's role claim isn't sensitive - decoding it client-side
// just lets the UI show "logged in as admin/viewer" without another
// round-trip. The server still enforces the real access control.
export function getRole(): Role | null {
  const token = getToken();
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.role === "admin" ? "admin" : payload.role === "viewer" ? "viewer" : null;
  } catch {
    return null;
  }
}
