"use client";

import { useSyncExternalStore } from "react";

import { ReviewDashboard } from "@/components/review-dashboard";

export function ReviewDashboardShell() {
  const mounted = useSyncExternalStore(
    () => () => undefined,
    () => true,
    () => false,
  );

  if (!mounted) {
    return <div className="loading">Loading financial workspace…</div>;
  }

  return <ReviewDashboard />;
}
