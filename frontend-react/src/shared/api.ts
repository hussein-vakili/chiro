export type QueryParams = Record<string, string | number | boolean | null | undefined>;

export interface FetchJsonResult<T = unknown> {
  response: Response;
  data: T;
}

export function buildUrl(endpoint: string, params: QueryParams = {}): string {
  const url = new URL(endpoint, window.location.origin);
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") {
      return;
    }
    url.searchParams.set(key, String(value));
  });
  return `${url.pathname}${url.search}`;
}

export async function fetchJson<T = unknown>(url: string, options: RequestInit = {}): Promise<FetchJsonResult<T>> {
  const headers = new Headers(options.headers || {});
  headers.set("Accept", "application/json");
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, {
    credentials: "same-origin",
    ...options,
    headers,
  });
  const text = await response.text();
  let data = {} as T;
  if (text) {
    try {
      data = JSON.parse(text) as T;
    } catch (_error) {
      throw new Error(`Invalid JSON response from ${url}`);
    }
  }
  return { response, data };
}
