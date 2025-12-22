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
  conversion_rate: number; // 0..1
};

type ApiResponse =
  | {
      has_target_action: false;
      data: [];
    }
  | {
      has_target_action: true;
      target_action_text: string;
      data: Point[];
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

  const point = payload[0].payload as Point;

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
        {point.visits} визитов
      </div>

      <div style={{ fontWeight: 600 }}>
        {point.target_actions} целевых
      </div>

      <div style={{ color: "#22d3ee" }}>
        Конверсия: {(point.conversion_rate * 100).toFixed(1)}%
      </div>
    </div>
  );
}

export default function DailyTargetActions({ token, days }: Props) {
  const [data, setData] = useState<Point[]>([]);
  const [hasTargetAction, setHasTargetAction] = useState<boolean | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    setHasTargetAction(null);

    fetch(
      `http://localhost:8000/dashboards/metrics/daily-target-actions?token=${token}&days=${days}`
    )
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((json: ApiResponse) => {
        if (!json.has_target_action) {
          setHasTargetAction(false);
          setData([]);
          return;
        }

        setHasTargetAction(true);
        setData(json.data);
      })
      .catch(() => setError(true));
  }, [token, days]);

  // -------------------------
  // ERROR
  // -------------------------
  if (error) {
    return <div className="error">Ошибка загрузки графика</div>;
  }

  // -------------------------
  // TARGET ACTION NOT SET
  // -------------------------
  if (hasTargetAction === false) {
    return (
      <div className="placeholder">
        Целевое действие не установлено
      </div>
    );
  }

  // -------------------------
  // LOADING
  // -------------------------
  if (hasTargetAction === null) {
    return <div className="placeholder">Загрузка…</div>;
  }

  // -------------------------
  // CHART
  // -------------------------
  return (
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
          dataKey="target_actions"
          stroke="url(#gradient)"
          strokeWidth={2}
          dot={false}
        />
        <defs>
          <linearGradient id="gradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#22d3ee" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
        </defs>
      </LineChart>
    </ResponsiveContainer>
  );
}
