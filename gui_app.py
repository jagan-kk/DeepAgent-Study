import sys
import os
from dotenv import load_dotenv
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout, 
                             QTextEdit, QLineEdit, QPushButton, QLabel)
from PyQt6.QtCore import QThread, pyqtSignal

# Import your deepagents setup
from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend

load_dotenv()
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
os.environ["OPENROUTER_API_KEY"] = os.getenv("OPENROUTER_API_KEY")

# 1. Background worker thread to prevent UI freezing
class AgentWorker(QThread):
    # Signals to communicate back with the main UI thread
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, user_command):
        super().__init__()
        self.user_command = user_command

    def run(self):
        try:
            # Initialize your agent inside the thread execution context
            agent = create_deep_agent(
                model="openrouter:tencent/hy3:free",
                tools=[],
                system_prompt="""You are a helpful file-management assistant.
You are working in a virtual filesystem. The project root is /.
Rules:
Treat tool results as the source of truth.
When the ls tool returns paths such as /.env, /main.py, or /.git/, those are entries inside the current project directory /.
Never say a directory is empty if the ls tool returned one or more entries.
Clearly separate files and directories in your response.
If a tool call fails, explain the error and try a reasonable relative path such as . or /.
""",
                backend=LocalShellBackend(
                    root_dir=r"C:\Users\USER\Documents\Task\DeepAgent",
                    virtual_mode=True,
                    env=os.environ.copy()
                )
            )
            
            # Invoke the agent
            result = agent.invoke(
                {"messages": [{"role": "user", "content": self.user_command}]}
            )
            
            # Extract the response string
            response_text = result["messages"][-1].content
            self.response_received.emit(response_text)
            
        except Exception as e:
            self.error_occurred.emit(str(e))

# 2. Main Windows Application Interface
class AgentApp(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # Window setup
        self.setWindowTitle("DeepAgent File Manager")
        self.resize(700, 500)
        
        # Layouts
        layout = QVBoxLayout()
        input_layout = QHBoxLayout()

        # Chat display log (Read-only)
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("Agent activity log will appear here...")
        
        # User input box
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter a command (e.g., 'create a new file called test.py')")
        self.input_field.returnPressed.connect(self.send_command) # Press Enter to send
        
        # Send Button
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_command)

        # Build UI layout hierarchy
        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_button)
        
        layout.addWidget(QLabel("<h3>Virtual Filesystem Agent</h3>"))
        layout.addWidget(self.chat_display)
        layout.addLayout(input_layout)
        
        self.setLayout(layout)

    def send_command(self):
        cmd = self.input_field.text().strip()
        if not cmd:
            return

        # Display user text in chat log
        self.chat_display.append(f"<b>You:</b> {cmd}")
        self.input_field.clear()
        
        # Disable inputs while the agent is processing
        self.input_field.setEnabled(False)
        self.send_button.setEnabled(False)
        self.chat_display.append("<i>Agent is thinking...</i>")

        # Spawn the background worker thread
        self.worker = AgentWorker(cmd)
        self.worker.response_received.connect(self.handle_response)
        self.worker.error_occurred.connect(self.handle_error)
        self.worker.start()

    def handle_response(self, text):
        # Remove the 'thinking...' placeholder line and show the output
        self.chat_display.append(f"<b>Agent:</b> {text}\n")
        self.cleanup_after_task()

    def handle_error(self, err_msg):
        self.chat_display.append(f"<font color='red'><b>Error:</b> {err_msg}</font>\n")
        self.cleanup_after_task()

    def cleanup_after_task(self):
        # Re-enable interactive items
        self.input_field.setEnabled(True)
        self.send_button.setEnabled(True)
        self.input_field.setFocus()

# 3. Application entry point
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AgentApp()
    window.show()
    sys.exit(app.exec())