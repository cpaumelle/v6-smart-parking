import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Statistic, Typography, Empty, Space, Badge, Spin, Alert } from 'antd';
import { AppstoreOutlined, ReloadOutlined } from '@ant-design/icons';
import { dashboardApi, DashboardData } from '../../services/api';

const { Title, Text } = Typography;

// Status colors
const STATUS_CONFIG = {
  free: { color: '#52c41a', icon: '○', label: 'Free' },
  occupied: { color: '#f5222d', icon: '●', label: 'Occupied' },
  reserved: { color: '#1890ff', icon: '▬', label: 'Reserved' },
  maintenance: { color: '#faad14', icon: '⚠', label: 'Maintenance' },
};

export const OperationsGrid: React.FC = () => {
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

  const stats = dashboardData?.spaces || {
    free: 0,
    occupied: 0,
    reserved: 0,
    maintenance: 0,
    occupancy_rate: 0,
  };

  return (
    <div className="operations-grid">
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Space>
            <Title level={2} style={{ margin: 0 }}>
              <AppstoreOutlined /> Operations Dashboard
            </Title>
            <Badge status="processing" text="Live Updates" />
          </Space>
          <Text type="secondary">
            Real-time Space Monitoring • Last updated: {lastUpdate.toLocaleTimeString()}
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

      {/* Statistics Bar */}
      <Spin spinning={loading && !dashboardData}>
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Free"
                value={stats.free}
                suffix={`/ ${dashboardData?.spaces?.total || 0}`}
                valueStyle={{ color: '#52c41a' }}
                prefix={STATUS_CONFIG.free.icon}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Occupied"
                value={stats.occupied}
                valueStyle={{ color: '#f5222d' }}
                prefix={STATUS_CONFIG.occupied.icon}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Reserved"
                value={stats.reserved}
                valueStyle={{ color: '#1890ff' }}
                prefix={STATUS_CONFIG.reserved.icon}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Maintenance"
                value={stats.maintenance}
                valueStyle={{ color: '#faad14' }}
                prefix={STATUS_CONFIG.maintenance.icon}
              />
            </Card>
          </Col>
        </Row>

        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={12}>
            <Card>
              <Statistic
                title="Occupancy Rate"
                value={stats.occupancy_rate}
                precision={1}
                suffix="%"
                valueStyle={{
                  color: stats.occupancy_rate > 80 ? '#f5222d' : stats.occupancy_rate > 50 ? '#faad14' : '#52c41a'
                }}
              />
            </Card>
          </Col>
          <Col span={12}>
            <Card>
              <Statistic
                title="Total Spaces"
                value={dashboardData?.spaces?.total || 0}
                valueStyle={{ color: '#1890ff' }}
              />
            </Card>
          </Col>
        </Row>

        <Card title="Recent Activity">
          {dashboardData?.recent_activity && dashboardData.recent_activity.length > 0 ? (
            <Space direction="vertical" style={{ width: '100%' }}>
              {dashboardData.recent_activity.map((activity, index) => (
                <div key={index} style={{ padding: '8px 0', borderBottom: index < dashboardData.recent_activity.length - 1 ? '1px solid #f0f0f0' : 'none' }}>
                  <Space>
                    <Badge status={activity.status === 'confirmed' ? 'success' : activity.status === 'cancelled' ? 'error' : 'processing'} />
                    <Text strong>{activity.space}</Text>
                    <Text type="secondary">•</Text>
                    <Text>{activity.user}</Text>
                    <Text type="secondary">•</Text>
                    <Text type="secondary">{new Date(activity.timestamp).toLocaleString()}</Text>
                  </Space>
                </div>
              ))}
            </Space>
          ) : (
            <Empty
              description={
                <Space direction="vertical">
                  <Text>No recent activity</Text>
                  <Text type="secondary">
                    Recent reservations and state changes will appear here
                  </Text>
                </Space>
              }
            />
          )}
        </Card>
      </Spin>
    </div>
  );
};
