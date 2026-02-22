"use client";

import { memo } from "react";
import {
  type EdgeProps,
  getBezierPath,
  EdgeLabelRenderer,
} from "reactflow";

function ConditionalEdgeComponent({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  markerEnd,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const condition = (data as { condition?: string })?.condition;

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: "#f97316",
          strokeWidth: 2,
          strokeDasharray: "6 3",
        }}
      />
      {condition && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: "all",
            }}
            className="bg-orange-900/90 text-orange-200 text-[10px] px-2 py-0.5 rounded-full border border-orange-600 whitespace-nowrap"
          >
            {condition}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export default memo(ConditionalEdgeComponent);
