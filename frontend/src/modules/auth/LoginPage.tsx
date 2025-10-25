import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, Card, Typography, Space, Divider, message } from 'antd';
import { UserOutlined, LockOutlined, GlobalOutlined } from '@ant-design/icons';
import { useAuth } from '../../contexts/AuthContext';
import './LoginPage.css';

const { Title, Text } = Typography;

interface VersionInfo {
  version: string;
  build: number;
  buildNumber: string;
  buildTimestamp: string;
}

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [loading, setLoading] = useState(false);
  const [versionInfo, setVersionInfo] = useState<VersionInfo | null>(null);

  useEffect(() => {
    // Fetch version info on component mount
    fetch('/version.json?' + Date.now()) // Cache-bust with timestamp
      .then(res => res.json())
      .then(data => setVersionInfo(data))
      .catch(() => setVersionInfo(null));
  }, []);

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.email, values.password);
      message.success('Login successful!');
      navigate('/dashboard');
    } catch (error: any) {
      message.error(error?.message || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card-wrapper">
        <Card className="login-card">
          <Space direction="vertical" size="large" style={{ width: '100%' }}>
            <div style={{ textAlign: 'center' }}>
              <GlobalOutlined style={{ fontSize: 48, color: '#1890ff' }} />
              <Title level={2} style={{ marginTop: 16 }}>
                Smart Parking V6
              </Title>
              <Text type="secondary">Multi-Tenant Parking Management Platform</Text>
            </div>

            <Divider />

            <Form
              name="login"
              onFinish={onFinish}
              layout="vertical"
              size="large"
              autoComplete="off"
            >
              <Form.Item
                name="email"
                label="Email"
                rules={[
                  { required: true, message: 'Please enter your email' },
                  { type: 'email', message: 'Please enter a valid email' },
                ]}
              >
                <Input prefix={<UserOutlined />} placeholder="Email" />
              </Form.Item>

              <Form.Item
                name="password"
                label="Password"
                rules={[{ required: true, message: 'Please enter your password' }]}
              >
                <Input.Password prefix={<LockOutlined />} placeholder="Password" />
              </Form.Item>

              <Form.Item>
                <Button type="primary" htmlType="submit" block loading={loading}>
                  Sign In
                </Button>
              </Form.Item>
            </Form>

            <div style={{ textAlign: 'center' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {versionInfo
                  ? `V${versionInfo.version} - Build ${versionInfo.buildNumber} - ${new Date(versionInfo.buildTimestamp).toLocaleString()}`
                  : 'V6.0.0 - Enterprise Multi-Tenant Platform'
                }
              </Text>
            </div>
          </Space>
        </Card>
      </div>
    </div>
  );
};
