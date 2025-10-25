import React, { useEffect, useState } from 'react';
import { 
  Row, Col, Card, Statistic, Table, Badge, Select, Button, Space, 
  Typography, Progress, Tooltip, Tag, Alert, Divider 
} from 'antd';
import {
  GlobalOutlined, TeamOutlined, AppstoreOutlined, WifiOutlined,
  DashboardOutlined, SyncOutlined, WarningOutlined, CheckCircleOutlined,
  ArrowUpOutlined, ArrowDownOutlined, LoginOutlined
} from '@ant-design/icons';
import { Gauge, Liquid, Column, Pie } from '@ant-design/plots';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/authStore';
import { useWebSocket } from '../../hooks/useWebSocket';
import { api } from '../../services/api';
import { formatNumber, formatCurrency, formatPercent } from '../../utils/formatters';
import './PlatformDashboard.css';

const { Title, Text } = Typography;

interface TenantMetrics {
  id: string;
  name: string;
  slug: string;
  spaces: number;
  devices: number;
  occupancy: number;
  revenue: number;
  health: 'healthy' | 'warning' | 'error';
  activeUsers: number;
  apiCalls: number;
}

interface SystemHealth {
  api: 'healthy' | 'degraded' | 'down';
  database: 'healthy' | 'degraded' | 'down';
  redis: 'healthy' | 'degraded' | 'down';
  chirpstack: 'healthy' | 'degraded' | 'down';
  backgroundJobs: {
    name: string;
    status: 'running' | 'stopped';
    lastRun: string;
  }[];
}

