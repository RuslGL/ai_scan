import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { useEffect, useState } from "react";

type Bucket = {
  from: number;
  to: number;
  value: number;
};

type ApiResponse = {
  has_data: boolean;
  distribution: Bucket[];
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
        Глубина {label}%
      </div>
      <div style={{ fontWeight: 600 }}>
        {payload[0].value} сессий
      </div>
    </div>
  );
}

export default function ScrollDepthDistribution({
  token,
  days,
}: Props) {
  const [data, setData] = useState<
    { label: string; value: number }[]
  >([]);
  const [hasData, setHasData] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);

    fetch(
      `http://localhost:8000/dashboards/metrics/scroll-depth-distribution?token=${token}&days=${days}`
    )
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((json: ApiResponse) => {
        if (!json.has_data) {
          setHasData(false);
          setData([]);
          return;
        }

        setHasData(true);
        setData(
          json.distribution.map((b) => ({
            label: `${b.from}–${b.to}`,
            value: b.value,
          }))
        );
      })
      .catch(() => setError(true));
  }, [token, days]);

  if (error) {
    return <div className="error">Ошибка загрузки графика</div>;
  }

  if (!hasData) {
    return <div className="placeholder">Нет данных</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data}>
        <XAxis dataKey="label" />
        <YAxis allowDecimals={false} />
        <Tooltip content={<CustomTooltip />} />
        <Bar
          dataKey="value"
          fill="#4f46e5"
          radius={[6, 6, 0, 0]}
        />
      </BarChart>
    </ResponsiveContainer>
  );
}
