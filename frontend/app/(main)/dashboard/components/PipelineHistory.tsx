"use client";

interface PipelineHistoryItem {
  id: string;
  design_name: string;
  status: string;
  duration_seconds: number | null;
  agent_count: number;
  created_at: string;
}

const STATUS_COLORS: Record<string, string> = {
  completed: "text-green-400 bg-green-900/20",
  failed: "text-red-400 bg-red-900/20",
  running: "text-blue-400 bg-blue-900/20",
  pending: "text-yellow-400 bg-yellow-900/20",
};

export default function PipelineHistory({
  data,
}: {
  data: PipelineHistoryItem[];
}) {
  if (data.length === 0) {
    return (
      <div className="text-gray-500 text-center py-8">
        No pipeline executions yet
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400 border-b border-gray-800">
            <th className="text-left py-2 px-3">Design</th>
            <th className="text-left py-2 px-3">Status</th>
            <th className="text-right py-2 px-3">Agents</th>
            <th className="text-right py-2 px-3">Duration</th>
            <th className="text-right py-2 px-3">Date</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={item.id}
              className="border-b border-gray-800/50 hover:bg-gray-800/30"
            >
              <td className="py-2 px-3 text-gray-200">{item.design_name}</td>
              <td className="py-2 px-3">
                <span
                  className={`px-2 py-0.5 rounded text-xs ${STATUS_COLORS[item.status] ?? "text-gray-400"}`}
                >
                  {item.status}
                </span>
              </td>
              <td className="py-2 px-3 text-right text-gray-300">
                {item.agent_count}
              </td>
              <td className="py-2 px-3 text-right text-gray-300">
                {item.duration_seconds != null
                  ? `${item.duration_seconds.toFixed(1)}s`
                  : "-"}
              </td>
              <td className="py-2 px-3 text-right text-gray-400">
                {new Date(item.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
