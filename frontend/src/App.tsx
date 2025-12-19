import { useEffect, useState } from "react";

type Point = {
  date: string;
  value: number;
};

export default function App() {
  const [data, setData] = useState<Point[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(
      "http://localhost:8000/dashboards/metrics/visits?site_url=example-site-1.tilda.ws&days=14"
    )
      .then((r) => {
        if (!r.ok) throw new Error("request failed");
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <pre>{error}</pre>;

  return (
    <div style={{ padding: 20 }}>
      <h2>Visits</h2>
      <pre>{JSON.stringify(data, null, 2)}</pre>
    </div>
  );
}
