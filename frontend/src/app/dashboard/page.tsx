'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@/lib/auth-context';
import { workspacesApi, monitorsApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, AlertTriangle, CheckCircle2, Clock, TrendingUp } from 'lucide-react';
import type { Workspace, Monitor } from '@/types/api';

export default function DashboardPage() {
  const { user } = useAuth();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const workspaces = await workspacesApi.list();
        if (workspaces.length > 0) {
          const ws = workspaces[0];
          setWorkspace(ws);
          const monitorsList = await monitorsApi.list(ws.id);
          setMonitors(monitorsList);
        }
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-32 w-32 spinner" />
      </div>
    );
  }

  const upMonitors = monitors.filter((m) => m.current_status === 'up').length;
  const downMonitors = monitors.filter((m) => m.current_status === 'down').length;
  const pausedMonitors = monitors.filter((m) => m.is_paused).length;
  const avgUptime =
    monitors.length > 0
      ? monitors.reduce((acc, m) => acc + m.uptime_percentage, 0) / monitors.length
      : 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Welcome back, {user?.username}!</h2>
        <p className="text-muted-foreground">
          Here's an overview of your API monitoring status
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Monitors"
          value={monitors.length}
          icon={<Activity className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          title="Up & Running"
          value={upMonitors}
          icon={<CheckCircle2 className="h-4 w-4 text-success" />}
          trend="+2.5%"
        />
        <StatCard
          title="Down"
          value={downMonitors}
          icon={<AlertTriangle className="h-4 w-4 text-error" />}
        />
        <StatCard
          title="Avg. Uptime"
          value={`${avgUptime.toFixed(2)}%`}
          icon={<TrendingUp className="h-4 w-4 text-success" />}
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Monitors</CardTitle>
          </CardHeader>
          <CardContent>
            {monitors.length === 0 ? (
              <p className="text-sm text-muted-foreground">No monitors yet. Create your first monitor to get started.</p>
            ) : (
              <div className="space-y-2">
                {monitors.slice(0, 5).map((monitor) => (
                  <div
                    key={monitor.id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          monitor.current_status === 'up'
                            ? 'bg-success'
                            : monitor.current_status === 'down'
                              ? 'bg-error'
                              : 'bg-warning'
                        }`}
                      />
                      <div>
                        <p className="text-sm font-medium">{monitor.name}</p>
                        <p className="text-xs text-muted-foreground">{monitor.url}</p>
                      </div>
                    </div>
                    <Badge variant={monitor.current_status === 'up' ? 'success' : 'destructive'}>
                      {monitor.current_status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Quick Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Active Monitors</span>
                <span className="font-semibold">{monitors.length - pausedMonitors}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Paused Monitors</span>
                <span className="font-semibold">{pausedMonitors}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Workspace</span>
                <Badge>{workspace?.plan_type || 'free'}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function StatCard({
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
