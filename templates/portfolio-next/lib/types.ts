export interface PortfolioSnapshot {
  version: number;
  syncedAt: string;
  handle: string;
  profile: {
    full_name?: string | null;
    headline?: string | null;
    bio?: string | null;
    avatar_url?: string | null;
    location?: string | null;
    email?: string | null;
    phone?: string | null;
    website?: string | null;
    linkedin_url?: string | null;
    github_url?: string | null;
    resume_url?: string | null;
  };
  projects: Array<{
    id?: string;
    title?: string;
    description?: string;
    tech_stack?: string[];
    live_url?: string | null;
    github_url?: string | null;
    image_url?: string | null;
  }>;
  skills: Array<{
    id?: string;
    name?: string;
    level?: string;
    category?: string;
  }>;
  experiences: Array<{
    id?: string;
    company?: string;
    role?: string;
    start_date?: string;
    end_date?: string | null;
    description?: string;
    is_current?: boolean;
  }>;
  education: Array<{
    id?: string;
    institution?: string;
    degree?: string;
    field?: string;
    start_year?: number;
    end_year?: number | null;
  }>;
  theme?: {
    portfolio_theme?: string | null;
    portfolio_font?: string | null;
    identity_card_palette?: string | null;
  };
}
