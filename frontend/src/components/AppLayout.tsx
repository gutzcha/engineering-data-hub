/*
 * ===
 * File Summary
 * Path: frontend\src\components\AppLayout.tsx
 * Type: typescript
 * Purpose: Reusable UI component primitives used across feature screens.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: AppLayout
 * Inputs:
 * - Downstream and upstream interactions in the same domain.
 * Outputs:
 * - API payloads, records, side effects, or UI views depending on file role.
 * Dependencies:
 * - Shared runtime services and adjacent domain modules.
 * Known risks:
 * - Validate behavior after migrations, dependency upgrades, or contract changes.
 * ===
 * 
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LogIn, LogOut } from "lucide-react";
import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

import type { NavigationItem } from "../app/routes";
import { apiGet, apiPost } from "../lib/api";

type AppLayoutProps = {
  navigationItems: NavigationItem[];
  children: ReactNode;
};

type CurrentUser = {
  username: string;
  roles: string[];
};

export function AppLayout({ navigationItems, children }: AppLayoutProps) {
  const queryClient = useQueryClient();
  const currentUser = useQuery({
    queryKey: ["current-user"],
    queryFn: () => apiGet<CurrentUser>("/accounts/me/"),
    retry: false
  });
  const logout = useMutation({
    mutationFn: async () => {
      await apiGet<{ csrfToken: string }>("/accounts/csrf/");
      await apiPost<void>("/accounts/logout/", {});
    },
    onSettled: () => {
      queryClient.removeQueries({ queryKey: ["current-user"] });
    }
  });

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">
            PE
          </span>
          <div>
            <p>Plastic Engineering</p>
            <strong>Data Hub</strong>
          </div>
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          {navigationItems.map((item) => {
            const Icon = item.icon;

            return (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.path === "/"}
                className={({ isActive }) =>
                  isActive ? "nav-link nav-link-active" : "nav-link"
                }
              >
                <Icon aria-hidden="true" size={18} strokeWidth={2} />
                <span>{item.label}</span>
              </NavLink>
            );
          })}
        </nav>
      </aside>

      <div className="main-column">
        <header className="topbar">
          <div>
            <span className="eyebrow">Workspace</span>
            <strong>Engineering Operations</strong>
          </div>
          <div className="topbar-actions">
            <div className="topbar-meta" aria-label="Environment status">
              <span>Operational</span>
              <span>Secure workspace</span>
            </div>
            {currentUser.isSuccess ? (
              <div className="topbar-user" aria-label="Current user">
                <span>{currentUser.data.username}</span>
                <button
                  className="topbar-auth-button"
                  type="button"
                  onClick={() => logout.mutate()}
                  disabled={logout.isPending}
                >
                  <LogOut aria-hidden="true" size={15} />
                  Sign out
                </button>
              </div>
            ) : (
              <NavLink className="topbar-auth-link" to="/login">
                <LogIn aria-hidden="true" size={15} />
                Sign in
              </NavLink>
            )}
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}

