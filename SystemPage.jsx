import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { 
  Server, 
  Cpu, 
  HardDrive, 
  Wifi, 
  Activity,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Download,
  Upload,
  Settings,
  Database,
  Shield,
  Clock
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'

// Mock data
const systemMetricsData = [
  { time: '10:00', cpu: 15, memory: 45, network: 12 },
  { time: '10:05', cpu: 18, memory: 47, network: 15 },
  { time: '10:10', cpu: 12, memory: 44, network: 8 },
  { time: '10:15', cpu: 22, memory: 48, network: 18 },
  { time: '10:20', cpu: 16, memory: 46, network: 11 },
  { time: '10:25', cpu: 14, memory: 45, network: 9 },
  { time: '10:30', cpu: 19, memory: 47, network: 14 },
]

const logEntries = [
  {
    timestamp: new Date(Date.now() - 60000),
    level: 'INFO',
    component: 'sync',
    message: 'Drift report received from living_room: 8.2ms'
  },
  {
    timestamp: new Date(Date.now() - 120000),
    level: 'DEBUG',
    component: 'mqtt',
    message: 'Device heartbeat: kitchen_speaker'
  },
  {
    timestamp: new Date(Date.now() - 180000),
    level: 'WARNING',
    component: 'audio',
    message: 'Buffer underrun detected, adjusting buffer size'
  },
  {
    timestamp: new Date(Date.now() - 240000),
    level: 'INFO',
    component: 'device',
    message: 'New device registered: bedroom_echo'
  },
  {
    timestamp: new Date(Date.now() - 300000),
    level: 'ERROR',
    component: 'network',
    message: 'Failed to connect to device office_speakers'
  }
]

export function SystemPage() {
  const [systemHealth, setSystemHealth] = useState({
    overall: 'healthy',
    components: {
      database: 'healthy',
      mqtt: 'healthy',
      audio: 'healthy',
      network: 'degraded'
    }
  })

  const [systemStats, setSystemStats] = useState({
    uptime: 168.5,
    cpuUsage: 15.2,
    memoryUsage: 45.8,
    diskUsage: 32.1,
    networkLatency: 2.1,
    totalDevices: 10,
    onlineDevices: 8,
    syncEvents: 1247
  })

  const getHealthColor = (status) => {
    switch (status) {
      case 'healthy': return 'text-green-600'
      case 'degraded': return 'text-yellow-600'
      case 'unhealthy': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getHealthIcon = (status) => {
    switch (status) {
      case 'healthy': return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'degraded': return <AlertTriangle className="w-4 h-4 text-yellow-600" />
      case 'unhealthy': return <AlertTriangle className="w-4 h-4 text-red-600" />
      default: return <CheckCircle className="w-4 h-4 text-gray-600" />
    }
  }

  const getLevelColor = (level) => {
    switch (level) {
      case 'ERROR': return 'text-red-600 bg-red-50 dark:bg-red-950'
      case 'WARNING': return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-950'
      case 'INFO': return 'text-blue-600 bg-blue-50 dark:bg-blue-950'
      case 'DEBUG': return 'text-gray-600 bg-gray-50 dark:bg-gray-950'
      default: return 'text-gray-600 bg-gray-50 dark:bg-gray-950'
    }
  }

  const formatUptime = (hours) => {
    const days = Math.floor(hours / 24)
    const remainingHours = Math.floor(hours % 24)
    return `${days}d ${remainingHours}h`
  }

  const handleRestart = (component) => {
    console.log(`Restarting ${component}`)
  }

  const handleBackup = () => {
    console.log('Creating backup')
  }

  const handleUpdate = () => {
    console.log('Checking for updates')
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">System</h1>
          <p className="text-muted-foreground">Monitor system health and manage configuration</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={handleBackup}>
            <Download className="w-4 h-4 mr-2" />
            Backup
          </Button>
          <Button variant="outline" onClick={handleUpdate}>
            <Upload className="w-4 h-4 mr-2" />
            Update
          </Button>
          <Button onClick={() => handleRestart('all')}>
            <RefreshCw className="w-4 h-4 mr-2" />
            Restart
          </Button>
        </div>
      </div>

      {/* System Health Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">System Health</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              {getHealthIcon(systemHealth.overall)}
              <span className="text-2xl font-bold capitalize">{systemHealth.overall}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              All critical systems operational
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Uptime</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{formatUptime(systemStats.uptime)}</div>
            <p className="text-xs text-muted-foreground">
              Since last restart
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">CPU Usage</CardTitle>
            <Cpu className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.cpuUsage}%</div>
            <Progress value={systemStats.cpuUsage} className="mt-2" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Memory Usage</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats.memoryUsage}%</div>
            <Progress value={systemStats.memoryUsage} className="mt-2" />
          </CardContent>
        </Card>
      </div>

      {/* Detailed System Information */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="health">Health Check</TabsTrigger>
          <TabsTrigger value="logs">System Logs</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* System Metrics Chart */}
          <Card>
            <CardHeader>
              <CardTitle>System Performance</CardTitle>
              <CardDescription>
                Real-time system resource utilization
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={systemMetricsData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" />
                  <YAxis />
                  <Tooltip />
                  <Area 
                    type="monotone" 
                    dataKey="cpu" 
                    stackId="1"
                    stroke="#8884d8" 
                    fill="#8884d8"
                    fillOpacity={0.6}
                    name="CPU %"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="memory" 
                    stackId="2"
                    stroke="#82ca9d" 
                    fill="#82ca9d"
                    fillOpacity={0.6}
                    name="Memory %"
                  />
                  <Area 
                    type="monotone" 
                    dataKey="network" 
                    stackId="3"
                    stroke="#ffc658" 
                    fill="#ffc658"
                    fillOpacity={0.6}
                    name="Network MB/s"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Resource Usage Details */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Storage</CardTitle>
                <CardDescription>Disk usage and available space</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">System Disk</span>
                  <span className="text-sm text-muted-foreground">{systemStats.diskUsage}% used</span>
                </div>
                <Progress value={systemStats.diskUsage} />
                
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Total</p>
                    <p className="font-medium">500 GB</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Used</p>
                    <p className="font-medium">160 GB</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Free</p>
                    <p className="font-medium">340 GB</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Network</CardTitle>
                <CardDescription>Network connectivity and performance</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Latency</p>
                    <p className="text-2xl font-bold">{systemStats.networkLatency}ms</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Status</p>
                    <div className="flex items-center space-x-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full" />
                      <span className="text-sm font-medium">Connected</span>
                    </div>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="text-muted-foreground">Upload</p>
                    <p className="font-medium">1.2 MB/s</p>
                  </div>
                  <div>
                    <p className="text-muted-foreground">Download</p>
                    <p className="font-medium">2.8 MB/s</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="health" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Component Health</CardTitle>
              <CardDescription>
                Status of individual system components
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(systemHealth.components).map(([component, status]) => (
                  <div key={component} className="flex items-center justify-between p-4 border border-border rounded-lg">
                    <div className="flex items-center space-x-3">
                      {getHealthIcon(status)}
                      <div>
                        <p className="font-medium capitalize">{component.replace('_', ' ')}</p>
                        <p className="text-sm text-muted-foreground">
                          {status === 'healthy' ? 'Operating normally' : 
                           status === 'degraded' ? 'Performance degraded' : 'Service unavailable'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant={status === 'healthy' ? 'default' : 'destructive'}>
                        {status}
                      </Badge>
                      <Button variant="outline" size="sm" onClick={() => handleRestart(component)}>
                        <RefreshCw className="w-4 h-4" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>System Logs</CardTitle>
              <CardDescription>
                Recent system events and messages
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {logEntries.map((entry, index) => (
                  <div key={index} className={`p-3 rounded-lg ${getLevelColor(entry.level)}`}>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Badge variant="outline" className="text-xs">
                          {entry.level}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          {entry.component}
                        </span>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {entry.timestamp.toLocaleTimeString()}
                      </span>
                    </div>
                    <p className="text-sm mt-1">{entry.message}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="config" className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>System Configuration</CardTitle>
              <CardDescription>
                Current system settings and version information
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-4">
                  <h4 className="font-medium">Version Information</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">SyncStream Version</span>
                      <span className="font-medium">1.0.0</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Build</span>
                      <span className="font-medium">dev-2024</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">API Version</span>
                      <span className="font-medium">v1</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-medium">Network Configuration</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">API Host</span>
                      <span className="font-medium">0.0.0.0:8080</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">MQTT Broker</span>
                      <span className="font-medium">localhost:1883</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">WebSocket</span>
                      <span className="font-medium">Enabled</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-medium">Audio Configuration</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Sample Rate</span>
                      <span className="font-medium">44.1 kHz</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Channels</span>
                      <span className="font-medium">Stereo</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Buffer Size</span>
                      <span className="font-medium">10 seconds</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="font-medium">Sync Configuration</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Measurement Interval</span>
                      <span className="font-medium">5 seconds</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Correlation Threshold</span>
                      <span className="font-medium">0.7</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Max Drift</span>
                      <span className="font-medium">1000ms</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

