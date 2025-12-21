import { useEffect, useState } from "react";

type KPIResponse = {
  has_data: boolean;
  total: number | null;
  avg_per_day: number | null;
  max_per_day: number | null;
  delta_percent: number | null;
  delta_note: string | null;
};

type Props = {
  token: string;
  days: 7 | 30;
};

export default function VisitsKPI({ token, days }: Props) {
  const [data, setData] = useState<KPIResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    setData(null);

    fetch(
      `http://localhost:8000/dashboards/metrics/visits-kpi?token=${token}&days=${days}`
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
          gridTemplateColumns: "repeat(4, 1fr)",
          gap: "16px",
        }}
      >
        <KPIItem label="Всего визитов" value={data.total} />
        <KPIItem
          label="В среднем в день"
          value={data.avg_per_day}
          format={(v) => v.toFixed(1)}
        />
        <KPIItem label="Максимум за день" value={data.max_per_day} />
        <KPIItem
          label="Изменение"
          subtitle="(сравн. с пред. периодом)"
          value={data.delta_percent}
          format={(v) =>
            `${v > 0 ? "+" : ""}${v.toFixed(1)}%`
          }
          note={data.delta_note}
        />
      </div>
    </div>
  );
}

function KPIItem({
  label,
  subtitle,
  value,
  format,
  note,
}: {
  label: string;
  subtitle?: string;
  value: number | null;
  format?: (v: number) => string;
  note?: string | null;
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
        {subtitle && (
          <span
            style={{
              fontWeight: 400,
              color: "#6b7280",
              marginLeft: "6px",
              fontSize: "11px",
            }}
          >
            {subtitle}
          </span>
        )}
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

      {note && (
        <div
          style={{
            fontSize: "11px",
            color: "#6b7280",
            marginTop: "2px",
          }}
        >
          {note}
        </div>
      )}
    </div>
  );
}
