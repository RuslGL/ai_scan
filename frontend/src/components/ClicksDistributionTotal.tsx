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
  total_clicks: number;
};

type ApiResponse = {
  data: Item[];
};

type Props = {
  token: string;
  days: 7 | 30;
};

function splitToTwoLines(label: string): [string, string?] {
  const parts = label.trim().split(/\s+/);
  if (parts.length <= 1) return [label];

  // делим примерно пополам по словам
  const mid = Math.ceil(parts.length / 2);
  const line1 = parts.slice(0, mid).join(" ");
  const line2 = parts.slice(mid).join(" ");

  return [line1, line2 || undefined];
}

function XAxisTick(props: any) {
  const { x, y, payload } = props;
  const label: string = String(payload?.value ?? "");

  const [l1, l2] = splitToTwoLines(label);

  // y + 12 чтобы подпись была под осью
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
        {l2 ? (
          <tspan x="0" dy="14">
            {l2}
          </tspan>
        ) : null}
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
      <div style={{ fontWeight: 600 }}>{payload[0].value} кликов</div>
    </div>
  );
}

export default function ClicksDistributionTotal({ token, days }: Props) {
  const [data, setData] = useState<{ button: string; value: number }[]>([]);
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
            value: item.total_clicks,
          }))
        );
      })
      .catch(() => setError(true));
  }, [token, days]);

  if (error) return <div className="error">Ошибка загрузки графика</div>;

  return (
    <>
      <div className="chart-header">Клики по элементам (всего)</div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={data}
          margin={{
            top: 10,
            right: 10,
            left: 10,
            bottom: 48, // критично: место под 2 строки
          }}
        >
          <XAxis
            dataKey="button"
            interval={0}
            tickLine={false}
            axisLine={{ stroke: "#1f2937" }}
            tick={<XAxisTick />}
            height={48} // чтобы Recharts зарезервировал место
          />
          <YAxis allowDecimals={false} />
          <Tooltip content={<CustomTooltip />} />
          <Bar dataKey="value" fill="#4f46e5" radius={[6, 6, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}
