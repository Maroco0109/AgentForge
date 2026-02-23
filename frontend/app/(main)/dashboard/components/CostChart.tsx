"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface CostChartProps {
  data: { date: string; cost: number }[];
}

export default function CostChart({ data }: CostChartProps) {
  if (data.length === 0) {
    return (
      <div className="h-64 flex items-center justify-center text-gray-500">
        No data yet
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={256}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
        <XAxis dataKey="date" stroke="#9ca3af" tick={{ fontSize: 12 }} />
        <YAxis
          stroke="#9ca3af"
          tick={{ fontSize: 12 }}
          tickFormatter={(v: number) => `$${v.toFixed(2)}`}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#1f2937",
            border: "1px solid #374151",
            borderRadius: "8px",
          }}
          labelStyle={{ color: "#9ca3af" }}
          formatter={(value: number) => [`$${value.toFixed(4)}`, "Cost"]}
        />
        <Bar dataKey="cost" fill="#34d399" radius={[4, 4, 0, 0]} name="Cost" />
      </BarChart>
    </ResponsiveContainer>
  );
}
