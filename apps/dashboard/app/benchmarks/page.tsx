"use client";

import React, { useState } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend,
} from "recharts";

interface Benchmark {
  id: string;
  name: string;
  category: string;
  status: "running" | "completed" | "failed" | "pending";
  progress: number;
  tests_total: number;
  tests_passed: number;
  avg_score: number;
  last_run: string;
}

const benchmarks: Benchmark[] = [
  {
    id: "rag-001",
    name: "RAG Adversarial",
    category: "rag",
    status: "completed",
    progress: 100,
    tests_total: 250,
    tests_passed: 238,
    avg_score: 0.87,
    last_run: "2 hours ago",
  },
  {
    id: "agent-001",
    name: "Multi-Step Agent",
    category: "agents",
    status: "running",
    progress: 65,
    tests_total: 100,
    tests_passed: 0,
    avg_score: 0,
    last_run: "Running...",
  },
  {
    id: "mem-001",
    name: "Long-Context Memory",
    category: "memory",
    status: "completed",
    progress: 100,
    tests_total: 150,
    tests_passed: 142,
    avg_score: 0.91,
    last_run: "5 hours ago",
  },
  {
    id: "tool-001",
    name: "Tool Failure Sim",
    category: "tool_use",
    status: "completed",
    progress: 100,
    tests_total: 200,
    tests_passed: 185,
    avg_score: 0.83,
    last_run: "1 day ago",
  },
  {
    id: "inject-001",
    name: "Prompt Injection",
    category: "security",
    status: "pending",
    progress: 0,
    tests_total: 500,
    tests_passed: 0,
    avg_score: 0,
    last_run: "Not run",
  },
];

const categoryScores = [
  { category: "RAG", score: 0.87, baseline: 0.82 },
  { category: "Agents", score: 0.79, baseline: 0.75 },
  { category: "Memory", score: 0.91, baseline: 0.88 },
  { category: "Tool Use", score: 0.83, baseline: 0.80 },
  { category: "Security", score: 0.0, baseline: 0.0 },
];

