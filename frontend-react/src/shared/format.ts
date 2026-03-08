export function toSpaPath(url: string | null | undefined, basename = "/app"): string {
  if (!url) {
    return "/";
  }
  const path = url.replace(/^https?:\/\/[^/]+/i, "");
  if (path === basename || path === `${basename}/`) {
    return "/";
  }
  if (path.startsWith(`${basename}/`)) {
    return path.slice(basename.length);
  }
  return path;
}

export function formatMoney(amount: number | string | null | undefined, currency = "GBP"): string {
  if (amount === null || amount === undefined || amount === "") {
    return "No pre-payment";
  }
  try {
    return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(Number(amount));
  } catch (_error) {
    return `${amount} ${currency}`;
  }
}
