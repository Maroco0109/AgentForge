"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

const PipelineEditor = dynamic(
  () => import("@/app/components/pipeline-editor/PipelineEditor"),
  { ssr: false }
);

export default function PipelineEditorPage() {
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="flex-1 overflow-hidden flex flex-col relative">
      {error && (
        <div className="absolute top-2 left-1/2 -translate-x-1/2 z-50 bg-red-900/90 text-red-200 text-sm px-4 py-2 rounded-md border border-red-700">
          {error}
          <button onClick={() => setError(null)} className="ml-2 text-red-400 hover:text-red-300">&times;</button>
        </div>
      )}
      <PipelineEditor onError={setError} />
    </div>
  );
}
