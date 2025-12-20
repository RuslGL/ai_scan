import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useEffect, useState } from "react";

type Point = {
  date: string;
  value: number;
};

type Props = {
  token: string;
  days: 7 | 30;
};

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: any[];
  label?: string;
}) {
  if (!active || !payload || !payload.length) return null;

  return (
    <div
      style={{
        background: "#020617",
        border: "1px solid #1f2937",
        borderRadius: "10px",
        padding: "10px 12px",
        color: "#e5e7eb",
        fontSize: "13px",
      }}
    >
      <div style={{ color: "#9ca3af", marginBottom: 4 }}>
        {label?.slice(8, 10)}.{label?.slice(5, 7)}
      </div>
      <div style={{ fontWeight: 600 }}>
        {payload[0].value} визитов
      </div>
    </div>
  );
}

export default function VisitsOverTime({ token, days }: Props) {
  const [data, setData] = useState<Point[]>([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);

    fetch(
      `http://localhost:8000/dashboards/metrics/visits?token=${token}&bucket=day`
    )
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((json: Point[]) => {
        setData(json.slice(-days));
      })
      .catch(() => setError(true));
  }, [token, days]);

  if (error) {
    return <div className="error">Ошибка загрузки графика</div>;
  }

  return (
    <div className="chart-block">
      <div className="chart-header">Визиты</div>

      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <XAxis
            dataKey="date"
            tickFormatter={(v) =>
              v.slice(8, 10) + "." + v.slice(5, 7)
            }
          />
          <YAxis allowDecimals={false} />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="value"
            stroke="url(#gradient)"
            strokeWidth={2}
            dot={false}
          />
          <defs>
            <linearGradient id="gradient" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#d946ef" />
              <stop offset="100%" stopColor="#22d3ee" />
            </linearGradient>
          </defs>
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
