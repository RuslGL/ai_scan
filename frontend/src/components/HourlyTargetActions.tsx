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

// -------------------------
// helpers
// -------------------------
function formatDateTime(iso: string) {
  // 2025-12-20T09:00:00 -> 20.12.2025, 09:00
  return `${iso.slice(8, 10)}.${iso.slice(5, 7)}.${iso.slice(
    0,
    4
  )} ${iso.slice(11, 16)}`;
}

/**
 * Показываем дату ТОЛЬКО при смене дня
 */
let lastRenderedDay: string | null = null;
function formatDateBoundaryTick(iso: string) {
  const day = iso.slice(8, 10);
  const month = iso.slice(5, 7);

  if (lastRenderedDay !== day) {
    lastRenderedDay = day;
    return `${day}.${month}`;
  }

  return "";
}

// -------------------------
// tooltip
// -------------------------
function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: any[];
  label?: string;
}) {
  if (!active || !payload || !payload.length || !label) return null;

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
        minWidth: "180px",
      }}
    >
      <div
        style={{
          fontSize: "12px",
          fontWeight: 600,
          marginBottom: "6px",
        }}
      >
        Почасовые целевые действия
      </div>

      <div style={{ color: "#9ca3af", marginBottom: 6 }}>
        {formatDateTime(label)}
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

// -------------------------
// component
// -------------------------
export default function HourlyTargetActions({ token }: Props) {
  const [data, setData] = useState<Point[]>([]);
  const [hasTarget, setHasTarget] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    lastRenderedDay = null; // сброс между рендерами

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
          tickFormatter={formatDateBoundaryTick}
          interval={0}
          minTickGap={20}
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
