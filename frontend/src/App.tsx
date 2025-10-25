import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Spin } from 'antd';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { AppLayout } from './components/layout/AppLayout';
import { LoginPage } from './modules/auth/LoginPage';
import { PlatformDashboard } from './modules/platform/PlatformDashboard';
import { OperationsGrid } from './modules/operations/OperationsGrid';
import { DevicePool } from './modules/devices/DevicePool';
import { SpaceManagement } from './modules/spaces/SpaceManagement';
import { ReservationManagement } from './modules/reservations/ReservationManagement';
import { TenantManagement } from './modules/tenants/TenantManagement';
import { SiteManagement } from './modules/sites/SiteManagement';
import { AnalyticsDashboard } from './modules/analytics/AnalyticsDashboard';
import { Settings } from './modules/settings/Settings';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container" style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh'
      }}>
        <Spin size="large" tip="Loading..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Platform Admin Route
const PlatformAdminRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, isAuthenticated, isPlatformAdmin, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-container" style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh'
      }}>
        <Spin size="large" tip="Loading..." />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Allow platform_admin or owner roles
  if (!isPlatformAdmin && user?.role !== 'owner') {
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<PlatformDashboard />} />
        <Route path="operations" element={<OperationsGrid />} />
        <Route path="devices" element={<DevicePool />} />
        <Route path="sites" element={<SiteManagement />} />
        <Route path="spaces" element={<SpaceManagement />} />
        <Route path="reservations" element={<ReservationManagement />} />
        <Route path="analytics" element={<AnalyticsDashboard />} />
        <Route path="settings" element={<Settings />} />

        {/* Platform Admin Only Routes */}
        <Route
          path="tenants"
          element={
            <PlatformAdminRoute>
              <TenantManagement />
            </PlatformAdminRoute>
          }
        />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}

export default App;
