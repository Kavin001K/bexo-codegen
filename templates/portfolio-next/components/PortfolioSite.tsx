"use client";

import { motion } from "framer-motion";
import type { PortfolioSnapshot } from "@/lib/types";

export function PortfolioSite({ data }: { data: PortfolioSnapshot }) {
  const { profile, projects, skills, experiences, education } = data;

  const navItems: { href: string; label: string }[] = [
    ...(profile.bio ? [{ href: "#about", label: "About" }] : []),
    ...(skills.length > 0 ? [{ href: "#skills", label: "Skills" }] : []),
    ...(experiences.length > 0 ? [{ href: "#experience", label: "Experience" }] : []),
    ...(projects.length > 0 ? [{ href: "#projects", label: "Projects" }] : []),
    ...(education.length > 0 ? [{ href: "#education", label: "Education" }] : []),
    { href: "#contact", label: "Contact" },
  ];

  return (
    <div className="mx-auto max-w-5xl px-4 pb-24 pt-12 sm:px-6">
      <nav aria-label="Primary navigation" className="mb-10 flex flex-wrap gap-4 border-b border-slate-800 pb-4 text-sm">
        {navItems.map((item) => (
          <a
            key={item.href}
            href={item.href}
            className="min-h-[44px] min-w-[44px] inline-flex items-center text-slate-300 hover:text-brand"
          >
            {item.label}
          </a>
        ))}
      </nav>

      <motion.header
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-16 flex flex-col gap-6 sm:flex-row sm:items-center"
      >
        {profile.avatar_url ? (
          <img
            src={profile.avatar_url}
            alt={profile.full_name ?? "Avatar"}
            className="h-28 w-28 rounded-2xl object-cover ring-2 ring-brand/40"
          />
        ) : (
          <div className="flex h-28 w-28 items-center justify-center rounded-2xl bg-slate-800 text-3xl font-bold text-brand">
            {(profile.full_name ?? "?")[0]}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
            {profile.full_name}
          </h1>
          <p className="mt-2 text-lg text-brand-accent">{profile.headline}</p>
          {profile.location && (
            <p className="mt-1 text-sm text-slate-400">{profile.location}</p>
          )}
        </div>
      </motion.header>

      {profile.bio && (
        <Section id="about" title="About" delay={0.1}>
          <p className="max-w-3xl leading-relaxed text-slate-300">{profile.bio}</p>
        </Section>
      )}

      {skills.length > 0 && (
        <Section id="skills" title="Skills" delay={0.15}>
          <div className="flex flex-wrap gap-2">
            {skills.map((s) => (
              <span
                key={s.id ?? s.name}
                className="rounded-full border border-slate-700 bg-slate-900 px-4 py-2 text-sm"
              >
                {s.name}
              </span>
            ))}
          </div>
        </Section>
      )}

      {experiences.length > 0 && (
        <Section id="experience" title="Experience" delay={0.2}>
          <ul className="space-y-6">
            {experiences.map((ex) => (
              <li key={ex.id ?? `${ex.company}-${ex.role}`} className="border-l-2 border-brand pl-4">
                <h3 className="font-semibold">
                  {ex.role} — {ex.company}
                </h3>
                <p className="text-sm text-slate-400">
                  {ex.start_date}
                  {ex.end_date || ex.is_current ? ` – ${ex.end_date ?? "Present"}` : ""}
                </p>
                {ex.description && (
                  <p className="mt-2 text-slate-300">{ex.description}</p>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {projects.length > 0 && (
        <Section id="projects" title="Projects" delay={0.25}>
          <div className="grid gap-6 sm:grid-cols-2">
            {projects.map((p) => (
              <motion.article
                key={p.id ?? p.title}
                whileHover={{ y: -4 }}
                className="overflow-hidden rounded-xl border border-slate-800 bg-slate-900/50"
              >
                {p.image_url && (
                  <img src={p.image_url} alt={p.title ?? "Project"} className="h-40 w-full object-cover" />
                )}
                <div className="p-4">
                  <h3 className="font-semibold">{p.title}</h3>
                  {p.description && (
                    <p className="mt-2 text-sm text-slate-400 line-clamp-3">{p.description}</p>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {p.live_url && (
                      <a
                        href={p.live_url}
                        className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg bg-brand px-4 text-sm font-medium text-white"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Live
                      </a>
                    )}
                    {p.github_url && (
                      <a
                        href={p.github_url}
                        className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-slate-600 px-4 text-sm"
                        target="_blank"
                        rel="noreferrer"
                      >
                        GitHub
                      </a>
                    )}
                  </div>
                </div>
              </motion.article>
            ))}
          </div>
        </Section>
      )}

      {education.length > 0 && (
        <Section id="education" title="Education" delay={0.3}>
          <ul className="space-y-4">
            {education.map((ed) => (
              <li key={ed.id ?? ed.institution}>
                <h3 className="font-semibold">
                  {ed.degree} — {ed.institution}
                </h3>
                <p className="text-sm text-slate-400">
                  {ed.field} · {ed.start_year}–{ed.end_year ?? "Present"}
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section id="contact" title="Contact" delay={0.35}>
        <div className="flex flex-wrap gap-3">
          {profile.email && (
            <a
              href={`mailto:${profile.email}`}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-slate-600 px-5 text-sm font-medium"
            >
              Email
            </a>
          )}
          {profile.linkedin_url && (
            <a
              href={profile.linkedin_url}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-slate-600 px-5 text-sm font-medium"
              target="_blank"
              rel="noreferrer"
            >
              LinkedIn
            </a>
          )}
          {profile.github_url && (
            <a
              href={profile.github_url}
              className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-lg border border-slate-600 px-5 text-sm font-medium"
              target="_blank"
              rel="noreferrer"
            >
              GitHub
            </a>
          )}
        </div>
      </Section>

      <footer className="mt-20 border-t border-slate-800 pt-8 text-center text-xs text-slate-500">
        Built with BEXO · Portfolio data syncs from your profile
      </footer>
    </div>
  );
}

function Section({
  id,
  title,
  children,
  delay = 0,
}: {
  id: string;
  title: string;
  children: React.ReactNode;
  delay?: number;
}) {
  return (
    <motion.section
      id={id}
      initial={{ opacity: 0, y: 12 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ delay }}
      className="mb-14"
    >
      <h2 className="mb-4 text-xl font-bold text-brand">{title}</h2>
      {children}
    </motion.section>
  );
}
