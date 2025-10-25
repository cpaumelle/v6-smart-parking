import React, { useState, useEffect } from 'react';
import {
  Table, Card, Typography, Button, Space as AntSpace, Tag, Modal, Form,
  Input, message, Popconfirm, Select, Row, Col, Statistic, Descriptions,
  Badge,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, TeamOutlined, ShopOutlined,
  EditOutlined, DeleteOutlined, StopOutlined, CheckCircleOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { tenantsApi, Tenant } from '../../services/api';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Option } = Select;

export const TenantManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filterType, setFilterType] = useState<string | undefined>();
  const [filterActive, setFilterActive] = useState<boolean | undefined>();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);
  const [editingTenant, setEditingTenant] = useState<Tenant | null>(null);
  const [selectedTenant, setSelectedTenant] = useState<Tenant | null>(null);
  const [form] = Form.useForm();

  // Stats
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    trial: 0,
    suspended: 0,
  });

  const fetchTenants = async () => {
    try {
      setLoading(true);
      const response = await tenantsApi.list({
        tenant_type: filterType,
        is_active: filterActive,
        page,
        page_size: pageSize,
      });
      setTenants(response.tenants || []);
      setTotal(response.total || 0);

      // Calculate stats
      const activeCount = response.tenants?.filter(t => t.is_active).length || 0;
      const trialCount = response.tenants?.filter(t => t.type === 'trial').length || 0;
      const suspendedCount = response.tenants?.filter(t => !t.is_active).length || 0;
      setStats({
        total: response.total || 0,
        active: activeCount,
        trial: trialCount,
        suspended: suspendedCount,
      });
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTenants();
  }, [page, pageSize, filterType, filterActive]);

  const handleCreate = () => {
    form.resetFields();
    setEditingTenant(null);
    setIsModalOpen(true);
  };

  const handleEdit = (tenant: Tenant) => {
    setEditingTenant(tenant);
    form.setFieldsValue({
      name: tenant.name,
      slug: tenant.slug,
      tenant_type: tenant.type,
      subscription_tier: tenant.subscription_tier,
    });
    setIsModalOpen(true);
  };

  const handleViewDetails = async (tenant: Tenant) => {
    try {
      const fullTenant = await tenantsApi.get(tenant.id);
      setSelectedTenant(fullTenant);
      setIsDetailModalOpen(true);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load tenant details');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingTenant) {
        await tenantsApi.update(editingTenant.id, values);
        message.success('Tenant updated successfully');
      } else {
        await tenantsApi.create(values);
        message.success('Tenant created successfully');
      }
      setIsModalOpen(false);
      form.resetFields();
      fetchTenants();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to save tenant');
    }
  };

  const handleSuspend = async (tenant: Tenant) => {
    try {
      await tenantsApi.suspend(tenant.id, 'Suspended by admin');
      message.success('Tenant suspended');
      fetchTenants();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to suspend tenant');
    }
  };

  const handleActivate = async (tenant: Tenant) => {
    try {
      await tenantsApi.activate(tenant.id);
      message.success('Tenant activated');
      fetchTenants();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to activate tenant');
    }
  };

  const handleDelete = async (tenant: Tenant) => {
    try {
      await tenantsApi.delete(tenant.id);
      message.success('Tenant deleted');
      fetchTenants();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to delete tenant');
    }
  };

  const columns: ColumnsType<Tenant> = [
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
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => (
        <Tag color={type === 'platform' ? 'purple' : type === 'trial' ? 'orange' : 'blue'}>
          {type.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Subscription',
      dataIndex: 'subscription_tier',
      key: 'subscription_tier',
      render: (tier: string) => (
        <Tag color={tier === 'enterprise' ? 'gold' : tier === 'professional' ? 'blue' : 'default'}>
          {tier?.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Status',
      key: 'status',
      render: (_, record) => (
        <Badge
          status={record.is_active ? 'success' : 'error'}
          text={record.is_active ? 'Active' : 'Suspended'}
        />
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
            disabled={record.type === 'platform'}
          >
            Edit
          </Button>
          {record.is_active ? (
            <Popconfirm
              title="Suspend this tenant?"
              description="This will prevent users from accessing the system."
              onConfirm={() => handleSuspend(record)}
              okText="Yes, suspend"
              cancelText="No"
            >
              <Button
                size="small"
                danger
                icon={<StopOutlined />}
                disabled={record.type === 'platform'}
              >
                Suspend
              </Button>
            </Popconfirm>
          ) : (
            <Button
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => handleActivate(record)}
              disabled={record.type === 'platform'}
            >
              Activate
            </Button>
          )}
          <Popconfirm
            title="Delete this tenant?"
            description="This action cannot be undone."
            onConfirm={() => handleDelete(record)}
            okText="Yes, delete"
            cancelText="No"
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              disabled={record.type === 'platform'}
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
              title="Total Tenants"
              value={stats.total}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active"
              value={stats.active}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Trial"
              value={stats.trial}
              valueStyle={{ color: '#fa8c16' }}
              prefix={<ShopOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Suspended"
              value={stats.suspended}
              valueStyle={{ color: '#ff4d4f' }}
              prefix={<StopOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Table */}
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Title level={2} style={{ margin: 0 }}>
            <TeamOutlined /> Tenant Management
          </Title>
          <AntSpace>
            <Select
              style={{ width: 150 }}
              placeholder="Filter by type"
              allowClear
              value={filterType}
              onChange={setFilterType}
            >
              <Option value="customer">Customer</Option>
              <Option value="trial">Trial</Option>
              <Option value="platform">Platform</Option>
            </Select>
            <Select
              style={{ width: 150 }}
              placeholder="Filter by status"
              allowClear
              value={filterActive}
              onChange={setFilterActive}
            >
              <Option value={true}>Active</Option>
              <Option value={false}>Suspended</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchTenants} loading={loading}>
              Refresh
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              New Tenant
            </Button>
          </AntSpace>
        </div>

        <Table
          columns={columns}
          dataSource={tenants}
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
            showTotal: (total) => `Total ${total} tenants`,
          }}
        />
      </Card>

      {/* Create/Edit Modal */}
      <Modal
        title={editingTenant ? 'Edit Tenant' : 'Create New Tenant'}
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="name"
            label="Tenant Name"
            rules={[{ required: true, message: 'Please enter tenant name' }]}
          >
            <Input placeholder="Enter tenant name" />
          </Form.Item>

          <Form.Item
            name="slug"
            label="Slug"
            rules={[
              { required: true, message: 'Please enter slug' },
              { pattern: /^[a-z0-9-]+$/, message: 'Slug must be lowercase alphanumeric with hyphens' },
            ]}
          >
            <Input placeholder="tenant-slug" disabled={!!editingTenant} />
          </Form.Item>

          {!editingTenant && (
            <Form.Item
              name="tenant_type"
              label="Type"
              initialValue="customer"
              rules={[{ required: true }]}
            >
              <Select>
                <Option value="customer">Customer</Option>
                <Option value="trial">Trial</Option>
              </Select>
            </Form.Item>
          )}

          <Form.Item
            name="subscription_tier"
            label="Subscription Tier"
            initialValue="basic"
            rules={[{ required: true }]}
          >
            <Select>
              <Option value="basic">Basic</Option>
              <Option value="professional">Professional</Option>
              <Option value="enterprise">Enterprise</Option>
            </Select>
          </Form.Item>

          {!editingTenant && (
            <Form.Item name="trial_days" label="Trial Days (optional)">
              <Input type="number" placeholder="Leave empty for no trial" />
            </Form.Item>
          )}

          <Form.Item style={{ marginBottom: 0 }}>
            <AntSpace style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit">
                {editingTenant ? 'Update' : 'Create'} Tenant
              </Button>
            </AntSpace>
          </Form.Item>
        </Form>
      </Modal>

      {/* Detail Modal */}
      <Modal
        title="Tenant Details"
        open={isDetailModalOpen}
        onCancel={() => setIsDetailModalOpen(false)}
        footer={null}
        width={800}
      >
        {selectedTenant && (
          <>
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Name">{selectedTenant.name}</Descriptions.Item>
              <Descriptions.Item label="Slug">{selectedTenant.slug}</Descriptions.Item>
              <Descriptions.Item label="Type">
                <Tag color={selectedTenant.type === 'platform' ? 'purple' : selectedTenant.type === 'trial' ? 'orange' : 'blue'}>
                  {selectedTenant.type.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Status">
                <Badge
                  status={selectedTenant.is_active ? 'success' : 'error'}
                  text={selectedTenant.is_active ? 'Active' : 'Suspended'}
                />
              </Descriptions.Item>
              <Descriptions.Item label="Subscription">
                {selectedTenant.subscription_tier?.toUpperCase()}
              </Descriptions.Item>
              <Descriptions.Item label="Created">
                {dayjs(selectedTenant.created_at).format('YYYY-MM-DD HH:mm')}
              </Descriptions.Item>
            </Descriptions>

            {selectedTenant.stats && (
              <>
                <Title level={4} style={{ marginTop: 24 }}>Statistics</Title>
                <Row gutter={16}>
                  <Col span={8}>
                    <Card>
                      <Statistic title="Users" value={selectedTenant.stats.user_count} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic title="Devices" value={selectedTenant.stats.device_count} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic title="Spaces" value={selectedTenant.stats.space_count} />
                    </Card>
                  </Col>
                </Row>
                <Row gutter={16} style={{ marginTop: 16 }}>
                  <Col span={8}>
                    <Card>
                      <Statistic title="Sites" value={selectedTenant.stats.site_count} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic title="Gateways" value={selectedTenant.stats.gateway_count} />
                    </Card>
                  </Col>
                  <Col span={8}>
                    <Card>
                      <Statistic title="Reservations" value={selectedTenant.stats.reservation_count} />
                    </Card>
                  </Col>
                </Row>
              </>
            )}

            <Title level={4} style={{ marginTop: 24 }}>Features</Title>
            <div>
              {selectedTenant.features && Object.entries(selectedTenant.features).map(([key, value]) => (
                <Tag key={key} color={value ? 'green' : 'default'} style={{ marginBottom: 8 }}>
                  {key}: {value ? 'Enabled' : 'Disabled'}
                </Tag>
              ))}
            </div>

            <Title level={4} style={{ marginTop: 24 }}>Limits</Title>
            <Descriptions bordered column={2}>
              {selectedTenant.limits && Object.entries(selectedTenant.limits).map(([key, value]) => (
                <Descriptions.Item key={key} label={key}>
                  {value as any}
                </Descriptions.Item>
              ))}
            </Descriptions>
          </>
        )}
      </Modal>
    </div>
  );
};
