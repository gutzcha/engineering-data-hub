import { NavLink } from "react-router-dom";
import type { ReactNode } from "react";

import type { NavigationItem } from "../app/routes";

type AppLayoutProps = {
  navigationItems: NavigationItem[];
  children: ReactNode;
};

export function AppLayout({ navigationItems, children }: AppLayoutProps) {
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
          <div className="topbar-meta" aria-label="Environment status">
            <span>Dev</span>
            <span>API: /api</span>
          </div>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
