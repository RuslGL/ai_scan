import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useEffect, useState } from "react";

type Item = {
  button: string;
  avg_clicks_per_session: number;
};

type ApiResponse = {
  data: Item[];
};

type Props = {
  token: string;
  days: 7 | 30;
};

/* ---------- helpers ---------- */

function splitToTwoLines(label: string): [string, string?] {
  const parts = label.trim().split(/\s+/);
  if (parts.length <= 1) return [label];

  const mid = Math.ceil(parts.length / 2);
  return [
    parts.slice(0, mid).join(" "),
    parts.slice(mid).join(" ") || undefined,
  ];
}

function XAxisTick(props: any) {
  const { x, y, payload } = props;
  const label = String(payload?.value ?? "");

  const [l1, l2] = splitToTwoLines(label);

  return (
    <g transform={`translate(${x},${y})`}>
      <text
        x={0}
        y={12}
        textAnchor="middle"
        fill="#9ca3af"
        fontSize={12}
      >
        <tspan x="0" dy="0">
          {l1}
        </tspan>
        {l2 && (
          <tspan x="0" dy="14">
            {l2}
          </tspan>
        )}
      </text>
    </g>
  );
}

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
      <div style={{ color: "#9ca3af", marginBottom: 4 }}>{label}</div>
      <div style={{ fontWeight: 600 }}>
        {payload[0].value.toFixed(2)} клика / сессию
      </div>
    </div>
  );
}

/* ---------- component ---------- */

export default function ClicksDistributionAvg({ token, days }: Props) {
  const [data, setData] = useState<
    { button: string; value: number }[]
  >([]);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);

    fetch(
      `http://localhost:8000/dashboards/metrics/clicks-distribution?token=${token}&days=${days}`
    )
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((json: ApiResponse) => {
        setData(
          (json.data || []).map((item) => ({
            button: item.button,
            value: Number(item.avg_clicks_per_session.toFixed(2)),
          }))
        );
      })
      .catch(() => setError(true));
  }, [token, days]);

  if (error) {
    return <div className="error">Ошибка загрузки графика</div>;
  }

  return (
    <>
      <div className="chart-header">
        Среднее число кликов за сессию
      </div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={data}
          margin={{
            top: 10,
            right: 10,
            left: 10,
            bottom: 48, // одинаково с первым графиком
          }}
        >
          <XAxis
            dataKey="button"
            interval={0}
            tickLine={false}
            axisLine={{ stroke: "#1f2937" }}
            tick={<XAxisTick />}
            height={48}
          />
          <YAxis allowDecimals />
          <Tooltip content={<CustomTooltip />} />
          <Bar
            dataKey="value"
            fill="#4f46e5" // тот же цвет, что и в ScrollDepth
            radius={[6, 6, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}
