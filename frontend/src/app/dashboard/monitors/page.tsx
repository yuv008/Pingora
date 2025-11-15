'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { workspacesApi, monitorsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useToast } from '@/hooks/use-toast';
import { Plus, Pause, Play, Trash2, ExternalLink, RefreshCw, Wifi } from 'lucide-react';
import { formatRelativeTime, formatResponseTime } from '@/lib/utils';
import { CreateMonitorDialog } from '@/components/dashboard/create-monitor-dialog';
import { useMonitorUpdates, useWebSocket } from '@/lib/websocket-context';
import type { Monitor } from '@/types/api';

export default function MonitorsPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { isConnected } = useWebSocket();

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
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // WebSocket real-time updates
  useMonitorUpdates((data) => {
    queryClient.invalidateQueries({ queryKey: ['monitors'] });
    toast({
      title: 'Monitor Updated',
      description: `${data.name} status changed to ${data.status}`,
      variant: data.status === 'up' ? 'success' : 'destructive',
    });
  });

  // Pause monitor mutation
  const pauseMutation = useMutation({
    mutationFn: ({ id, workspaceId }: { id: string; workspaceId: string }) =>
      monitorsApi.pause(id, workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
      toast({
        title: 'Success',
        description: 'Monitor paused successfully',
        variant: 'success',
      });
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to pause monitor',
        variant: 'destructive',
      });
    },
  });

  // Resume monitor mutation
  const resumeMutation = useMutation({
    mutationFn: ({ id, workspaceId }: { id: string; workspaceId: string }) =>
      monitorsApi.resume(id, workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
      toast({
        title: 'Success',
        description: 'Monitor resumed successfully',
        variant: 'success',
      });
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to resume monitor',
        variant: 'destructive',
      });
    },
  });

  // Trigger check mutation
  const checkMutation = useMutation({
    mutationFn: ({ id, workspaceId }: { id: string; workspaceId: string }) =>
      monitorsApi.triggerCheck(id, workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
      toast({
        title: 'Success',
        description: 'Check triggered successfully',
        variant: 'success',
      });
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to trigger check',
        variant: 'destructive',
      });
    },
  });

  // Delete monitor mutation
  const deleteMutation = useMutation({
    mutationFn: ({ id, workspaceId }: { id: string; workspaceId: string }) =>
      monitorsApi.delete(id, workspaceId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
      toast({
        title: 'Success',
        description: 'Monitor deleted successfully',
        variant: 'success',
      });
    },
    onError: () => {
      toast({
        title: 'Error',
        description: 'Failed to delete monitor',
        variant: 'destructive',
      });
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-32 w-32 spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-2xl font-bold tracking-tight">Monitors</h2>
            {isConnected && (
              <Badge variant="success" className="gap-1">
                <Wifi className="h-3 w-3" />
                Live
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground">Manage and monitor your API endpoints</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Create Monitor
        </Button>
      </div>

      {monitors.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <p className="mb-4 text-muted-foreground">No monitors yet</p>
            <Button onClick={() => setShowCreateDialog(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Your First Monitor
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {monitors.map((monitor) => (
            <MonitorCard
              key={monitor.id}
              monitor={monitor}
              workspaceId={workspaceId!}
              onPause={() => pauseMutation.mutate({ id: monitor.id, workspaceId: workspaceId! })}
              onResume={() => resumeMutation.mutate({ id: monitor.id, workspaceId: workspaceId! })}
              onCheck={() => checkMutation.mutate({ id: monitor.id, workspaceId: workspaceId! })}
              onDelete={() => {
                if (confirm('Are you sure you want to delete this monitor?')) {
                  deleteMutation.mutate({ id: monitor.id, workspaceId: workspaceId! });
                }
              }}
            />
          ))}
        </div>
      )}

      {workspaceId && (
        <CreateMonitorDialog
          open={showCreateDialog}
          onClose={() => setShowCreateDialog(false)}
          workspaceId={workspaceId}
        />
      )}
    </div>
  );
}

function MonitorCard({
  monitor,
  workspaceId,
  onPause,
  onResume,
  onCheck,
  onDelete,
}: {
  monitor: Monitor;
  workspaceId: string;
  onPause: () => void;
  onResume: () => void;
  onCheck: () => void;
  onDelete: () => void;
}) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'up':
        return 'bg-success';
      case 'down':
        return 'bg-error';
      case 'degraded':
        return 'bg-warning';
      default:
        return 'bg-muted';
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status) {
      case 'up':
        return 'success';
      case 'down':
        return 'destructive';
      default:
        return 'secondary';
    }
  };

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-start gap-4">
            <div
              className={`mt-1 h-3 w-3 rounded-full ${getStatusColor(monitor.current_status)}`}
            />
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <h3 className="font-semibold">{monitor.name}</h3>
                <Badge variant={getStatusVariant(monitor.current_status) as any}>
                  {monitor.current_status}
                </Badge>
                {monitor.is_paused && <Badge variant="outline">Paused</Badge>}
              </div>
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <span className="font-mono">{monitor.url}</span>
                <ExternalLink className="h-3 w-3" />
              </div>
              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                <span>Type: {monitor.monitor_type.toUpperCase()}</span>
                <span>Interval: {monitor.interval_seconds}s</span>
                <span>Uptime: {monitor.uptime_percentage.toFixed(2)}%</span>
                {monitor.last_check_duration_ms && (
                  <span>
                    Response: {formatResponseTime(monitor.last_check_duration_ms)}
                  </span>
                )}
              </div>
              {monitor.last_check_at && (
                <p className="text-xs text-muted-foreground">
                  Last checked {formatRelativeTime(monitor.last_check_at)}
                </p>
              )}
            </div>
          </div>

          <div className="flex gap-2">
            <Button variant="ghost" size="sm" onClick={onCheck}>
              <RefreshCw className="h-4 w-4" />
            </Button>
            {monitor.is_paused ? (
              <Button variant="ghost" size="sm" onClick={onResume}>
                <Play className="h-4 w-4" />
              </Button>
            ) : (
              <Button variant="ghost" size="sm" onClick={onPause}>
                <Pause className="h-4 w-4" />
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
