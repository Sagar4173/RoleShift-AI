import {
  ArrowRight,
  ArrowRightLeft,
  BarChart3,
  BrainCircuit,
  Briefcase,
  CheckCircle2,
  Cpu,
  Database,
  Eye,
  Gauge,
  GitCompareArrows,
  GraduationCap,
  Layers,
  ListChecks,
  Lock,
  Radar,
  Rocket,
  ShieldCheck,
  Sparkles,
  Target,
  Workflow,
} from "lucide-react";
import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";

import { cn } from "../lib/utils";

const navigation = [
  { label: "Product", href: "#product" },
  { label: "How It Works", href: "#how-it-works" },
  { label: "Architecture", href: "#architecture" },
];

const features = [
  {
    icon: Radar,
    title: "Role Intelligence",
    description:
      "Every role is analyzed as a whole — its responsibilities, its industry context, and the work it actually performs today.",
  },
  {
    icon: Gauge,
    title: "AI Exposure",
    description:
      "A single, explainable score quantifies how much of the role is exposed to AI transformation, with an impact rating from none to high.",
  },
  {
    icon: Cpu,
    title: "Automation & Augmentation",
    description:
      "Work is separated into what AI can automate outright and what AI will augment — helping people, not replacing them.",
  },
  {
    icon: Eye,
    title: "Future Responsibilities",
    description:
      "A forward view of the responsibilities the role will carry as AI adoption reshapes the work itself.",
  },
  {
    icon: GraduationCap,
    title: "Future Skills",
    description:
      "The capabilities the role will demand next, derived from the same structured analysis that maps today's skill set.",
  },
  {
    icon: Target,
    title: "Skill Gaps",
    description:
      "The distance between today's skills and tomorrow's needs, prioritized as low, medium, high, or critical.",
  },
  {
    icon: ListChecks,
    title: "Explainable Recommendations",
    description:
      "Every result is traceable — the role definition, the model, the prompt version, and the timestamps behind each analysis are recorded and reproducible.",
  },
];

const transformationSteps = [
  {
    icon: Briefcase,
    phase: "Current",
    title: "Today's role",
    description:
      "Responsibilities, human involvement, and the skill set that defines the role as it exists right now.",
  },
  {
    icon: BrainCircuit,
    phase: "AI Transformation",
    title: "Structured analysis",
    description:
      "An AI model examines the role against a deterministic framework — exposure, automation, and augmentation potential.",
  },
  {
    icon: Radar,
    phase: "Future",
    title: "Tomorrow's role",
    description:
      "Future responsibilities, future skills, and prioritized gaps give the role a forward path.",
  },
];

const pipelineSteps = [
  {
    step: "01",
    title: "Define the role",
    description:
      "Name the role, set its industry, and describe the work it performs today. One structured input drives everything downstream.",
  },
  {
    step: "02",
    title: "Structured AI analysis",
    description:
      "The role definition is sent to a specialized model through a strict, versioned analysis prompt that returns a structured profile.",
  },
  {
    step: "03",
    title: "Deterministic scoring",
    description:
      "Raw model output is validated and normalized into the exposure, automation, and augmentation scores — computed deterministically, not guessed.",
  },
  {
    step: "04",
    title: "Explainable output",
    description:
      "Future responsibilities, future skills, gaps, and reskilling priorities are compiled alongside full provenance for every analysis run.",
  },
];

const architectureItems = [
  {
    icon: Layers,
    title: "Layered backend",
    description:
      "A FastAPI service with strict typed schemas, centralized validation, and separation between routes, services, and data access.",
  },
  {
    icon: Database,
    title: "Document data store",
    description:
      "MongoDB Atlas keeps roles, analyses, and runs with immutable provenance — model, prompt version, and timestamps on every record.",
  },
  {
    icon: BrainCircuit,
    title: "Managed model runtime",
    description:
      "Inference runs on Ollama Cloud — a hosted model runtime that keeps the analysis pipeline simple and self-hostable.",
  },
  {
    icon: ShieldCheck,
    title: "Auditable by design",
    description:
      "Every analysis records the model and prompt version that produced it, so results can be traced, rerun, and reproduced.",
  },
  {
    icon: Lock,
    title: "Reduced attack surface",
    description:
      "Strict request validation, explicit CORS origins, gated documentation in production, and structured error handling.",
  },
  {
    icon: Workflow,
    title: "Built for iteration",
    description:
      "A 108-test backend suite and typed React frontend keep the pipeline safe to evolve as models and prompts improve.",
  },
];

