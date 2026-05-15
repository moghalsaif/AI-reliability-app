"use client";

import React, { useCallback } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Node,
  Edge,
  Connection,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// Custom node types for reflection visualization
const nodeTypes = {
  reflection: ReflectionNode,
  decision: DecisionNode,
  retry: RetryNode,
  success: SuccessNode,
  failure: FailureNode,
};

function ReflectionNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-blue-500/20 border border-blue-500/50 text-blue-200 text-sm min-w-[120px]">
      <div className="font-medium">{data.label}</div>
      <div className="text-xs opacity-70">Iter: {data.iteration}</div>
      <div className="text-xs opacity-70">Conf: {(data.confidence * 100).toFixed(0)}%</div>
    </div>
  );
}

function DecisionNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-purple-500/20 border border-purple-500/50 text-purple-200 text-sm min-w-[120px]">
      <div className="font-medium">{data.label}</div>
      <div className="text-xs opacity-70">{data.decision}</div>
    </div>
  );
}

function RetryNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-yellow-500/20 border border-yellow-500/50 text-yellow-200 text-sm min-w-[120px]">
      <div className="font-medium">{data.label}</div>
      <div className="text-xs opacity-70">Attempt #{data.attempt}</div>
    </div>
  );
}

function SuccessNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-green-500/20 border border-green-500/50 text-green-200 text-sm min-w-[120px]">
      <div className="font-medium">{data.label}</div>
    </div>
  );
}

function FailureNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/50 text-red-200 text-sm min-w-[120px]">
      <div className="font-medium">{data.label}</div>
      <div className="text-xs opacity-70">{data.error}</div>
    </div>
  );
}

const initialNodes: Node[] = [
  { id: "1", type: "decision", position: { x: 250, y: 0 }, data: { label: "Initial Plan", decision: "Process query" } },
  { id: "2", type: "reflection", position: { x: 250, y: 100 }, data: { label: "Self-Check", iteration: 1, confidence: 0.7 } },
  { id: "3", type: "retry", position: { x: 100, y: 200 }, data: { label: "Retry", attempt: 1 } },
  { id: "4", type: "reflection", position: { x: 400, y: 200 }, data: { label: "Verify", iteration: 2, confidence: 0.85 } },
  { id: "5", type: "success", position: { x: 400, y: 300 }, data: { label: "Success" } },
  { id: "6", type: "failure", position: { x: 100, y: 300 }, data: { label: "Failed", error: "Timeout" } },
];

const initialEdges: Edge[] = [
  { id: "e1-2", source: "1", target: "2", animated: true },
  { id: "e2-3", source: "2", target: "3", label: "retry", animated: true },
  { id: "e2-4", source: "2", target: "4", label: "proceed" },
  { id: "e3-6", source: "3", target: "6", label: "failed" },
  { id: "e4-5", source: "4", target: "5", label: "passed" },
];

export default function ReflectionsPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  return (
    <div className="space-y-6 h-[80vh]">
      <div>
        <h2 className="text-2xl font-bold mb-2">Reflection Loop Visualizer</h2>
        <p className="text-muted-foreground">
          Visualize reasoning retries, loop chains, and correction paths.
        </p>
      </div>

      <div className="border border-border rounded-lg h-full bg-card overflow-hidden">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
        >
          <Controls />
          <MiniMap
            nodeStrokeWidth={3}
            zoomable
            pannable
          />
          <Background gap={12} size={1} />
        </ReactFlow>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total Reflections" value="24" />
        <StatCard label="Avg Iterations" value="2.3" />
        <StatCard label="Retry Rate" value="15.2%" />
        <StatCard label="Loop Collapses" value="2" alert />
      </div>
    </div>
  );
}

function StatCard({ label, value, alert }: { label: string; value: string; alert?: boolean }) {
  return (
    <div className={`border rounded-lg p-4 ${alert ? "border-red-500/50 bg-red-500/10" : "border-border bg-card"}`}>
      <div className="text-muted-foreground text-sm mb-1">{label}</div>
      <div className={`text-xl font-bold ${alert ? "text-red-400" : ""}`}>{value}</div>
    </div>
  );
}
