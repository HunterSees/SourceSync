import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Slider } from '@/components/ui/slider'
import { 
  RotateCcw, 
  Radio, 
  Clock, 
  Activity,
  TrendingUp,
  TrendingDown,
  Minus,
  CheckCircle,
  AlertTriangle,
  XCircle
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter } from 'recharts'

// Mock data
const driftHistoryData = [
  { time: '10:00', living_room: 12, kitchen: 8, bedroom: 15, office: null },
  { time: '10:05', living_room: 8, kitchen: 12, bedroom: 6, office: null },
  { time: '10:10', living_room: 15, kitchen: 9, bedroom: 11, office: null },
  { time: '10:15', living_room: 6, kitchen: 14, bedroom: 9, office: null },
  { time: '10:20', living_room: 11, kitchen: 7, bedroom: 13, office: null },
  { time: '10:25', living_room: 9, kitchen: 16, bedroom: 8, office: null },
  { time: '10:30', living_room: 13, kitchen: 5, bedroom: 12, office: null },
]

const correlationData = [
  { device: 'Living Room', drift: 12, correlation: 92 },
  { device: 'Kitchen', drift: 8, correlation: 87 },
  { device: 'Bedroom', drift: 15, correlation: 95 },
  { device: 'Office', drift: 0, correlation: 0 },
]

const syncGroups = {
  main_floor: {
    name: 'Main Floor',
    devices: ['living_room', 'kitchen'],
    avgDrift: 10.0,
    maxDrift: 16.0,
    quality: 'good',
    lastSync: new Date(Date.now() - 120000)
  },
  upstairs: {
    name: 'Upstairs',
    devices: ['bedroom', 'office'],
    avgDrift: 15.0,
    maxDrift: 15.0,
    quality: 'fair',
    lastSync: new Date(Date.now() - 300000)
  }
}

