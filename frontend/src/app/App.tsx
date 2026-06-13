/*
 * ===
 * File Summary
 * Path: frontend\src\app\App.tsx
 * Type: typescript
 * Purpose: Frontend application shell and route composition for authenticated screens.
 * Primary responsibilities:
 * - Domain behavior is summarized for fast onboarding and avoids full-file reread.
 * - Core symbols: App
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

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { BrowserRouter } from "react-router-dom";

import { AppLayout } from "../components/AppLayout";
import { AppRoutes, navigationItems } from "./routes";

export function App() {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: false,
            staleTime: 30_000
          }
        }
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter
        future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
      >
        <AppLayout navigationItems={navigationItems}>
          <AppRoutes />
        </AppLayout>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;

