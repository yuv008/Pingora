'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { monitorsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useToast } from '@/hooks/use-toast';
import { Loader2, X } from 'lucide-react';

const monitorSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100),
  url: z.string().url('Must be a valid URL'),
  monitor_type: z.enum(['http', 'https', 'tcp', 'dns', 'websocket', 'grpc']),
  interval_seconds: z.number().min(30).max(86400).default(60),
  timeout_seconds: z.number().min(1).max(60).default(30),
});

type MonitorFormData = z.infer<typeof monitorSchema>;

export function CreateMonitorDialog({
  open,
  onClose,
  workspaceId,
}: {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const {
    register,
    handleSubmit,
    formState: { errors },
    reset,
  } = useForm<MonitorFormData>({
    resolver: zodResolver(monitorSchema),
    defaultValues: {
      monitor_type: 'https',
      interval_seconds: 60,
      timeout_seconds: 30,
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: MonitorFormData) => monitorsApi.create(workspaceId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['monitors'] });
      toast({
        title: 'Success',
        description: 'Monitor created successfully',
        variant: 'success',
      });
      reset();
      onClose();
    },
    onError: (error: any) => {
      toast({
        title: 'Error',
        description: error.response?.data?.detail || 'Failed to create monitor',
        variant: 'destructive',
      });
    },
  });

  const onSubmit = (data: MonitorFormData) => {
    createMutation.mutate(data);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm">
      <div className="relative w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Create Monitor</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Monitor Name</Label>
            <Input
              id="name"
              placeholder="My API"
              {...register('name')}
              disabled={createMutation.isPending}
            />
            {errors.name && <p className="text-sm text-destructive">{errors.name.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="url">URL</Label>
            <Input
              id="url"
              placeholder="https://api.example.com/health"
              {...register('url')}
              disabled={createMutation.isPending}
            />
            {errors.url && <p className="text-sm text-destructive">{errors.url.message}</p>}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="monitor_type">Type</Label>
              <select
                id="monitor_type"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background"
                {...register('monitor_type')}
                disabled={createMutation.isPending}
              >
                <option value="https">HTTPS</option>
                <option value="http">HTTP</option>
                <option value="tcp">TCP</option>
                <option value="dns">DNS</option>
                <option value="websocket">WebSocket</option>
                <option value="grpc">gRPC</option>
              </select>
              {errors.monitor_type && (
                <p className="text-sm text-destructive">{errors.monitor_type.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="interval_seconds">Interval (seconds)</Label>
              <Input
                id="interval_seconds"
                type="number"
                {...register('interval_seconds', { valueAsNumber: true })}
                disabled={createMutation.isPending}
              />
              {errors.interval_seconds && (
                <p className="text-sm text-destructive">{errors.interval_seconds.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="timeout_seconds">Timeout (seconds)</Label>
            <Input
              id="timeout_seconds"
              type="number"
              {...register('timeout_seconds', { valueAsNumber: true })}
              disabled={createMutation.isPending}
            />
            {errors.timeout_seconds && (
              <p className="text-sm text-destructive">{errors.timeout_seconds.message}</p>
            )}
          </div>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Monitor
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
