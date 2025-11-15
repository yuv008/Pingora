'use client';

import { useEffect, useState, Suspense } from 'react';
import { useQuery } from '@tanstack/react-query';
import { workspacesApi, monitorsApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { StatusGlobe, generateDemoMonitors } from '@/components/3d/status-globe';
import type { Monitor } from '@/types/api';

export default function GlobePage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);

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

  // Map monitors to globe data (with random coordinates for demo)
  const globeMonitors = monitors.map((monitor, index) => ({
    id: monitor.id,
    name: monitor.name,
    latitude: (index * 15) % 180 - 90,
    longitude: (index * 20) % 360 - 180,
    status: monitor.current_status,
  }));

  // Use demo monitors if no real monitors
  const displayMonitors = globeMonitors.length > 0 ? globeMonitors : generateDemoMonitors(25);

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-32 w-32 spinner" />
      </div>
    );
  }

  const upCount = displayMonitors.filter((m) => m.status === 'up').length;
  const downCount = displayMonitors.filter((m) => m.status === 'down').length;
  const degradedCount = displayMonitors.filter((m) => m.status === 'degraded').length;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Global Status</h2>
        <p className="text-muted-foreground">Real-time monitor status across the globe</p>
      </div>

      {/* Statistics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{displayMonitors.length}</div>
            <p className="text-xs text-muted-foreground">Total Monitors</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-success">{upCount}</div>
            <p className="text-xs text-muted-foreground">Up</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-error">{downCount}</div>
            <p className="text-xs text-muted-foreground">Down</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-warning">{degradedCount}</div>
            <p className="text-xs text-muted-foreground">Degraded</p>
          </CardContent>
        </Card>
      </div>

      {/* 3D Globe */}
      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Global Monitor Distribution</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="h-[600px] w-full bg-gradient-to-b from-background to-muted/20">
            <Suspense
              fallback={
                <div className="flex h-full items-center justify-center">
                  <div className="h-32 w-32 spinner" />
                </div>
              }
            >
              <StatusGlobe monitors={displayMonitors} />
            </Suspense>
          </div>
        </CardContent>
      </Card>

      {/* Legend */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-6">
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-success" />
              <span className="text-sm">Up - Monitor is operational</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-error" />
              <span className="text-sm">Down - Monitor is not responding</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-warning" />
              <span className="text-sm">Degraded - Monitor is slow</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="h-3 w-3 rounded-full bg-muted" />
              <span className="text-sm">Paused - Monitor is disabled</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
