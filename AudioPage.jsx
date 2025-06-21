import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { 
  Play, 
  Pause, 
  Square,
  Volume2, 
  VolumeX,
  Mic,
  MicOff,
  Radio,
  Headphones,
  Speaker,
  Upload,
  Download,
  Settings,
  Zap
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts'

// Mock data
const audioLevelsData = [
  { time: '10:00', input: 65, output: 70 },
  { time: '10:01', input: 68, output: 72 },
  { time: '10:02', input: 62, output: 68 },
  { time: '10:03', input: 70, output: 75 },
  { time: '10:04', input: 66, output: 71 },
  { time: '10:05', input: 64, output: 69 },
]

const deviceVolumeData = [
  { device: 'Living Room', volume: 80 },
  { device: 'Kitchen', volume: 60 },
  { device: 'Bedroom', volume: 40 },
  { device: 'Office', volume: 0 },
]

const audioSources = [
  { id: 'microphone', name: 'System Microphone', type: 'microphone', available: true },
  { id: 'line_in', name: 'Line Input', type: 'line', available: true },
  { id: 'file_test', name: 'Test Audio File', type: 'file', available: true },
  { id: 'stream_url', name: 'Network Stream', type: 'stream', available: false },
]

export function AudioPage() {
  const [isStreaming, setIsStreaming] = useState(false)
  const [globalVolume, setGlobalVolume] = useState(75)
  const [globalMute, setGlobalMute] = useState(false)
  const [selectedSource, setSelectedSource] = useState('microphone')
  const [bufferSize, setBufferSize] = useState(10)
  const [sampleRate, setSampleRate] = useState(44100)
  const [channels, setChannels] = useState(2)

  const handleStreamToggle = () => {
    setIsStreaming(!isStreaming)
  }

  const handleGlobalVolumeChange = (value) => {
    setGlobalVolume(value[0])
  }

  const handleGlobalMute = () => {
    setGlobalMute(!globalMute)
  }

  const handleTestTone = () => {
    // Mock test tone generation
    console.log('Test tone generated')
  }

  const handleLatencyTest = () => {
    // Mock latency test
    console.log('Latency test started')
  }

  const getSourceIcon = (type) => {
    switch (type) {
      case 'microphone': return <Mic className="w-4 h-4" />
      case 'line': return <Radio className="w-4 h-4" />
      case 'file': return <Upload className="w-4 h-4" />
      case 'stream': return <Download className="w-4 h-4" />
      default: return <Speaker className="w-4 h-4" />
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Audio Control</h1>
          <p className="text-muted-foreground">Manage audio streaming and device settings</p>
        </div>
        <div className="flex space-x-2">
          <Button variant="outline" onClick={handleLatencyTest}>
            <Zap className="w-4 h-4 mr-2" />
            Test Latency
          </Button>
          <Button 
            onClick={handleStreamToggle}
            variant={isStreaming ? "destructive" : "default"}
          >
            {isStreaming ? (
              <>
                <Square className="w-4 h-4 mr-2" />
                Stop Stream
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Start Stream
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Stream Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center space-x-2">
            <Radio className="w-5 h-5" />
            <span>Stream Status</span>
            <Badge variant={isStreaming ? "default" : "secondary"}>
              {isStreaming ? "Live" : "Stopped"}
            </Badge>
          </CardTitle>
          <CardDescription>
            Current audio streaming configuration and status
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold">{sampleRate / 1000}kHz</p>
              <p className="text-sm text-muted-foreground">Sample Rate</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{channels}</p>
              <p className="text-sm text-muted-foreground">Channels</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{bufferSize}s</p>
              <p className="text-sm text-muted-foreground">Buffer Size</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">{isStreaming ? '1411' : '0'}</p>
              <p className="text-sm text-muted-foreground">Bitrate (kbps)</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Audio Source and Global Controls */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Audio Source */}
        <Card>
          <CardHeader>
            <CardTitle>Audio Source</CardTitle>
            <CardDescription>
              Select and configure the audio input source
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Input Source</Label>
              <Select value={selectedSource} onValueChange={setSelectedSource}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {audioSources.map((source) => (
                    <SelectItem 
                      key={source.id} 
                      value={source.id}
                      disabled={!source.available}
                    >
                      <div className="flex items-center space-x-2">
                        {getSourceIcon(source.type)}
                        <span>{source.name}</span>
                        {!source.available && (
                          <Badge variant="secondary" className="ml-2">Unavailable</Badge>
                        )}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedSource === 'stream_url' && (
              <div className="space-y-2">
                <Label>Stream URL</Label>
                <Input placeholder="http://example.com/stream" />
              </div>
            )}

            {selectedSource === 'file_test' && (
              <div className="space-y-2">
                <Label>Test File</Label>
                <Select defaultValue="sine_wave">
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sine_wave">1kHz Sine Wave</SelectItem>
                    <SelectItem value="white_noise">White Noise</SelectItem>
                    <SelectItem value="music_sample">Music Sample</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <Button onClick={handleTestTone} className="w-full">
              <Headphones className="w-4 h-4 mr-2" />
              Generate Test Tone
            </Button>
          </CardContent>
        </Card>

        {/* Global Audio Controls */}
        <Card>
          <CardHeader>
            <CardTitle>Global Controls</CardTitle>
            <CardDescription>
              Control volume and settings for all devices
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Global Volume */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Master Volume</Label>
                <span className="text-sm text-muted-foreground">{globalVolume}%</span>
              </div>
              <div className="flex items-center space-x-4">
                <Button
                  variant="outline"
                  size="icon"
                  onClick={handleGlobalMute}
                >
                  {globalMute ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                </Button>
                <Slider
                  value={[globalVolume]}
                  onValueChange={handleGlobalVolumeChange}
                  max={100}
                  step={1}
                  className="flex-1"
                  disabled={globalMute}
                />
              </div>
            </div>

            {/* Audio Settings */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Sample Rate</Label>
                <Select value={sampleRate.toString()} onValueChange={(value) => setSampleRate(parseInt(value))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="44100">44.1 kHz</SelectItem>
                    <SelectItem value="48000">48 kHz</SelectItem>
                    <SelectItem value="96000">96 kHz</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Channels</Label>
                <Select value={channels.toString()} onValueChange={(value) => setChannels(parseInt(value))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="1">Mono</SelectItem>
                    <SelectItem value="2">Stereo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Buffer Size */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Buffer Size</Label>
                <span className="text-sm text-muted-foreground">{bufferSize}s</span>
              </div>
              <Slider
                value={[bufferSize]}
                onValueChange={(value) => setBufferSize(value[0])}
                min={1}
                max={30}
                step={1}
                className="w-full"
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Audio Monitoring */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Audio Levels */}
        <Card>
          <CardHeader>
            <CardTitle>Audio Levels</CardTitle>
            <CardDescription>
              Real-time input and output audio level monitoring
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={audioLevelsData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="input" 
                  stroke="#8884d8" 
                  strokeWidth={2}
                  name="Input Level"
                />
                <Line 
                  type="monotone" 
                  dataKey="output" 
                  stroke="#82ca9d" 
                  strokeWidth={2}
                  name="Output Level"
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Device Volumes */}
        <Card>
          <CardHeader>
            <CardTitle>Device Volumes</CardTitle>
            <CardDescription>
              Current volume levels for each connected device
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={deviceVolumeData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" domain={[0, 100]} />
                <YAxis dataKey="device" type="category" width={80} />
                <Tooltip />
                <Bar dataKey="volume" fill="hsl(var(--primary))" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Audio Buffer Info */}
      <Card>
        <CardHeader>
          <CardTitle>Buffer Information</CardTitle>
          <CardDescription>
            Audio buffer status and performance metrics
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="text-center">
              <p className="text-2xl font-bold text-green-600">85%</p>
              <p className="text-sm text-muted-foreground">Buffer Fill</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">2.1ms</p>
              <p className="text-sm text-muted-foreground">Latency</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">0</p>
              <p className="text-sm text-muted-foreground">Underruns</p>
            </div>
            <div className="text-center">
              <p className="text-2xl font-bold">99.8%</p>
              <p className="text-sm text-muted-foreground">Uptime</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Advanced Audio Settings */}
      <Card>
        <CardHeader>
          <CardTitle>Advanced Settings</CardTitle>
          <CardDescription>
            Fine-tune audio processing and quality settings
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="space-y-2">
              <Label>Compression</Label>
              <Select defaultValue="none">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">None</SelectItem>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="heavy">Heavy</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Noise Gate</Label>
              <Select defaultValue="disabled">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="disabled">Disabled</SelectItem>
                  <SelectItem value="light">Light</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="aggressive">Aggressive</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>EQ Preset</Label>
              <Select defaultValue="flat">
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="flat">Flat</SelectItem>
                  <SelectItem value="bass_boost">Bass Boost</SelectItem>
                  <SelectItem value="vocal">Vocal</SelectItem>
                  <SelectItem value="classical">Classical</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex justify-end space-x-2">
            <Button variant="outline">Reset to Defaults</Button>
            <Button>Apply Settings</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

