import { PortfolioSite } from "@/components/PortfolioSite";
import { getPortfolioData } from "@/lib/getPortfolioData";

export default function HomePage() {
  const data = getPortfolioData();

  if (!data) {
    return (
      <main>
        <nav aria-label="Primary navigation" className="mx-auto max-w-5xl px-4 pt-8">
          <a href="#top" className="text-sm text-brand">
            Home
          </a>
        </nav>
        <h1 id="top" className="mx-auto max-w-5xl px-4 pt-4 text-3xl font-bold">
          Portfolio
        </h1>
        <p className="mx-auto max-w-5xl px-4 pt-4 text-slate-400">Profile data unavailable.</p>
      </main>
    );
  }

  return (
    <main id="top">
      <PortfolioSite data={data} />
    </main>
  );
}
