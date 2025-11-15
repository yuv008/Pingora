export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  plan_type: 'free' | 'starter' | 'pro' | 'business' | 'enterprise';
  created_at: string;
  updated_at: string;
}

export interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  joined_at: string;
}

export interface Monitor {
  id: string;
  workspace_id: string;
  name: string;
  url: string;
  monitor_type: 'http' | 'https' | 'tcp' | 'dns' | 'websocket' | 'grpc';
  method: string;
  interval_seconds: number;
  timeout_seconds: number;
  is_paused: boolean;
  current_status: 'up' | 'down' | 'degraded' | 'paused' | 'unknown';
  uptime_percentage: number;
  last_check_at: string | null;
  last_success_at: string | null;
  last_failure_at: string | null;
  next_check_at: string | null;
  consecutive_failures: number;
  consecutive_successes: number;
  tags: string[];
  headers: Record<string, string> | null;
  body: string | null;
  expected_status_codes: number[];
  regions: string[];
  created_at: string;
  updated_at: string;
}

export interface MonitorCheck {
  id: string;
  monitor_id: string;
  region: string;
  status: 'up' | 'down' | 'degraded' | 'unknown';
  response_time_ms: number;
  status_code: number | null;
  error_message: string | null;
  checked_at: string;
  ssl_expiry_days: number | null;
  response_size_bytes: number | null;
}

export interface Incident {
  id: string;
  monitor_id: string;
  workspace_id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'investigating' | 'identified' | 'monitoring' | 'resolved';
  started_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AlertChannel {
  id: string;
  workspace_id: string;
  name: string;
  channel_type: 'email' | 'slack' | 'webhook' | 'sms' | 'pagerduty';
  is_enabled: boolean;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface AlertRule {
  id: string;
  workspace_id: string;
  name: string;
  is_enabled: boolean;
  trigger_on_down: boolean;
  trigger_on_recovery: boolean;
  min_severity: 'low' | 'medium' | 'high' | 'critical' | null;
  monitor_ids: string[];
  monitor_tags: string[];
  channel_ids: string[];
  created_at: string;
  updated_at: string;
}

export interface MonitorStats {
  monitor_id: string;
  total_checks: number;
  successful_checks: number;
  failed_checks: number;
  avg_response_time: number;
  p95_response_time: number;
  p99_response_time: number;
  uptime_percentage: number;
  period_start: string;
  period_end: string;
}

// API Request/Response types
export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface CreateMonitorRequest {
  name: string;
  url: string;
  monitor_type: 'http' | 'https' | 'tcp' | 'dns' | 'websocket' | 'grpc';
  method?: string;
  interval_seconds?: number;
  timeout_seconds?: number;
  headers?: Record<string, string>;
  body?: string;
  expected_status_codes?: number[];
  regions?: string[];
  tags?: string[];
}

export interface UpdateMonitorRequest {
  name?: string;
  url?: string;
  interval_seconds?: number;
  timeout_seconds?: number;
  headers?: Record<string, string>;
  body?: string;
  expected_status_codes?: number[];
  regions?: string[];
  tags?: string[];
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}
