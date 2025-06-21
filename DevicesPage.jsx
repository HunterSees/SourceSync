import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { 
  Speakers, 
  Radio, 
  Volume2, 
  Wifi, 
  WifiOff,
  Play,
  Pause,
  VolumeX,
  Settings,
  RotateCcw,
  Trash2,
  Plus,
  Search,
  Filter
} from 'lucide-react'

const mockDevices = [
  {
    id: 'living_room',
    name: 'Living Room Speaker',
    type: 'chromecast',
    location: 'Living Room',
    syncGroup: 'main_floor',
    isOnline: true,
    isPlaying: true,
    isMuted: false,
    volume: 0.8,
    currentOffset: 12.5,
    lastDrift: 8.2,
    avgDrift: 10.1,
    correlation: 0.92,
    ipAddress: '192.168.1.150',
    baseLatency: 300,
    lastSeen: new Date(Date.now() - 30000),
    cpuUsage: 15.2,
    memoryUsage: 45.8,
    temperature: 42.1
  },
  {
    id: 'kitchen',
    name: 'Kitchen Display',
    type: 'chromecast',
    location: 'Kitchen',
    syncGroup: 'main_floor',
    isOnline: true,
    isPlaying: true,
    isMuted: false,
    volume: 0.6,
    currentOffset: 15.1,
    lastDrift: 15.1,
    avgDrift: 12.8,
    correlation: 0.87,
    ipAddress: '192.168.1.151',
    baseLatency: 280,
    lastSeen: new Date(Date.now() - 45000),
    cpuUsage: 12.8,
    memoryUsage: 38.2,
    temperature: 39.5
  },
  {
    id: 'bedroom',
    name: 'Bedroom Echo',
    type: 'bluetooth',
    location: 'Bedroom',
    syncGroup: 'upstairs',
    isOnline: true,
    isPlaying: false,
    isMuted: true,
    volume: 0.4,
    currentOffset: 6.8,
    lastDrift: 6.8,
    avgDrift: 8.5,
    correlation: 0.95,
    ipAddress: '192.168.1.152',
    baseLatency: 150,
    lastSeen: new Date(Date.now() - 60000),
    cpuUsage: 8.1,
    memoryUsage: 28.5,
    temperature: 35.2
  },
  {
    id: 'office',
    name: 'Office Speakers',
    type: 'airplay',
    location: 'Office',
    syncGroup: 'upstairs',
    isOnline: false,
    isPlaying: false,
    isMuted: false,
    volume: 0.7,
    currentOffset: 0,
    lastDrift: null,
    avgDrift: null,
    correlation: null,
    ipAddress: '192.168.1.153',
    baseLatency: 200,
    lastSeen: new Date(Date.now() - 300000),
    cpuUsage: 0,
    memoryUsage: 0,
    temperature: 0
  }
]

