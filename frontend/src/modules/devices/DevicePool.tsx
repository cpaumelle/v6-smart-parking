import React, { useState, useEffect } from 'react';
import {
  Table, Card, Typography, Button, Space, Tag, message, Statistic, Row, Col,
} from 'antd';
import {
  ReloadOutlined, WifiOutlined,
} from '@ant-design/icons';
import { devicesApi, Device } from '../../services/api';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;

export const DevicePool: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filterStatus, setFilterStatus] = useState<'assigned' | 'unassigned' | undefined>();

  const fetchDevices = async () => {
    try {
      setLoading(true);
      const response = await devicesApi.list({
        status: filterStatus,
        page,
        page_size: pageSize,
      });
      setDevices(response.items || []);
      setTotal(response.total || 0);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load devices');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await devicesApi.getPoolStats();
      setStats(data);
    } catch (error: any) {
      console.error('Failed to load device stats:', error);
    }
  };

  useEffect(() => {
    fetchDevices();
    fetchStats();
  }, [page, pageSize, filterStatus]);

  const columns: ColumnsType<Device> = [
    {
      title: 'DevEUI',
      dataIndex: 'dev_eui',
      key: 'dev_eui',
      render: (eui: string) => <code>{eui}</code>,
    },
    {
      title: 'Type',
      dataIndex: 'device_type',
      key: 'device_type',
      render: (type: string) => (
        <Tag color={type === 'sensor' ? 'blue' : 'green'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => name || '-',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'assigned' ? 'success' : 'default'}>
          {status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Assigned To',
      dataIndex: 'space_code',
      key: 'space_code',
      render: (code: string) => code || '-',
    },
    {
      title: 'Last Seen',
      dataIndex: 'last_seen_at',
      key: 'last_seen_at',
      render: (date: string) => (date ? new Date(date).toLocaleString() : 'Never'),
    },
  ];

  return (
    <div>
      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Sensors"
                value={stats.total_sensors || 0}
                prefix={<WifiOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Unassigned Sensors"
                value={stats.unassigned_sensors || 0}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Total Displays"
                value={stats.total_displays || 0}
                prefix={<WifiOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic
                title="Unassigned Displays"
                value={stats.unassigned_displays || 0}
                valueStyle={{ color: '#faad14' }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Title level={2} style={{ margin: 0 }}>
            <WifiOutlined /> Device Pool
          </Title>
          <Space>
            <Button onClick={() => setFilterStatus(undefined)} type={!filterStatus ? 'primary' : 'default'}>
              All
            </Button>
            <Button onClick={() => setFilterStatus('assigned')} type={filterStatus === 'assigned' ? 'primary' : 'default'}>
              Assigned
            </Button>
            <Button onClick={() => setFilterStatus('unassigned')} type={filterStatus === 'unassigned' ? 'primary' : 'default'}>
              Unassigned
            </Button>
            <Button icon={<ReloadOutlined />} onClick={() => { fetchDevices(); fetchStats(); }} loading={loading}>
              Refresh
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={devices}
          rowKey="id"
          loading={loading}
          pagination={{
            current: page,
            pageSize,
            total,
            onChange: (newPage, newPageSize) => {
              setPage(newPage);
              if (newPageSize !== pageSize) {
                setPageSize(newPageSize);
              }
            },
            showSizeChanger: true,
            showTotal: (total) => `Total ${total} devices`,
          }}
        />
      </Card>
    </div>
  );
};
