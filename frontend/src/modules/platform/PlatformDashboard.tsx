import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Typography, Empty, Space, Spin, Alert } from 'antd';
import {
  AppstoreOutlined, WifiOutlined,
  GlobalOutlined, ReloadOutlined
} from '@ant-design/icons';
import { dashboardApi, DashboardData } from '../../services/api';

const { Title, Text } = Typography;

export const PlatformDashboard: React.FC = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await dashboardApi.getDashboardData();
      setDashboardData(data);
      setLastUpdate(new Date());
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load dashboard data');
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();

    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="platform-dashboard">
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={2} style={{ margin: 0 }}>
            <GlobalOutlined /> Platform Dashboard
          </Title>
          <Text type="secondary">
            Multi-Tenant System Overview • Last updated: {lastUpdate.toLocaleTimeString()}
          </Text>
        </div>
        <ReloadOutlined
          spin={loading}
          onClick={fetchDashboardData}
          style={{ fontSize: 20, cursor: 'pointer', color: '#1890ff' }}
        />
      </div>

      {error && (
        <Alert
          message="Error Loading Dashboard"
          description={error}
          type="error"
          closable
          onClose={() => setError(null)}
          style={{ marginBottom: 24 }}
        />
      )}

      {/* Key Metrics Row */}
      <Spin spinning={loading && !dashboardData}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Total Spaces"
                value={dashboardData?.spaces?.total || 0}
                prefix={<AppstoreOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Free Spaces"
                value={dashboardData?.spaces?.free || 0}
                valueStyle={{ color: '#52c41a' }}
                prefix={<AppstoreOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Total Devices"
                value={dashboardData?.devices?.total_devices || 0}
                prefix={<WifiOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={12} md={6}>
            <Card>
              <Statistic
                title="Gateways Online"
                value={dashboardData?.gateways?.online || 0}
                suffix={`/ ${dashboardData?.gateways?.total || 0}`}
                valueStyle={{ color: (dashboardData?.gateways?.online || 0) > 0 ? '#52c41a' : '#f5222d' }}
                prefix={<WifiOutlined />}
              />
            </Card>
          </Col>
        </Row>

        <Card style={{ marginTop: 24 }}>
          <Empty
            description={
              <Space direction="vertical">
                <Text>Full Platform Dashboard coming soon</Text>
                <Text type="secondary">
                  This will include: Tenant performance, System health, Analytics, and more
                </Text>
              </Space>
            }
          />
        </Card>
      </Spin>
    </div>
  );
};
