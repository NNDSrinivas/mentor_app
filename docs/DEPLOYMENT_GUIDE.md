# Deployment Guide

## Platform Requirements for System Audio Capture

The meeting capture utilities rely on `ffmpeg` and platform specific audio backends.
Ensure the following requirements are met on the target system:

### macOS
- macOS 13 or later with ScreenCaptureKit support
- `ffmpeg` installed (`brew install ffmpeg`)
- Screen Recording permission granted to the application

### Windows
- Windows 10 or later
- `ffmpeg` installed and available on `PATH`
- WASAPI loopback capture is used; no additional drivers are required

### Linux
- A PulseAudio or PipeWire based system
- `ffmpeg` installed and available on `PATH`
- The user must have permission to access the audio server

These dependencies are only required when enabling system audio recording via
`capture_meeting(record_system_audio=True)`.
