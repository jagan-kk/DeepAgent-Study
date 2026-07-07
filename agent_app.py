import sys
import os
from pathlib import Path
from langchain.agents.middleware import ModelFallbackMiddleware

from dotenv import load_dotenv
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLineEdit,
    QPushButton, QLabel, QFileDialog, QFrame, QSizePolicy, QToolButton,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QSettings
from PyQt6.QtGui import QIcon, QFont, QTextCursor

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

load_dotenv()
for k in ("GOOGLE_API_KEY", "OPENROUTER_API_KEY"):
    v = os.getenv(k)
    if v:
        os.environ[k] = v


DEFAULT_DIR = str(Path.home())

SYSTEM_PROMPT = """
You are a senior AI software engineer and intelligent workspace assistant. You have full access to a virtual filesystem (rooting at /) through your tools. Your goal is to help the user manage their workspace, analyze existing code, search for context, and write production-grade software.

### Core Philosophy
1. **Context is King:** Always explore and understand the existing codebase, structure, and configuration files before proposing changes.
2. **Action-Oriented:** Solve problems completely. Don't just explain how to fix a bug—provide the exact code or use your tools to apply the fix when requested.
3. **Rigorous File Awareness:** Treat tool results as absolute truth. Separate files and directories explicitly. If a directory contains hidden files (like `.env` or `.git`), it is NOT empty.

### Operational Modes

#### 1. File & Workspace Management
- Navigate directories using relative or absolute paths.
- Keep track of the project structure. When introducing the file tree, clearly distinguish between `📁 Directories/` and `📄 Files`.
- Never guess if a file exists; look it up. If a tool call fails, gracefully fallback to checking the project root (`/`) or current directory (`.`).

#### 2. Codebase Search & Analysis
- Use search tools to find function definitions, class structures, or specific keywords across the entire project.
- Synthesize information from multiple files (e.g., matching a backend route definition with its frontend API call).

#### 3. Coding & Refactoring
- Write clean, modular, and well-documented code adhering to best practices for the detected language.
- When modifying code, ensure you don't accidentally drop existing logic or dependencies unless explicitly asked.
- Provide clear explanations of *why* a architectural choice or bug fix was made.

### Response Guidelines
- **Tone:** Technical, concise, helpful, and direct. Avoid conversational filler; focus on the code and the filesystem.
- **Formatting:** Use clear Markdown headers, bold key files/paths, and wrap all code blocks in their correct language syntax identifiers.
- **Error Handling:** If a command or tool fails, explain exactly why it failed (e.g., "Permission denied", "File not found") and immediately offer a correction or an alternative path.

CRITICAL: At the end of every task, or when a new project rule/issue is discovered, you must use your file editing tools to update ./AGENTS.md with the current state, progress, and plans. Do not exit without logging your state here.
"""


# ---------- Worker ----------
class AgentWorker(QThread):
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    

    def __init__(self, user_command: str, root_dir: str):
        super().__init__()
        self.user_command = user_command
        self.root_dir = root_dir

    def run(self):
        backend=LocalShellBackend(
                    root_dir=self.root_dir,
                    virtual_mode=True,
                    env=os.environ.copy(),
                )
        try:
            agent = create_deep_agent(
                model="ollama:qwen3:8b",
                tools=[],  # Use the backend's tools
                memory=["./AGENTS.md"],
                skills=["./skills"],
                system_prompt=SYSTEM_PROMPT,
                backend=backend,
                middleware=[
                    ModelFallbackMiddleware(
                    "google_genai:gemini-2.5-flash", # First fallback
                    "openrouter:tencent/hy3:free", # Second fallback
        ),
                ]
            )
            result = agent.invoke(
                {"messages": [{"role": "user", "content": self.user_command}]}
            )
            self.response_received.emit(result["messages"][-1].content)
        except Exception as e:
            self.error_occurred.emit(str(e))


# ---------- Modern dark stylesheet ----------
STYLE = """
* { font-family: 'Segoe UI', 'SF Pro Display', system-ui, sans-serif; }
QWidget#Root { background: #0f1216; color: #e6e9ef; }

QLabel#Title { font-size: 20px; font-weight: 700; color: #ffffff; letter-spacing: 0.3px; }
QLabel#Subtitle { color: #8b93a7; font-size: 12px; }

QFrame#Card {
    background: #171b22;
    border: 1px solid #232935;
    border-radius: 14px;
}

QLabel#DirLabel { color: #8b93a7; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }
QLabel#DirPath { color: #d7dbe4; font-size: 13px; font-family: 'JetBrains Mono','Consolas',monospace; }

QPushButton {
    background: #6366f1; color: white; border: none;
    padding: 9px 18px; border-radius: 9px; font-weight: 600; font-size: 13px;
}
QPushButton:hover { background: #7c7ff2; }
QPushButton:pressed { background: #4f52d6; }
QPushButton:disabled { background: #2a2f3a; color: #6b7280; }

QPushButton#Ghost {
    background: transparent; color: #c7ccd8; border: 1px solid #2f3542;
}
QPushButton#Ghost:hover { background: #1e2330; border-color: #4a5163; color: #ffffff; }

QLineEdit {
    background: #0f1319; color: #e6e9ef; border: 1px solid #262c39;
    padding: 11px 14px; border-radius: 10px; font-size: 13px; selection-background-color: #6366f1;
}
QLineEdit:focus { border: 1px solid #6366f1; }

QTextEdit {
    background: #0b0e13; color: #d7dbe4; border: 1px solid #1c2029;
    border-radius: 12px; padding: 14px; font-size: 13px;
    selection-background-color: #6366f1;
}
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px; }
QScrollBar::handle:vertical { background: #2a3040; border-radius: 5px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #3a4256; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

QLabel#Status { color: #8b93a7; font-size: 11px; }
QLabel#Dot { font-size: 14px; }
"""


class AgentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.settings = QSettings("DeepAgent", "FileManager")
        self.root_dir = self.settings.value("root_dir", DEFAULT_DIR)
        self.worker: AgentWorker | None = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("DeepAgent — File Manager")
        self.resize(880, 640)
        self.setStyleSheet(STYLE)

        root = QVBoxLayout(self) 
        root.setContentsMargins(22, 22, 22, 22)
        root.setSpacing(16)

        # ---- Header ----
        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("⚡ DeepAgent")
        title.setObjectName("Title")
        subtitle = QLabel("Virtual filesystem assistant")
        subtitle.setObjectName("Subtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.setSpacing(2)
        header.addLayout(title_box)
        header.addStretch()

        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("Dot")
        self.status_dot.setStyleSheet("color:#22c55e;")
        self.status_text = QLabel("Ready")
        self.status_text.setObjectName("Status")
        header.addWidget(self.status_dot)
        header.addWidget(self.status_text)
        root.addLayout(header)

        # ---- Directory card ----
        dir_card = QFrame()
        dir_card.setObjectName("Card")
        dc = QHBoxLayout(dir_card)
        dc.setContentsMargins(16, 12, 16, 12)
        dc.setSpacing(12)

        dir_info = QVBoxLayout()
        dir_info.setSpacing(2)
        lbl = QLabel("WORKING DIRECTORY")
        lbl.setObjectName("DirLabel")
        self.dir_path_label = QLabel(self.root_dir)
        self.dir_path_label.setObjectName("DirPath")
        self.dir_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        dir_info.addWidget(lbl)
        dir_info.addWidget(self.dir_path_label)
        dc.addLayout(dir_info, 1)

        browse_btn = QPushButton("📁  Browse")
        browse_btn.setObjectName("Ghost")
        browse_btn.clicked.connect(self.browse_dir)

        reset_btn = QPushButton("↺  Home")
        reset_btn.setObjectName("Ghost")
        reset_btn.clicked.connect(lambda: self.set_root_dir(DEFAULT_DIR))

        dc.addWidget(reset_btn)
        dc.addWidget(browse_btn)
        root.addWidget(dir_card)

        # ---- Chat display ----
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("💬  Agent activity will appear here…")
        root.addWidget(self.chat_display, 1)

        # ---- Input row ----
        input_row = QHBoxLayout()
        input_row.setSpacing(10)
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Ask the agent…  (e.g. list files, create test.py)")
        self.input_field.returnPressed.connect(self.send_command)

        self.send_button = QPushButton("Send  ➤")
        self.send_button.clicked.connect(self.send_command)

        input_row.addWidget(self.input_field, 1)
        input_row.addWidget(self.send_button)
        root.addLayout(input_row)

    # ---------- Directory handling ----------
    def browse_dir(self):
        chosen = QFileDialog.getExistingDirectory(
            self, "Select working directory", self.root_dir
        )
        if chosen:
            self.set_root_dir(chosen)

    def set_root_dir(self, path: str):
        self.root_dir = path
        self.dir_path_label.setText(path)
        self.settings.setValue("root_dir", path)
        self.chat_display.append(
            f"<div style='color:#8b93a7;'>📂 Working directory set to "
            f"<span style='color:#a5b4fc;'>{path}</span></div>"
        )

    # ---------- Chat ----------
    def _set_status(self, text: str, color: str):
        self.status_text.setText(text)
        self.status_dot.setStyleSheet(f"color:{color};")

    def send_command(self):
        cmd = self.input_field.text().strip()
        if not cmd:
            return
        self.chat_display.append(
            f"<div style='margin-top:8px;'><b style='color:#a5b4fc;'>You</b> "
            f"<span style='color:#e6e9ef;'>{cmd}</span></div>"
        )
        self.input_field.clear()
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self._set_status("Thinking…", "#f59e0b")
        self.chat_display.append(
            "<div style='color:#6b7280;font-style:italic;'>Agent is thinking…</div>"
        )

        self.worker = AgentWorker(cmd, self.root_dir)
        self.worker.response_received.connect(self.handle_response)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.start()

    def handle_response(self, text: str):
        safe = text.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        self.chat_display.append(
            f"<div style='margin-top:4px;'><b style='color:#22c55e;'>Agent</b><br>"
            f"<span style='color:#d7dbe4;'>{safe}</span></div>"
        )
        self.cleanup_after_task()

    def handle_error(self, err_msg: str):
        self.chat_display.append(
            f"<div style='margin-top:4px;'><b style='color:#ef4444;'>Error</b> "
            f"<span style='color:#fca5a5;'>{err_msg}</span></div>"
        )
        self.cleanup_after_task()

    def cleanup_after_task(self):
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()
        self._set_status("Ready", "#22c55e")
        self.chat_display.moveCursor(QTextCursor.MoveOperation.End)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AgentApp()
    window.show()
    sys.exit(app.exec())
