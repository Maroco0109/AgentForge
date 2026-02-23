"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import UsageChart from "./components/UsageChart";
import CostChart from "./components/CostChart";
import PipelineHistory from "./components/PipelineHistory";

interface DashboardSummary {
  total_conversations: number;
  total_messages: number;
  total_templates: number;
  total_pipelines: number;
}

interface UsageHistoryItem {
  date: string;
  cost: number;
  request_count: number;
}

interface PipelineHistoryItem {
  id: string;
  design_name: string;
  status: string;
  duration_seconds: number | null;
  agent_count: number;
  created_at: string;
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [usageHistory, setUsageHistory] = useState<UsageHistoryItem[]>([]);
  const [pipelineHistory, setPipelineHistory] = useState<
    PipelineHistoryItem[]
  >([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [summaryData, usageData, pipelineData] = await Promise.all([
          apiFetch<DashboardSummary>("/api/v1/stats/summary"),
          apiFetch<UsageHistoryItem[]>("/api/v1/stats/usage-history?days=30"),
          apiFetch<PipelineHistoryItem[]>(
            "/api/v1/stats/pipeline-history?limit=20"
          ),
        ]);
        setSummary(summaryData);
        setUsageHistory(usageData);
        setPipelineHistory(pipelineData);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Failed to load dashboard"
        );
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-gray-400">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-4 text-red-400">
          {error}
        </div>
      </div>
    );
  }

  const summaryCards = [
    {
      label: "Conversations",
      value: summary?.total_conversations ?? 0,
      icon: "\uD83D\uDCAC",
    },
    {
      label: "Messages",
      value: summary?.total_messages ?? 0,
      icon: "\uD83D\uDCDD",
    },
    {
      label: "Templates",
      value: summary?.total_templates ?? 0,
      icon: "\uD83D\uDCCB",
    },
    {
      label: "Pipelines",
      value: summary?.total_pipelines ?? 0,
      icon: "\u26A1",
    },
  ];

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <h1 className="text-2xl font-bold text-gray-100">Dashboard</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {summaryCards.map((card) => (
          <div
            key={card.label}
            className="bg-gray-900 border border-gray-800 rounded-lg p-4"
          >
            <div className="flex items-center gap-2 text-gray-400 text-sm">
              <span>{card.icon}</span>
              <span>{card.label}</span>
            </div>
            <div className="mt-2 text-2xl font-bold text-gray-100">
              {card.value.toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm font-medium text-gray-400 mb-4">
            Daily Requests (30d)
          </h2>
          <UsageChart data={usageHistory} />
        </div>
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm font-medium text-gray-400 mb-4">
            Daily Cost (30d)
          </h2>
          <CostChart data={usageHistory} />
        </div>
      </div>

      {/* Pipeline History */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-sm font-medium text-gray-400 mb-4">
          Recent Pipeline Executions
        </h2>
        <PipelineHistory data={pipelineHistory} />
      </div>
    </div>
  );
}