const trustPoints = [
  { icon: ShieldCheck, text: "Strict input validation on every endpoint" },
  { icon: Database, text: "Full provenance on every analysis run" },
  { icon: Lock, text: "Gated documentation and explicit CORS in production" },
  { icon: CheckCircle2, text: "Deterministic scoring — no hidden magic numbers" },
];

function Brand() {
  return (
    <Link to="/" className="flex items-center gap-3" aria-label="RoleShift AI home">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 shadow-card">
        <BrainCircuit size={20} className="text-white" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="text-[15px] font-semibold tracking-tight text-white">
          RoleShift <span className="text-brand-400">AI</span>
        </p>
        <p className="text-[11px] font-medium tracking-wide text-ink-chrome-muted">
          Enterprise Intelligence OS
        </p>
      </div>
    </Link>
  );
}

function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_60%_50%_at_50%_-10%,rgba(99,102,241,0.16),transparent_70%)]"
      />
      <div className="relative mx-auto flex max-w-[1100px] flex-col items-center px-4 pb-20 pt-20 text-center sm:px-6 sm:pb-28 sm:pt-28">
        <p className="chip">
          <Sparkles size={12} className="text-brand-400" aria-hidden="true" />
          Role Intelligence Platform
        </p>
        <h1 className="mt-6 max-w-3xl text-balance text-4xl font-bold leading-[1.08] tracking-[-0.03em] text-white sm:text-6xl">
          Understand how <span className="text-brand-400">AI</span> will transform every role.
        </h1>
        <p className="mt-6 max-w-2xl text-pretty text-base leading-relaxed text-ink-secondary sm:text-lg">
          RoleShift AI turns any role into a forward view — AI exposure, automation and
          augmentation potential, future responsibilities, future skills, and prioritized skill
          gaps, all backed by explainable, reproducible analysis.
        </p>
        <div className="mt-10 flex flex-col items-center gap-3 sm:flex-row">
          <Link to="/app" className="btn btn-primary px-6 py-3 text-sm">
            Explore Role Intelligence
            <ArrowRight size={16} aria-hidden="true" />
          </Link>
          <Link to="#how-it-works" className="btn btn-secondary px-6 py-3 text-sm">
            See How It Works
          </Link>
        </div>
        <p className="mt-8 text-xs text-ink-muted">
          Free during early development — create an account in under a minute.
        </p>
      </div>
    </section>
  );
}

