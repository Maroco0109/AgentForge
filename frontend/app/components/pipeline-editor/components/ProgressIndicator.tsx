"use client";

interface ProgressIndicatorProps {
  completedCount: number;
  totalCount: number;
  isRunning: boolean;
}

export default function ProgressIndicator({ completedCount, totalCount, isRunning }: ProgressIndicatorProps) {
  if (!isRunning && completedCount === 0) return null;

  const progress = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
  const isComplete = completedCount === totalCount && totalCount > 0;

  return (
    <div className="absolute bottom-4 left-4 right-4 z-20">
      <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 shadow-lg">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-gray-300">
            {isComplete ? "Pipeline complete" : isRunning ? "Running pipeline..." : "Pipeline finished"}
          </span>
          <span className="text-gray-400">
            {completedCount}/{totalCount} agents
          </span>
        </div>
        <div className="w-full bg-gray-800 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all duration-500 ${
              isComplete ? "bg-green-500" : "bg-blue-500"
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>
    </div>
  );
}
