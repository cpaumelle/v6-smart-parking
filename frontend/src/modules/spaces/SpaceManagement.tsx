import React, { useState, useEffect } from 'react';
import {
  Table, Card, Typography, Button, Space as AntSpace, Tag, Modal, Form,
  Input, Switch, InputNumber, message, Popconfirm, Select,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  CarOutlined,
} from '@ant-design/icons';
import { spacesApi, Space, CreateSpaceData, UpdateSpaceData } from '../../services/api';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Option } = Select;

const STATE_COLORS: Record<string, string> = {
  free: 'success',
  occupied: 'error',
  reserved: 'processing',
  maintenance: 'warning',
  unknown: 'default',
};

export const SpaceManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingSpace, setEditingSpace] = useState<Space | null>(null);
  const [form] = Form.useForm();

  const fetchSpaces = async () => {
    try {
      setLoading(true);
      const response = await spacesApi.list({
        page,
        page_size: pageSize,
      });
      setSpaces(response.items || []);
      setTotal(response.total || 0);
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load spaces');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSpaces();
  }, [page, pageSize]);

  const handleCreate = () => {
    setEditingSpace(null);
    form.resetFields();
    form.setFieldsValue({ enabled: true, auto_release_minutes: 15 });
    setIsModalOpen(true);
  };

  const handleEdit = (space: Space) => {
    setEditingSpace(space);
    form.setFieldsValue({
      code: space.code,
      name: space.name,
      display_name: space.display_name,
      enabled: space.enabled,
      auto_release_minutes: space.auto_release_minutes,
    });
    setIsModalOpen(true);
  };

  const handleDelete = async (spaceId: string) => {
    try {
      await spacesApi.delete(spaceId);
      message.success('Space deleted successfully');
      fetchSpaces();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to delete space');
    }
  };

  const handleStateChange = async (spaceId: string, newState: Space['current_state']) => {
    try {
      await spacesApi.updateState(spaceId, newState);
      message.success('Space state updated');
      fetchSpaces();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to update state');
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      if (editingSpace) {
        const updateData: UpdateSpaceData = {
          name: values.name,
          display_name: values.display_name,
          enabled: values.enabled,
          auto_release_minutes: values.auto_release_minutes,
        };
        await spacesApi.update(editingSpace.id, updateData);
        message.success('Space updated successfully');
      } else {
        const createData: CreateSpaceData = {
          site_id: '00000000-0000-0000-0000-000000000001', // TODO: Get from site selector
          code: values.code,
          name: values.name,
          display_name: values.display_name,
          enabled: values.enabled,
          auto_release_minutes: values.auto_release_minutes,
        };
        await spacesApi.create(createData);
        message.success('Space created successfully');
      }
      setIsModalOpen(false);
      form.resetFields();
      fetchSpaces();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to save space');
    }
  };

  const columns: ColumnsType<Space> = [
    {
      title: 'Code',
      dataIndex: 'code',
      key: 'code',
      sorter: (a, b) => a.code.localeCompare(b.code),
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: 'Display Name',
      dataIndex: 'display_name',
      key: 'display_name',
    },
    {
      title: 'State',
      dataIndex: 'current_state',
      key: 'current_state',
      render: (state: string, record: Space) => (
        <Select
          value={state}
          style={{ width: 130 }}
          onChange={(newState) => handleStateChange(record.id, newState as Space['current_state'])}
        >
          <Option value="free"><Tag color={STATE_COLORS.free}>Free</Tag></Option>
          <Option value="occupied"><Tag color={STATE_COLORS.occupied}>Occupied</Tag></Option>
          <Option value="reserved"><Tag color={STATE_COLORS.reserved}>Reserved</Tag></Option>
          <Option value="maintenance"><Tag color={STATE_COLORS.maintenance}>Maintenance</Tag></Option>
          <Option value="unknown"><Tag color={STATE_COLORS.unknown}>Unknown</Tag></Option>
        </Select>
      ),
    },
    {
      title: 'Enabled',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>{enabled ? 'Yes' : 'No'}</Tag>
      ),
    },
    {
      title: 'Auto-Release',
      dataIndex: 'auto_release_minutes',
      key: 'auto_release_minutes',
      render: (minutes: number) => (minutes ? `${minutes} min` : '-'),
    },
    {
      title: 'Last Changed',
      dataIndex: 'last_state_change',
      key: 'last_state_change',
      render: (date: string) => (date ? new Date(date).toLocaleString() : '-'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <AntSpace>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            Edit
          </Button>
          <Popconfirm
            title="Delete space"
            description="Are you sure you want to delete this space?"
            onConfirm={() => handleDelete(record.id)}
            okText="Yes"
            cancelText="No"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              Delete
            </Button>
          </Popconfirm>
        </AntSpace>
      ),
    },
  ];

  return (
    <div>
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Title level={2} style={{ margin: 0 }}>
            <CarOutlined /> Space Management
          </Title>
          <AntSpace>
            <Button icon={<ReloadOutlined />} onClick={fetchSpaces} loading={loading}>
              Refresh
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              Add Space
            </Button>
          </AntSpace>
        </div>

        <Table
          columns={columns}
          dataSource={spaces}
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
            showTotal: (total) => `Total ${total} spaces`,
          }}
        />
      </Card>

      <Modal
        title={editingSpace ? 'Edit Space' : 'Create Space'}
        open={isModalOpen}
        onOk={() => form.submit()}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
        }}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="Space Code"
            name="code"
            rules={[
              { required: true, message: 'Please enter space code' },
              { pattern: /^[A-Z0-9]+$/, message: 'Code must be uppercase alphanumeric' },
            ]}
          >
            <Input placeholder="e.g., A001" disabled={!!editingSpace} />
          </Form.Item>

          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: 'Please enter name' }]}
          >
            <Input placeholder="e.g., Parking Space A001" />
          </Form.Item>

          <Form.Item label="Display Name" name="display_name">
            <Input placeholder="e.g., Zone A - Space 1" />
          </Form.Item>

          <Form.Item label="Enabled" name="enabled" valuePropName="checked">
            <Switch />
          </Form.Item>

          <Form.Item
            label="Auto-Release (minutes)"
            name="auto_release_minutes"
            tooltip="Automatically release space after this many minutes of occupancy"
          >
            <InputNumber min={0} max={1440} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
