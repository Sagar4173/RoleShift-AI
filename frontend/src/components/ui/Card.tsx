import type { ReactNode } from "react";

import { cn } from "../../lib/utils";

interface CardProps {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
  hover?: boolean;
}

export function Card({ title, subtitle, actions, children, className, hover }: CardProps) {
  return (
    <section className={cn("card", hover && "card-hover", className)}>
      {(title || subtitle || actions) && (
        <header className="card-header">
          <div className="min-w-0">
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="card-subtitle">{subtitle}</p>}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </header>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}
