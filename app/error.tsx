"use client";

import { useEffect } from "react";

type ErrorPageProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error("Reviewer Agent dashboard failed to load", error);
  }, [error]);

  return (
    <main className="connection-error">
      <span className="kicker">Connection needed</span>
      <h1>The Reviewer API is unavailable.</h1>
      <p>
        Start the full local stack with <code>docker compose up --build</code>, then
        try again. If you run the frontend separately, set <code>NEXT_PUBLIC_API_URL</code>
        to the public URL of the running API.
      </p>
      <button type="button" onClick={reset}>Try again</button>
    </main>
  );
}
