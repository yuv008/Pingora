'use client';

import { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { workspacesApi, incidentsApi } from '@/lib/api';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertTriangle, CheckCircle2, Clock, TrendingUp } from 'lucide-react';
import { formatRelativeTime, formatDuration } from '@/lib/utils';
import { useIncidentUpdates } from '@/lib/websocket-context';
import { useToast } from '@/hooks/use-toast';
import type { Incident } from '@/types/api';

export default function IncidentsPage() {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const { toast } = useToast();

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

  // Fetch incidents
  const { data: incidents = [], isLoading, refetch } = useQuery({
    queryKey: ['incidents', workspaceId],
    queryFn: () => (workspaceId ? incidentsApi.list(workspaceId) : []),
    enabled: !!workspaceId,
    refetchInterval: 30000, // Refetch every 30 seconds
  });

  // WebSocket updates for real-time incident changes
  useIncidentUpdates((data) => {
    toast({
      title: data.type === 'incident:created' ? 'New Incident' : 'Incident Updated',
      description: data.title || 'An incident has been updated',
      variant: data.type === 'incident:resolved' ? 'success' : 'destructive',
    });
    refetch();
  });

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="h-32 w-32 spinner" />
      </div>
    );
  }

  const ongoingIncidents = incidents.filter(
    (i) => i.status === 'investigating' || i.status === 'identified'
  );
  const resolvedIncidents = incidents.filter((i) => i.status === 'resolved');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Incidents</h2>
        <p className="text-muted-foreground">Monitor and manage service incidents</p>
      </div>

      {/* Statistics */}
      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          title="Total Incidents"
          value={incidents.length}
          icon={<AlertTriangle className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          title="Ongoing"
          value={ongoingIncidents.length}
          icon={<Clock className="h-4 w-4 text-error" />}
        />
        <StatCard
          title="Resolved"
          value={resolvedIncidents.length}
          icon={<CheckCircle2 className="h-4 w-4 text-success" />}
        />
        <StatCard
          title="MTTR"
          value="12m"
          icon={<TrendingUp className="h-4 w-4 text-info" />}
        />
      </div>

      {/* Ongoing Incidents */}
      {ongoingIncidents.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold">Ongoing Incidents</h3>
          {ongoingIncidents.map((incident) => (
            <IncidentCard key={incident.id} incident={incident} />
          ))}
        </div>
      )}

      {/* Resolved Incidents */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">
          Recent Resolved Incidents ({resolvedIncidents.length})
        </h3>
        {resolvedIncidents.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <CheckCircle2 className="mb-4 h-12 w-12 text-success" />
              <p className="text-muted-foreground">No resolved incidents</p>
            </CardContent>
          </Card>
        ) : (
          resolvedIncidents.slice(0, 10).map((incident) => (
            <IncidentCard key={incident.id} incident={incident} />
          ))
        )}
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: string | number;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">{title}</p>
            <p className="mt-2 text-3xl font-bold">{value}</p>
          </div>
          {icon}
        </div>
      </CardContent>
    </Card>
  );
}

function IncidentCard({ incident }: { incident: Incident }) {
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'destructive';
      case 'high':
        return 'warning';
      case 'medium':
        return 'info';
      case 'low':
        return 'secondary';
      default:
        return 'secondary';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'investigating':
        return 'warning';
      case 'identified':
        return 'info';
      case 'monitoring':
        return 'info';
      case 'resolved':
        return 'success';
      default:
        return 'secondary';
    }
  };

  const downtime =
    incident.resolved_at && incident.started_at
      ? Math.floor(
          (new Date(incident.resolved_at).getTime() - new Date(incident.started_at).getTime()) /
            1000
        )
      : null;

  return (
    <Card className={incident.status !== 'resolved' ? 'border-error' : ''}>
      <CardContent className="p-6">
        <div className="flex items-start justify-between">
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold">{incident.title}</h3>
              <Badge variant={getSeverityColor(incident.severity) as any}>
                {incident.severity}
              </Badge>
              <Badge variant={getStatusColor(incident.status) as any}>{incident.status}</Badge>
            </div>
            <p className="text-sm text-muted-foreground">{incident.description}</p>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>Started {formatRelativeTime(incident.started_at)}</span>
              {incident.acknowledged_at && (
                <span>Acknowledged {formatRelativeTime(incident.acknowledged_at)}</span>
              )}
              {incident.resolved_at && (
                <span>Resolved {formatRelativeTime(incident.resolved_at)}</span>
              )}
              {downtime && <span className="font-semibold">Downtime: {formatDuration(downtime)}</span>}
            </div>
          </div>
          {incident.status !== 'resolved' && (
            <div className="flex h-3 w-3 items-center justify-center">
              <span className="absolute inline-flex h-3 w-3 animate-ping rounded-full bg-error opacity-75"></span>
              <span className="relative inline-flex h-2 w-2 rounded-full bg-error"></span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