export function PlatformDashboard() {
  const { t } = useTranslation();
  const { currentTenant, switchTenant, user } = useAuthStore();
  const { subscribe, unsubscribe } = useWebSocket();
  
  const [selectedTenant, setSelectedTenant] = useState<string>('platform');
  const [realtimeMetrics, setRealtimeMetrics] = useState({
    totalOccupancy: 0,
    activeDevices: 0,
    todayRevenue: 0,
    activeAlerts: 0
  });

  // Fetch platform metrics
  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['platform', 'metrics'],
    queryFn: () => api.get('/api/v6/platform/metrics').then(res => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch system health
  const { data: health, isLoading: healthLoading } = useQuery({
    queryKey: ['platform', 'health'],
    queryFn: () => api.get('/api/v6/platform/health').then(res => res.data),
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Fetch tenant list
  const { data: tenants, isLoading: tenantsLoading } = useQuery({
    queryKey: ['platform', 'tenants'],
    queryFn: () => api.get('/api/v6/platform/tenants').then(res => res.data),
  });

  // Impersonate tenant mutation
  const impersonateMutation = useMutation({
    mutationFn: (tenantId: string) => 
      api.post(`/api/v6/platform/impersonate/${tenantId}`).then(res => res.data),
    onSuccess: (data) => {
      toast.success(t('platform.impersonate.success', { tenant: data.tenantName }));
      switchTenant(data);
      window.location.href = '/dashboard';
    },
    onError: () => {
      toast.error(t('platform.impersonate.error'));
    }
  });

  // Subscribe to WebSocket updates
  useEffect(() => {
    const handleMetricsUpdate = (data: any) => {
      setRealtimeMetrics(prev => ({
        ...prev,
        ...data
      }));
    };

    subscribe('/platform/metrics', handleMetricsUpdate);
    subscribe('/platform/alerts', (data) => {
      if (data.severity === 'error') {
        toast.error(data.message);
      } else if (data.severity === 'warning') {
        toast(data.message, { icon: '⚠️' });
      }
    });

    return () => {
      unsubscribe('/platform/metrics');
      unsubscribe('/platform/alerts');
    };
  }, [subscribe, unsubscribe]);

  // Gauge configuration for occupancy
  const occupancyGaugeConfig = {
    percent: (metrics?.globalOccupancy || 0) / 100,
    range: {
      color: ['#52c41a', '#faad14', '#f5222d'],
      width: 12,
    },
    indicator: {
      pointer: {
        style: {
          stroke: '#D0D0D0',
        },
      },
      pin: {
        style: {
          stroke: '#D0D0D0',
        },
      },
    },
    axis: {
      label: {
        formatter: (v: string) => Number(v) * 100,
      },
      subTickLine: {
        count: 3,
      },
    },
    statistic: {
      content: {
        formatter: () => `${formatPercent(metrics?.globalOccupancy || 0)}`,
        style: {
          fontSize: '24px',
          lineHeight: '24px',
        },
      },
      title: {
        formatter: () => t('platform.occupancy'),
        style: {
          fontSize: '14px',
          lineHeight: '14px',
        },
      },
    },
  };

  // Device health gauge
  const deviceHealthGaugeConfig = {
    percent: (metrics?.deviceHealth || 0) / 100,
    range: {
      color: ['#f5222d', '#faad14', '#52c41a'],
      width: 12,
    },
    indicator: {
      pointer: { style: { stroke: '#D0D0D0' } },
      pin: { style: { stroke: '#D0D0D0' } },
    },
    statistic: {
      content: {
        formatter: () => `${metrics?.devicesOnline || 0}/${metrics?.devicesTotal || 0}`,
        style: { fontSize: '20px' },
      },
      title: {
        formatter: () => t('platform.devicesOnline'),
        style: { fontSize: '14px' },
      },
    },
  };

  // Tenant table columns
  const tenantColumns = [
    {
      title: t('platform.tenant'),
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: TenantMetrics) => (
        <Space>
          <Badge status={
            record.health === 'healthy' ? 'success' : 
            record.health === 'warning' ? 'warning' : 'error'
          } />
          <Text strong>{text}</Text>
          <Tag color="blue">{record.slug}</Tag>
        </Space>
      ),
    },
    {
      title: t('platform.spaces'),
      dataIndex: 'spaces',
      key: 'spaces',
      width: 100,
      render: (val: number) => formatNumber(val),
    },
    {
      title: t('platform.occupancy'),
      dataIndex: 'occupancy',
      key: 'occupancy',
      width: 120,
      render: (val: number) => (
        <Progress 
          percent={val} 
          size="small" 
          strokeColor={{
            '0%': '#52c41a',
            '50%': '#faad14',
            '100%': '#f5222d',
          }}
        />
      ),
    },
    {
      title: t('platform.devices'),
      dataIndex: 'devices',
      key: 'devices',
      width: 100,
      render: (val: number) => formatNumber(val),
    },
    {
      title: t('platform.revenue'),
      dataIndex: 'revenue',
      key: 'revenue',
      width: 120,
      render: (val: number) => formatCurrency(val),
    },
    {
      title: t('platform.apiCalls'),
      dataIndex: 'apiCalls',
      key: 'apiCalls',
      width: 100,
      render: (val: number) => formatNumber(val),
    },
    {
      title: t('platform.actions'),
      key: 'actions',
      width: 150,
      fixed: 'right' as const,
      render: (_: any, record: TenantMetrics) => (
        <Space size="small">
          <Tooltip title={t('platform.view')}>
            <Button 
              type="link" 
              size="small" 
              icon={<DashboardOutlined />}
              onClick={() => setSelectedTenant(record.id)}
            />
          </Tooltip>
          <Tooltip title={t('platform.impersonate')}>
            <Button 
              type="link" 
              size="small" 
              icon={<LoginOutlined />}
              onClick={() => impersonateMutation.mutate(record.id)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // System health indicator
  const HealthIndicator = ({ status, name }: { status: string; name: string }) => (
    <div className="health-indicator">
      <Badge 
        status={status === 'healthy' ? 'success' : status === 'degraded' ? 'warning' : 'error'} 
        text={
          <Space>
            <Text>{name}</Text>
            {status === 'healthy' && <CheckCircleOutlined style={{ color: '#52c41a' }} />}
            {status === 'degraded' && <WarningOutlined style={{ color: '#faad14' }} />}
            {status === 'down' && <WarningOutlined style={{ color: '#f5222d' }} />}
          </Space>
        }
      />
    </div>
  );

  return (
    <div className="platform-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <Title level={2}>
          <GlobalOutlined /> {t('platform.title')}
        </Title>
        <Select
          value={selectedTenant}
          style={{ width: 250 }}
          onChange={setSelectedTenant}
          options={[
            { value: 'platform', label: '🌐 ' + t('platform.allTenants') },
            ...(tenants?.map((t: TenantMetrics) => ({
              value: t.id,
              label: `🏢 ${t.name}`
            })) || [])
          ]}
        />
      </div>

      {/* Key Metrics Row */}
      <Row gutter={[16, 16]} className="metrics-row">
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title={t('platform.totalTenants')}
              value={metrics?.totalTenants || 0}
              prefix={<TeamOutlined />}
              suffix={
                metrics?.newTenants > 0 && (
                  <Text type="success" style={{ fontSize: '14px' }}>
                    <ArrowUpOutlined /> {metrics.newTenants}
                  </Text>
                )
              }
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title={t('platform.totalSpaces')}
              value={metrics?.totalSpaces || 0}
              prefix={<AppstoreOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title={t('platform.totalDevices')}
              value={metrics?.totalDevices || 0}
              prefix={<WifiOutlined />}
              valueStyle={{ color: metrics?.deviceHealth > 95 ? '#52c41a' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small">
            <Statistic
              title={t('platform.todayRevenue')}
              value={realtimeMetrics.todayRevenue || metrics?.todayRevenue || 0}
              prefix="€"
              precision={2}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* Gauges and System Health */}
      <Row gutter={[16, 16]} className="gauge-row">
        <Col xs={24} md={8}>
          <Card 
            title={t('platform.globalOccupancy')} 
            size="small"
            extra={<SyncOutlined spin={metricsLoading} />}
          >
            <div style={{ height: 200 }}>
              <Gauge {...occupancyGaugeConfig} />
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card 
            title={t('platform.deviceHealth')} 
            size="small"
            extra={<SyncOutlined spin={metricsLoading} />}
          >
            <div style={{ height: 200 }}>
              <Gauge {...deviceHealthGaugeConfig} />
            </div>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card title={t('platform.systemHealth')} size="small">
            <Space direction="vertical" style={{ width: '100%' }}>
              <HealthIndicator status={health?.api || 'healthy'} name="API" />
              <HealthIndicator status={health?.database || 'healthy'} name="Database" />
              <HealthIndicator status={health?.redis || 'healthy'} name="Redis" />
              <HealthIndicator status={health?.chirpstack || 'healthy'} name="ChirpStack" />
              <Divider style={{ margin: '8px 0' }} />
              <Text type="secondary" style={{ fontSize: '12px' }}>
                {t('platform.backgroundJobs')}: {health?.backgroundJobs?.filter((j: any) => j.status === 'running').length || 0}/4
              </Text>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Alerts */}
      {metrics?.alerts && metrics.alerts.length > 0 && (
        <Alert
          message={t('platform.activeAlerts')}
          description={
            <Space direction="vertical">
              {metrics.alerts.map((alert: any, idx: number) => (
                <Text key={idx}>
                  {alert.severity === 'error' ? '🔴' : '🟡'} {alert.message}
                </Text>
              ))}
            </Space>
          }
          type="warning"
          showIcon
          closable
          style={{ marginBottom: 16 }}
        />
      )}

      {/* Tenant Table */}
      <Card 
        title={t('platform.tenantPerformance')}
        size="small"
        className="tenant-table-card"
      >
        <Table
          columns={tenantColumns}
          dataSource={tenants}
          loading={tenantsLoading}
          rowKey="id"
          size="small"
          pagination={false}
          scroll={{ x: 900 }}
          className="compact-table"
        />
      </Card>
    </div>
  );
}
