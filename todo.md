
## Todo List

### Phase 1: Project setup and documentation
- [x] Create project directory structure
- [x] Create README.md with project overview
- [x] Create todo.md

### Phase 2: Transmitter host implementation
- [x] Install required software (snapserver, mosquitto, python3-fastapi, ffmpeg)
- [x] Implement audio_buffer.py
- [x] Implement sync_controller.py
- [x] Implement mqtt_server.py
- [x] Implement audio_server.py
- [x] Create config.yaml

### Phase 3: Receiver node implementation
- [x] Document flashing Raspberry Pi OS Lite, enabling SSH and Wi-Fi
- [x] Document enabling I²S in /boot/config.txt
- [x] Document wiring up INMP441 or SPH0645
- [x] Implement mic_capture.py
- [x] Implement drift_detector.py
- [x] Implement mqtt_client.py
- [x] Implement audio_output.py
- [x] Implement ecosystem_driver.py
- [x] Create config.json

### Phase 4: MQTT sync protocol and shared utilities
- [x] Implement shared/utils.py
- [x] Implement shared/logger.py
- [x] Implement shared/protocol.py

### Phase 5: Control UI and API development
- [x] Implement ui/backend.py (Flask API)
- [x] Implement ui/frontend/ (React dashboard)

### Phase 6: Testing and documentation finalization
- [x] Test transmitter host
- [x] Test receiver nodes
- [x] Create comprehensive documentation
- [x] Test UI components
- [ ] Test MQTT communication
- [ ] Test UI and API
- [ ] Finalize documentation

### Phase 7: Deliver complete SyncStream system to user
- [ ] Package and deliver the system to the user


