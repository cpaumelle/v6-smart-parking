import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

export const AnalyticsDashboard: React.FC = () => {
  return (
    <Card>
      <Title level={2}>Analytics Dashboard</Title>
      <Empty description="Analytics dashboard coming soon" />
    </Card>
  );
};
