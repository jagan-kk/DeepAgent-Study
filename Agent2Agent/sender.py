from pathlib import Path
import smtplib
from email.message import EmailMessage
from deepagents import create_deep_agent
from langchain_openrouter import ChatOpenRouter
from langchain_core.tools import tool
from dotenv import load_dotenv, dotenv_values

PROJECT_DIR = Path(__file__).parent.resolve()
ENV_FILE = PROJECT_DIR / ".env"
load_dotenv(ENV_FILE, override=True)

env = dotenv_values(ENV_FILE)
SENDER_EMAIL = env.get("SENDER_EMAIL", "")
SENDER_PASSWORD = env.get("SENDER_PASSWORD", "")

@tool
def send_email(recipient_email: str, subject: str, body: str) -> str:
    """Sends an email to a recipient via Gmail SMTP."""
    recipient_email = recipient_email.strip()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, SENDER_PASSWORD)
            smtp.send_message(msg)
        return f"Email sent to {recipient_email}"
    except Exception as e:
        return f"Failed sending to {recipient_email}: {str(e)}"

@tool
def get_interns_list() -> str:
    """Reads interns.txt containing matched candidates."""
    interns_file = PROJECT_DIR / "interns.txt"
    if not interns_file.exists():
        return "Error: interns.txt not found."
    return interns_file.read_text(encoding="utf-8")

openrouter_model = ChatOpenRouter(
    model="google/gemini-2.5-flash",
    temperature=0.7,
    max_tokens=2000,
    api_key=env["OPENROUTER_API_KEY"],
)

def build_sender_agent():
    return create_deep_agent(
        model=openrouter_model,
        tools=[get_interns_list, send_email],
        system_prompt=(
            "You are an automated email dispatcher.\n\n"
            "Steps to complete:\n"
            "1. Read candidate list using `get_interns_list`.\n"
            "2. Parse entries formatted as 'Name - email'.\n"
            "3. Generate internship offer emails.\n"
            "4. Send each email using `send_email`.\n"
            "5. Report transmission results."
        ),
    )
