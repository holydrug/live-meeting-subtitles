# Voice Analyzer — AI Agent Documentation

## Промт для нового чата

```
Я продолжаю работу над проектом voice-analyzer — приложение для live транскрипции и перевода речи собеседника во время видеозвонков (Zoom, Google Meet).

Проект находится: ~/projects/voice-analyzer (WSL Ubuntu)

Архитектура: гибридная (Windows + WSL)
- Server (WSL): Whisper транскрипция на CUDA + перевод
- Client (Windows): WASAPI захват аудио + PyQt overlay

Текущий статус: базовая структура создана, нужно протестировать и доработать.

Прочитай CLAUDE.md для полного контекста.
```

---

## Архитектура проекта

```
┌──────────────────┐     WebSocket      ┌──────────────────────────┐
│  Windows Client  │  ───────────────→  │  WSL Server              │
│                  │                    │                          │
│  • WASAPI захват │     audio bytes    │  • Whisper large-v3      │
│  • PyQt Overlay  │  ←───────────────  │  • Google/DeepL/Local    │
│                  │     JSON result    │    перевод               │
└──────────────────┘                    └──────────────────────────┘
     Port: любой                              Port: 9876
```

## Структура файлов

```
~/projects/voice-analyzer/
├── server/                    # WSL (Python + CUDA)
│   ├── main.py               # WebSocket сервер
│   ├── transcriber.py        # faster-whisper wrapper
│   ├── translators/          # Переводчики
│   │   ├── base.py          # Интерфейс
│   │   ├── deepl.py         # DeepL API
│   │   ├── google.py        # Google Translate (free)
│   │   └── local.py         # NLLB локальная модель
│   └── requirements.txt
│
├── client/                    # Windows (Python)
│   ├── main.py               # WebSocket клиент + UI
│   ├── audio_capture.py      # WASAPI loopback
│   ├── overlay.py            # PyQt6 overlay window
│   └── requirements.txt
│
├── shared/                    # Общий код
│   └── protocol.py           # WebSocket протокол
│
├── config.yaml               # Конфигурация
├── run_server.sh             # Запуск сервера (WSL)
├── run_client.ps1            # Запуск клиента (Windows)
└── CLAUDE.md                 # Этот файл
```

## Технологии

| Компонент | Технология | Где |
|-----------|------------|-----|
| Транскрипция | faster-whisper large-v3 | WSL + CUDA |
| Перевод | Google Translate / DeepL / NLLB | WSL |
| Аудио захват | soundcard (WASAPI loopback) | Windows |
| UI | PyQt6 overlay | Windows |
| Коммуникация | WebSocket (websockets) | Оба |

## Железо пользователя

- GPU: RTX 5090
- RAM: 32GB DDR5
- OS: Windows 11 + WSL2 Ubuntu 24.04

## Запуск

**Терминал 1 (WSL):**
```bash
cd ~/projects/voice-analyzer
source venv/bin/activate
./run_server.sh
```

**Терминал 2 (PowerShell):**
```powershell
cd \\wsl.localhost\Ubuntu\home\amogusik\projects\voice-analyzer
.\venv_win\Scripts\Activate.ps1
.\run_client.ps1
```

## TODO / Известные проблемы

1. [ ] Установить Python на Windows и создать venv_win
2. [ ] Протестировать WebSocket соединение между Windows и WSL
3. [ ] Проверить захват аудио через WASAPI
4. [ ] Добавить обработку ошибок и reconnect
5. [ ] Добавить горячие клавиши (start/stop/clear)
6. [ ] Сохранение транскрипции в файл
7. [ ] Настройки через UI (выбор переводчика, языка)

## Команды разработки

```bash
# WSL — установка зависимостей сервера
cd ~/projects/voice-analyzer
source venv/bin/activate
pip install -r server/requirements.txt

# Windows — установка зависимостей клиента
cd \\wsl.localhost\Ubuntu\home\amogusik\projects\voice-analyzer
python -m venv venv_win
.\venv_win\Scripts\Activate.ps1
pip install -r client/requirements.txt

# Тест сервера (WSL)
python -m server.main --help

# Тест клиента (Windows)
python -m client.main --list-devices
```

## Протокол обмена (WebSocket)

**Client → Server:**
- Binary frame: raw audio (int16, mono, 16kHz)
- JSON: `{"type": "set_config", "translation_provider": "google"}`

**Server → Client:**
- JSON: `{"type": "result", "original": "Hello", "translated": "Привет", "language": "en"}`
- JSON: `{"type": "status", "status": "ready"}`
- JSON: `{"type": "error", "message": "..."}`

## Переключение переводчика

Через CLI:
```bash
./run_server.sh --translator google   # или deepl, local, none
```

Или в runtime через WebSocket:
```json
{"type": "set_config", "translation_provider": "deepl"}
```

## Полезные ссылки

- faster-whisper: https://github.com/SYSTRAN/faster-whisper
- soundcard: https://github.com/bastibe/SoundCard
- PyQt6: https://doc.qt.io/qtforpython-6/
