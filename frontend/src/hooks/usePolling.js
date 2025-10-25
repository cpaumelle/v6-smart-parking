/**
 * Simple polling hook to replace WebSocket complexity
 *
 * Usage:
 *   const { data, loading, error, refetch } = usePolling(
 *     () => api.getDashboardData(),
 *     30000  // Poll every 30 seconds
 *   );
 */

import { useState, useEffect, useCallback, useRef } from 'react';

export function usePolling(fetchFunction, intervalMs = 30000, options = {}) {
  const {
    enabled = true,
    onSuccess,
    onError,
    initialData = null,
  } = options;

  const [data, setData] = useState(initialData);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);

  const intervalRef = useRef(null);
  const isMountedRef = useRef(true);

  const fetch = useCallback(async () => {
    if (!enabled || !isMountedRef.current) return;

    try {
      setLoading(true);
      setError(null);

      const result = await fetchFunction();

      if (isMountedRef.current) {
        setData(result);
        setLastUpdate(new Date());

        if (onSuccess) {
          onSuccess(result);
        }
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err);
        console.error('Polling error:', err);

        if (onError) {
          onError(err);
        }
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [fetchFunction, enabled, onSuccess, onError]);

  // Initial fetch and setup polling
  useEffect(() => {
    isMountedRef.current = true;

    // Immediate fetch on mount
    fetch();

    // Set up polling interval
    if (enabled && intervalMs > 0) {
      intervalRef.current = setInterval(fetch, intervalMs);
    }

    // Cleanup
    return () => {
      isMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [fetch, intervalMs, enabled]);

  // Manual refetch function
  const refetch = useCallback(() => {
    fetch();
  }, [fetch]);

  return {
    data,
    loading,
    error,
    refetch,
    lastUpdate,
  };
}

/**
 * Hook for polling with automatic pause on page visibility
 * Stops polling when tab is hidden to save resources
 */
export function useVisibilityAwarePolling(fetchFunction, intervalMs = 30000, options = {}) {
  const [isVisible, setIsVisible] = useState(!document.hidden);

  useEffect(() => {
    const handleVisibilityChange = () => {
      setIsVisible(!document.hidden);
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);

  return usePolling(fetchFunction, intervalMs, {
    ...options,
    enabled: isVisible && (options.enabled !== false),
  });
}
