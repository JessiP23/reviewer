import type { Metadata } from "next";
import Link from "next/link";

import { RelayProvider } from "@/components/relay-provider";

import "./globals.css";

export const metadata: Metadata = {
  title: "LedgerLens · Evidence-first financial review",
  description: "Auditable financial statement review for small and midsize businesses.",
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <nav className="nav">
          <Link href="/" className="brand"><span>LL</span> LedgerLens</Link>
          <div>
            <span className="environment">Reviewer workspace</span>
            <Link href="/">Agent</Link>
            <Link href="/dashboard">Dashboard</Link>
            <a href={`${apiUrl}/graphql`} target="_blank" rel="noreferrer">API</a>
          </div>
        </nav>
        <RelayProvider>{children}</RelayProvider>
        <footer><span>Decision support, not accounting or financial advice.</span><span>Rule set financial-core/1.0.0</span></footer>
      </body>
    </html>
  );
}
