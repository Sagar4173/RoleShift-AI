import { ShieldX, Trash2, UserRound } from "lucide-react";
import { useCallback, useState } from "react";

import { Card } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { ForbiddenState } from "../components/ui/ForbiddenState";
import { PageHeader } from "../components/ui/PageHeader";
import { Skeleton } from "../components/ui/Skeleton";
import { useAuth } from "../context/AuthContext";
import { useApi } from "../hooks/useApi";
import { api } from "../services/api";
import type { Member, MemberRole } from "../types/api";

const ROLE_LABELS: Record<MemberRole, string> = {
  owner: "Owner",
  admin: "Admin",
  analyst: "Analyst",
  viewer: "Viewer",
};

const ROLE_OPTIONS: MemberRole[] = ["owner", "admin", "analyst", "viewer"];
const ADMIN_MANAGED_ROLES: MemberRole[] = ["analyst", "viewer"];
const MANAGER_ROLES: MemberRole[] = ["owner", "admin"];

export function MembersPage() {
  const { user } = useAuth();
  const myRole = user?.role ?? null;
  const isManager = myRole !== null && MANAGER_ROLES.includes(myRole);
  const [actionError, setActionError] = useState<string | null>(null);

  const members = useApi(() => api.listMembers(0, 100));
  const refresh = useCallback(() => {
    setActionError(null);
    members.refetch();
  }, [members]);

  const changeRole = async (member: Member, role: MemberRole) => {
    setActionError(null);
    try {
      await api.changeMemberRole(member.user_id, role);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to update role");
    }
  };

  const removeMember = async (member: Member) => {
    if (!window.confirm(`Remove ${member.display_name} from this organization?`)) return;
    setActionError(null);
    try {
      await api.removeMember(member.user_id);
      refresh();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Failed to remove member");
    }
  };

  if (!isManager) {
    return (
      <div className="animate-fade-up">
        <PageHeader
          eyebrow="Workspace"
          title="Members"
          description="Who belongs to this organization and what they can do."
        />
        <ForbiddenState
          title="Member management requires owner or admin access"
          description="Only owner and admin members can view and manage the organization roster."
        />
      </div>
    );
  }

  const optionsFor = (member: Member): MemberRole[] => {
    if (myRole === "owner") return ROLE_OPTIONS;
    if (member.role === "owner" || member.role === "admin") return [member.role];
    return ADMIN_MANAGED_ROLES;
  };

  const canRemove = (member: Member): boolean => {
    if (myRole === "owner") return true;
    return member.role === "analyst" || member.role === "viewer";
  };

  return (
    <div className="animate-fade-up">
      <PageHeader
        eyebrow="Workspace"
        title="Members"
        description="Who belongs to this organization and what they can do. Server-enforced roles: the UI only reflects what the API allows."
      />

      {actionError && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-lg border border-danger-100 bg-danger-50 px-3 py-2.5 text-xs text-danger-700"
        >
          <ShieldX size={14} className="mt-0.5 shrink-0" aria-hidden="true" />
          <span>{actionError}</span>
        </div>
      )}

      <Card>
        {members.loading ? (
          <div className="space-y-3 p-4">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : members.error || !members.data ? (
          <ErrorState
            title="Couldn't load members"
            description={members.error ?? "The backend is unreachable."}
            onRetry={refresh}
          />
        ) : members.data.items.length === 0 ? (
          <EmptyState
            icon={<UserRound size={24} />}
            title="No members yet"
            description="Members join this organization when they register."
          />
        ) : (
          <ul className="divide-y divide-border-default">
            {members.data.items.map((member) => {
              const isSelf = member.user_id === user?.id;
              return (
                <li key={member.user_id} className="flex flex-wrap items-center gap-3 px-4 py-3.5">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-brand-100 text-xs font-semibold text-brand-700">
                    {member.display_name
                      .split(/\s+/)
                      .map((part) => part[0])
                      .join("")
                      .slice(0, 2)
                      .toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-ink-primary">
                      {member.display_name}
                      {isSelf && <span className="ml-2 text-[11px] text-ink-muted">(you)</span>}
                    </p>
                    <p className="truncate text-xs text-ink-muted">{member.email}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    {isSelf && myRole === "owner" ? (
                      <span className="text-xs font-medium capitalize text-ink-muted">
                        {ROLE_LABELS[member.role]}
                      </span>
                    ) : (
                      <select
                        aria-label={`Role for ${member.display_name}`}
                        value={member.role}
                        onChange={(event) => changeRole(member, event.target.value as MemberRole)}
                        className="input !w-auto !py-1.5 text-xs"
                      >
                        {optionsFor(member).map((role) => (
                          <option key={role} value={role}>
                            {ROLE_LABELS[role]}
                          </option>
                        ))}
                      </select>
                    )}
                    {canRemove(member) && (
                      <button
                        type="button"
                        onClick={() => removeMember(member)}
                        className="rounded-md p-1.5 text-ink-muted transition-colors hover:bg-danger-50 hover:text-danger-600 focus:outline-none"
                        aria-label={`Remove ${member.display_name}`}
                        title="Remove from organization"
                      >
                        <Trash2 size={15} aria-hidden="true" />
                      </button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </Card>
    </div>
  );
}