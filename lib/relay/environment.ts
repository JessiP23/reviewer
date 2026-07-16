import {
  Environment,
  Network,
  RecordSource,
  Store,
  type RequestParameters,
  type Variables,
} from "relay-runtime";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchGraphQL(request: RequestParameters, variables: Variables) {
  const response = await fetch(`${apiUrl}/graphql`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ query: request.text, variables }),
  });
  if (!response.ok) {
    throw new Error(`GraphQL request failed (${response.status})`);
  }
  const payload = await response.json();
  if (payload.errors?.length) {
    throw new Error(payload.errors[0].message ?? "GraphQL request failed");
  }
  return payload;
}

export const relayEnvironment = new Environment({
  network: Network.create(fetchGraphQL),
  store: new Store(new RecordSource()),
});

export { apiUrl };