export default function BenchmarksPage() {
  const [selectedBenchmark, setSelectedBenchmark] = useState<Benchmark | null>(null);

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-2">Benchmark Lab</h2>
        <p className="text-muted-foreground">
          Adversarial datasets, stress tests, and regression benchmarks.
        </p>
      </div>

      {/* Category Performance */}
      <div className="border border-border rounded-lg p-6 bg-card">
        <h3 className="text-sm font-medium mb-4">Benchmark Performance by Category</h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={categoryScores}>
            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
            <XAxis dataKey="category" stroke="#666" />
            <YAxis domain={[0, 1]} stroke="#666" />
            <Tooltip
              contentStyle={{ backgroundColor: "#1a1a1a", border: "1px solid #333" }}
            />
            <Legend />
            <Bar dataKey="score" fill="#8884d8" name="Current" />
            <Bar dataKey="baseline" fill="#82ca9d" name="Baseline" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Benchmark List */}
      <div className="border border-border rounded-lg overflow-hidden">
        <div className="px-4 py-3 bg-muted font-medium text-sm flex justify-between items-center">
          <span>Benchmark Suites</span>
          <button className="px-3 py-1 bg-primary text-primary-foreground rounded text-xs hover:opacity-90">
            Run All
          </button>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-3 font-medium">Name</th>
              <th className="text-left p-3 font-medium">Category</th>
              <th className="text-left p-3 font-medium">Status</th>
              <th className="text-left p-3 font-medium">Progress</th>
              <th className="text-left p-3 font-medium">Score</th>
              <th className="text-left p-3 font-medium">Pass Rate</th>
              <th className="text-left p-3 font-medium">Last Run</th>
              <th className="text-left p-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {benchmarks.map((bm) => (
              <tr key={bm.id} className="border-t border-border hover:bg-muted/30">
                <td className="p-3 font-medium">{bm.name}</td>
                <td className="p-3">
                  <CategoryBadge category={bm.category} />
                </td>
                <td className="p-3">
                  <StatusBadge status={bm.status} />
                </td>
                <td className="p-3">
                  <ProgressBar progress={bm.progress} />
                </td>
                <td className="p-3 font-mono">
                  {bm.avg_score > 0 ? bm.avg_score.toFixed(2) : "-"}
                </td>
                <td className="p-3">
                  {bm.tests_total > 0
                    ? `${((bm.tests_passed / bm.tests_total) * 100).toFixed(1)}%`
                    : "-"}
                </td>
                <td className="p-3 text-muted-foreground text-xs">{bm.last_run}</td>
                <td className="p-3">
                  <button
                    onClick={() => setSelectedBenchmark(bm)}
                    className="text-xs px-2 py-1 rounded border border-border hover:bg-muted transition-colors"
                  >
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Test Types */}
      <div className="grid grid-cols-3 gap-4">
        <TestTypeCard
          title="Adversarial Tests"
          count={250}
          types={["Contradiction", "Entailment", "Paraphrase", "Negation"]}
          description="Test robustness against adversarial inputs"
        />
        <TestTypeCard
          title="Prompt Injection"
          count={500}
          types={["Direct", "Indirect", "Jailbreak", "Context Leak"]}
          description="Security and prompt injection resistance"
        />
        <TestTypeCard
          title="Stress Tests"
          count={300}
          types={["Long Context", "Multi-turn", "Tool Failure", "Memory Corruption"]}
          description="Stress test agent under adverse conditions"
        />
      </div>

      {/* Selected Benchmark Details */}
      {selectedBenchmark && (
        <div className="border border-border rounded-lg p-6 bg-card">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h3 className="text-lg font-bold">{selectedBenchmark.name}</h3>
              <p className="text-muted-foreground text-sm">ID: {selectedBenchmark.id}</p>
            </div>
            <button
              onClick={() => setSelectedBenchmark(null)}
              className="text-muted-foreground hover:text-foreground"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-4 gap-4 mb-6">
            <MetricBox label="Total Tests" value={selectedBenchmark.tests_total} />
            <MetricBox label="Passed" value={selectedBenchmark.tests_passed} />
            <MetricBox label="Failed" value={selectedBenchmark.tests_total - selectedBenchmark.tests_passed} />
            <MetricBox label="Avg Score" value={selectedBenchmark.avg_score.toFixed(2)} />
          </div>

          <div className="space-y-2">
            <div className="text-sm font-medium">Test Breakdown</div>
            <div className="space-y-1">
              {[
                { name: "Basic retrieval", pass: 95, total: 100 },
                { name: "Adversarial queries", pass: 82, total: 100 },
                { name: "Multi-hop reasoning", pass: 61, total: 80 },
                { name: "Long context stress", pass: 0, total: 70 },
              ].map((test) => (
                <div key={test.name} className="flex items-center gap-4 text-sm">
                  <div className="w-40 truncate">{test.name}</div>
                  <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
                    <div
                      className="h-full bg-primary rounded-full"
                      style={{ width: `${(test.pass / test.total) * 100}%` }}
                    />
                  </div>
                  <div className="w-16 text-right text-muted-foreground">
                    {test.pass}/{test.total}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function CategoryBadge({ category }: { category: string }) {
  const colors: Record<string, string> = {
    rag: "bg-blue-500/20 text-blue-400",
    agents: "bg-purple-500/20 text-purple-400",
    memory: "bg-green-500/20 text-green-400",
    tool_use: "bg-orange-500/20 text-orange-400",
    security: "bg-red-500/20 text-red-400",
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[category] || "bg-gray-500/20 text-gray-400"}`}>
      {category}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    running: "bg-blue-500/20 text-blue-400",
    completed: "bg-green-500/20 text-green-400",
    failed: "bg-red-500/20 text-red-400",
    pending: "bg-gray-500/20 text-gray-400",
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colors[status]}`}>
      {status === "running" && <span className="w-1.5 h-1.5 bg-blue-400 rounded-full mr-1 animate-pulse" />}
      {status}
    </span>
  );
}

function ProgressBar({ progress }: { progress: number }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary rounded-full transition-all"
          style={{ width: `${progress}%` }}
        />
      </div>
      <span className="text-xs text-muted-foreground w-8">{progress}%</span>
    </div>
  );
}

function TestTypeCard({ title, count, types, description }: { title: string; count: number; types: string[]; description: string }) {
  return (
    <div className="border border-border rounded-lg p-4 bg-card">
      <div className="flex justify-between items-start mb-2">
        <h4 className="font-medium">{title}</h4>
        <span className="text-2xl font-bold text-muted-foreground">{count}</span>
      </div>
      <p className="text-sm text-muted-foreground mb-3">{description}</p>
      <div className="flex flex-wrap gap-1">
        {types.map((type) => (
          <span key={type} className="text-xs px-2 py-0.5 rounded bg-muted text-muted-foreground">
            {type}
          </span>
        ))}
      </div>
    </div>
  );
}

function MetricBox({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border border-border rounded-lg p-3 bg-muted/50">
      <div className="text-xs text-muted-foreground mb-1">{label}</div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  );
}