export function SyncPage() {
  const [globalOffset, setGlobalOffset] = useState(0)
  const [autoSync, setAutoSync] = useState(true)
  const [syncThreshold, setSyncThreshold] = useState(50)

  const getSyncQualityColor = (quality) => {
    switch (quality) {
      case 'excellent': return 'text-green-600'
      case 'good': return 'text-blue-600'
      case 'fair': return 'text-yellow-600'
      case 'poor': return 'text-red-600'
      default: return 'text-gray-600'
    }
  }

  const getSyncQualityIcon = (quality) => {
    switch (quality) {
      case 'excellent': return <CheckCircle className="w-4 h-4 text-green-600" />
      case 'good': return <CheckCircle className="w-4 h-4 text-blue-600" />
      case 'fair': return <AlertTriangle className="w-4 h-4 text-yellow-600" />
      case 'poor': return <XCircle className="w-4 h-4 text-red-600" />
      default: return <Minus className="w-4 h-4 text-gray-600" />
    }
  }

  const handleGlobalResync = () => {
    // Mock global resync
    console.log('Global resync triggered')
  }

  const handleGroupResync = (groupId) => {
    // Mock group resync
    console.log(`Group resync triggered for ${groupId}`)
  }

  const handleManualAdjustment = (groupId, adjustment) => {
    // Mock manual adjustment
    console.log(`Manual adjustment for ${groupId}: ${adjustment}ms`)
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Synchronization</h1>
          <p className="text-muted-foreground">Monitor and control audio synchronization across devices</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline">
            <Activity className="w-4 h-4 mr-2" />
            View Logs
          </Button>
          <Button onClick={handleGlobalResync}>
            <RotateCcw className="w-4 h-4 mr-2" />
            Global Resync
          </Button>
        </div>
      </div>

      {/* Sync Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overall Sync Quality</CardTitle>
            <Radio className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex items-center space-x-2">
              {getSyncQualityIcon('good')}
              <span className="text-2xl font-bold">Good</span>
            </div>
            <p className="text-xs text-muted-foreground">
              All groups within acceptable range
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Average Drift</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">12.5ms</div>
            <p className="text-xs text-muted-foreground flex items-center">
              <TrendingDown className="w-3 h-3 mr-1 text-green-600" />
              2.1ms improvement from last hour
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sync Events</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">47</div>
            <p className="text-xs text-muted-foreground">
              In the last hour
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Sync Groups */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {Object.entries(syncGroups).map(([groupId, group]) => (
          <Card key={groupId}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center space-x-2">
                    {getSyncQualityIcon(group.quality)}
                    <span>{group.name}</span>
                  </CardTitle>
                  <CardDescription>
                    {group.devices.length} devices • Last sync {Math.floor((Date.now() - group.lastSync) / 60000)} min ago
                  </CardDescription>
                </div>
                <Badge variant="outline" className={getSyncQualityColor(group.quality)}>
                  {group.quality}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Average Drift</p>
                  <p className="font-medium">{group.avgDrift.toFixed(1)}ms</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Max Drift</p>
                  <p className="font-medium">{group.maxDrift.toFixed(1)}ms</p>
                </div>
              </div>

              {/* Manual Adjustment */}
              <div className="space-y-2">
                <Label className="text-sm">Manual Adjustment</Label>
                <div className="flex items-center space-x-2">
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleManualAdjustment(groupId, -10)}
                  >
                    -10ms
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleManualAdjustment(groupId, -5)}
                  >
                    -5ms
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleManualAdjustment(groupId, 5)}
                  >
                    +5ms
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={() => handleManualAdjustment(groupId, 10)}
                  >
                    +10ms
                  </Button>
                </div>
              </div>

              <div className="flex space-x-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  className="flex-1"
                  onClick={() => handleGroupResync(groupId)}
                >
                  <RotateCcw className="w-4 h-4 mr-2" />
                  Resync Group
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Drift History */}
        <Card>
          <CardHeader>
            <CardTitle>Drift History</CardTitle>
            <CardDescription>
              Real-time drift measurements for each device
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={driftHistoryData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="living_room" 
                  stroke="#8884d8" 
                  strokeWidth={2}
                  name="Living Room"
                />
                <Line 
                  type="monotone" 
                  dataKey="kitchen" 
                  stroke="#82ca9d" 
                  strokeWidth={2}
                  name="Kitchen"
                />
                <Line 
                  type="monotone" 
                  dataKey="bedroom" 
                  stroke="#ffc658" 
                  strokeWidth={2}
                  name="Bedroom"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Correlation vs Drift */}
        <Card>
          <CardHeader>
            <CardTitle>Correlation vs Drift</CardTitle>
            <CardDescription>
              Relationship between drift and correlation quality
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart data={correlationData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="drift" name="Drift (ms)" />
                <YAxis dataKey="correlation" name="Correlation %" />
                <Tooltip 
                  formatter={(value, name) => [
                    name === 'correlation' ? `${value}%` : `${value}ms`,
                    name === 'correlation' ? 'Correlation' : 'Drift'
                  ]}
                  labelFormatter={(label, payload) => payload?.[0]?.payload?.device || ''}
                />
                <Scatter dataKey="correlation" fill="hsl(var(--primary))" />
              </ScatterChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Sync Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Synchronization Settings</CardTitle>
          <CardDescription>
            Configure automatic synchronization behavior
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Global Offset */}
            <div className="space-y-2">
              <Label>Global Offset Adjustment</Label>
              <div className="flex items-center space-x-4">
                <Slider
                  value={[globalOffset]}
                  onValueChange={(value) => setGlobalOffset(value[0])}
                  min={-100}
                  max={100}
                  step={1}
                  className="flex-1"
                />
                <span className="text-sm font-medium w-16 text-right">
                  {globalOffset > 0 ? '+' : ''}{globalOffset}ms
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Apply offset to all devices simultaneously
              </p>
            </div>

            {/* Sync Threshold */}
            <div className="space-y-2">
              <Label>Auto-Sync Threshold</Label>
              <div className="flex items-center space-x-4">
                <Slider
                  value={[syncThreshold]}
                  onValueChange={(value) => setSyncThreshold(value[0])}
                  min={10}
                  max={200}
                  step={5}
                  className="flex-1"
                />
                <span className="text-sm font-medium w-16 text-right">
                  {syncThreshold}ms
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                Trigger automatic resync when drift exceeds this threshold
              </p>
            </div>
          </div>

          {/* Advanced Settings */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label>Measurement Interval</Label>
              <Input type="number" defaultValue="5" />
              <p className="text-xs text-muted-foreground">Seconds between measurements</p>
            </div>
            
            <div className="space-y-2">
              <Label>Correlation Threshold</Label>
              <Input type="number" defaultValue="0.7" step="0.1" />
              <p className="text-xs text-muted-foreground">Minimum correlation for valid measurement</p>
            </div>
            
            <div className="space-y-2">
              <Label>Max Drift</Label>
              <Input type="number" defaultValue="1000" />
              <p className="text-xs text-muted-foreground">Maximum allowed drift (ms)</p>
            </div>
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="outline">Reset to Defaults</Button>
            <Button>Save Settings</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

