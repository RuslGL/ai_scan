import { useEffect, useState } from "react";

type DashboardContext =
  | {
      role: "admin";
      sites: "*";
      default_site: null;
    }
  | {
      role: "user";
      sites: string[];
      default_site: string | null;
    };

type VisitPoint = {
  date: string;
  value: number;
};

export default function App() {
  const [context, setContext] = useState<DashboardContext | null>(null);
  const [siteUrl, setSiteUrl] = useState<string | null>(null);
  const [visits, setVisits] = useState<VisitPoint[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const params = new URLSearchParams(window.location.search);
  const token = params.get("token");

  // -----------------------------
  // Load dashboard context
  // -----------------------------
  useEffect(() => {
    if (!token) {
      setError("No dashboard token in URL");
      return;
    }

    fetch(`http://localhost:8000/dashboards/context?token=${token}`)
      .then((r) => {
        if (!r.ok) throw new Error("context request failed");
        return r.json();
      })
      .then((ctx: DashboardContext) => {
        setContext(ctx);

        if (ctx.role === "user") {
          setSiteUrl(ctx.default_site);
        }

        if (ctx.role === "admin") {
          // временно — первый сайт вручную
          setSiteUrl("example-site-1.tilda.ws");
        }
      })
      .catch((e) => setError(e.message));
  }, [token]);

  // -----------------------------
  // Load visits metrics
  // -----------------------------
  useEffect(() => {
    if (!token || !siteUrl) return;

    fetch(
      `http://localhost:8000/dashboards/metrics/visits?site_url=${siteUrl}&days=14&token=${token}`
    )
      .then((r) => {
        if (!r.ok) throw new Error("metrics request failed");
        return r.json();
      })
      .then(setVisits)
      .catch((e) => setError(e.message));
  }, [siteUrl, token]);

  // -----------------------------
  // Render
  // -----------------------------
  if (error) return <pre>{error}</pre>;
  if (!context) return <pre>Loading context…</pre>;
  if (!siteUrl) return <pre>Selecting site…</pre>;
  if (!visits) return <pre>Loading visits…</pre>;

  return (
    <div style={{ padding: 20 }}>
      <h2>Dashboard</h2>

      <div style={{ marginBottom: 12 }}>
        <strong>Role:</strong> {context.role}
      </div>

      <div style={{ marginBottom: 20 }}>
        <strong>Site:</strong>{" "}
        {context.role === "user" ? (
          siteUrl
        ) : (
          <select
            value={siteUrl}
            onChange={(e) => {
              setVisits(null);
              setSiteUrl(e.target.value);
            }}
          >
            <option value="example-site-1.tilda.ws">
              example-site-1.tilda.ws
            </option>
            <option value="example-site-2.tilda.ws">
              example-site-2.tilda.ws
            </option>
          </select>
        )}
      </div>

      <h3>Visits</h3>
      <pre>{JSON.stringify(visits, null, 2)}</pre>
    </div>
  );
}
