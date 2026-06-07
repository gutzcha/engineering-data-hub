import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const packageJson = JSON.parse(
  readFileSync(resolve(process.cwd(), "package.json"), "utf8")
) as { scripts: Record<string, string> };
const dockerfile = readFileSync(
  resolve(process.cwd(), "Dockerfile"),
  "utf8"
);
const styles = readFileSync(resolve(process.cwd(), "src/styles.css"), "utf8");

describe("App shell", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders route-aware navigation for the operational sections", () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ detail: "Authentication required" }), { status: 403 }))
    );

    render(<App />);

    const navigation = screen.getByRole("navigation", {
      name: /primary navigation/i
    });

    [
      "Home",
      "Records",
      "Projects",
      "Documents",
      "Search",
      "Dashboards",
      "Tasks",
      "Admin"
    ].forEach((section) => {
      expect(
        within(navigation).getByRole("link", { name: section })
      ).toBeInTheDocument();
    });

    expect(within(navigation).getByRole("link", { name: "Home" })).toHaveAttribute(
      "aria-current",
      "page"
    );
    expect(
      screen.getByRole("heading", { name: "Operational Overview" })
    ).toBeInTheDocument();
  });

  it("uses built frontend assets for the production container start path", () => {
    expect(packageJson.scripts.start).toContain("vite preview");
    expect(dockerfile).toMatch(/npm run build/);
  });

  it("keeps narrow viewports usable without page-level horizontal overflow", () => {
    expect(styles).not.toMatch(/body\s*{[^}]*min-width\s*:/s);
    expect(styles).toContain("@media (max-width: 900px)");
    expect(styles).toMatch(/\.app-shell\s*{[^}]*grid-template-columns:\s*1fr/s);
  });
});
