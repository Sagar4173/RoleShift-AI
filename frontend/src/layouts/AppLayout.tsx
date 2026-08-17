import {
  ArrowRightLeft,
  BrainCircuit,
  CircleDashed,
  GraduationCap,
  LayoutDashboard,
  LogOut,
  Menu,
  Radar,
  Settings,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { useConnectivity } from "../hooks/useConnectivity";
import { cn } from "../lib/utils";

const primaryNavigation = [
  { to: "/app", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/app/role-intelligence", label: "Role Intelligence", icon: Radar, end: false },
  { to: "/app/compare", label: "Compare Roles", icon: ArrowRightLeft, end: false },
  { to: "/app/new-role-analysis", label: "New Role Analysis", icon: Sparkles, end: false },
  { to: "/app/skills", label: "Skills & Reskilling", icon: GraduationCap, end: false },
];

const secondaryNavigation = [{ to: "/app/settings", label: "Settings", icon: Settings, end: false }];

function sectionTitle(pathname: string): string {
  if (pathname.startsWith("/app/role-intelligence")) return "Role Intelligence";
  if (pathname.startsWith("/app/compare")) return "Compare Roles";
  if (pathname.startsWith("/app/new-role-analysis")) return "New Role Analysis";
  if (pathname.startsWith("/app/skills")) return "Skills & Reskilling";
  if (pathname.startsWith("/app/settings")) return "Settings";
  return "Overview";
}

function Brand() {
  return (
    <div className="flex items-center gap-3 border-b border-surface-chrome-soft px-5 py-6">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 shadow-card">
        <BrainCircuit size={20} className="text-white" aria-hidden="true" />
      </div>
      <div className="min-w-0">
        <p className="truncate text-[15px] font-semibold tracking-tight text-white">
          RoleShift <span className="text-brand-400">AI</span>
        </p>
        <p className="truncate text-[11px] font-medium tracking-wide text-ink-chrome-muted">
          Enterprise Intelligence OS
        </p>
      </div>
    </div>
  );
}

interface NavItemsProps {
  onNavigate?: () => void;
}

function NavItems({ onNavigate }: NavItemsProps) {
  const items = [
    ...primaryNavigation.map((item) => ({ ...item, section: "Workspace" })),
    ...secondaryNavigation.map((item) => ({ ...item, section: "Platform" })),
  ];
  let lastSection = "";
  return (
    <>
      {items.map(({ to, label, icon: Icon, end, section }) => {
        const showSectionHeader = section !== lastSection;
        lastSection = section;
        return (
          <div key={to}>
            {showSectionHeader && (
              <p className="px-3 pb-1.5 pt-5 text-[11px] font-semibold uppercase tracking-wider text-ink-chrome-muted first:pt-0">
                {section}
              </p>
            )}
            <NavLink
              to={to}
              end={end}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "group relative flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-surface-chrome-soft text-white"
                    : "text-ink-chrome hover:bg-surface-chrome-soft hover:text-white",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <span
                    aria-hidden="true"
                    className={cn(
                      "absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-brand-500 transition-opacity",
                      isActive ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <Icon
                    size={16}
                    className={cn(
                      "shrink-0 transition-colors",
                      isActive ? "text-brand-400" : "text-ink-chrome-muted group-hover:text-brand-400",
                    )}
                  />
                  {label}
                </>
              )}
            </NavLink>
          </div>
        );
      })}
    </>
  );
}

function SidebarFooter() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const initials = user
    ? user.display_name
        .split(/\s+/)
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "??";

  return (
    <div className="border-t border-surface-chrome-soft p-4">
      <div className="flex items-center gap-2.5 rounded-lg bg-surface-chrome-soft px-3 py-2.5">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand-600 text-xs font-semibold text-white">
          {initials}
        </div>
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-white">{user?.display_name}</p>
          <p className="truncate text-[11px] text-ink-chrome-muted">{user?.email}</p>
        </div>
        <button
          type="button"
          onClick={() => {
            navigate("/", { replace: true });
            void logout();
          }}
          className="ml-auto shrink-0 rounded-md p-1.5 text-ink-chrome-muted transition-colors hover:bg-surface-chrome-raised hover:text-white focus:outline-none"
          aria-label="Sign out"
          title="Sign out"
        >
          <LogOut size={15} aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col bg-surface-chrome">
      <Brand />
      <nav
        className="mt-1 flex-1 space-y-0.5 overflow-y-auto px-3 pb-4"
        aria-label="Main navigation"
      >
        <NavItems onNavigate={onNavigate} />
      </nav>
      <SidebarFooter />
    </div>
  );
}

function ConnectionStatus() {
  const status = useConnectivity();
  if (status === "checking") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-border-default bg-surface-sunken px-2.5 py-1 text-[11px] font-medium text-ink-muted">
        <CircleDashed size={12} className="animate-spin" aria-hidden="true" />
        Checking…
      </span>
    );
  }
  const connected = status === "connected";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium",
        connected
          ? "border-success-100 bg-success-50 text-success-700"
          : "border-danger-100 bg-danger-50 text-danger-700",
      )}
      title={connected ? "Backend API is reachable" : "Backend API is unreachable"}
    >
      <span
        aria-hidden="true"
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          connected ? "bg-success-600" : "bg-danger-600 animate-soft-pulse",
        )}
      />
      {connected ? "API connected" : "API offline"}
    </span>
  );
}

export function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const { user } = useAuth();
  const title = sectionTitle(location.pathname);
  const initials = user
    ? user.display_name
        .split(/\s+/)
        .map((part) => part[0])
        .join("")
        .slice(0, 2)
        .toUpperCase()
    : "??";

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="flex min-h-screen bg-surface-page">
      {/* Desktop sidebar */}
      <aside className="hidden w-64 shrink-0 lg:block">
        <div className="fixed inset-y-0 left-0 w-64">
          <SidebarContent />
        </div>
      </aside>

      {/* Mobile sidebar */}
      {sidebarOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <div
            className="absolute inset-0 bg-surface-overlay"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute inset-y-0 left-0 w-64 bg-surface-chrome shadow-pop">
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              className="absolute right-3 top-5 rounded-md p-1 text-ink-chrome hover:bg-surface-chrome-soft hover:text-white focus:outline-none"
              aria-label="Close navigation"
            >
              <X size={18} />
            </button>
            <SidebarContent onNavigate={() => setSidebarOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-3 border-b border-border-default bg-surface-card/90 px-4 backdrop-blur sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="rounded-md p-1.5 text-ink-secondary hover:bg-surface-card-hover hover:text-ink-primary focus:outline-none lg:hidden"
              aria-label="Open navigation"
            >
              <Menu size={20} />
            </button>
            <div className="min-w-0">
              <p className="eyebrow">RoleShift AI</p>
              <p className="truncate text-sm font-semibold text-ink-primary">{title}</p>
            </div>
          </div>

          <div className="flex shrink-0 items-center gap-2 sm:gap-3">
            <ConnectionStatus />
            <Link to="/app/new-role-analysis" className="btn btn-primary hidden sm:inline-flex">
              <Sparkles size={14} aria-hidden="true" />
              New Role Analysis
            </Link>
            <Link
              to="/app/new-role-analysis"
              className="btn btn-primary sm:hidden"
              aria-label="New Role Analysis"
            >
              <Sparkles size={14} aria-hidden="true" />
            </Link>
            <div
              className="flex h-8 w-8 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700"
              aria-hidden="true"
            >
              {initials}
            </div>
          </div>
        </header>

        <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 sm:py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
