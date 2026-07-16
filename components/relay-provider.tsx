"use client";

import { RelayEnvironmentProvider } from "react-relay";

import { relayEnvironment } from "@/lib/relay/environment";

export function RelayProvider({ children }: { children: React.ReactNode }) {
  return (
    <RelayEnvironmentProvider environment={relayEnvironment}>
      {children}
    </RelayEnvironmentProvider>
  );
}