export function DevicesPage() {
  const [devices, setDevices] = useState(mockDevices)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterGroup, setFilterGroup] = useState('all')
  const [filterStatus, setFilterStatus] = useState('all')
  const [selectedDevice, setSelectedDevice] = useState(null)

  const getDeviceIcon = (type) => {
    switch (type) {
      case 'chromecast': return <Speakers className="w-5 h-5" />
      case 'airplay': return <Volume2 className="w-5 h-5" />
      case 'bluetooth': return <Radio className="w-5 h-5" />
      default: return <Speakers className="w-5 h-5" />
    }
  }

  const getStatusBadge = (device) => {
    if (!device.isOnline) {
      return (
        <Badge variant="secondary">
          <WifiOff className="w-3 h-3 mr-1" />
          Offline
        </Badge>
      )
    }
    
    if (device.isPlaying) {
      return (
        <Badge variant="default" className="bg-green-500">
          <Play className="w-3 h-3 mr-1" />
          Playing
        </Badge>
      )
    }
    
    return (
      <Badge variant="outline">
        <Pause className="w-3 h-3 mr-1" />
        Paused
      </Badge>
    )
  }

  const filteredDevices = devices.filter(device => {
    const matchesSearch = device.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         device.location.toLowerCase().includes(searchTerm.toLowerCase())
    const matchesGroup = filterGroup === 'all' || device.syncGroup === filterGroup
    const matchesStatus = filterStatus === 'all' || 
                         (filterStatus === 'online' && device.isOnline) ||
                         (filterStatus === 'offline' && !device.isOnline) ||
                         (filterStatus === 'playing' && device.isPlaying)
    
    return matchesSearch && matchesGroup && matchesStatus
  })

  const syncGroups = [...new Set(devices.map(d => d.syncGroup))]

  const handleDeviceAction = (deviceId, action, value = null) => {
    setDevices(prev => prev.map(device => {
      if (device.id === deviceId) {
        switch (action) {
          case 'mute':
            return { ...device, isMuted: !device.isMuted }
          case 'volume':
            return { ...device, volume: value }
          case 'resync':
            return { ...device, currentOffset: 0, lastDrift: 0 }
          default:
            return device
        }
      }
      return device
    }))
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Devices</h1>
          <p className="text-muted-foreground">Manage your SyncStream audio devices</p>
        </div>
        <Button>
          <Plus className="w-4 h-4 mr-2" />
          Add Device
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Label htmlFor="search">Search Devices</Label>
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  id="search"
                  placeholder="Search by name or location..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
            
            <div className="w-full md:w-48">
              <Label>Sync Group</Label>
              <Select value={filterGroup} onValueChange={setFilterGroup}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Groups</SelectItem>
                  {syncGroups.map(group => (
                    <SelectItem key={group} value={group}>{group}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="w-full md:w-48">
              <Label>Status</Label>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="online">Online</SelectItem>
                  <SelectItem value="offline">Offline</SelectItem>
                  <SelectItem value="playing">Playing</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Device Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredDevices.map((device) => (
          <Card key={device.id} className="relative">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    {getDeviceIcon(device.type)}
                  </div>
                  <div>
                    <CardTitle className="text-lg">{device.name}</CardTitle>
                    <CardDescription>{device.location}</CardDescription>
                  </div>
                </div>
                {getStatusBadge(device)}
              </div>
            </CardHeader>
            
            <CardContent className="space-y-4">
              {/* Device Info */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Type</p>
                  <p className="font-medium capitalize">{device.type}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Group</p>
                  <p className="font-medium">{device.syncGroup}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Drift</p>
                  <p className="font-medium">
                    {device.lastDrift ? `${device.lastDrift.toFixed(1)}ms` : 'N/A'}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Correlation</p>
                  <p className="font-medium">
                    {device.correlation ? `${(device.correlation * 100).toFixed(0)}%` : 'N/A'}
                  </p>
                </div>
              </div>

              {/* Volume Control */}
              {device.isOnline && (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label className="text-sm">Volume</Label>
                    <span className="text-sm text-muted-foreground">
                      {Math.round(device.volume * 100)}%
                    </span>
                  </div>
                  <Slider
                    value={[device.volume * 100]}
                    onValueChange={(value) => handleDeviceAction(device.id, 'volume', value[0] / 100)}
                    max={100}
                    step={1}
                    className="w-full"
                  />
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex space-x-2">
                {device.isOnline && (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeviceAction(device.id, 'mute')}
                    >
                      {device.isMuted ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeviceAction(device.id, 'resync')}
                    >
                      <RotateCcw className="w-4 h-4" />
                    </Button>
                  </>
                )}
                
                <Dialog>
                  <DialogTrigger asChild>
                    <Button variant="outline" size="sm" onClick={() => setSelectedDevice(device)}>
                      <Settings className="w-4 h-4" />
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl">
                    <DialogHeader>
                      <DialogTitle>{device.name} Settings</DialogTitle>
                      <DialogDescription>
                        Configure device settings and view detailed information
                      </DialogDescription>
                    </DialogHeader>
                    
                    {selectedDevice && (
                      <div className="space-y-6">
                        {/* Basic Settings */}
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label>Device Name</Label>
                            <Input value={selectedDevice.name} />
                          </div>
                          <div>
                            <Label>Location</Label>
                            <Input value={selectedDevice.location} />
                          </div>
                          <div>
                            <Label>Sync Group</Label>
                            <Select value={selectedDevice.syncGroup}>
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                {syncGroups.map(group => (
                                  <SelectItem key={group} value={group}>{group}</SelectItem>
                                ))}
                              </SelectContent>
                            </Select>
                          </div>
                          <div>
                            <Label>Base Latency (ms)</Label>
                            <Input type="number" value={selectedDevice.baseLatency} />
                          </div>
                        </div>

                        {/* Advanced Settings */}
                        <div className="space-y-4">
                          <h4 className="font-medium">Advanced Settings</h4>
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <Label>IP Address</Label>
                              <Input value={selectedDevice.ipAddress} />
                            </div>
                            <div>
                              <Label>Current Offset (ms)</Label>
                              <Input type="number" value={selectedDevice.currentOffset} />
                            </div>
                          </div>
                        </div>

                        {/* System Info */}
                        {selectedDevice.isOnline && (
                          <div className="space-y-4">
                            <h4 className="font-medium">System Information</h4>
                            <div className="grid grid-cols-3 gap-4 text-sm">
                              <div>
                                <p className="text-muted-foreground">CPU Usage</p>
                                <p className="font-medium">{selectedDevice.cpuUsage}%</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground">Memory Usage</p>
                                <p className="font-medium">{selectedDevice.memoryUsage}%</p>
                              </div>
                              <div>
                                <p className="text-muted-foreground">Temperature</p>
                                <p className="font-medium">{selectedDevice.temperature}°C</p>
                              </div>
                            </div>
                          </div>
                        )}

                        <div className="flex justify-between">
                          <Button variant="destructive">
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove Device
                          </Button>
                          <Button>Save Changes</Button>
                        </div>
                      </div>
                    )}
                  </DialogContent>
                </Dialog>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {filteredDevices.length === 0 && (
        <Card>
          <CardContent className="text-center py-12">
            <Speakers className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-medium mb-2">No devices found</h3>
            <p className="text-muted-foreground mb-4">
              No devices match your current filters. Try adjusting your search criteria.
            </p>
            <Button variant="outline" onClick={() => {
              setSearchTerm('')
              setFilterGroup('all')
              setFilterStatus('all')
            }}>
              Clear Filters
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

