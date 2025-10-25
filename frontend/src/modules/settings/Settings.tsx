import React from 'react';
import { Card, Typography, Empty } from 'antd';

const { Title } = Typography;

export const Settings: React.FC = () => {
  return (
    <Card>
      <Title level={2}>Settings</Title>
      <Empty description="Settings page coming soon" />
    </Card>
  );
};
