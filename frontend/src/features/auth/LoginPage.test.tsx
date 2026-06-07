import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { LoginPage } from "./LoginPage";

function renderLogin() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } }
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/login"]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<h1>Operational Overview</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

describe("LoginPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("establishes csrf before posting credentials and returns to the app", async () => {
    const user = userEvent.setup();
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "/api/accounts/csrf/") {
        document.cookie = "csrftoken=login-token";
        return jsonResponse({ csrfToken: "login-token" });
      }
      if (url === "/api/accounts/login/") {
        return jsonResponse({
          id: 1,
          username: "engineer",
          email: "",
          is_active: true,
          is_superuser: false,
          roles: ["Engineer"]
        });
      }
      return jsonResponse({ detail: "Not found" }, 404);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderLogin();
    await user.type(screen.getByLabelText("Username"), "engineer");
    await user.type(screen.getByLabelText("Password"), "test-pass");
    await user.click(screen.getByRole("button", { name: /^Sign in$/i }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Operational Overview" })).toBeInTheDocument();
    });
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/accounts/login/",
      expect.objectContaining({
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": "login-token"
        },
        method: "POST"
      })
    );
  });
});
