import { useEffect, useState } from "react";

type KPIResponse =
  | { has_data: false }
  | {
      has_data: true;
      total_sessions: number;
      total_clicks: number;
      sessions_with_clicks: number;
      click_sessions_percent: number;
    };

type Props = {
  token: string;
  days: 7 | 30;
};

export default function ClicksKPI({ token, days }: Props) {
  const [data, setData] = useState<KPIResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    setData(null);

    fetch(
      `http://localhost:8000/dashboards/metrics/clicks-kpi?token=${token}&days=${days}`
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

  if (!data.has_data) {
    return <div className="kpi-card">Нет данных</div>;
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
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "16px",
        }}
      >
        <KPIItem
          label="Всего сессий"
          value={data.total_sessions}
        />

        <KPIItem
          label="Всего кликов"
          value={data.total_clicks}
        />

        <KPIItem
          label="Сессий с кликами"
          value={data.sessions_with_clicks}
        />

        <KPIItem
          label="% сессий с кликами"
          value={data.click_sessions_percent}
          format={(v) => `${v.toFixed(1)}%`}
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
          marginBottom: "2px",
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
