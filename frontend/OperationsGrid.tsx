import React, { useEffect, useState, useMemo } from 'react';
import {
  Card, Row, Col, Badge, Space, Select, Button, Statistic,
  Typography, Tag, List, Tooltip, Input, Modal, Form, Radio,
  Drawer, Descriptions, Timeline, Alert, Progress, Divider
} from 'antd';
import {
  ReloadOutlined, FilterOutlined, FullscreenOutlined,
  FullscreenExitOutlined, BellOutlined, SettingOutlined,
  CarOutlined, ClockCircleOutlined, ToolOutlined, StopOutlined
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { useWebSocket } from '../../hooks/useWebSocket';
import { api } from '../../services/api';
import './OperationsGrid.css';

const { Title, Text } = Typography;
const { Search } = Input;

interface Space {
  id: string;
  code: string;
  name: string;
  status: 'free' | 'occupied' | 'reserved' | 'maintenance';
  sensorId?: string;
  displayId?: string;
  siteId: string;
  zone?: string;
  lastUpdate?: string;
  reservation?: {
    id: string;
    userEmail: string;
    startTime: string;
    endTime: string;
  };
}

interface Site {
  id: string;
  name: string;
  zones: string[];
}

interface ActivityItem {
  id: string;
  timestamp: string;
  type: 'space_change' | 'reservation' | 'device' | 'alert';
  message: string;
  metadata?: any;
}

// Space status colors and icons
const STATUS_CONFIG = {
  free: { color: '#52c41a', icon: '○', label: 'Free' },
  occupied: { color: '#f5222d', icon: '●', label: 'Occupied' },
  reserved: { color: '#1890ff', icon: '▬', label: 'Reserved' },
  maintenance: { color: '#faad14', icon: '⚠', label: 'Maintenance' },
};

export function OperationsGrid() {
  const { t } = useTranslation();
  const { subscribe, unsubscribe } = useWebSocket();
  
  const [selectedSite, setSelectedSite] = useState<string>('all');
  const [selectedZone, setSelectedZone] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedSpace, setSelectedSpace] = useState<Space | null>(null);
  const [detailsVisible, setDetailsVisible] = useState(false);
  const [activityFeed, setActivityFeed] = useState<ActivityItem[]>([]);
  const [realtimeStats, setRealtimeStats] = useState({
    occupancy: 0,
    free: 0,
    occupied: 0,
    reserved: 0,
    maintenance: 0,
  });

  // Fetch spaces
  const { data: spaces, isLoading, refetch } = useQuery({
    queryKey: ['spaces', selectedSite, selectedZone],
    queryFn: () => api.get('/api/v6/spaces', {
      params: {
        siteId: selectedSite !== 'all' ? selectedSite : undefined,
        zone: selectedZone !== 'all' ? selectedZone : undefined,
      }
    }).then(res => res.data),
    refetchInterval: 30000, // Refresh every 30 seconds as backup
  });

  // Fetch sites
  const { data: sites } = useQuery({
    queryKey: ['sites'],
    queryFn: () => api.get('/api/v6/sites').then(res => res.data),
  });

  // Update space state mutation
  const updateStateMutation = useMutation({
    mutationFn: ({ spaceId, status }: { spaceId: string; status: string }) =>
      api.put(`/api/v6/spaces/${spaceId}/state`, { status }).then(res => res.data),
    onSuccess: (data, variables) => {
      toast.success(t('operations.stateUpdated', { code: data.code }));
      refetch();
    },
    onError: () => {
      toast.error(t('operations.updateError'));
    },
  });

  // Subscribe to WebSocket updates
  useEffect(() => {
    const handleSpaceUpdate = (data: any) => {
      // Update space in real-time
      setActivityFeed(prev => [{
        id: Date.now().toString(),
        timestamp: new Date().toISOString(),
        type: 'space_change',
        message: `Space ${data.code} is now ${data.status}`,
        metadata: data,
      }, ...prev].slice(0, 50)); // Keep last 50 items
    };

    const handleStats = (data: any) => {
      setRealtimeStats(data);
    };

    subscribe('/spaces/updates', handleSpaceUpdate);
    subscribe('/spaces/stats', handleStats);

    return () => {
      unsubscribe('/spaces/updates');
      unsubscribe('/spaces/stats');
    };
  }, [subscribe, unsubscribe]);

  // Filter spaces based on search
  const filteredSpaces = useMemo(() => {
    if (!spaces) return [];
    
    return spaces.filter((space: Space) => {
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          space.code.toLowerCase().includes(query) ||
          space.name?.toLowerCase().includes(query)
        );
      }
      return true;
    });
  }, [spaces, searchQuery]);

  // Calculate statistics
  const stats = useMemo(() => {
    if (!filteredSpaces) return realtimeStats;
    
    const counts = {
      free: 0,
      occupied: 0,
      reserved: 0,
      maintenance: 0,
    };
    
    filteredSpaces.forEach((space: Space) => {
      counts[space.status]++;
    });
    
    return {
      ...counts,
      occupancy: filteredSpaces.length > 0 
        ? Math.round((counts.occupied / filteredSpaces.length) * 100)
        : 0,
    };
  }, [filteredSpaces, realtimeStats]);

  // Space Grid Component
  const SpaceGrid = ({ space }: { space: Space }) => {
    const config = STATUS_CONFIG[space.status];
    
    return (
      <Tooltip
        title={
          <div>
            <div>{space.name || space.code}</div>
            <div>{t(`operations.status.${space.status}`)}</div>
            {space.reservation && (
              <div>{space.reservation.userEmail}</div>
            )}
          </div>
        }
      >
        <div
          className={`space-cell space-${space.status}`}
          onClick={() => {
            setSelectedSpace(space);
            setDetailsVisible(true);
          }}
          style={{ 
            color: config.color,
            cursor: 'pointer'
          }}
        >
          <span className="space-icon">{config.icon}</span>
          <span className="space-code">{space.code}</span>
        </div>
      </Tooltip>
    );
  };

  // Space Details Drawer
  const SpaceDetailsDrawer = () => (
    <Drawer
      title={`Space ${selectedSpace?.code}`}
      placement="right"
      onClose={() => setDetailsVisible(false)}
      open={detailsVisible}
      width={400}
    >
      {selectedSpace && (
        <>
          <Descriptions column={1} bordered size="small">
            <Descriptions.Item label={t('operations.code')}>
              {selectedSpace.code}
            </Descriptions.Item>
            <Descriptions.Item label={t('operations.name')}>
              {selectedSpace.name || '-'}
            </Descriptions.Item>
            <Descriptions.Item label={t('operations.status')}>
              <Badge 
                status={
                  selectedSpace.status === 'free' ? 'success' :
                  selectedSpace.status === 'occupied' ? 'error' :
                  selectedSpace.status === 'reserved' ? 'processing' :
                  'warning'
                }
                text={t(`operations.status.${selectedSpace.status}`)}
              />
            </Descriptions.Item>
            <Descriptions.Item label={t('operations.sensor')}>
              {selectedSpace.sensorId || t('operations.noDevice')}
            </Descriptions.Item>
            <Descriptions.Item label={t('operations.display')}>
              {selectedSpace.displayId || t('operations.noDevice')}
            </Descriptions.Item>
            <Descriptions.Item label={t('operations.lastUpdate')}>
              {selectedSpace.lastUpdate 
                ? new Date(selectedSpace.lastUpdate).toLocaleString()
                : '-'}
            </Descriptions.Item>
          </Descriptions>

          {selectedSpace.reservation && (
            <Card title={t('operations.currentReservation')} size="small" style={{ marginTop: 16 }}>
              <Descriptions column={1} size="small">
                <Descriptions.Item label={t('operations.user')}>
                  {selectedSpace.reservation.userEmail}
                </Descriptions.Item>
                <Descriptions.Item label={t('operations.start')}>
                  {new Date(selectedSpace.reservation.startTime).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item label={t('operations.end')}>
                  {new Date(selectedSpace.reservation.endTime).toLocaleString()}
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}

          <Divider />

          <Space direction="vertical" style={{ width: '100%' }}>
            <Title level={5}>{t('operations.quickActions')}</Title>
            <Radio.Group 
              value={selectedSpace.status}
              onChange={(e) => {
                updateStateMutation.mutate({
                  spaceId: selectedSpace.id,
                  status: e.target.value,
                });
                setDetailsVisible(false);
              }}
            >
              <Radio.Button value="free">{t('operations.setFree')}</Radio.Button>
              <Radio.Button value="occupied">{t('operations.setOccupied')}</Radio.Button>
              <Radio.Button value="maintenance">{t('operations.setMaintenance')}</Radio.Button>
            </Radio.Group>
          </Space>
        </>
      )}
    </Drawer>
  );

  return (
    <div className={`operations-grid ${isFullscreen ? 'fullscreen' : ''}`}>
      {/* Header */}
      <Card size="small" className="operations-header">
        <Row align="middle" justify="space-between">
          <Col>
            <Space>
              <Title level={4} style={{ margin: 0 }}>
                {t('operations.title')}
              </Title>
              <Tag color={stats.occupancy > 80 ? 'red' : stats.occupancy > 60 ? 'orange' : 'green'}>
                {stats.occupancy}% {t('operations.occupied')}
              </Tag>
            </Space>
          </Col>
          <Col>
            <Space>
              <Select
                value={selectedSite}
                onChange={setSelectedSite}
                style={{ width: 150 }}
                options={[
                  { value: 'all', label: t('operations.allSites') },
                  ...(sites?.map((s: Site) => ({
                    value: s.id,
                    label: s.name,
                  })) || []),
                ]}
              />
              <Select
                value={selectedZone}
                onChange={setSelectedZone}
                style={{ width: 120 }}
                options={[
                  { value: 'all', label: t('operations.allZones') },
                  { value: 'A', label: 'Zone A' },
                  { value: 'B', label: 'Zone B' },
                  { value: 'C', label: 'Zone C' },
                ]}
              />
              <Search
                placeholder={t('operations.searchSpace')}
                allowClear
                style={{ width: 200 }}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              <Button icon={<ReloadOutlined />} onClick={() => refetch()} />
              <Button
                icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
                onClick={() => setIsFullscreen(!isFullscreen)}
              />
            </Space>
          </Col>
        </Row>
      </Card>

      {/* Statistics Bar */}
      <Row gutter={16} className="stats-bar">
        <Col span={4}>
          <Card size="small">
            <Statistic
              title={t('operations.free')}
              value={stats.free}
              valueStyle={{ color: '#52c41a', fontSize: '20px' }}
              prefix={STATUS_CONFIG.free.icon}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title={t('operations.occupied')}
              value={stats.occupied}
              valueStyle={{ color: '#f5222d', fontSize: '20px' }}
              prefix={STATUS_CONFIG.occupied.icon}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title={t('operations.reserved')}
              value={stats.reserved}
              valueStyle={{ color: '#1890ff', fontSize: '20px' }}
              prefix={STATUS_CONFIG.reserved.icon}
            />
          </Card>
        </Col>
        <Col span={4}>
          <Card size="small">
            <Statistic
              title={t('operations.maintenance')}
              value={stats.maintenance}
              valueStyle={{ color: '#faad14', fontSize: '20px' }}
              prefix={STATUS_CONFIG.maintenance.icon}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <div className="occupancy-bar">
              <Text>{t('operations.occupancy')}</Text>
              <Progress 
                percent={stats.occupancy} 
                strokeColor={{
                  '0%': '#52c41a',
                  '50%': '#faad14',
                  '100%': '#f5222d',
                }}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* Main Content */}
      <Row gutter={16}>
        {/* Space Grid */}
        <Col xs={24} lg={18}>
          <Card 
            title={t('operations.spaceGrid')}
            size="small"
            loading={isLoading}
          >
            <div className="space-grid-container">
              {filteredSpaces.map((space: Space) => (
                <SpaceGrid key={space.id} space={space} />
              ))}
            </div>
            
            {/* Legend */}
            <div className="grid-legend">
              {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                <Space key={key}>
                  <span style={{ color: config.color }}>{config.icon}</span>
                  <Text>{t(`operations.status.${key}`)}</Text>
                </Space>
              ))}
            </div>
          </Card>
        </Col>

        {/* Activity Feed */}
        <Col xs={24} lg={6}>
          <Card 
            title={
              <Space>
                <BellOutlined />
                {t('operations.liveActivity')}
              </Space>
            }
            size="small"
            className="activity-feed"
          >
            <Timeline>
              {activityFeed.map(item => (
                <Timeline.Item 
                  key={item.id}
                  color={
                    item.type === 'alert' ? 'red' :
                    item.type === 'reservation' ? 'blue' :
                    'gray'
                  }
                >
                  <Text style={{ fontSize: '12px' }}>
                    {new Date(item.timestamp).toLocaleTimeString()}
                  </Text>
                  <br />
                  <Text>{item.message}</Text>
                </Timeline.Item>
              ))}
            </Timeline>
          </Card>
        </Col>
      </Row>

      {/* Space Details Drawer */}
      <SpaceDetailsDrawer />
    </div>
  );
}
