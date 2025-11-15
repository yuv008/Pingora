import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
import type {
  User,
  Workspace,
  Monitor,
  MonitorCheck,
  MonitorStats,
  Incident,
  AlertChannel,
  AlertRule,
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  CreateMonitorRequest,
  UpdateMonitorRequest,
  PaginatedResponse,
  ApiError,
} from '@/types/api';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: `${API_URL}/api/v1`,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Token management
const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

export const setTokens = (accessToken: string, refreshToken: string) => {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
};

export const getAccessToken = (): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(TOKEN_KEY);
  }
  return null;
};

export const getRefreshToken = (): string | null => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }
  return null;
};

export const clearTokens = () => {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
};

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = getAccessToken();
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for token refresh
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value?: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

const processQueue = (error: Error | null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiError>) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject });
        })
          .then((token) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`;
            }
            return apiClient(originalRequest);
          })
          .catch((err) => {
            return Promise.reject(err);
          });
      }

      originalRequest._retry = true;
      isRefreshing = true;

      const refreshToken = getRefreshToken();
      if (!refreshToken) {
        clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }

      try {
        const response = await axios.post<TokenResponse>(
          `${API_URL}/api/v1/auth/refresh`,
          {},
          {
            headers: {
              Authorization: `Bearer ${refreshToken}`,
            },
          }
        );

        const { access_token, refresh_token } = response.data;
        setTokens(access_token, refresh_token);
        processQueue(null, access_token);

        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
        }
        return apiClient(originalRequest);
      } catch (refreshError) {
        processQueue(refreshError as Error, null);
        clearTokens();
        if (typeof window !== 'undefined') {
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// API Methods

// Authentication
export const authApi = {
  register: async (data: RegisterRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/register', data);
    setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },

  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/login', data);
    setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },

  logout: async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout');
    } finally {
      clearTokens();
    }
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  refreshToken: async (): Promise<TokenResponse> => {
    const refreshToken = getRefreshToken();
    const response = await axios.post<TokenResponse>(
      `${API_URL}/api/v1/auth/refresh`,
      {},
      {
        headers: {
          Authorization: `Bearer ${refreshToken}`,
        },
      }
    );
    setTokens(response.data.access_token, response.data.refresh_token);
    return response.data;
  },
};

// Workspaces
export const workspacesApi = {
  list: async (): Promise<Workspace[]> => {
    const response = await apiClient.get<Workspace[]>('/workspaces');
    return response.data;
  },

  get: async (id: string): Promise<Workspace> => {
    const response = await apiClient.get<Workspace>(`/workspaces/${id}`);
    return response.data;
  },

  create: async (data: { name: string; slug?: string }): Promise<Workspace> => {
    const response = await apiClient.post<Workspace>('/workspaces', data);
    return response.data;
  },

  update: async (id: string, data: { name?: string }): Promise<Workspace> => {
    const response = await apiClient.put<Workspace>(`/workspaces/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await apiClient.delete(`/workspaces/${id}`);
  },
};

// Monitors
export const monitorsApi = {
  list: async (
    workspaceId: string,
    params?: {
      status?: string;
      tags?: string[];
      search?: string;
      skip?: number;
      limit?: number;
    }
  ): Promise<Monitor[]> => {
    const response = await apiClient.get<Monitor[]>('/monitors', {
      params: {
        workspace_id: workspaceId,
        ...params,
        tags: params?.tags?.join(','),
      },
    });
    return response.data;
  },

  get: async (id: string, workspaceId: string): Promise<Monitor> => {
    const response = await apiClient.get<Monitor>(`/monitors/${id}`, {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },

  create: async (workspaceId: string, data: CreateMonitorRequest): Promise<Monitor> => {
    const response = await apiClient.post<Monitor>('/monitors', data, {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },

  update: async (
    id: string,
    workspaceId: string,
    data: UpdateMonitorRequest
  ): Promise<Monitor> => {
    const response = await apiClient.put<Monitor>(`/monitors/${id}`, data, {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },

  delete: async (id: string, workspaceId: string): Promise<void> => {
    await apiClient.delete(`/monitors/${id}`, {
      params: { workspace_id: workspaceId },
    });
  },

  pause: async (id: string, workspaceId: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/monitors/${id}/pause`, null, {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },

  resume: async (id: string, workspaceId: string): Promise<{ message: string }> => {
    const response = await apiClient.post<{ message: string }>(`/monitors/${id}/resume`, null, {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },

  triggerCheck: async (
    id: string,
    workspaceId: string
  ): Promise<{ message: string; monitor_id: string }> => {
    const response = await apiClient.post<{ message: string; monitor_id: string }>(
      `/monitors/${id}/check`,
      null,
      {
        params: { workspace_id: workspaceId },
      }
    );
    return response.data;
  },

  getChecks: async (
    id: string,
    workspaceId: string,
    params?: {
      limit?: number;
      offset?: number;
    }
  ): Promise<MonitorCheck[]> => {
    const response = await apiClient.get<MonitorCheck[]>(`/monitors/${id}/checks`, {
      params: {
        workspace_id: workspaceId,
        ...params,
      },
    });
    return response.data;
  },

  getStats: async (
    id: string,
    workspaceId: string,
    period: '1h' | '24h' | '7d' | '30d' = '24h'
  ): Promise<MonitorStats> => {
    const response = await apiClient.get<MonitorStats>(`/monitors/${id}/stats`, {
      params: {
        workspace_id: workspaceId,
        period,
      },
    });
    return response.data;
  },
};

// Incidents
export const incidentsApi = {
  list: async (
    workspaceId: string,
    params?: {
      monitor_id?: string;
      status?: string;
      severity?: string;
      skip?: number;
      limit?: number;
    }
  ): Promise<Incident[]> => {
    const response = await apiClient.get<Incident[]>('/incidents', {
      params: {
        workspace_id: workspaceId,
        ...params,
      },
    });
    return response.data;
  },

  get: async (id: string, workspaceId: string): Promise<Incident> => {
    const response = await apiClient.get<Incident>(`/incidents/${id}`, {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },
};

// Alert Channels
export const alertChannelsApi = {
  list: async (workspaceId: string): Promise<AlertChannel[]> => {
    const response = await apiClient.get<AlertChannel[]>('/alert-channels', {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },

  create: async (
    workspaceId: string,
    data: {
      name: string;
      channel_type: 'email' | 'slack' | 'webhook' | 'sms' | 'pagerduty';
      config: Record<string, any>;
    }
  ): Promise<AlertChannel> => {
    const response = await apiClient.post<AlertChannel>('/alert-channels', data, {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },
};

// Alert Rules
export const alertRulesApi = {
  list: async (workspaceId: string): Promise<AlertRule[]> => {
    const response = await apiClient.get<AlertRule[]>('/alert-rules', {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },

  create: async (
    workspaceId: string,
    data: {
      name: string;
      trigger_on_down?: boolean;
      trigger_on_recovery?: boolean;
      min_severity?: 'low' | 'medium' | 'high' | 'critical';
      monitor_ids?: string[];
      monitor_tags?: string[];
      channel_ids: string[];
    }
  ): Promise<AlertRule> => {
    const response = await apiClient.post<AlertRule>('/alert-rules', data, {
      params: { workspace_id: workspaceId },
    });
    return response.data;
  },
};

export default apiClient;
