import time
from pathlib import Path
from deepagents import create_deep_agent
from langchain_openrouter import ChatOpenRouter
from pypdf import PdfReader
from langchain_core.tools import tool
from dotenv import load_dotenv, dotenv_values

PROJECT_DIR = Path(__file__).parent.resolve()
ENV_FILE = PROJECT_DIR / ".env"
load_dotenv(ENV_FILE, override=True)

@tool
def get_candidate_resumes() -> dict[str, str]:
    """Reads all PDF resumes from the 'candidate' directory and returns a map of filename to text content."""
    candidate_dir = PROJECT_DIR / "candidate"
    if not candidate_dir.exists():
        return {}
    
    resumes = {}
    for pdf_path in candidate_dir.glob("*.pdf"):
        reader = PdfReader(pdf_path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        resumes[pdf_path.name] = text
    return resumes

@tool
def save_interns(content: str) -> str:
    """Writes matching candidate names and emails to interns.txt."""
    output_path = PROJECT_DIR / "interns.txt"
    output_path.write_text(content, encoding="utf-8")
    return f"Successfully written to {output_path}"

openrouter_model = ChatOpenRouter(
    model="google/gemini-2.5-flash",
    temperature=0,
    max_tokens=2000,
    api_key=dotenv_values(ENV_FILE)["OPENROUTER_API_KEY"],
)

def build_recruiting_agent():
    job_desc_file = PROJECT_DIR / "job_description.txt"
    job_desc = job_desc_file.read_text(encoding="utf-8") if job_desc_file.exists() else "No job description provided."

    return create_deep_agent(
        model=openrouter_model,
        tools=[get_candidate_resumes, save_interns],
        system_prompt=(
            "You are a recruiting Analyzer.\n\n"
            f"Here is the Job Description:\n---\n{job_desc}\n---\n\n"
            "Steps to complete:\n"
            "1. Call `get_candidate_resumes` to fetch candidate resumes.\n"
            "2. Evaluate candidates against the job description.\n"
            "3. For candidates matching at least 80%, format as 'Name - email' (one per line).\n"
            "4. Call `save_interns` to save to 'interns.txt'.\n"
            "5. Report which candidates were saved."
        ),
    )