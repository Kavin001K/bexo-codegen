import type { PortfolioSnapshot } from "./types";

export async function loadPortfolioData(): Promise<PortfolioSnapshot | null> {
  try {
    const res = await fetch("./data.json", { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as PortfolioSnapshot;
  } catch {
    return null;
  }
}
