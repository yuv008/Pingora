'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { workspacesApi, monitorsApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { Activity, TrendingUp, Clock, AlertTriangle } from 'lucide-react';
import type { Monitor } from '@/types/api';

export default function AnalyticsPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<'1h' | '24h' | '7d' | '30d'>('24h');

  // Fetch workspace
  useEffect(() => {
    async function fetchWorkspace() {
      try {
        const workspaces = await workspacesApi.list();
        if (workspaces.length > 0) {
          setWorkspaceId(workspaces[0].id);
        }
      } catch (error) {
        console.error('Failed to fetch workspace:', error);
      }
    }
    fetchWorkspace();
  }, []);

  // Fetch monitors
  const { data: monitors = [], isLoading } = useQuery({
    queryKey: ['monitors', workspaceId],
    queryFn: () => (workspaceId ? monitorsApi.list(workspaceId) : []),
    enabled: !!workspaceId,
  });

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-32 w-32 spinner" />
      </div>
    );
  }

  // Calculate metrics
  const avgUptime =
    monitors.length > 0
      ? monitors.reduce((acc, m) => acc + m.uptime_percentage, 0) / monitors.length
      : 0;

  const avgResponseTime =
    monitors.length > 0
      ? monitors.reduce((acc, m) => acc + (m.last_check_duration_ms || 0), 0) / monitors.length
      : 0;

  const activeMonitors = monitors.filter((m) => !m.is_paused).length;

  // Generate demo data for charts
  const uptimeData = generateUptimeData();
  const responseTimeData = generateResponseTimeData();
  const statusDistribution = [
    { name: 'Up', value: monitors.filter((m) => m.current_status === 'up').length, color: '#22c55e' },
    { name: 'Down', value: monitors.filter((m) => m.current_status === 'down').length, color: '#ef4444' },
    { name: 'Degraded', value: monitors.filter((m) => m.current_status === 'degraded').length, color: '#f59e0b' },
    { name: 'Paused', value: monitors.filter((m) => m.is_paused).length, color: '#64748b' },
  ].filter((item) => item.value > 0);

  const monitorsByType = Object.entries(
    monitors.reduce(
      (acc, m) => {
        acc[m.monitor_type] = (acc[m.monitor_type] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>
    )
  ).map(([type, count]) => ({ type, count }));

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Analytics</h2>
        <p className="text-muted-foreground">Monitor performance metrics and trends</p>
      </div>

      {/* Period Selector */}
      <div className="flex gap-2">
        {(['1h', '24h', '7d', '30d'] as const).map((period) => (
          <Badge
            key={period}
            variant={selectedPeriod === period ? 'default' : 'outline'}
            className="cursor-pointer"
            onClick={() => setSelectedPeriod(period)}
          >
            {period}
          </Badge>
        ))}
      </div>

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          title="Avg. Uptime"
          value={`${avgUptime.toFixed(2)}%`}
          icon={<Activity className="h-4 w-4 text-success" />}
          trend="+2.5%"
        />
        <MetricCard
          title="Avg. Response Time"
          value={`${avgResponseTime.toFixed(0)}ms`}
          icon={<Clock className="h-4 w-4 text-info" />}
          trend="-12ms"
        />
        <MetricCard
          title="Active Monitors"
          value={activeMonitors}
          icon={<TrendingUp className="h-4 w-4 text-primary" />}
        />
        <MetricCard
          title="Incidents (24h)"
          value="3"
          icon={<AlertTriangle className="h-4 w-4 text-warning" />}
        />
      </div>

      {/* Charts */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Uptime Trend */}
        <Card>
          <CardHeader>
            <CardTitle>Uptime Trend</CardTitle>
            <CardDescription>Historical uptime percentage over time</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={uptimeData}>
                <defs>
                  <linearGradient id="colorUptime" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.8} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="time" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="uptime"
                  stroke="#22c55e"
                  fillOpacity={1}
                  fill="url(#colorUptime)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Response Time */}
        <Card>
          <CardHeader>
            <CardTitle>Response Time</CardTitle>
            <CardDescription>Average response time trends</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={responseTimeData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="time" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="avg"
                  stroke="#3b82f6"
                  name="Average"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="p95"
                  stroke="#f59e0b"
                  name="P95"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Status Distribution</CardTitle>
            <CardDescription>Current monitor status breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusDistribution}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statusDistribution.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Monitors by Type */}
        <Card>
          <CardHeader>
            <CardTitle>Monitors by Type</CardTitle>
            <CardDescription>Distribution of monitor protocols</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monitorsByType}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="type" className="text-xs" />
                <YAxis className="text-xs" />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--card))',
                    border: '1px solid hsl(var(--border))',
                  }}
                />
                <Bar dataKey="count" fill="#3b82f6" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
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
  icon: React.ReactNode;
  trend?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="mt-2 text-3xl font-bold">{value}</p>
            {trend && <p className="mt-1 text-xs text-success">{trend}</p>}
          </div>
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}

// Helper functions to generate demo data
function generateUptimeData() {
  const now = Date.now();
  const data = [];
  for (let i = 23; i >= 0; i--) {
    data.push({
      time: new Date(now - i * 3600000).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }),
      uptime: 95 + Math.random() * 5,
    });
  }
  return data;
}

function generateResponseTimeData() {
  const now = Date.now();
  const data = [];
  for (let i = 23; i >= 0; i--) {
    const base = 150;
    data.push({
      time: new Date(now - i * 3600000).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      }),
      avg: base + Math.random() * 50,
      p95: base + 100 + Math.random() * 100,
    });
  }
  return data;
}
