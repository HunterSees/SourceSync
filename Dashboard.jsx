import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { 
  Speakers, 
  Radio, 
  Volume2, 
  Wifi, 
  WifiOff,
  Play,
  Pause,
  RotateCcw,
  AlertTriangle,
  CheckCircle,
  Clock,
  Activity
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts'

// Mock data for charts
const driftData = [
  { time: '10:00', drift: 12 },
  { time: '10:05', drift: 8 },
  { time: '10:10', drift: 15 },
  { time: '10:15', drift: 6 },
  { time: '10:20', drift: 11 },
  { time: '10:25', drift: 9 },
  { time: '10:30', drift: 13 },
]

const deviceTypeData = [
  { type: 'Chromecast', count: 4 },
  { type: 'AirPlay', count: 2 },
  { type: 'Bluetooth', count: 3 },
  { type: 'Analog', count: 1 },
]

export function Dashboard() {
  const [systemStats, setSystemStats] = useState({
    totalDevices: 10,
    onlineDevices: 8,
    playingDevices: 6,
    avgDrift: 12.5,
    syncQuality: 'good'
  })

  const [recentDevices, setRecentDevices] = useState([
    { id: 'living_room', name: 'Living Room Speaker', type: 'chromecast', status: 'online', drift: 8.2, correlation: 0.92 },
    { id: 'kitchen', name: 'Kitchen Display', type: 'chromecast', status: 'online', drift: 15.1, correlation: 0.87 },
    { id: 'bedroom', name: 'Bedroom Echo', type: 'bluetooth', status: 'online', drift: 6.8, correlation: 0.95 },
    { id: 'office', name: 'Office Speakers', type: 'airplay', status: 'offline', drift: null, correlation: null },
  ])

  const getSyncQualityColor = (quality) => {
    switch (quality) {
      case 'excellent': return 'bg-green-500'
      case 'good': return 'bg-blue-500'
      case 'fair': return 'bg-yellow-500'
      case 'poor': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  const getDeviceIcon = (type) => {
    switch (type) {
      case 'chromecast': return <Speakers className="w-4 h-4" />
      case 'airplay': return <Volume2 className="w-4 h-4" />
      case 'bluetooth': return <Radio className="w-4 h-4" />
      default: return <Speakers className="w-4 h-4" />
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
          <p className="text-muted-foreground">Monitor your SyncStream audio synchronization system</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" size="sm">
            <RotateCcw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
          <Button size="sm">
            <Play className="w-4 h-4 mr-2" />
            Start Stream
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Devices</CardTitle>
            <Speakers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.totalDevices}</div>
            <p className="text-xs text-muted-foreground">
              {systemStats.onlineDevices} online, {systemStats.totalDevices - systemStats.onlineDevices} offline
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Playing Devices</CardTitle>
            <Play className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.playingDevices}</div>
            <p className="text-xs text-muted-foreground">
              {((systemStats.playingDevices / systemStats.onlineDevices) * 100).toFixed(0)}% of online devices
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Drift</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.avgDrift}ms</div>
            <p className="text-xs text-muted-foreground">
              Within acceptable range
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sync Quality</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              <div className={`w-3 h-3 rounded-full ${getSyncQualityColor(systemStats.syncQuality)}`} />
              <span className="text-2xl font-bold capitalize">{systemStats.syncQuality}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              All devices synchronized
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Drift Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Drift Over Time</CardTitle>
            <CardDescription>
              Audio synchronization drift measurements in milliseconds
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={driftData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="drift" 
                  stroke="hsl(var(--primary))" 
                  strokeWidth={2}
                  dot={{ fill: 'hsl(var(--primary))' }}
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Device Types Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Device Types</CardTitle>
            <CardDescription>
              Distribution of connected device types
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={deviceTypeData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="type" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="hsl(var(--primary))" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Recent Devices */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Device Activity</CardTitle>
          <CardDescription>
            Latest status updates from connected devices
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentDevices.map((device) => (
              <div key={device.id} className="flex items-center justify-between p-4 border border-border rounded-lg">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    {getDeviceIcon(device.type)}
                    <div>
                      <p className="font-medium">{device.name}</p>
                      <p className="text-sm text-muted-foreground capitalize">{device.type}</p>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-4">
                  {device.status === 'online' ? (
                    <>
                      <div className="text-right">
                        <p className="text-sm font-medium">{device.drift?.toFixed(1)}ms drift</p>
                        <p className="text-xs text-muted-foreground">
                          {(device.correlation * 100).toFixed(0)}% correlation
                        </p>
                      </div>
                      <Badge variant="default" className="bg-green-500">
                        <Wifi className="w-3 h-3 mr-1" />
                        Online
                      </Badge>
                    </>
                  ) : (
                    <Badge variant="secondary">
                      <WifiOff className="w-3 h-3 mr-1" />
                      Offline
                    </Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* System Alerts */}
      <Card>
        <CardHeader>
          <CardTitle>System Alerts</CardTitle>
          <CardDescription>
            Recent notifications and system status updates
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center space-x-3 p-3 bg-green-50 dark:bg-green-950 rounded-lg">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <div>
                <p className="text-sm font-medium">All devices synchronized</p>
                <p className="text-xs text-muted-foreground">2 minutes ago</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 p-3 bg-yellow-50 dark:bg-yellow-950 rounded-lg">
              <AlertTriangle className="w-5 h-5 text-yellow-600" />
              <div>
                <p className="text-sm font-medium">High drift detected on bedroom speaker</p>
                <p className="text-xs text-muted-foreground">5 minutes ago</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-3 p-3 bg-blue-50 dark:bg-blue-950 rounded-lg">
              <CheckCircle className="w-5 h-5 text-blue-600" />
              <div>
                <p className="text-sm font-medium">New device registered: Office Speakers</p>
                <p className="text-xs text-muted-foreground">10 minutes ago</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

