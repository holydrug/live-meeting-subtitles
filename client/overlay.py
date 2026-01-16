"""
Overlay UI for displaying transcription and translation.
Semi-transparent window that stays on top.
"""

from collections import deque
from dataclasses import dataclass
import time

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QMouseEvent


@dataclass
class TextEntry:
    original: str
    translated: str
    timestamp: float


class OverlayWindow(QWidget):
    """Semi-transparent overlay for subtitles."""

    # Signal for thread-safe updates
    text_received = pyqtSignal(str, str)  # original, translated
    status_received = pyqtSignal(str)

    def __init__(
        self,
        width: int = 700,
        max_lines: int = 6,
        font_size: int = 15,
        opacity: float = 0.9,
        position: str = "bottom-right",
    ):
        super().__init__()

        self.max_lines = max_lines
        self.font_size = font_size
        self._entries: deque[TextEntry] = deque(maxlen=max_lines)
        self._drag_pos: QPoint | None = None

        # Window setup
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(width)

        self._setup_ui(opacity)
        self._position_window(position)

        # Connect signals
        self.text_received.connect(self._on_text)
        self.status_received.connect(self._on_status)

    def _setup_ui(self, opacity: float):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        # Container with background
        self.container = QWidget()
        self.container.setStyleSheet(f"""
            QWidget {{
                background-color: rgba(20, 20, 30, {int(opacity * 255)});
                border-radius: 12px;
            }}
        """)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 12)
        container_layout.setSpacing(8)

        # Header
        header = QHBoxLayout()

        self.status_label = QLabel("Connecting...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px;")
        header.addWidget(self.status_label)

        header.addStretch()

        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #666;
                border: none;
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover { color: #ff5555; }
        """)
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)

        container_layout.addLayout(header)

        # Text area
        self.text_layout = QVBoxLayout()
        self.text_layout.setSpacing(10)
        container_layout.addLayout(self.text_layout)

        # Placeholder
        self.placeholder = QLabel("Waiting for speech...")
        self.placeholder.setStyleSheet(f"color: #555; font-size: {self.font_size}px; font-style: italic;")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.text_layout.addWidget(self.placeholder)

        layout.addWidget(self.container)

    def _position_window(self, position: str):
        screen = QApplication.primaryScreen().geometry()
        margin = 30

        if "right" in position:
            x = screen.width() - self.width() - margin
        else:
            x = margin

        if "bottom" in position:
            y = screen.height() - 350 - margin
        else:
            y = margin

        self.move(x, y)

    def add_text(self, original: str, translated: str):
        """Thread-safe method to add text."""
        self.text_received.emit(original, translated)

    def set_status(self, status: str):
        """Thread-safe method to update status."""
        self.status_received.emit(status)

    def _on_text(self, original: str, translated: str):
        self.placeholder.hide()

        entry = TextEntry(original, translated, time.time())
        self._entries.append(entry)
        self._rebuild_display()

    def _on_status(self, status: str):
        self.status_label.setText(status)

    def _rebuild_display(self):
        # Clear old entries
        while self.text_layout.count() > 1:
            item = self.text_layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        # Add entries
        for entry in self._entries:
            widget = self._create_entry(entry)
            self.text_layout.addWidget(widget)

        self.adjustSize()

    def _create_entry(self, entry: TextEntry) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        font = QFont("Segoe UI", self.font_size)

        # Original
        orig_label = QLabel(entry.original)
        orig_label.setFont(font)
        orig_label.setStyleSheet("color: #ffffff;")
        orig_label.setWordWrap(True)
        layout.addWidget(orig_label)

        # Translation
        if entry.translated:
            trans_label = QLabel(entry.translated)
            trans_label.setFont(font)
            trans_label.setStyleSheet("color: #7cb7ff;")
            trans_label.setWordWrap(True)
            layout.addWidget(trans_label)

        return widget

    def clear(self):
        self._entries.clear()
        self._rebuild_display()
        self.placeholder.show()

    # Drag to move
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QMouseEvent):
        self._drag_pos = None
