/**
 * Simple Authentication Context
 * Replaces complex Zustand store with straightforward React Context
 */

import { createContext, useContext, useState, useEffect } from 'react';
import { authApi, api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check if user is already logged in on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = api.getAuthToken();

      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const userData = await authApi.me();
        setUser(userData);
      } catch (err) {
        console.error('Auth check failed:', err);
        // Invalid token, clear it
        api.setAuthToken(null);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  const login = async (email, password) => {
    try {
      setError(null);
      const response = await authApi.login(email, password);

      // Store token (backend returns 'access_token')
      api.setAuthToken(response.access_token);

      // Set user
      setUser(response.user);

      return response.user;
    } catch (err) {
      setError(err.message || 'Login failed');
      throw err;
    }
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } catch (err) {
      console.error('Logout error:', err);
    } finally {
      // Clear token and user regardless of API call result
      api.setAuthToken(null);
      setUser(null);
    }
  };

  const value = {
    user,
    login,
    logout,
    loading,
    error,
    isAuthenticated: !!user,
    isPlatformAdmin: user?.is_platform_admin || false,
    tenantId: user?.tenant_id || null,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }

  return context;
}

// Helper hook for protected routes
export function useRequireAuth() {
  const { user, loading } = useAuth();

  return { user, loading, isAuthenticated: !!user };
}

// Helper hook for platform admin routes
export function useRequirePlatformAdmin() {
  const { user, loading } = useAuth();

  return {
    user,
    loading,
    isAuthenticated: !!user,
    isPlatformAdmin: user?.is_platform_admin || false,
  };
}
