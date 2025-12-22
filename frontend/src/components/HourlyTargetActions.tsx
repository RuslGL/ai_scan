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
  visits: number;
  target_actions: number;
  conversion_rate: number;
};

type ApiResponse = {
  has_target_action: boolean;
  target_action_text?: string;
  data: Point[];
};

type Props = {
  token: string;
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

  const p = payload[0].payload as Point;

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
        {label?.slice(11, 13)}:00&nbsp;
        {label?.slice(8, 10)}.{label?.slice(5, 7)}
      </div>

      <div>Визиты: <b>{p.visits}</b></div>
      <div>Целевые действия: <b>{p.target_actions}</b></div>
      <div>
        Конверсия:{" "}
        <b>{(p.conversion_rate * 100).toFixed(1)}%</b>
      </div>
    </div>
  );
}

export default function HourlyTargetActions({ token }: Props) {
  const [data, setData] = useState<Point[]>([]);
  const [hasTarget, setHasTarget] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);

    fetch(
      `http://localhost:8000/dashboards/metrics/hourly-target-actions?token=${token}`
    )
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((json: ApiResponse) => {
        setHasTarget(json.has_target_action);
        setData(json.data || []);
      })
      .catch(() => setError(true));
  }, [token]);

  if (error) {
    return <div className="error">Ошибка загрузки графика</div>;
  }

  if (!hasTarget) {
    return (
      <div className="placeholder">
        Целевое действие не установлено
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <LineChart data={data}>
        <XAxis
          dataKey="date"
          tickFormatter={(v) => v.slice(11, 13)}
        />
        <YAxis allowDecimals={false} />
        <Tooltip content={<CustomTooltip />} />

        <Line
          type="monotone"
          dataKey="target_actions"
          stroke="url(#gradient)"
          strokeWidth={2}
          dot={false}
        />

        <defs>
          <linearGradient id="gradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#4ade80" />
          </linearGradient>
        </defs>
      </LineChart>
    </ResponsiveContainer>
  );
}
