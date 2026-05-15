"use client";

import React from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  ScatterChart,
  Scatter,
  ZAxis,
} from "recharts";

const reliabilityData = Array.from({ length: 30 }, (_, i) => ({
  day: `Day ${i + 1}`,
  success_rate: 0.85 + Math.random() * 0.12,
  hallucination_rate: 0.05 + Math.random() * 0.08,
  latency_p95: 2000 + Math.random() * 1500,
  tool_accuracy: 0.88 + Math.random() * 0.1,
  variance: 0.1 + Math.random() * 0.15,
}));

const modelComparison = [
  { model: "Qwen3-32B", success: 0.94, latency: 1200, cost: 0.8, hallucination: 0.04 },
  { model: "DeepSeek-R1", success: 0.91, latency: 2500, cost: 1.2, hallucination: 0.06 },
  { model: "Llama4-Mav", success: 0.89, latency: 1800, cost: 0.6, hallucination: 0.08 },
  { model: "GPT-4", success: 0.93, latency: 1500, cost: 3.0, hallucination: 0.03 },
  { model: "Ministral-8B", success: 0.82, latency: 800, cost: 0.2, hallucination: 0.12 },
];

const radarData = [
  { metric: "Success Rate", current: 0.92, baseline: 0.88 },
  { metric: "Low Hallucination", current: 0.95, baseline: 0.90 },
  { metric: "Tool Accuracy", current: 0.89, baseline: 0.85 },
  { metric: "Context Retention", current: 0.87, baseline: 0.82 },
  { metric: "Low Latency", current: 0.78, baseline: 0.75 },
  { metric: "Low Variance", current: 0.85, baseline: 0.80 },
];

export default function ReliabilityPage() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-2">Reliability Analytics</h2>
        <p className="text-muted-foreground">
          Stability trends, variance analysis, failure hotspots, and cost drift.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-5 gap-4">
        <ReliabilityCard label="Success Rate" value="92.4%" change="+3.2%" positive />
        <ReliabilityCard label="Hallucination Rate" value="4.8%" change="-1.1%" positive />
        <ReliabilityCard label="Variance Score" value="0.84" change="+0.05" positive />
        <ReliabilityCard label="Latency P95" value="2.1s" change="-12%" positive />
        <ReliabilityCard label="Cost/Run" value="$0.042" change="+5%" positive={false} />
      </div>

      {/* Radar Chart */}
      <div className="grid grid-cols-2 gap-6">
        <div className="border border-border rounded-lg p-6 bg-card">
          <h3 className="text-sm font-medium mb-4">Reliability Profile vs Baseline</h3>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#333" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: "#999", fontSize: 12 }} />
              <PolarRadiusAxis tick={{ fill: "#666", fontSize: 10 }} />
              <Radar
                name="Current"
                dataKey="current"
                stroke="#8884d8"
                fill="#8884d8"
                fillOpacity={0.3}
              />
              <Radar
                name="Baseline"
                dataKey="baseline"
                stroke="#82ca9d"
                fill="#82ca9d"
                fillOpacity={0.1}
              />
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        <div className="border border-border rounded-lg p-6 bg-card">
          <h3 className="text-sm font-medium mb-4">Multi-Run Comparison</h3>
          <ResponsiveContainer width="100%" height={300}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis
                type="number"
                dataKey="success"
                name="Success Rate"
                domain={[0.7, 1.0]}
                stroke="#666"
              />
              <YAxis
                type="number"
                dataKey="latency"
                name="Latency (ms)"
                stroke="#666"
              />
              <ZAxis type="number" dataKey="cost" range={[50, 400]} name="Cost" />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #333" }}
              />
              <Legend />
              <Scatter
                name="Model Comparison"
                data={modelComparison}
                fill="#8884d8"
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Trend Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="border border-border rounded-lg p-6 bg-card">
          <h3 className="text-sm font-medium mb-4">Stability Trend (30 days)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={reliabilityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="day" stroke="#666" fontSize={10} />
              <YAxis domain={[0.7, 1.0]} stroke="#666" fontSize={12} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #333" }}
              />
              <Line type="monotone" dataKey="success_rate" stroke="#82ca9d" strokeWidth={2} dot={false} name="Success Rate" />
              <Line type="monotone" dataKey="tool_accuracy" stroke="#8884d8" strokeWidth={2} dot={false} name="Tool Accuracy" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="border border-border rounded-lg p-6 bg-card">
          <h3 className="text-sm font-medium mb-4">Failure Hotspots</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={reliabilityData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="day" stroke="#666" fontSize={10} />
              <YAxis stroke="#666" fontSize={12} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #333" }}
              />
              <Bar dataKey="hallucination_rate" fill="#ef4444" name="Hallucination" />
              <Bar dataKey="variance" fill="#f59e0b" name="Variance" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Failure Analysis Table */}
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="px-4 py-3 bg-muted font-medium text-sm">Recent Failure Analysis</div>
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3 font-medium">Trace ID</th>
              <th className="text-left p-3 font-medium">Failure Type</th>
              <th className="text-left p-3 font-medium">Root Cause</th>
              <th className="text-left p-3 font-medium">Severity</th>
              <th className="text-left p-3 font-medium">Model</th>
            </tr>
          </thead>
          <tbody>
            {[
              { id: "t-3921", type: "Hallucination", cause: "Unsupported claim in citation", severity: "P1", model: "Qwen3-32B" },
              { id: "t-3920", type: "Tool Error", cause: "Invalid parameter schema", severity: "P2", model: "Ministral-8B" },
              { id: "t-3918", type: "Loop Collapse", cause: "Reflection oscillation", severity: "P0", model: "DeepSeek-R1" },
              { id: "t-3915", type: "Memory Poison", cause: "Stale context retrieval", severity: "P1", model: "Llama4-Mav" },
            ].map((row) => (
              <tr key={row.id} className="border-t border-border hover:bg-muted/30">
                <td className="p-3 font-mono text-xs">{row.id}</td>
                <td className="p-3">{row.type}</td>
                <td className="p-3 text-muted-foreground">{row.cause}</td>
                <td className="p-3">
                  <SeverityBadge severity={row.severity} />
                </td>
                <td className="p-3">{row.model}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ReliabilityCard({
  label,
  value,
  change,
  positive,
}: {
  label: string;
  value: string;
  change: string;
  positive: boolean;
}) {
  return (
    <div className="border border-border rounded-lg p-4 bg-card">
      <div className="text-muted-foreground text-sm mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      <div className={`text-sm mt-1 ${positive ? "text-green-400" : "text-red-400"}`}>
        {positive ? "↑" : "↓"} {change}
      </div>
    </div>
  );
}

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    P0: "bg-red-500/20 text-red-400 border-red-500/50",
    P1: "bg-orange-500/20 text-orange-400 border-orange-500/50",
    P2: "bg-yellow-500/20 text-yellow-400 border-yellow-500/50",
    P3: "bg-blue-500/20 text-blue-400 border-blue-500/50",
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${colors[severity] || colors.P3}`}>
      {severity}
    </span>
  );
}
