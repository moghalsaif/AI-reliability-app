"use client";

import React, { useCallback, useEffect, useState } from "react";
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
import { api, Trace } from "@/lib/api";

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
    <div className="px-4 py-2 rounded-lg bg-blue-500/20 border border-blue-500/50 text-blue-200 text-sm min-w-[120px] cursor-pointer hover:bg-blue-500/30 transition-colors">
      <div className="font-medium">{data.label}</div>
      <div className="text-xs opacity-70">Iter: {data.iteration}</div>
      <div className="text-xs opacity-70">Conf: {(data.confidence * 100).toFixed(0)}%</div>
    </div>
  );
}

function DecisionNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-purple-500/20 border border-purple-500/50 text-purple-200 text-sm min-w-[120px] cursor-pointer hover:bg-purple-500/30 transition-colors">
      <div className="font-medium">{data.label}</div>
      <div className="text-xs opacity-70">{data.decision}</div>
    </div>
  );
}

function RetryNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-yellow-500/20 border border-yellow-500/50 text-yellow-200 text-sm min-w-[120px] cursor-pointer hover:bg-yellow-500/30 transition-colors">
      <div className="font-medium">{data.label}</div>
      <div className="text-xs opacity-70">Attempt #{data.attempt}</div>
    </div>
  );
}

function SuccessNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-green-500/20 border border-green-500/50 text-green-200 text-sm min-w-[120px] cursor-pointer hover:bg-green-500/30 transition-colors">
      <div className="font-medium">{data.label}</div>
    </div>
  );
}

function FailureNode({ data }: { data: any }) {
  return (
    <div className="px-4 py-2 rounded-lg bg-red-500/20 border border-red-500/50 text-red-200 text-sm min-w-[120px] cursor-pointer hover:bg-red-500/30 transition-colors">
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
  const [traces, setTraces] = useState<Trace[]>([]);
  const [selectedTrace, setSelectedTrace] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [traceDetails, setTraceDetails] = useState<Trace | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getTraces(20)
      .then((data) => {
        setTraces(data.traces || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedTrace) {
      api.getTrace(selectedTrace)
        .then((trace) => setTraceDetails(trace))
        .catch(() => setTraceDetails(null));
    } else {
      setTraceDetails(null);
    }
  }, [selectedTrace]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      setSelectedNode(node);
      if (node.data && (node.data as any).traceId) {
        setSelectedTrace((node.data as any).traceId as string);
      }
    },
    []
  );

  return (
    <div className="space-y-6 h-[80vh]">
      <div>
        <h2 className="text-2xl font-bold mb-2">Reflection Loop Visualizer</h2>
        <p className="text-muted-foreground">
          Visualize reasoning retries, loop chains, and correction paths.
          Click any node to see trace details.
        </p>
      </div>

      <div className="flex gap-4 items-center">
        <select
          className="bg-card border border-border rounded px-3 py-2 text-sm"
          value={selectedTrace || ""}
          onChange={(e) => setSelectedTrace(e.target.value || null)}
        >
          <option value="">Demo Graph</option>
          {traces.map((t) => (
            <option key={t.trace_id} value={t.trace_id}>
              {t.trace_id} — {t.agent_name}
            </option>
          ))}
        </select>
        {loading && <span className="text-sm text-muted-foreground">Loading traces...</span>}
      </div>

      <div className="grid grid-cols-3 gap-6 h-full">
        <div className="col-span-2 border border-border rounded-lg bg-card overflow-hidden">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeClick={onNodeClick}
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

        <div className="border border-border rounded-lg p-4 bg-card overflow-y-auto">
          <h3 className="text-sm font-medium mb-4">Node Details</h3>
          {selectedNode ? (
            <div className="space-y-4">
              <div>
                <div className="text-xs text-muted-foreground mb-1">Type</div>
                <div className="text-sm font-medium capitalize">{selectedNode.type}</div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">Label</div>
                <div className="text-sm">{String((selectedNode.data as any)?.label || "")}</div>
              </div>
              {(selectedNode.data as any)?.iteration && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Iteration</div>
                  <div className="text-sm">{Number((selectedNode.data as any).iteration)}</div>
                </div>
              )}
              {(selectedNode.data as any)?.confidence && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Confidence</div>
                  <div className="text-sm">{(Number((selectedNode.data as any).confidence) * 100).toFixed(0)}%</div>
                </div>
              )}
              {(selectedNode.data as any)?.error && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Error</div>
                  <div className="text-sm text-red-400">{String((selectedNode.data as any).error)}</div>
                </div>
              )}
              {(selectedNode.data as any)?.decision && (
                <div>
                  <div className="text-xs text-muted-foreground mb-1">Decision</div>
                  <div className="text-sm">{String((selectedNode.data as any).decision)}</div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground">
              Click a node in the graph to view details
            </div>
          )}

          {traceDetails && (
            <div className="mt-6 pt-4 border-t border-border">
              <h4 className="text-sm font-medium mb-3">Trace Details</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Trace ID</span>
                  <span className="font-mono text-xs">{traceDetails.trace_id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Agent</span>
                  <span>{traceDetails.agent_name || "unknown"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <span className={traceDetails.success ? "text-green-400" : "text-red-400"}>
                    {traceDetails.success ? "Success" : "Failed"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Latency</span>
                  <span>{(Number(traceDetails.total_latency_ms || 0) / 1000).toFixed(2)}s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Spans</span>
                  <span>{traceDetails.span_count || 0}</span>
                </div>
              </div>
            </div>
          )}
        </div>
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
