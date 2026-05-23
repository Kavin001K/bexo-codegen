import fs from "fs";
import path from "path";
import type { PortfolioSnapshot } from "./types";

/** Read portfolio snapshot baked into public/data.json at `next build` time. */
export function getPortfolioData(): PortfolioSnapshot | null {
  try {
    const filePath = path.join(process.cwd(), "public", "data.json");
    const raw = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(raw) as PortfolioSnapshot;
  } catch {
    return null;
  }
}
