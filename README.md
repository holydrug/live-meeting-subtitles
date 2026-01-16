


https://github.com/user-attachments/assets/f74c706b-0963-4978-afc6-3137943b2e62




# Live Meeting Subtitles

Real-time voice transcription and translation for video calls (Zoom, Google Meet, Teams, etc.)

Captures system audio, transcribes speech using Whisper, and displays translated subtitles in an overlay window.

## Architecture

```
┌──────────────────────┐     WebSocket      ┌────────────────────────────┐
│   Windows Client     │  ───────────────►  │      WSL Server            │
│                      │                    │                            │
│  • WASAPI capture    │    audio bytes     │  • Whisper large-v3 (CUDA) │
│  • PyQt6 overlay     │  ◄───────────────  │  • Google/DeepL translate  │
│                      │    JSON results    │                            │
└──────────────────────┘                    └────────────────────────────┘
```

**Why hybrid?**
- WSL has native CUDA support for fast GPU inference
- Windows has native WASAPI for system audio capture
- WebSocket connects them seamlessly

## Requirements

### Hardware
- NVIDIA GPU with CUDA support (RTX 20xx or newer recommended)
- 8GB+ VRAM for large-v3 model (4GB+ for smaller models)

### Software
- Windows 11 with WSL2 (Ubuntu 22.04/24.04)
- Python 3.11+ (both Windows and WSL)
- NVIDIA drivers with CUDA support in WSL

## Installation

### 1. Clone the repository

```bash
# In WSL
cd ~/projects
git clone https://github.com/holydrug/live-meeting-subtitles.git
cd live-meeting-subtitles
```

### 2. Setup WSL Server

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r server/requirements.txt

# Verify CUDA is available
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"
```

### 3. Setup Windows Client

Open PowerShell and navigate to the project:

```powershell
# Navigate to project (via WSL path)
cd \\wsl.localhost\Ubuntu\home\YOUR_USERNAME\projects\live-meeting-subtitles

# Create virtual environment
python -m venv venv_win

# Activate
.\venv_win\Scripts\Activate.ps1

# Install dependencies
pip install -r client/requirements.txt
```

## Usage

### Start the server (WSL terminal)

```bash
cd ~/projects/live-meeting-subtitles
source venv/bin/activate
python -m server.main --translator google
```

Options:
- `--translator`: `google` (free), `deepl` (API key required), `local` (NLLB), `none`
- `--model`: Whisper model (`tiny`, `base`, `small`, `medium`, `large-v3`)
- `--device`: `cuda` or `cpu`
- `--target-lang`: Target language code (default: `RU`)

### Start the client (PowerShell)

```powershell
cd \\wsl.localhost\Ubuntu\home\YOUR_USERNAME\projects\live-meeting-subtitles
.\venv_win\Scripts\Activate.ps1
python -m client.main
```

Options:
- `--no-overlay`: Console mode without GUI
- `--device "NAME"`: Specific audio device
- `--list-devices`: Show available audio devices

### List audio devices

```powershell
python -m client.main --list-devices
```

## Configuration

Edit `config.yaml` to change default settings:

```yaml
server:
  host: localhost
  port: 9876
  model: large-v3
  device: cuda
  translator: google
  target_language: RU

client:
  overlay: true
  font_size: 18
  opacity: 0.85
```

## Troubleshooting

### "No loopback device found"
Make sure you have audio playing through the selected device. WASAPI loopback requires active audio output.

### CUDA not available in WSL
1. Update NVIDIA drivers on Windows (535+ recommended)
2. Ensure WSL2 is updated: `wsl --update`
3. Check with: `nvidia-smi` in WSL

### Connection refused
1. Check server is running on port 9876
2. Windows Firewall may block WSL connections — add exception

### High latency
- Use smaller model: `--model small` or `--model medium`
- Reduce chunk duration in config
- Ensure GPU is not throttling (check temps)

## Project Structure

```
live-meeting-subtitles/
├── server/                 # WSL (Python + CUDA)
│   ├── main.py            # WebSocket server
│   ├── transcriber.py     # Whisper wrapper
│   └── translators/       # Translation backends
│       ├── google.py      # Google Translate (free)
│       ├── deepl.py       # DeepL API
│       └── local.py       # NLLB local model
│
├── client/                 # Windows (Python)
│   ├── main.py            # WebSocket client + UI
│   ├── audio_capture.py   # WASAPI loopback
│   └── overlay.py         # PyQt6 overlay window
│
├── shared/                 # Common code
│   └── protocol.py        # WebSocket protocol
│
└── config.yaml            # Configuration
```

## License

MIT
