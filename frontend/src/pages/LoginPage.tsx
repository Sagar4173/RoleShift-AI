import { ArrowLeft, BrainCircuit, Eye, EyeOff, LoaderCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { ApiError } from "../services/api";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function LoginPage() {
  const { login, status } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
  const submittedRef = useRef(false);

  useEffect(() => {
    if (status === "authenticated" && !submittedRef.current) {
      navigate("/app", { replace: true });
    }
  }, [status, navigate]);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function validate(): boolean {
    const errors: { email?: string; password?: string } = {};
    if (!email.trim()) {
      errors.email = "Email is required";
    } else if (!EMAIL_PATTERN.test(email.trim())) {
      errors.email = "Enter a valid email address";
    }
    if (!password) {
      errors.password = "Password is required";
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!validate()) return;
    submittedRef.current = true;
    setSubmitting(true);
    setFormError(null);
    try {
      await login({ email: email.trim(), password });
      navigate(from ?? "/app", { replace: true });
    } catch (err) {
      if (err instanceof ApiError) {
        setFormError(err.status === 401 ? "Invalid email or password" : err.message);
      } else {
        setFormError("Unable to sign in. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-surface-page px-4 py-12">
      <Link
        to="/"
        className="mb-8 inline-flex items-center gap-2 text-sm text-ink-chrome transition-colors hover:text-white"
      >
        <ArrowLeft size={15} aria-hidden="true" />
        Back to home
      </Link>

      <div className="w-full max-w-sm">
        <div className="mb-8 flex flex-col items-center text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 shadow-card">
            <BrainCircuit size={24} className="text-white" aria-hidden="true" />
          </div>
          <p className="mt-4 text-lg font-semibold tracking-tight text-white">
            Sign in to RoleShift <span className="text-brand-400">AI</span>
          </p>
          <p className="mt-1 text-sm text-ink-muted">Continue to role intelligence</p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label htmlFor="email" className="label">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="input"
              placeholder="you@company.com"
              aria-invalid={fieldErrors.email ? true : undefined}
              aria-describedby={fieldErrors.email ? "email-error" : undefined}
            />
            {fieldErrors.email && (
              <p id="email-error" className="mt-1.5 text-xs text-danger-700">
                {fieldErrors.email}
              </p>
            )}
          </div>

          <div>
            <label htmlFor="password" className="label">
              Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="input pr-10"
                placeholder="••••••••"
                aria-invalid={fieldErrors.password ? true : undefined}
                aria-describedby={fieldErrors.password ? "password-error" : undefined}
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1.5 text-ink-muted transition-colors hover:text-ink-primary focus:outline-none"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff size={16} aria-hidden="true" />
                ) : (
                  <Eye size={16} aria-hidden="true" />
                )}
              </button>
            </div>
            {fieldErrors.password && (
              <p id="password-error" className="mt-1.5 text-xs text-danger-700">
                {fieldErrors.password}
              </p>
            )}
          </div>

          {formError && (
            <div
              role="alert"
              className="rounded-lg border border-danger-100 bg-danger-50 px-3 py-2.5 text-sm text-danger-700"
            >
              {formError}
            </div>
          )}

          <button type="submit" className="btn btn-primary w-full py-2.5 text-sm" disabled={submitting}>
            {submitting ? (
              <>
                <LoaderCircle size={15} className="animate-spin" aria-hidden="true" />
                Signing in…
              </>
            ) : (
              "Sign in"
            )}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-ink-muted">
          No account yet?{" "}
          <Link
            to="/signup"
            state={location.state}
            className="font-medium text-brand-400 transition-colors hover:text-brand-300"
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}