import React, { useState, useEffect } from 'react';
import {
  Table, Card, Typography, Button, Space as AntSpace, Tag, Modal, Form,
  Input, DatePicker, message, Popconfirm, Select, Row, Col, Statistic,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, CalendarOutlined,
  CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons';
import { reservationsApi, Reservation, CreateReservationData } from '../../services/api';
import { spacesApi } from '../../services/api';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;
const { TextArea } = Input;

const STATUS_COLORS: Record<string, string> = {
  active: 'processing',
  completed: 'success',
  cancelled: 'default',
  expired: 'warning',
  pending: 'blue',
  confirmed: 'cyan',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Active',
  completed: 'Completed',
  cancelled: 'Cancelled',
  expired: 'Expired',
  pending: 'Pending',
  confirmed: 'Confirmed',
};

export const ReservationManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [filterStatus, setFilterStatus] = useState<string | undefined>();
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [spaces, setSpaces] = useState<any[]>([]);
  const [selectedSpace, setSelectedSpace] = useState<string | undefined>();
  const [checkingAvailability, setCheckingAvailability] = useState(false);
  const [availabilityMessage, setAvailabilityMessage] = useState<string>('');
  const [form] = Form.useForm();

  // Stats
  const [stats, setStats] = useState({
    active: 0,
    completed: 0,
    cancelled: 0,
    total: 0,
  });

  const fetchReservations = async () => {
    try {
      setLoading(true);
      const response = await reservationsApi.list({
        status: filterStatus,
        page,
        page_size: pageSize,
      });
      setReservations(response.items || []);
      setTotal(response.total || 0);

      // Calculate stats
      const activeCount = response.items?.filter(r => r.status === 'active').length || 0;
      const completedCount = response.items?.filter(r => r.status === 'completed').length || 0;
      const cancelledCount = response.items?.filter(r => r.status === 'cancelled').length || 0;
      setStats({
        active: activeCount,
        completed: completedCount,
        cancelled: cancelledCount,
        total: response.total || 0,
      });
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to load reservations');
    } finally {
      setLoading(false);
    }
  };

  const fetchSpaces = async () => {
    try {
      const response = await spacesApi.list({ page: 1, page_size: 100 });
      setSpaces(response.items || []);
    } catch (error: any) {
      console.error('Failed to load spaces:', error);
    }
  };

  useEffect(() => {
    fetchReservations();
  }, [page, pageSize, filterStatus]);

  useEffect(() => {
    fetchSpaces();
  }, []);

  const handleCreate = () => {
    form.resetFields();
    setAvailabilityMessage('');
    setIsModalOpen(true);
  };

  const handleCheckAvailability = async () => {
    try {
      const values = await form.validateFields(['space_id', 'time_range']);
      const spaceId = values.space_id;
      const [startTime, endTime] = values.time_range;

      setCheckingAvailability(true);
      const result = await reservationsApi.checkAvailability(
        spaceId,
        startTime.toISOString(),
        endTime.toISOString()
      );

      if (result.is_available) {
        setAvailabilityMessage('✓ Space is available for the selected time range');
        message.success('Space is available!');
      } else {
        const conflictCount = result.conflicting_reservations?.length || 0;
        setAvailabilityMessage(
          `✗ Space has ${conflictCount} conflicting reservation(s) for this time range`
        );
        message.warning('Space is not available for this time range');
      }
    } catch (error: any) {
      if (error.errorFields) {
        message.warning('Please fill in space and time range first');
      } else {
        message.error('Failed to check availability');
      }
    } finally {
      setCheckingAvailability(false);
    }
  };

  const handleSubmit = async (values: any) => {
    try {
      const [startTime, endTime] = values.time_range;
      const data: CreateReservationData = {
        space_id: values.space_id,
        start_time: startTime.toISOString(),
        end_time: endTime.toISOString(),
        user_email: values.user_email,
        user_name: values.user_name,
        notes: values.notes,
      };

      await reservationsApi.create(data);
      message.success('Reservation created successfully');
      setIsModalOpen(false);
      form.resetFields();
      fetchReservations();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to create reservation');
    }
  };

  const handleCancel = async (reservationId: string) => {
    try {
      await reservationsApi.cancel(reservationId, 'Cancelled by user');
      message.success('Reservation cancelled');
      fetchReservations();
    } catch (error: any) {
      message.error(error.response?.data?.detail || 'Failed to cancel reservation');
    }
  };

  const columns: ColumnsType<Reservation> = [
    {
      title: 'Space',
      dataIndex: 'space_code',
      key: 'space_code',
      render: (code: string) => <Text strong>{code || 'N/A'}</Text>,
    },
    {
      title: 'User',
      key: 'user',
      render: (_, record) => (
        <div>
          <div>{record.user_name || 'N/A'}</div>
          {record.user_email && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              {record.user_email}
            </Text>
          )}
        </div>
      ),
    },
    {
      title: 'Start Time',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'End Time',
      dataIndex: 'end_time',
      key: 'end_time',
      render: (time: string) => dayjs(time).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Duration',
      key: 'duration',
      render: (_, record) => {
        const duration = dayjs(record.end_time).diff(dayjs(record.start_time), 'hour', true);
        return `${duration.toFixed(1)}h`;
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={STATUS_COLORS[status] || 'default'}>
          {STATUS_LABELS[status] || status.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <AntSpace>
          {record.status === 'active' && (
            <Popconfirm
              title="Cancel this reservation?"
              description="This action cannot be undone."
              onConfirm={() => handleCancel(record.id)}
              okText="Yes, cancel"
              cancelText="No"
            >
              <Button size="small" danger icon={<CloseCircleOutlined />}>
                Cancel
              </Button>
            </Popconfirm>
          )}
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
              title="Total Reservations"
              value={stats.total}
              prefix={<CalendarOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Active"
              value={stats.active}
              valueStyle={{ color: '#1890ff' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Completed"
              value={stats.completed}
              valueStyle={{ color: '#52c41a' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Cancelled"
              value={stats.cancelled}
              valueStyle={{ color: '#8c8c8c' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Table */}
      <Card>
        <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
          <Title level={2} style={{ margin: 0 }}>
            <CalendarOutlined /> Reservation Management
          </Title>
          <AntSpace>
            <Select
              style={{ width: 150 }}
              placeholder="Filter by status"
              allowClear
              value={filterStatus}
              onChange={setFilterStatus}
            >
              <Option value="active">Active</Option>
              <Option value="completed">Completed</Option>
              <Option value="cancelled">Cancelled</Option>
              <Option value="expired">Expired</Option>
            </Select>
            <Button icon={<ReloadOutlined />} onClick={fetchReservations} loading={loading}>
              Refresh
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              New Reservation
            </Button>
          </AntSpace>
        </div>

        <Table
          columns={columns}
          dataSource={reservations}
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
            showTotal: (total) => `Total ${total} reservations`,
          }}
        />
      </Card>

      {/* Create Reservation Modal */}
      <Modal
        title="Create New Reservation"
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
          form.resetFields();
          setAvailabilityMessage('');
        }}
        footer={null}
        width={600}
      >
        <Form form={form} layout="vertical" onFinish={handleSubmit}>
          <Form.Item
            name="space_id"
            label="Parking Space"
            rules={[{ required: true, message: 'Please select a space' }]}
          >
            <Select
              placeholder="Select a parking space"
              showSearch
              optionFilterProp="children"
              onChange={(value) => {
                setSelectedSpace(value);
                setAvailabilityMessage('');
              }}
            >
              {spaces.map((space) => (
                <Option key={space.id} value={space.id}>
                  {space.code} - {space.name} ({space.current_state})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="time_range"
            label="Reservation Time"
            rules={[{ required: true, message: 'Please select time range' }]}
          >
            <RangePicker
              showTime={{ format: 'HH:mm' }}
              format="YYYY-MM-DD HH:mm"
              style={{ width: '100%' }}
              onChange={() => setAvailabilityMessage('')}
            />
          </Form.Item>

          {selectedSpace && (
            <Form.Item>
              <Button
                type="dashed"
                icon={<CheckCircleOutlined />}
                onClick={handleCheckAvailability}
                loading={checkingAvailability}
                block
              >
                Check Availability
              </Button>
              {availabilityMessage && (
                <Text
                  style={{
                    display: 'block',
                    marginTop: 8,
                    color: availabilityMessage.startsWith('✓') ? '#52c41a' : '#ff4d4f',
                  }}
                >
                  {availabilityMessage}
                </Text>
              )}
            </Form.Item>
          )}

          <Form.Item
            name="user_name"
            label="User Name"
            rules={[{ required: true, message: 'Please enter user name' }]}
          >
            <Input placeholder="Enter user name" />
          </Form.Item>

          <Form.Item
            name="user_email"
            label="User Email"
            rules={[
              { required: true, message: 'Please enter user email' },
              { type: 'email', message: 'Please enter a valid email' },
            ]}
          >
            <Input placeholder="Enter user email" />
          </Form.Item>

          <Form.Item name="notes" label="Notes">
            <TextArea rows={3} placeholder="Optional notes about this reservation" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <AntSpace style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setIsModalOpen(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit">
                Create Reservation
              </Button>
            </AntSpace>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
