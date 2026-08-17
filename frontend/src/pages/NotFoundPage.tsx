import { ArrowRight, Home } from "lucide-react";
import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-page px-4 py-16 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 shadow-card">
        <span className="text-base font-bold text-white">404</span>
      </div>
      <p className="eyebrow mt-8">Page not found</p>
      <h1 className="mt-3 max-w-md text-balance text-3xl font-bold tracking-[-0.03em] text-white sm:text-4xl">
        This page doesn't exist
      </h1>
      <p className="mt-4 max-w-md text-sm leading-relaxed text-ink-secondary sm:text-base">
        The page you're looking for may have moved or never existed. Head back to the dashboard
        or explore role intelligence.
      </p>
      <div className="mt-8 flex flex-col items-center gap-3 sm:flex-row">
        <Link to="/app" className="btn btn-primary px-6 py-3 text-sm">
          <Home size={15} aria-hidden="true" />
          Back to dashboard
        </Link>
        <Link to="/app/role-intelligence" className="btn btn-secondary px-6 py-3 text-sm">
          Explore Role Intelligence
          <ArrowRight size={15} aria-hidden="true" />
        </Link>
      </div>
    </div>
  );
}