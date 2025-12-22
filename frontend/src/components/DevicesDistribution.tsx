import { useEffect, useMemo, useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  LabelList,
} from "recharts";

type ApiItem = {
  device: string;
  sessions: number;
};

type ApiResponse = {
  has_data: boolean;
  total_sessions: number;
  distribution: ApiItem[];
};

type Props = {
  token: string;
  days: 7 | 30;
};

type ChartItem = {
  name: string;
  sessions: number;
  percent: number;
};

export default function DevicesDistribution({ token, days }: Props) {
  const [data, setData] = useState<ApiResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    setData(null);

    fetch(
      `http://localhost:8000/dashboards/metrics/devices-distribution?token=${token}&days=${days}`
    )
      .then((r) => {
        if (!r.ok) throw new Error();
        return r.json();
      })
      .then((json: ApiResponse) => setData(json))
      .catch(() => setError(true));
  }, [token, days]);

  const chartData: ChartItem[] = useMemo(() => {
    if (!data || !data.has_data) return [];

    return data.distribution.map((item) => ({
      name:
        item.device === "desktop"
          ? "Desktop"
          : item.device === "mobile"
          ? "Mobile"
          : item.device,
      sessions: item.sessions,
      percent: Math.round(
        (item.sessions / data.total_sessions) * 100
      ),
    }));
  }, [data]);

  if (error) {
    return <div className="chart-card">Ошибка загрузки</div>;
  }

  if (!data) {
    return <div className="chart-card">Загрузка…</div>;
  }

  if (!data.has_data) {
    return <div className="chart-card">Нет данных</div>;
  }

  return (
    <div className="chart-card">
      {/* ⬅️ ДОБАВЛЕН ЗАГОЛОВОК */}
      <div className="chart-header">Устройства</div>

      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={chartData}
          margin={{ top: 28, right: 16, left: 0, bottom: 0 }}
        >
          <XAxis
            dataKey="name"
            tick={{ fill: "#9ca3af", fontSize: 12 }}
          />
          <YAxis
            tick={{ fill: "#6b7280", fontSize: 11 }}
            axisLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgba(255,255,255,0.04)" }}
            contentStyle={{
              background: "#020617",
              border: "1px solid #1f2937",
              borderRadius: "10px",
            }}
            labelStyle={{ color: "#e5e7eb" }}
            formatter={(v: number) => [`${v}`, "Сессий"]}
          />

          <Bar
            dataKey="sessions"
            fill="#4f46e5"
            radius={[8, 8, 0, 0]}
            isAnimationActive={false}
          >
            <LabelList
              position="top"
              content={({ x, y, width, index }) => {
                if (index === undefined) return null;
                const item = chartData[index];
                if (!item) return null;

                return (
                  <text
                    x={(x ?? 0) + (width ?? 0) / 2}
                    y={(y ?? 0) - 6}
                    textAnchor="middle"
                    fill="#e5e7eb"
                    fontSize={12}
                    fontWeight={500}
                  >
                    {item.sessions} ({item.percent}%)
                  </text>
                );
              }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
