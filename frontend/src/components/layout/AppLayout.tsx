import React, { useState, useEffect } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Layout, Menu, Avatar, Dropdown, Space, Typography, Badge, theme,
} from 'antd';
import {
  DashboardOutlined,
  AppstoreOutlined,
  WifiOutlined,
  CarOutlined,
  CalendarOutlined,
  BarChartOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
  GlobalOutlined,
  EnvironmentOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import './AppLayout.css';

const { Header, Sider, Content, Footer } = Layout;
const { Text } = Typography;

interface VersionInfo {
  version: string;
  build: number;
  buildNumber: string;
  buildTimestamp: string;
}

export const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [collapsed, setCollapsed] = useState(false);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);
  const [isOnline, setIsOnline] = useState(navigator.onLine);

  useEffect(() => {
    // Fetch version info on component mount
    fetch('/version.json?' + Date.now())
      .then(res => res.json())
      .then(data => setVersionInfo(data))
      .catch(() => setVersionInfo(null));
  }, []);

  // Simple online/offline detection
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const {
    token: { colorBgContainer },
  } = theme.useToken();

  const isPlatformAdmin = user?.role === 'platform_admin' || user?.role === 'owner';

  // Menu items
  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/operations',
      icon: <AppstoreOutlined />,
      label: 'Operations',
    },
    {
      key: '/sites',
      icon: <EnvironmentOutlined />,
      label: 'Sites',
    },
    {
      key: '/spaces',
      icon: <CarOutlined />,
      label: 'Spaces',
    },
    {
      key: '/devices',
      icon: <WifiOutlined />,
      label: 'Devices',
    },
    {
      key: '/reservations',
      icon: <CalendarOutlined />,
      label: 'Reservations',
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: 'Analytics',
    },
    ...(isPlatformAdmin
      ? [
          {
            key: '/tenants',
            icon: <TeamOutlined />,
            label: 'Tenants',
          },
        ]
      : []),
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ];

  // User dropdown menu
  const userMenuItems = [
    {
      key: 'profile',
      label: 'Profile',
      icon: <UserOutlined />,
      onClick: () => navigate('/settings'),
    },
    {
      type: 'divider' as const,
    },
    {
      key: 'logout',
      label: 'Logout',
      icon: <LogoutOutlined />,
      danger: true,
      onClick: logout,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="dark"
        width={240}
      >
        <div className="logo-container">
          {!collapsed ? (
            <>
              <GlobalOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <Text style={{ color: 'white', marginLeft: 8, fontSize: 16, fontWeight: 'bold' }}>
                Parking V6
              </Text>
            </>
          ) : (
            <GlobalOutlined style={{ fontSize: 24, color: '#1890ff' }} />
          )}
        </div>

        <Menu
          theme="dark"
          selectedKeys={[location.pathname]}
          mode="inline"
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>

      <Layout>
        <Header style={{ padding: '0 24px', background: colorBgContainer }}>
          <div className="header-content">
            <div className="header-left">
              <Space size="large">
                <div>
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    Tenant
                  </Text>
                  <br />
                  <Text strong>{user?.tenant_name || 'Platform'}</Text>
                </div>

                <Badge status={isOnline ? 'success' : 'error'} text={isOnline ? 'Online' : 'Offline'} />
              </Space>
            </div>

            <div className="header-right">
              <Space size="large">
                <Badge count={0}>
                  <BellOutlined style={{ fontSize: 20 }} />
                </Badge>

                <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                  <Space style={{ cursor: 'pointer' }}>
                    <Avatar icon={<UserOutlined />} />
                    <div>
                      <Text strong>
                        {user?.username || user?.email}
                      </Text>
                      <br />
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {user?.role?.replace('_', ' ') || 'User'}
                      </Text>
                    </div>
                  </Space>
                </Dropdown>
              </Space>
            </div>
          </div>
        </Header>

        <Content style={{ margin: '24px', minHeight: 'calc(100vh - 152px)' }}>
          <Outlet />
        </Content>

        <Footer style={{ textAlign: 'center', background: colorBgContainer, padding: '12px 50px' }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {versionInfo
              ? `Smart Parking V${versionInfo.version} - Build ${versionInfo.buildNumber} (${new Date(versionInfo.buildTimestamp).toLocaleString()})`
              : 'Smart Parking V6 Platform'}
          </Text>
        </Footer>
      </Layout>
    </Layout>
  );
};
