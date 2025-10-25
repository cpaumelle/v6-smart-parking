import React, { useState, useEffect } from 'react';
import {
  Table, Card, Typography, Button, Space as AntSpace, Tag, Modal, Form,
  Input, message, Popconfirm, Row, Col, Statistic, Descriptions,
  InputNumber,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, EnvironmentOutlined, ShopOutlined,
  EditOutlined, DeleteOutlined, EyeOutlined, DashboardOutlined,
} from '@ant-design/icons';
import { sitesApi, Site } from '../../services/api';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

export const SiteManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [sites, setSites] = useState<Site[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [editingSite, setEditingSite] = useState<Site | null>(null);
  const [selectedSite, setSelectedSite] = useState<Site | null>(null);
  const [form] = Form.useForm();

  // Stats
  const [stats, setStats] = useState({
    total: 0,
    totalSpaces: 0,
    totalDevices: 0,
    totalGateways: 0,
  });

  const fetchSites = async () => {
    try {
      setLoading(true);
      const response = await sitesApi.list({
        include_stats: true,
        page,
        page_size: pageSize,
      });
      setSites(response.sites || []);
      setTotal(response.total || 0);

      // Calculate stats
      const totalSpaces = response.sites?.reduce((sum, s) => sum + (s.space_count || 0), 0) || 0;
      const totalDevices = response.sites?.reduce((sum, s) => sum + (s.device_count || 0), 0) || 0;
      const totalGateways = response.sites?.reduce((sum, s) => sum + (s.gateway_count || 0), 0) || 0;
      setStats({
        total: response.total || 0,
        totalSpaces,
        totalDevices,
        totalGateways,
      });
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load sites');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSites();
  }, [page, pageSize]);

  const handleCreate = () => {
    form.resetFields();
    setEditingSite(null);
    setIsModalOpen(true);
  };

  const handleEdit = (site: Site) => {
    setEditingSite(site);
    form.setFieldsValue({
      name: site.name,
      slug: site.slug,
      address: site.address,
      city: site.city,
      state: site.state,
      postal_code: site.postal_code,
      country: site.country,
      latitude: site.latitude,
      longitude: site.longitude,
      timezone: site.timezone,
    });
    setIsModalOpen(true);
  };

  const handleViewDetails = async (site: Site) => {
    try {
      const fullSite = await sitesApi.get(site.id);
      setSelectedSite(fullSite);
      setIsDetailModalOpen(true);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load site details');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingSite) {
        await sitesApi.update(editingSite.id, values);
        message.success('Site updated successfully');
      } else {
        await sitesApi.create(values);
        message.success('Site created successfully');
      }
      setIsModalOpen(false);
      form.resetFields();
      fetchSites();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to save site');
    }
  };

  const handleDelete = async (site: Site) => {
    try {
      await sitesApi.delete(site.id);
      message.success('Site deleted');
      fetchSites();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to delete site');
    }
  };

  const columns: ColumnsType<Site> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record) => (
        <div>
          <Text strong>{name}</Text>
          <br />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {record.slug}
          </Text>
        </div>
      ),
    },
    {
      title: 'Location',
      key: 'location',
      render: (_, record) => (
        <div>
          {record.city && record.country ? (
            <>
              <Text>{record.city}</Text>
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                {record.country}
              </Text>
            </>
          ) : (
            <Text type="secondary">No location</Text>
          )}
        </div>
      ),
    },
    {
      title: 'Spaces',
      dataIndex: 'space_count',
      key: 'space_count',
      render: (count: number) => (
        <Tag color="blue">{count || 0}</Tag>
      ),
    },
    {
      title: 'Devices',
      dataIndex: 'device_count',
      key: 'device_count',
      render: (count: number) => (
        <Tag color="green">{count || 0}</Tag>
      ),
    },
    {
      title: 'Gateways',
      dataIndex: 'gateway_count',
      key: 'gateway_count',
      render: (count: number) => (
        <Tag color="purple">{count || 0}</Tag>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <AntSpace>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetails(record)}
          >
            View
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Delete this site?"
            description="This action cannot be undone if the site has no spaces or gateways."
            onConfirm={() => handleDelete(record)}
            okText="Yes, delete"
            cancelText="No"
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              Delete
            </Button>
          </Popconfirm>
        </AntSpace>
      ),
    },
  ];

  return (
    <div>
      {/* Statistics */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Sites"
              value={stats.total}
              prefix={<EnvironmentOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Spaces"
              value={stats.totalSpaces}
              valueStyle={{ color: '#1890ff' }}
              prefix={<ShopOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Devices"
              value={stats.totalDevices}
              valueStyle={{ color: '#52c41a' }}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Total Gateways"
              value={stats.totalGateways}
              valueStyle={{ color: '#722ed1' }}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Table */}
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Title level={2} style={{ margin: 0 }}>
            <EnvironmentOutlined /> Site Management
          </Title>
          <AntSpace>
            <Button icon={<ReloadOutlined />} onClick={fetchSites} loading={loading}>
              Refresh
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              New Site
            </Button>
          </AntSpace>
        </div>

        <Table
          columns={columns}
          dataSource={sites}
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
            showTotal: (total) => `Total ${total} sites`,
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingSite ? 'Edit Site' : 'Create New Site'}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={800}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="Site Name"
                rules={[{ required: true, message: 'Please enter site name' }]}
              >
                <Input placeholder="Enter site name" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="slug"
                label="Site Slug"
                rules={[
                  { required: true, message: 'Please enter site slug' },
                  { pattern: /^[a-z0-9-_]+$/i, message: 'Slug must be lowercase alphanumeric with hyphens/underscores' },
                ]}
              >
                <Input placeholder="site-slug" disabled={!!editingSite} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="address" label="Address">
            <Input placeholder="Street address" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="city" label="City">
                <Input placeholder="City" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="state" label="State/Province">
                <Input placeholder="State" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="postal_code" label="Postal Code">
                <Input placeholder="Postal code" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="country" label="Country">
            <Input placeholder="Country" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="latitude" label="Latitude">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="48.8566"
                  min={-90}
                  max={90}
                  step={0.000001}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="longitude" label="Longitude">
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="2.3522"
                  min={-180}
                  max={180}
                  step={0.000001}
                />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="timezone" label="Timezone">
                <Input placeholder="Europe/Paris" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ marginBottom: 0 }}>
            <AntSpace style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit">
                {editingSite ? 'Update' : 'Create'} Site
              </Button>
            </AntSpace>
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="Site Details"
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={null}
        width={800}
      >
        {selectedSite && (
          <>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Name">{selectedSite.name}</Descriptions.Item>
              <Descriptions.Item label="Slug">{selectedSite.slug}</Descriptions.Item>
              <Descriptions.Item label="Address" span={2}>
                {selectedSite.address || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="City">{selectedSite.city || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="State">{selectedSite.state || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="Postal Code">
                {selectedSite.postal_code || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Country">{selectedSite.country || 'N/A'}</Descriptions.Item>
              <Descriptions.Item label="Latitude">
                {selectedSite.latitude?.toFixed(6) || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Longitude">
                {selectedSite.longitude?.toFixed(6) || 'N/A'}
              </Descriptions.Item>
              <Descriptions.Item label="Timezone">
                {selectedSite.timezone || 'UTC'}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {dayjs(selectedSite.created_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
            </Descriptions>

            <Title level={4} style={{ marginTop: 24 }}>Statistics</Title>
            <Row gutter={16}>
              <Col span={8}>
                <Card>
                  <Statistic title="Spaces" value={selectedSite.space_count || 0} />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic title="Devices" value={selectedSite.device_count || 0} />
                </Card>
              </Col>
              <Col span={8}>
                <Card>
                  <Statistic title="Gateways" value={selectedSite.gateway_count || 0} />
                </Card>
              </Col>
            </Row>

            {(selectedSite.free_spaces !== undefined || selectedSite.occupied_spaces !== undefined) && (
              <>
                <Title level={4} style={{ marginTop: 24 }}>Current Occupancy</Title>
                <Row gutter={16}>
                  <Col span={12}>
                    <Card>
                      <Statistic
                        title="Free Spaces"
                        value={selectedSite.free_spaces || 0}
                        valueStyle={{ color: '#52c41a' }}
                      />
                    </Card>
                  </Col>
                  <Col span={12}>
                    <Card>
                      <Statistic
                        title="Occupied Spaces"
                        value={selectedSite.occupied_spaces || 0}
                        valueStyle={{ color: '#ff4d4f' }}
                      />
                    </Card>
                  </Col>
                </Row>
              </>
            )}
          </>
        )}
      </Modal>
    </div>
  );
};
