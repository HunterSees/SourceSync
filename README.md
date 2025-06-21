# SyncStream

## Purpose
Play audio perfectly synchronized across TVs, speakers, and smart devices using Raspberry Pi Zero Ws as intelligent per-device adapters. Each Pi:

* Receives the audio stream
* Plays it in sync with the others
* Monitors real-world audio drift via an onboard mic
* Adapts to whatever output device it’s connected to (speaker, TV, smart assistant)

## System Topology Overview

```
                          +---------------------+
                          |   Transmitter Host  | (PC or Pi 4B)
                          |---------------------|
                          | Audio Server        |
                          | Audio Buffer        |
                          | Drift Sync Engine   |
                          | MQTT Broker         |
                          | WebSocket API       |
                          +---------------------+
                                   ||
                          MQTT / WebSocket / HTTP
                                   ||
            +----------------------+------+------------------+
            |                      |                        |
    +---------------+      +---------------+       +---------------+
    | Pi Receiver A |      | Pi Receiver B |       | Pi Receiver C |
    |---------------|      |---------------|       |---------------|
    | Audio Output  |      | Audio Output  |       | Audio Output  |
    | Mic Drift Corr|      | Mic Drift Corr|       | Mic Drift Corr|
    | Ecosystem Logic|     | Ecosystem Logic|      | Ecosystem Logic|
    +---------------+      +---------------+       +---------------+
            |                      |                        |
       Output to TV A        Output to Speaker B     Cast to Google C
```

## Bill of Materials (per node)

| Item                      | Notes                                    |
|---------------------------|------------------------------------------|
| Raspberry Pi Zero W       | Acts as a per-device receiver node       |
| INMP441 or SPH0645 mic    | I²S digital mic for drift sensing        |
| Audio output method       | 3.5mm, USB DAC, HDMI, AirPlay, etc       |
| MicroSD card              | Minimum 8GB, Pi OS Lite                  |
| Power supply              | 5V USB                                   |
| Optional: speakers, amp   | Whatever your output device is           |

## Full Project Directory Structure

```
/syncstream
├── transmitter/              # Runs on the "master" node (PC or Pi 4B)
│   ├── audio_server.py       # Streams audio
│   ├── audio_buffer.py       # Rolling memory buffer for sync
│   ├── sync_controller.py    # Drift correction + buffer offset manager
│   ├── mqtt_server.py        # MQTT broker + message dispatch
│   └── config.yaml           # Device profiles, offsets, roles
│
├── receiver/                 # Runs on each Pi Zero W
│   ├── mic_capture.py        # Samples mic input (I²S)
│   ├── drift_detector.py     # Measures drift vs. source buffer
│   ├── mqtt_client.py        # Sends drift reports / gets buffer offsets
│   ├── audio_output.py       # Outputs audio with buffer delay
│   ├── ecosystem_driver.py   # Talks to AirPlay / Chromecast / HDMI / BT
│   └── config.json           # Local profile (device type, baseline latency)
│
├── ui/
│   ├── frontend/             # React/Svelte UI
│   └── backend.py            # FastAPI/WS to MQTT bridge
│
├── shared/
│   ├── utils.py              # Signal processing, audio I/O
│   ├── logger.py             # Unified logging
│   └── protocol.py           # MQTT topic format, message schemas
│
└── README.md
```

## Assembly Instructions

### STEP 1: Setup the Transmitter Host

A. Install required software:

```bash
sudo apt update
sudo apt install snapserver mosquitto python3-fastapi ffmpeg
```

B. Enable Snapserver or build custom audio stream

* Can stream via:
    * snapserver
    * HTTP PCM stream
    * Pipe ffmpeg or sox into audio_buffer.py

C. Implement:

* `audio_buffer.py`: stores the last N seconds of audio in RAM
* `sync_controller.py`: receives drift reports, sends buffer offsets back
* `mqtt_server.py`: standard MQTT broker + custom topic dispatcher
* `config.yaml`: maps device names → roles, offset profiles, capabilities

### STEP 2: Configure a Pi Receiver Node (per device)

A. Flash Raspberry Pi OS Lite

* Enable SSH and Wi-Fi

B. Enable I²S

In `/boot/config.txt`:

```
dtparam=i2s=on
dtoverlay=i2s-mmap
```

C. Wire up INMP441 or SPH0645

| Mic Pin | Pi GPIO |
|---------|---------|
| VDD     | 3.3V (Pin 1) |
| GND     | GND (Pin 6) |
| WS      | GPIO19  |
| CLK     | GPIO18  |
| SD      | GPIO20  |

### STEP 3: Mic Capture + Drift Detection

A. `mic_capture.py`

* Captures ~2s of I²S input at 44.1kHz
* Buffers sample to disk or memory

B. `drift_detector.py`

* Fetches last 2s of source audio from transmitter via HTTP or socket
* Runs `scipy.signal.correlate()` to compute offset
* Sends `{"device": "livingroom", "drift_ms": +23}` to MQTT

### STEP 4: MQTT Sync Protocol

MQTT Topics:

* `syncstream/drift/<device>` → publish drift
* `syncstream/buffer_offset/<device>` → transmit buffer offset
* `syncstream/config` → initial device profile push
* `syncstream/command/<device>` → stop/start/test tone/etc.

Messages are JSON. e.g.

```json
{
  "drift_ms": 42,
  "signal_strength": -54,
  "latency_adjustment_ms": -12
}
```

### STEP 5: Audio Output & Ecosystem Adaptation

A. `audio_output.py`

* Plays audio from stream URL
* Applies buffer delay using SoX, ffmpeg, or native Snapclient config

B. `ecosystem_driver.py`

Based on `config.json`:

```json
{
  "type": "chromecast",
  "target": "NestAudio-LR",
  "base_latency_ms": 300
}
```

Routes audio as follows:

| Type       | Tool / Method                       |
|------------|-------------------------------------|
| analog     | Play via USB DAC or 3.5mm jack      |
| hdmi       | aplay or ffmpeg to HDMI             |
| airplay    | Use shairport-sync                  |
| chromecast | Use mkchromecast or pychromecast    |
| alexa      | Bluetooth pair + pulseaudio         |

### STEP 6: Control UI & API

A. `backend.py` (FastAPI)

* `/devices`: list all nodes
* `/sync`: get/set drift values
* `/grouping`: assign zones
* `/manual-adjust`: tweak per-device delay

B. `frontend/`

* Dashboard: cards for each node
* Show:
    * Drift (ms)
    * Buffer delay (ms)
    * Device type
    * Link status
* Controls:
    * Resync
    * Mute
    * Group assign
    * Manual offset knob

### STEP 7: Advanced Features (Optional)

| Feature           | Implementation Plan                               |
|-------------------|---------------------------------------------------|
| Auto-calibration  | Record historical drift, average offset           |
| Zone-based playback | Use Snapcast groups or stream selection         |
| Real-time heatmap | Track jitter + sync stability per device        |
| OTA updates       | Use MQTT to push Git pulls + restart daemons    |
| Voice diagnostics | Each Pi speaks “I am online, drift is +14ms”    |
| One-click Pi setup| Pre-built SD card image with all logic onboard  |

## Final Result

A fully local, mic-feedback-synced, per-device Pi audio routing system that:

* Plays to anything: speakers, TVs, smart devices
* Tracks real-world drift using mics
* Self-adjusts buffer delay per node
* Exposes full dashboard for control
* Operates without cloud, offline and secure
* Scales linearly with devices, thanks to clean MQTT core


# SourceSync
