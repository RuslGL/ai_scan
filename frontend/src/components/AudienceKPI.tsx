import { useEffect, useState } from "react";

type KPIResponse = {
  has_data: boolean;
  sessions: number | null;
  unique_users: number | null;
  avg_session_duration: number | null; // seconds
};

type Props = {
  token: string;
  days: 7 | 30;
};

export default function AudienceKPI({ token, days }: Props) {
  const [data, setData] = useState<KPIResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    setData(null);

    fetch(
      `http://localhost:8000/dashboards/metrics/audience-kpi?token=${token}&days=${days}`
    )
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((json: KPIResponse) => setData(json))
      .catch(() => setError(true));
  }, [token, days]);

  if (error) {
    return <div className="kpi-card">Ошибка загрузки KPI</div>;
  }

  if (!data) {
    return <div className="kpi-card">Загрузка…</div>;
  }

  return (
    <div
      className="kpi-card"
      style={{
        border: "1px solid #1f2937",
        borderRadius: "14px",
        padding: "16px 20px",
        marginBottom: "24px",
        background: "linear-gradient(135deg, #020617, #020617)",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, 1fr)",
          gap: "16px",
        }}
      >
        <KPIItem
          label="Сессий"
          value={data.sessions}
        />

        <KPIItem
          label="Уникальные пользователи"
          value={data.unique_users}
        />

        <KPIItem
          label="Средняя длительность (мин)"
          value={data.avg_session_duration}
          format={formatMinutes}
        />
      </div>
    </div>
  );
}

function KPIItem({
  label,
  value,
  format,
}: {
  label: string;
  value: number | null;
  format?: (v: number) => string;
}) {
  const displayValue =
    value === null ? "—" : format ? format(value) : value.toString();

  return (
    <div>
      <div
        style={{
          fontSize: "13px",
          fontWeight: 600,
          color: "#e5e7eb",
          marginBottom: "4px",
        }}
      >
        {label}
      </div>

      <div
        style={{
          fontSize: "22px",
          fontWeight: 600,
          color: "#e5e7eb",
        }}
      >
        {displayValue}
      </div>
    </div>
  );
}

function formatMinutes(seconds: number): string {
  if (!seconds || seconds <= 0) return "—";
  return (seconds / 60).toFixed(1);
}
