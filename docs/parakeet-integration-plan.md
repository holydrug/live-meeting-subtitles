# План интеграции Parakeet TDT v3

> Дата: 2026-01-20
> Статус: **Фазы 1-3 завершены** (готово к тестированию)

## Цель

Заменить/дополнить Whisper Large-v3 на NVIDIA Parakeet TDT v3 для ускорения транскрипции в ~2x при сохранении качества.

---

## Результаты бенчмарка (RTX 5090, 2026-01-20)

| Model | Time (10s audio) | RTFx | VRAM |
|-------|------------------|------|------|
| **Parakeet TDT v3** | **0.075s** | **132.7x** | 4.71 GB |
| Whisper Large-v3 | 0.156s | 64.3x | 2.39 GB |

**Parakeet в 2.1x быстрее!**

### Важные замечания

1. **PyTorch nightly с CUDA 12.8** — требуется для RTX 5090 (Blackwell sm_120)
2. **CUDA graphs отключены** — временный workaround из-за несовместимости с PyTorch nightly
3. **Обе модели укладываются в 32GB VRAM**

---

## Сравнение моделей

| Параметр | Whisper Large-v3 | Parakeet TDT v3 |
|----------|------------------|-----------------|
| Размер | ~1.5B параметров | 600M параметров |
| Скорость (RTFx) | 64x (на RTX 5090) | **133x** (на RTX 5090) |
| VRAM | 2.4 GB | 4.7 GB |
| WER | ~10% | **~6%** |
| Языки | 100+ | 25 европейских |
| Автопунктуация | Нет | **Да** |
| Библиотека | faster-whisper | NeMo toolkit |
| Лицензия | MIT | CC-BY-4.0 |

**Вывод:** Для нашего кейса (EN/RU) Parakeet подходит и в 2x быстрее.

---

## План реализации

### Фаза 1: Подготовка окружения ✅ ЗАВЕРШЕНА

- [x] Проверить совместимость NeMo с RTX 5090 (Blackwell)
  - Требуется PyTorch nightly с CUDA 12.8: `pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu128`
- [x] Установить NeMo toolkit в WSL venv
  ```bash
  pip install nemo_toolkit[asr]
  ```
- [x] Скачать и протестировать модель локально
  ```python
  import nemo.collections.asr as nemo_asr
  from omegaconf import open_dict

  model = nemo_asr.models.ASRModel.from_pretrained("nvidia/parakeet-tdt-0.6b-v3")

  # ВАЖНО: отключить CUDA graphs (workaround для PyTorch nightly)
  decoding_cfg = model.cfg.decoding.copy()
  with open_dict(decoding_cfg):
      decoding_cfg.greedy.use_cuda_graph_decoder = False
      decoding_cfg.greedy.loop_labels = False
  model.change_decoding_strategy(decoding_cfg)
  ```
- [x] Замерить реальную скорость на RTX 5090
  - Результат: **132.7x realtime** (2.1x быстрее Whisper)

### Фаза 2: Реализация транскрайбера ✅ ЗАВЕРШЕНА

- [x] Создать `server/transcribers/parakeet.py`
- [x] Реализовать тот же интерфейс что у Whisper:
  ```python
  class ParakeetTranscriber(BaseTranscriber):
      def load(self) -> None
      def transcribe(self, audio: np.ndarray) -> TranscriptionResult
      def unload(self) -> None
  ```
- [ ] Добавить поддержку streaming (chunked inference) — *на будущее*
- [ ] Обработка timestamps для синхронизации — *на будущее*

### Фаза 3: Интеграция в сервер ✅ ЗАВЕРШЕНА

- [x] Рефакторинг: создан `server/transcribers/` модуль
- [x] Фабрика транскрайберов:
  ```python
  from server.transcribers import create_transcriber
  transcriber = create_transcriber("parakeet")  # или "whisper"
  ```
- [x] CLI параметр `--transcriber parakeet`
- [ ] Переключение в runtime через WebSocket — *на будущее*
- [ ] Обновить `requirements.txt` — *нужно добавить nemo_toolkit*

### Фаза 4: Тестирование

- [ ] Сравнить качество на реальных звонках (EN → RU)
- [ ] Замерить latency (время до первого слова)
- [ ] Проверить использование VRAM
- [ ] Stress-тест на длинных сессиях

### Фаза 5: Оптимизация

- [ ] Настроить batch size для оптимальной производительности
- [ ] Рассмотреть local attention для длинного аудио
- [ ] Кэширование модели между запросами

---

## Структура файлов (реализовано)

```
server/
├── transcribers/
│   ├── __init__.py         # Фабрика create_transcriber()
│   ├── base.py             # BaseTranscriber, TranscriptionResult
│   ├── whisper.py          # WhisperTranscriber
│   └── parakeet.py         # ParakeetTranscriber
├── transcriber.py          # [deprecated] старый файл
├── main.py                 # --transcriber whisper|parakeet
└── requirements.txt        # TODO: добавить nemo_toolkit[asr]
```

### Использование

```bash
# Запуск с Whisper (по умолчанию)
python -m server.main

# Запуск с Parakeet (2x быстрее)
python -m server.main --transcriber parakeet
```

---

## Риски и митигация

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| NeMo не поддерживает RTX 5090 | Средняя | Использовать nightly PyTorch, проверить CUDA 12.x |
| Streaming хуже чем у Whisper | Средняя | Оставить Whisper как fallback |
| Больше VRAM чем ожидалось | Низкая | У нас 32GB на 5090, должно хватить |
| Качество на русском хуже | Низкая | Протестировать заранее, RU в списке языков |

---

## Команды для тестирования

```bash
# Установка NeMo (WSL)
pip install nemo_toolkit[asr]

# Быстрый тест
python -c "
import nemo.collections.asr as nemo_asr
model = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3')
result = model.transcribe(['test.wav'])
print(result[0].text)
"

# Бенчмарк скорости
python -c "
import time
import nemo.collections.asr as nemo_asr

model = nemo_asr.models.ASRModel.from_pretrained('nvidia/parakeet-tdt-0.6b-v3')

start = time.time()
result = model.transcribe(['long_audio.wav'])
elapsed = time.time() - start

print(f'Transcribed in {elapsed:.2f}s')
print(result[0].text[:200])
"
```

---

## Ссылки

- [Parakeet TDT v3 на HuggingFace](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v3)
- [NeMo Toolkit GitHub](https://github.com/NVIDIA-NeMo/NeMo)
- [NeMo ASR Documentation](https://docs.nvidia.com/nemo-framework/user-guide/latest/nemotoolkit/asr/intro.html)
- [NVIDIA Blog: Parakeet ASR](https://developer.nvidia.com/blog/pushing-the-boundaries-of-speech-recognition-with-nemo-parakeet-asr-models/)
- [Streaming Inference Example](https://modal.com/docs/examples/streaming_parakeet)

---

## Следующий шаг

**Фаза 2:** Создать `server/transcribers/parakeet.py` с тем же интерфейсом что у Whisper.

### Зависимости для обновления

```bash
# server/requirements.txt - добавить:
nemo_toolkit[asr]>=2.6.0

# Для RTX 5090 требуется PyTorch nightly:
# pip install --pre torch torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
```

### Конфликты зависимостей

- `googletrans` требует `httpx==0.13.3`, но NeMo требует новее
- Решение: использовать `deep-translator` вместо `googletrans` или изолировать в Docker
