/*
 * ===
 * File Summary
 * Path: frontend\src\features\auth\LoginPage.tsx
 * Type: typescript
 * Purpose: Frontend feature module implementing business flows and UI surfaces.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: LoginPage
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

import { useQueryClient } from "@tanstack/react-query";
import { LogIn } from "lucide-react";
import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { apiGet, apiPost } from "../../lib/api";

type CurrentUser = {
  id: number;
  username: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  roles: string[];
};

type LoginLocationState = {
  from?: string;
};

export function LoginPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as LoginLocationState | null;
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setSubmitting] = useState(false);

  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await apiGet<{ csrfToken: string }>("/accounts/csrf/");
      const user = await apiPost<CurrentUser>("/accounts/login/", {
        username: username.trim(),
        password
      });
      queryClient.setQueryData(["current-user"], user);
      navigate(locationState?.from ?? "/", { replace: true });
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "Sign in failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="workspace-header" aria-labelledby="login-title">
        <div>
          <p className="section-kicker">Session access</p>
          <h1 id="login-title">Sign in</h1>
        </div>
      </section>

      <form className="auth-form" onSubmit={submitLogin}>
        <label className="field-control">
          <span>Username</span>
          <input
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>
        <label className="field-control">
          <span>Password</span>
          <input
            autoComplete="current-password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && (
          <div className="admin-alert" role="alert">
            <strong>Sign in failed</strong>
            <span>{error}</span>
          </div>
        )}
        <button className="button button-primary" type="submit" disabled={isSubmitting}>
          <LogIn aria-hidden="true" size={16} />
          Sign in
        </button>
      </form>
    </div>
  );
}

