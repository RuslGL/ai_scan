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

export default function VisitsOverTime({ token, days }: Props) {
  const [data, setData] = useState<Point[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;

    setLoading(true);
    setError(null);

    fetch(
      `http://localhost:8000/dashboards/metrics/visits` +
        `?token=${token}` +
        `&bucket=day`
    )
      .then((r) => {
        if (!r.ok) throw new Error("request failed");
        return r.json();
      })
      .then((json: Point[]) => {
        // берём последние N дней
        setData(json.slice(-days));
      })
      .catch(() => {
        setError("Ошибка загрузки графика");
      })
      .finally(() => {
        setLoading(false);
      });
  }, [token, days]);

  if (loading) {
    return <div className="chart-loading">Загрузка…</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!data.length) {
    return <div className="chart-empty">Нет данных</div>;
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
          <Tooltip
            formatter={(v: number) => [`${v}`, "Визитов"]}
            labelFormatter={(l: string) =>
              l.slice(8, 10) + "." + l.slice(5, 7)
            }
          />
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