function ProductSection() {
  return (
    <section id="product" className="scroll-mt-24 border-t border-border-faint bg-surface-sunken/40">
      <div className="mx-auto max-w-[1100px] px-4 py-20 sm:px-6 sm:py-24">
        <div className="max-w-2xl">
          <p className="eyebrow">The Product</p>
          <h2 className="section-title mt-3 text-2xl font-semibold tracking-[-0.02em] text-white sm:text-3xl">
            Seven lenses on every role
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-secondary sm:text-base">
            One structured analysis produces a complete, explainable picture of how AI changes a
            role — and what to do about it.
          </p>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, description }, index) => (
            <div
              key={title}
              className={cn(
                "card card-hover p-6",
                index === features.length - 1 && "sm:col-span-2 lg:col-span-1",
              )}
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-accent-soft">
                <Icon size={18} className="text-brand-400" aria-hidden="true" />
              </div>
              <h3 className="mt-4 text-[15px] font-semibold tracking-tight text-white">
                {title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function TransformationSection() {
  return (
    <section id="transformation" className="scroll-mt-24 border-t border-border-faint">
      <div className="mx-auto max-w-[1100px] px-4 py-20 sm:px-6 sm:py-24">
        <div className="max-w-2xl">
          <p className="eyebrow">The Concept</p>
          <h2 className="section-title mt-3 text-2xl font-semibold tracking-[-0.02em] text-white sm:text-3xl">
            Current → AI transformation → Future
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-secondary sm:text-base">
            Roles are not static. RoleShift AI models the journey each role takes as AI adoption
            reshapes the work.
          </p>
        </div>
        <ol className="mt-12 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_auto_1fr_auto_1fr] lg:items-stretch">
          {transformationSteps.map(({ icon: Icon, phase, title, description }, index) => (
            <li key={phase} className="contents">
              <div className="card p-6">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-accent-soft">
                    <Icon size={18} className="text-brand-400" aria-hidden="true" />
                  </div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-ink-chrome-muted">
                    {phase}
                  </p>
                </div>
                <h3 className="mt-4 text-[15px] font-semibold tracking-tight text-white">
                  {title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-ink-muted">{description}</p>
              </div>
              {index < transformationSteps.length - 1 && (
                <div
                  aria-hidden="true"
                  className="flex items-center justify-center py-2 text-brand-600 lg:px-4 lg:py-0"
                >
                  <ArrowRight size={20} className="rotate-90 lg:rotate-0" />
                </div>
              )}
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}

function PipelineSection() {
  return (
    <section
      id="how-it-works"
      className="scroll-mt-24 border-t border-border-faint bg-surface-sunken/40"
    >
      <div className="mx-auto max-w-[1100px] px-4 py-20 sm:px-6 sm:py-24">
        <div className="max-w-2xl">
          <p className="eyebrow">How It Works</p>
          <h2 className="section-title mt-3 text-2xl font-semibold tracking-[-0.02em] text-white sm:text-3xl">
            The intelligence pipeline
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-secondary sm:text-base">
            From a role description to a complete transformation profile — every step is
            deterministic, versioned, and recorded.
          </p>
        </div>
        <ol className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {pipelineSteps.map(({ step, title, description }) => (
            <li key={step} className="card card-hover flex flex-col p-6">
              <p className="text-xs font-semibold tabular-nums text-brand-500">{step}</p>
              <h3 className="mt-3 text-[15px] font-semibold tracking-tight text-white">
                {title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{description}</p>
            </li>
          ))}
        </ol>
        <div className="mt-10 flex flex-wrap gap-3">
          <Link to="/app" className="btn btn-primary">
            <Rocket size={14} aria-hidden="true" />
            Analyze your first role
          </Link>
          <Link to="/app/role-intelligence" className="btn btn-secondary">
            <GitCompareArrows size={14} aria-hidden="true" />
            See example analyses
          </Link>
        </div>
      </div>
    </section>
  );
}

function ArchitectureSection() {
  return (
    <section id="architecture" className="scroll-mt-24 border-t border-border-faint">
      <div className="mx-auto max-w-[1100px] px-4 py-20 sm:px-6 sm:py-24">
        <div className="max-w-2xl">
          <p className="eyebrow">Architecture</p>
          <h2 className="section-title mt-3 text-2xl font-semibold tracking-[-0.02em] text-white sm:text-3xl">
            Built to be trusted, built to be audited
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-ink-secondary sm:text-base">
            RoleShift AI is engineered around one idea: analysis you can explain, reproduce, and
            verify.
          </p>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {architectureItems.map(({ icon: Icon, title, description }) => (
            <div key={title} className="card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-surface-accent-soft">
                <Icon size={18} className="text-brand-400" aria-hidden="true" />
              </div>
              <h3 className="mt-4 text-[15px] font-semibold tracking-tight text-white">
                {title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-ink-muted">{description}</p>
            </div>
          ))}
        </div>
        <div className="card mt-10 p-6">
          <div className="flex items-center gap-2">
            <BarChart3 size={16} className="text-brand-400" aria-hidden="true" />
            <h3 className="section-title">What we stand behind today</h3>
          </div>
          <ul className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            {trustPoints.map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3">
                <Icon size={16} className="shrink-0 text-success-600" aria-hidden="true" />
                <span className="text-sm text-ink-secondary">{text}</span>
              </li>
            ))}
          </ul>
          <p className="mt-5 border-t border-border-faint pt-4 text-xs leading-relaxed text-ink-muted">
            RoleShift AI is in active development. We do not claim certifications, customer
            counts, or performance statistics — the platform's capabilities are exactly what you
            can verify yourself.
          </p>
        </div>
      </div>
    </section>
  );
}

function FinalCta() {
  return (
    <section className="border-t border-border-faint bg-surface-sunken/40">
      <div className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_50%_60%_at_50%_110%,rgba(99,102,241,0.14),transparent_70%)]"
        />
        <div className="relative mx-auto flex max-w-[900px] flex-col items-center px-4 py-20 text-center sm:px-6 sm:py-28">
          <p className="eyebrow">Get Started</p>
          <h2 className="section-title mt-3 text-balance text-2xl font-semibold tracking-[-0.02em] text-white sm:text-4xl">
            See what AI means for your roles
          </h2>
          <p className="mt-4 max-w-xl text-sm leading-relaxed text-ink-secondary sm:text-base">
            Explore role intelligence across industries, compare roles side by side, and trace
            every recommendation back to its source.
          </p>
          <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row">
            <Link to="/app" className="btn btn-primary px-6 py-3 text-sm">
              Explore Role Intelligence
              <ArrowRight size={16} aria-hidden="true" />
            </Link>
            <Link to="/app/new-role-analysis" className="btn btn-secondary px-6 py-3 text-sm">
              <Sparkles size={14} aria-hidden="true" />
              Analyze a new role
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border-faint bg-surface-chrome">
      <div className="mx-auto flex max-w-[1100px] flex-col items-center justify-between gap-6 px-4 py-10 sm:flex-row sm:px-6">
        <Brand />
        <nav aria-label="Footer" className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          {navigation.map(({ label, href }) => (
            <a
              key={href}
              href={href}
              className="text-sm text-ink-chrome transition-colors hover:text-white"
            >
              {label}
            </a>
          ))}
          <Link to="/app" className="text-sm text-ink-chrome transition-colors hover:text-white">
            Open Dashboard
          </Link>
        </nav>
        <p className="text-xs text-ink-chrome-muted">
          © {new Date().getFullYear()} RoleShift AI
        </p>
      </div>
    </footer>
  );
}

export function LandingPage() {
  const { hash } = useLocation();

  useEffect(() => {
    const id = hash.slice(1);
    if (id) {
      document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
    }
  }, [hash]);

  return (
    <div className="flex min-h-screen flex-col bg-surface-page">
      <header className="sticky top-0 z-40 border-b border-border-faint bg-surface-page/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1100px] items-center justify-between gap-4 px-4 sm:px-6">
          <Brand />
          <nav
            aria-label="Primary"
            className="hidden items-center gap-6 md:flex"
          >
            {navigation.map(({ label, href }) => (
              <a
                key={href}
                href={href}
                className="text-sm font-medium text-ink-chrome transition-colors hover:text-white"
              >
                {label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="btn btn-ghost hidden sm:inline-flex"
              aria-label="Sign in to your account"
            >
              Sign in
            </Link>
            <Link to="/app" className="btn btn-primary">
              Open Dashboard
              <ArrowRightLeft size={14} aria-hidden="true" />
            </Link>
          </div>
        </div>
      </header>
      <main className="flex-1">
        <Hero />
        <ProductSection />
        <TransformationSection />
        <PipelineSection />
        <ArchitectureSection />
        <FinalCta />
      </main>
      <Footer />
    </div>
  );
}