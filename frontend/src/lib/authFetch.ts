// Installs a global fetch wrapper that attaches the Clerk session token to
// requests aimed at the backend API. This is only called when Clerk is
// configured (a publishable key is present); otherwise window.fetch is left
// completely untouched and the app behaves exactly as before.

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://127.0.0.1:8000";

type ClerkWindow = Window & {
  Clerk?: { session?: { getToken: () => Promise<string | null> } };
  __zonalyzeAuthFetchInstalled?: boolean;
};

export function installAuthFetch(): void {
  const w = window as ClerkWindow;
  if (w.__zonalyzeAuthFetchInstalled) return;
  w.__zonalyzeAuthFetchInstalled = true;

  const originalFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    try {
      const url =
        typeof input === "string"
          ? input
          : input instanceof URL
            ? input.toString()
            : input.url;

      const clerk = w.Clerk;
      if (url && url.startsWith(API_BASE) && clerk?.session) {
        const token = await clerk.session.getToken();
        if (token) {
          const headers = new Headers(
            init?.headers ?? (input instanceof Request ? input.headers : undefined),
          );
          headers.set("Authorization", `Bearer ${token}`);
          init = { ...init, headers };
        }
      }
    } catch {
      // Token retrieval failed — fall through and send the request unmodified.
    }
    return originalFetch(input, init);
  };
}
