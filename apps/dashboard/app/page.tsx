"use client";

import React, { useEffect, useState } from "react";
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
  Legend,
} from "recharts";
import { api, Trace } from "@/lib/api";

export default function TracesPage() {
  const [traces, setTraces] = useState<Trace[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    api
      .getTraces(100)
      .then((data) => {
        setTraces(data.traces || []);
        setLoading(false);
      })
      .catch((err) => {
        console.error("Failed to fetch traces:", err);
        // Fallback to mock data if API unavailable
        const mockTraces: Trace[] = Array.from({ length: 20 }, (_, i) => ({
          trace_id: `trace-${i}`,
          name: `contract_agent_${i}`,
          agent_name: "contract_agent",
          start_time: new Date(Date.now() - i * 60000).toISOString(),
          success: Math.random() > 0.15,
          total_latency_ms: Math.random() * 5000 + 500,
          span_count: Math.floor(Math.random() * 10) + 3,
          status: Math.random() > 0.15 ? "success" : "error",
        }));
        setTraces(mockTraces);
        setError("API unavailable — showing demo data");
        setLoading(false);
      });
  }, []);

  // WebSocket for real-time updates
  useEffect(() => {
    const wsUrl = process.env.NEXT_PUBLIC_API_URL
      ? process.env.NEXT_PUBLIC_API_URL.replace("http", "ws") + "/v1/ws/traces"
      : "ws://localhost:8000/v1/ws/traces";
    
    const ws = new WebSocket(wsUrl);
    
    ws.onopen = () => {
      setWsConnected(true);
      console.log("WebSocket connected");
    };
    
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.type === "trace_update") {
          setTraces((prev) => [message.data as Trace, ...prev.slice(0, 99)]);
        }
      } catch (err) {
        console.error("WebSocket message error:", err);
      }
    };
    
    ws.onclose = () => {
      setWsConnected(false);
      console.log("WebSocket disconnected");
    };
    
    ws.onerror = (err) => {
      console.error("WebSocket error:", err);
      setWsConnected(false);
    };
    
    // Keepalive ping
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send("ping");
      }
    }, 30000);
    
    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, []);

  const successRate =
    traces.length > 0
      ? (traces.filter((t) => t.success).length / traces.length) * 100
      : 0;

  const avgLatency =
    traces.length > 0
      ? traces.reduce((sum, t) => sum + t.total_latency_ms, 0) / traces.length
      : 0;

  const chartData = traces.map((t) => ({
    time: new Date(t.start_time).toLocaleTimeString(),
    latency: t.total_latency_ms,
    spans: t.span_count,
    success: t.success ? 1 : 0,
  }));

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading traces...</div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold mb-2">Trace Explorer</h2>
        <p className="text-muted-foreground">
          Monitor agent traces, spans, and failures in real-time.
        </p>
      {error && (
        <div className="mt-2 text-sm text-yellow-400 bg-yellow-400/10 px-3 py-2 rounded">
          {error}
        </div>
      )}
      <div className="flex items-center gap-2 text-sm">
        <span
          className={`w-2 h-2 rounded-full ${
            wsConnected ? "bg-green-400 animate-pulse" : "bg-gray-400"
          }`}
        />
        <span className="text-muted-foreground">
          {wsConnected ? "Live updates" : "Offline"}
        </span>
      </div>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard title="Total Traces" value={traces.length} icon="📊" />
        <MetricCard
          title="Success Rate"
          value={`${successRate.toFixed(1)}%`}
          icon="✓"
          trend={
            successRate > 90 ? "good" : successRate > 70 ? "warning" : "bad"
          }
        />
        <MetricCard
          title="Avg Latency"
          value={`${(avgLatency / 1000).toFixed(2)}s`}
          icon="⏱"
        />
        <MetricCard
          title="Active Alerts"
          value={traces.filter((t) => !t.success).length}
          icon="🚨"
          trend={
            traces.filter((t) => !t.success).length > 3 ? "bad" : "good"
          }
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="border border-border rounded-lg p-6 bg-card">
          <h3 className="text-sm font-medium mb-4">Latency Trend</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="time" stroke="#666" fontSize={12} />
              <YAxis stroke="#666" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #333",
                }}
              />
              <Line
                type="monotone"
                dataKey="latency"
                stroke="#8884d8"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="border border-border rounded-lg p-6 bg-card">
          <h3 className="text-sm font-medium mb-4">Span Count Distribution</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="time" stroke="#666" fontSize={12} />
              <YAxis stroke="#666" fontSize={12} />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1a1a1a",
                  border: "1px solid #333",
                }}
              />
              <Bar dataKey="spans" fill="#82ca9d" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Trace List */}
      <div className="border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted">
            <tr>
              <th className="text-left p-3 font-medium">Trace ID</th>
              <th className="text-left p-3 font-medium">Agent</th>
              <th className="text-left p-3 font-medium">Status</th>
              <th className="text-left p-3 font-medium">Latency</th>
              <th className="text-left p-3 font-medium">Spans</th>
              <th className="text-left p-3 font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {traces.map((trace) => (
              <tr
                key={trace.trace_id}
                className="border-t border-border hover:bg-muted/50"
              >
                <td className="p-3 font-mono text-xs">{trace.trace_id}</td>
                <td className="p-3">{trace.agent_name || "unknown"}</td>
                <td className="p-3">
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      trace.success
                        ? "bg-green-500/10 text-green-400"
                        : "bg-red-500/10 text-red-400"
                    }`}
                  >
                    {trace.success ? "Success" : "Failed"}
                  </span>
                </td>
                <td className="p-3">
                  {(trace.total_latency_ms / 1000).toFixed(2)}s
                </td>
                <td className="p-3">{trace.span_count || 0}</td>
                <td className="p-3 text-muted-foreground">
                  {new Date(trace.start_time).toLocaleTimeString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MetricCard({
  title,
  value,
  icon,
  trend,
}: {
  title: string;
  value: string | number;
  icon: string;
  trend?: "good" | "warning" | "bad";
}) {
  const trendColor =
    trend === "good"
      ? "text-green-400"
      : trend === "warning"
      ? "text-yellow-400"
      : trend === "bad"
      ? "text-red-400"
      : "";

  return (
    <div className="border border-border rounded-lg p-4 bg-card">
      <div className="flex items-center justify-between mb-2">
        <span className="text-muted-foreground text-sm">{title}</span>
        <span className="text-lg">{icon}</span>
      </div>
      <div className={`text-2xl font-bold ${trendColor}`}>{value}</div>
    </div>
  );
}
