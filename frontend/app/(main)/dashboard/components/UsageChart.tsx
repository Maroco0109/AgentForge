"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface UsageChartProps {
  data: { date: string; request_count: number }[];
}

export default function UsageChart({ data }: UsageChartProps) {
  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        No data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={256}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 12 }} />
        <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1f2937",
            border: "1px solid #374151",
            borderRadius: "8px",
          }}
          labelStyle={{ color: "#9ca3af" }}
          itemStyle={{ color: "#60a5fa" }}
        />
        <Line
          type="monotone"
          dataKey="request_count"
          stroke="#60a5fa"
          strokeWidth={2}
          dot={false}
          name="Requests"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
