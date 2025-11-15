'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuth } from '@/lib/auth-context';
import { getAccessToken } from '@/lib/api';

interface WebSocketContextType {
  socket: Socket | null;
  isConnected: boolean;
  subscribe: (event: string, callback: (data: any) => void) => void;
  unsubscribe: (event: string, callback: (data: any) => void) => void;
  emit: (event: string, data: any) => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [socket, setSocket] = useState<Socket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const { isAuthenticated, user } = useAuth();

  useEffect(() => {
    if (!isAuthenticated || !user) {
      // Disconnect if not authenticated
      if (socket) {
        socket.disconnect();
        setSocket(null);
        setIsConnected(false);
      }
      return;
    }

    // Create socket connection
    const token = getAccessToken();
    const newSocket = io(WS_URL, {
      auth: {
        token,
      },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    newSocket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    });

    newSocket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    });

    newSocket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      setIsConnected(false);
    });

    setSocket(newSocket);

    return () => {
      newSocket.disconnect();
    };
  }, [isAuthenticated, user]);

  const subscribe = useCallback(
    (event: string, callback: (data: any) => void) => {
      if (socket) {
        socket.on(event, callback);
      }
    },
    [socket]
  );

  const unsubscribe = useCallback(
    (event: string, callback: (data: any) => void) => {
      if (socket) {
        socket.off(event, callback);
      }
    },
    [socket]
  );

  const emit = useCallback(
    (event: string, data: any) => {
      if (socket && isConnected) {
        socket.emit(event, data);
      }
    },
    [socket, isConnected]
  );

  const value = {
    socket,
    isConnected,
    subscribe,
    unsubscribe,
    emit,
  };

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>;
}

export function useWebSocket() {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
}

// Custom hooks for specific events
export function useMonitorUpdates(callback: (data: any) => void) {
  const { subscribe, unsubscribe } = useWebSocket();

  useEffect(() => {
    subscribe('monitor:update', callback);
    return () => {
      unsubscribe('monitor:update', callback);
    };
  }, [callback, subscribe, unsubscribe]);
}

export function useIncidentUpdates(callback: (data: any) => void) {
  const { subscribe, unsubscribe } = useWebSocket();

  useEffect(() => {
    subscribe('incident:created', callback);
    subscribe('incident:updated', callback);
    subscribe('incident:resolved', callback);

    return () => {
      unsubscribe('incident:created', callback);
      unsubscribe('incident:updated', callback);
      unsubscribe('incident:resolved', callback);
    };
  }, [callback, subscribe, unsubscribe]);
}

export function useAlertUpdates(callback: (data: any) => void) {
  const { subscribe, unsubscribe } = useWebSocket();

  useEffect(() => {
    subscribe('alert:sent', callback);
    return () => {
      unsubscribe('alert:sent', callback);
    };
  }, [callback, subscribe, unsubscribe]);
}
